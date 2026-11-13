# Stage review: VW-23, intake

13 Nov 2026. Read-only review. Nothing was changed. Uncommitted working note.

Run: VW-23, "Filler Slab Technology - Benefits and Construction Process", client C-086 (VK Nardep), machine `Uma-laptop-14605d`, server 0.97.0, instruction version 3.

Evidence: `vw2_log` (3 rows for the run so far), the server's request lines 04:20 to 04:33 UTC, `vw2_jobs` (none), `vw2_defects` (none in the window), `server/procedures/v3.json` (the intake step as served), `server/app/core.py`. No operator stage note was pasted.

## Timeline

| UTC | IST | What the server saw | Answer |
|---|---|---|---|
| 04:26:06 | 09:56:06 | `POST /api/runs` from Uma's laptop | 401, not signed in |
| 04:26:07 to 04:27:23 | 09:56:07 to 09:57:23 | connect, sign-in page, sign-in, approve the laptop | 200 |
| 04:27:30 | 09:57:30 | run created, claimed, next step read | 201, 200, 200 |
| 04:28:01 | 09:58:01 | intake instruction fetched (`vw stage intake prepare`) | 200 |
| 04:28:37 | 09:58:37 | run read again | 200 |
| 04:30:23 to 04:30:26 | 10:00:23 to 10:00:26 | run read, 3 files signed and receipted, intake recorded with "Yes, title 2" | 201 |
| 04:31:04 | 10:01:04 | category recorded: "documentary-explainer (Recommended)" | 200 |
| 04:31:11 | 10:01:11 | brief instruction fetched | 200 |

## A. Restrictions someone set

1. **Sign-in before a run can start.** 04:26:06 UTC (09:56:06 IST), once. `POST /api/runs` answered 401, then the laptop was connected through the browser. Cost: 84 seconds, once per laptop. The reason holds. It helped. No change.
2. **The category must be chosen by the operator, no default.** design/137; `core.py:334` "no default category; the brief waits for the operator's choice"; step 6 of intake: "The brief waits for it; never assume one." Fired at 04:31:04 UTC (10:01:04 IST). Cost: one extra turn, 38 seconds. The reason (every category of film, not documentaries only) holds. But it only slowed this stage: the last six runs of this client all recorded `documentary-explainer`, three of them by the "(Recommended)" button. Proposed change: ask it in the same question as the title (see D).
3. **Title required at record.** Step 5: "The title flag is required: record refuses without it." `core.py:364`. It did not refuse here. It shaped the work: the title question cannot be skipped. Reason holds (the run list needs a name). No change.
4. **Three attempts at recording the stage.** `"cap": 3` in the procedure, counted in `vw2_attempts` (`core.py:301`). One attempt used. Did not bite. No change.
5. **Removal by line number only.** Prompt origin "v1 VW-INTAKE-0.4.0 (ported verbatim 14 Oct 2026)". The assistant names lines to remove and never retypes speech. Reason holds (SK's exact-match rule). Shaped the work, did not slow it.
6. **Titles: up to three, 8 to 70 characters, no duration, platform, aspect ratio, tone word or client name.** Same origin. Shaped the titles offered. Not measurable here: I cannot see the three titles offered, only the one chosen.
7. **"Paste the full cleaned script only when it is under 40 lines or the operator asks."** Step 4. A fixed number. I cannot see whether it applied (the script's length is not in the log).

## B. Words in the prompt that restrict

1. **Examples from one older film.** "Scene 3: Why Choose CSEBs?", "Brick kilns emitting smoke", "Close-up of finished CSEB blocks", "Typically, the mixture contains: 50% sand, 20% clay". All from a compressed-earth-block documentary. Effect in this run: none visible. Risk: for an advertisement or a social clip the examples do not show what a non-script line looks like. Looser: one example per kind from two different film types, or no project named.
2. **The title example sets a pattern.** "Name the SUBJECT and the DELIVERABLE - \"Compressed Earth Blocks - Documentary Explainer\"". Earlier titles of this client follow it word for word: "Rat-Trap Bond Masonry - Documentary Explainer v9" (VW-22), "… - Short Explainer" (VW-19). VW-23's chosen title did not. Looser: "name the subject and what the film is" with no fixed example, or examples from three categories.
3. **"Clients rarely send a bare script. They send a plan: scene headings, durations, lists of visuals…"** Assumes a documentary plan. A two-column advertisement script or a shot list is not described. Looser: "The document may be a bare script or a plan around one."
4. **Capitals and repetition.** "YOU NEVER REWRITE A LINE. NOT ONE CHARACTER.", "THE RULE THAT MATTERS MOST - WHEN IN DOUBT, KEEP IT", and the same rule stated three more times. This is the older-model habit SK's rule of 2 Nov asks to remove. It stops nothing wrong, but it also stops the assistant from pointing out a clear typing mistake in a spoken line. Looser: state the rule once in plain case, and add "list any line that looks mistyped in `notes`; do not change it."
5. **"never assume one"** (the category). See A2.

## C. Steps that failed or were done again

1. **`POST /api/runs` 401**, 04:26:06 UTC (09:56:06 IST), once. The request reached the server. Cause: the laptop was not yet signed in. Label: our rule, working as intended. 84 seconds.
2. **The run was read three times** (04:28:01, 04:28:37, 04:30:23 UTC). Each of prepare, the middle step and record reads the run. Not a failure. No cost worth counting.

No refusal, no rejected check, no job, no retry, no defect.

## D. Getting the operator's input faster

| # | Question | Answered at | Wait | Mark |
|---|---|---|---|---|
| 1 | Client and picture AI (at `vw start`) | before 04:27:30 UTC | not visible | The last eight runs are all C-086, `openai`, `motion`. Could be offered as "same as last run". |
| 2 | Which title, and approve the cleaned script? | 04:30:23 UTC (10:00:23 IST), "Yes, title 2" | at most 106 s | Already one question for two things. Good. |
| 3 | Which category? | 04:31:04 UTC (10:01:04 IST), "documentary-explainer (Recommended)" | 38 s | Could be clubbed with question 2. The assistant has already read the script when it asks for the title. Could also be predicted from the client's last runs. |

Nothing was asked twice. Proposed change: one question at the end of intake: title, approval and category together, each with a recommended answer to click.

## E. Execution that can be better

1. **The category is a separate turn after record.** 38 seconds and one more message. Club it (A2, D3).
2. **Intake leaves one log line.** `vw2_log` has only the record (04:30:26). The prepare, the preview and the questions are not logged. The stage's start is visible only in the request lines.
3. **The category is logged under stage `brief`**, though it is step 6 of intake. A stage query on the log puts it in the wrong stage.
4. **The run does not say who operated it.** `owner_name` is "SK" and the category is recorded "by SK", but the machine is Uma's laptop. Guess: Uma signed in with SK's account. Reviews across operators cannot be split by person.
5. **No waiting on the machine.** The longest gap with the server idle was the operator reading the script (at most 106 s).

## F. Known weak spots

1. Rounds to pass a check: none. Recorded on the first attempt.
2. Refusals that are really questions: no refusal. The category question is the same kind of thing (D3).
3. Connection errors and timeouts: none seen. Every request reached the server.
4. Provider failures: none. Intake uses no provider.
5. Blank searches: none.
6. Next-step line against the plugin: none seen.
7. Output too big: not visible from the server.
8. Page and chat disagreeing: none. No page was used after sign-in.
9. A fixed defect coming back: none.
10. Who the stage waited for: the person, at most 144 s (106 + 38). The machine: about 36 s to write the proposal (04:28:01 to 04:28:37, a guess at what that gap was).
11. Money on rejected work: none. No paid job.
12. Answers identical to the previous run: category, client, picture AI and drawn route are the same as VW-22.
13. An older way still in the text: the prompt is "ported verbatim" from v1 on 14 Oct. I did not check design/35 line by line for intake.
14. A rule tied to one kind of film or an older model: yes, B1 to B4.
15. Too few log lines: yes, E2.

## The stage in one line

Intake: 04:28:01 to 04:31:04 UTC (09:58:01 to 10:01:04 IST), 3 minutes, 13 server calls, 0 refusals, 2 questions, 0 jobs, no server cost. Sign-in and run creation before it: 84 seconds.

## The three changes that would save the most

1. Ask title, approval and category in one question with recommended answers. Saves one turn (about 40 s) on every film.
2. Rewrite the intake prompt's examples and capitals: no single project, plain case, the rule stated once. Saves nothing today; removes the documentary bias before the first non-documentary film.
3. Log the prepare and the questions of the text stages, and log the category under intake. Makes the next review exact instead of read from request lines.

## Could not see

- The three titles offered, the lines removed and the script's length (they are in the run's files, not in the log).
- What the assistant did between 04:28:01 and 04:28:37, and how long the operator actually read before answering.
- Any retry or rewrite inside Uma's chat that made no server call. The operator's stage note would show it.
- The assistant's own token cost.
