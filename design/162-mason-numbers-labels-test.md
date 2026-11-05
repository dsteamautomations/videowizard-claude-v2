# 162 — The mason test, part 5: numbers, labels, a distinct pile; video plus dense frames (5 Nov 2026)

SK's findings on design/160's runs: the pile lost bricks between the walking shot and the close shot; in the video-plus-frames run the close shot showed the wall under construction at 7–8 s and the pan tilting in mid-air; SK chose video plus high-density frames as the only path from here and asked for numbers and words on the cartoon. My diagnosis (reply to SK): the pile and the wall were the same thing to the model (same bricks, same pattern, side by side) and the prompt said "half-built"; the pile's count was never fixed; the closing frames pulled the lift early.

## What changed

Cartoon (`162-assets/draw.py`): the pile is a loose, slightly skewed stack lying on the ground with a shadow, lighter in tone than the wall; its nine bricks are numbered 1–9; the pan's six bricks keep their colours and are numbered 10–15, and keep both onto the pile; the words PILE, PAN and WALL once on each, black on white. Prompt (`162-assets/prompt.txt`): no "half-built"; three brick things named and told apart (the wall finished at three courses and never growing; the pile a loose heap of nine growing to fifteen; the pan six then empty); the numbers, words and colours declared a guide to identity and state that never appear; the dense frames declared to belong to their seconds and never earlier. Inputs: the cartoon video, the twelve dense frames at the quick moments, the three photographs. One run (EVF), 111 s, 75,707 input tokens.

## Results (`162-assets/sixteen-moments.png`: cartoon on the top two rows, the output below, at sixteen moments)

| What | Result |
|---|---|
| Cuts (cartoon 3.5, 6.0) | 3.38, 6.0 |
| Text, numbers, labels in the output | **none**; every brick red |
| The wall | finished and tall in every shot; **no longer "under construction"** in the close shot; the pile reads as a loose heap on the ground, separate from the wall |
| The mason | back to the camera, on the camera's side, trowel on the wall top, all shots |
| The closing action | the helper lifts the empty pan and rises at 9.0–9.6 s, **at its second**, no early lift, no repeat |
| The pan at the cut to shot 3 | **empty from the first frame of the close shot**; the six bricks are not in it |
| Shot 3 action | the hands move bricks about on the pile and set them down; the pan stays empty; nothing goes back into the pan |
| The pile's count across shots | the walking shot shows a loose scatter plus a stack; the close shot a stack of about nine; the pan's six never arrive on it |
| Wall height | eight or more courses, not three (as in every run so far) |

## What it says

1. **Three of SK's four findings are fixed.** The pile is no longer the wall (a distinct drawing and a prompt that names the three brick things and says the wall does not grow). The closing action is on time (the frames told to keep their seconds, and the lift drawn only after the last brick). No numbers or words leaked at this size, so SK's labels are safe to use.
2. **One remains, and it is the real one: state does not survive a cut.** The pan holds six numbered, coloured bricks in the cartoon's last frame before the cut and in the first frame after it. The output drops them at the cut and starts the close shot with an empty pan. The same happened in design/160 (the pile shrinking at the cut) and design/158 (five bricks, then four). A cut is a new composition to this model; counts and contents are re-imagined from the prompt's general description, not carried from the previous shot. Labels and numbers on the cartoon did not change that, because the model is not reading state across the cut at all.
3. **Therefore a drawing rule, and a planning rule:** **a change of state happens inside one shot, with the thing visible before, during and after; never cut between the last sight of a state and its change.** Here the pan must be seen full in the close shot before the first brick leaves it: start the close shot earlier with the pan large and plainly full, or better, make the move from shot 2 to shot 3 a push-in with no cut, so the pan never leaves the frame between "six bricks" and "first pair lifted". Cuts are kept for moments where nothing countable changes hands (the walk, the squat).
4. **The wall's height is the model's own taste** on every run and is not a state; the check should not count it as a failure. If a client's wall must be three courses, that is an exact fact for the drawn route, not for AI video.

## Next test, if SK agrees

Same cartoon, two changes: shot 2 and shot 3 become one continuous shot (a push-in from the side view to the close view, 3.5–10 s, the pan in frame the whole time, full until the first pair leaves it); and the close view frames the pan large in the lower third. Video plus the dense frames, one run. Expected: the six bricks reach the pile. If they do, the rule in point 3 goes into the requirements note (design/161 §6) and the plan check: a `one_take` scene may not cut a shot boundary between a state and its change.

## Not covered

- One run; judged on half-second stills at 320 px; SK has the video.
- Whether labels leak at larger sizes or on a closer shot: not tested.
