"""design/214 (18 Nov 2026): instruction version 3, the visuals stage: Claude checks the sets of a reference round; no model checks them.

What changed in the program is said here in the instruction's own sentences: each picture of a made set comes to the look with its check
list; the look answers every line of every picture from what it sees in the picture, never from the request or the notes, checks a fact
of the drawing against the drawing sheet, says "not checked" for a picture it could not open, and never passes a line it did not look at;
the operator reads that as the set's one check. The helper file (`plugin/agents/vw-set-look.md`) and the command file
(`plugin/commands/vw.md`) say the same. The older sentences are retired by name (server/retired-sentences.json). Registered in
scripts/c1_split_v3.py after design/213's script. Exact anchors, each found once; run once: python scripts/d214_wording_v3.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'server' / 'procedures' / 'v3.json'
R = ROOT / 'server' / 'retired-sentences.json'
AGENTS = ROOT / 'plugin' / 'agents'
CMD = ROOT / 'plugin' / 'commands' / 'vw.md'

PAIRS = [   # (where: 'common' or a part's name, the old sentence, the new one)
    ('picture-search',   # the added words: the check that judges by them is the look's
     'the check judges by them, and the operator reads them on the line.',
     'your check judges by them, and the operator reads them on the line.'),
    ('picture-search',   # the look answers each picture's check list
     'which the operator reads in place of the notes;',
     'which the operator reads in place of the notes; each picture comes with its check list (`lines`), and no model checks a set, the check is yours: answer every line of '
     'every picture, pass or fail, from what you see in the picture, never from the request or the notes, with one plain sentence for a fail; check a fact of the drawing '
     'against the drawing sheet given with the set; never pass a line you did not look at; a picture you could not open is `not_checked`, with why;'),
    ('picture-search',   # the rewrite reads the look's check
     'from their words, the check and your look:',
     'from their words, your check and your look:'),
    ('picture-search',   # what step 2 shows
     "the program's check, your look and your two lines on the image model's notes.",
     "your check, your look and your two lines on the image model's notes."),
]
RETIRED = ["the program's check, your look and your two lines",   # the sentences replaced, for server/retired-sentences.json
           "and the result of the program's check",
           'from their words, the check and your look',
           'the check judges by them']
COMMANDS = [   # (the old sentence, the new one) in plugin/commands/vw.md
    ('(its `how` gives the points to judge by and the shape of the file;',
     '(its `how` gives the points to judge by and the shape of the file, and each picture comes with its check list: answer every line of every picture from what you see in it;'),
]
HELPERS = [   # (the file under plugin/agents, the old sentence, the new one)
    ('vw-set-look.md',
     'and records its looks and a recommendation',
     "answers every line of each picture's check list, and records its looks and a recommendation"),
    ('vw-set-look.md',
     "and the result of the program's check, the image model's notes,",
     "and its check list (`lines`), the image model's notes,"),
    ('vw-set-look.md',
     'never required, and never a fault.',
     'never required, and never a fault.\n\nThen check each picture against its own list (`lines`). No model checks a set: this check is yours, and the operator reads it as '
     'the check of the set. Answer every line of every picture, `pass` true or false, from what you see in the picture, never from the request or the notes. A fail gets one '
     'plain sentence of what you saw (`seen`); so does a pass of a line marked `say` (a fact of the drawing: a few words). Check a fact of the drawing against the drawing '
     'sheet among the inputs. Never pass a line you did not look at. A picture you could not open gets `"not_checked": "<why>"` in place of its verdict and its lines.'),
    ('vw-set-look.md',
     'one row per set, and in it one row per picture.',
     "one row per set, and in it one row per picture, with one answer for each line of that picture's list, by its `id`."),
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
    for where, old, new in reversed(PAIRS):
        part = next(p for p in st['parts'] if p['name'] == where)
        part['text'] = part['text'].replace(new, old)
    return st


def before_helper(name, text):
    """A helper file of plugin/agents as it read before this script."""
    for file, old, new in reversed(HELPERS):
        if file == name:
            text = text.replace(new, old)
    return text


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
    for name in sorted({h[0] for h in HELPERS}):
        raw = (AGENTS / name).read_bytes()
        end = '\r\n' if b'\r\n' in raw else '\n'
        text = raw.decode('utf-8').replace('\r\n', '\n')
        for file, old, new in HELPERS:
            if file == name and new not in text:
                if text.count(old) != 1:
                    sys.exit('not applied: plugin/agents/%s: not found once: %s' % (name, old[:60]))
                text = text.replace(old, new)
        (AGENTS / name).write_bytes(text.replace('\n', end).encode('utf-8'))   # bytes: the file keeps its line ends
    text = CMD.read_bytes().decode('utf-8')
    for old, new in COMMANDS:
        if new not in text:
            if text.count(old) != 1:
                sys.exit('not applied: plugin/commands/vw.md: not found once: %s' % old[:60])
            text = text.replace(old, new)
    CMD.write_bytes(text.encode('utf-8'))   # bytes: the file keeps its line ends
    print('visuals: design/214')
    print('words in the visuals stage:', sum(len(t.split()) for t in [st.get('prompt') or '', *(st.get('steps') or []), *(p['text'] for p in st.get('parts') or [])]))


if __name__ == '__main__':
    main()
