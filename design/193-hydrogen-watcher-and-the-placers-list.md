# design/193: Gemini 4 Hydrogen watches every clip, fits by sentence, and the placer gets each piece's own lines

**Status:** built and **deployed on 14 Nov 2026** (server 0.98.0, plugin 0.84.0, minimum 0.84.0, main 980f805). See "Built" and "Deployed" at the end.

**From:** the tests of 13 and 14 Nov on VW-19 ([hydrogen-test-results.md](_work/hydrogen-test-results.md), [hydrogen-settings-test.md](_work/hydrogen-settings-test.md), [phase1-sentence-fit-results.md](_work/phase1-sentence-fit-results.md)) and the verdict agreed on 14 Nov: change the model and the list now; do not rebuild the placing around Gemini yet. Claude stays the one who chooses the clip.

## 1. The requirement, restated

Five changes to the analysis and options stages:

| # | Change | Today |
|---|---|---|
| R1 | Every clip is watched by **Gemini 4 Hydrogen** in the **look-again way**, at high thinking and high picture quality. | Gemini 3.8 Flash; plain way for clips of 15 seconds or less, look-again above |
| R2 | Gemini is given the script as its **sentences** and says, for each piece, which sentences it shows, how exactly (exact, partly, related), from which second to which, and what the sentence says that the piece does not show. No new field: the answer goes into the two text fields the form already has. | The script as paragraphs; a fit by paragraph |
| R3 | The placer's short list carries, for each piece, **its own description, its "does not show" line and its fit by sentence**. | One line about the whole clip, the same for every piece of that clip |
| R4 | A piece that Gemini marked only **"related"** to a sentence is never placed under it as a **direct match**. It may be placed as B-roll. | Not checked |
| R5 | **Two clips of the same subject with the camera moving in opposite directions are one choice:** use one of them in neighbouring shots, not both. | No rule across clips; a rule only inside one clip |

Not in this change, by the verdict: Gemini's answer deciding the placement; a new answer form; batch; cache work; lower thinking or picture quality; pauses suggested after the placement; one look at the whole film.

## 2. How each is done, smallest working change

**R1. The model and the way of watching**
- `server/procedures/v3.json`, analysis stage: `model` becomes `gemini-4-hydrogen`; `processing_mode` becomes `AGENTIC`. `agentic_over_seconds` is no longer read.
- The step's wording to the operator changes: one Gemini 4 Hydrogen request per clip, the look-again way. The assistant tells the operator the likely cost before the paid step: about 0.33 US dollars a clip (the test's average).
- Kept: a clip the look-again way is refused for is sent once more the plain way (design/183).

**R2. The fit by sentence**
- `analysis.build_request_clip_log`: the "beats" given to Gemini are the script's sentences, in order, numbered `BEAT_01` to `BEAT_NN`, split by the same function the narration uses, so the numbers agree with the sentences the options stage already lists (`BEAT_02.S1`).
- `clip_log/prompt.py`: one paragraph added, generic for every kind of film: each beat is one sentence; primary = shown exactly; secondary = shown in part or only suits; in the reasoning field one line per fitted sentence, starting with the sentence, its seconds and EXACT, PARTLY or RELATED; in the limits field, per fitted sentence, what is missing.
- The request records that its fit is by sentence, so every later step knows which kind of log it holds.

**R3. The placer's list**
- `stage2/package.py`: each row gains `what` (the piece's own description) and `sentence_fits` (read from the two text fields: sentence, seconds, match, missing). `beat_fit_limits` is already in the row.
- `stage2/package.scene_fits`: with a log by sentence, a piece fits a scene directly when it is exact or partly for a sentence of that scene, and is related when it is only related. The mapping from the sentence to the scene uses the sentence's words on the timeline.
- `plugin/scripts/vw.py`: the pieces files show, per piece, `what`, `does_not_show` and its fits for that scene's sentences. The clip's overview stays once per clip, under its own name. A related piece keeps its one short row.

**R4. Related is not direct**
- `stage2/validator.py`: a shot marked `direct` under a word of sentence S is refused when the piece's fit for S is only RELATED, or when the piece has no fit for S at all. The refusal names the shot, the sentence and what Gemini wrote is missing, and says: place it as B-roll, or choose another piece, or leave a blank.
- Applies only to a log by sentence. A cut built on an older log is checked as today.

**R5. The same subject, filmed there and back**
- Options instructions: one rule, generic. Two neighbouring shots do not show the same subject from two clips whose camera moves in opposite directions (a pan one way and back, a track in and out); such a pair is one choice.
- The second look's checklist gains the same line, because it is the step that sees pictures.
- The server does not enforce it: Gemini watches each clip alone and names things differently in each, so the server cannot tell reliably that two clips show the same subject. See "Not covered".

## 3. Unstated but expected

- **Films in progress keep working.** A run whose clips were analysed before this change keeps its paragraph logs; packaging and checking read the kind recorded in the log. Nothing is analysed again unless the operator asks.
- **The library.** A clip already in the client's library is not sent again (design/147). Its stored log is by paragraph of another film; it is offered as today.
- **Cost is said before it is spent.** The paid step is announced with the estimate, never asked (the standing rule).
- **The plugin's minimum version rises**, because the list's shape changes.
- **Old ways** (design/35): "Gemini 3.8 Flash for the analysis" and "the plain way for a clip of 15 seconds or less" are retired; "the fit by paragraph" is kept for logs made before this release; "one line about the whole clip on every piece" is retired.
- **The live keys must be allowed Gemini 4 Hydrogen.** Checked with one small paid request at the deployment.
- **Wording for every category.** The added paragraph and the two rules name no kind of film.

## 4. Edge cases

| Case | Handling |
|---|---|
| The script has one sentence, or one very long sentence | One beat; nothing special |
| A script with more than 99 sentences | Beat numbers get three digits; the instruction already takes the count from the list |
| The sentence split at analysis and the narration's sentences do not agree in number (a sentence ending the splitter and the voice read differently) | The package falls back to the paragraph mapping for that film, says so in its answer, and R4 is not applied |
| Gemini writes a fit line not in the form asked for (4 of 417 in the test) | That line is ignored and counted; the piece keeps its primary and secondary lists |
| Gemini names a sentence that does not exist | Ignored and counted |
| The seconds of a fit lie outside the piece | Ignored and counted (0 of 417 in the test) |
| A piece is primary for a sentence but has no EXACT line (2 in the test) | Treated as partly: usable as direct, shown with "no line given" |
| The look-again way is refused for a clip (the drone clip, every time) | Sent the plain way, as today; the log says so |
| A request stops before finishing (about 1 in 20 in the test) | As today: the job fails and is sent again by the existing retry; no half answer is kept |
| A clip of a few seconds | Watched the look-again way like any other (accepted down to 3.8 s in the test) |
| A very long clip (over 95 s) | Not tested. The request's time limit stays; a clip that times out fails and can be retried or excluded, as today |
| The answer is cut off at the output limit | As today: refused as incomplete |
| A film analysed half before and half after the deployment | Each clip's log says its kind; a film with both kinds is packaged by paragraph, and says so |
| The scenes are approved again after a change | The fits are worked out again from the logs, as today |
| A "related" piece placed as B-roll | Allowed |
| The operator's own choice in the review (keep) of a shot R4 would refuse | R4 checks the assistant's proposal, never the operator's answer |
| Many candidates for one sentence (67 to 105 in the test) | The list keeps the tool's existing split into parts; exact first, then partly, then related as short rows |

## 5. Failure modes

| Failure | What happens |
|---|---|
| The key is not allowed the model | The first clip is refused with the provider's reason (design/183); the stage stops with it; nothing is charged |
| Google refuses the form (the "invalid argument" seen when a field was added) | Not expected: no field is added. If it happens, the clip is set aside with the reason, as today |
| The fit lines cannot be read for a whole clip | The clip is offered with its primary and secondary lists only; counted in the package's answer |
| Cost higher than announced | The estimate is an average; the real token counts are in each job's record, as today |
| The rule R4 refuses a cut the assistant cannot fix | The refusal names the three ways out (B-roll, another piece, a blank); a blank always passes |

## 6. Tests first

Without the database, as `server/tests/check_*.py`, on the real functions:
- The request lists the sentences in order, and records that the fit is by sentence.
- Reading the fit lines: the forms seen in the test, a line not in the form, a sentence that does not exist, seconds outside the piece.
- A row carries the piece's own description, its "does not show" line and its fits.
- The scene fit from a sentence log; the fall-back when the sentence counts differ; a paragraph log packaged as today.
- R4: a related-only piece as direct is refused; as B-roll it passes; an older log is not checked.
- The settings: every clip is sent the look-again way; the fall-back to the plain way still happens on a refusal.
- The plugin's pieces file: the new lines per piece, the overview once per clip.

The server's own suite (`server/tests`) needs Docker; it is run if Docker is available at build time, and listed as not run otherwise.

One real check at the deployment: one short clip analysed on the live server with the live key.

## 7. Not covered

- **R5 is an instruction and a second-look item, not a server check.** Catching it reliably needs one look at all the clips together, which is a later change.
- **The exact seconds.** Gemini mostly gives the whole piece (344 of 417). The placer still chooses the seconds inside it. Unchanged.
- **Whether the new way places better.** Phase 1 judged it about level with today's on one film. The measure is the next real film's score from the operator's keep, reject and trim answers, against VW-19's 8 of 10.
- **Long clips and other kinds of film.** Tested on one short documentary-explainer; the two longest clips of the first test were not answered.
- **The cost of a large film.** Estimated from the average, not measured: about 30 US dollars for 90 clips.
- **Films in progress are not moved** to the new logs.

## 8. Built (14 Nov 2026, committed, not deployed; server 0.98.0, plugin 0.84.0, plugin minimum 0.84.0)

- **R1:** `procedures/v3.json` analysis: `gemini-4-hydrogen`, `processing_mode: AGENTIC`, `fit_unit: sentence`; the step's wording (`scripts/d193_wording_v3.py`).
- **R2:** `analysis.sentence_beats` and `build_request_clip_log` (the sentences as beats; the identity records `fit_unit` and the count); `clip_log/prompt.beat_rule` (rule 6 by sentence; the paragraph rule word for word as it was). No field added to the form.
- **R3:** `stage2/package.own_lines`, `fit_unit`, `scene_fits_by_sentence`; `stage2/stage.py` chooses by sentence or by paragraph; `plugin/scripts/vw.py` `pieces_by_scene` shows `what`, `fits` and, for a paragraph log, `does_not_show`.
- **Crowded scenes (found while building):** on VW-19 two scenes had over 100 direct pieces. The list now puts the pieces exact for a sentence of the scene first and in full, then ten more in full, and the rest as one short row each.
- **R4:** `stage2/validator.related_as_direct`, called where a scene's step names the shot that shows it.
- **R5:** rule 4 of the options instructions and item 4 of the second look (`plugin/agents/vw-scene-review.md`). Not a server check.
- **Old ways:** rows 51 to 54 of design/35.

**Checked**
- `server/tests/check_sentence_fit.py`: every row of sections 1 and 4 that the code decides, on the real functions; passes. `check_chat_card.py` and `check_shared_change.py` still pass; the guard tests pass (15).
- The new code run on the 46 real answers of the 14 Nov test (no cost): the script's 11 sentences and the narration's 11 agree word for word; 145 pieces, 421 fit lines read, 4 left out; every scene gets its pieces.
- The new rule R4 applied to VW-19's real cut: it would refuse three of its seven direct shots, under the opening, the "quality of the bricks" sentence and the closing. Deepa rejected the quality shot on 14 Nov and the operator rejected the closing shots on 11 Nov; the opening was kept by both. Under the rule the opening must be placed as B-roll, which is allowed.

**Not run**
- `server/tests` (needs Docker, not running on this computer). Three expectations in `test_analysis.py` and one in `test_voice_media.py` that named the old model were changed to the new one, unrun.
- No request was sent to the provider from the application's own code path; the request shape is the one the 14 Nov test sent.

**Not covered, beyond section 7**
- The list is still long for a common action: about 83,000 characters for VW-19's second scene against 29,000 today, in several part files.
- The plugin's instructions file (`plugin/commands/vw.md`) was not changed; the stage instructions carry the new wording.

## 9. Deployed

14 Nov 2026, on the user's word: server 0.98.0, plugin 0.84.0 (minimum 0.84.0), main 980f805. Server and workers restarted; no job was running. The live instructions (version 3) carry the new analysis settings and the two rules, read back from the live database. No live key test was made, by the user's decision. First real use: VW-23, whose analysis and first cut are redone for a comparison with its cut of 13 Nov (baseline: [vw23-baseline-before-193.md](_work/vw23-baseline-before-193.md)).
