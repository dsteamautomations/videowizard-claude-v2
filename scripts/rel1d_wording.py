"""Release 1 (SK, 20 Nov 2026, "go ahead"): a layout is checked before its card is shown. On the first real step 7 the operator approved 19
layout drawings, then the fresh checkers failed 13 of the first 15 and each rebuilt layout came back as a new card. The served text and the
helper texts said to ask the operator as soon as the shot was drawn.

In v3.json, part `later`, one sentence replaced (the replaced words are in server/retired-sentences.json): `vw visuals next` asks the operator
whether the shot is laid out right only after a fresh checker passed that layout; the checkers of the layouts are started together, before any
layout card is shown; the operator sees only layouts that passed.
In the plugin: the guide skill's row of the shot's drawing and its paragraph of the shot's drawing, and the first line of `vw-guide-check`.
Registered in scripts/c1_split_v3.py after rel1c. Exact anchors, each found once; applying twice changes nothing.
Run once: python scripts/rel1d_wording.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'server' / 'procedures' / 'v3.json'

ASK = 'and `vw visuals next` asks the operator whether the shot is laid out right (`vw guide drawing`): no still before their Yes;'   # design/200
ASK_NEW = ('and, only after a fresh checker passed that layout, `vw visuals next` asks the operator whether the shot is laid out right (`vw guide drawing`): '
           'the checkers of the layouts are started together, in one message, before any layout card is shown, and the operator sees only layouts that passed; '
           'no still before their Yes;')
PAIRS = [('later', ASK, ASK_NEW)]   # (the part, the sentence as it is, the sentence as it becomes)

ROW_OLD = 'The operator approves it in the chat (`vw visuals next`),'
ROW_NEW = ('Only after a fresh checker has passed the layout (row 3: the checkers of all the layouts are started together, in one message, before any layout '
           'card is shown), the operator approves it in the chat (`vw visuals next`),')
PARA_OLD = '- The operator approves the drawing before the still. A correction changes the scene, and the new scene is drawn and approved again.'
PARA_NEW = ('- The operator sees the drawing only once a fresh checker has passed the layout, and approves it before the still. A correction changes the scene, '
            'and the new scene is drawn, checked and approved again.')
CHECK_OLD = 'You check the guide of one AI video shot before anything is paid for.'
CHECK_NEW = CHECK_OLD + " Your check comes first: the operator is shown the shot's layout drawing only after it passes."
HELPERS = [('skills/guide/SKILL.md', ROW_OLD, ROW_NEW), ('skills/guide/SKILL.md', PARA_OLD, PARA_NEW), ('agents/vw-guide-check.md', CHECK_OLD, CHECK_NEW)]   # (file under plugin/, the old sentence, the new one)

RETIRED = ['marked (free), and `vw visuals next` asks the operator', 'The operator approves the drawing before the still.']


def apply(prompt, parts):
    """The visuals text with this sentence: the common part is returned, the parts are changed in place. Applying twice changes nothing."""
    for where, old, new in PAIRS:
        part = next(p for p in parts if p['name'] == where)
        if new in part['text']:
            continue
        if part['text'].count(old) != 1:
            sys.exit('not applied: %s: not found once: %s' % (where, old[:60]))
        part['text'] = part['text'].replace(old, new)
    return prompt


def before(stage):
    """The visuals stage as it read before this script."""
    st = json.loads(json.dumps(stage))
    for where, old, new in reversed(PAIRS):
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
    print('visuals and helpers: a layout is checked by a fresh checker before its card is shown')


if __name__ == '__main__':
    main()
