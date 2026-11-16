"""design/210 part 2 (SK, 16 Nov 2026): instruction version 3, the visuals stage. The reference round's two steps are answered on the page
(`vw visuals page`), each in one visit: the things with their footage pictures, then the sets with their three pictures; a paid answer on
the page shows its price on its button; the operator's own picture is given on the page, or in the chat with `vw visuals own`; the chat,
one at a time, only where the page cannot be shown. The same sentences in the plugin's command file.
Exact anchors, each found once; run once: python scripts/d210b_wording_v3.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'server' / 'procedures' / 'v3.json'
R = ROOT / 'server' / 'retired-sentences.json'
CMD = ROOT / 'plugin' / 'commands' / 'vw.md'

PAIRS = [   # (where: common or a part's name, the old sentence, the new one)
    ('common', 'one visit, then `vw visuals page --record`); in the chat only where the page cannot be shown.',   # design/210's sentence stays whole; one follows it
     "one visit, then `vw visuals page --record`); in the chat only where the page cannot be shown. The round's two steps are answered on the page too, each in one visit: the "
     'things with their footage pictures, then the sets with their three pictures (section 4); in the chat, one at a time, only where the page cannot be shown.'),
    ('picture-search', 'send it (`vw visuals round --file out/reference-round.json`) and run `vw visuals next` (section E).',
     'send it (`vw visuals round --file out/reference-round.json`) and run `vw visuals page`: the operator answers step 1 there.'),
    ('picture-search', 'The operator answers both steps in the chat, one at a time (`vw visuals next`, section E).',
     'The operator answers both steps on the page (`vw visuals page`), each in one visit: step 1; then, when the sets are back, `vw visuals page` again for the sets, and once more '
     'for each set made again. A paid answer on the page shows its price on its button: the click, then their done, is their word. In the chat, one at a time (`vw visuals next`, '
     'section E), only where the page cannot be shown.'),
    ('picture-search', 'The operator can add their own picture (`vw visuals supply`) or undo Done on step 1 (`vw visuals round --undo`).',
     "The operator gives their own picture on the page (Use my own picture, on the thing's line; a person's photo with their words that they have the permission), or in the chat "
     'with `vw visuals own`; Done on step 1 is undone with `vw visuals round --undo`.'),
    ('later', "every element's set judged in the chat, one at a time (`vw visuals next`, section E; never `vw visuals round --sets` for the operator);",
     "every element's set judged on the page (`vw visuals page`, one visit for the sets that are back; in the chat, one at a time, `vw visuals next`, section E, only where the "
     'page cannot be shown; never `vw visuals round --sets` for the operator);'),
]
STEP = (3, '`vw visuals round`; `vw visuals status --wait 900`, writing the drafts meanwhile;',
        "`vw visuals round`; the operator answers the round's two steps on the page (`vw visuals page`), `vw visuals status --wait 900` between them, writing the drafts meanwhile;")
COMMANDS = [
    ('the operator answers both steps in the chat, one at a time (`vw visuals next`);',
     'the operator answers both steps on the page (`vw visuals page`), each in one visit (a paid answer shows its price on its button; `vw visuals status --wait 900` between '
     'the two; in the chat, one at a time, `vw visuals next`, only where the page cannot be shown);'),
    ("the operator's own picture of a thing or a place is stored approved with `vw visuals own --element E --file F`",
     "the operator's own picture is given on the page (Use my own picture, on its line) or in the chat: a thing's or a place's is stored approved with `vw visuals own --element E --file F`"),
]
RETIRED = ['The operator answers both steps in the chat, one at a time', "every element's set judged in the chat, one at a time", 'The operator can add their own picture (`vw visuals supply`)']


def apply_steps(steps):
    i, old, new = STEP
    if new not in steps[i]:
        if steps[i].count(old) != 1:
            sys.exit('not applied: step %d: not found once: %s' % (i, old[:60]))
        steps[i] = steps[i].replace(old, new)
    return steps


def apply(prompt, parts):
    """The visuals text with design/210 part 2's sentences: the common part is returned, the parts are changed in place. Applying twice changes nothing."""
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
    print('visuals: design/210 part 2, the reference round answered on the page, in two visits')
    print('words in the visuals stage:', sum(len(t.split()) for t in [st.get('prompt') or '', *(st.get('steps') or []), *(p['text'] for p in st.get('parts') or [])]))


if __name__ == '__main__':
    main()
