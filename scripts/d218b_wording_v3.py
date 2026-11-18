"""design/218b (SK, 18 Nov 2026): instruction version 3, the visuals stage, and three motion texts: a part seen from another direction of
view (from the side, from above, cut across, cut along) or at another scale is the same part, not a change of shape. Each drawing follows its
own approved spec and view; the assistant does not ask, makes the change of view readable and records one plain line (`vw motion note`).
Only two approved specs that truly contradict are asked. No sentence is retired: no text said a part must look the same in every drawing
(the rule writer wrote such rules on its own). Registered in scripts/c1_split_v3.py after design/218's script.
Run once: python scripts/d218b_wording_v3.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'server' / 'procedures' / 'v3.json'

ANCHOR = 'Only a real hue, or a colour a brand colour rule of the film could break, is asked (then `--quote`).'   # design/218's last sentence of the colour rule
VIEW = ('A part that two drawings show from different directions (from the side, from above, cut across, cut along) or at different scales is the '
        'same part, not a change of shape, and is never asked: each drawing follows its own approved spec and view, the later one makes the change of '
        'view readable (the view visibly turns or cuts, or a short label such as "section" where the spec\'s labels allow it; never a part that morphs '
        'into another shape), and you record one plain line: `vw motion note --shot D1,D2 --text "The steel is shown from the side in D1 and cut '
        'across here."` (carried in those drawings\' briefs, shown under Details on them; where a spec does not state its view, the line states it). '
        'A drawing that passed its fact check is not redrawn to match another view. Only two approved specs that truly contradict (the same view '
        'and scale, and a different count, size, material or arrangement of the same part) are asked, naming both specs and what differs.')
PAIRS = [('later', ANCHOR, ANCHOR + ' ' + VIEW)]
HELPERS = [   # (file under plugin/, the old sentence, the new one)
    ('agents/vw-motion-rules.md', 'Where the brief itself asks for something untrue or doubtful,',
     'A part another drawing shows from another direction (from the side, from above, cut across, cut along) or at another scale is the same part, '
     "not a change of shape: this drawing follows its own spec and stated view, so a rule that links drawings says what is the same and how it is "
     'seen here ("the steel is the same bars as in drawing D1, here seen cut across"), never "the steel looks as in drawing D1", and it is never '
     'a question. Where the brief itself asks for something untrue or doubtful,'),
    ('agents/vw-motion-check.md', 'Read the brief\'s "Motion style" part:',
     "Judge each part against this drawing's own spec and its stated view: the same part drawn from another direction or at another scale in "
     'another drawing is never a fault here. Read the brief\'s "Motion style" part:'),
    ('skills/motion/SKILL.md', "- Every text on screen is one of the brief's labels",
     "- A part another drawing shows from another direction or at another scale is the same part: draw it as this drawing's spec and view say, "
     'and make the change of view readable (the view visibly turns or cuts; a label such as "section" only where the brief lists it); never a '
     "part that morphs into another shape.\n- Every text on screen is one of the brief's labels"),
]


def apply(prompt, parts):
    """The visuals text with this design's sentences; the parts are changed in place. Applying twice changes nothing."""
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
    for name in sorted({h[0] for h in HELPERS}):
        _swap(ROOT / 'plugin' / name, [(old, new) for file, old, new in HELPERS if file == name], 'plugin/' + name)
    print('visuals: design/218b')


if __name__ == '__main__':
    main()
