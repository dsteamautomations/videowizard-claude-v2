# 35 — Decision log (SK's decisions and suggestions, in order)

Started 17 Oct 2026 at SK's request: every decision or suggestion SK makes is logged here, with the date and where it was carried out. Earlier decisions live in the design notes they shaped (design/21 exact-match editing, design/23 build report, design/19 scenes and pauses).

| # | Date | Decision or suggestion | Where it stands |
|---|---|---|---|
| 1 | 16 Oct | VW-2 continues with the ticket 11 workaround (text graphics made by the editor); the v1 editable-graphics port waits | design/28; ticket 11 open |
| 2 | 16 Oct | After three review rounds the assistant suggests leaving the hard scenes blank | Built (options prompt, round advice) |
| 3 | 16 Oct | Slide numbers must be visible on the footage, not only on the slides | Built (corner labels) |
| 4 | 16 Oct | Contact sheets agreed in principle; take effect from the next run, not VW-2 | design/27, awaiting the requirement list's yes |
| 5 | 17 Oct | SK takes care of all the tests; the builder fixes the patterns, reviews once more, and freezes the code | design/33 fix list, awaiting approval |
| 6 | 17 Oct | Another thread brings the system online; the builder does not touch the live server | design/29 (live-server thread) |
| 7 | 17 Oct | Fresh start: delete VW-2's database records and storage files; keep the v1 folder; no backup; delete the learned client rule; clear the render cache | Done 17 Oct; next run is VW-3 |
| 8 | 17 Oct | VW-3 uses the same clips and script (Rat-Trap Bond Masonry documentary) | Operator copies VW-2's `in` folder to VW-3 |
| 9 | 17 Oct | Contact sheets: not wanted if tied to VW-2; open for discussion as a general feature | design/27; no decision yet |
| 10 | 17 Oct | Options planning (stage 7) stays serial | design/34 |
| 11 | 17 Oct | Before raising analysis concurrency, verify Gemini's limits from official documentation or a small test with about 10 ten-second videos. **No testing starts until SK says so.** | design/34 P3 |
| 12 | 17 Oct | Parallel-work changes are discussion only for now; the quantum and time are estimates SK will not hold the builder to | design/34 |
| 13 | 17 Oct | Every decision or suggestion SK makes is logged | This file |
| 14 | 18 Oct | The workflow is reviewed stage by stage with one agreed prompt (eleven parameters, plus a twelfth on the enforcement layer after the gates/hooks/skills article); dropped from the list: cost before paid calls, cost of revising, a predefined edge-case dataset | The prompt is kept by the Mac builder session; one review file per stage |
| 15 | 18 Oct | After each stage's findings list, the findings are taken one at a time with buttons; SK decides each individually | Applied from stage 1 |
| 16 | 18 Oct | Stage prompts, steps and output shapes must never reach the operator; this is a standing check in every stage review | design/36 1.11 (instruction + hook + guard sentinel); a server-side intake call deferred |
| 17 | 18 Oct | Stage 1 (intake): 20 findings reviewed; 17 go ahead, 3 stay as they are (free-disk check at start, unreadable-pages rule as instruction, no "copy the clips now" sentence); titles need only be non-empty strings; a version suffix is allowed when the same film is made again for a client | design/36; deployed 18 Oct: server 0.3.0 (f84c2b6), plugin 0.2.0 |
| 18 | 18 Oct | Implement stage 1 before reviewing stage 2 (stage 2 needs stage 1's changes in place and the timestamps they add) | This order from now on |
| 19 | 18 Oct | Layer-one plugin tests run on the Mac with pytest in a `.venv`; server tests still need a Docker machine | plugin/tests; server/tests updated but not run on the Mac |
