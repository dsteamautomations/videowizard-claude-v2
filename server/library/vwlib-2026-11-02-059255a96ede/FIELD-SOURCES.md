# Where each job-form field comes from in a VideoWizard run

The library's job form (`library/forms/job-form.md`) is filled by the VideoWizard server (`library.job_form`), never by the operator. One form per step of a shot (start, end, take; a still; a graphic state), in the packet (`vw visuals packet --shot S`, under `library.job_forms`). This table says what the server puts in each field.

| Job-form field | Value in VideoWizard | Source |
| --- | --- | --- |
| `job_id` | `<run code>-<shot id>-<round>` | run code; plan shot id |
| `client_code` | The directory client id | `vw2_runs.client_id` |
| `requested_by` | `agent`, `vw-operator-assistant` | fixed |
| `round` | 1 | fixed in the packet |
| `playbook`, `task` | From `VW-MAP.md` by step | the step |
| `mode` | End image: `edit-with-identity`. Graphic state: `edit`. Otherwise `multi-reference` when more than one reference is bound to the shot, `edit` when one is, `generate` when none is | the step and the shot's bound references |
| `industry` | From the client card; `other` when the card has none | client card |
| `placement` / `video_aspect` | The brief's frame, default 16:9 | brief summary `production.format.frame` |
| `video_seconds` | Take only: the shot's length in seconds, rounded up to a whole second | plan `shot.start_frame`, `shot.end_frame` and the footage's frame rate |
| `request` | `words`: the narration under the shot; `purpose`: the shot's purpose | plan `shot.narration`, `shot.purpose` |
| `purpose` | `intent` and `treatment_fit` of the gap | plan `gap.intent`, `gap.treatment_fit` |
| `audience` | The brief's audience; `general` when it has none | brief summary |
| `style_direction` | `foundation`: the foundation's appearance; `shot`: the shot's appearance | plan `foundation.appearance`, `shot.appearance` |
| `copy` | Graphic state: one `label` per state, its `what_appears`. Otherwise the shot's information progression as one `body` line, or `none` | plan `shot.states[].what_appears`, `shot.information_progression` |
| `text_mode` | `rendered` | fixed |
| `mandatory_text` | `none`. The client's mandatory wording does not come from the client card. | fixed |
| `logo` | `none` | see VW-MAP overrides |
| `images` | Each reference bound to the shot: its id, its element, tag `scene` for a frame grab and `approved` for any other reference, and `keep`: the element's identity requirements | the shot's bound references; plan `elements[].requirements` |
| `brand_kit_id` | The directory client id | `vw2_runs.client_id` |
| `brand_preamble` | Lines `Colours:`, `Type:`, `Guidelines:`, `Trademarks:` from the client card's brand fields that are filled, or `none` | client card `color_palette`, `typography_fonts`, `client_brand_guidelines`, `trademark_patterns` |
| `hard_constraints` | The foundation's exclusions, then the client's learned rules | plan `foundation.exclusions`; the client's rules |
| `avoid` | The foundation's editing constraints | plan `foundation.editing_constraints` |
| `model` | Take: the shot's video model (Gemini Omni). Picture: the film's picture AI (GPT Image or Nano Banana, chosen when the film is created), the generate or the edit model by `mode` | `video_generators`; `visuals_stage.IMAGE_MODELS` |
| `finish` | `final` | fixed; no drafts |
| `variants` | 1 | fixed |
| `checked_by` | `person` | the operator |
| `trial` | `false` | fixed |

Not filled by the server, and not needed: `banned_words`, `images[].consent_id` (no real person's picture is sent, VW-MAP), `spend_cap_usd`, the fix-round fields (the assistant names the base picture and the one change in its answer: `base_image_id`, `single_change`).
