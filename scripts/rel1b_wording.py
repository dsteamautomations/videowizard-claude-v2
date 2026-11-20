"""Release 1, rows B1 and D (SK, 20 Nov 2026): one click against the check, and the lessons of step 6 carried into step 7, in the served text.

In v3.json, part `later`:
- B1: "Select (with their reason when the check did not pass it)" is replaced: on the pages of steps 6 and 7 the check's warning is in view
  before the buttons, and Yes or Select is one click whatever the check says (recorded as approved against the check; no second question,
  no typed reason); rejecting needs the operator's words. The replaced words are in server/retired-sentences.json.
- D1: after release 1 (A)'s sentence on "na": the checkers are started together, in one message, and the next-step line names what can start now.
- D2, D4: after the sentence on a second take: the cards before a take come in two batches in film order (every still, then every word to
  shoot); the two limits of step 7 the text did not name (the pictures of a still, the cost limit); the others are already there.
Nothing else is replaced: the other sentences are added. The page's words, the refusals and the next-step lines are Python constants
(server/app/pictures.py, takes.py, guide.py, visuals_stage.py) and are not this script's.
Registered in scripts/c1_split_v3.py after release 1 (A)'s script. Exact anchors, each found once; applying twice changes nothing.
Run once: python scripts/rel1b_wording.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'server' / 'procedures' / 'v3.json'

SELECT = 'in one visit: Select (with their reason when the check did not pass it), Make another, or Reject;'   # design/222
SELECT_NEW = ("in one visit: Select, Make another, or Reject; on the pages of steps 6 and 7 the check's warning is in view and Yes or Select is one click "
              'whatever it says, recorded as approved against the check (no second question, no typed reason); rejecting needs their words;')
NA = 'A line of any of Claude\'s lists may also be answered "na", it does not apply here, with one sentence why; `how` says when.'   # release 1 (A)
NA_NEW = (NA + " Start the checkers of the stills and of the takes together, in one message: `vw visuals next` names what can start now.")
AGAIN = 'say what caused the fault (`vw guide cause`), change that one thing, then `vw guide shoot --shot S`.'   # design/222
AGAIN_NEW = (AGAIN + " The cards before a take come in two batches, in film order: every still's card, each with Claude's check, then every word to shoot: "
             "have every still made before any word to shoot is asked. A still takes at most 16 pictures, the guide's frame and the shot's two drawings among "
             'them; the cost limit of the film is tested before every still and every take, and only the owner can change it.')
YES = 'no still before their Yes;'   # design/200
YES_NEW = (YES + ' in the scene file `changed_from_plan` is a list of at most ten strings, each one sentence of at most 300 characters, never an object, and `[]` when '
           'nothing changed;')   # D4b: 17 scene files were refused for this field's form on the first real run of step 7
PAIRS = [('later', SELECT, SELECT_NEW), ('later', NA, NA_NEW), ('later', AGAIN, AGAIN_NEW), ('later', YES, YES_NEW)]   # (the part, the sentence as it is, the sentence as it becomes)

FORM = 'a list of at most ten strings, each one plain sentence of at most 300 characters'
LIST_OLD = 'list each change in `changed_from_plan`.'
LIST_NEW = ('list each change in `changed_from_plan`: ' + FORM + ' saying what the plan had, what the scene has and why, never an object: '
            '`["The plan had the person at the right of the table; the scene has them at its left, facing right, so the working hand is toward the camera."]`; '
            'with nothing changed send `[]`.')
SEES_OLD = "The operator sees these lines with the shot's drawing."
SEES_NEW = SEES_OLD + ' Its exact form: ' + FORM + ', never an object; `"changed_from_plan": []` when nothing changed.'
HELPERS = [('agents/vw-guide-scene.md', LIST_OLD, LIST_NEW), ('skills/guide/SKILL.md', SEES_OLD, SEES_NEW)]   # (file under plugin/, the old sentence, the new one)

RETIRED = ['Select (with their reason when the check did not pass it)',   # B1: one click, no typed reason (design/35 row 276)
           'list each change in `changed_from_plan`.']                    # D4b: the helper's sentence gave no form


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
    print('visuals: one click against the check; step 7: the checkers together, the cards in two batches, its limits')


if __name__ == '__main__':
    main()
