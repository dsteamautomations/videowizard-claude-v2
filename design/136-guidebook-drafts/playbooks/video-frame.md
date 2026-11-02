# Video frames playbook

Every still picture a video needs: reference sheets, scene stills, the start image of a video shot, and its end image when the shot's final state must be exact. Read with `RULEBOOK.md` and the picture model's sheet. The server sets the model, the size, the quality and the pictures sent; never write them in a prompt.

## General: every category

### Decisions already taken

| Decision | Value | Why |
| --- | --- | --- |
| Everything critical is locked in the still | Identity, composition, visible text and the object's state are settled in the picture. | The video model amplifies any ambiguity in the still. |
| References first | A person, an object or a place appears only after its reference sheet is approved; every later picture of it names its five fixed traits. | One approved look, held in every shot. |
| Headroom for the move | When the shot names a camera move: a push-in needs margin around the subject; a pan leaves space on the side it travels to; a pull-back starts tight. With no move, compose for a locked-off frame. | A frame built for a static shot fights the move. |
| One picture per call | Each picture is made on its own, with its references. | Each one is checked and approved on its own. |

### The still card

Fill it before writing the prompt; an empty field is missing direction.

| Field | Write |
| --- | --- |
| Shot and kind | the shot id; a scene still or the start image of a video shot |
| Beat | what this one picture tells, in one sentence |
| Job | establish, reveal, detail, step, reaction or result |
| Framing | wide, medium, close or insert; camera height; lens feel ("a 50 mm feel") |
| Anchor | the one thing the eye lands on first, and its state |
| Depth | foreground (frames the shot, puts the viewer inside); midground (the subject and the act); background (the place and what is at stake) |
| Light and palette | one source, its direction, the surface it touches; the film's own colours |
| Feeling | shown by a body or an object (a grip, a posture), never named |
| Motion | a scene still may keep a trace of movement on the moving part; a start image is the instant before the action, sharp |
| Room for the move | start image only: what the planned move needs inside the frame |
| Continuity | the approved sheets this picture must match |

Every object in the frame earns its place: it serves the beat, the place or the continuity. A camera low and close makes a subject strong; high and wide makes it small.

### Reference sheets

The views the plan names (`required_views`), labelled, on one baseline, at equal scale, at the film's frame, on a plain background, one figure per view with space around it. The five fixed traits are named in words: for a person, see `video/consistent-character-frames.md`; for an object, its silhouette, colour, material, proportions and any marking.

### The prompt

Image roles first ("Image 1 is the approved sheet of …: keep …"). Then the layout: where the subject stands, by a landmark and a distance the picture shows, and the headroom for any named move. Then the subject, the anchor, the three depth layers, and the beat as an object's state. Words that must be read in the picture go only in the answer's `exact_text`; otherwise none. End with short, targeted constraints: no captions or arrows, no second subject, no change to the sheet's traits.

### The end image (only when the shot's final state must be exact)

An edit of the approved start, in one region, at the same framing and light. Only the change the shot plans differs; the camera does not move between start and end.

### Checklist lines

- The person's or object's five traits match the approved sheet, side by side. must.
- Palette, light direction and lens feel match the film's style and the scene's light. must.
- Headroom suits the camera move the shot names. must.
- No captions, numbers, arrows or speed lines unless `exact_text` names them. must.
- The still card's beat, job, feeling and motion can be read in the picture. should.

### What goes wrong, and the fix

| Habit | Fix |
| --- | --- |
| A person or object drifts between pictures | The approved sheet as Image 1; its five traits in words; "do not redesign" |
| A hairstyle is reinterpreted | Name the hairstyle's structure and say it does not change |
| Figures cross into each other on a sheet | Equal invisible cells with space inside; one figure per cell |
| A picture is pretty but tells nothing | Fill the still card first; a picture that fails it is not made |
| A start image already shows the action half done | The instant before the action; the take carries the movement |

## For advertisement-product

- **The product, every time:** silhouette, label text, colour, proportions and closure are its five traits; the label is readable wherever the shot faces it.
- **One product across several settings:** the approved first picture is Image 1 of the next, with the same palette and light.

## For training-education and documentary-explainer

- The real place and the real step; a working hand names its verb (lays, taps, levels), and the tool is the one the footage shows.

## For narrative-story and social-ugc

- The eye line: where each person looks, and why.

## Not available yet

- Cover and thumbnail frames (social-ugc): one idea, three to five words, readable at thumbnail size. VideoWizard does not make them today.
