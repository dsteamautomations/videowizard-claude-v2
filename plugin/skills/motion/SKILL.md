---
name: motion
description: Build one drawn shot of a VideoWizard film as a HyperFrames composition (HTML + GSAP), from the shot's brief, checked, snapshotted and uploaded with the vw motion commands. Used by the vw-motion-shot helper on a film started with --drawn motion.
---

# Motion: one drawn shot as a HyperFrames composition

You build one drawn shot. HyperFrames renders HTML to video by seeking a paused GSAP timeline frame by frame, so every render is identical. The CLI runs on the VideoWizard server, not here: **never run `npx`, `node` or `hyperframes`**; use the `vw motion` commands below. Lines in the references that say `npx hyperframes …` mean the `vw motion` command of the same job.

## Your folder

`runs/<code>/work/motion/<shot>/` holds `brief.md` (read it first, whole), `rules.md` (the numbered rules a fact checker will hold your frames to: every one must be plainly true in your drawing) and `refs/` (the approved pictures, to look at). `questions.md` beside them holds the rule writer's questions and notes: they are not rules, and they are not yours. The main assistant decides each point (a choice with no fact behind it is its own, and logged; a question about a fact goes to the operator once, with the others, before the first drawing is built). Build the project in `work/motion/<shot>/project/`: `index.html` at its root, one scene in `compositions/`. Write every file by hand; there is no `init`.

The server places these at check and render; refer to them, never create them:
- `assets/vendor/gsap.min.js`: GSAP (load it with `<script src="assets/vendor/gsap.min.js">`).
- `assets/fonts/<file>`: the fonts the brief names; declare each with `@font-face` and use only those families.
- `assets/ref/<id>.png`: the approved pictures the brief lists.

## The brief is the contract

- A note on the view or a colour the brief lists as added is below the spec: the spec wins where they differ.
- The brief's "Shared look (every drawing of this film)" lines hold for every drawing of the film, below the spec like a note. The main assistant recorded them before the first brief: a choice with no fact in it is its own, and logged; one that changes a fact or a proportion was asked once, with the others, before the first drawing was built. Never stop to ask about them.
- The root's `data-duration`, `data-fps`, `data-width`, `data-height` are exactly the brief's. The length is to the frame.
- A part another drawing shows from another direction or at another scale is the same part: draw it as this drawing's spec and view say, and make the change of view readable (the view visibly turns or cuts; a label such as "section" only where the brief lists it); never a part that morphs into another shape.
- Every text on screen is one of the brief's labels, word for word, and nothing else. Put each label in an element with a stable `id`. The corner note the brief names is drawn by the server in the lower right corner: never draw it, and keep that corner free.
- What appears when follows the narration: an element named by a word appears at that word's second (the brief lists each word's start). The plan's cues (`#id` at a word) are checked by the server against the render.
- Open the pictures the brief lists under "Look at these before you draw" first: a part the film is about is drawn from what its picture shows, not from the words alone.
- The claims and the drawing spec are facts: draw the parts, sizes, relationships and proportions as the spec says, and only those. A real object is drawn as it is built (a wall shows its bond; an opening has a lintel); when unsure, draw less, never something false.
- Colours are the brief's palette, with the colours it lists as added for every drawing. A thing the palette gives no colour: choose a neutral (a grey, an off-white or a near-black) that keeps it apart from what touches it and name it in `REVIEW.md` under "Colours added" (the thing, #RRGGBB, its words, one reason); never stop to ask. A real hue is the operator's: name it in `REVIEW.md` as a question.
- Silent: no audio, no music.

## Contract (HyperFrames)

1. Every timed element has `class="clip"`, `data-start` and `data-duration` in seconds and shows over `[start, start + duration)`.
2. Each composition builds one paused timeline and registers it after its tweens: `window.__timelines["<data-composition-id>"] = tl`. The host, the scene root and the timeline key share one id.
3. No `Date`, `Math.random`, timers, network fetches or `repeat: -1`: everything visible is a function of timeline time.
4. Never tween `display` or `visibility` on a `.clip`; animate a child. No CSS `transform` on an element GSAP transforms. Use `fromTo`, not `from`.
5. A scene file puts its styles, markup and scripts inside `<template>` and styles its root as `#root` (`inset: 0`).
6. Asset paths are `assets/...` with no leading `/`.
7. Content inside the 90 % action-safe box, text inside the 80 % title-safe box; every label at least 2.6 % of the frame height.

Details: `references/format.md` (the project shape, attributes, timing) and `references/motion.md` (eases, entrances, holds, what looks generated). Read them from the plugin's `skills/motion/references/` folder.

## Motion craft, for these shots

How things move and appear is the film's, not this skill's. Follow, in this order: the lines of the brief that are about this shot; then the brief's "In every style" lines; then its "Motion style" text and the motions it names. Use the film's named motions for their jobs and no others; for a job they do not cover (a callout, a number, a chart, a before-and-after, a list of steps) use the extra motion of that job below, at the style's pace. Read references/motion.md only for a number none of these gives (an ease, a stagger, an overlap, how long an exit takes); where it disagrees with the brief, the brief wins. Its parts about a whole film (the beat grid, transitions between scenes, title sizes, letter-by-letter text) are not for a drawn shot. In REVIEW.md, name each motion you used and which move is the strongest.

A motion outside these only for a reason the brief's lines for this shot give: say the reason in REVIEW.md. The main assistant sends a drawing back once when it used another motion without one.

The extra motions (a calm style takes the longer time and no overshoot; Lively and Product the middle; Bold and Playful the shorter, with the style's own landing):
- Leader then label (a callout): a thin leader draws from the part to the label's place in 0.6 s; the label arrives at its end by the film's own label motion and holds. Leaders never cross; a leader ends plainly.
- Count up (a number): counts to its real value in 0.6 to 1 s and lands with its mark.
- Grow from the baseline (a chart): one mark at a time, each 0.6 to 0.8 s, stopping exactly on its value.
- Wipe between states (a before-and-after): a straight edge crosses in 0.6 to 1 s, the new state behind it.
- Step list (points or steps, one at a time): each item arrives by the film's own label motion, 0.4 s apart.

## The camera

The brief's "Camera" line names the shot's one camera flow (Fixed when the plan names none): Fixed (the frame does not move); Step closer (once, from the whole to one part); Pull back (once, from one part to the whole); Pan along (a long object, a process in a line, a map); Follow (a step closer as each part is named, at most three in the shot); Slow push-in (a few percent, to hold one idea through a long sentence, only when no label is near the edge).

1. One camera flow per shot: the one the brief names, and no other move of the frame.
2. The one way to move the camera: the whole picture is one group that scales and moves; nothing inside it moves to fake the camera. The corner note is the server's and stays outside it.
3. A label lands only after the camera has come to rest; its reading time counts from then.
4. Keep the lower right corner free: the server draws the corner note there, outside the moving picture.
5. A drawing that continues another opens exactly as the earlier shot ended.
6. Judge a label's size at the end framing.
7. Never move the camera during a comparison or a quantity: a zoom changes how big things look. The plan gives such a shot Fixed.
8. Advice: do not move the camera at the moment a part changes state; it makes the change harder to follow.
9. The move starts on the narration's word and is never faster than the eye can follow.
10. The last second of the shot is still.

## A finish, when it suits the shot

A finish is a layer of effects the **server** adds on top of your drawing at snapshot and render: `blur` (a camera-like blur on the parts that move), `grain` (a fine film grain) and `vignette` (a soft darkening of the corners). It changes how the drawing looks, never what it shows. You never write or paste its code.

- To ask for one, put `finish.json` at the project root: a list with any of the three, for example `["blur", "grain", "vignette"]`. For blur, also put the attribute `data-hf-motion-blur` on each HTML element your timeline moves by `transform` (the element that moves, not a container, and not an element inside an `<svg>`). Nothing else.
- **Your drawing must be complete and right without the finish.** The operator can have it taken away, and the server leaves it off by itself if it cannot be drawn; the shot is then your drawing alone.
- Whether a finish suits is decided by the brief's "Motion style": a calm, still style takes `grain` and `vignette` at most; a style with parts that travel fast may take `blur` as well. With no reason from the style, ask for none.
- Keep one finish for all the drawn shots of a film: if the brief or an earlier shot's `REVIEW.md` names the film's finish, use the same.
- Look at your snapshots with the finish on (they come that way). If a label is harder to read, or a moving label smears while it must be read, take that effect out of `finish.json`.
- Say in `REVIEW.md` which finish you asked for and why, or that you asked for none.

## The loop

1. Read `brief.md` and `rules.md`, look at `refs/`, read the two references. When the brief says "Continues from <shot>", the main assistant puts that shot's last frame in `refs/continues-from.png`: start your drawing where it ends. With no pictures in `refs/`, first build the key frame as a still (everything in place, nothing moving), upload and snapshot it, and stop: answer "key frame ready" with its sha256, so it is checked before you animate.
2. Write the project. Then `vw motion upload --shot <shot>` (it zips `project/` and checks the rules; a refusal names each rule broken: fix and upload again).
3. `vw motion check --shot <shot>`: HyperFrames' own check on the server (lint, layout, contrast, timing). Fix every error; weigh every warning.
4. `vw motion snapshot --shot <shot> --at <t1,t2,…>`: PNGs saved to `snapshots/`, always the same set: the first frame, each cue, the middle of each move, the last frame, and a close-up of each labelled part (`--crop`). Look at every one as a stranger would: does it read as what it is, is every label whole and spelled as the brief says, does anything collide or leave the frame?
5. Fix, upload, check, snapshot again until clean. Then write `work/motion/<shot>/REVIEW.md`: what you built, what you checked, the weakest point, the warnings you kept and why, and the sha256 of the last upload.

You never render the delivery and never edit the plan: the main assistant names your upload in the plan and renders it.
