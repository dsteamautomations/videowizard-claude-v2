# 44 — Stage 8 (master and first cut) improvements: requirements (approved by SK 18 Oct 2026, implemented the same day)

Source: the stage 8 review run with the stage review prompt on 18 Oct 2026 and SK's decisions on its 5 findings, plus SK's numbering change given with 8.1. Measured on VW-3: 21 answers issued as 21 tool calls; the master render 6 min 39 s at 1080p and a 139 MB download; the master and first-cut approvals 5 s apart. Nothing here makes a paid call. No run is in flight at options or master; VW-3 is past the first cut, and its stored slides keep their old numbers (they are never shown again).

## Decisions carried from the review
- Slides are numbered the way the operator chooses: running numbers for scene options and backups only; the slides inside an option take its number and a letter (8.1, SK).
- `vw master slides` shows what still needs an answer; `vw master decide --file` sends all answers at once (8.1).
- `vw master status --wait N` (8.2).
- The master film renders at 1280×720 with the fast preset; the sound is unchanged (8.3).
- One approval: `vw master record` needs the watched-and-listened words and records the first cut too (8.4).
- The REJECT message, the swap sentence and the edit help are corrected (8.5).

## A. Slide labels (8.1, SK's rule)

| Slide | Label | Example slate line 1 |
|---|---|---|
| a scene's first option | the next running number | `#2 \| Scene 2: Laying the first course \| 57.2 s \| 7 shots` |
| the scene's backup | the next running number | `#3 \| Scene 2: Laying the first course \| BACKUP for #2 \| 57.2 s \| 6 shots` |
| a blank inside option n | n plus the next letter, in the option's event order | `#2A \| BLANK \| Scene 2 \| 12.4 s` |
| a decision inside option n | n plus the next letter, in the option's event order | `#2B \| DECISION \| Scene 2` then the question |

So the operator chooses between 2 and 3, and answers "2 KEEP, 3 REJECT, 2B DROP". Letters run A, B, C … over the blanks and decisions of that option together, in film order; blanks keep a letter so they can be named but need no answer. Numbers are not zero-padded. The corner label on footage is `#2`, and `#2B DECISION` on a placement behind a decision slide. The large number on a slate accepts the letter (`#2B`).

Where the label lives: `slides.py` sets `no` to the label string (`"2"`, `"2B"`) and keeps `number` (the running integer of the option the slide belongs to); `review_items` and the corner labels use `no`; `decide` takes the label as a string (an integer from an older plugin is its decimal string; `#` and lower case are accepted and normalised); decisions are keyed by the label; `build_master` names slides by label in every message; `swaps` carry labels.

## B. Server changes (`server/`)

| # | What changes | Why | Where |
|---|---|---|---|
| 8.1 | Labels as in §A. `GET /api/runs/{id}/master/slides` returns every slide of the current version: `{slide, type, scene, question, seconds, needs_answer, answer: {action, note, edit} or null}`, with `answered` and `waiting` (the labels still needed). `DecideBody.slide` becomes `str` (an `int` is accepted and converted); `option_number` stays for the oldest plugin. | The operator's way of naming slides; a view to ask and resume from. | `stage2/slides.py`, `stage2/stage.py` (`decide`, `build_master`, new `slides_view`), `main.py` (`DecideBody`, one GET) |
| 8.3 | `render_film` renders `review` and `master` on the 1280×720 timeline with the fast preset (the table `FILM_SIZE = {'review': …, 'master': …}` replaces `kind == 'review'`); the master keeps its loudness pass and `record['mix']`; the codec line names the size and the kind. Assembly is untouched. The master summary's `resolution` stays the plan's timeline (1920×1080, what assembly builds to); the film's own size is in the record's codec line. | Watched once, never delivered. | `stage2/render.py`, `render_jobs.py` (no change) |
| 8.4 | `record_master` refuses unless the quote contains both "watch" and "listen" (the first-cut rule, design/17 A50); after creating the master output it creates the first-cut output from it (the same summary and file as `record_first_cut`), and answers `first_cut_output` and `next: 'visuals for each gap' or 'assembly'`. `record_first_cut` stays for a run whose master was recorded before this change. | One question for one film. | `stage2/stage.py` `record_master` |
| 8.5 | `decide`: REJECT without a note → "REJECT needs the operator's reason (--note); it stays with this run's decisions." | 7.5 made the old text untrue. | `stage2/stage.py` |
| — | `SERVER_VERSION` 0.10.0 → 0.11.0. | | `config.py` |

## C. Plugin changes (`plugin/`)

| # | What changes | Why | Where |
|---|---|---|---|
| 8.1 | `vw master slides`: prints the server's list; the line says "k of n answered; waiting: 3, 2B, 5". `vw master decide --file out/decisions.json`: a list of `{slide, action, note?, edit?}`; sent in order, one request each; on the first refusal the tool stops and answers `{recorded: [...], refused: {slide, message}, remaining: [...]}` with exit 2; on success `{recorded: [...], decided, of}`. `--slide` is passed as the label (`#` stripped, upper case). | One call for all answers; clean resume. | `vw.py` `cmd_master`, parser (`--file` exists on options; added to master) |
| 8.2 | `vw master status --wait N`: the loop from 7.2 moved to `wait_for_film(run, film, wait_s)` and used by both commands; the line names the master film. | One turn per render. | `vw.py` `cmd_options`, `cmd_master`, parser (`--wait`) |
| 8.4 | `vw master record --quote` prints "Master and first cut recorded; next: …" from the answer. `vw first-cut record` unchanged. | | `vw.py` `cmd_master` |
| — | `plugin.json` 0.9.0 → 0.10.0. | | `.claude-plugin/plugin.json` |

## D. Procedure text (`server/procedures/v2.json`)
Master `steps`:
- Step 1: "Run `vw master slides` and ask the operator, in one message, for an answer to every slide it lists as waiting, by label: scene and BACKUP slides (1, 2, 3 …) KEEP, REJECT (with their reason) or KEEP_WITH_EDIT; DECISION slides (2B, 5A …) KEEP or DROP; BLANK slides need none. A scene's backup is the next number, so the operator chooses between 2 and 3. Write their answers to out/decisions.json as [{slide, action, note, edit}] and run `vw master decide --file out/decisions.json`; if it stops at a refusal, fix that answer and run it again (recorded answers are kept). For KEEP_WITH_EDIT the edit is in the shot's source frames: a frame is 1/25 s on the timeline; the shot's source frames and usable window are in the package row (`vw options show --option n` prints the option); turn 'trim the start a little' into about +12 frames and say what you did."
- Step 2: "`vw master build` audits collisions (it swaps to the scene's other option when that one is clean: say every swap to the operator, from which slide to which and why), validates edits and builds the fresh master; `vw master render`, then `vw master status --wait 600` and report its line until the film is ready; `vw master fetch`; let the operator watch out/master.mp4 and listen to it. Ask one question: did they watch it and listen to it, and do they approve it as the first cut? Their reply must say both; `vw master record --quote "<their reply>"` records the master and the first cut together. Rejection notes stay with this run. When a note states a preference that should hold for this client's future films, propose one line and, on the operator's yes, `vw master rule --add "<line>" --quote "<their yes>"`."
- Step 3 unchanged.
First cut `steps`, step 1: "Already recorded with the master's approval. If `vw next` still shows first_cut (a run approved before design/44), ask the one question (watched and listened, approved as the first cut) and `vw first-cut record --quote "<their reply>"`."
Options prompt, SLIDES paragraph: "They are labelled in film order: a scene's option and its BACKUP take the running numbers (#2, #3); the blanks and decisions inside an option take its number and a letter (#2A, #2B). The operator answers by label." vw.md's options and master paragraphs follow the same wording (the example `--slide n` becomes `--file out/decisions.json`, labels like 2, 3, 2B).

## E. Unstated but expected
- A 0.9.0 plugin against the 0.11.0 server: `--slide 2` still works (the label "2"); only the inner slides' names changed, and no run is at master.
- Old stored slides (VW-3) keep integer numbers; nothing reads them again except `vw options status`, which shows the session as stored.
- `decisions.json` may hold a subset; answers already recorded are not resent unless listed again (a listed one replaces the earlier answer, as today).
- The master film at 720p is still the hash-bound first cut; assembly's film and the Resolve segments are made from the plan at 1080p, as before.
- `record_master` with a quote lacking the words is refused before anything is written; nothing half-recorded.
- The first-cut stage remains in the stage table and its cap; `next` moves to visuals or assembly as soon as both outputs exist.

## F. Edge cases
| Case | Expected |
|---|---|
| scene 1 option with a blank and a decision, then its backup, then scene 2 | labels 1, 1A (blank), 1B (decision), 2 (backup for 1), 3 |
| `vw master decide --slide '#2b' --action DROP` | normalised to 2B |
| `--slide 1A --action KEEP` (a blank) | refused: "#1A is a blank … needs no decision" |
| `--slide 7` when the film has 1 to 5 | refused naming the labels that exist |
| decisions.json with 2 KEEP, 3 REJECT (no note), 1B DROP | 2 recorded, stops at 3 ("needs the operator's reason; it stays with this run's decisions"), exit 2, remaining [1B] |
| run again with the note added | 3 and 1B recorded; `decided` = 3 of 3 |
| `vw master slides` after that | waiting: [] ; every answer shown |
| build with both 2 and 3 kept | refused "both options kept (#2 and #3)" |
| build swaps scene 2 to its backup | `swaps: [{from: '2', to: '3', because: sub-clip}]`; the step says to tell the operator |
| `vw master status --wait 600` | same lines as the review film, naming the master film |
| master render | 1280×720, codec line says "master, made at this size", `mix` measured |
| `vw master record --quote "yes"` | refused: must say watched and listened |
| `vw master record --quote "watched and listened, yes"` | master and first-cut outputs recorded; `vw next` → visuals (gaps) or assembly |
| `vw first-cut record` after that | records again (history), harmless; the steps no longer ask for it |

## G. Tests (written first)
Layer one, `plugin/tests/test_master_cli.py` (new): `decide --file` sends in order, stops at a refusal with recorded/refused/remaining, exit 2; success answer; `--slide '#2b'` posts "2B"; `slides` prints the waiting line; `status --wait` follows the master film (ready, failed, expiry); `record` prints the first-cut line; the master and first-cut steps and vw.md carry the labels, `--file out/decisions.json`, `--wait 600`, "watched" and "listened", "say every swap".
Layer one, `server/unit/test_stage2_pure.py` extended: `SL.slides` labels for the fixture document (1, 1A, 1B, 2, 3); `review_items` corner labels (`#1`, `#1B DECISION`); the slate head regex accepts `#2B`; `render_film('master', …)` at 1280×720 with `mix` measured; the decide label normalisation helper.
Layer two, `server/tests` (Docker): `test_stage2.py` and `test_exact_match.py` end-to-end: slide labels in the propose answer; decide by label and by file; `GET master/slides`; build messages with labels; master record requires the words and records the first cut (one `vw next` → visuals); `test_stage3.py` run_until_assembly uses the new record wording and drops the first-cut call.

## H. Not covered
- `server/tests` cannot run on this Mac; compile check only until a Docker machine runs them.
- The 720p master's render time is measured on the next live run.
- How the operator takes to the letters is seen on the next run.

## I. Deploy order
1. Server (`deploy-server.sh`, workers restart): tell SK first.
2. Plugin (`deploy-plugin.sh`); the operator restarts Claude Code.
3. design/35: a row.

## J. Estimate
Server with tests: a day (the labels touch slides, decide, build, render items and every message). Plugin with tests: half a day. Deploys: an hour.
