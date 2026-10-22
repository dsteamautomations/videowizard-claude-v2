# design/71 — The six library points the server must own (L30), and the VideoWizard answer form (design/69)

Status: requirements note, builder, 22 Oct 2026. SK on 22 Oct: "I want to fix all the observations in L30"; design/69 approved by Revathi. For SK's approval, held until SK's review of the first VW-6 images (22 Oct); nothing built. Sources: design/70 §5b, design/69, the GPT Image 2.5 fact sheet (A4 sizes, A5 inputs, A7 errors), the Omni sheet (A5), `visuals_stage`, `visual_workers`, `stage3/assembly`, `stage2/render`.

## 1. What changes, item by item

| | Change | Where |
|---|---|---|
| P1 | **The end image names its pictures.** The packet's end instruction says: "Image 1 is the start image; images 2 onward are its identity sheets, sent by the server: take identity from them, nothing else." The server refuses an end keyframe (a keyframe with a keyframe parent) whose prompt does not name "Image 1". | `visuals_stage.packet`, `generate_image` |
| P2 | **A cap of 16 inputs.** After the start's sheets are appended, more than 16 parents is refused with the count. | `generate_image` |
| P3 | **Sizes.** The default image size follows the brief's frame: 16:9 → 1536×864 (as today), 9:16 → 1088×1936 (the sheet's working value; 1080×1920 fails the multiple-of-16 rule). An edit whose first parent is a keyframe or a frame takes that parent's size when it is a multiple of 16 on both sides, else the frame default. `prepare_take` refuses a start and end whose aspect ratios differ by more than one percent: a 1920×1080 frame and a 1536×864 edit share 16:9 and pass; the generators publish no pixel limit and set the output aspect themselves. | `generate_image`, `prepare_take`, `default_aspect` |
| P4 | **A dissolve at a shared boundary.** When a gap is recorded, each take shot keeps its start and end reference ids. At assembly, two consecutive take fills of one gap where the first's end image is the second's start image are joined by a six-frame dissolve: the first segment is rendered six frames longer from the take's spare tail, the two are cross-faded, the timeline length is unchanged. No spare tail, or a different boundary, means a cut as today; the prepare listing says which. | `visuals_stage.record_gap`, `assembly.prepare/build/render`, `render.Renderer.dissolve_pair`, `render_film` |
| P5 | **A refused picture says why.** The worker reads OpenAI's error body: `moderation_blocked` becomes "OpenAI refused the pictures or the prompt (moderation, stage <input/output>, <categories>). A frame with a recognisable face cannot be edited: use it as a look reference only, pick a frame without a face, or change the prompt." `image_generation_user_error` becomes "the prompt or the pictures are the problem; do not resend unchanged". The visuals prompt's reference passage says a frame showing a face is a look reference, never a parent. | `visual_workers.process_image`, the prompt |
| P6 | **A retry starts from an approved picture.** The prompt and the steps say: after a drift or a rejection, the next end image is made from the approved start, not from the candidate chain; a graphic state is retried from the last approved state. The server check follows in part B, when a picture reject exists (design/68 §5). | the prompt, the steps |
| F1 | **The VideoWizard answer form** (design/69 §3), as a file beside the original in the snapshot folder: `library/forms/answer-form.videowizard.md`, outside the manifest (the manifest check reads only listed files; the master adopts it in the next snapshot). The always-open set names it instead of `answer-form.md`; the plugin writes it; the prompt's paragraph says "the library's VideoWizard answer form". `warnings` dropped with `seen` and `tag_ok` (design/69 Q2 as proposed). | `server/library/<version>/library/forms/`, `library.ALWAYS`, the prompt |
| F2 | **Two lint rules move to the server** (design/69 §4, rules 3 and 8), on every prompt, with or without an answer form: a prompt that asks for a logo is refused; a prompt that names a model (`gpt-image`, `sunburst`, `flare`, `omni`, `kling`, `seedance`), a pixel size (`1536x864` and the like) or a resolution (`720p`, `1080p`) is refused with the offending word. | `library.check_prompt`, `generate_image`, `prepare_take` |
| | Server 0.26.0, plugin 0.24.0 (the always-open file name). | |

## 2. Not changed

The three composition instructions beyond P1's sentence; the plan schema; the cap; the page; the generators. P6 stays a rule in words until part B gives the server a picture reject to key on.

## 3. Tests first

- `test_library.py`: `check_prompt` refuses a logo request, a model name, a pixel size and a resolution, each naming the word, and passes a clean prompt; the always-open set names the VideoWizard form and the file exists; `default_size` gives 1536×864 for 16:9 and 1088×1936 for 9:16; the parent-size rule takes 1536×864 and refuses 1920×1080 back to the default.
- `test_visuals_stage_pure.py`: an end keyframe without "Image 1" is refused and with it passes; 17 parents after inheritance are refused; `prepare_take` refuses a 16:9 start with a 9:16 end and accepts a 1920×1080 frame with a 1536×864 end; `record_gap` writes the take's start and end ids; the packet's end instruction carries the numbering sentence.
- `test_stage2_pure.py` and an assembly pure test: two fills sharing a boundary with a spare tail get `dissolve_into_next` 6 and the pair renders to exactly n1 + n2 frames; without a spare tail they get 0; a boundary that is not shared gets 0.
- `visual_workers`: a 400 with `moderation_blocked` and one with `image_generation_user_error` give the two messages; another 400 keeps today's.
- Plugin: the always-open file lands under `work/visuals/library/always/`.
- The prompt within 3,500 words; the compile checks.

## 4. Not covered

server/tests (Docker); whether Omni, Kling and Seedance accept a 1920×1080 start with a 1536×864 end (same aspect) without re-framing, which the first such take on VW-6 shows; the dissolve's look on real takes; the form variant until the master adopts it.

## 5. Order

SK's approval → tests → change → compile checks → commit and push → tell SK → deploy the server (0.26.0, the workers restart) and the plugin (0.24.0, SK restarts the operator's Claude Code) → design/35 row, design/49 line. SK's review of the first images may add items; they join this note before approval or follow as design/72.
