"""design/211, part C (what the operator sees and decides): instruction version 3, the visuals stage.

Changed here, in the part `picture-search` (the two anchors of part C in design/211 section 3.12, and no other part's): what the operator
finds on the page at each step of a reference round (the assistant's proposal on every thing with its reason, the doubtful things first,
the others accepted in one click that shows the total price, each footage picture answered on its own; then each set with the footage
picture beside it, both checks and the image model's notes, the first sets judged before the others are ordered); and that the chat, where
the page cannot be shown, asks the same lines with the same words. The plugin's command file has no sentence of part C: COMMANDS is empty.
The older ways: the two sentences replaced are retired by name (server/retired-sentences.json); none is kept.
Registered in scripts/c1_split_v3.py. A builder does not run it against the repository: the merger runs the three scripts once, after the
merge (design/211 section 3.0, rule 6). Exact anchors, each found once; run once: python scripts/d211c_wording_v3.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'server' / 'procedures' / 'v3.json'
R = ROOT / 'server' / 'retired-sentences.json'
CMD = ROOT / 'plugin' / 'commands' / 'vw.md'

PAIRS = [   # (where: 'common' or a part's name, the old sentence, the new one)
    ('picture-search',   # the page: the proposals, the doubtful first, each picture answered on its own; the sets with their checks; the first sets before the rest
     'The operator answers both steps on the page (`vw visuals page`), each in one visit: step 1; then, when the sets are back, `vw visuals page` again for the sets, '
     'and once more for each set made again. A paid answer on the page shows its price on its button: the click, then their done, is their word.',
     "The operator answers both steps on the page (`vw visuals page`), each in one visit. Step 1 shows your proposal for every thing, with its reason, the plan's "
     'description and the shots that use it: the doubtful things first, which the operator answers one by one; the others by kind, which they may accept in one click '
     "that shows the total price (never a doubtful thing, never a real person's likeness). Each footage picture is shown with what you saw and is answered on its own: "
     'use it, make a clean set from it (paid), not this picture (the next best is shown), or leave the thing out, with the shots that lose it. Step 2 shows each set '
     "with the footage picture beside it, the program's check, your look and the image model's notes; the first sets are judged before the others are ordered, on one "
     "button with its price; a set made again shows the set before and the operator's words. Run `vw visuals page` again whenever the answer says so. A paid answer "
     'on the page shows its price on its button: the click, then their done, is their word.'),
    ('picture-search',   # the chat: the same lines, the same words
     'In the chat, one at a time (`vw visuals next`, section E), only where the page cannot be shown.',
     'In the chat (`vw visuals next`, section E), only where the page cannot be shown: the same lines with the same words and the same prices, asked in turn; a '
     'picture is answered there with its own button too.'),
]
RETIRED = ['each in one visit: step 1; then, when the sets are back, `vw visuals page` again for the sets, and once more for each set made again',
           'In the chat, one at a time (`vw visuals next`, section E), only where the page cannot be shown']   # the sentences replaced, for server/retired-sentences.json
COMMANDS = []   # (the old sentence, the new one) in plugin/commands/vw.md: part C has none


def apply(prompt, parts):
    """The visuals text with this part's sentences: the common part is returned, the parts are changed in place. Applying twice changes nothing."""
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


def main():
    raw = P.read_bytes()
    d = json.loads(raw.decode('utf-8'))
    st = next(s for s in d['stages'] if s['name'] == 'visuals')
    st['prompt'] = apply(st['prompt'], st['parts'])
    P.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\r\n' if b'\r\n' in raw else '\n')   # the file keeps its line ends
    raw = R.read_bytes()
    r = json.loads(raw.decode('utf-8'))
    r['sentences'] += [s for s in RETIRED if s not in r['sentences']]
    R.write_text(json.dumps(r, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\r\n' if b'\r\n' in raw else '\n')
    raw = CMD.read_bytes()
    text = raw.decode('utf-8')
    for old, new in COMMANDS:
        if new not in text:
            if text.count(old) != 1:
                sys.exit('not applied: plugin/commands/vw.md: not found once: %s' % old)
            text = text.replace(old, new)
    CMD.write_bytes(text.encode('utf-8'))   # bytes: the file keeps its line ends
    print('visuals: design/211 part C, what the operator sees and decides at the references')
    print('words in the visuals stage:', sum(len(t.split()) for t in [st.get('prompt') or '', *(st.get('steps') or []), *(p['text'] for p in st.get('parts') or [])]))


if __name__ == '__main__':
    main()
