# design/150: the treatment step's Set C (SK, 3 Nov 2026)

From the VW-18 review: two treatment refusals (direction over 2000 characters; `seconds` given as a list) and one judgement with no rule (the treatment named the round building at two gaps). SK asked on 3 Nov whether these were fixed; they were not (Sets A and B covered the plan step). Built the same day; deploys on hold.

## What the code showed
- The server refuses a Direction over 2000 characters (`visuals_stage.py`) and a `seconds` that is not one number; neither limit was in the treatment part. Worse, the text read "`seconds` (a video gap's segments with theirs)", which a writer reads as seconds per segment, the very shape the server refuses.
- A treatment entry has no clip field; footage is named in the prose of the `picture` line. So the one-clip rule cannot be a checker rule; it is the writer's.

## The three changes (text only, `scripts/d150_wording_v3.py`, chained in `c1_split_v3.py --check`)
- **C1.** "a few lines (at most 2000 characters)".
- **C2.** "`seconds`, one number, the gap's total (a video gap's segments carry theirs inside `shots`, never a list in `seconds`)".
- **C3.** "A footage clip, or a specific thing the footage shows (one building, one machine), is named at one gap only; a second gap that wants it says why in its line, or takes another."

## Also in this change: the B10 correction (SK)
An icon or an idea graphic (a benefit, a feature, a mood) stands for no real object: it has no sizes and no drawing spec, so B10's proposed sizes never touch it. This was already the rule (the checker asks for a spec only for a real object or a figure; the text calls icons a conceptual graphic). One clause added to the helper brief so the writer sees it beside B10; a figure an icon carries follows B6.

## Not built, a decision for SK
- **C4.** On a take-over, does the new laptop read the existing treatment draft first, or start fresh? VW-18: Person X's two accepted drafts were discarded.

## Tests
`server/unit/test_design150_pure.py` (3, on the text); the visuals word cap rises by the words added.

## Not covered
- Nothing in the server's behaviour changes; no database test.
- C3 depends on the writer: no check can read a clip out of a prose line.
