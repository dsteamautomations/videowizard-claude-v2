"""design/124 C1 (Change 2): the visuals instructions split by step. Version 3 carries a common `prompt` and ordered `parts`; prepare puts the parts
into the package; version 2 (no parts) gives the package it always gave."""
import json
import subprocess
import sys
from pathlib import Path

from app import visuals_stage as VS
from test_visuals_stage_pure import RUN, USER, FakeConn, session, store_with

ROOT = Path(__file__).resolve().parents[2]
V3 = json.loads((ROOT / 'server' / 'procedures' / 'v3.json').read_text(encoding='utf-8'))
VIS = next(s for s in V3['stages'] if s['name'] == 'visuals')
NAMES = ['preparation', 'treatment', 'plan', 'picture-search', 'later']


def package_of(monkeypatch, stage):
    sess = session()
    store = store_with(sess)
    monkeypatch.setattr(VS, 'gaps_source', lambda store, outputs: sess['source'])
    monkeypatch.setattr(VS.core, 'stage_table', lambda v: [stage])
    monkeypatch.setattr(VS.core, 'effective_rules', lambda conn, run, outputs: [])
    out = VS.prepare(FakeConn([]), store, USER, {**RUN, 'procedure_version': '3'}, [])
    return json.loads(store.files[out['package']['key']])


def test_prepare_carries_the_parts_of_a_split_procedure(monkeypatch):
    pk = package_of(monkeypatch, {'name': 'visuals', 'prompt': VIS['prompt'], 'steps': VIS['steps'], 'parts': VIS['parts']})
    assert pk['prompt'] == VIS['prompt'] and [p['name'] for p in pk['parts']] == NAMES and pk['parts'] == VIS['parts']


def test_prepare_of_a_procedure_without_parts_has_no_parts(monkeypatch):
    pk = package_of(monkeypatch, {'name': 'visuals', 'prompt': 'whole text', 'steps': ['s']})
    assert 'parts' not in pk and pk['prompt'] == 'whole text'


def test_v3_is_split_common_plus_five_parts_and_each_step_names_its_part_file():
    assert [p['name'] for p in VIS['parts']] == NAMES and all(p['title'] and p['text'] for p in VIS['parts'])
    assert 'A. STOP AND ASK, NEVER GUESS' in VIS['prompt'] and '\n1. PREPARATION' not in VIS['prompt'] and '\n5. GENERATED' not in VIS['prompt']
    assert all(f'part-{n}.md' in VIS['prompt'] for n in NAMES)   # the reading guide
    starts = [p['text'].split('\n', 1)[0] for p in VIS['parts']]
    assert starts == ['1. PREPARATION', '2. TREATMENT', '3. THE DETAILED PLAN', '4. THE PICTURE SEARCH', '5. GENERATED REFERENCES, SHEETS AND GOLDEN PICTURES']
    assert '10. BRAND' in VIS['parts'][-1]['text']
    assert all(any(f'part-{n}.md' in s for n in NAMES) for s in VIS['steps'])
    for n, s in zip(NAMES[:4], VIS['steps'][:4]):
        assert f'part-{n}.md' in s


def test_v2_is_untouched():
    v2 = json.loads((ROOT / 'server' / 'procedures' / 'v2.json').read_text(encoding='utf-8'))
    assert all('parts' not in s for s in v2['stages'])


def test_the_split_script_reproduces_the_text_word_for_word():
    """scripts/c1_split_v3.py --check: common (without the reading guide) + the parts' texts == the Phase B prompt, and v3.json holds that split."""
    r = subprocess.run([sys.executable, str(ROOT / 'scripts' / 'c1_split_v3.py'), '--check'], cwd=ROOT, capture_output=True, text=True, encoding='utf-8')
    assert r.returncode == 0, r.stdout + r.stderr
