"""design/211, the review of 17 Nov 2026 (three critics): instruction version 3, the visuals stage.

What the review changed in the program is said here in the instruction's own sentences: the step list names the rebuilt way (the digest,
the looks, each row a proposal), no longer the word match and the unseen frame; the views by kind (a material has its own; a way of working
shows the action or the change, hands and a tool allowed, never required; a default view the plan already shows is left out); the order
of authority in a request; a helper is given its group, its ids, the run folder's path and the tool's command line; the judging points
and the shape of the looks file come with the listing (`how`); the proposals say which sets are made first; a make that returned no
picture is not counted; a round file sent again brings back only what is new or changed in the plan; a set is never made by the image
command. The older sentences are retired by name (server/retired-sentences.json). Registered in scripts/c1_split_v3.py after the three
parts of design/211. Exact anchors, each found once; run once: python scripts/d211d_wording_v3.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'server' / 'procedures' / 'v3.json'
R = ROOT / 'server' / 'retired-sentences.json'
CMD = ROOT / 'plugin' / 'commands' / 'vw.md'

STEP = (3,   # the step list: the rebuilt way (review, N3)
        '`vw visuals elements`; `vw visuals frame --file`; out/reference-round.json; `vw visuals round`; the operator answers the round\'s two steps on the page '
        '(`vw visuals page`), `vw visuals status --wait 900` between them, writing the drafts meanwhile;',
        '`vw visuals digest`; each thing found in the footage by its looks (`vw visuals trial`, `vw visuals look`); out/reference-round.json, each row a proposal; '
        '`vw visuals round`; then what each answer says (`then`): the operator answers step 1 on the page (`vw visuals page`), `vw visuals status --wait 900` while sets are '
        'made, your looks at the made sets (`vw visuals round --looks`), the operator judges the sets on the page; writing the drafts meanwhile;')

PAIRS = [   # (where: 'common' or a part's name, the old sentence, the new one)
    ('picture-search',   # a helper is given what it needs to work the first time (review, N10)
     'With more than five things start `vw-reference-finder` helpers, about five things each, up to six at a time, each given a group name and its thing ids;',
     "With more than five things start `vw-reference-finder` helpers, about five things each, up to six at a time, each given a group name, its thing ids, the run folder's path "
     "and the tool's command line;"),
    ('picture-search',   # the views by kind (review, C1, S7, S10)
     'an object or a material whole, as the film uses it, and its telling detail (no person; a hand only in use); a place whole, from the other side, and its fixed things; '
     'a way of working at its key moment, its result, and the tool meeting the material (hands and forearms, no face);',
     'an object whole, as the film uses it, and its telling detail (no person; in use, the hand and the material the description names); a material as a surface, as the film '
     'uses it, and very close; a place whole, from the other side, and its fixed things; a way of working as the action or the change at its key moment, its result, and close '
     'on where it happens (hands and a tool allowed where the description names them, never required; no face); a default view that a view of the plan already shows is left out; '
     'lettering only where the description names it;'),
    ('picture-search',   # the looks: the judging points and the file's shape come with the listing (review, N2, S16)
     'with more than five sets start `vw-set-look` helpers, about five sets each;',
     "its `how` gives the points to judge by (against the footage picture, the approved drawing, the plan's words and the operator's) and the shape of the file; with more than "
     "five sets start `vw-set-look` helpers, about five sets each, each given a group name, its element ids, the run folder's path and the tool's command line;"),
    ('picture-search',   # the order of authority (review, C3, S11)
     "(the film's picture wins over the web)",
     "(the request says the order once, the earlier winning: the operator's words, the film's own pictures (the approved drawing for shape and size, the footage picture for look, "
     "colour and wear), your added words, the plan's description, then web photographs)"),
    ('picture-search',   # three makes: a make with no picture is not counted (review, M1, M2)
     'and a set is made three times at most.',
     'and a set is made three times at most, a make that returned no picture not counted.'),
    ('picture-search',   # the proposals say which sets are made first (review, C4)
     'which they may accept in one click that shows the total price (never a doubtful thing',
     'which they may accept in one click that says how many sets are made first, with their price, and that the others are asked after (never a doubtful thing'),
    ('picture-search',   # a second send; the image command (review, M5, M6)
     'A round whose answer has no `v` is an older round: follow the tool\'s answers.',
     'The round file sent again after step 1 orders nothing and brings back only a thing that is new in the plan or whose entry in the plan changed; a thing the operator left '
     'out comes back only when they ask for it by name (`vw visuals round --back E`), as an open line. A set is never made with `vw visuals image --kind sheet` on such a film: '
     'the server refuses it. A round whose answer has no `v` is an older round: follow the tool\'s answers.'),
]
RETIRED = ['`vw visuals elements`; `vw visuals frame --file`; out/reference-round.json',   # the sentences replaced, for server/retired-sentences.json
           'and the tool meeting the material (hands and forearms, no face)',
           'in one click that shows the total price',
           'the server adds the kept preamble',                     # three older sentences of the references step, gone from the instructions before this review
           'each thing gets the footage picture or Ignore this',
           'judges them all in one shot']
COMMANDS = [   # (the old sentence, the new one) in plugin/commands/vw.md
    ('by `vw-reference-finder` helpers of about five things each, or by you',
     "by `vw-reference-finder` helpers of about five things each (each given its group name, its thing ids, the run folder's path and the tool's command line), or by you"),
    ('(`vw-set-look` helpers for more than five; `round --looks <file>` records the looks)',
     "(its `how` gives the points to judge by and the shape of the file; `vw-set-look` helpers for more than five, each given its group name, its element ids, the run folder's "
     "path and the tool's command line; `round --looks <file>` records the looks)"),
    ('never from a rejected picture; three makes at most)', 'never from a rejected picture; three makes at most, a make that returned no picture not counted)'),
    ('a round whose answer has no `v` is an older round: follow the tool\'s answers;',
     'the round file sent again after step 1 orders nothing and brings back only a thing that is new in the plan or whose entry changed, a thing the operator left out only when '
     'they ask for it by name (returned with `--back`, as below); a set is never made with `vw visuals image --kind sheet` on such a film; a round whose answer has no `v` is '
     'an older round: follow the tool\'s answers;'),
]


def apply_steps(steps):
    i, old, new = STEP
    if new not in steps[i]:
        if steps[i].count(old) != 1:
            sys.exit('not applied: step %d: not found once: %s' % (i, old[:60]))
        steps[i] = steps[i].replace(old, new)
    return steps


def apply(prompt, parts):
    """The visuals text with the review's sentences: the common part is returned, the parts are changed in place. Applying twice changes nothing."""
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
    """The visuals stage as it read before this script: for the tests of the three scripts it follows, whose own sentences it changes."""
    st = json.loads(json.dumps(stage))
    for where, old, new in PAIRS:
        part = next(p for p in st['parts'] if p['name'] == where)
        part['text'] = part['text'].replace(new, old)
    i, old, new = STEP
    st['steps'][i] = st['steps'][i].replace(new, old)
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
    apply_steps(st['steps'])
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
    print('visuals: design/211, the review')
    print('words in the visuals stage:', sum(len(t.split()) for t in [st.get('prompt') or '', *(st.get('steps') or []), *(p['text'] for p in st.get('parts') or [])]))


if __name__ == '__main__':
    main()
