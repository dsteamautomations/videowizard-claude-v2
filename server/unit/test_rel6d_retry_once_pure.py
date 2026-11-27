"""Release 1 of 27 Nov 2026, phase 2, part D (SK approved; rule 4: "keep it"): a failed picture is made again once by itself.

6.16: a still that Claude's check failed still waited for the operator before it was made again. Now the assistant is told to make it
again once, with the failed lines (the route of a failed component); the picture is not shown meanwhile. The server counts the one try
(`still_retries`): a second failure goes to the operator as before. Rule 4: a picture that could not be made, for a cause other than a
refusal, is sent once more by the worker. Each test failed first. Without a database."""
import uuid

import pytest

from app import pictures as P, visual_workers as VW, visuals_stage as VS
from app.errors import Problem
from test_fixset3_pure import stills
from test_visual_workers_pure import JOB, Resp
from test_visuals_stage_pure import FakeConn, RUN, USER, g, saved


def state(store):
    s = saved(store)
    plan = VS.current_plan(store, s)
    return s, plan, {i['id']: i['state'] for i in P.expected(s, plan, [])}


def again(store, **more):
    """The assistant makes IM1's picture again, as it was told."""
    body = {'request_id': str(uuid.uuid4()), 'element_id': 'E1', 'name': 'still-IM1-again', 'kind': 'keyframe', 'shot_id': 'IM1', 'subject': 'the wall', 'parents': [],
            'prompt': 'The wall in its yard, its surface weathered.', **more}
    return g(lambda: VS.generate_image(FakeConn([]), store, USER, RUN, [], body))


# ---------- rules 1 to 3: the check failed ----------

def test_a_still_whose_check_failed_is_named_for_one_remake_and_not_shown_meanwhile():
    s, plan, states = state(stills(failed=True))
    k1 = s['references']['K1']
    assert P.retry_due(s, k1, plan) and not P.offered(s, k1, plan)
    assert states['IM1'] == P.STATE['redo']                                    # the page stays closed for it
    said = P.stills_failed(s, plan)
    assert len(said) == 1 and 'K1' in said[0] and 'the surface is new' in said[0] and 'once' in said[0]
    assert said[0] in P.waits_words(s, plan)                                   # the next-step line says it, each time


def test_a_still_that_passed_is_shown_as_before():
    s, plan, states = state(stills(failed=False))
    assert not P.retry_due(s, s['references']['K1'], plan) and P.offered(s, s['references']['K1'], plan) and P.stills_failed(s, plan) == []
    assert states['IM1'] == P.STATE['done']


def test_the_remake_is_counted_once_and_the_first_picture_stays_as_the_earlier_try(monkeypatch):
    monkeypatch.setattr(VS, 'prices', lambda: {'image_inr': 20.0, 'video_inr_per_s': 8.0})
    store = stills(failed=True)
    new = again(store)['reference_id']
    s, plan, states = state(store)
    assert s['still_retries']['IM1']['of'] == 'K1' and s['still_retries']['IM1']['by'] == new
    k1 = s['references']['K1']
    assert k1['status'] == 'rejected' and k1['rejection']['by'] == 'server' and 'the surface is new' in k1['rejection']['notes']   # kept, as the earlier try
    assert P.stills_failed(s, plan) == []
    # the second picture is made and fails the same line: it goes to the operator, no third try
    s['references'][new].update(status='candidate', sha256='b' * 64, key='run-1/visuals/references/new.png',
                                look={'sha256': 'b' * 64, 'lines': [{'id': 'l1', 'check': 'signs of use', 'pass': False, 'seen': 'the surface is new'}]})
    assert not P.retry_due(s, s['references'][new], plan) and P.offered(s, s['references'][new], plan) and P.stills_failed(s, plan) == []


def test_a_picture_the_operator_sent_back_is_not_retried_on_top():
    store = stills(failed=True)
    s = saved(store)
    s['references']['K0'] = {**s['references']['K1'], 'id': 'K0', 'status': 'rejected', 'rejection': {'notes': 'too dark', 'quote': 'No', 'by': 'u1', 'at': '2026-11-27T00:00:00+00:00'}}
    assert not P.retry_due(s, s['references']['K1'], VS.current_plan(store, s))   # their correction is the one try


def test_a_look_that_could_not_open_the_picture_is_no_ground_for_a_remake():
    store = stills(failed=True)
    s = saved(store)
    s['references']['K1']['look'] = {'sha256': s['references']['K1']['sha256'], 'not_checked': 'the file could not be opened', 'lines': []}
    assert not P.retry_due(s, s['references']['K1'], VS.current_plan(store, s))


def test_at_the_cost_limit_there_is_no_remake_and_the_first_picture_is_shown(monkeypatch):
    def at_the_limit(*a, **k):
        raise Problem(409, 'VISUALS_CAP', 'Rs 900 spent of Rs 900')
    monkeypatch.setattr(VS, 'check_cap', at_the_limit)
    store = stills(failed=True)
    with pytest.raises(Problem, match='spent of'):
        again(store)
    s, plan, states = state(store)
    assert s['still_retries']['IM1'] == {'of': 'K1', 'gave_up': 'Rs 900 spent of Rs 900'}
    assert s['references']['K1']['status'] == 'candidate' and P.offered(s, s['references']['K1'], plan) and states['IM1'] == P.STATE['done']


# ---------- rule 4: it could not be made ----------

def made(tmp_path, monkeypatch, status, body, attempt=1):
    monkeypatch.setattr(VW, 'SPOOL', tmp_path)
    monkeypatch.setattr(VW, 'storage', lambda: None)
    answer = Resp(status, body)
    answer._body = body   # as the Gemini call hands its answer in words (design/120)
    monkeypatch.setattr(VW, 'openai_client', lambda path, **kw: answer)
    return VW.process_image({**JOB, 'attempt': attempt})


SILENT = {'error': {'type': 'no_image', 'message': ''}}   # neither a picture nor a word came back


def test_a_picture_that_came_back_with_no_picture_and_no_word_is_sent_once_more_by_itself(tmp_path, monkeypatch):
    status, result, error, cost, retry = made(tmp_path, monkeypatch, 400, SILENT)
    assert (status, retry) == ('queued', 1) and result['failure'] == 'no_image' and error.endswith(VW.ONCE_MORE)
    status, result, error, cost, retry = made(tmp_path, monkeypatch, 400, SILENT, attempt=2)
    assert status == 'failed' and retry is None                                # the second failure is said to the operator, as before


@pytest.mark.parametrize('body', [{'error': {'type': 'moderation_blocked', 'moderation_stage': 'input', 'categories': ['violence'], 'message': 'blocked'}},
                                  {'error': {'type': 'image_generation_user_error', 'message': 'bad input'}},
                                  {'error': {'type': 'invalid_request_error', 'message': 'size is wrong'}},      # the same request would fail the same way
                                  {'error': {'type': 'no_image', 'message': 'I cannot draw a real person.'}}])   # the model's own words are a refusal
def test_a_refusal_is_never_sent_again_unchanged(tmp_path, monkeypatch, body):
    status, result, error, cost, retry = made(tmp_path, monkeypatch, 400, body)
    assert status == 'failed' and retry is None
