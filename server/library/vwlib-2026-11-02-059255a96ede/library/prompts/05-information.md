# Example prompts: labelled diagrams and teaching pictures

Five worked examples of an AI picture that carries words only: an explainer, a sector diagram, an illustrated map, a staged card, a process slide. Read with `00-method/craft.md`. The server sets the model, the frame and the size.

## General: every category

- **Words.** Every word to be read in the picture goes in the answer's `exact_text`, each with its place and size; the prompt names only where a label sits. Each example below lists its `exact_text` in a note.
- **Numbers.** A number, size or count takes the drawn route; never ask the picture model for a chart.
- **Places.** A landmark and a distance, never "centre" or "middle".
- **One closing line in every prompt:** no words other than the `exact_text`, no logos, signatures or captions.
- **Check before approving:** labels, counts, arrow directions and reading order, independently of how polished it looks.
- **Next edit:** one change per edit, the rest kept.

### Three-stage rain explainer

```text
A classroom infographic in three equal panels side by side, a title band along the top edge. Panel one: rain falling on a roof. Panel two: water running into a planted basin. Panel three: water soaking into the soil, shown in cutaway. A label sits under each panel. Simple cutaway illustrations, navy arrows, cream ground, green plants; clear space between the water routes and the labels.
Constraints: no drinking water shown, no performance figures. No words other than the exact_text; no logos, signatures or captions.
```

`exact_text`: WHERE RAIN GOES (title band, large); COLLECT, SLOW, SOAK (one under each panel, medium).
Next edit: "Increase only the arrow contrast; keep all stages and wording."
Check: the flow direction, and whether the soil cutaway shows the water soaking in.

### Tasting wheel for beginners

```text
A beginner tasting diagram: a round title disc with three equal sectors around it. Small original fruit, almond and cacao illustrations, one in each sector, beside its label. Cream paper, dark brown type, rust dividers, generous spacing. A simplified teaching graphic.
Constraints: exactly three sectors; no borrowed official wheel layout, no extra terms. No words other than the exact_text; no logos, signatures or captions.
```

`exact_text`: TASTE NOTES (on the title disc, large); FRUITY, NUTTY, COCOA (one per sector, medium).
Next edit: "Change only the fruity sector's accent to muted pink."
Check: count the sectors; each illustration matches its label.

### Illustrated neighbourhood map

```text
An illustrated map of a fictional neighbourhood. A square park where the two main streets cross; the library one block north of the park, the café one block east, the station one block south. A dotted walking route runs unbroken from the station to the park to the library. A label beside each place, a small title in the bottom corner by the station. Restrained isometric buildings, sage greenery, terracotta route.
Constraints: not a navigation map; no real coordinates, travel times or extra landmarks. No words other than the exact_text; no logos, signatures or captions.
```

`exact_text`: PARK, LIBRARY, CAFÉ, STATION (beside each place, medium); ILLUSTRATED MAP (bottom corner, small).
Next edit: "Change only the route colour to dark blue without moving its path."
Check: north, east and south placement; the route joins its end points without a gap.

### Plant life-cycle card

```text
A botanical learning card in a 2 by 2 grid of panels: a bean seed; germination with a root; a seedling with two leaves; a mature leafy plant. A label under each panel. Coloured pencil, clean cream margins, consistent scale. Three discreet arrows give the reading order: panel one to panel two, panel two to panel three, panel three to panel four.
Constraints: roots below the soil, leaves above; no dates or equal time spans implied. No words other than the exact_text; no logos, signatures or captions.
```

`exact_text`: SEED, ROOT, SEEDLING, PLANT (one under each panel, medium).
Next edit: "Enlarge only the root illustration in the second panel; keep the labels."
Check: the growth order, the plant's parts, the arrow between the rows; a subject expert reviews the botany.

### Workshop process slide

```text
A clean slide with a title band along the top edge and four equal cards in a row beneath it, joined by three thin arrows. Each card has one original simple illustration and its label beneath: a pencil drawing; a cardboard model; a hand testing the fit; a finished wooden object. Cream ground, alternating blue and rust accents.
Constraints: one illustration per stage; no extra steps or business claims. No words other than the exact_text; no logos, signatures or captions.
```

`exact_text`: FROM IDEA TO OBJECT (title band, large); SKETCH, PROTOTYPE, TEST, REFINE (one under each card, medium).
Next edit: "Change only the last card's accent to deep green."
Check: four cards, arrow direction, even alignment.

## For training-education and documentary-explainer

- The staged card and the process slide are the patterns for a step-by-step explanation: one action per panel, the reading order stated in arrows.

## For advertisement-product

- The process slide fits a "how it works" beat; the product's look comes from its approved sheet, and any claim only from the job form.
