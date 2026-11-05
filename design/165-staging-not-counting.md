# 165 — Staging, not counting: what nine runs say, the rules for the cartoon and the prompt, and four tests (5 Nov 2026)

## 1. The inference (SK: "that's the type of observation we are looking for")

Across the nine Omni runs on the mason scene (design/157–164) and the six on the park (design/156), the cartoon reliably controlled **staging**: who stands where, which way each person faces, the camera angle and framing, the cuts and their seconds, a camera move, the colour of a tool's handle, the identity of two people from two photographs. It did not control **manipulation of many identical objects**: how many bricks lie on the ground, how many are in the pan, which way a brick travels, whether a container is empty. Every run got the staging right and every run got the bricks wrong in some way, whatever the input (video, frames, both; tags, numbers, labels; a cut, no cut). The guide wins at the level of composition and loses at the level of hands and counts, where the model's own habit ("a helper arranging bricks") takes over. The tags could not help because the film was not allowed to show them: six identical red bricks are untrackable to the model once the colours are gone. The cut made the loss worse (design/162, 163) but was not the cause; the park's cups were the same failure (design/156, the thread's F4).

## 2. The rules for the instructions that build the cartoon and the prompt

These go into the drawing helper's skill and the prompt-writing step (design/161 §4), above the drawing rules of design/160. They replace "state every count" with "design the shot so that no count matters".

**Ask of the cartoon only what it has proved it controls:**
- Where each person stands and which way they face; the camera's angle, height and framing; each cut and its second; a camera move; the order of actions and their seconds; a single tool touching a single thing; the colour and identity of people and of one or two large, distinct objects.

**Do not ask of it what it has failed at:**
- Counts of identical objects (bricks, cups, coins, fruit, tiles). Neither the cartoon nor the prompt states a number of identical things; the prompt says "some bricks", "a few", "a heap", never "six".
- The contents of a container seen filling or emptying.
- The transfer of identical items from one group to another, where the result must be a correct count.
- Small objects in a wide frame.

**Design the shot around that:**
- Frame close enough that the thing the shot is about is large: a medium close-up, not a wide; the group's edges outside the frame, so no count is implied (SK's framing: the helper from behind in medium close-up with "some bricks" in the pan; a close-up of hands setting a brick on a lump whose edges leave the frame; never the whole heap).
- Show the action, not the inventory: hands set a brick down; a trowel spreads mortar; a pan is lifted. Do not show a heap before and after and expect the difference to be right.
- When a change of state must be seen, keep the thing in view through the change (design/163) **and** make the changing thing look different from what it joins, in the film itself, not only in the guide (new bright bricks on an old dusty heap; a red cup among steel tumblers). If it cannot look different, do not show the change.
- One moving thing per shot where possible; two people passing one object is safer than one person and a heap.
- Where a count or an inventory truly matters to the film (a client's exact wall, a measured stack), it is not an AI video shot: footage, a still, or the drawn route.

**In the prompt:**
- Describe composition, facing, camera, cuts, seconds, the look of people and large objects, and the one action per shot. Describe quantities in words that do not count ("a pan of bricks", "a heap").
- Keep the state sentence for the one thing that changes, in look terms ("the bright new bricks end on top of the dusty heap"), not in numbers.

## 3. The four tests (one run each, 24 fps cartoons, video plus dense frames, the three photographs)

| Test | What it asks | Why |
|---|---|---|
| T1 tiny numbers | two bricks in the pan, three on the ground, one transfer, 6 s, one shot | is the limit the number of identical things? |
| T2 differences the film may show | the no-cut scene with new bright bricks in the pan and an old dusty heap, pace fixed (1.2 s a pair from 5.6 s) | does a visible difference let the model track the transfer? |
| T3 hand-off | one brick at a time from the helper's hand to the mason's hand to the wall top, three times, 8 s, one shot | is a thing passed between hands tracked better than a thing added to its own kind? |
| T4 SK's staging | medium close-up behind the helper with "some bricks" in the pan; a close-up of hands setting two bricks on a lump whose edges leave the frame; a close-up of the trowel; no counts anywhere | does a shot designed by the rules above come out clean? |

## 4. Results (review sheets `165-assets/review-t*.png`: every half second at 480 px, the cartoon above each output frame)

| Test | Cuts | What happened | Verdict |
|---|---|---|---|
| **T1 tiny numbers** (6 s) | none, as drawn | the helper squats with a pan of two bricks and a heap of three; he lifts the two together and sets them on the heap; the pan is empty; he takes it, lifts it and stands holding the empty pan; the heap ends with about five | **pass**: at two and three the count holds, the direction holds, the container ends empty |
| **T2 new bricks on an old heap** (10 s) | 3.5 as drawn; **the push-in became a cut at 5.6** | the new bricks are bright and clean in the pan and the heap is dusty and dark in every shot; the hands take new bricks from the pan and set them on the heap, and the **new ones stay visibly new on top of the old**; nothing goes back; **the pan still holds two or three new bricks when it is lifted at 9.2 s** | **pass on tracking, fail on pace**: a visible difference lets the model keep the transfer straight; the placements again ran slower than drawn, even at 1.2 s a pair |
| **T3 hand-off** (8 s) | none, as drawn | three times: the helper bends to the pan, lifts one brick, holds it out; the mason's hand takes it; the mason lays it on the wall top, where it stays; the helper's hand returns; three bricks end in a row on the wall | **pass**: one object between two people is tracked through all three rounds |
| **T4 SK's staging** (10 s) | with the dense frames: **refused twice** by the API after about 35 s, `INVALID_ARGUMENT`, "There was a problem processing your request", no usage, no detail; with the video and photographs only: cuts 4.04 and 7.5 as drawn | medium close-up from behind, the pan with some bricks on his head, the mason ahead at the wall; cut to a close-up of hands setting one brick, then a second beside it, on a lump whose edges leave the frame; cut to the mason's trowel with the yellow handle spreading mortar, back to the camera | **pass** (video only): a shot designed by the rules of section 2 came out clean with nothing to count. The refusal of the frames version is unexplained; the same frame set shape (16 frames) was accepted on T3, so it is the content of some frame, not the count |

What the three say together, on top of section 1:

- **The limit is the number of identical things, not counting as such.** Two and three held (T1); six on nine did not (every earlier run). A handful is safe; a heap is not.
- **A difference the film may show is enough to track a transfer** (T2). The tags failed because the film could not show them; real differences, new against old, survive and do their job. Rule 2 of section 2 ("make the changing thing look different from what it joins, in the film itself") is proved.
- **One object passed between two people is the safest state change there is** (T3). It is also the most filmic: a hand-off is an action, a heap is an inventory.
- **Pace is still the open fault.** T2's pan was not empty at the lift even with 1.2 s a pair. The model's own pace for "two bricks from a pan onto a heap" looks nearer 1.5 s. The reference-speed table takes 1.5 s, and the closing action is drawn only after a margin of a second.
- **T4 is the shape of the answer**: SK's framing, medium close-up, hands and one brick at a time, the heap's edges outside the frame, no counts anywhere, came out clean at the first attempt.
- **The push-in became a cut again** (T2, as in design/164), this time with the video present. A slow push-in over 1.2 s is read as a cut about half the time; a longer, gentler move (3 s) or no move is safer.


## 5. SK's question after T3, and T5

SK: was T3's success because the start and the end of the small action were close together? And a test: the helper walks in, takes two bricks from the pan, walks out of the frame (dumping unseen), comes back, takes two more; three times; does the pan's count diminish?

My reading: distance is not the difference. In T1 the pan and the heap were a hand's width apart and the count held; in T3 the brick travelled across the frame from one man to the other and the count held; in the earlier runs the pan and the heap were adjacent and the count failed. What the passes share is **few objects** (two, three) and **a destination that is not a heap of the same kind** (a person's hand, the wall top, or a heap of three). What the failures share is six identical bricks joining nine identical bricks. SK's test isolates the one thing left: the pan's own count as it is emptied, with no destination in frame at all.

T5 (`165-assets/prompt-t5.txt`, `tests4.py` t5): one fixed side shot, 10 s, the pan of six large in the frame; the helper walks in from the left, squats, takes two, walks out right, comes back empty-handed; three times; the pan goes 6, 4, 2, 0. Run twice in parallel: video plus sixteen dense frames, and video only (after T4's refusals). Results in section 6.

## 6. T5 results (`165-assets/review-t5f.png`, `review-t5v.png`)

| | t5f: video + 16 frames | t5v: video only |
|---|---|---|
| Cuts | none, as drawn | none, as drawn |
| The action | the helper walks in from the left, squats, takes two bricks, stands, walks out right, three times; nothing comes back | the same |
| The pan's count | starts at about four (drawn: six); fewer after each visit; **two left at the end** | starts at about four; fewer after each visit; **empty at the end** |
| Extras | a **tripod standing in the frame** on the left | the same tripod; a trowel and a mortar board beside the pan |

- **The container's count is tracked loosely, never exactly**, even in a fixed shot with the pan large and nothing else in the frame. The direction (bricks leave, never return) and the per-visit quantity (two, every time) are right; the starting count and the running total are not. This is the firmest evidence that counts of identical things are not for this model.
- **"The camera on a tripod" put a tripod in the scene.** Any word naming camera equipment is drawn. Prompt rule: "the camera does not move", never a mount, a rig, a lens.
- **A reference picture of things not in the shot pulls them in**: the tools photograph brought a trowel and a mortar board into a shot with no mason. Rule: send only the pictures of what is in the shot (the plan's `element_ids`; the server already refuses the rest by name on takes).
- The dense frames gave nothing on this shot; the video-only run was truer at the end, as in T2.

## 7. Where this leaves the method

Thirteen runs on the mason scene (design/157–165) and six on the park. The cartoon is a reliable instrument for **staging** and a poor one for **inventory**. The build in design/161 stands, with section 2 of this note added to the drawing helper's skill and the prompt step, and three lines added to the plan check: no counts of identical things stated anywhere; a changing thing must look different from what it joins, in the film; a cut never falls between a state and its change. Shots that need a true count go to footage, a still or the drawn route.

## Not covered

- One run per test (two for T5); judged on half-second sheets at 480 px; SK has every video.
- The API's refusal of T4 with frames: not diagnosed.
