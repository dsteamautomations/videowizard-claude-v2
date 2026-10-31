"""Defect 37 (VW-12, 31 Oct 2026): a spec correction is folded into the plan's element and the plan proposed again; the accepted plan
was not on the operator's machine and no command brought it. `vw visuals plan` writes the server's current plan to out/visual-plan.json."""
import json

from test_visuals_cli import args, harness, run  # noqa: F401  (the fixture rides along)
import vw


def test_plan_writes_the_current_plan_to_out(harness, monkeypatch, capsys):
    ws, _ = harness
    got = {}
    plan = {'foundation': {'treatment': 't'}, 'elements': [{'id': 'brick', 'material_spec': {'dimensions': []}}], 'gaps': []}
    monkeypatch.setattr(vw, 'call', lambda method, path, **kw: (got.update(method=method, path=path) or {'version': 1, 'plan_digest': 'd', 'plan': plan}))
    code, out, err = run(args(what='plan'), capsys)
    assert code == 0 and got['method'] == 'GET' and got['path'].endswith('/visuals/plan')
    assert json.loads((ws / 'out' / 'visual-plan.json').read_text(encoding='utf-8')) == plan
    assert 'propose --file out/visual-plan.json' in err and out['file'].endswith('visual-plan.json')


def test_plan_takes_no_flags():
    assert vw.visuals_flags_refused(args(what='plan', file='x.json'))
