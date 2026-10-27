# design/109: code review of 27 Oct 2026, the fixes

SK asked for one dedicated review, module by module, of everything since 8b7c611 (design/101-108 and the defect fixes). Five reviews ran, every
finding was checked against the code, and SK chose two groups of fixes (27 Oct): group A, the pictures and takes path, before VW-7 regenerates its
pictures; group B, the delivery path, before anyone imports an edit bundle. The findings as reported, then what was built.

## Module 1: delivery and timeline (server/app/stage3/delivery.py, timeline.py)

Server unit suite: 482 passed. Six findings, most serious first. All six are in the FCPXML/EDL bundle of design/107 slice 1; none touches the pictures, voice or assembly stages.

| # | Severity | Where | What is wrong | Fix |
|---|---|---|---|---|
| 1 | High | delivery.py:223-226, 402-403 | Fill shots (AI takes, stills, supplied files) are rendered by assembly as `normalised/{shot_id}.mp4`, but delivery decides "AI or camera" by the fill's *raw* file name (`DG1-asset.png`). So the rendered fill is filed under `Media/Camera/Stabilised/` and the timeline points at `Media/AI/DG1-asset.png`, which is not in the bundle. Resolve opens every fill shot as offline media. Only generated takes named `{shot_id}.mp4` line up by chance. The slice-1 test encodes the wrong expectation. | Use `{shot_id}.mp4` in both places (the file that exists). Four lines plus the test. |
| 2 | High | delivery.py:391, timeline.py:89 | On a stabilised cut the copy's source in-point is 0 but the nat-sound intervals stay in the original clip's frames, so the nat sound lands seconds outside the cut and reads past the end of the copy. | Subtract the original in-point when the cut is stabilised (one line), or put the nat sound on the original file. |
| 3 | Medium | delivery.py:391-394, 252-256 | A stabilised cut carries no clip id, so Relink-list.csv omits a camera file used only through its stabilised copy, and the per-clip cut counts are low. The file is still shipped under Media/Camera. | Keep `clip_id` on the stabilised row. One field. |
| 4 | Medium | timeline.py:155-160 | EDL timecode at 29.97 fps is built from real seconds; NDF timecode counts frames at 30. Frame 1800 prints 00:01:00:01, should be 00:01:00:00; by one hour the drift is 3.5 s. 25/50/60 fps are exact. | `divmod(frames, round(fps))`. One line. |
| 5 | Low | timeline.py:75 | The declared length of each media file is the first cut's out-point, not the file's length. Resolve tolerates it; Final Cut rejects a later, deeper cut from the same file. | Take the real length from the media summary. |
| 6 | Low | timeline.py:91, 95 | `role` is written on `asset-clip`; the 1.9 DTD puts `audioRole` there. Resolve ignores it; a strict importer would refuse. | Rename the attribute. |

Checked and fine: element order inside asset-clip, gap markers, format ids and frame duration at 29.97, percent-encoded file URLs and `with_base` on Windows and Mac paths, read-back/differences round trip, camera copies, verification_missing, OPEN-EDIT text, AI-shots on a run with no visuals.

Recommendation: fix 1-4 together as one small commit with tests (they are all in the same two functions); 5 and 6 with them if you want the bundle strict, otherwise park. This is already live in 0.57.0; nobody has imported a bundle yet, so nothing has been handed out wrong.

## Module 2: visuals stage (server/app/visuals_stage.py, image_check.py)

Four findings, all in the design/106 role and drawing-spec paths. Old sessions do not crash on any new field (every new read is guarded; the reviewer and I checked each).

| # | Severity | Where | What is wrong | Fix |
|---|---|---|---|---|
| 1 | High | image_check.py:241 (fix_body), visuals_stage.py:1213 | A fix of a start image carries no `role`, so the server derives "end" from its parent being a keyframe. The fixed start is stored as an END: the Takes card shows it as the end and hides the real end, and approving it never queues the end picture (design/106 T1, T2 broken on every fix of a start). | `fix_body` copies the parent's `role` (and `pending_end`). Two fields. |
| 2 | Medium | visuals_stage.py:1210-1215 | `role: end` with no start parent is accepted and stored as an end made from nothing; the "Image 1" rule is skipped because there is no start. | One `need(...)`: an end must have a keyframe parent. |
| 3 | Medium | visuals_stage.py:1416-1420 (approve_specs) | "Approve all specs" approves a spec whose correction is still waiting for the assistant and throws the operator's correction words away (design/106 D4 says the next approval is of the revised spec). | `approve_specs` and `approve_spec` skip a shot with a pending correction until its digest changes, and say so. |
| 4 | Medium | visuals_stage.py:2441-2473 (status) | The chat path never sees a pending correction; only the page payload carries it. The assistant working through `vw visuals status` has no trigger to revise the spec ("one flow, two front ends"). | Add `spec_corrections` to the status answer and one line to the procedure. |

Minor, not bugs: every fix in a lit scene trips the light warning (the fix prompt never carries the light sentence); the role check runs after the keyframe gates, so a bad role gets the wrong message.

Recommendation: fix all four before VW-7 regenerates its pictures. 1 and 2 are exactly the start/end flow the rollback is meant to test; 3 and 4 are the drawing-spec approval Revathi will go through first.

## Module 3: plugin (plugin/scripts/vw.py, handoff.py, resolve_bridge.py, stages_av.py)

Plugin tests: 298 passed, 3 known Windows-only failures. Python 3.9: clean. Three real bugs, all in the design/107 edit-folder path.

| # | Severity | Where | What is wrong | Fix |
|---|---|---|---|---|
| 1 | High | vw.py:2092 (confirm), handoff.py:146-160 | `vw delivery download` rewrites the timeline file with the machine's absolute paths; `vw delivery confirm` then cross-checks that file byte-for-byte against the manifest and refuses with "run download again": a loop, every time. On Windows the cut paths are also joined wrongly (`C:\C:\...`). The CLI test passes only because it never runs the rewrite first. | Cross-check the portable copy of the timeline (or skip size and fingerprint for the timeline row) and read cut paths from the portable text. |
| 2 | High | timeline.py:185 (server), handoff.py:269-287 | Relink-list.csv writes 29.97 as `29.970`; the relink check compares it exactly with ffprobe's `30000/1001`, so every 23.976/29.97/59.94 clip (most phone and mirrorless footage) is reported "frame rate differs" and sent to by-hand. 24/25/30 are fine. | Compare rates rounded to three decimals. One line. |
| 3 | Medium | vw.py:2043-2048 | `check` and `download` demand free space for the whole bundle; after the first download the bundle occupies it, so a second `download` (which the hint itself recommends) is refused on a laptop with less than twice the bundle free. | Subtract what is already in `edit/`. |

Worth knowing, not fixing now: a storage 503 during download is not retried; a UNC path (`\nas\share`) loses its host in the file URL; `vw delivery open` imports into Resolve Studio before reserving, so a second run makes a duplicate timeline before the server's refusal; relink-check appends its section to the checklist on every run; a malformed timecode tag gives a traceback instead of a refusal.

## Module 4: visuals page and thumbnails (visuals.html, web.py, files.py)

| # | Severity | Where | What is wrong | Fix |
|---|---|---|---|---|
| 1 | High | visuals.html ~368 (`#ref-note`), ~283 (correction box), render() | The page redraws the step every 15 s while anything generates. The new note textarea and the spec-correction textarea are rebuilt from server data, so anything typed for longer than the poll is wiped before Save or Send is clicked. The same release deliberately preserved the pass-2 words and the keywords, not these two. | Carry both values across the redraw the same way the keywords are (two lines). |
| 2 | Medium | web.py:269-280 (thumb_bytes) | A corrupt or half-written picture makes Pillow raise; the thumb route answers a bare 500 with no cache header, re-hit on every redraw. The old file route would have served the bytes. | `except Exception`: fall back to the signed redirect. One line. |
| 3 | Medium | web.py:286 (thumb_response) | A key with `..` segments passes the "starts with the run id" check, so a signed-in owner of one run can read any picture in the bucket and now also write a thumbnail into another run's folder. Needs a hand-made request (browsers collapse `..`); the read half is pre-existing, the write is new. | Refuse keys containing `..` or `/./`. One line. |
| 4 | Low | visuals.html ~162, ~742 | The "confirm picks" flag is only cleared by Back or Finish, so after leaving and returning to the step a later round shows Finish before Done. | Clear it in `go()`. |
| 5 | Design gap | visuals.html ~655 (renderTakes) | With two start candidates (design/86 K4) the Takes card keeps one picture per role, so the second candidate the operator should choose between is folded under "earlier pictures". Matches design/106 T1's wording; not a defect. | Decide later. |

Cosmetic: thumbnails of transparent cut-outs get a black background; the viewer shows the real file.

## Module 5: plan contract and checks (visual_contract.py, image_check.py, video_providers.py, camera_move)

Digests verified unchanged for old plans under old and new code (the reviewer ran both versions side by side), so no ready take goes stale from these releases.

| # | Severity | Where | What is wrong | Fix |
|---|---|---|---|---|
| 1 | High | visuals_stage.py:1488-1499 (camera_move) | The camera-move check matches "camera" followed within 40 characters by move/pan/track whoever the mover is: "Same camera as Image 1, the worker has moved the brick" is refused as a camera move. The end-image instruction itself tells the assistant to write "the same framing, camera, light", so natural end prompts get hard-refused (design/106 T6 claims the opposite). | Add "same", "unchanged", "as Image 1" to the negations and require the move word to be about the camera (the second alternative already covers "push in", "dolly", "pan left"). Small regex change plus three tests. |
| 2 | Medium | image_check.py:38,59; video_providers.py:25 | design/101 allows the ambient line `still: nothing else moves`. With that value the motion prompt says "the surroundings stay alive: still: nothing else moves" and the take check adds a MUST line "surroundings move", so every correctly still take fails a must line. | One `startswith('still')` guard in both places. |
| 3 | Intended | visual_contract.py:481 | A stored plan with an `unknown` dimension is refused on resubmission until `tried` is filled (design/106 D6). Noted in design/106 for VW-7 and VW-9; the plan revision after the rollback fills it. | None. |

Minor: an unsized shot is skipped by the size-rhythm rules, so "three in a row" can read across it; `Element.size` gets no source check; `run_check` reads the picture file twice.

## Summary and recommendation

Twenty verified findings across five modules; nothing is fixed yet. In two groups:

**A. Fix before VW-7 regenerates (the pictures and takes path, 8 small changes, one commit, server only):**
visuals stage 1-4 (fix role, end-without-start, approve-all with a pending correction, corrections in chat status), checks 1-2 (camera-move false positives, still ambient line), page 1-2 (typed note wiped by the redraw, thumb 500 on a bad picture). These are exactly the flows the rollback is meant to exercise; without them Revathi hits them in the first hour.

**B. Fix before anyone imports an edit bundle (delivery path, 7 changes, one server commit and one plugin commit):**
delivery 1-4 (fill files misfiled and offline, nat sound on stabilised cuts, relink list missing stabilised originals, EDL timecode at 29.97), plugin 1-3 (confirm loop after download, 29.97 relink mismatch, disk-space check on the second download). Plus page 3 (the `..` key guard) with the server commit.

Parked unless you say otherwise: delivery 5-6, page 4-5, the plugin minors, the checks minors.


## As built, group A (server 0.58.0)

- visuals 1: `image_check.fix_body` copies the parent's `role` and passes its pending end prompt and answer, so a fix of a start is a start with the same end to make.
- visuals 2: `generate_image` refuses an end image without a keyframe parent.
- visuals 3: `correct_spec` records the spec digest it was made on; `approve_spec` refuses, and `approve_specs` skips (and names under `waiting`), a shot whose correction is pending on the current digest; `waiting` shows no spec item for it. An old correction without a digest counts as pending.
- visuals 4: `status` carries `spec_corrections` (shot to words); the procedure says where to look and that it is folded in with `planning revise`.
- checks 1: `CAMERA_MOVE` matches only `camera` followed by its own move verb (with adverbs or auxiliaries between), or an explicit move phrase; nothing else moving near the word.
- checks 2: `image_check.ambient_moves` returns no line for `still: …`; neither the motion text nor the take check asks for movement then.
- page 1: the note and spec-correction textareas carry class `keep`; `render()` saves their values before the redraw and puts them back.
- page 2: `thumb_response` falls back to the signed redirect when Pillow cannot read the picture.
- Tests: `server/unit/test_review_a_pure.py` (8), and the design/106 D4 test now expects the refusal. Server unit suite: 490 passed.
- Not covered: the page change is checked as text, not in a browser; the camera regex is tested on the eleven sentences in the test, not on a corpus of real prompts.

## As built, group B (server 0.58.0, plugin 0.50.1)

- delivery 1: `delivery.fill_names` gives the file assembly rendered for each fill (`{shot}.mp4`); the bundle files it under Media/AI and `resolve_events` points the timeline at it. The slice-1 test now expects `Media/AI/DG1.mp4`.
- delivery 2 and 3: a stabilised cut's row keeps `clip_id` (so Relink-list.csv and the cut counts see it) and carries `a2_file`, `a2_source_fps`, `a2_source_in_frame`; `timeline.fcpxml` puts the nat sound on the original file, at the cut's place, in the original's frames.
- delivery 4: `timeline.tc` counts frames at the nominal rate (`divmod` by round(fps)), so 29.97 NDF timecode is right.
- page 3: `web.own_key` (the run prefix, no `.`/`..`/empty segment, no backslash) guards the thumb route and the file and audio routes.
- plugin 1: `handoff.cross_check` checks the portable timeline when it exists and reads the cuts from it, so `vw delivery confirm` passes after `download` rewrote the paths; a changed timeline is still caught.
- plugin 2: `handoff.same_rate` compares frame rates to three decimals (29.970 in the CSV against 30000/1001 from ffprobe) in the relink check's match and by-hand lines.
- plugin 3: `handoff.needed_bytes` subtracts what the edit folder already holds; `vw delivery check` and `download` use it.
- delivery 5: `delivery.clip_frames` reads each camera file's real length from the media summary; `resolve_events` sets `source_frames` on every row (a fill's and a stabilised copy's length is the cut's) and `a2_source_frames` for the original behind a stabilised cut, so every asset declares its real duration.
- delivery 6: the nat-sound and voiceover clips carry `audioRole`, the 1.9 DTD's attribute, instead of `role`.
- plugin minor: `_fetch_to` treats a storage 5xx as a transport error, retried with the usual waits; a 4xx still stops at once.
- Tests: `server/unit/test_review_b_pure.py` (5), `plugin/tests/test_review_b.py` (6). Server unit suite: 495 passed. Plugin: 304 passed, the 3 known Windows-only failures (test_intake x2, test_start_defect_paths). Plugin parsed as Python 3.9.
- Not covered: no bundle was imported into Resolve after the change (Revathi's by-hand check stands); the 29.97 EDL is checked against computed timecodes, not against Resolve's reading. Parked: page 4-5, the other plugin minors (UNC host, Studio import before reserve, duplicate relink section, malformed timecode tag), the checks minors.

## As built, the parked sets 1-4 (SK, 27 Oct)

- page 4: `go()` clears the Done/Finish flag on every step change.
- page 5: the Takes card shows every live start candidate when there are two (design/86 K4), one picture per role otherwise.
- checks: an unsized shot breaks a size run and is the scene's opener when it comes first (never skipped over); an element's sizes go through the same `_dimension_needs` as a drawing spec's (an unknown names what was tried and carries no number, a known size names its source); the picture check reads the picture once for the model, the light line and the detail line.
- plugin: `with_base` keeps a network share's host (`file://nas/share/...`); `vw delivery open` reads the ledger first and refuses when the Resolve step is already reserved, dispatched or reported; `relink-check` rewrites its one `## Relink` section instead of appending; `tc_seconds` names a malformed timecode tag and `relink-check` refuses with it instead of a traceback.
- Tests: `server/unit/test_review_c_pure.py` (5), `plugin/tests/test_review_c.py` (4); the design/103 A5 test now gives its confirmed size a source, and the defect-29 and design/106 page tests read the new lines. Server unit suite: 500 passed. Plugin: 308 passed, the 3 known Windows-only failures.
- Not covered: the page changes are checked as text, not in a browser; a real network share was not tried.
