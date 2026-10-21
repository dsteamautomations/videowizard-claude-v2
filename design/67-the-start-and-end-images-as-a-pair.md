# design/67 — The start and end images as a pair: three instructions in the packet, the start's references sent again

Status: requirements note, prepared by the builder on 21 Oct 2026 from SK's three points on the end image (same day, after design/66). For SK's approval. Nothing built. Sources: design/66; `visuals_stage.packet` and `generate_image`; `visual_workers` (the image edit call sends every parent as an input image, in order).

## 1. SK's three points

1. The references that made the start image (identity sheets, place references) are sent again when the end image is made, so the person and the room are held by their sources and not only by the start picture.
2. The end prompt states positions: each subject against its landmark, its facing, its side of the frame, the camera unmoved.
3. The start prompt is written knowing the end: the two prompts are written as a pair before either image is generated, and the start is composed for the whole segment.

## 2. Today

- The packet (`vw visuals packet --shot S`) carries the scene, the shot with every subject's start and end state, the approved references, and two fixed instructions: one for the start image ("compose the starting state of every visible subject …") and one for the motion. Nothing for the end image.
- An end keyframe is edited from the parents the child names. The child may name the start and the sheets together, but nothing says so; named alone, the start is the only carrier of identity.
- The worker sends every parent as `image[]` to the edit call, in the order given, so the start first and the references after is already possible.

## 3. Changes, server only

| | Change | Where |
|---|---|---|
| A | The packet carries three fixed instructions instead of two: `start_image_instruction` (the present `image_instruction`, extended), `end_image_instruction` (new) and `video_instruction` (as today). `image_instruction` stays as an alias for one release so nothing that reads the packet breaks. | `visuals_stage.packet` |
| B | **Start:** "Write the start prompt and the end prompt together before generating either. Compose the start for the whole segment: every visible subject in its start state in the named layout, what the motion heads for already in frame, room in the frame for the move, nothing the end state needs cut off or hidden, nothing placed where the end would have to remove it. Keep landmark-relative positions; the camera only changes their screen projection." | the instruction text |
| C | **End:** "Make the end image from the approved start image as its parent; the server sends the start's own references with it. Show every subject in its end state as the plan gives it: its position against its landmark and its side of the frame, its facing, its pose, what it holds, how far the work has gone; for an acting subject the result of its last beat. Name the positions in words. Change nothing else: the same framing, camera, light, people and props. Keep in frame whatever the motion heads for." | the instruction text |
| D | When a keyframe is generated with a keyframe as a parent (an end image), the server appends that parent's own parents, in their order, after it, skipping any already named; the recorded generation lists all of them. The child names only the start. | `visuals_stage.generate_image` |
| E | `SERVER_VERSION` 0.24.0. | `config.py` |

Not changed: the plugin (`image --kind keyframe --parents <start>` is already the call); the page; the prompt (section 5 already says the pair is approved together, and the packet is where the composition rules live); the plan schema.

## 4. Tests, first

- `test_visuals_stage_pure.py`: the packet carries the three instructions and the alias; the start instruction says to write both prompts first and to leave room for the move; the end instruction names landmark, side of frame and facing. `generate_image` for a keyframe whose parent is a keyframe made from two approved sheets records three parents, start first, sheets after, and does not repeat a sheet the child also named; an isolated image from an approved sheet is unchanged.

## 5. Not covered

- `server/tests` (Docker). Whether the image model holds identity better with the sheets sent again: VW-6's first pair shows it, side by side on the page.

## 6. Order

SK's approval → tests → change → commit and push → tell SK → deploy the server (0.24.0, the workers restart; no plugin change, no restart of the child) → design/35 row 59, design/49 line. It must land before the child composes the first keyframe on VW-6, which comes after the gaps are accepted.
