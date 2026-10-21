# Video frames playbook

Version 0.1, written 2026-10-19. Status: draft, untested on a real job. One file for every still image that a video needs: continuity sheets, storyboards, keyframes, first and last frames, cover frames. The clip itself is the video-clip playbook. Read this with `RULEBOOK.md`, the model sheet, the video model's sheet section A5 for accepted sizes, and the job form. Built-from list at the end.

## 1. What this playbook covers

Tasks on the job form: `continuity-kit`, `storyboard`, `first-last-frame`, `keyframe`, `keyframe-set`, `cover-frame`. Every frame is a brief: it carries a shot number, the camera move it must leave room for, and the continuity anchors it must hold. It is approved like any other image before anything moves.

Added 2026-10-21, draft and untested: a diagram that builds in two to four still states is `video/diagram-in-states.md`; frames for AI shots that sit between real footage follow `video/gap-fill.md`.

## 2. Decisions already taken

| Decision | Value | Why |
| --- | --- | --- |
| Order of work | Shot list, then continuity kit, then storyboard, then keyframes, then first and last frames, then handoff. The client approves the shot order on the storyboard, where changes are cheap. | DIRECTION section 5h. |
| Aspect | Frames are generated at the video model's aspect from the start: 16:9 or 9:16 for Omni; Seedance's six ratios. A frame is never cropped after animation. | Cropping after animation is a silent failure. |
| Model | GPT Image 2.5 Sunburst for keyframes and first frames that carry a client product, a face from a consent-covered sheet, or text. Nano Banana 2.1 for storyboard grids, continuity sheets and cover frames, and for character work with up to four characters. Nano Banana Pro only if a sheet with more than four characters is needed. | Product and text precision; cheap consistent grids; Google's own keyframe guidance. |
| Everything critical is locked in the still | Identity, composition, aspect, visible text, product state. "The video model amplifies any ambiguity in the still." | Nano Banana keyframe guidance; house rule. |
| The continuity kit is approved first | A character sheet and a product sheet, each with five traits that must never change, plus palette, lens feel and light direction. Nothing is drawn for a shot until the kit is approved. | DIRECTION 5h step 2. |
| Headroom for the move | A push-in needs margin around the subject; a pan needs the subject off-centre in the direction of travel; a pull-back starts tight; an orbit needs space on all sides. Stated in the prompt from the shot list's camera move. | A frame built for a static shot fights the move. |
| One shot per call | Keyframes are generated one at a time with the kit attached. Grids are for storyboards only. | Consistency and inspection per shot. |

## 3. Before writing

1. The shot list: for each shot, number, intended seconds, action, camera move, voice-over or caption reference, transition to the next shot. Without it, `needs_input`. A shot list template is in the job form notes; the storyboard method's per-shot block is the pattern.
2. The video placement and model, so the aspect and accepted size are known.
3. For characters: the approved sheet tagged `person` with its consent id, or the brief for a fictional character. For products: the client photo tagged `product`.
4. The visual theme in five lines: palette with hex values, lighting style, lens character, film look, motion language. Written once and repeated verbatim in every frame prompt.
5. Which shots will be animated by image-to-video and which need a first and last frame pair.

## 4. Task notes

**continuity-kit.** A character sheet: front, three-quarter and side at equal scale on one baseline, plain background, the five fixed traits named in words: hair colour and structure, face shape, skin tone and markers, outfit items with colour and material, one accessory. Recipe P038 is the pattern; the fourteen-variable extraction in `video/consistent-character-frames.md` is the checklist for describing a real person from a reference. A product sheet: three angles, the label readable, the five fixed traits: silhouette, label text, colour, proportions, closure. The kit is tagged `approved` once signed and travels into every later call. Hairstyle structure, accessories and crop boundaries are hard rules, not hints.

**storyboard.** One grid image at the video's aspect, one panel per shot. State the grid, the reading order, the borders, and that no two panels may be near-identical. Each panel gets a function tag, a beat, a framing and the implied camera move, written under it in the shot list, not inside the image. Grid by scene length: up to 9 seconds 3x3, 9 to 12 seconds 3x4, over 12 seconds 4x4; panels edge to edge. Panel numbers and durations as small dark tabs inside each panel if the sheet must read on its own, which needs `high` quality on GPT Image. Recipes P084 and P085 are the patterns for a character-led board. The client approves shot order here.

**keyframe.** One shot, standalone, at the video aspect, with the kit as references and the theme block repeated. The keyframe card from `video/craft/animatic-keyframes.md` is filled before generating: panel id, function tag, beat, framing and lens, the one anchor the eye lands on, foreground, midground and background jobs, implied camera, light and palette, emotion through an object, motion as a still, sound under the frame. A frame that cannot name its beat, function, emotion and implied motion is not ready. Motion is prompted as its physical residue: smear, streak, held stillness, a frozen splash.

**keyframe-set.** The same product or character across several locations with the same palette and light. One call per frame, the approved first frame sent as Image 1 for the second, and so on, with the theme block verbatim each time. Seeds P055, P058.

**first-last-frame.** Two frames for one image-to-video shot. The first holds the composition at the start of the move, the last at its end. Same aspect, same light, same character traits; only what the move changes differs. For a loop, the same image serves both. State in the handoff what the transition path is: "the camera whip-pans right from the drummer to reveal the dancer".

**cover-frame.** From an approved keyframe, reframed to the platform's cover or thumbnail size, with the thumbnail rules from the social playbook: one idea, three to five words, reads at 160 px.

## 5. Writing the prompt

```text
{brand preamble}
Asset: keyframe, shot {n} of {total}, for {video model} at {aspect}. Target aspect ratio: {16:9 | 9:16}. Mode: {edit with identity | multi-reference}.
References: Image 1 is the approved character sheet: keep {five traits}. Image 2 is the approved product: keep silhouette, label text "{text}", colour, proportions. {Image 3 is the previous approved frame: keep its palette, light direction and lens feel.}
Theme, verbatim: palette {hex list}; light {style}; lens {character}; film look {look}; motion language {handheld | locked off | dolly}.
Shot: {framing}, {angle}. The eye lands on {one anchor}. Foreground {job}; midground {the act}; background {stakes or context}.
Beat: {one sentence of what changes}. Emotion through {object state}, not a named feeling.
Frozen motion: {smear | streak | held stillness | frozen splash} on {what}.
Headroom: {margin for a push-in | subject at left third for a pan right | tight for a pull-back}.
Exact image text: {none | "sign text"}. No other text.
Constraints: no captions, frame numbers, arrows or speed lines; no second character; no change to the kit's traits; no new props.
Render only explicitly requested image text. Do not add unrelated logos, signatures or captions.
```

For a storyboard grid, replace the Shot and Beat lines with the grid statement and one short line per panel, three to eight words each, reading order stated, and "no two panels near-identical: change shot size, angle, beat or depth relationship".

## 6. Handoff to the video model

What travels with every frame, in the answer form's notes: shot number and intended seconds; the camera move; the continuity anchors to hold; the audio reference; the transition to the next shot; whether this is a first frame, a last frame or a reference. The clip prompt is derived from the shot list, not re-invented, and does not re-describe what the frame already shows. The video-clip playbook takes over from here.

## 7. Checklist lines for video frames

- Aspect equals the video model's, and the size is at or above its accepted input. must.
- Character traits match the approved sheet, all five, side by side. must.
- Product silhouette, label text and colour match the approved product sheet. must.
- Palette, light direction and lens feel match the theme block and the previous approved frame. must.
- Headroom suits the camera move named in the shot list. must.
- No captions, numbers, arrows or speed lines inside a keyframe. must.
- Storyboard: panel count and order match the shot list; no two panels near-identical; grid as stated. must.
- First and last frame: same aspect, same light, same traits; only the move's change differs. must.
- The frame names its beat, function, emotion-through-object and implied motion in the card. should.

## 8. What goes wrong on frames, and the fix

| Habit | Fix | Seen in |
| --- | --- | --- |
| Character drifts between frames | Kit as Image 1 every call; five traits repeated in words; "do not redesign the character" | P080; Google and OpenAI guidance |
| Grid repeats one flattering composition | "No two panels near-identical" as a requirement | storyboard-sheet rules |
| Panel order jumbled | State reading order; number tabs inside panels | storyboard-sheet rules |
| Frame fights the camera move | State headroom from the shot list | DIRECTION 5h step 5 |
| Frame generated square then cropped to 9:16 | Generate at the video aspect from the start | Nano Banana keyframe guidance |
| Hairstyle reinterpreted on a real person | "Hairstyle structure intact, no loose hair, no reinterpretation" | consistent-character-frames principle 3 |
| Props cross cell boundaries on a sheet | Equal invisible cells with internal space; one figure per cell | P083 |
| A panel is pretty but carries no beat | Fill the keyframe card first; delete panels that fail it | animatic-keyframes section 1 |

## 9. Evidence

None yet. Core status also needs the motion hold recorded on at least two animated shots: label held, traits held, palette held, text held.

## 10. Built from

`DIRECTION.md` sections 5h and 6 video fields, scenarios A39 to A44; `video/craft/animatic-keyframes.md`; `video/craft/storyboard-sheets.md`; `video/consistent-character-frames.md`; `video/storyboard-method.md`; `00-method/craft.md` section 7; `prompts/07-stories-games.md` P038, P039; `prompts/14-sketch-to-story.md` P083 to P085; `prompts/10-production.md` P060; `models/nano-banana/smixs--visual-skills.md` keyframes section; `video/models/gemini-omni-1-1/FACT-SHEET.md` A5 and B7; `video/models/seedance/FACT-SHEET.md` A3 and B2.
