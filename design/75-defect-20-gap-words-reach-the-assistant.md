# design/75 — Defect 20: the words on a gap's Accept button reach the assistant and the feedback file; a change request is a revision

Status: defect note, builder, 22 Oct 2026; SK's yes the same day ("build and deploy the fix for defect 20 now"). Sources: defect 20 (VW-6, 22 Oct 05:24 UTC); VW-6's visuals session on the server (18 gaps accepted from the page, each with SK's words); `visuals_stage.accept`, `status`, `page_view`; `visuals.html`; the visuals prompt and steps.

## 1. What was wrong

The page's Accept button records the operator's words as the gap's acceptance (`session.accepted[gap].quote`), and nothing reads them back: `status` tells the assistant only that the gap is accepted; the feedback records of design/74 cover pictures and takes, not gaps; the page shows the badge without the words. SK wrote 18 comments; four of them ask for a change (a different route for BEAT_03-B2 and BEAT_04, a text-on-still idea for BEAT_01, a shorter label for BEAT_03-B1), and the single button recorded them as a yes.

## 2. What changes (server only; no plugin change, so the operator's session needs no restart)

| | Change | Where |
|---|---|---|
| D1 | `status` and the page carry each accepted gap's words and who said them (`quote`, `by`); the page shows the words under the gap's head. The assistant reads the status JSON already, so it sees them without a plugin change. | `visuals_stage.status`, `page_view`, `visuals.html` |
| D2 | A gap acceptance writes a feedback record (kind `gap`, verdict `pass`, the words), so `vw visuals feedback` carries them. | `visuals_stage.accept` |
| D3 | The step and the prompt: after acceptances, read every gap's words before any picture; words that ask for a change (a route, a different picture, a label) are a revision, not a yes: change the treatment entry and the plan for that gap, propose version 2, and that gap is accepted afresh (its digest changes, so the old acceptance drops); nothing is generated for a gap whose words ask for a change. | the prompt (section 2), step 3 |
| | Server 0.27.1. | |

## 3. Tests first

`test_visuals_stage_pure.py`: `accept` writes a feedback record per gap with the words; `status` and `page_view` carry the words and `by` on an accepted gap and nothing on an unaccepted one. `test_visuals_page_pure.py`: the template shows the acceptance words. `test_visuals_cli.py`: the prompt and the step carry "accepted afresh" and stay within 3,500 words.

## 4. Not covered

server/tests (Docker); the page under a real session; whether the assistant turns SK's four change requests into a plan v2 on its own (the resumed VW-6 is the check).

## 5. Order

Tests → change → compile → commit and push → deploy the server (0.27.1; the workers restart, nothing is running on VW-6) → defect 20 resolution line and `status` fixed → design/35 row, design/49 line → the operator session resumes with `/vw:vw what is next for VW-6`.
