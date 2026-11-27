"""Release 1 of 27 Nov 2026, phase 1, part B (SK approved, question 7): one gate for Select, and work stamped with its own shot.

Seen on VW-25: the page offered "Select" for 7 drawings and Select refused them, twice ("The plan changed since this drawing was rendered").
The page read "is this work old?" from its own shot's fingerprint (issue 17); Select still compared the whole plan. Now a render and a video
record the fingerprint of their own shot when they are ordered (`shot_print`), and one function (`visuals_stage.select_gate`) answers for
Select, the page and the chat card. Work with no stamp counts as old. Each test failed first. Without a database."""
import inspect

import pytest

from app import pictures as P, takes as T, visuals_stage as V
from app.errors import Problem
from test_design130_p1_pure import motion_store
from test_design221_p1_pure import NEW, edit_plan
from test_design221_p1b_pure import all_pass, selectable, upload
from test_guide_route_pure import card, shot_take, take_film   # noqa: F401 (take_film: the fixture)
from test_visuals_stage_pure import FakeConn, USER, g, saved


def shots(doc):
    return {s['id']: s for gap in doc['gaps'] for sc in V.all_scenes(gap) for s in sc['shots']}


def other(doc, sid):
    return next(s for i, s in shots(doc).items() if i != sid)


def drawing():
    """MO1 rendered from a project whose fact check passed: (store, conn, the job row as the page reads it)."""
    store = motion_store()
    sha = upload(store)['sha256']
    conn = selectable(store, sha)
    all_pass(sha, store)
    return store, conn


def page_row(store, conn):
    """The job as the page has it: its request is what the server puts in the jobs table when the work is ordered (the same render ordered
    once more on a connection that keeps the insert)."""
    row = conn.execute('select * from vw2_jobs where id', ()).fetchone()
    rec = FakeConn([])
    V.render_motion(rec, store, USER, NEW, [], {'shot_id': 'MO1'})
    return {**row, 'request': next(x.obj for x in rec.inserted[-1] if isinstance(getattr(x, 'obj', None), dict))}


def gate(store, job):
    s = saved(store)
    return V.select_gate(s, V.current_plan(store, s), job['unit'], job['request'], job)


# ---------- the stamp ----------

def test_a_render_records_the_fingerprint_of_its_own_shot_in_its_request_file_and_in_its_job():
    store, conn = drawing()
    s = saved(store)
    want = V.shot_prints(V.current_plan(store, s))['MO1']
    assert V.load_json(store, s['preparations']['MO1']['key'])['shot_print'] == want
    assert page_row(store, conn)['request']['shot_print'] == want


def test_a_take_records_the_fingerprint_of_its_own_shot(take_film):
    store, conn = take_film
    shot_take(store, conn, {'guide': True, 'blocked': None, 'not_read': False, 'scorecard': card()})
    s = saved(store)
    want = V.shot_prints(V.current_plan(store, s))['VS1']
    assert conn.take['request']['shot_print'] == want and V.load_json(store, conn.take['request']['request_key'])['shot_print'] == want


# ---------- a drawing ----------

def test_a_drawing_is_selected_after_another_shot_changed():
    store, conn = drawing()
    row = page_row(store, conn)                                              # as it was ordered
    edit_plan(store, lambda d: other(d, 'MO1').update(purpose='only the other shot changed'))
    assert g(lambda: V.select_take(conn, store, USER, NEW, [], 'job-9', 'yes'))['job_id'] == 'job-9'   # was: "The plan changed since this drawing was rendered"
    assert gate(store, row) == ''


def test_a_drawing_whose_own_shot_changed_is_refused_with_todays_words_and_the_page_calls_it_old():
    store, conn = drawing()
    row = page_row(store, conn)                                              # as it was ordered
    edit_plan(store, lambda d: shots(d)['MO1'].update(purpose='this shot changed'))
    with pytest.raises(Problem, match='The plan changed since this drawing was rendered; render it again'):
        g(lambda: V.select_take(conn, store, USER, NEW, [], 'job-9', 'yes'))
    s = saved(store)
    assert 'The plan changed since this drawing was rendered' in gate(store, row)
    assert P._stale(s, V.current_plan(store, s), row)


def test_a_drawing_whose_shot_left_the_plan_or_that_has_no_stamp_is_old():
    store, conn = drawing()
    row = page_row(store, conn)
    s = saved(store)
    plan = V.current_plan(store, s)
    assert not P._stale(s, plan, row)
    assert P._stale(s, plan, {**row, 'request': {k: v for k, v in row['request'].items() if k != 'shot_print'}})   # made before this release
    assert P._stale(s, plan, {**row, 'unit': 'GONE'})
    assert P._stale(s, plan, {**row, 'request': {**row['request'], 'plan_digest': V.digest(plan), 'shot_print': 'another'}})   # the plan version decides nothing


def test_changed_shared_parts_are_refused_by_the_same_gate():
    store, conn = drawing()
    row = page_row(store, conn)
    row = {**row, 'request': {**row['request'], 'parts': {'part-a': 'old'}}}
    s = saved(store)
    s['motion_parts_approved'] = {'parts': [{'id': 'part-a', 'digest': 'new'}]}
    assert V.select_gate(s, V.current_plan(store, s), 'MO1', row['request'], row) == V.MOTION_PARTS_CHANGED.format(shot='MO1')
    assert P._stale(s, V.current_plan(store, s), row)


# ---------- an AI video ----------

def test_a_take_follows_the_same_rule(take_film, monkeypatch):
    store, conn = take_film
    job_id = shot_take(store, conn, {'guide': True, 'blocked': None, 'not_read': False, 'scorecard': card()})
    monkeypatch.setattr(T.C, 'final', lambda j: True)   # its full-size video
    V.review_take(conn, store, USER, NEW, [], job_id, 'accepted', 'right for the film', '', 'Accept')
    s = saved(store)
    assert not T._stale(s, V.current_plan(store, s), conn.take)
    edit_plan(store, lambda d: other(d, 'VS1').update(purpose='only the other shot changed'))
    s = saved(store)
    assert not T._stale(s, V.current_plan(store, s), conn.take)
    assert g(lambda: V.select_take(conn, store, USER, NEW, [], job_id, 'Accept'))['job_id'] == job_id   # was: "The plan changed since this take was shot"
    edit_plan(store, lambda d: shots(d)['VS1'].update(purpose='this shot changed'))
    s = saved(store)
    assert T._stale(s, V.current_plan(store, s), conn.take)
    with pytest.raises(Problem, match='The plan changed since this take was shot'):
        g(lambda: V.select_take(conn, store, USER, NEW, [], job_id, 'Accept'))


def test_a_360p_take_is_not_selected_and_the_page_keeps_its_own_accept(take_film):
    store, conn = take_film
    job_id = shot_take(store, conn, {'guide': True, 'blocked': None, 'not_read': False, 'scorecard': card()})
    V.review_take(conn, store, USER, NEW, [], job_id, 'accepted', 'right', '', 'Accept')
    s = saved(store)
    assert not T._stale(s, V.current_plan(store, s), conn.take)             # not old: the page shows it with its own Accept
    with pytest.raises(Problem, match='the film takes its'):
        g(lambda: V.select_take(conn, store, USER, NEW, [], job_id, 'Accept'))


# ---------- one function, and it never leaves a blank page ----------

def test_the_page_and_select_read_one_function_and_no_whole_plan_comparison_is_left():
    src = inspect.getsource(V.select_take)
    assert 'select_gate(' in src and "prep.get('plan_digest') ==" not in src and 'base_preparation_digest' not in src
    assert 'select_gate(' in inspect.getsource(P._stale) and 'select_gate(' in inspect.getsource(T._stale)
    assert not hasattr(V, 'other_plan')                                      # the plan version decides nothing any more


def test_an_unexpected_error_in_the_check_is_said_for_that_item_only():
    store, conn = drawing()
    row = page_row(store, conn)
    s = saved(store)
    plan = V.current_plan(store, s)
    words = V.select_gate(s, plan, 'MO1', {**row['request'], 'parts': 'not a list of parts'}, row)
    assert words.startswith('MO1 could not be checked') and P._stale(s, plan, {**row, 'request': {**row['request'], 'parts': 'not a list of parts'}})
    assert V.select_gate(s, plan, 'MO1', row['request'], row) == ''          # the next item is checked as usual
