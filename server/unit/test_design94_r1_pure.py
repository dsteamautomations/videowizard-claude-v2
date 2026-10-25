"""design/94, Release 1: the right picture in the right shot (design/93 S1-S5, L1-L4, A1-A2, U1-U3, and the check-lines bug behind S4)."""
from pathlib import Path

import pytest

from app import image_check as IC, lookalike, visuals_stage as VS
from app.errors import Problem
from test_visuals_stage_pure import FakeConn, RUN, USER, accepted, g, plan_doc, saved, session, shot, store_with
from test_batch89b_pure import SPEC

STATES = [{'what_appears': 'the section', 'hold_s': 4}, {'what_appears': 'the cavities', 'hold_s': 3}, {'what_appears': 'the label', 'hold_s': 3}]


def film(**over):
    doc = plan_doc([shot('DG1', 0, 250, 'diagram', claims=['the cavity holds air'], depicts='a rat-trap wall in section'),
                    shot('AN1', 250, 500, 'animation', states=STATES, claims=['the wall builds in three steps'])],
                   [shot('DG2', 900, 1000, 'diagram', claims=['fewer bricks are used'], depicts='a conventional wall', drawing_spec=SPEC),
                    shot('VS1', 1000, 1150, 'video')])
    sess = session(versions=[{'version': 1, 'file': {'key': 'run-1/visuals/plan-v1.json'}, 'plan_digest': 'd1', 'warnings': []}], current='d1', accepted=accepted(doc),
                   repeat_rules='refuse', **over)
    return doc, sess


def pic(rid, shot_id=None, status='candidate', kind='keyframe', parents=(), **extra):
    return {'id': rid, 'name': extra.pop('name', rid), 'kind': kind, 'element_id': 'E1', 'status': status, 'key': f'run-1/visuals/references/{rid}.png', 'sha256': 'sha-' + rid,
            'bytes': 100, 'subject': 'the wall', 'generation': {'op': 'edit' if parents else 'generate', 'parents': [{'id': p} for p in parents]},
            **({'shot_id': shot_id} if shot_id else {}), **extra}


def refs(*rows):
    return {r['id']: r for r in rows}


def held(rid):
    return {'kind': 'still', 'reference_id': rid, 'key': f'run-1/visuals/references/{rid}.png', 'sha256': 'sha-' + rid, 'bytes': 100}


@pytest.fixture(autouse=True)
def cheap(monkeypatch):
    monkeypatch.setattr(VS, 'prices', lambda: {'image_inr': 4.0, 'video_inr_per_s': 8.9})


def image(store, **body):
    return VS.generate_image(FakeConn([]), store, USER, RUN, [], {'request_id': body.pop('request_id', 'q1'), 'element_id': 'E1', 'name': 'wall', 'kind': 'keyframe',
                                                                 'subject': 'the wall', 'prompt': 'A wall in section.', **body})


# ---------- R1.1 (S3): every picture records its shot ----------

def test_a_keyframe_names_its_shot_and_a_state_or_an_end_image_takes_its_parents():
    doc, sess = film(references=refs(pic('S1', 'AN1'), pic('K1', 'DG1'), pic('OLD', kind='state')))
    store = store_with(sess, doc)
    with pytest.raises(Problem, match='--shot'):
        g(lambda: image(store))
    out = image(store, kind='state', parents=['S1'], request_id='q2')
    assert saved(store)['references'][out['reference_id']]['shot_id'] == 'AN1'
    out = image(store, parents=['K1'], prompt='Image 1 is the start; the cavities now show.', request_id='q3')
    assert saved(store)['references'][out['reference_id']]['shot_id'] == 'DG1'
    out = image(store, kind='state', parents=['OLD'], fix_of='OLD', name='OLD-fix', request_id='q4')   # a fix of an old picture with no shot is still made
    assert 'shot_id' not in saved(store)['references'][out['reference_id']]


def test_a_fix_carries_the_shot_of_the_picture_it_fixes():
    assert IC.fix_body(pic('K1', 'DG1'), {'check': 'x', 'pass_when': 'the cavity shows'})['shot_id'] == 'DG1'


def test_the_page_gives_each_picture_its_shot_and_an_old_fix_its_originals():
    doc, sess = film(references=refs(pic('K1', 'DG1'), pic('K1F', fix_of='K1', parents=['K1']), pic('W1', kind='web', status='approved')))
    by = {r['id']: r for r in VS.page_view(FakeConn([]), store_with(sess, doc), RUN, [], 'VW-9')['references']}
    assert by['K1']['shot_id'] == 'DG1' and by['K1F']['shot_id'] == 'DG1' and by['W1']['shot_id'] is None


# ---------- R1.2 (S4): checked against its own shot only ----------

def test_a_picture_is_checked_against_its_own_shot_only():
    doc, sess = film()
    store = store_with(sess, doc)
    out = image(store, shot_id='DG1')
    checks = {l['check'] for l in saved(store)['references'][out['reference_id']]['server_checklist']}
    assert {'claim: the cavity holds air', 'depicts: a rat-trap wall in section'} <= checks
    assert not any('fewer bricks' in c or 'conventional wall' in c or 'three steps' in c or 'leaves' in c for c in checks)
    assert not any('DG2' in w for w in out.get('warnings') or [])
    out = image(store, shot_id='DG2', request_id='q2')
    assert any('drawing spec of DG2' in w for w in out['warnings'])
    out = image(store, kind='isolated', request_id='q3')
    checks = {l['check'] for l in saved(store)['references'][out['reference_id']].get('server_checklist') or []}
    assert not any(c.startswith(('claim:', 'depicts:', 'relationship:')) for c in checks)


# ---------- R1.5 (U2): a web picture is a guide only ----------

def test_a_web_picture_never_goes_into_the_film():
    doc, sess = film(references=refs(pic('W1', kind='web', status='approved')))
    with pytest.raises(Problem, match='a web picture is a guide only; it cannot appear in the film'):
        g(lambda: VS.still_from_reference(store_with(sess, doc), USER, RUN, [], 'DG1', 'W1', 'yes'))


# ---------- R1.6 (A1, L1): approving places it ----------

def test_approving_a_picture_for_a_still_shot_places_it_and_a_second_replaces_it():
    doc, sess = film(references=refs(pic('K1', 'DG1'), pic('K2', 'DG1')))
    store = store_with(sess, doc)
    out = VS.approve_reference(store, USER, RUN, [], 'K1', 'sha-K1', 'Yes, that one.')
    s = saved(store)
    assert s['references']['K1']['status'] == 'approved' and s['assets']['DG1']['reference_id'] == 'K1' and out['placed'] == 'DG1' and not out.get('replaced')
    out = VS.approve_reference(store, USER, RUN, [], 'K2', 'sha-K2', 'The second is better.')
    s = saved(store)
    assert s['assets']['DG1']['reference_id'] == 'K2' and out['replaced'] == 'K1' and s['references']['K1']['status'] == 'approved'


def test_a_refused_placement_approves_nothing():
    doc, sess = film(references=refs(pic('K1', 'DG1')), assets={'DG2': held('K1')})
    store = store_with(sess, doc)
    with pytest.raises(Problem, match='already in DG2'):
        g(lambda: VS.approve_reference(store, USER, RUN, [], 'K1', 'sha-K1', 'yes'))
    assert saved(store)['references']['K1']['status'] == 'candidate' and 'DG1' not in saved(store)['assets']


def test_approving_a_video_shots_image_or_a_state_places_nothing():
    doc, sess = film(references=refs(pic('V1', 'VS1'), pic('S1', 'AN1')))
    store = store_with(sess, doc)
    assert 'placed' not in VS.approve_reference(store, USER, RUN, [], 'V1', 'sha-V1', 'yes')
    assert 'placed' not in VS.approve_reference(store, USER, RUN, [], 'S1', 'sha-S1', 'yes')
    assert saved(store)['assets'] == {}


# ---------- R1.7 (L2): only into its own shot ----------

def test_a_picture_made_for_another_shot_moves_only_with_the_operators_words():
    doc, sess = film(references=refs(pic('K1', 'DG2', 'approved'), pic('K0', status='approved'), pic('F1', kind='frame', status='approved')))
    store = store_with(sess, doc)
    with pytest.raises(Problem, match='made for DG2'):
        g(lambda: VS.still_from_reference(store, USER, RUN, [], 'DG1', 'K1', 'yes'))
    VS.still_from_reference(store, USER, RUN, [], 'DG1', 'K1', 'yes', move='Use the DG2 drawing here; DG2 gets a new one.')
    s = saved(store)
    assert s['assets']['DG1']['reference_id'] == 'K1' and s['references']['K1']['shot_id'] == 'DG1'
    assert s['references']['K1']['moved']['from'] == 'DG2' and s['references']['K1']['moved']['quote'].startswith('Use the DG2')
    out = VS.still_from_reference(store, USER, RUN, [], 'DG2', 'K0', 'yes')
    assert any('no shot recorded' in w for w in out['warnings'])
    out = VS.still_from_reference(store, USER, RUN, [], 'DG2', 'F1', 'yes')   # SK, L2: a footage frame stays placeable under the reuse rules
    assert out['kind'] == 'still' and not any('no shot recorded' in w for w in out.get('warnings') or [])


# ---------- R1.8 (L3): where it is, and how to take it out ----------

def test_h5_names_the_shot_and_unplace_takes_the_picture_out():
    doc, sess = film(references=refs(pic('K1', 'DG1', 'approved')), assets={'DG1': held('K1')})
    store = store_with(sess, doc)
    with pytest.raises(Problem, match=r'already in DG1\..*take it out there first: `vw visuals unplace --shot DG1`'):
        g(lambda: VS.still_from_reference(store, USER, RUN, [], 'DG2', 'K1', 'yes', move='move it'))
    out = VS.unplace(store, USER, RUN, [], 'DG1', 'Take it out.')
    s = saved(store)
    assert 'DG1' not in s['assets'] and out['removed'] == 'K1' and s['references']['K1']['status'] == 'approved'
    assert s['unplaced'][0]['shot_id'] == 'DG1' and s['unplaced'][0]['quote'] == 'Take it out.' and s['unplaced'][0]['by'] == 'u1'
    with pytest.raises(Problem, match='DG1 holds no picture'):
        g(lambda: VS.unplace(store, USER, RUN, [], 'DG1', 'again'))


def test_unplace_refuses_a_recorded_gap():
    doc, sess = film(references=refs(pic('K1', 'DG1', 'approved')), assets={'DG1': held('K1')}, recorded_gaps={'G1': 'out-1'})
    with pytest.raises(Problem, match='G1 is recorded'):
        g(lambda: VS.unplace(store_with(sess, doc), USER, RUN, [], 'DG1', 'out'))


# ---------- R1.9 (A2, L4): a sequence in the plan's order ----------

def build(*extra):
    return [pic('A', 'AN1', name='keyframe-TITLE-a'), pic('B', 'AN1', kind='state', parents=['A'], name='state-TITLE-b'),
            pic('C', 'AN1', kind='state', parents=['B'], name='state-TITLE-c'), *extra]


def test_a_sequence_takes_its_states_in_the_plans_order_without_ticks():
    a, b, c = build()
    doc, sess = film(references=refs(c, pic('X', 'AN1', 'rejected', kind='state', parents=['A']), a, b))
    store = store_with(sess, doc)
    out = VS.sequence(store, USER, RUN, [], 'AN1', [], 'Yes, the build.')
    assert [st['reference_id'] for st in saved(store)['assets']['AN1']['states']] == ['A', 'B', 'C'] and out['warnings'] == []
    with pytest.raises(Problem, match=r"in the plan's order the states are A, B, C"):
        g(lambda: VS.sequence(store_with(sess, doc), USER, RUN, [], 'AN1', ['B', 'A', 'C'], 'yes'))
    assert VS.sequence(store_with(sess, doc), USER, RUN, [], 'AN1', ['A', 'B', 'C'], 'yes')['states'] == 3


def test_two_pictures_for_one_state_or_a_wrong_count_are_refused_by_name():
    doc, sess = film(references=refs(*build(pic('B2', 'AN1', kind='state', parents=['A'], name='state-TITLE-b2'))))
    with pytest.raises(Problem, match='two pictures for state 2: state-TITLE-b, state-TITLE-b2; reject one'):
        g(lambda: VS.sequence(store_with(sess, doc), USER, RUN, [], 'AN1', [], 'yes'))
    doc, sess = film(references=refs(*build()[:2]))
    with pytest.raises(Problem, match='AN1 plans 3 states; its pictures make 2: keyframe-TITLE-a, state-TITLE-b'):
        g(lambda: VS.sequence(store_with(sess, doc), USER, RUN, [], 'AN1', [], 'yes'))


def test_a_look_alike_state_names_both_cards(monkeypatch):
    monkeypatch.setattr(VS, '_fingerprints', lambda store, k: {'graphic': 0, 'picture': 0})
    monkeypatch.setattr(lookalike, 'distance', lambda a, b: 0)
    doc, sess = film(references=refs(*build()))
    with pytest.raises(Problem, match=r'state 2 \(state-TITLE-b\) looks the same as state 1 \(keyframe-TITLE-a\)'):
        g(lambda: VS.sequence(store_with(sess, doc), USER, RUN, [], 'AN1', [], 'yes'))


def test_states_with_no_shot_recorded_use_the_given_order_with_a_warning():
    doc, sess = film(references=refs(pic('A'), pic('B', kind='state', parents=['A']), pic('C', kind='state', parents=['B'])))
    out = VS.sequence(store_with(sess, doc), USER, RUN, [], 'AN1', ['A', 'B', 'C'], 'yes')
    assert out['states'] == 3 and any('no shot recorded' in w for w in out['warnings'])
    with pytest.raises(Problem, match='no pictures made for AN1'):
        g(lambda: VS.sequence(store_with(sess, doc), USER, RUN, [], 'AN1', [], 'yes'))


# ---------- the page (R1.3, R1.4, R1.8, R1.9, R1.10) ----------

def test_the_page_lists_a_shots_own_pictures_and_folds_its_references():
    page = (Path(__file__).resolve().parents[1] / 'app' / 'templates' / 'visuals.html').read_text(encoding='utf-8')
    assert 'r.shot_id===s.shot_id' in page and 'References used (' in page and 'guide only' in page and 'AI still for this shot · approve or reject' in page
    assert 'use as a state' not in page and 'seqTicks' not in page and 'data-a="unplace"' in page
