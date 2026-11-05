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

## Not covered

- The place picture is VW-18's rat-trap site set, not the morning's scene (which had no place picture): a wall on edge, as SK named it, in place of the three-course plinth wall of the shot list.
- Not run; SK asked for the prompt and the pictures.
