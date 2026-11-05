# 160 — The mason test, part 4: facing, tool contact, and video with or without dense frames (5 Nov 2026)

SK's two findings on design/159's video run: the mason faced the camera and turned to the wall in a split second at 1–2 s; at 4 s he threw the mortar at the foot of the wall, not on it. Cause (design/159 reply): the cartoon never showed which way the mason faced (a flat figure, no nose, no eyes, symmetrical) and never showed the trowel touching the wall or the mortar landing. SK agreed the conclusion: one method, the tagged cartoon video sent with the photographs and the timecoded prompt; dense frames of quick moments only as extra pictures if one test shows they help; the drawing rules written down.

## What changed in the cartoon (`160-assets/draw.py`)

- **Facing.** The mason is drawn from behind in every shot: the back of the head all hair, two ears, no face, feet pointing at the wall. The helper has a nose and an eye on the side he faces (right, towards the pile) in the side-on and the close shot.
- **Tool contact.** In shot 2 the trowel swings until its tip rests on the top course, and a strip of mortar appears on that course and stays. In shots 1 and 3 the trowel stays on the wall top with mortar already there.
- **Legible counts.** The six bricks in the pan are bigger and separated.
- Both crops widened so the contact point is inside the frame (it was just outside in the first draft; caught on the key stills).

Twelve frames were cut from this cartoon video at the quick moments (4.3, 4.7, 5.1, 5.5, 6.25, 6.75, 7.15, 7.65, 8.05, 8.55, 9.2, 9.8 s). Two runs: **DV** = cartoon video + 3 photographs + prompt (`160-assets/prompt-video.txt`); **DVF** = the same plus the twelve frames, with a paragraph saying they are frames of the same video and never add a cut (`prompt-video-plus-frames.txt`).

## Results (`160-assets/shots-1-and-2.png`, `shot-3.png`)

| | DV: video + photos | DVF: video + photos + 12 frames |
|---|---|---|
| Cuts (cartoon 3.5, 6.0) | 3.5, 5.96 | 3.5, 5.96 |
| The mason's facing | back to the camera, facing the wall, in all three shots; no turn | the same |
| The mortar | laid on the top course, the trowel tip on the wall; stays | the same |
| Shot 3 direction | pan → pile, no reversal | pan → pile, no reversal |
| The pan | empties by about 8.5 s; the hand takes the rim at 9.0–9.5 s | **empties by 7.0 s; the pan is lifted at 7.5 s, set down, lifted again at 9.5 s** |
| Colour leak | none | none |
| The mason's side of the wall | camera's side in all shots | camera's side in all shots |
| Invented cut | none | none |
| Wall time, input tokens | 85 s, 62,088 | 111 s, 75,446 |

## What it says

1. **Both of SK's findings are fixed by drawing them.** Facing and contact are drawing rules now, and the video carried both.
2. **The dense frames did not help and did some harm.** The two frames of the closing action (9.2 and 9.8 s) pulled the lift of the pan forward to 7.5 s, after which the model had time left and repeated it. A still of a moment is read as "do this", not "do this at this second"; the video already carries the second. Decision: **no extra frames on the video path.** The eyebrow case from the park (a half-second expression) is handled the thread's way instead: a longer, closer, continuous shot with a hold, drawn so in the cartoon.
3. **DV is the cleanest run of the nine on this scene.** Every rule in the list below has now been shown to matter by a failure before it and a pass after it.

## The drawing rules, as tested

| Rule | The failure that proved it | Design |
|---|---|---|
| One fixed world, every shot a crop of it | the pile changing sides (SK's earlier attempt) | 157 |
| A person shows a facing direction in every frame (nose, eyes, feet) | the mason's split-second turn | 160 |
| A tool that acts on something is drawn touching it; the result is drawn where it lands | mortar thrown at the foot of the wall | 160 |
| Every countable thing is legible at the size the model sees | five bricks for six; the tint | 159, 160 |
| Colour tags on elements that change state, with the state sentence in the prompt | bricks back in the pan | 158, 159 |
| The action fills the shot's seconds at a human pace; a closing action in the last second | the empty seconds: refilled pan, fumbling, invented cut | 158, 159 |
| Things in one frame do not share shape and colour | mortar in the pan | 158 |
| No body hides an object that matters; the contact point is inside the frame | the pan hidden; the trowel tip off-frame | 159, 160 |
| Check the key stills before sending | every round of fixes above | 157–160 |

Reference speeds for the pace rule (first entries): a brick set down 0.8–1.0 s; a pair lifted 0.5 s; a step 0.5–0.6 s; a squat 1.0 s; a head turn 0.6–0.8 s; a pan lifted and a man rising 1.2 s.

## Not covered

- One run per variant on one scene; nine runs on the scene in all (design/157–160).
- Judged on half-second stills at 240 px; SK has both videos.
- No footage on either side, no narration, no scene over 10 s.
