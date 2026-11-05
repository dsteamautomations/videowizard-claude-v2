# 161 — Requirements: the animatic branch (visuals steps 5–6, the `video` route) — 5 Nov 2026, for SK's approval

Status: requirements note, no code. Built on design/153 (scope), 155 (double-check), 156–160 (nine Omni runs on two scenes). Everything decided below was shown by a test; the "why" column names the note.

## 1. What changes, in one paragraph

On the `video` route a shot, or a scene marked `one_take`, no longer gets a start image and an end image. It gets an **animatic**: a cartoon video drawn by a helper from the plan, to fixed drawing rules, approved by the operator on the Takes step, and sent to Omni as the input video together with the sets and a timecoded prompt. Omni edits the cartoon into the take. Cuts inside the take are allowed when the scene is `one_take`. Everything else in the stage (references, the round, the sets, stills, graphics, HyperFrames, review, record) is untouched. The old way stays for every shot that is not on this path.

## 2. Decisions (locked unless SK reopens one)

| # | Decision | Why |
|---|---|---|
| D1 | The cartoon goes in as the **input video** (edit), with the photographs (the sets) and a **timecoded** prompt; never as a 3-second reference, never as frames | 155 (3 s cap); 158 (frames lose direction); 159 (frames leak tags, invent cuts, move the mason); 160 (extra frames pull actions early) |
| D2 | The unit of an animatic and a take is a **shot, or a scene with `one_take: true`**; inside a `one_take` scene shots may be shorter than 3 s and the take carries cuts | 155 §2, 156 (cuts from the timecoded text), 157 (three angles held) |
| D3 | Scenes longer than 10 s are **split at a shot boundary** into segments, each its own animatic and take; continuity between segments as today (sets, light line, person lines) | 155 (one video per call; 10 s input cap) |
| D4 | **No canvas** (design/153's fourth reference); the place set is enough | 155 §1; nine runs without one |
| D5 | The **operator approves the animatic** every time, in the slot of today's start-image approval | 154 §9 |
| D6 | Generator unchanged: **Gemini Omni 1.1 Flash** through the interactions endpoint; a `video` input item added | SK 5 Nov; 156 |
| D7 | The drawing rules of design/160 are **must lines** of the animatic check; the reference-speed table is a should | 157–160 |
| D8 | Colour tags on elements that change state, with the state sentence in the prompt | 158, 159 |
| D9 | The single-shot sentence and the `<FIRST_FRAME>` tags are **not sent** on an animatic take; the drift check is off on it | 155 §5, Google's deprecation |
| D10 | Documentary category defaults to one or two angles and a hold; advertisement and drama default to cutaways, reactions, point of view | 154 §9 |

## 3. The flow, step by step (visuals stage, `video` route)

1. **Plan** (step 3): `Scene.one_take: bool` (default false). `vw visuals check` allows a shot under 3 s only inside a `one_take` scene and refuses a `one_take` scene whose shots sum to more than 10 s ("split at a shot boundary"). Category planning rules (D10) in the plan part.
2. **References** (step 5): unchanged; the sets as today.
3. **Animatic** (new, between steps 5 and 6): once the shot's (or scene's) references are approved and the shot is bound, the assistant runs one `vw-animatic-shot` helper per unit (several at once). The helper writes an SVG-animation project (the HyperFrames machinery, rendered in Chromium at the film's fps) from the plan, the drawing rules and the figure library, uploads it (`vw visuals animatic --shot S --file …` / `--scene C`), and the server renders the mp4, the contact sheet (two frames a second plus every cut) and the key stills. A `vw-animatic-check` helper reads the sheet against the shot lines and the rules; failed must lines go back to a drawing helper; at most two redo rounds; then the operator sees the open lines. Free: no paid call.
4. **Approval**: the animatic (video, sheet, the take text the check helper wrote from it) on the Takes step; approve, or send back with words. `vw visuals animatic --shot S --approve --sha … --quote "…"` in chat.
5. **Take** (step 6): `prepare-take` on an animatic unit takes `--animatic <sha>` instead of `--start`/`--end`; the server uploads the mp4 through the Files API, waits for `ACTIVE`, and builds the request: the video item first, then the sets' pictures (the golden picture of each element in frame), then the text: the edit sentence, the state sentence (D8), the fixed positions, the timecoded shot list with counts, the closing action, the props line, no dialogue, no music, no captions. No single-shot sentence, no frame tags. Duration = the animatic's seconds. Everything after (Gemini reads the take, the operator watches, select or reject) unchanged.
6. **Assembly**: a `one_take` scene's job is recorded on every shot of the scene with `offset_frames` = the shot's start inside the animatic; assembly stays one fill per shot.

## 4. Changes by file

| Area | File | Change |
|---|---|---|
| Plan contract | `server/app/visual_contract.py` | `Scene.one_take`; the under-3-s and over-10-s checks; `Shot.animatic: {sha256, seconds, approved_at}` |
| Procedure text | `server/procedures/v3.json` (part `later`): sections 6 and 9 rewritten for the animatic unit; a new section `12. THE ANIMATIC` with the drawing rules and the reference speeds; a wording script `scripts/d161_wording_v3.py` with its anchor test | design/124's method |
| Animatic job | `server/app/animatic.py` (new, on `motion.py`'s render, `frames_png`, `snapshot`): upload, render, sheet, check rounds, approval; `server/app/main.py` routes `/visuals/animatic` | |
| Take request | `server/app/visuals_stage.py` `prepare_take`: `--animatic`; `server/app/video_providers.py`: Files API upload (`upload/v1beta/files`, resumable, poll `ACTIVE`, 48-hour expiry handled by re-upload), the `video` input item, `animatic_text()` beside `motion_text()`; `image_check.take_drift` skipped on animatic takes; the cost record carries the input video tokens | |
| Assembly | `server/app/stage3/assembly.py`: the shared job with per-shot default offsets | |
| Page | `server/app/templates/visuals.html`, `web.py`: the animatic card on the Takes step (video, sheet, take text, approve, send back) | |
| Plugin | `plugin/scripts/vw.py`: `vw visuals animatic` (upload, status, approve, send-back, download), `prepare-take --animatic`; `plugin/agents/vw-animatic-shot.md`, `vw-animatic-check.md`; `plugin/skills/animatic/` (the drawing rules, the figure library: people in named poses with facing, heads, hands, common objects, the camera helpers, colour tags) | |
| Procedure check | `scripts/c1_split_v3.py --check` still passes; `server/unit/test_design125_stage7_c_pure.py` word budget | |

## 5. Unstated but expected requirements

- The old way (start image, end image, golden picture, locked camera, one take per shot) stays the default for every shot not marked for the animatic, for the `still` route, and for films already past step 5 when this goes live. Nothing is removed. The operator is told the two ways in the step text.
- The animatic is never shown as the film: assembly refuses an animatic sha as a fill.
- Every paid call is said, not asked, as today; the animatic's rendering and checks are free.
- The decision log (design/142) records the animatic's approval and each redo round.
- `vw output` and `vw view` show the animatic beside the take.
- Minimum plugin version bumped; the server refuses an older plugin's `prepare-take` without `--animatic` on an animatic unit, with the message naming the update.

## 6. Edge cases and how each is handled

| Case | Handling |
|---|---|
| Animatic longer than 10 s, or longer than the unit's placement | refused at upload with the seconds |
| Animatic shorter than the placement | refused; the drawing helper must fill the seconds (the pace rule) |
| `one_take` scene whose shots sum over 10 s | plan check refuses: split at a shot boundary |
| A shot under 3 s outside a `one_take` scene | plan check refuses as today |
| Files API upload fails or the file never reaches `ACTIVE` | the job fails with the provider's text; `vw visuals recover` re-uploads; no automatic resubmission (as every paid call) |
| The uploaded file expired (48 h) before submission | re-upload on submit; the sha is checked |
| The API refuses a video with pictures | not seen in nine runs; if it happens, the job fails with the text and the operator may `prepare-take` with `--no-sets` (identity from the text alone), flagged on the card |
| The take has a cut where the animatic has none, or none where it has one | the Gemini read of the take compares the take's cuts to the animatic's (the server's scene-change measure); a mismatch is a mark on the card; the operator decides |
| A tag colour appears in the take | the Gemini read carries a must line "no element shows a tag colour"; a failure is a mark |
| The model invents a closing action or filler | the check helper refuses an animatic whose last second has no drawn action; after that, a mark on the take as above |
| Two redo rounds fail | the operator sees the open must lines and decides: approve as is (with notes), redraw with words, or fall back to the old way for that shot (`prepare-take --start`) |
| The figure library has no figure for a thing | the helper draws it from shapes to the rules; the check reads it; the library grows by a commit, never in a run |
| A scene with no people (objects only) | the same rules minus facing |
| Cost | the take's record carries the input video tokens (5,792 a second) with the output tokens; the price line in config updated |
| Concurrency | one animatic job per unit; a second upload while one renders is refused with the job id |
| Attempt caps | an animatic redo is free and does not count; a take counts as today |

## 7. Failure modes

- The helper's cartoons are poor at first: the operator's approval before any paid take is the guard; the figure library and the rules improve by commits.
- The model drifts from the cartoon in the look (taller walls): accepted; the check is on positions, counts, direction, timing, not on degree.
- A cut-heavy take between real footage looks wrong in a documentary: D10's default; the operator's eye at review.
- Dialogue: not from the cartoon edit (Google: speech only when extending a model-made clip); a later phase.

## 8. Tests, written first

Pure tests (no Docker): the plan checks (one_take, 3 s, 10 s); `animatic_text()` against a frozen expected string (no single-shot sentence, no tags, the state sentence, the timecodes, the counts); the provider's request body with a video item first; the assembly offsets for a shared job; the wording script's anchors; the animatic upload refusals (seconds, sha). Server tests (Docker): the animatic job's states and the approval; the take submission with a stubbed Files API. Plugin tests: the new subcommands' parsers. The live check after deploy: one scene on a fresh run, the mason scene redrawn by the helper from the plan, two takes.

## 9. Old ways (design/35)

Start image, end image, golden picture, locked camera, one take per shot: **kept** as the default and on `still`; **retired** only on an animatic unit. The frame tags: retired on animatic takes; a separate note for the regular flow. The storyboard-frames path: **not built** (159, 160); the thread's two-video continuity: **not available** (155).

## 10. Estimate

One builder, after SK's go: plan and checks 1–2 days; procedure text and wording script 1; animatic job and page 3; take request and Files API 1–2; assembly offsets 1; plugin commands and the two helpers 2; the figure library and the drawing-rules skill 3–5; tests throughout. **12–16 days**, deployed in two parts: first the plan flag and the cuts in a take (D2, D9) which work without any cartoon (156), then the animatic.

## Not covered

- The dialogue phase; the deprecated frame tags on today's takes; success rates (one scene, nine runs); the operator's chat text for the new step (written with the wording script).
