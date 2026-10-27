> Saved by the builder on 27 Oct 2026 as design/112 (110 and 111 were taken by batch 1 and batch 2 of Revathi's fixes). SK's answer the same day: build F11's edit route now with the rectangle region and the composite-back, which is S2's method; hold F19's drawing part until the drawn route (E1–E5) exists, so its labels and view are inputs to that route from the start. The builder's requirements for this note (what exists, questions) are kept at the end, under 'Builder's reading'.

# design/112 — Steady takes, short gaps as moving stills, and the drawn-graphic route

Status: proposed by Revathi, 27 Oct 2026, from operating VW-7's Takes step. Checked against `main` at server 0.53.0. For SK's approval. Save under the next free design number; as of 27 Oct 05:40 UTC the repo has 107, 108 and 109, so 110.

**Every change in this note is required.** None is optional or a nice-to-have. The builder implements all of them, or raises a conflict with Revathi before leaving any out. Every rule is for any film; VW-7 appears only as evidence.

## 1. Takes glide: the whole frame shifts between the start and the end

**What happened.** On VW-7, many takes made from a start and end pair show the whole picture drifting, or one frame gliding over the other, instead of a still camera with people moving in it.

**Why.** The end image is a GPT Image edit of the start, and an edit redraws the whole picture, so framing, scale and background shift slightly even when only the action should change. The video model is told to go from Image 1 to Image 2, so it animates that shift as a camera slide or a morph. The rule "the camera does not move between the two images" exists only as words in the end instruction (`visuals_stage`, end instruction). Nothing measures it: the pair check (design/91 N1) and the take check (N3) do not test framing. And `prepare_take` refuses a take without an end image (design/66: "Every take has a start and an end image"), so every shot goes through a pair.

**The image library already says what to do**, in the snapshot the server serves, but the server does not act on it:
- GPT Image sheet A5 and B5: a mask on Image 1 limits the edit; "if a region must be pixel-identical, composite the approved edit back onto the original"; repeated edits drift.
- Video-frame playbook, first-last-frame: "same aspect, same light, same traits; only the move's change differs" (a must line).
- Video-clip playbook: clip-from-frame, one approved frame and one move, is the default.
- Omni sheet B9: Google says first-and-last-frame is for "complex camera orbits, zoom transitions, or seamless looping clips".

| # | Required fix | Where |
|---|---|---|
| S1 | **Start image alone by default.** A take is made from the start image and the motion text (clip-from-frame). An end image is used only when the plan says the shot's final state must be exact, and the plan names which shots those are. `prepare_take` accepts a take without an end image. | `visuals_stage.prepare_take`, plan schema (`end_state_exact`), prompt, `vw.py` |
| S2 | **When an end image is used, only the action area changes.** The end is generated with a mask on the start covering the area the change list names (design/91 N1). After generation, that area is composited back onto the start, so every other pixel is identical. | `visuals_stage.generate_image` (mask from the change list), `visual_workers` (composite on retain) |
| S3 | **The pair's alignment is measured in code, before the operator sees it.** The end is registered against the start on the regions the change list leaves unchanged (phase correlation or feature matching, no model call). A shift, scale or rotation above about 1 % of the frame refuses the pair, naming the measured shift. | `image_check` (pair, code only) |
| S4 | **The camera is always stated.** `motion_text` appends the camera from the plan: "locked-off camera on a tripod" unless the shot names a camera move. | `video_providers.motion_text`, plan schema (`camera_move`) |
| S5 | **Every retained take is measured for drift in code.** Frame-to-frame whole-image translation and scale across the take. A take planned with a still camera that drifts or zooms fails a `must` line, with the measured drift on its card. | `visual_workers` (on retain), `image_check` (take), page |
| S6 | **The library wins unless the note says why not.** Where a verified line of the image library's fact sheets or playbooks and the server's behaviour differ, the server follows the library, or the design note records the reason. The builder lists every such conflict found while building this note. | design note, `library.py` (nothing automatic) |

## 2. Short gaps are moving stills first

**What exists.** Every still gets a 5 % push or pan at assembly (design/89 B2, `stage2/render.py` zoompan); a moving still runs at most 4 s, a frozen one 3 s; a graphic moves only by pushing in, so its text never slides. Nothing was removed.

**What is missing.** A preference. For a 2–4 s gap where one moving still would do, the planner may still choose AI video or a graphic build.

| # | Required fix | Where |
|---|---|---|
| K1 | For a shot under 4 s whose narration needs no visible action, the plan's **default route is a still with movement** (a footage frame or an AI still with a push or pan). AI video or a graphic build for such a shot needs a reason in the shot's purpose; the check warns without one. | prompt, `validate_plan` |
| K2 | A still that carries text (a label, a title) moves only by `push_in`, never a pan, and the push keeps every label inside the safe area; the check refuses otherwise. | `validate_plan`, `stage2/render.py` |
| K3 | The treatment's route counts show "still (moving)" and "still (frozen)" apart. | `visual_contract.routes`, treatment view |
| K4 | **No crop or pan cuts into a still's text.** Today a photographic still fills the frame by cropping up to 1.35× (`stage2/render.py`, `FILL_MAX_ZOOM`, design/91 N15) and may pan across the margin the zoom leaves, so text near an edge can be cut off. A still that contains text (a label, a title, a caption) is placed with no crop and no pan: it is contained with its full picture, and its only movement is `push_in` within the safe area. The plan check refuses a crop or pan on such a still, and the renderer refuses it as a backstop. | `stage2/render.py` (`still`, `motion_vf`), `validate_plan` |

## 3. The drawn-graphic route is built

**What exists.** SK decided on 23 Oct (design/89, decisions table) that the drawn graphic is the default route for technical diagrams, built after D, with Noto Sans in the repo. D is built. The plan check already says "or a drawn animation (next release)". There is no renderer, no route, no font file and no page support: `drawn.py` and the Noto font never appear in the git history. E was never started, and nothing overwrote it.

| # | Required fix | Where |
|---|---|---|
| E1–E4 | Build design/89 E1–E4 as written and as SK decided: the planner writes a declarative scene (canvas, the style sheet, shapes in real units with one scale, a timeline of actions keyed to a time or a narration word); the server validates and renders it with Pillow and ffmpeg at the film's size and frame rate; no model-written code runs on the server; Noto Sans Regular and Bold (OFL) in the repo, a client's brand font beside it when supplied; the result is reviewed and approved like a take, on the Takes step; re-renders are free and not counted against the cap; the drawn graphic is the default route for technical diagrams, charts, maps and timelines; the AI-image graphic sequence stays available but is no longer the default for technical diagrams. | `drawn.py` (new), plan schema, `visuals_stage`, `vw.py`, page, `server/fonts/` |
| E5 | The sourced drawing spec (design/89 D, design/106 D1–D6) is the input of every drawn graphic: the scene's units come from the spec, and a drawn graphic without an approved spec is refused. | `visuals_stage`, `validate_plan` |

## Order

1. S1, S4, S3 (start-only takes, the camera stated, the pair measured), then S2 and S5.
2. K1–K3.
3. E1–E5.
4. S6 is checked throughout and reported with the diff.

## Tests first

- S1: a take with a start image alone is accepted when the shot's `end_state_exact` is false, refused when it is true without an end.
- S2: the end request carries a mask from the change list; the retained end differs from the start only inside the mask.
- S3: a pair whose background is shifted by 2 % is refused with the measured shift; an aligned pair passes; the check runs with no model call.
- S4: `motion_text` carries "locked-off camera" for a shot with no camera move and the named move otherwise.
- S5: a synthetic take that drifts 3 % fails the drift line with the figure; a steady one passes.
- K1: a 3 s shot with no action planned as AI video warns; as a moving still it passes. K2: a still with a label and `pan_left` is refused. K4: a still with text wider than 16:9 is contained with no crop; the renderer refuses a crop on it. K3: the treatment counts moving and frozen stills apart.
- E1–E5: a scene with any executable key is refused; a valid scene renders exactly the shot's frames at the film's size; an action keyed to a word starts on that word's frame; a drawn graphic without an approved spec is refused; the rendered text uses the repo font.

## Not covered

- server/tests (Docker).
- How well the mask holds on GPT Image (the sheet says the mask is guidance); S2's composite is the backstop.
- The 1 % and 3 % thresholds are starting values; the first film tunes them.

---

## Builder's reading (27 Oct 2026, against main at server 0.59.0)

**What exists.**
- S1: `prepare_take` refuses a take without an end image (design/66 C2); the video-clip playbook's clip-from-frame form exists in the library, unused by the server. No `end_state_exact` on a shot.
- S2: no mask is sent with an edit; the worker stores the model's picture as it comes. The GPT Image fact sheet (A5, B5) says a mask is guidance and the composite is the guarantee. Batch 2's F11 (design/111, SK's answer) builds exactly this: the writer's rectangle region, the mask, the composite-back and the outside-unchanged measurement; S2 adds only "the region comes from the change list by default".
- S3: the pair check (design/91 N1) asks Gemini for differences; nothing measures alignment in code. The server has Pillow only: no numpy, no OpenCV. Phase correlation needs numpy (a new line in requirements.txt, installed by the deploy script) or a coarse Pillow-only method (block matching on a downscaled grey copy).
- S4: `Shot.camera` is free text; `motion_text` says nothing about the camera. No `camera_move` field.
- S5: `process_take` keeps ffprobe evidence (duration, timing); no frame-to-frame drift measurement; the same numpy question as S3.
- S6: the library snapshot `vwlib-2026-10-21` is served to the writer; the server follows parts of it in code (design/68, 71, 86); no list of conflicts exists.
- K1–K4: stills get a 5 % push or pan (`stage2/render.py` `motion_vf`), photographic stills fill by cropping up to 1.35× (`FILL_MAX_ZOOM`, design/91 N15), a graphic moves by `push_in` only; a still with text can be panned and cropped; no route preference for short gaps; `routes()` counts stills as one kind.
- E1–E5: nothing. No `drawn.py`, no fonts folder, no scene schema; design/89 E1–E4 and SK's decision of 23 Oct stand as the specification; design/89 D (the sourced spec) is built and design/106 D1–D6 refined it.

**Questions for SK.**
1. **Sequence against batch 2.** F19's labels and view are inputs to the drawn route (E), so F19's drawing part cannot ship before E. Recommendation: batch 2 (design/111) ships F7–F18, F21 and F11 with S2's method, plus F19's plan-check and count parts; design/112 is the next set (S, K, E) with F19's labels and view inside E5; two deploys, batch 2 first.
2. **numpy on the server** for S3 and S5 (and faster composite-back). Recommendation: add `numpy` to requirements.txt (the deploy script installs it); the Pillow-only alternative is slow and coarse.
3. **S1's default.** Every shot without `end_state_exact: true` becomes a start-only take; VW-7's revised plan must say which shots need an exact end. Recommendation: as written, with the plan check warning when a shot with a planned visible result (a change list) is start-only, so the planner decides on purpose.
4. **E's size.** The drawn route (schema, validator, renderer, Takes-step review, fonts, page) is the largest single item in all the sets; built in its own sub-set with its own tests and a sample render reviewed by SK before the route becomes the default. Recommendation: yes, after S and K.

**Not covered until built:** the thresholds (1 % and 3 %) are starting values; how well GPT Image honours a mask is measured by the composite, never assumed.

**SK's answers (27 Oct 2026).** 1. Batch 2 first, then this note; done (0.60.0). 2. numpy is added to the server's requirements. 3. S1 as written, with the plan-check warning on a shot that has a change list and no exact end. 4. E is its own sub-set after S and K, with one sample render reviewed by SK before the drawn route becomes the default. Build order: S1, S4, S3, then S2 and S5, then K1–K4, then E1–E5.

## As built: S1, S4, S3 (27 Oct)

- S1: `Shot.end_state_exact` (default false). `prepare_take` accepts a take with the start image alone; it refuses a start-only take only when the shot says its final state must be exact. The pair-only steps (the aspect check, the Gemini difference list, the alignment) run when an end is sent. The plan check warns on a video shot with a change list and no exact end ("its take is made from the start image alone … set end_state_exact true if the final state must be exact"), so the planner chooses on purpose (SK's answer 3). The picture estimate counts a start per video shot, an end only for an exact shot, and no new start for a start-only shot right after an exact end. The plugin's `prepare-take` needs `--start`; `--end` is optional and sent only when given. The procedure says the same.
- S4: `Shot.camera_move` (free words, empty is locked off). The take record carries it, and the motion text always ends the continuity part with "Camera: locked off on a tripod; the frame does not move, drift, zoom or slide." or "Camera: <the move>; nothing else about the frame changes."; the take check reads it as context and, for a locked-off camera, asks the must line "camera steady". Takes prepared before this release carry no camera key and read as before.
- S3: `image_check.pair_alignment` (numpy, now in requirements.txt): the end registered against the start on grey 256×144 copies, translation by phase correlation, scale by a search over 0.95–1.05 in steps of 0.005 (the best peak kept), no rotation, no model call. A shift above 1 % of the frame width or a scale off by more than 1 % refuses the pair at `prepare_take` with the figure ("shift 2.0 % of the frame (+5, +0 px at 256 wide), scale 1.000") and the two ways out (an edit inside a region, or start-only); the measurement is kept on the preparation as `alignment`. A pair the store cannot read is not refused; the reply says the alignment was not measured.
- Tests: `test_design112_s1s3s4_pure.py` (6: the warning and the estimate, a start-only take accepted and an exact shot refused without its end, the camera line and the take line, synthetic pairs shifted 2 % and zoomed 3 % refused and an aligned one with a changed action area passed, the refusal and the record through `prepare_take`). Three older tests updated for the new default (the estimate, the budget, the plugin's refusal). Server unit suite 573; plugin 310 plus the 3 known Windows-only; plugin parses under the 3.9 grammar.
- Not covered: rotation (an edit rarely rotates; S5's drift measure will show if it matters); the 1 % thresholds are starting values; the action area is not masked out of the correlation (the background dominates; a very large change may lower the peak but does not shift it).

## As built: S2, S5 (27 Oct)

- S2: every end image is an edit inside one region of its start. `generate_image` refuses an end keyframe without a region, naming the shot's change list to cover and the two ways (a region a third at most, or a start-only take when several places or the framing change); a start written with an end prompt and no `--end-region` is warned that the server will refuse to make that end. F11's mask, composite-back and outside-unchanged measurement are what make the region hold; nothing new there. The region still comes from the writer as a rectangle (SK's answer 3 to design/111), since the change list is words, not pixels.
- S5: `image_check.take_drift` reads up to twelve small grey frames of the retained take with ffmpeg (two a second) and registers each against the first with S3's method (phase correlation and the scale search, shared as `_match`); the worst shift and zoom are reported. For a locked-off camera (the take record's `camera_move` empty) it is the must line "camera drift", failing over 2 % (DRIFT_MAX, a starting value) with the figure on the take's card; for a planned camera move, or a take prepared before design/112, it is measured and reported, not judged. `run_take_check` measures first, in code, then asks Gemini; the drift line joins the record even when Gemini cannot run, and a failed measurement (no ffmpeg, a one-frame clip) never holds the take back (`drift_error` on the record).
- Tests: `test_design112_s2s5_pure.py` (4: the refusal and the warning; synthetic frame runs that drift 3 %, zoom 4 %, hold steady with a moving subject, and a planned move; the frames read from a real mp4 encoded with ffmpeg, skipped where ffmpeg is absent; the drift line on the take record without a Gemini key). Thirteen older fixtures that made an end without a region now give one. Server unit suite 577; plugin 310 plus the 3 known Windows-only.
- Not covered: rotation; a take whose subject fills most of the frame (the registration follows the subject, not the background); the 2 % threshold is tuned on VW-7's first takes.

## S6: the library against the server, conflicts found while building the S set (27 Oct)

| Library line (vwlib-2026-10-21) | Server before | Now |
|---|---|---|
| Video-clip playbook: clip-from-frame (one approved frame and one move) is the default | every take needed a start and an end (design/66 C2) | S1: start alone by default; an end only for `end_state_exact` |
| Omni sheet B9: first-and-last-frame is for orbits, zoom transitions and loops | every take used it | S1, same |
| GPT Image sheet A5, B5: a mask limits the edit; composite the approved edit back where pixels must be identical; repeated edits drift | ends were whole-frame edits, nothing composited | F11 (design/111) built the mask and the composite-back; S2 makes the region required on every end |
| Video-frame playbook, first-last-frame: "same aspect, same light, same traits; only the move's change differs" (a must) | the aspect was checked; nothing measured the framing | S3: shift and scale measured in code before the operator sees the pair |
| Omni house shape (B1, B2, B7, B9): the frame tags, the motion brief, the continuity line, one unbroken shot, no dialogue or music, the roles of the pictures, the length last | followed; no camera sentence anywhere in the shape | S4 adds "Camera: …" after the continuity part; the house shape's order is kept. The library has no line on the camera: a line for the next snapshot, not a conflict |
| GPT Image sheet: a mask is guidance, not a guarantee | — | unchanged: the composite is the guarantee; the outside-unchanged figure is on the edit record |

No other line of the served snapshot was found to differ from the server's behaviour in the take path. Versions for the S-set deploy: server 0.61.0, plugin 0.53.0 (`prepare-take` takes `--start` alone); numpy joins the server's requirements (the deploy script installs it).

## As built: K1–K4 (27 Oct)

- K1: a video shot under 4 s (STILL_MOVING_MAX_S) with no acting subject that has beats is warned `short_route` unless its purpose gives the reason ("because …", "since", "so that", "needs the motion"): the default for such a shot is a moving still. A graphic build is never under 4 s (a state holds 3 s at least), so the rule is about AI video.
- K2: `Shot.carries_text` (a label, a title, a caption on the picture); the plan check refuses a pan on it (push_in or none only), as it already did for every graphic.
- K3: `routes()` counts `still_moving` and `still_frozen` beside `still`; the page's per-gap split shows "still (moving)" and "still (frozen)" rows.
- K4: the handover marks a still `text` when the plan says `carries_text`, the shot is a graphic, or the approved picture's answer carries exact text; the renderer contains such a still whole (bars rather than a crop, like a graphic) and refuses a pan on it as a backstop. The 5 % push stays within the picture's own centre, so words inside the safe area stay in frame.
- Tests: `test_design112_k_pure.py` (4, the renderer part skipped where ffmpeg is absent). Two older assertions updated (the handover's still media gains `text`; the split row is "still (moving)"). Server unit suite 581; plugin 310 plus the 3 known Windows-only.
- Not covered: the safe area itself is not measured on the picture (design/96's label-size line reads it on the check); the K1 reason words are a short list.
