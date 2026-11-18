"""design/216 (18 Nov 2026): instruction version 3, the visuals stage: the sets screen and the VW-24 corrections.

One sentence, in the common part where the page is introduced: the assistant posts the page's `say` with the link exactly as it is (no
count and no summary of its own, finding B1), and says the page's `preparing` before `vw visuals page --fetch` fetches the pictures (B2).
No sentence is retired: the older wording of the link ("Open this page, answer each line, then tell me you are done:") lived in the
server's `how` (server/app/page_flow.py), not here. Registered in scripts/c1_split_v3.py after design/215's script. Exact anchors, each
found once; run once: python scripts/d216_wording_v3.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'server' / 'procedures' / 'v3.json'

PAIRS = [   # (where: 'common' or a part's name, the old sentence, the new one)
    ('common', 'each size asked once; one visit, then `vw visuals page --record`.',
     'each size asked once; one visit, then `vw visuals page --record`. With the link, say the page\'s `say` exactly as it is, with no count and no summary of your own; '
     'when `vw visuals page` first gives `preparing`, say that sentence as it is, then run `vw visuals page --fetch`.'),
]


def apply(prompt, parts):
    """The visuals text with this design's sentence: the common part is returned, the parts are changed in place. Applying twice changes nothing."""
    for where, old, new in PAIRS:
        part = None if where == 'common' else next(p for p in parts if p['name'] == where)
        text = prompt if part is None else part['text']
        if new in text:
            continue
        if text.count(old) != 1:
            sys.exit('not applied: %s: not found once: %s' % (where, old[:60]))
        text = text.replace(old, new)
        if part is None:
            prompt = text
        else:
            part['text'] = text
    return prompt


def before(stage):
    """The visuals stage as it read before this script."""
    st = json.loads(json.dumps(stage))
    for where, old, new in reversed(PAIRS):
        if where == 'common':
            st['prompt'] = st['prompt'].replace(new, old)
        else:
            part = next(p for p in st['parts'] if p['name'] == where)
            part['text'] = part['text'].replace(new, old)
    return st


def main():
    raw = P.read_bytes()
    d = json.loads(raw.decode('utf-8'))
    st = next(s for s in d['stages'] if s['name'] == 'visuals')
    st['prompt'] = apply(st['prompt'], st['parts'])
    P.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\r\n' if b'\r\n' in raw else '\n')   # the file keeps its line ends
    print('visuals: design/216')


if __name__ == '__main__':
    main()
