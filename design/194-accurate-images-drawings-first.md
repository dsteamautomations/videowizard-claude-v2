# 194 — Accurate images: the drawings-first workflow (approved by SK, 14 Nov 2026)

14 November 2026. Approved by SK on 14 Nov; built on branch `accurate-images` in the steps of section 12. The trial's drawings, pictures and prompts are outside the repository, in the review folder (`drawings-first-test-2026-11-14`). The drawing standard is design/195.

**One change from the approved plan, made in the build (step 1):** the drawing tool sits on the server, not in the plugin. A drawing set is data (facts, pieces in real units, people, views); the helper writes that description and the server draws every view from it (`server/app/draw3d.py`). So no helper code runs anywhere, the same description can be checked before it is drawn, and labels are placed by the server in one column. Wherever this document says "the drawing tool in the plugin" or "on the operator's machine", read "the server draws the helper's description".

**Three more things the build settled (steps 4 and 5):**
- The guide's first frame (the Blender boxes) stays Image 1 of a still, because the take is made from that guide and must start on it. The shot's two drawings follow as Images 2 and 3. A thing's real shape enters the drawing when its piece of the scene is marked `drawn_as`.
- No switch: the still made from the box frame alone is retired for every new still at release (SK's rule of 12 Nov: no route switch), not "kept until the first film has run". The rows are 55 to 58 of design/35.
- The server has no cutting view: a cut is modelled as its own pieces. Built: steps 1 to 6 on branch `accurate-images`; nothing deployed. Read against `main` (server 0.98.0, not deployed).

Basis: SK's trial document (`drawings-first-handover-from-trial-2026-11-14.txt`), the drawing standard (`drawing-standard-2026-11-14.md`), and the five-scenario trial on film VW-18 (`drawings-first-test-2026-11-14/vw18/RESULTS.md`).

## At a glance: the two areas this changes

The change touches two places in the visuals stage, and they are built and switched on separately.

### Area A: the reference picture of a thing (References step, made on Gemini)

| # | What happens | Who | Where it sits in the application | New or changed |
|---|---|---|---|---|
| A1 | The plan marks the thing: engineered set, composition set, form sheet, or no drawing | assistant | the plan (an element's record) | new field |
| A2 | Facts table: every size with its source or marked assumed; states; counts; footage beats the plan | helper | References step, before any set is queued | new |
| A3 | The thing is drawn: all views from one model, two copies of each sheet | helper, with the drawing tool in the plugin | operator's machine | new |
| A4 | The sheets are checked as plain SVG and rendered to PNG | application | server, the SVG rules and Chromium it already has | reused |
| A5 | The operator approves the drawing set in the chat, with sources and assumed sizes | operator | chat, one item per thing | new item |
| A6 | The reference set is made on Gemini: the footage frame when there is one, then the no-text drawings, then the prompt in the fixed order | application | the reference set request | changed: parents and prompt |
| A7 | The check: lines from the facts table, the drawings sent along | application | the picture check | changed: lines |
| A8 | The operator's verdict on the set | operator | chat, as today | unchanged |

### Area B: the start picture of an AI video shot (Blender guide path, made on GPT Image 2.6)

| # | What happens | Who | Where it sits in the application | New or changed |
|---|---|---|---|---|
| B1 | The place is written once in metres with its camera: the same description that builds the Blender guide | helper | the guide's scene description | unchanged source |
| B2 | Posture and right-hand checks on the numbers: faces the work, nothing behind the shoulders, head within 45 degrees of the body, right side to the camera, reach 0.62 m | application | the guide's checks before any spend | changed: three new checks beside the existing ones |
| B3 | The layout gives way where a posture is impossible: move or mirror, each change reported in one line | helper | with the scene description | new rule |
| B4 | The camera drawing and the view from above: real shapes from the things' models, the person with face, chest, back and right arm marked | helper, with the drawing tool | operator's machine | new |
| B5 | Checked and rendered | application | server | reused |
| B6 | The operator approves the shot drawing in the chat, with the reported changes | operator | chat, one item per shot | new item |
| B7 | The start picture on GPT Image 2.6: Image 1 the camera drawing, Image 2 the view from above, then the approved reference pictures of Area A and the person's reference; the prompt in the fixed order with the how-to-read paragraph and the right-hand lines | application | the guide's still request | changed: parents and prompt |
| B8 | If the picture looks drawn: a look reference is added (a cheap Gemini draft from the same drawings, or an approved earlier picture of the place) | application, on the operator's word | the same request, one more image | new option |
| B9 | The check and the operator's verdict; then the take, as today | application, operator | as today | unchanged |

A still (a shot picture that is not a video's first frame) follows Area B's steps B1 to B7 without the Blender guide, on the film's own image model with that model's guidance.

Order of dependence: Area B uses Area A's approved reference pictures. Area A can be switched on alone.

## 1. The requirement

A picture of a thing the image model does not know well (a bonded wall, a machine, a loaded lorry), or of people and things in set positions, must come out right. Today it often does not, because the model is given words and has to guess the construction and the layout.

The new way: before any paid picture, the thing and the shot are drawn from real measurements, the operator approves the drawings, and the drawings go to the image model as reference pictures.

## 2. Decisions already made by SK

| Decision | Date |
|---|---|
| Drawings first, to the drawing standard: one table of measurements, one model, every view from it | 14 Nov |
| No one-drawing level: a general picture gets at least three views | 14 Nov |
| GPT Image is told the drawings are diagrams: positions, shapes, pattern and counts only; real surfaces; its own surroundings | 14 Nov |
| Both models are warned that walls and edges look slanted in an angled drawing and must be plumb and level in the picture | 14 Nov |
| The final start picture of an AI video shot is made on GPT Image, on its latest version (`gpt-image-2.6-sunburst`, the model the application already uses for a start picture) | 14 Nov |
| Reference pictures of things are made on Gemini, as today | 14 Nov |
| Start pictures carry the video step's right-handed staging rules (section 5a) | 14 Nov |
| Every drawing is explained to the model: what kind of view it is and what each colour and shape stands for (section 5, point 3) | 14 Nov |
| A drawn person shows front and back by fixed marks and colours, and the working arm by its own colour (section 5a) | 14 Nov |
| A person is placed where a real person would do the job; the drawing may leave the plan's layout to make the posture possible, and reports it (section 5a) | 14 Nov |
| A look reference for GPT Image was tried once and worked; the result is kept aside for use if GPT Image's pictures look artificial (section 5b) | 14 Nov |

## 3. Where it applies

| Place | Today | New |
|---|---|---|
| Reference picture of a thing the footage shows | The footage frame is the reference | The frame, plus a drawing set made from it, when the thing's construction or pattern must be read in a shot |
| Reference picture of a thing with no source | Gemini looks the thing up on the web itself | The assistant draws it from the plan's facts and its own knowledge; the drawings are the references |
| Start picture of an AI video shot | GPT Image, from the Blender box layout's first frame | GPT Image, from the shot's camera drawing with real shapes, the plan view and the things' reference pictures |
| Shot picture (a still) with a technical thing or set positions | Words and references | The same drawings as for a start picture |

Not changed: people's likeness (drawings give position and pose only); labelled diagrams, charts and process pictures (the drawn route makes those; the drawing is the final picture); ordinary things the model already draws correctly.

## 4. The steps

| # | Step | Who | What goes in | What comes out |
|---|---|---|---|---|
| 1 | **Mark** which things and shots need drawings, and at which level | the assistant, in the plan | the plan's elements and shots | a level per thing: engineered set, composition set, form sheet, or none |
| 2 | **Facts table** for each marked thing | the assistant's helper | the plan's sizes and sources; the footage frame when there is one | every size with its source, or marked "assumed"; states (closed, dry, full); counts; a conflict between footage and plan is reported, and the footage wins |
| 3 | **Draw the shot first** | the helper | the shot's layout, positions and camera | the place from above and through the shot's camera in true perspective; anything the plan's words cannot deliver is reported now, before any spend |
| 4 | **Draw the thing** | the helper | the facts table | the set the level calls for, two copies of each sheet: labelled for the operator; no text and one colour per material for the model |
| 5 | **Check and render** | the application | the SVG sheets | refused if not plain SVG; rendered to PNG |
| 6 | **Operator approves the drawings** | the operator, in the chat, one item per thing or shot | the labelled sheets, the sources and the list of assumed sizes | yes, no, or a correction in words; a correction is redrawn free |
| 7 | **Reference picture** | the application, on Gemini | the footage frame when there is one, then the no-text drawings; the prompt in section 5 | the thing's reference set, as today |
| 8 | **Check** | the application's checker | the picture, the drawings, and check lines made from the same facts table | pass or fail per line; shown to the operator; never blocks (as today) |
| 9 | **Start picture or still** | the application, on GPT Image | Image 1 the camera drawing, Image 2 the plan view, then the things' approved reference pictures and the person's reference | one picture |
| 10 | **Operator's verdict** on the picture | the operator | the picture beside its camera drawing | yes, no, or correct it |

### When a picture is wrong

- **One fault at a time.** The failed fact is restated first in the prompt and its drawing moves to Image 1.
- **A fault in the drawing is fixed in the drawing**, free, and approved again before another paid picture.
- **Framing wrong on a start picture:** made again on GPT Image with the same drawings; never by editing the picture.
- **After two rounds** the operator decides: accept, change the shot, or cut the detail (as today for guides).
- **The spend cap** and the "announced, never asked" rule for paid steps are unchanged.

## 5. What the model is asked

Every prompt has the same order:

1. One opening line: what the picture is.
2. The job of each image: "Image 1 is … take … from it".
3. **How to read the drawings**, one short paragraph per drawing:
   - what kind of view it is, in plain words (seen straight down from above; square-on to the face; cut through; pulled apart; through the film's camera with a real lens) and what it is for (layout, pattern, what is inside, the exact frame);
   - what each colour and each shape stands for ("the white disc with a red line is the dial and its needle");
   - what a block figure means (where a person stands, which way they face, where the arm reaches);
   - which views are for understanding only and are not to be reproduced (the view from above);
   - that outlines, flat colours and the plain backdrop are drawing conventions, not things in the picture.
4. Both models: the slant warning, whenever a flat angled drawing is among the images.
5. GPT Image only: the drawings are diagrams; take positions, shapes, pattern and counts; real surfaces with natural variation and wear; choose believable surroundings.
6. Gemini only, on a shot: match the frame of Image 1 exactly; do not move the camera.
7. What must be true: the facts table as plain sentences, with every count, length and state.
8. The scene in plain sentences.
9. On a start picture: the right-handed staging lines of section 5a.
10. Nobody else, no text, no logo.

The same explanations are printed on the operator's labelled sheet beside each view: its name, what it shows and what it is for. SK's trial document did this for every view; my trial sheets carried only a title and labels.

### 5a. Right-handed staging on start pictures

A start picture is the first frame of a video take, so it must already obey the rules the take is held to (design/175, and the checks the Blender guide runs before any spend):

| Rule | In the drawing and the prompt |
|---|---|
| The job is done by the right hand | The acting arm in the drawing is the right arm; the prompt names the right hand |
| What the right hand uses is on the person's right, within reach | The thing is placed on the person's right, no farther than 0.62 m from the shoulder; an arm is never stretched |
| The right hand is never hidden by the body | The camera stands on the person's right side: over the right shoulder, or a right-profile angle |
| A handle, grip or opening faces the right of the frame, or the hand's approach | The thing is turned so in the drawing, and the prompt says which way it faces |
| The left hand does nothing | The prompt gives it a resting place: flat on a surface, on the knee, at the side |
| The action reads left to right | The person at the left or centre, what they reach for at the right |
| A thing is held in, and picked up by, the right hand, from the right side | As drawn; stated in the prompt |

When the plan's fixed order conflicts with a rule, the plan's fixed order stays and the reached-for thing is placed on the person's right (design/175).

#### The person is drawn so the model cannot mistake front for back (SK, 14 Nov)

What went wrong: in both GPT Image pictures of the lab shot the man faces the machine while his right hand reaches backward to the knob behind him. No person can work like that. Two causes: the block figure did not show which side was its front, and the layout put the knob where only a twisted arm could reach it.

Every drawn person, in every drawing, carries the same marks (the video guide already marks its box people's face and chest):

| Part | How it is drawn | Meaning |
|---|---|---|
| Front of the head | a pale panel with dark eyes and mouth | the face: the way the person looks |
| Front of the trunk | a pale panel with one dark stripe down the middle | the chest: the way the body faces |
| Back of the head and trunk | one fixed colour (purple), used for nothing else in any drawing | the back |
| Right arm | its own fixed colour (orange) | the working arm |
| Left arm | plain | the resting arm |

The how-to-read paragraph of every prompt names these marks: "the pale side with the dark stripe is his chest, the purple side is his back, the orange arm is his right arm."

#### The person stands where a real person would do the job (SK, 14 Nov)

These are instructions to the drawer (the assistant's helper), applied when the place is laid out, before any drawing is rendered:

1. **Face the work.** The body faces what the person is doing or watching. The thing the right hand uses is in front of the body or to its right, between hip and shoulder height.
2. **Never behind.** Nothing the hand uses lies behind the line of the shoulders. The arm bends at the elbow as a real arm does; it never reaches backward and never stretches (0.62 m from shoulder to hand at most).
3. **Head and body agree.** What the person watches lies within a comfortable turn of the head, at most 45 degrees from where the body faces. If it does not, the person or the thing is moved.
4. **Right side to the camera.** A person who faces left has the right side away from the camera, so the working hand is hidden. A person who works with the right hand therefore faces right, or the camera stands over the right shoulder.
5. **The layout gives way, not the body.** Where the plan's layout makes a possible posture impossible, the drawer moves the person, the thing or the camera by the least that makes it possible, and may mirror the layout. The plan's meaning (who does what to what) stays; its left and right may change.
6. **Every such change is reported** to the operator with the drawing, in one line each: what the plan said, what was drawn, why.

The application checks rules 1 to 4 on the place's numbers and refuses a drawing that breaks one, naming the rule.

Worked case, the lab shot (drawn again, free; no picture made from it): the plan had the machine at the left and the man at the right, in right profile, watching the dial. That cannot be: to watch the machine from its right he faces left, which hides his right hand. Redrawn: the man at the left facing right, the console in front of him, the machine beyond it. His right side is toward the camera, shoulder to knob 0.61 m, the dial 5 degrees off where his body faces, and the action reads left to right. File: `drawings-first-test-2026-11-14/vw18/out/view-BEAT05-before-after.jpg`. The hand was then drawn resting on the knob (shoulder to hand 0.58 m).

Pictures from the redrawn shot (three, one run each, judged by Claude): `drawings-first-test-2026-11-14/vw18/pictures/view-v2-BEAT05.jpg`.

| Picture | Posture | Layout and facts |
|---|---|---|
| Gemini draft (1K) | Natural: faces right, right hand on the control, left hand at his side | Guard door open again; a wheel in place of the knob; framing shifted |
| GPT Image 2.6, no look reference | Natural, as drawn | As drawn: man, console, machine; guard closed; needle up; one brick |
| GPT Image 2.6, with the Gemini draft as look reference | Natural, as drawn | As drawn; a little warmer and more worn than the picture without it |

The backward-reaching hand is gone in all three. With the how-to-read paragraph and GPT Image 2.6, the picture without a look reference is already lifelike, so the look reference stays an option, not a step.

The shot drawing step runs these as checks on the place's numbers, before the operator sees the drawing. In the trial, shot B11 as planned breaks the third rule: the camera sees the man's left side, so his right hand with the mug is partly hidden. Under this workflow that is reported at step 3 and the camera or the man is moved before any picture.

### 5b. A look reference for GPT Image (kept aside)

GPT Image follows the drawings closely and can come out looking drawn: clean, evenly coloured, the drawing's colours kept. One try on the lab shot fixed this.

- A lifelike picture of a similar scene is added as the last image, with these words: it is a look reference; keep its surface textures, its light, its true colours and the way it reads as an ordinary photograph; take nothing else from it, not positions, arrangement, states or the person; where it differs from Image 1 or the facts, Image 1 and the facts win.
- In the try the look reference was Gemini's own start picture of that shot. In use it would be a cheap Gemini draft (the 1K size) made from the same drawings, or an approved picture of an earlier shot in the same place.
- Result: the picture kept the drawn layout, the closed guard, the right hand on the knob, and had the worn paint, real room and soft light of the Gemini picture. File: `drawings-first-test-2026-11-14/vw18/pictures/view-final-BEAT05-look-try.jpg`.
- One run. Three things changed at once against the earlier GPT picture (GPT Image 2.6 instead of 2.5, the look reference, the how-to-read paragraph), so the gain cannot be put on one of them.

Status: not part of the workflow's fixed steps. It is used when the operator finds a GPT Image start picture artificial.

Plain sentences throughout. No keyword stacks, no quality tags, no long list of things to avoid. The rules are the same for every category of film; nothing in them is tied to brick or building.

## 6. Requirements not stated but expected

- The same numbers feed the Blender guide and the camera drawing, so the start picture matches the guide's first frame.
- The drawing tool runs on the operator's machine with the plugin (standard Python only); the server only checks and renders. The helper never runs code on the server.
- A drawing set is kept with the element and reused by every shot that shows the thing; it is drawn once.
- A drawing is never a parent of a person's picture, and never carries a logo, a brand or readable text to the model.
- The operator's chat and the page call the same server step.
- A film already past its references is not redrawn; the new way starts with a film's reference round.
- Drawing and approval are free steps; only pictures count against the cap.

## 7. Edge cases

| Case | Handling |
|---|---|
| No size in the plan and none in the footage | Sizes assumed from general knowledge, marked assumed on the sheet, approved by the operator |
| Footage and plan disagree | Footage wins; the conflict is shown to the operator before drawing |
| A loose or living thing (broom, cloth, plant, animal) | Form sheet only: shape, sizes, how it is held |
| Something that cannot be drawn as a solid (mesh, water, dust, a bent pose) | Named on the sheet and given in words |
| A thing too complex to model in reasonable time | The helper says so; the thing falls back to today's way and the operator is told |
| More drawings than the model takes (Gemini: six object pictures) | At most two sheets per thing per call; the camera drawing always first on a shot |
| Vertical film | The camera drawing is made at the film's frame; thing sets are unchanged |
| The same thing in two states (dry and wet, before and after) | One model, the state as a fact; a side-by-side sheet when both are in one shot |
| Several shots of one place | One place description, one camera per shot; the first approved picture is a reference for the next |
| A client's exact object | Its footage frame or supplied picture stays the truth; a drawing only adds construction |
| A shot with no technical thing and no set positions | No drawings; today's way |

## 8. Failure modes

| Failure | What happens |
|---|---|
| A wrong fact gives a precise wrong drawing | Caught at the operator's approval, with sources and assumed sizes shown; nothing is paid before it |
| The helper's SVG is refused or does not render | The reason is returned; the helper fixes and sends again; no paid step |
| The drawing tool fails on the operator's machine | The thing falls back to today's way; the operator is told which thing and why |
| The model copies the drawing's look (colours, clean edges) | One colour per material on the model's copy; the GPT guidance; a check line "looks like a real photograph" |
| The model changes the framing | Check line against the camera drawing; made again on GPT Image |
| A state is lost (guard open) | States are in the must-be-true list and the check list |
| A posture no person can hold (a hand reaching backward, a body facing one way and working the other) | Front and back are marked on the drawn person; the posture rules are checked on the place's numbers before the drawing is shown; a check line "the working hand is in front of the body and the arm bends naturally" |
| The plan's layout makes the job impossible to stage | The drawer changes the layout by the least needed, may mirror it, and reports each change; the operator approves the drawing, not the plan's words |
| The checker fails or is unavailable | The picture is unchecked but can still be approved, as today; the operator sees "not checked" |
| Provider error or limit | Retried as today; no second charge for a picture that never came |
| The operator rejects the drawing twice | The helper asks one question in the chat about the fact in dispute |

## 9. Older ways

| Older way | Status |
|---|---|
| Gemini's own web look-up as the only truth for a thing without a source | Kept for things marked "no drawing"; retired for marked things |
| Start picture from the Blender box frame alone | Retired for shots that have a camera drawing; kept until the first film has run the new way end to end |
| Facts used only as check lines, not in the prompt | Retired: the must-be-true list is in every prompt |
| ASCII or words-only layout descriptions as the layout's source | Retired |

## 10. What a build would touch

| Part | Change |
|---|---|
| `plugin/` | The drawing tool (from `vw18/draw3d.py`, about 250 lines) and the helper's instructions for facts table, model and sheets |
| `server/app/visual_contract.py` | A drawing level and a drawing set on an element; a camera drawing on a shot |
| `server/app/visuals_stage.py` | Accept, store and approve drawing sheets; add them as parents; the prompt order of section 5; per-model guidance |
| `server/app/svg_scene.py`, `drawn.py` | Reuse the SVG rules and the Chromium render for sheets (text allowed on the operator's copy) |
| `server/app/image_check.py` | Check lines from the facts table; the drawings sent with the picture |
| `server/app/guide.py`, `guide_spec.py` | The camera drawing from the guide's scene description; the still's parents |
| `server/procedures/v3.json`, visuals stage only | The steps, the standard and the prompt rules |
| `chat_flow.py` | One chat item per drawing set |
| `design/35-decision-log.md` | The older ways of section 9 |

Not touched: analysis, clip log, stage 2, the brand library, and the intake, brief, script and voice code.

## 11. Time and cost seen in the trial

- Drawing tool run: under 3 seconds for all four shots.
- One picture: 27 to 39 seconds on either model.
- The whole five-scenario trial, including writing the drawing tool once: about 45 minutes on this session's clock, of which about 10 minutes were pictures.
- With the tool in place, a thing's model was 20 to 60 lines. A helper on the operator's side will be slower than this session; 5 to 15 minutes per thing is my estimate, not a measurement.
- Pictures: about ₹13 per Gemini picture and ₹6 per GPT picture, by my high guess.
- The whole test, all rounds: 35 pictures, about ₹322 counted (SK raised the limit from ₹300 to ₹5,000 on 14 Nov).

## 12. Implementation plan

Nothing here is built. This session has no working copy of the application to change; the build is the builder thread's, on its own branch, after SK says the workflow is final. No deploy without SK's yes. Each step below is small enough to test and switch on alone, and each states its tests first.

| Step | What is built | Area | Tests written first | Done when |
|---|---|---|---|---|
| 1 | **The drawing tool in the plugin**: one model, any view, hidden surfaces, two copies of a sheet; the person with face, chest, back and right arm marked. From `vw18/draw3d.py` and `things.py` (about 300 lines, standard Python, 3.9-safe). | both | Views of one model agree (a point lands where its numbers say in every view); the no-text copy holds no text and one colour per material; a person's front and back colours are present in every view; an empty model, a model behind the camera and a huge model are refused with a reason | The dovetail and wall sets come out the same as in the trial |
| 2 | **Posture checks** beside the guide's right-hand checks: hand in front of the shoulders, head within 45 degrees of the body, right side to the camera | B | One passing and one refused case per rule; the lab shot as planned is refused, the mirrored one passes; a seated person; two people | The check names the broken rule in plain words |
| 3 | **Drawing sheets on the server**: a drawing level and a set on an element, a camera drawing on a shot; accept, check as plain SVG, render, store; one chat item to approve a set, with sources and assumed sizes; a correction redraws free | both | A sheet with a script or a link is refused; a sheet over the size limit is refused; approval by exact content; a changed sheet needs approval again; an unapproved sheet is never a parent; no paid call in any of it | The operator can approve a set in the chat and on the page through the same server step |
| 4 | **Area A switched on**: approved drawings as parents of the reference set on Gemini; the prompt in the fixed order; check lines from the facts table | A | Parent order (footage frame first, then drawings); at most two sheets per thing; the how-to-read paragraph names every colour used; states and counts appear in the must-be-true list and in the check lines; a thing marked "no drawing" goes the old way unchanged | One film's reference round runs with drawings for its marked things |
| 5 | **Area B switched on**: the camera drawing from the guide's scene description; the start picture on GPT Image 2.6 with the new parents and prompt; the look reference as an option | B | The camera drawing and the Blender first frame place each thing within a small tolerance of each other; right-hand lines present; the look reference is the last image and carries its "take nothing else" words; a shot with no drawing goes the old way | One AI video shot runs: drawing approved, start picture made, take made from it |
| 6 | **The words**: the visuals part of the procedure (steps, standard, prompt rules), the older ways in the decision log, the version numbers | both | The procedure text names no film, brand or building subject; retired ways are refused by name | SK has read the procedure text |

Old ways, restated for the build: Gemini's own look-up stays for things marked "no drawing"; the start picture from the Blender box frame alone stays until one film has run Area B end to end, then is retired by name.

Not for this build: tidy automatic placement of labels on the operator's sheets (a known weakness; labels are placed by the helper for now); drawings for people's likeness; any change outside the visuals stage.

## 13. Not covered

- No video take was made from a start picture of this workflow.
- The posture rules were tried on one shot only (three pictures). The 45-degree head turn is Claude's figure, not a tested limit.
- One run per case in the trial; no blind judge; the application's own checker was not run on the pictures.
- Label placement on the operator's sheets is still weak and needs work in the build.
- Whether a helper can write a correct model without this session's context is untested; the first film should be watched for it.
- People: the drawing places and poses; likeness stays with today's reference pictures.
