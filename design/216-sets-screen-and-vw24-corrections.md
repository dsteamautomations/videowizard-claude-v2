# design/216: the sets screen and the VW-24 corrections

18 Nov 2026. Built from `design/_work/sets-screen-release-18-nov-requirements.md` (approved by SK). Server 0.113.0, plugin 0.97.0 (minimum 0.97.0). Not deployed.

## What changed

**Part A, the step-5 screen** (`plugin/pages/decisions.html`, `layout.kind == 'sets'` only). The trial SK corrected over five rounds, ported: the list holds only what needs an answer, numbered, then "The other N sets"; "Settled earlier" folded; one large picture with the set's small pictures below and the footage beside it on a click; one answer for the whole set ("Approve all 3", "Make all 3 again", "Minor corrections"); the check's faults under each picture; Claude's recommendation as one coloured line with "more"; approving against "make again" asks once and marks the row "Against advice"; "Make B the main picture"; "Use my own picture instead"; the details folded; one count in the bottom bar; the end card. Arrows and Escape stay. Every word comes from the server: on the line (`answer_head`, `answer_note`, `strip_head`, `sure`, `rec.head/first/more`, per picture `name`, `set_cap`, `faults`, `check_head`, `check_none`, `main_label`, footage `cmp_cap`, the rest line's `name`, `things_wait`) and with the layout (`layout.words.sets`, `chat_flow.SETS_PAGE`). The answers are the same choices as before (`yes`, `use:<pic>`, `correct`, `correct_all`, `no`, `make`, `aside`, `own`, `rest`, `rest_out`), written the same way. Step 4 (design/212) is unchanged; its sets branches are removed.

**Part B.**
- B1: the server gives `say`, the message posted with the link (sets: what needs an answer by name, then the other sets, then "Then say done here."; other steps: the sentence of before). `how` step 4 and one instruction sentence (`scripts/d216_wording_v3.py`) say to post it unchanged.
- B2: the page answer carries `preparing` ("Preparing N pictures for the page, about M minutes.", 4 s a picture); `vw visuals page` stops before fetching 10 or more pictures, gives the sentence, and fetches on `--fetch`.
- B3: the "landmark and measured distance" and "as before" refusals count as retired for a v2 set (`visuals_stage.RETIRED_FOR_SETS`): the line says the plain sentence with "Make it"; the stored refusal of the last "done" is not repeated.
- B4: a place's request names its objects and materials (those its shots share), most shared first, with their approved references (golden, approved set picture, approved drawing, approved footage picture) as input pictures within Gemini's limits (14 in all, 6 objects), the rest in words; the check list adds "the film's own things in it match their references". `ref_sets._order` queues things before places (first go, the other sets, a remake). A place waiting for a thing's set says so on its line.
- B5: "These two people read alike, A and B: add what tells them apart."
- B6: MERGE_NONE, BACK_ASKED and the older rounds' "Leave it out" reworded; `vw visuals round --answer E --verdict correct --every-picture`.

## Older ways

Decision log rows 143 to 150 (`design/35-decision-log.md`). The older-round page digests (test_design211_together, test_design211c_lines) were taken again for B1 and B6 only.

## Not covered

- Not deployed, not seen on the live film; the page was checked in a headless browser with VW-24's round as text and grey stand-in pictures.
- Whether the picture model follows a thing's reference inside a place: seen only on the first real set.
- On VW-24 the tile is among the 17 waiting sets, which can be ordered only after the roof deck is judged: a "Make all 3 again" of the roof deck before the tile is approved is made with the tile in words (the line says so).
- The zoom view keeps the page's own large view (picture, caption, previous/next), not the trial's side panel with the faults; the faults are under the picture.
- The fetch is still one picture at a time (finding 16, "later: several at once"); `preparing` counts every picture of the round, also ones already fetched.
- An older page copy is not refused by the server: its answers are the same choices; the raised plugin minimum and the page-version check make the assistant publish the page again.
- Step 4 in the same style; mobile; findings 21 and 22.
