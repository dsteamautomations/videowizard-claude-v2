# 164 — The mason test, part 7: twenty frames, no video (5 Nov 2026)

SK's test before commenting on design/163: the same cartoon (the no-cut one) cut into twenty frames at half-second steps, no video, the three photographs, a prompt that says to follow the elements found in the frames as they are and to infer the action between frames and carry it out at a human pace; the pan-to-pile description kept. One run (G20), 24 parts (23 pictures), 103 s, 26,626 input tokens.

## Results (`164-assets/sixteen-moments.png`, `prompt.txt`)

| What | Result |
|---|---|
| Cuts (cartoon: one, at 3.5; a push-in at 5.4–6.6) | 3.46 **and 5.42**: the push-in became a cut |
| The pan's bricks after the squat | present: the pan is on the ground full at 3.8–4.6 s, and still full when the close view begins at 5.4–6.0 s |
| Shot 3 action | the hands take bricks from the pan and set them on the pile; the pile grows; nothing goes back |
| The closing action | the pan is lifted at 9.2–9.9 s **with three or four bricks still in it** (as in design/163) |
| Text, numbers, labels | none in the output; every brick red |
| The mason | back to the camera, on the camera's side, trowel on the wall top |
| The wall | finished, tall |

## What it says, beside design/163 (the same cartoon as video plus thirteen frames)

- **Continuity held here too.** The frames carried the full pan into the placing. So the thing that kept the bricks was the cartoon having no cut between the squat and the placing, not the video as such: twenty frames half a second apart show the pan full in frame after frame, and the model follows that. The rule of design/163 stands either way.
- **The push-in became a cut.** With frames only, a change of framing between two stills reads as a cut (5.42 s); with the video it read as a camera move. That is the one thing the video gave that the frames did not, on this scene.
- **The pace failure is identical**: the model places a pair in about 1.2 s and the drawn lift at 9.2 s came while bricks remained. This is the cartoon's timing, and neither input fixes it; the drawing does (design/163 point 2).
- Cost and time: frames 26,626 input tokens and 103 s; video plus frames 76,892 and 110 s.

## Not covered

- One run; judged on stills; SK has the video and the counts are his to confirm.
