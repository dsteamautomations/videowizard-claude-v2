# design/65 — Visuals: the agreed plan (revision of design/64)

Status: prepared by the builder on 21 Oct 2026 from design/64 (proposed by Revathi) and SK's decisions of the same day. For Revathi's review, then SK's approval. Nothing built. Sources: design/64; the v1 visual guideline audit G1–G20 (received 21 Oct); the current visuals prompt (2,656 words), `visual_contract.py`, `visuals_stage.py`, `stage2/render.py`, `stage3/assembly.py`, the intake code; VW-6's first pass at the stage (33 shots, 25 of them graphics) and the VK02 script document, whose per-scene "Visuals" lines are the team's own picture intentions.

## 1. What is kept from design/64 as written

D2 (text is not a reason to avoid an AI picture), D3 (when a graphic is the right picture), D3a (variety in long gaps), D3b (footage first), D4 (the G-guidelines restored in short form); prompt edits A.2, A.3, A.4, A.5, A.6; server B3 and B4; the test list and the edge cases that go with them. These are not repeated below except where a detail changes.

## 2. SK's decisions on 21 Oct, and what they change

| # | Decision | Effect on design/64 |
|---|---|---|
| S1 | An animated graphic is a **state sequence made with the GPT Image 2.5 API**: two to four approved stills of one diagram, each generated from the previous one as its parent, played as a build with holds and dissolves at assembly. The video-take route for graphics is **off in this release**. | A.1 and A.7 rewritten; B2 replaced by a sequence step; a new render item; a schema field for the states (§4, §5). |
| S2 | One sentence keeps the operator's own file as a route **on the operator's instruction only**; the planner never offers it. | A.8 softened; B5 as proposed (code stays). |
| S3 | The script document's per-scene **Visuals lines are kept at intake** and handed to the planner as the team's intended visuals, a source the treatment must cite or argue against. | New: intake, the visuals package, the prompt's section 2 (§6). |
| S4 | The **treatment is a recorded step**: shown gap by gap with the route counts and the cost estimate, approved with the operator's words, stored on the server before any plan is written. | New server step and gate (§5 B6); step 2 of the procedure; the page's first state. |
| S5 | **Approval per sequence**: all states of a graphic are shown together and approved with one reply; the server keeps every state's hash. | B2's replacement (§5 B2'). |
| S6 | **A cap of ₹1,000 per film** on the visuals stage's paid calls, raised only by the operator with their words. | New: a price table, a spend ledger, a check before every paid call (§5 B7). |
| S7 | **A visuals page in this release**, in the pattern of the review page: the treatment, the references, the state sequences and the takes approved by click; the chat remains the second front end. | New (§8). |

Also folded in, from the live runs of 20–21 Oct (design/49): the visuals package is read as one small file per section (as the options package since design/61), and the procedure says plainly that the treatment comes before the plan (the child skipped it on VW-6).

## 3. The routes, as the planner will see them

Four ways to make a picture, all inside the pipeline:

1. **Footage**: a frame or a still from any clip, used or unused (`vw visuals frame`, free), shown for a shot or used as a reference.
2. **An AI still** (GPT Image 2.5): a photograph-like scene, an illustration, a diagram, a chart or a labelled picture, approved and held for the shot.
3. **An AI graphic sequence** (GPT Image 2.5): two to four stills that are states of one graphic, each made from the previous one so the drawing stays the same and only the new part appears; approved as one sequence; assembled as a build with holds and dissolves, with an optional slow push. This is how a diagram, chart or illustration moves in this release.
4. **AI video**: a take from an approved keyframe, for scenes of people, places, work and material; the three generators and their lengths as today; a start and an end image when the final state matters (A.7 as proposed, for video shots).

A fifth route exists but is never offered: a file the operator supplies, on their instruction (`vw visuals asset`), for a client who owns an animation or an editor who draws better than any model.

What is gone: the hand-made route as a planning choice, the editor-or-AI question, "nothing in this pipeline draws animations or diagrams".

## 4. Prompt text (`server/procedures/v2.json`, visuals `prompt`)

- **A.1 Section 1, the routes.** Replace the four-route paragraph and the hand-made bullet with the four routes of §3 and this: "Every shot is made by one of these routes. Text is not a reason to choose or avoid a route: current image models write accurate text. Put every label, number and caption in the prompt exactly as it must read, keep labels short, and check each one on the candidate before approval; a misspelt candidate is regenerated. A file the operator supplies replaces a shot only on their instruction; never plan one." Remove the animation question and the sentence that writes its answer into `production_constraints`.
- **A.2, A.3, A.4, A.5, A.6** as proposed in design/64.
- **A.3 addition, graphics that move.** After "An abstract sentence does not by itself call for a diagram.": "A graphic that builds or reveals is planned as a sequence of two to four states on one shot of type animation: write what each state adds and how long it holds, at least three seconds a state; the states together fill the shot. The first state is generated like any reference; each later state is generated from the previous one as its parent, with a prompt that names only what changes, so the drawing and its text stay identical. The operator approves the sequence once, seeing all its states. Assembly plays the states with a short dissolve between them and, when the shot asks for it, a slow push. A graphic that does not change is a diagram shot: one still. Arrows that travel and parts that slide are not available in this release; plan a build or a reveal instead."
- **A.3 addition, the team's intended visuals (S3).** After "Build the film's graphics as one visual language…": "The package carries the script document's own visual notes per scene, the team's intended pictures. Treat them as a stated requirement with its source: follow them where they fit the direction and the footage, and where you depart from one, say so in the treatment with the reason."
- **A.7** as proposed, for video shots only (the end image is a video-generator feature).
- **New, section 2, the treatment as a record (S4).** "Before any plan, present the treatment gap by gap: the words under the gap, the team's intended visuals for that scene, your proposed picture in one line, its route, its length, and for a generated route the number of images it needs. End with the counts per route, the seconds of graphics, the estimated cost against the film's cap, and your reasons. Record it on the operator's yes (`vw visuals treatment --file out/visual-treatment.json --quote`); the plan is checked against it. A plan is refused until the treatment is recorded."
- **New, section 6, costs (S6).** "Each generated image and each take is paid and informed, never asked. The film has a cap, ₹1,000 unless the operator sets another; the server refuses a paid call that would pass it, and says so with the spend so far. Only the operator raises the cap, with their words (`vw visuals cap --inr N --quote`)."
- **Section 6, the sequence.** After the still sentence: "A graphic sequence is approved and held in one call: `vw visuals sequence --shot S --refs R1,R2,R3 --quote "…"`, the states in order; each state's hash is recorded. Show the operator all states together before asking."
- **Section 8**: a sequence's review is the review of its states on the page or in chat; a take's review as today.
- **A.8** as proposed except the operator's-file sentence, which stays in the form of §3.
- Word budget: the prompt stays at or below 3,500 words (design/45 test). Estimate after these edits: about 3,200.

## 5. Server (`server/`)

| # | What changes | Where |
|---|---|---|
| B1 | `FILE_TYPES` and the "operator supplies this file" warning go. `routes()` answers `{footage, still, graphic_sequence, video}` with shot counts and seconds each, `graphic_seconds`, and `images_estimated` (one per still, one per state of a sequence, one keyframe per video shot, two when an end image is planned). | `visual_contract.py` |
| B2' | Replaces design/64 B2. New `sequence(store, user, run, outputs, shot_id, reference_ids, quote)`: the shot is of type animation; the references are candidates or approved references of kind `state` (or `keyframe` for the first), in order, one per planned state; every state is approved in this call with its hash; the asset is `{'kind': 'sequence', 'states': [{reference_id, key, sha256, hold_frames}], 'dissolve_frames', 'motion'}`. `prepare_take` keeps refusing anything but video (message: "an animation shot takes a graphic sequence (`vw visuals sequence`)"). | `visuals_stage.py`, `main.py` route `POST /visuals/sequence` |
| B3 | As proposed: `still_from_reference` accepts image and diagram shots, refuses animation ("an animation shot takes a graphic sequence") and video. | `visuals_stage.py` |
| B4 | As proposed, plus the states: on an animation shot `states` is required, two to four entries, each with `what_appears` and `hold_s` ≥ 3, the holds summing to the shot's seconds (±0.2 s); a one-state animation is refused ("one state is a diagram still"); a diagram shot with states is refused. | `visual_contract.py` |
| B5 | `add_asset` stays, reachable only on the operator's instruction. | — |
| B6 | **Treatment record.** `treatment(store, user, run, outputs, document, quote)`: the document has one entry per gap (gap_id, intended_visuals cited or departed from, picture, route, seconds, images) plus the counts; stored in the visuals session as `treatment` with the operator's words, by and at, and a digest. `propose` refuses until a treatment is recorded and the plan's routes per gap agree with it (a changed route needs a new treatment record, with the reason). `status` carries the treatment. | `visuals_stage.py`, `main.py` route `POST /visuals/treatment` |
| B7 | **The cap.** Prices in settings, in INR, to be filled by SK: `VISUALS_PRICE_IMAGE_INR` (one GPT Image 2.5 image at 1536×864 high) and `VISUALS_PRICE_VIDEO_INR_PER_S` per generator. Today no job records a money amount, only tokens, characters or seconds, so the ledger is computed: images × price, take seconds × price. `visuals_spend(conn, run)` sums the run's image and take jobs; `check_cap(conn, run, estimate_inr)` refuses with `VISUALS_CAP` ("₹820 spent of ₹1,000; this call needs about ₹60") before `generate_image` and `submit_take`. The cap lives in the visuals session (`cap_inr`, default 1000), raised by `set_cap(…, inr, quote)` with the operator's words. `status` carries spend, cap and the estimate of what is still planned. | `config.py`, `visuals_stage.py`, `main.py` routes `GET /visuals/budget`, `POST /visuals/cap` |
| B8 | **The sequence as pictures.** A new item kind `sequence` beside `still` in the stage-2 renderer and the assembly: each state looped for its hold frames, a dissolve of `dissolve_frames` (default 12 at 25 fps) between states, an optional push (`motion: none | push`, 3 % over the shot), the whole exactly the shot's frames. Normalised like a still. | `stage2/render.py`, `stage2/render_jobs.py`, `stage3/assembly.py` |
| B9 | **Schema.** `Shot.states: list[State]` (default empty), `State {what_appears: str, hold_s: float}`; reference kind `state` beside isolated, sheet and keyframe; an image generated with `--kind state` requires one parent. Plans valid today stay valid. | `visual_contract.py`, `main.py` |
| B10 | **The team's intended visuals (S3).** Intake: `visual_lines(text, removals)` beside `timing_lines`: the removed lines of kind `visual_note`, grouped under the nearest preceding `scene_heading`, each group with the heading and the first words of the narration that follows; stored in the intake summary as `intended_visuals`. The visuals package carries them as `intended_visuals` so the planner can match each gap to its scene by the words under it. The treatment document cites them per gap. | `plugin/scripts/stages_text.py` (intake record), `visuals_stage.prepare` |
| B11 | **The page's routes** (§8). | `web.py`, `templates/visuals.html` |
| B12 | The visuals package for reading: one file per section under `work/visuals/` (prompt, brief, gaps, intended visuals, world evidence in files of 25 clips, schema), as design/61 did for options. | `plugin/scripts/vw.py` |
| — | `SERVER_VERSION` 0.21.3 → 0.22.0. | `config.py` |

## 6. Intake (S3)

The intake prompt already asks the assistant to mark each removed line with a kind, and `visual_note` is one of them; the VK02 document's "Visuals" bullets are exactly those lines. Nothing changes for the operator: the preview and the record stay as they are. The record gains `intended_visuals`, one entry per document scene: `{heading: "Scene 2: What is Rat-Trap Bond Masonry?", lines: ["Close-up of conventional brick masonry.", "Animation showing bricks laid on edge.", …], narration_starts: "Unlike conventional brickwork, where bricks…"}`. A document without visual notes gives an empty list and the planner is told so.

## 7. Plugin (`plugin/`)

| # | What changes | Where |
|---|---|---|
| C1 | `vw.md`: the visuals paragraph loses the editor question and the hand-made sentence; names the four routes, the treatment record, the sequence, the cap, the page. | `plugin/commands/vw.md` |
| C2 | `vw visuals check` prints the routes, the graphic seconds, the images estimated and the cost estimate against the cap. | `vw.py` |
| C3 | New commands: `vw visuals treatment --file out/visual-treatment.json --quote "…"`, `vw visuals sequence --shot S --refs R1,R2,R3 --quote "…"`, `vw visuals budget`, `vw visuals cap --inr N --quote "…"`; `vw visuals image --kind state --parents R` for a state. | `vw.py` |
| C4 | `vw visuals prepare` writes `work/visuals/` per section and prints the list with row counts; `vw next` and `prepare` print the visuals page link. | `vw.py` |
| — | `plugin.json` 0.20.1 → 0.21.0. | `.claude-plugin/plugin.json` |

## 8. The visuals page (S7)

`/runs/<code>/visuals`, linked from the run page from the first cut on, printed by the tool. Signed in only. Every button calls the same server function the tool calls.

**States of the page, in order:**
1. *Treatment.* The first cut's gaps in film order, each with the words under it, the team's intended visuals for that scene, and the assistant's proposed picture, route, length and images once the treatment is drafted; the counts, the graphic seconds and the estimated cost against the cap at the foot; "Approve the treatment" with the operator's words. Before a draft exists the page says the assistant is preparing it.
2. *Plan.* After the treatment: the plan's gaps and shots; a choice where the plan offers one (`select`); "Accept" per gap or all, with words.
3. *Pictures.* Per shot: the references as thumbnails with Approve by click (the server checks the stored hash); a graphic sequence as a filmstrip of its states with "Approve sequence"; a still shot with "Use this picture"; the images still generating shown with their state. A spend meter with the cap, and "Raise the cap" with a number and words.
4. *Takes.* Per video shot: the takes to watch in the page's player, "Select" with the operator's words or "Reject" with a reason; the duration against the placement shown.
5. *Record.* "Record the gaps" when every shot of a gap has a selection, a still or a sequence; the gaps recorded shown with their cost.

Routes: `GET /runs/{code}/visuals`, `GET /runs/{code}/visuals/data` (status, treatment, plan, references with their image links through the run's file route, takes, spend), `POST /runs/{code}/visuals/act` with actions `treatment`, `select`, `accept`, `approve` (reference, by hash), `sequence`, `still`, `select-take`, `reject-take`, `cap`, `record`. Each goes through the stage gate (`_run_at`, as the review page does). The page polls every 15 s while anything is generating. The page spends nothing itself: generation is started by the assistant, informed in chat.

## 9. Procedure steps (`server/procedures/v2.json`, visuals `steps`)

1. `vw visuals prepare`: the package under `work/visuals/` as files per section; read `prompt.md`, `gaps.json`, `intended-visuals.json` first; the world evidence files after.
2. Settle the treatment in conversation, then write `out/visual-treatment.json` and present it gap by gap, on the page by default (the link is printed): the words, the team's intended visuals, the picture, the route, the length, the images, the counts, the graphic seconds and the cost estimate. On the operator's yes `vw visuals treatment --file … --quote`. Nothing else before this.
3. Author `out/visual-plan.json` to the treatment; `vw visuals check` until valid; answer every warning in the shot's purpose; `propose`; `accept`.
4. References per element in the order of section 5; for a diagram, chart or labelled picture write every label and number exactly and check each on the candidate; a state of a sequence is generated from the previous state as its parent.
5. Per shot: a still (`still`), a graphic sequence (`sequence`), or for a video shot `bind`, `packet`, `prepare-take` (with `--end` when the final state matters), `take`; the operator approves on the page or in chat; `select-take` on their yes.
6. `record --gaps all --quote`.
The hand-made sentence and the animation question go.

## 10. Edge cases

| Case | Expected |
|---|---|
| A plan proposed before the treatment is recorded | Refused: "Record the treatment first (`vw visuals treatment`)." |
| A plan whose route for a gap differs from the treatment | Refused, naming the gap; a new treatment record with the reason clears it. |
| An animation shot with one state | Refused: "one state is a diagram still: plan it as a diagram, or add a state." |
| States whose holds do not fill the shot | Refused with the sum and the shot's seconds. |
| A state under 3 s | Refused (a state is read, not glanced). A diagram still under 3 s: warned, as design/64 B4. |
| `sequence` with a state not generated from the previous one | Accepted with a warning naming it; consistency is the operator's eye on the filmstrip. |
| `prepare-take` on an animation shot | Refused: "an animation shot takes a graphic sequence". |
| `still` on an animation shot | Refused: "an animation shot takes a graphic sequence". |
| A paid call that would pass the cap | Refused with spend, cap and the call's estimate; the assistant tells the operator; `cap` with their words raises it. |
| The cap raised on the page or in chat | Recorded once with the words; both front ends show the new cap at once. |
| A document with no Visuals lines | `intended_visuals` empty; the treatment says so; nothing else changes. |
| The team's intended visual departed from | Allowed; the treatment entry carries the reason, the operator sees it before approving. |
| Five graphics in a row, all-graphics gap, a 6 s static still | Warnings as design/64 B4. |
| A sequence state regenerated after approval | The sequence goes back to candidate; approve again (the hashes changed). |
| The operator supplies a file | `asset` as today, on their words; the page shows it as the shot's picture. |

## 11. Tests first

- `server/unit` `visual_contract`: routes with each type and the images estimate; no file warnings; states required, two to four, holds ≥ 3 s, holds fill the shot; one-state refusal; the B4 warnings as design/64.
- `visuals_stage` (pure, faked store): `treatment` records and `propose` refuses without it or on a changed route; `sequence` approves every state and writes the asset; `still` on diagram accepted, on animation refused; `prepare_take` on animation refused; `check_cap` refuses at the cap and passes under it; `set_cap` needs words; `visuals_spend` sums images and take seconds at the configured prices.
- The renderer: a `sequence` item of three states renders exactly the shot's frames with the dissolves (ffmpeg present on the test machine).
- Intake: `visual_lines` groups visual notes under their scene heading with the narration start; a document without them gives an empty list.
- Prompt test: no "hand-made", no "editor makes", no "Nothing in this pipeline draws"; the four routes named; at or below 3,500 words.
- Plugin: the check line prints the routes, the images and the cost against the cap; the new commands post the right bodies; the package files per section; the page link.
- The page: the template renders in each of the five states (Jinja); the route-exists test already in place covers its paths.

## 12. Not covered

- server/tests (Docker).
- Whether GPT Image 2.5 keeps a drawing identical across states when each is generated from the previous one; the first sequence on a live run is the check. If it drifts, the fallback within this design is one still per state approved as a sequence anyway, since the operator sees all states together.
- The actual prices: the cap is only as true as the two numbers SK fills in.
- Whether the push looks right on a diagram; it is optional per shot and off by default.

## 13. Order of work, versions, deploy

1. Prompt and steps; schema and contract; the treatment record and the gate; the cap. Server 0.22.0.
2. The sequence: reference kind, `sequence`, the renderer and assembly item.
3. Intake `intended_visuals` and the package; the package per section. Plugin 0.21.0.
4. The page.
5. Deploy server then plugin; the operator restarts Claude Code once. VW-6's visuals stage was reset on 21 Oct, so it starts at `vw visuals prepare` on the new flow; its first treatment and its first sequence are the live checks.

## 14. For Revathi's review

- S1 replaces design/64's video-take animation with the state sequence; A.7 stays for video shots. Agree, or keep the take route open per shot?
- S3 is new: intake keeps the script's Visuals lines and the planner treats them as a stated requirement with a source. Agree with the placement in section 2?
- The cap needs two prices in INR. Who supplies them?
- Dissolve 12 frames and push 3 % are proposed defaults; per-shot override only.
