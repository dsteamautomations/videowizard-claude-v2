# design/74 — The visuals queue before the test pass: design/68 part B (L6, L7), L24 to L29, L31

Status: requirements note, builder, 22 Oct 2026. SK on 22 Oct: "Part B and the queue: yes, implement it; leave L9." Built on that word as the approval; design/73 (reference assets) follows the test pass. Sources: design/49 (L24 to L31, 21 Oct), design/68 §5 (part B), design/71 P6, `visuals_stage`, `visuals.html`, `web.py`, `main.py`, `vw.py`, the prompt and steps in `v2.json`, the library's `record-template.videowizard.yaml`.

## 1. What changes, item by item

| | Change | Where |
|---|---|---|
| L6 | **The checklist beside each picture and take.** A reference generated with an answer keeps the answer's checklist; a take prepared with an answer keeps it on the preparation. The page lists the lines under the picture or the take; `vw visuals fetch --ref R` and `--job J` print them, so the review is ticked against what the prompt promised. | `page_view`, `prepare_take`, `visuals.html`, `vw.py` |
| L7 | **A picture reject with words, and the feedback record.** New `reject_reference(ref, notes, quote)`: a candidate or approved reference becomes `rejected` with the notes, the words, who and when; it cannot be approved, bound, used for a still, or named as a parent afterwards. The P6 server check follows: an end keyframe generated from a rejected keyframe is refused ("retry from the approved start, not the candidate chain"); a state from a rejected state likewise. A feedback record is written on approve, on reject, on a take's select (pass) and on a take's rejected review, in the library's record shape (app, library_version, run_code, job_id, playbook, task, model, inputs, prompt, checklist, verdict, verdict_by, what_went_wrong, suggestion), kept in the session and served as YAML by `GET /visuals/feedback`; `vw visuals feedback` writes `work/visuals/feedback.yaml`; the page shows a Reject button with the words box on candidate and approved pictures and a `rejected` badge. Both front ends, one function. | `visuals_stage.reject_reference`, `feedback_record`, `feedback_yaml`, `generate_image`, `main.py`, `web.py`, `visuals.html`, `vw.py` |
| L24 | **A boundary is shared only within one continuous shot.** The prompt (sections 2 and 6) and the packet's start instruction say: the end image of one segment is the start image of the next only within one continuous shot, same place and framing; a cut starts a new pair with its own two images. The estimate's count is unchanged (it is an estimate; the treatment carries the true count). | the prompt, `visuals_stage.packet` |
| L25 | **The treatment validator reads the shot list.** When an entry names one route and its `shots` use others, the routes are taken from the shots; when an entry names several routes and a shot uses one it does not name, the draft is refused naming the gap and the route, at draft time, not at propose. | `visuals_stage.treatment` |
| L26 | **The cap is the setting alone.** "Raise the cap" leaves the page and `vw visuals cap` leaves the plugin; the server's cap route and `set_cap` go; a refused paid call says "stop and tell the operator the spend; the builder changes the cap on SK's word"; the prompt, the steps, `vw.md` and the budget line say the same. A film whose session holds a cap keeps it. | `visuals.html`, `web.py`, `vw.py`, `main.py`, `visuals_stage.check_cap`, the prompt, `vw.md` |
| L27 | **Write while images generate.** The steps and the prompt say: after submitting a wave of images, write the next shot's answers instead of waiting in `status --wait`; generate the end image from the start candidate at once, so a shot has one approval wave; wait only when nothing is left to write. | the prompt (section 5), step 4 |
| L28 | **A draft after a record.** A treatment draft that arrives after a record is shown as the current treatment with the badge "draft, replaces the approved treatment of <time>" and the approve box; the status line says so. | `visuals.html` |
| L29 | **The page stays in step.** While the run is at visuals the page polls every 60 s at all times (15 s while a picture or take generates) and reloads when the tab becomes visible again. | `visuals.html` |
| L31 | **Bind before packet, said plainly.** `vw visuals packet` on the bind refusal says "Bind first: `vw visuals bind --shot S --refs E1=R1,R2`, then `packet`"; `bind`'s success line says to run `packet` next; on the page a click with the words box empty marks the box and says what is missing. | `vw.py`, `visuals.html` |
| | Server 0.27.0, plugin 0.25.0. | |

## 2. Not changed

L9 (the library handoff) waits for a full stage. The treatment shape, the plan schema, the generators, the library files, the assembly.

## 3. Tests first

- `test_visuals_stage_pure.py`: `reject_reference` sets `rejected` with notes and words and refuses a reference that is neither candidate nor approved; `approve_reference`, `bind`, `still_from_reference` refuse a rejected one; `generate_image` refuses a rejected keyframe parent with the P6 message and a rejected state parent; the feedback records on approve, reject, select and rejected review carry verdict, library_version, prompt, checklist and the answer's suggestion; `feedback_yaml` renders a record the YAML way; `treatment` takes routes from the shots when one route is named and refuses a shot route not named among several; `check_cap`'s message names the builder, not a command; `page_view` carries each picture's checklist, a take's checklist and the `rejected` status.
- `test_review_page.py`: the visuals template has no cap button and calls only paths with routes (the existing rule).
- `plugin/tests/test_visuals_cli.py`: `cap` is no longer a choice; `packet` on the bind refusal prints the bind-first line; `bind` names `packet`; `fetch --ref` and `--job` print the checklist; `reject --ref R --notes --quote` posts; `feedback` writes `work/visuals/feedback.yaml`; the prompt and steps carry L24, L26 and L27 and stay within 3,500 words; `vw.md` names no `vw visuals cap`.

## 4. Not covered

server/tests (Docker); the page under a real session (L28, L29, L31 are template logic, checked by reading and by the route rule); whether the assistant follows L27 on its own (the pass shows it).

## 5. Order

Tests → change → compile checks → self-review → commit and push → tell SK → deploy the server (0.27.0) and the plugin (0.25.0) → design/35 row, design/49 line → SK resumes VW-6.
