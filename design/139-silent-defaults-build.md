# design/139: building SK's design/138 decisions: requirements, impact on today's process, tests (2 Nov 2026, for SK's approval)

Source: SK's answers in `design/138-silent-defaults-questions.md` (A1–A8, B1–B12, C1–C25, D1), given in chat on 2 Nov 2026. Answers that keep today's behaviour need no build and are listed at the end. Paths are relative to `server/app` unless shown otherwise.

**Lane:** regular. Server, plugin and instructions (v3). Built, tested and committed after SK approves this list; **not deployed until SK says so** (deploy hold, 2 Nov).

**Depends on design/137** (the film's category, read from the script and confirmed in chat; not built yet). R12 (framing by category) needs it. Proposed: build design/137 first, in the same release.

## Films open today and what happens to them

VW-12 (the rat-trap brick trial film, to be deleted), VW-13 (30 Oct), VW-16 and VW-17 (2 Nov). Rule for every change below: **a film keeps what it was already made with; a new decision applies at the next step it has not yet done.** For example, VW-17's analysis already ran at horizontal 25 frames a second, so its cut stays horizontal 25. Each change names its older way for design/35.

---

## R1. The film's shape and frame rate come from the footage, and the AI video shape is asked (A1, A2, A3, C2, C20)

**Requirement**
1. After the clips are listed (the media step), the server counts the clips. Vertical means taller than wide once the rotation flag is applied; horizontal means wider than tall. It also counts each clip's frame rate.
2. The assistant recommends the shape most clips have and the frame rate most clips share, with the counts: "14 horizontal, 3 vertical: a horizontal film, the vertical clips used as they come up". The operator decides. The choices are **horizontal (16:9) or vertical (9:16)** only.
3. Straight after, the assistant asks the AI video shape. The recommendation is the film's own shape. The operator may choose the other one; nothing is refused.
4. Both answers are recorded on the server, with the operator's words: `vw shape <horizontal|vertical> --video <horizontal|vertical> --fps <n> --quote "<words>"`.
5. Everything that today assumes 1920 × 1080 at 25 reads the record instead:
   - the cut's timeline (`stage2/stage.py:19`);
   - the analysis's project timeline (`analysis.py:38`);
   - picture sizes and the job form (`library.py:118`, `:262-264`);
   - the frame-rate fallbacks in visuals (`visuals_stage.py:133`, `:182`, `:282`, `:796`, `:4199`);
   - the take's aspect: `PrepareTake` defaults to 16:9 today (`main.py:373`), and the plugin never sends it. The take now follows the recorded AI video shape.
6. Pictures follow what they are for. A start or end picture of a take uses the AI video shape; a still or a graphic uses the film's shape.
7. The brief stops asking the frame shape. Its "16:9 unless they say" line goes (`procedures/v3.json:47`). Square and 4:5 are refused by name: "kept for a future update (SK, 2 Nov)".

**Why it must come before the analysis:** the analysis judges crops against the film's frame (`analysis.py:38`). The clip listing already holds width, height, rotation and frame rate for each clip, so the count needs no analysis. See question Q1.

**Unstated but expected**
- `vw status` and the run line show the shape, the AI video shape and the rate.
- The same server step serves a page later (one flow, two front ends).
- An AI video in the other shape is placed as C23 already does: it fills up to 1.35 times, then keeps bars. The assistant says so when the operator chooses it.

**Edge cases**

| Case | Handling |
| --- | --- |
| No clips (a film made only of AI pictures) | no recommendation; the two shapes are asked plainly |
| A tie (as many vertical as horizontal) | both offered, no recommendation |
| Square clips | counted and reported as square; they vote for neither |
| A phone clip stored wide with a 90° rotation flag | counted by its picture as seen (rotation applied) |
| Clips at 29.97 or 59.94, or variable-rate phone clips | the film rate is a whole number (24, 25, 30, 50, 60); 23.976, 29.97 and 59.94 are offered as 24, 30 and 60, and the assistant says so. Clips already conform to the nearest frame (`stage2/validator.py:_tl_frames`). See Q2 |
| Rates disagree | the majority is recommended, together with the shape question (one message) |
| A changed mind after the analysis has started | refused: the analysis judged crops against the first answer; the refusal says to start the analysis again (`vw analysis --again`) if the shape must change |
| Asked twice for the same film | the second record replaces the first only while nothing reads it yet (before the analysis); otherwise refused as above |

**Failure modes**
- The analysis or the cut is refused for a new film with no shape record, naming `vw shape`.
- Older films (VW-12, VW-13, VW-16, VW-17) with no record are read as 16:9 at 25. That is what they were made with, not a guess for a new film. It is kept until they close (older way, design/35).

**Impact on today's process**
- The media step gains one question pair.
- The brief loses the shape question.
- The analysis, the cut, pictures and takes change their reading.
- Vertical films have never been made end to end. The first vertical film is an untested path through the cut (`stage2/render.py`), the editor's package and HyperFrames (drawn motion graphics); test with a short vertical film before a client's.

**Tests**
1. The shape count: mixed clips, a tie, square clips, a rotated phone clip, and no clips.
2. Frame-rate rounding: 29.97 becomes 30 and 23.976 becomes 24.
3. `vw shape` records the shape with the words; 1:1 and 4:5 are refused by name; a change after the analysis has started is refused.
4. The analysis request and the cut timeline carry 1080 × 1920 for a vertical film.
5. A take carries the AI video shape when it differs from the film's.
6. The analysis and the cut are refused without a record on a new film; an older film reads 16:9 at 25.
7. Instruction wording test: the brief no longer asks the shape.

---

## R2. Voices page: Eleven v4 settings shown and editable; the narration uses the voice's latest audition settings (A4, C4)

**Requirement**
1. The voices page shows Eleven v4's two settings with their plain effect: stability and similarity, 0 to 1, starting at 0.5 and 0.75.
2. "Try again with these settings" re-reads the test passage.
3. Each audition records its model and settings. Today the request already carries them (`voices.py:478-500`, `row['request']['settings']`).
4. **The fault:** a narration in a voice uses the settings of that voice's latest audition (the page has no separate chosen-audition record; the operator chooses a voice and narrates in it), shown before the narration starts. Today it uses the defaults (`voices.py:473` `narrate`). This is fixed in the server function both front ends call.
5. v2 and v3 are not offered. A request naming them is refused by name on both front ends (older way: retired).

**Edge cases**
- A value outside 0 to 1 is refused.
- A voice with no audition yet narrates at 0.5 / 0.75, and the page says so.
- An audition made before this change has its settings recorded already. If none are recorded, it was made at 0.5 / 0.75.
- Several auditions of one voice: the latest is used.

**Impact:** the voices page template and its two calls, `voices.narrate` and `voices.tryout`. The chat flow keeps working. Its `--model` choice narrows to v4.

**Tests**
1. The narration carries the latest audition's settings.
2. Out-of-range values and a v2 or v3 request are refused.
3. A page check on a local copy (as design/UX1).

---

## R3. Highlight colour chosen per drawing; brand colours from the card, otherwise asked once (A5)

**Requirement**
1. **SVG drawings:** a drawing whose actions use `highlight` names its colour (`highlight_color`, a hex value). The fixed `#FFC43D` (`drawn.py:20`, `:128`) goes.
2. **Drawn motion graphics (HyperFrames):** the assistant already writes the colours. The instruction and the guidebook say how to choose a highlight: it stands out against the background and everything else in the frame, and uses the brand colours where they stand out.
3. Brand colours are read from the client card (`color_palette`). When there are none, the assistant asks once per film: "What colours would you prefer to use?" The answer, including "no preference", is recorded with the operator's words (`vw colours "<list>" --quote`).
4. A preferred colour is never forced where it would not stand out.
5. The scene-review agent (`plugin/agents/vw-scene-review.md`) checks that the highlight stands out and does not clash.

**Edge cases**
- A bad hex value is refused.
- A highlight with no colour is refused, naming the field.
- A card with colours: no question is asked.
- "No preference" is recorded, and the assistant chooses.

**Older way:** SVG drawings already rendered keep their yellow. A drawing made again after the change names its colour.

**Tests**
1. The highlight colour named in the drawing is the one rendered.
2. A missing or bad colour is refused.
3. The colours are recorded with the words.
4. The question is asked only when the card has no colours (wording test).

---

## R4. The cut is refused until a scene split is approved (A6)

**Requirement:** the cut's options step refuses when no scene split is approved, naming the step to approve it. Today it splits one scene per paragraph without telling anyone (`stage2/stage.py:121-123`; `stage2/narration.py:190-207` is then unused).

**Impact:** a film whose options already ran is untouched. The instructions already propose a split for the operator to approve (`v3.json:220`).

**Tests**
1. Options are refused without an approved split.
2. Options run with one.

---

## R5. Languages are detected, never assumed to be English (A7)

**Requirement**
1. **Footage:** the analysis is no longer told "English" (`analysis.py:78`). It is told the languages are not given and to report what it hears. The clip record already has `spoken_language` for each speech block (`clip_log/schema.py:25`).
2. After the analysis, the summary names the film's footage languages: the main one first, then one or two others when the speech is mixed, or "no speech".
3. **Narration:** the assistant reads the language from the narration text at the brief and records it as `production.narration_language`. It tells the operator, who corrects it if it is wrong.
4. The brief stops asking the footage languages (`v3.json:47`).

**Edge cases**
- No speech in any clip: "no speech" is reported, and nothing is refused.
- A script mixing two languages: the main one is recorded and the other is named.
- Latin-script text that is not English (Hinglish, for example): the assistant names what it reads, and the operator confirms.

**Older way:** analyses already run keep their result. A re-run of an older film uses the new rule.

**Tests**
1. The analysis request carries no assumed language.
2. The summary reports the languages from the clip records: mixed, single and none.
3. The brief records the narration language read from the text (wording test).

---

## R6. The drawing-method note corrected (A8)

**Requirement:** the plugin comment (`plugin/scripts/vw.py:640`) and any operator-facing line that still says SVG is the default now say HyperFrames (design/130). It is wording only.

**Test:** none needed beyond compiling.

---

## R7. Spending limit on, shown at the start of visuals (B2)

**Requirement:** the limit is enforced already (`visuals_stage.py:398-410`), and the estimate already returns `cap_inr`. The instruction for the visuals start tells the operator the estimate and the limit before the first picture.

**At deploy:** the live `VISUALS_CAP_INR` on the VM is read (that one value only) and reported. Our notes say "removed 28 Oct" while the code applies ₹5,000.

**Test:** wording test only.

---

## R8. The plan must name every join (B6)

**Requirement**
1. Every shot in a gap names `transition_in` (cut, dissolve or match). A gap's last shot also names `transition_out`.
2. A plan with an empty join is refused by the plan check, naming the shots.
3. The default join in assembly (an 8-frame dissolve at graphics, a cut elsewhere: `stage3/assembly.py:20-35`) is used only for plans approved before this change.

**Older way:** kept until VW-13, VW-16 and VW-17 close, then retired.

**Impact:** every new plan carries two more fields per gap edge. The instruction already describes them (`v3.json`, `transition_in`).

**Tests**
1. A plan with an empty join is refused.
2. A plan with all joins passes.
3. An older approved plan still assembles with the default.

---

## R9. Shot lengths (C6)

**Requirement**
1. **No minimum on a blank.** The 3-second refusal and flag go (`stage2/validator.py:10`, `:130-134`).
2. **An AI video shot is at least 2 seconds on screen.** It is made at the generator's 3-second minimum and trimmed, as `take_seconds` already does (`visual_contract.py:516`). A video shot under 2 seconds is refused with "use a single picture" (`visual_contract.py:796`, beside the 10-second maximum).
3. Drawn and explainer graphics have no minimum.
4. The 10-second longest take stays, because Omni is the only video model.
5. Removed:
   - the long-blank warning (`stage2/validator.py:11`, `:16-17`);
   - the long run of AI video (`visual_contract.py:502`, `:971-984`; `visuals_stage.py:445-446`);
   - the long real shot (`stage2/validator.py:19`, `:196`).
6. Instruction and guidebook lines that state the removed rules are reworded. The retired sentences go into `server/retired-sentences.json`.

**Edge cases**
- A 2.0-second video passes.
- A 1.9-second video is refused.
- A 1-second blank filled by a still passes.

**Impact:** fewer flags to the operator. The plan may now place 1–2 second pictures and graphics.

**Tests**
1. A 2-second blank is accepted.
2. Video at 1.9 seconds is refused and at 2.0 seconds passes.
3. None of the three warnings appears any more.
4. The retired sentences are refused by name.

---

## R10. A picture request must name its kind (C11)

**Requirement:** the server already requires the kind (`main.py:196` has no default). The plugin fills "keyframe" when it is left out (`plugin/scripts/vw.py:1784`, `:1803`). That fill goes, and `vw visuals image` without `--kind` is refused, listing the kinds.

**Test:** the plugin refuses a request without `--kind`.

---

## R11. The camera is "not known" instead of guessed (D1)

**Requirement**
1. In `footage.camera_of` (`footage.py:46-48`), a clip with no maker tag and no known file-name pattern is recorded as **unknown**. Today any 8-bit clip under 50 Mbit/s is called "phone".
2. The codec stays in the evidence line, so the operator sees why.
3. The operator's correction stays as it is (`footage.CAMERAS`).
4. Downstream, an unknown camera is already left out of the look line (`visuals_stage.py:1004`).

**Impact:** a film's summary may read "camera not known" or "mixed" where it read "phone". Clips with a phone maker tag (Apple, Samsung, …) or a phone file name (PXL_, IMG_, VID_) are still read as phones. See Q3 on the "professional" guess.

**Tests**
1. An 8-bit, 20 Mbit/s clip with no tag and an unfamiliar name is unknown.
2. An Apple-tagged clip is a phone.
3. A PXL_ name is a phone.

---

## R12. Framing by category (C14; needs design/137)

**Requirement:** the framing line given for AI pictures ("Thirds by default, the centre only on purpose", `visuals_stage.py:3471`) reads the film's category. An advertisement or product film may centre the product as the hero; every other category keeps thirds. A film with no category is refused at visuals preparation already (design/137).

**Tests**
1. An advertisement film's guidance allows a centred product.
2. A documentary film's guidance keeps thirds.

---

## R13. The drawing font is asked once, with Noto Sans as the reference (C16)

**Requirement**
1. Before the first drawn shot, the assistant asks once per film: "Noto Sans (recommended), or another font of the same quality". The choices are the fonts the server holds.
2. The answer is recorded with the words (`vw font <name> --quote`).
3. Both drawing routes use it. SVG drawings already accept a font file (`drawn.font_file`). HyperFrames gets the font file from the server (`visuals_stage.py:3881`, `visual_workers.py:532`).
4. Renders have no network access (`motion.py:3`), so a font must be a file on the server. Today only Noto Sans is there (`server/fonts`). See Q4.

**Edge cases**
- A font the server does not hold is refused, listing the ones it has.
- A label in a script the chosen font cannot draw (Tamil, Devanagari): Noto Sans is used for that label, and the check says so.
- Asked again after drawings exist: allowed, but only drawings made afterwards change, and the assistant says so.

**Older way:** films without a recorded font draw in Noto Sans, as today (kept until they close).

**Tests**
1. The recorded font reaches both routes.
2. An unknown font is refused.
3. Older films keep Noto Sans.

---

## R14. Industry and audience read, then asked once (C19)

**Requirement**
1. The picture job form reads the industry from the client card and the audience from the brief (`library.py:131-137`).
2. When the card has no industry, the assistant asks once at the brief and records it in `production.industry`.
3. "other" and "general" are no longer filled in for new films.

**Older way:** films already past the brief keep "other" and "general" until they close.

**Tests**
1. The job form carries the card's industry and the brief's audience.
2. A new film with neither is refused at the brief step, naming the question.
3. An older film keeps the fallback.

---

## Questions for SK before the build

- **Q1. When is the shape asked?** Your words were "once the clips are listed and analysed". The analysis needs the shape before it runs, because it judges crops against the frame. Proposed: right after the clips are listed, just before the analysis starts.
- **Q2. Frame rates 29.97 and 59.94.** Proposed: the film runs at 30 or 60, and clips conform to the nearest frame, as they do today between mismatched rates. Alternatively, support exact NTSC rates, which is a larger change across the cut.
- **Q3. The "professional" guess.** The same codec rule calls any 10-bit or high-bitrate clip "professional". An iPhone recording in ProRes is 10-bit, so it would be called professional. Proposed: unknown too, the same as D1.
- **Q4. The font list.** Proposed: Noto Sans (recommended), Inter, Roboto, Montserrat and Lato. All are free (OFL) and added as files under `server/fonts`. A client's own brand font file would come later (no upload step exists today).

## Answers that need no build (kept as they are)

| Answer | What stays |
| --- | --- |
| B1 | HyperFrames for drawn shots |
| B3 | the builder's estimates for prices |
| B4 | Omni at 720p (review later) |
| B5 | the 5 % push-in on still pictures and AI-painted graphics |
| B7 | start picture only |
| B8 | Pexels |
| B9 | the suggestion after three rounds |
| B10 | camera copies left out |
| B11 | the analysis starts without asking |
| B12 | version 3 |
| C1 | no call to action |
| C3 | the 0.8 s pause |
| C5 | 15 s for deep analysis |
| C7 | high quality |
| C8 | one candidate |
| C9 | 2K |
| C10 | the server picks the model version |
| C12 | short still shots move |
| C13 | steady camera |
| C15 | diagram and cutaway |
| C17 | one reference round |
| C18 | no crop without a limit |
| C21 | trim or hold |
| C22 | shaky clips left alone |
| C23 | 1.35 times |
| C24 | today's sound levels |
| C25 | empty title |

## Build order

1. design/137 (category).
2. R4, R6, R9, R10 and R11: small and independent.
3. R5 and R14 (the brief).
4. R1 (shape and rate): the largest; it touches the analysis, the cut and visuals.
5. R2 (voices page).
6. R3, R12 and R13 (drawings and pictures).
7. R7 and R8 (instructions and the plan check).

Each step is tested before the next. One commit per step. One release at the end.

## Self-review (2 Nov, against the code and the answers)

1. **C14 location re-checked.** The table in design/138 cited `visuals_stage.py:3464`. The line is now `:3471`, and its wording is "Thirds by default, the centre only on purpose" (corrected above). The RULEBOOK tells the prompt never to write "centre" or "left third"; it governs prompt wording, not the framing choice, so they do not conflict.
2. **C11 is narrower than design/138 said.** The server already requires the kind; only the plugin fills it. R10 is plugin-only.
3. **C6 has a third 12-second clause.** The graphics-run warning (`visual_contract.py:_graphics_run`, over 8 s, with "above 12 s, give the reason") was not part of SK's C6 question. It is left as it is, and flagged here.
4. **A7 conflicts with the brief instruction.** It asks both languages "on every film" today. R5 removes the footage question and changes the narration question to one read from the script. Without this, the old question would come back.
5. **A1 timing** was raised as Q1 rather than built as worded, for the reason given there.
6. **Fonts on the drawn motion route** were only Noto Sans, and renders have no network. R13 would fail silently if the font were not a file, so the list is limited to files on the server (Q4).
7. **Old films** were checked against Supabase: four are open (VW-12, 13, 16, 17). Every R names what they keep, so nothing in flight breaks.
8. **No chosen-audition record exists on the voices page.** R2 now uses the voice's latest audition, shown before the narration starts.
9. **The analysis re-run** is `vw analysis --again` (checked in the plugin).
10. **One flow, two front ends.** Every new record (`vw shape`, `vw colours`, `vw font`) is a server step, so a page can call it later.

## Not covered

- Vertical films end to end. The cut, the editor's package and HyperFrames have never made one. The first one needs a short test film (R1).
- Square and 4:5 shapes, and vertical shorts cut from a horizontal film (parked by SK).
- A client's own font file uploaded (Q4).
- The live spending-limit value. It is read at deploy (R7).
- The Docker server suite (`server/tests`). As before, the unit tests and plugin tests run; the Docker suite does not.
