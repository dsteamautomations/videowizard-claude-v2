"""design/221 phase 3a (SK, 19 Nov 2026): the shared look (row 7), pictures to look at (row 5), the camera (section 10 with SK's ruling) and the motion
family (rows 8 and 10, design/221a F4 and F6). Every new sentence follows its anchor, so no earlier script's sentence is cut in two.

In v3.json: the planner's camera flow per drawn shot, by what the explanation is doing (plan part); the shared look recorded once before the first
brief with `vw motion note --shot all`, and the binding family with one send-back (section 11, its end). In plugin/: the skill's order of who wins,
the five extra motions, the camera flows and the ten points, the pictures to open first; the builder opens them first; the rule writer writes no
rule from the motion guidance and one must for a Fixed camera; the checker fails nothing for the motion guidance and looks for the corner box in
the still frames. The replaced sentences are in server/retired-sentences.json. Registered in scripts/c1_split_v3.py after design/221b's script.
Exact anchors, each found once; run once: python scripts/d221c_wording_v3.py"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'server' / 'procedures' / 'v3.json'

FIXED_RULE = 'The whole picture keeps its framing from the first frame to the last: nothing scales or pans the frame.'
LOOK = 'Look at these before you draw'
CORNER_BOX = 'right of 80 % of the width and below 90 % of the height'

PLAN_OLD = 'uploaded and named after the picture search (section 9, in part-later.md).'
PLAN_NEW = (PLAN_OLD + ' A drawn shot carries one camera flow, `camera_flow`, chosen by what the explanation is doing: naming parts, comparing two '
            'things, a quantity (a chart, heaps, counts), a change of state, a flow (load, heat, water) or a title or text: `fixed` (a comparison and a '
            'quantity always: a camera move changes how big things look); whole to part: `step_closer`; part to whole: `pull_back`; longer than the '
            'frame, or a process in a line: `pan_along` (a flow only when its path leaves the frame); a map: `step_closer` or `pan_along`; parts named '
            'one after another, closer each time: `follow` (at most three steps); one idea held through a long sentence, with no label near the edge: '
            '`slow_push_in`. One camera flow per shot; fixed when in doubt (no field is fixed). A flow the film\'s motion style does not allow is warned.')
END_OLD = 'A correction the operator makes that holds for the subject: `vw motion rule --subject … --add "…" --quote "…"`.'
END_NEW = (END_OLD + ' The shared look: before the first `vw motion brief` of the film\'s drawn graphics, read every approved spec together and record '
           'the choices that hold for every drawing, one line each, with `vw motion note --shot all --text "…"`: how each repeating part is shown, '
           'the view, the film\'s motions (its style\'s named motions and the extra ones the specs need), and which diagrams return (withdrawn with '
           '`vw motion note --shot all --remove "<the line>"`). Every brief carries them under "Shared look (every drawing of this film)", for every '
           'builder and checker. A choice with no fact in it is yours, and you log it (`vw log`); a choice that changes a fact or a proportion is '
           'asked once, with the others, before the first drawing is built, each with your recommended answer. Nothing of this is asked one at a time '
           'during the builds. The motions are binding: a builder uses the film\'s named motions and no others and names them in REVIEW.md. Read each '
           'REVIEW.md: a drawing that used another motion with no reason from its brief\'s own lines goes back once to a new `vw-motion-shot` helper '
           'with that point; never as a fact-check rule, and never a second time.')

PAIRS = [   # (where: 'common' or a part's name, the old sentence, the new one)
    ('plan', PLAN_OLD, PLAN_NEW),
    ('later', END_OLD, END_NEW),
]

CRAFT_OLD = ('How things move and appear is the film\'s, not this skill\'s: follow the brief\'s "Motion style" part for the pace, the arrivals, the labels, '
             'the camera and the changes between states. Where the brief\'s own lines for this shot ask for something the style does not, the brief\'s lines '
             'win for that shot. A line the viewer reads holds at least 0.5 s plus 0.3 s a word.')
CRAFT_NEW = '\n'.join([
    'How things move and appear is the film\'s, not this skill\'s. Follow, in this order: the lines of the brief that are about this shot; then the '
    'brief\'s "In every style" lines; then its "Motion style" text and the motions it names. Use the film\'s named motions for their jobs and no others; '
    'for a job they do not cover (a callout, a number, a chart, a before-and-after, a list of steps) use the extra motion of that job below, at the '
    'style\'s pace. Read references/motion.md only for a number none of these gives (an ease, a stagger, an overlap, how long an exit takes); where it '
    'disagrees with the brief, the brief wins. Its parts about a whole film (the beat grid, transitions between scenes, title sizes, letter-by-letter '
    'text) are not for a drawn shot. In REVIEW.md, name each motion you used and which move is the strongest.',
    '',
    'A motion outside these only for a reason the brief\'s lines for this shot give: say the reason in REVIEW.md. The main assistant sends a drawing '
    'back once when it used another motion without one.',
    '',
    'The extra motions (a calm style takes the longer time and no overshoot; Lively and Product the middle; Bold and Playful the shorter, with the '
    'style\'s own landing):',
    '- Leader then label (a callout): a thin leader draws from the part to the label\'s place in 0.6 s; the label arrives at its end by the film\'s own '
    'label motion and holds. Leaders never cross; a leader ends plainly.',
    '- Count up (a number): counts to its real value in 0.6 to 1 s and lands with its mark.',
    '- Grow from the baseline (a chart): one mark at a time, each 0.6 to 0.8 s, stopping exactly on its value.',
    '- Wipe between states (a before-and-after): a straight edge crosses in 0.6 to 1 s, the new state behind it.',
    '- Step list (points or steps, one at a time): each item arrives by the film\'s own label motion, 0.4 s apart.',
    '',
    '## The camera',
    '',
    'The brief\'s "Camera" line names the shot\'s one camera flow (Fixed when the plan names none): Fixed (the frame does not move); Step closer (once, '
    'from the whole to one part); Pull back (once, from one part to the whole); Pan along (a long object, a process in a line, a map); Follow (a step '
    'closer as each part is named, at most three in the shot); Slow push-in (a few percent, to hold one idea through a long sentence, only when no '
    'label is near the edge).',
    '',
    '1. One camera flow per shot: the one the brief names, and no other move of the frame.',
    '2. The one way to move the camera: the whole picture is one group that scales and moves; nothing inside it moves to fake the camera. The corner '
    'note is the server\'s and stays outside it.',
    '3. A label lands only after the camera has come to rest; its reading time counts from then.',
    '4. Keep the lower right corner free: the server draws the corner note there, outside the moving picture.',
    '5. A drawing that continues another opens exactly as the earlier shot ended.',
    '6. Judge a label\'s size at the end framing.',
    '7. Never move the camera during a comparison or a quantity: a zoom changes how big things look. The plan gives such a shot Fixed.',
    '8. Advice: do not move the camera at the moment a part changes state; it makes the change harder to follow.',
    '9. The move starts on the narration\'s word and is never faster than the eye can follow.',
    '10. The last second of the shot is still.'])
FACTS = '- The claims and the drawing spec are facts:'
OPEN_FIRST = (f'Open the pictures the brief lists under "{LOOK}" first: a part the film is about is drawn from what its picture shows, not from the '
              'words alone.')
SHOT_OLD = 'never `npx`, `node` or another shot\'s folder.'
RULES_OLD = 'for a shot whose style builds its parts in).'
RULES_NEW = (RULES_OLD + ' The same holds for the "In every style" lines and the named motions: write no rule from them, and no rule with a time or a '
             f'distance of a movement (a hold, a stagger, how long a fade takes). When the brief\'s Camera line is Fixed, write this one rule, as a must, '
             f'word for word: "{FIXED_RULE}" Write no other rule from the Camera line.')
CHECK_OLD = 'a way a label arrives that the style allows.'
CHECK_NEW = (CHECK_OLD + ' Nor for a movement that differs from the film\'s named motions or from the "In every style" lines: those are the builder\'s '
             'guidance, not rules. A fault a viewer would see in a frame is still a fault.')
NOTE_OLD = 'if a part of the drawing runs under it, add that as a should.'
NOTE_NEW = (NOTE_OLD + f' Look for that in every frame where the picture holds still: nothing of the drawing lies in the note\'s box ({CORNER_BOX}).')

BELOW_SPEC = '- A note on the view or a colour the brief lists as added is below the spec: the spec wins where they differ.'
SHARED_SKILL = ('- The brief\'s "Shared look (every drawing of this film)" lines hold for every drawing of the film, below the spec like a note. The main '
                'assistant recorded them before the first brief: a choice with no fact in it is its own, and logged; one that changes a fact or a '
                'proportion was asked once, with the others, before the first drawing was built. Never stop to ask about them.')

GAPS_OLD = 'put "not to scale" in its `label` and show no figure for the unknown size.'
GAPS_NEW = (GAPS_OLD + '\n- `camera_flow` on a drawn shot, by what the explanation is doing: naming parts, comparing two things, a quantity (a chart, heaps, '
            'counts), a change of state, a flow or a title: `fixed` (a comparison and a quantity always); whole to part: `step_closer`; part to whole: '
            '`pull_back`; longer than the frame, or a process in a line: `pan_along`; a map: `step_closer` or `pan_along`; parts named one after another, '
            'closer each time: `follow`; one idea held through a long sentence: `slow_push_in`. One camera flow per shot; fixed when in doubt.')

HELPERS = [   # (file under plugin/, the old sentence, the new one)
    ('agents/vw-plan-gaps.md', GAPS_OLD, GAPS_NEW),
    ('skills/motion/SKILL.md', CRAFT_OLD, CRAFT_NEW),
    ('skills/motion/SKILL.md', BELOW_SPEC, f'{BELOW_SPEC}\n{SHARED_SKILL}'),
    ('skills/motion/SKILL.md', FACTS, f'- {OPEN_FIRST}\n{FACTS}'),
    ('agents/vw-motion-shot.md', SHOT_OLD, f'{SHOT_OLD} {OPEN_FIRST}'),
    ('agents/vw-motion-rules.md', RULES_OLD, RULES_NEW),
    ('agents/vw-motion-check.md', CHECK_OLD, CHECK_NEW),
    ('agents/vw-motion-check.md', NOTE_OLD, NOTE_NEW),
]

RETIRED = ['Avoid stillness longer than about two seconds while the narration is speaking.',
           'the camera follows the subject with pans and gentle zooms, never faster than the eye can read',
           'moves only by panning along the object or stepping closer to a detail',
           'in another a single slow push-in of a few percent across the whole shot',
           'The whole frame drifts slowly in one direction through the shot',
           'letters easing from slightly wide to their final spacing',
           'The camera orbits and moves closer or further along smooth arcs',
           'The camera bobs lightly: a small nudge toward each new arrival',
           'The camera snaps between framings: a punch-in on the important part, a whip to the next.',
           'A line the viewer reads holds at least 0.5 s plus 0.3 s a word.',
           'Pictures you may place (approved; copies beside this brief in refs/ to look at)']


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
    rp = ROOT / 'server' / 'retired-sentences.json'
    r = json.loads(rp.read_text(encoding='utf-8'))
    r['sentences'] += [s for s in RETIRED if s not in r['sentences']]
    rp.write_text(json.dumps(r, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    print('visuals: design/221 phase 3a')


if __name__ == '__main__':
    main()
