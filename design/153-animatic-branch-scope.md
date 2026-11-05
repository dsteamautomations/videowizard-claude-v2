# 153 — Where the animatic branch starts and ends (4 Nov 2026, draft for SK; rechecked twice, 5 Nov)

SK, 4 Nov: the new process branches off the current one at the references and builds on it. This note says, in design/152's words, which steps the branch touches and which it leaves alone, and fixes the terminology of SK's description. Nothing here is approved yet; it is the reading list for the requirements note.

Rechecked 5 Nov against `visuals_stage.py`, `visual_contract.py`, `v3.json` and `visuals.html`: three corrections from the 4 Nov draft, marked **(corrected)**.

## 1. The span

Everything is inside stage 10 `visuals`. Stages 0–9 (start … master) and 11–12 (assembly, delivery) are untouched: the gaps still arrive from `master record`, the recorded gaps still go to the editor's package (design/132).

| Level | Untouched | The branch | Untouched |
|---|---|---|---|
| Flowchart phases (`design/visuals-flowchart.md`) | 1 PREPARATION · 2 TREATMENT · 3 DETAILED PLAN · 4 PICTURE SEARCH | **5 REFERENCE SHEETS AND GOLDEN PICTURES** (gains the canvas, loses the golden picture) · **6 SHOT PICTURES** (the `video` route loses its start and end images, gains the animatic) · **7 VIDEOS (takes)** (the packet and the generator change) | 8 REVIEW AND RECORD |
| Procedure steps (`v3.json` → visuals `steps`) | 1–4 | **5** References made by the picture AI, reference sheets and golden pictures · **6** Shot pictures and videos | 7 Review and record · 8 Brand |
| Sections (part `later`) | 1–4 (parts `preparation` … `picture-search`) | **5** GENERATED REFERENCES, SHEETS AND GOLDEN PICTURES · **6** SHOT IMAGES AND VIDEO · **9** THE LATER STEPS, IN ORDER (the order changes) | 7 CHECKS AFTER A TAKE · 8 REVIEW OF A TAKE OR A SEQUENCE · 10 BRAND · 11 DRAWN SHOTS WITH HYPERFRAMES |
| Page rail (`visuals.html` → `STEPS`) | `treatment` · `plan` | **`references`** · **`pictures`** · **`takes`** | `record` |
| Treatment routes (`TREATMENT_ROUTES`) | `footage`, `still` | **`video`** only | `graphic_sequence`, `drawn` (HyperFrames, `vw motion`) stay exactly as they are |

So: from visuals step 5 to visuals step 6, on the `video` route only. Step 7 onward is the same.

## 2. The terminology, fixed

| SK said | The glossary word | Note |
|---|---|---|
| "reference images from the original video" | references of kind `frame` | source 1 |
| "Nano Banana images for items not on the clip" | references of kind `sheet` made by the picture AI; on a kept film a **set** (two to four pictures of a thing) | source 2 |
| "one character sheet per person" | a person's **set** (full length, working pose, the face) | source 3; "character sheet" is not a glossary word |
| "the environment for every scene or beat" | **(corrected)** a new reference: one picture per **scene** of the whole place as that scene shows it, with its landmarks. Proposed word: **canvas** (SK's own word; not in the glossary, no clash). | source 4. **Scene**, not beat: a beat is the script's numbering; the plan's unit of place and action is the scene (gap → scene → shot). The 4 Nov draft said "this is just the `place` element": wrong. `place` elements already exist and already get a set in the round, with `signs_of_use` per landmark (design/111 F18). A place set shows the place as a thing; the canvas shows the scene's stage, landmarks in position, where the people and objects will act. New reference kind, to be added to `REF_KINDS`. |
| "golden picture", "start frame" | **golden picture** (already retired on kept films, design/151: the ticked picture of the set) and the **start image** (kind `keyframe`); **(corrected)** the video route also has an **end image** (`keyframe` with `role: 'end'`, design/77 L38) | all three retired on the `video` route by this branch |
| "2D animated video drawn programmatically by Claude" | new word needed. Proposed: **animatic** (the film-industry word for a timed cartoon pre-visualisation; not in the glossary, no clash) | avoid "cartoon", "drawn" and "scene": `drawn` is a route and `scene` is also an SVG scene in `vw visuals draw`. Likely built on the drawn route's own renderer (SVG scenes, HyperFrames, Chromium): to be decided in the requirements note |
| "the text-based inputs" | the shot's **packet** (`vw visuals packet --shot`) | |
| "Google Omni 1.1" | the shot's **generator** (provider and model per shot) | **(corrected 5 Nov)** already today's generator: section 9 says "every take is Gemini Omni, 3 to 10 s". Nothing new on the generator; what is new is sending it a video as a reference |
| "AI videos and motion graphics by Claude" | routes `video` (today's takes) and `drawn` (HyperFrames) | `drawn` untouched; `video` is the route this branch changes |
| "download the videos" | assembly's editor's package and delivery | untouched |

## 3. The new order of the later steps (section 9), video route

1. References (step 5): `frame`, sets for objects, people and places as today, **and one canvas per scene**.
2. For each shot on the `video` route (step 6): bind references (the canvas among them) → the **animatic** (Claude, timed to the shot's seconds, drawn against the bound references) → the packet = animatic + bound references + the shot text → the take by the generator.
3. Checks after a take, review, record (steps 7–8, unchanged).

Older way (old-ways rule, design/35): start image (and end image) + the prose packet → the take. **Retired on the `video` route** once the animatic is live; **kept** on `still` (a `keyframe` there is the shot's own picture, "picture" in the operator's words; `footage` makes no picture) and on films already past step 5 when the branch goes live.

## Open

- **Decided, SK 5 Nov: the canvas is one per scene.** The words **canvas** and **animatic** stand unless SK objects.
- Whether a shot that reuses a scene's canvas needs its own animatic or shares the scene's: decided at the requirements note.
- **(corrected, added)** The generator must accept a video as a reference, not only pictures. Untested; a test like design/128's G07-S4-SH1 comes before the requirements note.
