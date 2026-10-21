# Higgsfield: Kling 3.0 and Seedance 2.5 as VideoWizard calls them

Written 2026-10-21. Status: **draft, untested, for SK's decision.** This is not a fact sheet. The library's rule is that facts move into a fact sheet only once they are checked against the provider's own documentation, with a date. Nothing here has been checked against Higgsfield's pages. Every fact below comes from the VideoWizard server code (`server/app/video_providers.py` and `video_generators.py`, server 0.21.3) and says what VideoWizard sends, not what Higgsfield accepts.

## 1. Why this note exists

`models/CHOSEN-MODELS.md` (SK's decision) reaches Seedance 2.5 through OpenRouter, "because ByteDance's own API is not open to Indian users", and treats Kling as a watch item for 4.0. VideoWizard already calls **Kling 3.0 Standard** and **Seedance 2.5** through **Higgsfield**. Prompts written from the library for VideoWizard need to know the route they will travel. SK decides whether Higgsfield becomes a chosen route.

## 2. What VideoWizard sends today

| Item | Kling 3.0 Standard | Seedance 2.5 |
| --- | --- | --- |
| Model path | `kling-video/v3.0/std/image-to-video` | `bytedance/seedance-2.5/image-to-video` |
| Mode | Image to video only; a start image is required | Image to video only; a start image is required |
| Length | 3 to 15 s, whole seconds (`duration`) | 4 to 30 s, whole seconds (`duration`) |
| End image | `last_image_url` | `end_image_url` |
| Audio | `sound: off` | `generate_audio: false` |
| Cuts | `multi_shots: false` | none sent; the prompt carries the one-take line |
| Resolution | none sent | `resolution` from the run |
| Aspect | none sent; follows the start image | none sent; follows the start image |
| Images | Uploaded to Higgsfield storage first; public URLs sent | same |
| Prompt | The motion brief, plus fixed lines VideoWizard appends (below) | same |

The fixed lines VideoWizard appends to every video prompt: the subject reconciliation, the continuity notes, "Requested duration: N seconds. Use the first image as the starting frame.", the end-frame line when one is sent, "Do not render editorial captions or overlay text into the video. Do not create narration, dialogue or music. Preserve the depicted identities." A library prompt must not repeat or contradict these.

## 3. How the library sheets apply

- **Seedance sheet (OpenRouter).** The wording habits in Part B (one action per window of 3 s or more, stated end states, the one-take line, reference roles) are about the model and should carry over. Part A (request fields, prices, limits) is OpenRouter's and does **not** apply to Higgsfield. One known difference: on Higgsfield, VideoWizard sends no reference pictures besides the start and end frames.
- **Kling sheet.** It describes Kling 4.0 (watch) and Kling 3 by search snippet. Its wording habits (section 3) are the best guide available. Its access and price lines do not cover Higgsfield.
- **Playbook video-clip.** The motion brief (section 4) and the Seedance prompt shape apply. Drop the audio line from the prompt, since VideoWizard switches audio off in the settings and appends "no narration, dialogue or music".

## 4. Open questions for SK

1. Is Higgsfield a chosen route? If yes, `models/CHOSEN-MODELS.md` gains a row, and this note becomes a fact sheet after a check against Higgsfield's documentation.
2. Prices per second on Higgsfield for both models, needed for VideoWizard's ₹1,000 visuals cap (design/65 B7).
3. Does Higgsfield's Seedance accept reference images beyond the first and last frame? If so, VideoWizard could send element references as the OpenRouter sheet describes.
4. Kling 3.0 Standard against Pro on Higgsfield: is Pro available and worth it?
