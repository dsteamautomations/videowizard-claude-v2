# Gap fill: AI shots that sit between real footage

A film cut from real footage has gaps that AI stills and takes fill. The viewer sees real shot, AI shot, real shot, so the AI shot must look as if it came from the same camera on the same day, unless the film deliberately changes medium (a diagram, for example). Read with `playbooks/video-frame.md` and `playbooks/video-clip.md`.

## General: every category

### Read the neighbours first

Before writing the still's prompt, look at the last frame of the real shot before the gap and the first frame of the real shot after it. Write one line on each:

| Property | What to note | How it goes into the prompt |
| --- | --- | --- |
| Grade | warm or cool, contrast, saturation, black level | "warm daylight grade, medium contrast, slightly lifted blacks" |
| Light | time of day, sun or overcast, where the main light comes from | "overcast late morning, soft light from the doorway side" |
| Grain and sharpness | phone-clean, compressed, grainy, soft | "fine digital noise, slightly soft, phone camera" |
| Lens | wide or tight, depth of field | "wide phone lens, deep focus" |
| Motion blur | present on movement or not | "natural motion blur on fast hand movement" (motion brief) |
| Place and people | site, materials, clothing | from the film's world rules and approved sheets |

Write these as plain facts. "Cinematic" and "high quality" make the AI shot look less like the real one. The camera stays steady whatever the footage does: locked off, or the one move the shot names.

### The boundary-frame method

When the gap continues the same action or place as its neighbours, grab the last frame of the real shot before the gap. Use it as the reference for the gap's start image (a place or an object), or as the start image itself, only when no person is in it; a person is described in words.

### Cautions

- **Edges.** The footage and the video model may differ in size; a frame used as the start image is resized. Keep nothing important at an edge that may be cropped.
- **Exact continuity is not guaranteed.** The take's first frame will be close to the boundary frame, not identical. The editor cuts on it as a normal cut. Never promise an invisible join.
- **Not every gap is a continuation.** When the narration moves to a new idea, a clean cut to a different picture is better than forced continuity. Use the method only where the action or place carries over.

### Checklist lines

- Grade, light and grain match the neighbouring real shots, compared side by side. must.
- Place, materials and clothing agree with the neighbours and the world rules. must.
- With the boundary-frame method, the take's first frame is recognisably the boundary frame. must.
- No picture of a real person sent to the picture AI. must.
- The camera is steady: locked off, or the one move the shot names. must.

## For advertisement-product

- The product in the gap matches the product in the footage: same pack, same label side facing, same wear or freshness.

## For social-ugc

- The neighbours are often a phone's own look: name the phone capture as a fact (rule 11 of `RULEBOOK.md`), not as a style.

## Not available yet

- **A handheld or moving camera to match handheld footage (social-ugc, narrative-story):** VideoWizard keeps every take steady.
- **A short dissolve across the join (narrative-story):** VideoWizard makes no transitions.
