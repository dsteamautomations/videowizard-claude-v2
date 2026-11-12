# 186 — Finish effects on a drawn shot, as a layer the user can have removed

12 Nov 2026. **Requirement list for SK's approval. No code yet.**

This replaces the first version of this note (search across the whole HyperFrames library, check a part on first use). SK's decision of 12 Nov, after the research in `videobuilder-v4/phase2/motion/research/findings.md`: **finish effects only, as a removable layer; shader blocks are explored later.** The file keeps its name; the search and the check on first use are not built.

## The requirement

A drawn shot may carry a **finish**: a layer of effects from the HyperFrames library that changes how the drawing looks, never what it shows. Three effects to begin with: **motion blur** on the parts that move, **film grain**, and a **soft vignette**. The assistant decides per shot whether a finish suits it. The user is told in plain words that the layer is there, and can have it taken away.

## What is built

1. **The three parts live on the server**, copied once from the library (Apache 2.0, its notice kept), pinned, with their web links removed. No fetch at run time, no search, no check on first use.
2. **The helper asks for a finish; it never pastes one.** In the shot's project a small file names the effects wanted (`finish.json`: any of `blur`, `grain`, `vignette`), and the helper marks the moving elements for blur with one attribute. The server adds the layer itself at check, snapshot and render, the same way it supplies the animation library and the fonts today.
3. **The drawing is complete without the layer.** Removing the finish is the same upload rendered without it; nothing is rebuilt.
4. **Taking it away, on both front ends** (one server function): a button on the shot in the visuals page, and `vw motion finish --shot S --off` in the chat. `--on` puts it back. Each makes a new render (under a minute) and the shot's review starts again on the new take.
5. **The review says it plainly.** Where a drawn shot has a finish, the page and the assistant say: "This drawing has an added effect on top: a soft blur on the moving parts and a film grain. If you don't like it, it can be taken away."
6. **The skill tells the helper when a finish suits**: the film's motion style decides (a calm, still style gets grain and vignette at most; a lively one may take blur), and a finish is left off where it would hurt a label's reading.
7. **The record**: the shot's take says which effects it carries, and the decision log has a line when a finish is taken off or put back.

## Expected but unstated

- The helper still may not run `npx`, `node` or `hyperframes`, and the upload check still refuses clocks, timers and web links in the helper's own files. The server's three parts are exempt because they are the server's, checked once.
- The fact checker judges the frames with the finish on, so a label blurred or dimmed past reading fails as it would today.
- The same finish across a film: the choice is made per shot, but the skill says to keep one finish for all drawn shots of a film unless a shot gives a reason.
- Every category of film may use it; nothing here is tuned to explainers.
- Free: no account, no key, no paid call, no internet at render.

## Edge cases

| Case | Handling |
|---|---|
| No `finish.json` | No finish; the shot renders as today |
| An effect name that is not one of the three | The upload is refused, naming the three |
| Blur is asked for but no element is marked | Accepted; grain and vignette apply; the answer says nothing was marked for blur |
| An element is marked for blur but blur is not asked for | The mark is ignored |
| The finish makes the render fail or run past the time limit | The server renders once more without the finish, keeps that take, and says the finish was left off and why |
| The two renders of the check differ with the finish on | The finish is left off for that shot, with the reason; the film goes on |
| The user takes the finish off after the take was selected | A new take without it; the selection moves to the new take only on the user's word |
| The user asks to take it off twice, or off when there is none | Answered "already without a finish"; no render |
| A shot built before this release | No finish; nothing changes |
| A drawn shot on the older SVG route (not HyperFrames) | No finish offered |
| The finished file is much larger because of grain (14 MB against 1 MB in the test) | Grain is set lighter than the library's default, and the size is reported on the take; over the existing limit the finish is left off |
| Two people press the button at once | The existing job claim: one render, the second answer says it is already being made |

## Failure modes

- Anything that goes wrong with the finish ends in the same place: the shot is rendered without it, the reason is said and logged, and the film goes on. A finish never stops a film.
- The removal itself failing (the render fails): the take with the finish stays as it was, and the error is shown.

## Older way

A drawn shot with no finish: kept, and the default. Nothing is retired.

## Tests

Unit tests first for every row above, with the renderer replaced by a stand-in. On the server after the deployment: the three parts drawn twice and compared, once; then one of VW-21's drawn shots with a finish, and the same shot with it taken away.

## Not covered

- Whether grain on drawn shots sits well beside real footage in one film: only a real film shows it.
- Blur in a slow, calm motion style may add nothing; only the Lively style was rendered.
- Light sweep and focus pull: read, not rendered; added later if the first three prove their worth.
- Shader backgrounds, 3D objects and the rest of the library: left out; SK will look at shader blocks again later.
- The hand-drawn annotation parts: one failed on layout in the research; not included.
- No preview of "with" and "without" side by side on the page; the user sees one, then the other.

## Release

Server and plugin both change (the skill's text, one new command). The Mac updates the plugin. It goes out with the fixes waiting locally from VW-21, in one deployment, on SK's yes.

## Built (12 Nov 2026, on SK's "approved, go ahead"; not committed, not deployed)

- `server/motion_parts/`: `blur.html`, `grain.html`, `vignette.html` (the library's files, unchanged) and `NOTICE.md`.
- `server/app/motion.py`: `FINISH`, `finish_of` (reads `finish.json`), `finish_note`, `finish_in_force`, `finish_words`, `apply_finish` (the layer, once, at the end of `index.html`, sized to the film; grain at 0.09 instead of the library's 0.15, the vignette at a warm quarter strength); `problems` refuses a bad `finish.json`.
- `server/app/visuals_stage.py`: the request carries `finish` only when there is one (an older shot's request and its cached take are unchanged); `motion_finish` (off or on, a line in the decision log, then a new render; the selection is not moved); `_finish_view` for the page; the upload and the render answer say the finish.
- `server/app/visual_workers.py`: HyperFrames' check runs on the helper's own drawing, without the layer (its contrast rule would otherwise judge the vignette); `render_with_finish` then draws one frame twice, renders with the layer, and on any failure renders without it and records why; snapshots are taken with the layer on.
- Route `POST /visuals/motion/finish`; page action `motion-finish` with the sentence and one button on a drawing's take ("Take the effect away" / "Put the effect back"); `vw motion finish --shot S --off|--on`.
- `plugin/skills/motion/SKILL.md`: "A finish, when it suits the shot"; `plugin/commands/vw.md`: one paragraph for the main assistant.

Proven on the server before the build, by Claude's script outside the application (`videobuilder-v4/phase2/motion/research/inject_test.py`): a project whose helper only marked the moving elements, with the layer added at the end of the page, drew, and drew the same twice.

Tests: `server/unit/test_design186_finish_pure.py` (21), one in `plugin/tests/test_design183_set_aside.py`. Server unit suite 1,500 passed; plugin 472 passed and the same 4 Windows-only faults. The page's script parses.

Also not covered, found while building:
- `motion_finish` and the worker's wiring have no unit test of their own (they need the database and the renderer); their decisions are tested as plain functions. First real proof: VW-21.
- The new button was not clicked in a browser.
- There is no size limit on a drawn take in the application, so "over the existing limit the finish is left off" has nothing to act on; the take's size is recorded as before.
- The instruction for the main assistant is in `commands/vw.md` only, not in the visuals instructions (`v3.json`).
- Blur works on HTML elements moved by `transform`, not on shapes inside an `<svg>`; the skill says so.
