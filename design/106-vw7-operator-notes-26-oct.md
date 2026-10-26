# design/106 — VW-7 operator notes of 26 Oct: takes, drawing specs, and the References step

Status: proposed by Revathi, 26 Oct 2026, from operating VW-7 on servers 0.47.1–0.47.4. Checked against `main` at server 0.52.0. For SK's approval. Use the next free number if 106 is taken.

**Every change in this note is required.** None is optional or a nice-to-have. The builder implements all of them, or raises a conflict with Revathi before leaving any out. Every rule is for any film; VW-7 appears only as evidence.

**Already covered by later releases, so not repeated here:**
- Graphics runs and real pictures for real claims (design/103 G1, G2).
- The split per gap on the treatment (design/97 G3).
- Ambient motion in every take (design/101).
- A rejected take still showing "ready" (defect 30).

## 1. Takes step defects (VW-7, shot B01_S1)

| # | What happened | Required fix | Where |
|---|---|---|---|
| T1 | A new start picture, b6993f7a03203d2f5176efc6da93456a (made about 11:50 UTC, status `candidate`), never got a card on the visuals page. The B01_S1 card showed only the old end picture abb86e93, so the operator could not see or approve the new start. It was approved in chat at 11:55 UTC. | Every candidate picture of a shot appears on that shot's card as soon as it is retained. It replaces older candidates of the same role (start or end) in the card's main view, with the older ones folded. | the page's data view, `templates/visuals.html` |
| T2 | After the start was approved, the server did not make the end picture, although the request carried an end prompt (design/86 K1, `pending_end`). The reply said "the take for B01_S1 is the next step". The end had to be requested separately (bcbf1c5919cd6453fb394a6660d0b817). | Approving a start that carries `pending_end` always queues the end from it, from the page and from chat. The reply says "end image queued" with its job, and never names the take as next while the end is missing. | `visuals_stage` (approve), the act reply, `vw.py` |
| T3 | `vw visuals select --job 68d7f1d4-ffb7-4ab8-b4be-204ae39031dd --decision reject --notes … --quote …` did not reject the take. It ignored `--decision` and placed the take in the film at 0:00–0:05. `--decision` is accepted by every `vw visuals` subcommand (one shared flag list in `vw.py`), so `select` took it silently. | Each `vw visuals` subcommand refuses any flag it does not use, naming the flag. `select --decision reject` (or any `--decision` other than accept) is refused with "to reject a take, run `vw visuals review --job J --decision rejected --notes …`". The server's select never places a take when its words say reject. | `vw.py` (per-subcommand flag check), `visuals_stage.select_take` |
| T4 | — | VW-7's take placed by T3 is listed for the operator and removed on their words. | a one-off through `vw`, the operator's words; no database edits by hand |
| T5 | `vw visuals status --wait` returned at once because an old failed job (6f6de947, "Storage not reachable") was waiting for a decision. It no longer waited for the jobs still running. | `--wait` waits until the running and queued jobs end. It reports old jobs that need a decision once in its line, without ending the wait. | `vw.py` (status wait) |
| T6 | The end-picture check refused "the camera did not move" as a camera move. | The camera-move check matches only a move being asked for. Negations ("did not move", "stays still", "no camera move", "locked off") pass. | the end-prompt check (`library.check_prompt` or `visuals_stage`) |

## 2. Drawing specs are researched before the operator sees them

**What happened.** After the reference sheets, the operator was asked to approve 11 drawing specs:
- Nine listed parts and relationships but no sizes.
- Two listed a size as `unknown` (B02B_S1 cavity width, B01_S6 brick size).

The assistant then asked the operator to type the sizes, or to ask it to measure, or to approve as "illustrative, not to scale". The operator usually cannot give dimensions, and an "illustrative" drawing with wrong proportions is rework later. B02B_S1's spec even says "Facts: … rectangular cavities between … (observed, Footage 15694574, a0d773, 89e63)" beside "cavity width: unknown, no source". The clips to measure were known; only the measuring had not been done.

**What exists.** `visuals_stage.measure` reads sizes off approved footage frames (design/89 D2), and design/103 A5 asks for a real size, with source and status, on every person, object and material. Neither is run before a drawing spec is shown, and a spec can still reach the operator empty.

| # | Required fix | Where |
|---|---|---|
| D1 | **The planner researches; the operator approves the result.** Before a drawing spec is shown, every dimension it depends on is filled in from the sources, in order: the client's material; `measure` on footage frames (paid, announced, never asked); a standard or manufacturer figure from the web (one warning and yes covers every spec of the run); an approved reference image. Each value carries its source and status. | visuals steps in `v2.json`, the spec step, `validate_plan` |
| D2 | **Proportions are always specified, even on "illustrative" drawings.** "Illustrative" means no numbers are printed on the graphic, never that proportions are free. A spec of a real object always carries the ratios that matter (for example, a brick about 3 : 1.5 : 1; both walls the same thickness; the cavity about a third of the wall), sourced as in D1. | plan schema (`drawing_spec.proportions`), `validate_plan` |
| D3 | **`unknown` is allowed only after the sources were tried.** The spec records what was tried and why each failed, and the operator sees the risk in one line ("cavity width not found in the footage or a standard; drawn by eye"). | plan schema, `validate_plan` |
| D4 | **The operator is never asked to type dimensions.** They may correct a value; the default is the planner's sourced proposal. The "your words for these sizes" box becomes a correction box. | page, visuals steps |
| D5 | **One approval for all specs of the run,** shown as one table (drawing, part, value or ratio, source, status), with any `unknown` rows highlighted. | page, `vw.py`, one server function |
| D6 | **The plan check refuses** a spec whose dimension is `unknown` without a record of the sources tried, and warns on a spec of a real object with no proportions. | `validate_plan` |

On VW-7 the operator approved the specs as illustrative to keep testing. D1–D6 are required for every later film.

## 3. The reference round: a picture's note is easy to lose

**What happened.** In pass 2, a picked picture's note box appears only in the side panel, and only after the picture is ticked and opened (`p-note`: "Tick it to add a note"). The words box at the foot beside Done looks like the place for notes, but it holds the pass's words. Done ends pass 2 at once. So a note typed at the foot never reaches the picture or its sheet prompt.

| # | Required fix | Where |
|---|---|---|
| N1 | A note field under every ticked picture in the grid, not only in the side panel. | `templates/visuals.html` |
| N2 | The foot's box is labelled "words for the whole pass", with a line saying that picture notes go under each picture. | `templates/visuals.html` |
| N3 | Done first shows a summary ("1 picture ticked, 0 notes: finish pass 2?") with Back and Finish. | `templates/visuals.html` |
| N4 | Notes stay editable after Done, until the element's sheet is generated, and the sheet prompt uses the latest notes. | `visuals_stage` (picks), page |

## 4. The References step: the sheet first, the rest folded

**What happened.** design/97 R1 opens a sheet waiting for approval in the side panel, and R2 folds everything once it is approved. But while the sheet waits, the element's main column (`renderReferences`, the branch for an element without an approved sheet) still lists every footage frame, the search box and all the Google results, with the sheet last. Once picks are saved, the unpicked results no longer matter.

| # | Required fix | Where |
|---|---|---|
| R1 | Once a search has saved picks (or "nothing fits"), its unpicked results and the search box fold behind "show all (n)". | `templates/visuals.html` |
| R2 | Whenever a sheet exists, waiting or approved, it comes first in the element's column. Below it are only the pictures it was made from, then the folded rest. | `templates/visuals.html` |
| R3 | The same order in the reference round's pass 2, once Done is pressed. | `templates/visuals.html` |

## Order

1. **T1–T6** (defects, with T4 for VW-7).
2. **D1–D6.**
3. **N1–N4 and R1–R3.**

## Tests first

- T1: a new start candidate shows on its shot's card, with the older candidate folded.
- T2: approving a start with `pending_end` queues its end, from the page and from chat, and the reply names the end job.
- T3: `select --decision reject` is refused naming `review`; an unknown flag on any `vw visuals` subcommand is refused naming it.
- T5: `--wait` keeps waiting while a job runs, even with an older job needing a decision, and names that job once.
- T6: "the camera did not move", "stays still" and "locked off" pass the camera-move check; "the camera pans left" is caught.
- D1–D6: a spec reaches the operator only with every dimension sourced or marked `unknown` with its tried sources; a spec of a real object without proportions warns; the spec table renders as one approval.
- N1–N4: a ticked picture shows its note field in the grid; Done shows the summary; a note edited after Done reaches the sheet prompt.
- R1–R3: an element with saved picks folds its unpicked results; a pending sheet renders first.

## Not covered

- server/tests (Docker).
- How well `measure` reads small sizes such as a cavity width from handheld footage. The operator's approval of the spec table is the backstop.

## As built: T1 to T6 (builder, 26 Oct 2026; SK: implement and commit, do not deploy)

Server 0.53.0, plugin 0.47.0. Committed, not deployed.

- **T1 and T2 had one cause.** The new start b6993f7a was made as an edit of the old start 511c79e0. The server and the page read "a keyframe made from a keyframe" as an end image. So the page showed it as B01_S1's end, and the server allowed no end prompt with it, so approving it queued nothing and named the take.
  - A keyframe request may now say its `role` (start or end); `vw visuals image` takes `--role`, or `role` in a file row. Without it, the rule stays as before.
  - Every new keyframe stores its role, and the page reads it.
  - The Takes card shows the latest start and the latest end, and folds the earlier pictures ("n earlier pictures").
  - Approving a start with `pending_end` replies "end image queued (job …)" with the job, never naming the take.
- **T3:**
  - Every `vw visuals` subcommand refuses, by name, a flag it doesn't read, before anything is sent.
  - `select --decision …` is refused, naming `vw visuals review --job J --decision rejected`.
  - The server's select refuses words that say reject.
  - The 124 `vw visuals` commands in the procedure, the chat guide and the plugin's own lines all pass the new check.
- **T4: nothing to do.** Take 68d7f1d4's last review is "rejected", and a rejection takes a selected take out of its shot. B01_S1 now holds 68ec7cc9 ("Selected by SK").
- **T5:** `status --wait` waits while jobs run or are queued, and names old jobs needing a decision once in its line. An older test that encoded the old stop-at-once rule is updated to the new rule.
- **T6:** the camera-move check (`camera_move`) skips a negated move: "did not move", "doesn't move", "stays still", "no camera move", "locked off".
- **Tests:**
  - `server/unit`: 453 passed, 6 of them new in `test_design106_pure.py`.
  - `plugin/tests`: 271 passed, with the 3 known Windows-only failures.
  - A bug the older tests caught while building (the role written into the caller's request) is fixed.

## As built: D1 to D6 (builder, 26 Oct 2026)

Server 0.53.0, plugin 0.47.0. Committed, not deployed.

- **D1:** the procedure's plan step says to research a spec before it is shown. The sources come in order: the client's material; `measure` on footage frames (announced, never asked); a standard or maker figure (one warning and one yes for the run); an approved picture.
- **D2:**
  - `drawing_spec.proportions` (a list of the ratios that matter);
  - a spec without it gets the warning `spec_proportions_missing`;
  - the table shows each proportion as a "ratio" row.
- **D3:**
  - `Dimension.tried` records the sources tried and why each failed;
  - an unknown row in the table carries its risk line, e.g. "cavity width not found (…); drawn by eye";
  - the page highlights it.
- **D4:**
  - a spec is approved without words, as "Approved by SK";
  - the old "your words for these sizes" box is now a correction box (`correct_spec`, `vw visuals spec --shot S --notes "…"`);
  - a correction waits for the assistant, and the next approval clears it.
- **D5:**
  - `approve_specs` approves every spec still waiting in one call: `vw visuals spec` with no `--shot`, or "Approve all specs" on the page;
  - the Pictures step opens with one table of every spec still to approve;
  - the waiting list has one item, "Drawing specs · n to approve".
- **D6:** the plan check refuses an `unknown` size without `tried`.
- **No re-acceptance:**
  - `proportions` and `tried` stay out of the gap digest;
  - an old spec keeps its spec digest (absent stays absent);
  - VW-7's 18 and VW-9's 8 accepted gaps keep their digests.
- **Effect on runs in progress:** VW-7's and VW-9's current plans are refused if resubmitted until their unknown sizes record `tried` (VW-7: B01_S6's brick size; VW-9: B01D_S1's brick sizes). The assistant fills that when it next revises a plan.
- **Tests:**
  - `server/unit`: 462 passed, 9 of them new in `test_design106d_pure.py`.
  - Older expectations were updated to the new rules: the SPEC fixture gains `tried`; approval needs no words; the waiting label is now one item; the plugin's spec posts with no words.
  - `plugin/tests`: 272 passed, with the 3 known Windows-only failures.

## As built: N1 to N4 and R1 to R3 (builder, 26 Oct 2026)

Server 0.53.0, plugin 0.47.0. Committed, not deployed.

- **N1:** a note field sits under every ticked picture in the round's grid. A note typed there is the one saved with the pick.
- **N2:** pass 2's foot says "Picture notes go under each ticked picture", and its box is "words for the whole pass (optional)". The box was gone since design/99; it is back, labelled.
- **N3:** Done shows "n pictures ticked, k notes: finish pass 2?" with Back and Finish. Nothing is sent before Finish.
- **N4:**
  - `note_reference` changes a saved picture's note until its element has a sheet (a rejected sheet does not count);
  - on the page, the panel holds the note box and "Save the note"; in chat, `vw visuals note --ref R --notes "…"`;
  - status gives every reference its latest note, for the sheet prompt.
- **R1:** once a search has saved picks or "nothing fits", its results and the search box fold behind "show all (n)".
- **R2, R3:** whenever a sheet exists, waiting or approved, it comes first, then "Made from" its sources, then the rest folded. Pass 2 after Done is the same view.
- **D, added from the browser check:** a spec with no size and no proportion shows in the specs table as a highlighted "no size or proportion given" row, never silently. On VW-7 that is 9 of its 11 specs.
- **Browser check (local copy with VW-7's page data):**
  - the round reopened at pass 2: tick, the note in the grid, Done's summary, Back, and Finish posting the note;
  - References: the sheet first with "Made from" for all 12 elements, the search folded;
  - the panel's note box shown only while no sheet exists, and saving;
  - the specs table with one approval and a correction;
  - no script errors.
- **Tests:**
  - `server/unit`: 466 passed, 4 of them new in `test_design106n_pure.py`.
  - `plugin/tests`: 272 passed, with the 3 known Windows-only failures.
