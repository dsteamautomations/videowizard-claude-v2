# design/58 — L14: a network blip is not a defect

Status: proposed, 20 Oct 2026. Source: defect 18 on VW-6 (design/49, 20 Oct).

## What happened

`vw analysis status --wait 600` polled the server every 15 seconds. After three minutes of good polls this Mac lost its network path for about four minutes. The next poll failed with `ConnectError`; the tool returned `tell_builder`, the assistant filed defect 18 as instructed, and the run went on hold (design/48: nothing is recorded while a defect is open) until the builder had read the server logs and marked it fixed. The server was never down. The analysis ran on throughout.

Today one failed connection, anywhere, becomes a defect at once. The tool has the time and the context to tell a blip from an outage; the assistant and the operator do not.

## Change (plugin only)

1. **`request()` retries a connection failure for up to three minutes** (`plugin/scripts/vw.py`). An `httpx.RequestError` other than `ReadTimeout` (`ConnectError`, `ConnectTimeout`, `ReadError`, `RemoteProtocolError`: the connection could not be made or broke) is tried again every 15 seconds until 180 seconds have passed, with one stderr line per attempt: `server not reachable (ConnectError: <exception text>); trying again in 15 s`. A retry sends the same request: writes already carry a `request_id` the server treats as idempotent, so a request that did reach the server is not repeated. `ReadTimeout` keeps its two meanings (still working under `wait`, otherwise unreachable). The retry is in `request()`, so every command, loop or not, gets it; a wait loop's own deadline is unaffected by the retry time.
2. **After three minutes the outcome is `unreachable`, not `tell_builder`.** Exit 2 with the message: `VideoWizard server not reachable from this Mac for 3 minutes (ConnectError: <exception text>). Tell the operator to check this Mac's network, wait a minute, and run the same command again. File a defect only if it is unreachable again.` The exception text names the cause (DNS, refused, reset), which `ConnectError` alone did not.
3. **The command doc** (`plugin/commands/vw.md`, exit-code line): `unreachable` is named beside `tell_builder`: tell the operator, try once more, defect only on the second failure in a row. `plugin/operator-CLAUDE.md` where it says what `tell_builder` means, if it does.

Not changed: the server; `upload_file`'s own retry (design/19 C2); the defect gate (design/48); the 60-second request timeout; `vw connect`'s own polling of the approval.

## Why these numbers

Three minutes of retry plus the operator's one more attempt a minute later covers the four-minute gap seen today without hiding a real outage for long. Fifteen seconds matches the status loops' own cadence.

## Tests first

`plugin/tests/test_stage_calls.py` (sleep patched out, a fake client that fails N times then answers): a `ConnectError` that clears on the third attempt returns the body and printed two retry lines; one that never clears returns action `unreachable` after the 180-second budget with the exception text and `run the same command again` in the message; a `ReadTimeout` is not retried and keeps today's two messages; a retried `write` sends the same `request_id` every time. The doc test for `vw.md` (if one exists) checks the `unreachable` line.

## Not covered

A live blip cannot be staged; the next real one is the check. server/tests untouched.

## Version

Plugin 0.19.1 → 0.19.2; no server deploy. The operator restarts Claude Code once.
