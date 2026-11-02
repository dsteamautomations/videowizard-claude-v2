"""design/142 R1 (SK, 2 Nov 2026): one decision log per run for every stage. The server writes every write step and every refusal (the refusal on its own
connection, so it survives the rollback); the assistant adds its judgement calls; the log reads as one story by stage and time; no body is copied whole."""
import pytest

from app import runlog as L
from app.errors import Problem

RUN = '11111111-1111-1111-1111-111111111111'


def test_a_write_step_becomes_one_entry_with_its_ids_and_the_operators_words():
    e = L.entry_from(f'/api/runs/{RUN}/visuals/images', {'request_id': 'r1', 'element_id': 'E1', 'shot_id': 'VS1', 'prompt': 'a long prompt', 'quote': 'yes, make it'}, 201, {'reference_id': 'R9'})
    assert e['run_id'] == RUN and e['stage'] == 'visuals' and e['kind'] == 'step' and e['by_kind'] == 'operator'
    assert 'E1' in e['about'] and 'VS1' in e['about'] and e['quote'] == 'yes, make it' and e['request_id'] == 'r1'
    assert 'a long prompt' not in str(e)   # never the whole body


def test_a_refusal_carries_its_code_and_message():
    e = L.entry_from(f'/api/runs/{RUN}/options/check', {'request_id': 'r2'}, 422, {'code': 'STAGE2_CONTRACT', 'message': 'G2 must_include_action_peak dropped'})
    assert e['kind'] == 'refusal' and e['rule'] == 'STAGE2_CONTRACT' and 'G2 must_include' in e['entry'] and e['stage'] == 'options'


def test_a_check_that_comes_back_rejected_is_logged_with_its_flags():
    e = L.entry_from(f'/api/runs/{RUN}/options/check', {'request_id': 'r3'}, 200, {'status': 'rejected', 'refusals': ['G12: numbers'], 'act_on': ['B1 pre-roll'], 'for_information': {'R1': 3}})
    assert e['kind'] == 'refusal' and 'G12' in e['entry'] and 'B1 pre-roll' in e['entry']


def test_the_stage_comes_from_the_path_or_the_body():
    assert L.entry_from(f'/api/runs/{RUN}/output', {'request_id': 'a', 'stage': 'brief', 'accepted_quote': 'approved'}, 201, {})['stage'] == 'brief'
    assert L.entry_from(f'/api/runs/{RUN}/film', {'request_id': 'a', 'key': 'shape', 'value': 'vertical', 'quote': 'vertical'}, 200, {})['stage'] == 'media'
    assert L.entry_from(f'/api/runs/{RUN}/analysis/start', {'request_id': 'a'}, 201, {})['stage'] == 'analysis'


def test_reads_the_assistants_own_log_and_unrelated_paths_are_not_logged():
    assert L.entry_from(f'/api/runs/{RUN}/log', {'request_id': 'a', 'text': 'x'}, 201, {}) is None   # written by its own endpoint
    assert L.entry_from('/api/auth/me', {}, 200, {}) is None and L.entry_from('/api/runs', {'client': 'x'}, 201, {}) is None


def test_an_assistant_entry_needs_text():
    with pytest.raises(Problem):
        L.assistant_entry(RUN, 'options', {'text': ' '})
    e = L.assistant_entry(RUN, 'options', {'text': 'C0073 dropped: eye-trace', 'about': 'C0073', 'rule': ''})
    assert e['by_kind'] == 'assistant' and e['rule'] == 'no rule' and e['kind'] == 'decision'


def test_the_log_reads_as_one_story_by_stage_and_time():
    rows = [{'at': '2026-11-02T10:00:00Z', 'stage': 'analysis', 'kind': 'step', 'about': 'C1', 'rule': '', 'entry': 'analysis start', 'by_kind': 'operator', 'by_name': 'R', 'quote': ''},
            {'at': '2026-11-02T11:00:00Z', 'stage': 'options', 'kind': 'decision', 'about': 'C0073', 'rule': 'no rule', 'entry': 'dropped', 'by_kind': 'assistant', 'by_name': '', 'quote': ''}]
    md = L.markdown('VW-16', rows)
    assert md.index('## analysis') < md.index('## options') and 'C0073' in md and 'no rule' in md


def test_the_middleware_logs_a_refusal_and_passes_the_response_through(monkeypatch):
    from fastapi.testclient import TestClient
    from app import main
    seen = []
    monkeypatch.setattr(L, 'write_apart', seen.append)
    r = TestClient(main.app).post(f'/api/runs/{RUN}/options/check', json={'request_id': 'r9', 'note': 'their words'}, headers={'X-VW-Plugin': '0.1.0'})
    assert r.status_code == 426 and r.json()['code'] == 'PLUGIN_TOO_OLD'
    assert len(seen) == 1 and seen[0]['kind'] == 'refusal' and seen[0]['rule'] == 'PLUGIN_TOO_OLD' and seen[0]['quote'] == 'their words'
    r = TestClient(main.app).get('/api/meta')
    assert len(seen) == 1   # a read is never logged
