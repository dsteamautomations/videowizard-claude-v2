# design/216: the sets screen and the VW-24 corrections

18 Nov 2026. Built from `design/_work/sets-screen-release-18-nov-requirements.md` (approved by SK). Server 0.113.0, plugin 0.97.0 (minimum 0.97.0). Not deployed.

## What changed

**Part A, the step-5 screen** (`plugin/pages/decisions.html`, `layout.kind == 'sets'` only). The trial SK corrected over five rounds, ported: the list holds only what needs an answer, numbered, then "The other N sets"; "Settled earlier" folded; one large picture with the set's small pictures below and the footage beside it on a click; one answer for the whole set ("Approve all 3", "Make all 3 again", "Minor corrections"); the check's faults under each picture; Claude's recommendation as one coloured line with "more"; approving against "make again" asks once and marks the row "Against advice"; "Make B the main picture"; "Use my own picture instead"; the details folded; one count in the bottom bar; the end card. Arrows and Escape stay. Every word comes from the server: on the line (`answer_head`, `answer_note`, `strip_head`, `sure`, `rec.head/first/more`, per picture `name`, `set_cap`, `faults`, `check_head`, `check_none`, `main_label`, footage `cmp_cap`, the rest line's `name`, `things_wait`) and with the layout (`layout.words.sets`, `chat_flow.SETS_PAGE`). The answers are the same choices as before (`yes`, `use:<pic>`, `correct`, `correct_all`, `no`, `make`, `aside`, `own`, `rest`, `rest_out`), written the same way. Step 4 (design/212) is unchanged; its sets branches are removed.

**Part B.**
- B1: the server gives `say`, the message posted with the link (sets: "N things need your answer:" with one name per line, the plan's names as they are, then the other sets, then "Then say done here."; other steps: the sentence of before). `how` step 4 and one instruction sentence (`scripts/d216_wording_v3.py`) say to post it unchanged.
- B2: the page answer carries `preparing` ("Preparing N pictures for the page, about M minutes.", 4 s a picture); `vw visuals page` stops before fetching 10 or more pictures, gives the sentence, and fetches on `--fetch`.
- B3: the "landmark and measured distance" and "as before" refusals count as retired for a v2 set (`visuals_stage.RETIRED_FOR_SETS`): the line says the plain sentence with "Make it"; the stored refusal of the last "done" is not repeated.
- B4: a place's request names its objects and materials (those its shots share), most shared first, with their approved references (golden, approved set picture, approved drawing, approved footage picture) as input pictures within Gemini's limits (14 in all, 6 objects), the rest in words; the check list adds "the film's own things in it match their references". `ref_sets._order` queues things before places. After the critic's review: a place whose objects or materials have a set in the round with no approved reference yet is **held**, not ordered, in every go (`visuals_stage._queue_sets`: the first go, "Make the other N", a remake after Claude's rewrite, "Make it"); its line says "Waits for X: it is made when their sets are approved.", it counts as not judged, and it is ordered by itself (`ref_sets.release`, through the usual queue) in the same call as the last of those approvals, or when such a thing is set aside (then that thing is in words). A thing that needs no reference, has the operator's own picture or is settled from its footage holds nothing. "Make all 3 again" on such a place is recorded and counts as judged; the rewrite is stored and its make waits. The line says "It will be made again after the set of X is approved, so that it shows the real X."; the other sets' answer says how many are made now and which places wait for which things.
- B5: "These two people read alike, A and B: add what tells them apart."
- B6: MERGE_NONE, BACK_ASKED and the older rounds' "Leave it out" reworded; `vw visuals round --answer E --verdict correct --every-picture`.

## design/216b (18 Nov 2026, after the deploy of 0.113.0): Claude names a place's things

Server 0.114.0, plugin 0.98.0 (minimum 0.98.0). Which things belong to a place is a reading job: Claude gives, for each place, `things` (ids of the
film's objects and materials that are fixed parts of it or always stand in it; never a tool or a prop that only passes through, never a person;
[] when none) with `things_reason`, with its step-4 proposal, or later with `vw visuals round --things` (no file: what to read, written to
work/visuals/things-asked.json: each place's description, its shots' words, the plan's objects and materials; with a file: the rows). The server
checks each id (an object or a material of the plan, not the place; else refused naming the word) and stores the list on the place's row. A
place with no list is never ordered: `_queue_sets` marks it `things_due` and every "what next" asks Claude for the list
(`ref_sets.things_due_words`); `round_things` stores it and orders the place (which may still be held for its things' sets, as before). The
list drives the hold, the input pictures (Claude's order; over Gemini's limits the rest in words), the check line and the line's sentence; the
place's Details show "The film's things shown in this place: A, B. <reason>". A thing removed from the plan is dropped; one answered "No
reference needed" is named in words and holds nothing. On deploy, a place still held on the 0.113.0 guess drops that hold and waits for
Claude's list (in `ref_sets.release`, run on every page and chat call); a place already ordered or made is untouched.

VW-24 after the deploy: SITE_DECK, ROOM, SITE_BELOW and LANE have no list. Whichever of them is held (the deck after its correction or remake
answer; ROOM after "Make it"; SITE_BELOW and LANE after "Make the other 17") becomes "waits for Claude's list" at the first page or chat call;
the next "what next" asks Claude for the four places' things; once sent, each is ordered, or held until the things named (the tile for the
deck, if Claude names it) have approved sets, then ordered by itself. A place ordered on 0.113.0 before the deploy (its things approved in
between) is left alone and is not ordered again.

## Older ways

Decision log rows 143 to 153 (`design/35-decision-log.md`). The older-round page digests (test_design211_together, test_design211c_lines) were taken again for B1 and B6 only.

The page check of step 1 for a person the footage shows and the writer's words, lost with the old sets screen's checks, is restored (`server/unit/test_design216_step1_browser_pure.py`).

## Not covered

- Not deployed, not seen on the live film; the page was checked in a headless browser with VW-24's round as text and grey stand-in pictures.
- Whether the picture model follows a thing's reference inside a place: seen only on the first real set.
- On VW-24 the roof deck's "Make all 3 again" now waits for the tile's set (one of the 17): it is made after the tile is approved. Seen only in unit tests, not on the film.
- The zoom view keeps the page's own large view (picture, caption, previous/next), not the trial's side panel with the faults; the faults are under the picture.
- The fetch is still one picture at a time (finding 16, "later: several at once"); `preparing` counts every picture of the round, also ones already fetched.
- An older page copy is not refused by the server: its answers are the same choices; the raised plugin minimum and the page-version check make the assistant publish the page again.
- Step 4 in the same style; mobile; findings 21 and 22.
