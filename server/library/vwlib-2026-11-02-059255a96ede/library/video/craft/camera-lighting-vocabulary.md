# Camera, light and colour words

Precise production words for start images, for the plan's `camera_move` and for the light named in a shot. "Cinematic" is not a direction; "35 mm feel, warm window light from the left of the frame" is. The server writes the take's Camera line from `camera_move`: a steady, locked-off camera unless the shot names one move. Never write a camera move in the motion brief.

## General: every category

### Framing

extreme wide, wide, medium wide, medium, medium close-up, close-up, extreme close-up, macro insert, over-the-shoulder, point of view, profile, silhouette, low angle, high angle, top-down, tilted horizon, locked-off frame.

### Camera moves (for `camera_move`, one per shot)

static (the default), slow push-in, fast push-in, pull-back, tracking, lateral tracking, tilt up, tilt down, orbit, gimbal glide, dolly-in, dolly-out, crane, aerial, rack focus, snap zoom, whip pan, dolly-zoom, dive (the camera plunges down), drone first-person flight.

One move per shot, nothing layered on top. A name alone is not a direction: even a common move needs its subject, where it starts and where it ends.

### Lens feel

- 24 mm: wide, immersive, exaggerated nearness.
- 35 mm: natural, observational.
- 50 mm: intimate, human view.
- 85 mm: portrait, compressed background.
- 100 mm macro: texture, detail.
- Also: shallow depth of field, deep focus, compressed long-lens background, distorted wide-angle nearness.

### Light sources

overcast daylight, low sun, window daylight, sunset through blinds, moonlight through a window, fluorescent office light, classroom ceiling panels, studio softbox, practical lamp, overhead workshop lamp, monitor or phone glow, refrigerator light, neon sign spill, streetlamp, sodium street light, car headlights, candlelight, campfire flicker, stage spotlight, emergency red light.

### Light direction

top light, side light, backlight, underlight, soft frontal light, rim light, bounce fill, window key light, motivated practical (the source is visible in the frame).

### Light quality

hard shadow, soft diffused, low-key, high contrast, silhouette, specular highlights, volumetric haze, steam catching backlight, wet reflections, desaturated, clean commercial lighting, gritty naturalistic, blown-out highlights, crushed blacks. For a still that must look like a real photograph, `00-method/de-slop.md` wins: low contrast, no crushed blacks.

### Colour

Name the palette in concrete colours, never "cinematic colours": "cold blue-grey shadows, desaturated skin, greenish spill from the open fridge, black empty space". Describe a look by its colours and light, never by a director's or a film's name. A colour the brief bans stays banned in every picture and take of the film.

Common palettes, by description:
- **Cold:** blue-grey shadows, desaturated skin, black empty space.
- **Natural:** warm amber interiors, cool blue exteriors, clean contrast.
- **Saturated warm:** deep reds and greens, hazy practical lights.
- **Single neon:** black with one dominant neon hue (magenta or teal), hard edges.
- **Creamy:** warm creams, soft pastels, clean whites, no harsh blacks.
- **Mixed city:** several light sources at different colour temperatures, neon spill.

### Blocking

Describe a body's movement by: who moves, where they end, what they touch, what they look at, and what their body shows (a posture, never a named feeling). The start image already shows where they begin; the plan may already give the gaze and heading.

"Shoulders collapsed, he crosses to the refrigerator, opens it slowly, leans into the cold light, and stops when he sees the empty shelves" beats "a sad man goes to the fridge": the model can play it moment by moment.

### Rare terms

Common moves work by name. For a rarer term, keep the term and translate it into what visibly changes, or the model guesses: term, subject, the visible change, foreground and background, direction or speed. "Rack focus: the focus shifts from the leaves in the foreground to the person behind them; the leaves soften while the face sharpens." For a camera term this translation belongs in the plan's `camera_move`.

## For advertisement-product

- Creamy or clean commercial light by default; the product's own colours are never shifted by the grade.

## For documentary-explainer and training-education

- The real place's own light (daylight, office, workshop), named as its source and direction; a natural palette unless the brief sets another.

## For narrative-story

- Low-key light, a single neon hue or a cold palette may carry the mood of a scene; keep one palette per scene.

## Not available yet

VideoWizard makes silent, steady, single-shot takes and cuts in the edit. Filed for categories that may want them later:
- **Handheld micro-shake and phone-camera wobble** (social-ugc).
- **Time effects:** bullet time, speed ramps (advertisement-product, social-ugc).
- **Sound words** (advertisement-product, narrative-story, social-ugc): room ambience (room tone, distant traffic, rain on a roof, wind in leaves, fluorescent buzz); body and action (breath, footsteps, fabric rustle, a key in a lock, a zip); events (sudden silence, a low bass hit, glass breaking, distant thunder, a door slam).
- **Transitions in one generation** (advertisement-product, social-ugc, narrative-story): plain cut, fade, dissolve, white or black flash, wipe, an object covering the lens, match cut, a cut hidden in a whip pan, a subject leaving one frame and landing in the next, a zoom through a window or keyhole. One transition type per cut, named with the moment it fires.
