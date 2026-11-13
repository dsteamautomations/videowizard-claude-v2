# Stage review: VW-23, brief

13 Nov 2026. Read-only review. Nothing was changed. Uncommitted working note.

Evidence: `vw2_log` (2 rows for the stage), the server's request lines 04:31 to 04:46 UTC, `vw2_jobs` (none), `vw2_defects` (none), `server/procedures/v3.json` (the brief step as served), `plugin/scripts/stages_text.py` (the brief's checks). No operator stage note was pasted.

## Timeline

| UTC | IST | What the server saw | Answer |
|---|---|---|---|
| 04:31:04 | 10:01:04 | category recorded (reviewed under intake) | 200 |
| 04:31:11 | 10:01:11 | brief instruction fetched, run read (`vw stage brief prepare`) | 200 |
| 04:31:11 to 04:37:22 | 10:01:11 to 10:07:22 | no call from the laptop | |
| 04:37:22 to 04:37:25 | 10:07:22 to 10:07:25 | run read, 1 file signed and receipted, brief recorded with "Yes, same; approved" | 201 |
| 04:37:32 | 10:07:32 | script instruction fetched | 200 |

## A. Restrictions someone set

1. **Three things are asked on every film.** Prompt: "Brand and safety rules, whether the speaker may be seen on camera and where the film plays (production.format) are the operator's words, asked on every film in one message". The answer at 04:37:22 UTC (10:07:22 IST) was "Yes, same; approved". So last time's answers were offered and taken. The rule cost no extra turn here. Its reason (these are the operator's words, not the assistant's) holds. Proposed change: when the client has a latest brief, show its values already filled in and ask only for approval. That is what happened in effect; the text should say it.
2. **The category does not reach the brief.** The brief waits for the category (design/137, `core.py:334`), but `brief_prepare` (`stages_text.py:297`) fills only four places in the prompt: last brief, client rules, document timing, client card. The category chosen at 04:31:04 is not among them. The gate slowed intake by one turn and, as far as the prepare code shows, the brief does not use the answer. Proposed change: put the category into the brief prompt, or move the gate to the first stage that reads it.
3. **Web search only after the operator's yes, with a fixed sentence.** Step 5: "I am deviating from the usual procedure. I want to search the web for X, because Y. The result may affect Z." No sign it fired (no trace on the server either way). The reason holds. No change.
4. **Required questions block record.** `stages_text.py:319`: "question … is required; ask the operator and store their exact answer in `answers`." Did not refuse on the server's side. Reason holds.
5. **Chapters must be what the footage shows, and never from a previous brief.** Prompt: "a chapter is never an argument of the script"; step 2: "they are never taken from a previous brief"; generic names refused (`stages_text.py:393`). Shaped the chapters. Reason holds for a process film. See B2.
6. **Square and 4:5 are refused.** `stages_text.py:350`: "square and 4:5 are kept for a future update (SK, 2 Nov 2026)." Did not fire. It will fire on the first social clip. Worth a decision before a non-documentary film.
7. **Three record attempts** (`"cap": 3`). One used.
8. **Not asked, on purpose:** narration language (read from the script), footage languages, the film's shape, the target length. These restrictions save questions. Keep.

## B. Words in the prompt that restrict

1. **The ending leans to awareness.** "Never add a sales call to action by default." and "Educational or awareness work does not need a sales conversion." Right for this film. For an advertisement the default should be the opposite. Looser: "The ending follows the film's category: an awareness ending for an explainer, a call to action for an advertisement, unless the operator says otherwise."
2. **Chapter examples are all building work.** "laying the first course", "Mixing the mortar", "Pointing the joints". They push chapters toward steps of a manual process. Looser: one process example and one non-process example ("The product on the counter", "The customer's morning"), or none named.
3. **Brand and safety examples are site rules.** "no competitor logos, PPE required or not, nothing staged". Looser: add examples from another category (claims that need a disclaimer, people who must not be shown).
4. **"never search on your own"** plus the fixed sentence. It stops the assistant checking a number in the script without a turn. This is intended. No change proposed.
5. **"asked on every film"**: see A1.
6. **Prompt origin "v1 VW-BRIEF-0.4.0 (ported verbatim 14 Oct 2026)".** Long, with many "do not" and "never" lines (about twenty). No visible harm in this run. Worth one pass for today's models when the intake prompt is rewritten.

## C. Steps that failed or were done again

None seen on the server. One prepare, one record, first attempt. The run was read twice (prepare and record), which is normal.

The brief's checks run on the laptop before anything is sent (`stages_text.py:288` to `395`). A refusal there never reaches the server, so I cannot say there was none.

## D. Getting the operator's input faster

| # | Question | Answered at | Wait | Mark |
|---|---|---|---|---|
| 1 | Same production values as last time, and approve the brief? (a guess from the answer's words) | 04:37:22 UTC (10:07:22 IST), "Yes, same; approved" | at most 6 min 11 s, which includes the assistant writing the brief | Already clubbed and already predicted from the client's last brief. Could be a button: "Same as last time, approved". |

I see one answer. I cannot see whether it came after one message or several.

## E. Execution that can be better

1. **Six minutes with no server call** (04:31:11 to 04:37:22 UTC). This is the assistant writing the five decisions and the operator reading them. The server cannot split the two. It is the whole length of the stage.
2. **The brief leaves one log line.** Only the record. The questions, the "same as last time" answer and the chapters are not in the log.
3. **A category gate with no reader** (A2).

## F. Known weak spots

1. Rounds to pass a check: none seen on the server; local refusals not visible.
2. Refusals that are really questions: none.
3. Connection errors and timeouts: none. Every request reached the server.
4. Provider failures: none. The brief uses no provider.
5. Blank searches: none.
6. Next-step line against the plugin: none seen.
7. Output too big: not visible from the server.
8. Page and chat disagreeing: none. No page was used.
9. A fixed defect coming back: none.
10. Who the stage waited for: not separable. 6 min 11 s between prepare and record, person and assistant together.
11. Money on rejected work: none.
12. Answers identical to the previous run: yes. "same" for the production values.
13. An older way still in the text: not checked line by line against design/35.
14. A rule tied to one kind of film: yes, B1 to B3.
15. Too few log lines: yes, E2.

## The stage in one line

Brief: 04:31:11 to 04:37:25 UTC (10:01:11 to 10:07:25 IST), 6 minutes, 6 server calls, 0 refusals, 1 answer recorded, 0 jobs, no server cost.

## The three changes that would save the most

1. Give the category to the brief prompt and let it set the defaults (ending, chapter examples, brand and safety examples). This makes the category question earn its turn.
2. When the client has a latest brief, show its production values filled in and ask one approval with a button. Saves typing on every repeat client.
3. Log the questions and the "same as last time" answers of the brief, so the next review can split the person's time from the assistant's.

## Could not see

- The five decisions, the chapters and the questions shown to the operator.
- Any refusal by the brief's local checks, and any rewrite of `out/brief.json`.
- How the 6 minutes split between the assistant writing and the operator reading.
- Whether a web search was proposed.
- The assistant's token cost.
