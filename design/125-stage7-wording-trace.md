# 125 stage 7 — wording trace, instruction version 3

Every agreed wording change of stage 7, old text → new text, in the order applied. Made by `scripts/d125_stage7_wording_v3.py`.

## P3 — options, steps[0]

**Old:**

> shapes.json, coverage.json, rest.json, and the tables as numbered files each small enough for one read: sub-clips-1.json and on with at most 25 rows, cards-1.json and on, words-1.json and on)

**New:**

> shapes.json, coverage.json, rest.json, words-1.json and on, and pieces-<scene>.json: each scene's sentences and the pieces that fit it, direct first; pieces-other.json: pieces that fit no scene)

## P3 — options, steps[0]

**Old:**

> The direction prompt is prompt.md; tables are one row per line.

**New:**

> The direction prompt is prompt.md; tables are one row per line; a piece's full row and card: `vw options show --sub S`.

## P2 — options, steps[1]

**Old:**

> Scenes and pauses (design/19), always:

**New:**

> Scenes and pauses, always:

## P7 — options, steps[1]

**Old:**

> (from the brief's chapters; none when the brief has none)

**New:**

> (from the brief's chapters; none when the brief has none; a scene covers one chapter: a paragraph covering two is split where the second begins)

## P3, O4-O6 — options, steps[3]

**Old:**

> from coverage.json, the cards-N.json and the sub-clips-N.json files in work/options/ (words-N.json only for pauses), `vw options check --file out/options.json` until valid, then `vw options propose --file out/options.json`.

**New:**

> from coverage.json and the pieces files in work/options/ (words-N.json only for pauses), `vw options check --file out/options.json` until valid, then the second look: `vw options second-look` writes work/options/scenes/<scene>.json with still frames; one `vw-scene-review` helper per scene, all at once, each given only its scene, writes out/second-look/<scene>.json; `vw options join-second-look`, `check` again, then `vw options propose --file out/options.json`.

## P10 — options, steps[3]

**Old:**

> `check` and `propose` return the flags grouped by rule: act on R5 (hold), B1 and B2 (word timing), rule 11 (a long real shot) and E1 (a short blank); R1, R10, R8 and R4 only inform when shots are cut to the meaning across clips.

**New:**

> `check` and `propose` list in full the flags to act on (`act_on`: R5, B1, B2, rule 11, E1, E2, N17 and N14) and count the rest (`for_information`: R1, R10, R8, R4).

## P2 — options, steps[3]

**Old:**

>  Give every option its `steps` map (every step of the scene once: the event that shows it, a blank when no clip shows that exact step, and the why), its `carries_over` and, only when the narration moves, `moves_place` (design/91 N17, N14); act on the N17 and N14 flags.

**New:**

>  Give every option its `steps` map, `carries_over` and, only when the narration moves, `moves_place` (rules 10 and 11).

## P14 — options, steps[4]

**Old:**

> : the first answer approves the options (`vw options record --quote "<their yes>"` remains for an explicit approval).

**New:**

> : the first answer approves the options.

## P3 — options, prompt

**Old:**

> the 10-line summary cards, then the sub_clips table (only eligible sub-clips may be used; crops come from the solver). Open a full log only for a candidate (`vw options log --unit`).

**New:**

> then the pieces by scene (only eligible ones may be used; crops come from the solver). A full row and card: `vw options show --sub S`; a full log only for a candidate (`vw options log --unit`).

## P2 — options, prompt

**Old:**

> EXACT MATCHES FIRST (design/21):

**New:**

> EXACT MATCHES FIRST:

## P9 — options, prompt

**Old:**

> 3. Abstract ideas (savings, cost, comfort, strength claims) are blanks by default. Footage that relates indirectly (B-roll) may be offered only when it is clearly relevant, the viewer can relate it to the words, and nothing in it is wrong.

**New:**

> 3. An abstract idea is a sentence with nothing to show (savings, cost, comfort, strength claims): a blank. A sentence naming something the camera can see is matched like any other. B-roll: clearly related to the words, nothing wrong.

## O7 — options, prompt

**Old:**

> Any other second use, including another part of the same clip, is a decision of kind reuse with the reason no other clip or blank works.

**New:**

> A later part of the same clip in the same scene, not overlapping the first, needs no question, never side by side at the same shot size. Any other second use is a decision of kind reuse with the reason no other clip or blank works.

## P2 — options, prompt

**Old:**

> 10. Steps (design/91 N17):

**New:**

> 10. Steps (N17):

## P3 — options, prompt

**Old:**

> (beats.json `steps`: its sentences, numbered BEAT_03.S2)

**New:**

> (its sentences in its pieces file, numbered BEAT_03.S2)

## P2 — options, prompt

**Old:**

> 11. One place per process (design/91 N14):

**New:**

> 11. One place per process (N14):

## P13 — options, prompt

**Old:**

> SCENES: a scene with no exact match at all is declared in `gaps` (the whole scene is a blank). Otherwise give the scene a PRIMARY option

**New:**

> SCENES: a scene with no exact match at all is one blank of the scene's length (declaring a gap is refused). Give every scene a PRIMARY option

## O2, O3 — options, prompt

**Old:**

> They are labelled in film order: a scene's option and its BACKUP take the running numbers (#2, #3); the blanks and decisions inside an option take its number and a letter (#2A, #2B).

**New:**

> A slide carries its scene's number (#2); a backup is "#2 – second choice" (#2-2); the blanks and decisions inside add a letter (#2A, #2-2A).

## P14, O4 — options, prompt

**Old:**

> Write out/options.json in the package's `shapes.options` form, `vw options check` (it shows real, blank and decision seconds per scene), fix, `vw options propose`, `vw options render`, let the operator watch the review film, and record with their yes.

**New:**

> Write out/options.json in the package's `shapes.options` form, then follow the steps (check, the second look, propose, render); the operator's first slide answer approves.

## O1, O2, O3 — master, steps[0]

**Old:**

> scene and BACKUP slides (1, 2, 3 …) KEEP, REJECT or KEEP_WITH_EDIT;

**New:**

> scene slides (1, 2 …) and second choices (2-2) KEEP, REJECT or KEEP_WITH_EDIT, but a scene whose shots are all decisions takes only KEEP_WITH_EDIT (trim a shot): its parts decide it;

## O3 — master, steps[0]

**Old:**

>  A scene's backup is the next number, so the operator chooses between 2 and 3.

**New:**

> (removed)

## O1 — master, steps[0]

**Old:**

> A REJECT may be followed by one question for the reason (the reason is optional), a KEEP_WITH_EDIT by one for the shot and the frame trim.

**New:**

> A REJECT may be followed by one question for the (optional) reason, a KEEP_WITH_EDIT by one for the shot and trim.

## first-cut record retired — first_cut, steps[0]

**Old:**

> Already recorded with the master's approval (design/44). If `vw next` still shows first_cut (a run approved before design/44), ask the one question: did the operator watch the master film and listen to it, and do they approve it as the first cut? Their reply must say both. `vw first-cut record --quote "<their reply>"`.

**New:**

> Recorded with the master (`vw master record`); the separate first-cut record is retired.

## O9 — visuals, parts.plan

**Old:**

> helpers (your own agents, a few gaps each;

**New:**

> helpers (the `vw-plan-gaps` helper, a few gaps each;

## Words read by the assistant, per stage (prompt, steps and parts)

| Stage | Before | After |
|---|---|---|
| options | 1619 | 1617 |
| master | 454 | 453 |
| first_cut | 53 | 13 |
| analysis | 328 | 328 |
| visuals | 10227 | 10227 |


## Fixes after the independent check (30 Oct 2026, `scripts/d125_stage7_fixes_v3.py`)

### check 1, 5: E2 for an AI-only scene; one list of flags — options, prompt

**Old:**

> Flags come grouped by rule: act on R5, B1, B2, rule 11 and E1, on E2 (a blank over 12 s: find a footage cut-in, a B-roll clip or a frame that relates and split it; a run of AI pictures that long reads as synthetic); and on N17 and N14 (the step and the place: another clip, a blank, or a decision for the operator); R1, R10, R8 and R4 inform.

**New:**

> E2 (a blank over 12 s, an AI-only scene included): a run of AI pictures that long reads as synthetic; find a footage cut-in, a B-roll clip or a frame that relates and split it, or say in intent why it must stay whole. The steps list the flags to act on.

### check 3: P9 keeps "by default" and the B-roll gate — options, prompt

**Old:**

> 3. An abstract idea is a sentence with nothing to show (savings, cost, comfort, strength claims): a blank. A sentence naming something the camera can see is matched like any other. B-roll: clearly related to the words, nothing wrong.

**New:**

> 3. Abstract ideas (savings, cost, comfort, strength claims) are blanks by default; a sentence naming something the camera can see is matched like any other. B-roll only when clearly relevant, relatable to the words, and nothing in it wrong.

### check 5: what each act-on flag is — options, steps[3]

**Old:**

> `check` and `propose` list in full the flags to act on (`act_on`: R5, B1, B2, rule 11, E1, E2, N17 and N14) and count the rest (`for_information`: R1, R10, R8, R4).

**New:**

> `check` and `propose` list in full the flags to act on (`act_on`: R5 a hold, B1 and B2 word timing, rule 11 a long real shot, E1 a short blank, E2 a long blank, N17 and N14 the step and the place: another clip, a blank or a question) and count the rest (`for_information`: R1, R10, R8, R4).

### check 6: the per-file limit said — options, steps[0]

**Old:**

> pieces-<scene>.json: each scene's sentences and the pieces that fit it, direct first;

**New:**

> pieces-<scene>.json: each scene's sentences and the pieces that fit it, direct first, a large scene continuing in pieces-<scene>-2.json;

### check 2, 4: a scene decided by its parts; keep one of two versions — master, steps[0]

**Old:**

> scene slides (1, 2 …) and second choices (2-2) KEEP, REJECT or KEEP_WITH_EDIT, but a scene whose shots are all decisions takes only KEEP_WITH_EDIT (trim a shot): its parts decide it;

**New:**

> scene slides (1, 2 …) and second choices (2-2, keep one of the two) KEEP, REJECT or KEEP_WITH_EDIT; a scene slide whose footage is all questions (no second choice) needs no answer: its parts decide it, a trim (KEEP_WITH_EDIT) if wanted;

### check 2, 4: offset (the next sentence said twice) — master, steps[0]

**Old:**

> Watch the review film, then answer each slide (on the page, or `vw master decide`): the first answer approves the options.

**New:**

> The first answer approves the options.

Words: options 1617 → 1630; master 453 → 448

### the act-on list shortened (each flag's own message says what to do) — options, steps[3]

**Old:**

> (`act_on`: R5 a hold, B1 and B2 word timing, rule 11 a long real shot, E1 a short blank, E2 a long blank, N17 and N14 the step and the place: another clip, a blank or a question)

**New:**

> (`act_on`: R5, B1, B2, rule 11, E1, E2, N17, N14; each says what to do)

Words: options 1630 → 1607 (1,619 before this release)

## plugin/commands/vw.md, after the independent check

- "(procedure versions 2 and 3; version 3, the current default; you are the editor's planner)" → "(you are the editor's planner)"
- "B-roll and any clip reuse as decisions" → "B-roll and a clip reused in another scene as decisions"
- "but a scene whose shots are all decisions only KEEP_WITH_EDIT (trim a shot: its parts decide it)" → "a scene whose footage is all questions needs no answer (its parts decide it; a trim if wanted)"
- " Boundary doubts: `frames` (free) before `inspect` (paid; inform)." → "(removed: the options steps say it)"

The Options and master paragraph: 437 words before this release, 440 after.
- "(no re-recording, nothing paid; propose is refused until the scenes are approved)" → "(nothing re-recorded or paid; propose waits for the approved scenes)"

The Options and master paragraph: 437 words before this release, 438 after.
- "Then the review page is the default place to decide: the operator clicks each slide's answer while watching;" → "The page is the default place to decide;" (said earlier in the same paragraph)

The Options and master paragraph: 437 words before this release, 428 after.
