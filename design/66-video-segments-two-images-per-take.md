# design/66 — Video shots in segments, two images per take, the cap at ₹5,000

Status: requirements note, prepared by the builder on 21 Oct 2026 from the feedback on VW-6's visual treatment (multi-image control of AI video, pasted by SK the same day) and SK's decisions of the same day. For SK's approval. Nothing built. Sources: the feedback; design/65; the current visuals prompt (3,497 words), `visual_contract.py`, `visuals_stage.py`, `video_generators.py`, `video_providers.py`, `vw.py`; VW-6's treatment draft of 21 Oct (31 pictures, 3 AI video shots).

## 1. The feedback, and SK's decisions

The feedback says four things about AI video. A video model makes at most ten seconds, so a longer shot is made as segments, cut where the action breaks, not at the clock. Each segment is driven by two images, a start and an end, not one: the end image is the start image moved on by one small action, the same people, the same room, the same light, framed so that what the motion heads for is already in view. The images a gap needs are counted from its segments. And the cap stops being a factor: ₹4,000 to ₹5,000 a film.

SK decided on 21 Oct:

| | Decision |
|---|---|
| 1 | VW-6's treatment is revised toward AI video for the scene-like gaps; graphics stay for what a camera cannot show. |
| 2 | Segments share their boundary picture: the end image of one segment is the start image of the next. |
| 3 | The end image is mandatory on every take, no waiver. |
| 4 | Gemini Omni at 10 seconds stays the default generator; segments are sized to it. |
| 5 | The cap default becomes ₹5,000 for every film; VW-6's cap is raised today in the operator chat with SK's words, before any deploy. |
| 6 | Middle frames are not built: no generator in the catalogue takes them. |

## 2. What exists today

- A take takes a start image and an optional end image (`prepare_take`, `visuals_stage.py`); both must be approved references. All three generators accept the end image (`video_generators.CATALOG`, `end_image: True`); the adapters send first and last only (Kling `last_image_url`, Seedance `end_image_url`, Omni a two-image input). Nothing takes a middle frame.
- A video shot longer than its generator's maximum is refused at preparation ("split it or choose another generator"); the plan check warns `length` against the default generator. The prompt says "a shot that needs a middle state is two shots" and adds the end image only "when a video shot's final state matters".
- The image estimate (`visual_contract.routes`) counts one image per video shot. The treatment's `images` per gap is a whole number the assistant writes; the server's estimate multiplies it by the price.
- A keyframe is generated with `--parents` that must all be approved; a state may be generated from a candidate parent (design/65).
- The cap default is ₹1,000 (`settings.VISUALS_CAP_INR`), per film in the visuals session, raised by the operator with words. The prices behind the meter are still the builder's estimates (₹20 an image, ₹8 a second).
- VW-6's draft treatment has three AI video shots (5.0, 4.4 and 4.4 s); the 27.6 s first gap in the feedback's example is a still and two graphic sequences in that draft.

## 3. The rule, in words

A video gap is planned as segments, each a shot in the plan, each at most what the generator makes (ten seconds for Omni), each cut where an action begins or ends, never at a round number of seconds. Every segment has a start image and an end image. The end image is composed from the start image, generated with the start image as its parent and a prompt that names only the change: the same people, props, place and light, one small action further on, and framed so that what the motion heads for (the table, the window) is already in view in both. Where one segment ends the next begins, so the end image of a segment is the start image of the one after it: a gap of three segments needs four images, and the join between two takes is one picture both share. The plan already describes each subject's start and end state per shot and makes shots tile the gap exactly, so the end image is the shot's end state drawn; no schema change.

## 4. Changes

### A. The visuals prompt (stage 9 prompt, `server/procedures/v2.json`)

The prompt is at 3,497 of its 3,500 words; the additions below are paid for by trimming the passages they replace and two sentences that now repeat the steps.

| | Change | Where |
|---|---|---|
| A1 | The AI video route bullet says: a take from a start and an end image, for scenes of people, places, work and material; Omni makes 3 to 10 s; a longer shot is several segments (§3), Kling and Seedance per shot only when a single action cannot be cut. | section 1 bullet |
| A2 | The treatment paragraph: for a video gap, the segments with their seconds, and the images as segments plus one. | section 2 |
| A3 | The keyframe passage: replaces "When a video shot's final state matters … a shot that needs a middle state is two shots" with the rule of §3: compose the start image; generate the end image from it as its parent with a prompt naming only the change, framed to include what the motion heads for; approve both; the next segment's start is this end. | section 5 |
| A4 | The take passage: `prepare-take --shot S --start R --end R2 …`; the generator sentence drops "only when the default does not fit the shot's length" (the route bullet says it). | section 5 |
| A5 | The cap sentence: ₹5,000. | section 6 |

### B. The steps and the command doc

| | Change | Where |
|---|---|---|
| B1 | Step 2 (treatment): a video gap's entry names its segments with their seconds; images are segments plus one. | step index 1 |
| B2 | Step 4 (references): the end keyframe: `image --element E --kind keyframe --parents <start keyframe> --prompt "<only what changes>"`, generated as soon as the start candidate exists, both shown together and approved together. | step index 3 |
| B3 | Step 5 (per shot): `prepare-take --shot S --start R --end R2 --motion "…" --subject E1="…"`, the end required; the next segment's `--start` is this `--end`. | step index 4 |
| B4 | `vw.md` visuals paragraph: `prepare-take --start R --end R2`. | `plugin/commands/vw.md` |

### C. The server

| | Change | Where |
|---|---|---|
| C1 | `routes()`: the images estimated for video follow §3: in each scene a run of consecutive video shots counts its length plus one; a video shot on its own counts two. Stills and sequences as today. The check line, the budget and the page carry it without change. | `visual_contract.py` |
| C2 | `prepare_take` requires `end_image`, with a message that names the way: "Every take has a start and an end image: generate the end from the start (`vw visuals image --kind keyframe --parents <start>`), approve both, then `--start R --end R2`." Both approved, as today; start and end distinct. | `visuals_stage.py` |
| C3 | `generate_image`: a keyframe may have one parent that is still a candidate when that parent is itself a keyframe (the start); every other parent approved, as today. A state unchanged. | `visuals_stage.py` |
| C4 | `VISUALS_CAP_INR` default 5000.0; the comment says SK set it on 21 Oct. A film whose session already holds a cap keeps it. | `config.py` |
| C5 | `SERVER_VERSION` 0.23.0. | `config.py` |

### D. The plugin

| | Change | Where |
|---|---|---|
| D1 | `prepare-take` without `--end` is refused in the plugin before any request, with the same message as C2. | `vw.py` |
| D2 | `plugin.json` 0.22.0. | `plugin/.claude-plugin/plugin.json` |

Not changed: the treatment document's shape (the segments go in the picture line and the images count); the plan schema; the visuals page (the references list already carries each reference's kind and parents); assembly, which places each take by its frames and cuts consecutive takes hard, which is right when the two takes share their boundary picture; the generators and adapters.

## 5. VW-6

Two things happen on VW-6 itself, neither by code:

1. Before the deploy, the child raises the cap with SK's words: `vw visuals cap --inr 5000 --quote "…"`. The page shows the new cap at once.
2. After the deploy and the child's restart, the child re-drafts the treatment toward AI video for the scene-like gaps (`vw visuals treatment --file out/visual-treatment.json` replaces the draft on the page; the draft is not recorded, so nothing is undone), SK approves it on the page, and the stage continues: plan, check, propose, accept, references with the start and end keyframes, takes, one round of generation.

## 6. Tests, first

- `server/unit/test_visuals_pure.py`: `routes()` counts a lone video shot as two images, three consecutive video shots in one scene as four, and two video shots separated by a still as two each; the existing routes test updated.
- `server/unit/test_visuals_stage_pure.py`: `prepare_take` refuses without an end image with the message naming the command, and with the same reference as start and end; accepts with two approved references; `generate_image` accepts a keyframe with one candidate keyframe parent and still refuses a candidate sheet parent and a candidate parent on an isolated image; `budget()` plans images by the new count; `cap_of` on a session without a cap is 5,000, and the three existing assertions that read the ₹1,000 default move to ₹5,000.
- `plugin/tests/test_visuals_cli.py`: `prepare-take` without `--end` is refused locally and posts nothing; with `--end` the body carries both images.
- The prompt stays within 3,500 words; `v2.json` parses; `python -m py_compile` on every plugin file; the server files with the 3.10 interpreter.

## 7. Not covered

- `server/tests` (Docker; not on this Mac).
- Whether the generators honour the end image faithfully, and whether an end keyframe generated from the start keeps the people and the room identical: the first takes on VW-6 decide, and the review step watches for it.
- The join between two segments at assembly: a hard cut on a shared picture; if a model drifts from its end image the join shows. Watched on VW-6, logged in design/49.
- The visuals page under a real session, still untested since design/65.
- The prices behind the meter remain estimates until SK gives the figures.

## 8. Order

SK's approval → tests → the change → compile checks → commit and push → tell SK, deploy the server (0.23.0, the workers restart) → deploy the plugin (0.22.0), SK restarts the operator's Claude Code → design/35 row 58, design/49 entry → the child raises the cap (any time before), re-drafts the treatment, SK approves on the page → one round of generation.
