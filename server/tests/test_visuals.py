"""Visuals V1–V18 (design/09 §3), providers faked: OpenAI images and the video take provider."""
import base64
import hashlib
import json
import subprocess
from copy import deepcopy
from io import BytesIO

import pytest

from app import visual_workers
from conftest import vw
from test_analysis import FakeTransport, gemini  # noqa: F401
from test_planning import assessment, prepared, run_until_planning, write_plan
from test_voice_media import drain, fake  # noqa: F401


def drain_takes(database):
    """Worker ticks until no take is waiting on a poll lease (leases are expired by hand: the real worker waits 30 s → 5 min)."""
    import psycopg
    for _ in range(10):
        drain()
        with psycopg.connect(database) as c:
            n = c.execute("update vw2_jobs set lease_until = now() - interval '1 second' where provider='video' and status='submitted'").rowcount
        if not n:
            return


# ---------- fakes ----------

def png_bytes(color=(200, 30, 30), size=(64, 64)):
    from PIL import Image
    out = BytesIO()
    Image.new('RGB', size, color).save(out, format='PNG')
    return out.getvalue()


class FakeResponse:
    def __init__(self, status, body):
        self.status_code, self.content = status, json.dumps(body).encode()
        self.text = self.content.decode()


class FakeOpenAI:
    mode = 'ok'   # ok | missing_model
    calls = []

    @classmethod
    def __call__(cls, path, **kw):
        cls.calls.append((path, kw))
        if cls.mode == 'missing_model':
            return FakeResponse(404, {'error': {'message': 'The model does not exist'}})
        color = (30, 30, 200) if path.endswith('/edits') else (200, 30, 30)
        return FakeResponse(200, {'data': [{'b64_json': base64.b64encode(png_bytes(color)).decode(), 'revised_prompt': 'a block'}], 'usage': {'input_tokens': 10, 'output_tokens': 1000}})


def mp4_bytes(seconds, path):
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'lavfi', '-i', f'testsrc=duration={seconds}:size=64x64:rate=25', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', str(path)], check=True)
    return path.read_bytes()


class FakeProvider:
    """Google-shaped: submit returns an in-progress operation; the second poll completes with inline MP4."""
    mode = 'ok'          # ok | crash_after_submit
    submits = 0
    polls = {}
    video = b''

    def __init__(self, name):
        self.name, self.model = name, None

    def build(self, snapshot, store):
        assert store.get(snapshot['start_image']['key'])  # the approved PNG is readable
        return {'model': snapshot['model'], 'input': 'wire'}

    def submit(self, body, identity):
        FakeProvider.submits += 1
        if FakeProvider.mode == 'crash_after_submit':
            raise OSError('worker killed after dispatch')
        return {'id': 'op-' + identity[:8], 'status': 'in_progress'}

    def identity(self, result):
        return result['id']

    def poll(self, identity):
        FakeProvider.polls[identity] = FakeProvider.polls.get(identity, 0) + 1
        if FakeProvider.polls[identity] < 2:
            return {'id': identity, 'status': 'in_progress'}
        return {'id': identity, 'status': 'completed', 'steps': [{'type': 'model_output', 'content': [{'type': 'video', 'mime_type': 'video/mp4', 'data': base64.b64encode(FakeProvider.video).decode()}]}]}

    def state(self, result):
        return 'in_progress' if result['status'] == 'in_progress' else result['status']

    def output(self, result):
        return base64.b64decode(result['steps'][0]['content'][0]['data'])


@pytest.fixture
def providers(monkeypatch, tmp_path):
    FakeOpenAI.mode, FakeOpenAI.calls = 'ok', []
    FakeProvider.mode, FakeProvider.submits, FakeProvider.polls = 'ok', 0, {}
    FakeProvider.video = mp4_bytes(3, tmp_path / 'take.mp4')   # 3.0 s for a ~1 s placement → timing mismatch (V11)
    monkeypatch.setattr(visual_workers, 'openai_client', FakeOpenAI())
    monkeypatch.setattr(visual_workers, 'provider_factory', FakeProvider)
    monkeypatch.setattr(visual_workers, 'SPOOL', tmp_path / 'spool')
    return FakeProvider


# ---------- pipeline up to visuals ----------

def gap_plan(package):
    """S1 covers [0,25) from the clip; two explicit gaps G1 [25,40) and G2 [40,end)."""
    from test_planning import make_plan
    plan = make_plan(package)
    frames = plan['duration_frames']
    assert frames > 45, frames
    s1 = plan['shots'][0]
    s1.update(source_end_frame=25, timeline_end_frame=25)
    passage = s1['passage_ids']
    gap = {'kind': 'gap', 'source_id': None, 'source_start_frame': None, 'source_end_frame': None, 'crop_px': None, 'passage_ids': passage, 'uncertainty': '',
           'visible_talking': 'not_applicable', 'evidence_refs': []}
    plan['shots'] += [{**gap, 'id': 'G1', 'timeline_start_frame': 25, 'timeline_end_frame': 40, 'reason': 'No footage of the kiln.'},
                      {**gap, 'id': 'G2', 'timeline_start_frame': 40, 'timeline_end_frame': frames, 'reason': 'No footage of the finished wall.'}]
    plan['gap_decisions'] = [{'shot_id': 'G1', 'basis': 'no_suitable_evidence', 'reason': 'nothing shows a kiln'}, {'shot_id': 'G2', 'basis': 'no_suitable_evidence', 'reason': 'nothing shows the wall'}]
    return plan


def record_mac_stage(home, ws, stage):
    (ws / 'out' / f'{stage}.json').write_text(json.dumps({'stage': stage, 'done': True}), encoding='utf-8')
    rc, out, err = vw(home, 'output', '--stage', stage, '--file', f'out/{stage}.json', '--quote', f'yes {stage}')
    assert rc == 0, (out, err)


def run_until_visuals(home, database, fake, gemini):
    ws = run_until_planning(home, database, fake, gemini)
    package = prepared(home, ws)
    plan = gap_plan(package)
    write_plan(ws, plan)
    rc, out, err = vw(home, 'planning', 'draft', '--file', 'out/plan.json', '--quote', 'go')
    assert rc == 0, (out, err)
    st = vw(home, 'planning', 'status')[1]
    from app.planning.digest import digest
    review = assessment(package, plan, st['context_digest'], digest({'observations': [], 'frame_results': []}))
    (ws / 'out' / 'assessment.json').write_text(json.dumps(review), encoding='utf-8')
    rc, out, err = vw(home, 'planning', 'finalize', '--file', 'out/assessment.json', '--quote', 'yes')
    assert rc == 0, (out, err)
    assert [g['shot_id'] for g in out['certificate']['gaps']] == ['G1', 'G2']
    for stage in ('edit', 'first_cut'):
        record_mac_stage(home, ws, stage)
    nxt = vw(home, 'next')[1]
    assert nxt['stage'] == 'visuals' and nxt['units_open'] == ['G1', 'G2'], nxt
    return ws, plan['duration_frames']


STATE = {'position': {'landmark_id': 'L1', 'relation': 'on the table'}, 'facing': 'camera', 'pose': 'resting', 'holding': [], 'progress': 'intact'}


def shot(sid, a, b, visual_type, subjects=True):
    s = {'id': sid, 'start_frame': a, 'end_frame': b, 'visual_type': visual_type, 'narration': '', 'purpose': 'show it', 'relation': 'illustration', 'framing': 'medium',
         'camera': 'static', 'focus': 'the block', 'element_ids': ['E1']}
    if subjects:
        s['subjects'] = [{'element_id': 'E1', 'role': 'primary', 'screen_position': 'centre', 'start': STATE, 'end': STATE, 'behaviour': 'holds', 'hold_reason': 'static object'}]
    else:
        s['information_progression'] = 'A still of the block.'
    return s


def scene(sc_id, shots):
    return {'id': sc_id, 'purpose': 'p', 'location_time': 'workshop, day', 'layout': 'table centre', 'landmarks': [{'id': 'L1', 'description': 'the table'}],
            'boundary_continuity': 'none', 'shots': shots}


def visual_plan(frames):
    return {'foundation': {'treatment': 'documentary realism', 'appearance': 'warm daylight'},
            'elements': [{'id': 'E1', 'name': 'Earth block', 'kind': 'object', 'identity': 'representative', 'requirements': 'pressed earth block'}],
            'gaps': [{'gap_id': 'G1', 'intent': 'kiln', 'treatment_fit': 'fits', 'scenes': [scene('SC1', [shot('VS1', 25, 40, 'video')])]},
                     {'gap_id': 'G2', 'intent': 'wall', 'treatment_fit': 'fits', 'scenes': [scene('SC2', [shot('VS2', 40, frames, 'image', subjects=False)])]}]}


def vplan(ws, plan, name='out/visual-plan.json'):
    (ws / name).write_text(json.dumps(plan), encoding='utf-8')
    return name


# ---------- tests ----------

def test_v1_v2_v3_v4_v5_v6_v7_v8_v9_v11_v12_v14_v15_v16_v18_end_to_end(home, database, fake, gemini, providers):
    ws, frames = run_until_visuals(home, database, fake, gemini)
    rc, out, err = vw(home, 'visuals', 'prepare')
    assert rc == 0 and out['gaps'] == ['G1', 'G2'], err
    package = json.loads((ws / 'work' / 'visuals-package.json').read_text(encoding='utf-8'))
    assert package['prompt'] and package['generator_catalog']['default']['provider'] == 'google' and package['world_evidence']
    good = visual_plan(frames)
    # V1 shots do not tile the gap
    bad = deepcopy(good); bad['gaps'][0]['scenes'][0]['shots'][0]['end_frame'] = 39
    rc, out, _ = vw(home, 'visuals', 'check', '--file', vplan(ws, bad))
    assert out['status'] == 'rejected' and 'exact approved working gap duration' in out['error']
    # V2 beat chain broken
    bad = deepcopy(good)
    subj = bad['gaps'][0]['scenes'][0]['shots'][0]['subjects'][0]
    moved = {**STATE, 'pose': 'tilted'}
    subj.update(behaviour='acts', hold_reason='', end=moved, beats=[{'id': 'B1', 'start_frame': 25, 'end_frame': 30, 'action': 'tilt', 'target': 'edge', 'path': 'up', 'result': 'tilted', 'start': moved, 'end': moved}])
    rc, out, _ = vw(home, 'visuals', 'check', '--file', vplan(ws, bad))
    assert out['status'] == 'rejected' and 'Beat starting state' in out['error']
    # design/45 10.2: the check counts the routes and warns on the image shot
    rc, out, _ = vw(home, 'visuals', 'check', '--file', vplan(ws, good))
    assert out['status'] == 'valid' and out['routes']['video'] == 1 and out['routes']['still_or_file'] == 1 and any(w.get('kind') == 'route' and w['shot_id'] == 'VS2' for w in out['warnings'])
    # propose + accept both gaps (design/45 10.4: all)
    rc, out, err = vw(home, 'visuals', 'propose', '--file', vplan(ws, good))
    assert rc == 0 and out['version'] == 1 and out['routes']['video'] == 1, err
    rc, out, err = vw(home, 'visuals', 'accept', '--gaps', 'all', '--quote', 'yes both gaps')
    assert rc == 0 and out['accepted'] == ['G1', 'G2'], err
    # V3 foundation text edit keeps acceptance? No: foundation is part of the gap digest. An unrelated element edit keeps it.
    v2 = deepcopy(good); v2['elements'].append({'id': 'E9', 'name': 'Spare', 'kind': 'object', 'identity': 'representative', 'requirements': 'unused'})
    assert vw(home, 'visuals', 'propose', '--file', vplan(ws, v2))[1]['version'] == 2
    st = vw(home, 'visuals', 'status')[1]
    assert [g['accepted'] for g in st['gaps']] == [True, True]
    # V4 change G1's scene → G1 unaccepted, G2 untouched
    v3 = deepcopy(v2); v3['gaps'][0]['scenes'][0]['layout'] = 'table left'
    assert vw(home, 'visuals', 'propose', '--file', vplan(ws, v3))[1]['version'] == 3
    st = vw(home, 'visuals', 'status')[1]
    assert [g['accepted'] for g in st['gaps']] == [False, True]
    assert vw(home, 'visuals', 'accept', '--gaps', 'G1', '--quote', 'yes G1 again')[0] == 0
    # V16 frame reference from the clip at 0.5 s
    media = vw(home, 'view', '--stage', 'media')[1]['outputs'][0]['summary']['clips'][0]
    rc, out, err = vw(home, 'visuals', 'frame', '--element', 'E1', '--clip', media['id'], '--at', '0.5')
    assert rc == 0 and out['status'] == 'candidate' and out['sha256'], err
    frame_ref = out['id']
    rc, out, err = vw(home, 'visuals', 'fetch', '--ref', frame_ref)
    assert rc == 0 and hashlib.sha256((ws / out['path']).read_bytes()).hexdigest() == out['sha256']
    # V17 web reference without the selection reply
    (ws / 'in' / 'web.png').write_bytes(png_bytes((10, 200, 10)))
    rc, out, _ = vw(home, 'visuals', 'web', '--element', 'E1', '--file', 'in/web.png', '--url', 'https://example.org/block.png')
    assert rc == 2 and 'selection reply' in out['message']
    # V5 generated image (faked OpenAI)
    rc, out, err = vw(home, 'visuals', 'image', '--element', 'E1', '--kind', 'keyframe', '--prompt', 'a pressed earth block on a table')
    assert rc == 0 and out['model'] == 'gpt-image-2.5-flare' and out['op'] == 'generate', err
    gen_ref = out['reference_id']
    drain()
    st = vw(home, 'visuals', 'status')[1]
    gen = next(r for r in st['references'] if r['id'] == gen_ref)
    assert gen['status'] == 'candidate' and gen['sha256'] == hashlib.sha256(png_bytes((200, 30, 30))).hexdigest()
    # V7 wrong hash → 409; then approve both
    rc, out, _ = vw(home, 'visuals', 'approve', '--ref', gen_ref, '--sha', '0' * 64, '--quote', 'looks right')
    assert rc == 2 and out['code'] == 'REFERENCE_MISMATCH'
    assert vw(home, 'visuals', 'approve', '--ref', gen_ref, '--sha', gen['sha256'], '--quote', 'looks right')[0] == 0
    frame_sha = next(r for r in st['references'] if r['id'] == frame_ref)['sha256']
    assert vw(home, 'visuals', 'approve', '--ref', frame_ref, '--sha', frame_sha, '--quote', 'that frame')[0] == 0
    # V6 edit with two approved parents
    rc, out, err = vw(home, 'visuals', 'image', '--element', 'E1', '--kind', 'sheet', '--prompt', 'turnaround sheet', '--parents', f'{gen_ref},{frame_ref}')
    assert rc == 0 and out['model'] == 'gpt-image-2.5-sunburst' and out['op'] == 'edit', err
    drain()
    path, kw = FakeOpenAI.calls[-1]
    assert path == '/images/edits' and len(kw['files']) == 2
    sheet = next(r for r in vw(home, 'visuals', 'status')[1]['references'] if r['id'] == out['reference_id'])
    assert sheet['status'] == 'candidate'
    # V8 bind with an element lacking references; design/45 10.4: no quote needed
    rc, out, _ = vw(home, 'visuals', 'bind', '--shot', 'VS1', '--refs')
    assert rc == 2 and 'E1' in out['message']
    rc, out, err = vw(home, 'visuals', 'bind', '--shot', 'VS1', '--refs', f'E1={gen_ref},{frame_ref}')
    assert rc == 0 and out['elements'] == ['E1'], err
    rc, out, err = vw(home, 'visuals', 'packet', '--shot', 'VS1')
    assert rc == 0 and len(out['preparation']['references']) == 2 and out['placement']['fps'] == '25'
    # V9 subject key not in the shot
    rc, out, _ = vw(home, 'visuals', 'prepare-take', '--shot', 'VS1', '--start', gen_ref, '--motion', 'slow push in', '--subject-rec', 'E7=the block')
    assert rc == 2 and 'Reconcile every subject' in out['message']
    rc, out, err = vw(home, 'visuals', 'prepare-take', '--shot', 'VS1', '--start', gen_ref, '--motion', 'slow push in', '--subject-rec', 'E1=the block')
    assert rc == 0 and out['duration_seconds'] == 3 and abs(out['exact_seconds'] - 0.6) < 1e-9, err
    # take (design/45 10.5: a list); V12 second take while open
    rc, out, err = vw(home, 'visuals', 'take', '--shots', 'VS1')
    assert rc == 0 and out['queued'] == ['VS1'], err
    job = next(j['id'] for j in vw(home, 'visuals', 'status')[1]['jobs'] if j['unit'] == 'VS1' and j['provider'] == 'video')
    rc, out, _ = vw(home, 'visuals', 'take', '--shots', 'VS1')
    assert rc == 2 and 'still open' in out['refused']['VS1']
    rc, out, _ = vw(home, 'visuals', 'take', '--shots', 'all')
    assert rc == 0 and out['queued'] == []   # VS1 is open, VS2 is an image shot
    drain_takes(database)   # submit → in_progress → completed (two polls)
    assert FakeProvider.submits == 1
    rc, out, err = vw(home, 'visuals', 'fetch', '--job', job)
    # design/45 10.6: a 3.0 s take for a 0.6 s placement matches (assembly trims); the shortfall is zero
    assert rc == 0 and out['evidence']['timing_matches_placement'] is True and out['evidence']['shortfall_seconds'] == 0 and abs(out['evidence']['duration_seconds'] - 3.0) < 0.1, (out, err)
    # design/45 10.4: notes make the accepted review and the selection one call
    rc, out, err = vw(home, 'visuals', 'select', '--job', job, '--notes', 'block in place, no text', '--quote', 'select this take')
    assert rc == 0 and out['review_id'], (out, err)
    st = vw(home, 'visuals', 'status')[1]
    assert any(s['shot_id'] == 'VS1' and s['selected'] for g in st['gaps'] for s in g['shots'])
    # design/45 10.4: record all records the gaps that are done and skips the rest with the reason
    rc, out, err = vw(home, 'visuals', 'record', '--gaps', 'all', '--quote', 'done so far')
    assert rc == 0 and out['recorded'] == ['G1'] and 'VS2' in out['skipped']['G2'], (out, err)
    rc, out, _ = vw(home, 'visuals', 'record', '--gap', 'G2', '--quote', 'G2 done')
    assert rc == 2 and 'VS2' in out['message']
    # design/45 10.3: an approved reference fills the still shot; V14: a local still asset replaces it
    rc, out, err = vw(home, 'visuals', 'still', '--shot', 'VS2', '--ref', gen_ref, '--quote', 'use that picture')
    assert rc == 0 and out['kind'] == 'still' and out['sha256'] == gen['sha256'], (out, err)
    rc, out, _ = vw(home, 'visuals', 'still', '--shot', 'VS1', '--ref', gen_ref, '--quote', 'x')
    assert rc == 2 and 'video shot' in out['message']
    (ws / 'out' / 'wall.png').write_bytes(png_bytes((90, 90, 90), (1920, 1080)))
    assert vw(home, 'upload', '--stage', 'visuals', '--file', 'out/wall.png')[0] == 0
    rc, out, err = vw(home, 'visuals', 'asset', '--shot', 'VS2', '--file', 'out/wall.png', '--kind', 'still', '--quote', 'use the wall still')
    assert rc == 0 and out['placement'] == {'start_frame': 40, 'end_frame': frames}, err
    rc, out, err = vw(home, 'visuals', 'record', '--gaps', 'all', '--quote', 'G2 done')
    assert rc == 0 and out['recorded'] == ['G2'] and out['skipped'] == {}, err
    # V15 stage complete → assembly
    assert vw(home, 'next')[1]['stage'] == 'assembly'
    outs = vw(home, 'view', '--stage', 'visuals')[1]['outputs']
    g1 = next(o for o in outs if o['unit'] == 'G1')
    assert g1['summary']['shots'][0]['source'] == 'take' and g1['summary']['take_cost'][0]['seconds'] == 3 and len(g1['summary']['image_cost']) == 2
    assert {f['name'] for f in g1['files']} >= {'VS1.mp4', f'ref-{gen_ref[:8]}.png', f'ref-{frame_ref[:8]}.png'}



def test_v18_model_unavailable_and_supplied_reference(home, database, fake, gemini, providers):
    ws, frames = run_until_visuals(home, database, fake, gemini)
    assert vw(home, 'visuals', 'prepare')[0] == 0
    assert vw(home, 'visuals', 'propose', '--file', vplan(ws, visual_plan(frames)))[0] == 0
    assert vw(home, 'visuals', 'accept', '--gaps', 'G1', 'G2', '--quote', 'yes')[0] == 0
    FakeOpenAI.mode = 'missing_model'
    rc, out, _ = vw(home, 'visuals', 'image', '--element', 'E1', '--kind', 'isolated', '--prompt', 'block')
    assert rc == 0
    drain()
    st = vw(home, 'visuals', 'status')[1]
    ref = next(r for r in st['references'] if r['id'] == out['reference_id'])
    job = next(j for j in st['jobs'] if j['id'] == out['job_id'])
    assert ref['status'] == 'failed' and job['status'] == 'rejected' and 'unavailable' in job['error']
    (ws / 'in' / 'photo.png').write_bytes(png_bytes((1, 2, 3)))
    rc, out, err = vw(home, 'visuals', 'supply', '--element', 'E1', '--file', 'in/photo.png')
    assert rc == 0 and out['status'] == 'candidate', err


def test_v10_worker_killed_after_submit_then_recover(home, database, fake, gemini, providers):
    ws, frames = run_until_visuals(home, database, fake, gemini)
    assert vw(home, 'visuals', 'prepare')[0] == 0
    assert vw(home, 'visuals', 'propose', '--file', vplan(ws, visual_plan(frames)))[0] == 0
    assert vw(home, 'visuals', 'accept', '--gaps', 'G1', '--quote', 'yes')[0] == 0
    (ws / 'in' / 'photo.png').write_bytes(png_bytes((1, 2, 3)))
    ref = vw(home, 'visuals', 'supply', '--element', 'E1', '--file', 'in/photo.png')[1]
    assert vw(home, 'visuals', 'approve', '--ref', ref['id'], '--sha', ref['sha256'], '--quote', 'ok')[0] == 0
    assert vw(home, 'visuals', 'bind', '--shot', 'VS1', '--refs', f"E1={ref['id']}", '--quote', 'bind')[0] == 0
    assert vw(home, 'visuals', 'prepare-take', '--shot', 'VS1', '--start', ref['id'], '--motion', 'hold', '--subject-rec', 'E1=block')[0] == 0
    job = vw(home, 'visuals', 'take', '--shot', 'VS1')[1]['job_id']
    FakeProvider.mode = 'crash_after_submit'
    drain()
    st = next(j for j in vw(home, 'visuals', 'status')[1]['jobs'] if j['id'] == job)
    assert st['status'] == 'submission_unknown' and FakeProvider.submits == 1
    FakeProvider.mode = 'ok'
    drain()   # a lease-less submission_unknown job is never picked up again
    assert FakeProvider.submits == 1
    assert vw(home, 'visuals', 'take', '--shot', 'VS1')[1]['code'] == 'JOB_OPEN'


def test_v13_selection_goes_stale_when_preparation_changes(home, database, fake, gemini, providers):
    ws, frames = run_until_visuals(home, database, fake, gemini)
    assert vw(home, 'visuals', 'prepare')[0] == 0
    assert vw(home, 'visuals', 'propose', '--file', vplan(ws, visual_plan(frames)))[0] == 0
    assert vw(home, 'visuals', 'accept', '--gaps', 'G1', '--quote', 'yes')[0] == 0
    (ws / 'in' / 'photo.png').write_bytes(png_bytes((1, 2, 3)))
    ref = vw(home, 'visuals', 'supply', '--element', 'E1', '--file', 'in/photo.png')[1]
    assert vw(home, 'visuals', 'approve', '--ref', ref['id'], '--sha', ref['sha256'], '--quote', 'ok')[0] == 0
    assert vw(home, 'visuals', 'bind', '--shot', 'VS1', '--refs', f"E1={ref['id']}", '--quote', 'bind')[0] == 0
    assert vw(home, 'visuals', 'prepare-take', '--shot', 'VS1', '--start', ref['id'], '--motion', 'hold', '--subject-rec', 'E1=block')[0] == 0
    job = vw(home, 'visuals', 'take', '--shot', 'VS1')[1]['job_id']
    drain_takes(database)
    assert vw(home, 'visuals', 'review', '--job', job, '--decision', 'accepted', '--notes', 'ok', '--timing', 'trim', '--quote', 'yes')[0] == 0
    # generator change after the take → context differs → select refused
    assert vw(home, 'visuals', 'generator', '--shot', 'VS1', '--provider', 'higgsfield', '--model', 'kling-video/v3.0/std/image-to-video')[0] == 0
    rc, out, _ = vw(home, 'visuals', 'select', '--job', job, '--quote', 'select')
    assert rc == 2 and 'changed since this take was prepared' in out['message']
    assert vw(home, 'visuals', 'generator', '--shot', 'VS1', '--provider', 'google', '--model', 'gemini-omni-1.1-flash')[0] == 0
    assert vw(home, 'visuals', 'select', '--job', job, '--quote', 'select')[0] == 0


def test_no_gaps_means_no_visuals_work(home, database, fake, gemini):
    """planning with zero gaps declares units=[] → visuals is satisfied, next after first_cut is assembly."""
    from test_planning import make_plan
    ws = run_until_planning(home, database, fake, gemini)
    package = prepared(home, ws)
    plan = make_plan(package)
    write_plan(ws, plan)
    assert vw(home, 'planning', 'draft', '--file', 'out/plan.json', '--quote', 'go')[0] == 0
    st = vw(home, 'planning', 'status')[1]
    from app.planning.digest import digest
    (ws / 'out' / 'assessment.json').write_text(json.dumps(assessment(package, plan, st['context_digest'], digest({'observations': [], 'frame_results': []}))), encoding='utf-8')
    assert vw(home, 'planning', 'finalize', '--file', 'out/assessment.json', '--quote', 'yes')[0] == 0
    for stage in ('edit', 'first_cut'):
        record_mac_stage(home, ws, stage)
    assert vw(home, 'next')[1]['stage'] == 'assembly'
