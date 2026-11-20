"""Release 1, section A (SK, 20 Nov 2026): Claude's check, everywhere: the third answer and its guard, and step 7's still, in the served
text and the helper texts.

In v3.json, part `later`: after the sentence on "not seen", a rule that does not apply to a drawing is answered "na" with `why` (A3, A4);
after the sentence on a take's check, the still an AI video shot starts from is checked the same way before its card (A1), and a line of
any of Claude's lists may be answered "na" (A3). Nothing is replaced there: the sentences are added. In the helper texts
(vw-picture-look, vw-take-look, vw-set-look, vw-motion-check) and the guide skill the same points, said where the helper answers its
lines, with the guard and its two examples (A4); the picture helper's description names step 7's still, and the description it replaces
is in server/retired-sentences.json. The points to judge by (`how`), the refusals and the page's words are Python constants
(server/app/pictures.py, ref_sets.py, visuals_stage.py) and are not this script's.
Registered in scripts/c1_split_v3.py after the fix set's last script. Exact anchors, each found once; applying twice changes nothing.
Run once: python scripts/rel1a_wording.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'server' / 'procedures' / 'v3.json'

SEEN = 'and send its verdict with the same round number; nothing is rebuilt.'   # design/221 row 12
SEEN_NEW = (SEEN + ' A rule that does not apply to this drawing is answered "na" with `why`: it is recorded once as a note, and nothing is fetched or rebuilt for it.')
TAKE = 'A take whose check does not come within 30 minutes is shown as not checked.'   # design/222
TAKE_NEW = (TAKE + ' The still an AI video shot starts from is checked the same way before its card: it is listed with the pictures (kind `start`). '
            'A line of any of Claude\'s lists may also be answered "na", it does not apply here, with one sentence why; `how` says when.')
PAIRS = [('later', SEEN, SEEN_NEW), ('later', TAKE, TAKE_NEW)]   # (the part, the sentence as it is, the sentence with what is added)

GUARD = (' Or `"pass": "na"`, "does not apply here", with one sentence in `seen` saying why: only when this view cannot show the thing the line asks about, or the line is '
         'about another thing than this picture shows (a line about how a hand holds a tool, where no hand is in the frame; a line about the whole room, on a close view '
         'of one object). Never for something that is in view: that passes or fails.')
PIC_OLD = '`pass` true or false, from what you see in the picture, never from the request.'
TAKE_OLD = '`pass` true or false, from what the frames show, never from the request. Be literal.'
SET_OLD = 'Answer every line of every picture, `pass` true or false, from what you see in the picture, never from the request or the notes.'
PIC_WAS = "description: VideoWizard's checker of the pictures of step 6 (a still, a step of a graphic, the style sheet, a component)."
PIC_IS = "description: VideoWizard's checker of the pictures of steps 6 and 7 (a still, a step of a graphic, the style sheet, a component, the still an AI video shot starts from)."
ROW_OLD = 'Each row of `listed.json` names its file.'
ROW_NEW = (ROW_OLD + ' A row of kind `start` is the still an AI video shot starts from: its `overlay` input shows it under the red outlines of the layout, and its `layout` '
           'input is the layout alone.')
RULE_OLD = 'it is neither a pass nor a fail, and you will be given that frame and asked again for those rules only.'
RULE_NEW = (RULE_OLD + ' A rule that does not apply to this drawing is "na": write "pass": "na" and in "why" one sentence saying why. Give it only when this drawing\'s view '
            'cannot show the thing the rule asks about, or the rule is about another thing than this drawing shows; never for something that is in view, and never for a '
            'rule that passed or failed in an earlier round. It is recorded once as a note for the operator: no frame is taken and no round is counted for it.')
FILE_OLD = '"need": "for not seen: the frame or crop needed"}'
FILE_NEW = '"need": "for not seen: the frame or crop needed", "why": "for na: why it does not apply"}'
SKILL_OLD = 'say what to look for: every person and thing sits on the red outlines.'
SKILL_NEW = (SKILL_OLD + ' Claude checks the still first: `vw visuals pictures --looks` lists it (kind `start`) with its lines; its card comes with the check, or after 30 '
             'minutes as not checked.')

HELPERS = [   # (file under plugin/, the old sentence, the new one)
    ('agents/vw-picture-look.md', PIC_WAS, PIC_IS),
    ('agents/vw-picture-look.md', PIC_OLD, PIC_OLD + GUARD),
    ('agents/vw-picture-look.md', ROW_OLD, ROW_NEW),
    ('agents/vw-take-look.md', TAKE_OLD, TAKE_OLD + GUARD.replace('this view', 'these frames').replace('this picture', 'this take')),
    ('agents/vw-set-look.md', SET_OLD, SET_OLD + GUARD),
    ('agents/vw-motion-check.md', RULE_OLD, RULE_NEW),
    ('agents/vw-motion-check.md', FILE_OLD, FILE_NEW),
    ('skills/guide/SKILL.md', SKILL_OLD, SKILL_NEW),
]

RETIRED = ["VideoWizard's checker of the pictures of step 6 (a still, a step of a graphic, the style sheet, a component)."]   # A1: the helper checks step 7's still too


def apply(prompt, parts):
    """The visuals text with this release's sentences: the common part is returned, the parts are changed in place. Applying twice changes nothing."""
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
    print('visuals and helpers: the third answer and its guard, step 7\'s still under Claude\'s check')


if __name__ == '__main__':
    main()
