# Where each job-form field comes from in a VideoWizard run

The library's job form (`library/forms/job-form.md`) is filled by VideoWizard, never by the operator. One job per generated picture or take. "Packet" means `vw visuals packet --shot S` (the server's `visuals_stage.packet`). Names in code are as of server 0.21.3 plus design/65.

| Job-form field | Value in VideoWizard | Source |
| --- | --- | --- |
| `job_id` | `<run code>-<shot or element id>-<n>` | run code; shot or element id from the plan |
| `client_code` | The directory client id | `vw2_runs.client_id` |
| `requested_by` | `agent`, `vw-operator-assistant` | fixed |
| `round` | 1, then 2, 3… for each new attempt on the same shot or element | count of earlier references or takes for it |
| `playbook`, `task` | From `VW-MAP.md` by step | the command being prepared |
| `mode` | `generate`; `edit` when parents are attached (a state, an edit of a reference); `edit-with-identity` when an approved person sheet is attached; `multi-reference` for a keyframe with several element references | the image request's `parents` and the bound references |
| `industry` | From the client card | client directory (design/50) |
| `placement` / `video_aspect` | The brief's frame, default 16:9 | brief summary `production.format.frame` (`visuals_stage.default_aspect`) |
| `video_seconds` | The shot's placement rounded up to the generator's whole seconds | `prepare_take` |
| `request` | The words spoken under the shot, and the shot's `purpose` | the gap's narration words; plan `shot.purpose` |
| `purpose` | The gap's `intent` and the shot's relation to the narration | first-cut gap `intent`; plan `gap.treatment_fit` |
| `audience` | The brief's audience | brief answers |
| `style_direction` | The foundation's `appearance` plus the shot's `appearance` | plan `foundation.appearance`, `shot.appearance` |
| `copy` | Every label, number and caption the shot shows, exactly as written in the plan | plan `shot.information_progression` / `states[].what_appears` (design/65 B9); checked against the accepted script |
| `text_mode` | `rendered` | design/64 D2 |
| `mandatory_text` | From the client card's mandatory lines, if any | client card |
| `logo` | `none` | see VW-MAP overrides |
| `images` | The approved references bound to the shot, each with its tag: element references `approved`; a frame grab `scene`; the start image `first-frame`; the end image `last-frame`; a previous state `approved` | visuals session `references` and `bindings` |
| `images[].keep` | The element's identity requirements | plan `elements[].requirements` |
| `images[].consent_id` | Required for a real person; VideoWizard has none today, so real faces are not edited | — (gap: see change note) |
| `brand_kit_id`, `brand_preamble` | Rendered from the client card's brand group: palette, fonts, guidelines, trademark patterns | `client_card` brand fields (design/50) |
| `hard_constraints` | The foundation's exclusions, the client's learned rules, the brief's rules | plan `foundation.exclusions`; `core.effective_rules` |
| `avoid` | Earlier rejected pictures for this shot, with the operator's reasons | visuals session reviews; `editing_constraints` |
| `banned_words` | Client card trademark patterns, if any | client card |
| `model` | Fixed by the server: GPT Image 2.5 for images; the shot's generator for takes | `IMAGE_MODELS`; `video_generators` |
| `finish` | `final` | VW-MAP overrides |
| `variants` | 1 | — |
| `spend_cap_usd` | The run's remaining visuals cap, in INR converted at SK's rate, or the cap check alone | design/65 B7 `check_cap` |
| `checked_by` | `person` | the operator |
| `trial` | `false` | — |
| Fix round fields | The previous reference or take, the operator's rejection words as `what_went_wrong`, one `change` | visuals session reviews |
