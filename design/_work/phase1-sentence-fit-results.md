# Phase 1: Gemini 4 Hydrogen says which sentence each piece shows

14 Nov 2026. The test of the proposal in [analysis-options-improvement-proposal.md](analysis-options-improvement-proposal.md), after Deepa's decision: Gemini 4 Hydrogen, the look-again way for every clip, high thinking, high picture quality, no cache work, no batch.

Run by Claude's scripts outside the application (`model-test/sentences_vw19_hydrogen.py`, `phase1_vw19.py`, `ab_vw19.py`) on VW-19: 46 clips, 11 sentences, a finished cut. Nothing in the application, the server or any run was changed. Cost: 16.90 US dollars, 54 requests.

## In short

- **Gemini can answer the fine question.** Given the script as sentences, it named the sentences each piece shows and how exactly, for 134 of 142 allowed pieces, in the form asked.
- **It is strict, and that is the gain.** It calls a fit exact for only three of the eleven sentences (3, 8 and 9: the cavities, bricks laid on edge, the pattern of each course). For the opening, the quality sentence and the closing it offers footage only as "related". For four sentences it offers nothing usable, and those are the same four that today's cut left blank.
- **The cut built from its answers is about level with today's on this film.** Deepa judged the seven sentences with footage blind: the new cut better on 2, today's better on 3, the same on 2.
- **One weakness found:** the seconds it gives are mostly the whole piece, not the few seconds that show the sentence.
- **One limit found:** in the look-again way Google refuses our answer form with even one more field. The sentence fit had to go into fields the form already has.

## What "today's cut" and "the new cut" mean

| | Today's cut | The new cut |
|---|---|---|
| What it is | The real cut of VW-19, made in the application on 11 Nov | A cut made for this test on 14 Nov, outside the application |
| Who watched the clips | Gemini 3.8 Flash, as the application sends them: the plain way for clips of 15 seconds or less, the look-again way for longer ones | Gemini 4 Hydrogen, the look-again way for every clip, high thinking, high picture quality |
| What Gemini was asked | Describe each clip and say which paragraph of the script each piece fits (7 paragraphs) | The same, with the script as 11 sentences, and for each piece: which sentence, how exactly, what is missing |
| Who chose the clip for each sentence | Claude, the operator's assistant in the application (which Claude model was not checked) | Claude, a helper started from the master thread (Fable 5.2) |
| What Claude worked from | The application's short list: one line about the whole clip for every piece, with grades and timings | A list built from Gemini's answers: per sentence, the pieces ranked, each with its own description and its "does not show" line |
| The rules | The application's full instructions for the options stage | Six rules written for the test |
| Did Claude see the footage | No | No |
| Checks afterwards | The server's rule check with corrections; a second look by a Claude helper at still frames | None: one pass |
| What came out | The full file the server needs (frames, crops, markers) | A choice per sentence: which clip, which seconds |

Today's cut had the weaker watcher and the poorer list, but the full process. The new cut had the stronger watcher and the richer list, but a thin process with nothing checked. The score compares these two as they are; it does not show what the new input would do with the full process behind it.

## Test 1: today's score (the baseline)

From the operator's recorded answers on VW-19's finished cut.

| | Count |
|---|---|
| Footage shots placed | 10 |
| Kept as placed | 8 |
| Rejected | 2, both in the closing scene, note "use ai" |
| Alternatives offered for those two | 2, both rejected |
| Trimmed | 0 |
| Blanks left for AI video or graphics | 5 |

## Test 2: the sentence fit

**The request.** The server's own request, with two changes made in the test only: the script's paragraphs replaced by its 11 sentences, and one paragraph added that asks, for each piece: which sentences it shows, from which second to which, EXACT or PARTLY or RELATED, and what the sentence says that the seconds do not show.

**What happened on the way.**

| Try | Result |
|---|---|
| A new field in the form, as a list of rows | Refused by Google for all 46 clips, "invalid argument", in both ways of watching. Nothing was charged. |
| A new field as a list of text lines | Accepted the plain way, refused the look-again way. |
| No new field: the fit written into the form's two existing text fields (the fit's reasoning and its limits) | Accepted. This is what ran. |

So in the look-again way the form is at its size limit today. Any field we want to add needs another to be taken out.

**The run.**

| | |
|---|---|
| Clips answered | 46 of 46 |
| Watched the look-again way | 45; the drone clip was refused again and fell back to the plain way |
| Requests that failed and were sent again | 3 (2 stopped before finishing, 1 lost connection) |
| Cost per clip | 0.33 US dollars on average |
| Time per clip | about 2 minutes, 5 looks on average |
| The server's arrival check | All 46 answers kept; 145 pieces, none thrown out, one note |
| Allowed pieces | 142 (128 as they are, 14 with a crop) |

**How it answered.**

| | Count |
|---|---|
| Allowed pieces with at least one fit line | 134 of 142 |
| Fit lines in all | 417 |
| Lines not in the form asked for | 4 |
| EXACT | 59 |
| PARTLY | 281 |
| RELATED | 77 |
| Fit seconds lying outside the piece | 0 |

**Per sentence.**

| # | Sentence (short) | Spoken | EXACT | PARTLY | RELATED | Today's cut |
|---|---|---|---|---|---|---|
| 1 | Rat-trap bond is a simple, effective technique | 8.0 s | 0 | 1 | 24 | Footage, two shots |
| 2 | Unlike conventional brickwork, bricks go on edge | 6.6 s | 0 | 105 | 0 | A blank, then footage |
| 3 | This creates continuous hollow cavities | 3.8 s | 30 | 51 | 3 | Footage |
| 4 | Reduces brick use by nearly 25 %, saving cost | 7.4 s | 0 | 1 | 0 | Blank |
| 5 | Less heat enters; cooler indoors | 4.5 s | 0 | 4 | 14 | Blank |
| 6 | Success depends on the quality of the bricks | 5.0 s | 0 | 0 | 2 | Footage |
| 7 | Brick strength should match building height | 2.9 s | 0 | 0 | 0 | Blank |
| 8 | Bricks are then laid carefully on edge | 2.3 s | 26 | 31 | 10 | Footage |
| 9 | Each course forms a pattern with cavities | 6.0 s | 3 | 88 | 3 | Footage, two shots |
| 10 | Walls are cured for at least seven days | 4.7 s | 0 | 0 | 0 | Blank |
| 11 | The future lies in building wisely | 7.2 s | 0 | 0 | 21 | Footage, two shots (both rejected by the operator) |

Reading:
- **Sentence 2:** all 105 fits are "partly", and all for the same reason: no clip shows conventional brickwork with bricks laid flat. Gemini saw the gap that today's cut covered with a blank.
- **Sentences 4, 7, 10:** nothing, or one wall poster. These are today's blanks.
- **Sentence 11:** only "related". Today's cut placed two shots here as a direct match, and the operator rejected both.
- **Sentence 6:** only "related" (a row of bricks does not show quality). Today's cut called it a direct match, and the operator kept it.

**The weakness: the seconds are not narrow.**

| | Count |
|---|---|
| Fit lines whose seconds are the whole piece | 344 of 417 |
| EXACT lines whose seconds are the whole piece | 39 of 59 |
| EXACT lines more than twice as long as their sentence | 25 of 59 |

For a 3.8-second sentence Gemini often answers "25.0 to 43.2 seconds". It says which piece, not which few seconds. The placer still has to choose the seconds inside the piece, without seeing it.

## Test 3: is the fit steady?

Five clips were sent a second time; all five came back (three needed a second try).

| Clip | Pieces, run 1 and 2 | Sentences called EXACT, run 1 | Run 2 | Other fits in both runs | In one run only |
|---|---|---|---|---|---|
| C0088 | 5 and 4 | 8 | 8 | 4 | 2 |
| C0092 | 5 and 5 | 8 | 8 | 5 | 0 |
| C0102 | 3 and 3 | 8 | 8 | 3 | 3 |
| C0113 | 3 and 3 | none | none | 3 | 0 |
| C0114 | 4 and 3 | 3 | 3 | 3 | 1 |

The exact fit was the same in all five. The looser fits (partly, related) moved in three of the five. Five clips is a small number.

## Test 4: the richer list

- One list per sentence, the candidate pieces best first, each with its own description, its seconds, its match and what is missing: `model-test/out-vw19-phase1/list.md` and `list.json`.
- 417 candidate lines; about 46,000 characters with the top 12 shown per sentence.
- Sentences 2, 3, 8 and 9 have 67 to 105 candidates each. The list needs a cut-off or a ranking by more than match and grade.

## Test 5: Claude builds the cut from Gemini's answers

A fresh Claude helper that had not seen the footage or today's cut built the picture track from the list alone, under the film's rules (exact where it exists, a blank where nothing fits, no seconds used twice, different clips side by side).

| # | Today's cut | The new cut |
|---|---|---|
| 1 | C0089 1.0 to 5.2; C0104 65.1 to 69.1 | C0112 6.5 to 10.5 (related); C0089 14.5 to 18.5 (related) |
| 2 | Blank 3 s; C0102 0.6 to 4.2 | C0085 19.0 to 22.3 (partly); blank 3.3 s for conventional flat brickwork |
| 3 | C0131 0.6 to 4.6 | C0093 12.5 to 16.3 (exact) |
| 4 | Blank | Blank: a graphic of the brick count |
| 5 | Blank | Blank: a cross-section of the cavity wall |
| 6 | C0081 0.9 to 4.1 | C0081 1.0 to 6.0 (related): the same clip |
| 7 | Blank | Blank |
| 8 | C0091 16.0 to 18.2 | C0091 16.3 to 18.6 (exact): the same seconds |
| 9 | C0108 6.4 to 9.5; C0099 8.0 to 11.1 | C0104 49.5 to 52.5 (exact); C0105 1.6 to 4.6 (partly) |
| 10 | Blank | Blank |
| 11 | C0136 2.8 to 6.4; C0288 6.7 to 10.3 | C0134 4.0 to 7.6 (related); C0136 3.0 to 6.6 (related) |

- **Same choice on 2 sentences** (6 and 8), **the same blanks on 4** (4, 5, 7, 10), **different footage on 5** (1, 2, 3, 9, 11).
- The helper's own notes: clip C0104 was top-ranked for five sentences and it kept it for one; for sentence 9 it took one exact and one partly piece, because all three exact pieces were close-ups of the same clip; for sentence 4 the only candidate was a wall poster that prints "Saves 25 % in bricks", and it left a blank.
- **Not done:** the server's own rule check on this cut. The helper wrote a choice per sentence, not the full file the server checks (frames, crops, markers). So this compares the choices, not the whole options stage.

## Test 6 and 7: Deepa's judgement and the new score

Deepa watched the A and B files on 14 Nov without knowing which was which. The key was opened afterwards.

| # | Sentence (short) | Deepa's mark | Which that was |
|---|---|---|---|
| 1 | The opening | B is better | **The new cut** (C0112, then C0089) |
| 2 | Unlike conventional brickwork, bricks on edge | B is better | **Today's cut** (C0102) |
| 3 | Continuous hollow cavities | B is better | **The new cut** (C0093) |
| 6 | Quality of the bricks | The same clip in both; she likes neither: "there is nothing about quality" | Both wrong. Gemini had marked this clip "related" only and wrote "does not show brick testing or quality". Today's cut had called it a direct match. |
| 8 | Bricks laid carefully on edge | The same, and a good fit | Both right (the same seconds of C0091) |
| 9 | Each course forms a pattern | B is better | **Today's cut** (C0108, then C0099) |
| 11 | The closing | A is better. B shows the same building twice, the second time with the camera moving the other way | **Today's cut** is A (C0136, then the round pavilion C0288). The new cut is B (C0134, then C0136: two clips of the Takshashila building). |

**The score, seven sentences with footage:**

| | Sentences |
|---|---|
| The new cut better | 2 (sentences 1 and 3) |
| Today's cut better | 3 (sentences 2, 9 and 11) |
| The same and right | 1 (sentence 8) |
| The same and wrong | 1 (sentence 6) |

The four blanks are the same in both cuts.

**Reading, with care:**
- On this film the new way is not better than today's. It is about level: two better, three worse.
- Where Gemini's own mark was "exact" (sentences 3, 8 and one shot of 9) the picks were right twice and lost once. Where the helper built from "partly" or "related" pieces (1, 2, 9's second shot, 11), it won once and lost three times.
- Gemini's strictness was right on sentence 6: it said the clip does not show quality, and Deepa agrees. The helper used it anyway because the test's rules allowed a related piece under a general statement. Under a stricter rule both cuts would have a blank there.
- Seven sentences, one film, one judge. A difference of one sentence is not a result.

**Why the new cut put the same building twice under sentence 11.** Two causes, both in how the test was made, and one gap in the application:
1. **The helper was not given such a rule.** It worked from six rules written for this test. They say "do not use the same seconds twice" and "prefer different clips side by side". C0134 and C0136 are different clips, so it broke neither.
2. **Nothing in the list says the two clips are the same building.** Gemini watches each clip alone. It described C0134 as "tracking left to right along the finished two-storey building" and C0136 as "pulls backward from the Takshashila entrance porch". Both name the building, but no field says "this is the same subject as that clip, filmed the other way".
3. **In the application I found a rule only inside one clip:** two pieces of the same clip can be marked "mutually exclusive" (to avoid a zoom in and out), and the server checks that. I found no rule, in the instructions or the checks, for two different clips that film the same subject with the camera going there and back. If such a rule exists in the editors' own guide, it is not in the application as far as I searched. Today's cut avoided the fault here by taking the second shot from another building.

This is what the proposal's "one look at the whole film" (change E) is for: one pass over all the clips that says which clips are the same place or the same move filmed twice. Proposed as a new row for the fixes list: **two clips of the same subject with the camera moving in opposite directions are one choice; use one of them.**

## Pauses, now that the fit is by sentence

With the fit by sentence the arithmetic gives suggestions, where with paragraphs it gave none:

| Sentence | Its length | The moment that must not be cut | Pause suggested |
|---|---|---|---|
| 8, "Bricks are then laid carefully on edge" | 2.3 s | 2.6 to 3.0 s in eleven exact pieces | 0.3 to 0.7 s |
| 3, "This creates continuous hollow cavities" | 3.8 s | 4.8 s in one clip | 1.0 s |

All are inside the usual limit of 4 seconds.

## What phase 1 says about the proposal

| Part of the proposal | After phase 1 |
|---|---|
| Gemini says which sentence each piece shows | Works, and it is stricter than today's blind match. Supported. |
| From which second to which | Weak as asked: 344 of 417 answers give the whole piece. Needs a sharper question or a narrower piece. |
| Claude builds the cut from Gemini's answers and a richer list | Works on the choice per sentence. The list is long for the action sentences and needs a cut-off. |
| The form | At its limit in the look-again way: to add a field, one must go. |
| The operator's answers as a score | Counted. Baseline: 8 of 10 kept. Deepa's blind comparison: the new cut better on 2 sentences, today's on 3, level on 2. |

## Not known, not done

- Whether Gemini's descriptions are right: no fact was checked by a person in this phase.
- The full options stage with the new list (frames, crops, the server's rule check, the second look).
- Another kind of film. This is one short documentary-explainer.
- The drone clip is refused the look-again way every time; the cause is not known.
