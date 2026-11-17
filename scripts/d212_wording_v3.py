"""design/212 (SK, 17 Nov 2026): instruction version 3, the visuals stage: step 1 of the references in its new layout.

What changed in the program is said here in the instruction's own sentences: step 1 shows one thing at a time beside a list in five groups
(the routine things, accepted together after a look; with footage pictures; no picture and a set suggested; no picture and suggested to leave
out; no action needed), no longer "the doubtful first, the others by kind"; the buttons follow the case of the thing (Approve, Make a set,
Minor corrections, Upload my own, Leave out); a footage picture has a Keep tick, no button of its own; a person the footage does not show
is not asked and gets a set at done; and no cost is shown at the references, on the page or in the chat (the owner's decision: "remove all
the places where the cost is mentioned"), so the sentences that told of a price on a button are replaced. The older sentences are retired
by name (server/retired-sentences.json). Registered in scripts/c1_split_v3.py after design/211's four scripts. Exact anchors, each found
once; run once: python scripts/d212_wording_v3.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'server' / 'procedures' / 'v3.json'
R = ROOT / 'server' / 'retired-sentences.json'
CMD = ROOT / 'plugin' / 'commands' / 'vw.md'

PAIRS = [   # (where: 'common' or a part's name, the old sentence, the new one)
    ('picture-search',   # the five groups, the case's buttons, the person not in the footage
     "Step 1 shows your proposal for every thing, with its reason, the plan's description and the shots that use it: the doubtful things first, which the operator answers "
     "one by one; the others by kind, which they may accept in one click that says how many sets are made first, with their price, and that the others are asked after "
     "(never a doubtful thing, never a real person's likeness).",
     "Step 1 shows one thing at a time beside the list of things, each with your proposal, its reason, the plan's description and the shots that use it, in five groups in "
     "this order: the routine things, which they may look at and accept together in one click that says how many sets are made first and that the others are asked after "
     "(never a doubtful thing, never a real person's likeness); the things with footage pictures; the things with no picture for which a set is suggested; those suggested "
     "to leave out; and the people the footage does not show, who need no answer: each gets a set from the description at done, and may be given words or their own photo. "
     "The buttons follow the case of the thing: Approve, Make a set, Minor corrections (with their words), Upload my own, Leave out."),
    ('picture-search',   # a picture has a tick, no button of its own
     'Each footage picture is shown with what you saw and is answered on its own: use it, make a clean set from it (paid), not this picture (the next best is shown), or '
     'leave the thing out, with the shots that lose it.',
     "Each footage picture is shown with what you saw and a Keep tick: an unticked picture is not this picture (the next best is then shown and the thing comes back once), "
     "a ticked closest picture is taken as the thing's own; leaving the thing out names the shots that lose it."),
    ('picture-search',   # step 2: no price on the button
     'the first sets are judged before the others are ordered, on one button with its price;',
     'the first sets are judged before the others are ordered, on one button;'),
    ('picture-search',   # no cost at the references
     'A paid answer on the page shows its price on its button: the click, then their done, is their word.',
     "No cost is shown at the references, on the page or in the chat (the owner's decision of 17 Nov 2026): the server keeps the film's limit and records every spend, and "
     "only a refusal after done names the limit; never add a price yourself. The click, then their done, is their word."),
    ('picture-search',   # the chat: the same order, no prices; the person not in the footage is not asked
     'the same lines with the same words and the same prices, asked in turn;',
     'the same lines in the same order with the same words, asked in turn (a person the footage does not show is not asked: the first question says how many get a set);'),
]
RETIRED = ['the doubtful things first, which the operator answers one by one',   # the sentences replaced, for server/retired-sentences.json
           'the others by kind, which they may accept in one click',
           'A paid answer on the page shows its price on its button',
           'a paid answer shows its price on its button',
           'the same lines with the same words and the same prices',
           'on one button with its price']
COMMANDS = [   # (the old sentence, the new one) in plugin/commands/vw.md
    ('(a paid answer shows its price on its button;', '(no cost is shown at the references, on the page or in the chat;'),
]


def apply(prompt, parts):
    """The visuals text with this design's sentences: the common part is returned, the parts are changed in place. Applying twice changes nothing."""
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
    """The visuals stage as it read before this script: for the tests of the scripts it follows, whose own sentences it changes."""
    st = json.loads(json.dumps(stage))
    for where, old, new in PAIRS:
        part = next(p for p in st['parts'] if p['name'] == where)
        part['text'] = part['text'].replace(new, old)
    return st


def before_commands(text):
    """plugin/commands/vw.md as it read before this script."""
    for old, new in COMMANDS:
        text = text.replace(new, old)
    return text


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
    print('visuals: design/212')
    print('words in the visuals stage:', sum(len(t.split()) for t in [st.get('prompt') or '', *(st.get('steps') or []), *(p['text'] for p in st.get('parts') or [])]))


if __name__ == '__main__':
    main()
