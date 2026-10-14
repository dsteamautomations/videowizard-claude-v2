"""Analysis A1–A14 with a fake Gemini transport; worker runs in-process against local storage."""
import json
import re
import time
from pathlib import Path

import psycopg
import pytest

from app import analysis_jobs
from app.video_evidence.transport import GeminiTransportError
from conftest import connected, vw
from test_voice_media import clip, drain, fake, run_until_media  # noqa: F401


class FakeTransport:
    """Builds a schema-valid answer from the frozen request. Modes drive the failure cases."""
    mode = 'ok'            # ok | text | wrong_source | http429 | http429_forever | conn_after_dispatch | crash_after_upload | crash_after_generate
    calls = {'upload': 0, 'generate': 0}
    seen_modes = []

    def __init__(self, api_key, model, terminal_deadline_seconds, initial_soft_wait_seconds, on_update, capture_answer_deltas, allow_agentic_video):
        self.model = model

    def upload(self, path, mime, sha, existing_receipt=None):
        FakeTransport.calls['upload'] += 1
        if existing_receipt:
            return existing_receipt
        if FakeTransport.mode == 'crash_after_upload':
            FakeTransport.mode = 'ok'
            raise OSError('worker killed after upload')
        return {'uri': 'files/' + sha[:12], 'mimeType': mime, 'sha256': sha, 'state': 'ACTIVE', 'identity_verified': True}

    def generate(self, payload):
        FakeTransport.calls['generate'] += 1
        prompt = [p['text'] for p in payload['contents'][0]['parts'] if 'text' in p][-1]
        FakeTransport.seen_modes.append('AGENTIC' if payload['contents'][0]['parts'][0].get('mediaProcessing') == 'AGENTIC' else 'STATIC')
        mode = FakeTransport.mode
        if mode == 'http429' or mode == 'http429_forever':
            if mode == 'http429':
                FakeTransport.mode = 'ok'
            raise GeminiTransportError('http_error', 'rate limited', http_status=429, metadata={'provider_error': {'format': 'google_error', 'status': 'RESOURCE_EXHAUSTED'}})
        if mode == 'conn_after_dispatch':
            FakeTransport.mode = 'ok'
            raise GeminiTransportError('connection_error', 'socket closed')
        schema = payload['generationConfig']['responseJsonSchema']
        if 'answers' in schema.get('properties', {}):  # planning inspection (flash schema)
            qid = re.search(r'"id": "(Q[0-9]+)"', prompt).group(1)
            sid = re.search(r'"source_id": "([0-9a-f]{16})"', prompt).group(1)
            body = {'answers': [{'question_id': qid, 'status': 'answered', 'answer': 'The block does not move.',
                                 'observations': [{'source_id': sid, 'start_s': 0.2, 'end_s': 1.0, 'visual_observation': 'block still on table', 'relevant_speech': '', 'limits': 'none'}],
                                 'interpretation': 'static subject', 'uncertainty': 'low', 'inspection_method': 'full clip', 'sampling_rate': '1 fps'}],
                    'inspection_limits': 'short clip'}
            raw = json.dumps(body)
            return {'body': body, 'metadata': {'finish_reason': 'STOP', 'usage': {'promptTokenCount': 1200, 'candidatesTokenCount': 100}, 'elapsed_seconds': 0.5}, 'raw': raw}
        src = schema['$defs']['source']['properties']
        request_id = re.search(r'"request_id": "([0-9a-f]+)"', prompt).group(1)
        script_id = re.search(r'"script_id": "([0-9a-f]{64})"', prompt).group(1)
        end = float(re.search(r'"end_s": ([0-9.]+)', prompt).group(1))
        body = {'contract_version': 'source-evidence-v2', 'request_id': request_id, 'script_id': script_id,
                'sources': [{'source_id': 'WRONG' if mode == 'wrong_source' else src['source_id']['enum'][0], 'window_id': 'full', 'media_kind': 'video',
                             'clock': 'original_source_seconds', 'requested_interval': {'start_s': 0, 'end_s': end}, 'review_status': 'complete',
                             'coverage': {'visual': [{'interval': {'start_s': 0, 'end_s': end}, 'status': 'reviewed', 'note': None}], 'audio': [{'interval': {'start_s': 0, 'end_s': end}, 'state': 'silence', 'note': None}]},
                             'scope_omissions': [], 'entities': [{'id': 'E1', 'kind': 'object', 'label': 'earth block', 'uncertainty': None}],
                             'speech': [],
                             'visual_events': [{'id': 'V1', 'interval': {'start_s': 0, 'end_s': min(1.0, end)}, 'label': 'block on table', 'description': 'a pressed earth block rests on a table',
                                                'actor_ids': [], 'object_ids': ['E1'], 'context_result': None, 'camera_framing': 'close', 'uncertainty': None},
                                               {'id': 'V2', 'interval': {'start_s': 0, 'end_s': end + 50}, 'label': 'bad row', 'description': 'outside the window',
                                                'actor_ids': [], 'object_ids': ['NOPE'], 'context_result': None, 'camera_framing': None, 'uncertainty': None}],
                             'visible_text': [], 'interpretations': [], 'editorial_ideas': [], 'visual_slot_guidance': [], 'unresolved': []}],
                'additional_analysis': {k: '' for k in ('attempts', 'crop_guidance', 'clean_handles', 'continuity', 'preview_frames', 'speech_action_links', 'shorter_explanations', 'workflow_acknowledgement', 'unavailable')} | {'script_support': {'claims': []}},
                'claim_evidence': [], 'world_markers': [], 'evidence_limits': [], 'descriptive_name': 'earth-block-table'}
        raw = 'not json at all {' if mode == 'text' else json.dumps(body)
        if mode == 'crash_after_generate':
            FakeTransport.mode = 'ok'
            FakeTransport.pending_raw = raw
            raise OSError('worker killed after generate')
        return {'body': body if mode != 'text' else {}, 'metadata': {'finish_reason': 'STOP', 'usage': {'promptTokenCount': 1200, 'candidatesTokenCount': 400}, 'elapsed_seconds': 1.5}, 'raw': raw}


@pytest.fixture
def gemini(monkeypatch, tmp_path):
    FakeTransport.mode, FakeTransport.calls, FakeTransport.seen_modes = 'ok', {'upload': 0, 'generate': 0}, []
    monkeypatch.setattr(analysis_jobs, 'transport_factory', FakeTransport)
    monkeypatch.setattr(analysis_jobs, 'SPOOL', tmp_path / 'spool')
    return FakeTransport


def run_until_analysis(home, database, fake, n_clips=3, seconds=1):
    code, ws = run_until_media(home, database, fake)
    for i in range(n_clips):
        clip(ws / 'in' / f'c{i}.mp4', seconds=seconds, tone=440 + 110 * i)
    assert vw(home, 'stage', 'media', 'prepare')[0] == 0
    rc, out, err = vw(home, 'stage', 'media', 'record', '--quote', 'yes')
    assert rc == 0, err
    return code, ws, out['summary']['units']['analysis']


START = ['analysis', 'start', '--camera-audio', 'allowed', '--film-type', 'documentary']


def test_a1_three_clips_succeed(home, database, fake, gemini):
    code, ws, units = run_until_analysis(home, database, fake)
    rc, out, err = vw(home, *START)
    assert rc == 0 and len(out['created']) == 3, err
    assert vw(home, *START)[1]['reused'] == units  # A12: same inputs, no new jobs
    drain()
    st = vw(home, 'analysis', 'status')[1]
    assert st['counts'] == {'retained': 3}
    u = st['units'][0]
    assert u['recorded'] and u['summary']['usable_rows']['visual_events'] == 1 and u['summary']['excluded_rows'] >= 1  # A8 in passing
    assert u['cost']['input_tokens'] == 1200 and u['summary']['descriptive_name'] == 'earth-block-table'
    nxt = vw(home, 'next')[1]
    assert nxt['stage'] == 'planning'
    with psycopg.connect(database) as c:
        assert c.execute("select count(*) from vw2_files where stage='analysis'").fetchone()[0] == 6
    assert gemini.seen_modes == ['STATIC'] * 3
    rc, out, _ = vw(home, *START)  # stage complete: start is no longer allowed
    assert rc == 2 and out['code'] == 'NOT_ALLOWED'


def test_a2_killed_after_upload_resumes_without_second_upload(home, database, fake, gemini):
    run_until_analysis(home, database, fake, n_clips=1)
    vw(home, *START)
    gemini.mode = 'crash_after_upload'
    assert analysis_jobs.tick() is True
    st = vw(home, 'analysis', 'status')[1]
    assert st['units'][0]['status'] == 'failed'  # before dispatch: failed, retry allowed
    assert vw(home, 'analysis', 'retry', '--unit', st['units'][0]['unit'], '--note', 'try again')[0] == 0
    drain()
    assert vw(home, 'analysis', 'status')[1]['counts'] == {'retained': 1}
    assert gemini.calls['generate'] == 1


def test_a3_killed_after_generate_recovers_from_receipt(home, database, fake, gemini):
    run_until_analysis(home, database, fake, n_clips=1)
    vw(home, *START)
    gemini.mode = 'crash_after_generate'
    analysis_jobs.tick()
    st = vw(home, 'analysis', 'status')[1]['units'][0]
    assert st['status'] == 'submission_unknown'
    # the journaled response exists in the spool (the fake "died" after the provider answered): write it as the worker would have
    job_id = st['job_id']
    analysis_jobs.durable(analysis_jobs.SPOOL / f'{job_id}.response.json', json.dumps({'raw': gemini.pending_raw, 'metadata': {'finish_reason': 'STOP', 'usage': {}}}).encode())
    assert vw(home, 'analysis', 'recover', '--unit', st['unit'])[0] == 0
    drain()
    assert vw(home, 'analysis', 'status')[1]['counts'] == {'retained': 1}
    assert gemini.calls['generate'] == 1  # never a second paid call


def test_a4_a5_capacity_retry_once_then_rejected(home, database, fake, gemini):
    run_until_analysis(home, database, fake, n_clips=1)
    vw(home, *START)
    gemini.mode = 'http429'
    drain()
    assert vw(home, 'analysis', 'status')[1]['counts'] == {'retained': 1} and gemini.calls['generate'] == 2
    # A5: a second clip run that is rate limited forever
    code, ws, units = run_until_analysis(home, database, fake, n_clips=1)
    vw(home, *START)
    gemini.calls['generate'] = 0
    gemini.mode = 'http429_forever'
    drain()
    st = vw(home, 'analysis', 'status')[1]['units'][0]
    assert st['status'] == 'rejected' and gemini.calls['generate'] == 2  # one automatic capacity retry, then stop
    for i in range(3):
        assert vw(home, 'analysis', 'retry', '--unit', st['unit'], '--note', 'again')[0] == 0
        drain()
    rc, out, _ = vw(home, 'analysis', 'retry', '--unit', st['unit'], '--note', 'again')
    assert rc == 3 and out['code'] == 'NEEDS_USER_DECISION'


def test_a6_text_not_json(home, database, fake, gemini):
    run_until_analysis(home, database, fake, n_clips=1)
    vw(home, *START)
    gemini.mode = 'text'
    drain()
    st = vw(home, 'analysis', 'status')[1]['units'][0]
    assert st['status'] == 'retained_unstructured' and 'not structured' in st['error'] and gemini.calls['generate'] == 1


def test_a7_identity_mismatch(home, database, fake, gemini):
    run_until_analysis(home, database, fake, n_clips=1)
    vw(home, *START)
    gemini.mode = 'wrong_source'
    drain()
    st = vw(home, 'analysis', 'status')[1]['units'][0]
    assert st['status'] == 'failed' and 'identity' in st['error'].lower()
    gemini.mode = 'ok'
    assert vw(home, 'analysis', 'retry', '--unit', st['unit'], '--note', 'retry')[0] == 0
    drain()
    assert vw(home, 'analysis', 'status')[1]['counts'] == {'retained': 1}


def test_a9_lease_expiry_then_recover(home, database, fake, gemini):
    run_until_analysis(home, database, fake, n_clips=1)
    vw(home, *START)
    with psycopg.connect(database) as c:
        c.execute("update vw2_jobs set status='running', lease_until = now() - interval '1 minute' where stage='analysis'")
    st = vw(home, 'analysis', 'status')[1]['units'][0]
    assert st['status'] == 'running'
    drain()  # the expired lease is reclaimed and processed
    assert vw(home, 'analysis', 'status')[1]['counts'] == {'retained': 1}


def test_a10_long_clip_uses_agentic(home, database, fake, gemini, monkeypatch):
    from app import db
    doc = db.stage_table('1')
    for st in doc:
        if st['name'] == 'analysis':
            monkeypatch.setitem(st['settings'], 'agentic_over_seconds', 1.5)
    run_until_analysis(home, database, fake, n_clips=1, seconds=2)
    vw(home, *START)
    drain()
    assert gemini.seen_modes == ['AGENTIC']


def test_a11_understand_audio_no(home, database, fake, gemini):
    run_until_analysis(home, database, fake, n_clips=1)
    rc, out, err = vw(home, 'analysis', 'start', '--camera-audio', 'excluded', '--film-type', 'doc', '--understand-audio', 'no')
    assert rc == 0, err
    drain()
    with psycopg.connect(database) as c:
        req = c.execute("select request from vw2_jobs where stage='analysis'").fetchone()[0]
    assert req['identity']['understand_audio'] is False and req['identity']['camera_audio'] == 'excluded'
    assert vw(home, 'analysis', 'status')[1]['counts'] == {'retained': 1}


def test_a13_global_cap_three(home, database, fake, gemini):
    run_until_analysis(home, database, fake, n_clips=5)
    vw(home, *START)
    with psycopg.connect(database) as c:
        c.execute("update vw2_jobs set status='running', lease_until = now() + interval '30 minutes' where stage='analysis' and unit in (select unit from vw2_jobs where stage='analysis' order by created_at limit 3)")
    assert analysis_jobs.tick() is False  # cap reached: nothing claimed
    with psycopg.connect(database) as c:
        c.execute("update vw2_jobs set status='queued', lease_until=null where stage='analysis'")
    drain()
    assert vw(home, 'analysis', 'status')[1]['counts'] == {'retained': 5}


def test_a14_exclude_one_clip(home, database, fake, gemini):
    code, ws, units = run_until_analysis(home, database, fake, n_clips=3)
    rc, out, err = vw(home, 'analysis', 'start', '--camera-audio', 'allowed', '--film-type', 'doc', '--exclude', units[2])
    assert rc == 0 and len(out['created']) == 2 and out['excluded'] == [units[2]]
    drain()
    nxt = vw(home, 'next')[1]
    assert nxt['stage'] == 'analysis' and nxt['units_open'] == [units[2]]
    assert vw(home, 'analysis', 'exclude', '--unit', units[2], '--note', 'shaky footage')[0] == 0
    st = vw(home, 'analysis', 'status')[1]
    assert vw(home, 'next')[1]['stage'] == 'planning'
    assert vw(home, 'view', '--stage', 'analysis')[1]['outputs'][-1]['summary']['excluded'] is True
