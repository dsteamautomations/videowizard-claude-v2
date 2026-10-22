# Answer form, VideoWizard cut

Status: the VideoWizard variant of `answer-form.md`, 22 Oct 2026 (design/69, approved by Revathi). Inside VideoWizard the server fixes the model, the settings, the size, the pictures sent and their order, the wait, the file names and the spend check, and writes the feedback record from what it stores. So the answer keeps only what the assistant alone knows. Outside the manifest until the master adopts it. The master library's form is untouched.

## Three possible answers

| `status` | Meaning | What else is filled |
| --- | --- | --- |
| `ready` | A prompt is written and can be sent. | The fields below. |
| `needs_input` | Something required is missing or contradictory. Nothing is sent; settle it in chat. | `questions` only. |
| `refused` | The job cannot be done under our rules. Nothing is sent; the picture is dropped. | `reason`, `detail`. |

## The fields of a `ready` answer

| Field | What it is |
| --- | --- |
| `answer_id` | The assistant's id for this answer; the version in the file name. |
| `playbook_version` | The version of the playbook the step opened. |
| `files_opened` | The library files read for this job: tells the maintainer what the router opened. |
| `prompt` | The full text, exactly as sent. The server checks it is the prompt sent. |
| `exact_text` | The copy strings that must appear in the image, one per line, letter for letter. The server checks each is in the prompt. |
| `keep_list` | Per input picture id: the things in it that must not change, as nouns a checker can tick. |
| `checklist` | One line per thing a checker can see: `check`, `pass_when`, `weight` (`must` or `should`). At least one `must` line; the operator's verdict is ticked against it. |
| `lint` | The six presence checks, each `true` or `false`: banned phrases removed, composition, lighting, typography, materials, reference policy specified. |
| `risk_flags` | Optional. What is likely to go wrong with this prompt on this model, from the fact sheet's failure table. |
| `compliance_flags` | Optional. Only when the client card's industry carries compliance lines, by id and name. |
| `rewrites_made` | Optional. Vague words replaced, with the replacement. |
| `suggestion` | Optional. One line when a library rule helped, failed or was missing, naming the file and section. Copied into the feedback record. |
| `base_image_id`, `single_change` | On a fix round only: the picture the edit starts from, and the one change this prompt makes, in one sentence. |

About fifteen fields. Dropped from the full form because the server has them: `job_id`, `round`, `playbook_used` (the job form), `seen`, `tag_ok`, `warnings` (the pictures are the assistant's own approved references), the model and settings, the pictures to send and their order, `fixed_lines_present` (the server adds the video lines), `wait`, `output_name`, `save_beside`, `then`.

## `needs_input`

`questions`: a list, most important first, one question each: `field`, `question`, `why`, `options`. At most five. `can_proceed_with_defaults` as in the full form.

## `refused`

`reason`: `no-consent`, `policy`, `rights`, `impossible`. `detail`: one or two lines. `nearest_thing` if any.

## The lint before `ready`, under this cut

| Rule | Who checks |
| --- | --- |
| 1 required job-form fields present | The server fills the form. |
| 2 every copy string in the prompt in quotes; the standing no-extra-text line present | `exact_text` by the server; the no-extra-text line is the assistant's (presence check 1). |
| 3 no logo asked | The server refuses a prompt that asks for a logo. |
| 4 the aspect matches the placement | The server sets the size from the brief's frame. |
| 5 every picture sent has a role sentence; counts within limits | The server caps the inputs at 16; the role sentence is the assistant's. The end image names its pictures: Image 1 is the start, images 2 onward its identity sheets. |
| 6 every `person` picture has a consent id | No consent ids exist in VideoWizard; a real face is a look reference only, never edited. |
| 7 no banned phrase; the six presence checks | The assistant's, declared in `lint`. |
| 8 no model name, size or resolution inside the prompt | The server refuses the prompt with the offending word. |
| 9 fix round: one change, one keep-list, the base named | `single_change`, `keep_list`, `base_image_id`. |
| 10 the estimated cost under the spend cap | The server's cap check. |

Fails once, repair once. Fails twice, the answer is `needs_input` with the failing rule named.

## Example, status ready

```json
{
  "status": "ready",
  "answer_id": "v01",
  "playbook_version": "0.1",
  "files_opened": ["always/RULEBOOK.md", "start/playbooks__video-frame.md", "start/models__gpt-image__FACT-SHEET.md"],
  "prompt": "Image 1 is the start image; images 2 onward are its identity sheets: take identity from them, nothing else. The mason, now one step to the left of the wall's near corner, facing the camera, holds the brick above the wet mortar bed; the bucket by the doorway is empty. Same framing, camera, light, people and props. Render only explicitly requested image text; there is none.",
  "exact_text": [],
  "keep_list": {"K1": ["the wall's near corner", "the doorway", "the mason's blue shirt", "overcast yard light"]},
  "checklist": [
    {"check": "the mason's position against the near corner", "pass_when": "one step left of it, facing camera", "weight": "must"},
    {"check": "the bucket", "pass_when": "by the doorway, empty", "weight": "must"},
    {"check": "framing, camera and light", "pass_when": "identical to Image 1", "weight": "must"}
  ],
  "lint": {"bannedPhrasesRemoved": true, "compositionSpecified": true, "lightingSpecified": true, "typographySpecified": true, "materialsSpecified": true, "imageReferencePolicySpecified": true},
  "suggestion": "video-frame.md section 4: say that the end image is edited at the start's own size."
}
```
