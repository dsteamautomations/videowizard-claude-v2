"""Release 3, E1 (SK, 20 Nov 2026, N3: "Yes, add all three"): the run's log gains three lines. (a) A refused read of a run is a refusal entry,
as a refused write is (before: 24 of 51 refusals of one stage were not in the log). (b) A `visuals/chat/next` line names what it handed out:
the item's id and kind, a group's ids, a card's lines. (c) A question the assistant puts on an item (`vw visuals ask`) is a `question` entry
that names the item and the question, so its wait can be measured from the log. Short lines; no body, no picture data. Without a database."""
import uuid

from app import chat_flow as C, runlog as L, visuals_stage as V

RUN = '11111111-1111-1111-1111-111111111111'


# ---------- (a) a refused read ----------

def test_a_refused_read_is_an_entry_that_names_the_path_and_the_reason():
    e = L.entry_from(f'/api/runs/{RUN}/visuals/motion/brief/BEAT_02-B1_S1', {}, 422, {'code': 'VISUALS_REFUSED', 'message': 'Before the first brief, the texts of every drawn shot go in the plan'}, read=True)
    assert e['kind'] == 'refusal' and e['rule'] == 'VISUALS_REFUSED' and e['stage'] == 'visuals' and e['by_kind'] == 'assistant' and e['run_id'] == RUN
    assert e['entry'] == 'read visuals/motion/brief/BEAT_02-B1_S1 refused: Before the first brief, the texts of every drawn shot go in the plan'
    assert L.entry_from(f'/api/runs/{RUN}/visuals/shots/S1/packet', {}, 200, {'packet': {}}, read=True) is None        # a read that is answered is never logged
    assert L.entry_from(f'/api/runs/{RUN}/log', {}, 409, {'code': 'RUN_CLOSED', 'message': 'x'}, read=True) is None    # the log's own read
    assert L.entry_from('/api/meta', {}, 500, {}, read=True) is None                                                    # not a run's path
    assert L.entry_from(f'/api/runs/{RUN}/visuals', {}, 404, {'code': 'NOT_FOUND', 'message': 'Run not found.'}, read=True) is None   # a run this user does not hold: nothing to write under
    assert L.entry_from(f'/api/runs/{RUN}/visuals', {}, 401, {'code': 'AUTH', 'message': 'Sign in.'}, read=True) is None


def test_the_middleware_logs_a_refused_read_and_leaves_an_answered_read_alone(monkeypatch):
    from fastapi.testclient import TestClient
    from app import main
    seen = []
    monkeypatch.setattr(L, 'write_apart', seen.append)
    r = TestClient(main.app).get(f'/api/runs/{RUN}/visuals/motion/brief/S1', headers={'X-VW-Plugin': '0.1.0'})   # refused before any database is asked
    assert r.status_code == 426 and r.json()['code'] == 'PLUGIN_TOO_OLD'
    assert len(seen) == 1 and seen[0]['kind'] == 'refusal' and seen[0]['entry'].startswith('read visuals/motion/brief/S1 refused: Your vw plugin')
    assert TestClient(main.app).get('/api/meta').status_code == 200 and len(seen) == 1


# ---------- (b) which card was handed out ----------

def test_the_next_line_names_the_item_the_group_or_the_card_it_handed_out():
    assert C.handed({'item': {'id': 'question:BEAT_15-B1_S5', 'kind': 'question'}}) == 'handed out question:BEAT_15-B1_S5 (question)'
    group = {'kind': 'still end-frame', 'items': [{'id': 'still-end:D1'}, {'id': 'still-end:D2'}]}
    assert C.handed({'item': None, 'group': group}) == 'handed out 2 together (still end-frame): still-end:D1, still-end:D2'
    card = {'id': 'card-9f', 'step': 'Plan', 'entries': 3}
    assert C.handed({'item': None, 'card': card}) == 'handed out card card-9f (Plan, 3 lines)'
    assert C.handed({'item': None, 'needed': False, 'working': ['x']}) == 'nothing handed out'


def test_the_log_line_of_a_next_call_carries_it(monkeypatch):
    monkeypatch.setattr(C, '_next_item', lambda *a, **k: {'item': {'id': 'gap:G1:abc', 'kind': 'plan gap'}})
    monkeypatch.setattr(V, 'session_of', lambda *a, **k: {'current': None})
    plain = C.next_item(None, None, {'id': 'u1'}, {'id': 'run-1'}, [])
    assert 'log' not in plain                                                             # what the chat and the page read is as before
    out = C.logged(plain)                                                                 # the three chat routes answer with it (main.py)
    assert out['log'] == 'handed out gap:G1:abc (plan gap)'
    import inspect
    from app import main
    assert all('chat_flow.logged(' in inspect.getsource(fn) for fn in (main.visuals_chat_next, main.visuals_chat_answer, main.visuals_chat_card))
    e = L.entry_from(f'/api/runs/{RUN}/visuals/chat/next', {'request_id': str(uuid.uuid4())}, 200, out)
    assert e['kind'] == 'step' and e['entry'] == 'visuals/chat/next: handed out gap:G1:abc (plan gap)'
    answered = L.entry_from(f'/api/runs/{RUN}/visuals/chat/answer', {'request_id': 'r', 'item': 'gap:G0:x', 'choice': 'accept', 'quote': 'Accept'}, 200, {'answered': 'gap:G0:x', **out})
    assert answered['entry'] == 'visuals/chat/answer: handed out gap:G1:abc (plan gap)' and answered['quote'] == 'Accept'   # an answer brings the next card: the same words


# ---------- (c) a question asked ----------

def test_a_question_put_on_an_item_is_a_question_entry_with_the_item_and_the_question():
    body = {'request_id': 'r1', 'item': 'BEAT_15-B1_S5', 'question': 'No client logo file was given: which logo closes the film?', 'choices': ['The agency logo', 'No logo'], 'cost_inr': None}
    e = L.entry_from(f'/api/runs/{RUN}/visuals/ask', body, 200, {'item': 'BEAT_15-B1_S5', 'question': body['question']})
    assert e['kind'] == 'question' and e['by_kind'] == 'assistant' and e['about'] == 'item BEAT_15-B1_S5'
    assert e['entry'] == 'asked on BEAT_15-B1_S5: No client logo file was given: which logo closes the film? (The agency logo | No logo)'
    refused = L.entry_from(f'/api/runs/{RUN}/visuals/ask', body, 422, {'code': 'VISUALS_REFUSED', 'message': 'BEAT_15-B1_S5 already waits for an answer'})
    assert refused['kind'] == 'refusal'                                                   # a question that was not recorded is not an asked line
    answer = L.entry_from(f'/api/runs/{RUN}/visuals/answer', {'request_id': 'r2', 'item': 'BEAT_15-B1_S5', 'answer': 'The agency logo'}, 200, {})
    assert answer['about'] == 'item BEAT_15-B1_S5' and answer['kind'] == 'step'            # the answer names the same item, so the two lines pair
