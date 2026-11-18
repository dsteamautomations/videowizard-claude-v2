# design/214: Claude checks the sets; the Gemini check is taken out of this step

**Status:** built on 18 Nov 2026, server 0.111.0, plugin 0.95.0 (the plugin minimum is raised to 0.95.0: every laptop updates); **not deployed**, not pushed.

**The owner's words (SK, 18 Nov 2026):** "whatever Gemini is doing can be done by Claude if it can. I think we should go ahead and make Claude do it, especially the part that 3.8 is doing. Let us retain the Gemini Nano Banana generation, but exclude the Gemini 3.8 thing."

**Where:** References step 5, judging the reference sets of a v2 round (design/211, design/213). Nothing else changes.

**The image workflow he approved (design/200, step 8 of Area A)** asks for a check of "the picture, the drawings, and check lines made from the same facts table; pass or fail per line; shown to the operator; never blocks", and says "The checker fails or is unavailable: the picture is unchecked but can still be approved; the operator sees 'not checked'". It names no model, so nothing of it is set aside: the lines from the facts table are kept, each gets pass or fail, the result is shown, it never blocks, and "not checked" is said.

## 1. What is built

One flow, two front ends: the list, the answers and every sentence are built on the server (`ref_sets`, `chat_flow._round_v2`); the page and the chat read them.

| | What | Where |
|---|---|---|
| 1 | **No model checks a set of a v2 round.** When a set's pictures come back, the worker no longer marks them for the Gemini 3.8 Flash check and no call is made. The check list of each picture is still built when the set is ordered and kept on the picture (the view asked; the same thing as picture A, seen as this picture's view asks; the footage picture; the plan's description with the operator's and the writer's words; one thing only; no lettering the description does not name; "a real face" where it applies; every fact of an approved drawing). The checks that need no model (the picture's size, its parents) are still run and kept. | `visual_workers.finalize_image`, `image_check.code_only` |
| 2 | **The look answers the list.** `vw visuals round --looks` gives each picture its list (`lines`: `id`, `check`, `pass_when`, and `say` on a fact of the drawing). The look answers every line of every picture: `pass` true or false; one plain sentence of what was seen for a fail, and for a pass of a fact of the drawing. A look that leaves a line unanswered, names a line the picture does not have, or gives a fail with no words is refused: the refusal names the picture and the line and says how to send it again; nothing of that set is recorded. A picture that could not be opened is sent as `not_checked` with the reason: it needs no verdict, the set is still shown and can be approved. | `ref_sets.check_lines`, `looks_due`, `round_looks`, `LOOK_LINE_OPEN`, `LOOK_LINE_UNKNOWN`, `LOOK_LINE_WORDS`, `LOOK_HOW` |
| 3 | **What the operator sees: one result, "Claude's check".** "Claude's check passed", or "Claude's check found N faults" with each failed line as what was seen ("Picture B: ..."), or "Claude's check: not checked" with the picture and the reason; the amber dot on a picture a failed line names. The chat says the same sentences. The words "The program's check" are gone for a v2 set. It never blocks; no set is shown before its look is recorded. | `ref_sets.check_summary`, `chat_flow.WORDS`, `chat_flow._round_v2`, `page_flow._details` |
| 4 | **Sets made and checked before this release.** Their stored Gemini result stays in the record and is no longer read for the line. A set with no look gets its list like any other. A look recorded before this release, with no line answers, stands for a set the operator has already judged; a set not yet judged whose look lacks the answers is due for a look again, and is not shown until then. | `ref_sets.looked`, `check_summary` |
| 5 | **Every other use of the model check is untouched:** stills and other shot pictures, the start picture of a video shot, takes, drawn graphics, a set of an older round, a sheet of a film with no round. | tests |
| 6 | **The instructions and the helper** say that the check of a set is the look's own: each line is answered from what is seen in the picture, never from the request or the notes; a fact of the drawing is checked against the drawing sheet given with the set; a picture that could not be opened is "not checked"; a line that was not looked at is never passed. | `scripts/d214_wording_v3.py`, `plugin/agents/vw-set-look.md`, `plugin/commands/vw.md`, `server/retired-sentences.json` |

### The shape of a line and of its answer

A line, as `vw visuals round --looks` lists it under a picture: `{"id": "9a2a4ea2", "check": "the view", "pass_when": "the picture shows what its turn asked: ..."}`; a fact of the drawing also has `"say": true`. The id is made of the line's own words, so a list that changed has other ids.

Its answer, in the look file, in the picture's row: `"lines": [{"id": "9a2a4ea2", "pass": true}, {"id": "596ce391", "pass": false, "seen": "Two ways of laying are mixed in one wall."}]`. A picture that could not be opened: `{"ref": "...", "not_checked": "The file would not open."}`.

What is stored: on the picture's look, `lines` (`id`, `check`, `pass`, `seen`) or `not_checked`.

## 2. The trade-off, stated plainly

A second, independent model no longer looks at a set. The picture is made by one model and judged by Claude alone, who also wrote the added words of the request and makes the recommendation. On the sets of 16 Nov the Gemini check caught one real fault (two methods mixed in one picture). On the two sets of 17 Nov three of its four findings were false. So the step loses an independent catch that was right once, and loses three false alarms the operator had to read past.

What guards against the loss: the look must answer every line of the same list the model was given, a fail needs its sentence, a fact of the drawing needs words even when it passes, and the operator still judges every set.

## 3. What stays with Gemini

- The pictures of every set: the Gemini picture model, as before.
- The Gemini 3.8 Flash check of every other picture: stills and other shot pictures, the start picture of a video shot, takes, drawn graphics; the sets of an older round; the analysis of the footage.

## 4. Decisions taken by default (the owner can change any)

1. **Every failed line is a fault**, also a line the model's check treated as lighter ("nothing extra"). One list, one count.
2. **A pass of a fact of the drawing needs a few words**; any other pass needs none. A fail always needs its sentence.
3. **"Not checked" is the looker's word for a picture it could not open.** The server takes it as given, with the reason, and does not test the file.
4. **A failed line is shown as what was seen** ("Picture B: Two ways of laying are mixed in one wall."), without the line's name.
5. **A set already approved before this release, whose look has no line answers, reads "not checked"** where it is listed among the settled sets: no look is asked for it again.
6. **The same look sent twice is recorded again**; the later one stands. A look for a set that was made again, or that is approved, is refused as not the thing's set now.
7. **The check of a look and its verdict are not tied by the server:** a picture whose every line passes may still be "weak" in the look, and the recommendation is the looker's.
8. **The size of a look file:** the server sets no size of its own on it beyond 80 sets a file. Measured: five sets of three pictures with 14 drawn facts each, every line failed with the longest sentence, are under 256 KiB (the size the server allows a body it keeps in the database; a look is kept in the film's record file, not there). Helpers take about five sets each, as before. The page's round, one document of at most 256 KiB, holds such a set with every line failed.

## 5. Older ways (rows 128 and 129 of `design/35-decision-log.md`)

- The Gemini check of a set of a v2 round: retired at this release. Kept for a set of an older round, to its end.
- "The program's check" as the name of the result on a set, and a failed line shown with the line's name: retired for a v2 set.

## 6. Not built

- **The checks of stills, start pictures and takes** stay with the model. The owner's words cover "whatever Gemini is doing"; this change is the sets only.
- A second look by another helper as the independent check. Not asked for.
- A test by the server that a picture said to be "not checked" really cannot be opened.
- A fix round from a failed line of a set (`request_fix`): it was not offered on the sets screen and is not now.

## 7. Tests

- `server/unit/test_design214_pure.py` (25): no model call for a set of a v2 round and the code checks kept; every other picture still checked by the model (a still, a start picture, a set of an older round, a sheet with no round; takes and drawn graphics by their call sites); the list per picture with stable ids, from one source; the three refusals by name, and nothing half recorded; a fail with its sentence; the same look twice; "not checked" and approval after it; the three results on the page and in the chat; sets checked by the model before, with and without a look; a look of before for a judged and an unjudged set; fewer than three pictures; a place of one picture; 14 drawn facts within the limits of the look file and of the page's round; more than five sets; a set made again; a set not due; a list that changed.
- `plugin/tests/test_design214_looks.py` (3): the tool keeps the lists and sends the answers as written; the helper's sentences; the plugin's version.
- Tests of design/211 and 213 whose pins changed are listed in the commit message.

## 8. Not verified

- Not deployed; nothing was run against the live server, the database or VW-24's own session. What VW-24 meets after the deploy is read from the code: its two sets (MASON, SITE_DECK) have stored Gemini results and no look, so the round says the sets are back; `vw visuals round --looks` lists both with the lists that were stored when they were ordered; once the look answers them, the page shows "Claude's check" and the Gemini findings are no longer shown.
- No real look was made: no assistant or helper answered a real list on real pictures. Whether Claude finds the faults the model found, and no false ones, is not measured.
- The helper file was not run.
- The page was drawn in a local headless browser from the server's own round (the chip, its lines, the amber dot); no claude.ai page was published.
- `server/tests` (the database tests) and the whole suites were not run: only the tests of this area (the owner's rule of 17 Nov).
