# design/204: the treatment answered on a Claude artifact page

**Status:** built on 15 Nov 2026 (server 0.101.0, plugin 0.86.0, plugin minimum 0.86.0); **not deployed**; SK's deployment approval awaited. SK approved the list on 15 Nov ("Agreed for B first and then A. Yes for tests. Go ahead").

## Built

| Piece | Where |
|---|---|
| The page (fixed sections, the Direction, each gap with its shots and two reasons, the buttons the server gives, undo, reopen, a 2,000-character box with a counter, only changed lines redrawn) | `plugin/pages/decisions.html` |
| The lines as data, and the answers recorded in one call | `server/app/page_flow.py` (`page`, `page_record`); routes `/visuals/page`, `/visuals/page/record` in `server/app/main.py` |
| `vw visuals page`, `--url`, `--record` | `plugin/scripts/vw.py` |
| The guard: only the plugin's page may be published; a round is written from its file inside the run folder; answers are read into the run folder; nothing else | `plugin/hooks/guard.py` |
| The instructions | `plugin/commands/vw.md`; `scripts/d204_wording_v3.py`, `server/procedures/v3.json` |
| Old way 76 (the card, kept as the way back) | `design/35-decision-log.md` |

**How the data is laid out, as built (simpler than section 3 below):** each call writes one new document, `rounds/<round>`, holding every line of the step; the page shows the newest round; the operator's answers are documents under `rounds/<round>/answers`. The assistant never updates or deletes anything on the page, so it needs no version numbers: one `set` from a file per round, one `list` into the run folder per "done". Only the page's owner can write (a database rule, checked on the builder PC: an editor's write is refused).

**Tests:** server `test_design204_pure.py` (13); plugin `test_design204_page.py` (5) and `test_design204_cli.py` (4). The whole `server/unit` suite passes (1,688). The plugin suite: 484 pass; the same 7 tests fail with and without this change on this PC.

**Tried for real, on the builder PC only:** the page published from the plugin's file with the owner-only rule; a round built by the server's own function written to it in one call; an answer document saved by a list into a folder and read back in the shape the plugin expects. Trial page: https://claude.ai/artifact/RrA9bKebgdTJEu4zfy9mvG

**Not verified:**
- The page under SK's clicks in this final form (the trial of the earlier page was clicked; this one was only loaded with data).
- The whole loop on the operator's Mac: the Artifact tools there, the guard with them, a permission prompt on each write.
- No page test with a stand-in database was written; the page's logic is checked by reading and by the real round trip above.
- The artifact's name: every run's page is called "VideoWizard Decisions" (the page's own title wins over the name given at publish).

---

Requirements as approved:

**Why:** SK, 15 Nov: "Claude artifact implementation is required. Since the experiment is a success we need to replace the chat with the artifact page link… For now, for the treatment, the direction and the gaps." The trial of 15 Nov on the builder PC worked: the page was published from a file, nine rows were written in one call, SK's answer on the page was read back, and a rewritten line was written to the page.

Builds on design/202 (the two reasons, the Direction by name) and takes in design/203 (the Direction in six parts, "Show me a different direction").

## 1. Where the operator decides today, and where a page would be needed

**The visuals stage** (exact, from `server/app/chat_flow.py`): 18 kinds of decision in 7 groups.

| Group | Kinds of decision | Content | In this change |
|---|---|---|---|
| Treatment | the Direction; a gap's line | text | **Yes** |
| Plan | the shared rules; a choice of two ways; a gap's shots | text, tables | later |
| Reference drawings | a thing's drawing set | pictures | later |
| References | use the footage picture, make a set, or ignore; a set to make (paid); a set made | pictures | later |
| Pictures and graphics | an open question; a still; a graphic; a drawing's sizes; a picture reused | pictures, tables, short videos | later |
| AI video | the shot's layout drawing; the still; the word to shoot (paid); the take | pictures, video | later |
| Recording | a gap recorded into the film | yes or not yet | later |

So the visuals stage needs **one page with seven views**, the first of which is built here.

**The other stages** (counted from the instruction text, so approximate): the assistant asks the operator in the chat at intake (what was removed), the brief (category, values, rules), the script (claims), media (the clip list, the film's shape, the camera sound), analysis (clips already in the library; a refused clip), assembly (the fills) and delivery (the confirmation and the final word): about 15 questions in 7 stages. Three stages already have a page on the server: the voice, the options and master review, and the master film. None of these is in this change.

## 2. Requirement

At the treatment step the operator answers on one Claude artifact page, not on a card in the chat. The assistant gives the link; the operator answers the Direction, then the gaps; the operator returns to the chat and says "done"; the assistant records the answers on the server and goes on. The server stays the record. When the page cannot be used, the card is shown as today.

## 3. How it works

1. **One fixed page**, a file in the plugin (`plugin/pages/decisions.html`). The assistant publishes it by its path once per run; it never types it.
2. **The lines are data.** `vw visuals page` asks the server for the open lines (the same lines `vw visuals next` gives, from the same function) and writes one small file per line in the run folder. The assistant writes them to the page's database in one call, from those files.
3. **The operator answers on the page:** Accept, Change this (their words, at most 2,000 characters, with a counter), and on the Direction, Show me a different direction (design/203). Any answer can be undone until "done".
4. **"Done" in the chat is the authority.** The assistant reads the answers from the page into files in the run folder and runs `vw visuals page --record`: one call records every answer through the same server functions as the card.
5. **The page is brought up to date** from the server's answer: recorded lines show "Recorded"; a line sent back shows "With the assistant"; a rewritten line shows "Changed as you asked" with before and after; the next lines (the gaps, after the Direction) appear.
6. **The Direction first.** The page shows the Direction alone. The gaps appear only after it is recorded as accepted, as the server already rules.

## 4. Every path

| What the operator does | What happens |
|---|---|
| Accepts every line, says done | All recorded in one call; the page shows them recorded; the assistant goes on to the plan |
| Change this on a line | Their words are saved. After done: the line is sent back on the server; the assistant rewrites it; the page shows the new text, "Changed as you asked", before and after; it waits for an answer |
| Show me a different direction | Recorded as a change request with fixed words; a second Direction appears beside the first, each with how it answers the brief and what it risks; the operator accepts one |
| Changes the Direction after gaps were answered | The gap answers are dropped on the page and not recorded; every gap line is written again from the new Direction |
| Undo before done | The answer is removed; the line reads "To answer" |
| Reopen after done | Allowed while the treatment is not yet recorded as a whole: the page writes a change request with their words; the line goes back on the server. After the whole treatment is recorded, the page says to ask in the chat (a revision of an accepted treatment is its own step) |
| Says done with lines unanswered | The answered ones are recorded; the assistant says how many are still open and gives the link again |
| Says done with nothing answered | Nothing is recorded; the assistant says so |
| Answers, then never says done | Nothing is recorded; the answers wait on the page; `vw next` reminds the assistant that the treatment is open |
| Types in a box while the assistant updates the page | The box keeps its text and its place; only the lines that changed are redrawn |
| Answers a line whose text has since changed | The answer is void: each answer carries the line's revision, and the page and the server both ignore one given to an older text |
| Two answers at the same moment (two tabs) | The last one wins on the page; the server records what is there at "done" |
| The server refuses an answer | The refusal is written on that line of the page, in the server's words |

## 5. Failure modes

| Failure | Handling |
|---|---|
| The assistant's Claude has no artifact tools (not on the Mac, or blocked) | `vw visuals page` is not used; the card is shown as today. The assistant says once that the page is not available |
| Publishing the page fails | The card |
| Writing the lines to the page fails | One retry, then the card |
| Reading the answers fails | The assistant asks the operator to say them in the chat, or shows the card |
| The operator is signed out of Claude in the browser | The page says so; nothing is lost |
| The run is taken over on another machine or by another operator | The page belongs to the first operator's Claude account. A new page is published and filled from the server; the server holds every recorded answer |
| The page is shared with someone else | Only the owner can answer (a database rule); others can read |
| The page's database holds lines of an earlier step | Each write replaces the step's lines; answers to lines that are gone are deleted |

## 6. What is built

| Piece | Where |
|---|---|
| The page: fixed sections, the Direction, the gaps with every shot's picture, way and two reasons, three buttons, undo, reopen, a counter on typed text, redraw of changed lines only, answers tied to a line's revision | `plugin/pages/decisions.html` |
| The lines as data, from the function the card uses | `server/app/chat_flow.py` (`next_item` gains the lines as rows; `card_answer` takes answers by line) |
| `vw visuals page`: writes the line files; `--url` keeps the page's link for the run; `--record` reads the answer files and records them; prints what the assistant does next | `plugin/scripts/vw.py` |
| The guard allows the two artifact tools, only for the plugin's page file and files inside the run folder | `plugin/hooks/guard.py` |
| The assistant's instructions: publish once, write the lines, give the link, wait for "done", record, update; the card when the page is not available | `plugin/commands/vw.md`, `server/procedures/v3.json` (visuals, treatment) |
| Old way: the card for the treatment is kept as the fallback until the page has carried one full treatment on the operator's Mac, then retired on SK's word | `design/35-decision-log.md` |

Server and plugin both change, so the plugin's minimum version rises and every laptop updates.

## 7. Tests first

- Server (`server/unit`): the lines as rows for the Direction and for a gap; answers by line recorded as the card records them; an answer to an older revision ignored; the Direction's change drops gap answers; lines unanswered are named.
- Plugin (`plugin/tests`): `vw visuals page` writes one file per line; `--record` sends what the answer files hold; the guard allows the two tools for the page file and run-folder files and blocks them elsewhere.
- The page: one page test on a local copy with a stand-in database: accept, change, undo, reopen, the counter, a line rewritten while typing.
- Not testable here: the artifact tools on the operator's Mac. The first real treatment is the test, with the card as the way back.

## 8. Not covered

- The other six views of the visuals stage and the other stages (section 1).
- Pictures and video on the page (they need an upload per item; first needed for the reference drawings).
- Whether each write asks the operator for permission on the Mac. If it does, the assistant's settings need one line; found on the first run.
- Client material on claude.ai: the treatment's text is stored in the page's database under the operator's Claude account.
