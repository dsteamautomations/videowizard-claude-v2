# Consistent character frames from one reference: the multi-angle identity lock

Source repository: https://github.com/motiful/product-shots
Commit: 063c508b0b7f4db5cda89f10bdf20df25026dfc5
Licence: MIT
Source files: `skills/product-shots-multi-angle/SKILL.md`, `skills/product-shots-multi-angle/references/hard-constraints.md`, `skills/product-shots-multi-angle/references/variables-and-workflow.md`, `skills/product-shots-multi-angle/references/photography-style-presets.md`, `skills/product-shots-multi-angle/references/task-prompts.md`, `skills/product-shots-multi-angle/references/task-prompts-6-9.md`
Date copied: 2026-10-19

Note written here: the source is a nine-frame fashion-editorial method for e-commerce apparel. It is placed under `video/` because the same mechanism (extract identity variables first, repeat the style block verbatim in every frame, hard crop boundaries, two validation views that exist only to catch drift, an override map that says which frames to re-render) is what keeps a character consistent across keyframes and first frames. Blocks that existed only in Chinese in the source are translated and marked "[translated from Chinese]"; everything else is copied as written.

Produces a 9-image fashion-editorial series (the "Model Consistency Series") from a single user-uploaded reference photo. The method extracts 14 controllable variables from the reference, presents 3 photography-style presets (Retro Analog Flash / Soft Muted Film / Hard Flash Editorial), then renders 9 task-prompt templates (one per image) with strict crop, pose, hairstyle, and style continuity rules so all 9 frames read as a single shoot.

## Principles

1. **Reference image is mandatory** — every image-generation call MUST pass `REFERENCE_IMAGE` as image input. Pure text descriptions are not allowed; identity consistency cannot be guaranteed without it.
2. **Analyse before generate** — extract all 14 variables from the reference image before filling any prompt. Never guess defaults, never skip extraction.
3. **Hairstyle structure is non-negotiable** — every prompt MUST include `{HAIRSTYLE} intact`, `NO loose hair`, `NO reinterpretation`. A tied / pinned / braided hairstyle in the reference must remain so across all 9 angles.
4. **Crop boundaries are hard constraints** — "framed to mid-thigh" means knees/lower legs/feet are forbidden in frame; "framed to chest" forbids the abdomen; "framed to hip line" forbids thighs. Treat each frame's crop as a verifiable rule, not a hint.
5. **Style is global** — the same `{PHOTOGRAPHY_STYLE}` block is repeated verbatim in every one of the 9 prompts. No image may look cleaner / more digital / higher-contrast than the others.
6. **Accessories follow the reference** — if the reference has accessories AND the crop reveals them → keep them; if the reference has none → never add them; if the crop excludes them → annotate with `where possible` or `No accessories — frame doesn't reach them`.
7. **Pause for style selection** — if the user has not specified a style and has not uploaded a style reference image, present the 3 presets (do not auto-pick a default).
8. **Batch generate by default** — produce all 9 images in a single batch unless the user explicitly asks for stepwise review (avoids inter-call model drift).

## Section 1 — Variables (14 fields)

| # | Variable | Data Type | Source | Required | Default | Purpose |
|---|---|---|---|---|---|---|
| 1 | `REFERENCE_IMAGE` | Image URL | User upload | ✅ | none | Reference input to the image-generation model; locks identity |
| 2 | `HAIR_COLOR` | String | Image analysis | ✅ | none | Precise hue (e.g., "dark brown with red undertones") |
| 3 | `HAIRSTYLE` | String | Image analysis | ✅ | none | Structural description (tied/loose/bun, volume, texture, arrangement) |
| 4 | `HAIR_ACCESSORIES` | String | Image analysis | ❌ | `"none"` | Hair clips / bands / hoops — type, color, position |
| 5 | `SKIN_TONE` | String | Image analysis | ✅ | none | Skin tone + markers (freckles / moles / scars) |
| 6 | `EYE_COLOR` | String | Image analysis | ✅ | none | Iris color |
| 7 | `FACE_SHAPE` | String | Image analysis | ✅ | none | Facial structure description |
| 8 | `OUTFIT` | String | Image analysis | ✅ | none | All garment items (color / material / fit / layering) |
| 9 | `BAG` | String | Image analysis | ❌ | `"none"` | Type / color / material / position |
| 10 | `JEWELRY` | String | Image analysis | ❌ | `"none"` | All visible jewelry |
| 11 | `OTHER_ACCESSORIES` | String | Image analysis | ❌ | `"none"` | Other wearable accessories |
| 12 | `BACKGROUND_COLOR` | String / Hex | Image analysis or user-specified | ✅ | none | Studio backdrop color (e.g. `#f1eee9` or "light cream") |
| 13 | `PHOTOGRAPHY_STYLE` | String (long) | User-selected preset or custom | ✅ | none | Full lighting / texture / color spec |
| 14 | `ASPECT_RATIO` | String | User-specified or default | ✅ | `"3:4"` | Canvas aspect ratio |

`SUBJECT_DESCRIPTION` appears in the Task Prompts as a composed field that pulls from HAIR_COLOR + HAIRSTYLE + SKIN_TONE + OUTFIT + accessories — it is **not** a separate input variable.

If any required field cannot be extracted with confidence, ask the user to clarify (do NOT silently default).

### Variable Extraction Specifications

#### `HAIRSTYLE` Extraction Spec

```
Required dimensions:
1. Structure: tied / loose / bun / braided
2. Fastening: ponytail / bun / braid / chignon
3. Position: high / mid / low / side
4. Volume: voluminous / tight / natural
5. Texture: straight / curly / wavy / messy

Wrong example: "long hair"
Correct example: [translated from Chinese] "dark brown long hair tied in a low ponytail, tight and smooth, fastened with a black hair tie, no stray hairs"
```

#### `OUTFIT` Extraction Spec

```
Required dimensions:
1. Item list: top / pants / skirt / outerwear / shoes
2. Color: primary + accent (e.g. "off-white with light grey stripes")
3. Material: cotton / silk / leather / knit / denim
4. Fit: loose / fitted / oversized
5. Layering: inner + outer order

Wrong example: "white top and jeans"
Correct example: [translated from Chinese] "off-white loose cotton T-shirt, dark blue slim-fit jeans, black leather belt"
```

#### `SKIN_TONE` Extraction Spec

```
Required:
1. Base undertone: cool / warm / neutral
2. Lightness: light / medium / deep
3. Markers: location and density of freckles / moles / scars

Wrong example: "white skin"
Correct example: [translated from Chinese] "light warm-toned skin, faint freckles on the nose bridge and cheeks, small mole below the left cheekbone"
```

## Section 3 — Workflow

```
┌──────────────────────────┐
│ User uploads reference   │
└────────────┬─────────────┘
             │
             ▼
┌────────────────────────────────────┐
│ Multimodal analysis: extract 14    │ ← Vision Model
│ variables (hair/outfit/accessories │
│ /skin tone...)                     │
└────────────┬───────────────────────┘
             │
             ▼
┌────────────────────────────────────┐
│ Pause: present 3 photography style │ ← User interaction
│ presets (skip if style specified)  │
└────────────┬───────────────────────┘
             │
             ▼
┌────────────────────────────────────┐
│ Fill 9 prompt templates; each call │
│ receives:                          │
│ - reference image (mandatory)      │
│ - text prompt (composition+style)  │
└────────────┬───────────────────────┘
             │
             ▼
┌────────────────────────────────────┐
│ Single-batch generation, 9 images  │ ← Image-generation model
└────────────────────────────────────┘
```

Style-selection pause: skip the picker if the user has already specified a style (style keywords in the request such as "retro", "analog", "flash", "soft", "muted", "film", "hard", "editorial", "dramatic") or has uploaded an image specifically tagged as a style reference (distinct from REFERENCE_IMAGE which anchors identity). Otherwise pause and show the 3 presets.

### Workflow Design Notes

- **Analyse first** — extract variables before any prompt is filled. Prevents the model from guessing facial features / hair structure based on partial text.
- **Style confirmation** — visualised previews lower the user's decision cost and lock the lighting / colour budget before generation.
- **Batch generation** — all 9 images in one call avoids inter-call model-state drift (which produces "this image looks more digital than the others" failures).

## Variable Override Logic

The user can override any extracted variable. Map each variable to the images that must be re-rendered:

| Variable | Affected images | Reason |
|---|---|---|
| `HAIRSTYLE` / `HAIR_COLOR` / `HAIR_ACCESSORIES` | 1-9 (all) | hair is visible (or partially visible) in every frame; Image 4 + 8 are the strictest validation views |
| `OUTFIT` | 1, 2, 3, 4, 6, 7, 8, 9 | Image 5 (extreme facial close-up) does not show clothing |
| `BAG` / `JEWELRY` | 1, 2, 3, 6, 9 | the in-frame frames; other crops exclude these accessories |
| `PHOTOGRAPHY_STYLE` | 1-9 (all) | style is global by design (Rule 6); changing it requires regenerating every frame |
| `SKIN_TONE` / `EYE_COLOR` / `FACE_SHAPE` | 1-9 (all) | identity-locking variables; affect every frame |
| `BACKGROUND_COLOR` | 1-9 (all) | studio backdrop is shared across the series |
| `ASPECT_RATIO` | 1-9 (all) | canvas-level change |

## Hard Constraints — The 8 Rules

These rules are MUST-level. Identity / hairstyle / crop integrity cannot be recovered downstream — if any rule fails, regenerate the affected image(s).

### Rule 1 — Reference Image Mandatory (Identity)

```
RULE_001: Reference image is mandatory
- Every image-generation call MUST pass REFERENCE_IMAGE as the image input
- Violation: using text description only, without the reference image
- Consequence: identity consistency cannot be guaranteed; task fails
```

**Why** — pure text descriptions cannot transmit the high-dimensional facial features (micro-expression / bone structure / skin texture) that make the 9 frames look like the same person. The reference image is the image-generation model's image-to-image anchor; the text prompt only controls composition / pose / style.

Every prompt also carries the `[Reference image: {REFERENCE_IMAGE}]` header.

### Rule 2 — Analyse Before Generate (Workflow)

```
RULE_002: Analyse before generate
- All 14 variables MUST be extracted before any prompt template is filled
- Forbidden: guessing variable values, using silent defaults, skipping analysis
- Validation: confirm a complete variable-extraction output exists
```

### Rule 3 — Hairstyle Structure Intact (Hair)

```
RULE_003: No reinterpretation of hairstyle structure
- If the reference shows a tied/bunned hairstyle, every angle must keep that structure
- Forbidden: rendering a structured hairstyle as loose hair
- Required prompt constraints:
  - MUST include "{HAIRSTYLE} intact"
  - MUST include "NO loose hair"
  - MUST include "NO reinterpretation"
- Validation views: Image 4 (back) and Image 8 (side)
```

**CRITICAL** — Image 4 (back view) and Image 8 (side profile) exist *specifically* to verify that the hairstyle structure survives a 180° / 90° rotation. If the model renders a tied hairstyle as loose hair on these two frames, the entire 9-image set is invalid.

The hairstyle is visible in images 1, 2, 3, 4, 6, 7, 8, 9; each of those prompts carries "{HAIRSTYLE} intact" and "NO loose hair"; image 4 and image 8 additionally carry "NO reinterpretation".

### Rule 4 — Accessory Fidelity (Accessories)

```
RULE_004: Accessory add/remove constraint
- IF reference has an accessory AND the crop reveals it → MUST keep
- IF reference has no accessory → MUST NOT add
- Special case: accessories outside the crop may be omitted; annotate "where possible" in the prompt
```

For Image 5 (extreme facial close-up), accessories are physically out of frame — the prompt MUST state `No accessories — frame doesn't reach them` so the model does not hallucinate jewellery that contradicts the reference.

### Rule 5 — Hard Crop Boundaries (Crop)

```
RULE_005: Hard crop boundaries
- "crop at mid-thigh" = frame must end above the knees
- "crop at chest" = no abdomen visible
- "crop at hip line" = no thighs visible
- Violation: any body part extends past the crop boundary
- Example negative constraint: "No knees, lower legs, or feet"
```

Crop is enforced via explicit *negative constraints* in each prompt (e.g., `No knees, lower legs, or feet`). See the Task Prompts below for the per-image crop boundary and the matching negative-constraint phrase.

| Image | Upper bound | Lower bound | Forbidden |
|---|---|---|---|
| 1 | top of head | mid-thigh | knees, lower legs, feet |
| 2 | top of head | upper thigh | knees, lower legs |
| 3 | top of head | upper chest | abdomen, waist |
| 4 | top of head | hip line | thighs |
| 5 | (eyes/nose/lips only) | (eyes/nose/lips only) | forehead, chin, neck, shoulders, head outline |
| 6 | top of head | upper chest | abdomen and below |
| 7 | top of head | upper waist | (only upper-body clothing visible) |
| 8 | top of head | below chest | (strict chest crop) |
| 9 | top of head | mid-thigh | knees and below |

### Rule 6 — Global Style Unity (Style)

```
RULE_006: Global style unity
- All 9 images MUST apply the same {PHOTOGRAPHY_STYLE}
- Forbidden: some images cleaner / more digital / higher-contrast than others
- Validation: confirm every prompt contains the full style description
```

Each of the 9 prompts repeats the full chosen `{PHOTOGRAPHY_STYLE}` block verbatim. Do **not** abbreviate or reference it — repetition is what keeps the model's style budget aligned across calls.

### Rule 7 — User Override Re-render (Override)

The user may override any extracted variable. Re-render only the images affected by that variable — see Variable Override Logic above for the full mapping (HAIRSTYLE → all 9, OUTFIT → 1/2/3/4/6/7/8/9, BAG/JEWELRY → 1/2/3/6/9, PHOTOGRAPHY_STYLE → all 9). Keep already-correct images unchanged.

### Rule 8 — Single-Batch Generation (Batch)

```
RULE_008: Single-batch generation preferred
- Default: generate all 9 images in one call
- Exception: the user explicitly asks for stepwise review
- Reason: avoid model-state drift across separate calls
```

Multiple generation calls drift in style / lighting / colour temperature even with identical prompts. Single-batch generation locks the random-seed neighbourhood so the 9 frames inherit a shared visual signature.

### Why These Are MUST-level

- **Reference image absent** → identity is untraceable; the 9 frames look like 9 different people. Task fails.
- **Variable extraction skipped** → silent defaults (e.g. "long hair") lose the structural detail (low ponytail, no flyaways) that prompts need; outputs become generic.
- **Hairstyle reinterpretation** → tied hair becomes loose; the validation views (Image 4 / Image 8) flag it but only after rendering.
- **Accessory mismatch** → reference's silver chain becomes a gold pendant in Image 1, vanishes in Image 3; series is incoherent.
- **Crop boundary breach** → e-commerce / lookbook standards reject the asset (knees in a "mid-thigh" frame is an immediate fail).
- **Style drift** → some frames look filmic, others look CGI-clean → set is unusable as a single shoot.
- **Re-render of unaffected images** → wastes generation budget and risks introducing fresh drift on already-correct frames.
- **Multi-call generation** → state-difference contamination; a single batch avoids it.

### Self-check after rendering

Critical checks (subset of RULE_003 / RULE_005 / RULE_006):

- Image 4 (back view) — hairstyle structure visible from behind, no loose hair
- Image 8 (side profile) — hairstyle structure visible from side, no loose hair
- Image 5 (extreme close-up) — only eyes/nose/lips visible, no forehead/chin/shoulders
- All 9 — same {PHOTOGRAPHY_STYLE} signature (lighting / shadow direction / grain)

If any check fails, regenerate the affected image(s).

## Section 2 — Photography Style Presets

3 standardised photography styles, each a long-form `{PHOTOGRAPHY_STYLE}` block that is **repeated verbatim into every one of the 9 task prompts**. The presets cover three commercially distinct lighting moods (retro analog flash / soft muted film / hard flash editorial).

When the user has not specified a style and has not uploaded a style reference, offer: Use Preset A — Retro Analog Flash / Use Preset B — Soft Muted Film / Use Preset C — Hard Flash Editorial / I'll describe my own style / I'll upload a style reference image. Wait for the user's choice; do NOT auto-pick a default. The chosen preset block is used in full.

### Preset A — Retro Analog Flash

[translated from Chinese]

**Applicable scenarios**: retro fashion, streetwear brands, Y2K style

#### Light source configuration

```
Main light source:
  Type: on-camera direct flash
  Color temperature: 5500K (slightly cool)
  Power: medium-high (simulating the overexposure tendency of old-style flash)

Fill light:
  Type: ambient reflected light (slight)
  Role: lift shadows, avoid pure black

Flash characteristics:
  - Highlight blow-out areas: forehead / nose bridge / cheekbones
  - Catchlights: small and direct, not ring-shaped
```

#### Shadow specification

```
Cast shadow characteristics:
  Direction: single direction (consistent with the flash)
  Edge: sharp but softened
  Density: light (subject close to the backdrop)

Facial shadows:
  Visibility: visible
  Degree of lift: moderate (avoid dead black)
  Contrast: low (retro film characteristic)
```

#### Post-processing effects

```
Film simulation:
  Grain: fine, ISO 400-800 equivalent
  Vignetting: slight, natural fall-off in the four corners
  Color cast: slight warm or cool drift

Texture constraints:
  - Forbidden: CGI feel, over-sharpening, digital cleanliness
  - Preserve: skin pores, fabric texture, backdrop imperfections
```

#### Negative constraints (must not appear)

```
- Multi-directional shadows (indicates multiple light sources)
- Pure black shadows (inconsistent with film latitude)
- Overly crisp digital feel
- Ring-shaped catchlights (indicates a ring light was used)
```

### Preset B — Soft Muted Film

[translated from Chinese]

**Applicable scenarios**: high-end fashion, minimalist brands, art photography

#### Light source configuration

```
Main light source:
  Type: large softbox (120cm+)
  Position: front, raised 45°
  Degree of diffusion: extremely high

Ambient light:
  Intensity: high (significant ambient fill)
  Role: compress dynamic range, eliminate hard shadows
```

#### Color specification

```
Background color:
  Standard value: #f1eee9 (light cream)
  Tolerance: ±5% lightness/saturation

Skin tone treatment:
  Base: neutral warm beige-grey
  Relationship to background: tonal blending, no strong separation
  Saturation: reduced 15-25%

Overall tonality:
  Characteristic: high-key
  Dynamic range: compressed (no deep blacks / pure whites)
```

#### Material specification

```
Surface treatment:
  Reflection type: fully diffuse reflection
  Specular highlights: forbidden (all materials rendered matte)

Visual effect:
  Texture: flat, painterly
  Film grain: evenly distributed across the whole frame
```

#### Mood positioning

```
Atmosphere: emotionally detached, calm, artistic
Lighting characteristic: extremely even, no drama
```

### Preset C — Hard Flash Editorial

[translated from Chinese]

**Applicable scenarios**: fashion magazines, high-end e-commerce, where visual impact is required

#### Light source configuration

```
Main light source:
  Type: strongly directional hard light (bare bulb or narrow reflector)
  Directionality: extremely strong
  Contrast: high

Key constraints:
  - Highlight/shadow boundaries must be sharp
  - Shadow areas must retain color information (pure black forbidden)
```

#### Shadow technical specification (core)

```
Shadow transparency:
  Requirement: must be transparent (luminous)
  Color information: retain a warm-toned base (deep brown / red-brown)
  Detail retention: texture still visible in shadow areas

Ambient reflection:
  Role: fill shadows, prevent loss of information
  Intensity: moderate (does not break the hard-light character)

Forbidden states:
  - Pure black shadows (crushed blacks)
  - Muddy tonality
  - Loss of shadow detail
```

#### Skin texture specification

```
Surface characteristics:
  Oily sheen: pronounced (simulating sweat / oil)
  Pores: visible in high definition (in both lit and shadow areas)

Color contrast:
  Shadow areas: deep brown tones
  Lit areas: saturation lifted
  Local flush: cheeks / tip of nose show blood color (sun-flushed)

Highlight treatment:
  Density: high (multiple highlight points)
  Texture: wet, slightly overexposed
  Distribution: forehead / nose bridge / cheekbones / chin
```

#### Dynamic range

```
Latitude: film-like latitude (retain highlight and shadow detail)
Exposure tendency: high-key but with contrast retained
```

## Section 4 — Task Prompts — The 9 Images

The 9 image templates that compose the Model Consistency Series. Each carries:

- **Lens / camera spec** — focal length, depth-of-field, aspect ratio.
- **Crop spec** — upper/lower bounds with explicit forbidden body parts.
- **Pose spec** — body / hand / head / gaze rules.
- **Hairstyle / accessory spec** — what to assert verbatim (`{HAIRSTYLE} intact`, `NO loose hair`).
- **Prompt template** — the full English text with `{VARIABLE}` placeholders.

> **CRITICAL** — Image 4 (back view) and Image 8 (side profile) are the dedicated **hairstyle-structure validation views**. Their prompts MUST include `NO loose hair, NO reinterpretation`. If either fails, the whole 9-image set is invalid (see Rule 3).

Mandatory invariants per prompt:

- `[Reference image: {REFERENCE_IMAGE}]` header present
- `{PHOTOGRAPHY_STYLE}` block repeated VERBATIM
- hairstyle-visible images carry "{HAIRSTYLE} intact" + "NO loose hair"
- image 4 + image 8 additionally carry "NO reinterpretation"
- image 5 carries "No accessories — frame doesn't reach them"

Only Image 1 carries a full prompt template in the source. Images 2 to 9 are specified by their spec blocks, which were written in Chinese in the source and are translated below.

### Image 1 — Three-Quarter Fashion Portrait

**Purpose**: Editorial anchor shot (the lead frame of the series).

#### Specs

[translated from Chinese]

```
Lens: 85mm prime
Focal length equivalent: medium-telephoto portrait lens
Depth of field: medium (f/2.8-f/5.6)
Frame: {ASPECT_RATIO} vertical composition

Crop specification
Upper bound: headroom above the top of the head 5-10% of frame height
Lower bound: mid-thigh (15-20cm above the knee)
Crop type: hard truncation
Must not appear: knees, lower legs, feet

Pose specification
Stance:
  Weight: shifted to one side (asymmetric)
  Torso: slightly rotated (not parallel to the camera)

Hands:
  Position: behind the back
  State: asymmetric (one bent, one extended)

Head:
  Direction: looking straight into the camera
  Expression: distant and calm

Hairstyle constraint:
  State: {HAIRSTYLE} kept fully intact
  Mandatory constraint: "NO loose hair"
```

#### Prompt Template (verbatim)

```
[Reference image: {REFERENCE_IMAGE}]

{SUBJECT_DESCRIPTION} — {HAIR_COLOR} hair in {HAIRSTYLE}, {SKIN_TONE}, wearing {OUTFIT}. Accessories: {BAG} over shoulder, {JEWELRY}.

85mm prime lens, {ASPECT_RATIO} vertical. Framed top of head to mid-thigh — hard truncation through thighs. No knees, lower legs, or feet.
Stable upright posture, weight shifted to one side. Torso rotated left for asymmetric silhouette. Hands behind back, asymmetric — one bent, one extended.
Direct eye contact, distant calm expression. {HAIRSTYLE} intact — NO loose hair.

{PHOTOGRAPHY_STYLE}
Studio backdrop: {BACKGROUND_COLOR}. No added accessories beyond reference.
```

### Image 2 — High-Angle Bird's-Eye View

#### Specs

[translated from Chinese]

```
Lens: 35mm wide-angle
Viewing angle: high angle 60-75°
Perspective: wide-angle distortion (foreshortening)

Shooting angle specification
Camera position:
  Height: 1.5-2m above the subject
  Horizontal offset: offset to the upper right

Light source alignment:
  Flash: on-axis with the camera
  Shadow direction: single direction (multi-directional shadows forbidden)

Pose constraints
Body state:
  Pose: standing (lying flat forbidden)
  Verification method: check the direction of gravity (clothing should drape downward)

Hands:
  Position: on hips
  State: relaxed, asymmetric

Crop specification
Lower bound: upper thigh
Crop type: hard truncation
Composition: off-centered

Negative constraints
Forbidden:
  - Horizontal lying pose (body parallel to the ground)
  - Multi-directional shadows (indicates multiple light sources)
  - Dead-center composition
```

### Image 3 — Over-the-Shoulder Close-Up

#### Specs

[translated from Chinese]

```
Lens: 85mm portrait prime
Depth of field: shallow (f/1.8-f/2.8)
Focus: eyes

Crop specification
Upper bound: top of head
Lower bound: upper chest (strict chest crop)
Must not appear: abdomen, waist

Pose specification
Body direction: back to the camera (showing back/shoulders)
Head movement: sharp turn to the right, looking at the camera over the shoulder
Degree of head turn: large angle (close to 90°)

Expression: calm and resolute
Hair detail: a few strands brushing across the face are allowed
Hairstyle constraint: {HAIRSTYLE} structure intact — NO loose hair
```

### Image 4 — Back View with Hairstyle Visible

**Purpose (CRITICAL)**: [translated from Chinese] Validation composition — dedicated to checking the consistency of the hairstyle structure from the back view.

#### Specs

[translated from Chinese]

```
Lens: 85mm prime
Frame: {ASPECT_RATIO} vertical composition

Crop specification
Upper bound: top of head
Lower bound: hip line
Crop type: strict hip-line crop
Must not appear: thighs

Pose specification
Body direction: fully back to the camera (180° rear view)
Stance: upright
Arms: hanging naturally at both sides of the body
```

#### Key constraints (CRITICAL)

[translated from Chinese]

```
Hairstyle validation:
  Requirement: {HAIRSTYLE} must be clearly visible and structurally intact from the back
  Forbidden: loose hair, reinterpretation of the hairstyle structure
  Mandatory prompt constraint: "NO loose hair, NO reinterpretation"
```

### Image 5 — Extreme Facial Close-Up

#### Specs

[translated from Chinese]

```
Lens: 105mm+ macro lens
Depth of field: extremely shallow (f/1.4-f/2.0)
Focus: eyes

Crop specification (extreme)
Included area: eyes / nose / lips only
Cropped out: forehead, chin, head outline, shoulders, neck
Crop type: ultra-tight close-up

Composition specification
Symmetry: off-center (off-center editorial asymmetry)
Gaze: looking straight into the camera
Expression: neutral and calm

Detail requirements
Skin texture:
  Clarity: highly detailed
  Visible elements: pores, fine lines, eyelashes, moles, freckles

Hair strand treatment:
  Allowed: a few {HAIR_COLOR} strands may appear at the edge of the frame
  Forbidden: showing the full hairstyle outline

Accessory constraint
Accessories shown: none
Reason: the frame does not reach the position of the accessories
Prompt note: "No accessories — frame doesn't reach them"
```

### Image 6 — Over-Right-Shoulder Glance

#### Specs

[translated from Chinese]

```
Lens: 85mm portrait prime
Frame: {ASPECT_RATIO} vertical composition

Crop specification
Upper bound: top of head
Lower bound: upper chest
Must not appear: abdomen and below

Pose specification
Body direction: turned to the right
Chest twist: slightly to the left
Hands: behind the back

Head movement: glancing back over the right shoulder
Gaze characteristics: soft, not direct, slightly out of focus (candid feel)

Mood positioning
Atmosphere: soft candid feel
Expression: calm and introspective
Hairstyle: {HAIRSTYLE} intact
```

### Image 7 — Low-Angle Upward Gaze, Contrapposto

#### Specs

[translated from Chinese]

```
Lens: 100mm portrait prime
Camera height: hip level
Shooting direction: tilted upward

Crop specification
Upper bound: top of head
Lower bound: upper waist
Visible clothing: upper-body garments only

Pose specification (Contrapposto)
Definition: counterpoised stance (classical sculpture pose)
Technical requirements:
  - Weight shifted to one side
  - Body forms a natural S-curve
  - Shoulders and hips in opposing twist

Hands: bent, both hands on hips
Head: tilted back, chin raised, neck elongated
Gaze: soft, upward

Negative constraints
Forbidden:
  - Excessive eye whites
  - Exaggerated gaze
```

### Image 8 — Side Profile, Chest Crop

**Purpose (CRITICAL)**: [translated from Chinese] Validation composition — checks the consistency of the hairstyle structure from the side view.

#### Specs

[translated from Chinese]

```
Lens: 85mm portrait prime
Frame: {ASPECT_RATIO} vertical composition

Crop specification
Upper bound: top of head
Lower bound: below the chest (strict chest crop)

Pose specification
Body direction: full profile (90°, right side facing the camera)
Stance: upright, chin slightly raised
Gaze: level, straight ahead (not at the camera)
```

#### Key constraints (CRITICAL)

[translated from Chinese]

```
Hairstyle validation:
  Requirement: {HAIRSTYLE} must be clearly visible from the side
  Forbidden: loose hair, reinterpretation
  Prompt constraint: "no loose hair, no reinterpretation"

Accessories shown:
  Scope: only the {JEWELRY} visible on the right side
```

### Image 9 — Medium Portrait, Opposing Torso Twist

#### Specs

[translated from Chinese]

```
Lens: 85mm portrait prime
Frame: {ASPECT_RATIO} vertical composition

Crop specification
Upper bound: top of head
Lower bound: mid-thigh
Must not appear: knees and below

Pose specification (opposing twist)
Pelvis rotation: about 20° to the right
Chest rotation: about 30° to the left
Effect: natural opposing twist

Hands:
  Left arm: hanging naturally
  Right hand: placed on the waist/hip

Stance: relaxed contrapposto
Head: slightly raised
Gaze: looking straight into the camera
Expression: relaxed and confident

Hairstyle: {HAIRSTYLE} intact

Negative constraints
Forbidden:
  - Stiff posture
  - Symmetrical stance
```
