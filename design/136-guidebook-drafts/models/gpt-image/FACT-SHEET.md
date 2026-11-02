# GPT Image 2.5: how it reads words

How the picture model reads a prompt, for whoever writes one. The server picks the model, the size, the quality, the background and the pictures sent, and their order; never write them in a prompt. The facts below come from OpenAI's own pages, read on 19 Oct 2026; the few lines from other users' notes say so.

## General: every category

### What reaches the model

- The prompt reaches the model exactly as written; nothing rewrites it.
- Pictures sent with a call are named in the prompt by number, "Image 1", "Image 2", in the order the server sends them.
- A blocked prompt is rewritten, never sent again unchanged. An edit that shows a real person's likeness is usually refused outright (other users' notes); VideoWizard never sends a person's picture anyway.

### Prompt shape

For a complex picture, OpenAI advises labelled parts: scene, subject, details and constraints. Write:

- **Scene:** the place, the time, the ground.
- **Subject:** the one thing the picture is about.
- **Details:** materials, the light's direction and softness, the camera feel, the palette, the layout (a landmark and a distance, never "centre").
- **References:** Image N = its one role.
- **Constraints:** what must hold and what must not appear, short and specific.

Words to be read in the picture go only in the answer's `exact_text`. The constraints part is where drift is stopped; a prompt without it lets the model fill gaps its own way (other users' notes, in line with OpenAI's advice to keep the change apart from the constraints).

### Words that hurt

- Praise words give the model nothing to draw: "stunning", "epic", "masterpiece", "best quality", "8K", "ultra-detailed", "flawless". OpenAI's own advice is milder but the same: name scale, atmosphere and colour instead of mood words. Replace each with a fact ("overcast daylight", "brushed aluminium", "chipped paint"); the table is in `agency/deterministic-checks.md`.
- Style labels as a shortcut ("premium", "cinematic look", "like a famous brand's advert"): write the visible facts instead.
- Stylised words when realism is wanted. OpenAI's own example exclusion: avoid cinematic lighting, dramatic colour grading or stylised composition.

### Words that help

- Camera terms work as cues for the look, not as physics: "50mm feel", "eye level", "shallow depth of field".
- For a real photograph, say so ("photorealistic", "a real photograph"), then describe framing and texture.
- For people: body framing, relative scale, gaze and what the hands touch ("full body visible, feet included", "looking down at the open book").
- Concrete nouns beat adjectives: roughly 5 to 12 named objects and surfaces, 2 to 4 facts about light and material (other users' notes).
- A place and a date pull in period detail; check clothing and staging afterwards.

### Words in the picture

- Through `exact_text` only, each string with its place and size; keep each string short and say how many times it appears.
- Spell an unusual word out letter by letter only if it came back wrong.
- Close with a short constraint: no other text, no watermarks, no unrelated logos.
- Known failure: misspelled or soft text, worst in small text and several fonts. Read every character afterwards; in a translation, look for words left in the original language.

### Edits: keep the rest unchanged

- Say "change only X", then name what is kept: identity, geometry, layout, lighting, labels. Add the exclusions: no new text, logos or watermarks.
- For a tight local edit, also name what else holds: contrast, camera angle, the objects around it.
- For a person: do not change the face, features, skin tone, body shape, pose or identity.
- A garment change: only the garment changes, fitted to the existing pose, light and shadow matched; background, angle and framing unchanged.
- Repeated edits drift. Restate the keep-list every time, inspect every result, and go back to the last approved picture, never the drifted one.
- Prompting cannot guarantee untouched pixels.

### Several pictures in one call

- Number each picture and give it one purpose (subject, style, background); say how they combine and what goes where.
- A style reference gives one role ("palette", "texture" or "medium"); describe the new subject separately.

### Series and characters

- Approve one reference sheet first; pass it into every later call and repeat its defining traits each time; add "do not redesign the character".
- Known failure: recurring characters and objects may not stay the same between pictures. The approved sheet and the repeated traits are the fix.
- The same prompt gives different results. Never judge a prompt on one run.

## For advertisement-product

- A product: keep its geometry and the label's legibility exactly, and do not restyle it.

## For training-education and advertisement-product

- A software screen: describe it as if it already exists. Concept-art or sketch words produce a drawing of a screen, not a screen.

## For documentary-explainer and training-education

- A diagram: give the real labels (through `exact_text`) and how they relate; check the facts, not the looks.
- Historical clothing or staging: name the place and the date, then check the result against them.

## For social-ugc

- A candid look: state the capture as a fact ("a phone photo at eye level"), name where the imperfections sit, and rule out glow and polish in the constraints.

## Not available yet

- **Transparent cut-outs (advertisement-product):** the model can return a subject on a truly transparent ground when asked in words and in its settings; check the edges at hair, glass and shadow, since a drawn checkerboard is not transparency. VideoWizard puts every sheet on plain ground today.
