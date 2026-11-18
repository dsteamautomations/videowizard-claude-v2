# References steps 4 and 5: review before the seven changes (18 Nov 2026)

Read-only review of main 3f2bb88 (server 0.111.0 / plugin 0.95.0). Nothing was edited, committed, started or deployed. Only critical or serious points are listed. Paths are under `server/app/` unless said. "Ran" means I called the pure function locally with a sample string (no server, no database).

## A. Old rules that can refuse or distort a server-written v2 set request

Path walked: `_queue_sets` (visuals_stage.py:3341) → `generate_image` (3898) → `_queue_image` (4496), and `library.check_prompt(..., placed=False)` (library.py:236).

### A1. CRITICAL: the prompt lint still reads the plan's own words (4 rules), and the operator cannot fix any of them

`visuals_stage.py:3990` runs `check_prompt` on the whole server-written request. `placed=False` switched off only the two placing rules of defect 54. The other four still fire on the plan's description, the sizes, the writer's words and the operator's words. Ran, all refused:

| Rule (library.py) | Sample in a thing's description | Result |
|---|---|---|
| logo, line 240-242 | "a paper cement bag with the brand logo printed on the front" | "The prompt asks for a logo … the editor places it" |
| pixel size, line 246 | "a 600 x 600 mm vitrified tile" | "The prompt names a pixel size ('600 x 600')" |
| model word, line 243-245 (`flare`, `omni`, `sunburst`, `kling`, `seedance`) | "a trumpet with a wide flare", "a white Maruti Omni van" | "The prompt names a model" |
| resolution, line 249 | "a 1080p monitor" | refused (not run, same pattern) |

The logo rule also contradicts the request's own text (`ref_sets.FINISH`, line 144: "No text, lettering, logo or mark except what the description names") and hits every product or advertisement film whose product carries its brand.
The refusal is stored on the row and shown to the operator as "This set could not be made" with a sentence written for a prompt writer; "Make it" repeats it.
**Should it fire on a v2 set: no.** Smallest fix: at 3990, for a v2 set lint only the assistant's own words (`v2row['prompt']`), not `body['prompt']`.

### A2. CRITICAL: the quoted-words rule reads the whole v2 request

`visuals_stage.py:4053-4057`: with no answer form, `library.check_quoted(writer_prompt, [])` runs, and `writer_prompt` (3947) is the full server-written request. Ran, all refused:
- `a 4" pipe joined to a 6" pipe` (inch marks pair up as a quotation)
- `a 6' ladder against a 10' wall` (foot marks)
- `a bag printed "OPC 53 Grade"` (lettering the description names, which the request explicitly allows)

A v2 set has no exact-text field, so nothing can satisfy the rule. Very likely on a construction film. **Should not fire.** Smallest fix: skip this `elif` when `v2row is not None`.

### A3. SERIOUS: "cites the footage" sits beside "measure it first" and is the same kind of rule

`visuals_stage.py:3938-3941`: a thing whose size or fact source contains "footage" or "clip" (`visual_contract.FOOTAGE_CITED`, line 1301) and has no approved footage frame is refused: "approve a footage frame of X … and mark it identity exact in the plan".
Scenario: the plan's size says "estimated from clip C0084"; at step 4 the operator unticks every footage picture (or the finder found none) and chooses Make a set. Refused, with an instruction the operator cannot follow on the page.
**Should not fire on a v2 set** (the operator decided at step 4). Smallest fix: guard the whole block 3936-3946 with `v2row is None`; that also carries change 2.

### A4. SERIOUS: the "Not this" list is appended to the server's request

`visuals_stage.py:4129-4132` appends `not_this_line` ("Not this (name): …; …; …") to every prompt, v2 sets included. The list (1880-1917) is up to 12 model-written "no …" lines, plus lines kept in the library from earlier films under the same thing name, plus every rejection note of the thing (`_rejection_lines`, 1876). It is built when a material spec is approved (4332, 4409).
- It is a long negative list (a habit for older models) outside the request's order of authority.
- In a v2 round the rejection notes are not faults of the thing: "not ticked by the operator: not used" (chat_flow.py:360), "the plan changed after this set was made; the set is made again" (3654), "left out after three makes" (3701), and the operator's correction words (3467), e.g. "make the handle longer", which would then read "Not this: make the handle longer", the opposite of what was asked.
**Should not be added to a v2 set.** Smallest fix: skip 4129-4132 when `v2row is not None`. Not verified on live data: whether VW-24 holds a list for any thing.

### A5. The other gates on the path

| Gate | Can fire on a v2 set | Should it |
|---|---|---|
| 3903-3906 style, element, kind | no | n/a |
| 3907 animal has no sheet | no (refused when the round is sent) | yes |
| 3909 set only through the round | no | yes |
| 3915 `distinct_people` (2012): any two people alike on the trait words | yes: two people whose descriptions carry no age, build, hair or face word count as alike (both empty), and then **every** person's set is refused, also a person made from their own footage pictures | partly: fine for stand-ins; for people made from footage the picture tells them apart. The plan check warns first (`people_alike`), so it is known before the round. Not changed by the seven. |
| 3942-3946 measure it first | yes | no (change 2) |
| 3963-3969, 3988 parents approved, person pictures need permission | no (`inputs_of` gives approved inputs, and a person's only with permission) | yes |
| 4001-4008 input counts | no (at most 3 frames + 2 drawings) | n/a |
| 4020-4022 every Image k named | no (all request shapes name them; checked each shape) | n/a |
| 4026 `_no_question` | only if a question is open on that thing | yes |
| 4133-4140 material spec approved; relative words | spec not approved: yes, correct, and the page says so. The relative-words check reads only the assistant's added words ("standard", "typical", "roughly" refused): acceptable | yes |
| 4187 the film's limit | yes | yes (said with no amount) |
| `_queue_sets` three makes | yes | yes |

Placing rules (library.py:254-261) and "Change only" (262): cannot fire on a v2 set. Clean.

## B. Collisions

### B1. Change 5 (correction words into the thing's description): do not write them into `description`

1. **Accepted gaps are asked again.** `gap_digest` (visual_contract.py:1463) covers the elements a gap uses; only `size` and `material_spec` are exempt (`ELEMENT_NOTES`, 1262). A changed description cancels the acceptance of every gap that uses the thing.
2. **The assistant's plan file overwrites it.** The plan is `out/visual-plan.json` on the operator's laptop; the next `propose` replaces a description the server changed.
3. **The set is marked changed.** `ref_find.fingerprint` (ref_find.py:515) includes description. A change after the set was queued gives "The plan changed since this set was made" with "Make it again from the changed plan" on the set just corrected; the footage search is marked stale (chat_flow.py:897-898, the thing becomes doubtful); a left-out thing comes back on the next round file (ref_sets.py:747).
4. **The words lose their rank.** In the request the operator's words rank first and the plan's description below the film's pictures (ref_sets.py:358-362). Moved into the description, a correction of the footage picture or drawing is overruled by them on the next make.
5. **Contradicting corrections.** Today only the latest is used (`operator_words[-1]`, ref_sets.py:430). Appended to a description, "grey" then "white" both stay.
6. **One view only.** "In the close-up the stamp is upside down" would go into every later picture.
7. **People.** Descriptions feed "This person is not X (description)" in every other person's set (ref_sets.py:451) and the alike test (A5): "make him older" can make two people alike and block all person sets.
8. Drawings: an approved drawing set is keyed to its own data (drawings.py:89), so it does not go stale, but its facts can then contradict the corrected description with nothing saying so.

Smallest fix: keep the words outside the plan, in the session per thing (one field, e.g. the row's final writer words plus the last operator words, taken when the set is approved), and add them in the one place later pictures read the thing's words, with the operator's rank. No plan version, digest or fingerprint moves. Note that pictures made from the approved reference picture already carry the correction visually; the words matter where no reference is passed (the AI-video route).

### B2. Change 2 (measure it first): three more places hold the same rule

- `set_cause` (visuals_stage.py:3597-3600) is the second copy. Left as it is, "Make it" still refuses (3648-3649), step 4 still warns "A set cannot be made now: a size … is not measured yet" (chat_flow.py:895-897) and the row is still marked doubtful (ref_sets.py:698; part of finding 6, 43 of 49 doubtful).
- VW-24's cement bag keeps the stored refusal on its row; the page shows the old sentence until "Make it" is pressed (`_set_state`, 3877 matches the words "size still unknown").
- Pinned: `server/unit/test_design119_e_pure.py`, `server/pagetests/data/main/refs-step2-size-not-measured.json` (and two set-aside files).
- Downstream: nothing needs the measured size. An unknown size is left out of the request (ref_sets.py:316-324) and of later prompts (`size_sentence`, 6465). One side effect: when the size is measured later, the fingerprint changes (size is in `FP_FIELDS`) and the approved set shows "the plan changed since this set was made".

### B3. Change 3 (what the model searched)

- Stored: `visual_workers._sources` (line 118) keeps web chunks only; the list goes on the reference (`apply_image_result`, 375) and `ref_sets.set_facts` reads it (579). **Nothing on the v2 page or chat shows it today** (only the older layout, decisions.html:565), and the looker is not given it.
- "Searched: yes/no" needs three states, not two: a person's set is never asked to search (ref_sets.py:475, `search: kind != 'person'`), and a set stored before the change has no record. "No" on those would read as a fault.
- A set made from footage is told to search "only for what the film's picture does not show" (ref_sets.py:129), so "no" there is correct behaviour; the label should not alarm.
- Count per set, not per picture: the search is offered on each of the three turns (visual_workers.py:122-160).
- Not verified: the field names Gemini returns for image-search grounding.

### B4. Change 6 (rename "Drawings and materials")

The step holds two kinds of line: materials **and the drawing specs of drawn shots** (page_flow.py:274-300; its summary counts "N materials and M drawings"). The second kind are real drawings of the film, so "Sizes and materials" fits the materials and the sizes, not a drawn graphic's parts and labels. Decide the name with that in view.
Places the old words live: page_flow.py:267-271, 316-325; visuals_stage.py:4304, 5544, 5796; `server/procedures/v3.json` (3 places); `plugin/commands/vw.md:46`; `plugin/scripts/vw.py:1110, 2356, 2852`; pinned in `server/unit/test_design125_stage7_c_pure.py`, `test_design209_pure.py`, `test_design210_pure.py`, `test_design210_wording_pure.py`, `plugin/tests/test_design207_review.py`, `test_design209_cli.py`, `test_design210_wording.py`. The step name is compared by constant (`SPEC_STEP`, page_flow.py:1055), so the rename is safe in code. Retired instruction sentences go into `server/retired-sentences.json` (tests read it).

### B5. Change 1 (rename "Leave out")

- One label does three jobs. Step 4 (chat_flow.py:923), step 5 on a set that could not be made or was made three times (1133, 1215), and the waiting sets ("Leave these N out", 581-582). "No reference needed" is wrong for a set that failed three times: the operator wanted one.
- An older label "No set needed" already exists for the proposal `no_set` (chat_flow.py:892, explanation 1686: "Its words carry it; nothing is made"). Three names for near the same answer after the change, unless merged.
- The line naming what the shots lose already exists (`WORDS['cost']`, 558-559; `loss`, 666-667): reword, do not add a second.
- **The page hard-codes the words** (not server-sent): `plugin/pages/decisions.html:290, 299, 726, 783, 802, 803, 889`. A page change means publishing the page again and a plugin release.
- Other places: chat_flow.py:428, 486, 530, 556-559, 583-593, 656-657, 666-689, 1683, 1687; ref_sets.py:92, 117; v3.json part 3 (twice, plus "left out"); vw.md:46. Pinned in 12 files of `server/unit/` (test_design210b, 210_review, 211c_browser, 211c_lines, 211c_record, 211_review, 211_together, 212_browser, 212_layout, 213_browser, 213_layout, d213_sets_round.json) and pagetests data.
- The hint beside "Make a set" ("Picture not good? Have a set made instead") fits only a thing with a footage picture and a free choice. For a person, or a thing with approved drawings, a set is the only way ("instead" is wrong); with no picture there is nothing to be "not good".

### B6. Change 7 (two goes) is not always two

Three sets or fewer: one go (ref_sets.py:786). More goes follow from Minor corrections and Make again (up to three makes each), "Make it" on a set that failed, and a thing that comes back. The second go is all or nothing at the limit (ref_sets.py:959). The sentence should say "the first three, then all the others together once you have judged those; a set you send back is made again on its own" and drop the second half when three or fewer are asked.
Today the two goes are said only inside "Accept all" (`WORDS['goes']`, chat_flow.py:573, 1027): an operator who answers each thing never reads it; the step-4 note (page_flow.py:695) and "How this works" (`WORDS['help']`, 548) do not say it. After "done" the sentence goes to the assistant only (`GO1_MAKING`), with no operator-facing line.

### B7. Change 4 (default look) meets the set request

- The film's category is read and stored with the request's parts (ref_sets.py:433-436, 473) but never used in the request text.
- `FINISH` (ref_sets.py:144) says "Natural colours, no filters, no stylisation, no illustration" in the same request that passes the film's look (`LOOK_LINE`, 151). With a non-muted default (an advertisement, a social clip) the two contradict. Decide which wins for a reference and say it once.

## C. Words that do not say what happens next; money still named

1. **"Minor corrections" at step 4** (chat_flow.py:533, 921). It does not correct the footage picture: it has a new set of three made by the picture AI from the ticked pictures with the operator's words, counted as one of the three makes. Its panel button reads "Send corrections" (decisions.html:782, 799), which suggests a message. Smallest fix: "Make a set with my words", panel button "Make a set with these words" (that wording already exists for a thing with no picture).
2. **"Approve" in the chat** is explained as "It is right; go on" (`SAYS`, chat_flow.py:1681). At step 4 it means "the ticked footage pictures become the reference; nothing is made". The right sentence exists under the older label (1685) and is no longer reached.
3. **"Make a set" is explained as "A set of three pictures is made"** (1687): a place gets one picture, and nothing says when (at done, or in the second go).
4. Money and cost words still present:
   - Assistant-facing sentences with amounts: `GO1_MAKING`, `ALL_MAKING`, `REWRITE_MAKING` (ref_sets.py:31, 32, 46), `set_make`'s `then` (visuals_stage.py:3663); every answer also carries `cost_inr`. The assistant reads these and can repeat them.
   - **On the page:** when "done" at step 4 would pass the limit, page_flow.py:742 says "about ₹…, and ₹… is spent of the ₹… limit", shown as "Not recorded: …" (693). The instruction text allows it ("only a refusal after done names the limit") but the owner's ruling was no cost on this page. Smallest fix: `ref_sets.LIMIT_PLAIN` for a v2 round.
   - "(paid)" in the chat explanation of "Make it" (chat_flow.py:1683).
   - `plugin/commands/vw.md:46`: "it prints `held` … tell the operator the spend", and "(free)", "(paid …)" on the references steps.
   - `v3.json` part 3 (line 288): "free", "(paid)" three times. This is where finding 15 ("The exact thing, free." in reasons) comes from; no sentence tells the assistant or the finder not to write a cost word in a reason.

The page itself (decisions.html) names no amount on steps 4 and 5. Clean.

## D. Instruction text against live behaviour

1. **Unticked pictures: contradicts the code.** v3.json part 3 says "an unticked picture is not this picture (the next best is then shown and the thing comes back once)". Live: an unticked picture is only not used and no other is searched (chat_flow.py:355-360, 899-901); "Not this picture" is its own button.
2. **Order of authority: contradicts itself and the code.** The same part says the assistant's added words rank above the film's pictures, and later lists "the operator's words, the film's own pictures, your added words, the plan's description, then web photographs". Code: operator, added words, film's pictures, plan, web (ref_sets.py:358-362).
3. **`plugin/operator-CLAUDE.md:12`** lists the helpers allowed in the operator folder and leaves out `vw-reference-finder` and `vw-set-look`, which the steps tell the assistant to start. It also says "Paid steps are information, not a question", against "nothing paid is ordered without their words" on the references.
4. **Two goes:** the text tells the assistant how the making goes, never to tell the operator (change 7 covers it; add it to part 3 and vw.md).
5. Stale labels: "Use my own picture, on the thing's line" (v3.json part 3, vw.md:46); the button reads "Upload my own". "Every person gets a character sheet" against the owner's one word, "set" (the request to the picture model also opens "Character sheet of …", ref_sets.py:449).
6. vw.md:46 says a set is "three separate pictures"; a place is one.
7. **Documentary-only in general text:**
   - "muted and true to life by default" (v3.json:278), change 4.
   - Every set request asks for a "photograph-like image", "no illustration" (ref_sets.py:125, 144), and `_look` drops any sentence of the look that mentions drawn or animated pictures (152, 342-346). A film whose made pictures are stylised or illustrated still gets photographic references. Not verified whether such a film is in scope today.
   - An object may show "no person and no face", only "the hand that holds it" (ref_sets.py:178-181, check line 404-405). A product that is worn (a helmet, a watch, a garment) cannot be shown "as the film uses it", and Claude's check must fail a picture that does.
8. Older-model habits: only the "Not this" list (A4). The v2 request itself is plain sentences with no keyword stacks or quality tags.
9. Clean: both helper files and v3.json agree that Claude, not Gemini, checks the sets, that the server writes the request, and that nothing is appended (the rewrite replaces the added words). `vw-set-look.md` matches design/214.

## Not verified

- Live data of VW-24 (which things hold a "Not this" list, a quoted word, an inch mark or a logo in their description).
- Gemini's grounding fields for image search (change 3).
- `server/tests` and the page tests were not run; only the two lint functions were called with sample strings.
- `design/211`-`214` were not re-read line by line; the code was taken as the truth of what is live.
