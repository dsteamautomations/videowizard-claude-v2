# design/178: the reference round, faults 1 to 4 of the VW-20 test run, and the drawn-shot check

11 Nov 2026. Approved by SK ("Approved, build"). Requirements, edge cases and failure modes: `videobuilder-v4/phase2/testrun/requirements-faults-1-4.md`. The test run and all its faults: `videobuilder-v4/phase2/testrun/report.md`.

## What changed

| # | Change | Where |
|---|---|---|
| F1 | The page data carries the price of one set on this film (`budget.set_inr`). Step 1's and step 2's confirmations show the amount from it; no amount when it is missing | `visuals_stage.page_view`; `visuals.html` `step1Counts`, the step 2 confirmation |
| F2 | An approved own picture of a thing or a place is its reference: Done at step 1 makes no set for it (`own: true` on the round's row, with `from_footage`). The same when the picture is uploaded on a card whose set was not made | `visuals_stage._from_footage`, `supply_own`; `visuals.html` |
| F3 | One state per card. While some sets are being made the page shows step 2: ready sets are answered, a card being made says so, Done stays switched off with the reason. The server takes an answer for a ready set meanwhile and refuses Done by name | `visuals_stage.set_answer`, `round_sets`, the waiting list; `visuals.html` `renderKeptRound`, `keptCard`, the foot |
| F4 | A set that failed in the call says why in one plain sentence (`problem`), and its card offers Make it now, Upload my own picture, Set aside | `visuals_stage._set_state`, `_fail_words`; `visuals.html` `notMade` |
| F5 | After the round, a thing set aside or with its own picture never says "set made: judge it on step 2" | `visuals.html` `elState` |
| M1 | The timing file of a drawn shot (`index.motion.json`) is written only when it holds a cue. HyperFrames calls an empty one invalid, so every helper check reported a false error | `motion.prepare` |

## Old ways

- **Retired:** "the pictures are being made; nothing to do yet" as a state of the whole step. A film on the kept round never shows it again.
- **Retired:** an own picture uploaded at step 1 as extra material beside an AI set (things and places, kept round). Uploaded while its set is being made, or beside a set that is back, it is still one more choice of starting picture, as before.
- **Kept:** `budget.prices.image_inr` in the page data, for the other estimates on the page.

## Tests

`server/unit/test_round_faults_pure.py` (18); `server/pagetests/test_faults14.py` (10) on six new states of `build_states.py`. Three older tests changed to the new behaviour (named in the commit).

## Not covered

- Faults 5 to 11 of the report.
- Own pictures for people (U19, not ruled).
- Removing an own picture after it became the reference: it is locked like any starting picture.
- Cancelling a set that is being made.
- The database tests and a real Python 3.9 (as before).
