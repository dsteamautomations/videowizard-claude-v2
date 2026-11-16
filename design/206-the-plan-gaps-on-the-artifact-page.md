# design/206: the plan's gaps answered on the Claude artifact page

**Status:** built on 16 Nov 2026 (server 0.103.0, plugin 0.88.0, plugin minimum raised to 0.88.0: every laptop updates); **not deployed**; SK's deployment word awaited. SK approved the list on 16 Nov ("Approved") and added three points.

## SK's three points at approval, and what is built for each

| SK's point | What is built |
|---|---|
| Take the learnings of the treatment page; do not send several rounds of answers back to the operator | **One visit, one "done", for the whole plan.** Every plan question is on the same round: the shared rules, the gaps offered two ways, and every gap's shots. A gap offered two ways shows each way with its own shots, and "Take this way" accepts the gap in the same answer (on the card it was two questions). A change asked in the shared rules does not drop the gap answers given beside it. A second visit happens only for what the operator sent back, and then only those lines are open |
| The data properly saved and recorded; the user's side too | Each answer is saved on the page at the click and says so ("Saved on this page. It is recorded in VideoWizard when you say done in the chat."). On "done" every answer goes through the same server functions as the chat, each with its own log line by the operator with their words (design/205). An answer to a gap whose shots changed since is named as stale, never recorded. A refusal is written on its line and the other answers are still recorded |
| Show the gaps clearly so the operator can decide | Per gap: its name; what the operator accepted for it in the treatment; what changed since they accepted it; the totals and how the shots are made ("3 shots, 15.6 s in all. Made as: 2 × AI video, 1 × footage"); then the table (shot, made as, length, what it shows, over the words). On a narrow screen each shot is a small labelled block. The numbers in the top bar jump to their gap |

## Built

| Piece | Where |
|---|---|
| The plan's lines and the record of plan answers | `server/app/page_flow.py`: `_plan_page`, `_plan_answer`, `_table`, `_at_plan`; `page` and `page_record` call them |
| A way's shots before it is taken | `server/app/chat_flow.py`: `_gap_rows(session, gap, selection)` |
| The table, the ways, the jump, the "saved" line | `plugin/pages/decisions.html` |
| `vw visuals propose` points to the page; the page's step in the printed line; a page published by an older tool is published again to the same link (`republish`) | `plugin/scripts/vw.py` |
| Instructions | `plugin/commands/vw.md`; `scripts/d206_wording_v3.py`, `server/procedures/v3.json` (+99 words in the visuals stage) |
| Old way 80 (the card for the plan, kept as the way back) | `design/35-decision-log.md` |

**Different from the list below, on purpose:**
- Section 3 point 4 said a gap with two ways shows its shots in the next round. Built as one round (SK's first point).
- A round is one document of the page's database, which holds at most 256 KiB (the artifact runtime's contract on the builder PC; found by the reference-steps analysis). A plan too long for one document shows its first gaps and says how many more come after the next "done". A plan of 16 gaps is one round; the test's 40 gaps of 8 long shots is split.
- A run whose page was published by the older tool: the tool says to publish the page again to the same link first. Not in the list; without it the older page would show the gaps without their shots.

**Tests:** server `server/unit/test_design206_pure.py` (12); the whole `server/unit` suite passes. Plugin: `test_design204_page.py` (+1), `test_design204_cli.py` (+2); the plugin suite has the same 7 failures on this PC with and without this change. `server/tests/check_chat_card.py` repaired (it had not followed design/203's new argument).

**Checked in a browser on a local copy with a stand-in database and a round made by the server's own function:** the shared-rules line, a gap's table, the two ways, Accept, Change this with words (empty words kept the box open), Take a way, Undo, the jump, the phone width (labelled blocks, no sideways scroll).

**Not verified:**
- The page on claude.ai with a real plan, and the whole loop on an operator's machine (publish again to the same link, the write, the read). The first real plan is the test; the card is the way back.
- The 256 KiB limit in practice (taken from the contract file, not tried).
- A long plan split over two rounds, under real clicks.
- The treatment page was not changed; its own round is not capped (a treatment's lines are short).

---

Requirements as approved:

**Why:** SK, 16 Nov 2026: "Implement the claude artifact for the gaps that user has to accept or change, similar to what you implemented for Treatment page."

Builds on design/204 (the treatment on the page) and design/205 (the Direction alone first, the motion style). Live today: server 0.102.0, plugin 0.87.0.

## 1. Requirement

At the plan step the operator answers on the same Claude artifact page as the treatment, not on a card in the chat. The page shows each gap with its planned shots as a table. The operator chooses Accept or Change this (with their words) on each gap, returns to the chat and says "done". The assistant records every answer on the server in one call. The server stays the record. Where the page cannot be shown, the card is used as today.

## 2. What the plan step asks today (from `chat_flow._plan_items`)

| Kind | When it is asked | Answers | On the page in this change |
|---|---|---|---|
| A gap's shots | every gap not yet accepted | Accept, Change this | **Yes** |
| A choice of two ways | a gap the assistant offered two ways for | one button per way | **Yes** (proposed) |
| The shared rules | the film's shared rules changed after gaps were accepted | Accept, Change this | **Yes** (proposed) |

I propose all three. If only the gap's shots went on the page, the operator would answer the other two on a card in the chat and the rest on the page, in the same step.

## 3. How it works

1. **Same page, same link.** The run's page is the one published at the treatment. Once the treatment is recorded and a plan is proposed, `vw visuals page` gives the plan's lines; the page's heading reads "Plan".
2. **Same source as the card.** Every line is built by the function the chat and the card use (`chat_flow._plan_items`), so the page, the card and the chat cannot disagree.
3. **A gap's line shows:** the gap's name; "changed since you accepted it" with what changed, when it is asked again; the table of shots (number, shot, made as, length, what it shows, over the words); the totals line (shots and seconds).
4. **Order on the page:** the shared rules first (when asked), then the gaps in the film's order. A gap with two ways offered shows the two ways and their buttons; after "done" its shots appear in the next round.
5. **"Done" in the chat is the authority,** as at the treatment: answers are read from the page, recorded in one call through the same server functions as one answer at a time, and the page is brought up to date.
6. **After the last gap is accepted** the answer tells the assistant the next step, in the words the server already uses.

## 4. Unstated but expected

- Gaps already accepted are shown as "Recorded", so the operator sees the whole plan in one place.
- A gap sent back shows "With the assistant" with the operator's words.
- An accepted gap can be reopened from the page with the operator's words, while the plan is still open (the server's own function already takes a change on an accepted gap). After the visuals work has moved past the plan, the page says to ask in the chat.
- Gaps that wait behind the shared-rules question are listed under it by name and are not asked one by one (design/191).
- Each answer is a line in the run's log, by the operator, with their words (as design/205).
- An answer given in the chat instead is recorded with `vw visuals decide`, as today.
- The treatment's page behaviour does not change.
- All video categories: nothing in the lines is specific to one category; the table comes from the plan.

## 5. Edge cases

| Case | Handling |
|---|---|
| No plan yet (treatment recorded, plan not written) | The page says the treatment is recorded and the plan will appear here; nothing to answer |
| Every gap accepted | All lines "Recorded"; the note says nothing more to answer |
| "Done" with nothing answered | Nothing recorded; the assistant says so |
| "Done" with some gaps unanswered | The answered ones are recorded; the assistant says how many are open and gives the link again |
| "Change this" with no words | Refused on that line: the words are needed |
| Words over 2,000 characters | The page's box stops at 2,000 with a counter (as today) |
| The plan was proposed again after the page was filled (a gap's shots changed) | The answer names the older text and is ignored as stale; the new round shows the gap again with what changed |
| "Change this" on the shared rules, with gap answers in the same "done" | The shared rules are sent back first. The gap answers given beside it are still recorded: those gaps' own shots were what the operator saw. If the assistant's rewrite changes a gap, it is asked again with what changed |
| "Accept" on the shared rules | Every gap waiting behind it is accepted in the one answer, as today |
| A way chosen for a gap, and nothing else | Recorded; the next round shows that gap's shots to accept |
| A gap with many shots (20 or more) | The table scrolls sideways on a narrow screen; nothing is cut except "over the words", which stays at 220 characters as on the card |
| A plan with many gaps (30 or more) | One round document holds every line; the lines are text only. Checked against the round's size in a test with 40 gaps |
| The same gap answered twice (two tabs, or page and chat) | The second is named as stale; nothing changes |
| The earlier plan version cannot be read | Each gap is asked by itself and says so, as today |
| The run is taken over by another operator or machine | A new page is published and filled from the server (as design/204) |
| An open defect on the run | The server refuses the writes as today; the refusal is shown on each line |

## 6. Failure modes

| Failure | Handling |
|---|---|
| No artifact tools, or publishing fails | The card, as today; the assistant says once that the page is not available |
| Writing the round to the page fails | One retry, then the card |
| Reading the answers fails | The assistant asks for them in the chat, or shows the card |
| The server refuses one answer | The refusal is written on that line; the other answers are still recorded |
| An operator's plugin older than this release | Refused with the line that says to update (the page file changes, so the minimum rises) |
| The log row cannot be written | The answer is still recorded |

## 7. What is built

| Piece | Where |
|---|---|
| The plan's lines as data; the record call takes plan answers | `server/app/page_flow.py` (`page`, `page_record`) |
| The page draws a table with a header and a totals line; the heading follows the step | `plugin/pages/decisions.html` |
| The printed next-step lines name the plan | `plugin/scripts/vw.py` |
| The assistant's instructions for the plan step: the page first, the card where it cannot be shown | `plugin/commands/vw.md`, `server/procedures/v3.json` by a wording script |
| Old way: the card for the plan's gaps, kept as the way back until the page has carried one full plan on an operator's machine; then retired on SK's word | `design/35-decision-log.md` |

Server and plugin both change: the plugin minimum rises and every laptop updates.

## 8. Tests first

- Server (`server/unit`): the plan's lines for an open gap, an accepted gap, a gap sent back, a choice, the shared rules; answers recorded as the card records them; a stale answer ignored; a refusal kept on its line; the shared-rules case of section 5; 40 gaps in one round; the treatment's tests unchanged and passing.
- Plugin (`plugin/tests`): the page file holds the table drawing; `vw visuals page` writes a plan round.
- The page on a local copy with stand-in data: a table line, accept, change, undo, reopen.

## 9. Not covered

- The other five views of the visuals stage (reference drawings, references, pictures and graphics, AI video, recording) and the other stages.
- Pictures on the page: the plan's table is text only.
- The page under real clicks on an operator's machine: the first real plan is the test, with the card as the way back.
- "Accept all the rest" in one click: not asked for.
