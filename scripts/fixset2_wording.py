"""Fix set phase 2 (SK, 19 Nov 2026): what cost the most time on VW-24's redo of step 6, in the served text and the helpers' texts.

In v3.json (the later steps, section 11): the helpers of the drawings that do not wait on each other are started in one message (A1.4); the
still end-frames of all drawings come first, their cards in the order of the film (A1.3); a rule that compares with another drawing names it,
waits as a note while there is nothing to compare with and comes due later (A1.2); a later round reads the server's list, rules-round.md (A1.6);
the parts helper's open choices are asked with the other questions (A1.5); the shared look states the counts and the parts are every shape that
repeats (A1.1); a still with no rule a still can show passes with an empty verdict (c2). One sentence is replaced ("three or four at once"); the
others are added after their anchor. In plugin/: the same for the parts helper, the rule writer and the checker; the skill no longer says "place
each" (c4); the command file's sentence that step 7 replaced by hand is named here, so the test of design/218 reads it through now() (c3).
The replaced sentences are in server/retired-sentences.json. Registered in scripts/c1_split_v3.py after design/222's script. Exact anchors, each
found once; applying twice changes nothing. Run once: python scripts/fixset2_wording.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'server' / 'procedures' / 'v3.json'

TOGETHER_OLD = 'the others side by side, three or four at once;'
TOGETHER_NEW = ('the others side by side, all started in one message, not one after another (the next-step line of `vw visuals next` and `vw visuals status` '
                'names the drawings whose builder or checker can start now and which drawing waits on which); the checkers are started the same way;')
ORDER = 'see "The still end-frame" below).'
ORDER_NEW = (ORDER + ' The order of the work: the still end-frames of all the drawings that do not wait on another are built and checked first, and their cards '
             'come in the order of the film, before any motion is built: a change the operator asks for then reaches every drawing before anything is '
             'animated.')
COMPARE = 'and the checker is given the last frame for the rules that compare with it.'
COMPARE_NEW = (COMPARE + ' A rule that compares this drawing with another one names it in its mark (`must (still, with D1):`). Once that drawing\'s still '
               'end-frame is approved, `vw motion upload` and `vw motion brief` save it in work/motion/S/with-<that shot>/ and the checker answers the rule '
               'against it, as a must. Until then it waits as a note and holds nothing: the drawing is bound and rendered without it. When the other still is '
               'approved the next-step line says the comparison is due: give a checker that rule with both frames and send its verdict with the same '
               'round; a fail is a failed must of this drawing. It is closed only when the other drawing leaves the plan.')
ROUND = 'and a rule it leaves out keeps its pass.'
ROUND_NEW = (ROUND + ' The server writes that list: from round 2, `vw motion upload` saves work/motion/S/rules-round.md, the rules the round before left failed '
             'or not seen, and the checker reads it in place of rules.md; when the brief changed since, there is no such file and every rule is answered again.')
ASK = "a question about a fact is put to the operator once, with the other drawings' questions, before the first drawing is built."
ASK_NEW = (ASK + ' The parts helper answers with its open choices too (a count or a proportion two specs give differently), each with the answer it '
           'recommends: put them to the operator in the same go, one after another with no build between, and record each answer in the shared look.')
LOOK = 'and which diagrams return (withdrawn with `vw motion note --shot all --remove "<the line>"`).'
LOOK_NEW = (LOOK + ' State there the count of each shape that repeats across the drawings (how many of a part, how many divisions), so every drawing shows the '
            'same number.')
PARTS = 'upload it with `vw motion parts --file work/motion/parts/parts.svg`.'
PARTS_NEW = (PARTS + ' The parts are every shape two or more drawings show, not only the things of the plan: the helper lists them first from all the specs, '
             'with their counts, and names on each part the drawings that show it; with no repeating shape it writes an empty file and there are no shared '
             'parts.')
EMPTY = 'send its verdict with `vw motion verdict` as for any project.'
EMPTY_NEW = (EMPTY + ' When the upload says that no rule of the drawing is one a still can show, no checker is needed: send a verdict with an empty rule list.')

PAIRS = [   # (where: 'common' or a part's name, the old sentence, the new one)
    ('later', TOGETHER_OLD, TOGETHER_NEW),
    ('later', ORDER, ORDER_NEW),
    ('later', COMPARE, COMPARE_NEW),
    ('later', ROUND, ROUND_NEW),
    ('later', ASK, ASK_NEW),
    ('later', LOOK, LOOK_NEW),
    ('later', PARTS, PARTS_NEW),
    ('later', EMPTY, EMPTY_NEW),
]

A_PART = 'A part is a thing two or more drawings show (a building element, a product, a tool, an icon, a figure in a chart).'
A_PART_NEW = (A_PART + ' That is every shape that repeats, not only the things of the plan (a frame, a floor, a grid, an axis, a row of the same marks): before '
              'you draw, list from all the specs each shape that two or more drawings show, with the drawings that show it and its count where a spec gives '
              'one. When no shape repeats, write parts.svg as an empty `<svg xmlns="http://www.w3.org/2000/svg"></svg>` and say so.')
VIEW = 'Each brief then tells its drawing which view to place.'
VIEW_NEW = (VIEW + ' Name on every part the drawings that show it: `data-shots="<shot id> <shot id>"` (the ids are in brief.md); a part that draws no thing of '
            'the plan reaches only the briefs of the drawings it names.')
ANSWER = "Answer with each part's id and title, and the drawings that show it."
ANSWER_NEW = (ANSWER + ' Then your open choices, one line each, with the answer you recommend and why (a count or a proportion two specs give differently; a '
              'shape the specs do not settle): draw what you recommend; the main assistant asks the operator once, with the other questions, before the first '
              'drawing is built. Then the counts every drawing must share (how many of each repeating shape), for the shared look.')
MARK = 'a rule that needs the motion to be judged is never marked `(still)`.'
MARK_NEW = (MARK + ' A rule that compares this drawing with another drawing (the same part, count or size as in drawing D1) names that drawing in the mark: '
            '`must (still, with D1):`. The checker is then given that drawing\'s approved still end-frame; while there is none the rule waits as a note and '
            'holds nothing.')
LIST = 'On a still read it in place of rules.md and answer every rule in it and no other.'
LIST_NEW = (LIST + ' In round 2 or 3 of the animated drawing, when `work/motion/<shot>/rules-round.md` is there, it is the server\'s list for the round: the '
            'rules the round before left failed or not seen. Read it in place of rules.md and answer every rule in it; the other rules keep their pass, and you '
            'still look at the whole frame for a must-kind fault. For a rule that compares with another drawing, that drawing\'s approved still end-frame is '
            '`with-<that shot>/last-frame.png` in this shot\'s folder: compare against it; when it is not there, leave the rule out (the server keeps it as a '
            'note and asks for it when the frame exists).')
EACH_OLD = 'place each with `<use href="#part-<name>">` at the size and place this drawing needs'
EACH_NEW = 'place the view this drawing shows with `<use href="#part-<name>">` at the size and place it needs'
AT_ONCE_OLD = 'One helper per drawn shot, three or four at once.'
AT_ONCE_NEW = 'One helper per drawn shot, all that do not wait on another started together.'
TAKES_OLD = '; the AI video and the recording are asked in the chat, one at a time:'   # design/218's sentence in the command file
TAKES_NEW = ("; an AI video shot's layout drawing, its still and the word to make its first take, and the recording, are asked in the chat, one at a time;")   # as design/222 wrote it by hand (55e57f8)

HELPERS = [   # (file under plugin/, the old sentence, the new one)
    ('agents/vw-motion-parts.md', A_PART, A_PART_NEW),
    ('agents/vw-motion-parts.md', VIEW, VIEW_NEW),
    ('agents/vw-motion-parts.md', ANSWER, ANSWER_NEW),
    ('agents/vw-motion-rules.md', MARK, MARK_NEW),
    ('agents/vw-motion-check.md', LIST, LIST_NEW),
    ('skills/motion/SKILL.md', EACH_OLD, EACH_NEW),
    ('agents/vw-motion-shot.md', AT_ONCE_OLD, AT_ONCE_NEW),
    ('commands/vw.md', TAKES_OLD, TAKES_NEW),
]

RETIRED = ['the others side by side, three or four at once',                         # A1.4: all that do not wait on each other, in one message
           'One helper per drawn shot, three or four at once',
           'place each with `<use href="#part-<name>">`',                             # c4: the view this drawing shows (the brief said so since phase 1)
           'the AI video and the recording are asked in the chat, one at a time']     # c3: replaced by design/222 (the finished takes are answered on the page)


def apply(prompt, parts):
    """The visuals text with this set's sentences: the common part is returned, the parts are changed in place. Applying twice changes nothing."""
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


def now(file, text):
    """An earlier script's sentence for one plugin file as it reads after this script (for that script's test)."""
    for f, old, new in HELPERS:
        if f == file and new not in text:
            text = text.replace(old, new)
    return text


def main():
    raw = P.read_bytes()
    d = json.loads(raw.decode('utf-8'))
    st = next(s for s in d['stages'] if s['name'] == 'visuals')
    st['prompt'] = apply(st['prompt'], st['parts'])
    P.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\r\n' if b'\r\n' in raw else '\n')   # the file keeps its line ends
    for file, old, new in HELPERS:
        path = ROOT / 'plugin' / file
        raw = path.read_bytes()   # bytes in and out, so the file keeps its line ends
        end = '\r\n' if b'\r\n' in raw else '\n'
        text = raw.decode('utf-8').replace('\r\n', '\n')
        if new not in text:
            if text.count(old) != 1:
                sys.exit('not applied: plugin/%s: not found once: %s' % (file, old[:60]))
            path.write_bytes(text.replace(old, new).replace('\n', end).encode('utf-8'))
    rp = ROOT / 'server' / 'retired-sentences.json'
    r = json.loads(rp.read_text(encoding='utf-8'))
    r['sentences'] += [s for s in RETIRED if s not in r['sentences']]
    rp.write_text(json.dumps(r, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    print('visuals and helpers: fix set phase 2')


if __name__ == '__main__':
    main()
