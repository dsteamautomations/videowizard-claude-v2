"""4e, parts 1 and 2 (SK, 26 Nov 2026: "Approve as written"): the sizes, materials and graphic specs in the chat, in the served text.

In v3.json, each replaced (the replaced words are in server/retired-sentences.json):
- the common part, the card: the card is the way back for the sizes, materials and graphic specs too; two or more specs that wait come on one
  card (until then the card was for the treatment's lines and the plan's gaps only);
- part `plan` (once for each kind of film): in the chat two or more specs come on one card (until then: one at a time; that way is
  kept for one spec alone and for `vw visuals next --one`);
- part `plan` (once for each kind of film): a spec whose sizes still wait for their research is warned in the plan and stays with the
  assistant, the server naming what is missing; it is shown to the operator once this is done (until then: "warned in the plan and
  refused when the spec is approved"; retired).
Nothing in the plugin changes. Registered in scripts/c1_split_v3.py after a1. Exact anchors; applying twice changes nothing.
Run once: python scripts/specs_card_wording.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'server' / 'procedures' / 'v3.json'

PAIRS = [   # (the common part or a part, the words before, the words now)
    ('common', "The card is the way back for the treatment and the plan, only where the page cannot be shown. There, for the treatment's lines and for the plan's gaps, the server answers",
     "The card is the way back for the treatment, the plan and the sizes, materials and graphic specs, only where the page cannot be shown. "
     "There, for the treatment's lines, for the plan's gaps and for two or more specs, the server answers"),
    ('plan', 'are warned in the plan (`spec_unresearched`) and refused when the spec is approved;',
     'are warned in the plan (`spec_unresearched`); the server keeps that spec with you and names what is missing: it is shown to the operator once this is done;'),
    ('plan', 'one visit, then `vw visuals page --record`); in the chat, one at a time (`vw visuals next`), only where the page cannot be shown. A correction they send is in `spec_corrections`',
     'one visit, then `vw visuals page --record`); in the chat (`vw visuals next`; two or more come on one card), only where the page cannot be shown. '
     'A correction they send is in `spec_corrections`'),
]
RETIRED = ['The card is the way back for the treatment and the plan,', "for the treatment's lines and for the plan's gaps", 'and refused when the spec is approved',
           'one visit, then `vw visuals page --record`); in the chat, one at a time']


def apply(prompt, parts):
    """The visuals text with these sentences: the common part is returned, the parts are changed in place. Applying twice changes nothing.
    A part's sentence stands once in the text of one kind of film and once for each kind in v3.json: every place is changed."""
    for where, old, new in PAIRS:
        part = next((p for p in parts if p['name'] == where), None)
        text = part['text'] if part else prompt
        if old not in text and new not in text:
            sys.exit('not applied: %s: not found: %s' % (where, old[:60]))
        text = text.replace(new, old).replace(old, new)   # a place already changed is not changed twice
        if part:
            part['text'] = text
        else:
            prompt = text
    return prompt


def before(stage):
    """The visuals stage as it read before this script (for the tests of the earlier scripts)."""
    st = json.loads(json.dumps(stage))
    for where, old, new in PAIRS:
        part = next((p for p in st['parts'] if p['name'] == where), None)
        if part:
            part['text'] = part['text'].replace(new, old)
        else:
            st['prompt'] = st['prompt'].replace(new, old)
    return st


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
    print('visuals: two or more specs on one card in the chat; a spec that is not ready stays with the assistant')


if __name__ == '__main__':
    main()
