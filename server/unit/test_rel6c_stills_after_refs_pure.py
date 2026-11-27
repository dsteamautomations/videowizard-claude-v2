"""Release 1 of 27 Nov 2026, phase 2, part C (SK approved): a still picture is ordered only after the references of what it shows are approved.

Seen on VW-25 (6.2): the next-step line told the assistant to order all 19 stills at once during the first question of the references
step; none had an approved picture to be made from; 15 were sent back (two days, about Rs 76). Now a still is due only when every thing
it shows that gets a reference has its approved one (`visuals_stage.refs_waited`): the line names only the due stills and counts the
others, and the server refuses an order made too early. Each test failed first. Without a database."""
import uuid

import pytest

from app import pictures as P, visuals_stage as VS
from app.errors import Problem
from test_design221_p4_pure import V2
from test_visuals_stage_pure import FakeConn, RUN, USER, accepted, g, plan_doc, ref, saved, session, shot, store_with

WALL = {'id': 'WALL', 'name': 'Rat-trap wall', 'kind': 'object', 'identity': 'exact', 'requirements': "the client's wall"}
SHEET = {**ref('S2', 'approved'), 'kind': 'sheet', 'element_id': 'WALL'}


def film(rows=None, refs=None, no_round=False):
    """IM1 shows only the graphic E1; IM2 shows the wall, a thing of the reference round."""
    doc = plan_doc([shot('IM1', 0, 250, 'image'), shot('IM2', 250, 500, 'image', element_ids=['E1', 'WALL'])], [shot('VS1', 900, 1150, 'video', subjects=[])])
    doc['elements'].append(dict(WALL))
    rd = {} if no_round else {'round': {**V2, 'elements': {'WALL': {'verdict': 'approve'}} if rows is None else rows}}
    sess = session(versions=[{'version': 1, 'file': {'key': 'run-1/visuals/plan-v1.json'}, 'plan_digest': 'd1', 'warnings': []}], current='d1', accepted=accepted(doc),
                   references=dict(refs or {}), **rd)
    return store_with(sess, doc)


def waited(store):
    s = saved(store)
    plan = VS.current_plan(store, s)
    im2 = next(sh for _, sh in VS._accepted_shots(plan, s) if sh['id'] == 'IM2')
    return [e['id'] for e in VS.refs_waited(s, plan, im2)], s, plan


def order(store):
    body = {'request_id': str(uuid.uuid4()), 'element_id': 'WALL', 'name': 'still-IM2', 'kind': 'keyframe', 'shot_id': 'IM2', 'subject': 'the wall', 'parents': [],
            'prompt': 'The wall in its yard, at eye height, morning light.'}
    return g(lambda: VS.generate_image(FakeConn([]), store, USER, RUN, [], body))


# ---------- what holds a still ----------

def test_a_thing_of_the_round_holds_its_still_until_its_reference_is_approved():
    assert waited(film())[0] == ['WALL']
    assert waited(film(refs={'S2': {**SHEET, 'status': 'candidate'}}))[0] == ['WALL']      # made, not approved yet
    assert waited(film(refs={'S2': SHEET}))[0] == []
    assert waited(film(refs={'F2': {**ref('F2', 'approved'), 'kind': 'frame', 'element_id': 'WALL'}}))[0] == []   # the footage picture the operator approved


def test_what_gets_no_reference_holds_nothing():
    assert waited(film(rows={'WALL': {'verdict': 'ignore', 'ignored': True}}))[0] == []    # "no reference needed", left out, or gone on without
    assert waited(film(rows={}))[0] == []                                                   # the round does not list it
    assert waited(film(no_round=True))[0] == ['WALL']                                       # the references step has not begun
    s, plan = waited(film())[1:]
    im1 = next(sh for _, sh in VS._accepted_shots(plan, s) if sh['id'] == 'IM1')
    assert VS.refs_waited(s, plan, im1) == []                                               # a drawn thing has no reference set


# ---------- the next-step line ----------

def test_the_line_names_only_the_stills_that_are_due_and_counts_the_others():
    store = film()
    _, s, plan = waited(store)
    items = P.expected(s, plan, [])
    by = {i['id']: i for i in items}
    assert by['IM2']['waits_for'] == ['Rat-trap wall'] and 'waits_for' not in by['IM1']
    due = P.stills_due(items)
    assert 'IM1' in due and 'IM2' not in due and due.startswith('1 still shot has no picture asked for yet')
    assert P.stills_wait(items) == '1 still waits for the approved reference of: Rat-trap wall. It is ordered when that is approved; no order is taken before.'
    store = film(refs={'S2': SHEET})
    _, s, plan = waited(store)
    items = P.expected(s, plan, [])
    assert 'IM2' in P.stills_due(items) and P.stills_wait(items) == ''


def test_several_waiting_stills_are_counted_and_each_thing_named_once():
    items = [{'kind': 'still', 'id': 'IM1', 'state': P.STATE['none'], 'waits_for': ['The yard', 'The mason']}, {'kind': 'still', 'id': 'IM2', 'state': P.STATE['none'], 'waits_for': ['The yard']},
             {'kind': 'still', 'id': 'IM3', 'state': P.STATE['making'], 'waits_for': ['The gate']}]
    assert P.stills_wait(items).startswith('2 stills wait for the approved references of: The yard, The mason.')
    assert P.stills_due(items) == ''


# ---------- the order ----------

def test_an_order_made_too_early_is_refused_with_what_is_missing():
    with pytest.raises(Problem, match='IM2 waits for the approved reference of Rat-trap wall'):
        order(film())


def test_the_order_goes_once_the_reference_is_approved():
    assert order(film(refs={'S2': SHEET}))['reference_id']
