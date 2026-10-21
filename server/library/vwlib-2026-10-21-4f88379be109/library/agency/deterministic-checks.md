# Deterministic prompt checks

Provenance
- Source repository: https://github.com/kwistzzqq-byte/image2-ads-studio
- Commit: f055a79c0840a6a193060d2d84b8a957fc0bbc80 (2026-05-05)
- Licence: Apache-2.0 (copy at `_sources/LICENSE-kwistzzqq-byte-image2-ads-studio.txt`)
- Source files: `packages/ad-image-agent-core/src/deterministic-prompt.ts`, `packages/ad-image-agent-core/src/compiler.ts`, `packages/ad-image-agent-core/src/planner.ts`, `packages/ad-image-agent-core/src/templates.json`, `apps/ad-image-agent/server/llm-server.mjs`, `docs/template-authoring.md`
- Date copied: 2026-10-19
- Literal strings are extracted from TypeScript and JSON into tables. English strings are verbatim. One block is translated from Chinese and marked as such. The checks are keyword presence tests (regular expressions); treat them as a checklist, not a quality gate.

## 1. Banned vague phrases with fixed replacements

`STYLE_REWRITE_RULES` and `ENGLISH_REPLACEMENTS` in `deterministic-prompt.ts`. Any text in the user request, style direction, hard constraints, design plan and final prompt is rewritten with these rules before validation; any remaining match fails the `bannedPhrasesRemoved` check.

### 1a. English patterns (pattern and replacement both verbatim)

| Banned pattern (regex alternatives, case-insensitive) | Replacement |
| --- | --- |
| `Apple style` / `similar to Apple` / `Apple-like` | light gray or pure white background, centered product, soft shadow, minimal text, crisp edges, realistic material |
| `premium style` / `luxury style` / `high-end feel` | low-saturation main color, 25% negative space, thin dividers, rim light on subject edges, clear surface material, no cluttered decoration |
| `Instagram style` / `ins style` | natural light, light background, centered subject, soft shadow, a few lifestyle props |
| `cinematic style` / `cinematic look` | warm-cool contrast lighting, foreground-midground-background depth, low-key tonal layers, atmospheric depth, subject rim light |

### 1b. Patterns that exist only in Chinese in the source; replacement text is the source's own English equivalent (verbatim)

| Banned pattern (meaning, translated from Chinese) | Replacement |
| --- | --- |
| "like Apple style", "Apple style" | light gray or pure white background, centered product, soft shadow, minimal text, crisp edges, realistic material |
| "premium feel", "premium-feel style" | low-saturation main color, 25% negative space, thin dividers, rim light on subject edges, clear surface material, no cluttered decoration |
| "influencer style" | bright background, natural light, photo-friendly focal area, centered subject, a few lifestyle props, concise text area |
| "ins style" | natural light, light background, centered subject, soft shadow, a few lifestyle props |
| "big-brand feel" | minimal background, large subject scale, single dominant color, precise negative space, detailed highlights, no extra decoration |
| "cinematic feel" | warm-cool contrast lighting, foreground-midground-background depth, low-key tonal layers, atmospheric depth, subject rim light |
| "commercial studio-shoot style", "studio-shoot style" | neutral background, soft key light, realistic shadow, clear product material, crisp edge silhouette |
| "similar to X" (up to 18 characters) | use explicit composition, material, lighting, color, and typography hierarchy |
| "like X" (up to 18 characters) | use explicit composition, material, lighting, color, and typography hierarchy |
| "reference X style" | extract only the reference image composition, material, lighting, color, and typography hierarchy |
| "X style" (any 1 to 12 character word followed by the Chinese word for style) | explicit composition, material, lighting, color, and typography hierarchy |

## 2. Presence checks

`CHECK_PATTERNS` in `deterministic-prompt.ts`. A final prompt passes a check when it contains at least one of the listed terms (case-insensitive). The source regexes also contain Chinese terms; only the English terms are listed.

| Check | Matches any of |
| --- | --- |
| `compositionSpecified` | composition, subject, center, left, right, foreground, midground, background, negative space, layout, hero, copy area, text area, section |
| `lightingSpecified` | lighting, natural light, soft light, key light, fill light, rim light, highlight, shadow, reflection, backlight, light source |
| `typographySpecified` | typography, text, copy, headline, font, type, readable, information area, selling point |
| `materialsSpecified` | material, acrylic, metal, wood, glass, stone, concrete, fabric, paper, plastic, reflective, surface, texture |
| `imageReferencePolicySpecified` | reference image, uploaded image, preserve, do not change, structure, subject, perspective, door, window, boundary, upstream, do not copy, no reference image |

Sixth check: `bannedPhrasesRemoved` is true when no pattern from section 1 matches.

`DeterministicChecks` fields, in order: `bannedPhrasesRemoved`, `compositionSpecified`, `lightingSpecified`, `typographySpecified`, `materialsSpecified`, `imageReferencePolicySpecified`.

`DeterministicValidationResult`: `checks`, `bannedPhrases` (the matched strings), `missingRequirements` (names of failed checks), `passed` (true only when `missingRequirements` is empty).

## 3. Deterministic execution requirements

`formatDeterministicRequirements("en")`, verbatim. This block is appended to every compiled prompt and to the rewrite instructions.

- Do not use vague analogy terms, social-media labels, brand-style labels, or cinematic catch-all labels.
- If the user input contains vague style wording, rewrite it as explicit composition, material, lighting, color, typography hierarchy, and preserve/edit rules.
- Specify subject placement, image sections, light direction, main materials, text areas, and reference-image handling.
- For image edits, clearly state what to preserve: structure, subject, perspective, door/window/wall boundaries, or product identity; when there is no reference image, state that no reference image is used.

The rewrite step's developer prompt restates it (`llm-server.mjs`, English variant, verbatim):

- finalPrompt must be deterministic and executable. Do not use vague analogy terms, brand-style labels, social-media labels, or cinematic catch-all labels.
- If user input contains vague wording, rewrite it into explicit composition, materials, lighting, color, typography hierarchy, and preserve/edit rules.
- finalPrompt must specify subject placement, image sections, light direction, main materials, text area, and reference-image handling.

## 4. Repair-once rule

From `handleLlmPrompt` in `llm-server.mjs`.

1. The rewritten final prompt is passed through the style rewrite (section 1) and then validated (section 2).
2. If validation fails, the rewrite is requested a second time with `repairInstructions` carrying `previousFinalPrompt`, `bannedPhrases` and `missingRequirements`, and this task sentence (verbatim): The previous output failed deterministic validation. Remove banned wording, fill missing requirements, and return only corrected strict JSON.
3. If the second result still fails, the request stops with status 422 and the message (verbatim): LLM prompt failed deterministic validation after one repair attempt.

There is no third attempt.

## 5. No-invention rule

The rule appears in several verbatim forms. All are kept because they attach to different stages.

| Where | Sentence |
| --- | --- |
| Generation requirements, shared line (`compiler.ts`) | Any visible text must be clear, accurate, and readable; do not invent prices, dates, phone numbers, addresses, or promises the user did not provide. |
| Structured brief, no copy supplied (`compiler.ts`) | Copy requirement: if no exact copy is provided, reserve clean text areas and do not invent prices, dates, phone numbers, addresses, or brand promises. |
| Design plan, no copy supplied (`planner.ts`) | If the user did not provide exact copy, reserve clear text areas and do not invent prices, dates, or brand promises. |
| Developer prompt (`llm-server.mjs`) | Preserve the exact copy provided by the user. Do not invent prices, dates, brand promises, phone numbers, or addresses. |
| Product advertisement requirement (`compiler.ts`) | Do not invent product efficacy, qualifications, price, or certification. |
| Writing rules (`docs/template-authoring.md`) | Remove concrete brands, prices, people, dates, and unique slogans. |
| Risk warnings field description (`llm-server.mjs`) | Risk warnings in English, such as text accuracy, uploaded-image preservation, and non-invention rules. |

## 6. Generation requirements per task type

`generationRequirements` in `compiler.ts`, English branch, verbatim. The three shared lines precede the two task-specific lines in every compiled prompt.

Shared:

- The image must look like a real advertising production deliverable, not pure concept art.
- Any visible text must be clear, accurate, and readable; do not invent prices, dates, phone numbers, addresses, or promises the user did not provide.
- Structure, materials, lighting, and proportions must follow realistic production or commercial-placement logic.

| Task type | Requirement lines |
| --- | --- |
| `storefront_signboard` | Signboard, wall, doors, windows, lighting, and materials must fit a plausible storefront. / For image edits, preserve the uploaded structure, perspective, and subject placement. |
| `poster_design` | Include a clear headline, key visual, selling-point area, and supporting-information area. / Typography must have a readable commercial hierarchy. |
| `rollup_banner` | Use a vertical composition suitable for a display stand, with clear headline, selling points, and contact/action area. / Keep the bottom section readable and reserve space for a QR/action area when needed. |
| `event_backdrop` | The backdrop must work for onsite photos, stage viewing, or booth viewing; keep the main title unobstructed. / Large background areas should stay clean and avoid tiny unprintable details. |
| `signage_wayfinding` | Arrows, floor/area/function information must be directionally clear and easy to read. / Sign scale, mounting position, and spatial perspective must feel real. |
| `brand_wall` | Logo, brand name, and wall material must fit the interior space. / Wall mockups must preserve wall boundaries, perspective, and installation logic. |
| `local_store_promotion` | Promotion information must prioritize local-store conversion, with headline and benefit points first. / Store, product, or service subject must not be blocked by decoration. |
| `ecommerce_main_image` | Product subject must be clear, large enough, and platform-ready. / Do not alter product appearance, package shape, label, or key identity. |
| `product_ad` | Product hero, selling-point area, and brand atmosphere must form a complete ad image. / Do not invent product efficacy, qualifications, price, or certification. |
| `commercial_photography` | Prioritize realistic photography quality, light, material, and credible scene staging. / Do not add text unless the user explicitly provides copy. |

## 7. Manufacturability rules for built signage

English sources, verbatim:

- `docs/template-authoring.md`: For storefront, signage, and brand-wall tasks, emphasize manufacturable structure and realistic installation.
- `planner.ts`, default hard constraint: Avoid off-brief output, messy text, missing subject, and impossible production structures.
- `compiler.ts`, shared generation requirement: Structure, materials, lighting, and proportions must follow realistic production or commercial-placement logic.
- `compiler.ts`, task lines for `storefront_signboard`, `rollup_banner`, `event_backdrop`, `signage_wayfinding` and `brand_wall` (section 6).

The detailed build-logic negatives live only in Chinese, in the `negativeConstraints` field of `templates.json`. The distinct sets for the five built deliverables follow; the count is the number of templates carrying that set at this commit. These are appended to the compiled prompt's Avoid list when the template matches.

[translated from Chinese]

Storefront signboard (set of 18 templates)
- Do not change the on-site door and window structure or the building perspective
- Do not invent phone numbers, addresses, prices or qualifications
- Signboard material, size and mounting method must be real and manufacturable

Storefront signboard (set of 12)
- Do not generate floating structures that cannot be built
- Do not add unrelated brand text
- Do not make the signboard text unreadable

Storefront signboard (set of 10)
- Do not generate floating structures that cannot be built
- Do not add unrelated brand text
- Do not change the door and window proportions of the user's uploaded storefront
- Do not make the signboard text unreadable

Roll-up banner / display stand (set of 12)
- Vertical information must not be crowded
- Do not invent contact details or QR codes
- The bottom action area must keep a safe margin

Roll-up banner / display stand (set of 10)
- Do not turn the display stand into an ordinary landscape poster
- Do not omit the bottom stand structure
- Do not invent contact details
- Do not let the long-distance reading hierarchy become confused

Roll-up banner / display stand (set of 8)
- Do not pile information too densely
- Do not let the contact-details and QR-code area blur
- Do not change the brand or course name the user provided

Event backdrop (set of 12)
- The backdrop main title must not be blocked by people or stage equipment
- Do not use too much small text
- Printed-vinyl, truss or screen proportions must be reasonable

Event backdrop (set of 10)
- Do not generate stage structures that cannot be built
- Do not let the main title be blocked by people or lighting
- Do not invent the organiser's name
- Do not turn the backdrop into a small poster

Event backdrop (set of 8)
- Do not let the main title be blocked by people or decoration
- Do not generate large areas of complex detail that cannot be produced
- Do not omit the event name the user provided

Signage and wayfinding (set of 12)
- Arrow directions and area names must be clear
- Do not invent floor or area numbers
- Mounting position, scale and viewing distance must be real

Signage and wayfinding (set of 10)
- Do not generate arrows pointing the wrong way
- Do not invent floor and room numbers
- Do not make the wayfinding text too small
- Do not use complex irregular structures that cannot be built

Signage and wayfinding (set of 8)
- Do not generate arrows that point the wrong way or are unreadable
- Do not use complex irregular structures that cannot be manufactured
- Do not let the sign detach from the spatial perspective

Brand wall / wall mockup (set of 12)
- Do not change wall boundaries, sockets, door openings or the on-site perspective
- Logo and brand text must be clear
- Material, light strips and mounting thickness must be reasonable

Brand wall / wall mockup (set of 10)
- Do not change the perspective and boundaries of the uploaded wall
- Do not make the logo or company name unreadable
- Do not generate floating signs that cannot be installed
- Do not invent honours or qualifications

Brand wall / wall mockup (set of 8)
- Do not change the perspective and wall boundaries of the uploaded space
- Do not let the logo or brand lettering deform
- Do not generate floating structures that cannot be installed

## 8. Compiled prompt section order

`compilePrompt` in `compiler.ts`, English branch. Fixed lines verbatim; `${...}` marks a brief field.

1. Generate one commercially usable advertising image from the following production brief.
2. **User Brief**: the user request after vague-phrase rewriting, or when empty: Create an advertising image from the structured form fields.
3. **Structured Brief**: `Task type: ${label}` / `Input mode: ` image edit with uploaded image | text-to-image / `Industry: ${industry}` / `Aspect ratio: ${aspectRatio}` / `Visual execution direction: ${styleDirection}` / `Reference image policy: ${role label}` / `Required exact copy: ${copywriting}` or the no-copy sentence from section 5.
4. **Design Plan**: the design plan (see `advertising-brief-schema.md`).
5. **Matched Business Template Directions**: one line per matched template: `- ${id} / ${name}: use this matched business scenario as internal guidance for deliverable type, copy policy, production constraints, and advertising hierarchy.` or when none: - Use a general advertising layout with a clear subject, readable information hierarchy, and production-ready delivery.
6. **Visual Recipes**: per matched recipe: `- ${id} / ${name}` / `  Source structure: ${repo} ${caseId}; rewritten as a reusable debranded visual recipe.` / `  Apply its layout, subject, scene, lighting, typography, and detail formulas as internal visual guidance.` / `  Do not copy any upstream brand, exact text, person identity, price, or distinctive protected detail.` or when none: - Use clear commercial photography or graphic-design logic. Specify subject placement, scene, lighting, text area, and detail constraints.
7. **Generation Requirements**: section 6.
8. **Deterministic Execution Requirements**: section 3.
9. **Avoid**: the de-duplicated union of all matched templates' and recipes' `negativeConstraints`, followed by the brief's hard constraints, one `- ` line each.

The whole compiled prompt is passed through the style rewrite (section 1) once more, and `buildDeterministicChecks` is run on the result.

A plain (non-compiled) prompt, `buildPlainPrompt`, is: the user request (or: Generate one advertising image based on my requirements.) / `Required copy: ${copywriting}` / `Industry: ${industry}` / `Aspect ratio: ${aspectRatio}` / `Visual execution: ${styleDirection}` / for image edits: `Use my uploaded image. Reference image role: ${role label}.`
