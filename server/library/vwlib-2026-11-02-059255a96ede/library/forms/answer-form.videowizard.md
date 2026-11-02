# Answer form

The server fixes the model, the settings, the size, the pictures sent and their order, and writes the feedback record. The answer holds only what the assistant alone knows. It is the same for every video category.

## General: every category

### Three possible answers

| `status` | Meaning | What else is filled |
| --- | --- | --- |
| `ready` | A prompt is written and can be sent. | The fields below. |
| `needs_input` | Something required is missing or contradictory. Nothing is sent; settle it in chat. | `questions` only. |
| `refused` | The job cannot be done under our rules. Nothing is sent; the picture is dropped. | `reason`, `detail`. |

### The fields of a `ready` answer

| Field | What it is |
| --- | --- |
| `answer_id` | The assistant's id for this answer; the version in the file name. |
| `playbook_version` | The version of the playbook the step opened. |
| `files_opened` | The library files read for this job. |
| `prompt` | The full text, exactly as sent. The server checks it is the prompt sent. |
| `exact_text` | One entry per string to be read in the picture: `text` (letter for letter; never quoted in the prompt, the server adds it), `place` (`landmark_id`, a landmark of the scene, or `region`, a region of the frame) and `size_pct` (its height as a percent of the frame height). Quoted words in the prompt are refused. |
| `keep_list` | Per input picture id: the things in it that must not change, as nouns a checker can tick, labels named without quotes. |
| `checklist` | One line per thing a checker can see: `check`, `pass_when`, `weight` (`must` or `should`). At least one `must` line; the operator's verdict is ticked against it. |
| `lint` | The six presence checks, each `true` or `false`: banned phrases removed, composition, lighting, typography, materials, reference policy specified. |
| `risk_flags` | Optional. What is likely to go wrong with this prompt on this model, from the model sheet's failure table. |
| `compliance_flags` | Optional. Only when the client's industry carries compliance lines, by id and name. |
| `rewrites_made` | Optional. Vague words replaced, with the replacement. |
| `suggestion` | Optional. One line when a library rule helped, failed or was missing, naming the file and section. |
| `base_image_id`, `single_change` | On a fix round only: the picture the edit starts from, and the one change this prompt makes, in one sentence. One change per edit. |

### `needs_input`

`questions`: a list, most important first, one question each: `field`, `question`, `why`, `options`. At most five. `can_proceed_with_defaults`: `true` when the job could run on defaults and the questions are only improvements; `false` when it cannot.

### `refused`

`reason`: `no-consent`, `policy`, `rights`, `impossible`. `detail`: one or two lines. `nearest_thing` if any.

### The lint before `ready`

| Rule | Who checks |
| --- | --- |
| 1 required job-form fields present | The server. |
| 2 every string to be read is an `exact_text` entry with its place and size; the standing no-extra-text line is in the prompt | `exact_text` by the server; the line by the assistant. |
| 3 no logo asked | The server. |
| 4 the frame matches the brief | The server sets the size. |
| 5 every picture sent has a role sentence | The assistant. An end image names its pictures: Image 1 is the start, images 2 onward its identity sheets. |
| 6 no real person's picture sent | The server: a person is described in words. |
| 7 no banned phrase; the six presence checks | The assistant, declared in `lint`. |
| 8 no model name, size or resolution in the prompt | The server refuses it. |
| 9 fix round: one change, one keep-list, the base named | `single_change`, `keep_list`, `base_image_id`; the server refuses a second change. |
| 10 the estimated cost | The server; the operator approves each result. |

Fails once, repair once. Fails twice, the answer is `needs_input` with the failing rule named.

### Example: an end image, status ready

```json
{
  "status": "ready",
  "answer_id": "v01",
  "playbook_version": "0.1",
  "files_opened": ["library/RULEBOOK.md", "library/playbooks/video-frame.md", "library/models/gpt-image/FACT-SHEET.md"],
  "prompt": "Image 1 is the start image; images 2 onward are its identity sheets: take identity from them, nothing else. Change only the mason's hands: they now hold the brick just above the wet mortar bed. The mason stays one step to the left of the wall's near corner, facing the camera. Same framing, camera, light, people and props. Render only explicitly requested image text; there is none.",
  "exact_text": [],
  "keep_list": {"K1": ["the wall's near corner", "the doorway", "the mason's blue shirt", "the mason's position", "overcast yard light"]},
  "checklist": [
    {"check": "the brick", "pass_when": "held in both hands just above the mortar bed", "weight": "must"},
    {"check": "the mason's position against the near corner", "pass_when": "one step left of it, facing camera, as in Image 1", "weight": "must"},
    {"check": "framing, camera and light", "pass_when": "identical to Image 1", "weight": "must"}
  ],
  "lint": {"bannedPhrasesRemoved": true, "compositionSpecified": true, "lightingSpecified": true, "typographySpecified": true, "materialsSpecified": true, "imageReferencePolicySpecified": true},
  "suggestion": "playbooks/video-frame.md, The end image: say that the end is edited at the start's own size."
}
```
