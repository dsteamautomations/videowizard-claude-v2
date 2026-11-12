---
name: guide
description: How VideoWizard makes an AI video shot: a scene description of plain boxes that the server's Blender turns into a guide video, a still made from the guide's first frame, the overlay, the take's words, and the take on the operator's word. Read it before any `vw guide` command, and when you are the vw-guide-scene or vw-guide-check helper.
---

# An AI video shot, made from a guide

An AI video shot is never made from words alone. The server renders a **guide**: a short video of plain coloured boxes that fixes where everything is and how it moves. A **still** is then made from the guide's first frame, and the video model turns the guide into footage that starts on that still. Positions, paths, speed and timing come from the guide; the look comes from the still; words carry only what neither can.

You write data and words. You never run Blender, never call a picture or video model yourself, and never send a request the server refused in another form.

## The order, and who does what

| Step | Command | Paid? |
|---|---|---|
| 1. Scene description | a `vw-guide-scene` helper writes `work/guide/<shot>/scene.json`; `vw guide scene --shot S --file …` | free |
| 2. Check frames | `vw guide frames --shot S` (three frames and a strip arrive in `work/guide/<shot>/frames/`) | free |
| 3. The double check | a fresh `vw-guide-check` helper, who has not seen the build, writes `verdict.json`; `vw guide verdict --shot S --file …` | free |
| 4. The guide is rendered | by the server, after a passing verdict; `vw guide status --shot S` | free, several minutes |
| 5. The still | `vw guide still --shot S --file still.json`; then `vw guide look --shot S` | paid (one picture) |
| 6. The overlay | the operator looks at the overlay and approves the exact file, or it is repaired or rejected | free |
| 7. The take's words | `vw guide prompt --shot S --file take.txt` | free |
| 8. Shoot | only on the operator's word: `vw guide shoot --shot S --quote "<their words>"` | paid (one take) |
| 9. Review | `vw visuals status`; the take arrives with its scorecard; select or reject as for any take | free |

One helper builds one shot. The checker is always a different, fresh helper. After two failed rounds, show the operator what is still open before another round.

## Only three kinds of shot

`recipe` is one of:

- `walker`: one or two people walk, others stand or sit. Wide or medium.
- `one_action_close`: one person does one thing with the right hand, close.
- `transfer_close`: one thing is poured, picked up or handed over, close, and the shot ends before it is put down.

Anything else (a crowd crossing, a vehicle, a run, a door, night, people speaking, several cameras on one animation, a real place from a photo) is **not yet available**. Do not dress it up as one of the three: tell the operator, and plan the picture as footage, a still or a drawn shot.

## Before the scene: how the real thing works

Write `process_note` first, two to four lines: what moves, how far, how fast, in what order. If you cannot write it, you do not know the action well enough to build it: ask the operator.

## The scene description

Metres. X to the right, Y away from the camera's side, Z up. One JSON object:

```json
{
  "recipe": "walker",
  "process_note": "…",
  "seconds": 5,
  "camera": {"position": [0.6, -9.5, 1.7], "aim": [0.6, 0.0, 1.1], "lens": 35},
  "sun": {"direction": [0.5, 0.6, -0.62], "from": "stated"},
  "action": {"start": 0, "end": 5},
  "set": [
    {"id": "GROUND", "name": "the earth", "shape": "box", "min": [-30, -30, -0.02], "max": [30, 30, 0], "colour": [0.55, 0.48, 0.38], "ground": true, "level": true},
    {"id": "HOUSE_WALL", "name": "the house wall", "shape": "box", "min": [-0.5, 2.0, 0], "max": [7.5, 2.25, 3.0], "colour": [0.45, 0.12, 0.06]}
  ],
  "people": [
    {"id": "FATHER", "name": "the father", "element_id": "P1", "colour": [0.10, 0.30, 0.85], "height": 1.70, "pace": "stroll",
     "path": [{"t": 0, "at": [-2.2, -0.8, 0]}, {"t": 5, "at": [2.55, -0.8, 0]}]},
    {"id": "MOTHER", "name": "the mother", "element_id": "P2", "colour": [0.80, 0.05, 0.50], "height": 1.58, "at": [4.2, 1.2, 0.3], "facing": [-1, 0]}
  ],
  "props": [],
  "marks": {"band": null, "stripes": false}
}
```

- `seconds`: a whole number from 3 to 15, at least as long as the shot's slot. A take is made as long as its guide and trimmed.
- `set`: every piece of the place as a `box` (`min`, `max`) or a `cylinder` (`centre`, `radius`, `depth`, `axis`). One set per place: copy the place's pieces unchanged into every shot there, and build every side a camera will see. Mark the ground with `"ground": true`, any surface people stand on with `"level": true`, a thing fixed to a wall with `"hung": true`, a seat with `"seat": true`, a post with `"pole": true`. A turning part takes `"spin": {"axis": "X", "keys": [{"t": 0, "deg": 0}, {"t": 3, "deg": 180}]}`.
- `people`: a person in place has `at` and `facing`; a walker has `path` (timed points; the box faces the way it walks). `height` is the seated height for a seated person (`"seated": true`). `pace`: stroll, everyday, brisk or hurried. `element_id` is the person's id in the plan.
- `hands`: only for the hand that acts: `{"right": [{"t": 0.3, "at": [x, y, z]}, …]}`. A hold is two points at the same place.
- `props`: `size`, `at` (the middle of its foot where it rests), and `held`: `[{"from": 0.6, "to": 3, "by": "MAN.right"}]`. A held prop follows the hand.
- `sun.from`: `computed` when it was worked out from the place, date, time and street direction; `stated` when the planner chose it.
- `beats` (optional): `[{"kind": "lift", "from": 0.3, "to": 1.3}]` for a lift, a pass or a set-down, so their length can be checked.

### Rules the server refuses on

- Everything rests on something. A thing in the air needs what holds it (or `hung`).
- Every hand target is within 0.62 m of its shoulder. Move the person or the thing; never stretch.
- The right hand does the job, in view of the camera, and what it uses is on the person's own right. The camera is on the person's right side.
- Nobody passes through anything, and nobody moves faster than 2.5 m/s.
- Paths do not cross and nobody passes in front of anybody.
- Everybody and everything that matters is in the first frame, or walks in from the edge of the picture.
- Every person the plan puts in the shot has a box.

### Rules the server warns on

A beat shorter than a person takes; a person within 0.5 m of the edge of the ground they stand on; a post within 0.5 m of where someone stops; an action that ends more than a second before the clip does (in a still tail the model undoes the action: let the action fill the clip); pale or look-alike colours (use dark, strongly contrasting colours, one per thing).

### What no check can see

Steps, seats, bending and door arcs; an arm passing through a thing; one thing hiding another from the camera; whether a mark will be read as a real thing. The check frames are for these.

## The still

`still.json` is `{"prompt": "…", "parents": [{"id": "R12", "job": "the father: copy his face, hair, build and clothes", "crop": {"left": 0.1, "top": 0, "width": 0.4, "height": 0.6}}]}`.

- The server puts the guide's first frame first and writes the layout numbers and "Exactly N people" itself. Do not write positions in words.
- Your words, in this order: the view (size and angle); the place; each box and who or what it is, with that person's or thing's one fixed description, word for word the same in every still of the film; **THE MOMENT** (nothing done yet; or already walking); the sizes of props; the light by what it does (the sun's side, the shadows), no mood word.
- `parents`: only approved pictures, each with its job. For the first still of a scene: the people's full-length and face pictures and each prop's picture, cropped to the thing. For later stills of the same scene: crops of the scene's first approved still. Never a whole photo taken from another camera position; never a person's working-pose picture.
- A describes-what-it-looks-like word beats a trade name. A "not a …" phrase goes in only after that fault has been seen.

After `vw guide look`, show the operator the overlay and say what to look for: every person and thing sits on the red outlines. Then: approve the exact file; or repair one wrong part (`vw guide repair --still ID --region left,top,width,height --prompt "what is wrong; what it becomes"`); or reject it with the reason. A fault in the guide itself is fixed in the scene, never in words.

## The take's words

The server adds the fixed opening, the line that explains any marks, "Light stays exactly as in the image." and "No dialogue. No extra sound effects." You write the rest:

1. The key to the boxes: "BLUE box = the father in the image (light-blue shirt, white veshti)". A short identity, not the full description.
2. `ONE action only:` then the action, with a second on every move, repeating the guide's own times and no others. For a walker: the pace in plain words, "ALREADY WALKING" from the first frame or as they come in at the edge, "exactly on their box". Which hand acts; that the other hand stays still.
3. Who stays in place.
4. The exact count: "Exactly three people; no one else appears." For a transfer: "The shot ends there (the jug is not put down)."
5. Each fixed thing whose colour could drift, "from the first frame to the last".

Never: camera gear words; mood words; "Do not…" or "Keep…" sentences; a place or a path in words; push words about speed; anything about the light beyond the fixed line; an end picture. The server refuses these by name.

## When a take is wrong

Ask in this order, and change one thing:

1. Is it real footage, and as long as the guide? If not, the server has already set it aside; the operator may send the same request once more.
2. Does its first frame match the still? If not, the fault is the still or the guide.
3. Is the fault in the guide (a reach, a path, a speed, a missing support)? Fix the scene. It is free.
4. Only then the words, and only for what the guide and the still cannot carry.

The same request is never sent twice. After a second failure, do not try a third time: propose cutting the shot into shorter cuts, a closer angle, or leaving the detail out, and let the operator choose.
