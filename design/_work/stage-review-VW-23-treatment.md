# Stage review: VW-23, treatment

14 Nov 2026. Read-only review. Nothing was changed. Uncommitted working note.

The treatment is the first part of the `visuals` stage. This review covers it from `visuals/prepare` to the record of the treatment (every line accepted). The plan and everything after it are not in it.

Evidence, read by Claude from this PC: `vw2_log` (9 rows in the window, one of them with a blank stage), the server's request lines 15:05 to 17:30 UTC (`journalctl -u vw2-server` on the VM, read only), `vw2_receipts` (the answer the server gave to each call), `vw2_jobs` (none for this stage), `vw2_defects` (none in the window), `vw2_runs` (the film record), and the code and instruction text of the deployed commit `4d7f72d` (server 0.98.2; `/api/meta` says 0.98.2). No operator stage note.

The live server is not `main`: `main` (`8dcc281`) holds 0.99.0 and 0.98.3, not deployed. Every quote below is from `4d7f72d`.

## Timeline

| UTC | IST | What the server saw | Answer |
|---|---|---|---|
| 15:09:03 | 20:39:03 | `visuals/prepare`; then the package file (519,888 bytes) and the library | 200 |
| 15:10:50 | 20:40:50 | treatment draft sent | **409 `FILM_MOTION`** |
| 15:12:57 | 20:42:57 | film record: motion style `lively`, quote "Lively" | 200 |
| 15:13:05 | 20:43:05 | treatment draft sent: 18 gaps, 18 pictures, ₹196.6, **13 warnings** | 200 |
| 15:13:41 | 20:43:41 | treatment draft sent again: 18 gaps, **30 pictures, ₹244.6**, 0 warnings | 200 |
| 15:13:52 | 20:43:52 | `chat/next`: card `card-3a48a35c1b`, 10 lines (the direction and 9 gaps), 9 more waiting | 200 |
| 15:13:52 to 15:25:36 | 20:43:52 to 20:55:36 | no call (11 min 44 s) | |
| 15:25:36 | 20:55:36 | `chat/next` again: the same card, the same 16,360 bytes | 200 |
| 15:28:46 | 20:58:46 | `chat/card`: 10 answers recorded, none a change; the answer carries card `card-b805f40943`, 9 lines | 200 |
| 15:32:03 | 21:02:03 | `chat/card`: 9 answers recorded, none a change; "No decision waits now" | 200 |
| 15:32:10 | 21:02:10 | `next` | 200 |

All 19 lines were accepted, so the server recorded the treatment at 15:32:02 (`_record_lines`; `session.json` saved 15:32:02.58). No log line says so.

## A. Restrictions someone set

1. **The film's motion style must be recorded before any treatment call.** `visuals_stage.treatment` starts with `need_motion_style(run)   # design/179 S3`; `film.need_motion` raises 409 `FILM_MOTION`. Set by design/179 (12 Nov, live in 0.92.0). Fired once, 15:10:50 UTC (20:40:50 IST). The reason holds: this film has 76 s of drawn shots that take the style. It only slowed the stage: the assistant had no way to know (see B9), wrote and sent a full draft, and was refused. Cost: one refused call and 2 min 07 s to the answer. Change: ask the motion style before the treatment is written (in what `visuals/prepare` returns, or with the film's shape at media).
2. **Every line is accepted on its own.** Design/124 Change 6 (29 Oct): `_treatment_lines`, and the served words "There is no yes to the whole." 19 lines, 19 accepts, no change asked. From the first card handed out to the record: 18 min 11 s. The reason (the operator reads each line) holds only in part: the card has no way to say "the rest is fine". Change: an "Accept all the rest" button on the card.
3. **A card holds at most 12 entries; a longer step comes as cards of 10.** `CARD_ALL, CARD_PART = 12, 10` (design/190, 13 Nov). 19 lines became two cards (10 and 9), two submits, two server calls (15:28:46, 15:32:03). It shaped the work; nothing was refused. Whether the limit is a display limit of the chat is not written in the code. Change: one card for a whole treatment (this film needed 19).
4. **A still is at most 4 s.** `treatment_length_warnings` (design/89 B1, design/126 TR3): "at most 4 s; fill the stretch with several different stills or a moving shot". Fired 10 times on the first draft (15:13:05). A warning, not a refusal, but the assistant rewrote the draft to clear it: pictures 18 to 30, estimate ₹196.6 to ₹244.6. The operator never saw the cheaper draft. One number for every category of film; whether it still fits is SK's call.
5. **A run of graphics above 8 s is warned; above 12 s wants a reason.** `graphics_runs` (design/93 G1, design/126 TR1). Fired 3 times on the first draft (9.8 s, 19.0 s, 13.6 s). Same effect as item 4.
6. **The direction comes first, at most 2000 characters.** Design/124 Change 3. Not refused; the direction is about 1,500 characters. It helped: the card opened with it.
7. **The treatment is recorded before any plan or picture.** Design/65 B6. Holds.
8. **Five routes only** (`TREATMENT_ROUTES`, design/113) and the required fields per gap (`picture`, `seconds`, `images`, `frozen_seconds`, `depicts`). No refusal. Three routes were used first (drawn 6, still 10, footage 2 gaps).
9. **The spending limit of ₹5,000** (`VISUALS_CAP_INR`, design/74). The estimate is ₹244.6, 4.9 % of it. It did not shape anything.
10. **The frozen share limit of 10 %** (design/89 B4). The treatment's is 0. It did not shape anything, but the field is required in every gap.
11. **One decision or one card at a time, in the server's order** (design/188). No refusal.

Outside this stage, one minute before it: the master's approval was refused at 15:06:24 UTC for the words "Yes, approved" (`STAGE2_CONTRACT`: "must say the operator watched the film and listened to it (both words)"). It belongs to the master review.

## B. Words in the prompt that restrict

All from the served text `part-treatment.md` (5,342 characters), unless said.

1. **"the mason laying bricks on the half-built wall, the site around"**. An example from a building film in the general text. It fits this film by luck. Looser: "the person doing the film's main activity, with the place around them".
2. **"In a documentary or a client story, people, purposeful work and the material changing under their hands carry the film"**. A rule for one category in the general set. File it under the documentary category.
3. **"There is no yes to the whole."** See A2. Looser: "Each line can be changed on its own; the operator may accept the rest together."
4. **"an AI video shot is one action, at most four people, nobody crossing, hand work close and in the right hand, every transfer named and close"**. A fixed number and the limits of one video model, inside the treatment. What it stopped here is not visible (13.52 s of AI video in the treatment). It belongs to the plan and the take, not to the choice of picture.
5. **"muted and true to life by default"**. The direction repeats it word for word ("realistic representative scenes, muted and true to life"). The default went straight into the film. Wrong default for an advertisement or a product film. Looser: "the look that fits the film's category".
6. **"is named at one gap only"** (a footage clip or a thing in it). "Only". Effect here not visible.
7. **"never an empty view of the place; a close-up comes after a wider view"**. A fixed order for the opening of every film.
8. **"two graphics in a row only when each passes the test above"**. The rule is here in words; its numbers (8 s, 12 s, and 4 s for a still) are not in this part at all ("4 s" and "8 s" appear 0 times). The assistant met them as 13 warnings after sending. Add the three numbers to the part.
9. **Nothing on the motion style.** The word "motion" appears 0 times in `part-treatment.md`, and the answer of `visuals/prepare` says only: "settle the treatment with the operator and record it (`vw visuals treatment`), then write the plan". The first notice is the refusal.
10. **The refusal's own words**: "Recommend Restrained (documentaries, factual films) for this film's category … ask the operator once". The category is `documentary-explainer`; Lively is filed as "explainers, training". The operator chose Lively, against the recommendation.
11. **The step line and its part disagree.** Step 1: "then `vw visuals treatment --accept … --quote …` or `--send-back … --notes …` per line on the operator's words". The part: "the server hands the operator every line on one card". The step line is the way of 29 Oct.

## C. Steps that failed or were done again

| # | UTC (IST) | What | Times | Cause | Label | Reached the server |
|---|---|---|---|---|---|---|
| 1 | 15:10:50 (20:40:50) | Treatment refused, `FILM_MOTION` | 1 | The motion style was not asked before; no served text names it (B9) | our rule; our instruction was unclear | yes, 409 |
| 2 | 15:13:05 and 15:13:41 (20:43:05, 20:43:41) | Treatment draft sent twice, 36 s apart | 2 | The first answer had 13 warnings; the second has none. The limits are not in the served part (B8) | our instruction was unclear | yes, 200 both |
| 3 | 15:13:52 and 15:25:36 (20:43:52, 20:55:36) | The same card fetched twice | 2 | Not visible. A guess: the card did not show, or the chat was taken up again after a pause | not known | yes, 200 both |

No failed job, no timeout seen, no check rejected.

## D. Getting the operator's input faster

| # | Question | Asked from | Answered | Wait | Mark |
|---|---|---|---|---|---|
| 1 | The motion style | 15:10:50 UTC (20:40:50 IST) | 15:12:57, "Lively" | at most 2 min 07 s | Could be clubbed with the film's shape (asked at media, 13 Nov). Could be offered as ready answers: the last three films of this client have a style on record (VW-21 lively, VW-22 restrained, VW-23 lively). |
| 2 | Card 1: the direction and 9 gap lines | 15:13:52 (20:43:52) | 15:28:46, 10 accepts | 14 min 54 s | Could be one card with card 2. Could have "Accept all the rest". |
| 3 | Card 2: 9 gap lines | 15:28:46 (20:58:46) | 15:32:03, 9 accepts | 3 min 17 s | Same. |

20 decisions in all (1 and 19). None was a change.

Asked twice: card 1 was fetched twice (C3). Whether the operator saw it twice is not visible.

## E. Execution that can be better

1. **Slowest step: card 1, 14 min 54 s**, of which 11 min 44 s (15:13:52 to 15:25:36) passed with no call and nothing running. The server cannot tell reading from a card that did not show.
2. **"Changed since you last saw it" was shown for lines the operator had never seen.** Card 1 marks BEAT_01-B1, BEAT_04-B1 and BEAT_04-B2 as changed, with "What changed" lists (for example `images: "2" → "5"`). The earlier version was the assistant's own first draft, 36 s before; no card had been handed out. `_carry_lines` compares with the last draft sent, not with the last draft shown. Change: mark a line changed only against a draft that was handed to the operator.
3. **The cheaper first draft was thrown away unseen.** 18 pictures and ₹196.6 became 30 pictures and ₹244.6 to clear warnings. No money is spent yet; the plan will now make 12 more pictures. Change: put the limits in the served part (B8), so the first draft already meets them and the cost shown is the only one.
4. **Two next-step lines are out of date.** The tool, after a draft: "Now `vw visuals next`: the server hands the operator one line at a time, in the chat (design/188)"; the server handed a card. `visuals/prepare`: "record it (`vw visuals treatment`)"; the record is made by the card.
5. **Output size.** The package is 519,888 bytes (the tool splits it into files). Each card answer is about 16,000 bytes that the assistant must pass to the card tool "character for character".
6. **The log is too thin for this step.** Both card answers are logged as "visuals/chat/card" and nothing else: no "treatment recorded", no count of accepts and changes, no warnings, no estimate. The motion style is logged with a blank stage (row 2527), so a search by stage misses it. Everything above about the drafts and cards comes from `vw2_receipts`, not from the log.
7. **No money spent on work thrown away.** No job ran.

## F. Known weak spots

1. Rounds to pass a check: no rejection; one refusal (motion style) and one draft sent again for 13 warnings. Beforehand the assistant could have been told the motion style is needed and the three numbers (4 s, 8 s, 12 s).
2. Refusals that are really questions: yes, one, `FILM_MOTION`. It could have been asked at prepare with the recommended answer.
3. Connection errors and timeouts: none seen. Every request in the lines has an answer.
4. Provider failures and retries: none. The step uses no provider.
5. Blanks: none in the log. Whether unused footage existed for the gaps given to stills and graphics is not visible here.
6. A next-step line naming a missing command: none. Two lines describe an older flow (E4).
7. Output too big: the 519,888-byte package and the 16,000-byte cards (E5). Whether the assistant read all of it is not visible.
8. The page and the chat: step 0 still says "give the operator the page link"; the page was retired for operators on 12 Nov (design/35, old-ways row 47). No page call from the operator is in the lines.
9. A fixed defect that came back: none.
10. Who the stage waited for: the person about 20 min 18 s (2 min 07 s, 14 min 54 s, 3 min 17 s); the assistant and the server about 2 min 42 s.
11. Money on rejected work: none.
12. Answers identical to an earlier run: motion style "lively" is the same as VW-21 (same client, same category); VW-22 took "restrained". A candidate for "same as last film" as the first answer.
13. An older way still in the served text: yes. Step 0 "the page link" (row 47); step 1 the per-line `--accept` (B11); the tool's "one line at a time" (row 49 keeps it only for a machine that cannot show the card).
14. A rule tied to one kind of film or an older model: B1, B2, B4, B5 and the 4 s still (A4).
15. Too few log lines: yes (E6).

## The stage in one line

Treatment: 15:09:03 to 15:32:03 UTC (20:39:03 to 21:02:03 IST), 23 min, 12 server calls, 1 refusal, 3 questions holding 20 decisions (none a change), 0 jobs, ₹0 spent (estimate for the film's visuals ₹244.6 of ₹5,000).

## The three changes that would save the most

1. **One card for the whole treatment, with "Accept all the rest".** 19 accepts with no change took 18 min 11 s over two cards.
2. **Tell the assistant before it writes: ask the motion style at prepare, and put the 4 s, 8 s and 12 s limits in the treatment part.** Saves the refused call, the second draft, and shows the operator one cost.
3. **Mark a line "changed" only against what the operator saw, and log the record** (treatment recorded, accepts, changes, warnings, estimate; the motion style under the visuals stage).

## Could not see

- The treatment itself beyond card 1 (the direction and 9 gaps); card 2's nine lines were not read.
- Why the card was fetched a second time and what happened in the 11 min 44 s.
- How the motion style was asked (buttons or text) and whether the recommendation was shown.
- Whether the operator read each line or clicked through.
- Any refusal on the laptop that did not reach the server.
- The plugin version installed on Uma's laptop (the minimum is 0.84.0).
- The assistant's token cost.
- Not checked line by line: every design/35 old way against the whole visuals text; only the preparation and treatment parts were read.
