"""design/132: the editor's package first, then the assembly, in instruction version 3 (the assembly and delivery steps).
Writes server/procedures/v3.json. A second run fails (the old text is gone). Version 2 is not touched."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'server' / 'procedures' / 'v3.json'

PACKAGE = ("First the editor's package (design/115, design/132): once every gap is recorded, `vw delivery bundle` (the narration, the camera cuts by name "
           "and time, the raw AI files, the timeline, the EDL, the captions, the cut list and the relink list). The server refuses the assembly without it, "
           "and again after a gap is recorded anew: run it again. On the operator's computer (Windows or Mac): `vw pull <code>`, `vw delivery check`, "
           "`vw delivery download` (no camera copies by default), then `vw delivery open --originals \"<folder>\"` on Resolve Studio. Then the assembly below, the proof copy.")
OLD_BUNDLE = "`vw delivery bundle` writes the package manifest (approved film,"
NEW_BUNDLE = "`vw delivery bundle` again writes the full package with the approved film (approved film,"


def apply_steps(stages):
    """For c1_split_v3.py --check: the assembly gains the package as its first step; the delivery's bundle is the second, full one."""
    st = {s['name']: s for s in stages}
    asm, dl = st['assembly']['steps'], st['delivery']['steps']
    assert asm[0].startswith('`vw assembly prepare`'), 'assembly step 0'
    assert dl[0].count(OLD_BUNDLE) == 1, 'delivery step 0'
    asm.insert(0, PACKAGE)
    dl[0] = dl[0].replace(OLD_BUNDLE, NEW_BUNDLE)


def main():
    d = json.loads(P.read_text(encoding='utf-8'))
    try:
        apply_steps(d['stages'])
    except AssertionError as exc:
        sys.exit(f'not applied: {exc}')
    P.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    print('assembly and delivery steps written')


if __name__ == '__main__':
    main()
