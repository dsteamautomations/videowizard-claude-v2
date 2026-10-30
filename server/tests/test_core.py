"""Slice 1 edge cases E1–E30 from design/03-slice-1-core-requirements.md, plus the happy path."""
import threading

import pytest

from conftest import rid, seed_session


def new_run(client, headers, version='test', **extra):
    r = client.post('/api/runs', json={'request_id': rid(), 'client': 'C', 'procedure_version': version, **extra}, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()['id']


def out(client, headers, run, stage, unit=None, quote='yes', files=None, summary=None, request_id=None):
    body = {'request_id': request_id or rid(), 'stage': stage, 'summary': summary or {}, 'files': files or []}
    if unit is not None:
        body['unit'] = unit
    if quote is not None:
        body['accepted_quote'] = quote
    return client.post(f'/api/runs/{run}/output', json=body, headers=headers)


def nxt(client, headers, run):
    r = client.get(f'/api/runs/{run}/next', headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


FILE = {'name': 'a.mp3', 'key': 'k/a.mp3', 'sha256': 'ab' * 32, 'bytes': 10, 'receipt': True}
NOFILE = {**FILE, 'receipt': False}


def test_happy_path_create_to_close(client, alice):
    run = new_run(client, alice)
    assert nxt(client, alice, run)['stage'] == 's1'
    assert out(client, alice, run, 's1', quote='yes approve s1').status_code == 201
    assert out(client, alice, run, 's2', files=[FILE], summary={'units': {'s3': ['u1']}}).status_code == 201
    n = nxt(client, alice, run)
    assert n['stage'] == 's3' and n['units_open'] == ['u1']
    assert out(client, alice, run, 's3', unit='u1', quote=None).status_code == 201
    assert out(client, alice, run, 's4').status_code == 201
    n = nxt(client, alice, run)
    assert n['stage'] is None and 'close' in n['allowed']
    r = client.post(f'/api/runs/{run}/close', json={'request_id': rid()}, headers=alice)
    assert r.status_code == 200 and r.json()['status'] == 'closed'
    assert nxt(client, alice, run)['actor'] == 'none'


def test_e1_next_on_new_run(client, alice):
    run = new_run(client, alice)
    n = nxt(client, alice, run)
    assert n['stage'] == 's1' and n['actor'] == 'operator' and n['attempts'] == 0 and n['cap'] == 3
    assert n['needs_acceptance'] is True and n['paid'] is None and n['version'] == 'test'
    assert 'output' in n['allowed']


def test_e2_output_wrong_stage(client, alice):
    run = new_run(client, alice)
    r = out(client, alice, run, 's2', files=[FILE])
    assert r.status_code == 409 and r.json()['code'] == 'NOT_ALLOWED'
    assert r.json()['next']['stage'] == 's1'


def test_e3_acceptance_required(client, alice):
    run = new_run(client, alice)
    r = out(client, alice, run, 's1', quote=None)
    assert r.status_code == 422 and r.json()['code'] == 'ACCEPTANCE_REQUIRED'


def test_e4_quote_too_long_or_blank(client, alice):
    run = new_run(client, alice)
    assert out(client, alice, run, 's1', quote='   ').status_code == 422
    assert out(client, alice, run, 's1', quote='x' * 2049).status_code == 422


def test_e5_paid_stage_is_informed_not_gated(client, alice):
    run = new_run(client, alice)
    out(client, alice, run, 's1')
    assert nxt(client, alice, run)['paid'] == 'fakevoice'
    assert out(client, alice, run, 's2', files=[FILE]).status_code == 201


def test_e6_acceptance_fields_recorded(client, alice):
    run = new_run(client, alice)
    out(client, alice, run, 's1', quote='yes, go ahead')
    r = client.get(f'/api/runs/{run}', headers=alice).json()
    o = r['outputs'][0]
    assert o['accepted_by'] == 'alice' and o['accepted_quote'] == 'yes, go ahead' and o['accepted_at'].endswith('Z')


def test_e9_e10_e11_attempt_cap_and_decision(client, alice):
    run = new_run(client, alice)
    for _ in range(3):
        assert out(client, alice, run, 's1', quote=None).status_code == 422
    r = out(client, alice, run, 's1', quote='yes')
    assert r.status_code == 409 and r.json()['code'] == 'NEEDS_USER_DECISION'
    assert set(r.json()['options']) == {'retry', 'revise', 'defect', 'stop'}
    assert nxt(client, alice, run)['actor'] == 'operator_decision'
    # E10: again, still blocked
    assert out(client, alice, run, 's1', quote='yes').status_code == 409
    # E11: retry grants one more attempt
    r = client.post(f'/api/runs/{run}/decide', json={'request_id': rid(), 'stage': 's1', 'decision': 'retry'}, headers=alice)
    assert r.status_code == 200
    assert out(client, alice, run, 's1', quote=None).status_code == 422
    assert out(client, alice, run, 's1', quote='yes').status_code == 409


def test_e12_success_resets_attempts(client, alice):
    run = new_run(client, alice)
    out(client, alice, run, 's1', quote=None)
    assert nxt(client, alice, run)['attempts'] == 1
    assert out(client, alice, run, 's1').status_code == 201
    r = client.get(f'/api/runs/{run}', headers=alice).json()
    assert r['attempts'] == []


def test_e13_e14_per_unit_stage(client, alice):
    run = new_run(client, alice)
    out(client, alice, run, 's1')
    out(client, alice, run, 's2', files=[FILE], summary={'units': {'s3': ['u1', 'u2', 'u3']}})
    out(client, alice, run, 's3', unit='u1', quote=None)
    out(client, alice, run, 's3', unit='u2', quote=None)
    n = nxt(client, alice, run)
    assert n['stage'] == 's3' and n['units_open'] == ['u3']
    r = out(client, alice, run, 's3', unit='u9', quote=None)
    assert r.status_code == 422 and r.json()['code'] == 'UNKNOWN_UNIT'
    r = out(client, alice, run, 's3', unit='u1', quote=None)
    assert r.status_code == 409 and r.json()['code'] == 'NOT_ALLOWED'


def test_e15_revise_without_paid_work_after(client, alice):
    run = new_run(client, alice)
    out(client, alice, run, 's1')
    out(client, alice, run, 's1', quote=None)  # one failed attempt on s1 later? no: s1 done; fail on s2 instead
    out(client, alice, run, 's2', quote=None, files=[FILE])
    r = client.post(f'/api/runs/{run}/revise', json={'request_id': rid(), 'stage': 's1'}, headers=alice)
    assert r.status_code == 200, r.text
    n = nxt(client, alice, run)
    assert n['stage'] == 's1' and n['attempts'] == 0
    view = client.get(f'/api/runs/{run}/stages/s1', headers=alice).json()
    assert view['outputs'][0]['stale'] is True


def test_e16_revise_stage_without_output(client, alice):
    run = new_run(client, alice)
    r = client.post(f'/api/runs/{run}/revise', json={'request_id': rid(), 'stage': 's2'}, headers=alice)
    assert r.status_code == 409 and r.json()['code'] == 'NOT_ALLOWED'


def test_e16a_e16b_revise_blocked_by_paid_work_then_confirmed(client, alice):
    run = new_run(client, alice)
    out(client, alice, run, 's1')
    out(client, alice, run, 's2', files=[FILE], summary={'cost_cents': 250})
    r = client.post(f'/api/runs/{run}/revise', json={'request_id': rid(), 'stage': 's1'}, headers=alice)
    assert r.status_code == 409 and r.json()['code'] == 'PAID_WORK_AFTER'
    assert r.json()['outputs'] == [{'stage': 's2', 'unit': None, 'cost_cents': 250}]
    assert nxt(client, alice, run)['stage'] == 's3'  # nothing changed
    r = client.post(f'/api/runs/{run}/revise', json={'request_id': rid(), 'stage': 's1', 'confirm_quote': 'yes discard'}, headers=alice)
    assert r.status_code == 200
    assert nxt(client, alice, run)['stage'] == 's1'
    assert client.get(f'/api/runs/{run}/stages/s2', headers=alice).json()['outputs'][0]['stale'] is True


def test_e16c_revise_one_unit(client, alice):
    run = new_run(client, alice)
    out(client, alice, run, 's1')
    out(client, alice, run, 's2', files=[FILE], summary={'units': {'s3': ['u1', 'u2']}})
    out(client, alice, run, 's3', unit='u1', quote=None, summary={'cost_cents': 5})
    out(client, alice, run, 's3', unit='u2', quote=None)
    r = client.post(f'/api/runs/{run}/revise', json={'request_id': rid(), 'stage': 's3', 'unit': 'u1'}, headers=alice)
    assert r.status_code == 200, r.text  # own paid output: no confirmation needed
    n = nxt(client, alice, run)
    assert n['stage'] == 's3' and n['units_open'] == ['u1']


def test_e16d_view_is_read_only(client, alice):
    run = new_run(client, alice)
    out(client, alice, run, 's1')
    r = client.get(f'/api/runs/{run}/stages/s1', headers=alice)
    assert r.status_code == 200 and len(r.json()['outputs']) == 1
    assert client.get(f'/api/runs/{run}/stages/nope', headers=alice).status_code == 422
    assert nxt(client, alice, run)['stage'] == 's2'


def test_e17_e18_idempotent_replay_and_conflict(client, alice):
    run = new_run(client, alice)
    req = rid()
    a = out(client, alice, run, 's1', request_id=req)
    b = out(client, alice, run, 's1', request_id=req)
    assert a.status_code == b.status_code == 201 and a.json() == b.json()
    assert len(client.get(f'/api/runs/{run}/stages/s1', headers=alice).json()['outputs']) == 1
    c = out(client, alice, run, 's1', request_id=req, quote='different')
    assert c.status_code == 409 and c.json()['code'] == 'REQUEST_CONFLICT'


def test_e19_concurrent_outputs_same_stage(client, alice):
    run = new_run(client, alice)
    results = []
    barrier = threading.Barrier(2)

    def go():
        barrier.wait()
        results.append(out(client, alice, run, 's1').status_code)

    threads = [threading.Thread(target=go) for _ in range(2)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert sorted(results) == [201, 409]
    assert len(client.get(f'/api/runs/{run}/stages/s1', headers=alice).json()['outputs']) == 1


def test_e20_e21_ownership_and_admin(client, alice, bob, admin):
    run = new_run(client, alice)
    assert client.get(f'/api/runs/{run}', headers=bob).status_code == 404
    assert out(client, bob, run, 's1').status_code == 404
    assert client.get(f'/api/runs/{run}', headers=admin).status_code == 200
    new_run(client, bob)
    assert len(client.get('/api/runs', headers=alice).json()) == 1
    assert len(client.get('/api/runs', headers=admin).json()) == 2


def test_e22_e23_close_requires_receipts_then_rejects_writes(client, alice):
    run = new_run(client, alice)
    out(client, alice, run, 's1')
    out(client, alice, run, 's2', files=[NOFILE])
    out(client, alice, run, 's3', unit=None, quote=None)  # no units declared → single output
    out(client, alice, run, 's4')
    r = client.post(f'/api/runs/{run}/close', json={'request_id': rid()}, headers=alice)
    assert r.status_code == 409 and r.json()['code'] == 'UPLOAD_INCOMPLETE' and r.json()['files'] == ['a.mp3']
    client.post(f'/api/runs/{run}/revise', json={'request_id': rid(), 'stage': 's2', 'confirm_quote': 'yes'}, headers=alice)
    out(client, alice, run, 's2', files=[FILE])
    out(client, alice, run, 's3', quote=None)
    out(client, alice, run, 's4')
    assert client.post(f'/api/runs/{run}/close', json={'request_id': rid()}, headers=alice).status_code == 200
    r = out(client, alice, run, 's4')
    assert r.status_code == 409 and r.json()['code'] == 'RUN_CLOSED'


def test_e24_e25_adopt(client, alice):
    run = new_run(client, alice)
    out(client, alice, run, 's1')
    r = client.post(f'/api/runs/{run}/adopt', json={'request_id': rid(), 'version': 'nope'}, headers=alice)
    assert r.status_code == 404 and r.json()['code'] == 'VERSION_UNKNOWN'
    r = client.post(f'/api/runs/{run}/adopt', json={'request_id': rid(), 'version': 'test2'}, headers=alice)
    assert r.status_code == 200
    n = nxt(client, alice, run)
    assert n['stage'] == 's0' and n['version'] == 'test2'


def test_e26_body_too_large(client, alice):
    run = new_run(client, alice)
    r = out(client, alice, run, 's1', summary={'blob': 'x' * 300_000})
    assert r.status_code == 413


def test_e27_unknown_stage(client, alice):
    run = new_run(client, alice)
    assert out(client, alice, run, 'zzz').status_code == 422


def test_e28_files_required(client, alice):
    run = new_run(client, alice)
    out(client, alice, run, 's1')
    r = out(client, alice, run, 's2', files=[])
    assert r.status_code == 422 and r.json()['code'] == 'FILES_REQUIRED'


def test_e29_defect(client, alice):
    run = new_run(client, alice)
    r = client.post(f'/api/runs/{run}/defects', json={'request_id': rid(), 'stage': 's1', 'error': '502 from provider', 'log_excerpt': 'trace'}, headers=alice)
    assert r.status_code == 201 and r.json()['ticket'] >= 1
    assert nxt(client, alice, run)['stage'] == 's1'


def test_e30_bad_or_expired_session(client, database):
    assert client.get('/api/runs').status_code == 401
    assert client.get('/api/runs', headers={'Authorization': 'Bearer nope'}).status_code == 401
    assert client.get('/api/runs', headers=seed_session(database, 'old', expired=True)).status_code == 401


def test_run_code_and_default_version(client, alice):
    r = client.post('/api/runs', json={'request_id': rid(), 'client': 'C'}, headers=alice)
    assert r.status_code == 201
    assert r.json()['code'].startswith('VW-') and r.json()['procedure_version'] == '3'   # the default since design/124 C3; versions 1 and 2 are retired (design/125)


def test_next_lists_paid_provider_for_per_unit_stage(client, alice):
    run = new_run(client, alice)
    out(client, alice, run, 's1')
    out(client, alice, run, 's2', files=[FILE], summary={'units': {'s3': ['u1']}})
    n = nxt(client, alice, run)
    assert n['paid'] == 'fakeanalysis' and n['needs_acceptance'] is False


def test_output_answer_carries_next_and_a_replay_returns_the_same(client, alice):
    """design/34 1.15"""
    run = new_run(client, alice)
    r = out(client, alice, run, 's1', request_id='fixed-request-1')
    assert r.status_code == 201 and r.json()['next']['stage'] == 's2'
    again = out(client, alice, run, 's1', request_id='fixed-request-1')
    assert again.status_code == 201 and again.json()['next']['stage'] == 's2'   # the receipt replays the stored answer, next included
    assert nxt(client, alice, run)['stage'] == 's2'


def test_partial_client_name_resolves_only_when_unique(client, alice):
    """design/34 1.17 and 1.5"""
    r = client.post('/api/runs', json={'request_id': rid(), 'client': 'textiles', 'procedure_version': 'test'}, headers=alice)
    assert r.status_code == 201 and r.json()['client'] == 'VK Textiles' and r.json()['client_runs'] == []
    r = client.post('/api/runs', json={'request_id': rid(), 'client': 'v', 'procedure_version': 'test'}, headers=alice)
    assert r.status_code == 422 and r.json()['code'] == 'CLIENT_UNKNOWN' and r.json()['candidates'] == ['VK', 'VK Textiles']
    r = client.post('/api/runs', json={'request_id': rid(), 'client': 'nobody', 'procedure_version': 'test'}, headers=alice)
    assert r.status_code == 422 and r.json()['candidates'] == []


def test_create_answer_carries_last_brief_and_client_rules(client, alice):
    """design/37 2.2, 2.3: null and empty on a client's first film."""
    r = client.post('/api/runs', json={'request_id': rid(), 'client': 'C', 'procedure_version': 'test'}, headers=alice)
    assert r.status_code == 201 and r.json()['last_brief'] is None and r.json()['client_rules'] == [] and r.json()['last_voice'] is None   # design/39 4.2


def test_effective_rules_minus_waivers_plus_learned(client, alice, database):
    """design/37 2.7: brief rules, waived flags dropped by matching inside the rule text, learned rules added; no waivers before analysis."""
    import psycopg
    from psycopg.rows import dict_row
    from psycopg.types.json import Jsonb
    from app import core
    run_id = new_run(client, alice)
    out(client, alice, run_id, 's1', summary={'production': {'brand_and_safety_rules': ['PPE required on site', 'No competitor logos']}})
    with psycopg.connect(database, row_factory=dict_row) as conn:
        run = conn.execute('select * from vw2_runs where id=%s', (run_id,)).fetchone()
        outputs = [dict(o, stage='brief') for o in core.current_outputs(conn, run_id)]   # the test procedure has no brief stage; treat s1 as it
        rules = core.effective_rules(conn, run, outputs)
        assert rules['brief_rules'] == ['PPE required on site', 'No competitor logos'] and rules['waived_flags'] == [] and rules['learned'] == []
        assert rules['effective'] == ['PPE required on site', 'No competitor logos']
        conn.execute("insert into vw2_client_rules(client_id, rule, source_run) values (%s, 'Rejected option #1: no close-ups', 'VW-0')", (run['client_id'],))
        conn.execute("insert into vw2_jobs(run_id, stage, unit, provider, request, request_id) values (%s, 'analysis', 'clip1', 'gemini', %s, gen_random_uuid())",
                     (run_id, Jsonb({'kind': 'analysis', 'policy': {'camera_audio': 'allowed', 'waived_risk_flags': ['ppe']}})))
        conn.commit()
        rules = core.effective_rules(conn, run, outputs)
        assert rules['waived_flags'] == ['ppe'] and rules['brief_effective'] == ['No competitor logos']
        assert rules['effective'] == ['No competitor logos', 'Rejected option #1: no close-ups'] and rules['learned'][0]['source_run'] == 'VW-0'


def test_open_defect_stops_writes_until_fixed(client, alice, database):
    """design/48 O.2: a write on a run with an open defect is refused; next names the defect; fixed → writes again."""
    run = client.post('/api/runs', json={'request_id': rid(), 'title': 'd', 'client': 'c-vk'}, headers=alice).json()['id']
    r = client.post(f'/api/runs/{run}/defects', json={'request_id': rid(), 'stage': 's1', 'error': 'boom', 'log_excerpt': ''}, headers=alice)
    assert r.status_code == 201
    ticket = r.json()['ticket']
    assert client.get(f'/api/runs/{run}/next', headers=alice).json()['open_defects'] == [ticket]
    r = client.post(f'/api/runs/{run}/output', json={'request_id': rid(), 'stage': 's1', 'files': [], 'summary': {}, 'accepted_quote': 'yes'}, headers=alice)
    assert r.status_code == 409 and r.json()['code'] == 'DEFECT_OPEN' and r.json()['defect'] == ticket
    r = client.post(f'/api/runs/{run}/defects', json={'request_id': rid(), 'stage': 's1', 'error': 'again', 'log_excerpt': ''}, headers=alice)
    assert r.status_code == 201   # a second ticket is still possible
    import psycopg
    with psycopg.connect(database) as c:
        c.execute("update vw2_defects set status='fixed' where run_id=%s", (run,))
    assert client.get(f'/api/runs/{run}/next', headers=alice).json()['open_defects'] == []
    r = client.post(f'/api/runs/{run}/output', json={'request_id': rid(), 'stage': 's1', 'files': [], 'summary': {}, 'accepted_quote': 'yes'}, headers=alice)
    assert r.status_code == 201
