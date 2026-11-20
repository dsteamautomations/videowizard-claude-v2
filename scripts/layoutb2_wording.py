"""Layout B, second part (SK, 20 Nov 2026): 1. every box person has the yellow side stripes in the flat look (the layout video and the check
frames); 2. a piece of the set or a prop whose facing matters may name its `front`, and then carries a black front panel and a purple back panel.

The served visuals text (v3.json) does not describe the scene description or the guide's look and is unchanged: `apply` changes nothing there.
In the plugin: the checker's line on what the check frames show (layout B's line, now retired), the scene writer's sentence on `front`, and the
skill's schema line. Registered in scripts/c1_split_v3.py after layoutb. Exact anchors, each found once; applying twice changes nothing.
Run once: python scripts/layoutb2_wording.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from layoutb_wording import CHECK_NEW as CHECK_OLD   # noqa: E402  (layout B's line, replaced here)

CHECK_NEW = ('They show the guide as its video shows it: plain boxes in flat colours with thin black outlines (the outlines only separate the boxes and are never a fault); '
             'box people with a black face mark and chest mark, a purple back mark and a yellow stripe down each side; the set as boxes.')
CHECK_FRONT = 'A thing whose facing matters may carry a black panel on its front and a purple panel on its back: a layout aid, never a fault.'
WRITER_AT = 'Mark a piece that is a thing with an approved drawing set with `drawn_as`.'
WRITER = ('Set `"front": [x, y]` (its front side, written as a person\'s facing: [0, -1], [0, 1], [1, 0] or [-1, 0]) only on a piece or prop whose facing matters '
          'to the action, such as a chair one sits on, a cabinet opened from the front, a cart pushed one way or a screen that faces the camera or a person; '
          'it gets a black panel on its front and a purple one on its back. Never on a symmetric piece (a slab, a wall, a pile).')
SKILL_AT = '{"t": 3, "deg": 180}]}`.'
SKILL = ('A piece or a prop whose facing matters to the action (a chair one sits on, a cabinet opened from the front, a screen that faces someone) takes '
         '`"front": [x, y]`, its front side written as a person\'s facing: [0, -1], [0, 1], [1, 0] or [-1, 0]; it gets a black front panel and a purple back panel. '
         'Never on a symmetric piece (a slab, a wall, a pile).')
HELPERS = [('agents/vw-guide-check.md', CHECK_OLD, CHECK_NEW + ' ' + CHECK_FRONT),   # (file under plugin/, the old text, the new one)
           ('agents/vw-guide-scene.md', WRITER_AT, WRITER_AT + ' ' + WRITER),
           ('skills/guide/SKILL.md', SKILL_AT, SKILL_AT + ' ' + SKILL)]

RETIRED = [CHECK_OLD]


def apply(prompt, parts):
    """The visuals text with this change: nothing in v3.json changes (the served text does not describe the scene description)."""
    return prompt


def before(stage):
    """The visuals stage as it read before this script: the same."""
    return json.loads(json.dumps(stage))


def main():
    for f, old, new in HELPERS:
        path = ROOT / 'plugin' / f
        data = path.read_bytes()
        if new.encode('utf-8') in data:
            continue
        if data.count(old.encode('utf-8')) != 1:
            sys.exit('not applied: %s: not found once: %s' % (f, old[:60]))
        path.write_bytes(data.replace(old.encode('utf-8'), new.encode('utf-8')))   # bytes: the file keeps its line ends
    rp = ROOT / 'server' / 'retired-sentences.json'
    raw = rp.read_bytes()
    r = json.loads(raw.decode('utf-8'))
    r['sentences'] += [s for s in RETIRED if s not in r['sentences']]
    rp.write_text(json.dumps(r, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\r\n' if b'\r\n' in raw else '\n')
    print('layout B, second part: the checker, the scene writer and the skill told of the stripes in the flat look and of `front`')


if __name__ == '__main__':
    main()
