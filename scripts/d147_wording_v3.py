"""design/147 (the brand-generic library, SK 3 Nov 2026): instruction version 3, three short pointers (the tool's own answers carry the how, and
the analysis and options texts have a word budget, design/125). Exact anchors; run once: python scripts/d147_wording_v3.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'server' / 'procedures' / 'v3.json'
CHANGES = [   # (stage, step index, old, new)
    ('analysis', 3, 'When every clip is retained or excluded, `vw next` moves to options.',
     'When every clip is retained or excluded, `vw library show` (the brand-generic question), then `vw next` moves to options.'),
    ('analysis', 1, 'Then tell the operator the footage languages (`languages` in status); never assume English.',
     'Tell the operator the footage languages from status.'),
    ('options', 3, '`vw options join-second-look`, `check` again, then `vw options propose --file out/options.json`.',
     '`vw options join-second-look`, `check` again, then `vw options library` (the library round; its answer says how to propose), `check` again, then `vw options propose --file out/options.json`.'),
]


def main():
    d = json.loads(P.read_text(encoding='utf-8'))
    st = {s['name']: s for s in d['stages']}
    for stage, n, old, new in CHANGES:
        text = st[stage]['steps'][n]
        if new in text:
            continue
        if text.count(old) != 1:
            sys.exit(f'not applied: {stage} step {n}: anchor not found once')
        st[stage]['steps'][n] = text.replace(old, new)
    P.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    print('applied')


if __name__ == '__main__':
    main()
