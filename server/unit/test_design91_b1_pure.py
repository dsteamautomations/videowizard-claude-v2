"""design/91 batch 1: N1 the change list and the pair check, N2 the action budget, N3 the take check."""
import json
from fractions import Fraction
import types

import pytest

from app import image_check as IC, visual_contract as VC, visuals_stage as VS
from app.errors import Problem
from test_visuals_stage_pure import RUN, USER, accepted, g, gap_digest, plan_doc, ref, saved, session, shot, store_with
from test_visuals_pure import GAPS, plan, shot as pshot


def st(progress, landmark='L1'):
    return {'position': {'landmark_id': landmark, 'relation': 'at', 'amount': 1, 'unit': 'pace'}, 'facing': {'landmark_id': landmark, 'edge': 'right', 'camera_side': 'left side'},
            'pose': 'bending', 'holding': [], 'progress': progress}   # design/110 F2, F6


def subject(*beats, landmark='L1'):
    """One acting subject whose beats run one after another, each from the previous one's end state."""
    out = []
    for n, (a, b, min_s) in enumerate(beats):
        out.append({'id': f'B{n + 1}', 'start_frame': a, 'end_frame': b, 'action': 'lays one brick', 'done': 'laid one brick', 'target': 'the top course', 'path': 'along the course',   # design/110 F1
                    'result': 'one more brick on the course', 'start': st(f'{n} laid', landmark), 'end': st(f'{n + 1} laid', landmark), **({'min_s': min_s} if min_s is not None else {})})
    return {'element_id': 'E1', 'role': 'primary', 'screen_position': 'centre', 'behaviour': 'acts', 'start': st('0 laid', landmark), 'end': st(f'{len(beats)} laid', landmark), 'beats': out}


def video(sid, a, b, beats, **extra):
    return {**pshot(sid, a, b, 'video'), 'subjects': [subject(*beats)], 'fixed': ['L1'], **extra}   # design/111 F8: the scene's one landmark


def found(doc):
    return {(w.get('shot_id'), w['kind']) for w in VC.validate_plan(doc, GAPS, Fraction(25))[1]}


def rest(a=200):
    return [pshot('IM1', a, 500, 'image'), pshot('IM2', 500, 1000, 'image')]


# ---------- N1, N2 in the plan ----------

def test_a_video_shot_lists_its_changes_by_the_beat_that_causes_them():
    """N1: a change names a beat of the shot; without a change list the shot warns this release."""
    beats = [(0, 100, 3), (100, 200, 3)]
    assert ('VS1', 'changes_missing') in found(plan([video('VS1', 0, 200, beats)] + rest()))
    ok = video('VS1', 0, 200, beats, changes=[{'what': 'two more bricks on the top course', 'beat_id': 'B1'}])
    assert ('VS1', 'changes_missing') not in found(plan([ok] + rest()))
    with pytest.raises(ValueError, match='not a beat'):
        VC.validate_plan(plan([{**ok, 'changes': [{'what': 'a window opens', 'beat_id': 'B9'}]}] + rest()), GAPS, Fraction(25))
    out, _ = VC.validate_plan(plan([pshot('VS1', 0, 200, 'video')] + rest()), GAPS, Fraction(25))
    assert 'changes' not in out['gaps'][0]['scenes'][0]['shots'][0]   # absent stays absent


def test_three_bricks_at_three_seconds_each_do_not_fit_eight_seconds():
    """N2: a beat shorter than its action, or a subject whose actions need more than the shot, is refused."""
    changes = [{'what': 'three bricks laid', 'beat_id': 'B1'}]
    with pytest.raises(ValueError, match='9.0 s'):
        VC.validate_plan(plan([video('VS1', 0, 200, [(0, 70, 3), (70, 140, 3), (140, 200, 3)], changes=changes)] + rest()), GAPS, Fraction(25))
    with pytest.raises(ValueError, match='B1'):
        VC.validate_plan(plan([video('VS1', 0, 200, [(0, 50, 3), (50, 200, 3)], changes=changes)] + rest()), GAPS, Fraction(25))   # 2 s for a 3 s action
    VC.validate_plan(plan([video('VS1', 0, 200, [(0, 100, 3), (100, 200, 3)], changes=changes)] + rest()), GAPS, Fraction(25))
    assert ('VS1', 'min_s_missing') in found(plan([video('VS1', 0, 200, [(0, 100, None), (100, 200, None)], changes=changes)] + rest()))


# ---------- N1 at prepare-take ----------

class Pair:
    calls = []
    answer = {'differences': [{'what': 'two more bricks on the top course', 'change': 1}, {'what': 'a window shutter opens', 'change': 0}]}

    def __init__(self, key, model, **kw):
        pass

    def generate(self, payload):
        Pair.calls.append(payload)
        return {'body': Pair.answer}


def take_session(changes):
    vs = shot('VS1', 900, 1150, 'video', subjects=[subject((0 + 900, 1000, 3), (1000, 1150, 3), landmark='L2')], **({'changes': changes} if changes else {}))
    doc = plan_doc([shot('IM1', 0, 500, 'image')], [vs])
    gap = doc['gaps'][1]
    sess = session(versions=[{'version': 1, 'file': {'key': 'run-1/visuals/plan-v1.json'}, 'plan_digest': 'd1', 'warnings': []}], current='d1', accepted=accepted(doc),
                   references={'R1': ref('R1', 'approved'), 'R2': ref('R2', 'approved')},
                   bindings={'VS1': {'gap_digest': gap_digest(doc, gap), 'references': {'E1': [{'id': 'R1', 'sha256': 'sha-R1'}]}}})
    store = store_with(sess, doc)
    store.files['run-1/visuals/references/R1.png'] = b'start'
    store.files['run-1/visuals/references/R2.png'] = b'end'
    return store


BODY = {'shot_id': 'VS1', 'motion_prompt': 'he lays two bricks on the top course', 'subject_reconciliation': {'E1': 'the mason'}, 'start_image': 'R1', 'end_image': 'R2',
        'continuity_notes': 'the wall and the light stay'}


def test_a_pair_is_compared_and_a_difference_without_a_cause_is_marked_never_refused(monkeypatch):
    """N1: Gemini lists the differences; one no change explains is marked for the operator; the same pair is not checked twice."""
    monkeypatch.setattr(VS, 'settings', lambda: types.SimpleNamespace(GEMINI_API_KEY=types.SimpleNamespace(get_secret_value=lambda: 'k')))
    monkeypatch.setattr(VS, '_gemini_transport', lambda: Pair)
    Pair.calls = []
    store = take_session([{'what': 'two more bricks on the top course', 'beat_id': 'B1'}])
    out = VS.prepare_take(store, USER, RUN, [], BODY)
    assert any('a window shutter opens' in w and 'no cause' in w for w in out['warnings'])
    prep = saved(store)['preparations']['VS1']
    assert [d['what'] for d in prep['pair_check']['uncaused']] == ['a window shutter opens'] and prep['motion_prompt'] == BODY['motion_prompt']
    record = json.loads(store.files[prep['key']])
    assert record['changes'] == [{'what': 'two more bricks on the top course', 'beat_id': 'B1', 'at_s': [0.0, 4.0]}]
    assert 'two more bricks on the top course' in json.dumps(Pair.calls[0]) and len(Pair.calls) == 1
    VS.prepare_take(store, USER, RUN, [], BODY)
    assert len(Pair.calls) == 1   # the same two pictures and the same list: not checked again


def test_a_pair_check_that_fails_is_recorded_and_the_take_is_still_prepared(monkeypatch):
    monkeypatch.setattr(VS, 'settings', lambda: types.SimpleNamespace(GEMINI_API_KEY=types.SimpleNamespace(get_secret_value=lambda: 'k')))

    class Down(Pair):
        def generate(self, payload):
            raise RuntimeError('timeout')
    monkeypatch.setattr(VS, '_gemini_transport', lambda: Down)
    store = take_session([{'what': 'two more bricks', 'beat_id': 'B1'}])
    out = VS.prepare_take(store, USER, RUN, [], BODY)
    assert out['preparation_id'] and 'timeout' in saved(store)['preparations']['VS1']['pair_check']['error']


def test_a_shot_without_a_change_list_is_prepared_without_a_pair_check_and_warned(monkeypatch):
    Pair.calls = []
    monkeypatch.setattr(VS, '_gemini_transport', lambda: Pair)
    out = VS.prepare_take(take_session(None), USER, RUN, [], BODY)
    assert not Pair.calls and any('change list' in w and 'refused from the next' in w for w in out['warnings'])


# ---------- N3 ----------

class Video:
    uploaded, payload = None, None

    def __init__(self, key, model, **kw):
        pass

    def upload(self, path, mime, sha, existing_receipt=None):
        Video.uploaded = (str(path), mime, sha)
        return {'uri': 'files/abc', 'mimeType': mime}

    def generate(self, payload):
        Video.payload = payload
        return {'body': {'lines': [{'n': 1, 'pass': False, 'seen': 'a third brick appears on the course with no hand on it', 'at_s': 5.2},
                                   {'n': 2, 'pass': True, 'seen': 'the same trowel throughout', 'at_s': None}, {'n': 3, 'pass': True, 'seen': 'no', 'at_s': None},
                                   {'n': 4, 'pass': True, 'seen': 'no', 'at_s': None}, {'n': 5, 'pass': True, 'seen': 'two bricks laid', 'at_s': 9.8}]}}


def test_a_ready_take_is_read_by_gemini_and_an_appearing_object_is_marked_with_its_time(monkeypatch, tmp_path):
    """N3: the five fixed questions, the plan beside them; a failed must line marks the take."""
    monkeypatch.setattr(IC, 'settings', lambda: types.SimpleNamespace(GEMINI_API_KEY=types.SimpleNamespace(get_secret_value=lambda: 'k')))
    video_path = tmp_path / 'output.mp4'
    video_path.write_bytes(b'mp4')
    snapshot = {'motion_prompt': 'he lays two bricks', 'changes': [{'what': 'two more bricks on the top course', 'beat_id': 'B1', 'at_s': [0.0, 4.0]}], 'continuity_notes': 'the wall stays'}
    rec = IC.run_take_check(snapshot, video_path, 'a' * 64, Video)
    assert [l['check'] for l in rec['lines']] == [l['check'] for l in IC.TAKE_LINES] and len(IC.TAKE_LINES) == 6   # design/104 C4 added the frozen-person line
    assert rec['must_failed'][0]['check'] == IC.TAKE_LINES[0]['check'] and rec['must_failed'][0]['at_s'] == 5.2
    assert 'two more bricks on the top course' in json.dumps(Video.payload) and Video.uploaded[1] == 'video/mp4'


def test_a_take_check_that_fails_is_recorded_and_never_raises(monkeypatch, tmp_path):
    monkeypatch.setattr(IC, 'settings', lambda: types.SimpleNamespace(GEMINI_API_KEY=types.SimpleNamespace(get_secret_value=lambda: '')))
    rec = IC.run_take_check({'motion_prompt': 'm'}, tmp_path / 'none.mp4', 'a' * 64, Video)
    assert rec['error'] == 'no Gemini key on the server' and rec['lines'] == []


def test_the_page_shows_the_take_check_and_the_pair_beside_the_take(monkeypatch):
    """N1, N3 on the Takes step."""
    store = take_session([{'what': 'two more bricks', 'beat_id': 'B1'}])
    s = saved(store)
    s['preparations']['VS1'] = {'preparation_id': 'p1', 'motion_prompt': 'he lays two bricks', 'pair_check': {'uncaused': [{'what': 'a window opens'}], 'differences': []}}
    s['take_checks'] = {'j1': {'lines': [], 'must_failed': [{'check': 'appear or vanish', 'at_s': 5.2}]}}
    store = store_with(s, json.loads(store.files['run-1/visuals/plan-v1.json'])['document'])

    class C:
        def execute(self, sql, params=()):
            class R:
                def fetchall(_):
                    return [{'id': 'j1', 'unit': 'VS1', 'status': 'ready', 'result': {}, 'request': {'preparation_id': 'p1'}, 'error': None}] if 'from vw2_jobs' in sql else []

                def fetchone(_):
                    return {'spent': 0, 'n': 0}
            return R()
    monkeypatch.setattr(VS, 'reconcile', lambda conn, run, session: False)
    monkeypatch.setattr(VS, 'visuals_spend', lambda conn, run: {'spent_inr': 0})
    view = VS.page_view(C(), store, RUN, [], 'VW-9')
    sh = next(x for gp in view['gaps'] for x in gp['shots'] if x['shot_id'] == 'VS1')
    assert sh['changes'] == [{'what': 'two more bricks', 'beat_id': 'B1'}] and sh['motion'] == 'he lays two bricks' and sh['pair_check']['uncaused'][0]['what'] == 'a window opens'
    assert sh['takes'][0]['check']['must_failed'][0]['at_s'] == 5.2


def test_the_take_worker_saves_the_check_on_the_session_and_never_raises(monkeypatch, tmp_path):
    """N3: the record lands under take_checks for the job; a broken store leaves the take alone."""
    from app import visual_workers as VW
    from test_visuals_stage_pure import FakeStore
    store = FakeStore({'run-1/visuals/session.json': {'references': {}}, 'run-1/visuals/takes/p1.request.json': {'motion_prompt': 'm'}})
    locks = []

    class Conn:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def execute(self, sql, params=()):
            locks.append(params)
    monkeypatch.setattr(VW, 'storage', lambda: store)
    monkeypatch.setattr(VW, 'connect', lambda: Conn())
    monkeypatch.setattr(IC, 'run_take_check', lambda snapshot, path, sha, factory: {'lines': [], 'must_failed': [{'check': 'appear or vanish', 'at_s': 5.2}], 'seen_plan': snapshot['motion_prompt']})
    job = {'id': 'j1', 'run_id': 'run-1', 'request': {'request_key': 'run-1/visuals/takes/p1.request.json'}}
    VW.check_take(job, {'sha256': 'a' * 64})
    rec = json.loads(store.files['run-1/visuals/session.json'])['take_checks']['j1']
    assert rec['must_failed'][0]['at_s'] == 5.2 and rec['seen_plan'] == 'm' and locks == [('run:run-1',)]
    VW.check_take({**job, 'request': {'request_key': 'missing'}}, {'sha256': 'a' * 64})   # never raises
