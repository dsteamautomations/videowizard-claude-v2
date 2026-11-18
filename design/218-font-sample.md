# design/218: a sample picture before the font question; a missing neutral colour is Claude's

18 Nov 2026. Approved by SK. Server 0.116.0, plugin 0.100.0, **minimum plugin 0.100.0** (`vw font --sample`).

## What changed

| # | Change | Where |
|---|---|---|
| F1 | One picture of the offered fonts: a row per font with its name, the first label of this film's drawn graphics (else the server's neutral words), `230 x 110 x 75 mm`, and per other language of the film its label where the offer says the font holds it, else "English only". Drawn by headless Chromium (Playwright, as the svg route) with the files under `server/fonts` (`film.font_faces`), on the film record's colours (first colour named is the background), 900 px wide. No AI, no paid call | `server/app/font_sample.py` |
| F2 | `GET /api/runs/{id}/film/font-sample`: the PNG as base64, or `available: false` with "The font sample is not available." (renderer or every file missing), or "not asked" for a film with no drawn graphic | `main.get_font_sample`, `main._font_offer` (shared with `GET /film`) |
| F3 | `vw font --sample` saves `work/chat/font-sample.png` and says "File to show: …", then to ask the question as before; when not available it says the line and to ask as before (exit 0) | `plugin/scripts/vw.py` `cmd_film` |
| F4 | The server's "what next" (`need_font`) and the instruction (section 11) say: show the sample first, then the question unchanged | `visuals_stage.need_font`, `scripts/d218_wording_v3.py` |
| F5 | Step 6 is answered on the page; a chat card only for a question the server asks in the chat (the font) or where the page cannot be shown; a graphic sequence is reviewed at step 6 | `scripts/d218_wording_v3.py` (v3.json sections E and 8, `vw.md`) |
| A1 | A colour the palette names none for: Claude chooses a neutral (chroma, the brightest minus the darkest channel, at most `NEUTRAL_MAX_CHROMA` = 0.10) and records it once per thing with one reason: `vw motion colour --shot D1,D2 --thing walls --colour #5A524C --words "dark warm grey" --reason "the palette named none"` (`POST /visuals/motion/colour`), kept in the session's `added_colours`, never in the accepted plan. A hue, or a second colour for the same thing, needs the operator's words (`--quote`) | `visuals_stage.added_colour`, `add_colour`, `chroma`; `main.visuals_motion_colour`; `vw.py` `cmd_motion` |
| A2 | Every later brief's palette line is the plan's palette plus the added colours | `visuals_stage.palette_line` (in `motion_brief`) |
| A3 | Shown without asking, under Details on the drawn graphic's line: "Added by Claude: dark warm grey for the walls, because the palette named none." | `pictures.colour_notes`, `drawn_line` |
| A4 | The rule writer lists such a colour under "Colours to add", not as a question; the motion skill picks a neutral and names it under "Colours added" in REVIEW.md; section 11 says the assistant records it | `scripts/d218_wording_v3.py` |
| B | The check and the proposal warn (`palette_missing`, the assistant's list) when a part that the drawing specs of two or more drawn shots show has no word in the palette and no recorded colour; only while no gap was ever accepted (editing an approved palette sends the accepted gaps back), so the colour goes into the palette before the operator approves the plan. Built on the specs: before them the plan does not say what a drawn shot shows | `visual_contract.palette_warnings`, `visuals_stage.palette_due` |

The picture heads the card's fonts (the offer's first four, `font_sample.CARD`: the question card holds four and adds Other) under "On the card", then "Others you can name" (two columns above ten).

Edge cases: a long label is shortened at a word with "…"; a font whose file is missing gets a row "not installed on the server", the others are drawn; "Other" is never drawn.

## Old ways

Rows 169, 170 and 171 of `design/35-decision-log.md`.

## Tests

`server/unit/test_design218_colours_pure.py` (A, B); `plugin/tests/test_design218_font_sample.py` (the two commands); `server/unit/test_design218_font_sample_pure.py`: the rows, the HTML, the colours, the wording, the versions, and one real render with the repository's fonts (skipped where Chromium is not installed).

## Not covered

- B matches a part by its last word against the palette's words (a word match): "Brick walls" and "walls" are one thing; "the wall face" and "masonry" are two. A plan approved before its specs exist never gets the warning: A covers it.
- A brand colour rule is not read by the server: the instruction tells the assistant to ask then; the server only refuses a hue without words.
- The step-6 questions list (design/_work/step6-questions-18-nov.md) is a list; nothing beyond A and B was built from it.
- On today's offer every font holds the film's languages (`film.fonts_for` leaves the others out), so "English only" shows only if the offer changes; it is tested on a constructed offer.
- The client card's brand colours are not read: only the film record's colours (asked when the card has none); without a colour, white and near-black.
- Not run on the live server: whether its Chromium starts from the API process and whether its `server/fonts` files are the repository's.
