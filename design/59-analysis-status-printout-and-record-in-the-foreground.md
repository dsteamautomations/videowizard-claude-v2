# design/59 — L15 the analysis status printout, L16 media record in the foreground

Status: SK said go ahead, 20 Oct 2026 (design/49 candidates from VW-6).

## L15 — `vw analysis status` prints what the assistant acts on

**What happened.** On VW-6 the status command printed the server's whole answer: 46 units, each with its full summary card, cost and timestamps, 130–135 KB. The desktop app parked it (as in defect 17) and the assistant fell back to `vw next` and `show --unit` to find the two open units. The step says "report its line (counts and about how long is left)"; the card of a clip is read with `vw analysis show --unit` when it is needed.

**Change** (`plugin/scripts/vw.py`, `cmd_analysis`, `status`): the printed JSON is `counts`, `cap`, `units` (the number), `open` (unit, status, phase for every queued, running or storage-pending unit), `decide` (unit, status, error for every unit that needs a decision and is neither excluded nor recorded), `excluded` and `recorded` (numbers). No per-unit summary, cost or timestamp. The stderr line (counts, time left or the units that need a decision) is unchanged, as is the wait loop. At 46 clips the printout is under 2 KB; `show --unit` keeps the card.

**Tests first** (`plugin/tests/test_analysis_cli.py`): the printed JSON of a status with retained, running and failed units carries counts, the open list with phase, the decide list with the error, and no `summary` anywhere; the existing wait tests still pass on the line.

## L16 — media record runs in the foreground

**What happened.** The assistant ran `vw stage media record` as a background command "because it can take a while", then could not read the finished command's output file (outside the run, rightly blocked) and confirmed with `vw next`. The receipt (design/57) was never seen.

**Change** (`server/procedures/v2.json`, media step 3, text only): "Run it in the foreground with a timeout of at least 30 minutes, never as a background command: it prints one line per finished clip while it runs and the receipt at the end, and a background command's output cannot be read."

**Tests first** (`plugin/tests/test_media.py`, the steps test): the step names the foreground and the timeout and warns off the background.

## Not covered

server/tests (Docker). The next run's media and analysis stages are the live check.

## Versions and deploy

Plugin 0.19.2 → 0.19.3 (L15); server 0.20.2 → 0.20.3 (L16 is in the procedure the server serves). Both deploys; the workers restart (VW-6 is at the options stage: a deploy drains any running render or check first); the operator restarts Claude Code once.
