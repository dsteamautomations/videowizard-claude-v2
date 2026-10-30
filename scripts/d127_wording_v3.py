"""design/127: the options and master instructions (version 3) speak of scenes and shots: one cut per scene with alternatives on its shots,
notes instead of decision slides, B-roll in a second round, answers per shot (KEEP, REJECT, TRIM). Writes the trace design/127-wording-trace.md.
Every replacement is between two markers that must occur once; run once (it refuses a second run)."""
import json
import re

P = 'server/procedures/v3.json'
TRACE = 'design/127-wording-trace.md'

PROMPT = [   # (start marker, end marker, new text): the text from start up to (not including) end is replaced
    ('3. Abstract ideas', '4. Each clip',
     '3. Abstract ideas (savings, cost, comfort, strength claims) have no exact match: round 2 or a blank; a sentence naming something the camera can see is matched like any other.
'),
    ('4. Each clip', '5. You are not obliged',
     '4. Each clip appears once in the film. A later part of the same clip in the same scene, not overlapping the first, is allowed, never side by side at the same shot size. '
     'Any other second use carries a note of kind reuse with the reason no other clip or blank works.
'),
    ('A large share of blanks is fine.', '\n', 'A blank is fine when no unused clip conveys the idea.'),
    ('8. Decision slides:', '9. Speaker',
     '8. Notes: a shot that needs the operator\'s eye carries a note {kind, question}, shown with it. Kinds: reuse (always), check_by_eye (the log suggests a match but the '
     'specific method is unclear, e.g. bricks laid but not clearly on edge), poor_quality (the log grades the sub-clip C or describes shake or softness), join (shots joined '
     'across a sentence boundary that may not read as one action), other (any placement you are unsure of). B-roll needs no note. The operator answers every footage shot '
     'KEEP, REJECT or TRIM; a rejected shot becomes a blank.
'),
    ('SCENES:', 'RULES THE SERVER ENFORCES',
     'ROUND 2, B-ROLL (after round 1 passes `vw options check`): fill blanks with B-roll (match b_roll), only from clips no exact match uses (the server refuses a B-roll '
     'clip used as a direct match). A B-roll shows the subject or setting the words are about (construction work, workers, bricks, finished homes) and nothing in it '
     'contradicts the words; look at the shot before and the shot after it: it must not contradict them and should support the idea. Never into a blank whose words make '
     'a specific claim (a number, a comparison, a saving): that stays for a graphic. A blank stays when no unused clip conveys the idea.\n\n'
     'ALTERNATIVES: where another clip could serve a footage shot, give it in the shot\'s `alternatives` [{sub_clip_id, source_in_frame, source_out_frame, match, evidence}]: '
     'the same timeline length as the shot, a clip used nowhere else in the cut. The operator sees it only after rejecting the shot.\n\n'
     'SCENES: one option per scene, numbered 1..N in film order (a second cut of a scene is refused: give alternatives on its shots). A scene with no match at all, after '
     'round 2, is one blank of the scene\'s length (declaring a gap is refused). An option\'s events (real shots and blanks) sum exactly to the scene\'s frames.\n\n'),
    ('SLIDES:', 'ROUNDS:',
     'SLIDES: the server writes every row; you do not. A scene is a header (Scene 2); its shots are numbered in play order (2.1, 2.2); an alternative of shot 2.2 is 2.2A1. '
     'The operator answers by shot.\n\n'),
]
OPTION_STEPS = [   # (step index, start marker, end marker, new text)
    (2, 'Then, scene by scene,', None,
     'Then, scene by scene, say which words have an exact real match, which become blanks for AI video or animation, and which blanks round 2 can fill with B-roll.'),
    (3, 'Author out/options.json (shape in shapes.json) from coverage.json and the pieces files in work/options/ (words-N.json only for pauses), `vw options check --file out/options.json` until valid, then',
     ' the second look',
     'Author out/options.json (shape in shapes.json) from coverage.json and the pieces files in work/options/ (words-N.json only for pauses) in two rounds: round 1 the exact '
     'matches, `vw options check --file out/options.json` until valid; round 2 the B-roll into blanks and the alternatives, `check` again until valid; then'),
    (4, 'answers each slide: the first answer approves the options', 'and the run moves',
     'answers each shot: the first answer approves the options, '),
    (4, 'and answer each slide with you', ': the first answer',
     'and answer each shot with you (`vw master decide`)'),
]
MASTER_STEPS = [
    (0, None, None,
     "Run `vw master slides`: it prints the review page link, the default place to decide: the operator watches the film there and answers each shot; run `vw master slides` "
     "again to see what is answered and what waits. For an operator who prefers chat, ask for the answers with the question tool, one shot per question and at most four "
     "questions per message, in film order, each question carrying the label, its title (Scene 2 · Shot 1), its lines (the clip, its time and the words; B-roll said "
     "first) and the allowed answers as buttons: a footage shot (2.1) KEEP, REJECT or TRIM; an alternative (2.1A1) KEEP or REJECT, asked only after its shot is rejected; "
     "the one AI shot of an all-AI scene KEEP (Keep AI) or REJECT (Find footage); a scene header and an AI shot inside a scene need none. A REJECT may be followed by one "
     "question for the (optional) reason, a TRIM by one for the trim. The first answer approves the options. Never ask for labels typed in one message: a wrong label "
     "records the wrong shot. Write their answers to out/decisions.json as [{slide, action, note, edit}] and run `vw master decide --file out/decisions.json`; if it stops "
     "at a refusal, fix that answer and run the file again (recorded answers are kept). For TRIM the edit is in the shot's source frames (`--edit \"in:+12,out:-6\"`): a "
     "frame is 1/25 s on the timeline; the shot's source frames and usable window are in the package row (`vw options show --option n` prints the option); a scene keeps "
     "its length, so a trim that shortens one shot lengthens another; turn 'trim the start a little' into about +12 frames and say what you did."),
    (1, '`vw master build` audits collisions', '`vw master render`',
     "`vw master build` takes each shot's answer (a rejected shot its kept alternative, else a blank), validates the trims and builds the fresh master; when it refuses "
     "(a scene sent back to find footage, a blank under 3 s, a trim that changes a scene's length) say why to the operator and follow it; "),
    (2, None, None,
     'AI shots, and rejected shots without a kept alternative, are gaps for the visuals stage (AI video or animation); the master film shows a card there.'),
]


def words(t):
    return len(re.findall(r'\S+', t))


def cut(text, start, end, new):
    a = text.index(start)
    assert text.count(start) == 1, start
    z = len(text) if end is None else text.index(end, a)
    return text[:a] + new + text[z:], text[a:z]


d = json.load(open(P, encoding='utf-8'))
opt = next(s for s in d['stages'] if s['name'] == 'options')
mas = next(s for s in d['stages'] if s['name'] == 'master')
assert 'ROUND 2, B-ROLL' not in opt['prompt'], 'already applied'
trace = ['# 127 — wording trace (options and master, version 3)', '',
         'Generated by scripts/d127_wording_v3.py: every replaced passage, old then new, with word counts. Checked independently (see design/127).', '']
before = {'options prompt': words(opt['prompt']), 'options steps': words(' '.join(opt['steps'])), 'master steps': words(' '.join(mas['steps']))}
for start, end, new in PROMPT:
    opt['prompt'], old = cut(opt['prompt'], start, end, new)
    trace += [f'## options prompt — {start}', '', f'**Old ({words(old)} words):** {old.strip()}', '', f'**New ({words(new)} words):** {new.strip()}', '']
for i, start, end, new in OPTION_STEPS:
    opt['steps'][i], old = cut(opt['steps'][i], start, end, new)
    trace += [f'## options step {i + 1} — {start[:40]}', '', f'**Old ({words(old)} words):** {old.strip()}', '', f'**New ({words(new)} words):** {new.strip()}', '']
for i, start, end, new in MASTER_STEPS:
    if start is None:
        old, mas['steps'][i] = mas['steps'][i], new
    else:
        mas['steps'][i], old = cut(mas['steps'][i], start, end, new)
    trace += [f'## master step {i + 1}', '', f'**Old ({words(old)} words):** {old.strip()}', '', f'**New ({words(new)} words):** {new.strip()}', '']
after = {'options prompt': words(opt['prompt']), 'options steps': words(' '.join(opt['steps'])), 'master steps': words(' '.join(mas['steps']))}
trace += ['## Totals', '', '| Text | Before | After |', '|---|---|---|'] + [f'| {k} | {before[k]} | {after[k]} |' for k in before] + ['']
trace += ['The options prompt grows: round 2 (B-roll) and alternatives are new rules SK asked for (design/127 items 5 and 12); the SECONDARY, backup, decision-slide and '
          'letter-label passages they replace are gone. The master steps grow by 25 words: the alternatives and the all-AI scene's two answers are new.', '']
open(P, 'w', encoding='utf-8', newline='\n').write(json.dumps(d, ensure_ascii=False, indent=2) + '\n')
open(TRACE, 'w', encoding='utf-8', newline='\n').write('\n'.join(trace))
print(before, after)
