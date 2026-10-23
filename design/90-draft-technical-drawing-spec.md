# design/90: draft library guide `video/technical-drawing-spec.md` (design/89 D6)

This is the draft of the guide design/89 D6 asks for. It is not in the library yet. The library in `server/library/` is a fingerprinted snapshot of Revathi's master library, which lives outside this repository. So the guide goes into the master library, and arrives here with the next snapshot, in batch 4 (design/89 I). Until then, the visuals prompt and the plan step carry the rules, and the server enforces them (design/89 C and D, batch 2).

---

# Technical drawing spec: a drawing of a real object, drawn to its facts

Version 0.1, written 2026-10-23 for VideoWizard (design/89 D). Status: **draft, untested.** No job has run on it. Read it with `video/diagram-in-states.md`, `playbooks/video-frame.md` and `RULEBOOK.md`.

## 1. What this covers

A drawing of a real object: a wall section, a machine part, a joint, a circuit, a road profile. Its parts, sizes and proportions are facts, not style. An image model paints proportions by eye, so the facts are written down first, with their sources, and the operator approves them before any picture is made.

A chart, a timeline, a flow or a label needs no spec. Say so in the shot's `production_method`.

## 2. The spec (`drawing_spec` on the shot)

```json
{
  "parts": ["inner leaf", "outer leaf", "cavity", "header course"],
  "relationships": ["the two leaves are the same thickness", "the cavity is inside the wall, between the leaves"],
  "dimensions": [
    {"part": "leaf", "measure": "thickness", "value": 110, "unit": "mm", "source": "client brochure p.4", "status": "confirmed"},
    {"part": "brick", "measure": "length", "value": 230, "unit": "mm", "source": "clip c1 at 4.5 s", "status": "measured"},
    {"part": "cavity", "measure": "width", "value": null, "unit": "mm", "source": "", "status": "unknown"}
  ],
  "label": "illustrative, not to scale"
}
```

- **parts**: every part the drawing shows, by the name its label will carry.
- **relationships**: what must hold whatever the sizes: same, inside, above, parallel, touching, in this order. Each one becomes a `must` line in the picture's check.
- **dimensions**: one row per number. Each row has a value and unit, a source and a status.
- **label**: required when any size is unknown, and it must contain "not to scale".

## 3. Sources, in this order

1. **The client's own material.** The script, the brief, their documents, their supplied drawings. Give the page or the file.
2. **The footage, measured.** Use `vw visuals measure --refs F1 F2 --question "…"` on approved frames that show something of known size in the same frame: a brick, a door, a level, a person. Each number keeps the clip and the time it was read from.
3. **An authoritative web source.** A standard, a manufacturer's sheet or a textbook, used on the operator's yes (the web rule). Keep the URL and the figure as given.
4. **A reference picture the operator approves.** Use this for a shape that numbers cannot hold.

## 4. Status rules

| Status | Meaning | Rule |
|---|---|---|
| `confirmed` | from the client or a standard | a source is required |
| `measured` | from the footage | the clip and time is the source |
| `unknown` | no source found | **no value**: an unknown number is never invented; the drawing shows no figure for it and is labelled "illustrative, not to scale" |

The server refuses a spec that breaks these rules.

## 5. Approval and the check

- The operator approves the spec once, as a table (part, size, status, source), on the visuals page or with `vw visuals spec --shot S --quote "…"`. If the spec changes, it needs a new approval.
- The picture is checked against the spec:
  - every relationship is a must line;
  - every unknown size is a must line that no figure is shown for it;
  - the label is a must line;
  - every known size is a should line that its figure reads as the spec says and that its proportion looks right.
- The style sheet (`_STYLE`) is a parent of the drawing, so every drawing in the film shares its line weight, palette and labels.

## 6. Writing the prompt

- Name the parts in the spec's words. Put each label exactly as it must read.
- State the relationships as visible facts: "both leaves are drawn the same thickness".
- Give a figure only for a confirmed or measured size, written exactly as it must read: "110 mm". Never give a figure for an unknown size.
- When a size is unknown, put the label in the prompt as exact text: "illustrative, not to scale".
- Ask for a flat orthographic section or elevation, in the style sheet's line weight and palette. Never ask for perspective on a drawing that carries sizes.

## 7. Worked examples

**A wall section (construction).** Parts: inner leaf, outer leaf, cavity, header course. The leaf thickness of 110 mm is confirmed from the brochure. The brick length of 230 mm is measured from clip c1 at 4.5 s, against a 1 m level. The cavity width is unknown, so the drawing shows no figure for it and is labelled "illustrative, not to scale". Relationships: the leaves are the same thickness; the headers cross the cavity.

**A bicycle crank (machine part).** Parts: crank arm, spindle hole, pedal thread. The arm length of 170 mm is confirmed from the manufacturer's sheet (URL kept, on the operator's yes). The pedal thread is 9/16 inch, confirmed from the same sheet. The arm's taper is shown by an approved reference picture, not numbers. Relationships: the pedal thread is at the far end from the spindle; the arm is straight in elevation.

**A road profile (civil).** Parts: carriageway, camber, shoulder, drain. The carriageway width is measured as about 7 m from clip c3 at 12 s, against a car's width. The camber slope of 2.5 % is confirmed from the standard the client cites. The shoulder width is unknown, so no figure is shown for it and the drawing is labelled "illustrative, not to scale". Relationships: the road falls from its centre to both edges; the drain is lower than the shoulder.

## 8. Not covered

- How accurately Gemini measures from frames. The operator's approval of the spec is the backstop.
- Drawings with more than about ten labelled sizes. Split them into a build (`video/diagram-in-states.md`).
