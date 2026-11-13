# Stage review: VW-23, script

13 Nov 2026. Read-only review. Nothing was changed. Uncommitted working note.

Evidence: `vw2_log` (1 row for the stage), the server's request lines 04:37 to 06:50 UTC, `vw2_jobs` (none for this stage), `vw2_defects` (none), `server/procedures/v3.json` (the script step as served), `plugin/scripts/stages_text.py` (the script's checks), and one screenshot of Uma's chat pasted by Deepa (the proposed change and the claims). No operator stage note.

## Timeline

| UTC | IST | What the server saw | Answer |
|---|---|---|---|
| 04:37:32 | 10:07:32 | script instruction fetched, run read (`vw stage script prepare`) | 200 |
| 04:37:32 to 06:26:13 | 10:07:32 to 11:56:13 | no call from the laptop | |
| 06:26:13 to 06:26:19 | 11:56:13 to 11:56:19 | run read, 1 file signed and receipted, script recorded with "Yes, approved" | 201 |
| 06:26:26 | 11:56:26 | voice instruction fetched | 200 |

## A. Restrictions someone set

1. **A web search needs the operator's yes, and is proposed only for "a figure or claim that the message rests on".** Step 3, with the fixed sentence "I am deviating from the usual procedure. I want to check X, because the message rests on it." In this run the assistant listed four claims the film rests on and proposed no search (screenshot: "I am not proposing a web search for these: they are qualitative"). "Qualitative" is the assistant's own reason; the step has no such exception, and one of the four is a figure ("at least two weeks" of water curing). The rule's reason (nothing from the web without the operator seeing it) holds. The trigger is too loose to give the same result twice. Fix agreed by Deepa: five parameters (see the fixes table).
2. **Keep the wording unless a change is specific and useful.** Prompt: "Preserve its wording unless there is a specific useful change", "Avoid copy-editing for its own sake". One change was proposed (the stray "the"). It helped: the review was short. Holds.
3. **Only four kinds of problem are named**: ending against the intent, a phrase that misstates the message, an unexplained reference, a confusing transition. No rule covers how a line sounds when spoken. The one change made here (a slip the narrator would say aloud) is outside the four. It shaped the work by omission.
4. **The record step refuses a text that differs from the cleaned script plus the accepted changes.** `stages_text.py:497`. Runs on the laptop. No sign of it on the server. Holds (SK's exact-match rule).
5. **Every change needs the operator's decision before record.** `stages_text.py:435`. Holds.
6. **No checking tool.** The script stage has no search or fact-checking service of its own; the only method is the assistant's web search in the operator's chat. Claims are stored "checked: false" until a search is done.
7. **Three record attempts** (`"cap": 3`). One used.

## B. Words in the prompt that restrict

1. **"propose a web search … when the assessment names a figure or claim that the message rests on"**: one sentence decides every check. See A1. Replace with the five agreed parameters.
2. **"Avoid copy-editing for its own sake. Abstract language is not inherently defective."** Right for meaning. It leaves no room for a spoken-word pass (a slip, a tongue-twister, a sentence too long for one breath). Looser: add "A line that will sound wrong when spoken is a useful change."
3. **"Do not invent … sales actions"** and "CTA instructions and contact details, only when the accepted ending asks for an action". Right for an explainer. For an advertisement the ending will ask for an action as a rule; the wording works but only if the brief's ending says so. No change if the brief fix (ending follows the category) is built.
4. **"The tool checks that only the accepted changes are applied; do not critique again."** Stops a second look after the operator's rewording. No visible effect here.
5. **Prompt origin "v1 VW-SCRIPT-PREPARATION-0.5.0 (ported verbatim 14 Oct 2026)".** No example from an older film in this prompt. Fewer capitals than intake.

## C. Steps that failed or were done again

None seen on the server. One prepare, one record, first attempt. Every request reached the server.

The record step's checks run on the laptop first; a refusal there would not reach the server.

## D. Getting the operator's input faster

| # | Question | Answered at | Wait | Mark |
|---|---|---|---|---|
| 1 | Approve this wording (one change), or changes? With the claims listed and "If you want any of them checked, say which one." | 06:26:13 UTC (11:56:13 IST), "Yes, approved" | 1 h 48 min 41 s | One question, already clubbed. The claims could be ticks to click (check this one / leave it) instead of "say which one". |

The long wait was not the application: the stage was held while the rules and the claim checks were discussed with the builder.

## E. Execution that can be better

1. **The whole stage is one gap of 1 h 48 min with no server call.** The server shows nothing between prepare and record. A stage held for a discussion looks the same as a stuck stage.
2. **The script leaves one log line.** The change proposed, the decision on it and the claims are not in the log. They are only in the run's files.
3. **Claims are free text for the operator to answer.** See D.

## F. Known weak spots

1. Rounds to pass a check: none seen on the server; local refusals not visible.
2. Refusals that are really questions: none.
3. Connection errors and timeouts: none. Every request reached the server.
4. Provider failures: none. The script uses no provider.
5. Blank searches: none.
6. Next-step line against the plugin: none seen.
7. Output too big: not visible from the server.
8. Page and chat disagreeing: none. No page was used in this stage.
9. A fixed defect coming back: none.
10. Who the stage waited for: the person, 1 h 48 min. The machine: seconds.
11. Money on rejected work: none.
12. Answers identical to the previous run: not visible (the changes are not logged).
13. An older way still in the text: not checked line by line against design/35.
14. A rule tied to one kind of film: B3 only, mild.
15. Too few log lines: yes, E2.

## The stage in one line

Script: 04:37:32 to 06:26:19 UTC (10:07:32 to 11:56:19 IST), 1 h 49 min of which the server worked for seconds, 6 server calls, 0 refusals, 1 answer recorded, 0 jobs, no server cost.

## The three changes that would save the most

1. Replace the one-sentence search trigger with the five agreed parameters, and show the claims as ticks in one question.
2. Add a spoken-word rule to the script step, so changes like the stray "the" are found by rule and not by chance.
3. Log the proposed changes, the decisions and the claims (with checked or not), so a review can see them without the run's files.

## Could not see

- The full assessment and the final wording (in the run's files).
- Whether the one change was accepted, rejected or reworded.
- Any local refusal at record.
- The assistant's token cost.
