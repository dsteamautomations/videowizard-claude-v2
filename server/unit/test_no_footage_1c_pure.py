"""SK, 23 Nov 2026 (no-footage release 1c): the first cut of a film with no camera footage of its own.
Such a film has no clip to study, so the library question is not asked and "No analysed clips" is not a refusal. When its scenes are approved
and the client's library has nothing it can use, the server writes the cut itself: every scene is one stretch for the visuals stage, and the
options, the master and the first cut are recorded with the operator's words on the scenes; nothing is rendered and nothing is watched. When
the library has pieces, the cut goes the usual way with those pieces. A film with footage behaves as before."""
import json
import uuid
from pathlib import Path

import pytest

from app import brandlib, core, film, jobs, runlog
from app.errors import Problem
from app.stage2 import stage as S2

SERVER = Path(__file__).resolve().parents[1]
STAGES = json.loads((SERVER / 'procedures' / 'v3.json').read_text(encoding='utf-8'))['stages']
SPOKEN = 'The brick is pressed. It is cured for a week. Then it goes to the site.'
SCENES = {'scenes': [{'first_word_id': 'W1', 'title': 'Pressing'}, {'first_word_id': 'W5', 'title': 'Curing'}, {'first_word_id': 'W11', 'title': 'To the site'}], 'pauses': []}
USER = {'id': 'u1', 'name': 'Asha'}


class Store:
    def __init__(self):
        self.f = {}

    def get(self, k):
        if k not in self.f:
            raise Problem(404, 'FILE_MISSING', k)
        return self.f[k]

    def exists(self, k):
        return k in self.f

    def put(self, k, data, mime=None):
        self.f[k] = data
        return {'key': k}

    def size(self, k):
        return len(self.f[k])


class Conn:
    def __init__(self):
        self.jobs = 0

    def execute(self, sql, params=()):
        conn = self

        class R:
            def fetchone(self):
                if 'insert into vw2_jobs' in sql:
                    conn.jobs += 1
                    return {'id': f'job-{conn.jobs}'}
                return None

            def fetchall(self):
                return []
        return R()


@pytest.fixture
def world(monkeypatch):
    store, outputs, conn = Store(), [], Conn()

    def out_(stage, summary=None, files=None, unit=None, quote=None):
        return {'id': str(uuid.uuid4()), 'stage': stage, 'unit': unit, 'summary': summary or {}, 'files': files or [], 'accepted_quote': quote}

    def putj(k, v):
        store.put(k, json.dumps(v).encode())
        return {'name': k.rsplit('/', 1)[1], 'key': k, 'sha256': 'x', 'bytes': 1}

    words, t = [], 0.0
    for i, w in enumerate(SPOKEN.split()):
        words.append({'id': f'W{i + 1}', 'text': w, 'start_s': round(t, 2), 'end_s': round(t + 0.3, 2), 'passage_id': 'P001'})
        t += 0.4
    dur = round(t + 0.2, 2)
    store.put('run-1/voice/narration.mp3', b'mp3')
    outputs += [out_('intake', {'title': 'T'}), out_('brief', {'production': {'process_stages': []}}, [putj('run-1/brief/brief.json', {})]),
                out_('script', {}, [putj('run-1/script/script.json', {'spoken_text': SPOKEN, 'beats': [{'beat_id': 'BEAT_01', 'passage_id': 'P001'}]})]),
                out_('voice', {'duration_s': dur}, [putj('run-1/voice/timing.json', {'words': words, 'audio': {'duration_s': dur}}),
                                                    {'name': 'narration.mp3', 'key': 'run-1/voice/narration.mp3', 'sha256': 'x', 'bytes': 3}]),
                out_('media', {'clips': [], 'units': {'analysis': []}, 'footage': 'none', 'camera_audio': 'excluded'}, [{'name': 'media.json'}])]
    run = {'id': 'run-1', 'code': 'VW-T', 'procedure_version': '3', 'status': 'open', 'active_machine': None, 'client_id': 'c1', 'client': 'C', 'image_provider': 'openai',
           'film': {'category': {'value': 'documentary-explainer'}, 'footage': {'value': 'none'}, 'shape': film.check('shape', 'horizontal', 'horizontal', 25)}}

    def fake_output(conn_, user, run_, body):
        nxt = core.compute_next(run_, STAGES, outputs, {})
        assert nxt['stage'] == body['stage'], (nxt['stage'], body['stage'])   # as core.output: only the next stage is recorded
        st = next(s for s in STAGES if s['name'] == body['stage'])
        assert not st.get('needs_acceptance') or str(body.get('accepted_quote') or '').strip()
        assert not st.get('requires_files') or body.get('files')
        row = out_(body['stage'], body.get('summary'), body.get('files'), body.get('unit'), body.get('accepted_quote'))
        outputs.append(row)
        return row

    monkeypatch.setattr(core, 'client_rules', lambda conn_, cid: [])
    monkeypatch.setattr(core, 'effective_rules', lambda conn_, run_, outs: {'learned': []})
    monkeypatch.setattr(core, 'stage_table', lambda v: STAGES)
    monkeypatch.setattr(core, 'output', fake_output)
    monkeypatch.setattr(core, '_bump_attempt', lambda *a, **k: 1, raising=False)
    monkeypatch.setattr(jobs, 'record_file', lambda *a, **k: None)
    monkeypatch.setattr(runlog, 'write', lambda *a, **k: None)
    return {'store': store, 'outputs': outputs, 'conn': conn, 'run': run}


def scenes(w, quote='yes, these scenes'):
    return S2.set_scenes(w['conn'], w['store'], USER, w['run'], w['outputs'], json.loads(json.dumps(SCENES)), quote)


def test_the_cut_waits_for_the_scenes_and_for_nothing_else(world):
    with pytest.raises(Problem) as e:   # not the library question, not "No analysed clips"
        S2.prepare(world['conn'], world['store'], USER, world['run'], world['outputs'])
    assert e.value.code == 'SCENES_NOT_APPROVED' and len(e.value.extra['sentences']) == 3


def test_the_server_writes_the_cut_when_the_scenes_are_approved(world):
    out = scenes(world)
    by = {o['stage']: o for o in world['outputs']}
    assert {'options', 'master', 'first_cut'} <= set(by) and world['conn'].jobs == 0   # nothing was rendered
    assert out['first_cut'] == 'written' and out['gaps'] == ['BEAT_01-B1', 'BEAT_02-B1', 'BEAT_03-B1'] and 'visuals' in out['next']
    assert all(by[s]['accepted_quote'] == 'yes, these scenes' for s in ('options', 'master', 'first_cut'))
    nxt = core.compute_next(world['run'], STAGES, world['outputs'], {})
    assert nxt['stage'] == 'visuals' and nxt['units_open'] == ['BEAT_01-B1', 'BEAT_02-B1', 'BEAT_03-B1']


def test_what_the_later_steps_read_is_there(world):
    scenes(world)
    by = {o['stage']: o for o in world['outputs']}
    m = by['master']['summary']
    plan, _ = S2._file(world['store'], by['master'], f"master-v{m['version']}.json")   # the assembly and the package open it by this name
    assert plan['duration_frames'] == m['duration_frames'] == 165 and [e['kind'] for e in plan['events']] == ['gap'] * 3
    assert [(g['shot_id'], g['start_frame'], g['end_frame']) for g in m['gaps']] == [('BEAT_01-B1', 0, 40), ('BEAT_02-B1', 40, 100), ('BEAT_03-B1', 100, 165)]
    assert m['units'] == {'visuals': ['BEAT_01-B1', 'BEAT_02-B1', 'BEAT_03-B1']} and m['fps'] == '25' and m['resolution'] == [1920, 1080] and m['plan_digest']
    assert m['film'] is None and m['written_by'] == 'server' and by['options']['summary']['approved_by']['how'] == 'no_footage'
    f = by['first_cut']['summary']
    assert f['gaps'] == m['gaps'] and f['duration_frames'] == 165 and f['movie_sha256'] is None and by['first_cut']['files']
    assert m['gaps'][0]['reason'] == 'Pressing | narration: The brick is pressed.'
    pk = S2._package(world['store'], S2.session_of(world['store'], world['run']))
    assert len(pk['narration']['words']) == 16 and len(pk['narration']['sentences']) == 3 and pk['sub_clips'] == []   # the visuals stage times its gaps from these
    assert pk['policy'] == {'allow_speaker_audio': False, 'show_speaker_video': False}


def test_library_pieces_send_the_cut_the_usual_way(world, monkeypatch):
    monkeypatch.setattr(brandlib, 'library_round', lambda *a, **k: {'candidates': [{'sub_clip_id': 'lib:S1', 'clip_name': 'gate.mp4'}], 'rule': 'r', 'note': ''})
    out = scenes(world)
    assert 'first_cut' not in out and out['library'] == {'pieces': 1, 'clips': ['gate.mp4']} and '`vw options library`' in out['next']
    assert not [o for o in world['outputs'] if o['stage'] in ('options', 'master', 'first_cut')]
    with pytest.raises(Problem) as e:   # a cut with a real clip in it is watched before it is approved
        S2.record_master(world['conn'], world['store'], USER, world['run'], 'approved')
    assert e.value.code in ('NOT_ALLOWED', 'STAGE2_CONTRACT')


def test_a_film_with_footage_and_no_studied_clip_is_refused_as_before(world):
    run = {**world['run'], 'film': {k: v for k, v in world['run']['film'].items() if k != 'footage'}}
    with pytest.raises(Problem) as e:
        S2.prepare(world['conn'], world['store'], USER, run, world['outputs'])
    assert e.value.code == 'LIBRARY_NOT_ASKED'
    run['film']['library'] = {'asked': True, 'generic': []}
    with pytest.raises(Problem) as e:
        S2.prepare(world['conn'], world['store'], USER, run, world['outputs'])
    assert 'No analysed clips' in e.value.message
    with pytest.raises(Problem) as e:   # the film-less record is the server's own, for a film with no footage only
        S2.record_master(world['conn'], world['store'], USER, run, 'yes', film_needed=False)
    assert e.value.code == 'NOT_ALLOWED'


@pytest.mark.parametrize('name', ['options', 'master', 'first_cut'])
def test_the_instructions_of_a_film_with_no_footage_name_no_step_it_cannot_take(name):
    st = core.for_footage(next(s for s in STAGES if s['name'] == name), 'none')
    text = json.dumps(st['steps'], ensure_ascii=False).lower().replace('no camera footage', '')   # the steps are the flow; the options prompt keeps the rules of a cut, which hold for a library piece
    for w in ('second-look', 'vw-scene-review', 'exact real match', 'vw options inspect', 'find footage', 'vw options coverage', 'camera', 'b-roll', 'pieces-<scene>'):
        assert w not in text, (name, w)
    if name == 'options':
        steps = ' '.join(st['steps'])
        assert 'the server writes the first cut' in steps and '`vw options library`' in steps and '`vw options scenes' in steps
        assert st['prompt'].splitlines()[1].startswith('This film has no camera footage of its own.')   # said before any rule about clips
