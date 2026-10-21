# GPT Image 2.5 fact sheet: Sunburst and Flare

Status: written 2026-10-19 from OpenAI's own pages. Part A and Part B facts marked `[verified: page, date]` were read on the named page that day. Lines marked `[third-party]` come from other users' notes in this folder and are not confirmed by OpenAI. Part C is empty until jobs run.

Pages used, short names:
- G = https://developers.openai.com/api/docs/guides/image-generation
- P = https://developers.openai.com/api/docs/guides/image-prompting
- R = https://developers.openai.com/api/docs/api-reference/images/createEdit
- $ = https://developers.openai.com/api/docs/pricing

This is the most preferred image model family. Decision in `models/CHOSEN-MODELS.md`.

---

## Part A. The API: what the application sends

### A1. Models

| Model id | Use it for | Source |
| --- | --- | --- |
| `gpt-image-2.5-sunburst` | "workflows where editing precision matters most". Our photo fixing, product retouch, anything where a face, product or label must not move. Default model on the edit endpoint. | [verified: G and R, 2026-10-19] |
| `gpt-image-2.5-flare` | "fast, high-quality everyday image generation". Drafts, bulk variants, everyday posts. | [verified: G, 2026-10-19] |

Dated snapshots exist: `gpt-image-2.5-sunburst-2026-09-08`, `gpt-image-2.5-flare-2026-09-08`. Pin a snapshot in production so a silent update does not change results. [verified: R, 2026-10-19]

Same token prices for both. Same prompt rules for both. Sunburst takes longer. [verified: $ and G, 2026-10-19]

Older models `gpt-image-2`, `gpt-image-1.5`, `gpt-image-1`, `gpt-image-1-mini` still exist. Do not use them for new work. [verified: G, 2026-10-19]

### A2. Two ways to call

| Route | When | Notes | Source |
| --- | --- | --- | --- |
| Image API: `POST /images/generations` for a new image, `POST /images/edits` for an edit with pictures attached | Our default. Claude writes the prompt, the application sends it as is. | The model does not rewrite the prompt. Output comes back as base64 (`b64_json`); a download link is not supported for GPT image models. | [verified: R, 2026-10-19] |
| Responses API with the `image_generation` tool | Only if a conversation-style loop is wanted | A mainline model sits in front and may rewrite the prompt; the rewrite appears in `revised_prompt`. Adds that model's token cost. Cached input discount applies only here. | [verified: G and $, 2026-10-19] |

Decision for this library: Image API. We want the prompt sent exactly as written, so the feedback log records what the model actually saw.

### A3. Settings on every call

| Setting | Allowed values | Default | Notes | Source |
| --- | --- | --- | --- | --- |
| `model` | see A1 | `gpt-image-2.5-sunburst` on edits | | [verified: R] |
| `prompt` | text | required | No length limit stated. | [verified: R] |
| `size` | `1024x1024`, `1536x1024`, `1024x1536`, `auto`, or any `WIDTHxHEIGHT` within A4 | `auto` listed as default for gpt-image-2; not stated for 2.5 | Always send an explicit size. `auto` lets the model pick and makes cost unpredictable. | [verified: G and R] |
| `quality` | `low`, `medium`, `high`, `xhigh`, `max`, `auto` | `auto` | `xhigh` and `max` exist only on the 2.5 family. Send an explicit value. | [verified: G and R] |
| `background` | `transparent`, `opaque`, `auto` | not stated | `transparent` needs `output_format` `png` or `webp`. | [verified: G and R] |
| `output_format` | `png`, `jpeg`, `webp` | `png` | `jpeg` is faster to return than `png`. | [verified: G] |
| `output_compression` | 0 to 100 | not stated | Only for `jpeg` and `webp`. Leave out for `png`. | [verified: G] |
| `n` | 1 to 10 on generations; no maximum stated on edits | 1 | | [verified: G and R] |
| `moderation` | `auto`, `low` | `auto` | `low` is less strict. Keep `auto` for client work. | [verified: G] |
| `stream`, `partial_images` | true/false; 0 to 3 | off | Streams partial images. Each partial costs about 100 extra output tokens. Not needed for our pipeline. | [verified: G and $] |
| `safety_identifier` | hashed id of the end user, 128 characters or fewer | none | Recommended when serving end users. Use a hash, never a name or email. Replaces the deprecated `user`. | [verified: G and R] |
| `input_fidelity` | do not send | | Older models only. 2.5 always reads input pictures at high fidelity. | [verified: G and R] |

### A4. Size rules

- Both sides multiples of 16. [verified: G, 2026-10-19]
- Aspect ratio between 1:3 and 3:1. Nothing wider or taller. A 4:1 banner is not possible here; that is a Nano Banana job. [verified: G]
- Neither edge above 3840 pixels. [verified: G]
- Total pixels between 655,360 and 8,294,400. [verified: G]
- Above 2560x1440 is marked experimental. [verified: G and R]
- Common sizes named by OpenAI: 1024x1024, 1536x1024, 1024x1536, 2048x2048, 2048x1152, 3840x2160, 2160x3840. Square is usually fastest. [verified: G]
- Our placements map as: 1:1 feed 1024x1024 or 2048x2048; 4:5 feed 1024x1280 or 1664x2080; 9:16 story 1080x1920 fails the multiple-of-16 rule, use 1088x1936 or 1152x2048 then resize; 16:9 hero 1536x864 or 1920x1080 fails the rule, use 1920x1088 or 2048x1152. Working values, to be checked against the channel sheet once it exists.

### A5. Pictures sent in with an edit

- Up to 16 input pictures for GPT image models. [verified: R, 2026-10-19]
- Each picture and the mask under 50 MB. [verified: G]
- Passed as uploaded files in the multipart form (`image[]`), or as objects with `file_id` or `image_url`. [verified: R]
- Order matters. The prompt says "Image 1", "Image 2"; the application must send them in that order.
- Mask: optional, one only, applied to the first picture. Must carry an alpha channel. Same size and format as the first picture. The mask is guidance; "may not follow its exact shape with complete precision". [verified: G]

### A6. Price

OpenAI publishes token rates for 2.5, not a per-image price. Cost per image depends on size and quality and must be read from the `usage` field of each response. [verified: $ and G, 2026-10-19]

| Rate, standard, per million tokens | Sunburst and Flare |
| --- | --- |
| Image output | $30.00 |
| Image input | $8.00 |
| Text input | $5.00 |
| Batch rates | half of the above |

[verified: $, 2026-10-19]

For scale: on the older `gpt-image-2`, OpenAI listed a 1024x1024 image at about $0.006 low, $0.053 medium, $0.211 high. Token use on 2.5 may differ. Treat as a rough guide only. [verified: G, 2026-10-19]

What the application must do: store `usage.output_tokens` and `usage.input_tokens` on every record so the feedback log can report real cost per usable image.

### A7. Limits, waits, errors

- A complex prompt can take "up to 2 minutes". Design the application to wait, not to time out at 30 seconds. [verified: G]
- Rate limits: not stated on the pages read. Check the organisation's limits page. [unverified]
- GPT image models may require API Organisation Verification. [verified: G]
- Errors: `error.type` `image_generation_user_error` means the prompt or inputs are the problem; do not retry unchanged. Rate-limit and server errors: retry with backoff. [verified: G]
- Blocked content returns `moderation_blocked` with `moderation_stage` (`input` or `output`) and coarse `categories` such as `sexual`, `violence`, `harassment`, `self-harm`. Input block: change the prompt or pictures. Output block: change the prompt. [verified: G]
- Real-person likeness edits often fail at the moderation layer; expect a refusal, not a degraded image. [third-party: `00-method/craft.md` section 18]

---

## Part B. How this model reads words

### B1. Prompt shape

For complex requests, OpenAI says to "organize the prompt as scene, subject, details, and constraints, using labeled sections". The format is otherwise free: a short line, a paragraph, a JSON-like block, tags. [verified: P, 2026-10-19]

House shape for this library, which follows that advice and matches our recipes:

```text
Asset: {what it is}. Target aspect ratio: {ratio}. Mode: {generate | edit}.
Scene: {place, time, background}
Subject: {the one thing the image is about}
Details: {materials, light direction and softness, camera feel, palette, layout, text area, margins}
Exact text: "{string 1}" {position, size, style}; "{string 2}" ... No other text.
References: Image 1 = {role}. Image 2 = {role}.
Constraints: {what must not change or appear}
Render only explicitly requested image text. Do not add unrelated logos, signatures or captions.
```

The fifth slot, constraints, is where drift is stopped. A prompt without it lets the model fill gaps its own way. [third-party: smixs notes, agrees with P's "separate the change from the constraints"]

### B2. Words that hurt

- Praise words add nothing and the model keeps the detail budget for them: "stunning", "incredible", "epic", "masterpiece", "best quality", "8K", "ultra-detailed", "hyper-realistic", "flawless", "perfect". Replace with facts: "overcast daylight", "brushed aluminium", "chipped paint". [third-party: smixs notes and `00-method/de-slop.md`; OpenAI's page says the same in milder words: avoid "relying on mood words for complex scenes", specify scale, atmosphere and colour instead. verified: P]
- Style labels as a shortcut: "like an Apple ad", "premium", "Instagram style", "cinematic look". Replace with the concrete visual facts. The replacement table is in `agency/deterministic-checks.md` section 1. [verified: P agrees in principle; table is third-party]
- Concept-art or sketch language for app screens produces a drawing of a screen, not a screen. Describe the product "as if it already exists". [verified: P]
- Stylised terms when realism is wanted. OpenAI's own example exclusion: "Avoid cinematic lighting, dramatic color grading, or stylized composition." [verified: P]

### B3. Words that help

- Camera terms work as cues for the look, not as physics: "50mm feel", "eye level", "shallow depth of field". Do not expect exact simulation. [verified: P]
- For a real photo, say so: "photorealistic" or "real photograph", then describe framing and texture. [verified: P]
- For people: body framing, relative scale, gaze, interaction. OpenAI's examples: "full body visible, feet included", "looking down at the open book", "hands naturally gripping the handlebars". [verified: P]
- Concrete nouns beat adjectives: 5 to 12 named objects and surfaces, 2 to 4 light and material facts. [third-party: `craft.md` section 9]
- A place and date anchor pulls in period-correct detail; check clothing and staging afterwards. [verified: P]

### B4. Exact text in the image

- Put the words in quotes. State position and type style. [verified: P]
- Spell unusual words and brand names letter by letter when needed. [verified: P]
- Say how many times: "Render the tagline exactly once". [verified: P]
- Close with: no extra text, no watermarks, no unrelated logos. [verified: P]
- For only-this-copy jobs OpenAI suggests the phrasing "Include ONLY this card text (verbatim)". [verified: P]
- Small text, dense labels, several fonts: use `medium` or `high` quality at least; compare. [verified: P] Third-party notes push dense print work to `xhigh`. [third-party: smixs]
- Translated text: check for leftover words in the original language. [verified: P]
- Known failure: misspelled or soft text, especially small text and multiple fonts. Read every character after generation. [verified: P]

### B5. Edits: keeping the rest unchanged

- Say "change only X", then list what to preserve by name: identity, geometry, layout, lighting, labels. Add exclusions: no new text, logos, watermarks. [verified: P]
- For a tight local edit also name what else must hold: saturation, contrast, arrows, camera angle, surrounding objects. [verified: P]
- Identity line OpenAI gives: "Do not change her face, facial features, skin tone, body shape, pose, or identity in any way." [verified: P]
- Clothing change: allow only the garment to change; fit to the existing pose; match light and shadow; background, camera angle and framing unchanged. [verified: P]
- Products: "preserve geometry and label legibility exactly, and avoid restyling". [verified: P]
- Sketch to render: keep layout, proportions, perspective; "Do not add new elements or text." [verified: P]
- Repeated edits drift. Restate the preserve list every turn and inspect every result. [verified: P]
- If a region must be pixel-identical, composite the approved edit back onto the original in an editor. Prompting cannot guarantee untouched pixels. [verified: P]
- House pattern that matches the above, used in all retouching cards: Change: one thing. Preserve: named list. Constraints: no extra objects, no redesign, no drift. [third-party: smixs; consistent with P]

### B6. Several pictures in one call

- Number each input and give it a purpose: subject, style, clothing, background. Say how they combine and which element goes where. [verified: P]
- Style transfer: give the reference one role, "palette", "texture" or "visual medium", and describe the new subject separately. OpenAI's example: "Use the same style from the input image and generate a man riding a motorcycle on a white background." [verified: P]
- House form: "Image 1: base scene. Image 2: jacket reference, apply only the jacket fabric and cut to the subject in Image 1. Image 3: lighting reference, apply its golden-hour quality." [third-party: smixs; consistent with P]
- The mask, if any, applies to Image 1 only. [verified: G]

### B7. Series and characters

- Make one reference image, then pass it into every later call and repeat the defining details each time: appearance, outfit, five fixed traits. Add "Do not redesign the character." [verified: P]
- Known failure: recurring characters and brand elements may not stay consistent across generations. Approve the sheet first, then generate scenes. [verified: G and P]

### B8. Transparent cutouts

- Ask in words for an isolated subject on a fully transparent background, and set `background` to `transparent` with `png` or `webp`. Both. [verified: P]
- Check the real alpha channel at hair, glass, shadows and edges. "A drawn checkerboard is not transparency." [verified: P]
- Repeat the transparency requirement in every follow-up edit. [verified: P]

### B9. Quality setting method

- Choose the model first, then tune quality. [verified: P]
- Start at an explicit `medium`. If the result falls short, step up one. Once it passes, test one step down to save time and cost. Use `xhigh` and `max` only for a named unmet need within the wait budget. [verified: P and G]
- A higher setting does not guarantee a better image for every prompt. The same label is not the same quality across models. [verified: P]
- Change one thing per round: quality first, then the prompt. [third-party: smixs]
- For unretouched-looking portraits, third-party notes say `high` sharpens skin until it reads as retouched; stay at `medium` unless matching a supplied face matters more. Test before adopting. [third-party: `00-method/de-slop.md` section 6]

### B10. Failure habits and the fix that worked

| Habit | Fix | Source |
| --- | --- | --- |
| Small or multi-font text misspelled | Quote it, say once, raise quality one step, shorten the string | [verified: P] |
| Preserved details drift over repeated edits | Restate the full preserve list each turn; retry from the last approved file, not the drifted one | [verified: P; house rule] |
| Changes outside the edit region | Name the region, name what else must hold, add a mask on Image 1 | [verified: P and G] |
| Historical clothing or staging wrong | Name place and date, then check | [verified: P] |
| Diagram labels or relationships wrong | Put the real labels and relations in the prompt; verify facts, not looks | [verified: P] |
| Painted checkerboard instead of transparency | Set `background` transparent and ask in words; inspect alpha | [verified: P] |
| Over-polished or cinematic look when candid was wanted | State the capture as fact ("a real phone photo"), name located imperfections, ban the glow family in constraints | [verified: P in principle; detail third-party `de-slop.md`] |
| Character looks different per scene | Reference sheet first, repeat traits, "Do not redesign the character" | [verified: P] |
| Same prompt gives different results | Expected. Repeat requests to measure consistency; never judge a prompt on one run | [verified: P] |
| Extra decorative copy, fake badges, sponsor strips | Standing line in every prompt: render only requested text, no unrelated logos, signatures or captions | [house rule, seen in 92 recipe reviews] |

### B11. What this model should not be asked for as final

Final typography, legal text, real data charts, shippable app screens, the client's real logo. Use the image as a reference and rebuild those in the proper tool. [house rule, `00-method/workflow.md`]

---

## Part C. Evidence from our jobs

Empty. Fill from `feedback/records/` once jobs run.

| Measure | Sunburst | Flare |
| --- | --- | --- |
| Jobs run | 0 | 0 |
| First-try pass rate | | |
| Average attempts | | |
| Average output tokens per image, by size and quality | | |
| Wording that failed here and what replaced it | | |

Last check against OpenAI's pages: 2026-10-19. Next check due: 2027-01-19, or when OpenAI announces a model change.
