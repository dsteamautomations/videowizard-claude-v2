# design/69 — A VideoWizard cut of the library's answer form (due diligence, for SK before Revathi)

Status: builder's due diligence, 21 Oct 2026, after design/68 part A. A proposal for SK to put to Revathi, the library's owner; nothing built. Sources: the bundle's `forms/answer-form.md` (ten sections, ten lint rules), `forms/job-form.md`, `feedback/record-template.videowizard.yaml`, `feedback/README.md`, `RULEBOOK.md` §17, `VW-MAP.md` overrides, `FIELD-SOURCES.md`; the server after design/68 (`library.job_form`, `library.check_answer`, `visual_workers`, `video_providers.motion_text`).

## 1. Why

The child writes one answer form per generated picture and take. VW-6 has 60 pictures and 18 takes. The full form has eight sections for a `ready` answer; several of them restate decisions the VideoWizard server has already taken and records on its own. Estimated writing time per picture at the full form is about 1.5 minutes; at the cut below about 0.7. On VW-6 that is 45 to 60 minutes of a four-hour stage. It is the largest single saving available (design/49, 21 Oct, the options SK chose).

## 2. What the server already fixes or records, section by section

| Answer section | In the library | In VideoWizard | Keep? |
|---|---|---|---|
| 1 Identity: `job_id`, `round`, `answer_id`, `playbook_used`, `playbook_version`, `files_opened` | Claude copies and declares | `job_id` and `round` come from the server's job form; the playbook is fixed per step by VW-MAP | Keep `answer_id`, `playbook_version`, `files_opened` (cheap; they tell the maintainer what the router opened). Drop `job_id`, `round`, `playbook_used`: the server has them. |
| 2 What Claude saw in the pictures: `seen`, `tag_ok`, `keep_list`, `warnings` per picture | The reference policy's observations | The pictures are the operator-approved references the child itself composed, tagged by the server | Keep `keep_list` per picture (it feeds the prompt's hold lines and the checklist). Drop `seen`, `tag_ok`, `warnings`. |
| 3 Model and settings: `model`, `route`, `why_this_model`, `settings`, `estimated_cost_usd` | Claude picks by the fact sheets | Fixed by the server: GPT Image 2.5 Flare or Sunburst, 1536×864 high, the shot's generator; the cap is checked in INR by the server | Drop all five. |
| 4 Pictures to send, in order: `position`, `id`, `role_in_prompt`, `model_slot`, `mask` | Claude orders them | The server sends the parents in the order given and appends the start's references itself (design/67); slots are fixed per model | Drop. The prompt still names the pictures in the model's convention; see lint 5 below. |
| 5 The prompt: `prompt`, `fixed_lines_present`, `exact_text`; fix round `base_image_id`, `single_change` | The core | The server checks `prompt` and `exact_text` today (design/68 L5); `motion_text` appends the video fixed lines itself | Keep `prompt`, `exact_text`, and on a fix round `base_image_id`, `single_change`. Drop `fixed_lines_present` (the server adds the video lines; for images the no-extra-text line is one of the six presence checks). |
| 6 The checklist | The core; the record's spine | The server requires at least one must line; the operator's verdict is ticked against it | Keep, unchanged. |
| 7 Flags: `risk_flags`, `compliance_flags`, `rewrites_made`, `lint` | Learning and discipline | Nothing in the server covers them | Keep, all optional except `lint` (six booleans, one line). `compliance_flags` only when the client card's industry carries lines. |
| 8 Notes for the executor: `wait`, `output_name`, `save_beside`, `then` | Tells the application how to run the call | The worker waits, names and stores on its own | Drop all four. |
| 9, 10 `needs_input`, `refused` | Statuses | The server refuses anything but `ready`; the child settles a `needs_input` in chat and drops a picture on a `refused` | Keep the two statuses with `questions` or `reason` in short form. |
| (new, design/68) `suggestion` | — | Copied into the feedback record | Keep, optional. |

## 3. The cut form, as a list

`status`; `answer_id`; `playbook_version`; `files_opened`; `prompt`; `exact_text`; `keep_list` per input picture id; `checklist` (check, pass_when, weight); `lint` (six booleans); optional `risk_flags`, `compliance_flags`, `rewrites_made`, `suggestion`; on a fix round `base_image_id`, `single_change`; on `needs_input` the `questions`; on `refused` the `reason` and `detail`.

About fifteen fields instead of about forty. Everything the feedback record needs that is not in the form (`model`, `settings`, `inputs` with tags, `output_path`, `attempt`, `verdict`, `minutes_total`) the record template already says the server writes from what it stores, so the record loses nothing.

## 4. The ten lint rules under the cut

| Rule | Under the cut |
|---|---|
| 1 required job-form fields present | The server fills the form; a missing field is the server's, not the child's. |
| 2 every copy string in the prompt in quotes; the no-extra-text line present | `exact_text` checked by the server today; the no-extra-text line stays the child's (presence check 1 of six). |
| 3 logo `reserve` or `none`; no logo asked | Fixed `none` by the server. A mechanical check is cheap: refuse a prompt that asks for a logo. |
| 4 the aspect matches the placement | Fixed by the server (the brief's frame, 1536×864). |
| 5 every picture sent has a role sentence; counts within limits | The server knows the count and the model limits; the role sentence stays the child's. |
| 6 every `person` picture has a consent id | No consent ids exist (open for SK); real faces are look references only. |
| 7 no banned phrase; six presence checks | The child's, declared in `lint`. |
| 8 no model name, size or setting inside the prompt | A mechanical check is cheap: refuse a prompt containing the model ids, `1536x864`, `720p`. |
| 9 fix round: one change, one keep-list, the base named | `single_change`, `keep_list`, `base_image_id` kept. |
| 10 estimated cost under the spend cap | The server's cap check. |

Two of the ten become server checks (3 and 8), five are the server's already (1, 4, 5 count, 6 moot, 10), three stay the child's (2 partly, 7, 9). The server's lint would grow by two lines.

## 5. How to carry it in the bundle

As Revathi did for the record: a VideoWizard variant beside the original, `forms/answer-form.videowizard.md`, listed in VW-MAP's always-open table in place of `answer-form.md`, with one line saying which sections VideoWizard fixes and why. The master library's form is untouched. The next snapshot carries it; the server's lint reads the same field names it reads today (`status`, `prompt`, `checklist`, `exact_text`), so no server change is needed for the cut itself, only for the two added checks if wanted.

## 6. What this does not decide

Whether the dropped observations (`seen`, `tag_ok`, `warnings`) have a value for the library's learning that outweighs their cost in VideoWizard, where the inputs are the child's own approved pictures. Revathi's call. If she wants them, keeping `warnings` alone (a visible face, a competitor mark) costs little.

## 7. Questions for Revathi

1. Agree to a VideoWizard variant of the answer form with the fields of §3, as a file beside the original?
2. Keep `warnings` from section 2, or drop it with `seen` and `tag_ok`?
3. Agree that lint rules 3 and 8 move to the server as mechanical refusals?
4. Does the maintainer's handoff (design/68 part B, L9) need anything from the dropped sections?
