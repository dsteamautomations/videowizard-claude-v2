# design/221a: the motion family per film (supporting document for design/221, rows 8 and 10)

19 Nov 2026. Written by a side session of the builder thread (Claude), read only. **Nothing is built. Not committed.**
It belongs to `design/221-step6-drawn-graphics-rebuild.md` (sections 2, 6.8 and 6.10). SK approved row 10 on 19 Nov: "Yes, from the Motion Menu, with a supporting document for a clean build."

Sources: the Motion Menu (`Downloads/motion-menu.md`, version 0.1, 18 Nov 2026), the review `design/_work/motion-menu-against-step6-gaps.md`, the eight style files in `server/motion_styles/`, `server/app/film.py` (`styles`, `style_part`), `server/app/visuals_stage.py` (`motion_brief`), `plugin/skills/motion/SKILL.md` and `references/motion.md`, the three motion helpers in `plugin/agents/`, `server/unit/test_motion_style_fonts_pure.py`, and the failed-checks table of VW-24.

A line marked **(judgement)** is Claude's view. The menu itself says: "Draft for testing. Not yet tried on a real video." Every number taken from it is untested (section 6).

## 0. The whole change in one page

| # | What | Where | Kind of change |
|---|---|---|---|
| F1 | One fixed paragraph, the same for every style: a landed label stays still; the frame does not push or pan unless the shot asks; rest after a strong move; one strongest move, on the claim; no letter-by-letter text | A constant in `server/app/film.py`, printed by `style_part` under the style's text | Server, about 3 lines |
| F2 | Each style's text loses its camera and "keep moving" lines (section 1) | `server/motion_styles/<name>.md` | Text |
| F3 | Each style file gains a head line `energy:` and a section `motions:` with its family of 4 or 5 named motions (section 2) | The same eight files; `film.styles()` reads the section; `style_part` prints it | Text, and about 3 lines of server code |
| F4 | The order of who wins, and a list of five "extra" motions for jobs a family does not cover | `plugin/skills/motion/SKILL.md`, one paragraph replaced (section 3) | Plugin text |
| F5 | The shared look names the film's motions once | The shared-look list of design/221 row 7 | Text the assistant writes |
| F6 | The rule writer and the checker: no rule from any of this | `plugin/agents/vw-motion-rules.md`, `vw-motion-check.md`, one sentence each (section 4) | Plugin text |
| F7 | The advert and social rules, filed by category (section 5) | Written here; **not wired until a film of that category has drawn graphics** | Text only, later |

Not used: any HyperFrames catalog piece. Every motion below is written by the builder by hand in GSAP, as today. SK's decision of 12 Nov (finish effects only) stands.

**Why the fixed paragraph is not copied into each style file.** `test_the_eight_styles_are_files_each_a_short_text_filed_by_category` pins each style's text to 120 to 260 words. The paragraph (about 110 words) plus a family would break that pin in every file. One copy in `film.py` also cannot drift between eight files. The family goes in its own section of the file for the same reason: the word pin stays on the style text alone.

## The energy scale for a drawn graphic

The menu scores text animations from 1 to 5 and sets a limit by mode: "Calm 3, Normal 4, Energetic 5". Its scores are for text. For the moves of a diagram the scale is written anew here **(judgement, untested)**:

| Level | A move of this level in a drawn graphic |
|---|---|
| 1 | Nothing travels: a fade in place, a change of colour or brightness |
| 2 | A short travel (up to about 2 % of the frame width) or a line that draws; long ease-out; no overshoot |
| 3 | A part travels further or a set builds in order; a number counts; a wipe between two states; a small settle |
| 4 | A clear overshoot; a part that comes in from the edge of the frame; a hard cut to a new framing; a move of 0.3 s |
| 5 | A slam, a squash, a flash or wipe of the whole frame |

| Style | File | Menu mode | Highest energy |
|---|---|---|---|
| Restrained | `server/motion_styles/restrained.md` | Calm | 3 |
| Editorial | `editorial.md` | Calm | 3 |
| Data-led | `data-led.md` | Calm | 3 |
| Technical | `technical.md` | Calm | 3 |
| Lively | `lively.md` | Normal | 4 |
| Product | `product.md` | Normal | 4 |
| Bold | `bold.md` | Energetic | 5 |
| Playful | `playful.md` | Energetic | 5 |

The mapping of styles to modes is **(judgement)**; the menu's test is "Choose the mode from the tone the brand needs."
The builder never sees a number. The limit is kept in the file's head (`energy: 3`) for the record and for a test; the style's words and its family carry it.

---

## 1. Each style: today's text, the changes, the replacement

### 1.0 The fixed paragraph (F1), the same under every style

Exact text, printed by `style_part` after the style's text and its motions:

```
In every style: a label that has landed does not move, grow, fade or drift until it leaves. The whole frame does not push in, pan or drift unless this shot's own lines above ask for it; when they do, the whole picture moves as one group. After a strong move (a part that travels far, lands with a bounce or changes the whole picture) nothing else moves while the viewer reads what landed: about 0.5 s plus 0.3 s for each word. The last label of the shot holds at least 2 s, or to the end of the shot when the shot is shorter. One move in the shot is the strongest, and it is on the claim; every other move is quieter. Text moves as whole labels, lines or words, never letter by letter.
```

| Sentence | From the menu | Which side VW-24 supports |
|---|---|---|
| A landed label stays still | "A landed title should be completely still. The movement then passes to the next thing on screen." | The menu. Rule 64 of BEAT_04-B1-S1 failed because leader dots sat off their parts "while the labels fade and the slab moves"; rule 13 of BEAT_10 failed on a note that vanished and came back. No failure was "too still" |
| The frame does not push or pan unless the shot asks | Calm mode allows energy 3; the menu's camera rows are 3 to 5 | The menu. Three failed answers in three rounds were one push-in on BEAT_04-B1-S5 (rule 73 twice, rule 74). Not known: whether that push-in was asked by the plan or added for the style (no brief was seen) |
| "When they do, the whole picture moves as one group" | Not in the menu | VW-24: the review's own fix for that push-in (design/221, 6.8). The tested recipe is row 8's work, not this note's |
| Rest after a strong move, with the numbers | Rule 3: "Hold about 0.5 seconds plus 0.3 seconds for each word. The last line of the video holds at least 2 seconds." | No direct evidence. The server's check warned 24 times that a label was on screen too short ("Cement", 0.36 s); that points the same way |
| One strongest move, on the claim | Rule 2: "One video has one animation at its highest energy. It sits on the hero line." | No VW-24 evidence. Taken per shot here, because each drawn graphic is built alone **(judgement)** |
| No letter-by-letter text | "Letter must be tested before use in Tamil or Hindi." | Not tested (section 6) |

"The last line" in the menu is the last line of the **video**. Here it is the last label of the **shot**, with "or to the end of the shot" for a short shot **(judgement)**.

### 1.1 Restrained (`server/motion_styles/restrained.md`), energy 3

Today:

> Move as little as the meaning needs. One thing arrives at a time, on a long ease-out, and comes fully to rest before the next begins. Nothing bounces, spins or overshoots. A part enters by fading up while travelling a short distance, never from off screen.
>
> Give each shot one idea of its own so the film does not feel the same from shot to shot: in one shot the parts build in order; in another a single slow push-in of a few percent across the whole shot; in another a highlight that travels along the thing being explained. Choose the one that serves what the narration is saying, and use only that one.
>
> Labels fade in over about half a second on the word they belong to and then hold dead still until the shot ends. A change of state is a slow cross-fade or a part sliding into its new place, never a cut inside the shot.
>
> Leave still time: at least the last second of the shot has nothing moving. If in doubt, remove a movement.

| Change | Old words | New words | Evidence |
|---|---|---|---|
| The push-in goes | "in another a single slow push-in of a few percent across the whole shot" | "in another one part changes state while the rest waits" | VW-24 supports it (the BEAT_04-B1-S5 push-in). VW2's own `references/motion.md` also lists "a slow push late in a scene" under "Defaults that look generated" |

Replacement text (the body of the file, under the head):

```
Move as little as the meaning needs. One thing arrives at a time, on a long ease-out, and comes fully to rest before the next begins. Nothing bounces, spins or overshoots. A part enters by fading up while travelling a short distance, never from off screen.

Give each shot one idea of its own so the film does not feel the same from shot to shot: in one shot the parts build in order; in another a highlight travels along the thing being explained; in another one part changes state while the rest waits. Choose the one that serves what the narration is saying, and use only that one.

Labels fade in over about half a second on the word they belong to and then hold dead still until the shot ends. A change of state is a slow cross-fade or a part sliding into its new place, never a cut inside the shot.

Leave still time: at least the last second of the shot has nothing moving. If in doubt, remove a movement.
```

### 1.2 Editorial (`editorial.md`), energy 3

Today:

> Slow, spacious and composed. Type is the picture: a label is set large with generous space around it and arrives by a slow reveal (a line rising from behind a mask, letters easing from slightly wide to their final spacing). One thought on screen at a time, held long.
>
> Movements last a second or more with very gentle eases. The whole frame drifts slowly in one direction through the shot, a few percent at most, so that nothing is ever quite still and nothing is ever seen to start or stop.
>
> Drawings are few and simple, placed with wide margins, and appear by slow fades or soft wipes. A change of state is a long dissolve. Transitions between ideas are a slow fade through the background colour.
>
> Use thin rules and plain shapes; let the film's main colour carry large quiet areas and keep the accent for one small element. Never crowd the frame, never hurry a reveal, never bounce. If two things want to move at once, let one finish first.

| Change | Old words | New words | Evidence |
|---|---|---|---|
| The letter effect goes | "letters easing from slightly wide to their final spacing" | "words rising one after another" | Not VW-24. The menu: #14 and #24 Tracking are "Letter", avoid in "Tamil or Hindi, until tested" |
| The drifting frame goes | "The whole frame drifts slowly in one direction through the shot, a few percent at most, so that nothing is ever quite still and nothing is ever seen to start or stop." | "A large quiet shape of the background may drift a few percent through the shot; the type and the drawing do not drift with it." | No VW-24 evidence: the film was Lively. The menu lists "titles that keep floating, pulsing or sliding after they land". **(judgement)**; question 1 for SK |

Replacement text:

```
Slow, spacious and composed. Type is the picture: a label is set large with generous space around it and arrives by a slow reveal (a line rising from behind a mask, words rising one after another). One thought on screen at a time, held long.

Movements last a second or more with very gentle eases. A large quiet shape of the background may drift a few percent through the shot; the type and the drawing do not drift with it.

Drawings are few and simple, placed with wide margins, and appear by slow fades or soft wipes. A change of state is a long dissolve. Transitions between ideas are a slow fade through the background colour.

Use thin rules and plain shapes; let the film's main colour carry large quiet areas and keep the accent for one small element. Never crowd the frame, never hurry a reveal, never bounce. If two things want to move at once, let one finish first.
```

### 1.3 Data-led (`data-led.md`), energy 3

Today:

> The numbers are the subject. Bars grow from their baseline, lines draw from left to right, segments sweep round, each at a steady pace on a firm ease-out, and each stops exactly on its value. A figure counts up to its value as its mark grows, and lands at the same moment.
>
> Bring data in the order the narration reads it: one series or one bar at a time, the others waiting dimmed. When the narration compares, highlight the two compared marks in the accent colour and let the rest recede. Axes and gridlines appear first and quietly, then the data.
>
> Labels sit on a fixed grid, aligned to their marks, and appear by a short fade the moment their mark stops. Use tabular figures so counting digits do not shift.
>
> The camera is fixed: the chart never moves, zooms or tilts. Changes between charts are a clean cross-fade or the marks re-flowing into their new shape. No decoration, no three-dimensional charts, no movement that is not a change in the data.

**No change to the text.** It already says "The camera is fixed" and has no pressure to keep moving. It is the style closest to what the menu and VW-24 both point to. It gains only the head line and its motions.

### 1.4 Technical (`technical.md`), energy 3

Today:

> The picture is a drawing being made. Outlines draw themselves along their length; parts arrive along the axis they would be fitted on and stop exactly in place; an assembly comes together in the order it is built in reality. Movements are measured and linear or nearly so, with no bounce: a part moves like a thing guided on a rail.
>
> Show the inside: cut-away sections slide open, an exploded view separates along straight lines and closes again. Flows (water, heat, load, current) are shown as travelling marks along their path at a steady speed.
>
> Each label is attached to its part by a thin leader line that draws first, then the label appears at its end and holds. Dimension lines draw from one end to the other.
>
> The camera looks straight on or from a fixed three-quarter angle and moves only by panning along the object or stepping closer to a detail. Keep everything aligned to an implied grid. No decoration, no perspective tricks, nothing that moves without a physical reason.

| Change | Old words | New words | Evidence |
|---|---|---|---|
| The pan and the step closer go | "The camera looks straight on or from a fixed three-quarter angle and moves only by panning along the object or stepping closer to a detail." | "The view is straight on or a fixed three-quarter angle and stays where it is. A closer look at a detail is a cut to a second framing or an inset beside the drawing." | VW-24 supports it indirectly (the push-in failures were on a Lively film). **(judgement)** for this style |
| Leaders | "then the label appears at its end and holds" | "then the label appears at its end and holds. Leader lines never cross, and a leader ends plainly, with no mark that could be read as a part" | VW-24 directly: BEAT_13 rule 70 ("Leader lines do not cross one another") and BEAT_02 rules 8 and 48 (leader dots read as bar ends: "A stranger counts seven round dots") |

Replacement text:

```
The picture is a drawing being made. Outlines draw themselves along their length; parts arrive along the axis they would be fitted on and stop exactly in place; an assembly comes together in the order it is built in reality. Movements are measured and linear or nearly so, with no bounce: a part moves like a thing guided on a rail.

Show the inside: cut-away sections slide open, an exploded view separates along straight lines and closes again. Flows (water, heat, load, current) are shown as travelling marks along their path at a steady speed.

Each label is attached to its part by a thin leader line that draws first, then the label appears at its end and holds. Leader lines never cross, and a leader ends plainly, with no mark that could be read as a part. Dimension lines draw from one end to the other.

The view is straight on or a fixed three-quarter angle and stays where it is. A closer look at a detail is a cut to a second framing or an inset beside the drawing. Keep everything aligned to an implied grid. No decoration, no perspective tricks, nothing that moves without a physical reason.
```

### 1.5 Lively (`lively.md`), energy 4. VW-24's style

Today:

> Keep the picture working with the narration: something begins to move on most sentences. Parts build in from where they belong (a wall rises course by course, a pipe grows from its source), staggered so the eye can follow the order. Use eases with a small settle at the end; a part may travel in from the edge of the frame.
>
> Labels slide in from the side of the thing they name, settle with a slight overshoot, and hold. When the explanation moves to a new part, the earlier parts dim a little and the frame shifts toward the new one: the camera follows the subject with pans and gentle zooms, never faster than the eye can read.
>
> A change of state is shown as a movement the viewer can follow: the part moves, turns or fills, it does not swap. Use a wipe or a slide between two states of the whole picture.
>
> Avoid stillness longer than about two seconds while the narration is speaking. Avoid decoration that explains nothing.

| Change | Old words | New words | Evidence |
|---|---|---|---|
| "Avoid stillness" goes | "Avoid stillness longer than about two seconds while the narration is speaking." | "Stillness while the viewer reads is part of the style." | VW-24 supports it. All 6 movement failures were moments inside a move or a fade; none was "too still". Not proven that this line caused them: no brief was seen |
| The camera goes | "the earlier parts dim a little and the frame shifts toward the new one: the camera follows the subject with pans and gentle zooms, never faster than the eye can read" | "the earlier parts dim a little and the new part is the brightest thing in the frame. The frame itself stays where it is" | VW-24 supports it (BEAT_04-B1-S5, rules 73 and 74, three rounds) |
| The pressure in the first sentence is softened | "something begins to move on most sentences" | "when a sentence brings a new part or a new idea, something arrives or changes with it" | Not in SK's list for row 8. **(judgement)**: it is the same pressure as "avoid stillness", said at the start. If SK wants the old sentence kept, only this row is dropped |
| Labels hold still | "settle with a slight overshoot, and hold" | "settle with a slight overshoot, and then hold still" | The menu ("completely still"); the old words already meant it |

Replacement text:

```
Keep the picture working with the narration: when a sentence brings a new part or a new idea, something arrives or changes with it. Parts build in from where they belong (a wall rises course by course, a pipe grows from its source), staggered so the eye can follow the order. Use eases with a small settle at the end; a part may travel in from the edge of the frame.

Labels slide in from the side of the thing they name, settle with a slight overshoot, and then hold still. When the explanation moves to a new part, the earlier parts dim a little and the new part is the brightest thing in the frame. The frame itself stays where it is.

A change of state is shown as a movement the viewer can follow: the part moves, turns or fills, it does not swap. Use a wipe or a slide between two states of the whole picture.

Stillness while the viewer reads is part of the style. Avoid decoration that explains nothing.
```

### 1.6 Product (`product.md`), energy 4

Today:

> One object is the hero, centred, with clear space around it. It is presented, not explained: it turns slowly to show its form, comes forward, and is lit by a soft moving highlight. Movements are smooth and continuous with long, even eases, as if the object were on a turntable.
>
> Features are called out one at a time: the camera or the object moves so the feature faces the viewer, the feature brightens while the rest dims slightly, a thin line runs from it to its label, the label appears and holds, then all of it clears before the next. Never two callouts at once.
>
> The camera orbits and moves closer or further along smooth arcs; it never cuts inside a shot and never shakes. Backgrounds are plain, in the film's main colour, with a soft gradient at most.
>
> A change of state (open, closed, on, off) is shown on the object itself, in place. End each shot with the whole object at rest, centred, for the last second.

| Change | Old words | New words | Evidence |
|---|---|---|---|
| The object moves, not the camera | "the camera or the object moves so the feature faces the viewer" | "the object turns so the feature faces the viewer" | No VW-24 evidence (no product film yet). **(judgement)**: in a drawn graphic "the camera orbits" and "the object turns" look the same, but a turning object leaves the labels and the frame in place. Question 1 for SK |
| | "The camera orbits and moves closer or further along smooth arcs; it never cuts inside a shot and never shakes." | "The object turns and comes forward along smooth arcs. The frame around it stays where it is; nothing cuts inside a shot and nothing shakes." | Same |

Replacement text:

```
One object is the hero, centred, with clear space around it. It is presented, not explained: it turns slowly to show its form, comes forward, and is lit by a soft moving highlight. Movements are smooth and continuous with long, even eases, as if the object were on a turntable.

Features are called out one at a time: the object turns so the feature faces the viewer, the feature brightens while the rest dims slightly, a thin line runs from it to its label, the label appears and holds, then all of it clears before the next. Never two callouts at once.

The object turns and comes forward along smooth arcs. The frame around it stays where it is; nothing cuts inside a shot and nothing shakes. Backgrounds are plain, in the film's main colour, with a soft gradient at most.

A change of state (open, closed, on, off) is shown on the object itself, in place. End each shot with the whole object at rest, centred, for the last second.
```

### 1.7 Bold (`bold.md`), energy 5

Today:

> Fast and large. Every beat of the narration gets a hard change: a cut to a new framing, a big jump in scale, a block of colour that wipes across. Movements are short (a quarter to half a second) with sharp eases that start fast and stop dead.
>
> Labels are the loudest thing on screen: they slam in at large size, fill a good part of the frame, and are replaced by the next rather than kept. One label on screen at a time. Use the film's accent colour in full-frame flashes and wipes behind them.
>
> The camera snaps between framings: a punch-in on the important part, a whip to the next. Hold each framing just long enough to read, then move.
>
> The picture should feel like it is cut to a beat even though it is silent: keep the changes evenly spaced within a sentence. Nothing drifts, nothing fades slowly, nothing eases gently. Do not shrink a label to make room; cut to a new framing.

| Change | Old words | New words | Evidence |
|---|---|---|---|
| Cuts, not travelling moves | "The camera snaps between framings: a punch-in on the important part, a whip to the next. Hold each framing just long enough to read, then move." | "The framing changes by hard cuts: a cut to a closer view of the important part, a cut to the next. Nothing travels between two framings. Hold each framing long enough to read, then cut." | No VW-24 evidence (no Bold film). **(judgement)**: a cut has no frames in between, so the VW-24 kind of fault (a ghost or a squashed part during a move) cannot happen. A cut is not a push or a pan, so it does not clash with the fixed paragraph |

Bold keeps "every beat of the narration gets a hard change". The fixed paragraph's rest (0.5 s plus 0.3 s a word) is what "long enough to read" means.

Replacement text:

```
Fast and large. Every beat of the narration gets a hard change: a cut to a new framing, a big jump in scale, a block of colour that wipes across. Movements are short (a quarter to half a second) with sharp eases that start fast and stop dead.

Labels are the loudest thing on screen: they slam in at large size, fill a good part of the frame, and are replaced by the next rather than kept. One label on screen at a time. Use the film's accent colour in full-frame flashes and wipes behind them.

The framing changes by hard cuts: a cut to a closer view of the important part, a cut to the next. Nothing travels between two framings. Hold each framing long enough to read, then cut.

The picture should feel like it is cut to a beat even though it is silent: keep the changes evenly spaced within a sentence. Nothing drifts, nothing fades slowly, nothing eases gently. Do not shrink a label to make room; cut to a new framing.
```

### 1.8 Playful (`playful.md`), energy 5

Today:

> Everything has weight and spring. Parts drop, hop or pop into place and overshoot before settling; a thing that lands squashes a little and recovers; a thing that leaves winds up first. Use bouncy and elastic eases, and keep each movement short and clear.
>
> Build the picture one cheerful step at a time, each part arriving with its own small flourish, slightly off the beat of the one before so the frame feels alive. Shapes may wobble once after arriving and then rest.
>
> Labels pop in at an angle, straighten with a wobble, and hold still enough to read. The camera bobs lightly: a small nudge toward each new arrival, never a long move.
>
> A change of state is a transformation the viewer enjoys: a stretch, a flip, a puff. Keep the drawing truthful while it plays: the bounce is in how things arrive, not in what they show. Never more than two things moving at once, and always a moment of rest before the next.

| Change | Old words | New words | Evidence |
|---|---|---|---|
| The camera bob goes | "The camera bobs lightly: a small nudge toward each new arrival, never a long move." | "The frame stays where it is: the bounce belongs to the parts, not to the camera." | No VW-24 evidence. **(judgement)**; question 1 for SK |
| Labels hold still | "hold still enough to read" | "then hold still" | The menu ("completely still") |

The menu agrees with the rest of this style: overshoot "Playful: clear bounce. Only position and size bounce"; "Anticipation … Only for level 4 and 5 animations". The style already has "always a moment of rest before the next".

Replacement text:

```
Everything has weight and spring. Parts drop, hop or pop into place and overshoot before settling; a thing that lands squashes a little and recovers; a thing that leaves winds up first. Use bouncy and elastic eases, and keep each movement short and clear.

Build the picture one cheerful step at a time, each part arriving with its own small flourish, slightly off the beat of the one before so the frame feels alive. Shapes may wobble once after arriving and then rest.

Labels pop in at an angle, straighten with a wobble, and then hold still. The frame stays where it is: the bounce belongs to the parts, not to the camera.

A change of state is a transformation the viewer enjoys: a stretch, a flip, a puff. Keep the drawing truthful while it plays: the bounce is in how things arrive, not in what they show. Never more than two things moving at once, and always a moment of rest before the next.
```

All eight texts keep their first sentence's start, so `test_no_two_styles_share_their_opening` holds. Each stays inside 120 to 260 words (the changes are a few words each; to be counted at build). None has a backquote or a film's code.

---

## 2. The family of each style

### 2.1 How a family is written and used

- A family is 4 or 5 named motions. The menu's Rule 5: "One video uses 3 to 5 animations in total, and repeats them." "A small set makes the video feel like one piece of work."
- Each motion has one job. The jobs: a label arriving; a callout or leader line; stressing one part; a counter or number; a chart growing; a before-and-after or change of state; a part appearing; leaving.
- No family covers all eight jobs. A job the family lacks takes the **extra motion** of that job (2.10), at the style's own pace. The shared look names it once, so every drawing of the film uses the same.
- Every builder of the film uses these motions for these jobs and names them in its `REVIEW.md`.
- The numbers come from the menu's "how" settings and "Secs" column: "A fast move takes 0.3 to 0.6 seconds"; stagger "Words: 60 to 120 milliseconds apart"; overlap "Start the next when the previous is 30 to 50% done"; exits "shorter than entrances, by 40 to 50%"; overshoot "Calm: none. Normal: a little. Playful: clear bounce. Only position and size bounce. Colour and fading never bounce"; easing "Arrivals slow down gently at the end. Exits speed up."
- **Left out until tested in Tamil and Hindi: every letter-by-letter effect.** That is the menu's 19 "Letter" rows (among them #2 Typewriter, #7 Write on, #10 Drop in, #14 and #24 Tracking, #30 Text on a path). No motion below cuts a label into letters. Labels move whole, or by line, or by word, which the menu calls "likely safe in any language" (also untested: section 6).
- Where a motion has no menu row, the table says so.

**File format (F3).** After the style's text, a blank line, a line `motions:`, then one line per motion. Example for the head and the end of `lively.md`:

```
title: Lively
for: explainers, training
first: training-education
also: documentary-explainer, social-ugc
energy: 4

(the style's text, section 1.5)

motions:
- Label slide (a label arriving): …
- Build in order (a part appearing): …
```

The lines to put in each file are the "Line for the file" blocks below.

### 2.2 Restrained (energy 3; no overshoot; one thing at a time, no overlap)

| Name | Job | How it moves | Menu row | Level |
|---|---|---|---|---|
| Label fade | A label arriving | Fades in where it stands, over 0.5 s, on the word it belongs to; gentle ease-out; no travel | #1 Fade up, with the travel taken out | 1 |
| Build in order | A part appearing | Each part fades up while travelling a short way (about 2 % of the frame width), 0.6 s, long ease-out; the next starts only when this one is at rest | #48 Line-by-line reveal | 2 |
| Dim the rest | Stressing one part | Everything else goes one step paler over 0.4 s; the part itself does not change; no new colour, no glow; the rest returns over 0.4 s when the narration moves on | #13 Highlight, changed for a diagram | 2 |
| Cross-fade | A change of state, before and after | The old state fades out as the new fades in, 0.8 s, ease in and out | #76 Crossfade (0.4 s in the menu; slowed for this style) | 1 |
| Quiet leave | Leaving | Fades out in place over 0.25 s, speeding up | #57 Fade or blur out | 1 |

Line for the file:

```
motions:
- Label fade (a label arriving): fades in where it stands over 0.5 s on its word, gentle ease-out, no travel.
- Build in order (a part appearing): each part fades up while travelling a short way, about 2 % of the frame width, over 0.6 s on a long ease-out; the next starts only when this one is at rest.
- Dim the rest (stressing one part): everything else goes one step paler over 0.4 s; the part itself does not change; no new colour, no glow; the rest returns when the narration moves on.
- Cross-fade (a change of state): the old state fades out as the new fades in, 0.8 s, easing in and out.
- Quiet leave (leaving): fades out in place over 0.25 s, speeding up.
```

### 2.3 Editorial (energy 3; no overshoot; one at a time; everything a second or more)

| Name | Job | How it moves | Menu row | Level |
|---|---|---|---|---|
| Mask rise | A label arriving | The line rises from behind a straight mask, word by word, 100 ms apart, each word 1.0 s on a very gentle ease-out | #4 Mask reveal, #44 Stagger rise (both "Word") | 2 |
| Slow fade | A part appearing | Fades in where it stands over 1.0 s | #5 Blur in, without the blur | 1 |
| Rule draw | Stressing one part or word | A thin rule draws under the word or along the part's edge in 0.6 s, in the accent colour; one on screen at a time | #67 Underline draw ("More than one per screen": avoid) | 2 |
| Long dissolve | A change of state | The picture fades through the background colour to the new state, 1.2 s | #76 Crossfade, slowed | 1 |
| Quiet leave | Leaving | Fades out in place over 0.5 s | #57 Fade or blur out | 1 |

```
motions:
- Mask rise (a label arriving): the line rises from behind a straight mask, word by word, a tenth of a second apart, each word over 1 s on a very gentle ease-out.
- Slow fade (a part appearing): fades in where it stands over 1 s.
- Rule draw (stressing one part or word): a thin rule in the accent colour draws under the word or along the part's edge in 0.6 s; one on screen at a time.
- Long dissolve (a change of state): the picture fades through the background colour to the new state over 1.2 s.
- Quiet leave (leaving): fades out in place over 0.5 s.
```

### 2.4 Data-led (energy 3; no overshoot; one mark at a time)

| Name | Job | How it moves | Menu row | Level |
|---|---|---|---|---|
| Grow from the baseline | A chart growing | A bar grows from its baseline, a line draws from left to right; one mark at a time in the order the narration reads them; each 0.8 s on a firm ease-out; stops exactly on its value | #91 Chart grow ("Real data", "3 to 5 bars", 1.2 s) | 3 |
| Count up | A counter or number | The figure counts to its real value in the same 0.8 s as its mark and lands with it; tabular figures | #42 Counter ("A real number") | 3 |
| Label fade | A label arriving | Fades in over 0.3 s the moment its mark stops; no travel | #1 Fade up, without the travel | 1 |
| Accent pair | Stressing | The two compared marks take the accent colour over 0.4 s; the rest goes one step paler | #13 Highlight, changed | 2 |
| Re-flow | A change between two charts | The marks move to their new sizes and places over 0.8 s, easing in and out; or a clean cross-fade of 0.4 s when the two charts share nothing | #76 Crossfade, #78 Mask wipe swap | 2 |

```
motions:
- Grow from the baseline (a chart growing): a bar grows from its baseline, a line draws from left to right, one mark at a time in the order the narration reads them, each over 0.8 s on a firm ease-out, stopping exactly on its value.
- Count up (a number): the figure counts to its real value in the same 0.8 s as its mark and lands with it.
- Label fade (a label arriving): fades in over 0.3 s the moment its mark stops; no travel.
- Accent pair (stressing): the two compared marks take the accent colour over 0.4 s; the rest goes one step paler.
- Re-flow (a change between two charts): the marks move to their new sizes and places over 0.8 s, easing in and out; a clean cross-fade of 0.4 s when the two charts share nothing.
```

### 2.5 Technical (energy 3; no overshoot; linear or nearly so)

| Name | Job | How it moves | Menu row | Level |
|---|---|---|---|---|
| Draw on | A part appearing (an outline) | The outline draws along its length at a steady speed, 0.6 to 1.0 s by its length; then its fill fades in over 0.3 s | #54 Outline then fill (status B in the menu: no piece exists; hand-built, as everything here) | 2 |
| Fit along the axis | A part appearing (an assembly) | The part travels along the axis it would be fitted on, 0.6 s, nearly linear with a short ease-out, and stops exactly in place; parts come in the order they are built in reality | #43 Slide in | 3 |
| Leader then label | A callout | A thin leader draws from the part to the label's place in 0.6 s; the label fades in at its end over 0.3 s and holds | #85 Leader line callout (0.6 s) | 2 |
| Dim the rest | Stressing one part | As in Restrained | #13 Highlight, changed | 2 |
| Quiet leave | Leaving | Fades out in place over 0.25 s | #57 | 1 |

```
motions:
- Draw on (an outline appearing): the outline draws along its length at a steady speed, 0.6 to 1 s by its length; then its fill fades in over 0.3 s.
- Fit along the axis (a part of an assembly appearing): the part travels along the axis it would be fitted on, 0.6 s, nearly linear, and stops exactly in place; parts come in the order they are built in reality.
- Leader then label (a callout): a thin leader draws from the part to the label's place in 0.6 s; the label fades in at its end over 0.3 s and holds.
- Dim the rest (stressing one part): everything else goes one step paler over 0.4 s; the part itself does not change; the rest returns when the narration moves on.
- Quiet leave (leaving): fades out in place over 0.25 s.
```

### 2.6 Lively (energy 4; a slight overshoot on position only; overlap 30 to 50 %)

| Name | Job | How it moves | Menu row | Level |
|---|---|---|---|---|
| Label slide | A label arriving | Slides in from the side of the thing it names, a short way (up to 4 % of the frame width), 0.4 s, ease-out; goes a few pixels past its place and settles; then still | #43 Slide in; overshoot "Normal: a little" | 3 |
| Build in order | A part appearing | Each part comes from where it belongs, 0.5 s, with a small settle; the next starts when the one before is 30 to 50 % done. One part in the shot may travel in from the edge of the frame: that is the strongest move, and it is on the claim | #48 Line-by-line reveal; the menu's overlap and stagger settings | 3, the one from the edge 4 |
| Dim the rest | Stressing one part | Everything else goes one step paler over 0.4 s; the part does not change | #13 Highlight, changed | 2 |
| Wipe between states | A before-and-after of the whole picture | A straight edge crosses the frame in 1.0 s, easing in and out, with the new state behind it. A single part's change is a movement on the part (it moves, turns or fills) over 0.6 s | #93 Before and after split (1 s), #78 Mask wipe swap | 3 |
| Quiet leave | Leaving | Fades out in place over 0.2 s, speeding up | #57 (0.2 s) | 1 |

```
motions:
- Label slide (a label arriving): slides in from the side of the thing it names, a short way, up to 4 % of the frame width, over 0.4 s; goes a few pixels past its place, settles, then is still.
- Build in order (a part appearing): each part comes from where it belongs over 0.5 s with a small settle; the next starts when the one before is about a third to a half done. One part in the shot may travel in from the edge of the frame: that is the strongest move.
- Dim the rest (stressing one part): everything else goes one step paler over 0.4 s; the part itself does not change; the rest returns when the narration moves on.
- Wipe between states (a before-and-after of the whole picture): a straight edge crosses the frame in 1 s, easing in and out, the new state behind it. A single part's change is a movement on the part, over 0.6 s.
- Quiet leave (leaving): fades out in place over 0.2 s, speeding up.
```

### 2.7 Product (energy 4; no bounce; long even eases)

| Name | Job | How it moves | Menu row | Level |
|---|---|---|---|---|
| Turn to face | Presenting a part | The object turns so the feature faces the viewer, 1.0 to 1.5 s, a long even ease in and out; the frame does not move | No menu row. From the style's own text (nearest: #80 Rotating cube, status B) | 3 |
| Leader then label | A callout | A thin line runs from the feature to its label in 0.6 s; the label fades in over 0.3 s and holds; never two callouts at once | #85 Leader line callout | 2 |
| Dim the rest | Stressing one part | The rest dims slightly over 0.4 s; the feature keeps its brightness | #13 Highlight, changed | 2 |
| Change in place | A change of state (open, closed, on, off) | Shown on the object itself, where it is, over 0.8 s | #76 Crossfade | 2 |
| Clear | Leaving | The line and the label fade together over 0.3 s before the next callout | #57 | 1 |

```
motions:
- Turn to face (presenting a part): the object turns so the feature faces the viewer, over 1 to 1.5 s on a long even ease; the frame does not move.
- Leader then label (a callout): a thin line runs from the feature to its label in 0.6 s; the label fades in over 0.3 s and holds; never two callouts at once.
- Dim the rest (stressing one part): the rest dims slightly over 0.4 s; the feature keeps its brightness.
- Change in place (a change of state): shown on the object itself, where it is, over 0.8 s.
- Clear (leaving): the line and the label fade together over 0.3 s before the next callout.
```

### 2.8 Bold (energy 5; no bounce, things stop dead; anticipation allowed)

| Name | Job | How it moves | Menu row | Level |
|---|---|---|---|---|
| Slam | A label or a part arriving | Arrives large, from a third larger down to its size, in 0.3 to 0.4 s on a sharp ease that starts fast and stops dead; then still | #9 Stamp, #56 Fly from camera (both "Line") | 4 |
| Colour wipe | A change of state, a new idea | A block of the accent colour crosses the whole frame in 0.5 s; the new picture is behind it. Once in a shot it may be the strongest move | #49 Wipe ("A brand colour", 0.6 s) | 3; as the strongest move 5 |
| Cut closer | Stressing one part | A hard cut to a closer framing of the part; nothing travels | No menu row. `references/motion.md`: "Hard cuts belong inside a scene (punch-ins)" | 4 |
| Count up | A counter or number | The figure counts to its real value in 0.6 s and stops dead | #42 Counter | 3 |
| Push out | Leaving | The old label is pushed out by the next in 0.2 s, in the direction the next arrives | #75 Push; the menu's handover check | 2 |

```
motions:
- Slam (a label or a part arriving): arrives large, from a third larger down to its size, in 0.3 to 0.4 s on a sharp ease that starts fast and stops dead; then still.
- Colour wipe (a change of state): a block of the accent colour crosses the whole frame in 0.5 s, the new picture behind it. Once in a shot it may be the strongest move.
- Cut closer (stressing one part): a hard cut to a closer framing of the part; nothing travels.
- Count up (a number): the figure counts to its real value in 0.6 s and stops dead.
- Push out (leaving): the old label is pushed out by the next in 0.2 s, in the direction the next arrives.
```

### 2.9 Playful (energy 5; a clear bounce on position and size only; a wind-up before leaving)

| Name | Job | How it moves | Menu row | Level |
|---|---|---|---|---|
| Pop | A label arriving | Pops from four fifths of its size to full size with one clear bounce, 0.3 s, at a small angle that straightens as it lands; then still | #3 Pop in (0.3 s, "Line") | 3 |
| Drop and settle | A part appearing | Drops or hops into place in 0.5 s, goes past, squashes a little and recovers; each part about a tenth of a second off the beat of the one before | #45 Spring in; the menu's overshoot and stagger settings | 4 |
| Bounce ring | Stressing one part or number | A ring draws round it in 0.5 s and bounces once | #16 Hand-drawn circle (0.5 s) | 3 |
| Flip | A change of state | The part stretches, flips or puffs into its new state in 0.6 s; it is still the same part | #46 Flip in (status B; used here on a part, never on letters) | 3 |
| Wind up and go | Leaving | A small move back for 0.1 s, then away in 0.3 s | #62 Shrink to dot; the menu's anticipation setting | 3 |

```
motions:
- Pop (a label arriving): pops from four fifths of its size to full size with one clear bounce in 0.3 s, at a small angle that straightens as it lands; then still.
- Drop and settle (a part appearing): drops or hops into place in 0.5 s, goes past, squashes a little and recovers; each part about a tenth of a second off the beat of the one before.
- Bounce ring (stressing one part or number): a ring draws round it in 0.5 s and bounces once.
- Flip (a change of state): the part stretches, flips or puffs into its new state in 0.6 s; it is still the same part.
- Wind up and go (leaving): a small move back for a tenth of a second, then away in 0.3 s.
```

### 2.10 The extra motions (for a job the film's family does not cover)

These five live once, in the skill (F4). A film uses one only when a shot needs that job and the family has none for it.

| Name | Job | How it moves | Menu row |
|---|---|---|---|
| Leader then label | A callout | A thin leader draws from the part to the label's place in 0.6 s; the label arrives at its end by the film's own label motion and holds. Leaders never cross; a leader ends plainly | #85 |
| Count up | A number | Counts to its real value in 0.6 to 1.0 s and lands with its mark | #42 |
| Grow from the baseline | A chart | One mark at a time, each 0.6 to 0.8 s, stopping exactly on its value | #91 |
| Wipe between states | A before-and-after | A straight edge crosses in 0.6 to 1.0 s, the new state behind it | #93 |
| Step list | Points or steps, one at a time | Each item arrives by the film's own label motion, 0.4 s apart | #92 Checklist tick (0.4 s per item) |

Pace: a calm style (Restrained, Editorial, Data-led, Technical) takes the longer time and no overshoot; Lively and Product the middle; Bold and Playful the shorter time, with the style's own landing.

---

## 3. Which wins: the style or the skill's `references/motion.md`

**Today.** `plugin/skills/motion/SKILL.md`, under "Motion craft, for these shots":

> How things move and appear is the film's, not this skill's: follow the brief's "Motion style" part for the pace, the arrivals, the labels, the camera and the changes between states. Where the brief's own lines for this shot ask for something the style does not, the brief's lines win for that shot. A line the viewer reads holds at least 0.5 s plus 0.3 s a word.

So the style already wins over the reference. The trouble on VW-24 was the other way round: the reference says "a landed title is dead still" and lists "a slow push late in a scene" as looking generated, and the Lively style overruled it. With F1 and F2 the two no longer disagree on those points.

**The order, from strongest to weakest:**

1. The shot's own lines in the brief (what it shows, its claims, its labels and cue times, a camera move it asks for).
2. The fixed paragraph "In every style" (F1). The only thing above it is a shot's own line that asks for a frame move.
3. The style's text and its motions.
4. `references/motion.md`, only for a number the three above do not give (an ease, a stagger, an overlap, the length of an exit).

Parts of the reference that are about a whole film do not apply to one drawn shot: the beat grid, the transitions between worlds (zoom through a button, whip, iris), the title sizes of 4 to 9 %, "per letter for a name".

**The exact paragraph to put in the skill**, replacing the one quoted above:

```
How things move and appear is the film's, not this skill's. Follow, in this order: the lines of the brief that are about this shot; then the brief's "In every style" lines; then its "Motion style" text and the motions it names. Use the film's named motions for their jobs and no others; for a job they do not cover (a callout, a number, a chart, a before-and-after, a list of steps) use the extra motion of that job below, at the style's pace. Read references/motion.md only for a number none of these gives (an ease, a stagger, an overlap, how long an exit takes); where it disagrees with the brief, the brief wins. Its parts about a whole film (the beat grid, transitions between scenes, title sizes, letter-by-letter text) are not for a drawn shot. In REVIEW.md, name each motion you used and which move is the strongest.
```

Under it, the five extra motions of 2.10, one line each, in the words of that table.

The old sentence "A line the viewer reads holds at least 0.5 s plus 0.3 s a word" is dropped from the skill: the fixed paragraph now carries it, in one place.

---

## 4. Where each piece goes

| Piece | Goes in | How it reaches the builder |
|---|---|---|
| The style's changed text (section 1) | `server/motion_styles/<name>.md`, the body | `film.style_part` → the "Motion style" part at the end of every brief (`visuals_stage.motion_brief`, its last line). No change in `motion_brief` |
| The energy limit | The same file, a head line `energy: 3` (4, 5) | It does not reach the builder. `film.styles()` reads head lines but keeps only title, for, first, also; an extra head line is ignored today, so the line is safe to add. A unit test pins that each file has one of 3, 4, 5 |
| The family (section 2) | The same file, after a line `motions:` | `film.styles()` splits the body at that line into `text` and `motions`. `style_part` prints the text, then "The motions of this film, by name. Use these for these jobs and no others:", then the motion lines. A file with no such section prints no motions line (nothing breaks) |
| The fixed paragraph (1.0) | One constant in `server/app/film.py` | `style_part` prints it last, for every style |
| The film's motions, named once | The shared-look list (design/221, row 7): one line, "Motions (style Lively): Label slide, Build in order, Dim the rest, Wipe between states, Quiet leave. Extra for this film: Leader then label." | The assistant writes it before the first build from the film's style and the jobs the approved specs need. Every builder and checker gets the list. No question to the operator: there is no fact in it |
| The order of who wins; the extra motions | `plugin/skills/motion/SKILL.md` (section 3) | The builder loads the skill first |
| "Name each motion you used" | The same paragraph of the skill; `plugin/agents/vw-motion-shot.md` needs no change (it says "follow it exactly") | `REVIEW.md` |

**What must not become a fact-check rule.** Everything in this note is guidance for the builder. None of it goes into `rules.md`.

- `vw-motion-rules.md` already says: "The brief's 'Motion style' part says how things may move and appear in this film: it is what is allowed, not a list of rules to copy. Write no rule that restricts motion unless the brief asks for it". Add one sentence after it:

```
The same holds for the "In every style" lines and the named motions: write no rule from them, and no rule with a time or a distance of a movement (a hold, a stagger, how long a fade takes).
```

- `vw-motion-check.md` already says: "never fail a frame for a movement, a build, a camera move or a way a label arrives that the style allows." Add:

```
Nor for a movement that differs from the film's named motions or from the "In every style" lines: those are the builder's guidance, not rules. A fault a viewer would see in a frame is still a fault.
```

- Why: the check already holds 47 to 74 rules a drawing; exact numbers in look rules failed on VW-24 ("28 px" at 24 px; "three quarters" at 65 %); and design/179 S5 decided it.
- The one time check that stays is the server's own: a label on screen too short (design/221 row 17). It is measured by the server, not written by the rule writer.
- Who then sees a builder that ignored the family? The main assistant reads each `REVIEW.md` ("name each motion you used") against the shared look; and SK sees the drawing. A drawing is never sent back by the fact check for it. Whether it is sent back at all is question 2.

**Edge cases for the build**

| Case | Handling |
|---|---|
| A shot's own lines ask for a push-in or a pan | Allowed: the fixed paragraph says "unless this shot's own lines above ask for it". The builder uses the one tested way of row 8 (the whole picture as one group) |
| The next cue comes sooner than the hold of 0.5 s plus 0.3 s a word | The cue time wins: it is a fact of the brief and the server checks it. The builder says so in `REVIEW.md` |
| A shot shorter than 2 s | "or to the end of the shot when the shot is shorter" |
| A shot with no label | The label lines do not apply; the rest does |
| A film with one drawn graphic | The family still applies; no shared look is needed |
| A style file without a `motions:` section (a style added later) | The brief prints the style and the fixed paragraph; no motions line |
| A film on the older fixed style (`film.OLDER_STYLE`) | Nothing built for it (old runs are dropped, SK 18 Nov). Its text already says "a label that lands and holds dead still, a slow push-in only when the brief asks" |
| The style is changed after drawings were built | Not covered today (design/179, E9) and not covered here |
| A label in Tamil or Hindi | Moves whole or by word only; see section 6 |

**Old ways (for design/35)**

- Retired: Lively's "Avoid stillness longer than about two seconds"; the camera that follows the subject (Lively), pans along the object (Technical), orbits (Product), bobs (Playful), snaps by a whip (Bold); Restrained's slow push-in as a shot idea; Editorial's drifting frame and its letter spacing reveal; the hold sentence in the skill (moved to the fixed paragraph).
- Kept: a frame move that a shot's own brief lines ask for.

**Tests to write first (area tests only)**

- Each of the eight files: a head line `energy` of 3, 4 or 5; a `motions` section of 4 or 5 lines; the body still 120 to 260 words, no backquote, no film code.
- `style_part` for a film: holds the style's first sentence, the words "The motions of this film", each motion's name, and the fixed paragraph once.
- No style text holds "Avoid stillness", "pans and gentle zooms", "camera bobs", "camera orbits", "whole frame drifts", "letters easing".
- The skill holds the new paragraph and the five extra motions; the rule writer and the checker hold their new sentence (wording script and its pins).
- Version: the brief's new lines are read by an older skill without harm, so the plugin minimum need not rise for this alone **(judgement)**.

---

## 5. Adverts and social clips: the menu's rules that apply there and not to explainers

The menu was written for these films ("A 6-second ad", "Most social video is watched on mute", "the one hero line"). Filed by category, by SK's rule of 2 Nov. VW2's categories that take them: `advertisement-product` and `social-ugc`. Not for `documentary-explainer`, `training-education`, `narrative-story`.

| Menu rule | Explainer, training (general set) | Advert, social (filed under the category) |
|---|---|---|
| Rule 4, no repeats in a row: "The same entrance does not come twice in a row." | **Does not apply.** In a diagram every label arriving the same way is right: the viewer learns the pattern | Applies to lines of text: two neighbouring lines do not enter the same way |
| Rule 1, small steps: "Energy changes by 1 or 2 levels between neighbours. Never by 3 or more, except into the hero line." | Not applied: each drawn shot is built alone and has few moves | Applies across the lines of the film |
| Rule 2, one hero | One strongest move **per shot**, on the claim (the fixed paragraph) | One hero line **per film**: "The strongest animation goes there, and only there" |
| Rule 5, family size by length: "A 15-second ad: 3 animations. A 60-second video: up to 5." | The style's 4 or 5 motions, whatever the length | Applies as written |
| The handover: "If a line exits to the left, the next one enters from the right, as if pushed." | Not applied; a drawing that continues another starts on its last frame (design/221 rows 2 and 5) | Applies to lines that replace each other |
| Question 3, mute: "Most social video is watched on mute." | Not applied: the narration carries the film | Applies: the text on screen must carry the message without the voice |
| Question 2, length: "A 6-second ad cannot spend 2 seconds on one animation." | Not applied | Applies: no single move longer than a fifth of the film **(judgement on the number)** |
| The text-led rows of the menu (#25 Text flip, #26 Word carousel, #15 Strikethrough, #39 Karaoke captions, #84 Word-pop captions and the like) | Not used in drawn graphics | A later piece of work: title cards and captions. Not part of design/221 |

**The text for the category** (to be filed when it is wired, not now):

```
For an advertisement or a social clip: the film has one hero line, and the strongest move of the whole film is on it. Two neighbouring lines of text do not enter the same way. The energy of neighbouring lines rises or falls in small steps, except into the hero line. A film of about 15 s uses three motions in all; one of a minute, up to five. A line that replaces another enters from the side the other left by. The text on screen carries the message with the sound off.
```

**Where it is filed.** The cheapest place is a folder `server/motion_styles/categories/<category>.md`, read by `style_part` and printed after the fixed paragraph (`film.styles()` reads only the files directly in `motion_styles`, so a sub-folder does not disturb it). To check at build whether the brief already has a place for rules by category; if it has, use that.

**Recommendation: write the text now, wire it later.** No advert or social film has drawn graphics yet, the VW-24 redo is an explainer, and nothing here can be tested on it. Question 3.

---

## 6. What is untested, and the smallest test for each

By the menu's own words: "Nothing here is tested on a real video. The scores and limits are judgement. Correct them after 2 or 3 videos." By design/179: "The styles are drafts. None is 'kept' until it is rendered on the bench shots and SK has looked at it; that bench run is not done."

| # | Untested | The smallest test that settles it | Cost |
|---|---|---|---|
| T1 | That the new Lively text gives fewer movement faults, and that the result is not dull | Build one drawing, BEAT_04-B1-S5, from its stored brief with the new Lively text and the fixed paragraph. Compare with its three stored rounds: frames inside moves, the ghost, the note over the line. SK looks at both | One build, no run |
| T2 | The hold of 0.5 s plus 0.3 s a word against real narration | On VW-24's stored briefs (read only): for each label, the time from its cue to the next cue or the shot's end, against its hold. Count the labels that cannot have their hold. No drawing is built | A script over stored data |
| T3 | That builders keep to the family | On the VW-24 redo: read each `REVIEW.md`; count drawings that used only the named motions; list the motions used outside them | Reading, on the redo |
| T4 | The times and distances of section 2 (0.2 to 1.5 s; 2 % and 4 % of the width) | The redo's snapshots at the middle of each move, and SK's eye on the rendered drawings. Change the numbers in the style files after it; no code | On the redo |
| T5 | The energy scale for diagrams and the style-to-mode mapping | After the redo: for each drawing, name its strongest move and its level; check it is on the claim and within the style's limit | Reading, on the redo |
| T6 | Word-by-word and whole-label moves in Tamil and Hindi ("likely safe" is the menu's word, not a test) | One label in Tamil and one in Hindi, in the film's font, with Label slide and with Mask rise; snapshots mid-move; look for a broken or split letter group | Two tiny projects on the bench |
| T7 | Letter-by-letter effects in Tamil and Hindi | The same two labels with one letter-by-letter reveal. Until this passes, the fixed paragraph's last sentence stays | With T6 |
| T8 | The seven styles other than Lively, with their new texts and families | The bench shots of design/179, one drawing per style; SK looks | Seven builds; not needed for the VW-24 redo |
| T9 | Count up with digits that are not Latin, and with a unit beside the figure | One number label per script on the bench | With T6 |
| T10 | The advert and social text of section 5 | The first film of that category with drawn graphics | Later |

T1 and T2 can be done before anything is deployed. T3, T4 and T5 are read off the redo that design/221 already plans.

## 7. Open questions for SK

1. **The camera lines in the styles VW-24 did not test.** The evidence is one Lively film. This note also takes the frame moves out of Technical (pan, step closer), Product (orbit), Playful (bob), Bold (whip) and Editorial (the drifting frame), with a shot's own brief line as the way back in. Recommended: yes, all eight, so one fixed paragraph is true everywhere. Or only Lively, Restrained and Technical for now?
2. **Is the family binding?** Recommended: the builder uses the film's motions and no others, names them in `REVIEW.md`, and the main assistant sends a drawing back once if it used others without a reason from the shot's brief. Never a fact-check rule. Or is it guidance only, with no send-back?
3. **Adverts and social clips.** Recommended: keep section 5 as text in this note and wire it when the first such film has drawn graphics. Or wire it now, untested?

## Not covered

- The tested push-in recipe (design/221, row 8) and the shared-look list itself (row 7): this note only says what they receive.
- No frame, no brief and no project of VW-24 was looked at; no drawing was built in any new text; no word count of the new texts was run.
- The times, distances, levels and the style-to-mode mapping are judgement on top of an untested menu.
- Title cards, captions and other text-led work for adverts and social clips, where most of the menu's 98 rows belong.
- A style changed after drawings were built (design/179, E9).
- Whether the brief already has a place for rules filed by category.
