# 157 — The mason test: a cartoon drawn by Claude, frames to Omni (5 Nov 2026)

SK's brief, 5 Nov: nothing from other films; a scene with several small objects whose positions must hold; the helper walks in from a distance with the steel pan of bricks, sets it down and stacks the bricks on the pile by the mason; the mason holds the trowel, with a **yellow** handle to see whether a colour is carried from a reference picture; three angles (handheld behind the helper, a different angle as the pan goes down, a different angle as the bricks are stacked) that must not collide: in SK's earlier failed attempt the pile moved from the mason's left to his right between shots. Frames-only method (design/156), two runs, two generated characters.

## What was made

1. **Shot list** (`157-assets/shot-list.md`): three shots, 0–3.5 s, 3.5–6 s, 6–10 s, with a fixed left-to-right order in every shot: helper → brick pile → mortar board → mason → wall behind. The camera never crosses the wall.
2. **Reference pictures**, three, made with the run's image model `gemini-nano-banana-2.1` through the same `generateContent` call the server uses (`157-assets/gen_refs.py`, prompts `ref-*.txt`, 12–17 s each): the mason full length with the yellow-handled trowel; the helper full length with the pan of bricks on his head; a still life of the trowel, the pan with bricks and the mortar board (`157-assets/references.png`).
3. **The cartoon** (`157-assets/draw.py`): drawn with Pillow from one fixed world (2560×1440) that every shot crops with its own camera, so positions cannot flip between angles; handheld shake in shot 1 is a small sine on the crop. 150 frames at 15 fps, 1280×720, encoded with ffmpeg; one frame per second cut for the test (`157-assets/cartoon-one-frame-per-second.png`). Four rounds of fixes on the key stills before anything went out: the pan cut off at the top of shot 1, the mortar board hidden behind the mason, the mason out of frame in shot 3, the helper's arms reading as sticks. The check-before-sending list from the thread (design/154) found every one.
4. **The prompt** (`157-assets/prompt.txt`): the ten frames as a storyboard, the three photographs named by number, the fixed positions stated once ("the pile is always to the left of the mason on screen"), the three shots with seconds, a props line with counts.

Two runs, thirteen pictures each, 14,952 input tokens (≈ ₹2) on top of the take (≈ ₹90). 78 s each.

## Results (`157-assets/key-moments.png`: cartoon on top, M1 and M2 below, at 0.8, 2.6, 4.2, 5.6, 7.0 and 9.5 s)

| | M1 | M2 |
|---|---|---|
| Length, size, audio | 10.03 s, 720p, 24 fps, audio | same |
| Cuts found (cartoon: 3.5, 6.0) | 3.46, 6.0 | 3.42, 6.0 |
| Shot 1: behind the helper, walking in, pan on head, mason at the wall on the right, pile left of him | yes, with a gentle handheld move | yes |
| Shot 2: side-on, the helper squats, the pan goes down by the pile; the mason spreads mortar with the trowel | yes | yes |
| Shot 3: close on the pile, bricks from the pan to the pile two at a time; the trowel at the right edge | yes | yes |
| **The pile stays on the mason's left in all three angles** | **yes** | **yes** |
| Helper always left of the mason | yes | yes |
| Yellow handle on the trowel | yes, in shots 2 and 3 | yes, in shots 2 and 3 |
| The pan (steel, round, shallow), the mortar board with grey mortar, red bricks | all present, in the right places | all present |
| The two men match the photographs (blue shirt, checked lungi, towel; white vest, green lungi) | yes | yes |
| Only two people | yes | yes |
| Cartoon look leaked | no | no |
| Deviations | the wall is six to eight courses, not three; a few loose bricks lie on the ground in shot 1 beyond the pile | the wall taller than drawn; shot 2's angle is a three-quarter side view rather than front-right |

## What it says

- **A cartoon drawn by Claude, from a shot list, works the same way as SK's hand-steered one.** The cuts landed within 0.08 s of the drawing in both runs; every action and every object was where the cartoon put it.
- **The angle collision is fixed by the method itself.** Drawing every shot from one fixed world makes the left-to-right order a property of the drawing, not of the prompt. Both runs kept the pile on the mason's left through three angles, which is exactly what failed when words alone described the scene.
- **A colour on a reference picture carries into the take** (the yellow handle), through the storyboard frames, which also show it in yellow.
- **The objects survived**: pan, bricks, trowel, board, wall, all placed as drawn, in both runs, with no duplicates and no extra people. The props line with counts and the storyboard together did what the thread's F4 asked for.
- **Cost of the drawing**: about forty minutes of my time including four fix rounds, no paid call. That is the number design/155 phase 7 wanted measured; a figure library would cut it, since most of the forty minutes was drawing people and objects from scratch.
- **Deviations are of degree, not of position**: a taller wall, a slightly different side angle. Nothing the plan's check would call a blunder.

## Not covered

- Two runs on one scene; a success rate needs more.
- No footage on either side of the clip; no narration timing; no scene longer than 10 s.
- The reference pictures came straight from the image model with no round and no operator approval; in the real flow they would be a set (design/151).
- The outputs were sent to SK and stay in the scratchpad; not in the repository.
