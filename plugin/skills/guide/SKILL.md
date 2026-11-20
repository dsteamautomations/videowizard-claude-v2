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
| 1b. The shot's drawing | the server draws the shot from the scene: through the camera and from above, each person with front, back and working arm marked. Only after a fresh checker has passed the layout (row 3: the checkers of all the layouts are started together, in one message, before any layout card is shown), the operator approves it in the chat (`vw visuals next`), or `vw guide drawing --shot S` then `vw guide drawing-approve --shot S --sha … --quote "<their words>"`. No still before their Yes. | free |
| 2. Check frames | `vw guide frames --shot S` (three frames and a strip arrive in `work/guide/<shot>/frames/`) | free |
| 3. The double check | a fresh `vw-guide-check` helper, who has not seen the build, writes `verdict.json`; `vw guide verdict --shot S --file …` | free |
| 4. The guide is rendered | by the server, after a passing verdict: its first frame first (under a minute), its video behind it (several minutes; needed only for the take, row 8). Order the still (row 5) as soon as the first frame is ready; `vw guide status --shot S` says which is ready | free |
| 5. The still | `vw guide still --shot S --file still.json`; then `vw guide look --shot S` | paid (one picture) |
| 6. The overlay | the operator looks at the overlay and approves the exact file, or it is repaired or rejected | free |
| 7. The take's words | `vw guide prompt --shot S --file take.txt` | free |
| 8. Shoot | only on the operator's word: `vw guide shoot --shot S --quote "<their words>"` | paid (one take) |
| 9. Claude's check | `vw visuals pictures --looks`: a `vw-take-look` helper judges the take from its frames (one every half second, the sheet at four a second, the still); the server measures real footage, the length, the first frame and one continuous shot | free |
| 10. Review | on the page (`vw visuals page`), all takes together, once every take is made and checked: Select, Make another, or Reject. Until then say step 7's line of counts as it is and ask nothing | free |

One helper builds one shot. The checker is always a different, fresh helper. A scene gets one verdict. After the third failed check in a row the server holds the shot and asks the operator in the chat (`vw visuals next`): build nothing more for it until they answer.

## Any kind of shot may be an AI video

`recipe` is one of four words. Three kinds are proven here, with tested instructions; use the proven kind whenever the shot is one:

- `walker`: one or two people walk, others stand or sit. Wide or medium.
- `one_action_close`: one person does one thing with the right hand, close.
- `transfer_close`: one thing is poured, picked up or handed over, close, and the shot ends before it is put down.

Any other kind of shot is `other`: a machine running with nobody in view, a product turning on a table, a vehicle, many people, a run, a door, night. For `other`:

- Describe plainly what moves, how far, how fast and in what order (the `process_note`), and build exactly that: a thing that travels gets a `path`, a part that turns gets a `spin`.
- The server warns: "This kind of shot has not been tried here; the first take is a trial and may need a second." Tell the operator in those words. It is a warning, not a refusal; the operator still gives their word before the paid take, and the warning is shown again on the ready-to-shoot card.
- The guide is made of boxes. It cannot draw water, smoke or cloth: plan such a shot as a still or footage.
- A shot with no person is a normal shot: `"people": []`.

Known weak cases, each seen to fail, with what to do instead:

| Case | What failed | Do this |
|---|---|---|
| A run or sprint | A camera that follows the runner failed | Keep the camera fixed; expect a second take |
| Several people whose paths overlap | People came out as copies | Keep the paths apart, or expect a second take |
| A door | Failed when the door's swing clashed with the person's path | Keep the person's path clear of the door's swing |
| People speaking | The take has no sound, and lips will not match words | Show the person; never rely on what is said |

## Before the scene: how the real thing works

Write `process_note` first, two to four lines: what moves, how far, how fast, in what order. If you cannot write it, you do not know the action well enough to build it: ask the operator. It is required for every kind, `other` included, and so is `action`: the one thing that happens, with the second it begins and the second it ends.

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
- `set`: every piece of the place as a `box` (`min`, `max`) or a `cylinder` (`centre`, `radius`, `depth`, `axis`). One set per place: copy the place's pieces unchanged into every shot there, and build every side a camera will see. Mark the ground with `"ground": true`, any surface people stand on with `"level": true`, a thing fixed to a wall with `"hung": true`, a seat with `"seat": true`, a post with `"pole": true`. A turning part takes `"spin": {"axis": "X", "keys": [{"t": 0, "deg": 0}, {"t": 3, "deg": 180}]}`. A piece or a prop whose facing matters to the action (a chair one sits on, a cabinet opened from the front, a screen that faces someone) takes `"front": [x, y]`, its front side written as a person's facing: [0, -1], [0, 1], [1, 0] or [-1, 0]; it gets a black front panel and a purple back panel. Never on a symmetric piece (a slab, a wall, a pile).
- `people`: a person in place has `at` and `facing`; a walker has `path` (timed points; the box faces the way it walks). `height` is the seated height for a seated person (`"seated": true`). `pace`: stroll, everyday, brisk or hurried. `element_id` is the person's id in the plan.
- `hands`: only for the hand that acts: `{"right": [{"t": 0.3, "at": [x, y, z]}, …]}`. A hold is two points at the same place.
- `props`: `size`, `at` (the middle of its foot where it rests), and `held`: `[{"from": 0.6, "to": 3, "by": "MAN.right"}]`. A held prop follows the hand.
- `sun.from`: `computed` when it was worked out from the place, date, time and street direction; `stated` when the planner chose it.
- `beats` (optional): `[{"kind": "lift", "from": 0.3, "to": 1.3}]` for a lift, a pass or a set-down, so their length can be checked.

### A thing on a path

A piece of the set, or a prop that nobody holds, may travel as a person does: give it `"path"`, timed points of the middle of its foot. A prop is always in the first frame, on a path or not (refused otherwise: the still is made from the first frame). Only a piece of the set may start out of frame. It stays at the first point until that time, moves straight between points, and stays at the last. A bottle moving along a line, with nobody in view:

```json
{
  "recipe": "other",
  "process_note": "Bottles stand upright on a moving belt and travel along it at a steady 0.6 metres a second, left to right. Nothing else on the line moves; nobody is in the hall.",
  "seconds": 5,
  "action": {"start": 0, "end": 5},
  "set": [
    {"id": "GROUND", "name": "the floor", "shape": "box", "min": [-30, -30, -0.02], "max": [30, 30, 0], "colour": [0.30, 0.30, 0.32], "ground": true, "level": true},
    {"id": "BELT", "name": "the belt", "shape": "box", "min": [-3, -0.3, 0], "max": [3, 0.3, 0.9], "colour": [0.08, 0.20, 0.10]},
    {"id": "BOTTLE", "name": "the bottle", "shape": "cylinder", "centre": [-1.5, 0, 1.05], "radius": 0.05, "depth": 0.3, "axis": "Z", "colour": [0.50, 0.05, 0.05],
     "path": [{"t": 0, "at": [-1.5, 0, 0.9]}, {"t": 5, "at": [1.5, 0, 0.9]}]}
  ],
  "people": [],
  "props": []
}
```

(with `camera` and `sun` as above.)

- Build the thing where it stands at the start (`min` and `max`, or `centre`; a prop's `at`). The first point of its path is the middle of its foot there; the server refuses a path that starts anywhere else.
- At least two points, times in order from 0 to the shot's seconds. A thing that stays in place has no path.
- The thing points along its path: build it pointing the way it first moves, and it turns where the path bends. `"facing": [x, y]` on the thing stops that: it keeps pointing as built for the whole shot. A prop does not turn.
- A thing on a path may also `spin` (a wheel, a product turning on a moving line).
- A thing made of several pieces (a van and its wheels): give every piece the same moves, each from its own foot, and keep the path straight; each piece turns about its own middle.
- A thing has no speed limit. Start it in the first frame when you can: the still is made from the first frame. A piece of the set on a path that starts out of frame is warned on; a prop that is not in the first frame is refused.
- A prop has `held` or `path`, never both.

### Rules the server refuses on

- Everything rests on something. A thing in the air needs what holds it (or `hung`).
- Every hand target is within 0.62 m of its shoulder. Move the person or the thing; never stretch.
- The right hand does the job, in view of the camera, and what it uses is on the person's own right. The camera is on the person's right side.
- Nobody passes through anything, a moving thing included: a person never stands in the way of a thing on a path.
- Every person and every prop is in the first frame, or the person walks in from the edge of the picture.
- Every person the plan puts in the shot has a box.

The rules about a person (the right hand, reach, posture, the exact count) apply only when a person is in the shot.

### Rules the server warns on

A shot marked `other` (not tried here; the first take is a trial); a person faster than 2.5 m/s (a run has failed with a camera that follows: keep the camera fixed, expect a second take); people who overlap in the picture while one moves (they have come out as copies: keep the paths apart, or expect a second take); nothing moving at all (a still costs less); a piece of the set on a path that starts out of frame (a prop is always in the first frame: refused otherwise). The first four are repeated to the operator on the ready-to-shoot card.

A beat shorter than a person takes; a person within 0.5 m of the edge of the ground they stand on; a post within 0.5 m of where someone stops; an action that ends more than a second before the clip does (in a still tail the model undoes the action: let the action fill the clip); pale or look-alike colours (use dark, strongly contrasting colours, one per thing).

### The camera's small drift

The camera in the scene is one fixed position and aim. The server adds a tiny handheld drift to it at render, so the whole picture shifts by a few pixels across the shot. This is deliberate, it is not in your scene, and it is not a fault to fix or to report.

### What no check can see

Steps, seats, bending and door arcs; an arm passing through a thing; one thing hiding another from the camera; whether a mark will be read as a real thing. The check frames are for these.

## The still

`still.json` is `{"prompt": "…", "parents": [{"id": "R12", "job": "the father: copy his face, hair, build and clothes", "crop": {"left": 0.1, "top": 0, "width": 0.4, "height": 0.6}}]}`.

- The server puts the guide's first frame first (Image 1), then the shot's two approved drawings (Images 2 and 3) with the words that explain them, and writes the layout numbers and "Exactly N people" (with nobody in the shot: "Nobody is in view.") itself. Do not write positions in words, and do not describe the drawings. Your `parents` therefore start at Image 4; with the frame and the two drawings, at most 13 of them (12 with a look reference).
- Your words, in this order: the view (size and angle); the place; each box and who or what it is, with that person's or thing's one fixed description, word for word the same in every still of the film; **THE MOMENT** (nothing done yet; or already walking); the sizes of props; the light by what it does (the sun's side, the shadows), no mood word.
- `parents`: only approved pictures, each with its job. For the first still of a scene: the people's full-length and face pictures and each prop's picture, cropped to the thing. For later stills of the same scene: crops of the scene's first approved still. Never a whole photo taken from another camera position; never a person's working-pose picture.
- A describes-what-it-looks-like word beats a trade name. A "not a …" phrase goes in only after that fault has been seen.

After `vw guide look`, show the operator the overlay and say what to look for: every person and thing sits on the red outlines. Claude checks the still first: `vw visuals pictures --looks` lists it (kind `start`) with its lines; its card comes with the check, or after 30 minutes as not checked. Then: approve the exact file; or repair one wrong part (`vw guide repair --still ID --region left,top,width,height --prompt "what is wrong; what it becomes"`); or reject it with the reason. A fault in the guide itself is fixed in the scene, never in words.

## The take's words

The server adds the fixed opening, the line that explains any marks, "Light stays exactly as in the image." and "No dialogue. No extra sound effects." You write the rest:

1. The key to the boxes: "BLUE box = the father in the image (light-blue shirt, white veshti)". A short identity, not the full description.
2. `ONE action only:` then the action, with a second on every move, repeating the guide's own times and no others. For a walker: the pace in plain words, "ALREADY WALKING" from the first frame or as they come in at the edge, "exactly on their box". Which hand acts; that the other hand stays still. For a thing on a path: "ALREADY MOVING" from the first frame when it is, "exactly on its box".
3. Who and what stays in place.
4. The exact count: "Exactly three people; no one else appears." With nobody in the shot: "Nobody is in view; no person appears." For a transfer: "The shot ends there (the jug is not put down)."
5. Each fixed thing whose colour could drift, "from the first frame to the last".

Never: camera gear words; mood words; "Do not…" or "Keep…" sentences; a place or a path in words; push words about speed; anything about the light beyond the fixed line; an end picture. The server refuses these by name.

## When a take is wrong

Ask in this order, and change one thing:

1. Is it real footage, and as long as the guide? If not, the server has already set it aside; the operator may send the same request once more.
2. Does its first frame match the still? If not, the fault is the still or the guide.
3. Is the fault in the guide (a reach, a path, a speed, a missing support)? Fix the scene. It is free.
4. Only then the words, and only for what the guide and the still cannot carry.

A second take is ordered by the operator on the page ("Make another", with their words): that is their word, so no card is shown again. Say the cause first (`vw guide cause`), change that one thing, then `vw guide shoot --shot S` (no `--quote`). If the cause is the still or the layout, its card comes first; if it is the model's own limit, no take is made. If the operator withdraws the order in the chat: `vw guide shoot --shot S --cancel --quote "<their words>"`; if the cost limit refuses it, the order is dropped: tell the operator the spend. A take rejected with no new one ordered: ask the operator what happens to the shot (cut it, another angle, or leave it out).

The same request is never sent twice. After a second failure, do not try a third time: propose cutting the shot into shorter cuts, a closer angle, or leaving the detail out, and let the operator choose.

## A person stands where a real person would do the job

These rules are for every shot with a person, of any kind. The server refuses a posture no person can hold, before any spend. Lay the place out so that it cannot arise:

1. **Face the work.** The body faces what the person does or watches. What the right hand uses is in front of the body or to its right, between hip and shoulder height.
2. **Never behind.** Nothing a hand uses lies behind the line of the shoulders. An arm bends at the elbow; it never reaches backward and never stretches (0.62 m from shoulder to hand at most).
3. **Head and body agree.** Give `"watches": [x, y, z]` on a person who watches something: it must lie within 45 degrees of the way the body faces.
4. **Right side to the camera.** A person who faces left has the right side away from the camera, so the working hand is hidden. A person who works with the right hand faces right, or the camera stands over the right shoulder.
5. **The layout gives way, not the body.** Where the plan's layout makes the job impossible to stage, move the person, the thing or the camera by the least that makes it possible; mirror the layout if that is what it takes. The plan's meaning stays (who does what to what); its left and right may change.
6. **Say every such change.** List it in the scene: `"changed_from_plan": ["The plan had the man at the right of the machine; he stands at its left, facing right, so his right hand is toward the camera."]`. The operator sees these lines with the shot's drawing. Its exact form: a list of at most ten strings, each one plain sentence of at most 300 characters, never an object; `"changed_from_plan": []` when nothing changed.

## The shot's drawing

When the scene is accepted, the server draws it from the same numbers as the guide (free): through the film's camera and from above. Every person is drawn with a pale face and chest with dark marks, a purple back and an orange right arm, so the operator and the picture AI can both see which way each person faces and which arm works.

- A piece of the set or a prop that is a thing with an approved drawing set (the `vw:drawing` skill) carries `"drawn_as": "<element id>"`, and `"turn": <degrees>` when it is turned. It is then drawn as the thing's own model, standing where its box stands. Make the box the thing's real size: the server says when the two disagree.
- The operator sees the drawing only once a fresh checker has passed the layout, and approves it before the still. A correction changes the scene, and the new scene is drawn, checked and approved again.
- The still's request then carries the two drawings after the guide's first frame, with the words that explain them. You do not send them and you do not describe them: write the still's words as before.
- When an approved still looks drawn rather than photographed, make it again with a look reference: `"look": "<the id of an approved picture of this film>"` in the still's file. Only its surface, light and colour are taken.

