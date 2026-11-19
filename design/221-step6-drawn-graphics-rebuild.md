# design/221: step 6, drawn graphics: the approach to the approved corrections

19 Nov 2026. SK approved the list of corrections in the builder thread on 19 Nov, row by row, with changes. This note is the approach: what is built, in which order, how each piece is tested, and how sure the builder is. Nothing here is built yet.

Sources (all in `design/_work/`): `stage-review-VW-24-step6-pictures-drawn.md`, `step6-failed-checks-VW-24-negotiable.md`, `step6-checks-too-strict-VW-24.md`, `step6-wrong-rules-VW-24.md`, `motion-menu-against-step6-gaps.md`, `time-report-from-time-logs.md`, `step6-redo-requirements-19-nov.md` (the earlier list; this note replaces it). Pictures: the two private pages of 19 Nov (the references review and the five failed drawings).

## 1. The finding the corrections answer

On VW-24, 9 drawn graphics needed 23 fact-check rounds; 41 rule answers failed. One cause sits under 39 of them: **words go in, a picture must come out, and there is no picture in between.** Each builder got about 6,000 characters of words and invented its own picture. The tile pair was drawn five ways in five drawings. The time logs add: of 3 h 22 min of step 6 work, about half was waiting for answers that were asked one at a time, and one question stayed open for 11 h 19 min.

## 2. SK's rulings on the 23 rows

| # | Correction | SK, 19 Nov |
|---|---|---|
| 1 | Shared parts drawn once, approved once | Yes. Approved in the chat, not on a page. Finished things are also shown in the chat as they finish; the page comes at the end (reading B) |
| 2 | One project per returning diagram | Yes |
| 3 | A still end-frame per shot, approved before animation | Yes |
| 4 | Proportions in the spec | Yes. First find out why the tile's confirmed width did not reach each drawing's spec line (sizes may be kept per drawing, not per part) |
| 5 | The builder looks at the real thing and the neighbour | Yes |
| 6 | A shorter, cleaner brief | Yes |
| 7 | The shared look before the first build | Yes |
| 8 | Calm camera; one tested push-in | Yes |
| 9 | The server draws the corner note | Yes. With care: the five unverified points of the side chat (section 6.9) |
| 10 | A small family of motions per film | Yes, from the Motion Menu, with a supporting document for a clean build |
| 11 | Must and should | Yes (the seven rulings) |
| 12 | "Not seen" is its own answer | Yes |
| 13 | Later rounds judge what failed and what was touched | Yes |
| 14 | No stale or defaulted rule | Yes, critical. Also act on every value the brief defaults or fixes (section 6.14) |
| 15 | Questions and notes out of the rules | Yes |
| 16 | Fewer, non-overlapping rules | **Skipped** (confidence too low) |
| 17 | Label on screen too short | Revised: a label that first appears in this shot and is too short to read is non-negotiable; a label carried over from, or continuing into, another shot of the same diagram is not counted (its time is measured across the shots); once a returning diagram is one project the check measures the whole time by itself |
| 18 | What is shown while things are made | Changed: nothing is put on the page one by one. The chat says "9 stills made and checked"; everything appears on the page at the end |
| 19 | Stills ordered at the start | Yes |
| 20 | The font asked first | Yes |
| 21 | Step 6 and step 7 named apart | Yes |
| 22 | The log says what failed | Yes |
| 23 | Deploys in the middle of a step | **Ignored** (a building-stage matter) |

So 21 rows are built. Standing rules that apply to all of them: the page only when complete (SK, 19 Nov); the operator is not asked what needs no answer (18 Nov); old runs are dropped (18 Nov); every category of video (2 Nov); the older way of each change is named in design/35; no amount of money on these screens; no deploy without SK's yes; the whole server suite is not run without SK's word (19 Nov).

## 3. How it is built

- **Four phases, in this order,** each a set of rows that touch the same files. A later phase stands on the earlier one.
- **Each phase:** a short contract with a frozen example (step 0) → builders on disjoint files → area tests → one critic (critical and serious only) → the builder thread reads the diff and looks at the result itself → one local commit. No push of a half phase that would break `main` for the live server; pushes happen per finished phase; **no deploy until all four are done and SK says yes.**
- **Tests:** area tests for what changed, written first. Wording through wording scripts with their pins. Where a thing can be tried without a run, it is tried on VW-24's stored data (the 9 rule lists, the 56 uploaded projects, the briefs), read only. The whole `server/unit` suite: only on SK's word, asked before the deploy.
- **The measurement at the end:** VW-24 is set back to the start of step 6 (a script with its undo, on SK's word) and the tester runs it again. Counted before and after: first-round failures, redo rounds, questions asked, minutes to the first thing shown.

## 4. Phase 0: read before building (read only)

| # | Open point | Why it matters |
|---|---|---|
| P0.1 | Where a size lives: per drawing spec or per part (the tile is "410 mm (confirmed)" in one brief and "None (unknown)" in another) | Row 4. If sizes are per drawing, the fix is to keep a confirmed size on the part and print it in every drawing that shows the part |
| P0.2 | How the finish layer is put on (design/186): where in the render, with which fonts, and whether text can go the same way | Row 9 |
| P0.3 | The render's "every plan label is in the project word for word" check, and where the checker's frames come from | Row 9 |
| P0.4 | How a project, its rules, its brief and its verdicts are stored (`motion_projects`, `motion_checks`), and what a second project built from the first would share | Rows 1, 2, 14 |
| P0.5 | How the HyperFrames check measures a label's time on screen, and whether it can see across shots | Row 17 |
| P0.6 | How a chat card with a picture and buttons is made today (`chat_flow`), and how a status line reaches the chat | Rows 1, 3, 18 |
| P0.7 | The motion style texts, the skill's `references/motion.md`, and which wins | Rows 8, 10 |
| P0.8 | Every default and fallback in `motion_brief` (the table in 6.14), line by line | Row 14 |

Findings are written into this note (section 9) before a phase that depends on them starts. A finding that changes the approach is brought to SK.

## 5. The phases

| Phase | Rows | What it is | Mostly touches |
|---|---|---|---|
| 1. The brief tells the truth | 4, 6, 14, 15, 20, 21, 22 | No brief before its facts; nothing defaulted is printed as a fact; a short brief; proportions; questions out of the rules; names; logs | `motion_brief`, the spec, the rule writer's instructions, the served text, the log |
| 2. The fact check | 9, 11, 12, 13, 17 | Must and should; not seen; later rounds; the corner note by the server; the label-time rule | `motion_verdict`, the checker's and rule writer's instructions, the render, the check job |
| 3. One picture before many | 7, 1, 2, 5, 3, 8, 10 | The shared look; the shared parts; one project per diagram; pictures to look at; the still end-frame; the calm camera and the motion family | the motion skill, the builder's instructions, the brief, `motion_upload`, the chat cards |
| 4. What the operator is shown | 18, 19 | Render as each passes; status lines; finished drawings shown in the chat; the page at the end; stills at the start | `chat_flow`, `page_flow`, `pictures.py`, the served text |

Row 20 (font first) is in phase 1 because S1 (no brief before the font) makes it true by itself.

## 6. Each row: what is built, the edge cases, the test, the confidence

Confidence: **High** = follows by construction. **Medium** = should hold; only a run shows it. **Low** = a guess.

### Phase 1

**6.14 Row 14: no stale or defaulted rule (critical).**
- S1: `motion_brief` refuses while the film's font is not chosen (when the film has a drawn graphic with text). The refusal says how to ask the font, with the sample.
- S2: the rule writer writes no rule for what the server checks itself: font, frame size, length, label wording, letter size.
- S3: each rule list is stored with the fingerprint of the brief it was written from. When the brief changes later, the server names the changed line, says the rules of that drawing must be read again, refuses a verdict on the old list, and the chat says so.
- Every defaulted or fixed value in the brief (from SK's screenshot), each with its action:

| Value | Today | Action |
|---|---|---|
| Font "Noto Sans" | Server default until a font is chosen | Never printed as the film's font: S1 |
| Palette | Printed as "Proposed, taken from the materials in the footage…" and read as a rule | Printed as approved colours only once approved; a proposed palette is said to be proposed and a missing neutral is Claude's (design/218). The rule writer writes no "no colour outside the palette" rule from a proposed palette |
| Text size "at least 2.6 % … inside the inner 90 %" | One sentence for every text | Says labels; the corner note is exempt (SK); with row 9 the note is the server's anyway |
| "Illustrative, not to scale" | Set when the spec has an unknown size | Kept; drawn by the server (row 9) |
| Sizes "None (unknown)" | The spec's empty values printed raw | Not printed. A part the film is about must have its proportions (row 4) |
| Proportions "-" | Empty in the spec | Not printed; same |
| Motion style | Server default "restrained" until one is chosen | No brief before the motion style is chosen, as for the font |
| Appearance | Falls back to the plan's general line, then "-" | "-" is not printed |
| Subject rules | Carried over from earlier films, "every one holds" | Printed with their source ("from the subject file X"); a rule that names another film's thing is not applied. To verify in P0.8 what exactly is carried |
| Three rounds | Fixed in the server | Kept |
| The helper's own fixed numbers ("28 px", "three quarters") | Written into rules | The rule writer writes look rules without invented numbers; S2 removes the letter-size one |

- Edge cases: a film with no text in its drawings (no font needed); a font changed after drawings passed (S3 fires: rules read again, the drawings re-checked for the font by the server, not rebuilt unless a rule fails); a brief changed in a line no rule touches (the rule writer confirms the list unchanged, one call, no rebuild).
- Tests: S1 refusal with and without a font; S3 on VW-24's stored briefs (the brief before and after the font) names the Fonts line; every "None", "-" and "Proposed" case of the table.
- Confidence: **High** for stale rules. It does not catch a rule that was wrong from the start; the still end-frame and must/should are what catch those.

**6.4 Row 4: proportions in the spec.** After P0.1. A confirmed size or proportion is kept on the part (the plan's element), and every drawing that shows the part prints it. The spec screen refuses approval of a drawing whose main part has neither a size nor a proportion; Claude proposes one and the operator confirms it once, with the spec. Edge: a part with no real-world size (an arrow, a zone). Test: VW-24's tile reaches all nine briefs. Confidence: **High** for the brief, **Medium** for the drawing.

**6.6 Row 6: a shorter brief.** Order: what the shot must show and its claims; the parts to use (phase 3 fills this); the labels; the times, in seconds from the shot's start only (no whole-film frame numbers); the must-rules; then the style. No empty lines. Test: VW-24's five briefs rebuilt, compared by hand; length reported. Confidence: **Medium**.

**6.15 Row 15: questions and notes out of the rules.** The rule writer writes rules in `rules.md` and its questions in `questions.md`. The server holds only rules; a line that is not a rule is refused with "a note is not a rule: move it to questions.md". The main assistant decides each question (SK's rule of 18 Nov), logs the decision, and a question about a fact is shown to the operator with the spec, once, before the build. Test: VW-24's 57 note lines are sorted out of the 531. Confidence: **High** for the refusals, **Medium** for the doubts being handled well.

**6.20 Row 20: the font first.** By S1. The served text for step 6 says: first `vw font`. Confidence: **High**.

**6.21 Row 21: names.** "Step 6, pictures and drawn graphics" and "Step 7, AI video (in the chat)" in the served text and on the chat's video items. Confidence: **High**.

**6.22 Row 22: logs.** A verdict's log line carries the round, the counts and the failed rules' words; the two silent refusals keep their reason; the operator's answers are logged as the operator's. Confidence: **High**.

### Phase 2

**6.11 Row 11: must and should.** The rule writer marks each rule; the server keeps the class; only a failed must sends a drawing back; failed shoulds are notes, given to the builder too when a must failed. The classes are SK's seven rulings (in `step6-redo-requirements-19-nov.md`, part 3b). A free test before anything is built: the rule writer classes VW-24's nine stored lists and the result is compared with the 41 classed failures. Confidence: **High** for the redo rounds it removes; **Medium** that the rule writer classes well, which the free test measures.

**6.12 Row 12: not seen.** A third answer. The verdict lists the frame or crop needed; the assistant takes it and the same checker answers that rule; nothing is rebuilt. A fixed set of frames for every check: the first frame, each cue, the middle of each move, the last frame, a close-up of each labelled part. The neighbour's last frame from the start. Confidence: **High**.

**6.13 Row 13: later rounds.** Rounds 2 and 3 answer the rules that failed and the rules about what the fix touched; a rule that passed keeps its pass unless the checker says what changed; the checker still looks at the whole frame for a must-kind fault. A rule the checker adds itself is a should unless it names a must-kind. Confidence: **Medium**: a fix can break what nobody re-checks; the whole-frame look is the guard.

**6.9 Row 9: the server draws the corner note.** After P0.2 and P0.3. The five points SK asked to be careful with:
1. How the finish layer is put on, and whether a line of text can go the same way with the film's font: read first; if it cannot, the note is drawn in the page the render makes, in a fixed layer above the drawing.
2. The render's "every label word for word" check must skip the note once the server draws it.
3. The checker's frames are taken before the final render: the snapshot tool draws the note too, so the checker sees what the viewer will see; the rule writer writes no rule about the note.
4. A dark ground: the note's colour comes from the film's palette (light on dark).
5. A drawing that needs its lower right corner: the brief reserves the corner; when the drawing's own content must sit there, the note moves to the lower left, decided by the server from the brief's framing line, never by the builder.
Also: the note never sits over the drawing; one size for the film. Edge: a drawing whose spec has no unknown size gets no note. Test: frames of VW-24's stored projects with the note drawn by the server, at the first frame and inside a push-in. Confidence: **High** once point 1 is confirmed.

**6.17 Row 17: label on screen too short (SK's revised ruling).** A label that first appears in this shot and is on screen under its floor: a must. A label carried over from the earlier shot of the same diagram, or continuing into the next: not counted in this shot. With row 2 the check measures the whole time in the one project. Until a diagram is one project, the server takes "carried over" from the plan (the same label in the neighbouring shot of the same diagram). Test: VW-24's "Cement" case (0.36 s). Confidence: **High**.

### Phase 3

**6.7 Row 7: the shared look, before the first build.** The assistant reads all approved specs and writes one list for every builder and checker: the choices that apply to all drawings. A choice with no fact is Claude's and is logged; a choice with a fact is asked once, with the others, before the first build. Confidence: **High**.

**6.1 Row 1: shared parts.** Before any shot is built, one helper draws the film's repeating parts as one small parts file (code) with a picture of each. They are shown in the chat: the picture, click to enlarge, Approve and Reject on the card (SK). Once approved the server keeps the file; every brief says which parts to use; the upload refuses a project that redraws a shared part instead of using it (checked by the part's id in the project). Edge: a film with one drawn graphic (no shared parts); a part rejected (drawn again with the operator's words); a part that must change later (a new approval, and the drawings that use it are re-rendered, not rebuilt). Confidence: **High** for the 14 failures of this kind. Limit: a wrong part approved is wrong everywhere; the card is the guard.

**6.2 Row 2: one project per returning diagram.** A diagram that returns across shots is one project; each shot is a stretch of its timeline. The next shot is built on the earlier shot's files and its last frame. Cost, accepted: shots of one diagram are built in order. To verify in P0.4 whether one upload can serve several shots or each shot uploads a project that starts from the earlier one's files; the second is the smaller change and is the default. Confidence: **High** for the mismatch between shots.

**6.5 Row 5: pictures to look at.** The brief names the footage picture and the approved part "to look at before drawing", and the neighbour's last frame; the builder's instructions say to open them first. Confidence: **Medium**.

**6.3 Row 3: the still end-frame.** For each shot the builder first makes the last frame only, no motion. Claude checks it against the must-rules. It is shown in the chat (SK: the chat, not a page): the picture with Approve and Reject. Only then is the motion built. To keep the questions few, the stills of one diagram are shown together in one card. Edge: a shot whose point is the motion itself (the still shows the end; the motion is judged at the fact check). Confidence: **Medium to high**: most of the 19 "idea in words" failures are visible in a still.

**6.8 Row 8: calm camera; one push-in.** The motion style texts say: a landed label stays still; the whole frame does not push or pan unless the shot's brief asks for it; the "avoid stillness longer than two seconds" line goes. The motion skill gives one tested way to push in: the whole picture scales as one group, the note is outside it. The recipe is tried on VW-24's BEAT_04-B1-S5 before it is written down. Confidence: **Medium**; it changes the look, and SK sees it on the redo.

**6.10 Row 10: a small family of motions.** From the Motion Menu, by the review `motion-menu-against-step6-gaps.md` (sections 3 and 4). A supporting document is written first: `design/221a-motion-family.md`, with: the energy limit per motion style; "rest after loud" with its numbers; "one strongest move, on the claim"; and for each motion style a family of 3 to 5 named motions for labels, callouts, counters, charts and before-and-after, as words in VW2's own files, not as catalog pieces (SK's decision of 12 Nov on library blocks stands). Letter-by-letter effects are left out until tested in Tamil and Hindi. Where it goes: the shared look and every brief. Confidence: **Medium**: for consistency; no VW-24 failure came from this.

### Phase 4

**6.18 Row 18: what the operator is shown.**
- A drawing is rendered as soon as its fact check is clean (the next-step line gives the exact command; P0.4 settles whether the server can note the passed project on the shot itself).
- The chat gets a status line when the count changes: "5 drawn graphics done, 4 being redone, 1 not started; 9 stills made and checked."
- A finished drawing is shown in the chat as it finishes, to look at early; no answer is needed there (reading B).
- An early decision is a chat card: a shared part, a still end-frame, a held drawing (with its open must; select with a reason, reject, or one more round).
- The page is published once, when every still, drawn graphic and component is made, for the full review.
- Retired: "all drawings in one plan revision"; "held, asked as a free chat question"; the page filling while things are made.
Confidence: **High**.

**6.19 Row 19: stills at the start.** Ordered when step 6 begins, beside the drawings; Claude checks each as it returns; counted in the status line; on the page at the end. Confidence: **High**.

## 7. After the four phases

1. One critic over the whole, for what the phases did to each other.
2. The reset script for VW-24, with its undo. Cleared: the drawing projects, their checks and verdicts, the three recorded choices. Kept: the specs, the references, the plan, the font Mukta. Run on SK's word.
3. SK's word on the tests before the deploy; then the deploy, on SK's yes; then the plugin is published.
4. The redo on VW-24, measured as in section 3.
5. The report to SK: each row, built or not, what was tested, what was seen on the redo, what is not covered.

## 8. How sure the builder is, overall

- The set will not eliminate wrong drawings. It should remove most first-round failures of the kinds seen and cut the redo rounds by well over half. That is a judgement from one film of one category.
- Rows 1, 2 and 3 carry most of the effect and are the largest work.
- Row 14 is the one that makes the rest trustworthy: without it a check can pass a false rule.
- The redo is the measurement; the numbers of section 3 are reported, whichever way they fall.

## 9. Phase 0 findings

(Written here as each is read. Read by a helper, not yet re-read line by line by the builder thread; each builder confirms the lines it touches.)

### P0.1 and P0.8: the brief, the sizes, the defaults (19 Nov)

- **SK's suspicion is right: a size is kept in two places and nothing joins them.** A shot has its own `drawing_spec` (`visual_contract.py:134`); a material has `material_spec` on the element (`:145`). `motion_brief` reads only the shot's spec (`visuals_stage.py:6169`). The shot's `element_ids` are used only to choose pictures. So the tile's confirmed size on the element, or on another shot's spec, never reaches this shot's line. The size rows are also keyed by free text ("tile length", "tile pair depth in section"), so no code can match them. The approval screen shows "Already confirmed" for an exact match but writes nothing.
  - **What this changes in row 4:** the brief prints, for each element of the shot, that element's confirmed sizes and proportions (from `material_spec`, and from the shared part once row 1 exists), before the shot's own spec line. There is no notion of a "main part" in the code; the nearest is the shot's `element_ids`. The proportion check goes in `spec_research_needs` (`visual_contract.py:427`), the one function both approval paths use, and applies to the elements of kind object or material that the shot names.
- **"None (unknown)"** is the raw `value` of an unknown size printed as text (`visuals_stage.py:6170`); "(given)" is printed when a size has no status. **Shows** and **Framing** can also print "None".
- **The font:** before a font is chosen the brief prints `Fonts: "Noto Sans" … no other family` with no word that it is a default (`_motion_fonts`, `:5796`). `need_font` is called only at upload (`:5834`). S1 is one line after `:6160`; three test files build a run without a font and must record one.
- **The motion style:** with none recorded the brief prints an older fixed text (`film.OLDER_STYLE`, `film.py:37`), not "restrained". `need_motion` exists (`film.py:84`) and is not called by the brief.
- **The palette:** "Proposed, taken from the materials in the footage…" is not server text. The assistant wrote it into the plan (`foundation.graphic_style.palette`, free text). The palette has no approval of its own; it counts as approved once a gap is accepted. **Action for row 14:** the brief says "the palette (not yet approved)" until then, and the rule writer writes no palette rule from an unapproved palette.
- **Whole-film frame numbers** in "Progression" are the plan author's free text (`information_progression`), not generated. **Action for row 6:** the planner's instruction says times in seconds from the shot's start; the brief does not rewrite the text.
- **Subject rules** are global: one file per subject in `server/subject_rules/` plus rules operators added on any film (`add_subject_rule`, stored under `subject-rules/{name}.json`, not per run). A file is picked when the words of its name appear in the shot's words. Only `rat-trap-bond.md` exists. The header "every one holds in this drawing" names no source. **Action for row 14:** the brief names the source file and the film a rule was added on.
- **The text-size sentence** is fixed for every text (`:6193`); a second copy with other numbers is in `plugin/skills/motion/SKILL.md:38`. Both change together.
- **Rules at upload:** kept as `{'id', 'rule'}` per line in `session['motion_projects'][sha]['rules']` (`:5841`). Nothing of the brief is stored. **S3:** `set_motion` computes the brief's digest itself at upload and keeps it beside `rules` (no change to the plugin).

### P0.2, P0.3, P0.4, P0.5: the render, the corner note, the label time, the binding (19 Nov)

- **The finish layer** (`design/186-library-parts-check-on-first-use.md`, the note kept its old file name) is pasted into the project's page before the browser draws it (`motion.apply_finish`, `motion.py:147`, called from `visual_workers._motion_folder`, `:756`). It is not a second pass over frames. The film's font files are already in the folder at that point.
  - **Row 9, point 1: yes, a line of text can go the same way.** A sibling of `apply_finish` adds an `@font-face` for the film's font and a placed line with the note.
  - **The note needs its own switch.** The finish has a safety net that leaves the layer off when a frame does not draw the same twice (`render_with_finish`, `visual_workers.py:775`); the note must not vanish with it. So the note is its own layer, always written in `_motion_folder`, not part of `request['finish']`.
  - **Point 2:** the "every label word for word" check (`render_motion`, `visuals_stage.py:5921`) reads the uploaded files, not the prepared folder. With the note in the plan's labels and drawn by the server, the render would be refused. The note leaves `scene_motion.labels`; the server takes it from `drawing_spec.label`. Today nothing checks that the note is in the labels at all: the assistant copies it by hand.
  - **Point 3:** snapshots are made from the same prepared folder as the render (`process_motion_tool`, `visual_workers.py:835`), so a layer written in `_motion_folder` shows in the checker's frames by itself. The HyperFrames check runs on the plain project without server layers, so it never judges the note; the server sets its size and place, so nothing is lost.
  - **A snapshot of a project not yet named in the plan has no labels.** So the note must not depend on `scene_motion`: it comes from the shot's spec.
- **Row 17, the label time.** The warning comes from the HyperFrames tool, not from server code; the server keeps `code`, `message`, `fix`. Each `line_unread` message starts with the label's own words: `"Cement" (1 word) is on screen 0.36 s (±0.01 s), under its 0.40 s floor`. So the server can tell which label it is by those words. Nothing in the server knows that a label continues from or into another shot. **How it is built:** at the check, a `line_unread` whose label is in this shot's labels and not in the labels of the neighbouring shot of the same diagram is a must; one that is shared with a neighbour is not counted. "The same diagram" is taken from the plan: the drawn shots of one gap, and a shot's `return_of`.
- **Binding a passed drawing to its shot (row 18).** Today the assistant must put the upload's sha into the plan and propose a new plan version for every drawing. The server cannot do that itself without harm: every render carries the digest of the whole plan, and `select` refuses a take when the plan changed since it was rendered (`visuals_stage.py:5609`), so a plan version per drawing makes the other drawings' takes stale. **How it is built:** the labels and cues of every drawn shot are put into the plan once, before the first build (they are known from the spec). At a clean fact check the server notes the passed project for the shot in the session (`motion_bound`), and `_motion_request` reads it when the plan names no sha; labels and cues count for the bound project. The render follows with no plan change.
- **Row 2, one project per returning diagram.** Four things stop one upload from serving several shots: the project's length must equal the shot's; a render always runs the whole timeline from 0; verdicts are kept per shot; labels and cues are per shot. So the default of 6.2 stands: each shot uploads its own project, built on a copy of the earlier shot's files. The copy is the builder's step (the earlier project's zip is given to it); nothing on the server refuses it. The shared parts (row 1) make the copies the same by construction.

### P0.6, P0.7: the loop, the chat, the page, the styles (19 Nov)

- **The loop today** (served text, visuals part "later", section 11): a brief per shot → one rule writer per shot, all at once → one builder per shot, three or four at once → snapshots → a fresh checker per round → verdict. The builder gets `brief.md`, `rules.md` and `refs/` through the skill (`SKILL.md:12`); the builder's own agent file names only the brief and the pictures (`vw-motion-shot.md:11`): to be made the same. **Nothing hands a builder another drawn shot's project or frame.**
- **"All drawings in one plan revision" is not in any text.** The texts say "propose the revision" per shot. The assistant chose to batch on VW-24. With the binding of P0.4 the question goes away.
- **Stills:** nothing tells the assistant when to start them, and the server does not cue a still that is not yet asked for. Row 19 needs one sentence in the served text and a server cue ("N still shots have no picture yet").
- **Chat cards:** an item with a picture and buttons exists (`chat_flow._item` with `show=[_pic(...)]`; the AI-video still uses Approve / Reject). A new kind is added in `visuals_stage.waiting()` and `chat_flow._waiting_items`. Rows 1, 3 and the held drawing use this.
- **Status lines:** the tool's answer already carries lines the assistant must say (`then`, `tell`, `working`). `vw visuals status --wait` does not count stills and drawn graphics apart, and the helper loop is invisible in it. Row 18 adds the counts on the server, from the plan.
- **The page today opens the moment step 5 ends** and says "{n} more are being made or checked: they come to the page later." For "the page only when complete" it needs a list of what the plan expects (every still, graphic in steps, drawn shot and component) and stays closed until all are made. The chat hands out each still as it becomes ready today; it gets the same gate.
- **Motion styles** are eight files in `server/motion_styles/` (restrained, lively, bold, technical, editorial, playful, data-led, product). The skill says the style wins over its own reference (`SKILL.md:44`), and the reference says "a landed title is dead still" while Lively says "Avoid stillness longer than about two seconds" and Editorial "nothing is ever quite still". Row 8 changes the style texts and the sentence about which wins; the wording is in `221a-motion-family.md`.
- **Names:** the served text's section is "6. SHOT IMAGES AND VIDEO"; the page says "Pictures and drawn graphics".

## 10. The camera in a drawing that explains (SK's criterion, relayed from a side session, 19 Nov)

SK's words: "the drawn graphics (using hyperframe) are mostly for explaining concepts. so apply that criteria". This refines rows 8 and 10 and `221a-motion-family.md`; it agrees with SK's answer in the builder thread (the calm camera in all eight styles). Judgement from the code, the style texts and one film; only "Follow" was seen on a real film, and it failed there.

1. **A style does not have one camera.** The camera is its own small list of flows. A style allows some of them. Each shot picks **one**, by what the explanation is doing, and the shot's brief names it. Fixed when in doubt. The style decides how parts and labels arrive, not whether the frame moves.
2. **The flows for explaining (six):** Fixed; Step closer (whole to one part, once); Pull back (part to whole, once); Pan along (a long object, a process in a line, a map); Follow (several steps closer as parts are named, at most three in a shot); Slow push-in (a few percent, to hold one idea through a long sentence, only when no label is near the edge). Not offered for a film that explains: Orbit, Drift, Punch-in, Bob, Whip; they stay for adverts, product films and social clips, filed by category.
3. **By what the explanation is doing:** naming parts → Fixed. Comparing two things → Fixed, always. A quantity (a chart, heaps, counts) → Fixed, always. A change of state → Fixed. Whole to part → Step closer. Part to whole → Pull back. Longer than the frame, or a process in a line → Pan along. A flow (load, heat, water) → Fixed; pan only if the path leaves the frame. A map → Step closer or Pan along. A title or text → Fixed.
4. **Per style, for a film that explains:** Technical: Fixed usual; Step closer, Pull back, Pan along. Restrained: Fixed; Step closer, Slow push-in. Data-led: Fixed only. Lively: Fixed; Step closer, Pull back, Pan along, Follow. Editorial: Fixed; Slow push-in. Bold, Playful, Product: Fixed on any shot that explains; their own moves only on shots that do not explain.
5. **Ten points for any camera move** (1 to 5 were seen to fail on VW-24): (1) one camera flow per shot, named in the brief; (2) the whole picture moves as one group; (3) a label lands only after the camera has come to rest, and its reading time counts from then; (4) the corner note is outside the moving picture (row 9 does this); (5) a returning diagram opens exactly as the earlier shot ended; (6) label size is judged at the end framing; (7) never move the camera during a comparison or a quantity: a zoom changes how big things look and makes the comparison false; (8) never move the camera at the moment a part changes state; (9) the move starts on the narration's word and is never faster than the eye can follow; (10) the last second of the shot is still.
6. **SK's ruling, 19 Nov ("YES" to the builder's recommendation):** point 7 (no camera move during a comparison or a quantity) is a **must** of the fact check: it can mislead the viewer about size. Point 8 (no camera move at the moment a part changes state) is **style advice**: it only makes the change harder to follow.
7. Where it goes when built (phase 3): the flow's name on the shot in the plan and in the brief; the list of flows and the table of point 3 in the motion skill; the per-style allowance in the style files; points 2, 3, 6, 9, 10 in the builder's instructions; the push-in recipe of row 8 is "Step closer" built as one group.

## Not covered

- Row 16 (fewer rules) and row 23 (deploy practice): by SK's word.
- Other categories of film: the redo is one construction explainer.
- The stills and the references of step 5 keep their known faults from the dry run.
- A screen for step 7.
