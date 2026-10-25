# design/100 — Saved picks are approved; the panel's buttons always in view

25 Oct 2026. SK, on VW-9's References step (two screenshots). **Nothing is built until SK approves this note.** SK, verbatim:

> "I selected the picture, but I had to scroll down till the end of the page to see the approve button. You can either show only the selected image and make the other things collapsible (even the dimensions and other text), just like how we have done in the previous screens, so that they'll be able to see the approve. Since they are already approved in the previous screen, this seems like a redundant approval again. Think about it. If the user is selected in the previous screen, it can come here with the updated status. This can be shown to the user so that it can avoid two clicks by the user. Tell me what you think about this."

## 1. What I think

SK is right on both counts.

- **The second approval is redundant.** In pass 1 of the reference round, Done approves the footage frames (design/79). In pass 2 the operator looks at the web pictures, ticks the ones to use, adds notes, and presses Done. Yet those ticked pictures are saved as *candidates* (`_store_reference`), so the References step asks for an Approve again. The same happens with "Save N pictures" outside the round. Ticking and saving is the operator's choice, made while seeing the picture, so it should count as the approval.
  - **One case still needs a look:** a downloaded file that differs from what was ticked (the site served a thumbnail, or a different image). For that, Reject stays on every approved picture, and the card says when the picture came from a thumbnail.
- **The buttons fall below the screen** because the panel sticks to the top of the page with no height limit. A tall picture plus its details pushes Approve and Reject out of view, so the operator scrolls the whole page to reach them.

## 2. What changes

| # | Rule | Where |
|---|---|---|
| S1 | **Saved picks are approved when saved.** The pictures saved by pass 2's Done, or by "Save N pictures", are stored as approved, recorded as "Approved when saved by SK", with the same hash a manual approval keeps. The element then shows "pictures approved, sheet to make", and the assistant makes the sheet. Nothing waits on the operator for those pictures. | `visuals_stage._pick_into` (and through it `round_picks` and `pick`) |
| S2 | **Reject stays available** on an approved web picture, for a downloaded file that isn't what was ticked. A picture saved from the site's thumbnail says so on its card ("saved from the thumbnail: check it"). | page (the card); `reject_reference` already rejects an approved picture |
| S3 | **The panel's buttons are always in view.** The panel fits the screen (its height is the window's height minus the header and footer) and scrolls inside itself. The buttons sit in a bar pinned to the bottom of the panel. The picture is at most half the window's height. | page CSS (`.panel`, `.act`) |
| S4 | **The panel shows only what is needed to decide:** the picture, one line (element · name · status), and the buttons. The rest folds into "Details": the source and its size, the check lines, the note, the "made from" sources. This is the folded pattern the check line already uses (design/97 K1). | page (`panel`) |

The chat path follows S1 by itself: `vw visuals pick` and the round go through the same server function. The procedure's "show each (`fetch --ref`) and approve with its hash" after a pick becomes "the picked pictures are approved when saved; show them, and reject one only if the saved file is not the picture ticked."

## 3. Runs in progress

- **VW-9** has 3 web pictures waiting on References, saved before this change. They stay candidates: nothing is changed on a run without the operator. Today, one click on Approve each (no typing since design/99) clears them.
- **Every pick saved after the release** arrives approved.

## 4. Tests first

- `_pick_into` stores approved pictures, with the approval recorded and the hash kept. `round_picks` and `pick` do the same.
- A saved pick can still be rejected.
- A thumbnail-saved pick carries its flag to the page.
- The page:
  - the panel's height rule and its internal scroll;
  - the pinned button bar;
  - the picture's height limit;
  - "Details" folding the source, size, checks and note;
  - the thumbnail line on the card.

  The script parses, and a Node run on every step finds no error.
- `plugin/tests`: the procedure says the picks are approved when saved.

## 5. Not covered

- The page in a real browser beyond its content. The first check is SK's screen on VW-9.
- `server/tests` (Docker).

## As built (25 Oct 2026)

Server 0.47.0, plugin 0.45.0. The minimum plugin stays 0.42.0. Not yet committed or deployed.

**Server:**
- `_pick_into` stores each saved pick as approved, with `approval` = {by, at, sha256, quote}. The quote is "Approved when saved by SK", or the operator's words when given. `round_picks` and `pick` both go through it.
- The page view carries `from_thumbnail`.
- Reject works on an approved web picture, as before.

**The page:**
- The panel is at most `calc(100vh - 210px)` tall and scrolls inside itself.
- Its button bar (`.act`) is pinned to the panel's bottom on every screen size, and the picture is at most 50 % of the window's height.
- The kind, size, note and thumbnail line fold into "Details". So do the "made from" sources, except for a sheet still waiting for approval, which keeps them beside it (design/97 R1).
- A card saved from the thumbnail says "saved from the thumbnail: check it".

**The assistant:** the procedure's pick sentence and `vw visuals pick`'s reply say the picked pictures are approved when saved, and to reject one only if the saved file is not the picture ticked.

**Tests:**
- `server/unit`: 398 passed, 8 of them new in `test_design100_pure.py`. One older pick test now expects "approved".
- `plugin/tests`: 266 passed, with 3 known Windows-only failures. The plugin is compile-checked.
- The page script parses, and a Node run on every step and five links found no error.
