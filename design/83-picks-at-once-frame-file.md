# design/83 — The picks downloaded at once; `frame --file`

Status: requirements note, builder, 22 Oct 2026, from the parallelism audit (`parallelism-audit-2026-10-22.md`, SK: "see if all the opportunities are properly used"). Waits for SK's go.

| | Change | Where |
|---|---|---|
| P1 | **The picks' downloads run at once.** `_pick_into` fetches every chosen picture (and its thumbnail fallback) in a thread pool of 8, then records the references in the ticked order; a failed download is still that pick's failure, the rest are kept. `round_picks` gathers the picks of every search first and downloads them all in one pool, so pass 2 with ten elements takes seconds, not minutes. | `visuals_stage._pick_into`, `round_picks` |
| P2 | **`vw visuals frame --file out/frames.json`**: rows `{element, clip, at, name, subject}`, one call per row in order, stopping at the first refusal (as `still --file`); the step and the command text name it beside the round. | `vw.py`, `vw.md`, step 4 |
| | Server 0.30.1, plugin 0.28.1. | |

Tests first: `test_visuals_stage_pure.py`: three picks whose fakes only pass a barrier together are all kept, in order; a failed one is reported alone. `test_visuals_cli.py`: `frame --file` posts the rows in order and stops at a refusal. Not covered: server/tests (Docker); the page under a real session.
