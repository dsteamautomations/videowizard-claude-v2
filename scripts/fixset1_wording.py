"""Fix set phase 1 (SK, 19 Nov 2026): the proper fixes for the three hotfixes of VW-24's step 6, in the helpers' texts.

In plugin/ only; v3.json is not changed, so this script is not registered in scripts/c1_split_v3.py and the visuals word pin stays.
B3: the rule writer marks each rule `(still)` or `(motion)` after its class; the checker of a still reads rules-still.md, the server's list of the
musts a still can show. B2 and A3.2: a shared part names its view with data-view; the builder places the view its drawing shows.
Sentences are added after their anchor, none replaced, so earlier scripts' tests hold. Exact anchors, each found once; applying twice changes
nothing. Run once: python scripts/fixset1_wording.py"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CLASS = 'Start every rule with `must:` or `should:`.'
CLASS_NEW = (CLASS + ' After the class, in brackets, mark what shows the rule: `(still)` when the finished picture shows it, standing still as it is at the '
             'end of the shot; `(motion)` when only the moving drawing shows it (what appears when, how a thing moves or changes, a camera move or the lack '
             'of one, a time on screen). So a rule starts `must (still):`, `must (motion):`, `should (still):` or `should (motion):`. The still end-frame is '
             'checked on the `(still)` musts alone: a rule that needs the motion to be judged is never marked `(still)`.')
STILL = 'a rule about motion or timing is not answered on the still (what appears when, how a thing moves, a camera move).'
STILL_NEW = (STILL + ' When `work/motion/<shot>/rules-still.md` is there, it is the server\'s list for the still: the must rules a still can show, without '
             'the rules only motion shows. On a still read it in place of rules.md and answer every rule in it and no other.')
ELEMENT = '`data-element="<the thing\'s id>"` when it draws a thing of the plan (the brief lists the ids).'
ELEMENT_NEW = (ELEMENT + ' A thing the drawings show in more than one view (cut across in one, from above in another) is one symbol for each view, each '
               'with the same `data-element` and with `data-view` naming its view in the specs\' own word: `cutaway`, `plan`, `side` or `elevation`. Each '
               'brief then tells its drawing which view to place.')
OWN = 'say so in REVIEW.md and give it back to the main assistant; do not draw your own.'
OWN_NEW = (OWN + ' Where a thing has several views among the parts (cut across, from above), place the view this drawing shows: the line names it, and '
           'one view of a thing is enough.')

HELPERS = [   # (file under plugin/, the anchor, the anchor with the new sentences after it)
    ('agents/vw-motion-rules.md', CLASS, CLASS_NEW),
    ('agents/vw-motion-check.md', STILL, STILL_NEW),
    ('agents/vw-motion-parts.md', ELEMENT, ELEMENT_NEW),
    ('skills/motion/SKILL.md', OWN, OWN_NEW),
]


def now(file, text):
    """An earlier script's sentence for one plugin file as it reads after this script (for that script's test)."""
    for f, old, new in HELPERS:
        if f == file and new not in text:
            text = text.replace(old, new)
    return text


def main():
    for file, old, new in HELPERS:
        path = ROOT / 'plugin' / file
        raw = path.read_bytes()   # bytes in and out, so the file keeps its line ends
        end = '\r\n' if b'\r\n' in raw else '\n'
        text = raw.decode('utf-8').replace('\r\n', '\n')
        if new not in text:
            if text.count(old) != 1:
                sys.exit('not applied: plugin/%s: not found once: %s' % (file, old[:60]))
            path.write_bytes(text.replace(old, new).replace('\n', end).encode('utf-8'))
    print('helpers: fix set phase 1')


if __name__ == '__main__':
    main()
