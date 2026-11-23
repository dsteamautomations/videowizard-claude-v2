"""SK, 23 Nov 2026 (no-footage release 4): a film that is gaps end to end. The shot before and the shot after are read in film order across
touching gaps (the take's packet, the pictures shown to compare a take); the join out of a gap is asked only when a camera cut follows it.
Inside a gap, and beside a camera clip, everything reads as before."""
import pytest

from app import takes as T, visual_contract as VC, visuals_stage as VS


@pytest.fixture(autouse=True)
def accepted_as_planned(monkeypatch):
    monkeypatch.setattr(VS, 'gap_digest', lambda plan, gap: 'd')   # every gap of these films is accepted as it stands


def shot(sid, start, end):
    return {'id': sid, 'start_frame': start, 'end_frame': end, 'subjects': []}


def film(*gaps):
    """Accepted gaps of one scene each: ('g1', shot, shot), …"""
    plan = {'gaps': [{'gap_id': g, 'scenes': [{'id': g + 's', 'shots': list(shots)}]} for g, *shots in gaps]}
    session = {'accepted': {g['gap_id']: {'digest': 'd'} for g in plan['gaps']}, 'choice_selections': {}, 'references': {}, 'source': {'fps': 25, 'gaps': {}}}
    return plan, session


def test_the_shots_before_and_after_are_read_across_touching_gaps():
    a, b, c, d = shot('a', 0, 50), shot('b', 50, 100), shot('c', 100, 150), shot('d', 200, 250)
    plan, session = film(('g1', a, b), ('g2', c), ('g3', d))
    assert VS.across(plan, session, c) == (b, None)   # g2 touches g1; a clip stands between g2 and g3
    assert VS.across(plan, session, b) == (a, c) and VS.across(plan, session, d) == (None, None) and VS.across(plan, session, a) == (None, b)


def test_a_gap_not_accepted_gives_no_neighbour():
    b, c = shot('b', 50, 100), shot('c', 100, 150)
    plan, session = film(('g1', b), ('g2', c))
    session['accepted'].pop('g1')
    assert VS.across(plan, session, c) == (None, None)


def test_the_packet_of_a_gaps_first_shot_names_the_shot_before_it_in_the_film():
    b, c, e = shot('b', 50, 100), shot('c', 100, 150), shot('e', 150, 200)
    plan, session = film(('g1', b), ('g2', c, e))
    ctx = VS.packet_context(session, plan, plan['gaps'][1], c)
    assert ctx['neighbours']['previous']['shot_id'] == 'b' and ctx['neighbours']['next']['shot_id'] == 'e'
    assert VS.packet_context(session, plan, plan['gaps'][1], e)['neighbours'] == {'previous': {'shot_id': 'c', 'ends': []}, 'next': None}   # inside a gap: as before
    assert VS.packet_context(session, plan, plan['gaps'][0], b)['neighbours']['previous'] is None


def test_the_join_out_is_asked_only_when_a_camera_cut_follows_the_gap():
    gaps = {'g1': {'start_frame': 0, 'end_frame': 100}, 'g2': {'start_frame': 100, 'end_frame': 200}, 'g3': {'start_frame': 300, 'end_frame': 400}, 'g4': {'start_frame': 500, 'end_frame': 600}}
    assert not VC.join_out_due(gaps, 'g1', 600)   # another gap follows at once
    assert VC.join_out_due(gaps, 'g2', 600) and VC.join_out_due(gaps, 'g3', 600)   # a camera clip follows
    assert not VC.join_out_due(gaps, 'g4', 600)   # the film ends
    assert VC.join_out_due(gaps, 'g4', None) and VC.join_out_due(gaps, 'g4', 700)   # the length not known, or a clip after it: as before


def test_a_take_is_compared_with_the_shot_before_it_in_the_gap_before(monkeypatch):
    b, c = {**shot('b', 50, 100), 'visual_type': 'image'}, {**shot('c', 100, 150), 'visual_type': 'video'}
    plan, session = film(('g1', b), ('g2', c))
    session.update(assets={'b': {'reference_id': 'r1'}}, selections={}, references={'r1': {'id': 'r1', 'key': 'k1', 'sha256': 's1'}})
    monkeypatch.setattr(T.P, 'footage', lambda session, gap: (None, None))
    before, after = T._beside(session, plan, plan['gaps'][1], c, [])
    assert [p['_key'] for p in before] == ['k1'] and before[0]['role'] == 'before' and after == []
