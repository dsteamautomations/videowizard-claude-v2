"""Issue 17, requirement R2 (VW-25, SK 25 Nov 2026): a video or a render made on an earlier plan stays valid when what it was made from did not
change.

Seen on VW-25: the plan got a new version in which one drawn shot changed (with the operator's answer). Eleven AI videos made on the version
before, not yet accepted, became "must be made again (the plan changed)" and could not be accepted, though none of their shots had changed: a
video or a render remembered the fingerprint of the whole plan. Now each plan version keeps a fingerprint per shot (the shot, its scene and its
part of the film without their other shots, the things it shows and their facts, the part every gap shares), and work made on another version is
old only when its own shot's fingerprint differs. The older way (any new plan version made every unaccepted video and every render of the film
old) is retired.
Release 1 of 27 Nov 2026, part B: the work itself now records its own shot's fingerprint when it is ordered (`shot_print`), so nothing is
looked up by plan version; work with no stamp counts as old. The tests give the stamp. Without a database."""
import copy
import json

import pytest

from app import pictures as P, takes as T, visuals_stage as V
from test_design222_takes_pure import NOW, RUN, USER, guide, held, job, line_of, plan, rec, session, shot   # noqa: F401 (`held` is the fixture)
from test_visuals_stage_pure import RUN as FILM, TREATMENT, FakeConn, plan_doc, saved, store_with
from test_visuals_stage_pure import session as stored_session, shot as plan_shot


def film(*versions):
    """A session whose plan versions are these plans, the last one in force; (session, the plan in force)."""
    s = session(versions=[{'version': n, 'plan_digest': V.digest(p), 'shots': V.shot_prints(p)} for n, p in enumerate(versions, 1)])
    s['current'] = V.digest(versions[-1])
    s['guides'].update(S1=guide(takes=['j1']))
    s['take_checks'].update(j1=rec())
    return s, versions[-1]


def base(**more):
    p = plan(shot('S1'), shot('S2', start=129, end=260))
    return {**p, 'foundation': {'treatment': 'Bricks and how they are laid.'}, 'elements': [{'id': 'E1', 'name': 'Brick'}, {'id': 'E2', 'name': 'Trowel'}], **more}


def changed(p, change):
    q = copy.deepcopy(p)
    change(q)
    return q


def shots(p):
    return p['gaps'][0]['scenes'][0]['shots']


def made_on(p, sid='S1'):
    return [job('j1', sid=sid, shot_print=V.shot_print(p, sid))]   # as ordered on this plan


def test_a_change_to_another_shot_leaves_the_video_as_made_and_it_can_be_accepted(held, monkeypatch):
    one = base()
    s, p = film(one, changed(one, lambda q: shots(q)[1].update(narration='Other words for the other shot')))
    held(s, p)
    rows = made_on(one)
    assert [i['state'] for i in T.expected(s, p, rows, NOW)][0] == T.STATE['done']   # was "must be made again (the plan changed)"
    line = line_of(s, p, rows)
    assert 'select' in [b['choice'] for b in line['buttons']] and line['takes'][0]['short'] != T.W['stale']
    went = []
    monkeypatch.setattr(V, 'review_take', lambda *a, **k: went.append('reviewed'))
    monkeypatch.setattr(V, 'select_take', lambda *a, **k: went.append('selected') or {})
    monkeypatch.setattr(T.C, 'final', lambda j: True)
    T.answer(None, None, USER, RUN, {}, 'S1', rows, 'select', 'Select', '')   # was refused: "This take was made for an earlier plan of the film"
    assert went == ['reviewed', 'selected']


@pytest.mark.parametrize('change', [
    lambda q: shots(q)[0].update(narration='New words for this shot'),                        # the shot itself
    lambda q: shots(q)[0].update(end_frame=120),                                              # its place in the film
    lambda q: q['elements'][0].update(name='Fired brick'),                                    # a thing it shows
    lambda q: q['foundation'].update(treatment='Another film.'),                              # the part every gap shares
    lambda q: q.update(sequence_rules=[{'id': 'R1', 'rule': 'No hands in frame.'}]),
    lambda q: q['gaps'][0]['scenes'][0].update(setting='A yard at noon'),                     # its scene
    lambda q: q.update(visual_facts=[{'id': 'F1', 'about': 'E1', 'looks': 'red', 'status': 'confirmed'}]),   # a fact about a thing it shows
])
def test_a_change_to_what_the_video_was_made_from_makes_it_old_as_before(held, change):
    one = base()
    shots(one)[0]['element_ids'] = ['E1']
    s, p = film(one, changed(one, change))
    held(s, p)
    rows = made_on(one)
    assert [i['state'] for i in T.expected(s, p, rows, NOW)][0] == T.STATE['stale']
    assert [b['choice'] for b in line_of(s, p, rows)['buttons']] == ['again']
    with pytest.raises(ValueError, match='earlier plan'):
        T.answer(None, None, USER, RUN, {}, 'S1', rows, 'select', 'Select', '')


@pytest.mark.parametrize('change', [
    lambda q: q['elements'][1].update(name='Steel trowel'),                                   # a thing this shot does not show
    lambda q: q['elements'].append({'id': 'E3', 'name': 'Line'}),                             # a thing added to the plan
    lambda q: q.update(visual_facts=[{'id': 'F2', 'about': 'E2', 'looks': 'steel', 'status': 'confirmed'}]),   # a fact about another thing
    lambda q: shots(q).append(shot('S3', start=260, end=300)),                                # a shot added beside it
])
def test_a_change_to_what_the_shot_does_not_show_leaves_it(held, change):
    one = base()
    shots(one)[0]['element_ids'] = ['E1']
    s, p = film(one, changed(one, change))
    held(s, p)
    assert [i['state'] for i in T.expected(s, p, made_on(one), NOW)][0] == T.STATE['done']


def test_the_work_is_compared_with_the_shot_as_it_was_made_from_not_with_the_version_before(held):
    one = base()
    two = changed(one, lambda q: shots(q)[0].update(narration='Changed in version 2'))
    three = changed(two, lambda q: shots(q)[1].update(narration='Only the other shot changed in version 3'))
    s, p = film(one, two, three)
    held(s, p)
    assert [i['state'] for i in T.expected(s, p, made_on(one), NOW)][0] == T.STATE['stale']   # made on 1; its shot changed in 2
    assert [i['state'] for i in T.expected(s, p, made_on(two), NOW)][0] == T.STATE['done']
    back = changed(three, lambda q: shots(q)[0].update(narration=shots(one)[0]['narration']))   # version 4 gives the shot its words of version 1 again
    s, p = film(one, two, three, back)
    assert not T._stale(s, p, made_on(one)[0]) and T._stale(s, p, made_on(two)[0])


def test_work_with_no_stamp_or_whose_shot_left_the_plan_is_old(held):
    one = base()
    s, p = film(one, changed(one, lambda q: shots(q)[1].update(narration='x')))
    assert T._stale(s, p, job('j1', shot_print='the fingerprint of another shot'))
    assert T._stale(s, p, job('j1', shot_print=''))                     # made before the release: no stamp
    assert T._stale(s, p, job('j1', shot_print='', plan_digest=V.digest(p)))   # the plan it names decides nothing
    gone = changed(one, lambda q: shots(q).pop(0))
    assert T._stale(film(one, gone)[0], gone, made_on(one)[0])          # the shot left the plan


def test_a_render_of_a_drawn_graphic_follows_the_same_rule():
    one = base()
    render = {'unit': 'S1', 'request': {'kind': 'motion', 'shot_print': V.shot_print(one, 'S1')}}
    for change, old in [(lambda q: shots(q)[1].update(narration='x'), False), (lambda q: shots(q)[0].update(narration='x'), True),
                        (lambda q: q['foundation'].update(treatment='x'), True)]:
        s, p = film(one, changed(one, change))
        assert P._stale(s, p, render) is old
    s, p = film(one, changed(one, lambda q: shots(q)[1].update(narration='x')))
    s['motion_parts_approved'] = {'parts': [{'id': 'part-a', 'digest': 'new'}]}
    assert P._stale(s, p, {**render, 'request': {**render['request'], 'parts': {'part-a': 'old'}}})   # the shared parts test stays


def test_a_plan_version_keeps_no_fingerprints_of_its_shots_any_more():
    """Release 1 of 27 Nov 2026, part B: the work carries its own stamp, so a plan version keeps none and no older plan file is read for them."""
    doc = plan_doc([plan_shot('AN1', 0, 500, 'animation', states=[{'what_appears': x, 'hold_s': 5} for x in 'abcd'])], [plan_shot('VS1', 900, 1150, 'video')])
    store = store_with(stored_session())
    V.treatment(store, USER, FILM, [], {**TREATMENT, 'direction': 'Show the hollow inside the wall.'}, 'yes')
    V.propose(FakeConn(), store, USER, FILM, [], doc)
    stored = json.loads(store.files['run-1/visuals/plan-v1.json'])['document']
    assert 'shots' not in saved(store)['versions'][0] and set(V.shot_prints(stored)) == {'AN1', 'VS1'}
    assert not hasattr(V, '_with_shot_prints')
    assert V.shot_prints({'gaps': [], 'elements': []}) == {}
