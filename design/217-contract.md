# design/217 step 0: the contract of the pictures screen (step 6) and of Claude's check

18 Nov 2026. Built from the approved release `design/_work/step6-release-requirements-18-nov.md` (Part 1, C1-C7, F1-F6, R1-R4, D1-D8 as recommended), the trial's build requirement (`ux1-mockup/step6-trial/step6-build-requirements.md`), the review (`design/_work/step6-review-18-nov.md`) and the unfinished patch `ux1-mockup/step6-trial/design217-wip-not-committed.patch`. The fixture of this contract is `server/unit/d217_pictures_round.json`: one round in exactly this shape. Where this text and the fixture disagree, the fixture wins and S corrects this text.

Two builders build against it in parallel: **P** (the page) and **S** (the server). Section 6 splits the files.

## 1. What is reused, what is new

Reused unchanged: the round document (`rounds/<round>`), the answers (`rounds/<round>/answers/<line>`, written by the page's `write()`), the small pictures (`pics`), the large pictures' links (`zoom`), `pic()` / `sized()` / `_with_pictures()`, `HOW`, `CAPABILITIES`, `ROUND_BYTES`, `page_refused`, `vw visuals page --record` → `page_record()`, the sets screen's chrome (rail, one count, end card, help, keys, Undo, "asks once").

New, named plainly:
- the layout `layout.kind = "pictures"`, its lines (section 3) and its words (`layout.words.pictures`, section 2.2);
- the folded list `layout.coming` (items being made or waiting for Claude's check);
- `video` on a drawn line: the page copy of the drawing's video, sent as a large file under a code in `zoom` only (no small picture, never in `pics`);
- the picture role `role` on every entry of a line's `pics` (`main`, `step`, `sheet`, `before`, `after`, `earlier`);
- Claude's check of step-6 pictures: `vw visuals pictures --looks [file]`, routes `GET`/`POST /api/runs/{run_id}/visuals/pictures/looks` (section 5);
- the rule list of a drawn graphic held by the server (C6, section 5.6).

## 2. The round

### 2.1 Top-level fields

| Field | Type | Meaning |
|---|---|---|
| `step` | str | `"Pictures and drawn graphics"` (the step's name; `page_record` uses it to pick the step-6 `then`) |
| `round` | str | `r<stamp>`, the document id in `rounds` |
| `how`, `capabilities`, `title` | as today | unchanged (`HOW`, `CAPABILITIES`) |
| `open` | bool | true when at least one line needs an answer |
| `summary` | str | one line for the old header, e.g. "8 to answer, 4 still being made or checked." |
| `note` | str | shown when nothing is open: "Answer what is ready, then say done in the chat." or `layout.words.pictures.nothing` |
| `say` | str | the one message the assistant posts with the link (section 2.4) |
| `preparing` | str | as today (`WORDS['preparing']`), counting pictures and videos to send |
| `lines` | list | the lines, in the order: questions, the style sheet, then film order (section 3) |
| `layout` | object | below |
| `pic_docs`, `zoom_docs` | map | as today, when a picture was sent again |
| `picture_batches`, `zoom_uploads`, `pictures_failed` | as today | added by `page()`; `zoom_uploads` also carries each drawn line's video page copy |
| `videos` | [{code, key}] | added by `page()` (S, build): each drawn line's video page copy (`v` + 12 hex, 960 px H.264), which the tool fetches as `zoom/<code>.mp4` and uploads with the large pictures; the page reads its link at `zoom/<code>` (or the document `zoom_docs` names when the pictures are offered again, as for a picture); never in the round document. A copy that cannot be made, or one over the page's file limit (15 MB, `OWN_PICTURE_MAX`), leaves `video.code` "" and `video.none` set |

`layout`:

| Field | Type | Meaning |
|---|---|---|
| `kind` | `"pictures"` | the page draws the pictures screen |
| `help` | [str] | the help panel's paragraphs |
| `coming` | [row] | the fold "Still being made, nothing to do", one row per item with no answer yet (section 3.7) |
| `words` | object | `page_words()`; the pictures screen reads only `words.pictures` |

### 2.2 `layout.words.pictures` (layout chrome; the page holds no words)

Keys and the fixture's text: `todo`, `coming`, `nothing`, `against`, `done` {act → tag in the rail: `answer`, `approve`, `again`, `fix`, `select`, `reject`, `plain`}, `undo`, `cancel`, `details`, `more` ("See all {n}"), `fewer`, `compare`, `stop`, `frames` ("Show its frames"), `video` ("Show the video"), `video_bad` (the video failed to play in the browser), `loading`, `missing`, `no_large`, `gate_wait`, `gate_bad` ("{pics}"), `words_need` (default refusal of an empty box), `left_one`, `left_many` ("{n}"), `left_note`, `end_head`, `end_note`, `end_foot`, `foot` ("{n} of {m} answered."), `foot_wait`, `foot_done`, `help`, `keys`, `close`.

The only substitutions the page makes: `{n}`, `{m}`, `{pics}` in these chrome words, and `{words}` in a button's `say` (the operator's own words). Nothing else is composed on the page. No amount of money anywhere (D1).

### 2.3 The end card

One row per line that needs an answer: `<line.name>: <the chosen button's say>` with `{words}` replaced, followed by ` (<words.pictures.against>)` when the line is answered against its check (section 3.8). Head `end_head`, `end_note` above, `end_foot` below. Unanswered lines: `left_one`/`left_many` + `left_note` (as `sEnd`).

### 2.4 `say` and `preparing`

`say` (S, `pictures_say(lines, coming)`, shaped like `sets_say`):
- `"{k} things need your answer:"` (`"1 thing needs your answer:"`), then one name per line `"\n- <name>"`;
- then, when `coming` is not empty, `"{c} more are being made or checked: they come to the page later."`;
- then `"Then say done here."`;
- nothing to answer: `"Nothing waits for you on the page now."` + the `coming` sentence when it applies.
The chat posts it unchanged (design/216). `preparing` is the existing sentence.

## 3. The lines

### 3.1 Fields common to every line

| Field | Type | Meaning |
|---|---|---|
| `line` | str | `l01`, `l02`, … (answer document id) |
| `key` | str | `pic:<item>` |
| `item` | str | the chat item id, content-stamped: `question:<id>`, `picture:<ref>:<sha10>`, `graphics:<shot>:<n>`, `take:<job>` |
| `kind` | str | `question` \| `style` \| `still` \| `steps` \| `drawn` |
| `state` | str | `open` (needs an answer); a line not open is not sent |
| `name` | str | the name in the rail and the heading (Space Grotesk) |
| `kind_words` | str | under the name: "A still", "The style sheet", … |
| `ask` | str | the question above the buttons |
| `pics` | [pic] | the pictures of the line, each with a `role` (3.2) |
| `buttons` | [button] | the answers (3.9) |
| `details` | [[head, [str]]] | behind "Details"; may be empty; cut first when the round is too large |
| `refused` | str, optional | the server's refusal of the last answer (from `page_refused`); the line stays open and shows it |

Lines of kind `style`, `still`, `steps`, `drawn` also carry `check` (3.8). Lines of kind `still`, `steps`, `drawn` also carry:

| Field | Type | Meaning |
|---|---|---|
| `where` | str | "In the film at 1:35.1 to 1:40.6 (5.6 s) · Gap 5, Strong enough for three storeys" (film-time format of the rest of the page) |
| `film_at` | str | the shot's start, "1:35.1": shown under the name in the list, after `kind_words` ("A still · 1:35.1"), as on the trial |
| `words_head`, `words` | str | "The words under it:" and the narration |
| `try` | str | "Try 2" when there were earlier tries, else "" (the main picture's label stays "The new picture": the try is said once, here) |
| `foot_head` | str | the head of the strip of footage and earlier tries |

### 3.2 A picture entry (`pics[]`)

As `pic(key, label, mark)` plus:

| Field | Type | Meaning |
|---|---|---|
| `code`, `label` | str | as today; `missing: true` when `page()` could not make it |
| `role` | str | `main` (the picture answered), `step` (one step of a graphic), `sheet` (a drawing's frame sheet), `before` / `after` (your footage, only ever shown beside), `earlier` (an earlier try, not used) |
| `faults` | [str] | `step` only: Claude's failed lines for this step, in full (a still's, the style sheet's and a drawing's are `check.faults`, sent once) |
| `check_head` | str | with `faults`: "Claude's check of step 3:" |
| `n`, `caption` | int, str | `step` only: its number and "Step n: on '<words>': <what appears>" |
| `cmp_cap` | str | `before`, `after`, `earlier`: the caption when shown beside the main picture |
| `why` | str | `earlier` only: "You said: …" (the rejection's notes, or the question's answer that sent it back) |

Order in `pics`: `before`, then the main picture or the steps (or the sheet), then `after`, then `earlier` (newest first). No `before` when the film opens on the gap; no `after` at its end. The footage is never the main picture. Server side, `_with_pictures` needs no change: every picture is in `pics`.

### 3.3 Kind `question` (a question of Claude about a made picture)

Extra: `from` (str, "The server asks this about a picture already made. Nothing is made until you answer."). `ask` is the question in plain words (no reference ids; S writes it per `fork`). `pics`: one `main` when the question is about a made picture, else empty. No `check`. Buttons: one per choice, 2 to 4, `choice` `c1`…`c4`, `act` `answer`, each `say` the result in plain words. A question whose waiting step is `references` is not on this screen (it stays in the chat).

### 3.4 Kind `style` (the style sheet)

Extra: `sub` (str). `pics`: one `main`. Buttons: `yes` "Yes, use this look", `no` "No, make another", `correct` "Correct it". Asked only when the plan has a graphic in steps (D5): otherwise S never makes or lists it.

### 3.5 Kind `still`

`pics`: `before`?, `main`, `after`?, `earlier`*. Buttons: `yes` "Yes, put it in the film", `no` "No, make another", `correct` "Correct it". Only the newest try is answerable.

### 3.6 Kind `steps` (a graphic in steps, 2 to 4)

Extra: `strip_head` ("The steps, in order: click one to see it large"). `pics`: `before`?, `step` × N (all shown side by side), `after`?, `earlier`*. Buttons: `yes` "Yes, use all N steps", then `correct:1` … `correct:N` "Correct n" (one per step, F2; the question above them already says they are steps, so the row fits one line at 1536 px). No "No". Four steps in a window under 700 px high are drawn as two rows of two, each step's own lines then only in the check line.

### 3.7 Kind `drawn` (a drawn graphic) and the `coming` rows

Extra on a drawn line:

| Field | Type | Meaning |
|---|---|---|
| `video` | {code, label, none} | `code`: the video page copy's code in `zoom` ("" when there is none); `label`; `none`: shown in its place when `code` is "" ("The video is not available here: these are its frames.") |
| `finish` | str | "Added by the server: soft grain and darker corners." or "" |
| `held` | str | why select needs a reason ("Its fact check did not pass: to select it all the same, say why.") or "" |

`pics`: `before`?, `sheet`, `after`?. The page shows the video looping and muted (D6), the sheet one click away (`words.frames`); with no `code`, or when the zoom link is missing or the video fails to play, the sheet takes its place with `video.none` or `words.video_bad`. The open rules (`check.faults`) are shown in full (`check.show = "all"`). Buttons: `select` "Select: use it in the film" (`needs_words` true when `held` is set, F3), `reject` "Reject" (needs words), `plain` "Take the effect away" (only when `finish` is set; no confirmation, D8).

`layout.coming[]` rows (no `line`, no answers, not counted):

| Field | Type | Meaning |
|---|---|---|
| `name` | str | the shot's title or "The look of the graphics" |
| `kind_words` | str | "A still", "A graphic in steps", "A drawn graphic", "The style sheet" |
| `state` | str | `making` (being made: a reference `generating`, a render job not ready) or `checking` (made, waiting for Claude's check, C3) |
| `note` | str | `making`: "Being made. It joins the list when it is ready."; `checking`: "Claude is checking it. It joins the list when it is checked." |

### 3.8 The check block (`check`)

| Field | Type | Meaning |
|---|---|---|
| `state` | str | `pass` \| `fail` \| `not_checked` \| `none` |
| `head` | str | the one coloured line (green pass, amber fail, grey not_checked/none), e.g. "Claude's check found 4 problems: <first fault>" / "Claude's check found nothing wrong" / "Not checked: Claude's check did not come within 30 minutes. Judge it by eye." / "Not checked: Claude could not open the picture. Judge it by eye." / "Fact check: passed. All 53 rules held, after 2 redo rounds." / "Fact check: not passed. 2 of 53 rules are still open after 2 redo rounds:" / "Not fact-checked yet." |
| `by` | str | who checked: "Claude looked at the picture against its list of 22 lines." / "A Claude checker that never saw the build judged 53 rules on snapshots of the video." / "" |
| `show` | str | `first`: the faults after the first behind `words.more`; `all`: every fault in view (drawn) |
| `faults` | [str] | the failed lines in full (steps: prefixed "Step n: ") |
| `passed_head`, `passed` | str, [str] | behind "Details"-style fold |
| `advice_head`, `advice` | str, [str] | the program's measured lines (light, fine detail, size, transparency, two steps alike) shown as advice, never a fault (C4, D2, R3); for a drawn graphic "What the checker saw" |

`state` meanings: `pass` and `fail` from Claude's recorded look (or, for a drawn graphic, from the fact check round of the take's project sha); `not_checked`: the look said `not_checked` or the time-out passed (C3); `none`: a drawn graphic with no fact check yet, or an older svg drawing with no server check.

**Against the check** (Part 1, "asks once"): a line is answered against its check when the chosen button has `sure` and was confirmed. The rail tags it `words.pictures.against`, the end card appends it. The page writes nothing extra; the server knows the check.

### 3.9 A button

| Field | Type | Meaning |
|---|---|---|
| `label` | str | the button's words |
| `choice` | str | written in the answer: `c1`…`c4`, `yes`, `no`, `correct`, `correct:<n>`, `select`, `reject`, `plain` |
| `act` | str | `answer`, `approve`, `again`, `fix`, `select`, `reject`, `plain` (the rail's tag `words.done[act]`; `approve`/`select` are the "yes" side) |
| `needs_words` | bool | a box opens; the answer is written only with words |
| `say` | str | what happens, in the end card; `{words}` replaced with the operator's words |
| `hint`, `go` | str | with `needs_words`: the box's placeholder and its send button |
| `prefill` | str | with `needs_words`: the box opens with this text (D3: Claude's failed lines, for the operator to send or change); "" for none |
| `need` | str, optional | the refusal of an empty box; default `words.pictures.words_need` |
| `sure` | {ask, go, back}, optional | asked once before the answer is written: on `yes` when `check.state` is `fail`, and on a steps `yes` when the program measured two steps alike (R3) |

### 3.10 The answer documents the page writes

Collection `rounds/<round>/answers`, doc id `<line>`, exactly as `write()` does today: `{key, item, choice, notes, at}`. `notes`: the operator's words (or "" ). Undo deletes the document. Nothing is recorded before done.

### 3.11 What each choice calls (S, `page_flow._pictures_answer` through the chat item's `_run`)

`page_record` gets a branch for keys `pic:`. It finds the chat item by `item` among the current `CF._waiting_items(ctx)`; not found = **stale** (listed, nothing recorded). A choice not on the line, or words missing where needed, is refused with the sentence named. Order: questions, the style sheet, then film order.

| Kind | Choice | Server function |
|---|---|---|
| question | `c<n>` | `V.answer(store, user, run, outputs, item, choices[n-1])` |
| style, still | `yes` | `V.approve_reference(store, user, run, outputs, ref_id, sha256, quote, conn)` (a still with a shot is placed; no `figure_repeat` call, C5) |
| style, still | `no` | `V.reject_reference(…, ref_id, '', quote)`: no reason stored, nothing added to "not this" or the library (F4) |
| style, still | `correct` | `V.reject_reference(…, ref_id, words, quote)` |
| steps | `yes` | `V.sequence(…, shot_id, [ids], quote)`; two steps alike is no longer a refusal (R3), it is advice and `sure` |
| steps | `correct:<n>` | `V.reject_reference(…, chain[n-1].id, words, quote)`; every later step is rejected too, with no reason (nothing reaches the feedback or the library, as F4), its rejection's `cause` "Made from a step that was corrected." shown with the earlier try, and made again from it (F2) |
| drawn | `select` | `V.select_take(conn, store, user, run, outputs, job_id, quote, notes, timing_notes, None)`: `notes` = the operator's words when held, else ""; never a note the operator did not give (F3); `timing_notes` = the words when shorter than its slot |
| drawn | `reject` | `V.review_take(conn, store, user, run, outputs, job_id, 'rejected', words, '', quote)` |
| drawn | `plain` | `V.motion_finish(…, shot, False)` then `review_take(… 'rejected', "made again without the effect, at the operator's word" …)`; `next` says the step's own sentence, never "the Takes step" (R4) |

After `--record`, `then` says first, when any step-6 picture waits for its look: `"{n} picture(s) wait for Claude's check: run `vw visuals pictures --looks`."`; then one of:
- `PICTURES_LEFT`: "{n} line(s) still wait for the operator on the page: write the new round to the page and give them the link again.";
- `PICTURES_WAIT`: "The pictures and drawings still being made are not ready. Wait for them (`vw visuals status --wait 900`), then run `vw visuals page`.";
- `PICTURES_DONE`: "Every picture and drawing is answered. Go on with `vw visuals next`: it gives the next decision.";
- with a refusal, `ROUND_REFUSED` first.
`ROUND_NEXT` loses "(the stills and the graphics are not on the page yet)".

When the step applies: `_plan_step` returns `pictures` when the reference round is complete (v2 round), no spec or drawing waits, and at least one step-6 item waits or is coming. An older film (round not v2) keeps the chat. A film mid-step in the chat moves to the page at its next item.

## 4. The chat says the same

`_waiting_items` builds each step-6 item's text and buttons from the same words as its page line (labels, `ask`, check `head` and `faults`). F1: the check lines come from Claude's look (`ref.look.lines`) and the program's lines (`ref.check.code`), never from `ref.checklist`. A bare No in the chat stores no reason (F4).

## 5. Claude's check of step-6 pictures (C1-C7)

### 5.1 Which pictures

Every reference of kind `style`, `keyframe` (a still), `state` (a step of a graphic), `component`, and every remade picture (`fix_of`, or a new try of the same slot), of a film whose round is v2. Not: sets (design/214 already), AI-video start/end images and takes (step 7), the svg drawn route (C7).

### 5.2 What the workers stop doing

- `visual_workers.finalize_image`: for these kinds, no `check_pending`, no `image_check.run_check` (no Gemini 3.8 Flash call, C1); it stores `check = image_check.code_only(…)` extended with the measured light, fine-detail and transparency lines, each marked `advice: true` (C4, D2), and `ready_at` (when the picture became a candidate).
- `approve_reference`: no `figure_repeat` call (C5); its question is a line of Claude's list.
- `request_fix` and `vw visuals fix`: retired (D3), refused with the old-ways sentence; "Correct it" is the one way.
- At the deploy: a candidate still `check_pending` is cleared and becomes due for a look; a candidate with an older Gemini check and no look is due for a look; approved pictures keep their approval.

### 5.3 The list the server builds (`ref_sets.check_lines(ref)`, extended)

Each line `{id, check, pass_when, say?}`, `id` = sha1 of its words, first 8 hex (a list that changes has other ids). Built from `image_check.lines_of(ref)` plus:

| Kind | Lines |
|---|---|
| still | `server_checklist` (the exact words and their place, sizes, material, what the shot claims, signs of use, place), the writer's checklist, `FIXED` (no other readable text, no real face from the footage, nothing extra), `SCENE_FIXED`; plus "No background figure is the same individual as one in <pictures>" when the scene has figures (C5) |
| step n | `_graphic_lines` for that step, `FIXED`; plus "Adds what the plan's step n names; the rest as step n-1" (n > 1) |
| style | the writer's checklist, `FIXED`, and fixed lines: the plan's palette, sample labels readable, a sample of the drawing language and not a scene |
| component | `COMPONENT_LINES`, `FIXED` |
| remade | the original's full list (not a reduced one), plus "The line it was made for now passes" and "Nothing else changed against the earlier picture" |

The light line is not in Claude's list: the program measures it (advice, D2).

### 5.4 The routes and the file

`GET /api/runs/{run_id}/visuals/pictures/looks` (`vw visuals pictures --looks`): `{pictures: [{ref, sha10, kind, name, shot_id, n?, key (the 1600 px copy), inputs: [{ref, role, key}], request, lines}], then, how}`. `how` holds the judging points and the file shape (as `LOOK_HOW`, one source; the helper file points to it).

`POST` the same route (`vw visuals pictures --looks <file>`, file `work/visuals/pictures/looks.json`):

```json
{"by": "assistant | helper",
 "pictures": [{"ref": "<id>", "sha10": "<first 10 of its sha256>",
               "lines": [{"id": "<line id>", "pass": true, "seen": "<one sentence, required with a fail and with a `say` line, at most 300 characters>"}],
               "not_checked": "<only for a picture that could not be opened: why, one line; then no lines>"}]}
```

Who answers: the assistant for up to 5 due pictures; above 5, `vw-picture-look` helpers (a copy of `vw-set-look`), about 5 pictures each (C2). `vw visuals next` and `status` name the pictures waiting, first thing.

### 5.5 Refusals (per picture; a refused picture records nothing, the others record)

Reuse the design/214 sentences with "picture" wording: `LOOK_LINE_OPEN` (a line skipped), `LOOK_LINE_UNKNOWN` (a line it does not know), `LOOK_LINE_WORDS` (a fail, or a `say` line, with no words, or words over 300 characters), `LOOK_NOT_CHECKED` (`not_checked` with lines), and a new `PIC_LOOK_GONE`: "{name}: it is not a picture waiting for its check now (made again, answered, or changed): list the pictures again (`vw visuals pictures --looks`)." Returns `{recorded: [ref], refused: {ref: message}, left: [ref], then}`.

### 5.6 Where it is stored, the time-out, the drawn graphic

- Stored on the reference: `ref.look = {who, at, sha256, lines: [{id, check, pass, seen}]}` or `{who, at, sha256, not_checked}`. The program's lines stay in `ref.check.code`. `check_summary` reads `look` for these kinds. A helper that stops half-way: the pictures it did not answer stay due (never marked passed).
- Offered: `waiting()` lists a picture only with a look recorded, or after `PICTURE_LOOK_MINUTES = 30` from `asked_at` (stamped the first time `looks_due` lists it or `waits_words` reports it, never from when it was made: a film paused overnight is not offered as not checked), then as `not_checked` with "Claude's check did not come within 30 minutes" (C3, F6). A look that arrives later and before the operator's answer replaces it.
- A candidate the model checked before the deploy (`check.lines` or `check.model`, no `look`, no `ready_at`) keeps that check: offered as before, its check line from those lines; only a picture still `check_pending` at the deploy goes to Claude. Its chat item keeps its id and answers.
- A component whose look fails (or could not be opened) stays a candidate and is named, with its failed lines, in the `then` of the looks route and in `next` / `status` / the page's record ("make it again …"); the program's advice lines never decide its approval.
- Rule 0, fork 4 (a parent approved with a failed line): on a v2 film the failed lines are Claude's (`V.parent_failed`).
- Meanwhile its row is in `layout.coming` as `checking`.
- C6: `motion_verdict` is held to the whole rule list of the project: the server keeps the rules of the brief per project sha (ids from their words, as `check_lines`), and refuses a verdict that skips a rule, names an unknown one, or fails one with no words (the same three sentences). "All N rules held" uses the real N.
- C7: the svg drawn route (one drawing file read by Gemini) and AI video's take check are unchanged.

## 6. The split: Builder P and Builder S

The files are disjoint. Neither edits the other's files. Both read this contract and the fixture.

### Builder P (the page)

Files: `plugin/pages/decisions.html`; `server/unit/test_design217_browser_pure.py`; `plugin/tests/test_design217_page.py`; the preview tool under `ux1-mockup/` (e.g. `ux1-mockup/step6-trial/preview217.html` or a script that renders the fixture). Nothing else.

Owns: **Part 1** on the page: the `pictures` layout and every kind of section 3; the fold of `layout.coming`; one count; the end card; "asks once" (`sure`); the `prefill` box (D3 on the page); the video loop with the sheet one click away and the fallbacks (D6); no amounts (D1 on the page); no confirmation on `plain` (D8); fits 1536 by 510 and 1900 by 830 with no scrolling for each kind, measured by its tests; **F1** shown on the page (check `head`, `faults`, per-picture `faults`); **F2** on the page (one "Correct n" per step); **F3** on the page (select asks for the reason when `needs_words`, refuses an empty box with `need`); **C3** on the page ("Claude is checking it" rows, `not_checked` line).

Builds and tests against `server/unit/d217_pictures_round.json` (it may copy and mutate it inside its tests, e.g. to add `refused`, drop the zoom link of the video, a steps line of 2 and of 4). The sets screen's code may be reused inside `decisions.html`.

### Builder S (the server)

Files: everything under `server/app`; the server unit tests (`server/unit/test_design217_*.py` except `test_design217_browser_pure.py`); `plugin/scripts` (the `vw` tool: `vw visuals pictures --looks`); `plugin/agents` (`vw-picture-look`); `plugin/commands`; the wording script; `server/procedures/v3.json`; versions (`config.py` server version, `plugin.json`, `PLUGIN_MIN_VERSION` raised so an older page is not used); the design note (`design/217-…md`) and the decision log; `design/35` (old ways: the Gemini step-6 check, the second Gemini call, the paid fix round, the bare "No" reason, retired).

Owns: building the round exactly as section 2-3 (`_plan_step` → `pictures`, `_pictures_page`, `pictures_say`, `layout.coming`, `layout.words.pictures`, video page copy in `zoom_uploads`, `ROUND_BYTES` cutting details first); `_pictures_answer` and the `then` sentences; the chat's items (section 4); **C1-C7**; **F1** (the check from the look, in the round and the chat), **F2-F6** (server side), **R1** (the pixel-size rule does not read words the server wrote), **R2** (the "centre" refusal follows the guidance), **R3** (two steps alike: advice and `sure`, not a refusal), **R4** (the three "Takes step" sentences); **D1** (no amount in any field), **D2** (light as advice), **D3** (fix round retired; `prefill` from Claude's failed lines), **D4** (no component line; Claude's check covers it), **D5** (style sheet only with a graphic in steps), **D6**/**D8** (the fields that make them possible), **D7** (bare No, no reason).

### Shared files

None is edited by both. `server/unit/d217_pictures_round.json` is frozen at this commit: if the shape must change, S changes it and this contract in one commit and tells P which field changed. P never edits it. `server/pagetests` is not touched in this release (P's browser tests stand in for it).

## Not covered by this contract

- The look's real token load (measured on the first film).
- Whether Claude's look catches small label letters and a mismatched face (a real film only).
- The exact frame at a cut for the footage pictures on older masters.
- Phone width, dark mode, step 7.
