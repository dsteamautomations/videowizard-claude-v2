# design/217: step 6 "Pictures and drawn graphics" on the page, and Claude's check of its pictures (server side)

18 Nov 2026. Built by Builder S on branch `d217-server` from the approved release (`design/_work/step6-release-requirements-18-nov.md`), the contract `design/217-contract.md` and its fixture `server/unit/d217_pictures_round.json`. Server 0.115.0, plugin 0.99.0, plugin minimum 0.99.0. Not deployed.

## What changed, by item

- **Part 1 (server side).** `page_flow._plan_step` gives `pictures` once a v2 reference round is complete and an item of step 6 waits or is coming; `_pictures_page` builds the round of contract sections 2 and 3 from the chat's own items (`chat_flow._waiting_items` carries each line as `_line`, built once in `server/app/pictures.py`). `say` is `pictures.say`, `layout.coming` is `pictures.coming`, `layout.words.pictures` is `pictures.PAGE`. `page_record` records a `pic:` answer through the item's own run function (`_pictures_answer`): questions, the style sheet, then film order; a changed item is stale; then `PICTURES_LEFT` / `PICTURES_WAIT` / `PICTURES_DONE`, with the look duty first. A drawing's video gets a 960 px page copy (`page_flow.video_copy`, `videos` on the page; the tool uploads it with the large pictures). An older round keeps the chat; a film mid-step keeps its handed-out chat item and the page takes over at the next.
- **C1.** `visual_workers.finalize_image` stores the code checks and `ready_at` for a still, a step, the style sheet, a component or a remade one of a v2 film, and no `check_pending`; `check_image` only measures (light, fine detail, transparency) as advice (`_measure`). No Gemini 3.8 Flash call for these. The list per kind is `pictures.lines` (the style sheet gets a palette line, readable sample labels, no scene).
- **C2.** `GET/POST /api/runs/{id}/visuals/pictures/looks`, `vw visuals pictures --looks [file]`, helper `plugin/agents/vw-picture-look.md`. Refusals `PIC_LOOK_OPEN`, `PIC_LOOK_UNKNOWN`, `PIC_LOOK_WORDS`, `PIC_LOOK_NOT_CHECKED`, `PIC_LOOK_GONE`; a refused picture records nothing, the others record.
- **C3, F6.** `pictures.offered`: listed by `waiting()` only with its look, or `PICTURE_LOOK_MINUTES` (30) after `ready_at` as "not checked"; meanwhile a `checking` row in `layout.coming`. `next` and `status` say the pictures waiting first. A picture held by `check_pending` at the deploy is stamped and given to Claude's check (`pictures.stamp`, in `next`, `status` and the looks route).
- **C4, D2.** The program's lines (size, parents, light, fine detail, transparency) are `check.advice`, never a fault.
- **C5.** `figure_repeat` is not called on a v2 film; "no background figure repeated" is a line of the still's list, the scene's approved pictures among its inputs.
- **C6.** `vw motion upload` sends `rules.md`; the server holds the rules per project (`pictures.rules_of`); `motion_verdict` refuses a verdict that skips a rule, names an unknown one (a checker's own `seen` rule is allowed) or fails one with no `where`. A project uploaded before keeps the older way.
- **C7.** The svg route and the AI-video take check are not touched.
- **F1.** The check in the chat and on the page is `pictures.check_view` (Claude's look and the program's lines), never `ref.checklist`.
- **F2.** One `correct:<n>` per step; the step named is rejected, every later one as "Made from a step that was corrected."
- **F3.** A drawing is held as `select_take` holds it (`pictures.fact_view` from the verdicts of its project's sha); not held, the accepted review carries no words.
- **F4, D7.** `reject_reference` stores no reason for a bare "No" (`BARE_NO`): nothing joins the not-this list or the library.
- **F5.** Every step-6 picture has a list (fixed lines at least; the style sheet its own).
- **R1, D3.** The fix round is retired (`FIX_RETIRED`, `vw visuals fix` refused by name), so the server writes no fix prompt for the pixel rule to refuse; "Correct it" opens with Claude's failed lines (`prefill`).
- **R2.** `library.check_prompt` lets "centre" pass where the sentence frames the hero or the frame ("as the hero", "of the frame").
- **R3.** `sequence` warns for two steps alike; the page line carries it as advice and asks once (`sure`).
- **R4.** The three motion "Takes step" sentences name the Pictures and drawn graphics step.
- **D1.** No amount on these lines (a question's choice loses its price).
- **D4.** A component is approved by a clean look (`COMPONENT_APPROVED`; the program's advice lines never decide it), never asked. One that fails stays a candidate and is named with its failed lines in the looks route's `then` and in `next`, `status` and the page's record (`pictures.components_failed`), so the assistant makes it again.

## The merge (18 Nov)

- The together test (`server/unit/test_design217_together_pure.py`): a film with every kind, the server's round, the real page, every line answered, recorded through `page_record`. The round has the fixture's shape. Changes from the page builder's points: a still's `faults` sent once (`check.faults`), `layout.made` dropped (`end_foot` says it), the main picture's label without "(try 2)" (the tag says it), `film_at` under the name in the list, "Correct n" on the step buttons, 4 steps in a low window as two rows of two, a video sent again under the round's `zoom_docs` (the page and the tool), a video copy over 15 MB shown as its frames.
- The critic's review: `asked_at` (the 30 minutes count from Claude being asked), a picture the model checked before the deploy keeps its check and stays offered, `V.parent_failed` reads Claude's lines, a later step corrected stores no reason (`cause` instead), a failed component is said, "free" dropped, the chat's question says the page's words.
- **D5.** The style sheet is refused on a v2 film whose plan has no graphic in steps (`STYLE_NOT_NEEDED`); its components are made without it.
- **D6, D8.** `video` on a drawn line, the sheet as a picture; "Take the effect away" (`plain`) has no `sure`.

## Not covered

- Real films: Claude's look quality and token load, the 30-minute time-out on a real run, a video page copy made by ffmpeg on the VM (not run here), footage before and after taken from an approved footage picture of the neighbouring clip, not the frame at the cut (`pictures.footage`).
- Question wording per fork: one generic sentence for every fork (`say_answer`).
- `server/tests` (Docker) and the browser tests (Builder P).
