# 167 — The animatic round closed: every learning, and the direction from here (5 Nov 2026, for SK's agreement)

Twenty-five paid Omni runs on 5 Nov: six on the park scene (design/156), thirteen on the mason scene (157–164), six on the pan, the barrels and their text-only controls (165–166), plus SK's own thread before (design/154). Each learning below names the run that proved it. Section 5 is the direction; SK agrees or strikes items by number.

## 1. What the cartoon guide controls (proved)

| # | Learning | Proved by |
|---|---|---|
| 1.1 | **Positions and sides.** Drawn from one fixed world, the left-to-right order of people and things holds through every angle; the earlier "pile changed sides" failure never recurred. | 157 (three angles), 160, 163 |
| 1.2 | **Facing.** A person faces the way the drawing faces, once the drawing shows a nose, eyes or the back of a head and the feet. Without that, the model picks and may change its mind mid-shot. | 160 (the mason's split-second turn, then fixed) |
| 1.3 | **Cuts and their seconds.** Cuts land within 0.1 s of the drawing when the two framings differ clearly. | 156 (B, D), 157, 159, 160, 163 |
| 1.4 | **Order of actions and their seconds.** Sip, cup down, yawn, arm, turn, look; walk, squat, set down, lift; all in order, at the second. | 156, 157, 163, 165 T1/T3/T4 |
| 1.5 | **Tool contact and its result**, once drawn: the trowel's tip on the course, the mortar staying there. | 160 |
| 1.6 | **Identity from two or three photographs** holds through every run; a colour on a large distinct object (the yellow handle) carries. | 156, 157, every later run |
| 1.7 | **A single object passed between two people** is tracked through repeated rounds. | 165 T3 (three hand-offs to the wall) |
| 1.8 | **A handful of identical things moved one or two at a time** go the right way every time. | 165 T1 (two onto three), T5 (two per visit), 166 (one barrel at a time) |
| 1.9 | **A difference the film may show keeps two kinds apart** and makes a transfer legible: new bright bricks on an old dusty heap, blue drums beside white. | 165 T2, 166 t6b |
| 1.10 | **Guide marks do not leak at the sizes used**: numbers, the words PILE/PAN/WALL, colour tags on the video path. (A still of a purple brick did leak once on the frames path.) | 162, 163, 165; the leak: 159 CF |
| 1.11 | **SK's staging shape works first time**: establish wide, then tight on the action, hands and one object, the group's edges outside the frame, nothing to count. | 165 T4 |

## 2. What it does not control (proved)

| # | Learning | Proved by |
|---|---|---|
| 2.1 | **Counts of identical objects**, at any size, in any input: bricks six onto nine, a pan emptying, five barrels off a plank. The direction is right; the running total drifts. | 158–166, every count run |
| 2.2 | **It is the model, not the guide.** The same scenes as text only drift the same way. The cartoon neither overloads nor fixes it. | 166 controls |
| 2.3 | **State does not survive a cut.** A container full before a cut arrives empty after it; a pile shrinks at a cut; the park's cup count changed at the bench close-up. Keeping the camera on the change fixes continuity, not the count. | 162 → 163; 156; the thread's F4 |
| 2.4 | **Pace is the model's own.** Drawn speed is ignored: a pair of bricks 1.5 s, a barrel 1.6 s, not the 0.9–1.2 s drawn. A closing action drawn too early collides with unfinished work. Measured speeds go into a table; a margin of a second before the closing action. | 158, 159, 163, 165 T2, 166 |
| 2.5 | **Empty seconds get filled** with invented action: refilling the pan, fumbling, a cut to a wide. Every second must have a drawn action. | 158 |
| 2.6 | **A gentle push-in reads as a cut about half the time; a mild cut reads as none.** Camera moves must be slow and long or absent; cuts must change angle or size clearly, and the prompt should name them. | 159 CF, 164, 165 T2 (cuts); 166 (no cut) |
| 2.7 | **Two things of the same shape and colour in one frame merge**: the pile became the wall; mortar appeared in the pan. | 158, 162 |
| 2.8 | **The model's taste is not a failure**: the wall is always taller than drawn. Checks judge positions, counts, direction, timing, not degree. | every mason run |

## 3. Inputs, prompt and API (proved)

| # | Learning | Proved by |
|---|---|---|
| 3.1 | **The cartoon goes in as the edited input video**, up to 10 s, one per call. A video "reference" is capped at 3 s and is for likeness; two videos in one call are unsupported. | 155 (Google's page, our fact sheet) |
| 3.2 | **Video plus a timecoded prompt** keeps direction, camera moves and timing. Frames alone keep timing and are cheaper but lose the direction of a back-and-forth, can leak a tag, turn a framing change into a cut, and pull an action early. | 158 (direction), 159, 160, 164 |
| 3.3 | **Dense frames beside the video added nothing** on five tries and once pulled the closing early; once the API refused the frame set twice with a generic error. | 160, 162, 163, 165 T4 (refused), T5, 166 |
| 3.4 | **Text alone with a timecoded shot list already gets the cuts and the order** (today's method plus seconds). | 156 D |
| 3.5 | **Send only the photographs of what is in the shot**: a tools photo put a trowel and a board into a shot with no mason. | 165 T5 vs 166 |
| 3.6 | **Never name camera equipment**: "on a tripod" put a tripod in the scene. Say "the camera does not move". | 165 T5 |
| 3.7 | **Never say "half-built"** or any word that invites building in progress; name each brick thing and say the wall does not grow. | 162 |
| 3.8 | **The guide sentence** ("keep every shot, cut, angle, move, timing, position, facing and direction; change only the look; do not copy the cartoon style") and the **state sentence** (what moves, where it ends, never back) are the two fixed lines. | 156 A, 158–163 |
| 3.9 | **Our house shape's frame tags are deprecated** by Google and are not sent on animatic takes. | 155 |
| 3.10 | 24 fps cartoons at 1280×720 are accepted and behave as 15 fps ones did; a run costs about ₹90 for the take plus ₹8 for the video input and takes 80–110 s. | 165, 166 |

## 4. The thread's own findings that held (design/154)

F1 the guide-only sentence; F3 a longer, closer, continuous shot with a hold for a facial moment (not re-tested on the video path); F4 props must be counted in the prompt and never touch an empty hand (now superseded: do not count identical things at all; design shots so no count matters); F5 guide, prompt and natural behaviour must agree (the right hand; now also the pace); F6 one change per run; F8 conflicts, not length, break a prompt.

## 5. The direction (for agreement, by number)

| # | Decision | From |
|---|---|---|
| D1 | **Scene design first, by the staging rules**: establish wide, cut to tight on the action; one action per shot; hands and one object; a group's edges outside the frame; a handful moved one or two at a time; the thing that changes state looks different from what it joins, in the film; the destination is a hand, a row, a wall top, never a heap of the same kind; no count of identical things stated anywhere; a shot that needs a true count is footage, a still or the drawn route. | 1.7–1.11, 2.1–2.3, 2.7 |
| D2 | **The cartoon is the staging instrument**: one fixed world; facing drawn; tool contact drawn; things in one frame differ in shape and colour; no body hides an object; the contact point in frame; every second has a drawn action; a closing action with a second's margin; cuts unmistakable; camera moves slow and long or none; rendered at 24 fps; key stills checked before anything is sent. | 1.1–1.6, 2.4–2.6 |
| D3 | **The input is the cartoon video plus the photographs of what is in the shot plus the timecoded prompt.** Dense frames are off by default; they may be tried only for a half-second facial moment, which is untested. | 3.1–3.5 |
| D4 | **The prompt**: the guide sentence; the state sentence in look terms; fixed positions; each shot with seconds, its cut named; "the camera does not move"; no camera equipment, no "half-built", no counts of identical things; only the one changing thing described as changing. | 3.6–3.8 |
| D5 | **The speed table** (first entries: a pair of bricks lifted and set 1.5 s; a barrel from waist height 1.6 s; a step 0.5–0.6 s; a squat 1.0 s; a head turn 0.6–0.8 s; a hand-off round 2.4 s) is a should line the check helper measures on the cartoon. | 2.4 |
| D6 | **Build order**: (i) the `one_take` scene flag and the timecoded shot list on takes, which work today without a cartoon; (ii) the staging rules into the plan step and the plan check (no counts; a changing thing must differ; no cut between a state and its change; cuts must differ clearly); (iii) the animatic: the figure library, the drawing helper, the check helper, the Files API upload, the Takes-step card. The requirements note design/161 stands with these amendments. | 3.4, 161 |
| D7 | **The documentary default** is one or two angles and a hold; advertisement and drama get the full grammar. | 154 §9 |
| D8 | **Review practice**: half-second strips at 480 px or larger before any verdict on counts; SK watches the video; one run per variant decides a direction, not a rate. | this round |
| D9 | **Not pursued**: frames-only path; the thread's two-video continuity; the canvas; numbers and labels as the fix for counts (they are harmless but do not fix it); WAN and Kling stay SK's own side tests until one beats Omni on a count. | 155, 162–166 |

## 6. Untested, named

- A half-second facial expression on the video path with F3's longer hold (the park's eyebrow).
- A cartoon scene cut between real footage on both sides.
- Scenes over 10 s split into segments with continuity by the sets.
- The figure library's effort and the helper's first-pass quality.
- The API's refusal of one frame set (T4).
