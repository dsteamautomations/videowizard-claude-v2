# Video analysis and clip choice, in eight steps

13 Nov 2026. Written for Deepa, in plain words. It describes the application as it is today, read from the code and the served instructions, and marks in each step what stays and what may change. Nothing in the application was changed.

## The verdict (14 Nov 2026, agreed by Deepa)

**Change the model and the list now. Do not rebuild the placing around Gemini yet.** Claude stays the one who chooses the clip; Gemini becomes a better witness.

| Decision | What it means | Why |
|---|---|---|
| Gemini 4 Hydrogen watches every clip | The look-again way for every clip, high thinking, high picture quality. About 0.33 US dollars a clip. | It works with our request as it is; every answer passed the server's check; where a person judged a fact (the fan, the strikes, who speaks) it was right. |
| The script is given as sentences | Gemini says, for each piece, which sentence it shows, how exactly, and what is missing. No new field in the form. | Its fit is stricter and by sentence. It was right that no clip shows flat brickwork, and that the "quality" clip shows no quality. |
| The placer's list carries each piece's own lines | Its own description, its "does not show" line and its fit by sentence. | Today 97 of 107 pieces carry a line that describes another piece, and the "does not show" line is written and never shown. |
| A "related" piece is never placed as a direct match | It may be B-roll. | Sentence 6: Deepa rejected it, Gemini had warned, today's cut called it direct. |
| Two clips of the same subject filmed there and back are one choice | Use one of them, not both, in neighbouring shots. | Sentence 11: the same building appeared twice. This rule was not found in the application. |

**Not done, and why**

| Not done | Why |
|---|---|
| Letting Gemini's answer decide the placement | Judged blind on VW-19, the cut built from Gemini's answers was better on 2 sentences, today's on 3, level on 2. Not better. |
| Asking Gemini for the exact seconds | It gave the whole piece 344 times out of 417. |
| Lower thinking or picture quality to save cost | At lower thinking it stops looking again and missed the fan. |
| Batch or cache | The half-price batch refused the look-again way; reordering the request did not get the cache. |
| A new field in the answer form | In the look-again way Google refuses the form with even one more field. |

**What it rests on:** one short documentary-explainer (VW-19: 46 clips, 11 sentences), one judge, about 37 US dollars of tests. The measure from here is the next real film's score from the operator's keep, reject and trim answers, against VW-19's 8 of 10.

**Where the detail is:** the first test, [hydrogen-test-results.md](hydrogen-test-results.md); the settings, cache and batch, [hydrogen-settings-test.md](hydrogen-settings-test.md); the sentence fit and the blind comparison, [phase1-sentence-fit-results.md](phase1-sentence-fit-results.md); the requirements for the change, [design/193](../193-hydrogen-watcher-and-the-placers-list.md).

---

**How to use this file.** Each step ends with a table "What the test showed". It was filled in after the Gemini 4 Hydrogen tests of 13 and 14 Nov, so a later problem can be checked against the step it belongs to.

The film has twelve stages: intake, brief, script, voice, media, analysis, options, master, first cut, visuals, assembly, delivery. This file covers stage 6 (analysis) and stage 7 (options).

---

## Step 1: before the model watches anything

**In one line:** before any clip is watched, the server checks that everything is ready, skips clips it already knows, and packs one locked folder per clip.

Think of a new helper joining a film crew. Before they watch any footage, someone hands them a folder: what the film is about, the script, the house rules.

1. **Claude starts it without asking the operator.** The clip list was agreed at stage 5. Claude only says that analysis is starting, one paid request per clip.
2. **The server checks four things first**, and refuses to start if one is missing:
   - the brief, the script and the footage list are approved;
   - the film's shape is known (wide or tall, frames a second);
   - the operator has said whether the sound of the clips may be used;
   - whether the client gave safety rules. If none were given, a clip is not thrown out only because a worker has no helmet.
3. **The server looks for clips it has seen before.** In VW-22, 45 of 46 clips were already in the client's library. The server asked once: analyse again (paid) or skip (free).
4. **The server makes one folder per clip.** It holds the clip; what the film is for, who it is for, its tone and message; the script cut into numbered **paragraphs**; the chapters; the safety and brand rules; the rule about people who talk on camera; the long instruction; and the form to fill in, with 159 boxes.
5. **The folder is saved and locked.** The same clip sent again with nothing changed reuses the old answer. Nobody pays twice.
6. **Two ways of watching.** A clip of 15 seconds or less: the model looks once. A longer clip: the model may go back and look again at parts.

**Guard rails:** Claude may use only the one tool, one command at a time. Paid steps are told, not asked. Claude is told not to read the clips' full logs.

| Part | Stays or changes |
|---|---|
| Starting without asking; the four checks; the check for clips seen before; one locked folder per clip | Stays |
| The model that watches | Changes to Gemini 4 Hydrogen (Deepa, 13 Nov). Needs SK's yes before it goes live |
| The script cut into paragraphs | May change to sentences |
| The 15-second limit for the look-again way | To be measured for Hydrogen |
| The form with 159 boxes | May change later: some boxes are read by nothing |

**What the test showed**

| Point | Result |
|---|---|
| The request (T1) | Hydrogen takes the application's request as it is: the same instruction and form, only the model name changed. Checked by fingerprint on two clips. |
| The 15-second limit (F10, T4) | The look-again way is accepted on clips of 3.8, 8.2, 13.0 and 16.8 seconds. There is no minimum on Hydrogen's side. It costs 2.1 to 2.4 times the plain way. |
| Which way is better on a short clip | Not known. The two ways disagree on facts (a wooden batten against a fan blade; the direction of a camera move). A person must judge: Part A of the sheet. |
| A refusal of the look-again way | One clip of 46 (the drone clip, 21 s). It fell back to the plain way and was answered, after 1,033 seconds. The same kind as defect 48. |

---

## Step 2: the model watches one clip

**In one line:** the model cuts each clip into pieces, fills in a form for every piece, and says which paragraphs of the script each piece shows.

**Job 1: cut the clip into pieces.** It cuts wherever something changes: the camera starts or stops moving, someone starts or stops talking, the action changes.

Example, the 19-second test clip of the mason:

| Piece | Seconds | What happens |
|---|---|---|
| 1 | 0 to 7.5 | The mason spreads mortar. Nobody talks. |
| 2 | 7.5 to 10.3 | He keeps working while a person behind the camera asks a question. |
| 3 | 10.3 to 15.5 | A helper puts down two bricks. The mason answers. |
| 4 | 16.8 to 19.2 | The mason stands and strikes a brick four times. |

From 15.5 to 16.8 seconds his head leaves the picture. The model left that part out.

**Job 2: fill in the form for each piece**, in seven groups: from where to where it is usable and the one moment that must not be cut away; people and speech; camera; pace, cut points and impacts; script fit; sound; safety and quality.

**Job 3: write a ten-line card for the whole clip.**

**Rules the model must follow:** never make things up; say what it is unsure of; say what a piece does not show; do not decide the crop; two kinds of script fit, exact and related.

**Weak point:** the script fit is by paragraph. The model does not say which sentence, or from which second to which.

| Part | Stays or changes |
|---|---|
| Cutting into pieces; the seven groups; the rules | Stays |
| The model | Changes to Gemini 4 Hydrogen |
| Script fit by paragraph | May change to: which sentence, from which second to which |
| Boxes that nothing reads | May change later: use the good ones, drop the weak ones |

**What the test showed**

| Point | Result |
|---|---|
| Cost (T5) | About 0.10 US dollars for a clip watched the plain way, about 0.36 for the look-again way; about 1.2 cents per second of clip either way. 43 clips: 8.11 dollars. |
| Time (T5) | About 64 seconds a clip the plain way, about 206 the look-again way, with 5 looks on average. |
| The fields (T6) | 176 field names. 146 filled every time, none empty every time. The 30 sometimes empty are lists and blocks that apply only when something is there. |
| Fit by paragraph (F5, T13) | All 106 direct fits point at a paragraph of two sentences (paragraphs 2 and 5). The fit never says which sentence. Not corrected in this run. |
| Pieces (T8) | 116 pieces from 43 clips; 34 clips give more than one. In 13 clips the pieces overlap in time, and in 10 one piece covers nearly the whole clip beside the shorter ones. |
| Fields read by nothing (F9, T11) | The notes for the editor hold real editing advice in every clip (130 lines). The best frame is given for every piece, the title zone for 106 of 116. The colour-group label is useless: 41 different labels for 43 clips. |
| Are the facts right (T9) | Not checked yet. Six clips wait for a person: Part B of the sheet. |

---

## Step 3: the answer comes back

**In one line:** the server saves the answer, checks it piece by piece, throws out only what is broken, and tries again by itself when the model stumbles. No AI.

1. **The answer is saved at once.** If the server stops halfway, it carries on from the copy.
2. **Is it a proper form?** A jumble is kept and marked "not readable". It is not asked for again by itself.
3. **Is it about the right clip?** A form about another clip is failed.
4. **Each piece is checked alone.** A wrongly filled piece is thrown out; the good ones stay.
5. **Do the times agree?** Every time is written as a clock time, in seconds and as a frame. A small mismatch gives a note. A piece outside the clip is thrown out.
6. **Small checks, each giving a note:** the card has ten lines; no speech reported when the sound was removed; no two pieces with one name.

The rule of this desk: check, do not repair.

| What goes wrong | What the server does |
|---|---|
| The answer is cut off, empty, or the service is busy | Tries again by itself, up to three times |
| One key is over its limit | Rests that key and uses the next |
| The model refuses the clip itself | Sets the clip aside with the reason and carries on |
| Nobody knows if the request went through | Waits; the operator chooses to recover it or set it aside |
| The operator asks for another try | Allowed three times; then the operator must decide |

Claude waits, reports the count and the languages heard. Nothing is approved in this stage.

Example: VW-23 sent 94 clips, 8 needed a second try, all 94 came through, giving 187 pieces.

| Part | Stays or changes |
|---|---|
| Everything in this step | Stays |
| Hydrogen's answers passing this desk | Not yet shown. To be tested |

**What the test showed**

| Point | Result |
|---|---|
| Answers (T1) | 43 of 46 clips answered; all 43 ended properly. Two requests stopped before finishing (one succeeded when sent again). Three clips were left unanswered by Deepa's word, among them the two longest (52 and 95 s). |
| The arrival check (T2) | All 43 answers kept. 116 pieces kept, none thrown out, no note written. The check is the server's own code. |
| Connection | Thirteen requests failed at once on a lost connection overnight; they cost nothing and were sent again. A fault of this computer, not of the model. |

---

## Step 4: may this piece be used at all?

**In one line:** the server throws out bad and unsafe pieces, hides people who are seen talking when it can, and gives every piece one of five answers. No AI.

Most films have a narrator. People in the footage should not be seen talking, because their voice is not in the film.

| Answer | Meaning |
|---|---|
| Use as it is | Nothing to hide |
| Use with a crop | Someone is talking, but can be cut out of the picture |
| Use as a speaker | The film allows speakers to be seen |
| Sound only | The picture is refused; the sound is kept as background knowledge |
| Rejected | Not usable |

How the server decides, in order:

1. **Bad or unsafe?** Graded "reject", or not safe for the client: out. The operator can drop a safety flag for a client; that costs nothing.
2. **Is someone talking?** Yes when they look at the camera, or when lips can be seen and speech is heard. A worker with their back turned is not talking.
3. **Does this film show speakers?** Then the piece is used as a speaker.
4. **If not, can the speaker be cut out?** The model drew three boxes: the speaker's head, the speaker's body, the action that must stay. The server tries a cut from the side, then from above or below. The picture may be blown up at most 1.35 times, or 2 times for 4K footage. What remains must be sharp.

Extras: the shot size after a crop; whether the last frame may be held as a still; slow motion only at 50 frames a second or more.

| Part | Stays or changes |
|---|---|
| Everything in this step | Stays |
| Hydrogen's boxes and its "lips visible" answers | Not yet checked. To be tested |

**What the test showed**

| Point | Result |
|---|---|
| Allowed or not (T3) | 105 pieces allowed as they are, 2 with a crop, 5 with the picture refused and the sound kept, 4 refused. |
| Speaker boxes | No note about a head outside the body or a body too wide. |
| Defects inside a piece | 17 defects in 16 pieces (5 camera bumps). 4 of those pieces are ruled out by their grade; 12 are still allowed, and the defect and its seconds are not passed on. |

---

## Step 5: what Claude is given to choose from

**In one line:** Claude chooses clips from a short written list and never sees the footage; the best description of each piece is written but not on that list.

Claude's instruction opens with "you have NOT seen the footage". Think of someone picking photos for a magazine page from captions only.

The pack holds: the instruction; the scenes; every sentence and word with the moment it is spoken; the file shapes; the coverage report; one file per scene with its sentences and the pieces that fit it; and "other", the pieces that fit no scene. Each file is small enough to read in one go.

A piece is listed under a scene as **direct** (the model said it shows a paragraph exactly, and that paragraph falls in the scene), **chapter** (same chapter of the film) or **related**.

**The short list for each piece:** its name and the clip's name; "seen", which is one line about the whole clip; how it fits; grade; length; start and end; wide or close; the moment that must not be cut away; what the action leaves behind; safety flags; which of the five answers it got.

**The weakness.** The line "seen" comes from the clip's ten-line card and describes the whole clip. In the test clip, piece 1 (mortar) and piece 4 (brick) carry the same line. The model's own description of each piece, and its "does not show" line, are not on the list.

Claude can ask for the full row of one piece, or the full log of one clip. In VW-21, VW-22 and VW-23 no full log was opened even once.

| Part | Stays or changes |
|---|---|
| The pack, the coverage report, small files | Stays |
| The short list | Approved by Deepa, 13 Nov: add each piece's own description and its "does not show" line |
| Fit by paragraph | May change to sentence and seconds |
| Claude never watching | May change in part: the model that watches does the fine matching |

**What the test showed**

| Point | Result |
|---|---|
| One line for every piece (F1, T10) | Of the 107 pieces the placer would receive, 97 sit in clips with several pieces (32 of 42 clips), so the line it reads often describes another piece. Example: a piece that shows a pan pouring mortar is listed under 'a mason packing mortar with a trowel'. |
| The "does not show" line (F2, T7) | Hydrogen fills it every time a fit is claimed (112 of 112). It is not on the list today. |
| Size of the corrected list (T10) | Adding each piece's own description and its 'does not show' line makes the list about 79 % longer (55,646 to 99,458 characters). The tool already splits a long scene file into parts. Not run through the tool. |
| Nobody opens the full log (F3) | Not tested here; the corrected list would carry the two lines that matter without it. |

---

## Step 6: the library question, the scenes and the pauses

**In one line:** the operator marks clips for the library and approves the scenes; pauses can be added here, but Claude has read nothing about the footage yet, so none are proposed.

**Part 1, the library question.** Some clips would be true in any film for this client: the factory gate, staff at work. Claude reads each clip's name and ten-line card, makes a shortlist, and asks the operator which to mark. "None" is a fine answer. The server will not start the options stage until this is answered. Every analysed clip is stored for the client, which is how a later film skips clips it already has.

The same weakness as step 5 is here. Claude shortlists from the card, not from the pieces. The whole clip is marked, never one piece. When a library clip is offered to a later film, its pieces come with the one line about the whole clip and no script fit.

**Part 2, the scenes.** Claude reads only the paragraphs, the sentences and the file shapes, "and nothing else yet". It proposes the scenes in one message, usually one per paragraph, each with a title and its chapter. A scene must start at the start of a sentence. The operator approves. A fault seen in VW-21 and VW-23: Claude wrote the first word as "1" where "W00001" was wanted, and was refused.

**Part 3, the pauses.** A pause is a short silence put into the narration between two sentences. Nothing is recorded again. Rules today: only after the end of a sentence; at most 4 seconds; each needs a reason; a gap already in the recording counts; once approved, every scene's length is fixed. None has been proposed in the runs seen, because the instruction only says "any pauses", only one reason is allowed, and Claude has not read about the footage yet.

| Part | Stays or changes |
|---|---|
| The library question; the scenes | Stays |
| The library weakness | Approved by Deepa, 13 Nov: show each piece's own description; mark by piece; give a library piece its own description for a later film |
| The first-word fault | Approved: one filled example with a real word number |
| Longest pause | Decided: up to 4 seconds is usual, 7 seconds the longest allowed, shorter pauses stay allowed |
| When pauses are proposed | Approved: the server suggests them after the first choice of clips; the operator approves them then. Needs a step that re-times the film |
| Reasons for a pause | Approved: more reasons allowed, such as after a key number or before a new chapter |

**What the test showed**

| Point | Result |
|---|---|
| The library by clip (F4, T12) | In 23 of the 34 clips with several pieces, the pieces differ in what they fit, their chapter or their role. Marking the whole clip is wrong one way or the other for about two thirds of them. Which pieces are true in any film needs a person; not done. |
| Pauses after the footage (F6, T14) | 68 pieces carry a 'moment that must not be cut', 1.0 to 4.5 seconds long. None outlasts the sentences of its paragraph, so the arithmetic suggests no pause on this film. With a fit by sentence a short pause could show; that cannot be told from these answers. |
| The first word of a scene (F7) | Not tested: it belongs to the scenes step, not to the analysis. |

---

## Step 7: Claude builds the cut, and the server checks it

**In one line:** Claude lays real footage only under words it truly shows, leaves blanks elsewhere, and the server refuses the cut until every rule is met.

1. **Claude shows the coverage first**, scene by scene: these words have real footage, these will be blank.
2. **Round one, exact matches only.** "The same action, on the same object, done the same way. Related is not enough." A piece of the mason carrying bricks does not go under "the mason spreads mortar".
3. **Blanks are normal.** A blank says how long it is and what it must show. A later stage fills it with AI video or a drawing.
4. **Round two, general footage into some blanks**, only from clips round one did not use, never under a number or a claim.
5. **Spare choices** for a shot, seen by the operator only after a reject.

Main rules for Claude: cut to the meaning, shots of 2 to 3.5 seconds; each clip once in the film; every sentence tied to a shot or a blank, with a reason; every blank names the pieces looked at and why not; a doubtful shot carries a question for the operator; a shot starts a quarter to half a second before its words.

**The server's rule check, no AI.** Refusals stop the cut: a piece not allowed or not safe; a shot outside the usable part; the must-keep moment cut away; a shot too short to understand; three shots of one size in a row; hard sun to cloudy light inside a scene; shots that do not add up to the scene's length; a clip used twice with no note. Flags do not stop the cut; some must be acted on, others are only counted.

Examples: VW-23's cut was refused 9 times before it passed; VW-21's, 5 times. Many refusals are about the form of the file, not the film.

| Part | Stays or changes |
|---|---|
| Claude builds the cut; two rounds; the rule check | Stays |
| Where the exact match comes from | May change: Hydrogen says which sentence each piece shows, and Claude builds from that |
| Refusals about the form of a file | Proposed, not yet approved: a filled example for every file Claude writes |

**What the test showed**

| Point | Result |
|---|---|
| The cut and its refusals (F8) | Not tested. This run stops at the analysis answers. |
| What would change for the placer | Overlapping pieces from one clip (step 2) could be placed twice under two names; the check for a repeated shot should be looked at with Hydrogen's answers. |

---

## Step 8: the second look, the review film and the operator's answers

**In one line:** a helper checks the cut against still pictures, the operator watches the review film and answers keep, reject or trim on every shot, and the first answer approves the cut.

**Part 1, the second look.** The server takes still pictures from every shot as cut: first, middle, last, one a second, one every half second under a claim. One helper per scene, a fresh Claude that knows only its scene, puts sentence and pictures side by side: does the picture show the words; is there a better piece; does the cut fall where the action ends. A helper may change its scene and must say why. Then the rule check runs again. Limit: still pictures only, no movement, no sound.

**Part 2, a doubt about a cut point.** Free: nine stills around the point. Paid: Gemini watches one second before and after, as video.

**Part 3, the library round.** Library clips this film may use are offered now.

**Part 4, the review film.** The server saves the cut as a version, names scenes and shots by number (scene 2; shots 2.1, 2.2; a spare 2.2A1), and makes a review film, free. The operator watches it on the review page.

**Part 5, the answers.**

| Answer | What it does |
|---|---|
| Keep | The shot stays as placed |
| Reject | The shot goes; its spare is offered; with no spare the stretch becomes a blank |
| Trim | The shot stays but starts or ends a little earlier or later |

Guards: a trim stays inside the usable part, keeps the must-keep moment and does not make the shot too short. AI shots inside a scene need no answer. The first answer approves the whole cut. A reject needs no reason. After three rounds, Claude suggests that failing scenes become blanks.

| Part | Stays or changes |
|---|---|
| The second look; the stills and the paid look; the review film; keep, reject, trim | Stays |
| The operator's answers as a measure | Proposed, not yet approved: count them per film, with the share of narration under real footage and a small check of blanks |
| A reject needs no reason | Suggested, not yet approved: one click for the reason |

**What the test showed**

| Point | Result |
|---|---|
| The second look and the review | Not tested. This run stops at the analysis answers. |

---

## The faults found while reading, in one list

| # | Fault | Step |
|---|---|---|
| F1 | Claude is given one line about the whole clip for every piece; each piece's own description is not on its list | 5 |
| F2 | The "does not show" line is not on the list | 5 |
| F3 | No full log was opened in VW-21, VW-22 or VW-23, so much that is written is read by nobody | 5 |
| F4 | The library is chosen from the clip's card, the whole clip is marked, and a library piece arrives with no script fit | 6 |
| F5 | The script fit is by paragraph, not by sentence and seconds | 2 |
| F6 | Pauses are asked for before anything about the footage is read | 6 |
| F7 | The first word of a scene is written wrongly, the same way, run after run | 6 |
| F8 | Many refusals of the cut are about the form of the file | 7 |
| F9 | The model's colour-group label, its notes for the editor, the spoken words, the best frame, the title zone, the graphics ideas and the defects are written and used by nothing | 2 |
| F10 | The 15-second limit for the look-again way is ours and has never been measured for Hydrogen | 1 |

## After the test (14 Nov 2026)

The test ran 43 of VW-19's 46 clips through Gemini 4 Hydrogen with the application's own request. Results: [hydrogen-test-results.md](hydrogen-test-results.md). What needs a person: [hydrogen-test-for-your-eye.md](hydrogen-test-for-your-eye.md).

| Fault | After the test |
|---|---|
| F1 | Confirmed, large: 97 of the 107 pieces the placer would receive |
| F2 | Confirmed: the line is always written, never shown |
| F3 | Not tested |
| F4 | Supported: the pieces differ in 23 of 34 clips with several pieces; a person's marking is still needed |
| F5 | Confirmed: 106 of 106 direct fits point at a paragraph of two sentences |
| F6 | The arithmetic works, and suggests no pause on this film; needs a fit by sentence to be exact |
| F7, F8 | Not tested |
| F9 | Confirmed for the editor's notes, the best frame, the title zone and the defects; the colour-group label is useless as written |
| F10 | Answered: no minimum on Hydrogen's side; the look-again way costs about twice as much on a short clip; which way is right on the facts is for a person |

New points the test added, to watch in later films:

| # | Point |
|---|---|
| N1 | Pieces of one clip overlap in time (13 of 34 clips); one piece often covers nearly the whole clip |
| N2 | 12 of 16 pieces with a logged defect (camera bump, focus hunt) are still allowed, and the defect is not on the placer's list |
| N3 | The plain way and the look-again way disagree on facts for the same clip |
| N4 | The look-again way was refused for one clip (the drone clip); the fall-back worked but took 17 minutes |
| N5 | Two requests of 62 stopped before finishing their answer |
| N6 | A short clip costs about 10 cents; the cost is the long answer, not the video |
