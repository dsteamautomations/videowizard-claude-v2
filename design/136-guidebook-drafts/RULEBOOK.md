# Rulebook: read on every job

VideoWizard serves every category of video: documentaries and explainers, advertisements and product films, training, social clips, stories. A step reads the general rules here plus the part for its own film's category. The rules are written for today's picture and video models.

These rules apply to every picture and every take, whatever the playbook. Model habits are in the model sheets; job rules are in the playbooks. The server sets the model, the size, the quality, the pictures sent and the clip length; never write them in a prompt.

## General: every category

### 1. Before writing anything

1. Read the whole job form. If a required field is missing or contradictory, answer `needs_input`. Do not guess.
2. Look at every picture sent. Write two lines on each: what is in it, any text read letter by letter, colours, anything odd.

### 2. Every instruction can be checked by looking at the result

"Premium" cannot be checked; "brushed metal, one object, wide plain margins" can. Rewrite every vague word from the brief into visible facts before it reaches the prompt, and list the rewrites in the answer form. The replacement table is `agency/deterministic-checks.md`.

### 3. Layout before subject

State the layout first: where the subject sits (by a landmark and a distance the picture shows, never "centre", "middle" or "left third"), and what margin or empty area is kept. Then the subject. A model given the subject first spends its detail on the object and improvises the layout. Describe an empty area as a surface ("a plain off-white wall, no objects"), never as nothing.

### 4. Words in the picture

1. Words to be read in the picture go only in the answer's `exact_text`, each with its place and size, letter for letter as approved. Never put them in quotes in the prompt; a keep-list names existing labels without quotes.
2. End every prompt with the standing line: "Render only explicitly requested image text. Do not add unrelated logos, signatures or captions." Even with no text: that is when stray captions and fake watermarks appear.
3. Keep rendered words short: one to five words render best. Long copy is typeset later, not rendered.
4. Words in a script not yet tested on the model are typeset later, not rendered.
5. After generation, read every character in the whole frame, not only the headline.

### 5. Never drawn

- The client's logo: the editor places it. Leave room only when the plan asks.
- A number, size, count or chart: the drawn route makes it. An AI graphic carries words only.
- Legal text and long copy: typeset later.

### 6. Never invent

No price, date, phone number, address, award, badge, rating, certification, sponsor, feature or claim that is not in the job form. Background text too: nothing readable that looks like a real brand, a number or an address.

### 7. Reference pictures

1. Give each picture sent its job in a sentence: "Image 1 is the approved sheet of the mason". The server writes the picture tags.
2. Say what to take from each and what not to: "take only the colours and light from Image 2; do not copy any object from it".
3. Do not restate what a reference already shows. Describe only what must change or must hold.
4. Build the keep-list from the picture itself, as nouns a checker can tick: "lamp silhouette; brass colour; the label's wording".
5. A person is described in words from the footage pictures or the brief; a picture of a real person is never sent (`video/consistent-character-frames.md`).

### 8. Edits

1. One change per edit. Name the region, the change and the keep-list; repeat the keep-list every time. A second change is a second edit of the result.
2. If a result drifts, retry from the last approved picture, not the drifted one. Never stack repairs.
3. Prompting cannot promise untouched pixels, and a mask is guidance, not a boundary: check the area outside the change.

### 9. Words that help and words that hurt

Praise and quality words add nothing: rewrite or delete them with the vague-word table (`agency/deterministic-checks.md`). Concrete nouns and physical facts help: five to twelve named objects and surfaces for a scene, two to four light and material facts. Materials, light and palette are three separate controls; name each. Camera words as a look: "a 50 mm feel", "eye level", "low three-quarter angle". A named studio, director, artist or brand becomes the visible technique it stands for; real brands, interfaces and people never go into a prompt.

### 10. Negatives

Describe what should be there first. Then a short, targeted list of what the model tends to add wrongly for this job ("no fake logos, no unreadable microtext, no second subject"). Long negative lists take over the prompt.

### 11. A still that must pass as a real photograph

State the capture as a fact ("a phone photo", "a 35 mm film scan"), never as a style. Name three imperfections and where they sit ("pores across the nose", "two flyaways above the crown", "a scuffed skirting board behind"). Ask for low micro-contrast and no added sharpening; exclude HDR, bloom, glossy skin and perfectly even backgrounds. Describe once how a person differs from an idealised face.

### 12. People and symbols

1. No public figures, no lookalikes.
2. Never change a person's body shape, skin colour, apparent age or gender, or remove a permanent feature.
3. Sacred and national symbols: none on products, food or clothing; no religious text; a national flag follows that country's flag rules.
4. When the client's industry carries compliance lines, open `agency/compliance-checklist.md`.

### 13. After generation

Check the most expensive mistake first. People: eye spacing, nose, hairline, skin tone, hands. Objects: silhouette, joints, label spelling, proportions. Words: every character, line count, no leftover text. Graphics: arrow direction, label pairing. Places: window corners, door openings, floor seams, furniture scale. Then the keep-list. Then the rest of the frame for colour shift and crop creep. A failing must-line in the answer's checklist means fix or reject.

### 14. Video

1. The start image is approved before anything moves; it carries identity, composition and text.
2. The take's prompt is a motion brief: only what the subjects and the surroundings do. The server writes the picture tags, the camera line, the single-scene line and the length (`playbooks/video-clip.md`).
3. One camera move at most, the one the shot names; one main action. A longer passage is several shots.
4. Show, do not tell: bodies render, feelings do not. "His jaw locks" works; "he is scared" does not.
5. After the take, check that labels, a person's traits and the palette held through the motion. A broken take is made again from the approved image, never patched.

### 15. The lint before `ready`

The ten rules are in `forms/answer-form.videowizard.md`. Fail once, repair once. Fail twice, answer `needs_input` naming the rule.

## For advertisement-product

- The product's silhouette, label, colour and proportions never change; its label is read letter by letter after every picture.
- No claim about what the product does, no ingredient, price or certification the client did not give.

## Not available yet

VideoWizard does not do these today; they are filed for categories that may want them later.
- **Sound and dialogue (advertisement-product, social-ugc, narrative-story):** sound described or switched off; dialogue short, attributed to a visible action.
- **Several actions in one take (narrative-story):** timed windows of three seconds or more, each with one action and a visible end state.
- **The real logo composited onto a reserved area (advertisement-product).**
- **Cutouts with true transparency (advertisement-product):** only on a model that returns a real alpha channel; a drawn checkerboard is not transparency.
