# Diagram in states: a graphic that builds

One labelled diagram or illustrated explainer that changes on screen in two to four steps. Each step is a still (a "state"); together they play as a build, each state holding, then giving way to the next. Read with `RULEBOOK.md`. The server sets the model, the size and the quality; never write them in a prompt.

## General: every category

### What this covers

Nothing moves inside a state. Arrows that travel and parts that slide are out of scope; plan a build (parts appear) or a reveal (parts are highlighted) instead. A graphic that never changes is one still (`playbooks/web-app.md`, process explainer). A number, size, count or chart is not drawn by the picture AI: it takes the drawn route.

### Decisions already taken

| Decision | Value | Why |
| --- | --- | --- |
| Count | Two to four states. | One state is a still; five or more is a slideshow. |
| Hold | At least three seconds per state, long enough to read every new label twice. | A label not read is lost. |
| Plan the last state first | Write the full final diagram in words before state 1: every part, label, colour and place. Earlier states are that picture with parts missing or not yet highlighted. | Room for later parts must be kept from the start. |
| Each later state is an edit of the last approved one | One change per state, the full keep-list, a retry from the last approved state when one drifts (`RULEBOOK.md` rule 8). | Edits keep the drawing. |
| Words | Short and large, only through the answer's `exact_text`, each with its place and size; never quoted in the prompt. | The server places and checks them. |

### Before writing

1. The narration under the shot, and what the viewer must understand by the last state.
2. The end picture in words: background, every part, each label, colour meanings, and where each part sits by a landmark of the drawing and a distance ("below the tank, one tank-height down"), never "centre" or "left third".
3. The state list: what each state adds or highlights, and its hold in seconds. The holds add up to the shot's length.
4. The film's graphic style, from the approved style picture: line weight, label feel, background, the colours by name.

### The prompts

State 1:

```text
A diagram, state 1 of {n}.
Canvas: {background}, {margins}. Keep plain empty space at {places, by landmark} for parts that appear later.
Style: {line weight}; {label feel}; {flat | cutaway | isometric}; colours {by name}.
Shown now: {the parts in state 1, each with its place}.
Labels: only the exact-text entries, at their places.
Constraints: no parts from later states; no arrows unless listed.
Render only explicitly requested image text. Do not add unrelated logos, signatures or captions.
```

State 2 and later (Image 1 is the previous approved state):

```text
Image 1 is the approved state {k-1}.
Change only: add {the new part} at {place} | highlight {part} with {a coloured outline | a brighter fill}.
Keep exactly as in Image 1: canvas, background, every existing part, its place and size, every existing label (named without quotes), colours, line weight, label feel, margins.
Constraints: no other new element or text; do not redraw, restyle or move anything.
Render only explicitly requested image text. Do not add unrelated logos, signatures or captions.
```

### Checklist lines

- Every label reads letter for letter as its `exact_text` entry; no extra text. must.
- State k shows everything in state k-1 at the same place, size and colour. must.
- Only the planned change differs between consecutive states. must.
- The kept empty space is still plain until its state. must.
- The final state matches the end picture. must.
- Each new label can be read in its hold time at phone size. should.

### What goes wrong, and the fix

| Habit | Fix |
| --- | --- |
| A later edit restyles the whole drawing | A shorter "change only" line; the full keep-list; retry from the last approved state |
| No room for the next part | Plan the end picture first; keep named empty space in state 1 |
| Labels re-spelt or moved on edit | Name every existing label in the keep-list, without quotes |
| Colours shift between states | The same colour names in the style line of every prompt |
| Too many words for the hold | One idea per state; three to five words a label |

## For training-education and documentary-explainer

- A process or a cutaway: each state adds the next step in the order the narration says it.

## For advertisement-product

- A feature reveal: the product drawing stays fixed; each state highlights one part the client named. No claim the client did not give.

## Not available yet

- **Parts that move inside a state (travelling arrows, sliding parts):** VideoWizard plays states as holds.
- **Making earlier states by removal edits from the final state:** untested; record it in the feedback log if tried and it holds the drawing better.
