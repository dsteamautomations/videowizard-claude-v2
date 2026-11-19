"""design/220 (SK, 19 Nov 2026): instruction version 3, the visuals stage: the first sets are judged by Claude's look, and the look decides
whether the others follow.

One sentence in the picture-search part, after "… when the others are ordered (`then`): pass it on as it is.": the operator's word for the other sets is
needed only when a first set did not pass; when the look says "use" for every first set, the server orders the others itself as it records
the looks. No sentence is replaced: the older way (the others on the operator's word) stays as the path when a first set did not pass, so
nothing is added to server/retired-sentences.json. Registered in scripts/c1_split_v3.py after design/218b's script. An exact anchor, found
once; run once: python scripts/d220_wording_v3.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'server' / 'procedures' / 'v3.json'

PAIRS = [   # (where: 'common' or a part's name, the old sentence, the new one)
    ('picture-search', 'when the others are ordered (`then`): pass it on as it is.',
     'when the others are ordered (`then`): pass it on as it is. The operator\'s word for the others is needed only when a first set did not pass: when your look says "use" for '
     'every first set, the server orders the others itself as it records the looks, with no question to the operator, and its answer says so (`then`); when a first set '
     "is not passed, could not be made or could not be checked, the others wait for the operator's word and that set is shown first, with your look's words."),
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
    print('visuals: design/220')


if __name__ == '__main__':
    main()
