# Job form: what the application sends

Status: first draft, 2026-10-19. Plain words. One form for every kind of job: a social post, a product image, a photo fix, a website visual, a video frame, a video clip. Built from the pieces already in the library, named at the end.

## Who fills it

The application, with values typed by a person or produced by another agent. Claude never fills it. Claude reads it, and either writes a prompt or sends back questions (see `answer-form.md`).

## The rule for missing things

Some fields are required. If a required field is empty, Claude does not guess. It returns the answer form with status `needs_input` and names the missing fields. Optional fields have a stated default.

## The fields

### 1. Job identity

| Field | Required | What it is |
| --- | --- | --- |
| `job_id` | yes | The application's id for this job. Appears in file names and the feedback record. |
| `client_code` | yes | Short code for the client. Used in file names. |
| `requested_by` | yes | `person` or `agent`, with a name or agent id. Tells Claude whether a human saw the brief. |
| `round` | yes | `1` for a new job. `2`, `3`... for a fix round on an earlier output (then fill section 11). |
| `deadline` | no | Date and time. Default none. |
| `revision_rounds_included` | no | How many fix rounds the client has paid for. Default 2. |

### 2. What kind of job

| Field | Required | Values |
| --- | --- | --- |
| `playbook` | yes | `social`, `product`, `photo-fix`, `web-app`, `video-frame`, `video-clip`. Picks which library files Claude opens. |
| `task` | yes | What is being made, in a fixed word. Image tasks: `feed-post`, `story`, `carousel-cover`, `ad-variant`, `festival-post`, `greeting`, `event-announcement`, `testimonial-graphic`, `gbp-post`, `linkedin-graphic`, `thumbnail`, `display-set`, `product-hero`, `marketplace-main`, `marketplace-secondary`, `lifestyle-in-use`, `colourway-set`, `dish-hero`, `packaging-mockup`, `cleanup`, `relight`, `background-swap`, `portrait-retouch`, `product-retouch`, `cutout`, `restoration`, `property-enhance`, `reframe`, `landing-hero`, `icon-set`, `spot-illustration`, `device-mockup`, `app-store-panel`, `process-explainer`, `email-header`, `wireframe-to-concept`, `brand-board`, `storefront-signboard`, `poster`, `rollup-banner`, `event-backdrop`, `signage`, `brand-wall`. Video tasks: `continuity-kit`, `storyboard`, `first-last-frame`, `keyframe`, `keyframe-set`, `cover-frame`, `clip-from-frame`, `clip-from-text`, `clip-edit`, `clip-extend`. |
| `mode` | no | `generate`, `edit`, `edit-with-identity`, `multi-reference`, `extend`. Default: `edit` when a picture tagged `product`, `person`, `scene` or `approved` is attached, otherwise `generate`. |
| `industry` | no | One word: `retail`, `real-estate`, `healthcare`, `education`, `restaurant`, `local-service`, `software`, `other`. Sets the compliance flags. Default `other`. |

### 3. Where it will be used

| Field | Required | What it is |
| --- | --- | --- |
| `placement` | yes for images and frames | A placement id from `agency/channel-specs.yaml`, for example `meta_feed_4x5`, `meta_story_9x16`, `gbp_post_4x3`, `website_hero_16x9`, `marketplace_main_1x1`, `youtube_thumb_16x9`. Or `print` with `print_size_mm`. The sheet gives the aspect, the pixel size, the safe zones and the text density. |
| `placements_extra` | no | More placement ids when one master must fan out into several sizes. Default none. |
| `video_aspect` | yes for video | `16:9` or `9:16` for Omni; Seedance also takes `1:1`, `4:3`, `3:4`, `21:9`. |
| `video_seconds` | yes for clips | Whole seconds. Omni 3 to 10, Seedance 4 to 30. |

### 4. The brief in the client's words

| Field | Required | What it is |
| --- | --- | --- |
| `request` | yes | One to three sentences, as the client said it. "Make our Diwali post with the brass lamp photo and the 20 percent offer." |
| `purpose` | no | What the image is for in one line: "announce the festive offer to existing customers". Default taken from `task`. |
| `audience` | no | Who sees it. Default `general`. |
| `style_direction` | no | In observable words if possible: "warm, one product, deep blue backdrop, generous margins". Vague words like "premium" or "like Apple" are allowed here; Claude rewrites them with the replacement table before they reach a prompt. |

### 5. Exact words

| Field | Required | What it is |
| --- | --- | --- |
| `copy` | yes when any text should appear; `none` otherwise | A list. Each entry: `role` (`headline`, `subline`, `offer`, `validity`, `cta`, `body`, `caption`, `label`, `mandatory`), `text` exactly as approved, `language`. Claude never changes a letter. |
| `text_mode` | no | `rendered`: the model draws the words. `reserved`: the model leaves an empty area and the words are typeset later. Default: `rendered` for English copy, `reserved` for any other script until a test proves the model reliable. |
| `mandatory_text` | yes when the industry has one | The registration number, licence number, disclaimer. Comes from the brand kit if it is there. |
| `logo` | yes | `reserve` (leave an empty area; the real logo is composited later) or `none`. The model never draws a logo. |

### 6. Pictures and clips sent in

A list. Each entry:

| Field | Required | What it is |
| --- | --- | --- |
| `id` | yes | The picture's id in the application's table. |
| `tag` | yes | One of: `product`, `person`, `scene`, `style`, `material`, `sketch`, `logo`, `approved`, `avoid`, `storyboard`, `first-frame`, `last-frame`, `source-clip`. Meanings in `BUILD-PLAN.md` Part 3. |
| `link` | yes | A temporary link that works for about an hour, or a file path the executor can read. |
| `consent_id` | yes when `tag` is `person` | The written consent record for that person. No consent id, no identity edit. |
| `keep` | no | What must not change in this picture, in the client's words: "the label text, the brass colour, the lamp shape". Claude adds to it from what it sees. |
| `note` | no | Anything else: "this is the only photo we have, it is a WhatsApp forward". |

Rules: at most one `first-frame` and one `last-frame`. For Seedance, do not send `first-frame` together with other reference tags in one job; the first frame wins and the references do nothing. Count limits per model are in the fact sheets; Claude checks them.

### 7. Brand kit

| Field | Required | What it is |
| --- | --- | --- |
| `brand_kit_id` | yes | Which client kit, and its version. |
| `brand_preamble` | yes | The six to eight lines the application renders from the client's kit, which follows `agency/brand-kit-template.yaml`: brand name exactly as written, colours with hex values, background family, type feel, logo rule, photography style, people policy, banned words, mandatory text, approved copy bank. The application renders them; Claude pastes them at the top of the prompt. |
| `festival_sheet` | no | A festival name when the job is seasonal, matching a file in `agency/festivals/`: `diwali`, `pongal`, `onam`, `eid`, `independence-day`, `republic-day`. Pulls that sheet's dates, motifs and avoid-list. Default none. |

### 8. Must keep and must not

| Field | Required | What it is |
| --- | --- | --- |
| `hard_constraints` | no | Short lines the client insists on: "no people", "no firecrackers", "product must fill at least half the frame". Default: the playbook's own list. |
| `avoid` | no | Things rejected before: "no gift boxes, client hated them last time". Default none. |
| `banned_words` | no | Beyond the brand kit's list. Default none. |

### 9. Model and spend

| Field | Required | What it is |
| --- | --- | --- |
| `model` | no | A model id from `models/CHOSEN-MODELS.md`, or `auto`. Default `auto`: Claude picks by the rules in each fact sheet's "when to pick" section. |
| `finish` | no | `draft` or `final`. Draft means lowest useful size and quality, for choosing between ideas. Default `draft` on round 1, `final` on a fix round. |
| `variants` | no | How many different pictures to make from the same brief. Default 1. |
| `spend_cap_usd` | no | Stop before this amount. Default from the playbook. |

### 10. Checking

| Field | Required | What it is |
| --- | --- | --- |
| `checked_by` | yes | `person`, `auto` or `both`. Who ticks the checklist that comes back with the prompt. |
| `trial` | no | `true` when this job runs without a person looking before the result is stored. Marks the feedback record. Default `false`. |

### 11. Fix round only

Filled when `round` is 2 or more.

| Field | Required | What it is |
| --- | --- | --- |
| `previous_output_id` | yes | The picture id of the last approved or rejected output. |
| `verdict` | yes | `fix` or `reject`, from the checklist. |
| `what_went_wrong` | yes | One line per problem, in the checker's words: "the diya on the left has three flames", "the offer text says 25 not 20". |
| `change` | yes | The one change wanted this round. One change per round; if two are listed Claude does the first and queues the second. |
| `base` | no | `last-approved` (default) or `source`. Retry from the last approved file, or from the original picture when the last result drifted. |

## Example: a Diwali feed post

```json
{
  "job_id": "J-2026-1019-0042",
  "client_code": "BRASSCO",
  "requested_by": {"kind": "agent", "id": "social-planner-v2"},
  "round": 1,
  "deadline": "2026-10-21T18:00:00+05:30",
  "playbook": "social",
  "task": "festival-post",
  "mode": "edit",
  "industry": "retail",
  "placement": "meta_feed_4x5",
  "placements_extra": ["meta_story_9x16"],
  "request": "Diwali offer post using our brass lamp photo. 20 percent off all brass lamps till 31 October.",
  "purpose": "announce the festive offer to existing customers",
  "audience": "home buyers in Chennai, 30 to 55",
  "style_direction": "warm and festive, one product, deep blue backdrop, generous margins",
  "copy": [
    {"role": "offer", "text": "FESTIVE 20% OFF ON ALL BRASS LAMPS", "language": "en"},
    {"role": "validity", "text": "Valid till 31 October", "language": "en"}
  ],
  "text_mode": "rendered",
  "mandatory_text": "none",
  "logo": "reserve",
  "images": [
    {"id": "img_9f31", "tag": "product", "link": "https://.../img_9f31?sig=...", "keep": "lamp shape, brass colour, the engraved label on the base", "note": "shot on a phone, slightly yellow"}
  ],
  "brand_kit_id": "BRASSCO-v3",
  "brand_preamble": "Client code: BRASSCO  Brand kit version: 3 ...",
  "festival_sheet": "diwali",
  "hard_constraints": ["no people", "no firecrackers", "no deity images"],
  "avoid": ["gift boxes"],
  "model": "auto",
  "finish": "draft",
  "variants": 2,
  "spend_cap_usd": 1.00,
  "checked_by": "person",
  "trial": false
}
```

## What Claude does with it

1. Checks the required fields. Missing: returns `needs_input`.
2. Opens the playbook named, the common rules, the channel sheet row for the placement, and the fact sheet for the chosen or auto-picked model.
3. Looks at every picture, writes two lines on each, checks the tag against what it sees, builds the keep-list.
4. Writes the prompt, the settings, the picture order and the checklist, and returns them in the answer form.

## Where the fields came from

Brief template and reference roles: `00-method/prompting-guide.md`. Task types, copy policy, reference roles, hard constraints: `agency/advertising-brief-schema.md`. Intake lists: `agency/product-shoot/intake-brief.md`, `agency/retouching/README.md`. Reference tiers and observations: `agency/reference-image-policy.md`. Clarification order and defaults: `agency/marketplace/clarifying-questions.md`. Brand kit lines, channel sheet, scenario ids: `DIRECTION.md` sections 5a, 5b, 5f, 7. Picture tags: `BUILD-PLAN.md` Part 3. Model settings: the fact sheets. Feedback fields: `feedback/record-template.yaml`.
