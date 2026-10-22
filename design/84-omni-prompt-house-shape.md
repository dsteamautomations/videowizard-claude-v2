# design/84 — The take's text follows the library's Omni rules: one unbroken shot, the frame tags, the continuity line

Status: requirements note, builder, 22 Oct 2026, from SK's look at VW-6's seven takes ("missing continuity and some images appearing suddenly in a shot that was not previously present") and the check in `ai-video-pipeline-2026-10-22.md`. Waits for SK's go. Sources: `video_providers.motion_text`, `visuals_stage.prepare_take`, `packet`, the library's Omni fact sheet B1, B2, B7, B9, B11.

## What is wrong

The server's wrapper around the motion prompt was written in design/45, before the library. It does not say what the fact sheet says every Omni job must say: Omni Flash cuts to several shots by default unless told "in a single unbroken scene, no scene cuts" (B2); the pictures are bound to their roles with `<FIRST_FRAME>` and `<LAST_FRAME>` tags (B7); the continuity line holds the identity between the frames (B1). On VW-6 all seven takes went out without the single-shot sentence, without tags, and with an empty continuity line.

| | Change | Where |
|---|---|---|
| V1 | `motion_text` builds the house shape: `[# Sources <FIRST_FRAME>@Image1 <LAST_FRAME>@Image2]` (or `<FIRST_FRAME>@Image1` alone when there is no end), the motion prompt, `Continuity: {notes}`, `In a single unbroken scene, one continuous shot, no scene cuts, no jump cuts.`, `No dialogue. No music. No captions or overlay text.`, `Use Image1 as the starting frame and Image2 as the final frame; the transition follows the action above. Preserve the depicted identities.`, `{N}s`. The subject reconciliation stays as a JSON line after the motion prompt. | `video_providers.motion_text` |
| V2 | `prepare_take` refuses empty continuity notes (what stays unchanged between the frames; for a person, five traits from the sheet). The plugin's `--continuity` is required for a video shot; `prepare-take --file` rows carry it. | `visuals_stage.prepare_take`, `vw.py` |
| V3 | The packet's `video_instruction` adds: "The take is one unbroken shot: write the motion so nothing new enters the frame that the start or the end does not show. Write the continuity line: what stays unchanged, and for a person five traits from the sheet." The step text says the same. | `packet`, step 4 |
| | Server 0.31.0, plugin 0.29.0. The prepared snapshots of VW-6's seven takes keep their old text (`effective_prompt` is not stored, so a re-prepare picks up the new wrapper); regenerating them is SK's call, about ₹440. | |

Tests first: `test_visual_workers_pure.py` or a new `test_video_providers_pure.py`: `motion_text` with two images carries the tags, the single-shot sentence, the continuity line, the N s; with one image, the first-frame tag alone. `test_visuals_stage_pure.py`: `prepare_take` refuses empty notes. `test_visuals_cli.py`: the step and the command text name the rule. Not covered: the model's behaviour (VW-6's regenerated takes are the check); server/tests (Docker).
