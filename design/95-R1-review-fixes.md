# design/95 — Release 1's review: the fixes

24 Oct 2026. This answers the code review of design/94, Release 1 (commit 63b0802, live as server 0.41.0). SK: "think from a user perspective, and whichever is the best option, you can choose that and implement, and then commit and deploy." So each choice below is the builder's, made from the operator's seat, and recorded here.

## The fixes

| # | Finding | The choice, from the operator's seat |
|---|---|---|
| F1 | An automatic fix of a state counts as a second picture for that step, so the sequence refuses | **A fix stands in for its original.** In the order of states, a fix that is not rejected takes its original's place, and the states made from the original follow the fix. The operator sees one picture per step, the fixed one. Rejecting the fix brings the original back. Automatic fixes stay until Release 2 (design/93 X1), so this case is common. |
| F2 | Rejecting a step leaves the steps made from it as stray first steps, and the refusal names the wrong step | **Pictures made from a rejected picture leave the order.** They were drawn on a step the operator turned down. The refusal then reads plainly, for example "AN1 plans 3 states; its pictures make 1: state-TITLE-a2", and the next states are made from the new one. |
| F3 | A still shot that holds a picture hides new candidates for it | **The shot box shows the picture in the shot, then any new picture made for the shot** under "A new picture for this shot · approving replaces the one in the shot". After Approve, the page says where the picture went and what it replaced. A graphic sequence that is held shows the number of new pictures and says to Remove the sequence to rebuild it. |
| F4 | A video shot's box lists other shots' start and end images, and its "your turn" line counts them | **A video shot counts only its own start and end images.** Pictures with no shot recorded (before 0.38.0) still count by element, as before. |
| F5 | The plugin checks the minimum version only at `vw start`. Its own version is read from an environment variable nothing sets, so it always reports 0.1.0: raising the minimum would have refused every plugin at `vw start` | **The plugin reads its version from its `plugin.json` and sends it with every call (`X-VW-Plugin`).** The server refuses any `/api/` call from an older plugin, or from one that sends no version (0.39.0 and before), except `/api/meta`, `/api/auth/…` and `/api/connect…`. The message: "Your vw plugin (X) is older than this server needs (0.40.0): update it and restart Claude Code, then run the same command again." The minimum becomes **0.40.0**, this release's plugin, because no earlier plugin sends its version. An old plugin is told to update; it never works on silently. The pages are unaffected: they use the `/runs/…` routes. |
| F6 | The H5 refusal lost its hint about a return shot | Restored: "H5: this picture is already in B06D_S1. Two shots never show the same picture: compose another (a reimagined shot, return_of, for a return), or take it out there first: `vw visuals unplace --shot B06D_S1`, or Remove on the page." |
| F7 | A state or end image may name a different shot from its parent's | **A warning, not a refusal**, because a drawing may be continued in another shot on purpose: "made from K1, which was made for VS1; this picture is listed and checked under VS2". |
| F8 | `approve --file` does not say where each picture went | The summary adds "K2 placed in DG1 (replaces K1)" for each placed picture. |
| F9 | Two edge cases of design/94 had no tests | Tests added: approving the same picture twice, and a fix inside a sequence (F1). |
| F10 | (seen on VW-7's page) Shots without a title read "B01_S2 · · keyframe" | The empty title is left out: "B01_S2 · keyframe · keyframe-TOWN". |

## Edge cases

- A fix and its original both rejected: neither is in the order, and the steps made from the original leave it too (F2).
- An original approved and its fix a candidate: the fix still stands in (F1). The operator can reject the fix to keep the original.
- The builder's own `curl` to `/api/…` (for example a job release) needs the header now: `-H "X-VW-Plugin: 0.40.0"`.
- `vw start` keeps its own check, now with the real version.
- The server tests (`server/tests`, Docker) send the header from their client fixture.

## Tests first

- `server/unit/test_design95_pure.py`: F1 (stands in; rejecting the fix brings the original back), F2, F3 (the page view carries the placed picture's id), F5 (the refusal rule: missing, old, current, exempt paths), F6, F7, F9, the page text for F3, F4 and F10.
- `plugin/tests/test_visuals_cli.py`: the version comes from `plugin.json` and goes with every call (F5); `approve --file` names the placements (F8).

## Order of the deploy

Server 0.42.0 first, then plugin 0.40.0. From the server deploy until each operator updates, their plugin is refused with the update message. Revathi updates by hand, as before.

## Not covered

- `server/tests` (Docker): the fixture change is not run here.
- The page in a browser beyond reading its content (the pane is hidden here, so no screenshots).

## As built (24 Oct 2026)

Server 0.42.0, plugin 0.40.0, minimum plugin 0.40.0.

- `visuals_stage.state_chain`: a fix stands in for its original; a picture made from a rejected one leaves the order. The H5 hint is back. A picture naming another shot than its parent's is warned. The page view's asset carries `reference_id`.
- `main.plugin_refusal` and the `plugin_version_gate` middleware: 426 `PLUGIN_TOO_OLD` for an `/api/` call with no version or an older one, except `/api/meta`, `/api/auth/…` and `/api/connect…`.
- `vw.plugin_version()` reads `plugin.json`. Every call sends `X-VW-Plugin`, uploads to our own server too. `approve --file` names each placement.
- The page: a filled still shot lists new pictures made for it under "A new picture for this shot · approving replaces the one in the shot". A held sequence counts its new pictures. After Approve the page says where the picture went and what it replaced. Video boxes count only their own start and end images. An empty title is left out of a card.
- `server/tests/conftest.py`: the client sends a current version.

Tests: `server/unit` 310 passed (10 new in `test_design95_pure.py`; the design/94 H5 test reads the restored wording). `plugin/tests` 246 passed, with 3 known Windows-only failures. Plugin compile-checked. The page script parses. The version gate was checked on the app itself: no version gives 426 with the message, 0.40.0 passes, and `/api/meta` answers.
