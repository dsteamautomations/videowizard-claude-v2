# The other voices of the visuals stage: server and chat-tool texts against the instructions and SK's decisions

Read-only review, 29 Oct 2026. Repository unchanged. Instructions: `server/procedures/v3.json`, stage `visuals` (cited as **G§n** for the guide sections and **S-STEP n** for the steps). Decisions: design/124 (Changes 1–9, A2 and A3 notes, decisions 5, 9 and 20) and design/124-a3-disagreements.md (cited as **A3 item n**).

Tags: `HOLD-C3` means the text is inside the packet's fingerprinted dict (`visuals_stage.packet()`, `identity = digest(...)`), so changing it marks prepared takes stale in every film in progress. `NEEDS-SK` means SK has to make a judgement call. `LABEL-ONLY` items are in the table at the end.

Line numbers are for the current working copy.

---

## Findings, worst first

### 1. After preparation the server says "write the plan"; the instructions say "treatment first"
- **Text:** visuals_stage.py:152, `'next': 'write out/visual-plan.json then `vw visuals check`'`. `vw.py` copies the whole reply into its JSON output (`emit({**out, ...})`, vw.py:1395), so the assistant sees this `next` beside the tool's own correct line, "Settle the treatment with the operator and record it before any plan." (vw.py:1397).
- **Disagrees with:** S-STEP 1, "Nothing else before this: no plan, no image."; Change 1 (approved), "settle the treatment with the operator and record it (`vw visuals treatment`), then write the plan".
- **Effect:** two "what next" lines that disagree, at the very first step. The assistant may write the plan before the treatment. `propose` refuses later, so the cost is wasted work, not a wrong film.
- **Fix:** set `next` to the Change 1 wording.
- **Tags:** none (not fingerprinted).

### 2. The picture check's fixed "no readable text" must line fails labelled sheets, spec labels and style sheets
- **Text:** image_check.py:22, `{'check': 'readable text', 'pass_when': 'no readable text anywhere in the frame unless the prompt asked for exact text', 'weight': 'must'}`. `lines_of` (image_check.py:278) adds it to every picture, including sheets, graphics and the style sheet.
- **Disagrees with:** the server's own lines on the same pictures:
  - visuals_stage.py:1184 (sheet block in the prompt): "the views {views}, each labelled".
  - visuals_stage.py:1190 (sheet must line): "the sheet shows {name} in a {v} view, labelled as such".
  - visuals_stage.py:2440 (graphic must line from the spec label, for example "illustrative, not to scale"): "the drawing carries the words …". This label does not go through `exact_text`.
  - G§2: the graphic style carries "labels", so a style sheet shows sample labels.
- **Effect:** these pictures carry two must lines that cannot both pass. A correctly labelled sheet is marked failed. The operator sees false failures, and a requested fix round may strip the labels. Gemini can go either way, so the result is noise on every sheet.
- **Fix:** change the line to "no readable text except the words this prompt or this checklist asks for (exact text, the views' labels, the spec's label)", or leave it off sheets and the style sheet.
- **Tags:** none (the picture check is not fingerprinted).

### 3. Packet guidance asks for handheld camera movement; the motion text and the take check demand a locked-off camera
- **Text:** visuals_stage.py:3194, "The clips beside this gap are handheld: ask for slight handheld micro-movement in the take." (`shot_guidance`, in the packet's context).
- **Disagrees with:**
  - S-STEP 4: "the motion text always states the camera, locked off on a tripod unless the shot's `camera_move` names its one move … a locked-off take whose frame drifts or zooms over 2 % fails the must line 'camera drift'".
  - The server's own lines: video_providers.py:30, "Camera: locked off on a tripod; the frame does not move, drift, zoom or slide"; image_check.py:50 `CAMERA_STEADY` (a must line); image_check.py:133–135 (`take_drift` judges a must line when `camera_move` is empty).
- **Effect:** if the assistant follows the guidance, it writes handheld motion into a prompt that the server ends with "locked off on a tripod". The generator gets contradictory text. A take that obeys the guidance fails "camera drift" and "camera steady". That means a paid take is lost.
- **Fix:** make the guidance say "the clips beside this gap are handheld: if the take should match, name the move in the shot's `camera_move` (for example 'slight handheld sway'); otherwise the take is locked off". The alternative is to drop the line.
- **Tags:** `NEEDS-SK` (match the footage's handheld look, or always lock off). Not fingerprinted: `context` is outside the digest.

### 4. "Approved start image: the end image is made from it next" on a start-only shot
- **Text:** visuals_stage.py:2821 (`_approved_next`), `'start image': 'Approved: the end image is made from it next.'`. This reply is used exactly when no end was queued with the start: either the shot is start-only, or `end_prompt` was not sent.
- **Disagrees with:** G§1 and G§6, "A take is made from the start image alone by default … only then gets an end image"; decision 9, under which the server makes the end only from the `end_prompt` written with the start.
- **Effect:** on a start-only shot, both the operator and the assistant are told an end image comes next. The assistant may generate an unneeded end image, which is paid.
- **Fix:** "Approved: the take for {shot} is the next step" when the shot is not `end_state_exact`; "Approved: write the end request (`end_prompt`) and approve this start again" when it is.
- **Tags:** none.

### 5. Packet `end_image_instruction` tells the assistant to make the end itself (decision 9)
- **Text:** visuals_stage.py:3080, "Make the end image from the approved start image as its parent; the server sends the start's own references with it. … Image 1 is the start image; images 2 onward are its identity sheets, sent by the server: take identity from them, nothing else."
- **Disagrees with:** decision 9 (SK, 29 Oct): "The assistant writes the end's request together with the start (`end_prompt`, `end_answer`, `end_region`); the server makes the end from the approved start". It also leaves out A3 item 3's region rule, "an end image is an edit inside one region". "Images 2 onward are its identity sheets" is also out of date, because since the golden-picture change the inherited parents are golden pictures, sheets and frames (visuals_stage.py:2163–2167).
- **Effect:** the assistant is told to run the end generation itself. The server still allows that path (finding 9). Paid ends get made outside the decided flow, and without the region they are refused at visuals_stage.py:2253.
- **Fix:** "Write the end request with the start (`end_prompt`, `end_answer`, `end_region`: one region, a third of the frame at most); the server makes the end from the approved start; Image 1 is the start, the later images its own references."
- **Tags:** `HOLD-C3`.

### 6. Packet `start_image_instruction` still describes a start-and-end pair for every video
- **Text:** visuals_stage.py:3074–3079, "Write the start prompt and the end prompt together before generating either. … the end image of one segment is the start of the next there; a cut starts a new pair with its own two images."
- **Disagrees with:** G§1, "a take driven by an approved start image … with an approved end image only where the shot's final state must be exact"; A2 group 1 (held for C3): "start picture; an end picture only where it must be exact".
- **Effect:** for a start-only shot the assistant is told to write an end prompt it does not need and to plan "two images". This pushes toward paid end images.
- **Fix:** "Write the start prompt (and, only where `end_state_exact` is true, the end request with it) … a cut starts afresh with its own start image."
- **Tags:** `HOLD-C3`. This is row R2151, held in A2.

### 7. "The two frames" in the continuity request (packet and chat tool)
- **Text:**
  - visuals_stage.py:3094 (packet `video_instruction`): "Write the continuity line (`--continuity`): what stays unchanged between the two frames, and for a person five traits from the sheet."
  - vw.py:1598 (chat-tool refusal): `'Give the continuity line: `--continuity "what stays unchanged between the two frames; for a person five traits from the sheet"`.'`
- **Disagrees with:** start-only by default (G§6). The server's own refusal was already corrected in A2 (visuals_stage.py:3225): "what stays unchanged through the shot (and between the start and the end image when the shot has one)".
- **Effect:** the assistant writes continuity notes against an end frame that does not exist. The take check reads these notes as "What stays unchanged" (image_check.py:177).
- **Fix:** use the server's A2 wording in both places.
- **Tags:** `HOLD-C3` for the packet text. The vw.py text is not fingerprinted and can change now.

### 8. The prepare-take refusal tells the assistant to make the end itself and "approve both"
- **Text:** visuals_stage.py:3215–3216, "This shot's final state must be exact (end_state_exact): generate the end from the start (`vw visuals image --kind keyframe --parents <start>`), approve both, then `--start R --end R2`."
- **Disagrees with:** decision 9: the end comes from `end_prompt` and is made by the server after the start is approved; "the 'make the end from the start candidate at once, approve the pair together' wording is removed".
- **Effect:** the refusal sends the assistant down the path that decision 9 retires.
- **Fix:** "…write its end request with the start (`end_prompt` and `end_region`) and approve the start; the server makes the end, then `--start R --end R2`."
- **Tags:** none.

### 9. The server still offers an end made from a candidate start, and the picture check calls a candidate "approved"
- **Text:**
  - visuals_stage.py:2157, "Parents must be approved references of this run (an end keyframe may be made from a candidate start keyframe)."
  - image_check.py:311, `{'check': 'parent', 'pass_when': 'made from its approved parent', ... 'pass': all(p.get('status') in ('approved', 'candidate') ...)}`.
- **Disagrees with:** decision 9: "No end is made from a start not yet approved … `generate_image` refuses an end image whose parent start is still a candidate, with a message naming `end_prompt`".
- **Effect:** the refusal text advertises the retired path. The check line says "approved" and passes on a candidate, so the operator is told something untrue.
- **Fix:** remove the parenthesis (and the code path, when decision 9 is built), and make the check line pass only on approved parents.
- **Tags:** none.

### 10. A person's sheet is still made from footage frames and picks (decision 5)
- **Text:**
  - visuals_stage.py:1177 (`sheet_due`, for every element, people included): "write the reference sheet of {e} now: `vw visuals image --element {e} --kind sheet --parents {sources} …`".
  - vw.py:1479: "Now one sheet per element from its frames and picks."
  - vw.py:1502: "…then generate the element's sheet from them."
- **Disagrees with:** decision 5 (SK, 29 Oct): "a person's sheet is made from words … a footage or web picture of a person is never sent to the picture AI … `sheet_due` names no picture parents for a person and says 'from the person's description'". G§5 also says "A person from the footage or the web is never a parent for an edit".
- **Effect:** the server's cue tells the assistant to send person frames as parents, which is the case SK ruled out (the image models refuse faces).
- **Fix:** for a person, `sheet_due` says "from the person's description (build, age, posture, garments, hair), no picture parents"; the two vw.py lines say "one sheet per element (a person's from words)".
- **Tags:** none.

### 11. "Approved reference sheet: the shots are made from it" skips the golden picture
- **Text:** visuals_stage.py:2823, `'reference sheet': f"Approved: the shots of {row.get('element_id')} are made from it."`
- **Disagrees with:** S-STEP 3: "as soon as an element's sheet … is approved, `status.golden_due` names it: write its golden picture at once … Every later picture of the element has the golden picture as Image 1". A3 item 7: "change 'the sheet is what shots bind' to 'the golden picture (a person: the sheet)'".
- **Effect:** for every object, place, animal or material, the operator and the assistant are told the wrong next step. The assistant may make shot pictures from the sheet, and the server then refuses them (visuals_stage.py:2224–2225).
- **Fix:** "Approved: the golden picture of {E} is made from it next" for a non-person; keep the current text for a person.
- **Tags:** none.

### 12. Rejection messages assume every rejected picture is an end image or a generated picture
- **Text:**
  - vw.py:1438 appends to every rejection: "The next end image is made from the approved start (a state from the last approved state), never from this one."
  - visuals_stage.py:2142 (refusal on any rejected parent): "make the next … end image from the approved start, not from the candidate chain."
  - visuals_stage.py:2840 and 2850: "Rejected: the assistant makes a new {picture} with your note."
- **Disagrees with:** S-STEP 3 on web picks: "reject one only if the saved file is not the picture ticked … the next search is the operator's own words (or Ignore this), never yours". A frame, a web pick, a sheet or a golden picture has nothing to do with an "end image".
- **Effect:** after rejecting a web pick or a frame, the assistant is told to make a new one itself, and is given an irrelevant end-image rule. It may search or generate without the operator's words.
- **Fix:** choose the line by kind: an end image or a state gets the current rule; a web pick or frame gets "the next search is the operator's words, or Ignore this"; a sheet or golden picture gets "the assistant makes a new one with your note". Make the vw.py appendix conditional the same way.
- **Tags:** none.

### 13. The region refusal tells an end image to become "a new picture made with the golden picture"
- **Text:** visuals_stage.py:1207, "The region covers {n} % of the frame: an edit changes one region of a third at most; a bigger change is a new picture made with the golden picture as a reference (design/111 F11)."
- **Disagrees with:** A3 item 3 (approved): "if several places or the framing change, make the shot start-only". The server's own end refusal (visuals_stage.py:2256) already says "make the shot start-only (end_state_exact false)". `check_region` serves `--region` and `--end-region` for end images.
- **Effect:** for an end image that is too large, the assistant is told to make a whole new picture, which A3 item 3 deleted.
- **Fix:** "…a third at most; for an end image, make the shot start-only (end_state_exact false); for another picture, a new picture with the golden picture as Image 1". Drop the label at the same time.
- **Tags:** none.

### 14. The "film's world" line and the scene lines are added to pictures meant to stand alone on plain ground
- **Text:**
  - visuals_stage.py:2352–2353, `WORLD_LINE`: "the subject is in a real place of the film (its ground, light and surroundings), not on a plain studio or neutral background, and not an object alone out of its place of use".
  - It is added at visuals_stage.py:2329–2331 when `(body['kind'] in ('keyframe', 'isolated') or named)`, so any sheet or component made with `--shot` gets it.
  - image_check.py:278 adds `SCENE_FIXED` ("plausible setting … the ground") to sheets as well.
- **Disagrees with:** the server's own sheet line, visuals_stage.py:1191, "nothing in the frame but {who} on plain ground"; the component block, visuals_stage.py:2355, "One {name} alone … on a transparent background"; S-STEP 3, "the thing alone on plain ground".
- **Lead checked:** the golden picture is not a misfire. S-STEP 3 asks for "the element in its real place", so `WORLD_LINE` fits it. The misfire is limited to sheets and components that name a shot, plus the "plausible setting" should line on every sheet.
- **Effect:** a correct sheet or cut-out is marked against its own instruction. These are should lines, so the picture is marked but not failed.
- **Fix:** leave `WORLD_LINE` off kinds sheet, component and style, and `SCENE_FIXED` off sheets.
- **Tags:** none.

### 15. "Nothing rests on top of the stack" is in every inventory
- **Text:** visuals_stage.py:1282, "Inventory, exactly: … Nothing else of these kinds in frame; nothing rests on top of the stack." This goes into the start and end prompts, and into the must line at visuals_stage.py:1377.
- **Disagrees with:** the plan's own `objects` (G§4: "`objects` lists the movable things in frame with `count` and `place`"). A shot with no stack, or whose action puts something on a stack (laying a course), gets a must line its own action breaks.
- **Effect:** confusing prompt text, and a must line that can fail a correct end image (for example, bricks laid on a stack).
- **Fix:** add the stack clause only when an object's place names a stack and no beat places onto it, or drop it.
- **Tags:** none (the composed block is added in `generate_image`, outside the packet digest).

### 16. Plan warning says a chart needs no drawing spec; the drawn route requires one when it carries figures
- **Text:** visual_contract.py:681–682 (`spec_missing`), "a drawing of a real object … needs a drawing_spec with its sources; a chart, a timeline or a label needs none: say so in production_method".
- **Disagrees with:** visual_contract.py:226, "is drawn: it carries figures, so it needs a drawing_spec (the sourced sizes …)"; S-STEP 4, "a drawing spec is required when the shot carries figures"; A3 item 2, "any figure … takes the drawn route, so charts … are drawn".
- **Effect:** the assistant is told to skip the spec for a chart, and the drawn check then refuses it.
- **Fix:** "…a chart or timeline with figures is drawn and needs its spec; a title or a label alone needs none".
- **Tags:** none.

### 17. Packet bind advice keeps sending the client's footage frame after the golden picture exists
- **Text:** visuals_stage.py:3165–3166 (`bind_advice`, packet context), "the texture reference: take only its surface: its colour, wear and joints". This is advised for every exact object or material at MS or closer, with no check for a golden picture.
- **Disagrees with:** A3 item 6 (approved, server's copy wins): "before its golden picture exists, a picture of the client's object sends a footage frame; afterwards the golden picture carries it … Either remove the texture-bind advice when a golden picture exists, or state that it applies to the video bind only". The server's own gate already skips once a golden picture exists (visuals_stage.py:2693).
- **Effect:** the advice and the gate disagree. The assistant binds frames it no longer needs, which uses input-picture slots and adds a second identity source.
- **Fix:** skip the advice when `golden_of(session, e['id'])`.
- **Tags:** none (context is outside the digest).

### 18. Packet `exact_patterns` rule predates the golden picture
- **Text:** visuals_stage.py:3051, "name the geometry in nouns; the pattern is demanded on the checklist at medium and close shots only; no close reference is bound yet: bind a footage frame or an isolated picture of it first".
- **Disagrees with:** A3 item 6 and item 7: after the golden picture, it is Image 1 and carries the pattern.
- **Effect:** small. It points at the frame or "an isolated picture" rather than the golden picture.
- **Fix:** "…bind its golden picture (before one exists, a footage frame)".
- **Tags:** `HOLD-C3`.

### 19. The spec-approval texts point to the per-shot command
- **Text:**
  - visuals_stage.py:2448 (warning): "approve it as a table (`vw visuals spec --shot {id} --quote`, or on the page)".
  - visuals_stage.py:3429 (refusal before a drawing is rendered), the same wording plus "(design/113 E5)".
- **Disagrees with:** A3 item 12 (approved): "Keep B as the default [one table for all specs, `vw visuals spec` with no --shot] and delete A's per-shot command, or recast it as 'for a single late spec'".
- **Effect:** the assistant asks the operator spec by spec, which is against the one-table default.
- **Fix:** "approve the specs as one table (`vw visuals spec`, or on the page)". Drop the label.
- **Tags:** none.

### 20. The chat tool's status line counts open pictures only for OpenAI
- **Text:** vw.py:1670, `images, takes = sum(1 for j in open_ if j.get('provider') == 'openai'), ...`. Gemini picture jobs have provider `gemini-image` (visuals_stage.py:2632).
- **Disagrees with:** design/120 and A2 group 4: the picture AI is chosen per film.
- **Effect:** on a Gemini film the line reads " open; 3 ready" with no count of open pictures, so the assistant cannot tell what it is waiting for.
- **Fix:** count `provider in ('openai', 'gemini-image')`.
- **Tags:** none.

### 21. "Answer each warning in the shot's purpose" (Change 7 agreed, not built)
- **Text:** vw.py:1417, "{n} warning(s): answer each in the shot's purpose and show them to the operator".
- **Disagrees with:** Change 7 (SK, 29 Oct): "'answer every warning in the shot's purpose' becomes 'answer every warning in its warning_answers entry'". Today this matches S-STEP 2, so it changes together with Change 7.
- **Effect:** warning notes leak into the purpose, which is copied into picture requests.
- **Fix:** change it with Change 7: "answer each in the shot's `warning_answers`".
- **Tags:** none (to be built with Change 7).

### 22. The "too long" warning offers a generator switch as an equal choice
- **Text:** visual_contract.py:707–708 (`length`), "the default generator makes at most {n} s: split it, or choose {Kling/Seedance} (up to {m} s) with `vw visuals generator`".
- **Disagrees with:** A3 item 17 (approved): "only when a shot is longer than the default makes and its one action cannot be cut; otherwise split it."
- **Effect:** invites a dearer generator instead of a split.
- **Fix:** "split it; only when its one action cannot be cut, choose …".
- **Tags:** none.

### 23. Leftover "start and end" and "pair" wording outside the fingerprint
- **Text:**
  - visuals_stage.py:2680–2681, "the packet carries the pair instructions and the library's job form".
  - visuals_stage.py:1536 (waiting label shown to the operator and relayed by the assistant), `f"Start and end · {sh['id']}…"`.
  - visual_contract.py:830–831 (`changes_missing`), "list what differs between its start and end picture … the pair is checked against it".
- **Disagrees with:** G§6, start-only by default; A2 group 1.
- **Effect:** small. It keeps the start-and-end mental model alive.
- **Fix:** "the packet carries the start instructions"; label "Start image · S" (or "Start and end" only for `end_state_exact`); "list what the action changes (changes); the take, and the pair where there is one, is checked against it".
- **Tags:** none.

### 24. Graphic-style warning says "every graphic is bound to it"
- **Text:** visual_contract.py:895–896, "the operator approves it once as a style sheet picture and every graphic is bound to it".
- **Disagrees with:** A3 item 8 (approved): "a parent of every graphic's first (or only) picture; later states inherit it through the chain". The server refuses two parents on a state (visuals_stage.py:2153).
- **Effect:** small. It may lead the assistant to name the style on a state, which is refused.
- **Fix:** "…and every graphic's first picture is made from it".
- **Tags:** none.

### 25. The elements line points at Google before the operator's own picture, without their yes
- **Text:** vw.py:1456, "not seen in the footage: the operator picks a picture (`vw visuals search`) or the sheet is generated from words".
- **Disagrees with:** A3 item 10 (approved): "footage, the operator's own picture, Google on their yes, AI".
- **Effect:** small. It skips `supply` and the operator's yes.
- **Fix:** "not seen in the footage: the operator's own picture (`supply`), Google on their yes (`search`), or the sheet from words".
- **Tags:** none.

### 26. The cutaway reason is about walls for every section
- **Text:** visuals_stage.py:740, `('cutaway', 'a section is cut through the wall')`. This becomes the must line "the drawing is a cutaway view (a section is cut through the wall)" (visuals_stage.py:747).
- **Disagrees with:** G§2 and S-STEP 2 ("a section defaulting to cutaway"). The default is right; the wall-specific reason is not.
- **Effect:** a section of a slab, a pipe or a roof is checked against "cut through the wall".
- **Fix:** "a section is shown cut through".
- **Tags:** none.

### 27. The not-this model prompt says eight lines, but the code keeps twelve
- **Text:** visuals_stage.py:1087, "eight lines at most, no explanations"; visuals_stage.py:1097, `[:12]`.
- **Disagrees with:** S-STEP 3 sets no number. This is an internal inconsistency in a prompt the server sends to Gemini.
- **Effect:** none for the assistant. The two limits differ.
- **Fix:** use one number in both places.
- **Tags:** `NEEDS-SK` (8 or 12).

### 28. The packet carries `image_instruction`, a one-release alias of the start instruction
- **Text:** visuals_stage.py:3091, `'start_image_instruction': start_instruction, 'image_instruction': start_instruction,   # the old name answers for one release (design/67 A)`.
- **Disagrees with:** A2 group 5: "remove the alias" (held with C3).
- **Effect:** the assistant reads the same instruction twice under two names.
- **Fix:** remove `image_instruction` with the version 3 switch.
- **Tags:** `HOLD-C3`.

### 29. Note only, not flagged as wrong: the spending cap in messages (live until design/122)
- **Texts:**
  - visuals_stage.py:386–387 (`VISUALS_CAP` refusal, which also carries the label "(design/74 L26)"; see the table).
  - visuals_stage.py:2332 and 3341 (`check_cap` calls).
  - vw.py:1415 ("against cap ₹… (over the cap)").
  - vw.py:1422 (treatment "against the cap").
  - vw.py:1434–1435 (budget: "the cap is a setting the builder changes on SK's word").
  - The `budget` fields in check and status.
- **Status:** these match G§6 and A3 item 13 today. They go with design/122. Only the label in visuals_stage.py:387 needs action now.

---

## Leads checked and found already right (no action)
- R2262: `DRAWN_PASSES = 3` against "fixes the scene up to twice". The loop at visual_workers.py:468–491 renders at most three times and fixes at most twice, so the message is right.
- R2286: the audio policy text "retain original output" (visuals_stage.py:3274) sits in the take request file, which the assistant does not read; Higgsfield is sent `sound='off'`. This is an internal record mismatch, not a voice.
- R2315, R2317, R2320 ("OpenAI", "start and end images"): already corrected in vw.py (1550, 1559, 1583) by A2.
- R0789–R1098 ("refused from the next release"): no such text is left in visual_contract.py or visuals_stage.py strings (only one docstring, at visuals_stage.py:2392, which the assistant does not read).
- `light_warning` (visuals_stage.py:3176) agrees with A3 item 23. The end-region refusal (visuals_stage.py:2255–2256) agrees with A3 item 3.
- `WORLD_LINE` on the golden picture agrees with S-STEP 3 ("the element in its real place").

---

## LABEL-ONLY: change-history labels inside strings the assistant reads (76 items)

The only problem with each of these is the label; the fix is to delete the bracket or prefix. None of them is fingerprinted. Labels inside items 13 (visuals_stage.py:1207) and 19 (visuals_stage.py:3429) are counted there, not here.

| # | Place | Label | Message (start) |
|---|---|---|---|
| 1 | visuals_stage.py:387 | (design/74 L26) | cap refusal: "…the cap is a setting the builder changes on SK's word" |
| 2 | visuals_stage.py:2118 | (design/119 rule 7) | "…'s fact or size cites the footage …: approve a footage frame…" |
| 3 | visuals_stage.py:2123 | (design/119 rule 8) | "…has a size still unknown …: measure it first…" |
| 4 | visuals_stage.py:2183 | (design/111 F21) | "the prompt does not say what Image k is for…" |
| 5 | visuals_stage.py:2203 | (design/119 rule 5) | "…is a picture of …, which is not in shot…" |
| 6 | visuals_stage.py:2255 | (design/112 S2) | "An end image is an edit inside one region of its start…" |
| 7 | visuals_stage.py:2275 | (design/112 S2) | "the end written with this start has no region…" |
| 8 | visuals_stage.py:3252 | "H5:" prefix | "…is already the start of …; two shots never share a start image" |
| 9 | visuals_stage.py:3261 | (design/112 S3) | "The end image is not aligned with the start…" |
| 10 | visuals_stage.py:3425 | (design/117 P2) | "the plan's scene_svg … names no uploaded scene…" |
| 11 | visuals_stage.py:3480 | (design/117 P2) | "The scene breaks the rules…" |
| 12 | visuals_stage.py:3551 | "H5:" prefix | "this picture is already in …" |
| 13 | visuals_stage.py:3628 | "H4:" prefix | "give the crop that makes the framing clearly different…" |
| 14 | visuals_stage.py:3631 | "H4:" prefix | "the crop lies inside the frame…" |
| 15 | visuals_stage.py:3634 | "H4:" prefix | "the crop enlarges …×…" |
| 16 | visuals_stage.py:3650 | "H3:" prefix | "clip … plays elsewhere; a frozen frame of it is never shown…" |
| 17 | visuals_stage.py:3652 | "H3:" prefix | "clip … is shown as a frozen frame in …" |
| 18 | visuals_stage.py:3655 | "H2:" prefix | "clip … is already on screen in …: showing it again is a reuse…" |
| 19 | visuals_stage.py:3659 | "H4:" prefix | "… is … s from …; an approved reuse is at least … s apart" |
| 20 | visuals_stage.py:3661 | "H4:" prefix | "a different stretch of clip …" |
| 21 | visuals_stage.py:3663 | "H4:" prefix | "clip … can be enlarged only …×…" |
| 22 | visual_contract.py:224 | (design/117 P2) | "… is drawn: give scene_svg…" |
| 23 | visual_contract.py:226 | (…, design/89 D) | "… is drawn: it carries figures, so it needs a drawing_spec…" |
| 24 | visual_contract.py:366 | (design/106 D3) | "… is unknown: record the sources tried…" |
| 25 | visual_contract.py:380 | (design/111 F19) | "a size is unknown: the drawing is illustrative only when…" |
| 26 | visual_contract.py:383 | (design/111 F19) | "'illustrative' is earned only after all four sources were tried…" |
| 27 | visual_contract.py:385 | (design/111 F19) | "nothing is unknown: drop illustrative" |
| 28 | visual_contract.py:537 | (design/111 F10) | "element … is a repeating material: give its material_spec…" |
| 29 | visual_contract.py:538 | (design/111 F10) | "its sizes live in its material_spec, not in size" |
| 30 | visual_contract.py:541 | (design/111 F10) | "material spec of …: give the unit sizes…" |
| 31 | visual_contract.py:542 | (design/106 D2, design/111 F10) | "material spec of …: give the proportions that matter" |
| 32 | visual_contract.py:579 | (design/111 F16) | "… is a person: give description…" |
| 33 | visual_contract.py:580 | (design/111 F16) | "scene … shows …: give outfit[]…" |
| 34 | visual_contract.py:582 | (design/111 F16) | "scene … changes the colours of …: give time_jump…" |
| 35 | visual_contract.py:585 | (design/111 F16) | "outfit names …, which is not a person element" |
| 36 | visual_contract.py:629 | (design/113 E6, SK 27 Oct) | "… is a … with exact sizes or numbers: the drawn route is the default…" |
| 37 | visual_contract.py:634 | (design/112 K2, K4) | "… carries text …: it moves by push_in or not at all…" |
| 38 | visual_contract.py:642 | (design/112 K1) | "… s of AI video with no visible action…" |
| 39 | visual_contract.py:688 | (design/111 F19) | "give view … and view_reason…" |
| 40 | visual_contract.py:689 | (design/111 F19) | "view …: give view_reason" |
| 41 | visual_contract.py:722 | (design/110 F6) | "… is a living thing that stands still…" |
| 42 | visual_contract.py:739 | (design/121 change 3) | "beat …'s target is a landmark … or an element…" |
| 43 | visual_contract.py:740 | (design/121 change 3) | "beat … heads for …, which is not in the shot…" |
| 44 | visual_contract.py:751 | (design/110 F2) | "…'s position … alone says nothing a picture can place…" |
| 45 | visual_contract.py:753 | (design/110 F2) | "…'s position … needs a measured amount and a visible unit…" |
| 46 | visual_contract.py:757 | (design/110 F6) | "…'s facing is a heading…" |
| 47 | visual_contract.py:759 | (design/110 F6) | "…'s heading names a landmark of the scene" |
| 48 | visual_contract.py:761 | (design/110 F4) | "…'s objects name elements of the plan…" |
| 49 | visual_contract.py:762 | (design/110 F4) | "the place of … names a landmark of the scene" |
| 50 | visual_contract.py:769 | (design/110 F4) | "…'s … goes from … to …; name the change that does it…" |
| 51 | visual_contract.py:773 | (design/111 F7) | "… is a person with the face in frame: give gaze…" |
| 52 | visual_contract.py:774 | (design/111 F7) | "…'s gaze target is a landmark … or a named element…" |
| 53 | visual_contract.py:777 | (design/110 F1) | "beat … needs done, its action in the past tense…" |
| 54 | visual_contract.py:784 | (design/111 F17) | "shot … shows several …: give groups an entry…" |
| 55 | visual_contract.py:787 | (design/111 F17) | "the … are all alike: give the reason…" |
| 56 | visual_contract.py:789 | (design/111 F17) | "the … are … and different: give one trait each…" |
| 57 | visual_contract.py:795 | (design/111 F14) | "the technique … is not an element: add it…" |
| 58 | visual_contract.py:800 | (design/111 F15) | "its claim or descriptor is about size…" |
| 59 | visual_contract.py:801 | (design/111 F15) | "size is the message: name compare_to…" |
| 60 | visual_contract.py:802 | (design/111 F15) | "compare_to names an element in frame other than the subject…" |
| 61 | visual_contract.py:805 | (design/111 F8) | "names three fixed things of the background in fixed…" |
| 62 | visual_contract.py:807 | (design/111 F8) | "… is not a landmark of the scene (fixed names landmarks only)" |
| 63 | visual_contract.py:808 | (design/111 F8) | "… is an element, a thing that can be carried…" |
| 64 | visual_contract.py:810 | (design/111 F7) | "its only change is a look or an expression…" |
| 65 | visual_contract.py:816 | (design/110 F5) | "… is held but has no props entry…" |
| 66 | visual_contract.py:818 | (design/110 F5) | "the holder of … is a subject of the shot" |
| 67 | visual_contract.py:819 | (design/110 F5) | "the places of … name landmarks of the scene" |
| 68 | visual_contract.py:820 | (design/110 F5) | "… set down needs its position…" |
| 69 | visual_contract.py:821 | (design/110 F5) | "… carried out needs its cause…" |
| 70 | visual_contract.py:828 | (design/112 S1) | "… has a change list and no exact end: its take is made from the start image alone…" |
| 71 | visual_contract.py:872 | (design/111 F18) | "… is a place the film shows: give signs_of_use…" |
| 72 | visual_contract.py:874 | (design/111 F18) | "… is not a landmark of a scene that shows … (signs_of_use)" |
| 73 | image_check.py:138 | "before design/112" | take-card "seen" text: "(a camera move is planned, or the take is from before design/112: reported, not judged)" |
| 74 | vw.py:1483 | (design/121 change 2) | round posted: "While they do, write (never generate, never ask) the graphics' answer forms…" |
| 75 | vw.py:1502 | (design/100: …) | "web references saved and approved from search … (design/100: ticking and saving is the approval)" |
| 76 | vw.py:1504 | (design/121 change 1) | "Noted on the element's 'not this' list; the next search is the operator's…" |

**Count: 76** (21 in visuals_stage.py, 51 in visual_contract.py, 1 in image_check.py, 3 in vw.py).

Outside the brief's scope but of the same kind: library.py refusals that reach the assistant through `generate_image` carry 7 more labels (library.py:185, 187, 193, 205, 227, 231, 249: design/110 F2, design/111 F7, F10, F13). They are worth removing in the same pass.

---

## Tag counts
- `HOLD-C3`: 5 (items 5, 6, 7 for the packet part, 18, 28). Item 7's vw.py part is not held.
- `NEEDS-SK`: 2 (items 3, 27).
- `LABEL-ONLY`: 76 (table).
- Untagged, fixable now: 21 (items 1, 2, 4, 8–17, 19–26). Items 8, 9 and 10 are best done when decisions 9 and 5 are built.
- Note only: 1 (item 29, the cap).
