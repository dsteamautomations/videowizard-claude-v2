# 159 — The mason test, part 3: colour tags, human pace, a closing action; frames against video (5 Nov 2026)

SK's instructions after design/158: keep the frames path in play and fix it (show exactly what to do; tag the elements whose state changes, with colours rather than numbers, and tell the model the colours are a guide and never a colour to show; more frames where the action is quick); run the video path with the same tagged cartoon; make the cartoon video first and cut the frames from it; one run each, then decide.

## What changed in the cartoon (`159-assets/draw.py`, against design/157's)

- **Colour tags.** The six bricks in the pan are red, orange, blue, green, purple and cyan in the cartoon, and each keeps its colour when it lands on the pile. The wall and the old pile stay brick red. (`TAGS` in the code.)
- **Human pace and a closing action.** Three placements of a pair at 0.9 s each from 6.1 s; the pan is empty at 8.8 s; from 8.8 to 10 s the helper's hands take the empty pan, lift it, and he rises. No second of the shot is without a drawn action.
- **The mason's side.** A ground shadow under the mason's feet on the camera's side of the wall in shots 1 and 2.
- **The pan in view.** In shot 3 the pan sits between the helper and the pile, no longer hidden by his body.
- The mortar is a darker green-grey heap, the pan a brighter silver, so the two round things differ.

The cartoon was rendered first (10 s, 15 fps) and the frames were cut from it: fifteen, dense where the action is quick (3 in the walk, 4 in the squat, 8 in the placing and the closing). Both prompts (`159-assets/prompt-frames.txt`, `prompt-video.txt`) carry the same new paragraph: the colours identify the thing so its change of state can be followed, every brick in the output is the same red clay, a brick that has left the pan never returns; the same holds for any element with a colour or a mark. Both also state the counts (six in the pan, none after 8.8 s, six more on the pile), the closing action, and that the mason never goes behind the wall.

## Results (`159-assets/shot3-quarter-second.png`, `shots-1-and-2.png`)

| | CF: 15 frames + 3 photos (18 pictures, accepted) | CV: cartoon video + 3 photos |
|---|---|---|
| Cuts (cartoon: 3.5, 6.0) | 3.5, 5.96, **and 8.75** (an invented cut: the closing action became a new wider shot) | 3.46, 6.0 |
| Direction of the bricks in shot 3 | pan → pile; no reversal | pan → pile; no reversal |
| The pan empties | by 7.0 s, early; the hands keep placing bricks on the pile until 8.5 s with the pan already empty | gradually to 8.5 s, then the hands take the pan |
| The closing action (lift the empty pan, rise) | yes, but as a separate wide shot from 8.75 s | **yes, in the same shot, 9.0–9.75 s** |
| Colour tags in the output | **one brick on the pile shows a blue-purple tint at 8.0–9.5 s** | none; every brick red |
| The mason on the camera's side of the wall | shot 1 yes; **shot 2 behind the wall** | yes in all three shots |
| Brick counts across shots | about six on the head; the pile grows | about six on the head, six in the pan on the ground, the pile grows |
| Yellow handle | yes | yes |
| Wall height, deviations | taller than drawn | taller than drawn |
| Wall time, input tokens | 101 s, 20,720 (≈ ₹3) | 86 s, 62,025 (≈ ₹8) |

## What the pair says

1. **The three fixes work on the video path.** With the pace fixed and a closing action drawn, the video run has no filler, no reversal, no invented cut, no colour leak, and the mason stays on his side of the wall. Every problem SK found in design/158's video run is gone in this one.
2. **Colour tags carried the state in both runs** (no brick went back), and the rule sentence kept them out of the video run entirely. On the frames run one tagged brick leaked a tint: a still of a purple brick is a stronger instruction to a picture model than a frame of one in motion. If the frames path is used, tags should be hue shifts of brick red (lighter, darker, more orange) rather than blue and purple.
3. **Dense frames fixed the direction on the frames path** (eight frames across three seconds of placing), as SK predicted from the eyebrow case. They did not fix the rest: the closing frames read as a new camera, the pan emptied early, and the side-on shot 2 put the mason behind the wall again. A still cannot say that the camera did not cut, how fast the hands moved, or which side of a wall a man stands on when his legs are hidden.
4. **Cutting the frames from the cartoon video is the right order** (SK's suggestion); it costs nothing and makes the two paths comparable. But the pace lives in the cartoon on both paths; the video does not remove the need for the drawing rules on pace and closing actions, it only follows them better.

## Recommendation

Use **the video path** as the one method: the cartoon drawn to the rules (fixed world, colour tags on elements that change state, human pace from a reference-speed table, a closing action, distinct shapes for things in one frame), sent as the input video with the sets and a timecoded shot list that names counts and the state rule. Keep the frames path only as a fallback for a scene whose cartoon cannot be made (none yet). The build in design/155 phase 5 therefore includes the Files API upload after all (about a day).

The reference-speed table for the drawing rules, first entries: a brick set down 0.8–1.0 s; a pair lifted from a pan 0.5 s; a step 0.5–0.6 s; a squat 1.0 s; a head turn 0.6–0.8 s; a pan lifted and a man rising 1.2 s. Each a should line the check helper measures on the cartoon.

## Not covered

- One run per path on one scene; the comparison is consistent with design/158's two video runs and two frame runs, which makes five video and four frame runs in all on this scene, but no success rate.
- Brick counts were judged on quarter-second stills at 240 px, not counted frame by frame.
- Whether the API accepts more than eighteen pictures was not tested; eighteen was accepted.
