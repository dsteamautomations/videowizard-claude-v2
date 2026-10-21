# Answer form: what Claude returns

Status: first draft, 2026-10-19. Plain words. One form for every job. The application reads it to call the model, to run the check afterwards, and to write the feedback record.

## Three possible answers

| `status` | Meaning | What else is filled |
| --- | --- | --- |
| `ready` | A prompt is written and can be sent. | Sections 2 to 8. |
| `needs_input` | Something required is missing or contradictory. Nothing is sent to a model. | Section 9 only. |
| `refused` | The job cannot be done under our rules. Nothing is sent. | Section 10 only. |

## 1. Identity

| Field | What it is |
| --- | --- |
| `job_id`, `round` | Copied from the job form. |
| `answer_id` | Claude's id for this answer; goes into the file name as the version. |
| `playbook_used`, `playbook_version` | Which playbook and which version of it, for the feedback record. |
| `files_opened` | The library files Claude read for this job. Lets us see what the router did. |

## 2. What Claude saw in the pictures

One entry per picture sent in.

| Field | What it is |
| --- | --- |
| `id`, `tag` | From the job form. |
| `seen` | Two lines: what is in it, any text read letter by letter, colours, anything odd. |
| `tag_ok` | `true`, or `false` with a reason: "tagged product but shows a person". |
| `keep_list` | The things in this picture that must not change, as nouns a checker can tick. The client's `keep` plus what Claude saw: "lamp silhouette; brass colour; label text NET WT 200 G; engraved base pattern". |
| `warnings` | Blurry, watermarked, a visible face without a consent id, a competitor logo, a WhatsApp forward. |

## 3. Model and settings

| Field | What it is |
| --- | --- |
| `model` | The exact id to call: `gpt-image-2.5-sunburst`, `gpt-image-2.5-flare`, `gemini-nano-banana-2.1`, `gemini-omni-1.1-flash`, `bytedance/seedance-2.5`. |
| `route` | `openai`, `google`, `openrouter`. |
| `why_this_model` | One line, from the fact sheet's "when to pick" rules. |
| `settings` | The call parameters, named exactly as that API wants them, taken from the fact sheet. For GPT Image: `size`, `quality`, `background`, `output_format`, `n`. For Nano Banana: `response_format.aspect_ratio`, `response_format.image_size`, `generation_config.thinking_level`. For Omni: `response_format.aspect_ratio`, `response_format.resolution`, `response_format.delivery`, `generation_config.video_config.task`, `store`. For Seedance: `duration`, `size` or `resolution` plus `aspect_ratio`, `generate_audio`, `provider.options`. |
| `estimated_cost_usd` | From the fact sheet's price table. The executor stops if it is above the job's spend cap. |

## 4. Pictures to send, in order

A list in the exact order the prompt names them.

| Field | What it is |
| --- | --- |
| `position` | 1, 2, 3... The prompt says "Image 1", "@Image 1", `<IMAGE_REF_0>` according to the model's own convention; the fact sheet says which. |
| `id` | The picture id. |
| `role_in_prompt` | What the prompt tells the model this picture is for. |
| `model_slot` | Where it goes in the call: GPT Image `image[]`; Nano Banana `input` parts; Omni `input` parts with a tag; Seedance `frame_images` or `input_references`. |
| `mask` | Optional mask file id, only for GPT Image, applied to picture 1. |

## 5. The prompt

| Field | What it is |
| --- | --- |
| `prompt` | The full text, exactly as it must be sent, brand preamble included at the top. Nothing is added by the application. |
| `fixed_lines_present` | A list of the house lines Claude confirms are in it: the standing no-extra-text line; the logo reserve; the keep-list; the exact copy in quotes; the placement line. |
| `exact_text` | The copy strings that must appear in the image, one per line, for the checker to compare letter by letter. Empty when `text_mode` was `reserved`. |

For a fix round there are two more fields: `base_image_id`, the picture the edit starts from, and `single_change`, the one change this prompt makes, in one sentence.

## 6. The checklist for this image

One line per thing a checker can see. These are what the person or the vision model ticks. Written for this job, not copied from a template.

Each line: `check` (what to look at), `pass_when` (what counts as a pass), `weight` (`must` or `should`). Examples:

- Product outline, label and colours match picture img_9f31 side by side. must.
- Text reads exactly "FESTIVE 20% OFF ON ALL BRASS LAMPS" and "Valid till 31 October", letter by letter; nothing else written anywhere in the frame. must.
- Lower-right corner, about one eighth of the width, is empty. must.
- Two lit diyas at lower left, each with one flame. should.
- No deity, firecracker, person, gift box, badge or star. must.
- Output size is 928x1152 or larger at 4:5. must.

Any `must` line failing means `fix` or `reject`. The checker writes the verdict into the feedback record.

## 7. Flags

| Field | What it is |
| --- | --- |
| `risk_flags` | What is likely to go wrong with this prompt on this model, from the fact sheet's failure table: "petals may drift into the reserved corner", "small label text may soften on relight". |
| `compliance_flags` | Which lines of `agency/compliance-checklist.md` apply, by id and name: for example `C09 consent-on-file`, `C02 no-superlatives`, `C03 mandatory-text-present`, `C04 no-health-outcome-claims`, `C10 festival-motif-check`, `C16 disclosure-label`. |
| `rewrites_made` | Vague words from the brief that Claude replaced, with the replacement: "premium" became "low-saturation main colour, 25% negative space, rim light on the product edge". So the client can see the translation. |
| `lint` | The six deterministic checks, each `true` or `false`: banned phrases removed, composition specified, lighting specified, typography specified, materials specified, reference policy specified. A `false` here means Claude repaired once; if still false, the answer is `needs_input`. |

## 8. Notes for the executor

| Field | What it is |
| --- | --- |
| `wait` | How to wait: GPT Image synchronous with a long timeout; Omni `background=true` and poll every 10 seconds; Seedance poll every 30 seconds; Nano Banana synchronous. |
| `output_name` | The file name stem: `{client}_{campaign}_{asset}_{channel}_v{nn}_draft`, from DIRECTION section 5e. For video frames the asset part is `s{shot}-{role}`. |
| `save_beside` | The prompt text and this answer, with the same stem. |
| `then` | What happens after the check: `fan-out` to the extra placements, `next-variant`, `stop`. |

## 9. When something is missing: `needs_input`

| Field | What it is |
| --- | --- |
| `questions` | A list, most important first, one question each. Each: `field` (the job-form field name), `question` (in plain words), `why` (one line), `options` (if there is a short list to pick from). At most five. |
| `can_proceed_with_defaults` | `true` when the job could run on defaults and the questions are only improvements; `false` when it cannot. |

Order of asking, from the marketplace clarifying flow: placement first, then the pictures, then the purpose and audience, then style. One thing per question.

## 10. When the job is refused: `refused`

| Field | What it is |
| --- | --- |
| `reason` | One of: `no-consent` (a person's face or body would be edited without a consent id), `policy` (the request falls under the decline list in `agency/retouching/README.md` or the compliance checklist: body shape, age, skin colour, invented product features, structural property changes, before-and-after where forbidden, removing someone else's watermark), `rights` (a picture the client does not own), `impossible` (a size or length no chosen model can make). |
| `detail` | One or two lines. |
| `nearest_thing` | What Claude can do instead, if anything. |

## Example: the Diwali job, status ready

```json
{
  "status": "ready",
  "job_id": "J-2026-1019-0042",
  "round": 1,
  "answer_id": "v01",
  "playbook_used": "social",
  "playbook_version": "0.1",
  "files_opened": ["rulebook", "playbooks/social", "channel-sheet:meta_feed_4x5", "models/gpt-image/FACT-SHEET.md", "festivals/diwali"],
  "pictures_seen": [
    {"id": "img_9f31", "tag": "product", "tag_ok": true,
     "seen": "A brass oil lamp with a round base and engraved vine pattern, on a white table, phone photo, slight yellow cast. Label on base reads HERITAGE BRASS.",
     "keep_list": ["lamp silhouette", "brass colour", "engraved vine pattern", "label text HERITAGE BRASS", "proportions"],
     "warnings": ["yellow cast; relight will change apparent colour, so the keep-list names brass colour explicitly"]}
  ],
  "model": "gpt-image-2.5-sunburst",
  "route": "openai",
  "why_this_model": "edit with a product that must not move; label text must stay exact",
  "settings": {"size": "1024x1280", "quality": "medium", "background": "opaque", "output_format": "png", "n": 2},
  "estimated_cost_usd": 0.12,
  "pictures_to_send": [
    {"position": 1, "id": "img_9f31", "role_in_prompt": "the client's product photo; keep it exactly", "model_slot": "image[]"}
  ],
  "prompt": "Client code: BRASSCO ... (brand preamble) ...\nAsset: Diwali offer post. Target aspect ratio: 4:5. Mode: edit.\nImage 1 is the client's product photo. Keep the lamp's silhouette, engraved vine pattern, label text \"HERITAGE BRASS\", proportions and brass colour exactly as in Image 1. ...\nExact image text: \"FESTIVE 20% OFF ON ALL BRASS LAMPS\" large in the top area ...; \"Valid till 31 October\" small beneath it. No other text.\nConstraints: No deity images, no firecrackers, no people, no gift boxes ...\nRender only explicitly requested image text. Do not add unrelated logos, signatures or captions.",
  "fixed_lines_present": ["standing-no-extra-text", "logo-reserve", "keep-list", "exact-copy-quoted", "placement-line"],
  "exact_text": ["FESTIVE 20% OFF ON ALL BRASS LAMPS", "Valid till 31 October"],
  "checklist": [
    {"check": "lamp outline, pattern, label and colour against img_9f31", "pass_when": "match side by side", "weight": "must"},
    {"check": "both text strings", "pass_when": "letter by letter, nothing else written", "weight": "must"},
    {"check": "lower-right corner", "pass_when": "empty, about one eighth of width", "weight": "must"},
    {"check": "diyas", "pass_when": "two, lower left, one flame each", "weight": "should"},
    {"check": "forbidden items", "pass_when": "no deity, firecracker, person, gift box, badge", "weight": "must"},
    {"check": "output size", "pass_when": "1024x1280", "weight": "must"}
  ],
  "risk_flags": ["petals and bokeh may drift into the reserved corner", "label text may soften under relight; retry with 'do not relight the label face'"],
  "compliance_flags": ["no-superlatives", "festival-motif-check"],
  "rewrites_made": [{"from": "warm and festive", "to": "deep blue backdrop, two lit brass diyas, marigold petal arc, one soft warm key light from upper left"}],
  "lint": {"bannedPhrasesRemoved": true, "compositionSpecified": true, "lightingSpecified": true, "typographySpecified": true, "materialsSpecified": true, "imageReferencePolicySpecified": true},
  "wait": "synchronous, timeout 180 s",
  "output_name": "BRASSCO_diwali26_offerpost_meta-feed-4x5_v01_draft",
  "save_beside": ["prompt.txt", "answer.json"],
  "then": "fan-out to meta_story_9x16 after approval"
}
```

## Example: status needs_input

```json
{
  "status": "needs_input",
  "job_id": "J-2026-1019-0043",
  "questions": [
    {"field": "copy", "question": "What exact words go on the image? The brief says 'the offer' but no text was given.", "why": "Claude never invents prices or dates.", "options": null},
    {"field": "images[0].consent_id", "question": "The picture tagged person shows a face. Is there a consent record for this person?", "why": "No consent id, no identity edit.", "options": null}
  ],
  "can_proceed_with_defaults": false
}
```

## The lint Claude runs before answering `ready`

1. Every required job-form field is present.
2. Every `copy` string appears in the prompt inside quotes, unchanged, and the standing no-extra-text line is present.
3. The logo rule is `reserve` or `none`; the prompt never asks for a logo.
4. The aspect in the settings matches the placement row.
5. Every picture sent has a role sentence in the prompt, and the count and kinds are within the model's limits.
6. Every picture tagged `person` has a consent id.
7. No banned phrase from `agency/deterministic-checks.md` survives; the six presence checks pass.
8. No model name, size, length or setting name appears inside the prompt text unless that model's fact sheet says it belongs there.
9. On a fix round: one change, one keep-list, and the base image named.
10. The estimated cost is under the spend cap.

Fails once, Claude repairs once. Fails twice, the answer is `needs_input` with the failing rule named.

## Where the fields came from

Observations, do-not-copy list, deterministic checks, risk warnings and the strict-JSON rule: `agency/reference-image-policy.md` section 2 and `agency/deterministic-checks.md`. Checklist style and auto-reject triggers: `agency/product-shoot/qa-rubric.md` and the acceptance checks in `agency/retouching/`. Preserve lists and one-change rule: `00-method/workflow.md`. File naming: `DIRECTION.md` section 5e. Compliance flags: `DIRECTION.md` section 5d. Refusal list: `agency/retouching/README.md`. Settings and picture slots: the five model files.
