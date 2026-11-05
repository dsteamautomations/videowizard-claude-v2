# 171 — Wan 3.0 Omni test round on VW-18 (5 Nov 2026, evening)

The test round of design/170 §4, run by hand from this PC with the Wan CLI (0.0.3, logged in by SK), on real VW-18 plan text and VW-18's own reference pictures (the kept-method sets, still candidates: SK, "go ahead as they are"). Eight paid runs plus two unintended ones (section 5). Every verdict is read from half-second strips at 480 px (design/167 D8); the strips, the prompts, the environment pictures, the scripts and the logs are in `171-assets/`. SK has the eight videos.

## 1. What was run

| Run | Shot (VW-18 plan v5, film 50 fps) | Seconds | Pictures sent, in `@Image` order | Result |
|---|---|---|---|---|
| W1a | plinth wetting `BEAT_06-B1-s1` (8.2 s) | `--duration 8` | environment picture; worker full length; worker face; broom (from the wetting technique set); bucket with mug | 8.0 s, no cut |
| W1b | the same | `--smart-duration=true` | the same five | **8.0 s** chosen by the model, no cut |
| W2a | pointing close-up `B10_SH1` (6.8 s) | 7 | the pointed-and-open wall (technique set); the footage frame of the wall (`continues_footage`); the mason's working pose; the pointing trowel; the hawk | 7.0 s, no cut |
| W2b | string setting `BEAT_06-B1-s3` (4.6 s) | 5 | environment picture; the worker crouched; the peg with the line wound | 5.0 s, no cut |
| W3 | the mason scene as **one 30 s sequence of three shots** (design/157's scene, this morning's references) | 30 | the rat-trap site set picture; mason; helper; trowel and pan | 30.0 s, **cuts at 10 and 20 s as written** |
| W4 | five bricks from a pan to a wall, one at a time | 10 | the site set picture; helper; the pan | 10.0 s, no cut |
| W6a | kiln `BEAT_04-B1-S1` (4.0 s) with the environment picture | 4 | environment picture; the two workers; their faces | 4.0 s |
| W6b | the same with the kiln's own set picture instead | 4 | kiln set picture 1; the two workers; their faces | 4.0 s |

All outputs 1280×720, 30 fps, H.264, no watermark (`savedFiles[].watermark: without`), 2–5 minutes a job (the 30 s one 5 minutes).

The environment pictures (design/170 §3) were made on the VM with the run's image model from the scene's `layout`, `landmarks`, `light` and `air`, with the place's set picture (and the stack's, the peg's) as parents (`171-assets/env-*.txt`, `env-sheet.png`). All three came out as the scene with nobody in it, from the camera's position.

## 2. Results, test by test

**W1 — the timeline by the second against smart duration.** Both runs follow the text's order exactly: sweep with dust, the broom laid down, the mug out of the bucket, two throws with the arc of water in the air, the near top dark and wet at the end, the man a little bent with the mug, the broom on the earth. Identity from the set (face, stubble, green shirt, green checked lungi, sandals). The environment held frame for frame (plinth, stack behind right, coconut tree left, bucket at the foot). Pace: the sweep ran about 3 s instead of 4.7 s and the throws started early; the pace is the model's own, as it was with Omni (design/167). **Smart duration chose 8 s**, the last second named in the text; the two films are near-identical. Verdict: pass; **explicit duration is the default** (it is deterministic and the shot's frames are fixed by the plan); smart duration adds nothing while the text carries seconds.

**W2 — references by name, no start image.** Pointing: the mason's hands with the red thread on the right wrist, the hawk held below, the trowel pressing along one joint left to right then drawn back, crumbs on the ledge. String: the line slack on the earth at 0 s, drawn taut along the edge by 2 s, wound on the peg by 4 s, the watch on the left wrist, the sleeve rust-orange. Both environments held. **One miss, from the reference, not the model:** the pointed wall came out laid flat, not on edge, because the technique set picture that was sent as "the wall" shows a flat wall. The footage frame sent beside it did not override it. Verdict: pass on identity, tools, action and timing; the picture that stands for the place must show the right construction (a plan check for the environment picture: the wall type named in the layout must be in the picture).

**W3 — 30 s, three angles, one call.** Shot 1 (0–10 s) wide from the near end: the mason spreads, sets and taps bricks; the helper walks in from the right at about 6 s and stops across the wall by 9 s. **Cut at 10 s.** Shot 2 (10–20 s) close on the hands with a slow push-in: scrape, press into the vertical joint, strike flush, the bricks **on edge with their cavities**. **Cut at 20 s.** Shot 3 (20–30 s) wide from the far side over the wall, the helper in the right foreground back three-quarter: he lifts two bricks, carries them left along the wall, sets them within the mason's reach, the mason picks one up and turns it on edge as the shot ends. Both men keep their faces and clothes across all three angles. ffmpeg's scene detector did not register the cuts (the colours match), the strips show them plainly. Verdict: **pass, the strongest result of the round.** A scene can be written as one Wan call of up to 30 s with its cuts named by the second; this is the `one_take` idea of design/161 without a cartoon.

**W4 — counting.** The pan held three bricks at the start, not five; the helper moved one at a time, the pan ran empty, and five lay on the wall at the end: totals went 3 → 4 → 5 as bricks appeared in the pan. The end count was right because the text named the end state; the inventory along the way was not. The mortar in the pan's reference came along although the text said "without the mortar". Verdict: **counts of identical things stay out of the text** (design/165 holds for Wan too); the end state can be named.

**W5 — silent take.** Every output has an AAC stereo track even with `--audio-output=false`; it is silent (mean and peak −91 dB measured). The assembly's fill takes the video; the editor's package should drop the track (`-an` on retain, part (ii)) rather than carry a silent one. Not run through the assembly itself (no run holds these takes); the probe facts the assembly reads (duration, 30 fps, 1280×720) are in the logs.

**W6 — the environment picture against the place's set.** The two kiln films are near-identical: the kiln's own set picture is already a wide view from the camera's position, so the environment picture added nothing here. Where the place's set is not the shot's own view (the plinth: its set shows the plinth corner from another side; the string: a close low angle that no set holds) the environment picture is what fixes the layout, and W1/W2b held it. Verdict: **the environment picture earns its place per scene; when a scene's place set already is the camera's view, the server may send that picture as the environment and spend nothing** (a rule for part (i): the operator ticks one of the set pictures as the scene's view, or the server makes one).

## 3. What carries into the build (design/170 amended by this round)

1. **Explicit duration by default** (`--smart-duration=false --duration N`, N = the shot's seconds rounded up, 2–30). Smart duration stays a field on the record, off.
2. **The Wan take text of design/170 §2c works as written**: references by name in file order, one line per reference on what to take and what pose not to carry, the place, the fixed positions, the beats by the second, the camera (one line per cut with its second), the closing rules. Eight for eight on identity and action order.
3. **A scene may be one call of up to 30 s with cuts named by the second.** The plan's shots inside such a scene become the shots of the sequence; the server writes "Shot n, [a–b s], <camera>" from each shot's framing and camera, and the beats under it. This replaces the 10 s split rule on the Wan route.
4. **No counts of identical things in the text; the end state may be named.** Unchanged from design/165.
5. **The environment picture per scene, with the camera's view**: made from the scene's layout, landmarks, light and air with the place's set as parent; or one of the place's set pictures ticked as the view. The picture must show the construction the layout names (a check).
6. **A reference picture's pose and contents leak** (the guide's lesson, seen again: the mortar in the pan). The "take only X from it" line limits it; a picture that holds a wrong thing is not sent.
7. **The CLI's `--dry-run` is not used** (section 5).
8. **Silent takes carry a silent audio track**: strip it at retain.
9. **Cost**: 3 credits per second at 720P (30 for 10 s, 90 for 30 s, 24 for 8 s measured alone). The credits-before/after difference is unreliable with several jobs in flight (the logs show 294 for parallel runs); the worker records the table's estimate and the account's running balance.
10. **Concurrency and rate limits**: eight jobs in flight were accepted; two submissions were refused with `blocked` ("feeling uninspired") and succeeded on retry after 20 s. The worker treats `blocked` as a wait, not a failure.

## 4. Costs of the round

Balance 1,202 → 944: **258 credits**. The eight runs: 8+8+7+5+30+10+4+4 = 76 s × 3 = 228; the two unintended dry-run tasks of section 5: 2 × 5 s × 3 = 30. The two `blocked` refusals cost nothing.

## 5. Two process findings that change the worker's design

1. **`--dry-run` submitted real tasks.** On CLI 0.0.3, `wan omni2video … --dry-run` returned a `taskId` and the request, and the account's task list shows both dry runs as succeeded 5 s tasks (`0633f337…`, `31fbdfb7…`), paid. The guide and the bundled skill say a dry run sends nothing; on this version it does. The test script now checks the `@Image` tags locally and never passes `--dry-run`; the worker does the same. To re-check on a later CLI version before trusting it: run a dry run, then `wan task list`.
2. **The Windows `.cmd` shim cuts a multi-line prompt at its first line break** and drops every flag after it (the first dry run went out as the prompt's first paragraph, five seconds, adaptive, sound on, no references). The script calls the CLI's JavaScript entry through Node with the arguments as a list. On the VM (Linux) the shim is not involved, but the worker calls the entry the same way, never a shell line.

## 6. Verdict

Wan 3.0 Omni through the CLI does what design/170 asks on real plan text: identity from the sets, the place from one environment picture, the action in the written order, the length as asked up to 30 s, cuts where named. Its limits are the same as Omni's (pace is its own; counts drift) and one more (a reference's contents leak). The experiment continues as SK set it: more scenarios on this script before anything is integrated. Next scenarios worth their credits: a scene with three people; a 9:16 film; a take with a line of dialogue (`--audios`); a wide scene of a place with no set picture; a second run of the pointing shot with a correct wall picture.

## 7. Two more 30 s sequences on VW-18's own scenes (SK: "can you try that")

| Run | Sequence | Pictures | Result |
|---|---|---|---|
| W7 | the plinth gap as three shots: wide sweep and first throw (0–10), close at the top's level on the water (10–20), low at the corner on the string (20–30) | both environment pictures (the plinth from above, the corner low), the worker, his face, the broom, the bucket | 30.0 s; **cuts at 10 and 20 s** (ffmpeg found the first at 9.97); every beat in order: sweep with dust, broom down, mug, the arc; the sheet of water on the top with drops off the edge, the mug lowered; the line slack, drawn, wound at the peg and left taut along the edge. Same worker in all three. |
| W8 | the kiln as three shots: wide hand-over (0–10), close on the hands at the stack (10–20), a slow pan along the drying rows settling on the chimney (20–30) | environment picture, the two workers, their faces | 30.0 s; cuts at 10 and 20 s; the hand-over, the pair squared on the stack, the pan ending with the chimney at the left. **One invention: flames glowing in the firing trench from 23 s** although the scene says smoke and no flame; the text named the trench and the heat shimmer and said nothing about fire. |

Cost 90 credits each (3 a second); 5 minutes each. Balance after: see the logs.

What this adds to section 3: a real gap's shots can be written as one 30 s sequence and Wan keeps the cuts at the second and the person across the angles (three for three now, W3, W7, W8). Two environment pictures of one place (two camera positions) can go in one call and each serves its shot. The invention in W8 is the kind the take check (design/91 N3) catches: the check's "what must not appear" line gets the scene's exclusions ("no flame") word for word, as the light line does today.

## 8. Round 2 (SK, 5 Nov night): steps instead of seconds, the right hand, smart duration

SK's three changes after reviewing the prompts: (1) every action with the right hand; (2) `--smart-duration=true`; (3) the action written as a numbered series of steps, every timeline reference removed. The same five single-shot scenes, the same pictures, the prompts `171-assets/r2-*.txt`.

| Run | Plan length | Length the model chose | Steps in order | Right hand | Notes |
|---|---|---|---|---|---|
| R2-plinth | 8.2 s | **20 s** | all seven, in order: sweep along, broom down, mug out, two throws, the top wet, the standing end | yes: broom and mug in the right hand | slow, with idle stretches (standing 7.5–8.5 s, fumbling at the bucket 9.5–11.5 s); the same man and place throughout |
| R2-string | 4.6 s | **10 s** | all five: slack, drawn taut, wound twice, plucked, hands off, the line taut | yes: the right hand draws and winds, the left on the peg | no idle; the watch on the left wrist |
| R2-pointing | 6.8 s | **15 s** | all five: load from the hawk, press in, work along, strike back, lift off | yes: trowel in the right hand, hawk in the left throughout | the wall still flat-laid (the reference picture, as in round 1); a slow start, the hands enter at 1 s |
| R2-kiln | 4.0 s | **15 s** | the five, then **an extra repeat** (the first worker bends and lifts again at 10–12 s) | mostly: the lift is two-handed, the pass and the set right-handed | 3 s idle at the start; **no flame** this time (the place line now says "smoke only, no flame") |
| R2-count | 10 s | **15 s** | one brick at a time, in order, the pan empty at the end, five on the wall | yes | **the pan held two bricks at the start, not five**; the total drifted 2 → 5 as in round 1 |

Cost: 75 s of video = 225 credits (3 a second), about double the round-1 cost of the same five shots.

What this says:
1. **Steps without seconds hold the order** as well as the timeline did: five for five, every step present and in sequence. The seconds were never needed for the order.
2. **The right hand is honoured** wherever a hand is visible, with a line before the steps and "with his right hand" on each step.
3. **Smart duration without seconds makes long takes**: 10–20 s for 4–8 s shots, two to three times the plan's length, with idle stretches and, once, a repeated action. The model fills the time it gives itself. With the seconds in the text (round 1, W1b) it chose the text's last second. So: steps for the order, and either an explicit `--duration` from the plan or one line "the whole shot lasts N seconds", else the take runs long and costs double.
4. **The invention problem is fixable in the text**: "smoke only, no flame" removed the flames of W8.
5. **Counts drift regardless** of the prompt's form (round 1: 3 → 5; round 2: 2 → 5).

## Not covered

- The assembly was not run on these takes (no run holds them); the probe facts are in the logs.
- 1080P, 9:16, audio inputs, `--videos` (a footage stretch as reference): not run.
- One run per scenario except W1 (two); no repeat runs to measure variance.
- The mp4s are not in git (SK has them); the strips are.
