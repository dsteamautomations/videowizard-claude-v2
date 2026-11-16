# The reference steps on the Claude artifact page: analysis

16 Nov 2026. Read only: no code changed, nothing deployed, nothing run against the live server. `page_flow.py`, `chat_flow.py`, `decisions.html` and `vw.py` were being edited by another builder while this was read; line numbers are as read today.

## Verdict

1. **Feasible.** The reference steps fit the page model with little new server logic: the chat already keeps step-1 answers and records them in one call, and step 2 already takes all its answers in one call.
2. **Pictures are the only real unknown.** No picture has been shown on the page yet. Two methods should work by the platform's written contract; neither has been tried here. One short experiment settles it before any build.
3. **Recommended picture method:** one labelled side-by-side picture per line (the sheet `chat_flow.sheet_of` already makes), embedded as a small JPEG in its own database document, written from files in one batch call. The fall-back is uploading the same sheets to the page's asset store. Loading pictures from the VideoWizard server by link will very likely not work.
4. **Round trips:** one "done" for step 1, a wait while the sets are made, one "done" for step 2, plus one more "done" for each cycle of sets made again. Today the chat asks one question per thing in each step.
5. **A fault found on the way:** one database document may be at most 256 KiB. The design/206 test allows a round up to 900,000 bytes (`server/unit/test_design206_pure.py:162`). A large plan round could be refused by the page's database. The builder of design/206 should know now.

---

## 1. What the reference steps ask today

The order is fixed in `chat_flow._candidates` (line 657): after the plan, `_drawing_items`, then `_round_items`, then `_waiting_items`, `_guide_items`, `_record_items`. The reference steps are the first two.

"Two phases" means the two steps of the reference round (design/79, design/151), in the server `rd['pass']`: `1`, then `'making'`, then `2`, then `'complete'` (`visuals_stage._round_pass`, line 2964). A drawing set, when a thing has one, is asked before step 1.

### 1.1 The questions

| # | Question (item id) | When | What the operator is shown | Buttons | Paid? | Recorded by |
|---|---|---|---|---|---|---|
| D | A thing's drawing set (`drawing:<element>:<sha>`) | A drawing set has status `proposed` (`chat_flow._drawing_items`, line 400). Before step 1: `round_done` refuses while a drawing is open (`visuals_stage.py:3260`) | Every labelled sheet of the set (`labelled_key`, PNG in storage), the facts with a source, the sizes that are assumed | Yes · Correct it (words needed) | No (`vw drawing set` is free) | `drawings.verdict` (`drawings.py:121`), by the set's exact digest |
| 1a | Step 1, a thing the footage shows (`round1:<element>`) | Round at pass 1, one thing at a time (`_round_items`, lines 302 to 336; `open_[:1]`) | Up to 4 footage frames (`frames[:4]`, line 335) | Yes, use it · Leave it out | No for a thing: the footage picture becomes its reference (`_from_footage`, line 2899). **Yes for a person, and for a thing with approved drawings:** a set is still made | Kept in the session (`chat_round`) until the last thing is answered; then one `V.round_done` for all (line 329) |
| 1b | Step 1, a thing the footage does not show | Same | No picture | Yes, make one · Leave it out | **Yes**: one set | Same |
| 2a | Step 2, a person's set (`set:<element>:<set id>`) | Round at pass 2 or `'making'`, the set is back and not answered (line 344) | The 3 pictures of the set, and one side-by-side picture with a letter on each (`sheet_of`, line 259) | Yes · No · Correct it (words) | **No and Correct it are paid:** the set is made again | `V.set_answer` (line 3118) stores it; `flush_sets` (line 628) records through `V.round_sets(partial=True)` (line 3007) |
| 2b | Step 2, a thing's set | Same | Same | Use A · Use B · Use C · None of these; more: Correct it (words) | **None of these and Correct it are paid** | Same. "Use A" is Yes with the starting ("golden") picture |
| 2c | A set that was not made (`setmake:<element>`) | The set was refused or did not come back, and nothing stands in its way (lines 370 to 379; `V.set_cause`) | No picture | Make it · Leave it out | **Make it is paid** | `V.set_make` (line 3195) or `V.set_aside` (line 3221) |

A set is 3 pictures (`SET_MAX = 3`, `visuals_stage.py:1818`). Its price is 3 × the Gemini image price (`_set_budget`, line 3158); the server prints the rupee figure (`cost_inr`). A remake that the spend cap does not allow is held: the answer is kept and waits (`round_sets`, lines 3056 to 3059).

### 1.2 Where the pictures come from today

- Each picture is a storage key under the run: `<run id>/visuals/references/<ref id>.png` (`_ref_key`, line 43); the side-by-side sheet is `<run id>/visuals/chat/set-<hash>.jpg` (line 261), three 660 × 720 tiles, JPEG.
- In the chat, the tool downloads every `show` file into the run folder, `work/chat/` (`vw.py:2054`, `_download`), through `/api/runs/{run_id}/files/{key}` (`files.py:54`). That route needs the laptop's sign-in and answers with a redirect to a signed storage link (`files.py:62`). The assistant then shows the local files.
- On the server's own visuals page, pictures load from `/runs/{code}/thumb/{key}` (`web.py:341`): a JPEG at most 768 px wide, made once and stored beside the picture as `<key>.thumb.jpg` (`thumb_bytes`, `web.py:309`). It needs the browser's sign-in cookie.

So the pictures are already available as local files on the operator's machine. No video is shown in the reference steps.

### 1.3 Between the two phases

1. The last step-1 answer calls `V.round_done` (`visuals_stage.py:3253`). It approves the footage frames and queues one paid set per thing that needs one (`_queue_sets`, line 2972). The round is `'making'`.
2. The workers make the sets: three pictures, one per turn of one conversation (design/151 section 13). The assistant waits with `vw visuals status --wait 900` (instruction text, `server/procedures/v3.json`, visuals, part "picture-search"). How long a set takes: **not verified** (no timing found in the code).
3. The operator waits. `next_item` says "Nothing is needed from you now" with the `working` lines (`chat_flow.working`, line 664).
4. When no set is still being made, the round is at pass 2 and the sets are asked.
5. After step 2, each No, None of these or Correct it queues that set again. The round is `'making'` again, and those sets come back for another step 2. This repeats until every set is approved or set aside.

### 1.4 The instruction text today

- `plugin/commands/vw.md`, the Visuals paragraph: "References are one round for every element at once (design/79, design/151)…step 1 the operator approves the footage pictures and Done makes every set silently…step 2 they judge every set in one shot".
- `server/procedures/v3.json`, visuals, part "later", section 9: "every element's set judged in the chat, one at a time (`vw visuals next`, section E; never `vw visuals round --sets` for the operator)".
- Part "picture-search": the drawing set is answered "Yes or Correct it" in `vw visuals next`.

---

## 2. How pictures could reach the page

### 2.1 Facts that bound every method

| Fact | Source |
|---|---|
| One database document: at most 256 KiB, 32 levels deep | The artifact runtime contract on this PC (`db.d.ts`, version 0.2.96, lines 191 and 548) |
| `ArtifactData` `batch`: up to 50 writes, each from a `file_path`, whole batch at most 1 MiB, one approval | The `ArtifactData` tool's own description |
| Asset upload from the assistant: `Artifact` with `asset: true`, up to 25 files per call, one approval, 15 MB per file; the page must declare the `assets` capability; the returned link is used as an `<img>` source; a stored id also serves at `/_blob/<id>` | The `Artifact` tool's description; `assets.d.ts` lines 92 to 104 |
| The asset listing carries no file names | `assets.d.ts` line 329: "entries carry no names" |
| A page may load scripts only from a short list of hosts and style sheets only from Google Fonts | The `Artifact` tool's description. It says nothing about pictures from other hosts: **not verified**, but a block is likely |
| The guard today refuses any `Artifact` call with `asset` or `files`, and any `ArtifactData` action other than `set`, `list`, `get` | `plugin/hooks/guard.py` lines 166 and 176 |
| The page's capabilities are `db` and `user` only | `page_flow.CAPABILITIES`, line 26 |

### 2.2 How many pictures

- Per thing: up to 4 footage frames at step 1; 3 set pictures at step 2.
- Per film: VW-18 had 46 made sets (`design/151-reference-overhaul.md`, line 176), so about 138 set pictures. A typical count for VW-23 or VW-24: **not verified** (no figure found in the design notes).
- The side-by-side sheet turns one line's pictures into one file. With one sheet per line, a film of 46 things needs 46 pictures per phase, not 138.

### 2.3 The methods

| | Method | Verdict | Why | Smallest experiment |
|---|---|---|---|---|
| a | The page loads pictures by link from the VideoWizard server | **Likely blocked** | Two walls. (1) The server's picture routes need a sign-in: `/runs/{code}/thumb/…` needs the cookie, which is `samesite='strict'` (`main.py:110`, `web.py:56`) and is never sent from another site's page; `/api/runs/…/files/…` needs the laptop's token. (2) The page's security policy probably refuses pictures from another host. A signed storage link needs no sign-in, but lasts about an hour (`files.py:47`) and still meets wall 2 | Put one `<img>` with a fresh signed storage link in a trial round; open the page; read the browser console |
| b | Each picture uploaded to the page's asset store | **Should work; not tried** | The contract describes exactly this. Costs: the page must declare `assets` (every run's page is published again); the guard must allow asset uploads of picture files from the run folder to the run's page; and the assistant must carry each returned id back to the tool (ids come back in the tool's answer, not in a file, and the listing has no names). A wrong pairing would show the wrong picture on a line, so each picture needs its name drawn on it | Upload 3 sheets to a trial page in one call; write their ids into a round; check they show; time it; count the permission prompts |
| c | Small JPEG embedded as a `data:` link inside a database document | **Should work; not tried** | No new capability, no publishing again, no ids to carry: the picture is a file the tool writes, sent like the round file. Limits: 256 KiB per document, so one document per line (`rounds/<round>/pics/<line>`), and 1 MiB per batch. A three-picture sheet about 1,320 px wide should be 100 to 150 KB as JPEG, so about 140 to 200 KB embedded (**estimate, not measured**): about 5 lines per batch call. A whole round in one document does not fit | Write 5 such documents to a trial page in one `batch` from files; check the page shows them; check sizes; count the prompts |
| d | Pictures stay in the chat, or on the server's visuals page; the artifact page has only the buttons | **Works today, but poor** | The chat already shows the files. But the operator would look in one place and click in another, for every thing. The server's visuals page (`server/app/templates/visuals.html`) already has both steps with pictures and Done; using it is the way SK moved away from on 12 Nov (design/188: "never send the operator to any other page") | None needed |
| e | Each line on the artifact page links to the server's page | **Works, but two pages** | A sign-in link is one use and lasts ten minutes (`auth.py:114` to `135`), so it cannot sit in a round. A plain link asks for the sign-in. The operator would answer on the server's page anyway, so the artifact page adds nothing | None needed |

### 2.4 Recommendation

**Method c, with one labelled sheet per line.** It is the smallest change: the same "write a file, send it to the page" mechanism as today, one new guard rule (`batch` of `set` writes from files in the run folder), no capability change, and a picture can never land on the wrong line because the document's name is the line's name.

**Method b is the fall-back** if the experiment shows the sheet is not clear enough at that size, or `data:` pictures are refused, or the batch calls are too many. It gives full-size pictures.

Count of calls, for a film of 20 things and of 46 things (estimates):

| | 20 things | 46 things |
|---|---|---|
| c, one sheet per line | 4 batch calls per phase | about 9 per phase |
| b, one sheet per line | 1 upload call + 20 ids carried, per phase | 2 upload calls + 46 ids, per phase |
| b, every picture alone | 3 upload calls + 60 ids | 6 upload calls + 138 ids |

Whether each call asks the operator for permission on their machine: **not verified** (design/204 section 8 lists the same unknown for the treatment).

---

## 3. The reference steps on the page model

### 3.1 What fits as it is

| Page model | Reference steps |
|---|---|
| A line is `open`, `recorded` or `with_assistant` | A thing to answer; a thing answered; a drawing sent back for redrawing |
| Buttons come from the server's item | `_round_items` and `_drawing_items` already give the buttons, with `needs_words` on Correct it |
| Answers recorded on "done", each through the item's own function | `page_record`'s last branch already does `item['_run'](choice, label, words)` (`page_flow.py:257`). The step-1 `_run` keeps each answer and calls `round_done` on the last one. The step-2 `_run` calls `set_answer` then `flush_sets` |
| A stale answer is ignored by its item id | `set:<element>:<set id>`: a set made again has a new id. `drawing:<element>:<sha>`: a redrawn set has a new digest. Step 1 is guarded by the frames stamp (`_round_kept`, line 289) |
| Every answer logged with the operator's words | `page_flow._log` (line 57) |

### 3.2 What needs a change

| Matter | Today | On the page |
|---|---|---|
| Step 1 gives one thing at a time | `open_[:1]` (`chat_flow.py:308`) | The page asks for all of them; one small switch in `_round_items`. Step 2 already returns every set |
| Paid answers | The chat rule is "inform, do not ask" (`vw.md`, "Paid steps"). `round_done` and `round_sets` take a quote and fall back to a fixed one (`said(quote, 'Pass 1 done', user)`, line 3263) | Each paid button says so and gives the price of one set; the page's top line gives the total ("7 sets, about ₹X"). The button's label is logged as the operator's word, as design/205 does. Whether a click is enough for a spend is SK's call (question 2) |
| An answer that starts jobs | `round_done` queues the sets | "Done" for step 1 records and queues. The next round shows each such line as "being made" (a fourth state, or `with_assistant` with a note). Step 2 cannot be on the same "done": its pictures do not exist yet |
| The wait | The assistant waits with `status --wait 900` | The same. When the sets are back the assistant writes the step-2 round and says so in the chat. The page refreshes by itself (it follows the newest round, `decisions.html` line 252) |
| Step 1 answered in part | Kept in `chat_round`; nothing recorded until the last | Same. Kept lines show "kept; the sets are made when every thing is answered" |
| A set rejected and made again | Round back to `'making'`, then step 2 again for those sets | Each cycle is one more round and one more "done", for those lines only. Approved lines show `recorded` |
| A set regenerated while the page is open | `set_answer` discards an answer whose picture is from an older set (line 3131) | The stale-item rule covers it; the line returns with the new sheet |
| "Change this" for a picture | Correct it: the set is made again with the operator's words in the prompt (`round_sets`, line 3072), never from the rejected picture. No / None of these: made again without words | Two buttons, as today. Both are paid and say so. A drawing's Correct it is free: a helper redraws it |
| The spend cap holds a remake | `held` in the answer | The line stays open with the server's sentence on it (the page already shows a refusal on its line) |
| Drawings and step 1 together | Drawings are asked first; `round_done` waits for them | Both on the first round. `page_record` records drawings first. If a drawing is corrected, the step-1 answers stay kept, and the round is closed when the redrawn set is approved. This needs `round_done` called from `page_record` when every thing is answered and no drawing is open; today only the last `_run` calls it |

### 3.3 Round trips

| | Chat today | Page |
|---|---|---|
| Drawings | 1 answer per drawing set | On the step-1 round |
| Step 1 | 1 answer per thing | 1 "done" |
| Step 2 | 1 answer per set | 1 "done" |
| Sets made again | 1 answer per set, per cycle | 1 "done" per cycle |
| A drawing corrected | 1 more answer | 1 more "done" |

The least possible is two "done" for a film with no drawing corrected and no set rejected.

### 3.4 What does not fit, and stays in the chat

- The operator's own picture (`vw visuals own`), undo of step 1 (`round --undo`), and bringing a set-aside thing back (`round --back`). They are rare and need files or commands.
- The other groups of the visuals stage (stills, graphics, AI video, takes, recording). Takes are video; this analysis does not cover video on the page.

---

## 4. Plan

Feasible, with method c first and method b as the fall-back. Steps in order. Per the working rules, step 2 is SK's approval before any code.

| # | Step | What it proves or delivers | What changes |
|---|---|---|---|
| 0 | Tell the design/206 builder about the 256 KiB limit | A large plan round is not refused in front of an operator | The test's bound in `test_design206_pure.py`; perhaps one document per line for the plan too |
| 1 | **Experiment, on the builder PC, a trial page, no product code.** One trial round with: one signed storage link (a); 3 sheets uploaded as assets (b); 5 sheets as `data:` documents written by one `batch` from files (c). Use real sheets from a closed run | Which methods show a picture at all; the real size of a sheet at a size that is clear to judge; calls, prompts and seconds for 20 lines; whether 256 KiB holds in practice | Nothing in the repository |
| 2 | Requirements list as design/207, with the edge cases of section 3.2, and SK's answers to section 5. Wait for approval | The scope is agreed | One design file |
| 3 | Tests first (`server/unit`, `plugin/tests`), from the approved list | See "Tests" below | Test files |
| 4 | Server | Lines for drawings, step 1, "being made", step 2 and sets not made; the record branch; one labelled sheet per line | `chat_flow._round_items`: a switch to return every step-1 item. `chat_flow.sheet_of`: the thing's name on the sheet, a smaller size, and a sheet of the footage frames. `page_flow`: `_refs_page` and a references branch in `page_record`, beside `_plan_page`; each line carries `pic: {key, name}` and the price words. No new route: the tool downloads the sheet by its key through the existing files route |
| 5 | Plugin page | A line shows its picture; click to enlarge; a "being made" state; paid words beside paid buttons | `plugin/pages/decisions.html`: read `rounds/<round>/pics/<line>` and draw an `<img>`; about 30 lines |
| 6 | Tool and guard | The pictures reach the page with nothing typed | `vw.py`, `visuals page`: download each line's sheet, write one small JSON file per line under `work/page/`, print the batch list. `guard.py`: allow `ArtifactData` `batch` when every write is a `set` from a file inside the run folder to a path under `rounds`. For method b instead: allow `Artifact` with `asset: true`, the run's own link and picture files inside the run folder; add `assets` to `CAPABILITIES`; publish each page again |
| 7 | Instructions | The assistant uses the page for the reference steps and the chat where it cannot | `plugin/commands/vw.md` (Visuals), `server/procedures/v3.json` by a wording script (parts "picture-search" and "later" section 9), `page_flow.HOW`. Old way in `design/35-decision-log.md`: the reference steps one at a time in the chat, **kept as the way back** until the page has carried one full reference round on an operator's machine, then retired on SK's word |
| 8 | One deploy on SK's word; the first real reference round is the test | The whole loop on the operator's machine | Server and plugin versions; the plugin minimum rises |

**Tests (step 3).** Server: step-1 lines for a thing with footage, without footage, a person; all answered records once and queues; answered in part keeps and records nothing; a paid line carries its price; "being made" lines; step-2 lines for a person and a thing; Use A records the starting picture; No and Correct it queue again and the line returns with a new item id; an answer to an older set is stale; the cap holds a remake and says so on the line; a drawing approved, a drawing corrected with step-1 answers kept; every picture document under 256 KiB; nothing in a line names a video category. Plugin: `vw visuals page` writes one picture file per line; the guard allows the batch from run-folder files and refuses any other; the page file draws a picture line.

**Risks.**

| Risk | Handling |
|---|---|
| `data:` pictures refused by the page, or a clear sheet does not fit 256 KiB | The experiment finds it; then method b |
| Many calls on a large film (46 things: about 9 batch calls per phase) | Measure in the experiment; method b needs fewer calls but ids carried |
| A permission prompt on every call on the operator's machine | Not verified; found in the experiment only on the builder PC, and for real on the first run. One settings line may be needed |
| Client pictures, footage frames of real people among them, stored under the operator's Claude account | SK's decision (question 1). design/204 section 8 raised the same for text |
| The page's database fills up over many rounds | Each round's pictures are small; old rounds are never deleted today. Not measured |
| The operator's Mac behaves differently from the builder PC | The chat stays as the way back |

**Not covered by this analysis:** video on the page; the other visuals groups; timing of set generation; the page under real clicks.

---

## 5. Questions only SK can answer

1. May footage pictures (including pictures of real people) and reference pictures be stored in the page's database on claude.ai, under the operator's Claude account?
2. For a paid answer on the page (make a set; No or Correct it, which makes a set again), is the button click plus "done" enough, with the price shown on the line, or must the operator type words?
3. Is one side-by-side picture per thing (about 440 px for each of the three pictures, with A, B, C on them) clear enough to judge a set, or must each picture open at full size?
4. At step 1, should the page offer one button, "Accept all as proposed" (use the footage picture where there is one, make a set where there is none), so that step 1 is one click and one "done"?
5. Should the drawing sets (design/200) be answered on the same first round as step 1, or stay in the chat for now?
