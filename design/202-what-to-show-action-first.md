# design/202: the treatment step: what to show, why, and how the operator is asked

**Status:** requirements and implementation plan, revision 2 (15 Nov 2026), for SK's approval. No code written. Written by the monitor thread for the thread that builds.

## Built on 15 Nov 2026 (server 0.100.0; not deployed; SK's deployment approval awaited)

SK approved the requirements on 15 Nov ("Approved the requirement. go ahead with the implementation. wait for deployment approval").

| Built | Where |
|---|---|
| Each shot's two reasons, `fits_why` and `way_why`; a missing one is named in `reasons_missing` and reads "not given" to the operator; over 300 characters is refused | `server/app/visuals_stage.py` (`reasons_missing`, `treatment`) |
| `still_seconds`, `moving_seconds`, `still_share` in the totals; the warning `stills_many` above `VISUALS_STILL_SHARE` (default 0.10) | `visuals_stage.treatment`, `config.py`, `visual_contract.WARNING_PLAIN` |
| The Direction asked as "Do you accept the direction of the film?", with what a direction is, in full | `server/app/chat_flow.py` (`_treatment_items`, `DIRECTION_HELP`) |
| Each line shows every shot: made as, length, what the viewer sees, why it fits the words, why this way | `chat_flow._shot_rows` (the chat and the card read the same rows) |
| A line the operator sent back returns marked "changed as you asked", with what changed | `visuals_stage._carry_lines` (`asked`), `chat_flow._changed_text`, `chat_card.html` |
| The script's visual notes are no longer handed to the planner | `visuals_stage` (the package's `intended_visuals` is empty) |
| The instructions: the narration alone, meaning before a noun, the real thing first, action first, the order of the ways, a symbol at a glance, key pictures returning, a still moves, words on the picture by category, the two reasons; the masonry example removed | `scripts/d202_wording_v3.py`, `server/procedures/v3.json`, chained in `scripts/c1_split_v3.py` |
| Old ways 72 to 74 | `design/35-decision-log.md` |

**Three departures from the text below, each deliberate:**
1. **A missing reason warns; it does not refuse the draft.** design/195 (SK, 14 Nov): flags warn the user, they do not block. A refusal would also have stopped every older draft and 32 existing tests.
2. **The limit for stills is 10 %** until SK names a figure (20 % would not have warned on VW-21).
3. **The Claude artifact page (section 6.1) is not built.** It was tried with SK on the builder PC and works there; it still has to be tried on the operator's Mac under the plugin's guard. The card stays the way the operator answers.

**Tests:** `server/unit/test_design202_pure.py` (17 tests). The whole `server/unit` suite passes. No plugin file changed. Not run: the page suite, the live server, a real run.

**Corrected in the text below:** the picture-count instruction was already rewritten for the guide flow before this change; nothing was done there.

### Review of the first build (15 Nov, on SK's word; a reviewer who had not written the code, then fixes with tests first)

| # | Defect found in the first build (commit 40eb67b) | Fixed |
|---|---|---|
| 1 | Still seconds were wrong whenever a shot had no numeric seconds, or a gap of several ways had no shots: the whole gap was counted under its first way, so stills were lost or invented and the warning could be false | `still_and_moving`: counted shot by shot; what cannot be told is `unsplit_seconds`, never guessed |
| 2 | "Changed as you asked" was lost when the assistant sent the draft again before the operator saw the line, and the list of changes was then against a draft the operator never saw | The line keeps `asked` and `was` (what the operator was looking at) until they answer it |
| 3 | The gap's own `why` was no longer shown; a draft saved before the change read "not given" on every shot | The `Why` row is back; "not given" appears only on a draft made after the reasons were asked |
| 4 | The still warning could say "10 % of the film: above 10 %", and a share just over the limit could be missed | Compared before rounding; shown rounded up to a tenth |
| 5 | A reason that was a list, a number or only spaces counted as given and was shown as raw data | Only text counts (`reason_text`) |
| 6 | A shot's way outside the five was accepted and counted as moving | Refused by name |
| 7 | The preparation text still said to read the script's notes file first | Rewritten; the wording script now stops if a sentence it removes was reworded |
| 8 | The card's header still said "Changed since you last saw it" for a line changed as asked | Both the header and the list say "Changed as you asked" |
| 9 | A shot's way that is not text could break the question | Guarded |

Tests: `server/unit/test_design202_review_pure.py` (18 tests); the whole `server/unit` suite passes (1,653).

**Left as it is, and why:**
- The first step line of the visuals stage still lists `intended-visuals.json` among the files to read. The file is written empty; the step lines are built by another script's chain, and the change was not worth the risk.
- Older crashes on the same lines, not from this change: `shots` that is a list of words or a dictionary; an `fps` of `'25 fps'` or `'0'`.
- A footage frame held still (`frozen_seconds`) is not counted as a still picture; the frozen share already warns on it.
- A line the assistant rewrites back to exactly what the operator sent back shows as changed with no list.

**Not errors, but risks for a deployment:**
- **The card is larger.** On VW-21's eight gaps the card grows from about 10,700 to about 15,400 characters, all of which the assistant copies out to show it. A card of ten lines with long reasons may arrive cut or broken. Not seen on a real run.
- **A run that is at the treatment when this is deployed** (VW-24 was) keeps its draft: its lines show without reasons until the assistant sends the draft again.
- **How well the assistant writes the two reasons** is seen only on a real treatment.

**The trial artifact page (section 6.1) is not part of this build.** Reviewing it as it stands (`scratchpad/treatment-trial.html`, published privately): it must not be used for a real run before these are fixed:
1. An answer given to an older text of a line stays shown after the line is rewritten, unless the assistant deletes it in the same write (`for_rev` is stored but not checked by the page).
2. The page redraws on every change from the database, so the box the operator is typing in loses its place when the assistant updates a line at that moment.
3. If the Direction is un-accepted after gaps were answered, the gap answers stay in the database; the assistant must ignore them.
4. A failure to load the answers is silent: the lines read as unanswered.
5. No limit on the typed text (the server's strictest field is 2,000 characters); no rule yet that only the owner may answer if the page is shared.

---

**Revision 2 takes in SK's comments of 15 Nov on VW-24** (the latest plugin):
1. The script's visual notes are not to be considered.
2. Each line must show why: why the picture fits the words, and why it is made this way.
3. "Change this" must make the change and confirm it to the operator.
4. The Direction was not seen as a step of its own in VW-23 and VW-24; it must be presented first, by itself, and approved.
5. Where the operator answers (the chat, or a page) is open: section 6.

Research behind the rules: `videobuilder-v4/research/what-to-show-rules-15-nov.md`. Worked example: `videobuilder-v4/research/vw21-treatment-before-after.md`.

## 1. What was found on VW-24 (read from the code, server 0.99.3)

| SK's observation | What the tool does today | Cause |
|---|---|---|
| "The direction window did not come to us" | The Direction **is** asked first and alone (`chat_flow._treatment_items`). On VW-24 it was accepted at 06:37 UTC. | The question the operator sees is "Do you accept this line?": `_split(question)[1]` drops the heading "The direction of the film". The assistant posts the Direction as its own text, where it can be shortened. Nothing on screen says "this is the Direction". |
| The line says what is shown, not why | A line shows: the picture, made as, length, pictures to make, shows, held still. A "Why" row exists but nothing requires the assistant to fill it. | No field, no rule. |
| Is there a confirmation after "Change this"? | A changed line comes back as "to accept", marked "(changed since you last saw it)" with a "What changed" list (design/191, section 11 B2). | Present in the code; not confirmed on a real run. |
| The card | Up to 12 lines on one card, more as cards of 10 (`CARD_ALL`, `CARD_PART`). The page is fixed (`chat_card.html`); the server fills it. | See section 6: the assistant must re-type the whole card to show it. |
| The kiln | The assistant followed the team's script notes ("brick kilns emitting smoke"). Instruction 32.8 tells it to treat those notes as a stated requirement. | An instruction, now withdrawn by SK. |

## 2. Requirement

At the treatment the operator first approves the film's Direction, shown by name and in full. Then, for every shot of every gap, the operator sees what the viewer will see, how it is made, **why the picture fits the words** and **why it is made this way**, and accepts or changes it. A change is made and shown back before it counts. The assistant chooses each picture from the narration alone, looks first for a person doing something, and proposes AI video before a still.

## 3. What changes

### 3.1 The Direction (server, `chat_flow`)

1. Its question is "Do you accept the direction of the film?" (never "this line").
2. It is shown in full, word for word, from the server: as a card of its own, or on the page (section 6). The assistant does not retell or shorten it.
3. No gap line is shown until it is accepted. (Already so; kept and tested.)
4. Under it, two lines of help for the operator: what a Direction is ("what the viewer should understand by the end, and how the film will show it") and what accepting it means ("every gap's line is written from it").

### 3.2 Each shot's two reasons (server, `visuals_stage.treatment`)

1. Every shot of a gap carries two short texts, written by the assistant:
   - `fits_why`: why this picture fits the words, and what the viewer understands better with it.
   - `way_why`: why it is made this way: whether a real clip could do it, why a diagram and not a photo, why a still and not a video.
2. A gap with one way and no shot list carries both on the gap line.
3. Either one missing or empty: the draft is refused, naming the gap and shot.
4. Each at most 300 characters, so it stays one or two sentences.
5. Both are shown with the shot, under "What the viewer sees" and "Made as".

*Simpler than revision 1:* the shot's `job` word and `still_reason` are dropped. The two reasons say the same in the operator's language.

### 3.3 "Change this"

1. The operator's words are recorded with the line. (As today.)
2. The assistant rewrites only that line and sends the draft again. (As today.)
3. The line comes back marked **Changed as you asked**, with before and after for each thing that changed (the picture, the way, either reason, the length), and waits for Accept. (design/191 B2, extended to the two reasons.)
4. The assistant says one line: "N lines were changed as you asked and are back for your answer."
5. If the rewrite changed nothing, the server says so and the line stays "sent back"; it is never shown as changed.

### 3.4 How the assistant chooses (instructions, `server/procedures/v3.json`, section 2 TREATMENT)

New general rules:
1. **The narration alone.** The picture is chosen from what the narrator says. The script's visual notes are not used and not cited. (Instruction 32.8 is removed; the treatment entry no longer carries "the team's intended visuals".)
2. **Meaning, not a word.** Choose from what the sentence tells the viewer, not from a noun in it.
3. **The real thing first.** A tangible object or action the camera can point at, before a general view.
4. **Action first.** For anything a camera could film, first ask who is doing what; write the picture as a person doing one action that shows the meaning.
5. **Order of the ways for a scene:** real footage that shows it; else AI video; else a still, with the reason in `way_why`.
6. **A symbol only if it reads at a glance;** otherwise literal.
7. **Repeat the film's key pictures:** the same person, place or object returning.
8. **A still always moves** (a slow push or drift).
9. A diagram stays for what a camera cannot see or what must be read exactly. Unchanged.

Filed by category:
- Advertisement and social films: key words on the picture, three words or fewer at a time.
- Documentary and explainer: no words on the picture beyond a diagram's labels; the subtitles carry the words.

Wording corrected:
- The opening-gap instruction loses its masonry example.
- "People, purposeful work and the material changing under their hands carry the film" moves to the documentary category.
- The picture count line is rewritten for the guide flow: one still per AI video shot.

### 3.5 Moving and still (server, `visuals_stage.treatment`)

1. The totals gain `moving_seconds`, `still_seconds` and `still_share` (stills as a share of the film).
2. `still_share` above the limit raises one warning: "Still pictures are N % of the film: above L %. Make some of them moving shots."
3. The limit is a setting, `VISUALS_STILL_SHARE`. **Open: SK's figure.** VW-21's stills were 13.5 % of the film, so 20 % would not have warned on it; 10 % would.

## 4. Unstated but expected

- Real footage is never replaced by an AI video.
- The AI video limits stay (three kinds of action, a take of 3 to 15 s, at most four people, no circling camera). An action that fits none is reshaped; if that distorts the meaning, a still, and `way_why` says so.
- An AI scene stands for a typical scene, never for the client's own site, people or result.
- The cost estimate rises with more video and is shown before acceptance, against the cap.
- A treatment recorded before this release is still read; only a new draft needs the two reasons.
- Old ways (SK's rule of 30 Oct), listed in design/35: "the script's visual notes as a requirement" retired; "a treatment shot without its two reasons" retired and refused by name.
- One flow, two front ends: whatever is added to the chat's lines is added to the page's lines, from the same server function.

## 5. Edge cases

| Case | Handling |
|---|---|
| The operator wants a picture the script's notes described | "Change this" with their words; the operator's words are the source |
| A reason that only repeats the picture ("a kiln because the line is about kilns") | Not checked by the server; the operator reads it and can send it back. The instruction says a reason names what the viewer understands |
| A footage shot | Both reasons required; `way_why` is normally "a real clip shows it" |
| A drawn graphic | Both required; counted as moving |
| A film with no people (a product, software) | Stills and graphics throughout; the still warning fires once; the Direction states the reason |
| A gap shorter than 3 s | AI video allowed (made at 3 s, trimmed); under 1 s on screen stays a picture |
| The action needs a vehicle, a crowd, speech or night | Not available as AI video: reshape, or a still with the reason |
| The Direction is sent back | No gap line is shown; every line is written again from the new Direction (as today) |
| The Direction changes after gap lines were accepted | Those lines return to "to accept", each showing what changed (as today) |
| "Change this" with no words | Refused: words are required (as today) |
| The operator changes their mind on an accepted line | They say so in the chat; the assistant sends that line back with their words |
| A draft from an older plugin with no reasons | Refused with the two field names and one example of each |
| The still-share setting missing or not a number | The default is used |
| `still_share` exactly at the limit | No warning |
| A film with no measured length yet | `still_share` left out, as the frozen share is today |

## 6. Where the operator answers: decision for SK

SK's question: does the card add work for Claude every time, and should the operator answer in the chat or on a page?

**It does add work.** To show a card, the assistant must copy the whole card page into its reply "character for character" (`CARD_HOW`). A card of 10 lines is thousands of characters, re-typed at every card, every revision and every plan version. It costs time and tokens, and a single dropped character breaks the card. The card is also limited to 10 or 12 lines, and its answers travel back through the message box.

| | A. The card in the chat (today) | B. A page on the server |
|---|---|---|
| Load on the assistant | Re-types the card each time | None: it prints a link |
| Lines at once | 10 to 12, then another card | All of them |
| Answering | Buttons on the card, then "Submit all", then Enter in the message box | Buttons on the page record at once |
| Confirmation of a change | In the next card | On the page, where the line is |
| Look | Limited by the chat's card | The fixed layout SK liked: sections, colours, lines between blocks |
| Sign-in | None | The server's sign-in, as for the review page |
| Risk | The card arrives broken or cut | The operator has to come back and say "done" |

**Recommendation: B for the two steps with many lines (the treatment and the plan); the chat for single decisions (one picture, one take).** The review page is the proof: at the options step SK gave 13 answers in three minutes on it. The page already exists (`/runs/<code>/visuals`, Treatment and Plan tabs); it would be restyled to the fixed layout and gain the two reasons, not built anew. A claude.ai artifact cannot do this: it cannot write to our server and would have to be rebuilt for every run.

How B works for the operator:
1. The assistant says: "The treatment is ready. Open this page, answer each line, then tell me you are done," and prints the link.
2. On the page: the Direction first, alone. After it is accepted, every gap with its shots and reasons, Accept and Change this on each.
3. The operator returns to the chat and says "done".
4. The assistant runs `vw visuals next`. If lines were sent back it rewrites them and sends the operator to the page again; otherwise it goes on to the plan.

With B, the card (design/190) is kept as the fallback until the page has carried one full film, then retired on SK's word.

### 6.1 Revision 3 (SK, 15 Nov): the server page is on hold; a Claude artifact assessed

SK: the server page was tried before and was cluttered, which is why the work moved into the chat. **Option B is on hold.** SK's question was about a **Claude artifact** (a page published on claude.ai by the assistant), not a server page. Section 6 above wrongly said an artifact "cannot do this"; that is withdrawn.

**Option C: one Claude artifact as the decision page.** Read from the Artifact tool's own contract (runtime capabilities `db` and `assets`, available on SK's account in the builder's session):

- The page is one fixed file kept in the plugin. The assistant publishes it by its file path; it does not re-type it.
- The lines to decide are **data**, written by the assistant into the artifact's own database (one write of several rows). The page draws whatever rows it finds and updates live when a row changes.
- The operator's answers are rows the page writes. The assistant **reads them back** with the database tool when the operator says "done", and records each one on the server with the same `vw` commands as today. The server stays the record; the artifact is the form.

| Path | How it works with the artifact |
|---|---|
| Accept | The page writes the answer row. Nothing reaches the server until the operator says "done" in the chat |
| Change this | The page asks for the operator's words and writes them. After "done", the assistant sends the line back on the server, rewrites it, and updates the row: the page shows the new text marked "Changed as you asked", with before and after, and asks again |
| Reject (later steps: a picture, a set, a take) | As Change this: the words are required |
| Undo before "done" | Free: the operator presses the other button; the row is overwritten |
| Undo after "done" | The page offers "Reopen" on a recorded line; it writes a change request with the operator's words; the assistant sends the line back on the server (`treatment --send-back`, or `revise` once the step is recorded) |
| The operator answers some lines and leaves | Nothing is lost; the rows stay. The assistant records only on "done" and tells the operator which lines are still open |
| The server refuses an answer | The assistant writes the refusal into the row; the page shows it on that line |
| A new draft or plan version while the page is open | The assistant rewrites the rows; the page updates by itself; an answer given to the old text is dropped and the line asks again |
| The page and the server disagree | The server wins. After every "done" the assistant writes each line's recorded state back to the page |
| Pictures, drawings and takes (steps 3 to 7) | The page cannot load pictures from our server. The assistant uploads each file to the artifact's own store first (pictures, PDFs and videos are accepted, up to 15 MB each). It works, at the cost of an upload per item |

**What is not known and must be tried before any of this is built**

1. Whether the operator's Claude on the Mac has the Artifact tool and its database tool. This was read on the builder PC only.
2. The plugin's guard blocks every tool but `vw`, the run folder and questions. It must allow these two tools.
3. Each database write may ask the operator for permission unless allowed in the settings.
4. The artifact is private to the account that published it. If it is shared, anyone with access could answer, so it stays private and the operator's "done" in the chat is the authority.
5. Client material (the treatment text, later the pictures and takes) is stored on claude.ai, under SK's account.
6. Nothing here has been run. A trial is the first step: one page, VW-21's treatment as rows, SK answers, changes and undoes on it, and the answers are read back.

## 7. Implementation plan

| Step | What | Where | Depends on |
|---|---|---|---|
| 1 | Tests for 3.1 to 3.5 (section 8) | `server/unit` | Approval |
| 2 | The two reasons, the refusal, the totals, the still warning | `server/app/visuals_stage.py` (`treatment`, `_carry_lines`, `_diff`), `config.py` | Step 1 |
| 3 | The Direction's own question and help lines; the two reasons in each line; "Changed as you asked" | `server/app/chat_flow.py` (`_treatment_items`, `_split`, `_message`) | Step 2 |
| 4 | The instructions: nine rules, 32.8 removed, the category filing, the three corrections | `server/procedures/v3.json` and its wording scripts in `scripts/`; `plugin/commands/vw.md` if it repeats them | Step 1 |
| 5a | If A: the card shows the reasons and the Direction card | `server/app/chat_card.html`, `chat_flow._card_code` | Step 3 |
| 5b | If B: the page's Treatment and Plan tabs restyled, the reasons shown, the Direction first; `vw visuals next` prints the link and waits for "done" | `server/app/templates/visuals.html`, `server/app/web.py`, `chat_flow.next_item`, `plugin/scripts/vw.py` | Step 3 |
| 6 | design/35: the old ways; version numbers; the plugin minimum if the plugin changed | `design/35-decision-log.md`, `server/app/config.py`, `plugin/.claude-plugin/plugin.json` | Steps 2 to 5 |
| 7 | The unit suite (`server/unit`), the plugin tests, and for 5b one page test on a local copy | | Step 6 |
| 8 | Commit and push; deploy on SK's explicit yes (the workers restart; never while a run's job is running) | | Step 7 |
| 9 | The proof: on the next real run, the treatment's lines beside VW-21's, and the Direction seen and approved by name | The monitor thread | Step 8 |

Steps 1 to 4 are the same for A and B. Only step 5 differs: 5a is the smaller change; 5b removes the assistant's load.

## 8. Tests first

- The Direction: its question names it; no gap line is offered before it is accepted; sent back, none is offered.
- The two reasons: missing on a shot, missing on a single-way gap, empty, over 300 characters, present.
- A recorded treatment from before the change is still read.
- "Change this": a changed reason appears in the list of what changed; a rewrite that changed nothing is not shown as changed.
- Totals: `moving_seconds`, `still_seconds`, `still_share`; left out with no film length.
- The still warning at, above and below the limit; with the setting changed.
- The instruction text holds the new phrases; it no longer holds instruction 32.8 or the masonry example (the suite pins phrases).
- 5a: the card holds the reasons for each shot. 5b: the page shows the Direction alone first, then the lines with their reasons, and its buttons call the same server function as the chat.

## 9. Not covered

- Whether AI video holds attention better than a slowly moving still: no source measured it; this follows SK's ruling.
- The quality of a reason: the server checks that it is there, not that it is good. The operator is the judge.
- "Wide first, then closer" for AI video shots, switched off on 12 Nov: not changed here.
- The plan step's own display: the same two reasons could be carried into each plan shot later.
- Where the film will play (social feed, public screen): filed by category instead.
- Time and risk of more AI video: about three times the estimate and about 50 minutes of guide rendering on the VW-21 example, on the least proven step.
