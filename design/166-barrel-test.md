# 166 — The barrel test: large identical objects, five of them, with and without a visible difference (5 Nov 2026)

SK's test after design/165: instead of bricks, five water barrels on a plank over the rear carrier of a bicycle; the worker wheels it in, stops by two barrels already on the ground, and sets the five down beside them in a row, never stacked. Five is more than the two or three that held; the barrels are much larger than bricks. If the count holds, size matters. Two variants from one cartoon (`166-assets/tests4.py` t6, 24 fps, 10 s): **t6a** all seven barrels the same blue; **t6b** the five on the bicycle new blue, the two on the ground old white, which is what "a difference the film is allowed to show" means: a difference a viewer accepts as real, not a tag that must vanish. Both runs: video plus fourteen dense frames plus the helper's photograph only. Prompts `166-assets/prompt-t6a.txt`, `prompt-t6b.txt`.

## Results (`166-assets/review-t6a.png`, `review-t6b.png`, every half second at 480 px)

| | t6a all blue | t6b blue onto white |
|---|---|---|
| Cuts (cartoon: one at 3.5) | **none**: the model kept one framing through the cut | none |
| The arrival | the bicycle wheels in from the left with barrels on the plank; two barrels on the ground at right | the same, five blue clearly on the plank, two white on the ground |
| The unloading | one barrel at a time from the plank to the ground beside the two, never stacked; about four set down by 9.75 s | one at a time, never stacked; four blue set down by 9.75 s |
| The plank at the end | **still three or four on it** | two left |
| The ground row at the end | about five, all blue; which were the original two cannot be told | **four blue beside two white**, the two kinds never confused |
| Total barrels | not conserved: the plank did not empty while the row grew | roughly conserved: five became four down and one or two left |
| Pace | one barrel per 1.5–2 s against the drawn 1.2 s | the same |
| Identity, facing, direction | the worker matches his photograph; faces right; barrels go plank to ground only | the same |

## What it says

1. **Size helps, and so does the number per move.** Five large barrels moved one at a time went the right way every time, with no barrel ever going back and none stacked. That is better than six bricks moved two at a time ever did. But the **running total still drifted** in the all-blue variant: the plank did not empty as the row grew. Large and identical is better than small and identical; it is not exact.
2. **A visible difference is the stronger lever** (SK's earlier doubt, now answered in his own test). With blue onto white the model kept the two kinds apart throughout and the total came out nearly right. Make the thing that moves look different from what it joins, in the film, and the model can keep the books.
3. **Pace, again.** The cartoon's 1.2 s a barrel was too fast; the model does about 1.6 s for a knee-high drum. The reference-speed table takes: a barrel lifted from waist height and set down, 1.6 s.
4. **The cut did not happen.** The cartoon cuts from a wide view to a closer one at 3.5 s; both runs held one framing and ignored it. The two framings were close in angle and the subject the same, so the model smoothed it. A cut needs a real change of angle or size to be read as one.
5. **Only the photograph of what is in the shot was sent**, and nothing extra appeared, unlike T5's trowel.

## Where the four size and count tests leave the rules (design/165 §2)

- Identical things: a handful moved one or two at a time is safe; a total that must be exact is not, at any size. Large objects drift less than small ones.
- A difference the film may show (new against old, a colour, a size) is the best way to keep a count honest, and it is cheap: it is a line in the plan's element description and a colour in the cartoon.
- The destination should not be a heap of the same kind; a row, a hand, a wall top, or a different-looking group.
- Cuts must change the angle or the size clearly, or the model will not cut.

## The control: the same two scenes as text only (SK's question: is the cartoon the cause?)

SK: check whether the cartoon is the reason, by giving the same activities as a plain prompt; are we asking it to follow too many things at once? Two runs, no cartoon, no frames, the worker's photograph and the scene text only (`166-assets/prompt-t6a-text.txt`, `prompt-t6b-text.txt`; sheets `review-t6at.png`, `review-t6bt.png`, the cartoon-guided run above the text-only run at every half second). 52 s each, 1,400 input tokens.

| | t6at all blue, text only | t6bt blue onto white, text only |
|---|---|---|
| Cuts | **3.5 s, as the text asked** (the cartoon-guided run had ignored it) | none |
| The arrival | the bicycle is already well inside the frame at 0.25 s; no walk-in from off-frame | the same |
| The unloading | one at a time, never stacked, never back; about four or five on the ground by the end | one at a time; three blue beside the two white by the end |
| The plank at the end | **three still on it** | **three still on it** |
| Total | not conserved, as with the cartoon | not conserved; one white barrel drifts towards blue around 6–9 s |
| Pace | one barrel per 1.5–2 s, as with the cartoon | the same |

**Answer: the cartoon is not the cause.** Without it the model fails the count in the same way: the plank does not empty while the row grows, the pace is its own, and in the two-kind variant a colour even drifts. The cartoon neither overloaded it nor fixed it. What the cartoon did add is visible in the sheets: the walk-in from off-frame at the right second, the stop in the middle, the framing of the two shots; the text-only runs start with the bicycle already in frame and place things where they like. So the division holds exactly as design/165 §1 says: the cartoon buys staging; the count is the model's own limit, cartoon or not.

One odd pair: the text alone produced the cut at 3.5 s and the cartoon-guided run did not. The cartoon's two framings were too alike (design/166 point 4); the text named a cut and got one. Where a cut matters, the prompt should name it and the cartoon should make it unmistakable.

## Not covered

- One run per variant; judged on half-second sheets; SK has both videos.
- The counts above are mine from stills at 480 px; the exact plank and row counts are SK's to confirm.
