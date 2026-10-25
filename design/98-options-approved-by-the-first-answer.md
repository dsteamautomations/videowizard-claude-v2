# design/98 — Fewer gates: the options approved by the first answer, a reject without a reason, the final narration by its click

25 Oct 2026. Revised the same day with SK's additions (parts B and C). **Nothing is built until SK approves this note.**

SK, verbatim:
- On the options step: "I am taking a conscious decision to remove this step because here the user is not going to do anything else. They are just going to approve it, and again, in the next lead, they are going to check. If you differ, this unnecessary approval stage is not required for me. Rather, you give the key project button here if you feel you can combine these two stages as well. I do not understand the difference between the option stage and the approve button there." ("key project" = Keep / Reject.)
- On the reject reason: "dont make the reject reason a mandatory field."
- On the voices page, Final tab: "A new user might not know that they will have to go back to the Claude chat to continue with all of the conversation. Can you ensure that there is bold text or a very visible area (purposefully drawing attention to it) which will ask the user to go back to the chat and continue with the next steps?"
- On the Narrations tab: "Now it does not look like a radio button, probably because of the background and the other UI elements… You will have to make this stand out or give a hint that this is what has to be clicked on. A subtle change is enough here." And: "the manual approval text that needs to be typed in is another gate which might not be needed because the user understands that he has to click on the checkbox or the radio button and then he clicks on the button. Providing another verbal input is redundant in my opinion. If you have it for any other purpose, let me know."

---

## A. The options are approved by the first answer

### A1. What the step does today

- **On the review page,** after the review film renders, the operator types their words and presses "Approve these options". Only then do the slide buttons appear; until then each row says "after approval".
- **In chat,** the assistant runs `vw options record --quote "<their yes>"`.
- **Both call `stage2.record_options`.** It writes the options stage's output, with the operator's words as `accepted_quote`. That output holds:
  - the current version's options document;
  - the review film's hash;
  - the package;
  - a summary.
- **It also sets `session['accepted']`.** That record moves the run from options to master.
- **Two things refuse without it:** a slide answer (`decide`) and the master build both say "Record the options stage first". The slide routes only accept a run at master.
- **A new version of the options** clears the approval, the answers, the master and the review film.

### A2. The change

| # | Rule | Where |
|---|---|---|
| D1 | **The slide buttons show as soon as the current version's review film is rendered.** "Approve these options" goes. The line under the film says: "Answer each slide; your first answer approves these options." | `templates/review.html` |
| D2 | **The first answer approves the options.** When a slide is answered while the run is at the options stage, the server records the options output in the same call, then saves the answer. The record keeps everything it holds today. Its `accepted_quote` reads "Approved by answering the review slides: first answer #3 KEEP" (with the note, if any), the operator's id and the time. The run moves to master, as today. | `stage2.decide`, `stage2.record_options`, the decide routes (they accept a run at options when its review film is ready) |
| D3 | **No answer before the film exists.** At the options stage with no rendered review film of the current version, an answer is refused: "The review film for this version is not rendered yet." | `stage2.decide` |
| D4 | **A new version still clears the approval, the answers, the master and the film.** This is unchanged. | unchanged |
| D5 | **Chat follows the same flow.** `vw master decide --slide N --action …` works at the options stage too, and its first answer records the options. `vw options record --quote` stays for an explicit approval but is not required. The procedure's options and master steps say: "watch the review film, then answer each slide (on the page, or `vw master decide`); the first answer approves the options." | `vw.py`, `server/procedures/v2.json`, `commands/vw.md` |
| D6 | **The record says how it was approved:** the summary gains `approved_by: 'first_answer'` and the slide. The page's top line says "Options approved by your first answer (#3, 10:42)". | `record_options`, `templates/review.html` |

**One line on keeping the step:** the only thing it adds is a typed sentence. The record, the film's hash and the version are all kept by D2, so I see no reason to keep it.

---

## B. The review page: where the operator clicks, and a reject without a reason

### B1. Where the operator clicks

The layout is unchanged; this is how it looks today, row by row.

- **The page has two columns.** The review film plays on the left. On the right is the slides table, with three columns: **#**, **Slide** and **Answer**. Under 980 px the table sits under the film.
- **Clicking a row** jumps the film to that slide. The row under the playhead is outlined as the film plays, and "Now: #3 …" shows over the film.

| Row (Slide column) | Answer column: the buttons, side by side as rounded pills |
|---|---|
| **A scene** (an option of a scene): the scene's name, its clips and seconds, its length and its cue time | **Keep · Reject · Keep with edit** |
| **A backup** (badge "backup for #3"): the same | **Keep · Reject · Keep with edit** |
| **A decision** (badge "decision"): its question ("keep or drop: the clip …") | **Keep · Drop** |
| **A blank** (badge "blank"): AI video or animation comes here | no buttons: "no decision: a blank for AI video or animation" |
| **A slide inside a rejected scene** | greyed, "no answer needed: …" |

- **After an answer,** the chosen pill is filled in the accent colour. Under the buttons a line shows the answer, its note or edit, and the time, for example "**REJECT** · too dark · 2026-10-25 10:42". Any answer can be changed until the master is built.
- **Keep with edit** opens a small inline form in the row: shot, in ±frames, out ±frames, then "Record edit" or "Cancel".

**Reference (Mobbin):** [Frame.io review](https://mobbin.com/screens/ee704edf-a186-4f30-98ed-e15525a6ac59) shows the film large on the left and the review list on the right, each item with its own actions and timestamp. That is our layout, so nothing moves.

### B2. The change: Reject without a reason

| # | Rule | Where |
|---|---|---|
| R1 | **Reject records at once,** with one click. Under the row, a small optional field "Why? (optional)" with "Save" lets the operator add a reason. The reason can also be added later. | `templates/review.html` |
| R2 | **The server accepts a REJECT without a note.** "REJECT needs the operator's reason" goes (design/44 8.5). | `stage2.decide` |
| R3 | **Chat follows:** `vw master decide --slide N --action REJECT` records without `--note`. The master step says the assistant may ask for the reason; it is no longer a required question. | `vw.py` (none needed: it already passes the note through), `server/procedures/v2.json` |

A reason is still worth having when given: rejection notes feed the client's learned rules (`vw master rule`). So the field stays, optional.

---

## C. The voices page

### C1. The Final tab: "go back to the chat" (SK)

Today the Final tab shows the final narration's table and, at the foot, small grey text: "Done. The run is at media."

| # | Rule | Where |
|---|---|---|
| F1 | **A large banner at the top of the Final tab**, once a narration is final: a green check, then in large bold type "**Done here. Go back to the Claude chat to continue.**" Under it: "In the chat, type: **what is next for VW-8**", with a **Copy** button for that phrase. It sits in a box with the accent-coloured border, full width, above the narration's table. | `templates/voices2.html` |
| F2 | **The footer says the same in bold:** "Done here: go back to the Claude chat to continue." This replaces "Done. The run is at media." | `templates/voices2.html` |

**References (Mobbin):**
- [Sentry, "Return to your terminal to complete your setup"](https://mobbin.com/screens/fdd7eb4e-aebb-4156-a431-0f08d283e667): a check mark and one bold line that says exactly where to go next.
- [Fabric, "Your email was confirmed! Return to the app to continue."](https://mobbin.com/screens/747e6342-1b91-4501-b769-1bd90a3d00b1): the large headline with the instruction under it.

### C2. The Narrations tab: the radio button (SK)

Today each ready narration's row starts with a 16 px browser radio button in a column headed "Final". On the dark background it doesn't read as something to click.

| # | Rule | Where |
|---|---|---|
| N1 | **A visible choice:** the radio grows to 20 px, with a light ring and the accent colour when chosen. The whole row is clickable to choose it, and the chosen row is outlined in the accent colour. | `templates/voices2.html` (CSS and one click handler) |
| N2 | **A hint above the table:** "Pick the narration you want as final (click its row), then press **Make this the final narration**." The column head "Final" becomes "Pick one". | `templates/voices2.html` |

**Reference (Mobbin):** [Fabric's choice list](https://mobbin.com/screens/dd123fd1-1cd4-4777-b1af-52eaa3cad8c3): whole rows as targets, a clear radio on the right, the chosen row outlined, then one Continue button. It is a subtle change, as SK asked.

### C3. The final narration needs no typed words (SK)

- **Today,** "Make this the final narration" needs "your words (required)", and the server refuses without them (`voices.finalise`). The words are kept as the voice stage output's `accepted_quote`.
- **Why the words could stay:** they are the audit trail for the operator's choice. The rule removes them anyway, because the click records the same facts: the narration, who chose it, when, and from where.

| # | Rule | Where |
|---|---|---|
| W1 | **The words box goes.** "Make this the final narration" records at once. The output's `accepted_quote` reads "Made final on the voices page by <name>", with the time. Words typed elsewhere still go in when given (chat). | `templates/voices2.html`, `voices.finalise` |
| W2 | **Chat follows:** `vw stage voice record --job ID` records without `--quote` ("Chosen as final in chat by <name>"). With the operator's reply it keeps the reply. The procedure says: "when they say which narration is final, `vw stage voice record --job ID` (their reply as `--quote` if they gave one)". | `voices.finalise`, `vw.py`, `server/procedures/v2.json` |

---

## D. Runs in progress

- **VW-9** is at the options stage. Today it can approve on the page with words, as before; nothing is lost. After the release, its first answer approves.
- **VW-8** is at voice. Today the final narration needs words, as before. After the release, the click alone records it.
- **Runs past these steps** are unaffected.

## E. Tests first

`server/unit/test_design98_pure.py`:
- A (D2–D6):
  - an answer at the options stage, with the review film ready, records the options and the answer in one call, with the quote and the summary of D2 and D6;
  - with no rendered film, the answer is refused;
  - a second answer doesn't record again;
  - a new version clears the approval and the answers;
  - `vw options record` still works.
- B: a REJECT without a note is recorded; with a note it keeps it.
- C: `finalise` without words records "Made final on the voices page by …", and with words keeps them.
- The pages:
  - `review.html` has no approval box, shows the buttons when the film is ready, and has the optional "Why? (optional)" field;
  - `voices2.html` has the Final banner with the copy phrase, the larger radio with clickable rows and the hint, and no required words box.

`plugin/tests`:
- `master decide` posts at the options stage, and a REJECT posts without a note.
- `stage voice record` posts without `--quote`.
- The procedure's options, master and voice steps carry the new sentences.

## F. Not covered

- `server/tests` (Docker).
- The pages in a browser beyond their content.
- An operator who answers one slide by mistake has approved the options. They can still change every answer, and Revise clears the approval.

## As built (25 Oct 2026)

SK approved the revised note ("Yes approved go ahead"), with the UI kept to the three changes above: no other page, colour or navigation changed. Server 0.45.0, plugin 0.43.0. The minimum plugin stays 0.42.0: a 0.42 plugin works with this server, so nobody is forced to update mid-run.

- `stage2.decide(conn, …)` validates the answer first, then records the options when none are recorded (`record_options(…, approved_by)`), then saves the answer. A REJECT needs no note. The reply carries `options_approved` on the first answer.
- The slide routes (`/master/decide`, the review page's decide) accept a run at options or master.
- The review page:
  - shows the buttons once the film is ready, with no approval box;
  - its top line and foot say the first answer approves;
  - a Reject records at once, with an optional "Why? (optional)" field and Save.
- `core.acceptance_quote`: a voice stage output without words records "Chosen as final in chat by …"; every other stage still needs words. `voices.finalise` records "Made final on the voices page by …".
- The voices page:
  - on the Narrations tab, the radio is 20 px with a ring, the whole row picks, the picked row is outlined, the hint sits above the table, the column head reads "Pick one", and there is no words box;
  - the Final tab has the banner with the copy phrase, and its footer is bold.
- The procedure's options, master and voice steps and `commands/vw.md` say the same.

Tests:
- `server/unit`: 369 passed, 9 of them new in `test_design98_pure.py`. Older tests changed: `test_review_page` (decide takes the connection), `test_design97_r3_pure` (the reject line), `test_design95_pure` (the minimum may sit below the plugin).
- `plugin/tests`: 257 passed, with 3 known Windows-only failures.
- The plugin is compile-checked, and both pages' scripts parse.
