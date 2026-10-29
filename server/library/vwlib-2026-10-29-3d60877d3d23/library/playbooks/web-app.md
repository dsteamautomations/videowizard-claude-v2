# Website and app visuals playbook

Version 0.1, written 2026-10-19. Status: draft, untested on a real job. One file for every image that goes into a website, an app listing or a pitch for one. Read it with `RULEBOOK.md`, the channel sheet row, the model sheet and the job form. Built-from list at the end. This is the thinnest area in the library; several tasks here are written from first principles and need testing most.

## 1. What this playbook covers

Tasks on the job form: `landing-hero`, `icon-set`, `spot-illustration`, `device-mockup`, `app-store-panel`, `process-explainer`, `email-header`, `wireframe-to-concept`, `brand-board`. A product photo for a product page is the product playbook. A social graphic is social.

## 2. Decisions already taken

| Decision | Value | Why |
| --- | --- | --- |
| Nothing here is shippable UI | A generated screen, icon or illustration is a reference or a concept for sign-off. Icons and illustrations are redrawn as vectors; screens are built by the web team. The answer form says so in `then`. | Rulebook 5; workflow "what the model should not produce as final". |
| Real screenshots stay real | For `device-mockup` and `app-store-panel` the client's actual screenshot, tagged `scene`, is placed into a frame or panel. The screen contents are never regenerated. | A fake screen misrepresents the product. |
| Model | GPT Image 2.5 Sunburst for anything with screen text, UI detail or a placed screenshot. Nano Banana 2.1 for icon sets and spot illustrations, which have no text, and for 21:9 or wider heroes. | Dense text and placed screenshots need edit precision; icons need cheap consistent sets. |
| Quality | `high` for anything with small text. `medium` for icons, illustrations and heroes. | Fact sheets. |
| Reserved text side | Every hero reserves a calm area for live text, usually the left 45 percent on desktop and the top or bottom third on mobile, stated in the prompt as empty space. Copy is never rendered into a hero. | Live text is accessible, editable and indexable. |
| Device names | Devices are described, never named: "a current slim smartphone with rounded corners and a thin bezel", not a brand. | Compliance C08. |
| Palette lock | Brand colours by name and hex from the preamble; nothing else. | Brand kit. |
| Sets are one call where possible | An icon set or an illustration set is generated as one grid in one call so the style holds, then cut up. Extra items later are generated with the grid as Image 1. | Consistency across a set is the hard part. |

## 3. Before writing

1. Placement: `website_hero_16x9` plus `website_hero_mobile_4x5`, `email_header`, `appstore_screenshot`, or a page size from the web team.
2. The page's purpose and the headline that will sit beside the image, so the image can leave room for it and not say the same thing.
3. For icons: the list of concepts, one phrase each, and the count. For illustrations: the sections or empty states they serve.
4. For mockups and panels: the real screenshots, tagged `scene`, and the exact captions.
5. For a wireframe: the sketch tagged `sketch`, and the real copy for the page, or a note that copy is placeholder.
6. The brand's illustration and icon style line from the preamble: line weight, corner radius, fill or outline, palette. If the kit has none, the job form says "none" and Claude proposes one in the answer form's notes.

## 4. Task notes

**landing-hero.** One subject, photographed or illustrated in the brand's style, placed in one half of the frame; the other half calm and empty for live text. Describe the empty side as a surface, not as nothing: "a plain warm off-white wall, no objects, no texture, no gradient". Make the 16:9 master, then reframe to 4:5 for mobile from the approved master with the subject moved to the lower two thirds. Seeds P034, P001.

**icon-set.** One grid in one call. State the grid, the count, one concept per cell, equal spacing, one light direction, one line weight, one corner radius, a plain background, "strong silhouettes readable at small size", no text, no border. The recipe P040 is the pattern. The output is an atlas to be redrawn in vectors; say so. For a second batch, send the approved grid as Image 1 and "match its style exactly".

**spot-illustration.** The same discipline for small scene illustrations in feature sections and empty states: one style line repeated verbatim in every call, one palette, people without facial features if the brand's style is flat. The flat-design example in `gallery/more-illustration-styles.md` No. 142 shows how to pin a style in words: solid colour blocks, no gradients, no shadows, simplified proportions.

**device-mockup.** The client's screenshot is Image 1, tagged `scene`. The prompt places it on a described device on a described surface and changes nothing on the screen: "the screen shows Image 1 exactly, fitted to the screen shape with no stretching, no added icons, status bar or borders". The screen-replacement rule from the Nano Banana additions is the wording. If any pixel of the screen must be exact, composite in an editor.

**app-store-panel.** A caption band at the top with the exact caption in quotes, the real screenshot below in a described device, the brand background. One panel per call, then the rest with the first as Image 1 for consistency. Captions are claims; they go through C01. Sizes per store from the channel sheet row; verify before each listing.

**process-explainer.** Three or four stages in a row or a 2x2, each with one label in quotes and one simple illustration, thin arrows, reading order stated. Recipes P025, P029, P030 are the patterns. Facts in the labels come from the job form; nothing is invented. For live text pages, generate the illustrations without labels and let the page carry the words.

**email-header.** A mood image, 2:1 to 4:1, that still reads at half width. No copy in the image; the headline is live text. Made by reframing an approved master where one exists. The simplest background that survives image-blocking.

**wireframe-to-concept.** The sketch is a layout guide only: "use the sketch for position and silhouette; the stroke is a shape guide, not an object to print". One concept per call, or a 2x2 board of four directions with equal gutters for a sign-off meeting, as in P074. Real copy if supplied, otherwise short placeholder words the client knows are placeholders. The result is a concept for sign-off, then built properly.

**brand-board.** A one-image showcase: wordmark area reserved, palette swatches with hex values as text, type feel shown as sample words, two or three touchpoints such as a card, a bag, a screen. Seeds P031, P081, gallery No. 60 and 62. The logo itself is never drawn; the board shows where it sits.

## 5. Writing the prompt

For screens and panels, Google's and OpenAI's advice agree: describe the product "as if it already exists", with layout, hierarchy, spacing and real interface elements; avoid concept-art and sketch language. Pixmind's realism cues: a status bar time, one item checked off, "no watermark, no real app branding".

House shape for a screen-based image:

```text
{brand preamble}
Asset: {task} for {placement}. Target aspect ratio: {ratio}. Mode: {generate | edit}.
Device or canvas: {described device, screen size in words} on {surface}, {camera angle}, {light}.
Screen: {Image 1 exactly, fitted to the screen, nothing added} | {the app as if it exists: header with "exact text", three cards labelled "A", "B", "C", bottom navigation "Home", "Cards", "Profile"}.
Palette: {brand colours by name and hex}; {background family}.
Exact image text: {captions in quotes, exactly once each}. No other text.
Constraints: no placeholder text, no lorem ipsum, no concept-art rendering, no real brand or device names, no added icons or notifications, {logo reserve}.
Render only explicitly requested image text. Do not add unrelated logos, signatures or captions.
```

House shape for a set of icons or illustrations:

```text
{brand preamble}
Asset: {icon set | spot illustration set} of {n} items. Target aspect ratio: 1:1. Mode: generate.
Grid: {rows} by {columns}, equal cells, equal spacing, plain {colour} background, no borders, no text.
Style, repeated verbatim in every call: {line weight}, {corner radius}, {fill or outline}, {palette by hex}, {one top-left light direction}, {flat | soft shaded}.
Items, one per cell, left to right, top to bottom: {1 concept}, {2 concept}, ...
Constraints: one item per cell; strong silhouettes readable at 24 px; same scale across cells; no cell empty; no captions; this is an atlas for vector redraw.
Render only explicitly requested image text. Do not add unrelated logos, signatures or captions.
```

## 6. Checklist lines for web-app

- Reserved text side empty and calm; the subject does not cross into it. must, heroes.
- Screen content identical to Image 1 when a screenshot was placed; no added icons, bars or notifications. must, mockups and panels.
- Every caption and label letter by letter; no placeholder text in a final. must.
- Icon set: one item per cell, equal scale, one light direction, no cell empty, silhouettes readable at 24 px. must.
- Style identical across the set when placed side by side: line weight, corner radius, palette. must.
- No real device, app or brand name or logo visible. must.
- Both hero crops from one master; subject position consistent between them. should.
- Reading order and arrow directions correct in explainers. must.
- Output size per the channel row or the web team's spec. must.

## 7. What goes wrong on web-app jobs, and the fix

| Habit | Fix | Seen in |
| --- | --- | --- |
| The screen gets redesigned or gains icons | "The screen shows Image 1 exactly; no icons, status bars or app borders"; composite if it persists | Nano Banana additions note 1 |
| Concept-art look on a screen | "Describe the product as if it already exists"; add status bar time and real labels | craft section 6; Pixmind lines 8 and 9 |
| Icons in a set drift in style or scale | One grid, one call; repeat the style line verbatim; send the approved grid as Image 1 for additions | P040; storyboard-sheet rules |
| Hero subject invades the text side | Describe the empty side as a plain surface; "no objects in the left 45 percent" | P034 |
| Invented testimonials, availability or checkout UI on a landing concept | Forbid them by name in constraints | P034 constraints |
| Small UI text soft | `high` quality on GPT Image; 2K on Nano Banana; or leave labels to live text | fact sheets |
| A real brand's interface style leaks from a shelf prompt | Replace names; describe the aesthetic | gallery markers |
| Wireframe strokes printed into the concept | "The stroke is a shape guide, not an object to print on top" | P074 |

## 8. Evidence

None yet. Promotion needs acceptance on two briefs from two different clients, and for icons and screens, acceptance by the web team without rework.

## 9. Built from

`00-method/craft.md` section 6; `00-method/craft-additions-pixmind.md` UI and advertising lines; `00-method/craft-additions-nanobanana.md` note 1; `gallery/ui-ux-mockups.md` No. 103 to 107; `gallery/ui-and-ad-additions.md` UI section; `gallery/more-illustration-styles.md` No. 142 to 147; `prompts/06-brand-ui.md` P031 to P036; `prompts/07-stories-games.md` P040; `prompts/05-information.md` P025, P029, P030; `prompts/14-sketch-to-story.md` P074, P081, P082; `DIRECTION.md` section 7 scenarios A30 to A38; `models/gpt-image/FACT-SHEET.md` and `models/nano-banana/FACT-SHEET.md` sections on text, references and when to pick.
