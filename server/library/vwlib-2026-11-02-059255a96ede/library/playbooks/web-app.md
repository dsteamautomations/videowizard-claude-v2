# Labelled pictures and screens playbook

A labelled still without figures that explains a process (the process explainer), and, for product films, a real screen shown on a device. Read with `RULEBOOK.md` and the picture model's sheet. The server sets the model, the size and the quality; never write them in a prompt.

## General: every category

### The process explainer

Three or four stages in a row or a two-by-two, each with one short label and one simple illustration, thin arrows between them, the reading order stated. Each label is an `exact_text` entry with its place and size, never quoted in the prompt. Facts in the labels come from the job form; nothing is invented. A number, size, count or chart is not drawn here: it takes the drawn route. A graphic that changes on screen is `video/diagram-in-states.md`.

Pin the illustrated style by its technique, the same in every picture of the film: for example solid colour blocks, no gradients, no shadows, simplified proportions. Describe empty space as a surface ("a plain off-white ground, no objects"), never as nothing.

### The prompt

Image roles first, if any. Then the layout: the stages, their order and where each sits by a landmark and a distance (the first stage, then "one stage-width further along"), never "centre" or "left third". Then each stage's illustration, the arrows and their direction, the style line. Labels: only the exact-text entries. End with short constraints (no extra icons, no second set of arrows) and the standing no-extra-text line.

### Checklist lines

- Reading order and arrow directions are correct. must.
- Every label reads letter for letter as its `exact_text` entry; no extra text. must.
- The style is the same across every stage. must.

## For advertisement-product

### Decisions already taken

| Decision | Value | Why |
| --- | --- | --- |
| Real screens stay real | The client's actual screenshot is placed on a described device; the screen's contents are never regenerated. | A fake screen misrepresents the product. |
| Devices are described, never named | "A slim smartphone with rounded corners and a thin bezel", not a brand. | No real brands in a prompt. |

### The device mockup

The screenshot is Image 1. The prompt places it on a described device, on a described surface, at a named angle and light, and changes nothing on the screen: "the screen shows Image 1 exactly, fitted to the screen shape with no stretching, no added icons, status bar or borders". Describe the product as if it exists, never as concept art.

### Checklist lines

- The screen's content is identical to Image 1; no added icons, bars or notifications. must.
- No real device, app or brand name or logo visible. must.

### What goes wrong, and the fix

| Habit | Fix |
| --- | --- |
| The screen is redesigned or gains icons | "The screen shows Image 1 exactly; no icons, status bars or app borders" |
| A concept-art look on the screen | Describe the device and the product as if they already exist: surface, angle, light |

## Not available yet

- **A screen invented from words (advertisement-product):** an app described "as if it exists", with its layout and labels. VideoWizard shows only real screenshots today.
- **Pixel-exact screens composited in an editor (advertisement-product):** VideoWizard does not composite.
