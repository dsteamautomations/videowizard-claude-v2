# Prompt craft for labelled pictures

How to lay out a picture with many parts: a labelled diagram, a teaching board, a technical illustration, a place. Read with `RULEBOOK.md`. A number, size or count in a graphic takes the drawn route; an AI picture carries words only, never a chart or a figure. Words to be read go only in the answer's `exact_text`, each with its place and size; never quote them in the prompt.

## General: every category

### 1. Labelled sections for a busy picture

For a picture with many interacting parts, labelled sections (scene, subject, details, constraints) are fine. Every value is a visible fact. No quality flags, no version headers, no aspect or size lines.

### 2. Fixed regions for boards and explainers

A strong board is a layout contract, not "make an infographic about X".

1. Name the kind of picture: a cutaway explainer, a field-guide plate, a classroom wall chart.
2. Fix the regions by landmark: a title band along the top edge, the cutaway below it, a summary strip along the right edge, a key along the bottom edge.
3. Say how annotation behaves: lead lines, numbered markers, close-up details, material notes.
4. Bound the style: a museum board, a science poster, an editorial card; not a generic poster.
5. The words of every label go in `exact_text`; the prompt says only where a label sits.

For a teaching board of a body, a material or the ground: name the subject exactly ("geological strata cross-section"); name the views ("front and back views"); ask for wall-chart clarity: clean hierarchy, thin labels, a key, a muted palette, nothing gory.

### 3. Diagram grammar

Use the language of diagrams, not of illustration:
- **Structure:** columns, zones, stacks, panels, nodes, ribbons, dashed dividers.
- **Direction:** arrows, loops, numbered flow markers, a reading order stated step by step.
- **Meaning:** what each colour and line style stands for (solid for the normal path, dashed for the exception).
- **Cleanliness:** large readable labels, a plain ground, uncluttered.

### 4. Style as visible technique

Name a style by what can be seen: medium, line, palette, texture ("flat 2D cel shading, thick outlines"; "coloured pencil on cream paper"). Never by a studio, artist or brand.

### 5. Formulas by picture kind

- **A place (interior or building):** the room or building type, the camera height and lens feel, the materials, the light's direction, the plain space, realistic shadows.
- **A technical illustration:** an exploded or cutaway structure, the parts in order, numbered markers, the materials, a plate or blueprint style.

## For advertisement-product

### Promotional hierarchy

A poster-like still needs a hierarchy, or every text block gets the same weight:
- The product or event name largest; then the claim; then variants; then any fine print. Each piece of wording is an `exact_text` entry with its place and size.
- Prices, dates and claims only from the job form; never invented. The logo is never drawn; the editor places it.
- Readable from a distance: a clear hierarchy, nothing tiny.

Three glances: at the first, the shape and theme are recognised; at the second, the promise reads; at the third, close looking finds texture and small details.

## For training-education and documentary-explainer

- A process explainer states its reading order outright (first panel to second, second to third), and each stage shows one action with its tool.

## Not available yet

- **Charts, data figures and app screens drawn by the picture model.** VideoWizard draws every number, chart and measured diagram itself; an AI picture never carries them.
- **Multi-panel boards and storyboard grids.** VideoWizard plans shots in the visual plan, one picture per call.
