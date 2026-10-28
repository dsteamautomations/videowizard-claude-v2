# design/118 — VW-7's pictures: where the four failures come from (assessment, 28 Oct 2026)

SK's question, with four pictures: the footage frame of the brick plinth being swept, the approved material spec of the brick, the web reference of a rat-trap wall, and the generated picture of a man sweeping a concrete plinth. Four complaints: the references were not used; brick sizes are not uniform; the same passer-by, bicycle and water pot recur across scenes; a worker behind a wall looks cut at the waist. Read against VW-7's session on the server (plan version 8, 103 references, 56 generated pictures) and the code. No change made.

## 1. "The references were not used" — the plan asked for a concrete plinth

The sweeping picture is shot B06A_S1's start image (`09ae718a`). What went to the image model:

- Image 1 the YARD picture, Image 2 the mason's sheet, Image 3 the labourer's sheet, **Image 4 the PLINTH picture: "take its flat grey plinth top and its edge, nothing else"**.
- The layout line: "the grey plinth top runs across the frame at knee height".
- The plan's PLINTH element: *"Flat grey stone or concrete plinth top, about knee height"*, identity representative, size unknown ("no plinth is shown clearly enough to measure; `vw visuals measure` has not been run").

The footage frame of the brick plinth was never approved as a frame for PLINTH. The approved frames of the run are LEVEL, MORTAR_PAN, RTB_WALL (the title wall), BROOM ("broom_sweeping", the same frame, approved for the broom only), TROWEL and POINT_TROWEL. The web reference of the rat-trap wall belongs to RTB_WALL; it was used, as design/111 F11 says, to make the RTB_WALL sheet, and the RTB_WALL golden picture is Image 1 of every wall shot. B06A_S1 does not name RTB_WALL among its elements.

So the model did what it was told: a grey concrete plinth, swept. The references for this picture were passed correctly for the plan it had; the plan was wrong about the plinth. The system did notice: the check failed six must lines on it (fact F_PLINTH, fact F_SITE, person kept, inventory, the mason's start state, faces) and the picture is rejected.

**Where the rule is missing.** The fact F_PLINTH cites "broom observed in footage f9c75", and the element's size entry says the footage shows the plinth, yet the element carries no footage frame and is "representative". A client's own thing that the footage shows should be `identity: exact` with an approved frame as its identity (RTB_WALL has exactly that). The server can say so: an element whose fact or size cites a footage frame, with no approved frame of its own, is warned at the plan and refused a picture at the References step until a frame is approved for it. Today nothing checks that the plan's words about a thing agree with the footage of that thing.

## 2. Brick sizes not uniform — the spec went out in words and as the brick picture, and the model still drew them wrong

**Correction (28 Oct, later the same day):** the count below of "two prompts in fifty-six" was wrong; it came from a truncated read of the stored prompts. Read in full, every brick-showing shot that was rejected for brick size (B02A_S1, B05A_S2, B05B_S3, B07B_S2, B07B_S3, B09B_S1) carried the material spec sentence and, in most, the brick's golden picture as an image, and the material check line failed on each. The fault is not that the spec was left out; it is that words and one picture do not make the model hold a unit's proportions across a scene. The paragraph below stands corrected by this note; the rest of the section's conclusions hold.

The material spec of the brick (230 × 110 × 75, laid on edge, the pattern) is approved. Design/111 F10 adds its sentence to a prompt and a must line to the check for every picture that shows a repeating material. In the stored prompts the sentence appears in two of the fifty-six pictures (the brick's own picture and the truck shot); the `material: Burnt clay brick` check line ran on seven, and **failed on all seven**, and four of those seven pictures were approved with that line failed (B04_S1, B04_S4, B05A_S1 and the brick's own isolated picture). So three things:

- Most brick-showing prompts went out without the spec sentence (older plan versions before BRICK was listed among the shot's elements, or shots that show bricks through RTB_WALL only, which has no material spec of its own: the wall's bricks are described as a pattern, not as units). Either way the model was rarely told the unit's proportions.
- Where the check did measure, it caught the fault every time. The approvals went past it.
- Under all of it: the image model does not count or measure. Repeated identical units are its weakest subject; a sentence helps a little, a reference picture of the bond at the right scale helps more, and the drawn route (design/117) is the only place the count is exact.

What would change it: RTB_WALL carries the brick's material spec too (a wall of bricks is the repeating material); a wall's reference picture is cropped to show three or four courses large, as Image k, with the line "take the unit size and the bond from it"; and an approval over a failed material line asks the operator the design/110 question first, as a failed keyframe line does.

## 3. The same bicycle, water pot and passer-by — copied from the VILLAGE picture

The VILLAGE picture (`49b71989`, approved) has in its Details: *"a parked bicycle and a clay water pot at the edge of the lane"*. It is Image 3 or 4 of the home shots (B04_S6, B05B_S9, B05B_S11, B03A_S1) with the line "take its style of home, its trees and morning air, nothing else; do not copy its layout". The model took the bicycle and the pot along with the style. The repeated person is the LABOURER: one element, one sheet, deliberately the same man, in each scene's outfit (the plan gives three different outfits across scenes, so he is not always in the same clothes, but he is always the same man at a distance).

SK's proposal is the right shape and cheap: the server knows what each approved picture put in its Details (the prompt is stored), so when a picture is a parent for its style only, the prompt gets the line *"Image k also shows a bicycle and a clay water pot: show neither"*, drawn from that parent's own Details sentence. For passers-by: a background person who only passes should not be a named element with a sheet; the plan names them in words per scene ("a woman with a basket", "two boys on one cycle"), different in each, and the "no two alike" constraint the VILLAGE sheet already carries for houses applies to them.

## 4. The worker cut at the waist — the plinth's height is unknown and the camera is at eye level

Two things meet here.

- Every "waist-high wall" layout puts the mason behind the wall with an eye-level camera. A waist-high wall in front of a standing man hides him to the waist; the model is geometrically right, and the plan's framing is what makes him look legless. That is a planning choice: a three-quarter view, a slightly higher camera, or the man in front of the wall shows the ground he stands on.
- In the sweeping picture the plinth was planned "knee height" and drawn waist height. The PLINTH's size is *unknown* in the plan, so no `real size` line was asked of the check (that line is added only for elements with a size), and nothing anchored the plinth to the man. Design/105's measure tool exists to take the plinth's height from the footage frame; the plan says it was not run.

What would change it: a height word in a layout ("knee height", "waist height", "chest height") becomes a must line, "the wall reaches the person's knee, the rest of the person above it", and a prompt sentence saying where the person stands against it; a thing with an unknown size that the footage shows is measured before its first picture, not left unknown.

## 5. In one sentence each

1. The plinth picture matched a wrong plan, not a missing reference; the check caught it; the gap is that nothing ties an element's words to the footage of it.
2. The brick spec reached two prompts in fifty-six, failed the check whenever it ran, and was approved past it four times; the model cannot count bricks, so the spec must ride on the wall element and its reference crop, and the hold must bite.
3. The bicycle and pot are copied from the VILLAGE picture; the fix is a line naming the parent's own props as excluded, built from the stored prompt.
4. The waist cut is the plan's eye-level framing behind a waist-high wall, plus an unmeasured plinth; a height-word line and the measure tool close it.

Nothing here is a hotfix for Revathi's current step; each is a rule for the next plan revision or a small server change. If SK wants them built, the requirements note is design/119, with the four changes above and the questions they raise (the identity rule for footage things; the material spec on the wall; the "also shows" line; the height-word line and the measure before the first picture).
