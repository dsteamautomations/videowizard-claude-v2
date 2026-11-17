"""design/213 (17 Nov 2026): instruction version 3, the visuals stage: the references sets screen in the new layout, and the corrections
of step 5 (judging the sets) after the first real film.

What changed in the program is said here in the instruction's own sentences: step 2 shows one set at a time beside a list in four groups
(to judge, could not be made, waiting to be made, settled) with the answers Approve, Minor corrections, Make again, Upload my own and
Leave out; a place gets one picture; a way of working is proposed "leave" unless a still shows its action; a person whose kept footage
frame shows the face is asked for at step 1 with one question, the permission; where the plan and the footage differ the added words say
what to take from each, and they rank above the film's pictures; a look turns the image model's notes into two plain lines, and is given
the thing's kept footage pictures; a limit with no room is said with no amount. The two helper files (`plugin/agents/vw-reference-finder.md`,
`plugin/agents/vw-set-look.md`) and the command file (`plugin/commands/vw.md`) say the same. The older sentences are retired by name (server/retired-sentences.json). Registered in
scripts/c1_split_v3.py after design/212's script. Exact anchors, each found once; run once: python scripts/d213_wording_v3.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'server' / 'procedures' / 'v3.json'
R = ROOT / 'server' / 'retired-sentences.json'
AGENTS = ROOT / 'plugin' / 'agents'
CMD = ROOT / 'plugin' / 'commands' / 'vw.md'

PAIRS = [   # (where: 'common' or a part's name, the old sentence, the new one)
    ('picture-search',   # L: the look says whether a person's frame shows the face
     'looks: [{trial, view, verdict, seen, keep, closest}]}]}; verdict pass, weak or fail):',
     "looks: [{trial, view, verdict, seen, keep, closest, face, child}]}]}; verdict pass, weak or fail; on a person's frame `face` says whether it shows their face and `child` "
     'whether they are a child, as seen, never guessed from words):'),
    ('picture-search',   # L: the one question of step 1; the frames untied where the person is not the character
     "it goes to the picture AI only with the person's recorded permission (own likeness, part-plan.md; a footage frame may still be a video take's start image).",
     "it goes to the picture AI only with the person's recorded permission (own likeness, part-plan.md; a footage frame may still be a video take's start image). Where a kept "
     "frame shows a person's face, step 1 asks the operator one thing: whether they have that person's permission (a parent's or guardian's for a child). With it the kept "
     'frames go to the set, the best face frame first; without it a stand-in is made from the description, who will differ from the person in the clips. Where the person in '
     "the footage is not the film's character, give that row no frames (`frames: []`): nothing is asked then."),
    ('picture-search',   # C and W: the added words where the plan and the footage differ; a way of working
     'and `prompt` only for what the plan does not say.',
     "and `prompt` only for what the plan does not say. Where the plan's thing and the footage differ (the footage shows a trial piece on the ground, the plan the finished "
     'thing in its place), write in `prompt` what to take from the footage and what from the plan: the request ranks these words above the film\'s pictures, the check judges '
     'by them, and the operator reads them on the line. For a way of working propose `leave` unless a still picture (not an AI video) shows the action, and say so in the '
     'reason: on the video route nothing reads its set.'),
    ('picture-search',   # P: a place gets one picture
     'a place whole, from the other side, and its fixed things;',
     'a place as one picture, the whole place (a round posted before 17 Nov 2026 keeps its three: whole, from the other side, its fixed things);'),
    ('picture-search',   # N: the kept footage pictures beside the set; the notes as two plain lines
     "its `how` gives the points to judge by (against the footage picture, the approved drawing, the plan's words and the operator's) and the shape of the file;",
     "its `how` gives the points to judge by (against the footage picture, the approved drawing, the plan's words and the operator's) and the shape of the file; the thing's "
     "kept footage pictures come with the set to compare with, also when it was not made from them (never beside a stand-in); each look turns the image model's notes into two "
     'plain lines, `chose` (what the model chose) and `aside` (what it set aside), which the operator reads in place of the notes;'),
    ('picture-search',   # S: the answers of step 2
     "the operator judges each: Yes (ticking the golden picture of a thing, the one every shot starts from; a person's is the full-length front), No, or Correct it with "
     'their words; one click orders the other sets. After No or Correct it nothing is made',
     "the operator judges each: Approve (choosing the reference picture of a thing, from which pictures of it start; a person's is the full-length front, with the face), "
     'Minor corrections with their words, or Make again; one click orders the other sets. After Make again or Minor corrections nothing is made'),
    ('picture-search',   # S: the screen of step 2, and the limit with no amount
     "Step 2 shows each set with the footage picture beside it, the program's check, your look and the image model's notes; the first sets are judged before the others are "
     "ordered, on one button; a set made again shows the set before and the operator's words.",
     "Step 2 shows one set at a time beside the list, in four groups in this order: to judge (those you would make again or are unsure of first), could not be made, waiting "
     "to be made, settled; each set with the film's own pictures to compare, the program's check, your look and your two lines on the image model's notes. Its answers are "
     'Approve, Minor corrections, Make again, Upload my own and, where it is allowed, Leave out; a set made three times offers no remake. The first sets are judged before the '
     'others are ordered, on one button; leaving some out shows which shots lose a reference, never covers a person, and makes the others on the same word; a set made again '
     "shows the set before and the operator's words. Where the film's limit has no room the line says so with no amount: only the owner raises it."),
]
RETIRED = ['the one every shot starts from',   # the sentences replaced, for server/retired-sentences.json
           "your look and the image model's notes",
           'a place whole, from the other side, and its fixed things',
           'After No or Correct it nothing is made']
COMMANDS = [   # (the old sentence, the new one) in plugin/commands/vw.md
    ("Yes with the golden tick on a thing (the one every shot starts from; a person's golden is the full-length front, and the face close-up follows it into shots), No, or "
     'Correct it (',
     "Approve with the reference picture chosen on a thing (the one pictures of that thing start from; a person's is the full-length front, and the face close-up follows it "
     'into shots), Minor corrections with their words, or Make again ('),
]
HELPERS = [   # (the file under plugin/agents, the old sentence, the new one)
    ('vw-reference-finder.md',   # L: the face, a child, a person who is not the character
     'say why in `not_searched`.',
     "say why in `not_searched`. On a frame of a person, say in its look whether it shows their face (`\"face\": true` or `false`) and whether the person is a child "
     "(`\"child\": true`): what you see, never a guess from the words. Where the person in the footage is not the film's character, keep none of their frames."),
    ('vw-set-look.md',   # P: a set may be one picture
     'looks at all three pictures of each set',
     'looks at every picture of each set'),
    ('vw-set-look.md',   # N: the kept footage pictures that were not inputs
     "and the result of the program's check, and the image model's notes.",
     "and the result of the program's check, the image model's notes, and `footage`: the film's own kept pictures of the thing that the set was not made from (none beside a stand-in)."),
    ('vw-set-look.md',
     '`picture-1.jpg`, `picture-2.jpg`, `picture-3.jpg`: the set.',
     "`footage-1.jpg`, `footage-2.jpg`: the film's own kept pictures the set was not made from; compare with them too. `picture-1.jpg`, `picture-2.jpg`, `picture-3.jpg`: the "
     'set (a place has one picture).'),
    ('vw-set-look.md',   # N: the notes as two plain lines
     '`doubt` when you cannot tell.',
     "`doubt` when you cannot tell. Where the set has notes of the image model, add two plain lines to its row, which the operator reads in place of the notes: `chose`, what "
     'the model chose, and `aside`, what it set aside (one line each; the server refuses a set that has notes and not these two).'),
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
        text = (AGENTS / name).read_bytes().decode('utf-8')
        for file, old, new in HELPERS:
            if file == name and new not in text:
                if text.count(old) != 1:
                    sys.exit('not applied: plugin/agents/%s: not found once: %s' % (name, old[:60]))
                text = text.replace(old, new)
        (AGENTS / name).write_bytes(text.encode('utf-8'))   # bytes: the file keeps its line ends
    text = CMD.read_bytes().decode('utf-8')
    for old, new in COMMANDS:
        if new not in text:
            if text.count(old) != 1:
                sys.exit('not applied: plugin/commands/vw.md: not found once: %s' % old[:60])
            text = text.replace(old, new)
    CMD.write_bytes(text.encode('utf-8'))   # bytes: the file keeps its line ends
    print('visuals: design/213')
    print('words in the visuals stage:', sum(len(t.split()) for t in [st.get('prompt') or '', *(st.get('steps') or []), *(p['text'] for p in st.get('parts') or [])]))


if __name__ == '__main__':
    main()
