# design/76 — L32: Accept and Revise on the visuals page, so a change request is never recorded as a yes

Status: requirements note, builder, 22 Oct 2026; SK the same day: "need this" for the next batch. Held until VW-6's pass is done (a server deploy restarts the workers). Sources: defect 20 and design/75; `visuals_stage.accept`, `status`, `page_view`; `visuals.html`; `vw.py`.

## 1. Why

On 22 Oct SK's four change requests went in through the only button a gap has, Accept, and were recorded as acceptances. design/75 makes the assistant read the words and treat a change request as a revision; this note gives the operator the second button so the record itself is right.

## 2. What changes

| | Change | Where |
|---|---|---|
| V1 | **A revision request on a gap.** New `revise_gap(gap_id, notes, quote)`: the gap is not accepted (an earlier acceptance of it is dropped), and `session.revisions[gap_id] = {notes, quote, by, at}`; `status` and the page carry it as `revise` with the words; `propose` of a new version clears the entry when the gap's digest changes; `accept` of the gap clears it. Both front ends: the page's Revise button beside Accept, with the same words box, and `vw visuals revise --gap G --quote "…"` for the chat path. | `visuals_stage.revise_gap`, `propose`, `accept`, `status`, `page_view`, `main.py`, `web.py`, `vw.py`, `visuals.html` |
| V2 | **The page.** Each gap row gets Accept and Revise; a gap under revision shows a `revise` badge with the words; the words box's placeholder differs per button ("your yes" / "what to change"). | `visuals.html` |
| V3 | **The step.** Step 3 says: a gap under revision is changed (treatment entry, plan), proposed as the next version and accepted afresh; `vw visuals status` lists the gaps under revision with their words; nothing is generated for them until then. design/75's reading of the words stays as the fallback. | step 3, the prompt |
| V4 | **The feedback file.** A revision writes a record (kind `gap`, verdict `fix`, the words), beside the acceptance records of design/75. | `visuals_stage.revise_gap` |
| | Server 0.28.0, plugin 0.26.0. | |

## 3. Tests first

`test_visuals_stage_pure.py`: `revise_gap` drops the acceptance, stores the words, writes the `fix` record; `accept` and a new `propose` clear it; `status` and `page_view` carry it. `test_visuals_page_pure.py`: both buttons and the badge in the template. `test_visuals_cli.py`: `revise` posts the gap and the words; the step names the revision.

## 4. Not covered

server/tests (Docker); the page under a real session.

## 5. Order

After VW-6's pass: SK's go → tests → change → compile → commit and push → deploy the server (0.28.0) and the plugin (0.26.0; the operator's session restarts) → design/35 row, design/49 line.
