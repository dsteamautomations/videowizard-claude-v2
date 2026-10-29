"""design/124 Change 6 (each treatment line accepted or sent back in chat) and Change 9 (`vw visuals plan-join`: the helpers' gaps joined into one plan)."""
import json

import vw
from test_visuals_cli import args, harness, run   # noqa: F401 (harness is a fixture)


# ---------- Change 6 ----------

def test_treatment_accept_and_send_back_post_the_lines(harness, monkeypatch, capsys):
    posted = []
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: posted.append((path, body)) or {'lines': {'G1': 'accepted'}, 'next': 'G2 still to accept.'})
    code, out, err = run(args(what='treatment', accept='direction,G1', quote='Yes to those.'), capsys)
    assert code == 0 and posted[-1][0].endswith('/visuals/treatment') and posted[-1][1] == {'accept': ['direction', 'G1'], 'send_back': [], 'notes': '', 'quote': 'Yes to those.'}
    assert 'G2 still to accept.' in err
    code, out, err = run(args(what='treatment', send_back='G2', notes='the water on the wall'), capsys)
    assert code == 0 and posted[-1][1]['send_back'] == ['G2'] and posted[-1][1]['notes'] == 'the water on the wall'
    n = len(posted)
    code, out, err = run(args(what='treatment', accept='G1'), capsys)   # a yes needs the operator's words
    assert code == 2 and '--quote' in out['message'] and len(posted) == n
    code, out, err = run(args(what='treatment', send_back='G2'), capsys)   # a send-back needs what to change
    assert code == 2 and '--notes' in out['message'] and len(posted) == n


# ---------- Change 9 ----------

def gap(gid, *eids):
    return {'gap_id': gid, 'intent': 'i', 'treatment_fit': 'f', 'scenes': [{'id': 'SC' + gid, 'shots': [{'id': 'S' + gid, 'element_ids': list(eids)}]}]}


def write_parts(ws, files):
    base = {'foundation': {'treatment': 't', 'appearance': 'a'}, 'elements': [{'id': 'E1', 'name': 'The mason'}], 'gaps': ['G1', 'G2', 'G3']}
    (ws / 'out' / 'plan-base.json').write_text(json.dumps(base), encoding='utf-8')
    (ws / 'out' / 'plan-gaps').mkdir()
    for name, body in files.items():
        (ws / 'out' / 'plan-gaps' / name).write_text(json.dumps(body), encoding='utf-8')


def joined(ws):
    return json.loads((ws / 'out' / 'visual-plan.json').read_text(encoding='utf-8'))


def test_plan_join_orders_the_gaps_and_merges_a_thing_added_by_two_helpers_once(harness, capsys):
    ws, _ = harness
    write_parts(ws, {'b.json': {'gaps': [gap('G3', 'E1', 'N9')], 'new_elements': [{'id': 'N9', 'name': 'Water drum '}]},
               'a.json': {'gaps': [gap('G1', 'E1', 'N2'), gap('G2', 'N2')], 'new_elements': [{'id': 'N2', 'name': 'water drum'}]}})
    code, out, err = run(args(what='plan-join', base='out/plan-base.json', gaps=['out/plan-gaps/']), capsys)
    plan = joined(ws)
    assert code == 0 and [g['gap_id'] for g in plan['gaps']] == ['G1', 'G2', 'G3'] and plan['foundation']['treatment'] == 't'
    assert [e['id'] for e in plan['elements']] == ['E1', 'N2']   # the drum once, by name
    assert plan['gaps'][2]['scenes'][0]['shots'][0]['element_ids'] == ['E1', 'N2']   # the second helper's id points at the one kept
    assert 'visual-plan.json' in err and 'vw visuals check' in err


def test_plan_join_refuses_a_missing_or_unknown_gap_by_name(harness, capsys):
    ws, _ = harness
    write_parts(ws, {'a.json': {'gaps': [gap('G1'), gap('G2')]}})
    code, out, err = run(args(what='plan-join', base='out/plan-base.json', gaps=['out/plan-gaps']), capsys)
    assert code == 2 and 'G3' in out['message'] and not (ws / 'out' / 'visual-plan.json').exists()
    (ws / 'out' / 'plan-gaps' / 'c.json').write_text(json.dumps(gap('G3')), encoding='utf-8')   # one gap alone in a file is read too
    (ws / 'out' / 'plan-gaps' / 'd.json').write_text(json.dumps(gap('G8')), encoding='utf-8')
    code, out, err = run(args(what='plan-join', base='out/plan-base.json', gaps=['out/plan-gaps']), capsys)
    assert code == 2 and 'G8' in out['message']
    (ws / 'out' / 'plan-gaps' / 'd.json').write_text(json.dumps(gap('G2')), encoding='utf-8')
    code, out, err = run(args(what='plan-join', base='out/plan-base.json', gaps=['out/plan-gaps']), capsys)
    assert code == 2 and 'G2' in out['message'] and 'twice' in out['message']
