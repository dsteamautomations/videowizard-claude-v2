# design/77 — The VW-6 pass fixes: L33, L35, L38, L39, L41

Status: requirements note, builder, 22 Oct 2026; SK the same day: "you can [start] development activity for the pending issues". Built one item at a time, deployed together with design/76 and design/73 when SK pauses VW-6. Sources: the pass findings (vw6-pass-findings-2026-10-22.md, design/49 of 22 Oct), the exported prompts (vw6-image-prompts-2026-10-22.md), `visuals_stage`, `visual_contract`, `vw.py`, the prompt and steps.

## 1. What changes, item by item

| | Change | Where |
|---|---|---|
| L33a | **A still shot needs no bind.** Step 5 and the prompt say: still shots take `still` with an approved picture; `bind` and `packet` are for video shots. | step 4, the prompt |
| L33b | **Batch calls.** `vw visuals still --file out/stills.json` (a list of `{shot, ref, quote}`), `vw visuals bind --file out/bindings.json` (a list of `{shot, refs, selectors}`), `vw visuals approve --file out/approvals.json` (a list of `{ref, sha, quote}`): one call each, in order, stopping at the first refusal as `image --file` does; the server functions are unchanged, the plugin loops. | `vw.py`, `vw.md`, step 4 and 5 |
| L35 | **The packet before a keyframe.** `packet` marks the shot's binding `packet_read_at`; `generate_image` of a keyframe for an element that belongs to a video shot refuses when no accepted video shot naming that element has a binding with the packet read: "Bind the shot and read its packet before composing its start image (`vw visuals bind`, then `packet`)". An element used only by still or graphic shots is unaffected. The step says bind, packet, start, end from the start candidate at once, the pair shown together. | `visuals_stage.packet`, `generate_image`, step 4 |
| L38 | **The end image does not move the camera.** The packet's end instruction says "The camera does not move between the two images: the same framing, lens and position. The end shows the action's visible result, a different pose or state from the start, never the same frozen pose." `generate_image` of an end keyframe refuses a prompt that names a camera move (push, pushes, drift, drifts, dolly, zoom, pan, tilt, tracking, "camera has moved", "camera moves") with the word. | `visuals_stage.packet`, `generate_image` |
| L39 | **A scale anchor and the landmarks in the packet.** The start instruction says "Name one human-scale anchor against a named landmark (a person beside a doorway, a hand on a course) so the scale is fixed." The packet lists the scene's landmarks (id and description) in its own `landmarks` field beside the instructions; the prompt's section 6 says the start names positions against them. | `visuals_stage.packet`, the prompt |
| L41 | **A client material comes from a footage frame.** The prompt's element rule: anything specific to the client that the footage shows (a wall pattern, a product, a tool, a uniform) is an element of its own, kind `object`, identity `exact`, with its footage frames as views, and its description in the foundation's world rules as exact text every prompt reuses. `generate_image` refuses a keyframe for a shot whose subjects include an exact-identity object element unless a reference of kind `frame` for that element is among the parents: "<element> is the client's own: send one of its approved footage frames as a parent, named by number as the material reference". | the prompt (section 5), `generate_image` |
| L42 | **The footage character is asked, stored and passed down** (SK, 22 Oct: VW-6's clips are from a professional cinema camera; the assistant assumed phone footage and the theme carried it into all 44 prompts). `vw stage media prepare` adds a one-line guess from the probe (width, bit rate, pixel format: "looks professional" or "looks like phone footage") to its listing; the media step asks once, with that evidence, "camera class, handheld or tripod, graded or natural", and `vw stage media record --camera cinema|mirrorless|phone|mixed --support handheld|tripod|mixed --look natural|graded|log` records the answer in the media output summary as `footage_character` with the operator's words. The visuals package and the packet carry it; the prompt's theme rule says the theme's texture line comes from the recorded footage character, never from an assumption, and the foundation's appearance names it. A run recorded before this release has none: the prompt says to ask the operator once and record it in the foundation. The analysis prompt is unchanged this round. | `stages_av.media_prepare`, `media_record`, `vw.py`, the media step, `visuals_stage.prepare`, `packet`, the prompt |
| | Server 0.28.0, plugin 0.26.0 (with design/76 and design/73, one deploy, SK's decision of 22 Oct). | |

SK's decisions of 22 Oct: the theme follows the recorded footage character (no separate choice); Higgsfield stays optional, Gemini Omni is the primary generator (no library change); design/73 ships in this deploy; the prices stay as set, in rupees; VW-6 is paused until the batch is live, then image generation resumes from the references step.

## 2. Not changed

The plan schema (an object element with exact identity and frame views needs no new field); the generators; the page (design/76 changes it).

## 3. Tests first

- `test_visuals_cli.py`: `still --file`, `bind --file`, `approve --file` post one call per row in order and stop at the first refusal; the step and the prompt say a still shot needs no bind.
- `test_visuals_stage_pure.py`: `packet` marks the binding; a start keyframe for a video shot's element is refused before the packet is read and accepted after; an element of a still shot is unaffected; an end keyframe naming a camera move is refused with the word and one without passes; the packet carries the landmarks and the new sentences; a keyframe for a shot with an exact object element is refused without a frame parent and accepted with one.
- The prompt within 3,500 words; compile checks.

## 4. Not covered

server/tests (Docker); whether the model keeps the bond from a frame parent (VW-6's next wall shot is the check); the camera-word list is a list, a move said in other words passes.
