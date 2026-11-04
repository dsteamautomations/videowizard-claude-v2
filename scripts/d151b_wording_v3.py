"""design/151 section 13 (SK, 4 Nov 2026): instruction version 3, the visuals stage's picture-search part: a set is three pictures, one per turn of one
conversation, with Google Search and Image Search on (gemini-nano-banana-2.1 draws one picture per turn). Exact anchor; run once: python scripts/d151b_wording_v3.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'server' / 'procedures' / 'v3.json'

OLD = "by the kept method: two to four separate pictures from real photographs with Google Search on ("
NEW = "by the kept method: three separate pictures, one per turn of one conversation, from real photographs with Google Search and Image Search on ("


def apply_visuals(parts):
    """The same change on the split's parts (scripts/c1_split_v3.py --check)."""
    parts = {p['name']: p for p in parts}
    t = parts['picture-search']['text']
    if NEW in t:
        return
    if t.count(OLD) != 1:
        sys.exit('not applied: picture-search anchor not found once')
    parts['picture-search']['text'] = t.replace(OLD, NEW)


def main():
    d = json.loads(P.read_text(encoding='utf-8'))
    v = next(s for s in d['stages'] if s['name'] == 'visuals')
    apply_visuals(v['parts'])
    P.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    print('applied')


if __name__ == '__main__':
    main()
