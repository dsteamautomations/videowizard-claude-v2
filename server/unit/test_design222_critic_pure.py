"""design/222, the critic's nine points on the finished branch (19 Nov 2026), each with a test that failed first. Without a database."""
from datetime import timedelta

import pytest

from app import guide as G, guide_worker as GW, pictures as P, takes as T, visual_workers as VW, visuals_stage as V
from app.errors import Problem
from test_design222_takes_pure import NOW, RUN, SHA, USER, guide, held, job, line_of, look, plan, rec, session, shot, states   # noqa: F401 (`held` is the fixture)


# S1: while step 6 is still being made, no take is asked one by one in the chat
def test_s1_the_takes_wait_for_step_6_too(held, monkeypatch):
    s, p = session(), plan(shot('S1'), shot('S2', 'still', 129, 260))
    s['guides'].update(S1=guide())
    s['take_checks'].update(j1=rec(look=look()))
    held(s, p)
    monkeypatch.setattr(V, 'item_link', lambda *a: '')
    assert T.complete(T.expected(s, p, [job('j1')], NOW)) and not P.complete(P.expected(s, p, [job('j1')]))      # every take is made and checked; a still of step 6 is not started
    assert [w['kind'] for w in V.waiting(s, p, 'VW-99', [job('j1')])] == []
    assert [w['kind'] for w in V.waiting(s, p, 'VW-99', [job('j1')], gate=False)] == ['take to select']


# S2: "Use take n after all": the earlier take is selected first; a refusal leaves the newer take as it was


# S3: a take rejected with no new one ordered: the server says what the assistant asks


# S4: a take shot for an older plan: on the page with Make another and Reject, never a dead end
def test_s4_a_take_for_an_older_plan_is_on_the_page_and_cannot_be_selected(held):
    s, p = session(), plan(shot('S1'))
    s['guides'].update(S1=guide(takes=['j1']))
    s['take_checks'].update(j1=rec(look=look()))
    held(s, p)
    rows = [job('j1', shot_print='of another plan')]
    assert T.complete(T.expected(s, p, rows, NOW))                         # it does not keep the page closed
    line = line_of(s, p, rows)
    assert [b['choice'] for b in line['buttons']] == ['again'] and line['takes'][0]['short'] == T.W['stale']   # design/223: it cannot be accepted; the operator says what should change
    with pytest.raises(ValueError, match='earlier plan'):
        T.answer(None, None, USER, RUN, {}, 'S1', rows, 'select', 'Select', '')
    assert G.same_of('r', 's', 'p', 'plan-1') != G.same_of('r', 's', 'p', 'plan-2')   # the same guide, still and words for another plan is another request


# S5: a changed layout keeps the order given on the page
def test_s5_a_new_scene_keeps_the_order():
    order = {'job_id': 'j1', 'words': 'He lays the broom down.'}
    assert G.carried({'again': order, 'shoot_asked': {'stamp': 'x'}, 'stills': []}) == {'again': order}
    assert G.carried({'again': {**order, 'sent': 'j2'}}) == {} and G.carried({}) == {}


# S6: an order the cost limit refuses is dropped and said; an order can be withdrawn


# S7: the price line is said once per order, on both paths


# S8: the looks list names the takes' own helper, and the takes still due are counted


# S9: a take whose submission is unknown is still open, never "could not be made"
def test_s9_an_unknown_submission_is_being_made(held):
    s, p = session(), plan(shot('S1'))
    s['guides'].update(S1=guide())
    held(s, p)
    assert states(s, p, [job('j1', status='submission_unknown')]) == [('S1', 'being made')]


# not built: a take ordered from the page is a decision in the run's log, with its price


# lesser: a failed measurement leaves the line out; a re-run of the worker's check keeps Claude's lines on the card
