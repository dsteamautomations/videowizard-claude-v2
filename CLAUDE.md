# VideoWizard v2 — builder workspace

This folder (`/Users/vasudha/Codex/videowizard-claude-v2`, GitHub `dsteamautomations/videowizard-claude-v2`, branch `main`) is where VideoWizard v2 is fixed, tested and deployed. SK is the lead developer and the only approver.

## Roles and places

- **Builder (this folder).** Fixes defects, runs tests, commits, pushes, deploys. The working copy here is never what the operator runs.
- **Operator.** Works in `/Users/vasudha/Documents/videobuilder - Operator ` with `/vw:vw`. The operator always runs the **live server** `https://8-234-82-225.sslip.io` (set by `VW2_SERVER_URL` in that folder's `.claude/settings.json`) and the **pushed plugin** (`vw@vw-local`, installed at user scope from the GitHub marketplace `dsteamautomations/videowizard-claude-v2`, which reads `plugin/` on `main`; enabled only in the operator folder by its `.claude/settings.json` and disabled at user scope, so its guard hook never runs in any other folder). Never point the operator at this working copy. Operator-side guidance: `plugin/operator-CLAUDE.md`, `design/30-operator-handoff-live-server.md`.
- **Live server.** GCE VM `vw2`, project `sm-project-435806`, zone `asia-south1-a`; code in `/opt/vw2/app` (user `vw2`), venv `/opt/vw2/venv`, services `vw2-server` and `vw2-worker`, spool `/var/lib/vw2/spool`. SSH: `gcloud compute ssh vw2 --zone asia-south1-a --project sm-project-435806 --tunnel-through-iap`. Logs: `journalctl -u vw2-server` / `-u vw2-worker`. History: `design/25`, `design/26`, `design/29`. Builder handoff (state, reading list, deploy steps from a new laptop): `design/72`.

## Working rules

- Requirements before code. Write down what will change and why; wait for SK's approval before coding.
- Tests first. Then the change. Keep a "not covered" list with every piece of work and say what it leaves unverified.
- Minimal. No enterprise guardrails, no frameworks, no extra abstractions.
- Tell SK before restarting anything (server, workers, the operator's Claude Code). A worker restart drains running jobs first, up to 40 minutes.
- Never print, paste or commit secrets. `server/.env` stays out of git and out of chat; move it only as a file.
- Never modify `videowizard-beta` (the v1 system).
- Run only the tests for what changed.
- One flow, two front ends (SK, 20 Oct 2026, after defect 16). The operator's chat path (the `vw` tool) and the web pages are two front ends on the same server steps. Anything a page does for the operator (saving a library voice before an audition, applying the recorded direction, recording with the operator's words) lives in the server function both paths call, never as an instruction the assistant must remember on the chat side. When a page gains a step, the same server function serves `vw`; when `vw` gains a step, the page calls it too. A procedure step may describe the behaviour; it must never be the only place it exists.

## The defect loop

1. **Defect arrives.** The operator files it with `vw defect`. Read it on the live server's defects page (`https://8-234-82-225.sslip.io/defects`, sign in as SK) or in the `vw2_defects` table of Supabase project **VideoBuilder** (`myaibwryhhkunghfxqye`).
2. **Fix here.** Requirements note, SK's approval, test, change.
3. **Test** only what changed (see "Testing on this Mac").
4. **Commit and push** `main`.
5. **Deploy** with the script that matches the change (both if both sides changed):
   - `./scripts/deploy-server.sh` — anything under `server/`. Tell SK first: the workers restart.
   - `./scripts/deploy-plugin.sh` — anything under `plugin/`. The operator must restart Claude Code in the operator folder afterwards.
6. **Resolution note.** One line on the defect: what was wrong, what changed, which commit; and set its `status` to `fixed` in `vw2_defects` (the run refuses every write while a defect is `open`, design/48).
7. **Tell SK** the operator can resume with `/vw:vw what is next for <run code>`.

## Deploy scripts

Both refuse to run if the working tree is dirty or local `main` is not exactly `origin/main`.

- `scripts/deploy-server.sh` (design/29 "UPDATES ON THE VM"): `git bundle` of `main` → `gcloud compute scp` to `/tmp` on the VM → on the VM `git pull` from the bundle, `pip install -r server/requirements.txt`, `systemctl restart vw2-server vw2-worker` → polls `/api/meta` and prints `server_version`. The VM holds no GitHub credential, which is why the code travels as a bundle. `server_version` is the constant in `server/app/config.py`; bump it when a release should be visible there.
- `scripts/deploy-plugin.sh`: `python -m py_compile` on every `plugin/**/*.py`, then with the bundled binary: `claude plugin marketplace update vw-local`, `plugin uninstall` + `plugin install vw@vw-local --scope user`, `plugin disable --scope user` again, and a check that the installed commit equals `main`. A plain `plugin update` is a no-op unless the version in `plugin.json` changes, which is why the script reinstalls. Nothing changes on the VM.

A job stuck `running` after a crash or a forced kill: release it by hand (analysis: `POST /api/jobs/{id}/release`).

## Testing on this Mac

- `python` is a wrapper at `~/.local/bin/python` that runs `/usr/bin/python3` (3.9.6). The plugin's hooks and scripts run with it, so keep `plugin/` 3.9-compatible.
- Server tests (`server/tests`) start a throwaway `postgres:17` in Docker; **Docker Desktop is not installed here**, so they cannot run on this Mac yet. `pytest` is not installed either. Until that changes, list `server/tests` under "not covered" and compile-check instead (`python -m py_compile`). The full suite can be run on the VM (`/opt/vw2/venv`, needs Docker there too) or on a machine with Docker.
- Compile-check the plugin before every push: `for f in $(find plugin -name '*.py'); do python -m py_compile "$f"; done`.

## Tools on this Mac

- Claude Code CLI (no `claude` on PATH): `/Users/vasudha/Library/Application Support/Claude/claude-code/2.1.304/6bbba6adc37f/claude.app/Contents/MacOS/claude`. The version segment changes when the desktop app updates; fix the path in `scripts/deploy-plugin.sh` when it does.
- `gcloud` lives in `~/google-cloud-sdk` (PATH and `CLOUDSDK_PYTHON` are set in `~/.zprofile`; the SDK needs Python 3.10+ and uses the standalone CPython in `~/google-cloud-sdk/platform/python3`). Account and project are SK's (`gcloud auth login`, project `sm-project-435806`).
- No `gh`, `brew`, `node` or `docker` on PATH. Git talks to GitHub over HTTPS with the token in the macOS Keychain.
