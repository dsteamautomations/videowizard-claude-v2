"""Fix set phase 3 (SK, 19 Nov 2026): the stills and the smaller faults of VW-24's redo of step 6, in the served text and the helpers' texts.

In v3.json: the still pictures are ordered at the start in one call, from a file one `vw-still-prompts` helper writes, and the text shows that
file with every field as text (A2.1, M7); a still another picture is made from is asked early on a chat card and its approval also allows it as
the parent (A2.2); one snapshot call takes at most 12 frames (A3.6, M5); the corner note and a logo picture are not text a drawn shot carries
(A3.3). One sentence is replaced (the single-picture command in the stills sentence); the others are added after their anchor. In plugin/: the
checker and the builder are told the frame limit, the builder and the command text that a refused call is never sent again unchanged (M6).
The helper `plugin/agents/vw-still-prompts.md` is a new file, written with this set. The replaced sentence is in server/retired-sentences.json.
Registered in scripts/c1_split_v3.py after fix set phase 2's script. Exact anchors, each found once; applying twice changes nothing.
Run once: python scripts/fixset3_wording.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'server' / 'procedures' / 'v3.json'

STILLS_OLD = ('order the still pictures at the start of the step, at the same time as the drawn graphics are begun (`vw visuals image --shot S --element E --kind '
              'keyframe --prompt "…"`); they need nothing from the drawings,')
STILLS_NEW = ('order the still pictures at the start of the step, all of them in one call (`vw visuals image --file out/images.json`), at the same time as the drawn '
              'graphics are begun: one `vw-still-prompts` helper, started beside the parts helper, writes that file, one row per still, every field as text '
              '(`[{"element": "E1", "shot": "S1", "kind": "keyframe", "name": "still-S1", "prompt": "…"}]`); they need nothing from the drawings (a still another '
              'picture is made from is asked early: order the picture made from it; the server then puts the still on a chat card, and its approval also allows it as '
              'the parent),')
FRAMES = 'and a close-up of each labelled part (`vw motion snapshot --shot S --at … --crop …`).'
FRAMES_NEW = FRAMES + ' One call takes at most 12 frames: ask the rest in a second call.'
LABELS = '`vw motion brief` is refused while a drawn shot that carries text has none.'
LABELS_NEW = (LABELS + ' The corner note and a logo picture are not text the shot carries: a shot whose only text they are has `labels: []` and is not asked for '
              'labels.')

PAIRS = [   # (the part's name, the old sentence, the new one)
    ('later', STILLS_OLD, STILLS_NEW),
    ('later', FRAMES, FRAMES_NEW),
    ('plan', LABELS, LABELS_NEW),
]

SET = 'The frames are the same set for every check: the first frame, each cue, the middle of each move, the last frame, and a close-up of each labelled part.'
SET_NEW = SET + ' A snapshot call takes at most 12 frames: more frames than that, asked in `need`, come in two calls of 12 or fewer.'
ONLY = "never `npx`, `node` or another shot's folder."   # the end of "Run only `vw motion` commands for this shot …" (an earlier script's sentence starts here)
ONLY_NEW = (ONLY + ' `vw motion snapshot` takes at most 12 frames in one call (`--at`): for more, ask in two calls of 12 or fewer. A refused call is never sent again '
            'unchanged: read the refusal and change the call.')
REFUSED = '- `refused`: read `message`, fix the input if it is yours, otherwise tell the operator.'
REFUSED_NEW = REFUSED + ' Never send a refused call again unchanged.'

HELPERS = [   # (file under plugin/, the old sentence, the new one)
    ('agents/vw-motion-check.md', SET, SET_NEW),
    ('agents/vw-motion-shot.md', ONLY, ONLY_NEW),
    ('commands/vw.md', REFUSED, REFUSED_NEW),
]

RETIRED = ['order the still pictures at the start of the step, at the same time as the drawn graphics are begun (`vw visuals image --shot S']   # A2.1: all of them in one call, from the file


def apply(prompt, parts):
    """The visuals text with this set's sentences: the common part is returned, the parts are changed in place. Applying twice changes nothing."""
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
    print('visuals and helpers: fix set phase 3')


if __name__ == '__main__':
    main()
