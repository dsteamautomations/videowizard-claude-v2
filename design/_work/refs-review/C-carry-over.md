# C. What the Treatment and Plan steps now produce, and whether the References step uses it

17 Nov 2026. Read-only study for SK. **No code was changed. Nothing was run on the server, the VM or the database.**

SK's question 1: does the References step make use of the new data and corrections of the two earlier steps?

**Short answer: only in part.** Of 70 items, the References step uses 21 in full, 19 in part and 20 not at all. 10 do not apply to references. What is carried well is what was built for people (own likeness, a sheet for every person, people who read alike), the material spec, the approved drawings and the cost limit. What is not carried is most of what the operator now reads and approves on the plan page: the world of the film, each thing's description, the views the plan asks for, the signs of use, and where and how each thing is used.

## How to read this file

- **The References step** here means: the footage pictures (step 1), the paid sets (made after step 1) and the judging of the sets (step 2), with the page that shows them.
- **Used?** is one of YES, PARTLY, NO, or N/A (the item has nothing to do with references).
- **FACT** means I read it in the code or in VW-24's files. **INFERENCE** means I reason from the code; it was not seen on a run.
- Yesterday's review (`design/_work/references-step-review-vw24-17-nov.md`) already showed that the plan's views, descriptions and sizes do not reach the *choice of footage pictures*, and that Gemini's clip analysis is barely used. This file does not repeat that. It covers the paid sets and the page as well, and every other item.

Short names for files:

| Short | File |
|---|---|
| VS | `server/app/visuals_stage.py` |
| VC | `server/app/visual_contract.py` |
| PF | `server/app/page_flow.py` |
| CF | `server/app/chat_flow.py` |
| DH | `plugin/pages/decisions.html` |
| INS | `server/procedures/v3.json`, visuals stage, part "picture-search" (1,017 words) |
| EV | `ux1-mockup/vw24-part1/evidence.json` (VW-24: 50 plan elements, 10 frames, 49 set prompts) |
| RD | `ux1-mockup/vw24-part1/round.json` (VW-24: the 49 lines of step 1 as the operator sees them) |

How a set's prompt is built today (FACT), because many rows rest on it:

- **A thing** (object, place, material, process, technique): the assistant writes a free text, the "subject block", in the round file. The server wraps it: a fixed opening, a fixed line about three pictures, the subject block, one line of "cosmetics" (the place and the film's look), and a request for notes (VS:2025-2041). The server then adds the material sentence, the known sizes and the "not this" list (VS:3942-3958). Nothing else of the plan is added by the server.
- **A person**: the server writes the prompt from the plan: requirements, description, every scene outfit, the place and look, the assistant's "why" line, one line against each other person (VS:2054-2074).
- **The three pictures of a set are fixed**: a thing is "the whole", "a three-quarter view", "a close-up of the key detail"; a person is "full-length front", "three-quarter view in a working pose of their trade", "the face" (VS:1976-1984).

---

## 1. From the Treatment step

| # | Item | Where it is produced | Used by the References step? | What the References step should do with it | Effect on the operator if not carried |
|---|---|---|---|---|---|
| 1 | The Direction in six parts (idea, who it is for, whose story, feel, how the film moves, what each kind of picture does) | VS:887 `DIRECTION_PARTS`, VS:900 `direction_from`; design/203 | **NO.** FACT: the set prompts read only `foundation.appearance` and the first scene's place (VS:2019-2022). No part of the Direction is read at VS:2025-2074. | Little is needed in the prompt: a reference is a neutral picture. But "what the film will not do" could be shown to the operator at the top of the page, so they judge sets against it. | Low. The operator judges 40 sets with nothing on the page that says what film they are for. |
| 2 | The Direction placed by the server at the head of the plan | VS:297-311 `_with_direction`; design/207 point 14 | **NO.** FACT: nothing in the round reads `foundation.treatment`. | Nothing in the prompt. It is the ready source for row 1's line on the page. | None by itself. |
| 3 | "From the brief": the film's purpose, audience and tone, shown above the Direction | CF:74 `_direction_rows`; design/203 section 5.2 | **NO.** | Nothing needed. | None. |
| 4 | Each shot's two reasons (`fits_why`, `way_why`), shown again under each gap on the plan page | VS:857 `reasons_missing`; PF:220-221; design/202, design/207 point 14 | **NO.** FACT: a line of the references page holds a title, one fixed sentence, pictures and buttons (PF:482-485). It does not say why the thing is in the film. | Under each thing, one line from the plan: "used in gap G3, shots 2 and 4: the mason beds a brick". | The operator cannot judge "Leave it out", nor which view matters. In RD, 33 of 49 lines carry the same sentence, word for word. |
| 5 | Each gap's way (footage, AI video, still, diagram) as accepted | VS:956 `treatment`; VS:322 `_ways_departed` | **PARTLY.** FACT: for a person, a row is demanded only when a picture is made of them (VS:3194-3196). For a thing there is no such test: the round takes whatever rows the assistant posts, and the estimate counts every thing (VS:777). | Ask and pay only for a thing that some made picture shows. A thing seen only in footage shots or in a drawn graphic needs no set. | INFERENCE: sets may be paid for things no made picture uses. Not counted on VW-24. |
| 6 | Still and moving seconds; the "stills are N % of the film" warning | VS:837 `still_and_moving`; VC:1418 | **N/A** | | |
| 7 | A line the operator sent back returns marked "Changed as you asked", with before and after | VS:1090 `_carry_lines`; DH:354-356; design/202 section 3.3 | **NO.** FACT: a set made again after "Correct it" returns as a new line with no mark, no before and after, and without the operator's own words on it (PF:508-513 has no `asked`, `changes` or correction field). | Show on the new set: "Made again as you asked: '<their words>'", and the earlier set folded beside it. | The operator must remember what they asked for, on each of several sets, and cannot compare. |
| 8 | The script's visual notes are no longer used | VS:155 (`intended_visuals: []`); design/202 | **YES.** FACT: the round reads no script notes. | Nothing. | None. |
| 9 | The motion style chosen on the page | PF:129 `_motion_line`; design/205 | **N/A** | | |
| 10 | "Action first": a person doing one thing; the work is done by the right hand | INS treatment part; design/202 section 3.4; design/175 | **PARTLY.** FACT: a person's second picture is "a working pose of their trade" (VS:1977). The right hand reaches the prompt only if the assistant wrote it in the person's `requirements` (EV, MASON: "Works with his right hand"). FACT: on VW-24 two technique prompts say "held in both hands" (EV: T_POUR, T_SCREED). | The server adds the right-hand line to a person's working pose and to a technique's set. | A reference that shows the work left-handed or two-handed is copied into every shot made from it. INFERENCE. |
| 11 | Rules filed by category (documentary, advertisement, social) | INS treatment part; design/202 section 3.4 | **NO.** FACT: the set prompt names no category (VS:2025-2074), although design/151 section 3.3 says the server adds "the film's category and place". The fixed texts speak of "one real site" and "the same site" (VS:1958, 1960). | The fixed texts are made generic; the category is passed where it changes what a reference should look like (a product film: a clean studio picture). | A product or software film gets building-site wording in every set prompt. |
| 12 | A second Direction on request | VS `_treatment_lines`; design/203 section 5.3 | **N/A** | | |

## 2. From the Plan step: the world of the film and the list of things

| # | Item | Where it is produced | Used by the References step? | What the References step should do with it | Effect on the operator if not carried |
|---|---|---|---|---|---|
| 13 | The look of the film (`foundation.appearance`) | VC:31; shown as "The look", CF:195 | **YES.** FACT: VS:2022 puts it in every set ("the film's look: …", VS:1965, 2066). | Nothing more. | None. |
| 14 | The world rules (`foundation.world`: place, period, people, work, clothes, tools) | VC:32; CF:196; design/207 point 13 | **NO.** FACT: no code between VS:2019 and VS:2074 reads `foundation.world`. | Add to a place's and a person's set the rules that bind it: the period, the region, what the period forbids. | INFERENCE: a set may break the period or the region the operator approved on the plan page. They find out only by looking at each picture. |
| 15 | What is not shown (`foundation.exclusions`) | VC:33; CF:196 ("Not shown") | **NO.** FACT: not read by the set prompts. | One line in each set: "Not in this film: …". | The same. A paid set may show what the film excludes. |
| 16 | Specifications (`foundation.specifications`) | VC:34; CF:196 | **NO.** | As row 15, where a specification names the thing. | Low. |
| 17 | "Ask of the world": the everyday things a viewer expects; fixed things (poles, wires, signs) belong to the place | INS plan part; design/207 point 13 | **NO.** FACT: a place's set is the assistant's own text. The fixed line pulls the other way: "nothing in the picture that the real photographs do not justify" (VS:1966). design/207 also records that three lines of the picture library still say "every object earns its place". | A place's set names the fixed things of that place, so every later picture of it has them in the same spot. | The place's reference has no poles or wires; the shots add them in different spots each time. INFERENCE. |
| 18 | The world block shown on the page: read only, grouped under one heading per kind, each group folding, tagged "To read" | PF:197-202; DH:154, 323-335 | **NO.** FACT: `_round_page` (PF:534-581) adds no world line and no grouping. RD is 49 flat lines: 7 people, then materials, objects, places and techniques, with no heading between them. | Group the things by kind under folding headings. Keep the world block at the top, folded. | The operator scrolls 49 lines of equal weight. The description they read once on the plan page is gone when they need it to judge a picture. |
| 19 | Each thing's `description` (a person's face, build, age, hair; a thing's look) | VC:50; CF:206 | **PARTLY.** FACT: a person's description is in the prompt (VS:2064). A thing's is not added by the server; the assistant retypes it in its own words (VS:3287 sends `row['prompt']`). The page line shows no description (PF:482). | The server places the plan's description in a thing's set too, and the page shows it under the title. | For things, the words the operator approved are not the words the picture is made from. EV: the pan's subject block asks for "from the side and from above"; the plan asked for "side" and "tipped, pouring". |
| 20 | `requirements` | VC:46 | **PARTLY.** FACT: a person's is in the prompt (VS:2063). A thing's is used only by the word match that looks for footage (VS:2949). | As row 19. | As row 19. |
| 21 | `required_views`: the views the plan asks for | VC:47 | **NO.** FACT: the three pictures are fixed (VS:1976-1984). `required_views` is read only on older films (VS:2166, 2179, 2187). EV: 14 things state views. The mason asks for "right hand and forearm", the tile-maker for "hands"; neither is made. | The plan's views name the pictures of the set, and the footage frames to take. | The set shows angles the film does not use and misses the one it needs. The operator pays again with "Correct it". |
| 22 | Sizes with status and source (`confirmed`, `measured`, `proposed`, `unknown`) | VC:124-131 | **PARTLY.** FACT: a known size is written into the set ("Sizes: …", VS:3954-3958). An unknown size with an approved footage picture stops the set until it is measured (VS:3760-3764; VS:3481-3484). But in EV all 24 sizes are `unknown`, so no size line reaches any VW-24 set, and the assistant wrote loose sizes into the subject blocks ("about a hand wide", "knee-high", "five across and four deep"). The page line shows no size. | The page shows each thing's sizes and their status. A size the assistant writes into a subject block comes from the plan, not from its own words. | Sizes that nobody approved go into paid pictures. The plan's rule is "never invented". |
| 23 | The material spec and its approval | VC:145; VS:2254 `material_approved`; design/209 | **YES.** FACT: a set waits for the approved spec (VS:3946-3947; VS:3476-3480); its sentence and check lines are added (VS:3952-3953); a set made before a spec changed is marked to be made again (VS:3498-3509). | Nothing more. | None. |
| 24 | Unit sizes only for a material laid in units; a liquid or loose material says its amount or coverage | VC:771 (`material_bare`); design/207 point 5 | **PARTLY.** FACT: the amount lives in the description, which the server does not add to a thing's set (row 19). EV: water's subject says "a finger deep", written by the assistant. | Covered by row 19. | As row 22. |
| 25 | `signs_of_use`: a place's traces of work or living | VC:51, 181; checked at the plan | **NO.** FACT: the signs are added only to shot pictures (VS:3977-3985), not to a set. EV: 9 places carry two signs each. | A place's reference shows the place in use, with its signs, unless row 26 applies. | INFERENCE: the place's reference is clean and unused; each shot then adds the signs by itself, in different spots. |
| 26 | `staged_clean`: why a place is shown clean | VC:52 | **NO.** FACT: read only for shot pictures (VS:1557-1558). | With row 25. | Low. |
| 27 | `speaker`: marks a real, named person | VC:53; warning `stand_in_real`, VS:336-347, 381-384 | **PARTLY.** FACT: the page says the same sentence for every person ("from the description, or from their photo when you have their permission", PF:476). It does not say which person is real and named. `speaker` is not read in PF. | On that person's line: "This is a real, named person. Without their photo the picture is a made-up stand-in." | The warning the operator read on the plan page is not repeated at the one moment they can act on it (adding the photo). |
| 28 | `identity`: exact (the client's own thing) or representative | VC:45 | **PARTLY.** FACT: an exact thing whose facts cite the footage needs an approved footage picture before any picture of it (VS:3757-3759). The page does not show the word. EV and RD: the stone heap is `exact`; RD line 30 shows its one footage picture, the one yesterday's review found to show something else. The mason's trowel and the brick are `representative` and go straight to a paid set, although yesterday's review found both in the clip analysis. | Show "the client's own" on the line. For an exact thing, never offer a paid set as the plain default. | The operator may approve a generic paid picture of the client's own thing. |
| 29 | `visual_facts` (how a thing looks and is done, with its source) | VC:152-160 | **NO.** FACT: in the set path they are read only to see whether a fact cites the footage (VS:3757). | The confirmed facts about a thing go into its set as "what must be true", as the drawing facts do. | The set is made from web photographs alone, even where the plan holds a confirmed fact. |
| 30 | The place of each scene (`location_time`) | plan scenes | **PARTLY.** FACT: every set of the film gets the place of the **first** scene that has one (VS:2019-2021), whatever the thing is. | Use the place of the scenes the thing is in. | INFERENCE: on VW-24 the curtain, the tile yard and the roof deck all get the same "place reads as …" line. |
| 31 | Scene outfits; clothes may change when the time changes | VC outfits; design/207 point 3 | **PARTLY.** FACT: a person's prompt lists every outfit of every scene in one line, with no time and no rule which one the sheet shows (VS:2059-2065). | The sheet shows the outfit of the most scenes and names the others in words; or one picture per outfit when they differ much. | A sheet that mixes two outfits; the operator cannot tell which one each shot will use. INFERENCE. |
| 32 | People who read alike are named, all pairs at once, at the plan check | VS:2006 `alike_people`; VS:385-389 | **YES.** FACT: the round refuses alike people (VS:3173, 3743) and each person's prompt carries one "Not P2: …" line per other person (VS:2070). | One small thing: the round's own refusal still names one pair at a time (VS:2015). | Low. |
| 33 | Which shots use a thing, and how close those shots are (shot size) | plan shots (`element_ids`, `size`) | **NO.** FACT: not read by the round or the page. (Yesterday's review found the same for the footage pictures.) | Decide the pictures of the set from the closest shot that shows the thing. Show the shots on the line (row 4). | A reference is made at a distance the film never uses. |

## 3. SK's decisions D1 to D7 (design/207)

| # | Item | Where it is produced | Used by the References step? | What the References step should do with it | Effect on the operator if not carried |
|---|---|---|---|---|---|
| 34 | D1: own likeness, with the operator's recorded permission | VS:2544 `likeness`; VS:2527 `person_picture_refused` | **YES.** FACT: with the permission the photo is Image 1 of the sheet (VS:3744-3745, 2050); the page asks for the permission words before taking a photo (PF:439-450, 619; DH:303); a set made from a photo is not approved once the permission is gone (VS:3350). | Nothing more. | None. |
| 35 | D1: a refused photo offers another photo or a stand-in | CF:448-457; PF:517 | **YES.** | Nothing more. | None. |
| 36 | D2: a footage reuse no longer waits for the operator | VS:5904 `_reuse_gate` | **N/A** (a matter of shots, not of references) | | |
| 37 | D3: every named person gets a sheet, up to ten named people | VS:3194-3196; VS:2163; VC:464 | **YES.** FACT: the round refuses to start while a person a picture is made of has no row. | Note: each sheet is about ₹35 and one judgement. Ten people is ten of each. | None. |
| 38 | D4: a living extra (dog, bird) is carried by words, with no sheet | VS:3160, 3182, 3738; VS:1735 `animal_lines` | **YES.** FACT: an animal row is refused with a plain sentence. | Nothing more. | None. |
| 39 | D5: a thing travels on a timed path | `server/app/guide_spec.py:83-96` | **N/A** | | |
| 40 | D6: the cost limit, ₹750 a minute, lowest ₹1,500 | VS:734 `cap_for`; VS:730 `cap_of` | **YES.** FACT: the page's top line, each paid button and the close of step 1 read the film's own limit (PF:420-423, 570, 598; VS:4000). | Nothing more. | None. |
| 41 | D6: the plan's estimate against the limit ("₹X for the shots, and up to ₹Y for N reference sets, of the ₹Z limit") | VS:764 `plan_estimate`, VS:769 `set_estimate`; PF:250-253 | **PARTLY.** FACT: the references page shows the sets against the limit and the spend so far (PF:570). It does not show what the shots still need. The close of step 1 tests only that the sets fit under the limit (PF:598). RD: "up to 41 sets, about ₹1,450, of the ₹3,754 limit; spent so far ₹1,345". After these sets ₹959 is left for every still and every take of the film. | Show three figures: spent, these sets, what the plan's shots still need. Warn when the three pass the limit. | The operator approves 41 sets and meets the limit in the middle of the stills or takes. INFERENCE: VW-24's shot estimate is not in the files I read. |
| 42 | D6: the owner sets another limit for one film | VS:746 `set_cap` | **YES.** FACT: read through `cap_of`. | Nothing more. | None. |
| 43 | D7: the three framing warnings go to the assistant only | VC:1432-1438 | **N/A.** (The matching idea for references, "a poor footage picture is caught before the operator sees it", is in file D.) | | |

## 4. The plan check, its warnings, and the approvals after the plan

| # | Item | Where it is produced | Used by the References step? | What the References step should do with it | Effect on the operator if not carried |
|---|---|---|---|---|---|
| 44 | The new warning kinds and the assistant's answers to them (`stand_in_real`, `people_alike`, `material_bare`, `people_many`, `video_untried`, `text_card`, `still_more_than_agreed`, `compare_not_person`, `look_wide`, `extra_repeated`, `animals_many`, `same_setup`) | VC:1410-1438; VS:350-394 | **PARTLY.** FACT: `people_alike` is enforced at the round (row 32). `stand_in_real` is not repeated (row 27). `material_bare` has no effect on the set. The others are about shots. | Rows 27 and 22. | As rows 27 and 22. |
| 45 | "Read before you answer": the plain lines above a gap | PF:222-224; DH:368 | **NO.** FACT: a reference line has no `warnings` (PF:482-485, 508-513). | A line may carry one or two plain sentences: "real person, no photo yet", "the client's own thing", "its size is not known". | The operator answers without the one fact that would change the answer. |
| 46 | The check reports every fault in one answer | VC:694-737 (`_COLLECT`); design/207 point 2 | **PARTLY.** FACT: the making of the sets collects every refusal per thing and goes on (VS:3289-3297, 3304-3308). But the posting of the round stops at the first faulty row (VS:3178-3196). | The round's own check lists every faulty row at once. | Slower start of the round; the operator waits. Not seen by them directly. |
| 47 | Drawings and materials approved on the page, in plain words, each size asked once | CF:528 `_spec_views`; PF:271-292; design/209 | **YES.** FACT: the approved material spec gates and feeds the set (row 23). | Nothing more. | None. |
| 48 | The reference drawings, approved before the round | `server/app/drawings.py:121, 145, 160`; PF:333-367; design/200, 210 | **YES.** FACT: step 1 cannot close while a drawing is open (VS:3580-3582); approved sheets go to the set with the words that explain them and their facts (VS:3749-3753); the facts are checked on the picture (VS:3919-3920). | Nothing more. | None. |
| 49 | "Not to scale" and sizes that are assumed | VC:140; `drawings.py` (`assumed`); design/207 point 10 | **PARTLY.** FACT: every fact of the drawing set goes to the picture AI under the sentence "The drawings were made from this thing's real sizes … are the truth" (VS:1967-1969; `drawings.py:160-163` sends all facts). INFERENCE: an assumed size is then told to the model as a real one. I did not read how an assumed fact is worded. | An assumed size is sent as "about", or left out of "what must be true". | Low for the operator; a wrong guess becomes fixed in the reference. |
| 50 | Any kind of AI video (`recipe: other`) | VC:333 | **N/A** | | |
| 51 | A person for scale; the size sentence in a still and a start picture | VS:1717 `size_line` | **N/A.** By decision the size sentence is never on a reference set (VS:3968). | | |
| 52 | A look is framed close, so the person's face picture must be among the references | VC:1091 (`look_wide`); design/207 point 12 | **YES.** FACT: a person's set has a face close-up, and it is added to a shot's request while the picture service has room (VS:2077-2092). | Nothing more. | None. |
| 53 | The same set-up not twice; no picture twice | VC:1198 | **N/A** | | |
| 54 | A plan that changes after it was accepted (the shared change asked once; "what changed" on each gap) | VS:552, 567, 603; design/191 | **PARTLY.** FACT: a set is marked "made before a change" only for a changed material spec or a changed photo (VS:3490-3509). A person's description, a thing's description, its views or its sizes changed in the plan after the set was made mark nothing. A thing the plan no longer names drops out of the round's questions silently (CF:380). | Keep, with each set, the fingerprint of the plan fields it was made from; mark a set whose fields changed. | An approved sheet stays in use after the person was re-described. The operator is not told. |

## 5. How the page behaves (designs 204 to 210)

| # | Item | Where it is produced | Used by the References step? | What the References step should do with it | Effect on the operator if not carried |
|---|---|---|---|---|---|
| 55 | Answers are saved at the click and kept until "done" | DH:397, 442; PF:405-407 | **YES.** FACT: step-1 answers are kept until every thing is answered, then recorded once (PF:590-600; CF:329). | Nothing more. | None. |
| 56 | One visit and one "done" per step; no repeated rounds | design/206, SK's first point | **PARTLY.** FACT: step 1 is one visit, step 2 is one visit per cycle. But: a long list is cut and the rest comes after the next "done" (PF:549-561); and a kept answer is dropped without a word when that thing's footage pictures change (CF:312-314). | Say on the line when a kept answer was dropped and why. | The operator answers a thing twice and does not know why. |
| 57 | "Changed since you last saw it", folded; open when the operator asked for the change | DH:354-356; design/205, plugin 0.89.1 | **NO.** FACT: no reference line carries `changes` (row 7). | Row 7. | Row 7. |
| 58 | Blocks that fold; approved content kept readable | DH:201-203, 292-293, 334 | **NO** for the open lines (row 18). FACT: only an approved set folds (DH:292-293). | Row 18. | Row 18. |
| 59 | The "To read" tag for what is read and not answered | DH:154 | **NO.** FACT: the tag is given only to the world line. A thing whose reference is already settled (its own picture) is still drawn as a question. | Use it for lines that need no answer. | Small. |
| 60 | A refusal is written on its own line, in the server's words | PF:562-563, 890; DH:358 | **YES.** | Nothing more. | None. |
| 61 | An answer to an older text or an older set is named as stale and changes nothing | PF:609-615; CF:442 (the set's id is in the item) | **YES.** | Nothing more. | None. |
| 62 | Each answer is one log line, by the operator, with their words | PF:153 `_log`, 828, 872; design/205 | **PARTLY.** FACT: logged, yes. But a comment typed at step 1 is only logged; it does not reach the set's prompt (CF:399-405 ignores `words`; design/210 "Not covered" says so). The box's own hint says "where a set is corrected, it says what to correct" (DH:400). | A step-1 comment on a thing that gets a set goes into that set's prompt, as a step-2 comment does. | The operator writes "the handle is red" at step 1; the set is made without it; they pay for a second set. |
| 63 | A round is one document of at most 256 KiB | PF:166, 549 | **YES.** | Nothing more. | None. |
| 64 | A recorded line keeps its content | PF:523-530 | **PARTLY.** FACT: an approved set keeps its pictures. A thing settled at step 1 from its footage picture is left out of the sets page altogether (PF:501). | Show those things too, folded: "from your footage". | After step 1 the operator cannot look back at which footage pictures they approved. |
| 65 | The top line gives the bounds: things, sets, cost, limit, spent | PF:570, 576-577 | **YES** (but see row 41). | Row 41. | Row 41. |
| 66 | The price on every paid button; the click plus "done" is the operator's word | PF:430-436; design/210 | **YES.** | Nothing more. | None. |
| 67 | The older way is named and kept as the way back (old-ways rows 101, 102) | `design/35-decision-log.md` rows 101-102; CF:369 | **YES.** | Nothing more. | None. |
| 68 | The instructions were brought in line with the new rules | INS; `scripts/d207_wording_v3.py`, `d210*_wording_v3.py` | **PARTLY.** FACT: INS states own likeness, a sheet for every person and none for an animal. It says nothing of the plan's views, the world rules, the signs of use, the sizes or the description. It says "a frame of each" (one) and fixes a person's three pictures. | Say in INS what the subject block must take from the plan, or better, let the server place it (row 19). | The assistant rewrites each thing from memory. |
| 69 | One flow, two front ends | repo `CLAUDE.md`; PF:468 calls `CF._round_items(every=True)` | **YES.** | Nothing more. | None. |
| 70 | The plan-join fix after a proposal | `plugin/scripts/vw.py` `plan_join`; design/209 | **N/A** | | |

---

## Counts

| Used by the References step? | Rows | How many |
|---|---|---|
| YES | 8, 13, 23, 32, 34, 35, 37, 38, 40, 42, 47, 48, 52, 55, 60, 61, 63, 65, 66, 67, 69 | 21 |
| PARTLY | 5, 10, 19, 20, 22, 24, 27, 28, 30, 31, 41, 44, 46, 49, 54, 56, 62, 64, 68 | 19 |
| NO | 1, 2, 3, 4, 7, 11, 14, 15, 16, 17, 18, 21, 25, 26, 29, 33, 45, 57, 58, 59 | 20 |
| N/A | 6, 9, 12, 36, 39, 43, 50, 51, 53, 70 | 10 |

## The ten that matter most, of the NO and PARTLY rows

1. **Row 21, the plan's views.** The pictures of every set are fixed. 14 VW-24 things ask for views that are not made.
2. **Rows 19 and 20, the description.** For a thing, the picture is made from the assistant's retelling, not from the words the operator approved.
3. **Rows 4 and 33, why and where a thing is used.** Not on the page and not used to choose the pictures.
4. **Row 18, the page.** 49 flat lines, no grouping, no description, the same sentence on 33 of them.
5. **Row 41, the money.** The references may take the money the plan's shots need; the page does not show the three figures together.
6. **Rows 14 and 15, the world rules and "not shown".** Approved on the plan page; absent from every set.
7. **Row 25, signs of use.** Nine VW-24 places carry them; no place's set gets them.
8. **Rows 7 and 57, "changed as you asked".** A set made again does not show the operator's words or the earlier set.
9. **Row 62, the step-1 comment.** Typed by the operator, kept in the log, never sent to the picture.
10. **Row 54, a plan changed after the sets.** Only a spec or a photo change marks a set; a changed description does not.

## Not checked

- No set of VW-24 was looked at: the sets were not yet made when the evidence was taken. Every effect on a real picture above is an inference from the prompt.
- VW-24's plan estimate for the shots (row 41) was not in the files read.
- How an assumed size is worded when it is sent with a drawing (row 49).
- The chat path's wording was read only where it shares code with the page.
- Whether the picture library's own step file for references adds any of the missing items. The round's code does not read it for a set's prompt, but the assistant may read it when it writes the subject block.
