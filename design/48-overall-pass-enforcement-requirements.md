# 48 — Overall pass, parameters 12 and 13: the web gate, the open-defect gate, two tool paths, read-only records (approved by SK 18 Oct 2026, implemented the same day)

Source: the overall pass of the stage review prompt's parameters 12 (enforcement layer) and 13 (tool allowance) across the whole process on 18 Oct 2026, and SK's decisions on its 4 findings. Nothing here makes a paid call. The guard has not blocked anything live since it shipped; SK's stage 2 subagent check is still pending and the `Agent` tool stays blocked until it passes.

## Decisions carried from the review
- A web search or fetch needs the operator's recorded yes; the guard holds the rule (O.1).
- An open defect stops every write on the run until the builder marks it fixed (O.2).
- `vw defect --log` reads only inside the run folder; `vw start --script` refuses hidden and system places and is logged (O.3).
- The guard log, the run manifest and the active marker are read-only for the assistant (O.4).

## A. The web gate (O.1)

| Piece | What |
|---|---|
| `vw web --about "<X>" --ok "<the operator's words>"` | Writes `runs/<code>/work/web-ok.json`: `{about, ok, at (UTC), by: 'operator', calls: []}`. Refused without `--ok` or without an active run. Prints "web permission recorded for <X>; valid ten minutes; say what you searched and show what you found". |
| The guard on `WebSearch` and `WebFetch` | Reads the active run's `work/web-ok.json`. Allowed when it exists and `at` is less than ten minutes old; every allowed call is appended to the file's `calls` (tool, query or url, time) and to `work/guard.log` as `· WebSearch · allowed (<about>) · <query>`. Otherwise blocked with: "Blocked: a web search needs the operator's yes. Say to them: 'I am deviating from the usual procedure. I want to search the web for X, because Y. The result may affect Z.' On their yes run `vw web --about "X" --ok "<their words>"`, then search." |
| Ten minutes, several calls | One yes covers the search and the fetches that follow it on that subject for ten minutes; a new subject or a later search needs a new yes. The assistant still says what it searched and shows what it found (instruction, as today). |
| `ToolSearch` | Still allowed (it loads schemas only). |
| Outside a run | No active run → blocked (no file to read). |
| vw.md, operator-CLAUDE.md | The web paragraph names the command: "…search only after the operator says yes, recorded with `vw web --about "X" --ok "<their words>"`; the guard refuses a search without it…". |

## B. The open-defect gate (O.2)

| Piece | What |
|---|---|
| Server | `core.load_run(conn, user, run_id, lock=True)` (every write takes the lock) refuses with `409 DEFECT_OPEN` "defect N is open on this run; the builder resolves it, then the run continues" when `vw2_defects` has a row for the run with `status = 'open'`. Reads, `vw next`, `vw view` and filing another defect (`post_defect` loads without the lock) still work. |
| Resolution | The builder sets `status = 'fixed'` (the table's existing value) with the resolution note; the defects page already shows the status. CLAUDE.md's defect loop step 6 says so. |
| Plugin | A `DEFECT_OPEN` refusal prints "A defect is open on this run (N); the builder is on it. Nothing more can be recorded until it is fixed." and exits 2. `vw next` adds the open defect to its line when one exists ("… · defect N open"): `GET next` answers `open_defects: [N]`. |
| vw.md, operator-CLAUDE.md | "…file a defect and stop: the server refuses every write on the run until the builder marks it fixed." |

## C. The two tool paths (O.3)

| Piece | What |
|---|---|
| `vw defect --log <path>` | The path must resolve inside the active run folder (`logs/` or `work/`); otherwise refused: "--log must name a file inside the run folder". |
| `vw start --script <path>` | Refused when any part of the resolved path starts with `.` (hidden folders and files, `~/.vw2`, `~/.claude`, `.ssh`, `.env`), or when it lies under `/etc`, `/private/etc`, `/usr`, `/System`, `/Library` or `~/Library` (not `/var`: temporary folders hold no secrets): "--script cannot read from <folder>; copy the file into runs/<code>/in/ by hand". An allowed copy is appended to `runs/<code>/work/guard.log` (the run exists at that point) as `· vw start --script · allowed · <path>`. |

## D. Read-only records (O.4)
The guard refuses `Write`, `Edit`, `MultiEdit` and `NotebookEdit` when the target's name is `guard.log` (anywhere), or the target is `runs/<code>/manifest.json` at the run root, or `runs/.active`: "Blocked: <name> is the tool's own record; the assistant reads it but never writes it." Reads stay allowed. `Bash` is unaffected (it runs only `vw`).

## E. Versions
`SERVER_VERSION` 0.14.0 → 0.15.0; `plugin.json` 0.13.0 → 0.14.0.

## F. Unstated but expected
- A 0.13.0 plugin against the 0.15.0 server: a `DEFECT_OPEN` refusal shows as a generic refusal with the message; nothing else changes.
- The web gate cannot know what the operator meant; it records the subject the assistant named and the operator's words, and the time. The operator can read `work/web-ok.json` and `work/guard.log` (kept at close since design/47).
- A permission file from an earlier run never applies: it lives inside that run's folder.
- A defect filed by `vw decide --decision defect` stops the run the same way.
- Nothing stops the operator from running `vw` by hand; the gates are on the assistant's calls and on the server.

## G. Edge cases
| Case | Expected |
|---|---|
| WebSearch with no `web-ok.json` | blocked with the warning text; a line in guard.log |
| `vw web --about X --ok "yes, search"` then WebSearch, then WebFetch within ten minutes | both allowed, both appended to the file's `calls` and to guard.log as allowed |
| the same file after eleven minutes | blocked; a new `vw web` needed |
| `vw web` without `--ok` | refused |
| `vw stage brief record …` while defect 7 is open | refused `DEFECT_OPEN` naming 7 |
| `vw next` while defect 7 is open | answers, with `open_defects: [7]` in the JSON and "defect 7 open" in the line |
| `vw defect` while defect 7 is open | accepted (a second ticket) |
| defect 7 set to `fixed` | writes work again |
| `vw defect --log ~/.vw2/session.json` | refused |
| `vw defect --log logs/vw.log` | accepted |
| `vw start --client X --script ~/.claude/notes.md` | refused, hidden folder |
| `vw start --client X --script ~/Desktop/script.docx` | copied; a guard.log line |
| Edit on `runs/VW-9/work/guard.log` | blocked |
| Write on `runs/VW-9/manifest.json` | blocked; Write on `runs/VW-9/out/manifest.json` (a different file) allowed |
| Read on any of them | allowed |

## H. Tests (written first)
Layer one, `plugin/tests/test_guard.py` extended: the web gate (blocked without the file, allowed within ten minutes with the calls and the log line, expired after, no active run); the read-only records. `plugin/tests/test_web_cli.py` (new): `vw web` writes the file, refuses without `--ok`. `plugin/tests/test_start_defect_paths.py` (new): `--log` outside the run refused and inside accepted (the server faked); `--script` refusals for hidden and system places and the guard.log line on an allowed copy; the `DEFECT_OPEN` message and the `vw next` line.
Layer two, `server/tests/test_core.py` (Docker): a defect filed → `output` refused with `DEFECT_OPEN` → status set to `fixed` → `output` accepted; `next` carries `open_defects`.

## I. Not covered
- `server/tests` cannot run on this Mac; compile check only until a Docker machine runs them.
- The guard in the operator folder: SK's pending check is the live test of every hook rule here.

## J. Deploy order
1. Server (`deploy-server.sh`, workers restart): tell SK first.
2. Plugin (`deploy-plugin.sh`); the operator restarts Claude Code.
3. CLAUDE.md step 6 and design/35: a row.

## K. Estimate
Guard and plugin with tests: half a day. Server gate with tests: 2 h. Deploys: an hour.
