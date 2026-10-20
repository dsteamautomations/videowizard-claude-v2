"""Voice stage pieces as pure functions and faked server calls (design/39 4.1–4.6)."""
import argparse
import json
import threading

import pytest

from conftest import STAGES
import vw
from stages_av import voice_prepare, voice_record
from stages_text import digest, script_prepare, script_record

SCRIPT = {'spoken_text': 'Earth blocks are pressed.\n\nNot fired.\n', 'passages': {'P001': 'Earth blocks are pressed.', 'P002': 'Not fired.'},
          'beats': [{'beat_id': 'BEAT_01', 'passage_id': 'P001', 'text': 'Earth blocks are pressed.'}, {'beat_id': 'BEAT_02', 'passage_id': 'P002', 'text': 'Not fired.'}]}
SCRIPT['content_digest'] = digest(SCRIPT['spoken_text'])
BRIEF = {'summary': {'purpose': 'p', 'audience': 'a', 'message': 'm', 'tone': 'calm', 'ending': 'e', 'constraints': '', 'content_digest': 'abc',
                     'production': {'narration_language': 'en', 'field_speech_languages': ['ta']}}}
LAST = {'run': 'VW-3', 'voice_id': 'v9', 'name': 'UD - Narrator', 'model_id': 'eleven_v4', 'settings': {'stability': 0.5, 'similarity_boost': 0.75}, 'choice_note': 'warm'}


def prior_of():
    return lambda stage: {'brief': BRIEF, 'script': {'summary': {'content_digest': SCRIPT['content_digest']}}}[stage]


@pytest.fixture
def vws(ws):
    (ws / 'out' / 'script.json').write_text(json.dumps(SCRIPT), encoding='utf-8')
    return ws


# ---------- 4.2 prepare inputs ----------

def test_voice_prepare_passes_brief_languages_and_last_voice(vws):
    out = voice_prepare(vws, STAGES['voice'], prior_of(), last_voice=LAST)
    i = out['inputs']
    assert i['brief']['tone'] == 'calm' and i['narration_language'] == 'en' and i['field_speech_languages'] == ['ta'] and i['last_voice'] == LAST
    assert 'UD - Narrator' in out['message'] and out['prepared_at']
    out = voice_prepare(vws, STAGES['voice'], prior_of())
    assert out['inputs']['last_voice'] is None and 'last voice' not in out['message'].lower()


# ---------- 4.3 length warning ----------

def test_script_record_warns_over_the_v4_limit(ws):
    intake = {'summary': {'title': 'T', 'client': 'VK', 'source_digest': ''}}
    prior = lambda stage: {'intake': intake, 'brief': BRIEF}[stage]
    for n, warned in ((10000, False), (10001, True)):
        text = ('a' * (n - 2)) + '.\n'   # exactly n characters after record's strip + newline
        intake['summary']['source_digest'] = digest(text)
        (ws / 'out' / 'source.txt').write_text(text, encoding='utf-8')
        script_prepare(ws, STAGES['script'], prior)
        (ws / 'out' / 'script.json').write_text(json.dumps({'spoken_text': text, 'notes': '', 'assessment': '', 'changes': []}), encoding='utf-8')
        s = script_record(ws, STAGES['script'], prior)['summary']
        assert s['characters'] == n and (('length_warning' in s) is warned), n
        if warned:
            assert '10,000' in s['length_warning'] and 'requests and joined' in s['length_warning']


# ---------- 4.4 wait inside the tool ----------

def jobs_args(**kw):
    return argparse.Namespace(**{'what': 'jobs', 'wait': 0, 'voice': [], 'excerpt': None, 'model': 'eleven_v4', 'settings': None, 'job': None, 'note': None,
                                 'scope': 'account', 'search': '', 'cursor': '', 'language': '', 'accent': '', 'gender': '', 'age': '', 'use_case': None,
                                 'high_quality': False, 'owner': None, **kw})


@pytest.fixture
def voice_harness(ws, monkeypatch):
    monkeypatch.setattr(vw, 'RUNS', ws.parent)
    monkeypatch.setattr(vw, 'active', lambda: {'code': 'VW-9', 'run_id': 'run-1', 'files': []})
    slept = []
    monkeypatch.setattr(vw.time, 'sleep', lambda s: slept.append(s))
    return ws, slept


def run_voice(a, capsys):
    with pytest.raises(SystemExit) as exc:
        vw.cmd_voice(a)
    out, err = capsys.readouterr()
    return exc.value.code, json.loads(out), err


def test_jobs_wait_returns_when_settled(voice_harness, monkeypatch, capsys):
    ws, slept = voice_harness
    answers = [[{'id': 'j1', 'status': 'queued'}], [{'id': 'j1', 'status': 'running'}], [{'id': 'j1', 'status': 'ready'}]]
    monkeypatch.setattr(vw, 'call', lambda method, path, wait=None, **kw: answers.pop(0) if answers else [{'id': 'j1', 'status': 'ready'}])
    code, out, err = run_voice(jobs_args(wait=120), capsys)
    assert code == 0 and out[0]['status'] == 'ready' and slept == [5, 5] and '1 ready' in err


def test_jobs_wait_times_out_and_names_still_open(voice_harness, monkeypatch, capsys):
    ws, slept = voice_harness
    clock = [0.0]
    monkeypatch.setattr(vw.time, 'monotonic', lambda: clock[0])

    def sleep(s):
        slept.append(s)
        clock[0] += s
    monkeypatch.setattr(vw.time, 'sleep', sleep)
    monkeypatch.setattr(vw, 'call', lambda method, path, wait=None, **kw: [{'id': 'j1', 'status': 'running'}])
    code, out, err = run_voice(jobs_args(wait=12), capsys)
    assert code == 0 and len(slept) == 3 and '1 still open' in err and 'run again' in err


def test_jobs_wait_stops_on_submission_unknown(voice_harness, monkeypatch, capsys):
    ws, slept = voice_harness
    monkeypatch.setattr(vw, 'call', lambda method, path, wait=None, **kw: [{'id': 'j7', 'status': 'submission_unknown'}])
    code, out, err = run_voice(jobs_args(wait=120), capsys)
    assert code == 0 and slept == [] and 'j7' in err and 'recover' in err


def test_jobs_without_wait_reads_once(voice_harness, monkeypatch, capsys):
    ws, slept = voice_harness
    monkeypatch.setattr(vw, 'call', lambda method, path, wait=None, **kw: [{'id': 'j1', 'status': 'queued'}])
    code, out, err = run_voice(jobs_args(), capsys)
    assert code == 0 and slept == [] and '1 still open' in err


# ---------- 4.5 pooled submission, 4.6 model line and note ----------

def test_auditions_go_through_the_pool_in_order_and_say_the_model(voice_harness, monkeypatch, capsys):
    ws, _ = voice_harness
    (ws / 'out' / 'script.json').write_text(json.dumps(SCRIPT), encoding='utf-8')
    posted = []

    def write(path, body, wait=None):
        posted.append((body['request']['voice_id'], threading.current_thread().name))
        return {'id': 'job-' + body['request']['voice_id'], 'status': 'queued',
                'request': {**body['request'], 'settings': body['request'].get('settings') or {'stability': 0.5, 'similarity_boost': 0.75}}}
    monkeypatch.setattr(vw, 'write', write)
    a = jobs_args(what='audition', voice=['v1', 'v2', 'v3', 'v4', 'v5', 'v6'], excerpt='Earth blocks are pressed.')
    code, out, err = run_voice(a, capsys)
    assert code == 0 and [j['voice_id'] for j in out['jobs']] == ['v1', 'v2', 'v3', 'v4', 'v5', 'v6']
    assert all(t != 'MainThread' for _, t in posted)
    assert 'eleven_v4' in err and 'stability 0.5' in err and 'similarity_boost 0.75' in err


def test_narrate_note_is_kept_and_copied_into_the_record(voice_harness, monkeypatch, capsys):
    ws, _ = voice_harness
    (ws / 'out' / 'script.json').write_text(json.dumps(SCRIPT), encoding='utf-8')
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: {'id': 'job-n', 'status': 'queued', 'request': {**body['request'], 'settings': {'stability': 0.5, 'similarity_boost': 0.75}}})
    code, out, err = run_voice(jobs_args(what='narrate', voice=['v2'], note='warmer, clearer on the numbers'), capsys)
    assert code == 0 and json.loads((ws / 'work' / 'voice-choice.json').read_text())['choice_note'] == 'warmer, clearer on the numbers'
    # the record copies the note; a minimal fetched job and timing make beat_durations work
    job = {'id': 'job-n', 'request': {'kind': 'narration', 'voice_id': 'v2', 'name': 'Ravi', 'model_id': 'eleven_v4', 'settings': {'stability': 0.5, 'similarity_boost': 0.75},
                                       'source_script': SCRIPT['content_digest']},
           'result': {'audio_key': 'k/n.mp3', 'sha256': 'ab' * 32, 'bytes': 10, 'timing_key': 'k/n.timing.json', 'timing_sha256': 'cd' * 32, 'timing_bytes': 5, 'duration_s': 2.0}, 'cost': {'characters': 37}}
    (ws / 'work' / 'voice-fetched.json').write_text(json.dumps(job), encoding='utf-8')
    words = [{'id': 'W1', 'text': 'Earth', 'passage_id': 'P001', 'start_s': 0.0, 'end_s': 0.3}, {'id': 'W2', 'text': 'pressed.', 'passage_id': 'P001', 'start_s': 0.3, 'end_s': 0.9},
             {'id': 'W3', 'text': 'Not', 'passage_id': 'P002', 'start_s': 1.1, 'end_s': 1.4}, {'id': 'W4', 'text': 'fired.', 'passage_id': 'P002', 'start_s': 1.4, 'end_s': 1.9}]
    (ws / 'out' / 'timing.json').write_text(json.dumps({'words': words, 'audio': {'duration_s': 2.0}}), encoding='utf-8')
    s = voice_record(ws, STAGES['voice'], prior_of(), None)['summary']
    assert s['choice_note'] == 'warmer, clearer on the numbers' and s['name'] == 'Ravi' and len(s['beats']) == 2 and s['prepared_at'] is None or s['prepared_at']


def test_voice_record_without_a_note_has_an_empty_note(vws):
    job = {'id': 'job-n', 'request': {'kind': 'narration', 'voice_id': 'v2', 'name': 'Ravi', 'model_id': 'eleven_v4', 'settings': {}, 'source_script': SCRIPT['content_digest']},
           'result': {'audio_key': 'k', 'sha256': 'ab' * 32, 'bytes': 1, 'timing_key': 't', 'timing_sha256': 'cd' * 32, 'timing_bytes': 1, 'duration_s': 2.0}}
    (vws / 'work' / 'voice-fetched.json').write_text(json.dumps(job), encoding='utf-8')
    words = [{'id': 'W1', 'text': 'x', 'passage_id': 'P001', 'start_s': 0.0, 'end_s': 0.5}, {'id': 'W2', 'text': 'y', 'passage_id': 'P002', 'start_s': 1.0, 'end_s': 1.5}]
    (vws / 'out' / 'timing.json').write_text(json.dumps({'words': words, 'audio': {'duration_s': 2.0}}), encoding='utf-8')
    assert voice_record(vws, STAGES['voice'], prior_of(), None)['summary']['choice_note'] == ''


# ---------- 4.1 the prompt ----------

def test_voice_prompt_is_the_core():
    p = STAGES['voice']['prompt']
    for stale in ('employee', 'browser', 'application', 'save_voice_plan', 'generate_auditions', 'generate_narration', 'choose_voice', 'accept_voice',
                  'effects', 'voice lab', 'Codex', 'package', 'VW10', 'Explore', '/runs/RUN_ID'):
        assert stale not in p, stale
    assert p.startswith('VW-PROCEDURE') and 'same voice as last time' in p and 'vw voice jobs --wait' in p and len(p.split()) < 700
    steps = ' '.join(STAGES['voice']['steps'])
    assert '--wait' in steps and 'last voice' in steps and '--note' in steps and 'save_voice_plan' not in steps   # design/54: the page is the default, the last voice a recommendation
