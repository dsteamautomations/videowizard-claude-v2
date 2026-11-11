"""The checklist of layer 1: controls.json lists every row of the inventory (page-facts section 3) with its test. A row with no test,
or a test with no row, fails here."""
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROWS = json.loads((HERE / 'controls.json').read_text(encoding='utf-8'))


def by_id():
    found = {}
    for f in sorted(HERE.glob('test_controls_*.py')):
        for m in re.finditer(r"@ident\('([^']+)'\)\ndef (\w+)", f.read_text(encoding='utf-8')):
            found.setdefault(m.group(1), []).append(f'{f.name}::{m.group(2)}')
    return found


def test_every_inventory_row_has_one_test():
    found = by_id()
    missing = [f"{r['id']} ({r['control']})" for r in ROWS if len(found.get(r['id'], [])) != 1]
    assert not missing, f'inventory rows without exactly one test: {missing}'
    wrong = [r['id'] for r in ROWS if found[r['id']] != [r['test']]]
    assert not wrong, f'controls.json names another test than the one that carries the id: {wrong}'
    extra = sorted(set(found) - {r['id'] for r in ROWS})
    assert not extra, f'tests with an id that is not a row of controls.json: {extra}'


def test_the_checklist_is_the_whole_inventory():
    """Rows 1 to 105 (79 is written 79a in the inventory) and the five automatic behaviours 106 to 110."""
    want = [str(n) if n != 79 else '79a' for n in range(1, 111)]
    assert [r['row'] for r in ROWS] == want
    assert len({r['id'] for r in ROWS}) == len(ROWS)
