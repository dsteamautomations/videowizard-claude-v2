# References step: who does each job, and who should (audit B, 17 Nov 2026)

Read-only audit. No code changed, nothing run on the server, the VM or the database.

**Actors.** S = server code (rules, regex, tables, templates). A = the assistant on the operator's laptop. M = a model the server calls (Gemini Flash for checks and measures, Gemini image for sets). O = the operator.

**Sources.** `server/app/visuals_stage.py` (VS), `chat_flow.py` (CF), `page_flow.py` (PF), `image_check.py` (IC), `visual_workers.py` (VW), `visual_contract.py` (VC), `library.py` (LIB), `drawings.py`, `plugin/scripts/vw.py`, `server/procedures/v3.json` stage 9 part 3 ("4. THE PICTURE SEARCH"). Film evidence: `ux1-mockup/vw24-part1/evidence.json` and `round.json` (VW-24: 50 plan elements, 10 footage frames, 49 lines on the step-1 page).

**FACT** = read in the code or in the VW-24 files. **INFERENCE** = a risk reasoned from the code, not seen on a film.

**Count: 59 judgements. Wrong actor 31. Right actor 22. Unclear 6.**

Size of change: S = a few lines, M = one function or one new model call, L = a change of flow.

---

## 1. Every judgement in the step

### A. Finding each element in the footage

| # | Job | Today: actor, place, quote | Right actor | Why | Symptom or risk | Size |
|---|---|---|---|---|---|---|
| 1 | Which clip shows the element | **S**, VS:2943 `element_matches`: `shared = want & (_words(ent.name) \| _words(ent.description))` | M (vision on a frame) or A looking at frames. **Wrong** | Word overlap cannot tell a mason from a mason's trowel | FACT (VW-24): MASON's best hit is the entity `mason_trowel`; TILEMAKER's is `mason_foreground`; SAND_HEAP's is `wet_concrete_pile`; CEMENT_BAG's is `mangalore_tiles_stack`; BAR_BUNDLE's is `measuring_tape`. Already proven by the owner | M |
| 2 | Which second of the clip | **S**, VS:2960 `'seconds': ent.get('first_seen_s')` | M or A. **Wrong** | First seen is not best seen | FACT: 38 of the 43 top hits in VW-24 say 0.0 s | with 1 |
| 3 | Whether the kinds agree | **S**, VS:2926 `KIND_MATCH` table, +1 to the score | Goes away with 1. **Wrong** | A table of kind pairs is a guess about meaning | FACT: the table lets an animal match a `person` entity | S |
| 4 | What A is told about the hits | **S**, vw.py:2485 prints only `hits[0]` and "and N more clip(s)" | S. **Unclear** | Fine once the hits are true; today it hides the better hits | FACT: A sees one clip per element in the tool's line | S |
| 5 | Deciding "the footage does not show it" | **S**, twice. vw.py:2485: no word hit means "not seen in the footage … its set is made in the round". PF:475: no grabbed frame means the page says `'Your footage has no picture of {x}. '` | M or A decides; S only stores the answer. **Wrong** | The server states a fact about the footage that nobody checked | FACT: the VW-24 page told the operator "Your footage has no picture of this person" for the mason, while the analysis lists `mason_foreground` (head and torso at 10.9 to 11.7 s). The paid set followed | M |
| 6 | Choosing the clip and the second of the frame, and judging it sharp, large, evenly lit | **A**, from the analysis text. Rule only in the instruction: "take the sharpest frame, the subject large and evenly lit, never a blurred one". S grabs blind, VS:2896-2906 | A chooses, then someone must look: S can score sharpness, M or A confirms the element is in the frame. **Wrong** (a look is missing) | A picks a time from words; no step looks at the grabbed frame before the operator | FACT: 7 of VW-24's 10 frames come from a clip that is not in that element's hit list, so A ignored the hits. One frame (STONE_HEAP) ended rejected. INFERENCE: why | M |
| 7 | "Every element the footage shows gets a frame" | **A**, instruction only ("grab a frame of each the footage has") | S enforces, from a true list of sightings. **Wrong** | The repo rule: an instruction must not be the only place a rule lives | FACT: TROWEL has the entity `mason_trowel`, no frame was grabbed, and a paid set was asked. INFERENCE: that the footage frame was good enough | S after 1 |
| 8 | Cutting the frame, keeping clip and time | **S**, VS:2896-2906 | S. **Right** | Exact and repeatable | none | |
| 9 | Which elements the round takes (no graphic, no animal, every person a picture is made of) | **S**, VS:3181-3196 | S. **Right** | A rule of the flow | none | |
| 10 | Leaving a thing out of the round file | **A**, silently. S asks a row only for people (VS:3195) | S requires a row for every thing; leaving out is O's. **Wrong** | A thing with no row gets no reference and nobody is asked | INFERENCE (VW-24's file had every thing) | S |
| 11 | Which things need reference drawings first | **A**, instruction only ("a thing whose construction, pattern or mechanism must be right … is drawn before the round") | A. **Unclear** | The judgement is A's; but nothing reminds or records the decision per thing | INFERENCE: a thing that needed drawings goes straight to a set | S |
| 12 | Drawings approved before Done | **S**, VS:3580 | S. **Right** | Order | none | |
| 13 | Approving a drawing set | **O**, drawings.py:121 | O. **Right** | | none | |

### B. Writing the round and the set prompt

| # | Job | Today | Right actor | Why | Symptom or risk | Size |
|---|---|---|---|---|---|---|
| 14 | The subject block of a thing, the why line of a person | **A**, VS:3192 | A. **Right** | Writing | none | |
| 15 | Refusing a subject block that "describes how" | **S**, VS:1972 `HOW_WORDS = (step by step\|how to\|how it is done\|procedure)` | A's own check, or drop it. **Wrong** | Four phrases cannot read meaning | FACT: T_POUR's block says "the pan held in both hands and tipped away from the body" (it describes how) and passes | S |
| 16 | Are two people alike | **S**, VS:1994-2016 `TRAIT_WORDS` regexes; `traits(a) == traits(b)` refuses | A or M reading the two descriptions. **Wrong** | Likeness is a reading job | FACT: `4\d` counts any number from 40 to 49 as "in their forties". INFERENCE: two people who differ only in words outside the list are refused; two who share a face but differ in one listed word pass | M |
| 17 | The person prompt | **S** template, VS:2054-2074: all outfits joined (2059), one "Not X: …" line for every other person (2070) | S for the facts; A for which outfit and which people to set apart. **Unclear** | Assembling plan facts is S's; six negative descriptions in one prompt is a choice | FACT: VW-24 has 7 people, so each sheet carries 6 other people's looks. INFERENCE: traits bleed across | S |
| 18 | One prompt wrapper for every kind of thing | **S**, VS:2025-2041 with `KEPT_PREAMBLE`, `KEPT_COSMETICS` ("No person …", "Camera close enough … the surroundings soft") and the must lines `KEPT_THING_LINES` ("no person, no hands, no face"; "the subject fills the frame … the setting is only a soft hint") | A says per element what applies, or S keeps a wrapper per kind. **Wrong** | A technique needs hands; a place is its surroundings | FACT: T_POUR ("pan held in both hands") is sent with "No person" and checked against "no hands". STREET ("wide enough to see several houses") is sent with "surroundings soft" and "the subject fills the frame" | M |
| 19 | The place and the look named in every set | **S**, VS:2019-2022 `_place_look`: the first scene that has a `location_time` | A, per element. **Wrong** | A film has more than one place | FACT (code): ROOM, HOUSE, LANE and TILE_YARD sets all get the first scene's place. INFERENCE: wrong setting hints | S |
| 20 | The three views of a set | **S**, VS:1976-1984 fixed `THING_VIEWS` / `PERSON_VIEWS` | A: the plan already has `required_views` (VC:47). **Wrong** | The plan's author knew which views the film needs; the server throws them away on a kept film | FACT: MASON asks "right hand and forearm"; TILE asks "underside" and "a stacked pair in a grid bay"; PAN asks "tipped, pouring". None is ever requested | S |
| 21 | A set is three pictures | **S**, VS:1993 | S. **Right** | Cost stays predictable. (VW:64 says 4: a loose end, not an actor fault) | none | |
| 22 | Google search on for every thing's set | **S**, VS:3752 `'search': True` | **Unclear** | Needed for a method (a bond, a technique); doubtful for a bucket or for a thing with a frame and drawings | INFERENCE: time and a second source of truth beside the frame | S |
| 23 | Which image model makes sets | **S**, VS:4000 | S. **Right** | A fixed decision | none | |
| 24 | Which footage frame is Image 1 of a set | **S**, VS:3748 `own[:1]` | O's pick (see 27). **Wrong** | "First" has no meaning: the session is stored key-sorted (VS:2514 says so) | FACT (code): with two approved frames the one sent is arbitrary. TILE had two | S |

### C. Step 1 (the operator's first answers)

| # | Job | Today | Right actor | Why | Symptom or risk | Size |
|---|---|---|---|---|---|---|
| 25 | Use the footage picture, make a paid set, leave out, own picture | **O**, one question per thing, no recommendation; CF:390-407 | O decides; A or M pre-answers and O reviews the exceptions. **Wrong** (O asked the routine) | Most answers are forced by the rules (a person always gets a set) | FACT: round.json: "49 things: 49 to answer … up to 41 sets, about ₹1,450". Every person line says "A reference set is made for every person" and still asks | M |
| 26 | Deciding a thing needs no AI set | **S**, VS:3202-3220 `_from_footage`: an approved frame and no drawings means no set | O, with a recommendation; a third answer "make a clean set from this frame" is missing. **Wrong** | A working frame is not always a fit reference | FACT: the buttons are only "Yes, use it" and "Leave it out" (CF:407). PAN's reference is the frame "pan tipping concrete onto the grid". INFERENCE: a cluttered frame becomes the picture every shot starts from | M |
| 27 | The golden picture of a footage thing | **S**, VS:3218 `session['golden'][eid] = approved[0]` | O ticks, as at step 2. **Wrong** | Same as 24: "first" is arbitrary | FACT (code) | S |
| 28 | Approving the footage frames | **S** approves every frame of the row on one yes, VS:3604-3609; the page shows the first four, PF:474 `[:4]` | O, per frame. **Wrong** | A yes to what was shown approves what was not | INFERENCE (no VW-24 row had more than two) | S |
| 29 | Saying what "Leave it out" costs the film | Nobody. CF:875: "This thing gets no reference" | S computes the shots that show the thing and says so. **Wrong** | The server knows; later, `bind` wants a reference for every element of a shot (VS:4752) | INFERENCE: a later shot stalls or is made from words alone | S |
| 30 | Consent to spend at Done | **O**; the price is on the button, PF:430 | O. **Right** | | none | |
| 31 | Price, count of sets, the cap | **S**, VS:693, 3620, 4000 | S. **Right** | Must be the same every time | none | |
| 32 | A real person's likeness | **O** in their words; **S** enforces at every door, VS:2518-2537 | O and S. **Right** | | none | |
| 33 | Which photo or frame of that person is used | **S**, VS:2507-2515: newest own photo, else the earliest-made frame | O. **Unclear** | Small; a face-poor frame may be chosen | INFERENCE | S |
| 34 | Taking the operator's own picture as approved | **O** gives it, S approves on upload, VS:2635 | O. **Right** | Their picture, their word | none | |
| 35 | Undo of Done | **S**, VS:2472 | S. **Right** | | none | |

### D. Making the sets

| # | Job | Today | Right actor | Why | Symptom or risk | Size |
|---|---|---|---|---|---|---|
| 36 | Queue, ids, round number, pass state | **S**, VS:3276-3309 | S. **Right** | State | none | |
| 37 | Size measured and material spec approved before a set | **S** gates (VS:3760, 3946); **M** measures (VS:4268) | S and M. **Right** | | none | |
| 38 | "This element cites the footage, so it needs a frame first" | **S**, VC:1299 regex `\b(footage\|clips?)\b` on source text, used at VS:3757 | S, on a plan field A fills. **Wrong** | A word in a sentence stands in for a decision | INFERENCE: "no footage of this" would trigger it | S |
| 39 | Material words lint | **S**, LIB:271 regex (`roughly\|approximately\|typical\|standard`, "short brick") | A. **Wrong** | Pattern on prose | FACT: the comment at VS:2045 records that it refused the server's own preamble and no material set could be made (VW-19) | S |
| 40 | Applying the operator's correction | **S**, VS:3286: every past correction appended as "The operator's correction: …" | A rewrites the subject block. **Wrong** | Corrections can contradict the block or each other | INFERENCE | S |
| 41 | Making sets when A posts the round again after Done | **A's post spends.** VS:3246-3255 `_round_merge`: the row is set `'verdict': 'approve', 'ignored': False`, its candidate frames are approved, and "the set is made at once" | O. **Wrong** | Spend, approval of frames and undoing "Leave it out" are the operator's | FACT (code): a thing the operator left out, posted again by A, is made and paid with no operator word | S |
| 42 | `vw visuals round --make E` | **A** may call it; no operator quote, VS:3512, vw.py:1988 | O's word. **Wrong** | Paid | INFERENCE | S |
| 43 | Why a set failed, in plain words | **S**, substring tests, VS:3447, 3709 | S. **Right** (brittle: use codes) | | none | |

### E. Looking at a set before the operator does

| # | Job | Today | Right actor | Why | Symptom or risk | Size |
|---|---|---|---|---|---|---|
| 44 | Checking a made set | **M**, Gemini Flash at low thinking (IC:21), **on picture 1 only** (VW:390 "the check runs on the first"), against generic lines; it never blocks (IC:476) | M on all three, against the footage frame, the plan's description and each other; A reads the result. **Wrong** | The set line asks "keep every detail the same across the set"; nobody tests it | FACT (code). INFERENCE: pictures 2 and 3 reach the operator unchecked | M |
| 45 | Showing the check and the model's own notes | **Nobody.** The page lines carry neither (PF:489-531); the notes are stored (VW:366) | S shows them; A reads note 3 ("anything in my request that the photographs contradicted"). **Wrong** | The image model reports its own departures and nobody reads them | FACT (code) | S |
| 46 | The assistant looking at the pictures | **A is told not to**: CF:30 `'do not study them yourself unless the operator asks you to'` | A, the strongest eyes in the system. **Wrong** | The operator becomes the only checker of 41 sets | FACT (code) | S |
| 47 | The "a real face" must line on a person's set made from their own footage frame | **S** adds it to every picture, IC:22-25, 288 | S picks lines by case. **Wrong** | With permission, matching the face is the aim | INFERENCE: a permitted likeness fails a must line | S |

### F. Step 2 (judging the sets)

| # | Job | Today | Right actor | Why | Symptom or risk | Size |
|---|---|---|---|---|---|---|
| 48 | Yes, No, Correct it | **O**, VS:3312 | O. **Right** | (a recommendation would come from 44) | none | |
| 49 | Golden picture of a thing | **O** ticks, VS:3353 | O. **Right** | | none | |
| 50 | Golden picture and face of a person | **S** by position: picture 1 (VS:3373), face = `"{set}-3"` (VS:2088) | S, after M confirms which picture is which view. **Wrong** | The worker records "picture n did not come back" (VW:136); positions then shift | INFERENCE | S |
| 51 | Remake cost and the cap hold | **S**, VS:3342-3366 | S. **Right** | | none | |
| 52 | Setting a set aside | **O**, VS:3541 | O. **Right** | | none | |

### G. Hand-over to later steps

| # | Job | Today | Right actor | Why | Symptom or risk | Size |
|---|---|---|---|---|---|---|
| 53 | The "not this" list | **M**, Flash, text only (VS:1880-1917), plus the operator's rejection words pasted as they are (VS:1876) | A writes it, or M with the rejected pictures. **Wrong** | A weak text call guesses what a picture model gets wrong; a correction is not a negative | FACT (code): "Correct it" words such as "make the handle longer" are stored as rejection notes (VS:3377) and become a "Not this" line | M |
| 54 | Sharing that list across films | **S**, by the element's name as a slug, VS:1849, 1915 | A or O confirms it is the same thing. **Wrong** | "The mason" of two films is two people | INFERENCE | S |
| 55 | The golden picture is Image 1 of every later picture | **S**, VS:3881 | S. **Right** | | none | |
| 56 | Which references a shot binds | **A** chooses; **S** checks kind and cover, VS:4746 | A and S. **Right** | | none | |
| 57 | Texture and look advice | **S**, by kind and shot size, VS:4963 | **Unclear** | Advice only; never bound | none seen | |
| 58 | Estimate of sets before the round | **S**, VS:770 | S. **Right** | | none | |
| 59 | "Never answer for the operator" with `--verdicts` and `--sets` | **A**, instruction only; S asks only for a quote | S takes these answers only from the page or a button. **Wrong** | An instruction is the only guard on paid answers | INFERENCE | M |

---

## 2. Top 10 wrong-actor cases, ranked

Rows 1 to 3 (the word match) are the owner's proven case and are left out of the ranking.

1. **No one with eyes checks a set before the operator (44, 45, 46).** A weak model checks picture 1 of 3 against generic lines. The result is not shown. The image model's own notes are not read. The assistant is told not to look. FACT.
2. **A second post of the round spends and overrides the operator (41).** It sets `ignored: False`, approves frames and makes the set at once. FACT in code.
3. **The server decides a thing needs no set, and picks its golden picture as "the first" (26, 27, 24).** The operator gets no "make a clean set from this frame" answer. The order of frames is arbitrary. FACT in code.
4. **The server says "your footage has no picture" when it only means "no frame was grabbed" (5, 6, 7).** No one looks at a grabbed frame either. FACT on VW-24 (the mason).
5. **The three views are a fixed list; the plan's `required_views` are ignored (20).** FACT on VW-24 (mason's hand, tile underside, pan tipped).
6. **One prompt wrapper for every kind (18, 19).** A technique is sent with "No person" and checked for "no hands". A place is told to fill the frame with soft surroundings. FACT on VW-24 (T_POUR, STREET).
7. **The operator answers 49 routine questions with no recommendation (25).** FACT (round.json).
8. **The "not this" list (53, 54).** A text-only weak model, plus correction words pasted as negatives, shared across films by name. FACT in code.
9. **Corrections are appended, never rewritten (40).** INFERENCE on the symptom.
10. **"Alike people" by regex (16).** A reading job done by a word list. FACT in code, INFERENCE on the symptom.

Next in line: 29 (nobody says what "Leave it out" costs), 59 and 42 (paid answers guarded by an instruction only), 15, 38, 39 (regex lints on prose).

## 3. What is right today (keep)

Price, cap, counts, ids and state are the server's. Spend at Done, the likeness permission, drawing approval, the Yes/No on a set and the golden tick of a thing are the operator's. The subject block is the assistant's. Measuring a size is a model's.

## 4. Not covered

- The older (search and picks) round: retired on kept films; only its shared code was read.
- `draw3d` and the drawing helper's own judgements (inside the drawings step).
- The shot pictures, guides and takes after the hand-over, beyond the first use of a reference.
- No film was run; every symptom marked INFERENCE is untested.
- The pictures in `vw24-part1/pics` were not opened; frame fitness (row 26) is judged from the frame's subject text only.
