# design/222: step 7, AI video, on the decisions page

19 Nov 2026. Approved by SK in the builder thread ("Yes, build it", 19 Nov, relayed). Built on the branch `step7-page`; not released: no version bump, no deploy.

The approved requirement list, with the trial, SK's answers and the conflicts between them: `design/_work/step7-build-requirements-19-nov.md` (revision 3, sections 1a and 1b are what the page shows). The study: `design/_work/step7-what-to-show-19-nov.md`. The test of Claude's check: `design/_work/step7-take-check-test-result-19-nov.md`. The contract and its frozen fixture: `design/222-contract.md`, `server/unit/d222_takes_round.json`. The trial page and the evidence (videos, frames, screenshots) are outside the repository, in `ux1-mockup/step7-trial/` on the builder PC.

## The requirement, in short

1. The finished AI video takes are judged on the decisions page, all together, once every take of the film is made and checked. In view for a take: the take playing, the shot's name, the words spoken during the shot marked in time, the check as one short line, and Select, Make another, Reject. Two takes of a shot are two tabs. "See it in the film" and "Details" open over the page.
2. What is decided before a shot's first take is paid for stays a card in the chat: the layout drawing, the still, the word to make the take, and "send the same request once more".
3. Claude checks each take from frames the server takes from it; Gemini 3.8 Flash no longer watches it. The server measures real footage, the length, the first frame and one continuous shot.
4. "Make another" on the page is the operator's word for one more take: no second Shoot card. After "done" the chat says one line with the number of new takes, their length and the amount, and asks nothing.
5. While takes are being made or checked the page is closed and the chat says one line of counts.
6. A recorded answer stays in the list with its decision; it is changed in the chat.

## SK's answers (19 Nov 2026)

D1 no cost on the page. D2 two takes: two tabs, one in view at a time. D3 rejecting needs words. D4 "Make another" on the page; D4a its price is said in the chat after done, not asked. D5 Claude checks ("the claude checks can be retained", after the test). D6 selecting against a failed check needs a typed reason. D7 an earlier rejected take may be used after all, asked once. D8 a recorded answer is shown and changed in the chat. D9 the page opens when every take is made and checked. D10 no take shown one by one in the chat: the line of counts only. D11 the layout drawing stays a chat card for now. D12 "AI video" and "take". Then: "too cluttered" (the trial redone with less in view, approved) and "Words only, no sound" (the words in time).

## The test of Claude's check (19 Nov)

VW-12's 17 takes, judged from frames by six helpers that had not seen Gemini's results: 197 lines; 150 both passed, 8 both failed, 6 only Gemini failed, 33 only Claude failed. Claude found a jump to another view inside three takes that Gemini passed (one is the only take SK rejected). ffmpeg's scene score above 0.25 marks exactly those three takes, at 1.1 s, 1.5 s and 4.0 s. Built from it: the half second, the sheet at four a second required, the measured line "one continuous shot", and two rules for the helper (what the still already shows is not the take's fault; nothing that only motion shows is asked of frames).

## What is built

| Requirement | Where |
|---|---|
| Each AI video shot's state, the line of counts, when the page opens | `server/app/takes.py`: `_state`, `expected`, `complete`, `status_line` |
| A ready take is not asked one by one; the dead start-picture branch | `visuals_stage.waiting` |
| A take is offered only with its check, or 30 minutes after Claude was asked | `takes.offered`, `asked`, `due` |
| Claude's check: the takes due, the record of a look, the scorecard from it | `takes.listed`, `record`, `look_lines`; `pictures.looks_due`, `record_looks`, `TAKE_LOOK_HOW`; `main.py` (the two looks routes); `plugin/agents/vw-take-look.md` |
| The frames every half second, the sheet required, one continuous shot, the frame rate "24/1" | `guide_worker.half_second_frames`, `jumps`, `continuous_line`, `frame_rate`, `take_checks`, `scorecard` |
| Gemini no longer watches a guide take | `visual_workers.take_reading`, `check_take` |
| The page's line of a take; the check as one line; the words in time; before and after | `takes.line`, `_take`, `check_view`, `caption`, `_beside`, `recorded` |
| Select, Make another, Reject, Use take n after all | `takes.answer`; the chat item in `chat_flow._waiting_items` |
| "Make another" is the word for one more take; no second Shoot card; the one line after done | `guide.word_for`, `shoot`, `set_cause`; `chat_flow._guide_items`; `takes.again_due`, `ordered`; `page_flow.page_record` |
| The step after the pictures; the round open and closed; a video copy for every take | `page_flow._plan_step`, `_takes_lines`, `_takes_page`, `_with_videos` |
| The page layout `takes` | `plugin/pages/decisions.html` |
| The served text; the command text; the guide skill | `scripts/d222_wording_v3.py` (registered in `scripts/c1_split_v3.py`), `server/procedures/v3.json`, `server/retired-sentences.json`; `plugin/commands/vw.md`; `plugin/skills/guide/SKILL.md` |
| The tool sends `vw guide shoot` with no `--quote` | `plugin/scripts/vw.py`, `main.GuideShoot` |
| The old ways | `design/35-decision-log.md`, rows 226 to 231 |

Tests: `server/unit/test_design222_takes_pure.py` (the server, the served text, the plugin, the log) and `server/unit/test_design222_browser_pure.py` (the real page file in a browser, with the fixture).

## Not covered, not verified

- **Nothing has run on a real film.** No take made from a guide exists in the application, so the frames, the measured jump, the helper's check, the page with a guide take's own lines and "Make another" have only run in tests, and the page only with VW-12's takes (made the older way). The first real run must show: frames and the sheet stored for a take; the take listed by `vw visuals pictures --looks` and a look recorded; the page closed until all are checked, then open; a selection recorded from the page; a take ordered with "Make another" sent without a second card, with the one line said.
- The frames Claude gets are not marked with the planned action's seconds; the take's words (`request`) carry them.
- The grey part of a sentence that begins before the shot's gap is not shown (the words of the gap only).
- A drawn graphic beside a shot has no picture in "See it in the film".
- The cost limit: "Make another" is absent when one more take would pass it; several takes ordered in one visit are each refused by the limit when their turn comes (`check_cap`), said in the chat.
- Changing a recorded answer on the page; all shot drawings on one page visit; one rule everywhere for "against the check": not in this build.
- No migration for older films; a film whose reference round is not of today's kind keeps the chat.
- `server/tests` (the database suite) and the whole `server/unit` suite were not run (SK's word of 19 Nov): only the files of this change and every file that pins what it touches.
