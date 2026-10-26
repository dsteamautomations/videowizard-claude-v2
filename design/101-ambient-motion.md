# design/101 — The surroundings move in every take (ambient motion)

26 Oct 2026. SK, after VW-7: "I had requested ambient conditions to be added as a rule while generating images. When I mean ambient, I mean that when a video is created, the surroundings also should appropriately move. For example, a tree in the scene should have a slight motion, and there should be other activities going around the particular scene." The audit (`course-learnings-audit-2026-10-26.md`) found no server rule for it. On VW-7 the moving palms and drifting dust reached the takes only because the assistant wrote them in, and the take check never asks whether the background moves. **Nothing is built until SK approves this note.**

## 1. What changes

| # | Rule | Where |
|---|---|---|
| M1 | **The scene says what moves around the action.** Each scene gets `ambient`: one line naming what moves besides the main action, chosen from the setting and the footage beside the gap. Examples: "palm fronds and tree leaves sway in a light breeze; fine dust drifts in the light; two workers on the far scaffolding pass bricks"; "indoors, still air; a ceiling fan turns; a child crosses the doorway". A scene meant to be still says so ("still: nothing else moves"). The field defaults to empty, so old plans stay valid. | `visual_contract.Scene` |
| M2 | **The plan check warns when it is missing.** A scene with a video shot and an empty `ambient` gets the warning "scene X: say what moves around the action (ambient): trees, air, people in the background, or 'still'". It is a warning, never a refusal, as with design/91 N4. | `validate_plan` |
| M3 | **The server writes it into every take.** When the shot's scene has an ambient line, the take's text gains one fixed sentence after the motion: "Throughout the shot the surroundings stay alive: {ambient}." The server reads it from the plan, so the assistant can't drop it. Takes already prepared keep their text. | `prepare_take` (the record gets `ambient`); `video_providers.motion_text` |
| M4 | **The take check asks whether it moved.** When the take has an ambient line, the check gets one more **must** line: "surroundings move: what the plan's ambient line names moves visibly through the shot; nothing that should move is frozen". It is given the line to compare against. A frozen background then shows as marked, like any failed must line. As design/96 X1 says, no fix starts on its own. | `image_check` (`TAKE_LINES` plus this line when the take has `ambient`) |
| M5 | **The start image has something to move.** The start-image instruction gains: "Put in the frame what the scene's ambient line says moves (the trees, the people in the background, the dust in the light), so the take can move it." | `visuals_stage.packet` start instruction |
| M6 | **The assistant is told, and the operator sees it.** The procedure's plan step names the field in one sentence. On the page, the shot's facts show "Moves around it: {ambient}" for a video shot, on the Plan step and on the Takes cards. | `procedures/v2.json`; `page_view` gives each shot its scene's ambient; `visuals.html` |

Nothing else changes. The handover's B3 ("natural, unhurried motion") and C4 ("no person stands frozen while others move") stay in their own releases (4 and 6).

## 2. No re-acceptance (SK, 26 Oct)

SK: approved, without asking for acceptance again. So the ambient line is left out of the fingerprints that would otherwise force work:

| Fingerprint | Done | So |
|---|---|---|
| The gap's digest (acceptance, bindings) | `ambient` is left out | Adding or changing a scene's ambient line keeps its gaps accepted and its shots bound. Approved pictures stay approved. |
| The take's preparation digest (a ready take is selectable only while it is current) | `ambient` is left out, and M5's sentence sits in the packet's context, which the digest already leaves out | Takes prepared before the release, or before a scene got its line, stay selectable: VW-7's B01_S1 takes, and every other run's. Built as first written, M5 alone would have made every prepared take on every run unselectable after the deploy. |

**The cost:** the ambient line reaches the takes without an operator's yes recorded on the run. The operator sees it on the page (M6) and can ask the assistant to change it.

**VW-7:** the assistant adds an ambient line to each scene that has a video shot still to make, and submits the plan again. Nothing is accepted or bound again, and the next takes carry the line.

## 3. Tests first

- **M1:** the plan schema takes `ambient`, defaulting to empty. An old plan passes.
- **M2:** a scene with a video shot and no ambient gets the warning; a graphics-only scene doesn't; "still: nothing else moves" counts as filled.
- **M3:** a take prepared for a shot whose scene has an ambient line carries it in `effective_prompt` once, after the motion. Without the line, the text is unchanged from today.
- **M4:** the take check asks six lines and passes the ambient line when the take has one; five lines without.
- **M5:** the packet carries the sentence.
- **No re-acceptance:** adding an ambient line to an accepted plan keeps its gaps accepted, its bindings valid, and a ready take's preparation digest unchanged. A plan with no ambient line gives the same digests as today.
- **M6:** the procedure names the field; the page data gives the shot its ambient; the page shows "Moves around it". The script parses, and a browser check runs on a local copy of the page with VW-7's data.
- **The suites:** `server/unit` and `plugin/tests` both run. The plugin doesn't change: the plan schema it gives the assistant comes from the server.

## 4. Not covered

- Whether Omni moves the background reliably when asked. VW-7's first take asked for swaying palms and they stayed still. M4 will show how often this fails, and whether the sentence needs to be stronger or earlier in the prompt.
- Stills. A still has no motion; M5 only puts the moving things in the frame.
- `server/tests` (Docker).

## 5. Release

Server 0.48.0; the plugin is unchanged. Not committed or deployed until SK says so.

## As built (26 Oct 2026)

Server 0.48.0, plugin unchanged. Not committed or deployed.

**M1 to M6, as described above.**
- The ambient line is left out of the gap's digest and the take's preparation digest (`without_ambient`).
- The start-image sentence is carried in the packet's context.
- Tested: a plan without the line gives the same digests as before, so ready takes on every run stay selectable.

**Added at SK's request (screenshot of VW-7's Takes step):**
- On the Takes step, a take's check folds to one line ("Take check: 5 passed", or what was marked, at which second), as a picture's check has since design/97 K1.
- The Review column shows the latest verdict with its reason, and folds the earlier ones ("1 earlier").

**Tests:**
- `server/unit`: 419 passed, 10 of them new in `test_design101_pure.py`.
- `plugin/tests`: 267 passed, with the 3 known Windows-only failures.
- Browser: a check on a local copy of the page with VW-7's data showed the "Moves around it" line, the folded rows (64 to 84 px each), and no script error.
