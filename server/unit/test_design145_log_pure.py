"""design/145 (SK, 3 Nov 2026): the decision log covers the page buttons, the background results and the visuals plan; no upload noise; steps outside a
stage under "run"."""
from app import jobs, runlog as L, visuals_stage as VS

RUN = '11111111-1111-1111-1111-111111111111'


def test_a_page_button_is_an_entry_with_its_run_code_stage_and_words():
    e = L.entry_from('/runs/VW-18/visuals/act', {'action': 'approve', 'ref': 'R12', 'shot': 'VS3', 'quote': 'looks right'}, 200, {'approved': True})
    assert e['run_code'] == 'VW-18' and e['stage'] == 'visuals' and 'approve' in e['entry'] and 'R12' in e['about'] and e['quote'] == 'looks right'
    m = L.entry_from('/runs/VW-18/review/act', {'action': 'decide', 'slide': '3.2', 'decision': 'REJECT', 'note': 'wrong tool'}, 200, {})
    assert m['stage'] == 'master' and 'REJECT' in m['about'] and m['quote'] == 'wrong tool'
    assert L.entry_from('/runs/VW-18/voices2/act', {'action': 'tryout', 'voice_ids': ['a']}, 201, {})['stage'] == 'voice'


def test_a_refused_page_button_is_a_refusal():
    e = L.entry_from('/runs/VW-18/visuals/act', {'action': 'take'}, 409, {'code': 'NOT_ALLOWED', 'message': 'over the cap'})
    assert e['kind'] == 'refusal' and 'over the cap' in e['entry']


def test_upload_steps_are_not_logged_and_steps_outside_a_stage_go_under_run():
    assert L.entry_from(f'/api/runs/{RUN}/files/sign', {'request_id': 'a'}, 200, {}) is None
    assert L.entry_from(f'/api/runs/{RUN}/files/receipt', {'request_id': 'a'}, 200, {}) is None
    assert L.entry_from(f'/api/runs/{RUN}/defects', {'request_id': 'a', 'error': 'x'}, 201, {})['stage'] == 'run'
    assert L.entry_from(f'/api/runs/{RUN}/claim', {'request_id': 'a'}, 200, {})['stage'] == 'run'


class Conn:
    def __init__(self, row):
        self.row, self.sql = row, []

    def execute(self, sql, args=()):
        self.sql.append((sql, args))
        return type('R', (), {'fetchone': lambda s: self.row})()


def test_a_finished_job_is_logged_and_a_retry_is_not():
    row = {'run_id': RUN, 'stage': 'visuals', 'unit': 'R7', 'request': {'kind': 'image', 'reference': {'name': 'keyframe-VS3', 'kind': 'keyframe'}}}
    c = Conn(row)
    jobs.finish(c, 'j1', 'ready', result={'check': {'verdict': 'fail', 'failed': ['label size']}})
    logged = [a for s, a in c.sql if 'insert into vw2_log' in s]
    assert len(logged) == 1 and 'ready' in logged[0][5] and 'keyframe-VS3' in logged[0][3] and 'fail' in logged[0][5]
    c = Conn(row)
    jobs.finish(c, 'j1', 'queued', retry_in=5)
    assert not [a for s, a in c.sql if 'insert into vw2_log' in s]
    c = Conn({**row, 'stage': 'analysis', 'request': {'kind': 'analysis', 'clip': {'name': 'C0054.mp4'}}})
    jobs.finish(c, 'j2', 'retained')
    assert not [a for s, a in c.sql if 'insert into vw2_log' in s]   # logged with its details at record (design/142)


def test_the_plan_writes_one_entry_per_gap_with_routes_and_purposes():
    plan = {'gaps': [{'gap_id': 'G1', 'scenes': [{'id': 'SC1', 'shots': [{'id': 'VS1', 'visual_type': 'video', 'purpose': 'show the pour'},
                                                                          {'id': 'IM1', 'visual_type': 'image', 'purpose': 'the finished slab'}]}]},
                     {'gap_id': 'G2', 'recommended_choice': 'B', 'choice_reason': 'warmer',
                      'choices': [{'id': 'A', 'scenes': [{'id': 'x', 'shots': [{'id': 'D1', 'visual_type': 'drawn', 'purpose': 'a'}]}]},
                                  {'id': 'B', 'scenes': [{'id': 'y', 'shots': [{'id': 'D2', 'visual_type': 'diagram', 'purpose': 'b'}]}]}]}]}
    out = VS.plan_log({'id': RUN}, plan, 3)
    assert len(out) == 2 and 'VS1 AI video' in out[0]['entry'] and 'show the pour' in out[0]['entry']
    assert 'choice B' in out[1]['entry'] and 'warmer' in out[1]['entry'] and 'D2' in out[1]['entry'] and 'D1' not in out[1]['entry']


def test_the_middleware_logs_a_page_button(monkeypatch):
    from fastapi.testclient import TestClient
    from app import main, web
    seen = []
    monkeypatch.setattr(L, 'write_apart', seen.append)
    monkeypatch.setattr(web, 'page_user', lambda s: None)   # no session: the page refuses, and the refusal is logged
    r = TestClient(main.app).post('/runs/VW-18/visuals/act', json={'action': 'approve', 'ref': 'R1'})
    assert len(seen) == 1 and seen[0]['run_code'] == 'VW-18' and seen[0]['stage'] == 'visuals' and r.status_code == seen[0].get('status', r.status_code)
