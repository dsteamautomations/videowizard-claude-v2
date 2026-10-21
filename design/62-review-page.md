# design/62 — The review page: watch the film and decide by button

Status: proposed, 21 Oct 2026. SK chose this route (option 2) over typing slide labels in chat, and wants the interim (part A) in place for the run that starts today. One flow, two front ends (CLAUDE.md): every button calls the server function the vw tool calls.

## The problem

After the review film the operator answers every numbered slide by typing labels in chat: "1 KEEP, 2B KEEP, 2C DROP", about 20 to 25 labels on a nine-scene film, from memory, after watching the film somewhere else. One wrong letter records the wrong decision against the wrong slide and nothing catches it.

## Part A — interim, in the procedure text only (this run)

Master step 1 changes from "ask the operator, in one message, for an answer to every slide" to: ask with the question tool, one slide per question and at most four questions per message, in film order, each question carrying the slide label, the scene, the slide's own lines (clips and seconds, or the decision's question) and the allowed answers as buttons: scene and backup slides KEEP / REJECT / KEEP_WITH_EDIT, decision slides KEEP / DROP. A REJECT is followed by one question for the reason; a KEEP_WITH_EDIT by one for the shot and the frame trim. The answers go into out/decisions.json and `vw master decide --file` as today. Nothing is typed by label. Server: the step text (served by the server). Plugin: nothing; the question tool is already allowed by the guard. Test: the step-text test in plugin/tests/test_master_cli.py.

## Part B — the page

**Where.** `/runs/<code>/review`, linked from the run page from the options stage on and named by the vw tool (`vw options fetch` and `vw master slides` print the link, as `vw next` prints the voices page at the voice stage).

**What it shows.** Left: the review film of the current version, streamed from storage (a `/runs/<code>/film/<key>` route that answers 307 to the signed storage URL, which serves byte ranges, so the player seeks). Right: the slide list of the current version in film order: label, type (scene, BACKUP for #n, DECISION, BLANK), scene title, the slide's lines, seconds, and the buttons. Clicking a row seeks the film to that slide; as the film plays, the row whose slide is on screen is highlighted. The cue times come from the render plan the server already saves (`render-review-v<n>.json`: slates and items in order, each with its frames), summed in a pure function `slide_cues(plan, fps)`.

**Three states, same page.**
1. *Options stage, film rendered, not recorded.* The slide rows show, read-only, under the film; one box at the foot, "Approve these options", with the words field; the button calls `record_options` with the operator's words, exactly as `vw options record --quote` does. A film that is not rendered for the current version shows "The review film is rendering" with the job state, polling every 15 s (the page calls `status`).
2. *Master stage, decisions open.* Each scene or backup row has KEEP, REJECT, KEEP WITH EDIT; each decision row has KEEP, DROP; blank rows have none. REJECT opens a one-line reason field on the row (the server refuses without it); KEEP WITH EDIT opens shot, in and out fields with the server's own help text. Each click posts one action and the row shows the recorded answer, by whom, when; an answer can be changed by clicking another button (the server overwrites, as the tool does). A counter in the sticky top says "k of n answered; waiting: 3, 2B, 5", the same line `vw master slides` prints.
3. *All answered.* The foot says "All n answered. The assistant builds the master film from here" and names the chat command (`vw master build`). Building, rendering and the first-cut approval stay in chat in this design; the page does not take them on.

**Server.** `web.py`: `review_page` (HTML), `review_data` (JSON: run, stage, version, film key and duration, slides with answers, cues, render state), `review_act` (POST: `record`, `decide`; each calls `stage2.record_options` or `stage2.decide` through the same stage gate `_stage_run` applies, so the page can never decide at the wrong stage), `run_film` (307). `stage2/stage.py`: `review_view(conn, store, run)` (the page's data: `slides_view` plus the film, the cues and the render state), `slide_cues(plan, fps)`. `main.py`: nothing new; `vw master slides` and `vw options fetch` add `review_page_url`. `run.html`: the link. `templates/review.html`: the page, following voices2 (sticky top, zebra table, the footer status line, the theme switch from base). `static/style.css`: the review rules.

**Plugin.** `vw.py`: `review_page_url(code)` beside `voice_page_url`; `options fetch` and `master slides` print it; `vw next` names it at the options and master stages. Procedure: the master step says the page is the default place to decide; chat questions (part A) remain for an operator who prefers them. Both record through the same function, so an answer given on the page is visible to `vw master slides` at once and the other way round.

**Safety and edges.** Decisions on the page go through the same validation as the tool: a blank slide refuses, REJECT without a reason refuses, an edit is parsed by `_parse_edit`. A new proposal (version n+1) or a changed package invalidates the current version's decisions on the server already (`session['current'] = None` paths); the page reads the current version on every load and after every action, so a stale page shows the refusal and reloads. Only signed-in users; the run page link appears only when the run is at options or master. The page never calls a provider or spends money. No new tables: decisions live in the stage-2 session file as today.

**Tests first.** server/unit: `slide_cues` on a plan with two options, one decision slide and a blank (cue of each slide label equals the frames before its slate); `review_view` shaping on a faked session (render ready / not ready, the stage, the waiting list); the Jinja render check of review.html with each of the three states (the pattern test_voices_page2 uses). plugin/tests: `review_page_url`, the two commands printing it, the step text. server/tests (Docker): a page test with a real session, not run here.

**Not covered.** Docker tests; the page on an iPad (SK reviews on a Mac). The first live use is the new run's options stage.

## Order and deploy

Part A rides on the pending server deploy (0.20.5 carries L17; the step text makes it 0.20.6 if it goes after). Part B is its own release: server 0.21.0, plugin 0.20.0, built with tests first and a self-review before the deploy; the aim is to have it ready before the new run reaches the review film, and if it is not, part A carries this run.
