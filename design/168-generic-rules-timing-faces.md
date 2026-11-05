# 168 — SK's four questions on design/167: generic rules, timing order, the scene flag and 24 fps, faces and emotion (5 Nov 2026)

## 1. Generic rules, with the specifics as examples

The specific rules in design/167 D2 ("tool contact drawn", "facing drawn") are instances of one problem: **anything the cartoon leaves unstated, the model fills in from its own habit, and where our intent is not the habit, the result is wrong.** The mortar thrown at the foot of the wall, the mason turning to face the camera, the bricks going back into the pan: each was a detail we had not drawn, filled in by habit. So the generic rules, each with the examples that found it:

| # | Generic rule | Examples that found it |
|---|---|---|
| G1 | **Draw what decides the outcome.** Any detail the shot's meaning depends on is drawn explicitly, in contact, with its result; what the model would do by habit anyway is left to it. | where a tool acts: tip on the course, mortar left there (160); which way a person faces: nose, eyes, back of head, feet (160); what each hand holds (158); which way a transfer goes and where the thing lands (162, 163) |
| G2 | **The film is never asked to keep a tally.** No count of identical things is stated or implied; shots are designed so no count matters. | bricks, the pan, the barrels (158–166) |
| G3 | **A change is seen, not implied.** The camera stays on anything that changes state, from before the change to after it; the thing that changes looks different from what it joins, in the film. | the pan at the cut (162 → 163); new bricks on an old heap, blue drums by white (165, 166) |
| G4 | **Every second has a drawn cause.** No gap in the action; a closing action with a margin; the drawn pace is the model's measured pace. | the refilled pan, the fumbling, the invented wide shot (158); the early lift (160); the barrels (166) |
| G5 | **Things that must be told apart look apart.** No two things of one shape and colour in a frame unless they are the same thing. | the pile became the wall; mortar in the pan (158, 162) |
| G6 | **Cuts and moves are unmistakable or absent.** A cut changes angle or size clearly and is named in the prompt; a camera move is long and slow or not there. | the push-in read as a cut (159, 164, 165); the mild cut ignored (166) |
| G7 | **The cartoon, the prompt and natural behaviour never disagree.** When they do, the model serves all three and invents. | the right-hand cup (the thread's F5); the drawn pace (166) |
| G8 | **Nothing in the inputs that is not in the shot.** Photographs only of what is in frame; no word that names equipment or a state of building. | the tripod, the trowel in the pan shot, "half-built" (162, 165) |

The drawing helper's skill and the prompt step carry G1–G8 as the rules and the table's examples as examples, so the next system reads the problem, not a list of tools.

## 2. Timing: the cartoon decides the seconds, not the list

What the runs showed: the model follows the cartoon's cuts and the order of actions to the second, and performs each action at its own pace regardless of what we drew (2.4 in design/167). So a shot list with seconds written before the cartoon is a guess that the cartoon then has to honour and the model then ignores. SK's instinct is right, and it becomes the rule:

- The plan gives **the beats in order and the gap's total seconds**, which the narration fixes and which cannot move.
- The drawing helper lays the actions out at the **measured pace** (the speed table) and draws the cuts where the beats change. **The cartoon's timeline is the timeline.**
- The server **measures the cartoon** (its cuts, and the action marks the helper writes as it draws) and **writes the timecoded prompt from the cartoon**, never the other way round.
- If the actions at natural pace do not fit the gap's seconds, the plan is revised (fewer actions, a hold, a longer gap at the next plan revision), never the pace squeezed. The check helper refuses a cartoon whose actions run faster than the table.

Did the cartoon ever form our time frame? No: I drew every cartoon from a list I had written first, and the model's pace deviated from both. From here the list is beats, the cartoon is seconds.

## 3. The scene flag, and 24 fps

**The flag** is one yes/no mark on a scene in the plan: `one_take: true` means "make this whole scene as one clip with the cuts inside it", instead of today's one clip per shot. It is how multi-angle inside one take is switched on (design/155 §2), and it works today with a timecoded prompt and no cartoon (design/156 D). It is not the list of scenes; it is a property of one scene.

**24 fps** changes nothing in time or cost. Rendering 240 frames instead of 150 takes a few seconds more on the server. Omni charges the input video by the second (5,792 tokens a second), not by the frame, and makes 24 fps output either way. Every run in 165–166 was 24 fps and ran in the same 80–110 s.

## 4. Faces and emotion: the camera play must not strip the people out

What we avoid is inventories, not people. The rule set gains a section so the "nothing to count" framing never produces a film of hands and heaps:

| # | Rule |
|---|---|
| E1 | **Every scene has at least one shot on a face**: concentration, effort, a reaction, a look between two people. An extreme close-up of the mason's eyes as he sets a brick is a correct shot. |
| E2 | **A face is never cropped by the frame to hide a count.** If a group must be out of frame, it is out by angle or by what the hands hold, not by cutting the head. (T4's shot 1 cut the top of the helper's head to hide the pan; that was wrong.) Headroom is a check line on the cartoon. |
| E3 | **A tight shot on an action may hold the face in the same frame**: over the shoulder, hands and face, the brick and the eyes above it. |
| E4 | **A facial moment gets its own time**: a longer, closer, continuous shot with a hold of at least a second (the thread's F3), drawn with the expression (brow, eyes, mouth) and named in the prompt as action plus emotion ("his eyes narrow on the brick; concentration"). |
| E5 | **The facing rule gives the look a direction**: who looks at whom, drawn, so a reaction lands on its cause. |
| E6 | **Faces are identity**: the photographs of the people in the shot always go in; a face shot is the one place a dense frame may be tried, since it is the one untested case where a half-second matters. |

These sit beside G1–G8 and D1 as the fourth group of rules: staging (D1), drawing (G), emotion (E).

## 5. The inputs, confirmed

The cartoon video alone with the photographs and the prompt, as SK agrees (it is an edit in Omni). Dense frames stay off; the one place they may be tried is E6.
