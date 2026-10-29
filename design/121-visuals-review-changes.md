# 121 — Visuals stage review: changes agreed with SK (started 29 Oct 2026)

A running list. SK and the assistant review the Visuals stage one step at a time; every change agreed is added here. **Nothing here is built yet.** Each change waits for SK's go-ahead before any code, as usual (requirements, then tests, then the change).

Written in plain English first; the last part of each change ("For the builder") says where it lands.

---

## Change 1 — Every Google search ends with a clear answer

**Step:** the reference round (finding example pictures for each thing the film shows: first from the client's footage, then from Google Images).

### The problem today
- When none of the 10 Google pictures fits, the operator can press "Nothing fits" and write a reason. The page says "the assistant searches again with your hint", but nothing tells the assistant, and the assistant has been told to wait quietly. So no new search happens.
- The operator can press Done on pass 2 with no picture ticked and no new search for a thing. Nothing stops them.

### What changes (agreed with SK, 29 Oct 2026)
1. **Three answers per searched thing.** On pass 2, every thing that went to Google needs one of:
   - **a ticked picture** (as today);
   - **new words and "Search again"**: the new 10 pictures replace the old ones for that thing, and the operator ticks from them;
   - **"Ignore this"**: one click, no typing. It means "no Google picture for this thing". The AI then works from the footage picture and the written description only.
2. **Done stays locked** until every searched thing has one of the three answers. The page names the things still waiting, for example "2 things still need an answer: Brick kiln, Trowel".
3. **The "Nothing fits" reason becomes optional.** If written, it still goes onto the thing's "not this" list (the looks the AI must avoid). The page stops saying "the assistant searches again".
4. **A search that failed** (Google or the search service did not answer) counts as waiting too: the operator searches again or presses "Ignore this".
5. **"Ignore this" can be undone** with the existing Undo button, like the rest of the pass, until the reference sheet for that thing is made.
6. **Same rule in chat.** When the operator works in chat instead of the page, the same three answers apply and the same lock holds. The rule lives on the server, not only on the page.

### To check first
- **Search again during pass 2 may break Done today.** A new search made during pass 2 does not seem to be linked to the round, so ticking a picture from it might make Done refuse the whole pass ("search is not in this round"). This is read from the code and has not been tried yet. Change 1.1 fixes it either way, but it needs a test first.

### Not changing
- Pass 1 (footage picture or Google) stays as it is.
- The searches still run all at once on the one search key; no new keys are needed.

### For the builder
- Server: `visuals_stage.round_picks` holds the lock and accepts an `ignore` answer per element; `search` during pass 2 updates the round row's `search_id`; `round_done` leaves failed searches waiting; `round_undo` reopens an ignored element. Chat: `vw visuals round --picks` file rows accept `{"ignore": true}`.
- Page: `templates/visuals.html`, pass 2 footer (Done disabled with the waiting list), an "Ignore this" button beside "Nothing fits", and new wording for the nothing-fits message.
- Procedure text (`procedures/v2.json`, visuals steps): replace "a 'nothing fits' reason is the next search's hint" with the three answers.
- Tests: pass 2 refused while a thing is unanswered; each of the three answers unlocks it; a failed search waits; Search again in pass 2 then Done; the same through the chat path.

---

## Change 2 — Use the waiting time during the picture round

**Step:** the reference round, while the operator works through the page (often 15 minutes or more).

### The problem today
The assistant's instructions say "ask nothing per element and generate nothing meanwhile", so it simply waits. But some work does not depend on the example pictures at all and costs nothing to write.

### What changes (agreed with SK, 29 Oct 2026)
While the operator does the round, the assistant **writes, but does not make or spend**:
1. **The instructions for every diagram, chart and title card** in the plan, in the form the system already uses for picture instructions. These need the graphic style, not the example pictures.
2. **The measurement sheets** (the sizes and parts of a drawn object, and of a repeating material such as bricks), filled from the client's own material and the plan. The material sheets stay in even though materials also appear in ordinary pictures (SK, 29 Oct 2026): no picture of a material can be made before its sheet is approved, so having it ready saves time. Anything that needs a paid measurement from the footage, or a web source that needs the operator's yes, is left for after the round.
3. **The drawn-diagram layouts** (the files that place labels, arrows and numbers), as drafts on the assistant's side.

Rules for this waiting time:
- **Only for slots the operator has already approved.** The round comes after the operator has approved the treatment (gap by gap, including which slots are graphics and what each graphic shows) and accepted the plan. A gap under revision is skipped until it is accepted again.
- **Nothing paid**: no pictures made, no paid measurements.
- **No questions to the operator** and nothing new on their page while the round is open, so the round is not interrupted.
- When the round is finished, the assistant shows the measurement sheets in one table as usual, then carries on with the reference pictures. The written instructions are used when their turn comes.
- If the round changes something a draft depends on (for example a thing is ignored), the assistant updates that draft before using it.

### Not changing
- The order of approvals stays the same: the style picture, the measurement table and every picture are still approved by the operator as today.
- No server change: this is a change to the assistant's instructions only.

### For the builder
- Procedure text (`procedures/v2.json`, visuals steps, the reference-round paragraph): replace "ask nothing per element and generate nothing meanwhile" with the waiting-time list above, then `vw visuals status --wait 900` once the writing is done.
- Check: the instructions stay consistent with rule 0 ("stop and ask, never guess"): any question the drafts raise is held and asked after the round, as one list.

---

## Decision — No in-between pictures for a video (SK, 29 Oct 2026)

A video stays as today: one start picture, an end picture only where the final moment must be exact, and the written timeline (each action, its seconds, where each person ends, what changes). No pictures for the seconds in between: the video tools take a start and an end picture only, and each extra picture would add cost and an approval. A long passage is still split into shorter shots, each with its own start picture.

---

## Change 3 — Every thing an action heads for is on the list

**Step:** the plan (before the picture round), checked by the server.

### What was checked (29 Oct 2026, from the code)
The video AI receives only the start picture (and the end picture when there is one) and the written timeline. The reference pictures of each thing are used to make those start and end pictures; they do not go to the video AI. So a thing looks right in the video only if it is in the start or end picture, and it is in those pictures only if the plan lists it in the shot.

Already checked by the server today, so these are safe:
- every person or animal that acts in a shot;
- everything someone holds, and every prop (where it starts and where it ends);
- every counted thing in the frame (for example "12 bricks on the plinth");
- where a person is looking (it must be a named thing or a fixed part of the place);
- every way of working named in an action (plastering, sawing and so on).

**The gap:** what an action heads for (its target, for example "walks to the cement mixer") is free words. Nothing checks that the cement mixer is a named thing or a fixed part of the place. If it is neither, it gets no reference picture, is not placed in the start picture, and the video AI invents it.

Left out on purpose (no change): people who only pass in the background, and background life (leaves, dust, signs of use). These are described in words by design, different in every scene.

### What changes
1. **The target of every action is picked, not written freely**: a named thing on the list, or a fixed part of the place (a landmark such as the doorway or the near wall). This is the same rule the server already uses for where a person looks.
2. If the target is a named thing, it must also be listed in that shot, so it goes into the start picture.
3. The check refuses a plan that breaks either rule and says which shot and which action, as it does today for held things.

### Not changing
- How the start and end pictures are made, and what the video AI receives.
- Nothing new for the operator: this is a check on the assistant's plan.

### For the builder
- `visual_contract.py`: `Beat.target` checked like `Gaze.target` (a landmark of the scene or an element), and an element target must be in `shot.element_ids`. Free words that describe the target go in `path` / `result`, which stay free.
- Procedure text: one line in the scenes paragraph ("a beat's target is a landmark id or an element id of the shot").
- Tests: a target that is neither is refused; a target element not in the shot is refused; a landmark target passes; an element target in the shot passes.
- To check before building: plans already approved on live runs may have free-word targets. The rule applies to new and revised plans; an approved plan is not re-checked.

---

## Change 4 — The operator's notes reach the picture AI, and are checked

**Step:** the reference sheet (the one main picture of each thing, made from its approved footage pictures and the Google pictures the operator ticked).

### What was checked (29 Oct 2026, from the code)
- The operator can write a note on a ticked Google picture (pass 2) or on a footage picture ("use this brick colour, ignore the wall").
- The server saves the note and shows it to the assistant. The assistant's instructions say to turn the notes into keep or avoid lines when it writes the sheet's request.
- **The server never adds the note itself** to what goes to the picture AI, though it adds many other lines (sizes, light, the "not this" list, spelling). So a note reaches the picture AI only if the assistant remembers to copy it.
- **The picture check does not test the note**: after the sheet is made, nothing flags a sheet that ignored it.
- This matters for the whole film: the golden picture is made from the sheet, and every later picture of the thing copies the golden picture.

### What changes (agreed with SK, 29 Oct 2026)
1. **The server adds every note automatically** to the sheet's request, beside the line for the picture it belongs to: "Image 2 is the operator's pick; the operator's note on it: use this brick colour, ignore the wall."
2. **Every note becomes a point on the picture check** of the sheet, so a sheet that ignores a note is flagged on its card like any other failed point.
3. **Notes on footage pictures count the same** as notes on Google pictures.
4. **A note changed or added after the sheet was made** marks the sheet "sources changed", as a picture added after the sheet already does today, so a new sheet is made with it.
5. The assistant's instructions stop asking it to copy the notes by hand (the server does it), so the note is never written twice.

### Not changing
- How the operator writes a note (page or chat).
- Pictures after the sheet: they carry the notes through the golden picture, as today.

### For the builder
- `visuals_stage.generate_image`, kind `sheet`: for each parent with `source.note`, add the note under its job line with `with_composed`, and a checklist line per note (`{'check': 'operator note on Image k', 'weight': 'must', 'pass_when': <the note>}`) beside `sheet_lines`.
- `note_reference` (the note on a footage frame): mark the element's sheet `sources_changed` when the sheet already exists, as `supply` does.
- Procedure text: "the notes as keep or avoid lines" becomes "the server adds the notes; do not repeat them".
- Tests: a sheet whose parents carry notes has each note in its prompt and a must line per note; a parent with no note adds nothing; a note saved after the sheet marks it sources changed.

---

## Change 5 — A second, stock-photo search beside the plain one

**Step:** the reference round, the Google search for each thing.

### What was tested (29 Oct 2026, Google Images in a browser, two things: "red clay brick kiln worker", "mason plastering wall trowel")
- Plain words: news pictures (kiln) and shop pictures of the tool on white (trowel).
- `site:depositphotos.com`: ignored by Google Images; the same results as plain words.
- The site's name as a plain word ("depositphotos", "unsplash"): nearly every picture from that site; clean, sharp, well framed, people at work. "depositphotos" also kept the Indian context; "unsplash" was less local.
- "stock photo": Shutterstock, Getty, iStock, Dreamstime; a Getty picture showed its watermark already in the preview.

### What changes (agreed with SK, 29 Oct 2026)
1. **Two boxes per thing:** the search words (two to six, as today) and a **source box**, filled in by default with a stock site's name, not counted in the six words.
2. **Two searches per thing:** the plain words, and the words plus the source box. Both sets of pictures are shown side by side. The plain one often suits an object (a clean shop picture of the tool); the stock one suits people at work and places.
3. **Clearing the source box** means only the plain search runs, for that thing; the operator can fill it again and search again.
4. **Watermarks.** Paid stock sites print their name across the picture. For every Google picture sent to the picture AI, the server adds one line: "Image k may carry a watermark or a stock site's lettering: ignore it, never copy it", and the picture check gets one must point: "no watermark or stock-site lettering anywhere".
5. **Inspiration only**, as today: a Google picture is a guide for one thing (its shape, colour, how it is used), named in its job line; it never goes into the film, and a person from the web is never copied. **No copyright wording is added to the prompt**: telling the picture AI that a picture is someone else's copyrighted work can make it refuse the whole request, and the job line already says what to take.

### To do first
- **A real test through the project's own search** (the service the operator uses, not a browser): the same two things, plain and with "depositphotos", "unsplash" and "pexels". Look at the downloaded full-size pictures: which carry a watermark, which download at all. The default in the source box is chosen from this test, with SK.
- The search service charges a small amount per search; two searches per thing doubles it. The price is not in the project yet; find it in the test.

### For the builder
- Page (`templates/visuals.html`): the source box beside the keywords on every card (pass 1 and Search again); both result sets shown, labelled.
- Server: `_search_into` / `round_searches` / `round_done` run two searches per thing when the source is set (the source word appended, outside the 2-6 count); the session keeps both under the element; picks from either count for Change 1's lock.
- `generate_image`: the watermark line under the job line of every `web` parent, and the must line on the checklist.
- Chat: `vw visuals search … --source "<word>"`, and a `source` per row in the round file.
- Tests: two searches when the source is set, one when it is empty; the 2-6 count ignores the source; the watermark line and must line for a web parent, none for a footage frame.

---

## Change 6 — Search one thing at a time, and download the full pictures in the background

**Step:** the reference round, pass 1.

### Today
On pass 1 the operator goes through the whole list (footage picture, or Google with words), then presses Done once; only then do all the searches run, together. The small previews show at once on pass 2; the full-size pictures download only when the operator presses Save, which is also when a site that blocks downloads is found.

### What changes (agreed with SK, 29 Oct 2026)
1. **A Search button on each thing's card in pass 1.** It runs that thing's search (both searches of Change 5) at once, so the operator can look at the pictures before moving to the next thing.
2. **Full-size pictures download in the background** as soon as a search returns, for all its pictures. Save is then instant, and a picture that cannot be downloaded is marked on its card before the operator ticks it.
3. **Every Search button must be pressed (SK, 29 Oct 2026).** Done on pass 1 stays locked until every thing has an answer: "use the footage picture", or its search has been run. The page names the things still waiting ("2 things not searched yet: Brick kiln, Trowel"). Done no longer runs any search itself, so no search is ever run twice and the time saving is kept.
4. Change 1's lock still holds on pass 2.

### Not changing
- The yes to a search is still the operator's click.

### For the builder
- Server: a per-element search inside pass 1 that writes the round row's `search_id` (the same fix Change 1 needs for Search again); `round_done` refuses while an element set to search has no `search_id`, naming them, and runs no search (the before-the-lock searches of design/92 go away).
- Chat: the same lock; the assistant runs `vw visuals search` per element on the operator's words before `round --verdicts`.
- Background downloads: after each search, `_download_picks` over all its results in a worker thread, stored with the session; Save uses the stored file, falling back to a download as today; a failed one is marked on the result row.
- Page: the Search button and a "could not download" mark on a result.
- Tests: Done refused while a thing set to Google is unsearched, with the names; Done accepted when every thing is footage or searched, and runs no search; a stored download is used at Save; a failed download is marked before the tick.

---

## Change 7 — Larger text on the visuals page (made 29 Oct 2026, not deployed)

**Step:** the whole visuals page (every step: Treatment, Plan, References, Pictures, Takes, Record).

### What changed
- Every text size on the page went up by about a quarter: the main text from 15 to 17, the step names from 16 to 19, the small grey notes from 12.5 to 15, the picture captions and check lines from 11.5-12 to 15, the small labels from 11 to 14 (the smallest text on the page now).
- The page is wider on a big screen (up to 1400 instead of 1100), so the larger text does not crowd; the footer bar widens with it.
- The search pictures are larger (200 wide instead of 160), and the tick circles and tick boxes larger, so they are easier to see and click.
- The page scrolls more; nothing else moves.
- Desktop and laptop only (SK, 29 Oct 2026): no phone layout work.

### Checked
- On a local copy of the page with VW-7's real data (no live server), in a browser at 1440, 1366 and 1280 wide: the References step, pass 2 with the Google pictures, a picture opened in the side panel, a tick with its note box, and the footer. All readable, nothing overlapping.

### For the builder
- `templates/visuals.html` only (the style block and eight inline sizes). One server deploy; no test covers styling.

---

## Build — 29 Oct 2026 (server 0.72.0, plugin 0.59.0; not deployed)

All seven changes are built on `main`. Tests first: `server/unit/test_design121_pure.py` (17 tests: the two searches and the source outside the six words, the downloads at the search and Save from the stored copy, a picture that will not download marked, Done on pass 1 waiting by name and searching nothing, Ignore this on both passes, a failed search waiting, Search again on pass 2, undo, the notes and the watermark in the sheet's prompt and check, a late note marking the sheet, the action target, the page). Older tests changed where the behaviour changed on purpose: the round's searches no longer run at Done (`test_l60_busy_pure`, `test_visuals_stage_pure`), a note after the sheet is saved and marks it (`test_design106n_pure`), a fixture's free-word target became its landmark (`test_design91_b1_pure`), the pass-1 labels (`test_visuals_page_pure`), the chat search posts its source (`plugin/tests/test_visuals_cli`). Results: server unit 705 passed; plugin 320 passed, 3 failed (the known Windows-only ones: text-mode line endings in test_intake, a Mac path in test_start_defect_paths).

The page was checked in a browser on a local copy with VW-7's data and a faked server: pass 1 (the three answers, a thing's Search posts its words and source and does not block the others, Done greyed out naming the things not searched, Done unlocked once each has an answer, the verdicts posted), pass 2 (both searches side by side, "will not download" marks, Ignore this and Undo Ignore, Done greyed out naming what waits, picks and ignores posted), and the single-thing view with its source box.

As built, beside the plan above:
- Pass 1 also offers **Ignore this** (not only pass 2), so a thing with no footage picture whose search keeps failing never blocks the round.
- Ticks may be made on pass 1 already, under each search's pictures; they are sent with pass 2's Done.
- The stock word's default is `depositphotos` (one constant, `STOCK_SOURCE`), from the browser test; the real test through the search service is still to do (below).

### Not covered
- **The real test through Apify** (Change 5's "to do first"): which stock sites download at full size, which carry watermarks, the price per search. The default word may change after it. Needs the server's search key; a few searches cost a few cents.
- **The watermark line's effect** on a real picture (GPT Image and Gemini): only checked as text in the prompt and the checklist.
- **Server tests with Docker** (`server/tests`), and Python 3.9 for the plugin (compiled under 3.12 only).
- **Stored downloads are never deleted** (about 20 pictures a search, in the run's storage); a cleanup when the stage is recorded, if storage grows.
- **Plans already approved** keep their free-word action targets; the new rule applies when a plan is checked or proposed again (VW-7's next revision will need its targets as landmarks or elements).
- The page's concurrent searches were checked against a faked server; two real searches at once on the VM are not yet seen.

### Local tests after the build (29 Oct 2026, SK's PC)

**The real search test (Change 5's "to do first").** Eight real searches through the project's own search service and downloader, all at once: "red clay brick kiln worker India" and "mason plastering wall trowel", each plain and with "depositphotos", "unsplash", "pexels". All eight came back in 52 s together (a search 8-34 s, its ten downloads 8-30 s). Every picture downloaded, some only as Google's small preview.

| Source word | What came back | Watermarks | Picture size |
|---|---|---|---|
| none | kiln: news photos of Indian kilns; trowel: shop photos of the tool alone | none seen | mostly Google's previews (400-740 px) |
| depositphotos | trowel: nine of ten from Depositphotos, clean and sharp; kiln: mixed with Getty, Alamy, Dreamstime, Shutterstock, iStock | **yes**: Getty, Alamy, Dreamstime, Shutterstock print their names; a large Depositphotos picture (1600 px) carries its watermark and ID bar | Depositphotos 600 px |
| unsplash | trowel: all Unsplash, but only as previews; kiln: mixed | **faint repeated "Unsplash+" lettering** across the trowel pictures | previews only (about 650 px) |
| pexels | kiln: all ten from Pexels, clean, Indian scenes; trowel: mixed with Dreamstime, Shutterstock, Vecteezy | **none on Pexels pictures**; the others' yes | Pexels full size (up to 5000 px) or preview |

Reading: **pexels** gave the cleanest, largest, unwatermarked pictures for people at work; depositphotos gave sharp but small pictures and pulls in watermarked sites; unsplash brings faint watermarks. The plain search stays useful for objects (shop pictures of the tool alone). The default word is SK's choice.

**The watermark line on real pictures.** Three reference sheets made with the server's own GPT Image call from watermarked stock pictures: a Getty kiln picture (with and without the line) and a watermarked Depositphotos trowel picture (with the line). None of the three shows any watermark or lettering beyond the view labels: the sheet's "alone on plain ground" already drops the background where watermarks sit. The line costs nothing and stays as a guard for other picture kinds; the check's "no watermark" line is the safety net.

**Server tests with Docker** (`tests/test_visuals.py`, `tests/test_web.py`, dummy keys so nothing paid could be called): 6 passed, 7 failed, and the same 7 fail on the code before this change. The cause is older: since design/120 a run needs `--images openai|gemini`, and these tests' run helper does not pass it. Not caused by design/121; a fix to the test helper is a separate small job.
