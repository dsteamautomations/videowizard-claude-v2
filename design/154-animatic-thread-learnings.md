# 154 — What the "Evening at the park" thread taught, and what to take from it (5 Nov 2026, for discussion)

SK ran the animatic idea by hand in a separate thread (write-up `video-pipeline-writeup.md`, 4 Nov, with the code, the guide videos and the stills). SK's own caveats: the reference picture was set by hand, and character consistency was not used for every object. This note says what worked there, what we take, what we leave, and answers SK's question about cuts and angles inside a take. Nothing here is built or approved. No test has been run. Second read 5 Nov: section 6 added, sections 3 and 5 amended. Third read, full (every code file, all 13 stills, one frame per second of the four videos): section 7 added.

## 1. What the thread did (in our words)

| The thread | Our word (design/152) | Same or different |
|---|---|---|
| A 20 s story in two **parts** of 10 s, each part one Gemini run | a **scene** of several **shots**, one **take** per shot | **Different**: there, one run holds four shots with cuts inside it; here, every shot is its own take and assembly cuts between them |
| The **animatic** (SVG per frame, Python + cairosvg, ffmpeg to mp4, 15 fps, 1280×720) | no equivalent yet; the drawn route renders SVG in Chromium (HyperFrames) | the same idea as our drawn route; the renderer differs |
| Character sheets from ChatGPT, prompted by hand | a person's **set** (design/151), made by the picture AI from the plan | ours is the automated version; keep ours |
| A still from an earlier output used as the look reference | a footage frame of kind `frame`, or the **golden picture** | ours; the thread's way is what SK calls the manual flaw |
| Part 2 sent the real Part 1 clip as "Video 1 for the look" and the animatic as "Video 2 for actions and timing" | nothing: identity comes from the sets and the golden picture on every take | **new**: the previous take of the scene as a look reference; worth a test, not a rule yet |
| Prompt blocks: Location, Characters, Props (counts, empty hands), Shot n (a to b s) with sub-steps, faces as Action + Emotion, Style | the **packet** (foundation, scene, shot, references, the fixed lines); the plan's start and end object counts; subjects with beats | mostly already in the packet; two additions below |
| "Use the attached video as a guide for shots, camera angles and timing only. Do not copy the cartoon drawing style." | the server's fixed lines in the motion text | **take**: one fixed server line |
| A temporary public URL for the video (uguu.se, 3 hours) | the server sends files to the API itself | leave: not needed |
| The Gemini app took two videos as attachments, by hand | our server calls the API | **the unknown**: whether the API path takes a video reference at all (design/153's open test) |

## 2. The findings, judged one by one

| # | The thread's finding | Take, adapt or leave | How it lands in our flow |
|---|---|---|---|
| F1 | The model copies the cartoon unless told it is a guide only | **take** | a fixed line the server adds to every take that carries an animatic |
| F2 | Six shots in 10 s felt rushed; hold 2–3 s, 3.5 s for a facial moment; cutaways | **adapt** | already how the plan cuts shots ("cut where an action begins or ends"); add the holds as a planning rule, filed generic |
| F3 | Small facial movements are weak; one longer, closer, continuous shot with timed sub-steps and a hold at the end; faces as Action + Emotion; a guide longer than the output fails | **take** | two lines in the plan's shot rules; the animatic is never longer than the take |
| F4 | Props multiply when counts and empty hands are not stated; a cartoon object touching a hand reads as held | **take, half there** | counts are already in the plan's start and end states; **new drawing rule**: an object never touches a hand that is empty in the plan, checked on the animatic's contact sheet |
| F5 | The guide, the prompt and natural behaviour must agree (the right-hand coffee cup) | **take** | the packet already has "tools handled as a practitioner would" on pictures; extend it to the animatic: handedness, eating and drinking, cultural habit, as a must line read on the contact sheet before the take |
| F6 | Change one thing per run; run each version twice | **adapt** | one change per retry, yes (our review loop already does that); "run twice" no: it conflicts with "no unbounded paid retries"; a second take only on the operator's ask |
| F7 | Dialogue: not over a busy mouth, exact lines only, script + pronunciation + meaning, no subtitles | **take, filed by category** | our documentaries have narration, not dialogue; file under advertisements and drama |
| F8 | Short prompts are not better; conflicts are the problem | **take** | agrees with "rules written for today's models" (CLAUDE.md); no change |
| §5 | Two sheets per person, text-free, same light | **leave** | the set does this (design/151) |
| §6 | Previous clip as Video 1 (look), animatic as Video 2 (timing) | **test** | continuity across a scene's shots; test after the one-video test passes |
| §10 | Temporary public hosts | **leave** | the server has the file |

## 3. SK's question: cuts and angles inside a take

**What the rule says today** (section 9 of part `later`): the motion text always states the camera, "locked off on a tripod unless the shot's `camera_move` names its one move", and a locked-off take that drifts over 2 % fails. The rule is per **take**, and a take is one **shot**. Several angles are already allowed: they are several shots of the scene, each its own take, cut together at assembly.

**What the thread did**: one 10 s take holding four shots with cuts inside it (wide, close-up of the bench, front medium, push-in). The animatic made the cuts land at exact seconds. SK saw the result and liked it.

**A fact that changes the size of the question (second read).** Omni Flash cuts to several shots by default. Our server suppresses that on every take with a fixed sentence, "In a single unbroken scene, one continuous shot, no scene cuts, no jump cuts" (design/84 B2, `video_providers.motion_text`). The thread never sent that sentence, so the model cut where the cartoon cut. The multi-angle clip SK liked is the model's own habit, steered by the animatic, not a new capability.

**So the change is not "allow angles". It is "stop suppressing the cuts on a take that carries an animatic, and let the animatic decide where they fall".** Three ways to do it:

| | Way | What changes | Size |
|---|---|---|---|
| A | **One take per shot, animatic per shot** (today's unit, plus the animatic) | the packet gains the animatic and the fixed line; the tripod rule stays as it is per take, `camera_move` allowed | smallest; the cut between angles stays at assembly |
| B | **One take per scene, animatic per scene, cuts inside** | the unit of a take moves from shot to scene; the drift check, the Gemini read, the trim at assembly and the take cards all change to per scene; a bad cut wastes the whole scene's seconds | largest |
| C | **A, and a scene may be marked `one_take`** | as A, plus one flag on the scene: its shots become timing marks inside one animatic and one take, with cuts inside; the single-shot sentence and the tripod line are replaced by "the camera and the cuts as the guide shows them"; the drift check is off for that take | middle; the test decides whether B's result is worth B's cost |

Recommendation: **C**. Build A first (it is the branch design/153 already describes), then the `one_take` flag once the video-reference test passes. What the thread showed to be good (continuity of light and faces across a cut, cutaways in the same run) is exactly what the flag buys; the per-shot default keeps today's checks for every scene that does not need it. Documentaries would use it rarely; advertisements and drama often: a category rule, not a general one.

Older way (old-ways rule): one shot = one take, camera locked off, cuts at assembly. **Kept** as the default; the flag is the exception.

## 4. What does not transfer

- The thread's renderer chain (`v7 → v6 → v5 → v4 → v3` Python files, cairosvg, 15 fps). Our animatic will be an SVG animation rendered in Chromium like a HyperFrames shot; the drawing ideas transfer (world coordinates, the camera as the viewBox, blended arm poses, the layering rule for an arm around a shoulder, the left/right mirror trap), the code does not.
- ChatGPT sheets, hand-set reference stills, temporary URLs.
- "Run twice before judging" (paid; the operator decides a second take).
- Its 10 s parts as the unit: only through the `one_take` flag, if C is chosen.

## 5. Before anything is built

1. **The video-reference test** (design/153): one shot of an existing film, its animatic drawn by hand from the plan, sent through our API path with the sets. What it must prove, precisely: (a) the interactions endpoint our provider calls (`video_providers.Provider.build`: today a list of `image` items and one `text` item) accepts a `video` item at all; (b) how the video's role is named, since the house shape binds pictures to roles with `<FIRST_FRAME>@Image1` tags and the animatic must not become the first frame; (c) with the single-shot sentence removed, the take cuts where the animatic cuts; (d) the sets still hold identity when a cartoon is in the inputs. Like design/128's G07-S4-SH1. design/116 already records that nothing in the flow takes a video reference yet.
2. If it passes, the requirements note for way A, with the fixed line, the F4 and F5 contact-sheet lines, and the holds rule.
3. The `one_take` test only after A is live.

## 6. Second read: what the write-up does not show, and what it costs

- **The zip holds no generated video.** It holds the cartoons (four guides, all exactly 10 s or 20 s), the stills and the code; no Gemini output. Every "it worked" in the write-up is the thread's own report. The last fix, the right-hand guide, had **not been reviewed** when the write-up was made (its open item 1), and the write-up does not say whether the two-video method for Part 2 (previous clip for the look, cartoon for the timing) produced a good clip. So: the lessons F1 to F8 came from real failures and are sound; the fixes for F4 and F5 are unverified in the document itself.
- **The clips came from the Gemini app, not the API.** The outputs were 640×360, 24 fps, with audio, and the videos were "attached" by hand with `@video1` tags. Our takes go to the interactions API with a requested resolution and no audio. Nothing in the thread shows that the API path takes a video; that is test (a) above.
- **The animatic was hand-coded, one Python file per round.** A drawing library of about 330 lines (`animatic_v3_six_shots.py`: world background, bench, couple, dog, bush, the camera as the viewBox) and a chain of five files on top of it, one per round. Each close angle needed its own drawing (the hands close-up, the view from behind the bench, the point of view, the ground level). That is the real cost signal for us: an animatic is a helper's drawing job per shot, free of paid calls, and every extra angle is an extra drawing. Our `vw-motion-shot` helpers already do this kind of job for drawn shots, which is where the animatic should live.
- **The arm-pose and head machinery is the transferable part.** Named arm poses blended by a ramp, head `turn`, `tilt`, `brow`, `narrow`, `mouth`, the layering rule for an arm behind a neck, the left/right mirror trap. These are drawing rules for the helper's instructions, not code to copy.
- **The thread's prompt and our packet overlap more than the first read said.** Our motion text already carries timed events (design/128's timeline), the end state, the ambient line, the camera line, the gaze, heading and tool lines, the light line and the person lines. What the thread adds that we lack: the guide-only opening line (F1), the "props with counts and empty hands" sentence as one line (we have the counts, not the sentence), and faces as Action + Emotion.

## 6a. SK, 5 Nov: the generator

The clips were made with Gemini Omni, the same model our takes use. SK keeps Omni for this branch because it will also carry dialogue in later phases. So the test in section 5 is only about the input path (a video item in our API call), not about the model.

## 7. Third read: what the guides and the code show that the write-up does not say

- **The current Part 1 guide still breaks the thread's own rule F4.** In `animatic_v7_part1_right_hand.py` the fix for the cup was to move it to his right hand and draw it larger. Her tumbler and davara stay where they were, at the bench edge next to her hand (`davara(492, 356)` against her hands at x 514 and 526); the shot 1 still shows the small cup touching her hand. The write-up's cause 3 for the extra cups ("her davara set touched her hand") was named but not fixed in the guide. If the regenerated Part 1 still shows a cup in her hand, this is why.
- **The Part 2 guide and the Part 2 prompt disagree on shot 7.** The prompt says "In the background, the husband's hand points up at the butterfly"; the ground-level drawing (`s7_dog`) shows only the two pairs of feet and the dog, no hand. That is the F5 conflict in the thread's own files, waiting for the next run. Our rule: the contact-sheet check reads the animatic against the shot's lines before the take, which catches exactly this.
- **Cutaways shorter than three seconds exist only inside a one-take scene.** The thread's shots run 1.5 s (the hand puts the cup down), 2 s (the point of view), 2.5 s. Omni makes takes of 3 to 10 s, and the plan already turns a shot under 4 s with no visible action into a moving still. So a 1.5 s cutaway with action (a hand setting a cup down) cannot be its own take at all today. This is the strongest concrete argument for way C: the `one_take` flag is the only way a short action cutaway reaches the film as video.
- **Every round had several framings inside one clip, from the first.** Round 1 (`animatic_v1_three_clips.py`) was already three framings with pushes inside ten seconds, and the write-up says round 3's six shots "worked" apart from feeling rushed. The multi-angle result is therefore not a late discovery; it held from the first run. What the later rounds learned is the pacing (2 to 3 s a shot, 3.5 s for a face).
- **The animatic was rendered in Claude's own sandbox, not on SK's machine.** `animatic_v5_part1_closeups.py` writes to `/home/claude/bench5/`; the chat Claude drew and encoded the frames itself and handed back the mp4. In our flow the same job is a helper on the server, rendering in Chromium. The frame rate (15 fps) and size (1280×720) were enough for the model to follow; no reason to render more.
- **The drawings carry the thread's film grammar in code, not only in prose.** The 180-degree rule is a fixed world coordinate (he is at x 455, she at x 520, in every shot that shows them); a cut is a new viewBox; a push-in is a shrinking viewBox; "cut in the middle of the stretch" is a shot boundary placed inside a ramp. For our helper's instructions these are four rules, not a library to port.
- **What matched the write-up exactly.** The four guides run exactly 10 s, 10 s, 10 s and 20 s; the frames of `part1-v4-right-hand-10s.mp4` follow the shot table in section 3 of the write-up second for second (wide sip 0–2.5, bench close-up 2.5–4, yawn 4–6.5, push-in with the head turn and her look 6.5–10); the Part 2 pointing hand is his right (`L["point"]`, screen-left), as the write-up says; the head machinery (`turn`, `brow`, `brow_other`, `narrow`, `mouth`) is in `animatic_v5_part1_closeups.py` as described.

## 8. SK's correction, 5 Nov: the cartoon guides the cuts; the evaluation

SK: Omni itself made the ten-second clip with four shots inside it; the cartoon guided the cuts, where before only words did. The change is "cartoon plus text" guiding Omni, and the cartoon is made by its own prompt, a director's prompt (how to show the shot, not only where the subject sits; the surroundings and the focus too). A loop is needed: a Claude looks at every cartoon against its prompt; small drift → the video prompt is rewritten to say what the cartoon shows; a blunder → the cartoon is redone. Time matters: the operator waits.

**Correction to section 3's wording.** "Not possible today" meant one sentence in our server's take text, which asks Omni for one unbroken shot. Omni cuts on its own; we switch that off. Removing the sentence for a cartoon-guided take is one line. There is no capability gap.

**The pipeline SK describes, in our words:**

| Step | Today (video route) | With the cartoon |
|---|---|---|
| 1 | the plan's shot: layout, subjects, beats, one camera | the plan's **scene**: the same, plus a **director's brief**: the shots inside the scene (angle, size, what is in focus, cutaways), their seconds, the cuts |
| 2 | start image (and end image), approved by the operator | the **animatic**, drawn by a helper from the brief and the references (sets, canvas); free |
| 3 | — | the **check**: a helper reads the animatic's contact sheet against the brief: small drift → the take prompt is written from what the animatic shows; a blunder (a hand holding what should be empty, a subject missing, the wrong hand, the wrong order) → redo the animatic, at most two rounds, then the operator decides |
| 4 | the packet's motion text: words only, one unbroken shot | the take: the animatic + the references + a short text that says what the animatic shows; the single-shot sentence dropped |
| 5 | Gemini reads the take, the operator watches, selects | unchanged |

**This loop already exists for drawn shots.** The HyperFrames route (section 11 of the procedure) is: brief → one helper draws → snapshots at the beats → a check helper gives a verdict → failed rules go back to a drawing helper → at most two redo rounds → the operator sees the open rules. The animatic is that loop with a scene of people instead of a diagram. That is the main reason the estimate is days, not weeks: the loop, the helpers, the snapshots, the verdict format and the Chromium render exist; what is new is the director's brief, the drawing rules for people and places, and the take that carries a video.

**Multi-angle: yes.** The director's brief names the angles; the animatic draws them as cuts; Omni follows them. Short cutaways (1.5 s) are fine inside a scene's clip. The scene's clip stays within Omni's 10 s; a longer scene is two clips, cut at a shot boundary, the second carrying the first as its look reference (the thread's "Video 1" method; to be tested after the first test).

**Time per scene, estimated, to be measured in the test:** drawing helper 5–10 min; check 2–3 min; a redo round adds 5–10 min; so 10–30 min from the accepted plan to the take request, with no paid call in it. Today the same stretch is the start image, its check, the operator's approval, the end image where needed, each a paid picture and an operator wait. The operator's wait moves from several picture approvals to one look at the animatic (a contact sheet on the Takes step), which is free to redo.

**What is new to write (the requirements note):**
1. The director's brief: a scene-level prompt and its rules, generic, with category rules for documentary (few cuts, no drama) and advertisement or drama (cutaways, reactions, point of view).
2. The drawing rules for the animatic helper: world coordinates, the camera as the viewBox, cuts as viewBox jumps, named poses, draw order, the mirror trap, the empty-hand rule, the natural-behaviour rule, timing to the narration's seconds.
3. The check helper's rules: drift versus blunder, and the rewrite of the take text from the animatic.
4. The take: a video input in the API call, the guide-only sentence, the single-shot sentence dropped, the drift check off.
5. The page: the animatic's contact sheet and video on the Takes step, approve or redo.

**Open:** whether the operator must approve the animatic before the take (one more wait, fewer wasted takes) or only sees it when the check fails (faster; the first take may be wasted).

## 9. Rethink, 5 Nov (SK asked for a second opinion on section 8)

Five places where section 8 was too neat.

1. **"The loop already exists" is half true.** The HyperFrames loop exists: brief, draw, snapshot, verdict, redo. What does not exist is the drawing itself. HyperFrames draws diagrams: boxes, labels, arrows, pictures placed. An animatic draws people with poses that blend over time, heads that turn, hands that hold things, a dog, a bench, and a camera that cuts. The thread needed a figure library of about 330 lines plus five rounds of hand-written code, steered by SK over several sessions, to get one couple on one bench right. A helper drawing from nothing, per scene, will not reach that in one pass. The honest build is a **figure library built once** (people in named poses, heads with the thread's controls, common objects, the camera helpers), which the helpers then call. That is the part I left out of the estimate: 3 to 5 days on its own. Way A becomes about 7 to 10 days, not 4 to 5.

2. **The time per scene is a guess until the test.** 10 to 30 minutes assumes the helper gets a usable cartoon in one or two rounds. The thread's history says the first cartoons of a new scene are wrong in small ways that matter (a cup touching a hand, eyes instead of a head turn). The test must measure the rounds, not only the render.

3. **The canvas may be redundant once the animatic exists.** design/153 added a fourth reference, one realistic picture per scene of the stage with its landmarks. The animatic now carries the stage, the positions and the cuts. What is left for the canvas is the look of the place, and the place's set (design/151) already gives that. The thread used no canvas: a cartoon, two sheets, a prompt. Recommendation: do not build the canvas; let the test show whether the place set and the animatic are enough; add the canvas only if the place drifts between shots.

4. **The operator's approval is a substitution, not an extra wait.** Today the operator approves the start image of every video shot (and the end image where there is one), each a paid picture. With the animatic there is no start image. Approving the animatic takes that slot: one look at a contact sheet and the short video on the Takes step, free to redo. So "approve every time" adds no wait against today and protects a paid take. Recommendation: the operator approves the animatic every time; the check helper runs before it so the operator sees a cartoon that already passed the drift and blunder rules.

5. **Documentaries are the hard case, not the easy one.** The thread's film was all generated; cuts inside the clip only had to match each other. In our documentaries the gap sits between real footage; a ten-second AI clip with four cuts inside it has to match the footage on both sides in light, lens and pace. More cuts means more places to look wrong. The director's brief for the documentary category should default to one or two angles and a hold, and allow more only when the gap's purpose asks for it. Advertisements and drama get the thread's grammar as their default.

**What does not change:** the test is still the gate (the video input on the API); the single-shot sentence is still one line; the check helper is still the HyperFrames verdict with new rules; way C is still the recommendation, with the one-take scene as the way short cutaways reach the film.

## Not covered

- The write-up's Appendix C (earlier prompts) and the code were read for the method, not run.
- No file from the zip is copied into this folder; the zip stays in the scratchpad.
