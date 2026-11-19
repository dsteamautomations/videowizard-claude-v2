"""design/221 after phase 1 (SK, 19 Nov 2026): the critic's four points on phase 1, then phase 2 (the fact check: rows 9, 11, 12, 13, 17).

In plugin/: the rule writer is told plainly that every line of rules.md is a rule (the critic's A3). Phase 2, in v3.json and plugin/: the same set
of frames for every check, and the last frame of the shot a drawing continues from (row 12); each rule a must or a should, only a failed must sends
the drawing back, failed shoulds are notes (row 11); "not seen" answered by the same checker in the same round (row 12); rounds 2 and 3 answer what
failed and what the fix touched (row 13); a short label of this shot only is a must (row 17); the corner note is drawn by the server, never in the
labels, never in a rule (row 9). The replaced sentences are in server/retired-sentences.json. Registered in scripts/c1_split_v3.py after
design/221's script. Exact anchors, each found once; run once: python scripts/d221b_wording_v3.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'server' / 'procedures' / 'v3.json'

RULES_ONLY = 'rules.md holds rules only: a list under a Questions or Notes heading in it is refused at upload.'

FRAMES = 'the first frame, each cue, the middle of each move, the last frame, and a close-up of each labelled part'
SNAP_OLD = ('Snapshot each shot at its beats with crops of the parts its rules name (`vw motion snapshot --shot S --at … --crop …`), then a fresh '
            '`vw-motion-check` helper per shot with the round number,')
SNAP_NEW = (f'Snapshot each shot at the same set of frames every time: {FRAMES} (`vw motion snapshot --shot S --at … --crop …`). When the brief says '
            '"Continues from <shot>", take that shot\'s last frame too (`vw motion snapshot --shot <that shot> --at <its last second>`), copy it to '
            'work/motion/S/refs/continues-from.png and tell the builder and the checker. Then a fresh `vw-motion-check` helper per shot with the round number,')
LOOP_OLD = 'Failed rules go to a new `vw-motion-shot` helper with only those rules; at most two redo rounds, then show the operator the open rules.'
LOOP_NEW = ('Each rule is a must or a should (rules.md marks it). Only a failed must sends the drawing back: the failed musts go to a new `vw-motion-shot` '
            'helper, with the failed shoulds as notes to fix in the same redo. A verdict with no failed must is clean ("Passed, N notes"); the notes are '
            'shown with the drawing. A rule the checker answers "not seen" is neither a pass nor a fail: take the frames the verdict asks for, give them '
            'to the same checker for those rules only, and send its verdict with the same round number; nothing is rebuilt. In round 2 or 3, give the '
            'checker the rules that failed before and the builder\'s list of what it changed: it answers those rules and the rules about what the fix '
            'touched, and a rule it leaves out keeps its pass. A label of this shot only that the check finds on screen too short is a must too. At most '
            'two redo rounds caused by a must, then show the operator the open musts.')
LABELS_OLD = 'Put `scene_motion: {sha256, labels, cues}` on the shot (labels word for word;'
LABELS_NEW = ('Put `scene_motion: {sha256, labels, cues}` on the shot (labels word for word, never the spec\'s not-to-scale note: the server draws it '
              'in the lower right corner of every frame;')

PAIRS = [   # (where: 'common' or a part's name, the old sentence, the new one)
    ('later', SNAP_OLD, SNAP_NEW),
    ('later', LOOP_OLD, LOOP_NEW),
    ('later', LABELS_OLD, LABELS_NEW),
]

CHECK_OLD = ('Then mark every rule pass or fail (each rule\'s words copied from rules.md exactly as they are written: the server holds that list and refuses '
             'a verdict that leaves a rule out or changes its words), with where in which frame you saw it, and for a fail the exact change that would make '
             'it pass. A rule you cannot judge from these frames fails, with "not visible: snapshot at <second> or a crop of <part> needed" as its fix. Add a '
             'rule of your own only for a plain fault a viewer would notice that no rule covers; give it the next number and the group "seen".')
CHECK_NEW = ('Each rule in rules.md starts with `must:` or `should:`; the server keeps that class, so copy the rule\'s words without it. Then mark every rule '
             'pass, fail or "not seen" (each rule\'s words copied from rules.md exactly as they are written after its class: the server holds that list and '
             'refuses a verdict that leaves a rule out or changes its words), with where in which frame you saw it, and for a fail the exact change that '
             'would make it pass. A rule you cannot judge from these frames is "not seen": write "pass": "not seen" and in "need" the frame or crop that '
             'would show it ("a snapshot at 2.4 s", "a crop of the lower left joint"); it is neither a pass nor a fail, and you will be given that frame '
             'and asked again for those rules only. In round 2 or 3 you are given the rules that failed before and what the fix changed: answer those '
             'rules and every rule about what the fix touched; you may leave out a rule that passed before and is not about the fix (it keeps its pass), '
             'and do not re-measure a look rule that passed. Still look at the whole frame for a must-kind fault: a wrong count, a wrong fact, a part '
             'that reads as something else, a label that cannot be read. Add a rule of your own only for a plain fault a viewer would notice that no rule '
             'covers; give it the next number and the group "seen". It is a should, unless it is one of those four must kinds: then write "class": '
             '"must" and in "kind" that kind in one line.')
LOOK_OLD = 'Look closely at every label, letter by letter, and at every part the rules name: joints, edges, where things meet.'
LOOK_NEW = (LOOK_OLD + f' The frames are the same set for every check: {FRAMES}. When the brief says "Continues from <shot>", you are also given that '
            'shot\'s last frame (work/motion/<shot>/refs/continues-from.png): compare against it only what the rules say continues. The corner note '
            '("Illustrative, not to scale" or the like) is drawn by the server: never fail its words, size or place; if a part of the drawing runs under '
            'it, add that as a should.')
JSON_OLD = '"fix": "for a fail: the exact change"}]}'
JSON_NEW = '"fix": "for a fail: the exact change", "need": "for not seen: the frame or crop needed"}]}'
GROUPS_OLD = ('Write `work/motion/<shot>/rules.md`: numbered rules, one line each, each one a thing a stranger could check by looking at a frame, in three '
              'groups:')
GROUPS_NEW = ('Write `work/motion/<shot>/rules.md`: numbered rules, one line each, each one a thing a stranger could check by looking at a frame. Start '
              'every rule with `must:` or `should:`. A must sends the drawing back when it fails: a wrong fact, size, proportion, count or material; a '
              'label\'s words wrong, covered or unreadable; a part missing or extra; the narration\'s claim not shown; text other than the brief\'s; a part '
              'the narration is about that reads as something else; a part that changes when it must stay; a label on screen too short to read; anything '
              'that breaks the film. A should is a note the builder fixes when it can: a small break in an arrow that still reaches its end; a part '
              'slightly off its place or touching another symbol; how a background symbol the narration is not about looks; a fault under about half a '
              'second during a camera move or a fade, with every label still readable; spacing, line weight, style, a neutral colour the palette does not '
              'name, how a highlight is made when it reads. The rules come in three groups:')
NUMBERS_OLD = 'such as "three quarters" of your own).'
NUMBERS_NEW = (NUMBERS_OLD + ' Write no rule about the corner note the brief says the server draws ("Illustrative, not to scale" or the like): the server '
               'sets its words, size and place.')
SNAPSKILL_OLD = ('4. `vw motion snapshot --shot <shot> --at <t1,t2,…>`: PNGs of the moments that matter (each build step, each label landing, the end) '
                 'saved to `snapshots/`.')
SNAPSKILL_NEW = f'4. `vw motion snapshot --shot <shot> --at <t1,t2,…>`: PNGs saved to `snapshots/`, always the same set: {FRAMES} (`--crop`).'
LABEL_ID = 'Put each label in an element with a stable `id`.'
READ_OLD = '1. Read `brief.md` and `rules.md`, look at `refs/`, read the two references.'
READ_NEW = (READ_OLD + ' When the brief says "Continues from <shot>", the main assistant puts that shot\'s last frame in `refs/continues-from.png`: '
            'start your drawing where it ends.')
REDO_OLD = 'If you were given a list of failed rules from a fact check, change only what those rules name,'
REDO_NEW = ('If you were given a list of failed rules from a fact check (the musts, and the shoulds as notes to fix in the same go), change only what '
            'those rules name,')

HELPERS = [   # (file under plugin/, the old sentence, the new one)
    ('agents/vw-motion-rules.md', RULES_ONLY, RULES_ONLY + ' Every line of rules.md is a rule: no heading, question, note or colour to add goes in it.'),
    ('agents/vw-motion-rules.md', GROUPS_OLD, GROUPS_NEW),
    ('agents/vw-motion-rules.md', NUMBERS_OLD, NUMBERS_NEW),
    ('agents/vw-motion-check.md', CHECK_OLD, CHECK_NEW),
    ('agents/vw-motion-check.md', LOOK_OLD, LOOK_NEW),
    ('agents/vw-motion-check.md', JSON_OLD, JSON_NEW),
    ('agents/vw-motion-shot.md', REDO_OLD, REDO_NEW),
    ('skills/motion/SKILL.md', SNAPSKILL_OLD, SNAPSKILL_NEW),
    ('skills/motion/SKILL.md', LABEL_ID, LABEL_ID + ' The corner note the brief names is drawn by the server in the lower right corner: never draw it, and keep '
     'that corner free.'),
    ('skills/motion/SKILL.md', READ_OLD, READ_NEW),
]

RETIRED = ['Snapshot each shot at its beats with crops of the parts its rules name', LOOP_OLD, 'A rule you cannot judge from these frames fails',
           'PNGs of the moments that matter (each build step, each label landing, the end)']


def apply(prompt, parts):
    """The visuals text with this design's sentences: the common part is returned, the parts are changed in place. Applying twice changes nothing."""
    for where, old, new in PAIRS:
        part = None if where == 'common' else next(p for p in parts if p['name'] == where)
        text = prompt if part is None else part['text']
        if new in text:
            continue
        if text.count(old) != 1:
            sys.exit('not applied: %s: not found once: %s' % (where, old[:60]))
        text = text.replace(old, new)
        if part is None:
            prompt = text
        else:
            part['text'] = text
    return prompt


def before(stage):
    """The visuals stage as it read before this script."""
    st = json.loads(json.dumps(stage))
    for where, old, new in reversed(PAIRS):
        if where == 'common':
            st['prompt'] = st['prompt'].replace(new, old)
        else:
            part = next(p for p in st['parts'] if p['name'] == where)
            part['text'] = part['text'].replace(new, old)
    return st


def now(file, text):
    """An earlier script's sentence for one plugin file as it reads after this script (for that script's test)."""
    for f, old, new in HELPERS:
        if f == file and new not in text:
            text = text.replace(old, new)
    return text


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
    print('visuals: design/221 after phase 1')


if __name__ == '__main__':
    main()
