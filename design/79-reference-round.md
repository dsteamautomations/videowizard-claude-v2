# design/79 — The reference round: every element at once, two passes on one page, no shuttling

Status: requirements note, builder, 22 Oct 2026, from SK's model of the same day ("let it first create, pull the reference images and populate it in one shot … the user goes from 1 to N on the page, then comes to the chat … two times at most"); SK: "immediately proceed". Built on that word. Sources: the References step of design/78, design/73 (search, pick, sheets), the operator's per-element loop seen on VW-6, `visuals_stage`, `visuals.html`, `vw.py`, the step text.

## 1. The model

The assistant prepares a **round** for all elements in one shot, before the operator is sent to the page: for each person, object or place element, the best footage frame or frames grabbed (free) and the search keywords it would use. The operator opens the page once:

- **Pass 1, every element at once.** One row per element: its frames, its keywords (editable), and one verdict per row: **approve the frame** (an element with no frame has only the search answer) or **search with these keywords**. One words box for the whole pass, which is also the yes to every search; **Done**. The server then approves the chosen frames and runs the searches itself, so pass 2 is on the page at once.
- **Pass 2, the searched elements.** One row per searched element: the ten pictures, ticks in order, a note per picture, the lightbox; one words box; **Done**. The server makes the picks into web references.
- **Then the chat, without questions.** The assistant reads the round in one call, generates one sheet per element from the frames and picks (paid, informed), and the sheets appear on the page's References step for Approve or Reject with one words box. The operator is on the page twice: the round, then the sheets.

Nothing is paid from a click; the assistant asks nothing per element; every verdict is recorded with the operator's words.

## 2. What changes

| | Change | Where |
|---|---|---|
| Q1 | **The round on the server.** `round_start(elements)`: a list of `{element_id, frames: [reference ids of kind frame, candidates of that element], keywords}` for every non-graphic element of the current plan; stored as `session.round = {n: 1, elements: {...}, at}`; a round replaces an unfinished one. `round_done(verdicts, quote)`: `{element_id: {verdict: approve|search, keywords}}` for every element in the round; `approve` approves the element's round frames (by their stored hash) with the words; `search` runs `search()` with the final keywords and the words as the yes (R6's two-to-six-word rule applies; a search that fails is recorded on the row, the rest go on); the round moves to pass 2 with the searched elements, or is complete when none. `round_picks(picks, quote)`: `{search_id: [{n, note}]}` for the pass-2 rows; `pick()` per search; the round is complete. `status` and the page view carry the round with each row's state. | `visuals_stage`, `main.py` routes `POST /visuals/round`, `/visuals/round/done`, `/visuals/round/picks`, `web.py` acts |
| Q2 | **The page.** The References step shows the round when one is open: pass 1 as a table (element · frames as thumbnails · keywords box · Approve the frame / Search radio), the footer with one words box and **Done (N elements)**; pass 2 as the rows of searched elements with the ten thumbnails, ticks, notes and the lightbox of design/73, the footer with one words box and **Done**; when the round is complete, the element list of design/78 with the sheets to approve and a "Start a new round" note for the assistant. Each picture card shows its own state badge (candidate · approved · rejected), not only the element's. | `visuals.html` |
| Q3 | **The chat path.** `vw visuals round --file out/reference-round.json` posts the round and prints the page link; `vw visuals status --wait 900` waits until the round is complete (the status says `round: pass 1 · pass 2 · complete`); `vw visuals round --done` and `--picks` exist for an operator who answers in chat. Step 4 says: grab a frame for every element the footage has (`frame`, `--file` for several), write the keywords for every element, post the round, send the operator to the page once, wait, then one sheet per element from its frames and picks, then the sheets' approval on the page; ask nothing per element. | `vw.py`, `vw.md`, step 4 |
| | Server 0.29.0, plugin 0.27.0. | |

## 3. Not changed

The functions behind approve, search, pick and the sheets; the words rule; the picks page details of design/73 R4b (reused in pass 2); the other steps of design/78.

## 4. Tests first

`test_visuals_stage_pure.py`: `round_start` refuses a frame that is not the element's candidate and stores the round; `round_done` approves the frames of an approve row, runs the searches of the search rows (Apify faked), records a failed search on its row, moves to pass 2 or completes; `round_picks` makes the references and completes; `status` carries the round. `test_visuals_page_pure.py`: the pass-1 table, the pass-2 rows, the per-picture badge, `Done`. `test_visuals_cli.py`: `round --file` posts the rows; `--done` and `--picks` post; the step names the round and says "ask nothing per element".

## 5. Not covered

server/tests (Docker); the page under a real session (SK's next look); the assistant preparing the whole round on its own (the step says it; VW-6 is the check).
