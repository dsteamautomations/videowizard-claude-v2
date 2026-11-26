"""A1 (SK, 25 Nov 2026: "Yes, checker decides"; requirements approved 26 Nov): the operator's layout drawing card is retired. When a fresh
checker passes a layout, the still is ordered: the operator is not asked about the layout drawing. Only a layout that failed its check three
times in a row is put to them, as before.

In v3.json (the replaced words are in server/retired-sentences.json):
- part `later`: the sentence of release 1 ("only after a fresh checker passed that layout, `vw visuals next` asks the operator ... no still
  before their Yes") becomes "after the check passes, order the still";
- the common part: a group is handed out for several still end-frames only (the group of layout drawings went with their card).
In the plugin: the guide skill (the row of the shot's drawing, the still's inputs, the changes line, the paragraph of the shot's drawing), the
first line of `vw-guide-check`, and two places of the command text.
Registered in scripts/c1_split_v3.py after vw25. Exact anchors, each found once; applying twice changes nothing.
Run once: python scripts/a1_wording.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'server' / 'procedures' / 'v3.json'
sys.path.insert(0, str(ROOT / 'scripts'))

from rel1d_wording import ASK_NEW as ASK, CHECK_NEW as CHECK, PARA_NEW as PARA, ROW_NEW   # noqa: E402  (release 1's sentences, replaced here)
from rel2b_wording import GROUP   # noqa: E402  (release 2's sentence, shortened here)

ASK_NEW = ('and a fresh checker checks that layout (`vw guide drawing` fetches the drawing): the checkers of the layouts are started together, in one message; '
           'after the check passes, order the still: the operator is not asked about the layout drawing;')
GROUP_NEW = GROUP.replace(', or several layout drawings of AI video shots,', '')
PAIRS = [('later', ASK, ASK_NEW)]   # (the part, the sentence as it is, the sentence as it becomes)

ROW = ROW_NEW + ' or `vw guide drawing --shot S` then `vw guide drawing-approve --shot S --sha … --quote "<their words>"`. No still before their Yes.'
ROW_A1 = ('A fresh checker checks the layout (row 3: the checkers of all the layouts are started together, in one message); after the check passes, order the still. '
          'The operator is not asked about the drawing (`vw guide drawing --shot S` fetches it); only a layout that failed its check three times in a row is put to them.')
PARA_A1 = ('- Nobody approves the drawing: when a fresh checker has passed the layout, the still is ordered. The operator sees the layout under the still (the still '
           'laid over it) and says a fault of the layout there; the scene is then changed, drawn and checked again.')
CHECK_A1 = CHECK.replace(" Your check comes first: the operator is shown the shot's layout drawing only after it passes.",
                         ' Your check decides: when it passes, the still is ordered and the operator is not asked about the layout.')
HELPERS = [   # (file under plugin/, the old sentence, the new one)
    ('skills/guide/SKILL.md', ROW, ROW_A1),
    ('skills/guide/SKILL.md', "then the shot's two approved drawings (Images 2 and 3)", "then the shot's two drawings (Images 2 and 3)"),
    ('skills/guide/SKILL.md', "The operator sees these lines with the shot's drawing.", 'The operator sees these lines with the still.'),
    ('skills/guide/SKILL.md', PARA, PARA_A1),
    ('agents/vw-guide-check.md', CHECK, CHECK_A1),
    ('commands/vw.md', "an AI video shot's layout drawing, its still and the word to make its first take, and the recording, are asked in the chat",
     "an AI video shot's still and the word to make its first take, and the recording, are asked in the chat"),
    ('commands/vw.md', 'the server draws the shot from it and the operator approves that drawing in the chat before any still, or `guide drawing`, `guide drawing-approve`)',
     "the server draws the shot from it; nobody approves that drawing: the still is ordered once the layout's check has passed; `guide drawing` fetches it)"),
]

RETIRED = ['no still before their Yes', 'asks the operator whether the shot is laid out right', 'before any layout card is shown', 'or several layout drawings of AI video shots',
           "the operator is shown the shot's layout drawing only after it passes", 'the operator approves that drawing in the chat before any still']


def apply(prompt, parts):
    """The visuals text with these sentences: the common part is returned, the parts are changed in place. Applying twice changes nothing."""
    for where, old, new in PAIRS:
        part = next(p for p in parts if p['name'] == where)
        if new in part['text']:
            continue
        if part['text'].count(old) != 1:
            sys.exit('not applied: %s: not found once: %s' % (where, old[:60]))
        part['text'] = part['text'].replace(old, new)
    if GROUP not in prompt and GROUP_NEW not in prompt:
        sys.exit('not applied: the group sentence is not in the common part')
    return prompt.replace(GROUP, GROUP_NEW)


def before(stage):
    """The visuals stage as it read before this script (for the tests of the earlier scripts)."""
    st = json.loads(json.dumps(stage))
    st['prompt'] = st['prompt'].replace(GROUP_NEW, GROUP)
    for where, old, new in PAIRS:
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
    raw = rp.read_bytes()
    r = json.loads(raw.decode('utf-8'))
    r['sentences'] += [s for s in RETIRED if s not in r['sentences']]
    rp.write_text(json.dumps(r, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\r\n' if b'\r\n' in raw else '\n')
    print('visuals and helpers: the layout drawing card is retired; after the check passes, the still is ordered')


if __name__ == '__main__':
    main()
