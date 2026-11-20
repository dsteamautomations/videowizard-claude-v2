"""Layout B (SK, 20 Nov 2026): the layout video and the check frames are rendered flat (Blender Workbench: flat colours, thin black outlines); the
first frame, from which the still is made, stays EEVEE. A box person gains a purple back mark, so the back reads by its colour in a flat render.

The served visuals text (v3.json) does not describe the guide's look and is unchanged: `apply` changes nothing there.
In the plugin: the checker's line on what the check frames show (the replaced line is in server/retired-sentences.json), with the take's and the
still's older sentences on the marks (Python constants in server/app/guide.py, replaced there) retired by name.
Registered in scripts/c1_split_v3.py after rel4. Exact anchors, each found once; applying twice changes nothing.
Run once: python scripts/layoutb_wording.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CHECK_OLD = 'They show plain coloured boxes: box people with a black face mark and chest mark, the set as boxes.'
CHECK_NEW = ('They show the guide as its video shows it: plain boxes in flat colours with thin black outlines (the outlines only separate the boxes and are never a fault); '
             'box people with a black face mark and chest mark, a purple back mark and, when the scene has stripes, a yellow stripe down each side; the set as boxes.')
HELPERS = [('agents/vw-guide-check.md', CHECK_OLD, CHECK_NEW)]   # (file under plugin/, the old sentence, the new one)

RETIRED = [CHECK_OLD,
           'The small black squares on box people show which way each person faces.',                                  # the still's opening, before layout B
           'The small black squares on box people mark their face and chest, so they show which way each person faces.',   # the take's opening, before layout B
           "the thin stripe down the side of each box person marks that person's side."]                                # the stripe, its colour unnamed


def apply(prompt, parts):
    """The visuals text with this change: nothing in v3.json changes (the served text does not describe the guide's look)."""
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
    print('layout B: the checker told what the flat check frames show; the older mark sentences retired')


if __name__ == '__main__':
    main()
