# Audit B: four guidebooks against "every video category, today's models"

Library: `videowizard-v2/server/library/vwlib-2026-10-29-3d60877d3d23/`. Read only. Context file: `VW-MAP.md` ("Where VideoWizard overrides the library").

**How words are counted:** whitespace tokens (`wc -w`) per section body, heading lines excluded. Table pipes and code blocks count, so table-heavy sections read a little high. Where one heading mixes kept and removed text it is split into a/b rows, each with its own count. Override rows are named by their "Library says" cell in VW-MAP.

---

## 1. `library/video/craft/animatic-keyframes.md` (4,769 words)

| file § heading | words | tag | evidence (≤20 words) | action | generic rewrite |
|---|---|---|---|---|---|
| (preamble: provenance, warnings) | 140 | PROVENANCE | "Source repository: https://github.com/smixs/visual-skills … race-brief constraints (faces banned, cold palette, amber ban)" | Remove (move to SOURCES.md) | — |
| # Keyframes for an animatic, para 1 | 65 | PICTURE-KIND | "a panel must report its story function, its drama, and the motion it cannot show, all frozen" | Keep. Drop "(usually) no face" | — |
| # intro, para 2 (cross-links) | 96 | OVERRIDDEN | "`seedance.md` / `kling.md` / `veo.md` to animate each locked frame … Storyboard format C" | Remove. Rows "A choice of video model" and "Storyboard grids" (not used). Most linked files are not in the bundle | — |
| # intro, the running brief | 61 | SOURCE-SPECIFIC | "drag/drift race spot, cold combative palette … amber only as the start-tree's alien pulse" | Remove | — |
| ## Contents | 72 | PROVENANCE | "1. What an animatic keyframe must do 2. The keyframe card" | Remove (navigation only) | — |
| ## 1a What a keyframe must do (four jobs) | 202 | PICTURE-KIND | "every panel does four things at once … One readable story-beat … One function tag … One emotion … One implied motion" | Keep. Filed with the keyframe step | — |
| ## 1b "machine's face" sentence | 33 | SOURCE-SPECIFIC | "Reaction is reassigned … to the machine's face — the needle jumping, the slick wrinkling" | Convert | "When no face is shown, give the reaction to an object or body part that visibly changes state." |
| ## 2. The keyframe card | 355 | SOURCE-SPECIFIC | "Light + palette … concrete colors, amber-ban repeated"; "Sound. what audio sits under the held frame" | Convert. See **Rewrite A**. The Sound field is also OVERRIDDEN (row "Audio described…": takes have no sound). Timecode and the race caption words are dropped | Rewrite A (below) |
| ## 3. Density ladder | 340 | OVERRIDDEN | "Loudness in the audio = panel count in the board … A 30s spot lands at ~18-26 panels" | Remove. Row "Storyboard grids…": the visual plan carries the shots and seconds. Also race-specific ("Sportsman tree fires three ambers") | — |
| ## 4a Six frozen cues (intro + table) | 278 | PICTURE-KIND | "Never write 'motion' — write the artifact motion leaves behind" | Keep for **image shots** (held stills). For a start image of a video take, see contradiction C8. Replace the race examples in the table (guardrail, tyre sidewall) with neutral ones | — |
| ## 4b Per-technique kit | 431 | SOURCE-SPECIFIC | "Dod Mantle whip-panned every overtake in *Rush* … Goodyear's deliberately silent slow-mo … NHRA burnout-cam" | Convert. Named directors and brands are style anchors (RULEBOOK 9 says translate them) | "Speed in a still: subject sharp, background smeared along the travel line. Force: smoke, dust or spray lit from behind. Intent: a pose that can only resolve forward, empty space ahead of the subject. Instability: tilt the horizon, at one beat only." |
| ## 4c Speed-budget rule | 89 | SOURCE-SPECIFIC | "(a) camera at/below bumper height, (b) asphalt streaking the lower frame" | Convert (fast-motion stills, any category) | "A 'fast' still needs three of: low camera, ground streaking past, a near object passing the frame edge, sharp subject on a blurred field, a vibration cue." |
| ## 5a Faces banned, redistribute | 81 | SOURCE-SPECIFIC | "Faces banned, redistribute: decision → anatomy mid-action; internal state → an object crossing a threshold" | Convert: faces are allowed in VideoWizard. Keep the idea for faceless shots | "Where a face is not shown, a decision goes to a hand mid-action, an inner state to an object changing state, rivalry or looking to the space between subjects." |
| ## 5b Two load-bearing rules | 121 | SOURCE-SPECIFIC | "Anatomy only on a decision … (Leone's hands-before-the-draw; Nike *Take It to the Next Level* …)" | Convert. The rule is sound for every category; drop the named film and adverts | "Show a hand only when it does something: name the verb (grip, press, turn, release). Show an object only in its changed state (switched on, poured, broken), never idle." |
| ## 5c Substitution table + cheat-sheet | 380 | SOURCE-SPECIFIC | "tach needle pinned in red arc; slick sidewall wrinkling … Cold palette throughout" | Convert to a short mapping; drop the drag-race rows | "Feeling as a visible state: fear: tremor, held breath, sweat; resolve: grip at full strength, tendons raised; focus: body still, eyes or tool on the target; strain: a material at its limit; relief: grip opening, dust settling." |
| ## 6a Core law + depth-layer jobs | 138 | PICTURE-KIND | "One focal point, one emotion, three working depth layers, zero dead objects." | Keep | — |
| ## 6b Plane table (drag-race objects) | 87 | SOURCE-SPECIFIC | "roll-cage bar, mirror edge, harness strap … rival lane headlight" | Convert: keep the "Default job" column, drop the race column | "Foreground frames or puts us inside; midground holds the subject and the act; background gives place, context or stakes. Give each layer a different sharpness." |
| ## 6c One-glance + reward | 83 | PICTURE-KIND | "name the single focal point before generating … The second-look reward is a reflection, a bridge object" | Keep. Strip the tach and staging-bulb examples | — |
| ## 6d Centerline spine, then break symmetry | 119 | SOURCE-SPECIFIC | "Anderson centers … Bong breaks balanced staging … both cars mirrored across the centerline, Tree dead-middle" | Convert | "A symmetric frame reads as stillness or tension; break the symmetry at the moment of change. Use the pair once." |
| ## 6e Evidence test (functional vs decorative clutter) | 96 | GENERAL | "Keep an object only if it does at least one of: indicator of state … stage of action … bridge" | Keep (drop "(Park)") | — |
| ## 6f Angle encodes the beat | 38 | GENERAL | "low / ground-level = power … eye-level lateral = parity … high / top-down = judgment, smallness, aftermath" | Keep | — |
| ## 7a Weight at the start (token lore) | 63 | OUTDATED | "the model puts most attention on the first 30-40% of tokens" | Remove. Token-position lore from older models; RULEBOOK 3 (canvas before subject) already sets the order | — |
| ## 7b Panel → prompt skeleton | 138 | SOURCE-SPECIFIC | "[Light + palette] … concrete colors; amber-ban"; "[Face rule] 'no face'" | Convert | "Prompt order: framing and camera height; the anchor and its state; foreground, midground and background, each with its job; the frozen motion (image shots only); one light source, its direction, named colours; texture only if the style calls for it." |
| ## 7c Rules that keep the still honest | 143 | SOURCE-SPECIFIC | "Keep faces out or fragmented … ~70% of the frame stays unlit" | Convert. The low-key look is the race brief's own; it conflicts with de-slop §6 (C6) | "Name blur only where it falls ('blur on the turning wheel, the subject sharp'). Show a sound by what causes it (steam, a hammer mid-strike), never by naming it." |
| ## 7d Hand to seedance/kling/veo | 56 | OVERRIDDEN | "hand it to `seedance.md` / `kling.md` / `veo.md` with the single dominant move" | Remove. Rows "A choice of video model" and "The clip prompt carries the camera move…" (the server writes the Camera line) | — |
| ## 8. Worked board, 30s race spot | 692 | SOURCE-SPECIFIC | "A Sportsman-tree drag run, cold palette, no faces — ~13 panels" | Remove. Also OVERRIDDEN (no storyboards; its Sound column is not used) | — |
| ## 9. Checklist | 369 | SOURCE-SPECIFIC | "Cold palette held — steel/cyan/magenta/mercury-white … amber ≤15% … No face … Sound cell filled" | Convert | "Before sending: beat in one sentence; one job; one anchor; a feeling shown through a body or object state; an object in its changed state, not idle; three depth layers; for a start image, room for the planned move. Fails any → rewrite." |

## 2. `library/video/consistent-character-frames.md` (4,256 words)

| file § heading | words | tag | evidence (≤20 words) | action | generic rewrite |
|---|---|---|---|---|---|
| # title block: source lines + "Note written here" | 106 | PROVENANCE | "Source repository: https://github.com/motiful/product-shots … the source is a nine-frame fashion-editorial method for e-commerce apparel" | Remove (move to SOURCES.md) | — |
| # title block: "Produces a 9-image fashion-editorial series" | 65 | SOURCE-SPECIFIC | "presents 3 photography-style presets (Retro Analog Flash / Soft Muted Film / Hard Flash Editorial)" | Remove | — |
| ## Principles P1 Reference image mandatory | 28 | OVERRIDDEN | "Pure text descriptions are not allowed; identity consistency cannot be guaranteed without it." | Remove. Row "A person's reference picture sent with every call…" (Decision 5: people from words) | — |
| ## Principles P2 Analyse before generate | 23 | GENERAL | "extract all 14 variables from the reference image before filling any prompt. Never guess defaults" | Keep (agrees with Decision 5) | — |
| ## Principles P3 Hairstyle non-negotiable | 34 | OUTDATED | "every prompt MUST include `{HAIRSTYLE} intact`, `NO loose hair`, `NO reinterpretation`" | Convert. Capitalised negative strings are an old-model habit | "Name the hair's structure (loose or tied, where, how fastened). It is the same from every side." |
| ## Principles P4 Crop boundaries hard | 40 | PICTURE-KIND | "'framed to mid-thigh' means knees/lower legs/feet are forbidden in frame" | Keep (the crop as a checkable rule; RULEBOOK 2) | — |
| ## Principles P5 Style is global, verbatim | 32 | OVERRIDDEN | "the same `{PHOTOGRAPHY_STYLE}` block is repeated verbatim in every one of the 9 prompts" | Remove. Row "Nine-photo series, three style presets…" (style from the approved style picture) | — |
| ## Principles P6 Accessories follow the reference | 46 | GENERAL | "if the reference has none → never add them" | Keep | — |
| ## Principles P7 Pause for style selection | 31 | OVERRIDDEN | "present the 3 presets (do not auto-pick a default)" | Remove. Same row (three style presets) | — |
| ## Principles P8 Batch generate | 26 | OVERRIDDEN | "produce all 9 images in a single batch" | Remove. Same row ("one picture per call") | — |
| ## Section 1 Variables: kept fields (hair ×3, skin, eyes, face, outfit, jewellery, other accessories, header, composed-field note, ask-user line) | 254 | PICTURE-KIND | "`OUTFIT` … All garment items (color / material / fit / layering)"; "ask the user to clarify (do NOT silently default)" | Keep as the base of **Rewrite B**. It lacks build, age, posture and how garments are worn, which VW-MAP Decision 5 names | Rewrite B (below) |
| ## Section 1: `BAG` row | 22 | SOURCE-SPECIFIC | "`BAG` … Type / color / material / position" | Fold into "carried items" (Rewrite B) | — |
| ## Section 1: `REFERENCE_IMAGE`, `BACKGROUND_COLOR`, `PHOTOGRAPHY_STYLE`, `ASPECT_RATIO` rows | 95 | OVERRIDDEN | "`ASPECT_RATIO` … `\"3:4\"`"; "`REFERENCE_IMAGE` … locks identity" | Remove. Rows "A person's reference picture…" and "Nine-photo series…, a 3:4 frame" (the server sets frame, ground and style) | — |
| ### Variable Extraction Specifications (hairstyle, outfit, skin) | 217 | PICTURE-KIND | "Wrong example: 'long hair' Correct example: 'dark brown long hair tied in a low ponytail, tight and smooth'" | Keep. The wrong/right pairs are the most useful part of the file | — |
| ## Section 3 Workflow (diagram + style pause) | 144 | OVERRIDDEN | "Fill 9 prompt templates; each call receives: reference image (mandatory)"; "Single-batch generation, 9 images" | Remove. Rows "A person's reference picture…" and "Nine-photo series…" | — |
| ### Workflow Design Notes | 70 | OVERRIDDEN | "Batch generation — all 9 images in one call avoids inter-call model-state drift" | Remove. "Analyse first" is REDUNDANT with P2 (they agree) | — |
| ## Variable Override Logic | 156 | OVERRIDDEN | "`OUTFIT` | 1, 2, 3, 4, 6, 7, 8, 9 | Image 5 … does not show clothing" | Remove. Row "Nine-photo series…" (one sheet); row "Edits" (one change per edit) | — |
| ## Hard Constraints intro | 23 | REDUNDANT | "Identity / hairstyle / crop integrity cannot be recovered downstream — if any rule fails, regenerate" | Remove. RULEBOOK 8.3 and 15 say the same (they agree) | — |
| ### Rule 1 Reference Image Mandatory | 93 | OVERRIDDEN | "pure text descriptions cannot transmit the high-dimensional facial features" | Remove. Decision 5 row | — |
| ### Rule 2 Analyse Before Generate | 37 | REDUNDANT | "All 14 variables MUST be extracted before any prompt template is filled" | Remove. Same as P2 (they agree) | — |
| ### Rule 3 Hairstyle Structure Intact | 140 | OUTDATED | "MUST include 'NO loose hair' … 'NO reinterpretation' … Validation views: Image 4 (back) and Image 8 (side)" | Convert | "State the hair's structure once, in words a checker can tick. Where the sheet shows a back or side view, check there that the structure held." |
| ### Rule 4 Accessory Fidelity | 81 | REDUNDANT | "IF reference has no accessory → MUST NOT add" | Remove. Same as P6 (they agree). The "frame doesn't reach them" string is OUTDATED | — |
| ### Rule 5 Hard Crop Boundaries (9-image table) | 223 | SOURCE-SPECIFIC | "e-commerce / lookbook standards"; nine per-image crops "5 | (eyes/nose/lips only)" | Convert | "Write a crop as the last part of the body in frame ('head to mid-thigh'). Add one negative only if the result breaks it." |
| ### Rule 6 Global Style Unity | 67 | OVERRIDDEN | "repeats the full chosen `{PHOTOGRAPHY_STYLE}` block verbatim. Do not abbreviate" | Remove. Row "Nine-photo series…" (approved style picture). Verbatim repetition is also OUTDATED | — |
| ### Rule 7 User Override Re-render | 43 | OVERRIDDEN | "Re-render only the images affected by that variable" | Remove. Rows "Edits" and the sheet request | — |
| ### Rule 8 Single-Batch Generation | 62 | OVERRIDDEN | "Single-batch generation locks the random-seed neighbourhood" | Remove. "One picture per call"; the seed claim is untested | — |
| ### Why These Are MUST-level | 153 | REDUNDANT | "Crop boundary breach → e-commerce / lookbook standards reject the asset" | Remove. It restates Rules 1–8 and DISAGREES with VW on Rules 1, 6 and 8 | — |
| ### Self-check after rendering | 69 | SOURCE-SPECIFIC | "Image 4 (back view) — hairstyle structure visible from behind … Image 5 … only eyes/nose/lips" | Convert | "After the sheet: hair structure, garments and accessories match the description in every view; nothing added; each view cropped as written." |
| ## Section 2 Photography Style Presets (intro) | 110 | OVERRIDDEN | "3 standardised photography styles … repeated verbatim into every one of the 9 task prompts" | Remove. Row "three style presets" | — |
| ### Preset A Retro Analog Flash | 193 | OVERRIDDEN | "Applicable scenarios: retro fashion, streetwear brands, Y2K style"; "5500K"; "ISO 400-800" | Remove (also SOURCE-SPECIFIC) | — |
| ### Preset B Soft Muted Film | 141 | OVERRIDDEN | "Standard value: #f1eee9 (light cream) Tolerance: ±5%" | Remove (also SOURCE-SPECIFIC; over-explicit numbers) | — |
| ### Preset C Hard Flash Editorial | 209 | OVERRIDDEN | "Oily sheen: pronounced … Highlight treatment: Density: high (multiple highlight points)" | Remove. It also contradicts de-slop §6 (C5) | — |
| ## Section 4 Task Prompts intro + invariants | 190 | OVERRIDDEN | "`[Reference image: {REFERENCE_IMAGE}]` header present; `{PHOTOGRAPHY_STYLE}` block repeated VERBATIM" | Remove. Row "fixed front/side/back views" (`required_views` from the plan) | — |
| ### Image 1 Three-Quarter Fashion Portrait | 208 | OVERRIDDEN | "Accessories: {BAG} over shoulder … 85mm prime lens, {ASPECT_RATIO} vertical … Hands behind back" | Remove. Fixed fashion views and poses; the server builds the sheet request | — |
| ### Image 2 High-Angle Bird's-Eye | 112 | OVERRIDDEN | "Camera position: Height: 1.5-2m above the subject … Hands: on hips" | Remove (same row) | — |
| ### Image 3 Over-the-Shoulder Close-Up | 94 | OVERRIDDEN | "Head movement: sharp turn to the right, looking at the camera over the shoulder" | Remove (same row) | — |
| ### Image 4 Back View | 117 | OVERRIDDEN | "Mandatory prompt constraint: 'NO loose hair, NO reinterpretation'" | Remove (same row; the check survives in the Rule 3 rewrite) | — |
| ### Image 5 Extreme Facial Close-Up | 121 | OVERRIDDEN | "105mm+ macro … Included area: eyes / nose / lips only" | Remove (same row) | — |
| ### Image 6 Over-Right-Shoulder Glance | 82 | OVERRIDDEN | "Gaze characteristics: soft, not direct, slightly out of focus (candid feel)" | Remove (same row) | — |
| ### Image 7 Low-Angle, Contrapposto | 91 | OVERRIDDEN | "Body forms a natural S-curve … Head: tilted back, chin raised" | Remove (same row; fashion posing) | — |
| ### Image 8 Side Profile | 116 | OVERRIDDEN | "full profile (90°, right side facing the camera)" | Remove (same row) | — |
| ### Image 9 Opposing Torso Twist | 92 | OVERRIDDEN | "Pelvis rotation: about 20° to the right Chest rotation: about 30° to the left" | Remove (same row; over-explicit degrees) | — |

## 3. `library/00-method/de-slop.md` (1,132 words)

| file § heading | words | tag | evidence (≤20 words) | action | generic rewrite |
|---|---|---|---|---|---|
| (preamble) | 80 | PROVENANCE | "Source repository: https://github.com/smixs/visual-skills … Model names and the `quality: medium` advice kept as written and flagged" | Remove | — |
| # De-Slop intro | 148 | PICTURE-KIND | "Load this whenever the brief is a real photograph … Do NOT load it for illustration, 3D, poster graphics" | Keep. Trim the "same rule GPT Image 2.5 already carries… gpt-image.md" sentence (a cross-file note) | — |
| ## 1. The default prior | 209 | PICTURE-KIND | "Eyes | large, round, wide-open, symmetric | narrow, hooded, monolid, one eye smaller" | Keep. Also the best feed for Rewrite B's "Face" field | — |
| ## 2. Escalate every deviation in two places | 111 | PICTURE-KIND | "In `Constraints` … one imperative line per axis, labeled: `EYES:`, `SKIN:`, `BODY:`" | Keep, both model branches (the film's model may be either). RULEBOOK 11 says it in one line (they agree) | — |
| ## 3. Boosters banned | 57 | REDUNDANT | "`4K`, `8K`, `ultra-detailed` … `masterpiece`, `best quality`, `sharp focus`, `crisp`" | Remove. RULEBOOK 9 and the GPT Image fact sheet carry it (they agree). DISAGREES with craft §3 and §1 (C1, C2) | — |
| ## 4. A capture pipeline instead of adjectives | 139 | PICTURE-KIND | "Do not ask for 'realistic'. Name the device and the path the file took" | Keep | — |
| ## 5. Imperfections, and where they sit | 118 | PICTURE-KIND | "An imperfection without a location gets ignored or sprayed everywhere. Name the place" | Keep. Drop the link to `prompt-framework.md` (not in the bundle) | — |
| ## 6a Sharpness and grading (bullets 1–3) | 54 | PICTURE-KIND | "Ban the glow family in `Constraints`: HDR, bloom, high clarity, luminous or radiant skin" | Keep | — |
| ## 6b `quality: medium` bullet | 65 | OVERRIDDEN | "On GPT Image 2.5 stay at `quality: medium` for this kind of work" | Remove. Row "Images at a chosen quality" (always high) | — |
| ## 7. Self-check before sending | 104 | PICTURE-KIND | "At least three located imperfections from §5, each with a place." | Keep | — |
| ## 8. When the result still misses | 47 | GENERAL | "Treat every mismatch as a variable that was under-specified … one change per iteration" | Keep (agrees with the VW edit rule) | — |

## 4. `library/00-method/craft.md` (2,260 words)

| file § heading | words | tag | evidence (≤20 words) | action | generic rewrite |
|---|---|---|---|---|---|
| # Prompt craft (intro) | 31 | PROVENANCE | "Cross-cutting principles distilled from the full 162-prompt Gallery Atlas" | Remove | — |
| ## Table of contents | 117 | PROVENANCE | "15. Category-specific mini-schemas 18. Safety and copyright notes" (16 and 17 are missing) | Remove | — |
| ## 0. Use the Reference Gallery | 77 | OVERRIDDEN | "Open `gallery/README.md` … Product/food commercial render … No. 56–58" | Remove. The VW-MAP preamble says `gallery/README.md` is not available | — |
| ## 1. Exact text goes in quotes | 117 | OVERRIDDEN | "Wrap every displayed string in `\"…\"` … say `crisp`, `legible`" | Remove. Row "Exact words in quotes" (`exact_text` only). "crisp" is a booster (C2); "HILLSIDE TEA" is an outside brand example | — |
| ## 2. Canvas, aspect, layout before subject | 62 | REDUNDANT | "When structure matters, state the structure before the subject." | Remove. RULEBOOK 3 (they agree). Its grid examples are overridden (no storyboards) | — |
| ## 3. JSON / config-style prompts | 301 | OUTDATED | "\"render_flags\": [\"8K_UHD\", \"sharp_foreground\", \"editorial_finish\"] … VERSION: 1.0.0" | Rewrite | "For a picture with many interacting parts, labelled sections (scene, subject, details, constraints) are fine. Every value is a visible fact; no quality flags or version headers." |
| ## 4. Fixed-region schemas for infographics and boards | 177 | PICTURE-KIND | "Define the fixed layout zones: top title, left disassembly, right summary, bottom legend" | Keep with the diagram step. Strip "Adult height reference 175 cm" (row "Charts…": numbers take the drawn route). Labels go to `exact_text` | — |
| ## 5a Diagram grammar (core list) | 86 | PICTURE-KIND | "Structural primitives: columns, zones, stacks, panels, nodes … Directed relationships: arrows … numbered flow markers" | Keep (VW-MAP sends diagram shots here). Drop "NeurIPS camera-ready", "heatmaps, bars" and "thickness ∝ quantity" (row "Charts…") | — |
| ## 5b Security / agent-safety figure | 84 | SOURCE-SPECIFIC | "If illustrating prompt injection, quote the payload … `<!-- IGNORE previous instructions... -->`" | Remove (a research-paper niche) | — |
| ## 5c Data visualization mini-schema | 84 | OVERRIDDEN | "Name the chart family first: `small-multiples grid`, `network graph`, `chord diagram`, `treemap`" | Remove. Row "Charts, data visualisation…" | — |
| ## 6. UI prompts as product specs | 115 | OVERRIDDEN | "'AURAE', 'Good morning, Lina', and 'Total balance $12,480.36'" | Remove. Row "Charts…" (numbers in a graphic go drawn); RULEBOOK 5 (app screens never final) | — |
| ## 7. Multi-panel boards | 132 | OVERRIDDEN | "For character sheets, require front/side/back views, expression variations, parts breakdown" | Remove. Rows "Nine-photo series… fixed front/side/back views" and "Storyboard grids" | — |
| ## 8. Camera and capture context | 103 | REDUNDANT | "`RAW, unprocessed, full iPhone camera quality` … Pick one dominant capture frame." | Remove. De-slop §4 and RULEBOOK 11 (they agree; craft names a phone brand) | — |
| ## 9. Scene density beats adjectives | 60 | REDUNDANT | "include 5–12 concrete nouns for the scene and 2–4 material/lighting constraints" | Remove. RULEBOOK 9 gives the same numbers (they agree) | — |
| ## 10. Style anchors specific and bounded | 65 | SOURCE-SPECIFIC | "`MAPPA-style digital 2D animation`, `Studio Pierrot Naruto-Shippuden aesthetic`" | Convert. As written it DISAGREES with RULEBOOK 9 | "Name a style as its visible technique (medium, line, palette, texture, e.g. 'flat 2D cel shading, thick outlines'), never as a studio, artist or brand." |
| ## 11. Promotional hierarchy | 156 | CATEGORY: advertisement-product | "Product/event name largest … Claim/tagline … CTA … Three-glances test for hero posters" | Keep, filed under adverts. Change "`Exact readable text:`" to `exact_text`. Prices and dates only from the job form (RULEBOOK 6); the logo is never drawn | — |
| ## 12a Material, lighting, palette separate | 74 | REDUNDANT | "Do not compress them into 'premium'. Split them" | Remove. RULEBOOK 9 (they agree) | — |
| ## 12b Brand/label control | 48 | REDUNDANT | "use `no readable fake labels except a tiny generic mark \"AM ROUTINE\"`" | Remove. RULEBOOK 4.3 standing line and RULEBOOK 6 (they agree; "AM ROUTINE" is an outside brand) | — |
| ## 13. Edit prompts preserve invariants | 172 | OVERRIDDEN | "Make it a winter evening with heavy snowfall, snow dusted …, breath vapor …, cold blue-grey lighting" | Remove. Row "Edits": one change per edit, and the example makes about five. The keep-list rules are REDUNDANT with RULEBOOK 7–8. Attaching reference pictures for people is overridden by Decision 5 | — |
| ## 14. Negation is for strong priors | 74 | REDUNDANT | "Avoid lists should be short and targeted. Too many negatives can dominate the prompt." | Remove. RULEBOOK 10 (they agree) | — |
| ## 15. Category-specific mini-schemas | 67 | PICTURE-KIND | "Architecture/Interior: room type + camera/lens + materials + light direction + negative space" | Keep the place and technical-illustration formulas. Drop "Brand systems" (adverts; the logo is never drawn) and "Photography" (same as de-slop) | — |
| ## 18. Safety and copyright notes | 58 | REDUNDANT | "Real-person likeness edits often fail at the moderation layer" | Remove. RULEBOOK 7.6, 9 and 14; moot under Decision 5 (no person pictures sent) | — |

---

## Rewrite A: the still-picture card (replaces animatic-keyframes "## 2. The keyframe card")

Any AI still, any category. Fill every field first; an empty field is missing direction.

```text
STILL CARD
- Shot and kind.     shot id; image shot or start image of a video shot
- Beat.              what this one picture tells, in one sentence
- Job.               establish / reveal / detail / step / reaction / result
- Framing.           wide / medium / close / insert; camera height; lens feel ("50mm feel")
- Anchor.            the one thing the eye lands on first, and its state
- Depth.             foreground job (frame, put us inside); midground (subject, act);
                     background (place, stakes)
- Light and palette. one source, its direction, the surface it touches; the film's colours
- Feeling.           a body or object state (grip, posture), never named
- Motion.            image shot: frozen residue (blur on the moving part);
                     start image: the instant before the action, no blur
- Room for the move. start image: what the planned move needs in frame
- Continuity.        the sheets this picture must match
```

Add by category:
- documentary-explainer, training-education: the real place or step; a working hand names its verb.
- advertisement-product: product side, label, scale.
- narrative-story, social-ugc: the eye line.

(Dropped: Timecode, Sound, race captions.)

## Rewrite B: the person-description table (replaces consistent-character-frames "## Section 1 — Variables")

From the footage pictures, in words only (Decision 5). Unsure of a field: ask the operator, never default.

| Field | Write | When |
|---|---|---|
| Build | frame, proportions against something in shot | always |
| Apparent age | a range ("late forties") | always |
| Skin | undertone, lightness, located markers | always |
| Face | shape; each departure from the model's ideal (de-slop §1) | face visible |
| Eyes | colour, lid shape | face visible |
| Hair | colour; structure: loose or tied, fastening, position, volume, texture | always |
| Garments | each item: colour, material, fit, layers, how worn | always |
| Footwear | type, colour, wear | feet in frame |
| Accessories, carried items | type, colour, position, or "none" | always |
| Posture | stance, habitual hold | always |

By category:
- training, documentary: uniform, protective kit, tool in hand.
- advertisement-product: the product worn or held, side shown.
- narrative-story: wardrobe per scene.
- social-ugc: phone or camera habit.

No name, no real-person likeness; frame and style come from the film.

---

## Word totals per file

Kept = GENERAL + CATEGORY + PICTURE-KIND. Remove or convert = every other tag.

- **animatic-keyframes.md:** 4,769 total; 900 kept; 3,869 to remove or convert (of which 1,853 are SOURCE-SPECIFIC to convert, the rest to remove).
- **consistent-character-frames.md:** 4,256 total; 580 kept (P2, P4, P6, the Section 1 kept fields, the extraction specs); 3,676 to remove or convert (2,962 OVERRIDDEN).
- **de-slop.md:** 1,132 total; 930 kept; 202 to remove (provenance, the booster list already in RULEBOOK 9, the `quality: medium` bullet).
- **craft.md:** 2,260 total; 486 kept (§4, §5a, §11, §15); 1,774 to remove or convert.

## Contradictions between files (and with VideoWizard)

1. **Booster words.** craft §3's schema asks for `"8K_UHD"`, `"hyper-realistic commercial photography"` and `"sharp_foreground"`. De-slop §3 bans `8K`, `hyper-detailed` and `sharp focus`, and RULEBOOK 9 agrees with de-slop.
2. **"crisp".** craft §1 says to write `crisp`, `legible` for text. De-slop §3 and §6 say never write "crisp". They collide on any photographic still that also carries words.
3. **Which views a person sheet has.** craft §7 asks for front/side/back plus expressions and parts breakdown. consistent-character-frames fixes nine fashion crops. The video-frame playbook says front, three-quarter and side. VideoWizard says only the plan's `required_views`. Three library answers, one override.
4. **Words versus a reference picture for people.** consistent-character-frames P1 and Rule 1 say "Pure text descriptions are not allowed". Decision 5 and de-slop §2 (escalate each deviation in words) say the opposite. De-slop fits VideoWizard; consistent-character-frames does not.
5. **Gloss on skin.** consistent-character-frames Preset C asks for "Oily sheen: pronounced … multiple highlight points". De-slop §6 bans "luminous or radiant skin, glossy hair highlights".
6. **Blacks and contrast.** animatic-keyframes §7 and §9 ask for "crushed blacks", "~70% of the frame stays unlit" and an anamorphic flare. consistent-character-frames Preset C forbids "Pure black shadows (crushed blacks)". De-slop §6 asks for "low contrast … flat or natural" grading. Only the low-key race look demands crushed blacks.
7. **Named style anchors.** animatic-keyframes §4 to §6 (Rush, Ritchie, Vaughn, Leone, Nike, Honda Cog, Anderson, Bong) and craft §10 (MAPPA, Studio Pierrot) use names. RULEBOOK 9 says translate every name into its technique. animatic's own preamble warns about it but keeps the names.
8. **Motion blur in a start image.** animatic-keyframes §4 and §7 (and video-frame playbook line 37, which copies it) bake smear and streaks into the keyframe. For the start image of an Omni take, the video model has to create that motion itself. A pre-blurred first frame risks smear that never resolves. Not tested. Rewrite A limits frozen motion to image shots until one test settles it.
9. **One change per edit.** craft §13's model edit makes about five changes at once. De-slop §8 ("one change per iteration") and VideoWizard's Edits row ("the server refuses a 'Change only' that names two") both forbid that.
10. **Faces.** animatic-keyframes treats "No face" as a pass condition (§9). consistent-character-frames is built around faces (eye colour, face shape, a facial close-up). The no-face rule is the race brief's, not a VideoWizard rule.
11. **Negatives.** consistent-character-frames Rules 3 to 5 require fixed capitalised negative strings ("NO loose hair", "No knees, lower legs, or feet") in every prompt. craft §14 and RULEBOOK 10 say negatives should be short, targeted and used only against a strong prior.
12. **Repetition.** consistent-character-frames Rule 6 says repeat the style block verbatim and "Do not abbreviate". RULEBOOK 7.3 says "Do not restate what a reference already shows". VideoWizard sends the approved style picture instead.
