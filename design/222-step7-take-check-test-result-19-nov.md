# The test of section 9.7: Claude checking a take from frames, against Gemini watching it

19 Nov 2026. Run before the step 7 build, on SK's word ("Approved, test first"). No money was spent. The server and the database were only read; the temporary files on the VM are deleted. No product code was written.

**Page with the disagreements (private):** https://claude.ai/artifact/WaL36EQAXtzNPrVE5JXxft

## What was done, and by whom

1. **The frames** were made by a script of mine on the VM from the 17 original takes of VW-12, as section 9.1 says: one frame every half second, the first and the last, 960 px wide (9 to 19 frames a take), and the sheet at four frames a second made by the server's own code (`drawn.sheet`).
2. **Six Claude helpers** (Opus, fresh, two or three takes each) judged each take from those frames, the sheet and the start picture, on **the same lines Gemini 3.8 Flash had on 1 Nov** and with the same plan text. They were given no result of Gemini and no decision of SK, and were told to open nothing but their own takes' folders. The instructions they had: `frames-test\HOW.md`.
3. **The comparison** (`scripts\compare_test.py`) is line by line against Gemini's stored lines. The "camera drift" line is left out: the server measures it; neither checker reads it.

## The counts

| | |
|---|---|
| Lines compared, on 17 takes | **197** |
| Both passed | 150 |
| Both failed | 8 |
| Only Gemini failed | **6** |
| Only Claude failed | **33** |
| (a) Of Gemini's 14 failed lines, Claude also failed | **8** |
| Takes with at least one failed line: Gemini | 9 of 17 |
| Takes with at least one failed line: Claude | 14 of 17 |
| Lines Claude marked "frames are not enough to decide this" | 18 (almost all "surroundings move") |

Time and size: each helper took 2 to 4 minutes and about 50,000 tokens a take. For 19 takes that is about a million tokens of the operator's Claude plan, and under 10 minutes with helpers side by side.

## (c) The take SK rejected

"Housing construction at work, shot 1, take 1" (rejected by SK on 31 Oct with no words). Gemini passed it on every line. **Claude failed five lines, all from one fault: at 1.25 s the picture jumps to another view of another street** (the cement bags, the bamboo poles and the brick stack are gone; the wall and the far houses are different). I looked at the sheet myself: the jump is there, between 1.00 s and 1.25 s.

## (b) What Claude failed and Gemini passed (33 lines)

- **A jump to another view inside the take: 11 lines, 3 takes.** Shot 1 take 1 (above); shot 1 take 2 (the same jump, at about 1.25 s; Gemini failed this take on two other lines); "Daughter joins her parents at the step" (a jump from the wide view to a close view between 4.0 and 4.25 s; I looked at this sheet too: it is there; Gemini passed this take on every line and SK selected it). A take must be one continuous shot; this is the largest fault the test found, and Gemini did not see it in any of the three.
- **A thing or a person appears, vanishes or ends wrong: 10 lines.** For example: a second helper appears from nowhere at 2.0 s (shot 2 of the first gap); the trowel is gone from the mason's hand in the last frame ("Bricks laid flat"); the brick falls out of the press and the clip ends with empty plates ("Good bricks, shot 4"); the spray goes into the window hole instead of onto the wall ("Helper spraying the wall"). Not verified by me one by one: they are on the page for SK.
- **The camera or the background moved: 7 lines.** Claude read it from how fixed things shift between frames. The server's own measurement had already marked two of these takes.
- **The light, and whether the surroundings move: 5 lines.** The weak group. Three are "no leaf is seen to stir", which stills cannot show (the helpers said so themselves). Two are a literal reading of the light against the plan, where the start picture already had that light: not a fault of the take.

## What only Gemini failed (6 lines)

1. "Same tools": the broom disappears ("Preparing the plinth"). Claude failed the same fault under three other lines of that take. Not a miss.
2. and 3. "Good bricks, shot 1": the planned end and the background, because the camera tracks. The plan asks for a glide along the wall; Claude passed both for that reason. Probably Gemini's error; SK decides on the page.
4. "Where bricks come from, shot 3": the tractor's parts distort as they come near. **Claude saw only growth, no change of shape.** This is the kind of fault I expected frames to miss.
5. "Mason pointing the joints": mortar smeared on the brick faces instead of a clean joint. Claude passed it and marked that frames were not enough.
6. "Where bricks come from, shot 1": the pan ends on the head, not in the hand. A different reading of the same picture.

So of Gemini's 14 failed lines: 8 found, 1 found under other lines, 2 probably not faults, **3 that Claude from frames did not see** (4, 5, 6).

## The result, plainly

- **On these 17 takes, Claude from frames is not worse than Gemini watching the video. On the faults that matter most it was better:** it found a jump to another view in three takes, a second person appearing, and tools and bricks that vanish, none of which Gemini marked. One of those takes is the only one SK rejected.
- **It is noisier.** It marked 14 of 17 takes against Gemini's 9. Some of its failed lines are weak (the light, the leaves) or literal. How many of the 33 SK agrees with is not known until he has looked at the page.
- **It missed three things Gemini saw:** a shape distorting in motion, a smear of mortar, and one reading of where a tool ends.
- **Limits of this test:** one run of each checker; VW-12's takes are of the older way and its lines are not the five lines of a guide take; I verified two of the three jumps on the sheets myself, not the other lines.

## My recommendation

1. **Keep the half second.** A quarter second is not needed: every fault that happened between two half-second frames (the jumps at 1.25 s and 4.25 s, the broom at 3.25 s) was found, because the helpers used the sheet at four a second to place it. A quarter second would double the pictures and the tokens for no fault this test missed.
2. **Keep the sheet at four a second as a required part of the check.** It did real work here.
3. **Add one measured line by the server: "one continuous shot".** A sudden change between two neighbouring frames (a jump to another view) is measured from the file, in the same place as the three measured lines of today. It is cheap, it does not depend on any checker, and it is the largest fault found. A take that fails it is marked on its line; it is not set aside (SK may still want it).
4. **Two small changes to what Claude is asked,** to cut the noise: what the start picture already shows is not a fault of the take (the two light lines); "the surroundings move" is not asked of frames (the guide take's five lines do not have it anyway).
5. **Not recommended now:** a second checker (Gemini kept beside Claude). It would catch the three misses, and it doubles what the operator must read. Decide after the first film made the new way.

If SK agrees, sections 9.1, 9.3 and 9.4 of `222-step7-build-requirements-19-nov.md` get points 3 and 4 (about 40 more lines of code and 4 more tests); nothing else in the approved list changes.

## Found while testing (not fixed, not verified)

- `guide_worker.take_checks` reads the frame rate with `float(ev.get('fps') or 24)`, and the stored value is the text "24/1". If that is what a guide take's file gives, the line raises, and the sheet and the "first frame and still" pair are never made for a guide take (the fault is caught and kept as `code_error`). No guide take has ever run, so this has never shown. The build should read it as a fraction.

## Files

- `frames-test\` : the frames of each take, `task.json` (what a helper was given), `answers\` (what each helper wrote), `compare.json` (every line, both verdicts).
- `scripts\s7_frames.py`, `scripts\prep_test.py`, `scripts\compare_test.py`, `scripts\build_test_page.py`.
- `take-check-test.html`, `test-media\` : the published page.
