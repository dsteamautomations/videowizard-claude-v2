# 174 — The mason atom written in Alibaba's own prompt formula (5 Nov 2026)

SK: take Alibaba's prompt formula (design/173 §3, from OpenArt's guide) and convert the toughest of the morning's three test scenes, the mason at the corner of a rat-trap bond wall (design/157's shot list: the helper walks in with the pan of bricks, sets it down by the pile, stacks the bricks; three angles; the pile always on the mason's left). The formula's shape: a one-line summary (subject, place, movement); every reference labelled "@ImageN is …"; numbered shots with time ranges and one clear thing each; the sound in three separate lines; on-screen words in quotes (none here); the length and the shape stated; "fixed shot" where the camera holds.

One choice of ours inside the formula: no count of identical bricks (design/165, 171: counts drift whatever the form); the pan is "full of red bricks" and "empty" at the end.

## The pictures, in the order they are attached (the tags follow this order)

| Tag | File | What it is |
|---|---|---|
| @Image1 | `rat_trap_site__sheet__3.png` | the place: a half-built rat-trap bond wall of red bricks on edge, on a site with red earth and trees (VW-18's set picture) |
| @Image2 | `ref-1-mason.jpg` | the mason, full length: about 45, moustache, faded sky-blue shirt with rolled sleeves, blue-and-white checked lungi to the knee, a white towel on the left shoulder, the trowel with the bright yellow handle in his right hand |
| @Image3 | `ref-2-helper.jpg` | the helper, full length: about 22, white sleeveless vest, dark green lungi, a cloth pad on his head, the steel pan of bricks on it |
| @Image4 | `ref-3-tools.jpg` | the trowel with the yellow handle, the shallow steel pan with red bricks, the heap of grey mortar on its square board |

## The prompt

```
A helper carries a steel pan of bricks to a mason laying a rat-trap bond wall on a building site in Tamil Nadu at midday, sets the pan down by the brick pile and stacks the bricks while the mason spreads mortar.

@Image1 is the place: the half-built rat-trap bond wall of red bricks on edge, the red earth, the trees behind. @Image2 is the mason: keep his face, moustache, sky-blue shirt, checked lungi, the towel on his shoulder and the trowel with the bright yellow handle exactly as in the picture. @Image3 is the helper: keep his face, white vest, green lungi and the cloth pad on his head exactly as in the picture. @Image4 shows the trowel with the yellow handle, the steel pan with red bricks and the mortar on its board: keep them exactly as in the picture.

In every shot the mason is at the wall on the right of the frame, facing the wall with his back to the camera, on the camera's side of the wall. The pile of red bricks is on the ground to the mason's left, so it is always left of him on screen. The mortar board is between the pile and the mason. The helper comes from the left. Only these two people.

Shot 1 [0-3.5s]: Handheld, low, behind the helper, following him. He walks away from the camera toward the mason with the steel pan full of red bricks on his head, both hands steadying it. Ahead of him the wall, the mason bent at the wall on the right with the yellow-handled trowel resting on the top course, the brick pile on the ground to the mason's left.

Shot 2 [3.5-6s]: Fixed shot, side-on, medium, camera low from the front right. The helper squats and lowers the pan to the ground next to the brick pile. On the right the mason scrapes mortar from the board with the yellow-handled trowel and spreads it along the top course of the wall.

Shot 3 [6-10s]: Fixed shot, close and low on the brick pile. The helper's hands lift bricks from the pan two at a time and set them on top of the pile, until the pan is empty; the pan stays on the ground in front of the pile. At the right edge of the frame the mason's trowel with the yellow handle works on the top of the wall. At the end the helper lifts the empty pan in both hands and rises.

No voice lines in the whole video.
Sound effects: the scrape of the trowel on the wall, bricks set down on bricks, an open building site around.
No background music.

Realistic documentary live action. 10 seconds, 16:9.
```

## For the CLI

The same prompt with `--images <place>,<mason>,<helper>,<tools>` in that order, `--duration 10 --ratio 16:9 --resolution 720P`, sound on (`--audio-output=true`) since the formula writes the sound into the prompt, or off for a silent take. Not run yet; the pictures and the prompt are in `174-assets/`.

## Result (run M1, 5 Nov night, via the CLI: 10 s, 16:9, 720P, sound on)

`174-assets/M1-mason-alibaba.strips.png`, every half second. 10.03 s, 1280×720, 30 fps, a sound track (site ambience, −22 dB mean).

| Asked | Got |
|---|---|
| Shot 1 [0–3.5 s], handheld behind the helper walking to the mason, pan on his head, the mason bent at the wall on the right, the pile to his left | **yes**: the helper from behind with the pan of bricks, the rat-trap wall with its cavities, the mason bent at it on the right with his back to us, the pile on the ground left of him |
| cut at 3.5 s | **yes** |
| Shot 2 [3.5–6 s], side-on medium, low from the front right; the helper squats and lowers the pan by the pile; the mason scrapes the board and spreads on the top course | the helper lowers the pan beside the pile, yes; the mason with the **yellow-handled** trowel at the top course, yes; the pile left of him, yes; **but the shot is frontal, not side-on, and the mason faces the camera** instead of keeping his back to it |
| cut at 6 s | **yes** |
| Shot 3 [6–10 s], close and low on the pile; bricks from the pan to the pile two at a time until the pan is empty; the trowel at the right edge; he lifts the empty pan and rises | the close low shot, the hands moving bricks from the pan to the pile, the yellow-handled trowel at the right edge, yes; he lifts the pan and rises at 9 s, yes; **but the pan still holds bricks when he lifts it** |
| Identity: the mason (blue shirt, towel, checked lungi), the helper (white vest, green lungi, pad) | **yes**, both, through all three shots |
| Only two people; the pile always left of the mason; the camera never crosses the wall | **yes**, all three; the left-to-right order (helper, pile, mason, wall) held in every shot, which is what failed in SK's own first attempt and what the cartoon was drawn to fix |
| Sound: no voice, site effects, no music | **yes**: ambience and work sounds, no speech, no music |

Verdict: Alibaba's formula gave the structure (three shots at their seconds, the references held, the fixed order held, the sound as written) from a short text with no cartoon and no staging video. Two misses of degree: the mason turns to face the camera in the middle shot, and the pan is not emptied: the first is a facing fault the staging video (design/172) fixes, the second is the inventory limit seen all day. Cost 30 credits.

## Not covered

- The place picture is VW-18's rat-trap site set, not the morning's scene (which had no place picture): a wall on edge, as SK named it, in place of the three-course plinth wall of the shot list.
