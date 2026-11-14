# Phase 1: Gemini 4 Hydrogen says which sentence each piece shows

14 Nov 2026. The test of the proposal in [analysis-options-improvement-proposal.md](analysis-options-improvement-proposal.md), after Deepa's decision: Gemini 4 Hydrogen, the look-again way for every clip, high thinking, high picture quality, no cache work, no batch.

Run by Claude's scripts outside the application (`model-test/sentences_vw19_hydrogen.py`, `phase1_vw19.py`, `ab_vw19.py`) on VW-19: 46 clips, 11 sentences, a finished cut. Nothing in the application, the server or any run was changed. Cost: 16.64 US dollars, 53 requests.

## In short

- **Gemini can answer the fine question.** Given the script as sentences, it named the sentences each piece shows and how exactly, for 134 of 142 allowed pieces, in the form asked.
- **It is strict, and that is the gain.** It calls a fit exact for only three of the eleven sentences (3, 8 and 9: the cavities, bricks laid on edge, the pattern of each course). For the opening, the quality sentence and the closing it offers footage only as "related". For four sentences it offers nothing usable, and those are the same four that today's cut left blank.
- **The cut built from its answers differs from today's on 7 of 11 sentences**, and is honest about what each shot lacks. Which is better is for Deepa: the A and B files are ready.
- **One weakness found:** the seconds it gives are mostly the whole piece, not the few seconds that show the sentence.
- **One limit found:** in the look-again way Google refuses our answer form with even one more field. The sentence fit had to go into fields the form already has.

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

Five clips were sent a second time; four came back (one failed twice).

| Clip | Pieces, run 1 and 2 | Sentences called EXACT, run 1 | Run 2 | Other fits in both runs | In one run only |
|---|---|---|---|---|---|
| C0088 | 5 and 4 | 8 | 8 | 4 | 2 |
| C0092 | 5 and 5 | 8 | 8 | 5 | 0 |
| C0102 | 3 and 3 | 8 | 8 | 3 | 3 |
| C0113 | 3 and 3 | none | none | 3 | 0 |

The exact fit was the same in all four. The looser fits (partly, related) moved in two of the four. Four clips is a small number.

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

Ready, not done. For the seven sentences with footage on either side there are two short video files, A and B, drawn by lot:

- Files: `C:\Coworkspace\Review Videobuilder Tool\model-test\out-vw19-ab\` (`S01-A.mp4` to `S11-B.mp4`).
- The sheet to mark: [phase1-ab-sheet.md](phase1-ab-sheet.md).
- The key (which is today's and which is new): `key.json` in the same folder. Open it only after marking.

The new score is counted from those marks.

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
| The operator's answers as a score | The baseline is counted (8 of 10 kept). The comparison waits for Deepa's marks. |

## Not known, not done

- Whether the new picks are better: Deepa's marks.
- Whether Gemini's descriptions are right: no fact was checked by a person in this phase.
- The full options stage with the new list (frames, crops, the server's rule check, the second look).
- Another kind of film. This is one short documentary-explainer.
- The drone clip is refused the look-again way every time; the cause is not known.
