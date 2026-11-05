"""design/151 section 13 (SK, 4 Nov 2026): instruction version 3, the visuals stage's picture-search part: a set is three pictures, one per turn of one
conversation, with Google Search and Image Search on (gemini-nano-banana-2.1 draws one picture per turn). Exact anchor; run once: python scripts/d151b_wording_v3.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'server' / 'procedures' / 'v3.json'

OLD = "by the kept method: two to four separate pictures from real photographs with Google Search on ("
NEW = "by the kept method: three separate pictures, one per turn of one conversation, from real photographs with Google Search and Image Search on ("


MORE = [('picture-search', "(a thing with an approved frame is made from it; a size still unknown on such a thing is refused: measure first)",
         "(a thing with an approved footage picture gets no AI set: that picture is its reference and its golden picture)"),   # SK, 5 Nov 2026 (VW-18)
        ('later', "The golden picture (the ticked picture of a thing's set; a person's full-length front, which brings the face close-up into every shot by default) is what shots bind;",
         "The golden picture (a thing's approved footage picture, else the ticked picture of its set; a person's full-length front, which brings the face close-up into every shot by default) is what shots bind;")]


def apply_visuals(parts):
    """The same change on the split's parts (scripts/c1_split_v3.py --check)."""
    parts = {p['name']: p for p in parts}
    t = parts['picture-search']['text']
    if NEW not in t:
        if t.count(OLD) != 1:
            sys.exit('not applied: picture-search anchor not found once')
        parts['picture-search']['text'] = t.replace(OLD, NEW)
    for name, old, new in MORE:
        t = parts[name]['text']
        if new in t:
            continue
        if t.count(old) != 1:
            sys.exit(f'not applied: {name} anchor not found once: {old[:50]}')
        parts[name]['text'] = t.replace(old, new)


def main():
    d = json.loads(P.read_text(encoding='utf-8'))
    v = next(s for s in d['stages'] if s['name'] == 'visuals')
    apply_visuals(v['parts'])
    P.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    print('applied')


if __name__ == '__main__':
    main()
