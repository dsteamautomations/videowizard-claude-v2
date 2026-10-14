# Slice 2+3 — executor plugin + web UI: requirement list for approval

Replaces the earlier slice-2 list. Login is the v1 browser connect flow (ported); the web UI is server-rendered HTML from FastAPI (no Next.js).

Scope: an operator can connect from chat by approving a code in the browser, `/vw start` a run, see `next`, record a dummy output, view, revise, pull the run onto another machine, close it, and see runs and stage outputs in the browser. The hooks stop the model from doing anything outside the plugin. No stage logic, no storage yet.

## 1. What is built

| Part | Content |
|---|---|
| **Connect flow (server)** | `POST /api/connect` (no auth) → `{id, code, url, expires_at}` (10 min); `GET /api/connect/{id}` (no auth) → `pending` / `approved` + executor token once; `POST /api/connect/{id}/approve {code}` (browser session only); token handed out once, then the connection is spent |
| **Web pages (server-rendered, 5)** | `/login` (username, password → browser session cookie), `/connect/{id}` (shows the code, Approve button), `/runs` (mine; admin: all), `/runs/{code}` (stages, latest output per stage, stale history, download links from slice 4+5), `/defects` (admin). Plain HTML + one CSS file, no JS framework |
| `plugin/.claude-plugin/plugin.json` | name `vw`, version `0.1.0` |
| `plugin/commands/vw.md` | the `/vw` command: run `vw next` first, show one sentence, ask the operator only when `next` says so, pass replies verbatim as `accepted_quote`, inform (not ask) on paid steps, never debug, file a defect and stop on errors, show the connect link when the session is missing |
| `plugin/scripts/vw.py` | CLI: `connect`, `whoami`, `start`, `next`, `output`, `view`, `revise`, `decide`, `defect`, `pull`, `close`; JSON on stdout, one-line summary on stderr |
| `plugin/hooks/hooks.json` + `guard.py` | PreToolUse: Bash allowed only for `python …/scripts/vw.py …`; Edit/Write/MultiEdit only under the active run folder; everything else blocked with a one-line reason |
| `plugin/operator-CLAUDE.md` | five lines for the operator profile |
| Workspace | `runs/<code>/{in,out,work,logs}` + `manifest.json` (path, stage, action retain/upload/delete, sha256, receipt); `runs/.active` holds the current code |
| Server additions | `GET /api/meta` → `{plugin_min_version, server_version}`; `POST /api/runs/{id}/claim {machine}`; `next` returns `active_machine` |

Executor token stored in `%LOCALAPPDATA%\vw2\session.json` (Mac: `~/.vw2/`), machine id beside it. Browser session is an httpOnly cookie (v1 settings).

## 2. Unstated requirements treated as in scope

1. `start` preflight: server reachable, session valid, plugin version ≥ minimum, free disk ≥ what the operator states; then the plan §2 questions; then create + claim.
2. `output` is generic (stage, unit, files hashed from `out/`, summary, accepted quote); later stage scripts call it.
3. `close`: refuses if any `upload` file lacks a receipt; deletes `work/` and `logs/`; keeps `out/` only for `retain` files; marks the manifest closed.
4. `pull <code>`: creates the workspace from the ledger (no downloads yet) and claims the run.
5. Another machine holds the run → "active on <machine> since <time>; take over? y/n"; proceed only on yes.
6. Web pages never write run state (no buttons except Approve on `/connect` and logout). Admin sees all runs and the defect list.
7. Connect code is 6 characters, shown on both sides, so the operator can see they are approving their own connection.

## 3. Edge cases (tests)

| # | Case | Expected |
|---|---|---|
| C1 | `connect` then approve with the right code from a browser session | plugin receives a token; `whoami` works |
| C2 | approve with the wrong code | 400; connection still pending |
| C3 | approve from an executor session | 403 BROWSER_REQUIRED |
| C4 | approve after 10 minutes | 410 EXPIRED; plugin says "start connect again" |
| C5 | poll after the token was handed out | 410 SPENT (token is never shown twice) |
| C6 | `/login` wrong password | page re-shown with the message; no cookie |
| C7 | `/runs/{code}` as another operator | 404 |
| C8 | `/runs` as admin | all runs listed |
| P1 | no session file | prints the connect link and exits 2 |
| P2 | expired executor session (401) | same |
| P3 | server unreachable | "server not reachable at <url>; tell the builder", exit 2, no defect |
| P4 | plugin version below minimum | exit 2 with the install command |
| P5 | `start` when `runs/<code>` exists | refuses; suggests `pull` or a new title |
| P6 | `output` hashes files from `out/`; refuses a path outside `out/` | sha256 matches; exit 2 |
| P7 | `close` with an `upload` file lacking a receipt | exit 2 listing files; nothing deleted |
| P8 | `close` success | `work/`, `logs/` gone; `out/` keeps retain files only |
| P9 | `pull` on a fresh machine | folders + manifest from ledger; run claimed |
| P10 | run active on another machine | prompt; `n` aborts, `y` claims |
| P11 | guard: `gcloud`, `psql`, `git`, `python other.py` via Bash | blocked, exit 2 with reason |
| P12 | guard: `python <plugin>/scripts/vw.py next` | allowed |
| P13 | guard: Write under `runs/VW-3/out/` allowed; Write elsewhere or into the plugin folder blocked | as stated |
| P14 | guard: no `runs/.active` and a Write | blocked |
| P15 | `output` gets NEEDS_USER_DECISION | exit 3 with options printed, so the model asks |

## 4. Not in this slice

Stage scripts, storage uploads/downloads, download links (they appear with slice 4+5), connections list/revoke page (dropped), lease timers, Agent SDK app, dark mode.

## 5. From you

Nothing to install. Approve or amend; then tests, then code.
