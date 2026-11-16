"""design/210, the wording review (SK, 16 Nov 2026): instruction version 3, the visuals stage. A walk through the instructions in the order the
assistant acts found sentences that still sent a page step to the chat, or to a command that refuses. Changed here: section E's heading; a
question is handed out by `vw visuals next` (not shown on a card of the server's own page); in the chat the Direction is asked alone, then the
gap lines on a card; an offered choice of the plan is the operator's (the page's Take button; `vw visuals select` only as the chat way, with
their answer); the picture search reads in the order it is done (the frames, the drawings approved on the page, then the round); the wait is
between the round's two steps and ends when the sets are back; Done on step 1 is not undone. The same sentences in the plugin's command file.
The older ways: the sentences replaced are retired by name (server/retired-sentences.json); none is kept.
Exact anchors, each found once; run once: python scripts/d210c_wording_v3.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'server' / 'procedures' / 'v3.json'
R = ROOT / 'server' / 'retired-sentences.json'
CMD = ROOT / 'plugin' / 'commands' / 'vw.md'

PAIRS = [   # (where: common or a part's name, the old sentence, the new one)
    ('common',   # C2: a question is handed out by `vw visuals next`; operators cannot open the server's own page
     "the question shows on the item's card and in `status`; the server refuses every derived write on that item until the operator answers (the card's buttons, or "
     'their words through',
     'the server hands the question to the operator in the chat, in its turn (`vw visuals next`), and lists it in `status`; the server refuses every derived write on '
     "that item until the operator answers (the question's buttons, or their words through"),
    ('common',   # F8: the heading of section E
     "E. THE OPERATOR'S DECISIONS, ONE AT A TIME, IN THE CHAT\n",
     'E. WHERE THE OPERATOR DECIDES: THE PAGE, THEN THE CHAT\n'),
    ('treatment',   # C1: the chat asks the Direction alone, then the gap lines on a card
     'the server hands the operator every line on one card, the Direction first, and you record the card with `vw visuals card`',
     'the server asks the Direction alone, as one question (recorded with `vw visuals decide`), then hands the operator the gap lines on one card, and you record the '
     'card with `vw visuals card`'),
    ('plan',   # F3: an offered choice is the operator's: the page's Take button records it
     'or leave it out); `vw visuals select --gap G --choice C` for an offered choice; then `vw visuals page`',
     'or leave it out); then `vw visuals page`'),
    ('plan',   # F3: `select` named only as the chat way
     'the server asks an offered choice first, as buttons, then hands the operator the gaps on one card',
     "the server asks an offered choice first, as buttons (or, with the operator's answer, `vw visuals select --gap G --choice C`), then hands the operator the gaps "
     'on one card'),
    ('picture-search',   # F7: the order it is done in: the frames, the drawings approved on the page, then the round
     'The references are one round for every element at once (people, objects, places, the materials and processes the film relies on), never one element at a time. '
     '`vw visuals elements` shows where each is seen in the footage (work/visuals/elements.json); grab a frame of each the footage has (`vw visuals frame --file`, '
     'free); write out/reference-round.json, one row per element, every person included and none for an animal: element_id, its frame reference ids, and `prompt` (a '
     'thing: the subject block, what the picture must represent, its frame, nobody in it, never how the work is done; the server adds the kept preamble, the set '
     'line, the cosmetics from the plan and the four notes; a person: the why line); send it (`vw visuals round --file out/reference-round.json`) and run `vw visuals '
     'page`: the operator answers step 1 there. A clip frame is free and exact, source and time kept (`vw visuals frame --element E --clip <id> --at <seconds>`); '
     "search the clip analyses first, footage left out of the edit included (not the operator's explicit exclusions), and take the sharpest frame, the subject large "
     "and evenly lit, never a blurred one for identity. A footage frame of a person serves your description; it goes to the picture AI only with the person's "
     "recorded permission (own likeness, part-plan.md; a footage frame may still be a video take's start image). Every person gets a character sheet; an animal gets "
     "none. The server writes a person's sheet from the plan (description, outfits, place, your why line, one line against every other person), and from the person's "
     'photo when the permission is recorded, as three separate pictures: full length, working pose, the face; every person the words act with is an element (the '
     'check warns of one missing).\nA thing whose construction, pattern or mechanism must be right in a picture, or which a picture AI is unlikely to know, is drawn '
     'before the round: load the `vw:drawing` skill; a `vw-drawing` helper writes its drawing set as data (its facts, each with its source or marked assumed; its '
     'pieces in real sizes; its views) and sends it, `vw drawing set --element E --file work/drawing/E/set.json` (free; the server draws every view and refuses a '
     'faulty set in plain words). The operator approves the reference drawings on the page (`vw visuals page`, which also sends the pictures as it says): the '
     'labelled sheets, small and large on a click, with the sources and the assumed sizes, and they answer Yes or Correct it; in the chat, one at a time (`vw visuals '
     "next`), only where the page cannot be shown. Approved drawings go with that thing's set by themselves, with the words that explain them and its facts. Where "
     "the footage and the plan's sizes disagree, draw from the footage and tell the operator in one line. A loose or living thing gets a form sheet; a person never "
     'gets a drawing set. A drawing set is a reference for the picture AI; it is not the drawing spec of a drawn graphic.',
     'The references are one round for every element at once (people, objects, places, the materials and processes the film relies on), never one element at a time. '
     '`vw visuals elements` shows where each is seen in the footage (work/visuals/elements.json); grab a frame of each the footage has (`vw visuals frame --file`, '
     'free). A clip frame is free and exact, source and time kept (`vw visuals frame --element E --clip <id> --at <seconds>`); search the clip analyses first, '
     "footage left out of the edit included (not the operator's explicit exclusions), and take the sharpest frame, the subject large and evenly lit, never a blurred "
     "one for identity. A footage frame of a person serves your description; it goes to the picture AI only with the person's recorded permission (own likeness, "
     "part-plan.md; a footage frame may still be a video take's start image).\nA thing whose construction, pattern or mechanism must be right in a picture, or which a "
     'picture AI is unlikely to know, is drawn before the round: load the `vw:drawing` skill; a `vw-drawing` helper writes its drawing set as data (its facts, each '
     'with its source or marked assumed; its pieces in real sizes; its views) and sends it, `vw drawing set --element E --file work/drawing/E/set.json` (free; the '
     'server draws every view and refuses a faulty set in plain words). The operator approves the reference drawings on the page (`vw visuals page`, which also sends '
     'the pictures as it says): the labelled sheets, small and large on a click, with the sources and the assumed sizes, and they answer Yes or Correct it; in the '
     "chat, one at a time (`vw visuals next`), only where the page cannot be shown. Approved drawings go with that thing's set by themselves, with the words that "
     "explain them and its facts. Where the footage and the plan's sizes disagree, draw from the footage and tell the operator in one line. A loose or living thing "
     'gets a form sheet; a person never gets a drawing set. A drawing set is a reference for the picture AI; it is not the drawing spec of a drawn graphic.\nThen the '
     'round, once any drawing set is approved: write out/reference-round.json, one row per element, every person included and none for an animal: element_id, its '
     'frame reference ids, and `prompt` (a thing: the subject block, what the picture must represent, its frame, nobody in it, never how the work is done; the server '
     'adds the kept preamble, the set line, the cosmetics from the plan and the four notes; a person: the why line); send it (`vw visuals round --file '
     'out/reference-round.json`) and run `vw visuals page`: the operator answers step 1 there. Every person gets a character sheet; an animal gets none. The server '
     "writes a person's sheet from the plan (description, outfits, place, your why line, one line against every other person), and from the person's photo when the "
     'permission is recorded, as three separate pictures: full length, working pose, the face; every person the words act with is an element (the check warns of one '
     'missing).'),
    ('picture-search',   # F5: the wait is between the two steps
     '`vw visuals status --wait 900` until the round is complete; ask nothing per element and generate nothing meanwhile.',
     '`vw visuals status --wait 900` between the two steps and after a set is made again: it ends when the sets are back; then `vw visuals page`. Ask nothing per '
     'element and generate nothing meanwhile.'),
    ('picture-search',   # F2: the server refuses that undo once the sets are ordered
     'or in the chat with `vw visuals own`; Done on step 1 is undone with `vw visuals round --undo`.',
     "or in the chat with `vw visuals own`. Done on step 1 is not undone (the sets are ordered and paid then): at step 2 a set is made again with the operator's "
     'words, and one that was not made can be left out.'),
]
COMMANDS = [
    ('The treatment and the plan are answered on the page; every other decision of this stage is asked in the chat, one at a time:',
     'The treatment, the plan, the drawings and materials, the reference drawings and the two steps of the references are answered on the page (`vw visuals page`); '
     'the stills, the graphics, the AI video and the recording are asked in the chat, one at a time:'),
    ("(the card's buttons, or `vw visuals answer",
     '(the buttons of the question that `vw visuals next` hands out, or `vw visuals answer'),
    ("`propose`, `select` a choice where offered, then `vw visuals page` for the operator's answers",
     "`propose`, then `vw visuals page` for the operator's answers (a gap offered two ways is chosen there; in the chat, where the page cannot be shown, `vw visuals "
     "next` asks it, or `vw visuals select --gap G --choice C` with the operator's answer)"),
    ('`status --wait 900`: step 1 the operator approves the footage pictures',
     '`vw visuals page` for step 1, then `status --wait 900` between the two steps and after a set is made again (it ends when the sets are back; then `vw visuals '
     'page`): step 1 the operator approves the footage pictures'),
]
RETIRED = ['Done on step 1 is undone with `vw visuals round --undo`',
           '`vw visuals select --gap G --choice C` for an offered choice',
           "THE OPERATOR'S DECISIONS, ONE AT A TIME, IN THE CHAT",
           'every line on one card, the Direction first',
           'until the round is complete; ask nothing per element',
           "the question shows on the item's card"]


def apply(prompt, parts):
    """The visuals text with the wording review's sentences: the common part is returned, the parts are changed in place. Applying twice changes nothing."""
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
    print('visuals: the design/210 wording review, each step sent to where it is answered')
    print('words in the visuals stage:', sum(len(t.split()) for t in [st.get('prompt') or '', *(st.get('steps') or []), *(p['text'] for p in st.get('parts') or [])]))


if __name__ == '__main__':
    main()
