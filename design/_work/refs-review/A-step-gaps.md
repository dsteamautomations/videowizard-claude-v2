# References step: new gaps (review A, 17 Nov 2026)

Read-only audit. No code changed, nothing run on the server, the VM or the database.

Sources: `server/app/visuals_stage.py` (VS), `visual_workers.py` (VW), `page_flow.py` (PF), `chat_flow.py` (CF), `guide.py`, `plugin/skills/guide/SKILL.md`, `server/procedures/v3.json`; film VW-24 in `ux1-mockup/vw24-part1/evidence.json` (EV) and `round.json` (RJ).

Not repeated here (already found): word-overlap footage hint, nobody looks at a frame, sub-clips dropped, `required_views` ignored, first frame only downstream, one yes for all frames, "no picture" meaning no frame grabbed, the frame rule.

FACT = read in the code or the two JSON files. INFERENCE = my conclusion; not run, not seen on a real picture.

VW-24 in numbers (FACT, RJ): 49 lines. 7 people, 33 "no picture, make a set", 8 footage yes, 1 drawn (tile). Up to 41 sets, about ₹1,450. Limit ₹3,754. Already spent ₹1,345.

Size: S = under a day, M = one to three days, L = more.

---

## Ranked list

### 1. Sets for places, techniques and most materials have no defined use in AI video shots. Size L

- FACT. The still of an AI video shot takes only the pictures the assistant names (`guide.py:229-258`, `parents` is a free list). The server does not require the golden picture of any element of the shot.
- FACT. The guide skill names only two uses: "the people's full-length and face pictures and each prop's picture, cropped to the thing", and "never a whole photo taken from another camera position" (`plugin/skills/guide/SKILL.md:153`). A place set is exactly such a whole photo. The take's words refuse "a place or a path in words" (SKILL.md:168).
- FACT. VW-24 pays for 9 place sets and 5 technique sets without footage (EV), about ₹490.
- INFERENCE. These sets are judged by the operator and then not used on the video route. I found no rule that feeds a place or technique set into a guide scene, a guide still or a take.
- Fix direction: write down, per kind, what the reference is for and which step consumes it; do not make a set for a kind that no step consumes.

### 2. No approved reference is bound to the shots that name the element. Size M

- FACT. On the still route the golden picture must be Image 1 only for the picture's own element (`VS:3881-3882`). Other elements of the shot are not checked: the server only refuses a parent that is NOT in the shot (`VS:3855-3860`), never a missing one.
- FACT. On the video route nothing is checked (gap 1). Later stills of a scene take "crops of the scene's first approved still", not the references (SKILL.md:153).
- FACT. The old `bind` did require every element covered (`VS:4752-4753`), but "a still shot needs no bind" and video goes through the guide (v3.json:293, section 6).
- Why it hurts: the mason is in every site step. Whether his set reaches each still depends on the assistant remembering. INFERENCE: identity drifts scene to scene and nobody is told.
- Fix direction: the server adds the golden picture (and a person's face) of every element in the shot by itself, or refuses the still naming the missing ones.

### 3. One prompt template for five different kinds; it contradicts itself for techniques and places. Size M

- FACT. Every non-person set gets the same must lines: "no person, no hands, no face anywhere" and "the subject fills the frame; the setting is only a soft hint" (`VS:1985-1989`), and the same cosmetics: "No person", "surroundings soft", "Natural daylight" (`VS:1965-1966`).
- FACT. VW-24 technique prompts need hands: T_BRICKLAY "a brick lowered ... pressed down", T_OIL "a wide flat brush drawn in a long straight stroke", T_STRIKE "one board freed and lowered away" (EV). The preamble also says "I am not going to describe how the work is done" (`VS:1953-1954`), which is what a technique is.
- FACT. Place prompts need the setting: STREET "wide enough to see several houses" (EV) against "subject fills the frame".
- FACT. LANE asks "at evening ... warm low light" (EV); the server adds "Natural daylight". ROOM and SITE_BELOW are interiors.
- INFERENCE. The model gets two opposite orders; the check on picture 1 fails a must line or the picture is wrong.
- Fix direction: one small contract per kind (object, material, place, technique): its three views, its must lines, its light rule.

### 4. All 41 sets are ordered in one go, with no trial and no undo. Size S

- FACT. Done on step 1 queues every set at once (`VS:3611-3620`). It cannot be undone (`VS:2468`, `2478`).
- FACT. Every set shares the server's wrapper (gap 3, gap 5). A fault in the wrapper repeats 41 times, ₹1,450, before the operator sees one picture.
- Fix direction: make three sets first (one person, one object, one place), let the operator judge them, then order the rest.

### 5. Every set is told it is in the film's first place. Size S

- FACT. `_place_look` takes the `location_time` of the first scene that has one (`VS:2019-2022`). It goes into every thing set ("The place reads as {place}", `VS:2040`) and every person sheet (`VS:2066`).
- Why it hurts: VW-24 has 9 different places (street, tile yard, family room, lane ...). All their sets and all the objects get one place sentence. INFERENCE: the family room's fan regulator is told it sits in the opening scene's place.
- Fix direction: take the place from the scenes that show the element; for a place element use its own words.

### 6. The operator's comment on step 1 never reaches the picture. Size S

- FACT. Every step-1 line has a comment box (`PF:484`, RJ `comment: true`). The run function stores only verdict, quote, frames, own (`CF:399-401`); `words` is not used. The words go to the log only (`PF:642`).
- Why it hurts: "make the mason older, in a lungi" is typed, ₹35 is paid, the set ignores it.
- Fix direction: carry step-1 words into the row as its first correction, or remove the box.

### 7. 49 questions with nothing to decide them by; no ranking, no defaults. Size M

- FACT. A step-1 line shows a title, one fixed sentence and two buttons (RJ). It does not show the plan's description, the prompt that will be sent, or how many shots use the thing. 33 lines read exactly the same.
- FACT. No "accept all proposals", no grouping, order is the plan's order (`PF:471`). The assistant's own proposal (EV `verdict`: 48 approve, 1 ignore) is not shown.
- INFERENCE. Step 1 costs 15 to 25 minutes of reading identical lines; step 2 then shows 41 sets, 123 pictures. Most answers are a blind yes.
- Fix direction: show the proposal as the default with one "accept all" and list only the exceptions; sort by shots that use the thing; show the count.

### 8. Many elements do not deserve a paid set; nothing asks "is it worth it". Size M

- FACT (EV). Sets asked for: Clean water, Cotton curtain, Wall fan regulator, Coil of binding wire, Heap of coarse sand, Cement bag, Metal bucket. NEIGHBOUR is "talking ... in the lane at evening", one scene.
- FACT. One act is split into many sets. Oiling: SHUTTER_OIL, OIL_BRUSH, OIL_TIN, T_OIL (4 sets, ₹140). Curing: WATER, CURING_RIDGES, BUCKET, T_CURE. Bricklaying: BRICK, MORTAR, TROWEL, T_BRICKLAY.
- FACT. The server makes a set for every row that is not ignored (`VS:3614`). There is no rule by use (shots, seconds on screen, close or far).
- Fix direction: a set only when the thing is in two or more made shots or is seen close; else its words carry it. One set for a technique with its tools and material together.

### 9. Sets are made alone, so overlapping sets disagree. Size M

- FACT. Each set is queued with `parents: []` (`VS:3287`); only its own frame and drawings are added (`VS:3747-3752`). No approved set feeds another.
- FACT (EV). SITE_YARD's prompt lists cement bags, a bar bundle, sand, stone, a wire coil, a bucket. Each of these also has its own set. ROOM lists the shuttered window and the tile ceiling; SHUTTER_WINDOW and CEILING_FINISH have their own sets. T_STRIKE shows the shuttering board and the ceiling.
- FACT (EV). BAR_BUNDLE is proposed "ignore", yet SITE_YARD still asks for "a bundle of steel bars".
- INFERENCE. The cement bag in the yard picture and the cement bag set will differ; later shots get two truths.
- Fix direction: order by dependency (objects and materials first, then places and techniques with those approved pictures as inputs).

### 10. Only picture 1 of a set is checked; the golden picture may be picture 2 or 3. Size S

- FACT. The check runs on the job's own reference id (`VW:409`); the other pictures are copies of the row without `check` (`VW:390-392`). The must lines and the drawn facts (`VS:3917-3920`) are therefore tested on one picture of three.
- FACT. For a thing the operator may tick any of the three as golden (`VS:3353`).
- Fix direction: check all three, or check the ticked one before it is recorded.

### 11. Step 2 gives the operator nothing to judge against. Size M

- FACT. A set line shows "Three pictures of the same thing" and pictures lettered A, B, C (`PF:508-511`). Not shown: the footage frame, the drawings, the plan's description, the name of each view, the check result, the model's notes and its sources (stored on the row, `VW:373-374`; not read in `PF`, 0 hits for "sources").
- FACT. The model is asked for four notes, including "anything in my request that the photographs contradicted" (`VS:1963-1964`). The operator never sees them on the page.
- FACT. Nothing says which view should be golden. Ticking the close-up makes a detail "the one every shot starts from".
- Fix direction: put the footage frame or drawing beside the set, label the views, show the failed must lines and the "contradicted" note, propose the whole view as golden.

### 12. A person's set: one picture of three is never used, and the person is made alone. Size M

- FACT. Picture 2 is "a working pose of their trade" (`VS:1977`). The guide skill says "never a person's working-pose picture" (SKILL.md:153). A third of each of 7 person sets is paid for and judged for nothing.
- FACT. "Their trade" is asked of the daughter (8), the woman of the house, the home owner (EV). Category-specific wording.
- FACT. A person's golden is always picture 1; the operator cannot choose (`VS:3373`, `3437`).
- FACT (EV). All 7 people have height "unknown". Each is made alone on plain ground (`VS:1973-1975`). Father, mother and child share scenes; nothing fixes their relative height.
- FACT. Garments are every scene outfit joined in one line (`VS:2059-2065`). With two outfits the sheet gets both.
- INFERENCE (EV matches). The footage shows real workers (white shirt, wristwatch, gold ring; a pink cuff). The mason is made from words. Cuts between filmed hands and the AI mason will not match.
- Fix direction: replace picture 2 with a back or side view; one outfit per sheet; give each person a height against one other; state in the plan whether the stand-in must match the filmed worker's clothes.

### 13. One spend limit covers sets, remakes, stills and video; the sets eat it first. Size S

- FACT. `visuals_spend` sums every image and every take second (`VS:716-727`); `check_cap` is one figure (`VS:782-790`).
- CORRECTED by the master thread: the step-1 page read here is a trial copy; its ₹1,450 is the estimate of the same sets, not a second spend. FACT: ₹1,345 was spent on 38 sets of a ₹3,754 limit; about ₹2,400 is left for every remake, every still and every take.
- FACT. Step 1 is refused only if the first order does not fit (`PF:596-599`); no room is kept for remakes.
- Fix direction: show on the page what is left after the sets and what the stills and takes are estimated to need (`plan_estimate` exists, `VS:764`); warn before Done.

### 14. Remakes: "No" repeats the same prompt; corrections pile up for ever; no count limit. Size S

- FACT. A "No" without words makes the set again with an unchanged prompt (`VS:3375-3381`, `3286`). ₹35 for a second roll of the dice.
- FACT. Every correction is appended and all are sent every time (`VS:3286`, `3380`). A later correction that reverses an earlier one leaves both in the prompt. None can be removed.
- FACT. The round counter only counts (`VS:3285`); nothing stops a fifth remake except the limit. The line does not show what this element has cost so far.
- Fix direction: "No" needs a reason or a choice of cause; show the standing corrections on the line with a remove; after two remakes ask the operator for their own picture or to leave it.

### 15. A re-sent round file can pay for sets the operator never agreed to. Size S

- FACT. After step 1, a re-posted row is merged with `verdict: 'approve'`, `ignored: False` and its set is queued at once (`VS:3246-3255`). This covers an element the operator left out and an element new in a revised plan.
- Why it hurts: the operator said "Leave it out" for the bar bundle; the assistant re-posts; ₹35 is spent with no question.
- Fix direction: a merged row that was ignored or is new goes back to the operator as an open line.

### 16. "Leave it out" does not say what happens to the shots. Size S

- FACT. The button reads "Leave it out"; the chat hint reads "This thing gets no reference" (`CF:875`). The page text says nothing more (RJ).
- FACT. For a person the text says "A reference set is made for every person" and still offers "Leave it out" (RJ l01-l07). The round itself refuses to start without every person (`VS:3195-3196`).
- INFERENCE. I found no code that marks, warns or re-plans the shots naming an ignored element. They are made from words alone.
- Fix direction: on the line, say "used in N shots; left out, those shots are made from the description" and warn at the still.

### 17. A failed or partial set is shown as a normal set. Size S

- FACT. If turn 2 or 3 returns no picture, the set ends with one or two pictures and a note (`VW:137-139`, `150-156`). The page still says "Three pictures of the same thing" (`PF:509`). A person's face (picture 3) may be missing; then no face is added to shots, silently (`VS:2088-2089`).
- FACT. A limit or outage on turn 2 or 3 throws away the pictures already made and requeues the whole set (`VW:135-136`). INFERENCE: Google bills those pictures; the film's spend does not show them (failed jobs are left out, `VS:719`).
- FACT. The operator reads one of four fixed sentences, e.g. "The picture service refused the request" (`VS:3447-3456`). The real reason stays in the log. The only offer is to make it again, paid, with the same prompt.
- INFERENCE. The daughter (a girl of 8, EV) is a likely refusal.
- Fix direction: say "2 of 3 came back, missing: the face"; show the service's reason; keep finished turns on a requeue.

### 18. The writer's prompt and the server's three views pull apart. Size S

- FACT (EV). Many prompts ask for two states in one picture: BUCKET "empty and full of clear water", SHUTTER_WINDOW "closed and with one leaf open", CEMENT_BAG "one bag, and a short stack of five", HOUSE "from the front and from one side", PROP_POST "one of each, side by side".
- FACT. The server then asks, per turn, for "the whole", "a three-quarter view", "a close-up of the key detail" (`VS:1976`). Which picture carries which state is not said. The preamble also demands "one way only".
- FACT. The assistant is told to write "its frame" in the prompt (v3.json:288), e.g. "Framed close from above"; the server's views then override the frame.
- Fix direction: the round row gives the three views itself (state A, state B, detail); the server stops adding generic ones.

### 19. The method is tuned to building-site documentaries. Size M

- FACT. Fixed text for every film: "how the work is done", "on one real site", "one consistent way of working", "stand on a real site" (`VS:1953-1960`, `1985-1987`). "The photographs win" over the request.
- FACT. The plan may set `studio_background` (`VS:3998`); the set cosmetics ignore it and always write a real place and daylight (`VS:1965-1966`).
- INFERENCE. A client's own product (an advertisement, a product film) is not on Google Images, or a competitor's is. The model will copy what it finds. A packshot on a plain ground cannot be asked for.
- Fix direction: file the kept preamble under its category; for an exact product the client's pictures win and search is off.

### 20. Reasons a set cannot be made are told only after Done. Size S

- FACT. A set waits for an approved material spec and a measured size (`VS:3470-3487`). Step-1 lines do not show the cause (`PF:463-486` never reads it). The operator says yes, says done, then finds "not made" on step 2.
- Fix direction: show the cause on the step-1 line and settle it before Done.

### 21. Page and chat say different things. Size S

- FACT. Page note: "say done in the chat" (RJ). The operator works on a page and must go back to the chat to finish.
- FACT. Chat step 2 for a thing: "Use A / Use B / Use C / None of these", with "Correct it" among the extra choices (`CF:438-441`). The page adds the price to "No" and "Correct it" (`PF:433-435`); the chat buttons carry none.
- FACT. Chat asks "which picture is the reference?"; the page says "the one every shot starts from". Given gaps 1 and 2, the second is not true for video shots.
- FACT. The tile line asks "Use this picture from your footage as the reference?" and the yes button costs ₹35 (RJ l08): one yes means two things.
- Fix direction: one wording table used by both front ends; a Done on the page.

---

## What I did not check

- No picture of VW-24 was looked at; `pics/` and `zoom/` were not opened. Every statement about results is inference.
- The plan of VW-24 (scenes, shots, outfits) is not in the two JSON files, so shot counts per element are not given.
- `image_check.py` was not read; gap 10 rests on which reference id the check is given.
- `plugin/scripts/vw.py` and `plugin/pages/decisions.html` were only searched, not read through.
- Whether Google bills pictures of a requeued set (gap 17) is not verified.
