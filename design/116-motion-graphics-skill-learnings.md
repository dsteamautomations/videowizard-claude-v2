# design/116 — What the Motion Video Director skill teaches us about the drawn route (study, 28 Oct 2026; reviewed the same day)

SK's request: after VW-7's pictures came out well and its motion graphics failed, study `github.com/mattypark/Motion-graphics-skill` (a copy of Miftahul Islam Efaz's "Motion Video Director", plugin version 3.0.0) and say what it teaches, which parts could be brought into our setup, and whether they take care of the current failures. No code; this is the reading. SK then asked for a second, critical pass over the first reading; the corrections are marked **(review)**.

## 1. What the repository is

One skill file (`SKILL.md`, about 50 KB of instructions to the assistant) and five small helper scripts. No renderer, no library, no icon set, no scene language. Its method:

- The assistant **writes the animation as code** (Canvas, SVG, GSAP, Three.js) in a project folder, one deterministic `drawFrame(t)` per scene, renders frames in headless Chrome, and joins them with ffmpeg.
- A **fast preview loop** (`scripts/preview.mjs`): render a time range small and at 8 frames a second, tile every frame into one contact sheet with a timestamp under each, look at the sheet, fix, re-run, and only then render in full. "Never check a change with a full render or a few random stills."
- A **production playbook** around it: brief, voiceover script, storyboard timed to the words, style board, preview approval, final render, a QA checklist; `PROGRESS.md` and `LOG.md` in the project folder.
- The rest is **taste written down**: director's rules (one idea per shot, text of six to eight words, reading time 0.3 s a word plus 0.5 s), an intensity table by video type (educational = level 3: highlights, arrows, step counters, diagrams; corporate = level 1), animation principles (easing never linear, entrances 200–500 ms, exits faster, stagger related items 40–80 ms, one focal point per moment), colour and composition, typography, sound design, and four reverse-engineered "recipes" of Instagram reels.
- The other scripts: `preflight.sh` (what is installed), `analyze_ref.sh` (break a reference video into frames, cuts and a spectrogram), `create_env.sh` and `normalize_env.py` (API key files). The MCP connections SK mentioned are only named in the playbook; nothing in the repository depends on them.

What it is not: there is no asset in it that draws a brick, a house or an icon. Its examples (SaaS reels, talking-head captions, kinetic type) are a different genre from a construction explainer. Its quality comes from two things: the assistant writes free code for each scene, and it looks at every frame before it ships.

## 2. Our drawn route beside it

Design/113 went the other way on purpose: the planner never writes code. It writes a **declarative scene** (rect, line, arrow, circle, polygon, text, image, group, repeat; actions appear, build, move, highlight, fade keyed to a second or a word) and the server renders it with Pillow and ffmpeg. That choice keeps the operator's chat deterministic, cheap and checkable, and it stands. The failures Revathi met are not the choice. They are one wrong routing decision, three gaps in the language, one mandatory field that forces nonsense, and a check that reads the wrong thing.

## 3. Where VW-7 stands (review)

Revathi has worked around every failure by hand: left edges computed from text length, walls drawn course by course, the golden picture inside the house fronts, seven separate drops. Her plans carry those workarounds now. Any fix that changes what an existing scene means (a new default anchor, say) would move her texts again. Every change below keeps her scenes rendering as they do today; new fields are opt-in.

## 4. The failures, what the skill does about each, what to bring in

| # | Failure on VW-7 | What the skill does | What to bring in |
|---|---|---|---|
| 0 **(review)** | **Concept shots were routed to drawing.** "Fewer bricks, less soil, less fuel" has nothing exact in it; its icons became polygons because the planner drew a thing that should have been a picture. The procedure already says the picture sequence "stays for a painterly look where nothing must be exact", but its headline sentence makes drawing "the default for technical diagrams, charts, maps and timelines", and the planner read every graphic as one of those. | "Real proof floats in as cards": photos, UI, product shots. The skill never builds a real object from primitives; icons come as Lottie or SVG files. | **Sharpen the route rule.** Drawn when something must be exact: sizes, counts, a sequence of courses, a comparison of two measured things. Everything conceptual goes to the picture route that already works: a still with a push-in, or a sequence of states for a build. And the hybrid the language already allows: an `image` shape carries the approved picture of the thing, and the drawn layer adds the text, arrows, highlights and builds over it. This is a procedure change and one check line; no renderer work, and it removes most of the need for an icon set. |
| 1 | **Text drawn from its left edge, placed by its centre.** Titles at x = 50 start mid-frame and run off ("Fewer bricks: less soil and fue"). The safe-area check tests the anchor point only, so a text whose box leaves the frame passes. **(review)** The bottom labels ("Single storey", "Two storeys") are not clipped; they sit in the bottom 5 %, under a player's controls, for the same reason: the anchor passes, the box is never measured. | Canvas text has `textAlign` and `textBaseline`; the contact sheet catches anything cropped. | **An `align` field on text (`left`, `centre`, `right`) and a `baseline` (`top`, `middle`, `bottom`). (review) Default `left` and `top`, as today, so Revathi's computed edges stay right.** The server measures the text box with the font at render size and **refuses a scene whose text box leaves the safe area**, before any render. The procedure tells the planner: titles `align: centre`. |
| 2 | **Primitives only.** A wall became a filled rectangle with lines. | See 0. | **The units rule.** A drawing of a measured thing is built from its units: a wall is a `repeat` of a course at the spec's pitch, a stack of bricks is a `repeat` of a brick. One procedure sentence and one check line ("a wall shows its courses"). **(review) No icon set now.** With rule 0 the icons are pictures; an icon set is a guess at a need no run has shown yet. Build it only when a run asks for an icon a picture cannot give. |
| 3 | **A build on a repeat reveals every copy at once.** `states` treats a repeat as one shape. | GSAP staggers: every item its own tween, 40–80 ms apart. | **`build` steps through a repeat's copies** using `every_s`, as it already steps through a group's members. One change in `states` and `draw_shape`. Revathi's seven separate drops keep working. |
| 4 | **An undocumented size cap.** Hundreds of drawn bricks pushed the plan past the 256 KB request body limit (`MAX_BODY_BYTES`, design/93's guard against blobs in the database); the refusal names no cause. | Not a concern there: scenes are files on disk. | **Name the cap in the refusal with the cure** ("use `repeat` for courses, an `image` for a picture"). With fixes 0 and 2 a wall is three shapes, not three hundred; the limit stays. If a run with many drawn shots still hits it, the scenes move to storage as files; not before. |
| 5 | **The percent key in the corner** ("wall height 32 %", "outline width 16 %"), in all three screenshots, not in Revathi's list. **(review) Root cause:** `drawn_needs` requires a `drawing_spec` for every drawn shot, so a concept shot with no real sizes forces the planner to invent a spec in percent, and the server then labels those percentages, "never dropped" (design/113 answer 2). | No size labels; a diagram's figures are text the author writes. | **The spec is required only when the scene is in real units** (`mm`, `cm`, `m`). A `%` scene needs no spec and gets no server labels; its figures ("20 kg/cm²") are the planner's own text, as they already are. A spec given in percent is refused at the References step: a percentage is layout, not a size. |
| 6 | **The check read two frames and passed wrong drawings.** **(review)** Half right in the first reading: the check *did* catch the text (its label lines failed and show as check marks on the Takes step; that is where Revathi's quotes came from). By SK's answer 3 on design/113 it never holds a drawing back. What it missed is the shapes: a rectangle named "wall" and a polygon named "fuel" satisfy lines that ask about labels and the view. | The contact sheet: every frame of the move on one picture, looked at before the render counts. | **A contact sheet per drawn shot, shown and read.** One frame every half second at a quarter size, tiled with the time under each (one ffmpeg `tile` filter), stored beside the mp4, shown on the Takes step as the shot's picture, and given to the Gemini read in place of the two frames, with three new fixed lines: every text whole and inside the frame; each named object looks like the thing it is named; things that build appear one after another. **Question for SK:** should a failed must line now hold the drawn shot until the operator accepts it with a quote, as a take is held? Today it only marks. |

Cheap polish, after the fixes, not with them **(review: moved out of the fix sets)**: `appear` gets a fixed 300 ms fade-in and `move` an ease-in-out, no new fields; the skill's reading-time rule (0.3 s a word plus 0.5 s) as a warning on drawn text against the shot's seconds.

## 5. What not to bring in

- The code-writing renderer. It is why the skill's output looks good and why it cannot be checked, repeated or run by an operator who does not read code. Design/113's decision stands.
- Node, Playwright, GSAP, Three.js, Motion Canvas, the Python models. The VM has none and needs none for 2D diagrams.
- The project-folder workflow and its gates. We have the run, the session, the procedure and the References approval; a second bookkeeping is the "two front ends" problem design/93 forbids.
- The MCP connections and asset hunting. Our pictures come from the approved references and Gemini; sound and stock footage are the editor's.
- The reels recipes, 3D, kinetic captions, sound design, loudness: a different genre.
- **(review) Considered and left out:** a run-level palette for drawn shots (the skill's 60-30-10). Revathi's shots are already consistent in cream and brick; nothing asks for it. The icon set, as said in row 2. `analyze_ref.sh` for reference videos: our references are pictures, and nothing in the flow takes a video reference yet.

## 6. Build order (review)

Three sets, each deploying on its own, VW-7's existing scenes untouched by any of them:

- **Set A, the language (server, tests first):** `align` and `baseline` on text with the measured box check (row 1); stepped `build` on a repeat (row 3); the spec optional for `%` scenes and no percent labels (row 5); the 413 refusal naming the cap (row 4). Small, mechanical, closes the three screenshots.
- **Set B, the routing and the check (procedure and server):** the sharpened route rule and the units rule with their check lines (rows 0 and 2); the contact sheet per drawn shot, shown and read, with the three lines (row 6); SK's answer on holding a failed drawing.
- **Later, only on a shown need:** the fade-in and easing; the reading-time warning; an icon set; scenes as files.

Set A first because it needs no decision beyond this note; set B needs SK's one answer and changes what the planner is told, so Revathi's next plans change with it.

## 7. Not covered by this study

- I have not run the skill. The reading is of its text and scripts; its outputs are the author's reels and the GIFs in its `assets/`.
- Whether Gemini Flash reads a tiled contact sheet as reliably as two full frames is untested; the first renders of set B will tell.
- The three screenshots are all I have seen of VW-7's drawn output; Revathi's other drawn shots may show failures these six rows do not name.

## 8. SK's questions after the review (28 Oct 2026)

**The approved graphic style.** Every run approves a style picture and a palette text on the Pictures step (design/89). The AI pictures are made and checked against it. The drawn route ignores it: `drawn.py` never reads it, `check_drawn` never compares with it, and the procedure's drawn sentences never name it. The planner picks colours per shape from memory of the palette, which is why VW-7's clips are close to the style and not of it. Whatever route we take, the style picture and palette become an input to the drawing and a line in its check. That was missing from rows 0 to 6 and is now part of set B.

**Why the code route looked worse than it is.** The objection "the operator cannot read code" was weak: the operator reads neither the plan's scene data nor code; they see pictures and clips. The real differences are three. Code needs a runtime the server does not have (a browser engine); code cannot be checked by rules before it runs, only by looking at its render; and code run on the server from a model's output needs a sandbox. None of these is a reason to stay with primitives if the primitives cannot reach the look.

**What makes the skill's output good.** Not the fact that it is code. Three things: curves, paths, gradients and shadows are available, so a flame looks like a flame; the assistant renders, looks at a contact sheet, fixes and renders again until it is clean; and a person approves the preview. Our route has none of the three today.

**Inputs the code can take.** Yes. The approved style picture and the palette text go to the model as the look to match; the golden picture of the shot and the spec's sizes go in as the content; the code loads approved pictures as image layers and animates over them. The check compares the contact sheet with the style picture and the golden picture. That turns "no control over what it does" into the same control the pictures have now.

**Three ways forward, from least to most change.**

| | What | Runtime | Checkable before render | Look | Cost to reach |
|---|---|---|---|---|---|
| 1 | Primitives with sets A and B | as today | yes | correct, plain | small |
| 2 | **SVG scenes** (recommended) | cairosvg on the VM (one pip, one apt library) and the Noto font | yes: SVG is data; text anchors, paths, gradients and embedded images are native; the same action list drives visibility and movement per frame | most of the skill's 2D look; models draw good SVG | medium: a renderer that rasterises an SVG per frame, the actions applied as attribute changes; the style and golden pictures embedded as `<image>`; the sheet and the read as in set B |
| 3 | Code (JavaScript in headless Chrome) | Node, Chromium and Playwright on the VM, or on the operator's PC as the skill does | no; by render only, in a sandbox | the skill's full look, including 3D | large: a runtime on the VM, a sandbox, a write-render-look-fix loop in the planner, and a setup on every operator's PC if rendered there |

Why 2 over 3 for now: SVG is what the model would write inside the code anyway for a 2D diagram; it keeps the server as the renderer and the rules as the first check; it needs no browser, no sandbox and nothing on Revathi's PC; and the look-fix loop with the contact sheet works the same. If a run then asks for something SVG cannot give (3D, physics), route 3 is the next step and the loop and the checks carry over.

What stays from the earlier plan under route 2: set A's fixes become SVG natives (`text-anchor` instead of `align`; builds step through `<g>` children; no spec for conceptual scenes); set B stays as written, with the style picture added to the drawing's inputs and the read.

## 9. The recommendation with the restrictions lifted (SK, 28 Oct: "all I want is a better output"; installing on the VM or the operator's PC is allowed)

The route question was the wrong axis. Four things make the skill's output good, and they are independent of each other: what the drawing language can express; what renders it; whether someone looks at every frame and fixes before anyone else sees it; and whether the approved look goes in as an input. The best answer picks each on its own.

1. **Pictures for the things, drawing for the exact parts.** The run's pictures already come out well and carry the approved style. A drawn shot becomes an approved picture (the golden picture, or a picture made for the shot) as the base, with the drawn layer over it for what must be exact: labels with units, arrows, highlights, the courses that build one by one, the comparison bars. Only a shot whose whole content is measured (two walls at their course pitch) is drawn end to end. This alone is the largest step in look, because the model that makes pictures is far better at a flame, a mound or a house than any shape language, and it is already paid for and approved.

2. **SVG as the drawing language, not JavaScript.** SVG has paths, curves, gradients, shadows, text anchoring, fonts and embedded images: everything the skill's code uses for 2D. It is data, so the rules still run first (text inside the frame, palette colours only, sizes from the spec, no figure for an unknown size) and the same scene renders the same way twice. The action list stays (appear, build, move, highlight, fade keyed to a word or a second), applied per frame as attribute changes; `build` steps through a group's children. Scenes are stored as files, not in the plan body, so the size cap goes away.

3. **Headless Chromium on the VM as the renderer.** Not cairosvg: it has no filters, so no shadows or blur, and its font handling is weaker. Chromium renders SVG completely, with the Noto font, at 1080p, through Playwright's Python package (`pip install playwright`, `playwright install chromium --with-deps`), so no Node and nothing on the operator's PC. Rendering stays deterministic: the server sets the frame's time, takes a screenshot, pipes it to ffmpeg. And because Chromium is there, a later "scene code" option (JavaScript, for 3D or particles) is a flag on the same renderer, not a rewrite; today nothing in a construction explainer needs it.

4. **The look-and-fix loop, on the server, before the operator sees anything.** Render the shot at a quarter size, tile one frame every half second into a contact sheet, give the sheet with the style picture, the golden picture and the shot's lines to Gemini, and let it fix the SVG and render again, up to three passes. Then the operator sees the sheet and the clip on the Takes step, with what the loop fixed and what still fails, and approves or rejects with a note. The sheet is also the record. The loop costs one Flash vision call a pass.

5. **The style and the golden picture as inputs everywhere**: to the planner when it writes the scene, to the fix loop, to the final read.

What this keeps from design/113: the planner writes data; the server renders; the spec's sizes are checked; the operator approves. What it drops: Pillow primitives as the language; the percent spec; two-frame reads.

What to prove before building it all, as design/113 did with its sample: take the three failed VW-7 shots, run the new pipeline on the VM by hand (SVG from the model with the style and golden pictures, Chromium render, the sheet, the Flash fix loop), and show SK the three clips. The sample answers the unknowns: Chromium's memory and speed on the VM, Flash's ability to fix SVG, and the look. If it passes, the build is: the SVG renderer and the loop on the server (replacing `drawn.py`'s drawing, keeping its contract), the routing and style sentences in the procedure, the sheet on the Takes step, scenes as files. If it fails on look, the next step is scene code on the same renderer, and the sample has already installed what it needs.

Not covered: the VM's size for Chromium (check before the sample); whether Revathi's existing VW-7 drawn plans convert (they would be re-planned as SVG; three shots, one sitting); the operator's remaining drawn shots on VW-7 keep rendering on the current route until the new one is live.

## 10. SK's addition: components from the picture model (28 Oct)

An image model returns pixels, never SVG; only a text model writes SVG. That does not matter: the plan above composites pictures inside SVG, and a picture can be a part as well as a whole. So the addition strengthens point 1 of section 9 rather than changing it:

- **A component set per run.** Each thing a drawn shot needs (a brick, a flame on logs, a mound with a spade, a drop, a chimney with smoke, a house front) is made by the picture model as a cut-out on a transparent background, in the approved style with the style picture as its reference, checked and approved once on the Pictures step like any picture, then reused across every shot of the run.
- **The SVG scene places and moves them.** Each component is an `<image>` the actions can appear, build, move, highlight and fade; the drawn layer adds the exact parts over and between them. A brick flying into the wall, seven drops falling one by one, a flame growing: motion graphics with designed parts, with no part drawn from primitives.
- **Consistency comes free.** One style reference for every component, and one approved copy of each part for the whole run, so the second shot's brick is the first shot's brick.

Costs and limits: one picture per component (the run's image price), approved once; the model's transparent backgrounds are good but not perfect, so the check keeps a line for clean edges; a component is a flat picture, so a turn or a cutaway of it is a second component, not a transform. Vectorising the cut-outs is possible and unnecessary: Chromium composites pictures at full quality.

For the sample: the three failed shots need about eight components (bricks stacked, mound and spade, flame, house front at one, two and three storeys, a drop, a bolt). They are made first, then the three scenes.
