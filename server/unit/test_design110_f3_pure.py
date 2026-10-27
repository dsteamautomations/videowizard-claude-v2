"""design/110 F3 (+F44): the start picture shows the action not yet done. The packet carries one start_targets line per acting subject; every start
keyframe of a video shot gets the must line "not yet done"; at approval the server reads that line (failed or undecided: refused, and the operator is
asked, rule 0 fork 5; absent: the model is asked once); a take is never prepared from a start whose line failed."""
import json
import types

import pytest

from app import image_check as IC, visuals_stage as VS
from app.errors import Problem
from test_design101_pure import take_store
from test_design106_pure import approvable, revise_start, start_store
from test_visuals_stage_pure import RUN, USER, FakeConn, g, saved


@pytest.fixture(autouse=True)
def cheap(monkeypatch):
    monkeypatch.setattr(VS, 'prices', lambda: {'image_inr': 4.0, 'video_inr_per_s': 8.9})


def put(store, s):
    store.files['run-1/visuals/session.json'] = json.dumps(s).encode('utf-8')


def with_line(store, rid, passed):
    s = saved(store)
    s['references'][rid]['check'] = {'lines': [{'check': 'not yet done', 'weight': 'must', 'pass': passed, 'seen': 'two bricks, the third in hand' if passed else 'the third brick is already set'}],
                                     'must_failed': [] if passed else [{'check': 'not yet done', 'weight': 'must', 'pass': False, 'seen': 'the third brick is already set'}], 'model': 'm'}
    put(store, s)


# ---------- the packet and the must line ----------

def test_the_packet_carries_a_start_line_per_acting_subject_and_the_digest_does_not_move():
    store, doc = take_store()
    pk = VS.packet(store, RUN, [], 'VS1')
    st = pk['preparation']['context']['start_targets']
    assert st['lines'] == ['E1: about to lays one brick; not yet done: one more brick on the course; still as at the start: 0 laid.'] and 'word for word' in st['instruction'] and 'before the action' in st['instruction']
    assert VS.start_targets(doc['gaps'][1]['scenes'][0], doc['gaps'][1]['scenes'][0]['shots'][0]) == st['lines']
    assert VS.not_yet_lines(doc['gaps'][1]['scenes'][0]['shots'][0]) == [{'check': 'not yet done', 'weight': 'must',
                                                                            'pass_when': 'the picture still shows the start state (E1: 0 laid) and one more brick on the course has NOT happened yet; '
                                                                                         'this line FAILS when one more brick on the course is already in the picture, even with a hand still on it'}]
    assert VS.not_yet_lines({'subjects': [], 'visual_type': 'video'}) == [] and VS.not_yet_lines({'subjects': [{'behaviour': 'holds', 'beats': []}], 'visual_type': 'video'}) == []
    assert 'start_targets' not in pk['preparation'] and 'start_targets' in pk['preparation']['context']   # in the context, which the digest leaves out: no take goes stale


def test_every_start_keyframe_of_a_video_shot_carries_the_must_line_and_an_end_does_not():
    store = start_store()
    rid = revise_start(store, role='start')['reference_id']
    lines = saved(store)['references'][rid]['server_checklist']
    assert [l for l in lines if l['check'] == 'not yet done'] == VS.not_yet_lines(json.loads(store.files['run-1/visuals/plan-v1.json'])['document']['gaps'][1]['scenes'][0]['shots'][0])
    assert 'not yet done' in [l['check'] for l in IC.lines_of(saved(store)['references'][rid])]
    s = saved(approvable(store, rid))
    s['references'][rid]['status'] = 'approved'
    put(store, s)
    end = VS.generate_image(FakeConn([]), store, USER, RUN, [], {'request_id': 'r-end', 'element_id': 'E1', 'name': 'keyframe-end-VS1', 'kind': 'keyframe', 'shot_id': 'VS1', 'subject': 'the labourer',
                                                                'prompt': 'Image 1 is the start; the labourer at the edge.', 'parents': [rid], 'role': 'end'})
    assert 'not yet done' not in [l['check'] for l in saved(store)['references'][end['reference_id']].get('server_checklist') or []]


# ---------- approval reads the stored line ----------

def test_a_start_whose_line_failed_is_refused_at_approval_and_the_operator_is_asked():
    store = start_store()
    rid = revise_start(store, role='start')['reference_id']
    approvable(store, rid)
    with_line(store, rid, False)
    with pytest.raises(Problem, match=f"{rid} already shows the result"):
        g(lambda: VS.approve_reference(store, USER, RUN, [], rid, 'a' * 64, '', FakeConn([])))
    s = saved(store)
    q = s['questions'][rid]
    assert q['fork'] == 'not_yet' and q['by'] == 'server' and q['choices'] == ['make a new start (4 INR)', 'approve anyway'] and s['references'][rid]['status'] == 'candidate'
    VS.answer(store, USER, RUN, [], rid, 'approve anyway')
    assert saved(store)['references'][rid]['not_yet_ok'] is True
    s = saved(store)
    s['references']['K1']['status'] = 'rejected'   # no second start for the slot (fork 3 is rule 0's)
    put(store, s)
    row = VS.approve_reference(store, USER, RUN, [], rid, 'a' * 64, '', FakeConn([]))
    assert row['status'] == 'approved' and row.get('end_reference_id')


def test_an_undecided_line_is_a_question_and_a_passed_line_approves(monkeypatch):
    store = start_store()
    rid = revise_start(store, role='start')['reference_id']
    approvable(store, rid)
    with_line(store, rid, None)
    with pytest.raises(Problem, match='could not be decided'):
        g(lambda: VS.approve_reference(store, USER, RUN, [], rid, 'a' * 64, '', FakeConn([])))
    assert saved(store)['questions'][rid]['fork'] == 'not_yet'
    store = start_store()
    rid = revise_start(store, role='start')['reference_id']
    approvable(store, rid)
    with_line(store, rid, True)
    s = saved(store)
    s['references']['K1']['status'] = 'rejected'
    put(store, s)
    assert VS.approve_reference(store, USER, RUN, [], rid, 'a' * 64, '', FakeConn([]))['status'] == 'approved'


def test_a_start_without_the_line_is_asked_the_line_once_at_approval(monkeypatch):
    store = start_store()
    rid = revise_start(store, role='start')['reference_id']
    approvable(store, rid)
    s = saved(store)
    s['references'][rid]['check'] = {'lines': [{'check': 'scale', 'weight': 'must', 'pass': True, 'seen': 'ok'}], 'must_failed': [], 'model': 'm'}   # a picture checked before this release
    s['references']['K1']['status'] = 'rejected'
    put(store, s)
    asked = []
    real = IC.check_lines

    def fake(store_, session, ref, lines, transport_factory):
        asked.append([l['check'] for l in lines])
        return {'lines': [{'check': 'not yet done', 'weight': 'must', 'pass': True, 'seen': 'two bricks laid, the third in hand'}], 'must_failed': []}
    monkeypatch.setattr(IC, 'check_lines', fake)
    row = VS.approve_reference(store, USER, RUN, [], rid, 'a' * 64, '', FakeConn([]))
    assert row['status'] == 'approved' and asked == [['not yet done']]
    assert [l['check'] for l in saved(store)['references'][rid]['check']['lines']] == ['scale', 'not yet done']   # kept with the check, asked once
    monkeypatch.setattr(IC, 'settings', lambda: types.SimpleNamespace(GEMINI_API_KEY=types.SimpleNamespace(get_secret_value=lambda: '')))
    rec = real(store, saved(store), saved(store)['references'][rid], [{'check': 'x', 'pass_when': 'y', 'weight': 'must'}], None)
    assert rec['error'] == 'no Gemini key on the server' and rec['lines'] == []   # no key: undecided, never a pass


# ---------- a take is never prepared from a failed start ----------

def test_a_take_is_not_prepared_from_a_start_whose_line_failed():
    store, _ = take_store()
    with_line(store, 'R1', False)
    body = {'shot_id': 'VS1', 'motion_prompt': 'he lays one brick', 'subject_reconciliation': {'E1': 'the mason'}, 'start_image': 'R1', 'end_image': 'R2', 'continuity_notes': 'the wall'}
    with pytest.raises(Problem, match='R1 already shows the result'):
        g(lambda: VS.prepare_take(store, USER, RUN, [], body))
    VS.answer(store, USER, RUN, [], 'R1', 'approve anyway')   # the operator's word: the take may be prepared from it
    assert VS.prepare_take(store, USER, RUN, [], body)['preparation_id']
    store, _ = take_store()
    with_line(store, 'R1', True)
    assert VS.prepare_take(store, USER, RUN, [], body)['preparation_id']
