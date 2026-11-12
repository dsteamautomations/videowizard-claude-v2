---
name: motion
description: Build one drawn shot of a VideoWizard film as a HyperFrames composition (HTML + GSAP), from the shot's brief, checked, snapshotted and uploaded with the vw motion commands. Used by the vw-motion-shot helper on a film started with --drawn motion.
---

# Motion: one drawn shot as a HyperFrames composition

You build one drawn shot. HyperFrames renders HTML to video by seeking a paused GSAP timeline frame by frame, so every render is identical. The CLI runs on the VideoWizard server, not here: **never run `npx`, `node` or `hyperframes`**; use the `vw motion` commands below. Lines in the references that say `npx hyperframes …` mean the `vw motion` command of the same job.

## Your folder

`runs/<code>/work/motion/<shot>/` holds `brief.md` (read it first, whole), `rules.md` (the numbered rules a fact checker will hold your frames to: every one must be plainly true in your drawing) and `refs/` (the approved pictures, to look at). Build the project in `work/motion/<shot>/project/`: `index.html` at its root, one scene in `compositions/`. Write every file by hand; there is no `init`.

The server places these at check and render; refer to them, never create them:
- `assets/vendor/gsap.min.js`: GSAP (load it with `<script src="assets/vendor/gsap.min.js">`).
- `assets/fonts/<file>`: the fonts the brief names; declare each with `@font-face` and use only those families.
- `assets/ref/<id>.png`: the approved pictures the brief lists.

## The brief is the contract

- The root's `data-duration`, `data-fps`, `data-width`, `data-height` are exactly the brief's. The length is to the frame.
- Every text on screen is one of the brief's labels, word for word, and nothing else. Put each label in an element with a stable `id`.
- What appears when follows the narration: an element named by a word appears at that word's second (the brief lists each word's start). The plan's cues (`#id` at a word) are checked by the server against the render.
- The claims and the drawing spec are facts: draw the parts, sizes, relationships and proportions as the spec says, and only those. A real object is drawn as it is built (a wall shows its bond; an opening has a lintel); when unsure, draw less, never something false.
- Silent: no audio, no music.

## Contract (HyperFrames)

1. Every timed element has `class="clip"`, `data-start` and `data-duration` in seconds and shows over `[start, start + duration)`.
2. Each composition builds one paused timeline and registers it after its tweens: `window.__timelines["<data-composition-id>"] = tl`. The host, the scene root and the timeline key share one id.
3. No `Date`, `Math.random`, timers, network fetches or `repeat: -1`: everything visible is a function of timeline time.
4. Never tween `display` or `visibility` on a `.clip`; animate a child. No CSS `transform` on an element GSAP transforms. Use `fromTo`, not `from`.
5. A scene file puts its styles, markup and scripts inside `<template>` and styles its root as `#root` (`inset: 0`).
6. Asset paths are `assets/...` with no leading `/`.
7. Content inside the 90 % action-safe box, text inside the 80 % title-safe box; text at least 2.6 % of the frame height.

Details: `references/format.md` (the project shape, attributes, timing) and `references/motion.md` (eases, entrances, holds, what looks generated). Read them from the plugin's `skills/motion/references/` folder.

## Motion craft, for these shots

How things move and appear is the film's, not this skill's: follow the brief's "Motion style" part for the pace, the arrivals, the labels, the camera and the changes between states. Where the brief's own lines for this shot ask for something the style does not, the brief's lines win for that shot. A line the viewer reads holds at least 0.5 s plus 0.3 s a word.

## The loop

1. Read `brief.md` and `rules.md`, look at `refs/`, read the two references. With no pictures in `refs/`, first build the key frame as a still (everything in place, nothing moving), upload and snapshot it, and stop: answer "key frame ready" with its sha256, so it is checked before you animate.
2. Write the project. Then `vw motion upload --shot <shot>` (it zips `project/` and checks the rules; a refusal names each rule broken: fix and upload again).
3. `vw motion check --shot <shot>`: HyperFrames' own check on the server (lint, layout, contrast, timing). Fix every error; weigh every warning.
4. `vw motion snapshot --shot <shot> --at <t1,t2,…>`: PNGs of the moments that matter (each build step, each label landing, the end) saved to `snapshots/`. Look at every one as a stranger would: does it read as what it is, is every label whole and spelled as the brief says, does anything collide or leave the frame?
5. Fix, upload, check, snapshot again until clean. Then write `work/motion/<shot>/REVIEW.md`: what you built, what you checked, the weakest point, the warnings you kept and why, and the sha256 of the last upload.

You never render the delivery and never edit the plan: the main assistant names your upload in the plan and renders it.
