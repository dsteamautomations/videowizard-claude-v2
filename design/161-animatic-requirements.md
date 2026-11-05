# 161 — Requirements: the animatic branch (visuals steps 5–6, the `video` route) — 5 Nov 2026, consolidated

Status: requirements note, no code. First written 5 Nov after the double-check (design/155); amended the same evening after the test round (design/156–168) and SK's agreement to design/167 §5 and design/168; **rewritten whole on 5 Nov night so that one text holds every rule, with no section overriding another.** The words follow the glossary (design/152); new words are defined in section 1.

## 1. Words

- **animatic**: a cartoon video, drawn by a helper from the plan to the rules of section 5, that guides one take. Never shown in the film.
- **animatic unit**: what one animatic and one take cover: a single shot, or a whole scene whose plan carries `one_take: true`.
- **`one_take`**: a yes-or-no mark on a scene in the plan. True means the scene's shots are made as one take with the cuts inside it, instead of one take per shot. It is a property of one scene, not a list of scenes.
- **speed table**: the measured seconds the generator takes for common actions (section 5.4). The cartoon is drawn to it.
- **action marks**: the seconds at which each drawn action begins and ends and each cut falls, written by the drawing helper as it draws (`marks.json`), measured by the server against the rendered cartoon.
- **take text**: the prompt sent with the take (today's motion text). On an animatic unit it is written from the animatic's marks (section 6).
- **guide sentence**: "Keep every shot, every cut, the camera angles and moves, the timing, the positions of the people and objects, the direction each person faces and the direction of every action exactly as in the video. Change only the look. Do not copy the cartoon drawing style."
- **state sentence**: one sentence for the one thing that changes in the unit, in look terms, never in numbers: what it is, where it ends, that it never returns.

## 2. What changes, in one paragraph

On the `video` route an animatic unit no longer gets a start image and an end image. It gets an animatic, checked by a helper against the rules, approved by the operator on the Takes step, and sent to Omni as the input video together with the photographs of what is in the shot and the take text. Omni edits the cartoon into the take. Cuts inside a take are allowed when the scene is `one_take`. Everything else in the stage (references, the round, the sets, stills, graphics, HyperFrames, review, record) is untouched. The old way stays for every shot that is not an animatic unit.

## 3. Decisions (locked; SK reopens by number)

| # | Decision | Shown by |
|---|---|---|
| D1 | **Scene design first, by the staging rules of section 4.** A shot that needs a true count of identical things is footage, a still or the drawn route, never AI video. | 165, 166 |
| D2 | The animatic goes in as the **input video to be edited**, up to 10 s, one per call; never as a 3-second reference, never as still frames. With it go **only the photographs of the people and things in the shot** and the **take text**. No storyboard frames; dense frames are off by default and may be tried once for a facial moment (E6). | 155, 158–160, 164–166 |
| D3 | **The animatic decides the seconds.** The plan gives the beats in order and the unit's seconds (fixed by the narration). The helper draws at the speed table's pace; the server measures the marks and writes the take text from them. A cartoon faster than the table is refused; beats that do not fit the seconds send the plan back for revision, never the pace squeezed. | 158, 163, 165, 166, 168 §2 |
| D4 | The animatic unit is a **shot, or a `one_take` scene**. Inside a `one_take` scene a shot may be shorter than 3 s; the take carries the cuts. | 155, 156, 157 |
| D5 | A scene longer than 10 s is **split at a shot boundary that is not a state change** into segments, each its own unit; continuity between segments as today (the sets, the light line, the person lines). | 155, 163 |
| D6 | **No canvas**; the place set is enough. | 155, nine runs |
| D7 | **The operator approves the animatic** every time, after the check helper, in the slot of today's start-image approval. Free to redo. | 154 §9 |
| D8 | Generator unchanged: **Gemini Omni 1.1 Flash** through the interactions endpoint; a `video` input item added through the Files API. | SK 5 Nov, 156 |
| D9 | The **generic drawing rules G1–G8 are the must lines** of the animatic check; the speed table is a should line; the emotion rules E1–E6 are must lines. | 168 |
| D10 | **No count of identical things** is stated anywhere in the plan, the animatic or the take text. Colour tags on a changing thing are allowed in the cartoon as a guide but are never relied on; the film-visible difference (G3) is what keeps a transfer straight. | 158–166 |
| D11 | The **single-shot sentence**, the **`<FIRST_FRAME>` tags** and the **drift check** are off on an animatic take. | 155, Google's deprecation |
| D12 | **Cartoons render at 24 fps**, 1280×720 (or the film's shape). | 168 §3 |
| D13 | **Documentary** defaults to one or two angles and a hold; **advertisement and drama** default to cutaways, reactions, point of view. A category rule, not a general one. | 154 §9 |
| D14 | **Build order**: (i) `one_take` and the timecoded take text, which work without an animatic; (ii) the staging, emotion and prompt rules into the plan step and the plan checks; (iii) the animatic. | 156, 167 D6 |
| D15 | **Not pursued**: the frames path; two-video continuity; numbers and labels as a fix for counts; WAN and Kling (SK's own side tests). | 155, 162–166 |

## 4. Staging rules (the plan step and the plan check; category D13 on top)

| # | Rule |
|---|---|
| S1 | Establish wide, then cut tight on the action. One action per shot. |
| S2 | What we avoid is inventories, not people. A group of identical things is kept out of the count by framing (its edges outside the frame) or by what the hands hold, never by cropping a person. |
| S3 | A handful of identical things may be moved, one or two at a time. A total that must be exact is never asked of AI video (D1). |
| S4 | A thing that changes state looks different, in the film, from what it joins (new against old, a colour, a size). If it cannot, the change is not shown. |
| S5 | The destination of a moved thing is a hand, a row, a wall top or a different-looking group, never a heap of its own kind. |
| S6 | A change of state happens inside one shot, with the thing in view before, during and after. No cut falls between the last sight of a state and its change (also the rule for where D5 splits). |
| S7 | A cut changes angle or size clearly. A camera move is slow and long, or absent. |
| S8 | Every scene has at least one face shot (E1). |

The plan check refuses: a stated count of identical things (S3, D10); a changing thing with no stated look difference (S4); a cut between a state and its change (S6); two consecutive shots whose camera lines are the same (S7); a `one_take` scene whose shots sum over 10 s (D5); a shot under 3 s outside a `one_take` scene (as today); a scene with no face shot (S8, warning only on the documentary category's single-angle default).

## 5. Drawing rules (the drawing helper's skill; the check helper's must lines)

### 5.1 The generic rules (design/168 §1)

| # | Rule | Found by |
|---|---|---|
| G1 | **Draw what decides the outcome.** Any detail the shot's meaning depends on is drawn explicitly, in contact, with its result; what the model would do by habit anyway is left to it. Examples: where a tool acts (tip on the course, mortar left there); which way a person faces (nose, eyes, back of head, feet); what each hand holds; which way a transfer goes and where the thing lands. | 158, 160, 162, 163 |
| G2 | **The film is never asked to keep a tally.** | 158–166 |
| G3 | **A change is seen, not implied.** The camera stays on a state change from before to after; the changing thing looks different from what it joins. | 162, 163, 165, 166 |
| G4 | **Every second has a drawn cause.** No gap; a closing action with a margin of a second; the pace from the speed table. | 158, 160, 166 |
| G5 | **Things that must be told apart look apart.** No two things of one shape and colour in a frame unless they are the same thing. | 158, 162 |
| G6 | **Cuts and moves are unmistakable or absent.** | 159, 164–166 |
| G7 | **The cartoon, the take text and natural behaviour never disagree.** | thread F5, 166 |
| G8 | **Nothing in the inputs that is not in the shot.** Photographs only of what is in frame; no word naming equipment or a state of building. | 162, 165 |

### 5.2 Craft rules (how the helper draws)

One fixed world per scene, every shot a crop of it. No body hides an object that matters; a contact point is inside the frame. A thing's size is legible at the size the model sees it. The figure library supplies people in named poses with facing, heads with brow, eyes and mouth, hands, common objects, the camera helpers. The key stills (one per shot and one per action mark) are rendered and read before anything is uploaded.

### 5.3 Emotion rules (design/168 §4)

| # | Rule |
|---|---|
| E1 | Every scene has at least one shot on a face: concentration, effort, a reaction, a look between two people. |
| E2 | A face is never cropped by the frame to hide a count. Headroom is a check line. |
| E3 | A tight shot on an action may hold the face in the same frame (over the shoulder; hands and eyes). |
| E4 | A facial moment gets a longer, closer, continuous shot with a hold of at least a second, drawn with the expression and named in the take text as action plus emotion. |
| E5 | Who looks at whom is drawn, so a reaction lands on its cause. |
| E6 | The photographs of the people in the shot always go in. A face shot is the one place a dense frame may be tried. |

### 5.4 The speed table (a should line; grows by commits)

A pair of bricks lifted from a pan and set on a pile 1.5 s · a knee-high barrel lifted from waist height and set down 1.6 s · a step 0.5–0.6 s · a squat 1.0 s · a head turn 0.6–0.8 s · one brick handed from one person to another and laid 2.4 s · a closing action (lift an empty container and rise) 1.2 s plus a margin of 1.0 s.

## 6. The take text (written by the server from the marks)

In order: the guide sentence; the photographs named by what they show; the place in one or two sentences; the people and large objects by look (from the sets' descriptions); the fixed positions (who is left, who is right, who faces where, who never moves); each shot with its seconds from the marks, its cut named ("cut to …"), the one action of the shot, the camera ("the camera does not move" or its one slow move); the state sentence; "no dialogue, no music, no text or captions" (the category may add sound). Never: a count of identical things; a word naming camera equipment; "half-built" or any word that invites building; a thing not in the shot; the single-shot sentence; frame tags.

## 7. The flow, step by step (visuals stage, `video` route)

1. **Plan** (step 3): `Scene.one_take`; the plan checks of section 4; the category defaults (D13).
2. **References** (step 5): unchanged; the sets as today.
3. **Animatic** (new, between steps 5 and 6): once the unit's references are approved and the shots are bound, the assistant runs one `vw-animatic-shot` helper per unit (several at once). The helper writes the project (the HyperFrames machinery, rendered in Chromium at 24 fps) from the plan, section 5 and the figure library, with `marks.json`; uploads it (`vw visuals animatic --shot S --file …` or `--scene C --file …`); the server renders the mp4, measures the marks (its scene-change measure confirms the cuts), and makes the contact sheet (two frames a second plus every mark) and the key stills. A `vw-animatic-check` helper reads the sheet against the shot lines and G1–G8, E1–E6, the speed table; failed must lines go back to a drawing helper; at most two redo rounds; then the operator sees the open lines. Free: no paid call.
4. **Approval**: the animatic (video, sheet, marks, the take text the server wrote) on the Takes step; approve, or send back with words. In chat `vw visuals animatic --shot S --approve --sha … --quote "…"`.
5. **Take** (step 6): `prepare-take --animatic <sha>` (no `--start`/`--end`); the server uploads the mp4 through the Files API, waits for `ACTIVE`, and builds the request: the video item first, then the photographs of the elements in frame (each element's golden picture or set picture), then the take text. Duration = the animatic's seconds. Everything after (Gemini reads the take, the operator watches, select or reject) unchanged, with the read's new lines of section 9.
6. **Assembly**: a `one_take` scene's job is recorded on every shot of the scene with `offset_frames` = the shot's start inside the animatic; assembly stays one fill per shot.

**Step (i) without an animatic**: a `one_take` scene may be taken today's way (start image, no cartoon) with the take text of section 6 written from the plan's shots and the single-shot sentence dropped. That is what D14 (i) ships first.

## 8. Changes by file

| Area | File | Change |
|---|---|---|
| Plan contract | `server/app/visual_contract.py` | `Scene.one_take`; the section 4 checks; `Shot.animatic: {sha256, seconds, marks, approved_at}` |
| Procedure text | `server/procedures/v3.json` (part `plan`: section 4's rules; part `later`: sections 6 and 9 rewritten for the animatic unit; a new section `12. THE ANIMATIC` with sections 5 and 6 of this note); `scripts/d161_wording_v3.py` with its anchor test | |
| Animatic job | `server/app/animatic.py` (new, on `motion.py`'s render, `frames_png`, `snapshot`): upload, render, marks, sheet, check rounds, approval; routes in `server/app/main.py` | |
| Take request | `server/app/visuals_stage.py` `prepare_take --animatic`; `server/app/video_providers.py`: Files API upload (resumable, poll `ACTIVE`, re-upload after the 48-hour expiry), the `video` input item, `animatic_text()` beside `motion_text()`; `image_check.take_drift` skipped; the cost record carries the input video tokens | |
| Assembly | `server/app/stage3/assembly.py`: the shared job with per-shot default offsets | |
| Page | `server/app/templates/visuals.html`, `web.py`: the animatic card on the Takes step (video, sheet, marks, take text, approve, send back) | |
| Plugin | `plugin/scripts/vw.py`: `vw visuals animatic` (upload, status, approve, send-back, download), `prepare-take --animatic`; `plugin/agents/vw-animatic-shot.md`, `vw-animatic-check.md`; `plugin/skills/animatic/` (sections 4–6 of this note as the skill, the figure library) | |
| Procedure check | `scripts/c1_split_v3.py --check` passes; the word budget test | |

## 9. Unstated but expected requirements

- The old way (start image, end image, golden picture, locked camera, one take per shot) stays the default for every shot that is not an animatic unit, for the `still` route, and for films past step 5 when this goes live. Nothing is removed. The step text tells the operator the two ways.
- The animatic is never the film: assembly refuses an animatic sha as a fill.
- Every paid call is said, not asked, as today; rendering and checks are free.
- The decision log (design/142) records the animatic's approval and each redo round.
- `vw output` and `vw view` show the animatic beside its take.
- The Gemini read of a take gains lines: the take's cuts against the marks; no tag colour visible; no invented action after the last mark; a face not cropped.
- Minimum plugin version bumped; the server refuses an older plugin's `prepare-take` on an animatic unit with the message naming the update.
- The live check after deploy is judged on half-second strips at 480 px or larger, and SK watches the video (D8 of design/167).

## 10. Edge cases and how each is handled

| Case | Handling |
|---|---|
| Animatic longer than 10 s, or longer or shorter than the unit's placement | refused at upload with the seconds; the helper redraws (G4) or the plan is revised (D3) |
| Actions faster than the speed table | the check refuses the animatic with the measured and the table seconds |
| Beats that do not fit the unit's seconds at the table's pace | the plan goes back for revision (fewer beats, a hold, a longer gap at the next revision) |
| `one_take` scene over 10 s | plan check refuses: split at a shot boundary that is not a state change (D5) |
| A shot under 3 s outside a `one_take` scene | plan check refuses as today |
| A cut drawn between a state and its change | plan check (S6) and animatic check refuse |
| Two consecutive shots whose framings are alike | plan check warns (S7); the animatic check refuses a cut the scene-change measure cannot find |
| A face cropped by the frame | animatic check refuses (E2) |
| A count of identical things in the plan or the take text | plan check refuses; the server strips numbers of identical things from the take text and names the line |
| Files API upload fails or never reaches `ACTIVE` | the job fails with the provider's text; `vw visuals recover` re-uploads; no automatic resubmission |
| The file expired (48 h) before submission | re-upload on submit; the sha checked |
| The API refuses the request (`INVALID_ARGUMENT`, as T4's frame set) | the job fails with the text; the operator retries once; a second refusal marks the unit for the old way |
| The take cuts where the animatic does not, or does not where it does | the Gemini read marks it against the marks; the operator decides |
| A tag colour visible in the take | a mark; the operator decides |
| Invented action after the last mark | a mark; the check already refuses a cartoon with an empty last second |
| Two redo rounds fail | the operator sees the open lines: approve as is with notes, redraw with words, or the old way for that unit (`prepare-take --start`) |
| The figure library lacks a figure | the helper draws it from shapes to section 5; the library grows by a commit, never in a run |
| A scene with no people | the same rules minus facing and E1–E6 |
| Cost | the take's record carries the input video tokens (5,792 a second); the price line in config updated |
| Concurrency | one animatic job per unit; a second upload while one renders is refused with the job id |
| Attempt caps | an animatic redo is free and does not count; a take counts as today |

## 11. Failure modes

- The helper's first cartoons are poor: the check and the operator's approval guard every paid take; the library and the rules improve by commits.
- The model drifts from the cartoon in degree (a taller wall): accepted; the checks judge positions, direction, timing, facing, not degree.
- A cut-heavy take between real footage looks wrong in a documentary: D13's default; the operator's eye at review.
- Dialogue does not come from the cartoon edit (Google: speech only when extending a model-made clip): a later phase.

## 12. Tests, written first

Pure tests: the plan checks of section 4; `animatic_text()` against a frozen expected string (the guide sentence, the state sentence, the timecodes from marks, no single-shot sentence, no tags, no numbers of identical things); the provider's request body with the video item first and only the in-frame photographs; the assembly offsets for a shared job; the wording script's anchors; the animatic upload refusals (seconds, sha, speed). Server tests (Docker): the animatic job's states, marks and approval; the take submission with a stubbed Files API. Plugin tests: the new subcommands' parsers. The live check after deploy: one scene on a fresh run, drawn by the helper from the plan, two takes, judged as section 9's last line says.

## 13. Old ways (design/35)

Start image, end image, golden picture, locked camera, one take per shot: **kept** as the default and on `still`; **retired** only on an animatic unit. The frame tags: retired on animatic takes; a separate note for the regular flow. The storyboard-frames path and the thread's two-video continuity: **not built**.

## 14. Estimate

One builder, after SK's go, in D14's order: (i) plan flag, take text, tests 2 days; (ii) the rules into the procedure and the plan checks 2 days; (iii) animatic job and page 3, take request and Files API 1–2, assembly offsets 1, plugin commands and the two helpers 2, the figure library and the skill 3–5. **14–17 days** in three deployable parts.

## Not covered

- The dialogue phase; the deprecated frame tags on today's takes; success rates (one or two runs per case); the operator's chat text for the new step (written with the wording script); a cartoon unit cut between real footage (untested).
