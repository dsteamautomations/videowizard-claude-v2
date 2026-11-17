# design/213: the references sets screen in the new layout, and the corrections of step 5

**Status:** built on 17 Nov 2026, server 0.110.0, plugin 0.94.0 (the plugin minimum is raised to 0.94.0: every laptop updates); **not deployed**, not pushed.

**Why:** the first real film, VW-24, reached "References step 5" (judging the sets) on 17 Nov 2026 with two sets made. The issues are in `design/_work/references-step5-issues-17-nov.md`, with the judgement of each correction the owner read. A trial page with VW-24's real data was approved; it is kept beside the repository, in `ux1-mockup/vw24-step2/` (`sets-redesign-trial.html`, screenshots in `shots/`). This change builds that screen into the real page and the server, and the corrections.

## 1. What is built

One flow, two front ends: the group, the order, the case, the buttons and every sentence of step 2 are built in `chat_flow._round_v2`; the page (`page_flow._sets_lines_v2`) and the chat (`vw visuals next`) read it. The page file only draws and writes the answers as every line's answer is written.

| | What | Where |
|---|---|---|
| S | **The screen.** Step 2 of a v2 round has `layout: {kind: 'sets', made, help, groups, pick}`. Four groups in order (`chat_flow.STEP2_GROUPS`): "To judge" (the sets Claude would make again or is unsure of first), "Could not be made", "Waiting to be made", "Settled". One set at a time: the film's own pictures to compare, the made pictures, the buttons directly under them, "Use as the reference" on each made picture of a thing (none chosen at the start), "i" for what Claude saw, "Why?", one chip for the check, the banner of the waiting sets ("Make them" off until the first sets are judged, "Show the N", "Leave some out" with a table), "Your answer" saying what will happen, keys, auto-advance. | `chat_flow._round_v2`, `page_flow`, `plugin/pages/decisions.html` (the `#things` layout of design/212, with a `sets` branch) |
| P | **A place gets one picture**, "the whole place", in a round posted from this release on (`round['place_one']`). A round posted before keeps three for every place, also one not ordered yet. Its line has no A, B, C: Approve takes the one picture. | `ref_sets.views_for(element, plan, rd)`, `ONE_LINE`; the line builder |
| W | **A way of working**: no code change. The instructions say: propose "leave" unless a still (not an AI video) shows the action, with that reason. | `scripts/d213_wording_v3.py` |
| L | **A person the footage shows.** A look at a frame records `face` (and `child`), as seen. At step 1, a person with a kept frame whose look says it shows the face is asked one thing: "Your footage shows this person. Do you have their permission to make pictures of them?" (for a child: "the permission of a parent or guardian"). "I have their permission" needs their own words, recorded through `visuals_stage.likeness`; the kept frames then go to the set, the best face frame first, and a check line asks that the face matches the footage. "Make a stand-in": the set is made from the description, nothing of the footage person is used or shown to the looker, and the line says "The made person will differ from the person in your clips." Frames that show only hands or the back: no question. | `ref_find.look_extra`, `faces_of`; `ref_sets.footage_person`, `inputs_of`; `chat_flow._round_v2` (case `likeness`) |
| C | **The plan against the footage.** No new field: the row's added words (`prompt`). They now rank above the film's own pictures in the request (the operator's words stay first), and the footage check line says these words win. The instructions tell Claude to write there what to take from the footage and what from the plan. The words are shown openly on the step-1 line and the step-2 line of a thing that has footage pictures ("Claude added for the picture: …"). | `ref_sets._authority`, `_lines`; `chat_flow` (`differs`) |
| K | **The check tells the truth.** "A real face" is asked only when footage frames go with the request of a set that is not a permitted likeness; never on a set made from words. "Same as picture 1" became "the same thing as picture A, seen as this picture's view asks", and is given each picture's view. | `ref_sets.set_request`, `image_check.SAME_THING` |
| N | **The notes.** Each picture keeps its own notes of the image model. Claude's look gives two plain lines per set, `chose` and `aside` (required when the set has notes: `ref_sets.LOOK_MODEL`); the line shows them behind one click and the chat says them; the raw notes stay in the record. The looker gets the thing's kept footage pictures also when the set was not made from them (`footage-N.jpg`). | `visual_workers`, `ref_sets.round_looks`, `looks_due`, `set_facts` |
| F | **A first set that cannot be made is replaced** by the next waiting one, so the first go is three made sets where three are possible. Not after a limit refusal, and not when none of the first sets could be ordered. | `visuals_stage.round_done` |
| | **The limit with no amount.** Where the film's limit has no room at the references of a v2 round, the refusal is one sentence: "These cannot be made now: the film has reached the limit its owner set. Ask the owner to raise it." On the line, the page and the chat. | `ref_sets.LIMIT_PLAIN`, `is_limit` |

## 2. What each button records

| Button (page; key) | The chat | Sent | The server |
|---|---|---|---|
| Approve (A), a person | Approve | `yes` | `visuals_stage.set_answer` yes: picture 1 is the reference, the face goes with it |
| Approve (A), a thing: after "Use as the reference" on a picture (1 2 3) | Approve A, Approve B, Approve C | `use:<picture>` | yes, with that picture as the reference. Approve with no picture chosen is refused on the page: "Choose the picture that is the reference first." |
| Approve, a set of one picture | Approve | `use:<the picture>` | the same |
| Minor corrections (C), words required | the same | `correct` + words | the set waits for Claude's rewrite, then is made again |
| Make again (M), after a small confirm | the same | `no` | the same, from the checks and the look. Not offered when the set was made three times: the line says so, and a thing then has Leave out |
| Make it again from the changed plan | the same | `remake` | `visuals_stage.set_make` |
| Upload my own (U) | `vw visuals own` | `own` | the existing own-picture path; a person's photo with the words of permission |
| A set not made: Make it (M), Upload my own, Leave out (L) | the same | `make`, `own`, `aside` | `set_make`, the own-picture path, `set_aside` |
| A refused photo: Another photo, A stand-in (words) | the same | `photo`, `standin` | as before |
| A thing back after a second send: Make a set, Add words for the picture, Leave out | the same | `approve`, `words`, `ignore` | `ref_sets.round_reopen` |
| Make them | Make the other N sets | `rest` | `ref_sets.round_rest` |
| Leave some out, then "Leave these N out" | Leave these N out (and make the other M) | `rest_out` | each is set aside; the people, who always get a set, are ordered on the same word |
| Step 1: I have their permission (words) · Make a stand-in | the same | `permit`, `standin` | `visuals_stage.likeness`, then a set is made (`approve`) |

## 3. What changed against the judgement the owner read

- **Places:** one picture, not a composition drawing. No later step uses a place's second or third picture, and the three did not show one layout on VW-24. A composition drawing stays allowed where Claude judges a place needs one, as before; it is not made a rule.
- **Item 2 (a person from the footage):** the line asks for the permission only, and only where a kept frame shows the face. It does not ask "is this the person the film means": where the footage person is not the film's character, Claude gives the row no frames. A stand-in "will differ from" the person; nothing promises it "will not resemble" them.
- **Item 3 (plan against footage):** the existing added words are used; no new line per thing and no new field. They are shown openly, not behind "Why?".
- **Item 4 (a real face):** the rule is reversed: the line is asked when footage of a thing goes with the request (a face could be copied from it), and never on a set made from words or on a permitted likeness.
- **Item 9 (the notes per picture):** kept, per turn, by the worker, which already holds them per turn; no free text is split by a program.
- **The limit sentence** is new: without it the no-cost rule would have left "Make them" unanswered.

## 4. Decisions taken by default (the owner can change any)

1. **This changes default 9 of design/211 section 8.1** ("Sets of places and ways of working are still made"): a place's set is one picture in a new round; a way of working is proposed "leave" unless a still shows its action. Reason: after this step one picture of a set is used, and nothing on the video route reads a place's or a way of working's set.
2. **"Claude added for the picture: …"** is the sentence on the line. No field says that the added words are a difference from the footage, so the line does not claim one; the instructions make Claude write the difference there.
3. **"Leave these N out" also makes the others** (the people) on the same word, as the approved trial said ("6 sets will be made. 11 are left out."); the chat's button says so.
4. **A thing back after a second send** is under "To judge": it waits for the operator, and nothing "could not be made".
5. **A partial set, or one whose plan changed, is not listed first**: only Claude's "make again" or "look closely" is. Both are said openly on the set.
6. **A one-picture set is charged as one picture**; the estimates that count three per set (the room for "Make them", the summary of the tool) still count three: they err on the careful side.
7. **A replacement of a failed first set** is not ordered after a limit refusal, nor when no first set could be ordered (an outage leaves the rest waiting).
8. **The answers kept on the page** ("Kept from before: …"), the panels' words and the keys are the page's own fixed words, as on step 1.

## 5. Older ways (rows 119 to 127 of `design/35-decision-log.md`)

The groups and the labels of step 2 before; three pictures for a place; a person with footage frames made from words; the film's pictures above the writer's words; "a real face" on every person's set and "same as picture 1"; the notes joined and shown raw; the limit refusals with amounts; "Leave these out" leaving the people for a second click; a failed first set not replaced.

## 6. Not built

- **A composition drawing for places as a rule** (issues 6, 7, 15).
- **Whether a thing's footage frame that also shows people may go to the image model without a permission question** (`visuals_stage`, the frames of a thing): the owner decides.
- **Step 4's open findings:** the helpers' usage; what counts as doubtful; the word "free" in Claude's reasons; the chat naming amounts after "done" (`ref_sets.GO1_MAKING`, `ALL_MAKING`, `REWRITE_MAKING`).
- **Of the trial:** "Clear my answers", the trial banner, its example placeholders, its own upload panel (the page's upload is used).
- A phone layout for step 2. An older round keeps the layout it had.

## 7. Tests

- `server/unit/test_design213_layout_pure.py` (23): the four groups and their order; VW-24's stored round in its shapes (`vw24_step2_shapes.json`: 2 to judge, 1 not made, 17 waiting, 14 settled; 35 lines; its made sets with three pictures; nothing stored by showing it); every button and what it records, page and chat; a set made three times; a changed plan, a partial set, a set made again; "Look closely"; the two lines for the notes; a set of one picture; the limit sentence; the writer's words; the permission case; no cost at five states; an older round. The round the page checks draw (`d213_sets_round.json`) is asserted to be the server's own output.
- `server/unit/test_design213_core_pure.py` (23): P, C, K, N, F, L and the limit in `ref_sets`, `image_check`, `visual_workers`, `visuals_stage`, `ref_find`.
- `server/unit/test_design213_browser_pure.py` (11 runs, headless Chromium): 1366×768 and 1920×1080, light and dark; what each button writes; the waiting sets; not made, waiting, settled; the keys and auto-advance; 1000 px; all answered; step 1's permission question and the writer's words.
- `plugin/tests/test_design213_looks.py`: the tool fetches the footage pictures of a look and passes `chose`, `aside`, `face`, `child`.
- Tests of design/211 and 212 whose pins changed are listed in the commit message.

## 8. Not verified

- Not deployed; no claude.ai page was published: the page file was drawn in a local headless browser with a stand-in for the page's database and file store.
- VW-24's own session was not read (no database, no VM): the proof uses the shapes of its 35 lines as the live server gave them.
- No real model call: the request of a one-picture place, the face check line, the two lines for the notes and the per-picture notes were not seen on a real set. The helper files were not run.
- The page while Claude is looking at a set (state "looking") is tested on the server only, not in the browser.
- The whole suites were not run (the owner's rule of 17 Nov): only the tests of this area.
- A person with kept frames that show no face: their set is still made from the description, while step 1 says "from the ticked pictures". Not corrected here.
