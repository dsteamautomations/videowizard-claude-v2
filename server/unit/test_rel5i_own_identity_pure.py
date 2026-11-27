"""Release 1 of 27 Nov 2026, part I, rows 2 and 3 (SK: "Yes, both"): what was already ordered is told by the work's own shot.

"The same request is never sent twice" compared an identity that held the fingerprint of the whole plan. After a change to another shot the
same take could be ordered and paid again, and the same drawing was rendered again. Now the identity of a take, of a render and of a
correction leaves the whole plan out; a take's "same request" holds its own shot's fingerprint (`visuals_stage.shot_print`, as part B).
Each test failed first. Without a database."""
import pytest

from app import guide as GD, visuals_stage as V
from app.errors import Problem
from test_design221_p1_pure import NEW, edit_plan
from test_guide_route_pure import card, shot_take, take_film   # noqa: F401 (take_film: the fixture)
from test_rel5b_one_gate_pure import drawing, other, shots
from test_visuals_stage_pure import FakeConn, USER, saved


def test_the_identity_of_a_request_leaves_the_whole_plan_out_and_keeps_everything_else():
    a = {'kind': 'motion', 'shot_id': 'MO1', 'shot_print': 'p1', 'plan_digest': 'one plan'}
    assert V.own_identity(a) == V.own_identity({**a, 'plan_digest': 'another plan'})
    assert V.own_identity(a) != V.own_identity({**a, 'shot_print': 'p2'}) and V.own_identity(a) != V.own_identity({**a, 'shot_id': 'MO2'})


def test_a_takes_same_request_holds_its_own_shot():
    assert GD.same_of('g', 's', 'words', 'print') != GD.same_of('g', 's', 'words', 'another print')


def test_a_drawing_is_not_rendered_again_after_another_shot_changed():
    store, conn = drawing()
    was = saved(store)['preparations']['MO1']['preparation_id']
    edit_plan(store, lambda d: other(d, 'MO1').update(purpose='only the other shot changed'))
    rec = FakeConn([])
    V.render_motion(rec, store, USER, NEW, [], {'shot_id': 'MO1'})
    assert saved(store)['preparations']['MO1']['preparation_id'] == was       # was: another identity, so "already rendered" no longer applied


def test_a_drawing_whose_own_shot_changed_is_another_request():
    store, conn = drawing()
    was = saved(store)['preparations']['MO1']['preparation_id']
    edit_plan(store, lambda d: shots(d)['MO1'].update(purpose='this shot changed'))
    V.render_motion(FakeConn([]), store, USER, NEW, [], {'shot_id': 'MO1'})
    assert saved(store)['preparations']['MO1']['preparation_id'] != was


def test_the_same_take_is_not_sent_again_after_another_shot_changed(take_film):
    store, conn = take_film
    shot_take(store, conn, {'guide': True, 'blocked': None, 'not_read': False, 'scorecard': card()})
    edit_plan(store, lambda d: other(d, 'VS1').update(purpose='only the other shot changed'))
    with pytest.raises((Problem, ValueError), match='the same request is never sent twice'):   # was: sent and paid again
        GD.shoot(conn, store, USER, NEW, [], 'VS1', 'Shoot.')
