# design/97 — Release 3: the visuals page from the operator's seat

25 Oct 2026. Release 3 of the combined revision (`VW2-revision-plan-2026-10-24.md`). It builds design/93's page points that are still open (`design-93-ui-status-2026-10-25.md`):
- P1–P3, the approval panel;
- R1–R2, the reference sheet;
- V1–V3, seeing pictures large;
- W1–W4, knowing where to look;
- K1, the check summary;
- A2's single Reject, A4–A5, and L4's highlight;
- G3, the split per gap.

It also builds today's open issue O4, the review page's button line. **Nothing is built until SK approves this note.**

## 1. The requirement, restated

The operator sees the picture they judge large, with their words box and buttons beside it, on every step. They can tell at once what is waiting for them and where, and every request from the assistant links straight to it. After each verdict, one line says what happens next.

## 2. The approach

**One shared panel, on every step.** The References step already has one (design/80): click a picture, and it shows large on the right, with its facts, words box, Approve and Reject. Release 3 uses that same panel on the Pictures and Takes steps too, and for the style sheet. On a narrow window it sits under the grid, as today. Nothing new is invented, and every step behaves the same.

## 3. What changes

| # | Rule | Where |
|---|---|---|
| P1, P2 | **Every verdict on a picture is given in the panel beside it:** style sheet, reference pictures and sheets, stills, a sequence (any of its states opens the whole sequence), a start and end pair, a take. The words box and the buttons are in the panel, and the picture stays in view while the operator types. The footer's words box stays only for step-wide actions (record the treatment, accept gaps, record gaps). The buttons and their server calls are unchanged. | `templates/visuals.html` |
| P3 | Under 900 px the panel sits under the grid and keeps its picture above the words box. On a phone, the words box and buttons stay pinned to the bottom of the screen while the panel is open. | page CSS |
| V2 | **The panel is wider** (about 45 % of the content, not 340 px), and its picture fills it. A start and end pair, or the states of a sequence, are shown side by side in the panel at the same size. | page |
| V1, V3 | **Click the panel's picture to open the viewer:** full screen, at the picture's own resolution. Zoom with the wheel, a pinch or + and −; drag to pan; ← and → for the previous and next picture of the same shot, sequence or element; Esc to close. The viewer keeps the panel's words box and buttons on its right, so a verdict needs no closing. | page |
| K1 | **The check folds into one line:** "11 passed · 1 to look at", coloured by the worst result. A failed must line shows its text in that line. A click opens the full lines. This applies to the cards and the panel. | page (`checklist`) |
| R1 | **A sheet waiting for approval** opens in the panel, large. Beside it is a strip of only the pictures it was made from (its parents), for comparison. | page |
| R2 | **Once a sheet is approved,** the element shows the sheet alone, with its sources folded into "sources (n)". Unticked search results and unused candidates are hidden behind "show all (n)". | page |
| W1 | **Every item has a link** of the form `/runs/VW-7/visuals#pictures/B02B_S1/<picture>` (a reference: `#references/<element>/<picture>`; a take: `#takes/<shot>/<take>`). Opening it goes to that step, opens the item in the panel, scrolls to it and outlines it. The server builds the link, so both front ends give the same one. | `visuals_stage.waiting` and `item_link`, page |
| W2 | **Every section is labelled by type and shot:** "Still · B01_S2 · Hot half-built house", "Graphics · B02B_S1 · Hollow cavities", "Reference sheet · MASON", "Take · B01_S3". | page |
| W3 | **What waits for the operator is marked.** Each waiting item carries a "waiting for you" badge. The step line counts per step ("Pictures · 3 waiting"). A "Next waiting" button jumps to the next one. The top line counts the whole stage ("4 waiting for your verdict") and opens a list of links, one per item with its label. | `visuals_stage.waiting`, page view, page |
| W4 | **`vw visuals status` lists each waiting item with its label and link.** The procedure tells the assistant to give the operator the label and the link, never only "on the page". | `status`, `vw.py`, `server/procedures/v2.json`, `vw.md` |
| A2 | **A sequence has one Reject,** in the panel, which names the step: "Reject state 2" with the words. It rejects that state, so the next one is made from the state before it. | page |
| A4 | **After each verdict, one line says what happens next.** The server writes it, so both front ends show the same words. For example: "Approved: in the film at 0:14–0:17 (B01_S2).", "Rejected: the assistant makes a new start image with your note.", "Sequence approved: in the film at 0:21–0:30.", "Take selected: in the film at 0:31–0:36.", "Taken out of B01_S2: it stays approved.", "Fix requested: it appears here in about a minute." | the act replies (`approve_reference`, `reject_reference`, `sequence`, `select_take`, `unplace`, `request_fix`), page, `vw.py` |
| A5 | **A placed picture shows "Approved · in the film at 0:14–0:17"** and Remove, nothing else. | page |
| L4 | **A sequence error outlines both cards** it names. | page |
| G3 | **Each gap's row on the Plan step shows its split by route:** for example "graphics 12.0 s (2 shots) · AI video 5.0 s (1) · still 8.0 s (2)". The same split comes back from `vw visuals check`. The treatment, before the plan, keeps its totals: it has no shots yet. | `visuals_stage.gap_split`, page, `check` |
| O4 | **The review page explains its buttons**, under the slide's buttons: "Keep: use it. Reject: not this one (say why). Keep with edit: use it with a shot or trim change. Drop: leave the decision out. The buttons answer after you approve the options." | `templates/review.html` |

## 4. What waits for the operator (W1, W3, W4)

`waiting` lists, in film order:
- a candidate picture whose check is done: a reference, the style sheet, a still's picture, a start and end pair, or a sequence once all its states are made;
- a ready take not yet selected;
- a drawing spec not yet approved;
- a reuse waiting for the operator's words.

A picture still being made or checked is not waiting for the operator; it counts under "being made". Each item has its kind, label, step, link and the shot or element.

## 5. Edge cases

| Case | Handling |
|---|---|
| A link to an item that is gone (rejected, or replaced since) | The page opens the step and says "That item is no longer waiting: <label>." |
| A link opened before the page has loaded | The page applies it once the data is in. |
| The panel open on an item when the page refreshes itself | The same item stays selected. Words typed so far are kept (design/80 S4). |
| A sequence with a state still being made | The sequence shows in the panel with "state 3 being made". Approve the sequence is offered only once every state is in. |
| Keyboard arrows while typing in the words box | Ignored, as today. |
| A take in the panel | It plays in the panel's player, not the footer player, so the verdict sits beside it. |
| A narrow window | The panel goes under the grid; on a phone the words box and buttons stay pinned (P3). |
| VW-7 | Every shot is filled, so nothing waits. Remove and the film times show at once. |

## 6. Tests first

- `server/unit/test_design97_r3_pure.py`:
  - `waiting` lists a checked candidate, a ready take, an unapproved spec and a reuse, in film order, with labels and links;
  - it leaves out a picture being made or checked, and a sequence missing a state;
  - `item_link` has the form above;
  - each verdict's reply carries its `next` line with the film time;
  - `gap_split` sums seconds and shots per route per gap;
  - `check` returns it.
- The page:
  - the template carries the shared panel on every picture step, the viewer (zoom, pan, arrows, Esc), the check summary line, the link handling, the waiting marks and counter, and "Next waiting";
  - its script parses (`node --check`).
- `review.html` carries the O4 line.
- `plugin/tests`:
  - `status` prints each waiting item's label and link;
  - a verdict prints its `next` line;
  - the procedure text names the label and the link.

## 7. Not covered

- The treatment table and the gaps keep the footer's words box (P2): they are page-wide tables, not one picture. Moving them is a later change, if Revathi asks.
- How the panel feels on every screen size. The first check is Revathi's laptop on VW-8.
- The page in a browser beyond reading its content, as before.
- `server/tests` (Docker).

## As built (25 Oct 2026)

Server 0.44.0, plugin 0.42.0. The minimum plugin is 0.42.0: the procedure now gives the links `vw visuals status` prints from 0.42.0. Not yet committed or deployed.

**Server (`visuals_stage`):**
- `waiting`, `item_link`, `film_time`, `split_of`, `_accepted_shots`.
- A `next` line on approve, reject, sequence, select-take, unplace and fix. `_picture_word` and `_approved_next` word it.
- The page view carries `waiting`, and `split` per gap. `status` carries `waiting`; `check` carries `split`.

**The page (`templates/visuals.html`):**
- The shared panel on the Pictures and Takes steps, wider (up to 45 %).
- A sequence or a pair side by side in the panel. A sequence has one Approve and "Reject state N".
- A take plays in the panel with Select and Reject. A sheet shows beside its sources.
- A placed picture reads "Approved · in the film at …" with Remove.
- The viewer: zoom with the wheel or + and −, drag to pan, ← and →, Esc.
- The check in one line.
- The link handling (`#step/group/item`).
- The waiting marks, the per-step counts, the top counter with its list, and Next waiting.
- The server's next line after each verdict.
- The cards a refusal names are outlined.
- The split per gap on the Plan step.
- On a phone, the words box and buttons are pinned.

**The review page:** the button line (O4).

**The tool (`vw`):** `status` lists the waiting items with label and link; each verdict prints the server's next line. The procedure step and `vw.md` say to give the operator the label and the link.

**Tests:**
- `server/unit`: 360 passed. 31 are new in `test_design97_r3_pure.py`. The design/95 page test now looks for the server's next line.
- `plugin/tests`: 256 passed, with 3 known Windows-only failures.
- The plugin is compile-checked.
- The page script parses. It was also run in Node against fixture data on every step and seven links, with no error. The panel's text was read for a sequence, a placed still, a take and a failed candidate.

**Not covered:** the page in a real browser (layout, the viewer's drag and pinch, the phone pin). The first look is on the live page after the deploy.
