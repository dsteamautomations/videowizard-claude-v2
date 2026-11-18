"""design/215 (18 Nov 2026): instruction version 3, the visuals stage: the references fix set.

What changed in the program is said here in the instruction's own sentences: the three labels of the answer that was "Leave out" ("No
reference needed" at step 1, "Do not make this set" on the waiting sets, "Go on without a reference" on a set that failed or was made three
times); how many sets are made first, said to the operator by the server; no amount and no cost word at the references, also in a reason;
an unticked picture is only not used; one order of authority, the program's; the operator's corrections are kept per thing by the server;
whether the picture model searched is recorded and shown; the older rules for a prompt the assistant writes do not read a set's request;
the step "Sizes, materials and graphic specs"; the default look follows the film's category and the Direction; an object in use is filed
by category. The command file, the finder's helper file and the operator's rules file say the same. The older sentences are retired by
name (server/retired-sentences.json). Registered in scripts/c1_split_v3.py after design/214's script. Exact anchors, each found once; run
once: python scripts/d215_wording_v3.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'server' / 'procedures' / 'v3.json'
R = ROOT / 'server' / 'retired-sentences.json'
AGENTS = ROOT / 'plugin' / 'agents'
CMD = ROOT / 'plugin' / 'commands' / 'vw.md'
RULES = ROOT / 'plugin' / 'operator-CLAUDE.md'

S = 'picture-search'
PAIRS = [   # (where: 'common' or a part's name, the old sentence, the new one)
    # change 6: the step is named for what it holds; "drawings" is the step after it
    ('common', 'The operator answers the treatment and the plan, then the drawings and the materials, on the page',
     'The operator answers the treatment and the plan, then the sizes, materials and graphic specs, on the page'),
    ('common', 'they too are approved on the page, after the drawings and the materials,', 'they too are approved on the page, after the sizes, materials and graphic specs,'),
    ('plan', 'after the plan is accepted they approve the drawings and the materials on the page', 'after the plan is accepted they approve the sizes, materials and graphic specs on the page'),
    # change 4: the default look, by category and the Direction
    ('treatment', '(palette, contrast, saturation, muted and true to life by default, light;',
     "(palette, contrast, saturation, light; by default the look the film's category and the Direction call for: on a documentary-explainer film muted and true to life;"),
    # W4: no cost word in the references part
    (S, 'Find each thing in the footage first, free: `vw visuals digest`', 'Find each thing in the footage first: `vw visuals digest`'),
    (S, '`vw drawing set --element E --file work/drawing/E/set.json` (free; the server draws every view', '`vw drawing set --element E --file work/drawing/E/set.json` (the server draws every view'),
    # change 1 and W4: the proposal, and its reason with no cost word
    (S, '`leave`: leave it out); `reason`, one line the operator reads;',
     '`leave`: no reference needed); `reason`, one line the operator reads, which names no cost and no cost word (never "free" or "paid");'),
    # one word, "set"
    (S, "Every person gets a character sheet; an animal gets none. The server writes a person's sheet from the plan",
     "Every person gets a set; an animal gets none. The server writes a person's set from the plan"),
    # W8: an object in use, filed by category
    (S, 'an object whole, as the film uses it, and its telling detail (no person; in use, the hand and the material the description names);',
     'an object whole, as the film uses it, and its telling detail (the thing stays the subject; in use, the person who wears, holds or uses it as far as the use needs; on a '
     'documentary-explainer film no person, only the hand that holds it and the material the description names);'),
    # change 1, change 7, W4: step 1's answers and how the making goes
    (S, 'use its footage picture as the reference (free; no AI set, and the first picture in view order is its golden picture), have a clean set made from it (paid), have a set '
        "made (paid), or leave it out; one footage picture can be marked not this one. Done approves the frames and orders the first three sets only; the others are ordered on the "
        "operator's word, once they have judged the first.",
     'use its footage picture as the reference (no AI set, and the first picture in view order is its golden picture), have a clean set made from it, have a set made, or no '
     'reference needed; one footage picture can be marked not this one. Done approves the frames and orders the first three sets only, made to check the method; the others are made '
     "in one go on the operator's word, once they have judged the first; with three sets or fewer all are made at once. The server says this to the operator in its own sentence "
     'when step 1 is recorded and again when the others are ordered (`then`): pass it on as it is.'),
    # W6: one order of authority, the program's; change 3: the search record; R1 to R5: the older rules do not read a set
    (S, "the operator's words, the film's own pictures (the approved drawing for shape and size, the footage picture for look, colour and wear), your added words, the plan's "
        'description, then web photographs), else from real photographs with Google Search and Image Search on.',
     "the operator's words, your added words, the film's own pictures (the approved drawing for shape and size, the footage picture for look, colour and wear), the plan's "
     'description, then web photographs), else from real photographs with Google Search and Image Search on; a place is one picture. The server records whether the picture model '
     "searched and shows it on the set's line: searched (with the pages, where it gave any), did not search, not asked (a person's set), or not known; never say it yourself and "
     "never guess it. The older rules for a prompt you write do not read a set's request: the wording rules read only the words you or the operator added, and the quoted-words "
     'rule, "the plan cites the footage", "measure it first" and the "Not this" list are not applied to a set.'),
    # change 5: the operator's corrections of a thing
    (S, 'Minor corrections with their words, or Make again; one click orders the other sets.',
     'Minor corrections with their words, or Make again; one click orders the other sets. A correction stays on that set; where the operator ticks "This applies to every picture '
     'of this thing" (in the chat: "Correct every picture of it"), the server keeps it for the thing, carries it into every later request of it (a later set, a still, a start '
     "picture), the later correction winning, and shows it on the thing's line: never write a correction into the plan's description."),
    # change 1: the groups and the buttons of step 1; W5: an unticked picture
    (S, 'the things with no picture for which a set is suggested; those suggested to leave out; and the people',
     'the things with no picture for which a set is suggested; those for which no reference is suggested; and the people'),
    (S, 'The buttons follow the case of the thing: Approve, Make a set, Minor corrections (with their words), Upload my own, Leave out. Each footage picture is shown with what you '
        "saw and a Keep tick: an unticked picture is not this picture (the next best is then shown and the thing comes back once), a ticked closest picture is taken as the thing's "
        'own; leaving the thing out names the shots that lose it.',
     'The buttons follow the case of the thing: Approve, Make a set, Make a set with words (their words), Upload my own, No reference needed. Each footage picture is shown with '
     'what you saw and a Keep tick: an unticked picture is only not used, and no other is searched ("Not this picture" is its own button: the next best is then shown and the thing '
     'comes back once); a ticked closest picture is taken as the thing\'s own; "No reference needed" names the shots made without a reference.'),
    # change 1: step 2
    (S, 'Its answers are Approve, Minor corrections, Make again, Upload my own and, where it is allowed, Leave out; a set made three times offers no remake. The first sets are '
        'judged before the others are ordered, on one button; leaving some out shows which shots lose a reference, never covers a person, and makes the others on the same word;',
     'Its answers are Approve, Minor corrections, Make again, Upload my own and, on a set that could not be made or was made three times, Go on without a reference; a set made '
     'three times offers no remake. The first sets are judged before the others are ordered, on one button; "Do not make this set" on the waiting sets shows which shots lose a '
     'reference, never covers a person, and makes the others on the same word;'),
    # W3: no amount, also in the refusal
    (S, "No cost is shown at the references, on the page or in the chat (the owner's decision of 17 Nov 2026): the server keeps the film's limit and records every spend, and only "
        'a refusal after done names the limit; never add a price yourself.',
     "No cost is shown or named at the references, on the page, in the chat or in a reason you write (the owner's decision of 17 Nov 2026): the server keeps the film's limit and "
     'records every spend, and a refusal after done says the limit with no figure; never add a price or a cost word yourself.'),
    (S, 'never use them to answer for the operator, and nothing paid is ordered without their words.', 'never use them to answer for the operator, and nothing is ordered without their words.'),
    (S, "(the client's material and the plan; paid measures and web figures after the round)", "(the client's material and the plan; measures and web figures after the round)"),
    # stale labels
    (S, "The operator gives their own picture on the page (Use my own picture, on the thing's line;", "The operator gives their own picture on the page (Upload my own, on the thing's line;"),
    (S, "(the first sets are ordered and paid then; the others only on the operator's word): at step 2 a set is made again from the request you rewrite with the operator's words, "
        'and one that was not made can be left out.',
     "(the first sets are ordered then; the others only on the operator's word): at step 2 a set is made again from the request you rewrite with the operator's words, and for one "
     'that was not made the operator may go on without a reference.'),
    (S, 'a thing the operator left out comes back only when they ask for it by name', 'a thing the operator said needs no reference comes back only when they ask for it by name'),
]
RETIRED = ['muted and true to life by default',   # the sentences replaced, for server/retired-sentences.json
           'an unticked picture is not this picture',
           'those suggested to leave out',
           'Every person gets a character sheet',
           'only a refusal after done names the limit',
           'nothing paid is ordered without their words',
           'the first sets are ordered and paid then',
           'have a clean set made from it (paid)',
           "then the drawings and the materials, on the page",
           'they approve the drawings and the materials on the page',
           'Use my own picture, on the thing\'s line']
COMMANDS = [   # (the old sentence, the new one) in plugin/commands/vw.md
    ('The treatment, the plan, the drawings and materials, the reference drawings and the two steps', 'The treatment, the plan, the sizes, materials and graphic specs, the reference drawings and the two steps'),
    ("the same page lists the drawings and the materials (design/209): each drawing's parts and sizes and each material's facts",
     "the same page lists the sizes, materials and graphic specs (design/209): each graphic's parts and sizes and each material's facts"),
    ('(`vw visuals trial --file`, rows `{element, clip, at}`, free)', '(`vw visuals trial --file`, rows `{element, clip, at}`)'),
    ('footage, clean, set, no_set or leave, with its reason in one line;', 'footage, clean, set, no_set or leave (no reference needed), with its reason in one line, which names no cost and no cost word;'),
    ("from the plan's words and views and the film's own pictures, as three separate pictures);", "from the plan's words and views and the film's own pictures, as three separate pictures, a place as one);"),
    ('step 1 each thing gets its footage picture as the reference (free), a clean set made from it, a set, or is left out, and Done orders the first three sets only, the others on',
     'step 1 each thing gets its footage picture as the reference, a clean set made from it, a set, or no reference, and Done orders the first three sets only (the server says to '
     'the operator how the making goes: pass its sentence on as it is), the others on'),
    ('`vw drawing set --element E --file …` (free), and the operator approves', '`vw drawing set --element E --file …`, and the operator approves'),
    ('(no cost is shown at the references, on the page or in the chat;', '(no cost is shown or named at the references, on the page, in the chat or in a reason you write;'),
    ('it prints `held`, the answers whose remake the spend cap holds: they are kept and wait, tell the operator the spend)',
     "it prints `held`, the answers whose remake the film's limit holds: they are kept and wait; tell the operator so with no amount; `all: true` on a correction keeps it for every "
     'later picture of the thing, only where the operator said so)'),
    ("(paid: only on the operator's words; refused in plain words while its cause stands)", "(only on the operator's words; refused in plain words while its cause stands)"),
    ('a thing the operator left out only when they ask for it by name', 'a thing the operator said needs no reference only when they ask for it by name'),
    ("the operator's own picture is given on the page (Use my own picture, on its line)", "the operator's own picture is given on the page (Upload my own, on its line)"),
]
HELPERS = [   # (the file under plugin/agents, the old sentence, the new one)
    ('vw-reference-finder.md',
     'the frames you did not keep are what the operator falls back on.',
     'the frames you did not keep are what the operator falls back on. A note says where the thing is seen or why it is not; it never names a cost or a cost word (never "free" '
     'or "paid").'),
]
OPERATOR = [   # (the old sentence, the new one) in plugin/operator-CLAUDE.md
    ('- Paid steps are information, not a question: say which provider is used and proceed.',
     '- Paid steps are information, not a question: say which provider is used and proceed. Except the references of a film (the footage pictures and the sets): nothing is ordered '
     "there without the operator's own word, and no amount or cost word is said there."),
    ('and for a thing that is drawn before its picture `vw-drawing`).', 'for a thing that is drawn before its picture `vw-drawing`, and for the references `vw-reference-finder` and `vw-set-look`).'),
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
        if where == 'common':
            st['prompt'] = st['prompt'].replace(new, old)
        else:
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


def _swap(path, pairs, name):
    """The pairs applied to one text file, each old sentence found once; bytes in and out, so the file keeps its line ends."""
    raw = path.read_bytes()
    end = '\r\n' if b'\r\n' in raw else '\n'
    text = raw.decode('utf-8').replace('\r\n', '\n')
    for old, new in pairs:
        if new not in text:
            if text.count(old) != 1:
                sys.exit('not applied: %s: not found once: %s' % (name, old[:60]))
            text = text.replace(old, new)
    path.write_bytes(text.replace('\n', end).encode('utf-8'))


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
        _swap(AGENTS / name, [(old, new) for file, old, new in HELPERS if file == name], 'plugin/agents/' + name)
    _swap(CMD, COMMANDS, 'plugin/commands/vw.md')
    _swap(RULES, OPERATOR, 'plugin/operator-CLAUDE.md')
    print('visuals: design/215')


if __name__ == '__main__':
    main()
