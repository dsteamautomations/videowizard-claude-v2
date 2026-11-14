# Gemini 4 Hydrogen on VW-19's clips: results

14 Nov 2026. The test of [hydrogen-test-list.md](hydrogen-test-list.md). Run by Claude's scripts outside the application (`model-test/run_vw19_hydrogen.py`, `check_vw19_hydrogen.py`). Nothing in the application, the server, the database or any run was changed.

## In short

- **Hydrogen works with the application's request as it is.** 43 of 46 clips were answered. Every answer passed the server's own arrival check, with no piece thrown out and no note.
- **It costs about 10 cents for a short clip and about 36 cents for a longer one.** The 43 answered clips cost 8.11 US dollars; the whole test cost 9.16.
- **The look-again way works on short clips**, down to 3.8 seconds. It costs two to two-and-a-half times the plain way. Whether its answers are better needs a person's eye; the two ways disagree on some facts.
- **The fault "one line for the whole clip" is real and large.** 107 of 116 pieces sit in clips with several pieces, so the placer reads a line that describes another piece.
- **The script fit by paragraph cannot say which sentence.** All 106 direct fits land in two paragraphs of two sentences each.
- **Hydrogen fills the "does not show" line every time** a fit is claimed. It is written and not shown to the placer.
- **The colour-group label is useless for grouping:** 41 different labels for 43 clips.
- **The pause arithmetic suggests no pause** on this film.

What is not judged yet: whether Hydrogen's facts are right. That needs a person; the sheet is [hydrogen-test-for-your-eye.md](hydrogen-test-for-your-eye.md).

## How the test was made

| Point | What was done |
|---|---|
| Film | VW-19, the rat-trap bond explainer: 46 clips, 3.8 to 95 seconds |
| Request | Built by the server's own function (`analysis.build_request`) from VW-19's files, with the policy and settings VW-19's own jobs recorded. For two clips the instruction text and the answer form have the same fingerprints as VW-19's real jobs. Only the model name differs |
| Way of watching | As production: plain for clips of 15 seconds or less (28), look-again for longer ones (18) |
| Order | Shortest first, one request at a time (the test key file holds one key) |
| Spending limit | None (Deepa, 13 Nov) |
| Stopped | By Deepa's word on 14 Nov, with 43 clips answered |

## Part 1: does it work at all

### T1: every clip gets an answer

| | Count |
|---|---|
| Clips | 46 |
| Answered | 43 (28 plain, 15 look-again) |
| Not answered | 3: C0065 (25 s), C0122 (52 s), C0104 (95 s) |
| Answers that ended properly | 43 of 43 |

- **Two requests stopped before finishing** ("incomplete response"): C0139 (4.3 s, plain) and C0065 (25 s, look-again). C0139 succeeded when sent again. C0065 was not sent a third time.
- **Thirteen requests failed in a fraction of a second with a connection error** during the night. That is this computer losing its connection, not the model. They cost nothing; eleven succeeded when sent again, two were not sent again (C0122, C0104).
- **One refusal of the look-again way:** the drone clip (DJI, 21 s). The request fell back to the plain way, as the application does (design/183), and was answered. The whole request took 1,033 seconds. This is the same kind of refusal as defect 48, now seen on Hydrogen.
- **Not learnt:** how Hydrogen copes with the two longest clips (52 and 95 seconds).

### T2: the server's arrival check

| | Count |
|---|---|
| Answers kept | 43 of 43 |
| Pieces kept | 116 |
| Pieces thrown out | 0 |
| Notes written by the check | 0 |

The check is the server's own code (`clip_log.gate.review`), run on this computer.

### T3: allowed or not

| The server's answer for a piece | Pieces |
|---|---|
| Allowed as it is | 105 |
| Allowed with a crop | 2 |
| Picture refused, sound kept for context | 5 |
| Refused | 4 |

No note about the speaker boxes (head inside body, body too wide) was written.

### T4: short clips, both ways (fault F10)

| Clip | Length | Plain: cost, time, pieces | Look-again: cost, time, looks, pieces |
|---|---|---|---|
| C0032 | 3.8 s | 0.08 USD, 59 s, 1 | 0.19 USD, 78 s, 3 looks, 1 |
| C0114 | 8.2 s | 0.09 USD, 64 s, 2 | 0.20 USD, 102 s, 2 looks, 3 |
| C0113 | 13.0 s | 0.14 USD, 89 s, 3 | 0.34 USD, 140 s, 6 looks, 4 |
| C0134 | 16.8 s | 0.11 USD, 108 s, 3 | 0.25 USD, 105 s, 5 looks, 3 |

- **The look-again way is accepted on a short clip.** No refusal on any of the four. There is no minimum length on Hydrogen's side down to 3.8 seconds.
- **It costs 2.1 to 2.4 times the plain way.** It reads 20 to 50 thousand video tokens where the plain way reads 1 to 5 thousand.
- **It gives one more piece on two of the four clips**, with tighter boundaries.
- **The two ways disagree on facts.** On C0032 the plain way sees "a wooden batten" and "a scaffolding pole"; the look-again way sees "a ceiling fan blade" and "a conduit pipe". On C0134 they disagree on the direction the camera moves. One of them is wrong each time; which, only a person can say (Part A of the sheet).
- **So the 15-second limit stays a cost choice, not a need.** Whether to lower it depends on which way is right on the facts.

### T5: time, tokens and cost

| | Plain way (28 clips) | Look-again way (15 clips) |
|---|---|---|
| Cost in all | 2.77 USD | 5.34 USD |
| Cost per clip | 0.10 USD (highest 0.17) | 0.36 USD (highest 0.49) |
| Cost per second of clip | 0.012 USD | 0.013 USD |
| Time per clip | 64 s (longest 107 s) | 206 s (longest 1,033 s, the drone clip) |
| Looks per clip | 0 | 5 |
| Tokens read | 368,552, of which video 68,372 | 1,787,181, of which video 1,144,512 |
| Tokens written | 166,580 | 172,051 |
| Thinking tokens | 128,768 | 182,513 |

- **The whole test:** 62 requests, 9.16 US dollars, at Hydrogen's listed price (1.50 dollars per million tokens read, 7.50 per million written or thought).
- **For a short clip the cost is the answer, not the video.** The plain way reads about 1,200 to 5,000 video tokens and writes and thinks about 10,000.
- **Estimate for a film like VW-23 (94 clips):** about 15 to 25 US dollars, if its clips are like these. Not measured.
- **Time:** one request at a time, the 43 clips took about 80 minutes of model time. The application sends 15 at once.

## Part 2: the values that come back

### T6: every field

- The answers hold **176 field names** (counting the fields inside each piece and each clip).
- **146 are filled every time.** None is empty every time.
- **30 are sometimes empty**, almost all rightly so: they are lists or blocks that apply only when something is there.

| Field | Filled | Empty | Reading |
|---|---|---|---|
| Risk flags | 2 | 114 | Rightly empty: nothing risky |
| Text on screen | 14 | 102 | Rightly empty |
| Defects | 16 | 100 | Rightly empty |
| Speaker crop block | 20 | 96 | Only when a speaker is seen |
| Spoken words block | 33 | 83 | Only when speech is heard |
| Camera moves | 41 | 75 | A still camera has none |
| Clean sound stretches | 59 | 57 | |
| The moment that must not be cut | 68 | 48 | Null for a still scene, as the instruction allows |
| Direct fit to a paragraph | 69 | 47 | 47 pieces fit nothing directly |
| Camera doubt line | 79 | 37 | Allowed empty when nothing is in doubt |
| "What is inferred, not seen" line of the action | 106 | 10 | |
| The piece's own doubt line | 114 | 2 | |

- **No field was wrong in form.** The server's check found nothing to refuse.
- The full table is in `model-test/out-vw19-hydrogen/checks.json` under `T6.table`.

### T7: the doubt and "does not show" lines

| | Count |
|---|---|
| Pieces | 116 |
| Pieces with a fit to the script | 112 |
| Fit claimed, "does not show" empty | **0** |
| Direct fit claimed, "does not show" empty | **0** of 69 |
| Fit said to be seen directly | 76 |
| Fit said to be illustrative | 36 |

Hydrogen writes what the piece does not show every time it claims a fit.

### T8: pieces per clip

| Pieces in a clip | Clips |
|---|---|
| 1 | 9 |
| 2 | 13 |
| 3 | 10 |
| 4 | 5 |
| 5 | 5 |
| 6 | 1 |

- **34 of 43 clips give more than one piece.** 116 pieces in all.
- **In 13 of those 34 clips the pieces overlap in time.** In 10, one piece covers nearly the whole clip beside its shorter pieces. The placer could pick the same seconds twice under two names.

### T9: truth, by a person

Not done. Six clips are ready in Part B of the sheet: a short clip, an action in several pieces, speech, a risk flag, the longest answered clip, and the drone clip.

## Part 3: the faults from the eight steps, corrected on paper

### T10: one line about the whole clip for every piece (faults F1, F2)

| | |
|---|---|
| Pieces in clips with several pieces | **107 of 116** |
| Size of the short list today | 55,646 characters |
| Added by each piece's own description and "does not show" line | 43,812 characters |
| Growth | **79 %** |

Three examples from the answers:

| Clip, seconds | Today the placer reads | The piece's own description | Does not show |
|---|---|---|---|
| C0085, 0.0 to 1.2 | A mason packing wet mortar with a trowel into the joints of bricks laid on edge | A metal pan pours wet mortar onto the bricks, then is lifted out of the frame | Bricks being placed, or cavities inside the wall |
| C0085, 26.0 to 26.9 | The same line | The camera bumps and tilts up, blurring the frame and showing the mason's lower face | "Technical camera bump tail; unusable for any script beat" |
| C0088, 6.0 to 12.0 | A mason laying four bricks on edge while a helper brings water and bricks | The mason places the second brick and aligns both with two hands while a helper walks past | The hollow cavity is not clearly seen from this angle |

- **The second example shows the fault at its worst:** a piece the model itself calls unusable is listed to the placer as a mason packing mortar.
- **The size limit:** the list grows by about four fifths. The tool already splits a scene's file into parts when it is too long (VW-19's fifth scene is in two parts today), so it will be more parts, not a failure. Not run through the tool.

### T11: written and read by nothing (faults F3, F9)

| Field | What Hydrogen wrote | Use |
|---|---|---|
| Notes for the editor | 130 lines over all 43 clips | High. Examples: "do not cut directly between non-adjacent sub-clips without a cutaway"; "the cleanest hero slice is 1.0 to 7.5 s, before the foot appears"; "the speech-to-text line is a false positive from trowel scraping" |
| Spoken words | 33 pieces, 14 stated facts | Low on this film: mostly unintelligible off-camera remarks |
| Best frame | 116 of 116 pieces | Ready to use as the piece's picture |
| Zone for a title | 106 of 116 pieces | Ready for the visuals stage |
| Graphics ideas | 117 | Mixed: labels and call-outs, some slow-motion advice |
| Defects | 17 in 16 pieces (5 camera bumps, 1 focus hunt, 11 other) | High: a bump inside a piece should rule the piece out or trim it |
| Colour-group label | **41 different labels for 43 clips** | None as written: almost every clip gets its own label, so nothing can be grouped by it |

### T12: the library is marked by clip (fault F4)

- 34 clips have several pieces. In **23 of them the pieces differ** in what they fit, their chapter, their role, or whether they are allowed.
- So marking the whole clip for the library is wrong one way or the other for about two thirds of the clips with several pieces.
- **Limit of this check:** it counts differences by the model's own fields. Which pieces are true in any film needs a person; that was not done.

### T13: fit by paragraph (fault F5)

| | |
|---|---|
| Paragraphs | 7 |
| Paragraphs with more than one sentence | 4 |
| Sentences | 11 |
| Direct fits | 106, all into paragraph 2 (47) or paragraph 5 (59) |
| Direct fits into a paragraph of several sentences | **106 of 106** |

Every direct fit on this film points at a paragraph with two sentences, so the fit never says which sentence the piece shows. Not corrected in this run: the request stayed as the application sends it.

### T14: pauses after the footage is read (fault F6)

- Hydrogen marked "the moment that must not be cut away" on 68 pieces. The moments are 1.0 to 4.5 seconds long; most are 2 to 3.
- The longest sentence in each paragraph is 4.7 to 8.0 seconds.
- **No piece's moment outlasts the sentences of the paragraph it fits. The arithmetic suggests no pause on this film.**
- **Limit of this check:** it compares with the longest sentence of the paragraph, because the fit is by paragraph. With a fit by sentence, a 3-second moment under a 2.3-second sentence (paragraph 5 has one) could ask for a short pause. That cannot be told from these answers.

## What the test did not do

- It did not compare with Gemini 3.8 Flash.
- It did not test Hydrogen choosing the clip for each sentence, or the script cut into sentences.
- It did not test the scenes file or the form refusals (F7, F8).
- No fact in any answer has been checked by a person yet.
- The two longest clips were not answered.
- One film of one kind; one run per clip.

## Faults found in the test itself

- **The earlier cost guess was wrong.** A short clip costs about 10 cents, not "a few cents".
- **The run was not finished in one go.** Thirteen requests failed overnight on a lost connection and had to be sent again.
- **My first field table was wrong** (it called 13 fields "always empty" that are often filled). Corrected before this document; the figures above are from the corrected count.

## Files

- Answers, requests, the spending record and the checks: `model-test/out-vw19-hydrogen/` (`ledger.json`, `checks.json`).
- The sheet for a person: [hydrogen-test-for-your-eye.md](hydrogen-test-for-your-eye.md).
- The eight steps, filled in: [analysis-and-options-in-eight-steps.md](analysis-and-options-in-eight-steps.md).
