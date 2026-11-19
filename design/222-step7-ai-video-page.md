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

## The critic's points on the finished branch (19 Nov), each fixed with a test that failed first

`server/unit/test_design222_critic_pure.py`.

| Point | Fault | Fix |
|---|---|---|
| S1 | While step 6 was still being made, finished takes were asked one by one in the chat | `visuals_stage.waiting`: the takes wait for step 6 too |
| S2 | "Use take n after all" rejected the newer take first; a refusal of the earlier one left both rejected | `takes.answer`: the earlier take is selected first (its reason is its timing note when it is short), then the newer one is rejected |
| S3 | After a plain Reject nothing told the assistant to ask what happens to the shot | `takes.rejected_due`, said by `chat_flow.next_item` and after the page's done |
| S4 | A take shot for an earlier plan kept the page closed, with no way out | it counts as complete and is on the page with Make another and Reject (no Select); `guide.same_of` counts the plan in the request's identity |
| S5 | A changed layout lost the order given on the page | `guide.carried`, used by `set_scene` |
| S6 | An order the cost limit refused stayed pending for ever; an order could not be withdrawn | `guide.cap_or_drop` drops it and keeps why; `guide.cancel_order` (`vw guide shoot --shot S --cancel --quote …`) |
| S7 | The line with the amount was not said on the chat path, and was said again on a second "done" | `takes.ordered` counts each order once; the chat item says it when answered in the chat |
| S8 | The looks answer named the pictures' helper for takes and did not count the takes left | `pictures.looks_due`, `record_looks` |
| S9 | A take whose submission was unknown read "could not be made" | it is still open |
| not built | no decision in the run's log for a take ordered on the page | `takes.answer` writes it, with its length and amount |
| lesser | a failed jump measurement read "no jump"; a re-run of the worker's check lost Claude's lines on the card | `guide_worker.jumps` raises; `visual_workers.merged_check` |

Left as it is, and said: the cost limit is tested per line when the page is built, and again when each ordered take is sent (several orders in one visit are refused one by one, in the order the assistant sends them, each said in the chat).

## The second critic's points on cfabf4d (20 Nov), each fixed with a test that failed first

`server/unit/test_design222_critic2_pure.py` (the answers go through the page's own route, `page_flow._pictures_answer`, with nothing mocked) and two tests in `test_design222_browser_pure.py`.

| Point | Fault | Fix |
|---|---|---|
| 1 | One Reject or Make another closed the page and hid every other unanswered take | `takes._state` marks a shot one of whose takes was already answered as `aside`: `complete` does not wait for it. A remake is offered only with its check (`takes.answerable` in `visuals_stage.waiting`). A first take still being made keeps the page closed (D9) |
| 2 | A take shown as "not checked" could be selected after a failing look arrived, against faults never shown | `takes.item_id`: the item's id carries a mark of the check as shown; an answer to an older view is stale |
| 3 | An order given on the page outlived the shot's selection | `select_take` drops it; `guide.shoot` refuses a take for a shot with a take selected |
| 4, 5 | "Use take n after all" wrote a rejection on the newer take and could leave the earlier take accepted after a refusal | only the earlier take is selected; a shot with a selection is not asked about again (`visuals_stage.waiting`); a refusal restores the earlier take's reviews |
| 8 | A take whose page video could not be made had nothing to look at | the line carries each take's frame sheet (`pics`, role `sheet`); the page shows it in the player's place with "The take cannot be played here: these are its frames, in order." |
| 9 | E18: an open question on the shot was ignored | `takes.question_open`: the take is not offered and the shot reads "waiting for you in the chat" |
| 10 | "Make another" on a take with no guide entry saved the rejection and then failed | refused before anything is saved; the button is not offered |
| 6 | No test through the page's route; requirement tests 16, 17, 21, 22 missing | added |
| 7, 11 | E36 a long caption; `vw visuals status` without step 7's counts; E30; the decisions in the log | the caption follows the word being spoken within two lines; `visuals_stage.status` carries the line; a remake whose still or layout card waits reads "waiting for you in the chat"; Select, Reject, "Use take n after all" and a withdrawn order are decisions in the run's log |

## The real page against the approved trial

Checked with VW-12's 17 real takes on the real page file at page areas of 1536 x 510 and 1900 x 830 (no scroll of the page or the main area, no console error; the player's picture is 620 x 349 and 970 x 546). Screenshots and the scripts are outside the repository (`ux1-mockup/step7-trial/real-page/`). The differences from the trial:

1. The trial's own banner is not on the real page.
2. The left list is step 6's: a little wider (230 to 290 px against 210 to 270), its rows a little taller, the dot at the top of a two-line name.
3. The player's background is step 6's black.
4. The details sheet's right column is the take's rows in the server's order (where it sits, how it was asked for, how it was made), then the start picture; the trial had the picture second.
5. In a pause of more than 0.4 s between two words the real page keeps the earlier word marked; the trial marked none.
6. The take's video is kept while its line is open: opening a box or answering does not start it again from 0:00 (the trial did).
7. The end card's rows read across in a grid and the list scrolls inside the card when it is long; the trial's read down in columns.

## Not covered, not verified

- **Nothing has run on a real film.** No take made from a guide exists in the application, so the frames, the measured jump, the helper's check, the page with a guide take's own lines and "Make another" have only run in tests, and the page only with VW-12's takes (made the older way). The first real run must show: frames and the sheet stored for a take; the take listed by `vw visuals pictures --looks` and a look recorded; the page closed until all are checked, then open; a selection recorded from the page; a take ordered with "Make another" sent without a second card, with the one line said.
- The frames Claude gets are not marked with the planned action's seconds; the take's words (`request`) carry them.
- The grey part of a sentence that begins before the shot's gap is not shown (the words of the gap only).
- A drawn graphic beside a shot has no picture in "See it in the film".
- The cost limit: "Make another" is absent when one more take would pass it; several takes ordered in one visit are each refused by the limit when their turn comes (`check_cap`), said in the chat.
- Changing a recorded answer on the page; all shot drawings on one page visit; one rule everywhere for "against the check": not in this build.
- No migration for older films; a film whose reference round is not of today's kind keeps the chat.
- `server/tests` (the database suite) and the whole `server/unit` suite were not run (SK's word of 19 Nov): only the files of this change and every file that pins what it touches.
