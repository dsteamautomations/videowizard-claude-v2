# design/80 — The picks page as a split view: the grid stays still, the chosen picture opens beside it

Status: requirements note, builder, 22 Oct 2026, from SK's look at pass 2 on VW-6 ("the options come below after I select… if it can open up on the side, like a split view, it will be great. Even the buttons are actually disturbing"). Waits for SK's go. Sources: `visuals.html` (`renderRound`, `resultCard`, `lightbox`, `bigPicture`), design/73 R4b, design/79 Q2; Mobbin screens of Magnific, Gamma, Savee, Meetup, Later and Higgsfield (a grid or large picture with a fixed detail column on the right; selection shown as a count and a tray, never as controls under the thumbnails).

## 1. What is wrong today

On pass 2 a ticked card grows a note box and four chips under it, so the grid reflows and the row jumps every time a tick is set. The large view is a dark overlay that covers the grid, so comparing two pictures means open, close, open. Pass 1 opens a footage frame the same way. The Approve and Reject buttons under the reference cards on the element view do the same to that grid.

## 2. The model

The References step becomes two columns: **the grid on the left, a detail panel on the right.** Clicking a picture selects it; it opens in the panel, not over the grid and not under it. The grid never changes shape: a card is the thumbnail, its order number when ticked, and one line of caption. Everything else about a picture (the tick, the note, the chips, the source link, Approve and Reject) lives in the panel.

- **The panel** (sticky, about a third of the width): the picture large; under it the element, the site, the size and a source link; then the controls for that picture: pass 2, **Tick as Image N** or **Untick**, the note box and the chips; the element view, **Approve** and **Reject**; pass 1 and footage frames, nothing to do, only the picture. **‹ Previous** and **Next ›** and the arrow keys move through the pictures of the same row; Escape clears the panel. A tick or a note changes only that card's badge, never the grid's layout.
- **The footer** on pass 2 shows the ticked pictures as numbered chips (Image 1 · P_KILN · 3, …), each a click back to its picture, and a ✕ to untick; the count and the words box as today; **Done**.
- **Narrow screens** (under 900 px): the panel sits under the grid as a card, which is the only place the picture opens below.
- The dark overlay (`lightbox`, `bigPicture`) is no longer used on the References step. It stays on Pictures and Takes until those steps are looked at.

## 3. What changes

| | Change | Where |
|---|---|---|
| S1 | `resultCard` and `refCard` become thumbnail, order badge, state badge and caption only; no note, chips, Approve or Reject inside the card. | `visuals.html` |
| S2 | A `panel(sel)` function renders the detail column for the selected picture (`{search_id, n}` for a search result, `{ref_id}` for a reference); the page keeps `selPic` beside `selEl`; the pass-1 table, the pass-2 rows and the element view render inside `.split` (grid left, panel right). | `visuals.html` |
| S3 | The footer on pass 2 lists the ticks as chips; a chip selects its picture, its ✕ unticks. | `visuals.html` |
| S4 | Keys: arrows move within the row, Escape clears the selection; the note box keeps the focus while typing (the panel re-renders only on a tick, not on input). | `visuals.html` |
| | Server 0.30.0; no route, no plugin change (the page only). | `config.py` |

## 4. Not changed

The round model, the acts and routes, the words rule, the picks' order and notes as posted, the other steps, the chat path.

## 5. Tests first

`test_visuals_page_pure.py`: the page carries the `.split` frame and the panel's controls (`Tick as Image`, `Untick`, `Previous`, `Next`); `resultCard` text carries no `textarea`; the footer chip markup for a tick. Rendering is browser-side, so the needles check the script text; SK's look at VW-6 is the real check.

## 6. Not covered

server/tests (Docker); the page in a browser (no local server; SK's next look on VW-6); the Pictures and Takes steps keep the overlay.
