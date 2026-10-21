# VideoWizard map: which library files each picture step opens

This file stands in for the library's `INDEX.md` inside VideoWizard. Where `RULEBOOK.md` says "open only what INDEX.md says", read "what this map says". Everything not in this bundle is the library's shelf and is never opened during a run.

## Always open, for every generated picture or take

| File | Why |
| --- | --- |
| `library/RULEBOOK.md` | The rules for every job. |
| `library/forms/answer-form.md` | The shape of the answer and the lint before `ready`. |
| `library/agency/deterministic-checks.md` section 1 | The vague-word replacement table (RULEBOOK rule 2). |

## Per step

| VideoWizard step (command) | Library task | Playbook | Model sheet | Open when |
| --- | --- | --- | --- | --- |
| Reference of a person, object or place, generated (`vw visuals image --kind isolated` or `sheet`) | `continuity-kit` | `playbooks/video-frame.md` | `models/gpt-image/FACT-SHEET.md` | A person: `video/consistent-character-frames.md` |
| Frame grab from a clip (`vw visuals frame`) | none: no prompt is written | — | — | Choosing the frame for a gap: `video/gap-fill.md` section 3 |
| AI still for an image shot: a scene (`image --kind keyframe`, then `still`) | `keyframe` | `playbooks/video-frame.md` | `models/gpt-image/FACT-SHEET.md` | `video/craft/animatic-keyframes.md` (the keyframe card); next to real footage: `video/gap-fill.md`; a real photograph look: `00-method/de-slop.md` |
| AI still for a diagram shot: diagram, chart, labelled picture (`image`, then `still`) | `process-explainer` | `playbooks/web-app.md` (process-explainer) | `models/gpt-image/FACT-SHEET.md` | `00-method/craft.md` section 5 (diagram grammar); `prompts/05-information.md` |
| Graphic sequence for an animation shot (`image --kind state --parents R`, then `sequence`) | `graphic-states` | `video/diagram-in-states.md` | `models/gpt-image/FACT-SHEET.md` B5 | `00-method/craft.md` section 5 |
| Start image of a video shot (`image --kind keyframe`) | `keyframe` | `playbooks/video-frame.md` | `models/gpt-image/FACT-SHEET.md`, and the video model's sheet A5 for its accepted size | `video/craft/animatic-keyframes.md`; next to real footage: `video/gap-fill.md`; a person: `video/consistent-character-frames.md` |
| End image of a video shot (`image --kind keyframe`, `prepare-take --end`) | `first-last-frame` | `playbooks/video-frame.md` | as above | `video/gap-fill.md` section 3 |
| Video take (`prepare-take`, `take`) | `clip-from-frame` | `playbooks/video-clip.md` | Omni: `video/models/gemini-omni-1-1/FACT-SHEET.md`; Kling: `video/models/kling/FACT-SHEET.md` section 3 and `video/models/higgsfield/NOTES.md`; Seedance: `video/models/seedance/FACT-SHEET.md` Part B and `video/models/higgsfield/NOTES.md` | `video/craft/camera-lighting-vocabulary.md`; next to real footage: `video/gap-fill.md`; a faceless explainer: `video/still-to-motion-pipeline.md` |
| Any step, when the client's industry carries compliance lines (healthcare, education, real estate, finance, restaurant) | — | — | — | `agency/compliance-checklist.md` |

Five to nine files per step, as the library intends.

## Where VideoWizard overrides the library

These win over the playbooks and fact sheets inside VideoWizard, because the server decides them.

| Library says | VideoWizard does | Why |
| --- | --- | --- |
| Nano Banana for storyboards, continuity sheets, cover frames and character work (video-frame playbook) | GPT Image 2.5 for every image: Flare to generate, Sunburst to edit | The server only calls OpenAI images (`visuals_stage.IMAGE_MODELS`). |
| Seedance through OpenRouter | Kling 3.0 Standard and Seedance 2.5 through Higgsfield; Omni direct from Google | The server's catalog (`video_generators.CATALOG`). See `video/models/higgsfield/NOTES.md`. |
| Storyboard grids, cover frames | Not used | VideoWizard plans shots in the visual plan, not in a storyboard image. |
| Draft at low size, then final | One generation per attempt at the run's size | The ₹1,000 visuals cap (design/65 S6); the operator approves each result. |
| Audio described or switched off | Always off, no narration, dialogue or music | The narration is VideoWizard's own; the server appends this line to every video prompt. |
| `placement` from the channel sheet | The brief's frame (`production.format.frame`), default 16:9 | design/53 L7. Images default to 1536×864, `high`. |
| Logo `reserve` | Never drawn, no reserved area unless the plan asks for one | The editor places the logo in Resolve (design/49 L9). |
| `checked_by` person or auto | Always person: the operator's yes or no, with their words | design/02 decision 10. |
| The application writes the feedback record | The VideoWizard server writes it from the stored request, answer and verdict | One flow, two front ends. |

## Fixed lines the server appends (do not repeat them in a prompt)

Every video prompt gets: the subject reconciliation, the continuity notes, the requested duration, "Use the first image as the starting frame", the end-frame line when one is sent, and "Do not render editorial captions or overlay text into the video. Do not create narration, dialogue or music. Preserve the depicted identities." (`video_providers.motion_text`).
