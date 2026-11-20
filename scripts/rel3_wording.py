"""Release 3 (SK, 20 Nov 2026): the served words of the visuals stage for rows C1 to C4, C6, E2 and E4, and the plugin's two texts about a defect.

In v3.json, the visuals stage:
- part `later`, E4: "Nothing of this is asked one at a time during the builds." gets a path for a question nobody could foresee (asked at
  once, recommended answer first, the other builds go on); the older sentence is in server/retired-sentences.json;
- part `later`, E2: the render is named with `--wait` once;
- part `plan`, C1, C3, C4: after the sentence on the corner note and a logo: the two plan warnings and which changes ask the operator nothing;
- the common text (`prompt`), C2: after "you close your own question only by quoting their words.": the proposal that follows an answer.
In the plugin, C6: commands/vw.md and operator-CLAUDE.md say that a defect holds the shot it names, else the step.
Registered in scripts/c1_split_v3.py after rel2c. Exact anchors, each found once; applying twice changes nothing.
Run once: python scripts/rel3_wording.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'server' / 'procedures' / 'v3.json'

ONE_AT_A_TIME = 'Nothing of this is asked one at a time during the builds.'   # design/221 phase 3a
UNFORESEEN = ('Nothing known beforehand is asked one at a time during the builds. A question nobody could foresee, met in the middle of a build, is asked at once: record it '
              '(`vw visuals ask`, your recommended answer first among the choices) and run `vw visuals next`; questions that wait together are asked one after the other with '
              'no build between them, and the builds that do not depend on the answer go on.')
RENDER = 'Then `vw motion render --shot S` (free; it checks the timing).'   # design/221
RENDER_WAIT = 'Then `vw motion render --shot S --wait` (free; it checks the timing; `--wait` returns when the render is ready, as a check and a snapshot do).'
NO_TEXT = 'The corner note and a logo picture are not text the shot carries: a shot whose only text they are has `carries_text: false`.'   # fix set, the critic's points
AT_THE_PLAN = (' The plan check names a drawn shot that carries text and lists no labels (`labels_missing`), and a logo or a brand picture whose file was not given '
               '(`supplied_missing`: ask the operator for the file with the plan; it goes in in/brand/). Labels in words the plan already holds, and `carries_text: false` '
               'on such a shot, ask the operator nothing; a label in new words is asked with its gap.')
QUOTING = 'you close your own question only by quoting their words.'   # design/110 rule 0
ANSWERS = (' When their answer changes the plan, propose it with `vw visuals propose --file out/visual-plan.json --answers <the item>`: a change inside what the question '
           'names is accepted with that answer, with no second card.')
PAIRS = [('later', ONE_AT_A_TIME, UNFORESEEN), ('later', RENDER, RENDER_WAIT), ('plan', NO_TEXT, NO_TEXT + AT_THE_PLAN), (None, QUOTING, QUOTING + ANSWERS)]   # (the part, None for the common text; as it is; as it becomes)

DEFECT_OLD = 'run `vw defect --error "<message>"`, and stop.'
DEFECT_NEW = ('run `vw defect --error "<message>"` (with `--shot S` when the problem is about one shot: the server then holds only that shot), and stop the work the defect '
              'holds; with a shot named, the rest of the run goes on.')
OPERATOR_OLD = 'On any error, file a defect with `vw defect` and stop; the server refuses every write on the run until the builder marks the defect fixed.'
OPERATOR_NEW = ('On any error, file a defect with `vw defect` (naming the shot with `--shot` when it is about one shot) and stop the work it holds: the server refuses the '
                'writes of that shot, or of the whole step when no shot is named, until the builder marks the defect fixed.')
NEVER_OLD = 'or continue after a defect is filed (the server refuses every write on the run until the builder marks the defect fixed).'
NEVER_NEW = ('or continue the work a filed defect holds (the server refuses the writes of the shot the defect names, or of the whole step when it names none, until the builder '
             'marks the defect fixed).')
HELPERS = [('commands/vw.md', DEFECT_OLD, DEFECT_NEW), ('commands/vw.md', NEVER_OLD, NEVER_NEW), ('operator-CLAUDE.md', OPERATOR_OLD, OPERATOR_NEW)]   # (file under plugin/, the old sentence, the new one)

RETIRED = [ONE_AT_A_TIME, 'the server refuses every write on the run until the builder marks the defect fixed']


def apply(prompt, parts):
    """The visuals text with these sentences: the common part is returned, the parts are changed in place. Applying twice changes nothing."""
    for where, old, new in PAIRS:
        part = next(p for p in parts if p['name'] == where) if where else None
        text = part['text'] if part else prompt
        if new in text:
            continue
        if text.count(old) != 1:
            sys.exit('not applied: %s: not found once: %s' % (where or 'the common text', old[:60]))
        if part:
            part['text'] = text.replace(old, new)
        else:
            prompt = text.replace(old, new)
    return prompt


def before(stage):
    """The visuals stage as it read before this script."""
    st = json.loads(json.dumps(stage))
    for where, old, new in reversed(PAIRS):
        if where:
            part = next(p for p in st['parts'] if p['name'] == where)
            part['text'] = part['text'].replace(new, old)
        else:
            st['prompt'] = st['prompt'].replace(new, old)
    return st


def main():
    raw = P.read_bytes()
    d = json.loads(raw.decode('utf-8'))
    st = next(s for s in d['stages'] if s['name'] == 'visuals')
    st['prompt'] = apply(st['prompt'], st['parts'])
    P.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\r\n' if b'\r\n' in raw else '\n')   # the file keeps its line ends
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
    print('visuals: a question nobody could foresee; the render with --wait; the plan warnings and the changes that ask nothing; the proposal that follows an answer; a defect holds what it names')


if __name__ == '__main__':
    main()
