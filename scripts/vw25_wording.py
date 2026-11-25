"""VW-25 issues 8 and 9 (SK, 25 Nov 2026): the visuals cards, in the served text.

In v3.json, each replaced (the replaced words are in server/retired-sentences.json):
- part `treatment`: the assistant no longer writes "the words under it" in a gap's entry: the server shows the narration under every gap line
  and its time in the film (issue 9, decision D7); `fits_why` is the reason, never the words themselves and never only that the operator asked;
- part `plan` (once for each kind of film): a drawing's parts are named with the words of the accepted `depicts` line, which the operator now
  reads beside the parts (issue 8).
Registered in scripts/c1_split_v3.py after d223. Exact anchors; applying twice changes nothing.
Run once: python scripts/vw25_wording.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'server' / 'procedures' / 'v3.json'

SPEC = 'and `view` with `view_reason` (give both; a section defaults to cutaway), checked on the drawing.'
PAIRS = [   # (part, the words before, the words now)
    ('treatment', 'has one entry per gap: `gap_id`; the words under it; `picture` in one line;', 'has one entry per gap: `gap_id`; `picture` in one line;'),
    ('treatment', '`fits_why` (why the picture fits the words and what the viewer understands better with it)',
     '`fits_why` (why the picture fits the words and what the viewer understands better with it: the reason, never the words themselves and never only that the operator asked)'),
    ('plan', SPEC, SPEC + ' In it, name the parts with the words of the accepted `depicts` line: the operator reads that line beside the parts.'),
]
RETIRED = ['has one entry per gap: `gap_id`; the words under it;']   # the server shows the words (issue 9)


def apply(prompt, parts):
    """The visuals text with these sentences: the common part is returned, the parts are changed in place. Applying twice changes nothing.
    A sentence stands once in the text of one kind of film and once for each kind in v3.json: every place is changed."""
    for where, old, new in PAIRS:
        part = next(p for p in parts if p['name'] == where)
        if old not in part['text'] and new not in part['text']:
            sys.exit('not applied: %s: not found: %s' % (where, old[:60]))
        part['text'] = part['text'].replace(new, old).replace(old, new)   # a place already changed is not changed twice
    return prompt


def _write(path, data, raw):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\r\n' if b'\r\n' in raw else '\n')   # the file keeps its line ends


def main():
    raw = P.read_bytes()
    d = json.loads(raw.decode('utf-8'))
    st = next(s for s in d['stages'] if s['name'] == 'visuals')
    st['prompt'] = apply(st['prompt'], st['parts'])
    _write(P, d, raw)
    rp = ROOT / 'server' / 'retired-sentences.json'
    raw = rp.read_bytes()
    r = json.loads(raw.decode('utf-8'))
    r['sentences'] += [s for s in RETIRED if s not in r['sentences']]
    _write(rp, r, raw)
    print('visuals: VW-25 issues 8 and 9')


if __name__ == '__main__':
    main()
