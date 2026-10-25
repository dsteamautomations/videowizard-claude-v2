# design/99 — The visuals page: full control, no typing for a click

25 Oct 2026. SK's UI comments on the visuals page. **Nothing is built until SK approves this note.**

The screenshot did not come through with the message. I read "the place where the picture is viewed" as the side panel that opens beside the grid on the References, Pictures and Takes steps (design/80, design/97).

SK, verbatim:
- "I want a close button in that place where the picture is viewed, so that the user can close that and that space is available."
- "I don't want the approval reason for each and every picture. If somebody is clicking it, it is upload, so I don't want to type a reason for approval."
- "For reject, if there is a reason, I don't know what we are going to do with that. Even the reject option, you can remove. I don't want the user to enter reject later. If reject is used, then probably for revision, you let me know. Then we can retain that."
- "the user should be able to have full control on the screen. For example, on the screen, they didn't have a button to close the pop-up picture. When they select the search with keywords, the user might not know whether it is saved or not. For that particular row, they should know the upload action, which is not very clear."

## 1. Answer on Reject: it is used for revision, so keep it

**When a picture is rejected, its reason is read twice:**
- **By the assistant, before the next attempt.** The next composition packet carries it under "earlier rejections" (design/86 K7), so the next picture avoids the same fault. The next picture is then made from the last approved one, never from the rejected one (design/74 L7).
- **By the library's feedback file** (`vw visuals feedback`, design/74 L7), which records what failed and why.

**Recommendation:**
- Keep Reject, with one click.
- Keep the reason, but optional, chosen with quick chips or typed: a reason is what makes the next picture better. Without one, the assistant asks in chat what was wrong.

## 2. What changes

| # | Rule | Where |
|---|---|---|
| C1 | **The panel has a Close (×) at its top right, and Esc closes it.** When nothing is open, the panel disappears and the grid takes the full width. Today an empty panel keeps its column ("Click a picture to see it here"). The viewer already has "Close (Esc)". | `templates/visuals.html` (`split`, `panel`) |
| C2 | **Approve with one click: no typed words** for approving a picture, reference, sheet or style sheet, approving a sequence, Use for the shot, Remove, or Select on a take. The record reads "Approved on the visuals page by SK" (or "Selected …", "Removed …") with the time. Words typed in chat are kept when given. The words box leaves the panel. | `visuals_stage` (`approve_reference`, `sequence`, `_place_still`, `unplace`, `select_take`: the operator's words optional, a default line instead), page, `vw.py` (`--quote` optional), the procedure text |
| C3 | **Reject in one click, the reason optional.** Under the picture: "What was wrong? (optional)", with chips ("wrong subject", "text wrong", "light or colour", "framing", "not like the footage") and a short field. The rejection records at once; a reason saved after it is added to the same rejection. The same applies to a take's Reject. | `reject_reference`, `review_take` (reason optional), page |
| C4 | **The search: one click, and it says what it saved.** Search runs on the button, with no words at the foot: the click is the operator's yes to the web search (design/73's web rule). The row then says "10 pictures found for 'rat trap bond wall' · tick the ones to use". | `search` (the yes is the click; the record reads "Searched on the visuals page by SK"), page |
| C5 | **Ticked is not saved, and the page says so.** A ticked picture shows "ticked · not saved". A bar pinned at the foot says "3 ticked · not saved yet", with **Save 3 pictures** and **Clear**. "Use the ticked pictures" becomes "Save 3 pictures", with no words needed. After saving, each card shows "Saved ✓" and the bar says "3 pictures saved as references for TOWN". Leaving the step or the page with unsaved ticks asks first: "3 ticked pictures are not saved. Leave anyway?" | `pick` (no words), page |
| C6 | **The reference round needs no words either.** Pass 1's Done and pass 2's Done record on the click. | `round_done`, `round_picks`, page |
| C7 | **Every action answers on its own card:** "Approved ✓", "Rejected", "Saved ✓", "Removed". A card being saved shows "saving…". The footer line stays for the longer message. | page |

**Typed words stay for the steps that carry real content or a rule SK set:**
- approving the treatment and accepting the plan's gaps (the operator's yes to the whole plan);
- Revise (what to change);
- approving a reuse of the same footage (design/89 H7, SK's rule);
- correcting the footage character;
- recording gaps.

These are page-wide steps, not one picture each, and they keep the footer's words box.

## 3. References (Mobbin, inspiration only)

- [Magnific's picture panel](https://mobbin.com/screens/785b0693-68e4-4989-ab72-7cb74e3cbce4): the picture large, the actions beside it, × at the top right, and ‹ › to move. C1, C2.
- [Savee's selection bar](https://mobbin.com/screens/631523cf-0305-4b77-9364-bdb28ed91ccd): "3 selected" pinned at the foot with the action and a close, and "Saved" once done. C5.
- [Higgsfield's picked grid](https://mobbin.com/screens/79bc2f66-114a-4b85-b55a-08251214fee3): picked pictures outlined with a tick, and a pinned bar with the count and the actions. C5, C7.

## 4. Runs in progress

Nothing on a run changes; only the page and the rules for optional words do. A record made with words keeps them. VW-7, VW-8 and VW-9 continue unchanged; their next approvals simply need no typing. No plugin update is forced: the minimum plugin stays 0.42.0.

## 5. Tests first

`server/unit/test_design99_pure.py`:
- Each of approve, sequence, Use for the shot, Remove and Select records without words, with the default line, and keeps words when given.
- A reject without a reason records; a reason saved later is added to it.
- Search, pick, round Done and round picks record without words.
- Every step listed in section 2 as keeping words still refuses without them.

The page:
- the panel's ×, the collapse when empty, and Esc;
- no words box in the panel;
- the reject chips;
- "ticked · not saved", the pinned bar, "Saved ✓" and the leave warning;
- the script parses, and a Node run on every step finds no error.

`plugin/tests`: `approve`, `reject`, `sequence`, `still`, `unplace`, `select`, `search` and `pick` post without `--quote`, and the procedure text says the words are optional there.

## 6. Not covered

- The screenshot I didn't receive. If it shows a different place than the side panel, I'll adjust C1.
- How the pages look in a browser beyond their content.
- `server/tests` (Docker).

## As built (25 Oct 2026)

Server 0.46.0, plugin 0.44.0. The minimum plugin stays 0.42.0: an older plugin still sends the words, which are kept. Not yet committed or deployed.

**Server (`visuals_stage.said`):** a click with no words records "Approved by SK", "Rejected by SK", "Placed by SK", "Removed by SK", "Selected by SK", "Searched by SK", "Saved by SK", "Pass 1 done by SK" or "Pass 2 done by SK". The default line names who and what. It doesn't name the front end, because one function serves both.
- **Optional words:** `approve_reference`, `sequence`, `_place_still`, `unplace`, `select_take`, `review_take`, `_search_into`, `_pick_into`, `round_done`, `round_picks`.
- **Reject:** `reject_reference` records without a reason. A reason sent afterwards for the same rejected picture is added to its rejection and to the feedback record.
- **Request models:** `quote` defaults to ''. Remove has its own `UnplaceBody`. A reuse keeps `ReuseApprove` with its required words.
- **Unchanged, words still required:** correcting the footage, Revise, the reuse approval, the drawing spec approval, the treatment, accepting gaps and recording gaps.

**The page:**
- the panel's × and Esc on every step, and no panel column when nothing is open (a closed pending sheet stays closed);
- no words box in the panel;
- Reject records at once, then shows "What was wrong? (optional)" with five chips, a short note, "Save the reason" and "Skip";
- a take's Reject does the same;
- cards say "Approved ✓", "Rejected", "to approve", "being made", and "saving…" while a click is recorded;
- search results show "ticked · not saved" or "Saved ✓";
- the footer says "3 ticked · not saved yet" with "Save 3 pictures" and "Clear";
- the row says "10 pictures found for '…'" and "2 saved ✓ (#1, #2)";
- leaving the step or the page with unsaved ticks asks first;
- the round's Done needs no words.

**The tool (`vw`):** `approve` (and `--file` rows), `reject`, `sequence`, `still`, `unplace`, `select` and `pick` send an empty quote when none is given. `search` still asks for the operator's yes in chat, because in chat there is no click to stand for it. The procedure and `vw.md` say a click needs no typed words.

**Tests:**
- `server/unit`: 390 passed, 22 of them new in `test_design99_pure.py`. Older tests changed: four refusals of an empty quote removed from `test_visuals_stage_pure`, two page needles in `test_visuals_page_pure`, and one in `test_design94_r1_pure`.
- `plugin/tests`: 265 passed, with 3 known Windows-only failures. The plugin is compile-checked.
- The page script parses. A Node run on every step and six links found no error, and the panel reads × · check line · Try a fix · Approve · Reject, with no words box.
