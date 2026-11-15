# design/205: the Direction alone first; the motion style on the page; the log says what happened

**Status:** built on 15 Nov 2026 (server 0.102.0, plugin 0.87.0, plugin minimum raised to 0.87.0: every laptop updates); **not deployed**; SK's deployment word awaited.

**Why:** SK, 15 Nov 2026, after the stage review of VW-24's treatment (`design/_work/stage-review-VW-24-treatment.md`) and one defect seen on the page.

## SK's points and what is done with each

| # | SK's point | What is built |
|---|---|---|
| 1 | Defect: on the page the earlier Direction under "Changed since you last saw it" is cut ("…drawn: on...") | It was cut on purpose at 400 characters (`visuals_stage.direction_changes`). The new Direction below it was never cut. Now the earlier text is shown whole (a Direction is at most 2,000 characters) |
| 2 | "A still always moves slowly": leave room for a still that must be held steady to be read (a document); the assistant decides | The served sentence now reads: "A still moves slowly; one the viewer must read (a document, a page, a sign) is held steady, your call." |
| 3 | "Three to five beats" should not be fixed; is "a few beats" clear enough? | "A few" alone is too loose. The sentence now gives the test, not a count: one beat for each turn in what the viewer learns, as many as the film's length needs, with one example of scale (about three in a one-minute film). The 400-character limit on the part still holds it short |
| 4 | Keep the Direction first. But do not write the gap lines before the Direction is accepted: write the Direction alone, send it to the page, take the answer, then write the gaps | The server takes a draft that holds only the Direction. The page shows it; when it is accepted the assistant is told to write every gap line and send the whole treatment. The Direction stays accepted when it is sent again unchanged. The instructions say: no gap line before the Direction is accepted |
| 5 | Ask the motion style with buttons, on the same page as the Direction, with the reason for the recommended style | The page's first line is the motion style: every style, the recommended one first with its reason (the film's category), one button per style. It is recorded with the operator's choice as their words |
| 6 | Let the operator see a style: a button and a small display area that shows a frame of their film in that style | Each style has a "Show me" button; a small frame in the film's shape plays the film's title and the Direction's idea in that style. It is a rough sample drawn by the page, not a drawing made by the film's drawing tool; the page says so |
| 7 | Last time not all styles were offered | The page lists all eight, from the server's style files; adding a style file adds it to the page |
| 8 | Log what a draft returned and what the page recorded, with the operator's words | A draft's log line now says: the Direction alone or how many gaps, lines to accept, warnings by kind, reasons missing. Each answer recorded from the page is its own log line, by the operator, with their words (or the button they chose). The record call's line says what was recorded, stale, refused and dropped |

Not taken from the review, because SK did not ask for it: one "done" for both steps (SK wants the Direction settled first), and "Accept all the rest".

## Unstated but expected

- A film from before the film record (no motion style question) sees no motion line.
- A film whose motion style is already chosen sees it as a recorded line, not a question.
- The motion style can be chosen on the page before any Direction is written (`vw visuals page` right after prepare).
- The Direction and the motion style can be answered in the same visit; either may be answered first.
- A Direction-only draft is never recorded as the treatment, even when its one line is accepted.
- The old flow still works: a whole treatment in one send is taken as before (the card path).

## Edge cases

| Case | Handling |
|---|---|
| Direction-only draft, Direction accepted | Not recorded as the treatment. The answer says: write every gap line now and send the whole treatment |
| The whole treatment sent with the accepted Direction unchanged | The Direction stays accepted; every gap line is "to accept" |
| The whole treatment sent with the Direction changed | The Direction returns to "to accept" (as today); the gaps wait behind it |
| A Direction-only draft sent when the draft already has gap lines and the Direction is unchanged | Refused: nothing changed, and the gap lines would be lost; send the whole treatment |
| A Direction-only draft sent with a changed Direction when gap lines exist | Taken: the gap lines go (they are written again from the new Direction, as the rules already say) |
| "Change this" or "Show me a different direction" on a Direction-only draft | As today: sent back with the words; the assistant sends the Direction alone again |
| The second Direction taken on a Direction-only draft | It becomes the Direction; no gap line exists to send back |
| The whole treatment sent before a motion style is chosen | Refused as today (FILM_MOTION); the message now names the page first |
| A Direction-only draft, or a line answer, before a motion style is chosen | Taken: the motion style is asked beside it on the page |
| The motion style answered twice (two rounds, or chat and page) | The second is named as stale; nothing changes |
| A style name the server does not hold | Refused on its line, in the server's words |
| Empty or huge Direction | As today: refused without a Direction; refused over 2,000 characters or a part over its length |
| A page answer the server refuses | Logged as refused on the record line; the other answers are still recorded and logged |

## Failure modes

| Failure | Handling |
|---|---|
| The page cannot be shown | The card, as today. The motion style is then asked in the chat on the refusal, as before today |
| The log row cannot be written | The answer is still recorded (the log is a record; it never fails a step). In the same transaction as the answer, so a rolled-back answer leaves no line |
| An older plugin (0.86.0) | Refused with the line that says to update: its own line after a draft sends the assistant to the card, and its page file has no "Show me" |

## Old ways (design/35)

- 77: the whole treatment written and sent before the Direction is accepted. Kept (still taken by the server) until the Direction-alone flow has carried one film; then refused on SK's word.
- 78: the motion style asked in the chat after a refused treatment. Kept for the card path only, until the card is retired.
- 79: the earlier Direction shown cut at 400 characters. Retired.

## Tests

Server `server/unit/test_design205_pure.py`; the wording pins in `test_design125_stage7_c_pure.py`. Plugin: the page file checks in `plugin/tests/test_design204_page.py`.

## Not covered

- The page under real clicks in this form (motion line, "Show me"): checked on a local copy with stand-in data only, not on the operator's Mac.
- The sample is an illustration of each style's manner by the page's own CSS. It does not use the film's colours or font, and it is not a render of a real shot.
- The card path does not show the motion styles with a preview.
- "Accept all the rest" and one "done" for both steps: not asked for.
