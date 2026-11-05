# 158 — The mason test, part 2: why the bricks went the wrong way, and the video path (5 Nov 2026)

SK watched the two frame-path runs of design/157 and saw what my six-moment sheet missed: in shot 3 the helper moves bricks from the pile back into the pan and then stacks again (M1), or stares into the empty pan and reaches for the pile (M2). SK asked for the cause, and for the same setup run with the cartoon video sent in. Both done; the quarter-second strips of shot 3 for all four runs are `157-assets/shot3-quarter-second-all-four.png`.

## What the strips show (shot 3, 6–10 s, every 0.25 s)

| Run | Inputs | 6.0–7.0 s | 7.0–8.0 s | 8.0–10 s | Verdict |
|---|---|---|---|---|---|
| M1 | 10 frames + 3 photos | bricks lifted from the pan to the pile | **bricks are back in the pan** | the pan holds three or four bricks again while the hands work the pile | reversal, as SK saw |
| M2 | 10 frames + 3 photos | bricks lifted from the pan to the pile | the pan is empty | **the hands reach into the empty pan again and again** | confusion, as SK saw |
| V1 | cartoon video + 3 photos | bricks lifted from the pan to the pile | the pan is empty; its inside reads as grey mortar | the hands arrange and pat the pile | direction right; filler at the end; the pan's inside confused with mortar |
| V2 | cartoon video + 3 photos | bricks lifted from the pan to the pile | the pan is nearly empty; the hands place on the pile | the hands tidy the pile; **at 9.33 s the model cuts to a wide shot of its own** | direction right; an invented fourth shot at the end |

Cuts measured: V1 3.46 and 5.96 s; V2 3.46, 5.96 and 9.33 s (the cartoon: 3.5 and 6.0). M1 and M2 were 3.46/6.0 and 3.42/6.0.

## The causes

1. **One frame per second cannot say which way a back-and-forth action goes.** The hands travel pan → pile → pan every 1.3 s. Sampling once a second catches them at the pile holding bricks, then at the pan empty, then at the pile again. Those stills fit "bricks from pan to pile" and "bricks from pile to pan" equally. The video carries the direction; both video runs got it right, both frame runs did not. **Confirmed.**
2. **The shot's action ran out before the shot ended, in all four runs.** I drew six bricks placed two at a time over 3.9 s, the pan emptying at 9.9 s. The model empties a pan of six bricks in about 1.5 to 2 s, because real hands do. Then two to three seconds of shot had nothing drawn for them, and each run filled the time its own way: V1 patted the pile, V2 cut to a wide shot, M1 put bricks back, M2 fumbled in the empty pan. The drawing rule from this: **a shot's drawn action must fill its seconds at a human pace, and the shot must end on a drawn closing action** (the helper lifts the empty pan and stands; or the shot is shorter). The thread's F5 said "the guide, the prompt and natural behaviour must agree"; this is the same rule on timing.
3. **My cartoon under-drew the evidence of direction.** The bricks standing in the pan were small; the bricks added to the pile were almost the pile's colour. A storyboard that wants to show a transfer must show the source emptying and the destination growing in every frame, unmistakably.
4. **Two round grey things.** The pan and the mortar on its board are both grey and round in my references and in the cartoon; V1 ended with mortar in the pan. A drawing and reference rule: things that will be in the same frame must not share shape and colour.

## What this changes in design/156's conclusion

design/156 found the edited-cartoon path "loosest in timing" and dropped it. That was the prompt, not the path: the park edit prompt carried no seconds. Here the edit prompt carried the timecoded shot list and both video runs cut within 0.04 s of the cartoon. So:

- **The video path with a timecoded shot list keeps both the timing and the direction of motion.** It costs the Files API upload, about ₹8 of input a take, and the 10-second limit on the input video, all known from design/155.
- **The frames path keeps the timing and is cheaper, but loses the direction of any action that goes back and forth.** It can be repaired in part (frames at the pick-up and the put-down instead of once a second; the source and the destination drawn so their counts read at a glance), but a still can never show which way a hand is moving.
- Neither path fixes cause 2; that is a drawing rule, needed on both.

Recommendation: **the video path with the timecoded shot list becomes the primary path, the frames stay as the cheap path for shots with no back-and-forth action**, decided per shot by the check helper. The deviations of the video runs (filler, one invented cut) all trace to cause 2 and should disappear once the shot is drawn to fill its seconds.

## Next test, if SK agrees

Redraw shot 3 only: twelve bricks in the pan, placements at a human pace, a closing action (the helper lifts the empty pan and rises) in the last second; the pan drawn as a shallow wide silver dish and the mortar as a grey heap on a brown board. Run the video path twice and the frames path twice with the same cartoon. Expected: no filler, no reversal on the video path; the frames path still at risk on direction.

## Not covered

- Still two runs per path on one scene.
- The video runs were judged on quarter-second stills, not watched; SK has both files.
- The model's "invented cut" at 9.33 s in V2 was not investigated beyond cause 2.
