# 163 — The mason test, part 6: no cut between a state and its change (5 Nov 2026)

SK's decision after design/162: try it without the cut. The side view (the squat, the pan set down) and the close view (the bricks from the pan to the pile) became **one continuous shot from 3.5 to 10 s**, a slow push-in between 5.4 and 6.6 s, the pan with its six numbered, coloured bricks never leaving the frame. Everything else as design/162: numbers, labels, the distinct pile, the three brick things named in the prompt, thirteen dense frames cut from the cartoon video (one more at 6.0 s, the pan full before the first lift). One run (FVF), 110 s, 76,892 input tokens.

## Results (`163-assets/sixteen-moments.png`: cartoon on the top two rows, the output below)

| What | Result |
|---|---|
| Cuts (cartoon: one, at 3.5) | **one, at 3.46**; the push-in came as a camera move, no cut |
| The pan's bricks after the squat | **present**: the pan is set down full (3.8–5.4 s) and is still full when the close view arrives (6.0–6.4 s) |
| Shot 3 action | the hands take bricks **from the pan** and set them **on the pile**; the pile grows (6.8–8.4 s); nothing goes back |
| The pile across the push-in | the same heap, growing; no re-imagining |
| The closing action | the helper lifts the pan and rises at 9.2–9.9 s, on time, **but two or three bricks are still in the pan when it is lifted** |
| Text, numbers, labels | none in the output; every brick red |
| The mason | back to the camera, on the camera's side, trowel on the wall top |
| The wall | finished, tall (the model's taste, as always) |

## What it says

1. **The rule is proved.** Without a cut between the state and its change, the six bricks survive into the placing for the first time in six runs on this scene. With the cut (designs 158, 159, 160, 162) the pan arrived empty or the pile shrank every time; the park's cups (design/156, the thread's F4) failed at the same kind of cut. **A change of state happens inside one shot, with the thing in view before, during and after; a scene never cuts between the last sight of a state and its change.** This goes into the requirements note (design/161 §6) as a plan check on `one_take` scenes.
2. **What is left is pace, not continuity.** The model places a pair in about 1.2 s, not the 0.9 s I drew, so the third pair was still in the pan when the drawn closing action (anchored by the frames at 9.2 and 9.8 s) began. The reference-speed table gets its first measured entry: **a pair of bricks lifted from a pan and set on a pile: 1.2 s**. The drawing fix is to start the placing at 5.6 s, right after the pan is down, and keep 1.0 s of closing at the end; or draw four bricks instead of six for a shot of this length.
3. **Dense frames behaved** this time: no early action, because the prompt ties each frame to its second and the video now has no cut for a frame to be mistaken for.

## The state of the method after six runs on this scene

| Rule | Proved by |
|---|---|
| One fixed world; every shot a crop of it | 157 |
| No cut between a state and its change | **163**, and the failures of 158–162 and the park |
| A person shows a facing direction | 160 |
| A tool touches what it acts on; the result is drawn where it lands | 160 |
| Things in one frame never share shape and colour (the pile and the wall) | 162 |
| Numbers, words and colour tags on what changes state, declared a guide; they do not leak at this size | 162, 163 |
| Human pace from measured speeds; a closing action in the last second | 158, 159, 163 |
| Dense frames of quick moments, each tied to its second, beside the video | 162, 163 |
| The operator checks the key stills before anything is sent | every round |

## Not covered

- One run; judged on stills at 320 px; SK has the video and the count of bricks on the pile is his to confirm.
- The pace fix (point 2) is not yet run.
