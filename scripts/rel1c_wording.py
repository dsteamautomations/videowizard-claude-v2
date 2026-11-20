"""Release 1, the critic's point 10 (20 Nov 2026): three sentences of the served text that contradicted one click (B1) and step 7's two
batches of cards (D2).

In v3.json, part `later`, each replaced (the replaced words are in server/retired-sentences.json):
- the held drawing's card: "select it anyway with their reason" becomes one click, recorded as selected against the check;
- a drawing of the older drawn route whose must lines still fail: "`select` needs `--notes` saying why it is taken" becomes: `select` takes
  it all the same and records that it went against the check;
- "Nothing of step 7 is asked one by one" becomes "No finished take is asked one by one" (the cards before a take are asked in the chat,
  in two batches).
Registered in scripts/c1_split_v3.py after rel1b. Exact anchors, each found once; applying twice changes nothing.
Run once: python scripts/rel1c_wording.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'server' / 'procedures' / 'v3.json'

HELD = 'select it anyway with their reason, reject it (rebuilt from round 1)'   # design/221 row 18
HELD_NEW = 'select it anyway (one click, recorded as selected against the check), reject it (rebuilt from round 1)'
NOTES = 'a drawing whose must lines still fail is held: `select` needs `--notes` saying why it is taken, else reject it with what to change;'   # design/117
NOTES_NEW = ('a drawing whose must lines still fail is held: `select` takes it all the same and records that it went against the check, else reject it with '
             'what to change;')
ONE = 'Nothing of step 7 is asked one by one:'   # design/222
ONE_NEW = 'No finished take is asked one by one:'
PAIRS = [('later', HELD, HELD_NEW), ('later', NOTES, NOTES_NEW), ('later', ONE, ONE_NEW)]   # (the part, the sentence as it is, the sentence as it becomes)

RETIRED = ['select it anyway with their reason', '`select` needs `--notes` saying why it is taken', 'Nothing of step 7 is asked one by one']


def apply(prompt, parts):
    """The visuals text with these sentences: the common part is returned, the parts are changed in place. Applying twice changes nothing."""
    for where, old, new in PAIRS:
        part = next(p for p in parts if p['name'] == where)
        if new in part['text']:
            continue
        if part['text'].count(old) != 1:
            sys.exit('not applied: %s: not found once: %s' % (where, old[:60]))
        part['text'] = part['text'].replace(old, new)
    return prompt


def before(stage):
    """The visuals stage as it read before this script."""
    st = json.loads(json.dumps(stage))
    for where, old, new in reversed(PAIRS):
        part = next(p for p in st['parts'] if p['name'] == where)
        part['text'] = part['text'].replace(new, old)
    return st


def main():
    raw = P.read_bytes()
    d = json.loads(raw.decode('utf-8'))
    st = next(s for s in d['stages'] if s['name'] == 'visuals')
    st['prompt'] = apply(st['prompt'], st['parts'])
    P.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\r\n' if b'\r\n' in raw else '\n')   # the file keeps its line ends
    rp = ROOT / 'server' / 'retired-sentences.json'
    r = json.loads(rp.read_text(encoding='utf-8'))
    r['sentences'] += [s for s in RETIRED if s not in r['sentences']]
    rp.write_text(json.dumps(r, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    print('visuals: a held drawing and `select` are one click; no finished take is asked one by one')


if __name__ == '__main__':
    main()
