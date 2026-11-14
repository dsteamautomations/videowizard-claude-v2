# 195 — Drawing standard for accurate pictures (with design/194)

14 November 2026. For SK's approval. This sets how the drawings are made before a picture is asked for, and how much work goes into them. It is not yet the workflow document; that follows once this standard is agreed.

Proof set made to this standard: `drawings-first-test-2026-11-14/dovetail-1-elevations-plan-detail.png`, `dovetail-2-pulled-apart.png`, `dovetail-3-together.png` (made by Claude's script `dovetail.py` on this PC, outside the application).

## 1. The one rule everything else follows from

**One table of real measurements makes one model, and every view is that model seen from one direction.**

- No view is drawn on its own. The plan, the elevations, the section and the camera view all come from the same numbers, so they cannot disagree.
- Things that must be equal are built from the same number, so they are equal by construction (every brick, every tail, both stacks).
- A number is typed in one place only. Change it there and every view changes.

This is what SK's rat-trap set did by hand with its millimetre coordinates. My first joint drawings did not do it: each view was typed separately. The dovetail proof set does.

## 2. Two levels of effort

The level is decided by what must be right in the picture, not by how much time is available. The helper never lowers the level on its own; if it cannot reach the level, it says so and the picture waits.

| Level | When | What is drawn | Work | Time per subject (honest estimate) |
|---|---|---|---|---|
| **3. Engineered set** | The construction, pattern or mechanism must be exact and the image model does not know the subject (a bonded wall, a joint, a machine part, a product's inner parts) | 4 to 6 views in 3 files, all from one model: the face views that show the pattern, a plan, a section or pulled-apart view for what is hidden, a detail of the one repeating unit with its sizes, and a view from the photograph's own camera | Research the real sizes and rules first, with sources. Write the measurement table. Build the model. Check each view against the rules. | 10 to 20 minutes, most of it research and checking. The drawing itself took about 4 minutes for the proof set, with one round of fixes. |
| **2. Composition set** | Placement, relative size and framing must be right, and one or two facts must not drift (a site, a room, a product among other things) | 3 views: a plan with the camera on it, the view from that camera with real shapes (not boxes), and a detail sheet that proves each fact that must not drift | The place is written once in metres. Shapes are simple but true in proportion. | 5 to 10 minutes |

**There is no "one drawing" level (SK, 14 Nov).** A general picture gets the full composition set of at least three views, as in SK's kiln example, because each view removes a different guess: the plan fixes where things are, the camera view fixes the frame, the detail sheet fixes what must not drift. More views are added when the picture has more that must hold (a second detail sheet, a face view of a key object). Plain boxes worked out from the place's numbers are not a drawing set: they only supply the positions that the camera view is then drawn over with real shapes. In the paid test, boxes alone failed on Gemini.

No drawing at all: an ordinary subject the model already draws correctly from words, or anything the client's footage shows (the footage frame is the reference).

Mixed subjects take the higher level for the part that needs it. A technical thing standing in a scene is a Level 3 set for the thing and a Level 2 set for the scene.

**Where I was not at standard.** My timed test used plain boxes for the scene and something below Level 3 for the joint, and called it a test of SK's method. Under this standard that joint would have been Level 3.

## 3. The views, by what each one controls

Names change with the subject; the job of each view does not.

| The view | What it fixes | Needed when |
|---|---|---|
| Face view, square on (elevation) | The pattern seen on a surface; heights | A surface pattern must be read |
| From above (plan) | Where things are; spacing; where the camera stands | Almost always |
| Cut through (section) | What is inside and cannot be photographed | The inside is the point |
| Pulled apart | How parts fit together | A joint, an assembly, a mechanism |
| One unit, enlarged, with sizes | The repeating unit and its proportions | Anything built from repeated units |
| Side by side (comparison) | What is the same and what differs between two things or two states | Before and after, two products, two states |
| From the photograph's camera | The frame itself: angle, what is near, left and right | Every picture |
| In order (steps) | Sequence | A process; often the drawing is then the final picture |

A set is complete when every fact on the "must be true" list can be pointed to in at least one view.

## 4. How each drawing is made

1. **Facts first.** Every size and rule in the measurement table has a source, or is marked "assumed". An assumed number is shown to the operator as assumed.
2. **Real units.** Millimetres for a thing, metres for a place. Every view states its scale.
3. **One colour, one meaning,** the same in every view of the set. Colour separates parts or materials, never decoration.
4. **Hidden surfaces are worked out, not guessed.** What is in front hides what is behind, by calculation.
5. **The camera view uses the photograph's camera**: the same angle and height the picture will be asked for.
6. **Two copies of every sheet.** With labels and sizes for the operator; without any text for the image model. Short labels, a leader to the exact spot, sizes on dimension lines.
7. **Plain SVG**, fixed colours, white background, twice the size for a sharp picture.

## 5. When a set is ready (checked before the operator sees it)

- Every "must be true" fact is visible in a named view.
- Counts are right: the number of repeating units in each view matches the table.
- The views agree with each other. With one model this holds by construction; it is still looked at once.
- Nothing runs off the sheet; no label covers the subject.
- The camera view matches the shot's camera.
- The helper has looked at each rendered sheet, not only written it.

Then the operator approves the labelled set, with the sources beside it, before any paid picture.

## 6. What I am being upfront about

- **The dovetail proof set is right in its geometry and still untidy in its labels**: on the first sheet several leader lines cross each other. I stopped after one round of fixes. Under this standard it would need one more round before an operator sees it.
- **Wood grain, texture and light are not drawn.** The drawing fixes shape and arrangement; the image model adds material and light.
- **A wrong fact gives a precise wrong drawing.** The standard cannot catch a wrong source; the operator's approval can.
- **Curved and organic subjects** (a person, an animal, cloth, a plant) do not suit Level 3. For those the drawing fixes position and pose only.
- **Times are estimates** except the two measured drawing times. Research time depends on the subject.
- **Tested since** (section 7): sets at this standard were followed by both models on five things of a real film.

## 7. Additions from the VW-18 trial (14 Nov, five scenarios; results in `drawings-first-test-2026-11-14/vw18/RESULTS.md`)

| # | Addition | Why (what the trial showed) |
|---|---|---|
| 1 | **The model's copy uses one colour for one material.** Colours that carry a meaning (cross bricks darker, frame blue, guard yellow) are for the operator's copy only. | GPT Image copied the darker brick ends and the machine's blue and yellow into the photograph. |
| 2 | **The camera view is drawn in true perspective with the shot's own lens.** A flat angled view is for the operator. If a flat angled view is sent to a model, the prompt warns that walls and edges look slanted in it and must be plumb and level in the picture (SK). | Flat angled drawings make upright walls lean. |
| 3 | **Each model gets its own guidance.** GPT Image: the drawings are diagrams; take positions, shapes, pattern and counts only; real surfaces; its own surroundings (SK). Gemini: match the frame of Image 1 exactly; do not move the camera. | GPT Image reproduces faithfully; Gemini changed the framing in three of four start pictures. |
| 4 | **Footage beats the plan's numbers.** When the film's footage shows the thing, its proportions come from the frame, and any conflict with the plan's sizes is reported to the operator before drawing. | The plan's 190 x 90 x 90 brick cannot build the wall seen in the footage. |
| 5 | **A loose or living thing gets a form sheet, not an engineered set**: overall shape, sizes, how it is held or used. | The broom: both models were right from one form sheet and the footage frame. |
| 6 | **Assumed sizes are written on the sheet as assumed**, and the operator approves them. | The machine, the lorry and the plinth had no size in the plan. |
| 7 | **Only what a camera can see is modelled, and the sheet says what is left out.** | The plinth's inner bond; the mesh of the guard. |
| 8 | **Every state or condition is on the must-be-true list and on the check list** (closed, dry, full, at rest), not only in the scene's words. | Gemini opened the guard door that was asked closed. |
| 9 | **What cannot be drawn as a solid is named on the sheet and given in words**: mesh, water, cloth, dust, a bent pose. | The block figure stands upright; the bent sweeping pose came from words and was right. |
| 10 | **The shot is drawn before any reference is paid for.** Drawing the frame shows what the plan's words cannot deliver. | Bricks "level with the boards" are invisible from eye height; the technician's "right profile" and "facing the machine" cannot both hold. |
| 11 | **A length or count that matters is stated in the facts as a number**, not left to the drawing alone. | Gemini made the plinth a short block. |
| 12 | **Every view is explained**, on the operator's sheet and in the prompt: what kind of view it is in plain words, what it shows, what it is for, and what each colour and shape stands for. A view meant only for understanding (the view from above) is named as not to be reproduced (SK). | SK's trial document did this for every view; my trial sheets carried a title and labels only. |
| 13 | **A shot drawing obeys the right-handed staging rules and is checked for them**: the right hand does the job, on the camera's side of the body; what it uses is on the person's right within 0.62 m of the shoulder; the left hand rests (SK; design/175). | The start picture is the first frame of a take held to those rules. Shot B11 as planned hides the right hand. |
| 15 | **A drawn person shows front and back.** Face and chest are pale panels with dark marks; the back of the head and trunk is one fixed colour used for nothing else; the right arm has its own colour. The same in every drawing, and named in the how-to-read paragraph (SK). | GPT Image drew a man facing the machine with his right hand reaching backward to the knob: the block figure had no front. |
| 16 | **A person is placed where a real person would do the job.** The body faces the work; what the right hand uses is in front or to the right, never behind the shoulders; what is watched lies within 45 degrees of where the body faces; a right-handed worker faces right or is seen over the right shoulder (SK). | The same picture: the plan's layout could only be staged with a twisted arm. |
| 17 | **The layout gives way, not the body.** The drawer may move or mirror the plan's layout by the least needed, and reports each change in one line (SK). | The lab shot had to be mirrored: man at the left facing right, machine beyond. |
| 14 | **A drawing never fixes the look.** Where a picture comes out looking drawn, a look reference (a lifelike picture, for texture, light and colour only) is added (kept aside, SK). | One try on GPT Image 2.6: layout kept, look lifelike. |

Still weak: the labels on the operator's sheets (leader lines cross on the busy sheets). Labels are placed by hand in the drawing script; this needs one more pass before an operator uses the sheets.
