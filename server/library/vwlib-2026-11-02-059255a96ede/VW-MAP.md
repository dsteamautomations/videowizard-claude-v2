# VideoWizard map: which guidebooks each picture step reads

This file stands in for the library's index inside VideoWizard. Where `RULEBOOK.md` says "open only what the index says", read "what this map says". Nothing outside this bundle is opened during a run.

**Every category of video.** VideoWizard serves documentaries and explainers, advertisements and product films, training, social clips and stories. Each guidebook has a general part and short parts by category; a step is given the general part and its film's own category part only. Parts marked "not available yet" are never given: they wait for a category VideoWizard does not make today.

## Always open, for every generated picture or take

| File | Why |
| --- | --- |
| `library/RULEBOOK.md` | The rules for every job. |
| `library/forms/answer-form.videowizard.md` | The shape of the answer and its lint before `ready`. |
| `library/agency/deterministic-checks.md` | Vague words into visible facts; what every picture prompt says. |

## Per step

| VideoWizard step (command) | Guidebooks |
| --- | --- |
| Reference of a person, object or place (`vw visuals image --kind isolated` or `sheet`) | `playbooks/video-frame.md` (reference sheets); the picture model's sheet; for a person, `video/consistent-character-frames.md` |
| Frame from a clip (`vw visuals frame`): no prompt is written | `video/gap-fill.md` (choosing the frame) |
| AI still for an image shot (`image --kind keyframe`, then `still`) | `playbooks/video-frame.md` (the still card); the picture model's sheet; next to real footage, `video/gap-fill.md`; a real-photograph look, `00-method/de-slop.md` |
| AI still for a labelled picture without figures (`image`, then `still`; rare on motion films) | `playbooks/web-app.md`; the picture model's sheet; `00-method/craft.md`; `prompts/05-information.md` |
| Graphic sequence for an animation shot (`image --kind state --parents R`, then `sequence`) | `video/diagram-in-states.md`; the picture model's sheet; `00-method/craft.md` |
| Start image of a video shot (`image --kind keyframe`) | `playbooks/video-frame.md`; the picture model's sheet; next to real footage, `video/gap-fill.md`; a person, `video/consistent-character-frames.md` |
| End image, only where the final state must be exact (`end_prompt`, `end_answer`, `end_region`, written with the start) | `playbooks/video-frame.md` (the end image); the picture model's sheet; `video/gap-fill.md` |
| Video take (`prepare-take`, `take`) | `playbooks/video-clip.md`; `video/craft/camera-lighting-vocabulary.md`; `video/models/gemini-omni-1-1/FACT-SHEET.md`; next to real footage, `video/gap-fill.md`; a faceless explainer, `video/still-to-motion-pipeline.md` |
| Any step, when the client's industry carries compliance lines | `agency/compliance-checklist.md` |

## What the server decides (these win over any guidebook)

| VideoWizard does | Why |
| --- | --- |
| The film's picture AI (GPT Image or Nano Banana), chosen when the film is created, makes every picture of that film; the server sets the model, size, quality (always high) and the pictures sent. Never write them in a prompt, and never pass `--quality`. | One look per film; `library.check_prompt`. |
| Gemini Omni makes every take, 3 to 10 seconds; a longer passage is several shots, cut where an action begins or ends. | SK's decision. |
| The motion brief is only what moves; the server writes the rest of the video request (see below). | One request shape. |
| Every take is one unbroken, silent shot: no sound, dialogue, captions or cuts. | The film's sound is the narration. |
| The camera is locked off unless the shot's `camera_move` names its one move. | Takes sit between steady footage. |
| A start image for every video shot; an end image only where the final state must be exact, an edit of the approved start in one region, with no camera move between them. | design/112, design/124. |
| A person is described from words, never from a reference photo; one sheet at the film's frame with the plan's `required_views`. | Decision 5 (design/124). |
| One change per edit; a second change is a second edit of the result. | `library.check_prompt`. |
| Words to be read in a picture go only in the answer's `exact_text`, with place and size; nothing else is quoted. | The server writes them in and checks them. |
| A labelled diagram, a chart or anything carrying a number is drawn (HyperFrames on a motion film); an AI picture carries no figures. | The plan check. |
| A place is a landmark and a distance the picture shows; "centre" alone is refused. No model name in a prompt. | `library.check_prompt`. |
| Logos are never drawn; the editor places them. The operator alone approves, with their words; the server writes the record. | One operator per film. |

## Lines the server writes around every motion brief (never repeat them)

`video_providers.motion_text` sends, in this order:
1. The picture tags (`<FIRST_FRAME>@Image1`, and `<LAST_FRAME>@Image2` with an end image).
2. The motion brief, as written.
3. The plan's timeline: each beat with its seconds, then "Then hold until N s." when the take is longer; and the end state: "By the end and until the last frame: …; each stays where it is, in plain view."
4. The ambient life, when the shot has it.
5. "Natural, unhurried motion; no sudden, exaggerated or floating movement."
6. The subject reconciliation and the continuity notes.
7. The person lines, when there are people.
8. The camera line from `camera_move`, or "locked off on a tripod".
9. The gaze, heading, tool and fixed-position lines, when the plan has them.
10. The light, when the plan names it.
11. "In a single unbroken scene, one continuous shot, no scene cuts, no jump cuts. No dialogue. No music. No captions or overlay text."
12. The pictures' roles ("Use Image1 as the starting frame …") and the length.
