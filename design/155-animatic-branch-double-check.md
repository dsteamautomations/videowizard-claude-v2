# 155 — The animatic branch, double-checked phase by phase (5 Nov 2026, for SK's decision)

SK, 5 Nov: "Go through everything in a phased manner. Whatever decisions you made, split them into phases, question your decisions in each phase, check everything one level deep." This note does that. Every fact below was checked today against the code, our Omni fact sheet (`server/library/…/gemini-omni-1-1/FACT-SHEET.md`) or Google's Omni page (`aistudio.google.com/docs/omni`, read verbatim). Where a decision changed, it says so. It replaces sections 3, 8 and 9 of design/154 where they differ.

## The one fact that changes the design

Google's page, under Limitations, verbatim: "Video references support a maximum of 3 clips, up to 3 seconds each." Our fact sheet row 90 says the same. A ten-second cartoon cannot go in as a *reference*.

What the Gemini app did with SK's cartoon is the other path: **edit**. Verbatim: "Input videos for editing and extension must be 10 seconds or less when uploading", "Upload your videos using the Files API to edit them with Gemini Omni Flash", and the working edit prompts Google lists include "Make this video anime". SK's prompt ("use the attached video as a guide … do not copy the cartoon drawing style, make it look realistic") is an edit of the cartoon into realism. So the animatic is not a reference beside the pictures; **it is the input video, edited into the take**. Everything below follows from that.

Two more verbatim facts that bound the design:
- "Referencing or reasoning across multiple videos is not supported." So the thread's Part 2 method (the real Part 1 clip for the look plus a second cartoon for the timing) **is not available on the API**. One video per call.
- "Do not include control strings (such as `<FIRST_FRAME>`, `<LAST_FRAME>` …) in your text prompts. These tags are deprecated and unsupported in future models." Our house shape (design/84, `motion_text`) still sends them on every take today. That is a separate fix for the regular flow, not this branch.

## Phase 0 — the test (the gate)

| Decision | Checked | Stands? |
|---|---|---|
| Send the thread's Part 1 cartoon through our API path with the sets and a prompt | `video_providers.Provider.build` sends `input` = image items (base64) + one text item, `response_format` video. There is no video item and no Files API code (fact sheet row 68: upload, poll `PROCESSING` → `ACTIVE`, pass `{"type":"video","uri":…}`). | **Changed.** The test is a standalone script, not the server: upload the cartoon with the Files API, call interactions with `{"type":"video","uri"}` + the two set pictures + the text, once with the task left to the model, once with `generation_config.video_config.task: "edit"`. Like design/128's test. |
| What it must prove | (a) the call is accepted with a video plus images (the edit example on Google's page shows video + text only; the extension example shows video + image + text; **video + images on an edit is undocumented**); (b) the output keeps the cartoon's cuts and seconds; (c) the sets hold identity; (d) the cost (input video is 5,792 tokens a second: about ₹8 for ten seconds, on top of the take as today). | Stands, with (a) sharpened: if images are refused on an edit, identity must come from the text and the cartoon's colours, and the branch is weaker. |
| Deploy hold | A script on the VM with the key there touches nothing running. | Stands; no deploy. |

## Phase 1 — references (visuals step 5)

| Decision | Checked | Stands? |
|---|---|---|
| Drop the per-scene canvas (design/153) | Place elements already get a set in the round and carry `signs_of_use` per landmark (`visuals_stage.py` 967–983, design/111 F18). The thread used no canvas. | Stands. |
| The previous take as a look reference for the next clip of a long scene (thread §6) | Not supported: one video per call. Extension (`previous_interaction_id`) carries the generated clip into a 3–10 s continuation, but then the second cartoon cannot ride along. | **Changed.** A scene longer than ten seconds is cut into segments at a shot boundary, each with its own cartoon and its own take; continuity between segments is what it is today between shots: the sets, the light line, the person lines. The canvas is revisited only if the place drifts between segments in the test. |
| Golden picture, start image, end image retired on cartoon takes | `_picture_word`, the keyframe `role: 'end'`, `end_state_exact` on the shot. | Stands. Kept on `still` and on films past step 5. |

## Phase 2 — the plan and the director's brief (visuals step 3)

| Decision | Checked | Stands? |
|---|---|---|
| A new "director's brief" per scene | `Shot` already has `camera`, `camera_move`, `framing`, `focus`, `start_frame`, `end_frame`; `Scene` has `layout`, `landmarks`, `light`, `ambient`, `activity_level`. Several angles of one scene are already several shots, each with its own camera. | **Changed, smaller.** No new brief object. What is new: (1) a scene flag `one_take: true`, meaning its shots are the cuts of one cartoon and one take; (2) planning rules that ask for angles and cutaways, filed by category (documentary: one or two angles and a hold by default; advertisement and drama: the thread's grammar, cutaways, reactions, point of view); (3) inside a `one_take` scene a shot may be shorter than 3 s (today `OMNI_ONLY` says "3–10 s; split the shot" and a shot under 4 s with no action becomes a moving still: both exceptions are needed, the sum of the scene's shots staying within 10 s). |
| Way A (cartoon per shot) versus way C (per shot plus the flag) | A one-shot scene is a `one_take` scene with one shot. | **Merged.** There is one design: the unit of a cartoon and a take is a shot, or a `one_take` scene. "A then C" is not two builds. |
| Scene, not beat, as the unit (design/153) | Beats are the script's numbering; shots bind to them through `start_frame`/`end_frame`. | Stands. |

## Phase 3 — the cartoon (new, between steps 5 and 6)

| Decision | Checked | Stands? |
|---|---|---|
| Draw it with the HyperFrames machinery | `motion.py`: `render(folder, fps, out)` makes the mp4 in Chromium; `frames_png` pulls frames; `snapshot` crops at seconds; the helpers `vw-motion-shot`, `vw-motion-rules`, `vw-motion-check` exist in `plugin/agents/`. | Stands for the loop. |
| "The loop already exists" | The loop, yes. The drawing of people, no: HyperFrames has drawn diagrams; the thread needed a 330-line figure library and five rounds for one couple. | Stands as corrected in design/154 §9: a **figure library built once** (named poses blended by a ramp, head `turn`/`tilt`/`brow`/`narrow`/`mouth`, draw order, the mirror trap, common objects) is a build item of its own, 3–5 days. |
| 15 fps, 1280×720 is enough | The thread's guides were that and the model followed them. Our render runs at the film's fps; a cartoon at the film's fps costs nothing more. | Stands; render at the film's fps, no special case. |
| Duration | The cartoon is exactly the take's seconds, never longer (thread F3) and never over 10 s (the edit limit). | Stands; the server refuses a longer cartoon. |

## Phase 4 — the check and the operator's approval

| Decision | Checked | Stands? |
|---|---|---|
| A check helper reads the contact sheet against the shot lines; drift → rewrite the take text; blunder → redo, at most two rounds | `vw-motion-check` with `rules.md` and `verdict` rounds is exactly this shape; `frames_png` gives the sheet. | Stands. New rules: the empty-hand rule, the natural-behaviour rule (handedness, drinking, cultural habit), the order of events, every subject present, nothing in frame that the plan does not name. |
| The operator approves the cartoon every time | Today the operator approves every start image (paid). The cartoon takes that slot and is free to redo. | Stands: approval every time, after the check; on the Takes step. |
| Who writes the take text | The check helper rewrites the motion text from what the cartoon shows (SK's rule: the prompt follows the cartoon unless the cartoon blundered). | Stands. The operator sees the text beside the cartoon. |

## Phase 5 — the take (visuals step 6)

| Decision | Checked | Stands? |
|---|---|---|
| Add a video input to the take call | `Provider.build` gains the Files API upload and the video item first (media before text, fact sheet row 57), then the set pictures, then the text; `task: edit` as the fallback when the model infers wrongly. | Stands; new code, about a day. |
| Drop the single-shot sentence; add the guide-only sentence | `motion_text` builds the sentence; verbatim from Google: by default Omni "will try to create a video with a few different shots"; the single-shot phrases are the ones we send. | Stands; one branch in `motion_text` on `one_take`. The guide-only sentence is Google's own advice for edits: simple prompt, "keep everything else the same" for what must not change (the cuts, the timing, the positions), one line on what changes (realistic, these people, this place). |
| Drop the `<FIRST_FRAME>` tags on cartoon takes | Deprecated by Google; no first frame exists on a cartoon take. | Stands, and the regular flow should drop them too (separate note). |
| The drift check | `image_check.take_drift`: a must when the camera is locked off. | Stands: off on a `one_take` take (the cartoon decides the camera); the Gemini read of the take stays. |
| Audio | Omni makes an audio track by default; our takes say "No dialogue. No music." | Stands for documentaries (the narration is ours). For SK's later dialogue phase: verbatim, dialogue is generated only when extending a model-generated clip in multi-turn, never by editing an uploaded video. So **dialogue will not come from the cartoon edit itself**; it needs a second turn. Noted for that phase, not this one. |

## Phase 6 — assembly and the page

| Decision | Checked | Stands? |
|---|---|---|
| One take serving several shots | `stage3/assembly.py`: "one fill per gap shot", with a per-shot `offset_frames` chosen by the operator. | **Changed, smaller.** A `one_take` scene's job is recorded on every shot of the scene with its default offset = the shot's start inside the cartoon. Assembly stays per shot and needs no new concept; the page's `x.takes` per shot stays. About a day. |
| The cartoon on the Takes step | `visuals.html` lists takes per shot; a cartoon card with its contact sheet, its video and the take text, approve or redo. | Stands; 1–2 days. |

## Phase 7 — time and rollout

| Decision | Checked | Stands? |
|---|---|---|
| 10–30 minutes per scene before the take | A guess. The thread's rounds were hand-steered. | Stands as a number to measure in the test, not to promise. |
| Build estimate | Test 1 day; provider + Files API 1; plan flag and rules 1–2; figure library 3–5; drawing rules and helper 2; check rules 1; assembly and page 2–3. | **12–15 days** after the test passes, one builder, with the old way kept beside it and the usual tests. |
| Old ways | Start image, end image, golden picture, locked camera, one take per shot: kept as the default for every scene without `one_take`, and on `still`. Retired only on `one_take` takes. | Stands. |

## What could still sink it (in order)

1. Images refused beside the video on an edit call: identity then rests on the text. The test answers this first.
2. The edit does not keep the cartoon's cuts and seconds: the page says "the model applies the edit while preserving the parts of the video you want to keep", not that timing is preserved. The test answers this second.
3. The figure library is harder than estimated: the first cartoons of people look wrong in ways the model copies. Mitigation: the operator's approval before any paid take, and the thread's rules in the drawing instructions from day one.
4. Documentaries: a cut-heavy clip between real footage looks wrong. Mitigation: the documentary default of one or two angles.

## Not covered

- The deprecated frame tags in today's house shape: a separate requirements note.
- The dialogue phase: only the one fact above.
- `scripts/` and `server/tests` not touched; nothing built.
