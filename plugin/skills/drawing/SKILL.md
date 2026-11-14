---
name: drawing
description: How VideoWizard draws a thing before any picture of it is paid for: one description of the thing as data (facts with sources, solid pieces in real units, views), which the server draws and the operator approves. Read it before any `vw drawing` command, and when a thing's construction, pattern or mechanism must be right in a picture.
---

# A thing drawn before its picture

A picture AI guesses what it does not know. A thing whose construction, pattern or mechanism must be right is therefore **drawn first**, from real measurements, and the drawings go to the picture AI as reference pictures. You write one description of the thing as data. The server draws every view from it, so the views cannot disagree. The operator approves the drawings before any paid picture uses them.

You write data. You never draw by hand, never write SVG, and never call a picture model yourself.

## The one rule

**One table of real measurements makes one model, and every view is that model seen from one place.** A number is written once. Things that must be equal are built from the same number.

## When a thing gets a drawing set, and at which level

| Level | When | Views |
|---|---|---|
| `engineered` | its construction, pattern or mechanism must be exact, and a picture AI is unlikely to know it (a bonded wall, a joint, a machine, a loaded vehicle, a product's parts) | 4 to 6: the faces that show the pattern, from above, a cut or a pulled-apart view for what is hidden, one repeating unit enlarged, an angled view |
| `composition` | placement, relative size and one or two facts must not drift (a site, a room, a product among other things) | 3 or more: from above, an angled or camera view with real shapes, a side-by-side or detail view for each fact that must hold |
| `form` | a loose or living thing: a bundle, cloth, a plant | 2 or more: its overall shape with sizes, how it is held or used |
| none | an ordinary thing a picture AI draws correctly from words; a person (a person never gets a drawing set) | |

Never lower the level to save time. If you cannot reach the level, say so and stop: "not yet available: <what is missing>".

## Before you write

1. **The facts.** Every size, count and state the picture must show, each with its source (the plan, a measure on a footage frame, a standard) or marked `"assumed": true`. An assumed size is shown to the operator as assumed.
2. **Footage beats the plan's numbers.** When the film's footage shows the thing, take its proportions from the frame. If the plan's sizes cannot build what the frame shows, draw from the frame and tell the operator in one line.
3. **Only what a camera can see.** Model the faces and patterns that can be photographed; say in a fact what you left out (the inside of a wall, the mesh of a guard).

## The description

`work/drawing/<element>/set.json`:

```json
{
  "unit": "mm",
  "level": "engineered",
  "name": "Dovetail corner",
  "facts": [
    {"what": "board thickness", "value": 18, "unit": "mm", "source": "the joiner's drawing"},
    {"what": "slope of a tail", "value": "1 in 7", "assumed": true},
    {"what": "the joint", "value": "closed tight, no gap", "source": "the shot's plan"}
  ],
  "materials": {
    "maple":  {"colour": [230, 201, 154], "is": "pale maple, the pin board"},
    "walnut": {"colour": [139, 90, 60],   "is": "dark walnut, the tail board"}
  },
  "pieces": [
    {"shape": "box", "min": [18, 0, 0], "max": [150, 18, 120], "material": "maple"},
    {"shape": "prism", "axis": "X", "from": 0, "to": 18, "outline": [[0, 6], [18, 8.57], [18, 35.43], [0, 38]], "material": "walnut"},
    {"shape": "cylinder", "axis": "Z", "centre": [40, 40], "radius": 5, "from": 0, "to": 60, "material": "maple"},
    {"shape": "box", "min": [0, 0, 0], "max": [230, 75, 110], "material": "maple",
     "repeat": [{"step": [240, 0, 0], "count": 8}, {"step": [0, 0, 240], "count": 5}]}
  ],
  "views": [
    {"id": "a", "kind": "square on", "name": "The tail board, square on", "toward": [-1, 0, 0],
     "shows": "the tails and the ends of the pins between them", "for": "the pattern on this face"},
    {"id": "b", "kind": "square on", "name": "The pin board, square on", "toward": [0, -1, 0],
     "shows": "the pins with straight sides and the ends of the tails", "for": "the pattern on this face"},
    {"id": "c", "kind": "from above", "name": "From above", "toward": [0, 0, 1],
     "shows": "the two boards meeting at the corner", "for": "how the boards stand to each other"},
    {"id": "d", "kind": "three-quarter", "name": "From outside the corner", "toward": [-1, -1, 0.9],
     "shows": "both boards and how they lock", "for": "the overall form"}
  ],
  "labels": [{"view": "a", "at": [0, 9, 22], "text": "tail: 32 at the end"}],
  "dims": [{"view": "a", "from": [0, 0, 0], "to": [0, 0, 120], "text": "120"}]
}
```

| Part | Rule |
|---|---|
| `unit` | `mm` for a thing, `m` for a place. Z is up. |
| `facts` | each has `what`, and a `source` or `"assumed": true`; the server refuses a fact with neither. Counts, lengths and states (closed, dry, full, at rest) are facts. These lines go into the picture's request and into its check. |
| `materials` | one colour for one material, with `is`: what it is, in plain words. Purple is kept for a person's back; the server refuses a material close to it. |
| `pieces` | `box` (`min`, `max`), `prism` (`axis`, `from`, `to`, and an `outline` of points in the two other axes), `cylinder` (`axis`, `centre` in the two other axes, `radius`, `from`, `to`; `radius_to` for a taper). A piece may carry `colour`, a marking colour for the operator's sheet only. |
| `repeat` | on a piece: up to three entries, each `{"step": [dx, dy, dz], "count": n}`. The piece is copied n times along the step; a second entry repeats that whole row, a third those rows. The example's last piece is 8 bricks in a row, and that row on 5 courses. This is how anything built of equal pieces is written: you cannot run a script, and a size is still written once. At most 4,000 pieces with the repeats written out. |
| `views` | each has `id`, `kind`, `name`, `shows` (what it shows) and `for` (what it is for), one line each. `kind` is one of: `from above`, `square on`, `cut through`, `pulled apart`, `three-quarter`, `one unit enlarged`, `side by side`, `through the camera`. A camera view gives `camera` (`position`, `aim`, `lens`); every other view gives `toward`, the direction from the thing to the eye. At most 6. |
| `labels`, `dims` | for the operator's sheet: a point of the model and short words. The server sets them in one column. |
| `people` | optional, in a composition: `at`, `facing` (the way the chest points), `height`, and `hands` (where each hand is). The server draws the face and chest pale with dark marks, the back purple and the right arm orange. |

The server cannot cut the model open. Where the inside is the point, build the cut face as its own thin pieces standing beside the thing, show it in a view of kind `cut through`, and state what is inside as facts.

## Sending it, and the operator's approval

```
vw drawing set --element E --file work/drawing/E/set.json
```

Free. The server refuses a faulty description in plain words; fix what it names and send again. Then `vw visuals next` shows the operator the labelled sheets, the facts with their sources and the assumed sizes; they answer **Yes** or **Correct it** with their words. Outside the chat: `vw drawing show --element E`, then `vw drawing approve --element E --sha … --quote "<their words>"` or `vw drawing reject … --notes "<what is wrong>" --quote "…"`.

A correction changes one thing in the description, and the set is sent and approved again.

## What happens with an approved set

- The thing's reference set is made with the drawings: the footage frame first when there is one, then two sheets at most (the angled view, then the first flat view), with the words that explain them and the facts. A thing the footage shows then gets a set made from its footage picture and the drawings.
- In an AI video shot, a piece of the scene marked `"drawn_as": "<element>"` is drawn as this thing's own model (the `vw:guide` skill).
- The facts are checked on every picture made with the drawings.

## What you check before sending

- Every fact the picture must show can be pointed to in a view.
- Counts in the model match the facts.
- The angled view is seen from the side a camera will see.
- No size is typed twice.
