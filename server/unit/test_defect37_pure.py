"""Defect 37: the server gives back the current visual plan (for `vw visuals plan`), and version 3's plan part folds a spec correction
into out/visual-plan.json and proposes again, never with the retired `planning revise`."""
import json
from pathlib import Path

from app import visuals_stage as VS

V3 = json.loads((Path(__file__).resolve().parents[1] / 'procedures' / 'v3.json').read_text(encoding='utf-8'))


def test_plan_of_returns_the_current_plan_with_its_version(monkeypatch):
    session = {'current': 'd2', 'versions': [{'version': 1, 'plan_digest': 'd1', 'file': {'key': 'k1'}}, {'version': 2, 'plan_digest': 'd2', 'file': {'key': 'k2'}}]}
    monkeypatch.setattr(VS, 'session_of', lambda store, run, outputs: session)
    monkeypatch.setattr(VS, 'load_json', lambda store, k: {'document': {'gaps': [], 'k': k}})
    out = VS.plan_of(None, {'id': 'r'}, [])
    assert out == {'version': 2, 'plan_digest': 'd2', 'plan': {'gaps': [], 'k': 'k2'}}


def test_the_plan_part_no_longer_names_planning_revise():
    st = next(s for s in V3['stages'] if s['name'] == 'visuals')
    part = next(p for p in st['parts'] if p['name'] == 'plan')['text']
    assert 'planning revise' not in part and 'fold into out/visual-plan.json (`vw visuals plan`), propose again' in part
