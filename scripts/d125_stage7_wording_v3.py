"""design/125 stage 7: the agreed wording changes in instruction version 3 (P2, P3, P7, P9, P13, P14, O1-O7, O9, the first-cut record retired),
one exact replacement each. Writes server/procedures/v3.json and the trace design/125-stage7-wording-trace.md (old -> new per pair, word counts per stage).
Every old text must occur exactly once. Version 2 is not touched."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'server' / 'procedures' / 'v3.json'
STAGES = ('options', 'master', 'first_cut', 'analysis', 'visuals')

PAIRS = [
    # stage, field, change, old, new
    ('options', 'steps[0]', 'P3',
     'shapes.json, coverage.json, rest.json, and the tables as numbered files each small enough for one read: sub-clips-1.json and on with at most 25 rows, cards-1.json and on, words-1.json and on)',
     "shapes.json, coverage.json, rest.json, words-1.json and on, and pieces-<scene>.json: each scene's sentences and the pieces that fit it, direct first; pieces-other.json: pieces that fit no scene)"),
    ('options', 'steps[0]', 'P3',
     'The direction prompt is prompt.md; tables are one row per line.',
     "The direction prompt is prompt.md; tables are one row per line; a piece's full row and card: `vw options show --sub S`."),
    ('options', 'steps[1]', 'P2', 'Scenes and pauses (design/19), always:', 'Scenes and pauses, always:'),
    ('options', 'steps[1]', 'P7',
     "(from the brief's chapters; none when the brief has none)",
     "(from the brief's chapters; none when the brief has none; a scene covers one chapter: a paragraph covering two is split where the second begins)"),
    ('options', 'steps[3]', 'P3, O4-O6',
     'from coverage.json, the cards-N.json and the sub-clips-N.json files in work/options/ (words-N.json only for pauses), `vw options check --file out/options.json` until valid, then `vw options propose --file out/options.json`.',
     'from coverage.json and the pieces files in work/options/ (words-N.json only for pauses), `vw options check --file out/options.json` until valid, then the second look: `vw options second-look` writes work/options/scenes/<scene>.json with still frames; one `vw-scene-review` helper per scene, all at once, each given only its scene, writes out/second-look/<scene>.json; `vw options join-second-look`, `check` again, then `vw options propose --file out/options.json`.'),
    ('options', 'steps[3]', 'P10',
     '`check` and `propose` return the flags grouped by rule: act on R5 (hold), B1 and B2 (word timing), rule 11 (a long real shot) and E1 (a short blank); R1, R10, R8 and R4 only inform when shots are cut to the meaning across clips.',
     '`check` and `propose` list in full the flags to act on (`act_on`: R5, B1, B2, rule 11, E1, E2, N17 and N14) and count the rest (`for_information`: R1, R10, R8, R4).'),
    ('options', 'steps[3]', 'P2',
     ' Give every option its `steps` map (every step of the scene once: the event that shows it, a blank when no clip shows that exact step, and the why), its `carries_over` and, only when the narration moves, `moves_place` (design/91 N17, N14); act on the N17 and N14 flags.',
     ' Give every option its `steps` map, `carries_over` and, only when the narration moves, `moves_place` (rules 10 and 11).'),
    ('options', 'steps[4]', 'P14',
     ': the first answer approves the options (`vw options record --quote "<their yes>"` remains for an explicit approval).',
     ': the first answer approves the options.'),
    ('options', 'prompt', 'P3',
     'the 10-line summary cards, then the sub_clips table (only eligible sub-clips may be used; crops come from the solver). Open a full log only for a candidate (`vw options log --unit`).',
     'then the pieces by scene (only eligible ones may be used; crops come from the solver). A full row and card: `vw options show --sub S`; a full log only for a candidate (`vw options log --unit`).'),
    ('options', 'prompt', 'P2', 'EXACT MATCHES FIRST (design/21):', 'EXACT MATCHES FIRST:'),
    ('options', 'prompt', 'P9',
     '3. Abstract ideas (savings, cost, comfort, strength claims) are blanks by default. Footage that relates indirectly (B-roll) may be offered only when it is clearly relevant, the viewer can relate it to the words, and nothing in it is wrong.',
     '3. An abstract idea is a sentence with nothing to show (savings, cost, comfort, strength claims): a blank. A sentence naming something the camera can see is matched like any other. B-roll: clearly related to the words, nothing wrong.'),
    ('options', 'prompt', 'O7',
     'Any other second use, including another part of the same clip, is a decision of kind reuse with the reason no other clip or blank works.',
     'A later part of the same clip in the same scene, not overlapping the first, needs no question, never side by side at the same shot size. Any other second use is a decision of kind reuse with the reason no other clip or blank works.'),
    ('options', 'prompt', 'P2', '10. Steps (design/91 N17):', '10. Steps (N17):'),
    ('options', 'prompt', 'P3', '(beats.json `steps`: its sentences, numbered BEAT_03.S2)', '(its sentences in its pieces file, numbered BEAT_03.S2)'),
    ('options', 'prompt', 'P2', '11. One place per process (design/91 N14):', '11. One place per process (N14):'),
    ('options', 'prompt', 'P13',
     'SCENES: a scene with no exact match at all is declared in `gaps` (the whole scene is a blank). Otherwise give the scene a PRIMARY option',
     "SCENES: a scene with no exact match at all is one blank of the scene's length (declaring a gap is refused). Give every scene a PRIMARY option"),
    ('options', 'prompt', 'O2, O3',
     "They are labelled in film order: a scene's option and its BACKUP take the running numbers (#2, #3); the blanks and decisions inside an option take its number and a letter (#2A, #2B).",
     "A slide carries its scene's number (#2); a backup is \"#2 – second choice\" (#2-2); the blanks and decisions inside add a letter (#2A, #2-2A)."),
    ('options', 'prompt', 'P14, O4',
     "Write out/options.json in the package's `shapes.options` form, `vw options check` (it shows real, blank and decision seconds per scene), fix, `vw options propose`, `vw options render`, let the operator watch the review film, and record with their yes.",
     "Write out/options.json in the package's `shapes.options` form, then follow the steps (check, the second look, propose, render); the operator's first slide answer approves."),
    ('master', 'steps[0]', 'O1, O2, O3',
     'scene and BACKUP slides (1, 2, 3 …) KEEP, REJECT or KEEP_WITH_EDIT;',
     'scene slides (1, 2 …) and second choices (2-2) KEEP, REJECT or KEEP_WITH_EDIT, but a scene whose shots are all decisions takes only KEEP_WITH_EDIT (trim a shot): its parts decide it;'),
    ('master', 'steps[0]', 'O3', " A scene's backup is the next number, so the operator chooses between 2 and 3.", ''),
    ('master', 'steps[0]', 'O1',
     'A REJECT may be followed by one question for the reason (the reason is optional), a KEEP_WITH_EDIT by one for the shot and the frame trim.',
     'A REJECT may be followed by one question for the (optional) reason, a KEEP_WITH_EDIT by one for the shot and trim.'),
    ('first_cut', 'steps[0]', 'first-cut record retired',
     None, 'Recorded with the master (`vw master record`); the separate first-cut record is retired.'),
    ('visuals', 'parts.plan', 'O9', 'helpers (your own agents, a few gaps each;', 'helpers (the `vw-plan-gaps` helper, a few gaps each;'),
]


def apply_visuals(parts):
    """The stage-7 pairs that land in the visuals parts, for c1_split_v3.py --check (applied after design/125's)."""
    for stage, name, change, old, new in PAIRS:
        if stage == 'visuals':
            part = next(p for p in parts if p['name'] == name[6:])
            assert part['text'].count(old) == 1, (change, old[:60])
            part['text'] = part['text'].replace(old, new)


def field(stage, name):
    if name.startswith('steps['):
        return stage['steps'], int(name[6:-1])
    if name.startswith('parts.'):
        return next(p for p in stage['parts'] if p['name'] == name[6:]), 'text'
    return stage, name


def words(stage):
    return sum(len(t.split()) for t in [stage.get('prompt') or '', *(stage.get('steps') or []), *(p['text'] for p in stage.get('parts') or [])])


def main():
    d = json.loads(P.read_text(encoding='utf-8'))
    stages = {s['name']: s for s in d['stages']}
    before = {n: words(stages[n]) for n in STAGES}
    trace = ['# 125 stage 7 — wording trace, instruction version 3', '',
             'Every agreed wording change of stage 7, old text → new text, in the order applied. Made by `scripts/d125_stage7_wording_v3.py`.', '']
    for stage, name, change, old, new in PAIRS:
        holder, k = field(stages[stage], name)
        text = holder[k]
        if old is None:   # the whole step is replaced
            old = text
        if text.count(old) != 1:
            sys.exit(f'{stage} {name} ({change}): the old text occurs {text.count(old)} times: {old[:80]!r}')
        holder[k] = text.replace(old, new)
        trace += [f'## {change} — {stage}, {name}', '', '**Old:**', '', '> ' + old.replace('\n', '\n> '), '', '**New:**', '',
                  ('> ' + new.replace('\n', '\n> ')) if new else '> (removed)', '']
    after = {n: words(stages[n]) for n in STAGES}
    trace += ['## Words read by the assistant, per stage (prompt, steps and parts)', '', '| Stage | Before | After |', '|---|---|---|',
              *(f'| {n} | {before[n]} | {after[n]} |' for n in STAGES), '']
    longer = [n for n in STAGES if after[n] > before[n]]
    if longer:
        sys.exit(f'longer than before: {longer} {before} {after}')
    P.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    (ROOT / 'design' / '125-stage7-wording-trace.md').write_text('\n'.join(trace) + '\n', encoding='utf-8', newline='\n')
    print(f'{len(PAIRS)} replacements written; words before {before}, after {after}')


if __name__ == '__main__':
    main()
