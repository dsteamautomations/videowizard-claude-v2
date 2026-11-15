# Stage review: VW-24, treatment (visuals step 1)

Read on 15 Nov 2026 by the builder thread. Read only: nothing fixed, nothing deployed, no row or run file changed.

Times are UTC with IST in brackets (IST = UTC + 5:30). All on 15 Nov 2026.

The treatment ran **twice**. Pass 1 (06:28 to 06:37) ran under server 0.99.x and was abandoned when SK reviewed it and asked for new rules. Pass 2 (12:17 to 12:36) ran under server 0.101.1 with the new rules and the Claude artifact page, and was approved.

Evidence used: `vw2_log` ids 2780 to 2794; `journalctl -u vw2-server` 06:27 to 06:40 and 12:10 to 13:05; `vw2_jobs`; `vw2_defects`; `server/app/visuals_stage.py`, `film.py`, `page_flow.py`; `server/procedures/v3.json` (visuals, part "treatment"); `plugin/commands/vw.md`. No operator note was pasted.

## Timeline

| UTC (IST) | Call | Code | Log |
|---|---|---|---|
| 06:28:37 (11:58:37) | POST visuals/prepare | 200 | 2780 |
| 06:28:37, 06:28:39 | GET package.json, GET visuals/library | 307, 200 | |
| 06:30:36 (12:00:36) | POST visuals/treatment | **409** | 2781 refusal FILM_MOTION |
| 06:34:26 (12:04:26) | POST film (motion = lively) | 200 | 2782, quote "Lively" |
| 06:34:34 (12:04:34) | POST visuals/treatment | 200 | 2783 |
| 06:35:35 (12:05:35) | POST visuals/treatment | 200 | 2784 |
| 06:35:44 (12:05:44) | POST visuals/chat/next | 200 | 2785 |
| 06:37:27 (12:07:27) | POST visuals/chat/answer | 200 | 2786, quote "Accept" (the Direction) |
| | *5 h 40 min: SK's review, new rules built, two deploys (about 11:55 and 12:11 UTC)* | | |
| 12:17:20 (17:47:20) | POST visuals/prepare | 200 | 2789 |
| 12:17:21, 12:17:22 | GET package.json, GET visuals/library | 307, 200 | |
| 12:20:08 (17:50:08) | POST visuals/treatment | 200 | 2790 |
| 12:21:58 (17:51:58) | POST visuals/treatment | 200 | 2791 |
| 12:22:07 (17:52:07) | POST visuals/page | 200 | 2792 |
| 12:28:13 (17:58:13) | POST visuals/page/record | 200 | 2793 (the Direction) |
| 12:36:34 (18:06:34) | POST visuals/page/record | 200 | 2794 (the 16 gaps) |
| 12:37:06 (18:07:06) | GET visuals | 200 | |

No job ran in the stage. No defect was raised in the window.

That the second record call approved the treatment is **inferred**: no draft was sent after it, and the plan's check began at 12:56:38 and its proposal was accepted at 13:02:59 (log 2818), which the server allows only with a recorded treatment. The log line itself says nothing (see C5, F15).

## A. Restrictions someone set

| # | Restriction | When it fired | Set by | Reason still holds? | Helped or slowed |
|---|---|---|---|---|---|
| A1 | A film needs a motion style before a treatment is taken. `film.py:84` `need_motion`: "This film has no motion style yet. Recommend Restrained (documentaries, factual films)… ask the operator once" | 06:30:36 (12:00:36), once, 409 | design/179, SK 12 Nov | Yes: the style feeds the drawn shots | Slowed: 3 min 58 s from refusal to the next accepted send. The question is right; its place is wrong (see C1). Proposed: ask it at `vw visuals prepare` with buttons |
| A2 | The Direction is answered before any gap line is shown. `page_flow.page`: the Direction alone until accepted | 12:22:07 to 12:28:13 (17:52 to 17:58), once | design/124 change 6; kept in design/190, 204 | Yes: a changed Direction rewrites every gap line | Helped, but it costs one extra round trip (a second "done"). Proposed: keep |
| A3 | No yes to the whole: each line is accepted on its own. Served text: "There is no yes to the whole." | 16 gap lines answered between 12:28:13 and 12:36:34 | design/124 change 6 | Partly: the page already shows every line; 16 clicks for 16 unchanged lines | Slowed a little (8 min 21 s for 16 lines, about 31 s a line, reading included). Proposed: an "Accept all the rest" button on the page; a line the operator opens to change is left out of it |
| A4 | The Direction in six parts, each with a length limit (160, 300, 200, 300, 400, 500 characters); a part over its length is refused | Pass 2; no refusal seen | design/203, SK 15 Nov | Yes, new today | Shaped the work. No refusal, so no cost seen |
| A5 | Each shot carries two reasons of at most 300 characters; a missing reason is flagged, not refused | Pass 2; no refusal seen | design/202, SK 15 Nov | Yes, new today | Shaped the work. Whether any reason was missing is not in the log |
| A6 | Still pictures above 10 % of the film are warned (`VISUALS_STILL_SHARE = 0.10`) | Pass 2; not visible whether it warned | design/202, SK 15 Nov | Yes | Guess: this warning is why the draft was sent twice (C3). Not provable from the log |
| A7 | A gap missing, a gap twice, or a field out of form is refused; five routes only | Both passes; no refusal seen | design/150 set C, design/124 | Yes | No cost seen |
| A8 | Nothing is recorded until the operator says "done" in the chat | 12:28:13 and 12:36:34 | design/204, SK 15 Nov | Yes: it is what makes undo possible on the page | Helped. Cost: the operator must come back to the chat twice |
| A9 | Only the page's owner may write to it (`CAPABILITIES`, rule `write: owner`) | Pass 2 | design/204 | Yes | No cost seen |
| A10 | The preparation is run before a treatment; the server refuses older tools (plugin minimum 0.86.0) | 12:17:20 | design/204 | Yes | No refusal seen: the Mac was updated first |

## B. Words in the served text that restrict

All from `server/procedures/v3.json`, visuals, part "treatment" (1,357 words).

| # | Quote | What it narrows | Looser wording |
|---|---|---|---|
| B1 | "an AI video shot is one action, at most four people, nobody crossing, hand work close and in the right hand, every transfer named and close" | A fixed count and staging rules written for the video model's weak points on 5 Nov. The model has changed since (Hydrogen, design/193) | "an AI video shot is one action; keep the people few and their paths apart" and move the count to the per-model rules, tested against today's model |
| B2 | "`shape`, the film from its opening to its end in three to five beats" | A fixed count for every film length and category | "in a few beats" |
| B3 | "two or three sentences each" (the six parts) beside the character limits | Two limits on the same thing; "the film's one idea in one sentence" then contradicts it for `idea` | Keep the character limits; drop "two or three sentences each" |
| B4 | "A still always moves slowly." | "always" stops a deliberate hard hold (a document, a title card) | "A still moves slowly unless it must be read" |
| B5 | "in a documentary or explainer, none beyond a diagram's labels" | "none" also stops a place name, a date or a person's name on screen | "none beyond a diagram's labels and a name, place or date the viewer needs" (SK's ruling of 15 Nov was about sentences on the picture; a guess that names were not meant) |
| B6 | "muted and true to life by default" | A look default that suits documentaries; it is in the general text | File it under the documentary category; other categories take their look from the brief |
| B7 | "the frozen share against its 10 % limit" | A number typed into the text; the server holds its own figure (`frozen_limit`) | "against its limit" (the server prints the figure) |
| B8 | "the order of the ways for a scene is real footage that shows it; else AI video; else a still" | Fixed order. It is SK's ruling of 15 Nov, so it stays; noted because it decides most lines | No change |
| B9 | "A footage clip, or a specific thing the footage shows (one building, one machine), is named at one gap only" | "one gap only" stops a deliberate return, while the same text says "Bring the film's key pictures back" | "is named at one gap, or returns on purpose with the reason in its line" (the text already allows the reason; the two sentences should be joined) |

## C. Steps that failed or were done again

| # | What | Time | Times | Cause and label | Reached the server? | Proposed change |
|---|---|---|---|---|---|---|
| C1 | Treatment refused: no motion style | 06:30:36 (12:00:36) | 1 | **Our instruction was unclear.** The motion style is asked nowhere in the served text of the visuals stage or in `plugin/commands/vw.md`; the assistant learns of it only from the refusal (`film.py:84`, rule FILM_MOTION). Cost: 3 min 58 s to the next accepted send, of which 3 min 50 s was the question and its answer | Yes, 409 | `vw visuals prepare` returns the question with its buttons when the film has no motion style |
| C2 | The whole of pass 1 thrown away | 06:28:37 to 06:37:27 | 1 | **The operator changed their mind** (SK reviewed the draft and asked for new rules). 8 min 50 s of the run, no money | Yes | None: this was a review, not a fault |
| C3 | The draft sent twice in a row, both accepted | 06:34:34 and 06:35:35; 12:20:08 and 12:21:58 | 2 pairs | **Guess: the assistant revised after reading the first answer's warnings or missing reasons.** The server answers 200 with `warnings`, `reasons_missing`, `direction_missing`; the log line holds none of it. Cost: 1 min 1 s and 1 min 50 s | Yes, 200 | The log line of a draft says how many warnings, which kinds, and how many reasons are missing; then this can be told apart from a plain repeat |
| C4 | The preparation run again | 12:17:20 | 1 | **Our rule changed** (new instructions). Asked for in the operator prompt | Yes, 200 | None |
| C5 | Two record calls with nothing in the log about what was recorded | 12:28:13, 12:36:34 | 2 | **The server.** `visuals/page/record` writes one step line, "by assistant", with no quote. On the card path the same answer is logged "by operator" with the quote (log 2786, "Accept") | Yes, 200 | `page_record` logs one line per answer with the line, the choice and the operator's words, as the card path does |

## D. The operator's questions

| # | Question | Asked | Answered | Wait | Mark |
|---|---|---|---|---|---|
| D1 | Which motion style? | 06:30:36 (as a refusal) | 06:34:26 | 3 min 50 s | **Offer as ready answers, earlier.** The recommendation was Restrained; the operator took Lively, so it cannot be predicted from the category alone |
| D2 | Do you accept the direction of the film? (card) | 06:35:44 | 06:37:27 | 1 min 43 s | Asked again in pass 2 (D3), because the rules changed |
| D3 | The Direction, on the page | 12:22:07 (page data ready; the link reached the operator some time after) | 12:28:13 | at most 6 min 6 s, including the page being published and filled | Could be **clubbed with D1**: motion style and Direction on the same first page |
| D4 | The 16 gap lines, on the page | 12:28:13 | 12:36:34 | 8 min 21 s | Could be **clubbed into one click** for unchanged lines (A3) |

Asked twice: the Direction (D2, D3), for the reason above. Nothing else.

## E. Execution that can be better

1. **The motion style found by refusal** (C1). 3 min 58 s. Ask at prepare.
2. **Two "done" trips** (12:28:13 and 12:36:34). The operator answers on the page, returns to the chat, says done, returns to the page. Proposed: once the Direction is accepted on the page, the page shows the gap lines at once from the round it already holds, and one "done" records both. If the Direction is changed, the gap answers are dropped, as today.
3. **Writing the draft: 2 min 48 s and 1 min 50 s** (12:17:20 to 12:20:08 to 12:21:58). The slowest machine steps. Fine for 16 gaps; the second send is the part to understand (C3).
4. **The log is too thin to review this stage** (C3, C5, F15).
5. Money spent on work thrown away: none. No job ran.
6. Output too large: not seen. The page data was one call; the size is not in the log.

## F. Known weak spots

1. Rounds to pass a check: none refused in the treatment itself. One motion-style refusal before the first send (C1).
2. Refusals that are really questions: one, the motion style (06:30:36). Yes, it could be asked at prepare with the recommended answer.
3. Connection errors and timeouts: none seen. Every request has an answer code.
4. Provider failures: none. No job ran.
5. Blanks: not a treatment matter. None seen.
6. A next-step line naming a missing command: none seen. `vw visuals page` and `--record` both ran on the Mac.
7. Output too big to read: none seen.
8. The page and the chat disagreeing: none seen. Pass 1 used the card, pass 2 the page; `chat/next` was not called in pass 2 before 13:03.
9. A fixed defect that came back: none.
10. Who the stage waited for, pass 2: the person at most 14 min 27 s (two page waits), the machine about 4 min 47 s. Pass 1: the person 5 min 33 s, the machine about 3 min 17 s.
11. Money on rejected work: ₹0.
12. Answers identical to the previous run: none usable. VW-21 to VW-23 predate the motion style question's page and the six-part Direction.
13. An older way still in the served text: yes, on purpose. The card (`vw visuals next`, `vw visuals card`, `vw visuals decide`) is old way 76 in design/35, kept as the way back until the page has carried a full treatment on the Mac. This run is that treatment, so the condition for retiring it is met on SK's word.
14. A rule tied to one kind of film or an older model: B1 (four people, nobody crossing: written for the 5 Nov video model) and B6 (muted look in the general text).
15. Too few log lines: **yes.** A draft's warnings, the lines recorded on the page and the operator's words on the page are not in the log.

## The stage in one line

- Pass 1: 06:28:37 to 06:37:27 (11:58 to 12:07 IST), 8 min 50 s, 9 server calls, 1 refusal, 2 questions, 0 jobs, ₹0. Abandoned.
- Pass 2: 12:17:20 to 12:36:34 (17:47 to 18:06 IST), 19 min 14 s, 8 server calls, 0 refusals, 2 questions (17 lines), 0 jobs, ₹0. Approved.

## The three changes that would save the most

1. **One "done", not two:** the page shows the gap lines as soon as the Direction is accepted, with "Accept all the rest". Saves one round trip and most of the 8 min of clicking.
2. **Ask the motion style at prepare, with buttons** (best on the same page as the Direction). Saves about 4 min and one refusal on every new film.
3. **Log what a draft returned and what the page recorded**, with the operator's words. Saves no minutes in the run; without it the approval of a treatment has no record in the run log and a review like this one rests on guesses.

## Could not see

- The treatment's text, its warnings, its totals and which lines were accepted: they are in the run's session file in storage, which this review did not open (it needs the server's keys).
- What each of the two draft sends returned, so why the draft was sent twice.
- The Claude side of the page: the publish, the writes to the page, any permission prompts on the Mac, and how long the operator had the link before answering. None of these are server calls.
- The assistant's chat and the operator's words on the page (the page's database holds them; the run log does not).
- Whether the operator read every gap line or accepted quickly.

## Follow-up outside this stage (not reviewed)

The plan step that followed had 4 rejected checks (12:56:38 to 12:58:54) and one refused proposal at 13:02:36: "foundation.treatment starts from the treatment's Direction, word for word". The six-part Direction is new today; this refusal may come from it. It belongs to the plan's review.
