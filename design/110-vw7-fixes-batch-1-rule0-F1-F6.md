# design/110: VW-7 fixes, batch 1: rule 0 and F1–F6 (requirements, for SK's approval)

Source: Revathi's builder note "VW-7 fixes, batch 1: rule 0 and F1–F6", 27 Oct 2026 (approved by Revathi in the thread "Review VW-7 visuals fixes one by one"; checked by her against server 0.53.0). Every entry is required; this note says what exists today on `main` (server 0.58.0, after design/109), what changes, where, the edge cases, the tests, and the questions SK answers before code. Nothing is built yet.

## What exists today (measured on main)

- The plan (`visual_contract.py`): `Position(landmark_id, relation)`; `State(position, facing: str, pose, holding: [element ids], progress)`; `Beat(action, target, path, result, start, end, min_s)`; `Subject(start, end, behaviour acts|holds, beats)`; `Shot.changes: [Change(what, beat_id)]`; `Scene.landmarks: [Landmark(id, description)]`. The check refuses a position whose landmark is not in the scene and a held thing that is not an element; it only warns when `changes` is empty.
- The packet (`visuals_stage.packet`): `end_targets` composes one sentence per subject from its end state ("E1 ends <relation> <landmark>, facing <facing>, <pose>, holding <held>; <progress>."); the end instruction tells the assistant to carry those lines word for word. The start prompt is the assistant's, written from the packet; the server adds nothing to it.
- The picture check (`image_check.lines_of`): the server's own lines (`server_checklist`: claims, spec relationships), the writer's checklist, three fixed must/should lines and the scene lines. Nothing asks whether a start already shows the result.
- `approve_reference` queues the pending end at once; `prepare_take` runs the pair check (differences without a cause are marked, never refused).
- The take check (`TAKE_LINES`): appear or vanish, same tools/clothes/faces, no repeat without precondition, no change of shape, planned end, frozen person; plus the light and ambient lines.
- References: one round (pass 1 frames and keywords, pass 2 picks); `search`, `nothing_fits`, `round_done`, `round_picks`, `note_reference` exist on the server; the page shows the search box per element and folds it once picks are saved; `vw visuals supply` stores an operator file as a `supplied` reference through the plugin only; there is no undo of Done and no page upload.
- No "open question" state exists anywhere; the procedure tells the assistant to ask at a few named points only.

## The change, rule by rule

### Rule 0: an open question is a server state

- New session record `questions: {item_id: {question, choices: [...], asked_by, at, cost_inr?, answer?, answered_by, answered_at}}` where `item_id` is a reference id, a shot id or an element id.
- New server functions and routes: `ask(item, question, choices, cost)` and `answer(item, choice|words)`; the page shows the card as "waiting for operator decision" with the choices as buttons; `status` returns `questions` (open ones) so the chat assistant sees them; `waiting` gets one item per open question.
- Derived writes refuse while the item (or the item it derives from) has an open question: `generate_image` with that reference among its parents or for that shot, `request_fix`, the end queued by `approve_reference`, `prepare_take`, `bind`, `_place_still`, `select_take` for that shot. The refusal names the question.
- Server-raised questions, because the server sees these forks itself: fork 3 (a second picture approved for the same start or end slot of a shot: the server asks "keep which?" instead of keeping both), fork 4 (a picture approved with a stated flaw in its quote or with a failed must line is about to become a parent: asked once), fork 5 (a check fails on an approved picture: F3's approval check). Forks 1, 2, 6–10 are the assistant's, by the procedure text (one question, concrete choices, the paid cost, then stop); the assistant records them with `ask` so they are on the server too.
- References additions: "Search again" and "Nothing fits" stay on every element's card after Done and after its sheet is made (today they fold); "Add your own picture" on the page (a file from the computer or a link) stored as an approved `supplied` reference, the same server function `vw visuals supply` calls; Done on a pass asks "Done with N elements?" (pass 1 already shows a summary; pass 2 gets the same) and `round_undo` reopens the pass until the next step has used it (pass 1: until any pick is saved; pass 2: until any sheet is generated from the picks); redoing one element never touches another's references (true today; a test pins it).

### F1: the end prompt's first sentence per acting subject is cause → path → result

- `end_targets` gains, in front of each acting subject's end-state sentence: "Because <subject name> has <past tense of the beat's action> <target> along <path> from <start place> to <end place>, <result> is now in frame." composed from the subject's beats (the last beat, or each beat joined) and its start and end positions (F2's landmark + amount). Only shots that get an end picture (`pending_end` present or an end made by hand); start-only takes untouched.
- The past tense is not computed by grammar: the beat's `action` is written in the plan as an infinitive phrase today ("set the brick on the course"); the plan gains `done: str` per beat (the same action in the past: "has set the brick on the course"), required for video shots. The server composes with it. No guessing of verb forms.

### F2: a position is landmark + measured amount in a visible unit

- `Position` gains `amount: float | None` and `unit: str` (bricks, paces, body-lengths, hands, doorways, metres only when measured); `relation` stays. The plan check refuses a subject state position with no amount or no unit, and a `relation` that is only "centre", "middle", "nearby", "closer", "further", "beside", "at" without a landmark (the landmark id is already required). The prompt check (`library.check_prompt`, run on every start and end prompt) refuses "the centre", "the middle", "nearby", "closer", "further" standing alone (not followed within the sentence by a landmark word from the scene's landmarks).
- End prompts: `end_targets` says the distance moved from the start position ("two paces from where he stood in Image 1, level with the palm").

### F3 (+F44): the start shows the action not yet done

- Packet: `start_targets`, one line per acting subject: "about to <action>; has not yet <done>: <what is still untouched: the start state's progress>." The start instruction says to carry it word for word.
- Check: one new must line on every start keyframe of a shot with an acting subject, in `server_checklist` when the picture is queued: "not yet done: the picture shows the moment before <action>; <result> is not visible yet". Built from the beats and the start state.
- Approval: `approve_reference` on a start reads the stored check; if that line failed, or the check has no answer for it, the approval is refused with the reason and the server opens a question on the picture (fork 5: "the start already shows the result; make a new start (₹4) or approve anyway?"). Nothing is queued until answered. (Question 2 below: run the model again at approval, or read the stored check.)

### F4: inventory lines, and the check counts

- `State` gains `objects: [{element_id, count: int, place: Position}]`, the movable things in frame for that subject's start and end (people's `holding` stays). The plan check: a thing in the end objects that is not in the start objects, or whose count changed, must be named by a `Change` of that shot ("the counts agree with the action"); a thing dropped must appear in a change too.
- Prompt composition: the server composes "Inventory, exactly: <object × count at place> ...; nothing else of this kind in frame; nothing rests on top of the stack" and sends it as `inventory_start` and `inventory_end` in the packet; the start and end instructions say to end the prompt with it word for word; `check_prompt` refuses a start or end prompt without its inventory line (matched on "Inventory, exactly:").
- Check: one must line on start and end keyframes: "inventory: exactly the listed things, in the listed counts and places; nothing extra of those kinds". On the end picture the line also says what changed and why.

### F5: a tool stays the same tool

- Tools and props are elements already (`holding` names element ids). `Shot` gains `props: [{element_id, holder: element_id, start: Position, end: {where: in_hand | set_down | carried_out, position?: Position, cause?: str}}]`; the plan check requires one entry per element held by any subject of a video shot, and `set_down` to carry a position, `carried_out` a cause.
- The server composes the tool sentence from it ("The same <tool name>: it keeps its shape, size, colour and handle ...; <holder> holds nothing else; no second tool appears; the tool is fully inside the frame." plus where it ends) into `tool_lines` for the start prompt, the end prompt and the motion text (added by the server in `motion_text`, as the ambient sentence is).
- Check: one must line on the end picture ("the same tool as in Image 1, in the place the action leaves it: <where>") and one on the take ("the tool keeps its identity; it ends <where>").

### F6: a heading against a landmark and a frame edge

- `State.facing` becomes `Heading(landmark_id, edge: left|right|top|bottom|toward camera|away, camera_side: str)` for every subject state (question 4: all subjects, or travelling ones only). The plan check refuses a landmark not in the scene. `end_targets`, `start_targets` and the motion text carry "Heading: front toward <landmark> at the <edge>; the <camera_side> faces the camera; it must not turn, reverse or show its other side" unless a change of the shot names a turn, then the new heading.
- Non-acting living things (elements of kind person or animal that are subjects with behaviour `holds`) get the small-change sentence ("each has moved at least one body-length toward <landmark> and turned a little; none stands where it stood in the start") in the end prompt and the motion text; the plan check requires their end position to differ from the start by an amount (F2).
- Check: one must line on the end picture: "heading kept: each travelling subject faces the same landmark and shows the same side as in Image 1"; the take check gets the same line.

## Unstated but expected

- Old plans: every new field defaults so a stored plan still loads and validates for a still shot or a graphic; the stricter rules fire on video shots only, and only when the plan is submitted again (VW-7's plan is revised anyway after the reset; VW-8 and VW-9 are held). No digest of an already ready take changes: the new fields are kept out of `gap_digest` and the preparation digest like design/101–103's (`note_free_*`).
- The composed sentences are server data in the packet; the assistant copies them; `check_prompt` refuses a start or end prompt that lacks them, so the rule cannot be skipped from chat or the page.
- Costs: every new picture-check line rides on the existing Gemini call (no new call); F3 at approval reads the stored check (question 2).
- The page: open questions on cards with buttons; the References additions; nothing else moves.
- `vw.md` and the procedure gain rule 0's text: the fork list, the question form, "never guess", what never needs a question; the facts list asked once before the first picture.

## Edge cases

- Empty or old data: a shot with no beats (no acting subject) gets no F1/F3 lines; a subject with no objects gets "Inventory, exactly: nothing movable in frame"; a state with free-text `facing` from an old plan is read as a heading with no landmark and is refused only when the plan is resubmitted.
- Two acting subjects: one F1 sentence each, in the plan's order; one inventory for the frame (the union), not one per subject.
- A turn is the action: the heading constraint is dropped and the new heading named, when a change names the turn.
- Duplicate questions: `ask` on an item that already has an open question is refused with the open one; answering twice is refused; a question survives a page redraw and a server restart (session storage).
- Concurrency: `ask`, `answer`, `round_undo` run under the run lock like every other write; a derived write that started before the question was opened is not undone.
- Undo after use: `round_undo` is refused once a pick is saved (pass 1) or a sheet exists from this round's picks (pass 2), naming what used it.
- Upload: "Add your own picture" accepts PNG/JPEG/WebP up to the existing supplied-file limit, refuses other types, and stores the sha; a link is fetched with the web-pick downloader (same size and type limits, same failure message).
- Counting lines on busy frames: the inventory lists only the shot's movable things; background things the plan does not name are not counted (the line says "of these kinds").
- Permissions and defects: unchanged (a run with an open defect still refuses writes).

## Failure modes

- Gemini cannot decide a counting or heading line: the line comes back with no answer; the picture is a candidate with that line marked "undecided", never auto-rejected; F3 at approval treats "undecided" as a question (fork 5), not as a pass.
- Composition fails for a malformed plan: the plan check refuses before any picture is queued, naming the shot and the field.
- A page upload fails midway: nothing is stored; the card says so.

## Tests first

Server unit: rule 0 (ask, answer, refusal of each derived write, duplicate ask, status and waiting carry it, server-raised forks 3–5, round_undo allowed then refused, redo one element leaves the others); F1 (the composed sentence per acting subject with subject, verb, target, path, start place, end place, result; none on a start-only shot); F2 (schema defaults; refusals for no amount, no unit, bare relation words; prompt check refusals and passes; the distance in end_targets); F3 (start_targets; the must line present on a start keyframe only; approval refused and a question opened on a failed or undecided line; approval passes on a passed line); F4 (plan check on counts against changes; inventory lines composed; prompt refused without them; the must line); F5 (props required for held elements; set_down needs a position; the sentence in start, end and motion text; the must lines); F6 (heading schema and refusal; the lines; the turn exception; secondary living things' change). Digests unchanged for old plans. Page: text checks for the question card, the buttons, the References controls, the upload control, Done confirm and undo.
Plugin: `vw visuals ask` / `answer` / `supply` (unchanged) / `round undo` flags in `VISUALS_FLAGS`; the procedure text present.

## Questions for SK (answer in order, or say "go with the recommendations")

1. **Size and order.** This is seven rules with four plan-schema changes; built in the note's order (rule 0 server state, F3, F1, F2, then F4, F5, F6), one commit per rule, tests first, diff shown before each commit, nothing deployed until the batch is done. Recommendation: yes, that order, and VW-7's plan revision waits for the whole batch so Revathi revises once.
2. **F3 at approval.** The note says the same line "runs again" at approval. Running Gemini again on the same picture adds nothing but a second answer that may differ, and makes the approve click wait 10–20 s. Recommendation: at approval the server reads the stored check's F3 line; a failed or undecided line refuses the approval and opens the question; the model runs again only when the stored check has no F3 line at all (a picture made before this release).
3. **F1's past tense.** The server must not invent verb forms. Recommendation: each beat of a video shot gains `done` (the action in the past tense, written by the assistant with the plan); the plan check requires it; the server composes with it.
4. **F6 for every subject or only travelling ones.** `facing` exists on every subject state. Recommendation: every subject state gets the structured heading (one rule, no "does it travel?" judgment); the "must not turn" constraint is written for acting subjects, the small-change sentence for secondary living things.
5. **Who answers a question.** Recommendation: the operator, on the page (buttons) or in chat (`vw visuals answer`), recorded with their words like every approval; the assistant may answer only a question it asked itself when the operator's later words settle it, quoting them.
6. **"Search again" after the sheet exists.** A new pick after the sheet is made leaves the sheet stale. Recommendation: the server marks that element's sheet "sources changed" (shown on the card, in status and in waiting); the assistant makes a new sheet; the old one stays approved until the new one is.

## Not covered (known before the build)

- The operator's behaviour: rule 0's forks 1, 2, 6–10 are judgment calls in the assistant's procedure text; the server enforces only the state once a question is asked and the three forks it can see.
- Gemini's counting and heading answers are not benchmarked; the lines are must lines, so a wrong "fail" costs one fix round, a wrong "pass" is caught by the operator.
- The page changes are checked as text, not in a browser, as before; Revathi's by-hand checks after the deploy.

## SK's answers (27 Oct)

1. The note's order, one commit per rule, tests first, diff before each commit; VW-7's plan revision waits for the whole batch. 2. At approval the server reads the stored F3 line; Gemini runs again only when the stored check has none. 3. Each beat of a video shot carries `done`, the action in the past tense. 4. The structured heading on every subject state. 5. Only the operator answers; the assistant closes its own question only with the operator's quoted words. 6. A new pick after the sheet marks it "sources changed"; the old sheet stays approved until the new one is.

## As built: rule 0

- Session: `questions` (open, by item: question, choices, by, at, cost_inr, fork) and `answered` (the history). `visuals_stage.ask` (the assistant, any picture, shot or element of the run; at least two choices; once per item), `answer` (the operator's words; a fork-3 answer rejects the other picture with "rule 0: the operator kept …", a fork-4 "use it as the parent" sets `parent_ok`), `_no_question` (the gate), `round_undo`, `supply_own`.
- The gate: `generate_image` (the element, the shot, every parent), `approve_reference` (the picture and its shot), `request_fix`, `bind`, `prepare_take` (the shot, the start, the end), `sequence`, `_place_still`, `select_take` (the take's shot). The refusal names the question and both ways to answer.
- Server-raised forks: 3, in `approve_reference`, when a second start or end of a video shot would be approved (a still's second picture still replaces, design/94): the question goes on the shot with the picture ids as choices, the new picture stays a candidate until answered; 4, in `generate_image`, when a parent approved with a failed must line is about to be used (a fix of that picture is exempt). Fork 5 comes with F3.
- Shown: `status.questions`, `page_view.questions`, one `waiting` item per question ("Question · item · …", first in the list), the card on the page (picture panel, shot cards, element card) with the choices as buttons.
- References: the search box and "Add your own picture" (a file or an https link, stored as an approved `supplied` reference through `add_reference`) stay on every element card; only the results fold. Done on pass 1 asks "Done with N elements?" like pass 2. `round_undo` (page and `vw visuals round --undo`): pass 1 until a pick is saved, pass 2 until a sheet was made from the round's pictures. A new frame, pick or supplied picture marks the element's unrejected sheets `sources_changed` (card, status, waiting); approving a new sheet of that element clears it.
- Routes: `/visuals/ask`, `/visuals/answer`, `/visuals/round/undo`; page actions `answer`, `supply`, `round-undo`. Plugin 0.51.0 (pending): `vw visuals ask --item --question --choices "a|b" [--cost]`, `vw visuals answer --item --answer`, `vw visuals round --undo`. The procedure's visuals prompt opens with "0. STOP AND ASK, NEVER GUESS" (the fork list, the question form, what never asks); the references step names the additions; `vw.md` carries the rule in one paragraph.
- Tests: `server/unit/test_design110_r0_pure.py` (10), `plugin/tests/test_design110_r0.py` (2); two design/106 tests now go through the fork-3 question. Server unit suite: 510 passed. Plugin: 310 passed, the 3 known Windows-only failures. Page script passes `node --check`.
- Not covered: forks 1, 2, 6–10 are the assistant's judgment, by the procedure text; the page is checked as text and by node, not in a browser; `supply` from a link is not tried against a real site; fork 5 waits for F3.

## As built: F3 (+F44)

- Packet: `context.start_targets` = one line per acting subject ("E1: about to <action>; not yet done: <result>; still as at the start: <start progress>.") with the instruction to carry it word for word; in the context, so no preparation digest moves.
- Check: `not_yet_lines(shot)` gives the must line "not yet done" for every start keyframe of a video shot with an acting subject (a fix of a start too); it names the start state and the result and says when the line fails. Added to `server_checklist` in `generate_image`.
- Approval (`_not_yet_gate`, at approval): the stored line decides; failed or undecided refuses the approval and opens the question on the picture (rule 0 fork 5, choices "make a new start (4 INR)" / "approve anyway"); a stored check without the line (a picture checked before this release) is asked the line once through `image_check.check_lines` and the answer kept with the check; no stored check at all means nothing to read. "Approve anyway" sets `not_yet_ok` and `parent_ok`.
- Takes: `prepare_take` reads the start image's stored line; a failed line refuses the take with the same question.
- Live check (f3-live, 27 Oct): VW-7's own B07B_S2 prompt with the line gives the before-state picture and passes; without it the third brick is already on the bed and fails; the negative control fails; steady across two reads. Two earlier line wordings were not steady and were dropped.
- Tests: `server/unit/test_design110_f3_pure.py` (6). Server unit suite: 516 passed. Plugin untouched.
- Not covered: the model's reading is sampled on two shots, not benchmarked; the F1 `done` field (next) will tidy the start_targets grammar.
