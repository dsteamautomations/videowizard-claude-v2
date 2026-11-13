# Gemini 4 Hydrogen test: what will be checked

13 Nov 2026. For Deepa's go. Nothing has been run. Nothing in the application, the server, the database or any run is changed by this test; it runs outside the application on copies.

Deepa's instruction (passed on by the builder thread, 13 Nov): no comparison with Gemini 3.8 Flash; go ahead with Gemini 4 Hydrogen; run all the videos through it; look at the values that come back; correct the mistakes found in the eight steps (the summary being passed, not the real description, and the similar ones); list the tests first, then start; change nothing; state the results in a document; afterwards go back to the eight-step file.

## The film and the request

- **Film:** VW-19, the short rat-trap bond explainer. Its 46 clips are on this computer, 3.8 to 95 seconds, 803 seconds in all. 28 are 15 seconds or less, 18 are longer.
- **Request:** the application's own analysis request, unchanged: the same instruction, the same form with 159 boxes, the same settings, the script as paragraphs. Only the model's name is Gemini 4 Hydrogen.
- **How the clips are watched:** as the application does today. Plain for the 28 short clips, look-again for the 18 longer ones.
- **"Correct the mistakes"** is done in the test's own working files, after the answers are back. No file of the application is edited.

## Part 1: does it work at all (eight-step file, steps 1 to 4)

| # | Check | How |
|---|---|---|
| T1 | Every clip gets an answer | Count answered, refused, cut off, retried, by way of watching. A refusal with the look-again way is noted (an earlier fault) |
| T2 | The answers pass the server's arrival check | The server's own check code is run on each answer, on this computer. Count pieces kept and thrown out, and every note it writes |
| T3 | Allowed or not | The server's own code gives each piece one of the five answers. Count them. Check the speaker boxes: head inside body, body not too wide |
| T4 | The short-clip question (F10) | Four clips of 3.8, 8.2, 13.0 and 16.8 seconds are also sent the other way. Is the look-again way accepted on a short clip, and is the answer better? Deepa judges the pairs |
| T5 | Time, tokens and cost | Per clip and in total, split by way of watching. Cost at Hydrogen's listed price |

## Part 2: the values that come back (steps 2 and 5)

| # | Check | How |
|---|---|---|
| T6 | Every one of the 159 fields | For each field: in how many pieces it is filled, empty, or plainly wrong in form. One table |
| T7 | The doubt and "does not show" lines | How many are empty where a fit is claimed |
| T8 | Pieces per clip | How many clips give more than one piece, and how different those pieces are |
| T9 | Truth, by a person | Six clips of different kinds. Deepa watches each and marks the main facts right or wrong: the action, counts, who speaks, what is not shown. No model judges |

## Part 3: the faults from the eight steps, corrected on paper

| # | Fault | The correction tried in the test | What is measured |
|---|---|---|---|
| T10 | F1, F2: one line about the whole clip for every piece | Build Claude's short list twice from Hydrogen's answers: as today, and with each piece's own description and "does not show" line | For how many pieces the two differ in meaning; whether each scene's file still fits the size limit; ten pieces side by side for Deepa's eye |
| T11 | F3, F9: fields written and read by nothing | List what Hydrogen wrote in the editor's notes, the spoken words, the best frame, the title zone, the graphics ideas, the defects | How often each holds something a later step could use, with examples |
| T12 | F4: the library is chosen and offered by clip | For each clip with several pieces, mark which pieces would be true in any film and which not | How many clips are mixed, so that marking the whole clip is wrong either way |
| T13 | F5: fit by paragraph | Not corrected in this run. The request stays as the application sends it | Only counted: how many paragraphs hold more than one sentence, so the fit cannot say which |
| T14 | F6: pauses before the footage | From Hydrogen's "moment that must not be cut away" and the recorded narration, work out where an action is longer than its sentence | How many pauses the arithmetic would suggest, their lengths, and how many pass the new limit of 7 seconds |

## What this test does not do

- It does not compare with Gemini 3.8 Flash.
- It does not test Gemini choosing the clip for each sentence, or the script cut into sentences. That needs a changed request. It can follow as a second run on a few clips, after these results.
- It does not test the scenes file or the form refusals (F7, F8). Those belong to Claude's work in the options stage, not to the analysis.
- It is one film of one kind. One run per clip.

## Cost and limit

- The one production request already run (19 seconds, look-again way) cost about 0.52 US dollars.
- The 18 longer clips, up to 95 seconds, are the cost. The 28 short clips, watched the plain way, should cost a few cents each.
- My estimate for the whole run: 10 to 25 US dollars. It is an estimate; the longest clips have not been tried.
- Proposed limit: 25 US dollars. The run stops when the limit is reached, and reports what was done.
- The four shortest-clip pairs (T4) run first, with their cost reported, before the rest.

## What Deepa gives

- Her go, and the limit.
- About one hour afterwards: six clips to watch (T9), four short pairs to judge (T4), ten pieces to look at (T10).

## What comes out

- `design/_work/hydrogen-test-results.md`: every check above with its result.
- The eight-step file, with each step's "What the test showed" table filled in.
- The answers themselves, kept in `model-test/out-vw19-hydrogen/`.
