# VideoWizard map: which library files each picture step opens

This file stands in for the library's `INDEX.md` inside VideoWizard. Where `RULEBOOK.md` says "open only what INDEX.md says", read "what this map says". Everything not in this bundle is the library's shelf and is never opened during a run. A file or section named in a library file but not in this bundle (for example `DIRECTION.md` section 5d, `gallery/README.md`, `seedance.md`, `kling.md`, `veo.md`) is not available: work from what is here.

## Always open, for every generated picture or take

| File | Why |
| --- | --- |
| `library/RULEBOOK.md` | The rules for every job. |
| `library/forms/answer-form.videowizard.md` | The shape of the answer and the lint before `ready`. RULEBOOK section 17's ten rules are the lint table in this file. |
| `library/agency/deterministic-checks.md` section 1 | The vague-word replacement table (RULEBOOK rule 2). |

## Per step

| VideoWizard step (command) | Library task | Playbook | Model sheet | Open when |
| --- | --- | --- | --- | --- |
| Reference of a person, object or place, generated (`vw visuals image --kind isolated` or `sheet`) | `continuity-kit` | `playbooks/video-frame.md` | `models/gpt-image/FACT-SHEET.md` | A person: `video/consistent-character-frames.md` Section 1 (the variable table, to describe the person) |
| Frame grab from a clip (`vw visuals frame`) | none: no prompt is written | — | — | Choosing the frame for a gap: `video/gap-fill.md` section 3 |
| AI still for an image shot: a scene (`image --kind keyframe`, then `still`) | `keyframe` | `playbooks/video-frame.md` | `models/gpt-image/FACT-SHEET.md` | `video/craft/animatic-keyframes.md` (the keyframe card); next to real footage: `video/gap-fill.md`; a real photograph look: `00-method/de-slop.md` |
| AI still for a diagram shot: a labelled picture with words only (`image`, then `still`) | `process-explainer` | `playbooks/web-app.md` (process-explainer) | `models/gpt-image/FACT-SHEET.md` | `00-method/craft.md` section 5 (diagram grammar); `prompts/05-information.md` |
| Graphic sequence for an animation shot (`image --kind state --parents R`, then `sequence`) | `graphic-states` | `video/diagram-in-states.md` | `models/gpt-image/FACT-SHEET.md` B5 | `00-method/craft.md` section 5 |
| Start image of a video shot (`image --kind keyframe`) | `keyframe` | `playbooks/video-frame.md` | `models/gpt-image/FACT-SHEET.md`, and the Omni sheet A5 for its accepted size | `video/craft/animatic-keyframes.md`; next to real footage: `video/gap-fill.md`; a person: `video/consistent-character-frames.md` Section 1 |
| End image of a video shot, only where the final state must be exact (`end_prompt`, `end_answer`, `end_region`, written with the start) | `first-last-frame` | `playbooks/video-frame.md` | as above | `video/gap-fill.md` section 3 |
| Video take (`prepare-take`, `take`) | `clip-from-frame` | `playbooks/video-clip.md` | `video/models/gemini-omni-1-1/FACT-SHEET.md` | `video/craft/camera-lighting-vocabulary.md`; next to real footage: `video/gap-fill.md`; a faceless explainer: `video/still-to-motion-pipeline.md` |
| Any step, when the client's industry carries compliance lines (healthcare, education, real estate, finance, restaurant) | — | — | — | `agency/compliance-checklist.md` |

Five to nine files per step, as the library intends.

## Where VideoWizard overrides the library

These win over the rulebook, the playbooks and the fact sheets inside VideoWizard, because the server decides them.

| Library says | VideoWizard does | Why |
| --- | --- | --- |
| GPT Image or Nano Banana per job (video-frame, web-app and diagram-in-states playbooks; de-slop section 2) | The film's picture AI, GPT Image or Nano Banana, chosen when the film is created, makes every picture of that film. The server picks the model, the size, the input limits and the background; write the picture, never the model's settings. | The run's image model (`visuals_stage.provider_of`). |
| Images at a chosen quality; `medium` for photographic stills (de-slop section 6); start at `medium`, step down once it passes (GPT Image sheet B9); Flare for drafts | Picture quality is the server's: always high. Never pass `--quality`; no medium pictures, no drafts. | SK's decision. |
| A choice of video model (Omni, Seedance, Kling; video-clip section 2, RULEBOOK 1.4) | Gemini Omni only, direct from Google. Every take is 3 to 10 seconds; a longer passage is split into shots of up to 10 seconds, cut where an action begins or ends. Lines in the bundle about Seedance, Kling or Veo do not apply. | The server's catalog (`video_generators.CATALOG`). |
| Each video model's own prompt shape and tags (video-clip section 5's Seedance template, `@Image 1` roles, timed windows) | One request shape for every video take: Omni's, built by the server around the motion brief (see "Fixed lines" below). | SK's decision. |
| The clip prompt carries the camera move, the audio, the single-scene line and the length (RULEBOOK 16.2, video-clip sections 4 and 5; Omni sheet A2 "the prompt is sent exactly as Claude writes it") | The motion brief is only what the subjects and the surroundings do. Never write the picture tags, a Camera line, an Audio line, the one-take line or the length: the server writes them from the plan and wraps the brief in them. | `video_providers.motion_text`. |
| Audio described, dialogue in quotes, several shots in one generation, named transitions, timed cuts (RULEBOOK 16.5-16.6, video-clip sections 2 and 7, camera-lighting-vocabulary sections 8 and 11) | Never. Every take is one unbroken shot with no sound, no dialogue, no music, no cuts and no transitions. The narration is VideoWizard's own. | The server adds the line and sends no sound. |
| A handheld or moving camera to match the footage (gap-fill section 2, video-clip UGC style, the theme's motion language) | Steady: a take is locked off on a tripod unless the shot's `camera_move` names its one move. Do not ask for handheld movement or micro-shake. | SK's decision; the server writes the Camera line from `camera_move`. |
| A first and a last frame for every move; the camera moving between them (video-frame section 4, first-last-frame) | A start image for every video shot; an end image only where the final state must be exact. The end is written together with the start as `end_prompt` (with `end_answer` and `end_region`): an edit inside one region of the start, same framing, no camera move. The server makes it after the operator approves the start; no end is made from a start that is still a candidate. | Decision 9 (design/124). |
| A person's reference picture sent with every call; a footage frame of a person as a reference (consistent-character-frames Principles 1, gap-fill section 3, video-frame section 3.3) | A person's sheet is made from words: look at the person's footage pictures and describe them (build, age, posture, garments and how they are worn, hair; the variable table of consistent-character-frames Section 1 is the checklist). Never send a footage or web picture of a person to the picture AI. Objects and places keep their footage pictures as parents. | Decision 5 (design/124). |
| Nine-photo series, three style presets, batch generation, a 3:4 frame, fixed front/side/back views (consistent-character-frames, craft section 7, video-frame section 4) | One sheet at the film's frame showing the plan's `required_views`, each labelled, alone on plain ground; one picture per call; the style comes from the approved style picture. | The server's sheet request. |
| Edits: "one change per turn" (RULEBOOK 8.1) | One change per edit. A second change goes in a second edit of the result; the server refuses a "Change only" that names two. | `library.check_prompt`. |
| Exact words in quotes (RULEBOOK 4.1, craft section 1, diagram-in-states section 6) | Words to be read in the picture go only in the answer's `exact_text`, each with its place and size. Quote nothing else in a prompt; a keep-list names labels without quotes. | `library.check_quoted`, `check_exact_places`. |
| Charts, data visualisation, measured diagrams (craft section 5, `prompts/05-information.md` P027) | A number, size or count in a graphic takes the drawn route; an AI graphic carries words only, never a chart or a figure. | The plan check. |
| "Centre", "middle", "left third" as a place | A place is a landmark and a measured distance in a unit the picture shows (bricks, paces, a hand, a doorway); "centre" alone is refused. | `library.check_prompt`. |
| A model name in the prompt (video-frame section 5's "for {video model}") | Never write a model name in a prompt; the server refuses it. | RULEBOOK 13; `library.check_prompt`. |
| Storyboard grids, cover frames, handoff notes in the answer | Not used | VideoWizard plans shots in the visual plan, not in a storyboard image; the plan carries the shot, the seconds and the camera. |
| Draft at low size, then final | One generation per attempt at the film's size | The operator approves each result. |
| `placement` from the channel sheet | The brief's frame (`production.format.frame`), default 16:9 | The server sets the size from the frame. |
| Logo `reserve` | Never drawn, no reserved area unless the plan asks for one | The editor places the logo. |
| `checked_by` person or auto; a second person signs the compliance checklist | Always person: the operator's yes or no, with their words; the operator alone signs. | One operator per film. |
| Compliance C09 (consent ids) | Met by sending no real person's picture (decision 5). | Decision 5 (design/124). |
| Compliance C03 and C18 (the sector's mandatory text) | Not checked here: the job form's `mandatory_text` is always none; the client's mandatory wording does not come from the client card. | SK's decision. |
| The application writes the feedback record | The VideoWizard server writes it from the stored request, answer and verdict | One flow, two front ends. |

## Fixed lines the server writes around every motion brief (never repeat them in a prompt)

`video_providers.motion_text` sends, in this order:

1. The picture tags: `[# Sources <FIRST_FRAME>@Image1]`, or `[# Sources <FIRST_FRAME>@Image1 <LAST_FRAME>@Image2]` when an end image is sent.
2. The motion brief, as the assistant wrote it.
3. When the shot has ambient life: "Throughout the shot the surroundings stay alive: {ambient}."
4. "Natural, unhurried motion; no sudden, exaggerated or floating movement."
5. "Subject reconciliation:" and the shot's subject reconciliation.
6. "Continuity: {continuity notes}"
7. The person lines (the fixed layer and the scene's colours), when there are people.
8. The Camera line from the plan's `camera_move`: "Camera: {move}; nothing else about the frame changes." or "Camera: locked off on a tripod; the frame does not move, drift, zoom or slide."
9. The gaze, heading, tool and fixed-position lines, when the plan has them.
10. When the plan names the light: "The light does not change: {light}."
11. "In a single unbroken scene, one continuous shot, no scene cuts, no jump cuts. No dialogue. No music. No captions or overlay text."
12. "Use Image1 as the starting frame. Preserve the depicted identities." or, with an end image, "Use Image1 as the starting frame and Image2 as the final frame; the transition follows the action above. Preserve the depicted identities."
13. The length: "{n}s".
