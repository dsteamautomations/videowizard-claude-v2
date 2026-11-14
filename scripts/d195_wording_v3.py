"""design/195 (SK, 14 Nov 2026): instruction version 3, the options: a flagged piece may be used; the operator sees the flags on the shot.
Exact anchor, found once; run once: python scripts/d195_wording_v3.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'server' / 'procedures' / 'v3.json'
OLD = 'never both in neighbouring shots.'
NEW = (OLD + ' A piece with `risk_flags` may be used: the operator sees the flags on the shot and decides. Of two pieces that fit equally, place the one without '
       'flags and give the flagged one as its alternative; a flagged piece goes first when it is the only good fit.')


def main():
    raw = P.read_bytes()
    d = json.loads(raw.decode('utf-8'))
    op = next(s for s in d['stages'] if s['name'] == 'options')
    if NEW not in op['prompt']:
        if op['prompt'].count(OLD) != 1:
            sys.exit('not applied: the anchor was not found once')
        op['prompt'] = op['prompt'].replace(OLD, NEW)
    P.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\r\n' if b'\r\n' in raw else '\n')   # the file keeps its line ends
    print('options: a flagged piece may be used')


if __name__ == '__main__':
    main()
