# design/117 — Drawn route v2: components, SVG scenes, Chromium render, the fix loop (requirements, 28 Oct 2026)

SK's decision (28 Oct, after design/116): "Agreed. I want to go ahead with this." Implementation and unit tests only; **deployment is on hold** and nothing in this note installs anything on the VM or the operator's PC until SK says so.

## 1. The requirement, restated

A drawn shot (a graphic whose content must be exact: sizes, counts, a build in steps, a comparison) comes out looking designed and consistent with the run's approved style, and no one sees a wrong drawing before it has been looked at frame by frame and fixed. Five parts:

1. **Components.** The things a drawn shot shows (a brick, a flame on logs, a mound with a spade, a house front) are pictures made by the picture model in the approved style, each a cut-out on a transparent background, approved once on the Pictures step and reused in every shot of the run.
2. **SVG scenes.** The planner writes the scene as one SVG document (data, never code) that places the components and the approved pictures, draws the exact parts (labels with units, arrows, bars, courses), and keeps the action list of design/113 (appear, build, move, highlight, fade, keyed to a word or a second) by element id.
3. **Chromium renders.** The server renders every frame in headless Chromium through Playwright's Python package: full SVG (paths, gradients, filters, fonts, embedded pictures), deterministic (the server sets the time; no animation of the SVG's own), nothing on the operator's PC.
4. **The look-and-fix loop.** After a render the server makes a contact sheet (one frame every half second, tiled with the time under each), gives it with the style picture, the shot's pictures and the shot's lines to Gemini, and lets Gemini correct the SVG and render again, at most three passes. The operator then sees the sheet, the clip and what the loop fixed or could not fix, and approves or rejects with a note.
5. **The style as an input.** The style picture and the palette go to the planner when it writes the scene, to the fix loop, and to the final read; the palette's colours are a line of the read.

Out of scope (design/116 §5): JavaScript scene code, 3D, sound, the skill's project bookkeeping, asset hunting, an icon set.

## 2. What exists, and what stays

- `drawn.py` (design/113) renders `scene_drawn` (primitives) with Pillow. **It stays as it is** so VW-7's existing drawn plans keep rendering; a shot carries `scene_drawn` or `scene_svg`, never both. The old route is removed in a later note once no live run uses it (question 2).
- `render_drawn`, `process_drawn`, `check_drawn`, the `drawn` job family, the Takes step's drawn card, `vw visuals draw`: kept and extended; the SVG path branches inside them.
- `generate_image` and the picture check (design/89, 71, 111): a component is one more picture kind through the same function; the Pictures step approves it as it approves any picture.
- `image_ref` on a shape already requires an approved picture of the run; SVG `<image>` uses the same rule.
- The VM: e2-standard-4, 4 vCPU, 16 GB, 91 GB free, Ubuntu 24.04, Python 3.12 venv. Chromium fits (about 250 MB a process, one per worker, eight workers).

## 3. The pieces

### P1 Components (server, plugin, procedure)

- `REF_KINDS` gains `component`. `vw visuals image --element E --kind component --prompt …` (and the page's form) makes one through `generate_image`: element kind `object`, `material`, `process` or `technique` (never `person`, `graphic`, `style`); the style picture is sent as Image 1 (the server adds it when the planner does not); the request asks the image API for a transparent background (`background: transparent`, PNG).
- Server lines added to the prompt (design/71 F2 style): "one <element name> alone, nothing else in the frame, on a transparent background, in the style of Image 1, seen from the front/side as the plan says".
- The picture check (the existing Gemini read) gets two more must lines for a component: "one thing only, no background, no ground, no shadow outside its edge" and "the edge is clean, nothing cut off". The server adds a code line: the PNG has an alpha channel and at least 20 % of its pixels are fully transparent; otherwise the candidate is marked failed with "no transparent background" and the planner retries.
- A component is approved like any picture; it needs no golden picture and no sheet (it is a thing's picture, not a person). It is listed on the Pictures step under its element with the word "component".
- Procedure: "A drawn shot's things are components: one picture per thing per run, made in the approved style on a transparent background, approved once, placed by the scene with `<image href="ref:<id>">`. A thing is never drawn from shapes when a component or the golden picture can show it."

### P2 SVG scenes (contract, upload, rules)

- `Shot.scene_svg: {'sha256': …, 'actions': [DrawnAction…]}` beside `scene_drawn`; exactly one of the two on a drawn shot.
- The SVG travels as a file, not in the plan body: `vw visuals scene --shot S --file scene.svg` → `POST /api/runs/{id}/visuals/scene` (multipart, like `font`), stored at `<run>/visuals/scenes/<sha>.svg`, listed in `session['scenes']` with its sha, size, shot and time. The plan's `scene_svg.sha256` must name an uploaded scene. Limit 2 MB.
- **Rules at upload (refused with the reason, before any render):**
  - parses as XML with root `svg`; `viewBox` present with the film's aspect (16:9 within 1 %); `width`/`height` absent or equal to the viewBox;
  - elements allowed: `svg g defs title desc rect circle ellipse line polyline polygon path text tspan image use linearGradient radialGradient stop clipPath mask pattern filter feGaussianBlur feDropShadow feOffset feBlend feMerge feMergeNode feFlood feComposite feColorMatrix`; anything else refused by name (`script`, `foreignObject`, `animate*`, `set`, `style`, `a`, `switch`);
  - attributes: no `on*` handlers, no `style` attribute containing `url(` or `@import`, no `href`/`xlink:href` except on `image` (`ref:<reference id>` of an approved picture or component of the run) and on `use`/gradients/filters/clip/mask (`#id` inside the document);
  - ids: every element an action names exists and is unique; a `build` names a `g` (its children step) or a list of ids;
  - fonts: `font-family` only `Noto Sans` or the run's brand font name; the server supplies both as `@font-face`;
  - colours: every `fill`/`stroke` is `none`, `currentColor`, a `#RRGGBB`, or a `url(#id)` to a gradient in the document (the palette is read by Gemini, not refused here, so tints stay possible);
  - text: every `text` has `font-size` of at least 4 % of the viewBox height (design/91 N13) and at most eight words (design/116, the skill's rule); its rendered box inside the inner 90 % of the frame is measured by Chromium at render time (P3), not here.
- **Spec rule:** `drawing_spec` is required when the shot has `claims` with a figure or the scene's text carries a number with a unit; then every known size of the spec appears in the scene's text with its unit (string match), and an unknown size shows no figure (design/106 D6 kept). A conceptual scene with no figures needs no spec. The server places no labels of its own on an SVG scene.
- `drawn_needs` (design/113 E1/E5) runs for `scene_drawn`; a new `svg_needs` runs for `scene_svg` with the rules above that do not need the file (the file's rules run at upload and again at render, since the plan may change after the upload).

### P3 Chromium render (server, worker)

- `server/app/svg_render.py` (new): `page_html(svg_text, fonts, images)` (an HTML wrapper: the SVG inline at the film's size, `@font-face` from data URIs, `ref:` images rewritten to data URIs, all CSS animation disabled, `background` from the SVG's own first `rect` or white); `measure(page)` (every `text`'s `getBBox` in frame pixels, for the safe-area rule and the text-box check); `render(request, out_path, images, fonts)` with the same contract as `drawn.render` (`{'frames', 'digest'}`): one browser per worker process (lazy, reused, restarted on error), one page per render, viewport = film size, device scale 1, GPU off; per frame `page.evaluate(setState, state)` then `page.screenshot(type='jpeg', quality=95)` (or PNG; the sample decides on speed), piped to ffmpeg as today; `frame(request, index)` for one frame.
- `states()` is lifted from `drawn.py` into a shared `drawn_states.py` and keyed by ids; for SVG, `setState` sets `visibility`, `opacity`, `transform: translate(dx, dy)` in viewBox units and, for highlight, an outline (a stroke of the highlight colour on a cloned path behind, or an `outline` filter) on the named element; `build` steps a `g`'s children in document order.
- Determinism: the same request renders byte-identical frames (a test). Timeouts: 120 s a render, 10 s a frame; a crash restarts the browser once, then fails the job with the reason.
- `process_drawn` branches: `scene_svg` → `svg_render.render`; otherwise `drawn.render` as today. Both produce the sheet (P4).
- `requirements.txt` gains `playwright==1.57.0` (the exact version pinned on the day of the commit); the VM step (held) is `playwright install chromium --with-deps` as root once, and the worker service file adds `PLAYWRIGHT_BROWSERS_PATH=/opt/vw2/browsers`.

### P4 The contact sheet and the fix loop (worker, check)

- `sheet(frames_png, fps, every_s=0.5, cols=6, scale=0.25)` in `svg_render.py` (works for both routes: it takes frame PNGs): one frame every half second, the time under each, tiled, one JPEG; stored at `<run>/visuals/drawn/<job>-sheet-<pass>.jpg`.
- `check_drawn` becomes the loop, run inside `process_drawn` so the operator sees the finished result once:
  1. render → sheet → the read: Gemini Flash (the analysis model) gets the sheet, the style picture, the shot's pictures (components, golden) and the lines: the claims, the spec's relationships, every text as a label line, the view, and the fixed lines "every text is whole and inside the frame", "each named object looks like the thing it is named, as its picture shows it", "things that build appear one after another", "the colours are those of the approved style";
  2. if every must passes, or the pass count is three, stop;
  3. else the fix: the same model gets the SVG, the sheet, the failed lines and the rules of P2, and returns the corrected SVG only; the server runs the P2 rules on it (an invalid fix counts as a pass and is dropped); the actions stay; render again from step 1;
  4. the result keeps the best pass (fewest must failures; the last on a tie), every pass's sheet and lines, and a one-line account of each fix ("pass 2: moved the title inside the frame; recoloured the arrow to the palette's saffron").
- The SVG the loop produced is stored beside the original (`<sha>.svg` and `<job>-fixed.svg`); the plan's `scene_svg` is not rewritten (the plan is the planner's); the next `draw` of an unchanged plan reuses the job by digest as today, so the fix is not lost. A planner who wants the fixed SVG back runs `vw visuals scene --shot S --download`.
- Cost: one Flash vision read and at most two fix calls a shot, counted as the run's spend like a check.
- A drawing whose must lines still fail after the loop: **question 1** (hold until the operator accepts with a quote, or mark only as today).
- No Gemini key or a read error: the loop is skipped, the clip is marked "unchecked: <reason>", never held (design/113 answer 3 kept for that case).

### P5 The operator's view (page, plugin, procedure)

- Takes step, drawn card: the sheet as the picture, the clip, the pass count, the lines with pass/fail, the loop's account; "Your turn: look at the sheet and the drawing, select it, or reject it with what to change."
- Pictures step: components listed under their element.
- `vw visuals status`, `what is next`: name the scene upload and the components when a drawn shot lacks them.
- Procedure (`v2.json`, VW-VISUALS): the routing rule (design/116 row 0: drawn only when something must be exact; a conceptual graphic is a picture with a push-in or a sequence of states; the hybrid places the picture and draws the exact parts over it); the component rule (P1); the SVG authoring rules (P2) in the planner's words, with a short example scene; the text rules; the loop's existence ("the server renders, reads a sheet of every frame, fixes up to twice, then shows the operator").

### P6 Versions and logs

Server 0.68.0, plugin 0.56.0 (design/115's 0.67.0/0.55.0 are committed, not deployed). Design/35 row and design/49 line when deployed, not before.

## 4. Unstated but expected

- VW-7's existing drawn shots keep rendering unchanged; nothing re-plans them.
- A component made for one shot is reusable by every shot (approved pictures are run-wide already).
- The brand font (design/113 E4) is served to Chromium as the SVG's font when the run has one; Noto Sans otherwise.
- A render of an unchanged scene is free and cached by digest, loop included.
- The operator never sees an intermediate pass; the card shows the finished loop.
- The plugin stays Python 3.9; the page stays one file; the server's tests run without Chromium except the ones marked as needing it, which run on this PC with Chromium installed in the test venv (and on the VM later).
- Nothing in this work writes to the database by hand; sessions change through the server functions.

## 5. Edge cases and how each is handled

| Case | Handling |
|---|---|
| Empty, non-XML, or non-`svg` root file | upload refused: "not an SVG document" |
| No `viewBox`, or aspect not 16:9 | refused with the film's aspect named |
| `script`, `foreignObject`, `animate`, `style`, `a`, external `href`, `on*` attributes, `url(` in style | refused by name; nothing else of the file is read |
| `image` href not `ref:` or naming an unapproved or rejected picture | refused: the picture's id and status |
| An action names an id not in the document; two elements with one id | refused: the id |
| `build` on a non-group with one id | treated as `appear` |
| Text under 4 % or over eight words | refused with the text quoted |
| Text box leaves the inner 90 % at render (measured by Chromium) | the render stops before frame 1; the job fails with the text and its box; the loop's fix pass is offered the same way (the measurement is a line the fix sees) |
| Font glyph missing (a script Noto Sans lacks) | Chromium falls back; a warning on the upload names the characters |
| Component PNG without alpha, or under 20 % transparent | candidate marked failed: "no transparent background" |
| Component prompt names a person, a graphic or the style | refused |
| Scene over 2 MB | refused: "use `use` for repeats and components for things" |
| Scene uploaded, plan not updated (sha not in the plan) | `draw` refuses: "the plan's scene_svg names no uploaded scene" |
| Plan changed after upload | the rules run again at render from the stored file and the current plan |
| Chromium missing on the host | the worker fails the job with "Chromium is not installed (playwright install chromium)"; the API's `/api/meta` reports `chromium: false` |
| Chromium crash or frame timeout | browser restarted once, render retried once, then the job fails with the reason; nothing partial stored |
| Screenshot size differs from the film size | the job fails (the `size` code line) |
| Frame count differs from the plan | the `frames` code line fails, as today |
| ffmpeg fails | the job fails with ffmpeg's last lines, as today |
| Gemini unavailable or a read error | loop skipped; clip marked "unchecked"; never held |
| Gemini returns an invalid or rule-breaking SVG | that pass is dropped; the previous SVG stays; the pass still counts |
| The loop oscillates (fix A breaks B) | three passes at most; the best pass kept (fewest must failures) |
| Two workers render the same digest | the existing same-job check in `render_drawn` returns the first job |
| Eight renders at once | one browser per worker process; about 2 GB in all; the VM has 16 GB |
| A cue beyond the shot's end | the action never fires; a warning names it (as design/113) |
| A zero-frame shot | refused by the plan check, as today |
| Determinism | the same request twice gives byte-identical frames (tested) |
| Huge `use` repeats (thousands) | Chromium renders them; the 2 MB limit and the 120 s timeout bound it |
| The palette has colours the scene does not use | fine; only colours outside the palette are a line |

## 6. Failure modes outside the code

- Flash cannot edit SVG well: the sample shows it; the fallback is the Pro model for the fix call (a config value), then "read only, no fix" if neither works.
- Chromium's `--with-deps` on the VM needs root: a one-time step in the deploy note, run by SK or by me on SK's word.
- Transparent backgrounds from the image model have soft halos: the "clean edge" line catches the bad ones; a rejected component is retried with "harder edge".

## 7. Tests, written first

Server (`server/unit`, pure, no Chromium):
- `test_design117_p1_pure.py`: the component request lines and parents; the alpha code line (PNGs with and without alpha, 10 % and 30 % transparent); refusals (person, graphic, style).
- `test_design117_p2_pure.py`: the SVG rules, one test per refusal in §5 plus a valid scene that passes; the spec rule (figure present, figure missing, unknown size with a figure); the plan check with `scene_drawn` and `scene_svg` both given.
- `test_design117_p4_pure.py`: the sheet from fixture frames (count, tiling, timestamps present); the loop with a fake transport: all pass on pass 1; a fail then a valid fix then pass; a fail with an invalid fix; three passes and the best kept; no key.
- `test_design117_states_pure.py`: `states` on ids with `build` through a group's children; the existing design/113 state tests still pass against the shared module.

Server (`server/unit`, needs Chromium, marked `chromium`):
- `test_design117_p3_chromium.py`: `page_html` and `measure` (a text inside and one outside the safe area); `render` of a 12-frame fixture scene with a component image, a gradient, a filter and a build: frame count, size, a pixel of the component where it should be, the build's third child absent at frame 2 and present at frame 10; determinism (two renders, equal bytes); a crash simulation (the browser closed under it) recovers once.

Plugin (`plugin/tests`): `vw visuals scene --file` (upload, sha, size limit, missing file), `--download`; `image --kind component` argument passing; the procedure's new sentences load (`v2.json`); 3.9 parse.

Page: `node --check`; a fixture session with a drawn card in each state renders the sheet and the account (the existing page test pattern).

On this PC: ffmpeg and ffprobe are present; Playwright is not in the test venv. The build's first step (after approval) is `pip install playwright` and `playwright install chromium` into `%TEMP%w2venv`, so the `chromium` tests run here; they are skipped with a reason where Chromium is absent, like design/113's ffmpeg tests.

Run after the build: the full server suite, the full plugin suite, as always.

## 8. Not covered (until the sample)

- The look. No test can say the drawing is good; the sample on the VM (three VW-7 shots, components first) is the gate before deployment, when SK lifts the hold.
- Flash's SVG editing quality; Chromium's speed on the VM (an estimate: 250 frames in about 20 s).
- The image model's transparent backgrounds on these subjects.
- Resolve, the editor's package and everything downstream: unchanged, the clip is an mp4 as before.

## 9. Questions for SK (one at a time)

1. A drawing whose must lines still fail after three passes: hold it until the operator accepts it with a quote (as a take with a failed must is asked about), or mark it only, as today? Recommendation: hold; the loop has had its tries, and a quote records why the operator took it anyway.
2. Keep the primitive route (`scene_drawn`, `drawn.py`) alive beside the SVG route until VW-7 is done, then remove it in its own note? Recommendation: yes; VW-7's three drawn shots keep rendering and Revathi is not re-planning mid-run.
3. The fix call's model: Flash 3.8 (the analysis model, cheap) with the Pro model as a config fallback if the sample shows Flash cannot edit SVG? Recommendation: yes, Flash first, the sample decides.

## 10. Self-review (what changed between the first draft and this note)

- Dropped the server-placed size labels for SVG scenes: the planner writes labels in SVG; the spec rule checks they are there. One less mechanism.
- Dropped a palette refusal at upload (tints would be refused); the palette is a read line instead.
- Moved the text-box measurement into Chromium (`getBBox`), which is exact, instead of a Pillow estimate for SVG fonts.
- The loop runs inside the render job, not as a second job family, so the card never shows a half-checked drawing and the existing job plumbing is untouched.
- The old route stays: deleting it would re-plan VW-7 for no gain now.
- Components reuse `generate_image` and the picture check rather than a new path; the only new code is the transparent-background request, two lines and the alpha check.
- No new job tables, no new pages, no new plugin bookkeeping; two plugin flags and one command.
- The one real dependency added is Playwright with Chromium; everything else is Pillow, ffmpeg and Gemini, already there.

## 11. SK's answers (28 Oct 2026)

1. **Hold it.** A drawing whose must lines still fail after the loop's passes is held: selecting it needs a quote, recorded with the failed lines, as a take with a failed must is.
2. **Remove the primitive route.** The server is not deployed until every step of VW-7 is done, so nothing live needs `scene_drawn`. Amendments to the note: `drawn.py`'s Pillow drawing, `DrawnShape`, `DrawnLabel`, `Shot.scene_drawn`, `drawn_labels` and `drawn_needs` go; `DrawnAction`, `cue_seconds` and `states` move to the SVG route; a drawn shot carries `scene_svg` only; `render_drawn` and `process_drawn` have one path; design/113's E1, E2, E3 and E6 tests are replaced by design/117's (the fixtures that still apply, the cues and the states, are carried over); the procedure's primitive sentences are replaced by the SVG ones. Design/113's decisions that stay: data not code, the approved spec before a render, the brand font, the free render, the operator's verdict on the Takes step.
3. **Flash first.** The fix call uses the analysis model (Gemini Flash 3.8); `DRAWN_FIX_MODEL` in config names it, so the Pro model is one line away if the sample shows Flash cannot edit SVG. All three answered: "start the build, tests first, commit and push per rule, no deploy."

## 12. As built (28 Oct 2026, server 0.68.0, plugin 0.56.0; not deployed)

**P1 components.** `generate_image` takes `kind: component` for an object, material, process or technique element: it needs an approved style picture, adds it as Image 1 when the planner did not, appends `COMPONENT_BLOCK` to the prompt ("one <name> alone … on a transparent background"), adds `COMPONENT_LINES` ("one thing only", "clean edge") to the checklist, and the request carries `background: transparent`, which `process_image` passes to the image API on both generate and edit. `image_check.run_check` adds the code line `transparent background` (`alpha_line`: an alpha channel and at least 20 % transparent pixels) as a must for a component; a component gets no scene lines. The page lists components under their element.

**P2 SVG scenes.** `svg_scene.py` (new): `parse`, `view_box`, `check` (the rules of §3 P2, every problem named), `ids_of`, `children_of`, `members`, `texts_of`, `image_refs`, `action_problems`, `spec_problems`, `embed`. `visual_contract`: `SvgScene {sha256, actions}` as `Shot.scene_svg`; `svg_needs` (the scene named, the actions keyed inside the shot, the spec required when a claim carries a figure); `DrawnShape`, `DrawnLabel`, `DrawnScene`, `drawn_labels`, `drawn_needs`, `Shot.scene_drawn` removed. `visuals_stage.set_scene` (upload: the rules against the run's references and fonts, the file at `<run>/visuals/scenes/<sha>.svg`, `session['scenes']`), `scene_of` (download: the loop's fixed SVG when there is one). Routes `POST /visuals/scene`, `GET /visuals/scene/{shot}`. Plugin `vw visuals scene --shot S --file scene.svg` and `--download`.

**P3 Chromium render.** `drawn.py` rewritten: `font_file`, `cue_seconds` and `states` (now by element id, a build through a group's children) kept from design/113; `page_html` (the scene inline at the film's size, `@font-face` from data URIs, the pictures embedded, animation off), one Chromium per worker (`browser`, `reset`, `available`), `measure` (every text's box) and `outside` (the safe-area rule), `render` (PNG frames piped to ffmpeg, the sheet's frames kept), `frame_png`, `sheet_indexes`, `sheet` (Pillow tiles, the time under each). `render_drawn` builds the request from the uploaded scene: the pictures it places (approved), the style picture, the palette, the spec's sizes, the brand font with its family name (the file's stem). `requirements.txt` gains `playwright==1.64.1`. `/api/meta` reports `chromium`.

**P4 the loop.** `image_check`: `drawn_asks` (claims, relationships, every text as a label, the view, then `DRAWN_FIXED`: text whole, things look like their names, builds step, palette), `drawn_sheet_check` (one Flash read of the sheet with the style and the shot's pictures as references; JPEG or PNG by the bytes), `drawn_fix` (the model returns `{svg, changed}`; `DRAWN_FIX_MODEL` in config, Flash); `drawn_lines_check` (two frames) removed. `process_drawn`: the rules, the actions, the spec and the measured text boxes before any render (a failure names them); then up to `DRAWN_PASSES` = 3 of render → sheet → read → fix → rules on the fix; an invalid fix or a fix error ends the loop; a crashed browser is restarted once; the pass with the fewest must failures is kept (the later on a tie); stored: the mp4, every pass's sheet, the fixed SVG when a pass changed it; the result carries `check` (`lines`, `must_failed`, `best_pass`, `sheet_key`, `fixed_svg_key`, `passes` with what each fixed or dropped). `check_drawn` writes that record to `session['take_checks']` under the run's lock. `select_take` holds a drawn job whose must lines still fail until `notes` say why (answer 1). The page's take rows carry `sheet_url`.

**P5 the operator's view.** The drawn card shows the sheet under the clip, `drawnPasses` (each pass, what was fixed, what was dropped, and the hold notice), and the status line says "Held: …" when a line still fails. The procedure's two drawn sentences and the F19 fragment rewritten (the route for what must be exact, pictures for concepts, the hybrid; the scene upload and its rules; the component; the loop and the hold; `--download`).

**Tests.** `server/unit`: `test_design117_p1_pure` (6), `p2_pure` (26), `p3_states_pure` (7), `p3_chromium` (4, run here with Chromium in the test venv; skipped by name where it is missing), `p4_pure` (11), `p5_pure` (3); `svg_fixture.py`; `drawn_fixture.as_drawn` now gives `scene_svg`; design/113's E1, E2, E3 tests removed (their cue and state tests carried into p3), E6 adapted; design/114's drawn call moved to the sheet read. `plugin/tests/test_design117.py` (3). The full suites' results are in the commit's note.

**Held for the deploy (not done).** On the VM, once as root, before `deploy-server.sh`: `/opt/vw2/venv/bin/pip install playwright==1.64.1` then `PLAYWRIGHT_BROWSERS_PATH=/opt/vw2/browsers /opt/vw2/venv/bin/playwright install chromium --with-deps`, and `Environment=PLAYWRIGHT_BROWSERS_PATH=/opt/vw2/browsers` in `vw2-worker.service` (and `vw2-server.service`, for the meta flag); then the sample on the three VW-7 shots (components first) before any run depends on it.

**Not covered.**
- The look: the sample is the gate (§8).
- Flash's SVG editing and Chromium's speed on the VM: the sample.
- The image model's transparent backgrounds on these subjects: the sample; the alpha line catches a picture that is not a cut-out.
- No database-backed test; the loop and the routes are exercised with fakes.
- The page's drawn card is checked by its text and `node --check`, not in a browser; the first render on the VM is the look at it.
- A brand font's family name is taken as the file's stem; a font whose internal name differs renders in Noto Sans in Chromium (the rule accepts the stem). Named here; a run with a brand font tells.
