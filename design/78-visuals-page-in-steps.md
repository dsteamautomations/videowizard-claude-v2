# design/78 — The visuals page in steps, in the voices page's pattern

Status: requirements note, builder, 22 Oct 2026, from SK's finding L45 the same day ("this page is looking very cluttered; refer to the voices page; split into tabs or pages; the font and background like the voices page"). For SK's go. Sources: `visuals.html` (310 lines after design/73), `voices2.html` (design/55: four steps on a sticky line, one view at a time, a footer with one primary action, zebra tables, a docked player), `web.py`, `page_view`.

## 1. What changes

One page, `/runs/<code>/visuals`, rebuilt on the voices page's frame. Nothing changes on the server's functions or the `vw` tool; the page's data read and its act route stay as they are, so the chat path and the page remain the same steps.

| | Change | Where |
|---|---|---|
| U1 | **Six steps on a sticky line**, as the voices page has four: **Treatment** · **Plan** · **References** · **Pictures** · **Takes** · **Record**. One view at a time; the line marks the step the run is at (from the data: no treatment → Treatment; treatment, no plan → Plan; plan, gaps to accept → Plan; accepted gaps, sheets missing → References; and so on) and lets the operator open any earlier or later step. The step chosen is kept in the browser so a refresh returns to it. | `visuals.html` |
| U2 | **Treatment**: the intended visuals and the treatment table as today, the approve box in the footer (the draft after a record badge stays). | |
| U3 | **Plan**: the gaps as a table (gap, words, route, length, shots, state) with Accept and Revise per row and the words box in the footer; a gap's shots fold open under its row. The element list is not here. | |
| U4 | **References**: one element at a time, as the voices page shows one voice's tryouts: a left list of elements with their state (seen in the footage · pictures ticked · sheet approved · needs a picture), the chosen element's section on the right (footage first, the search box, the ten thumbnails, the lightbox, the ticks, the notes, nothing fits, the sheet). An element collapses in the list once its sheet is approved. | |
| U5 | **Pictures**: per shot, the candidates and their checklists, Approve and Reject, stills held and sequences approved, as today, grouped by gap with a gap filter. | |
| U6 | **Takes**: per video shot, the pair (start and end) and the takes with the docked player of the voices page, Select and Reject. | |
| U7 | **Record**: the gaps ready to record, the spend meter, the Record button in the footer. | |
| U8 | **Look**: the voices page's stylesheet classes (the `.v2` frame: top line, steps, zebra tables, footer, player, badges) shared by both pages, so the font, the background and the controls are the same; the light/dark switch of design/35 row 44 applies. | `visuals.html`, the shared stylesheet |
| U9 | **The footer** carries one words box and the step's primary action (Approve the treatment · Accept / Revise · Use the ticked pictures · Approve / Reject · Select · Record), as the voices page does. | |
| | Server version bump only (template), no plugin change. | |

## 2. Not changed

The data the page reads (`/visuals/data`), the actions it sends (`/visuals/act`), the server functions behind them, the chat path, the words rule (every button with the operator's words), the polling and the reload on return (design/74 L29).

## 3. Tests first

`test_visuals_page_pure.py` by text: the six step names and the step line; each step's primary action present; the References view carries the picks page points of design/73 R4b; no cap button; the element sections are not on the Plan view. `test_review_page.py`'s rule: every path the template calls has a route.

## 4. Not covered

server/tests (Docker); the page under a real session: SK's next look is the check; the shared stylesheet's effect on the voices page itself (checked by reading).

## 5. Order

SK's go → the text tests → the template → the server version → commit and push → deploy the server (nothing runs on VW-6 during it) → design/35 row, design/49 line.
