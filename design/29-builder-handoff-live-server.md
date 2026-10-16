# 29 — Builder handoff: VideoWizard v2 live server

16 Oct 2026. Paste the block below as the first message of a new builder chat opened in `C:\Coworkspace\Review Videobuilder Tool`.

```text
You are the builder for VideoWizard v2. Repo: C:\Coworkspace\Review Videobuilder Tool\videowizard-v2 (GitHub: dsteamautomations/videowizard-claude-v2, branch main). Task: finish the move of the server and workers from SK's Windows PC to a Google VM, switch the operator over, then run updates on the VM.

READ FIRST
- design/25-live-server-requirements.md (why a VM, edge cases, failure modes)
- design/26-deployment-instructions.md (what the deployment team runs; services, settings, cut-over, rollback)
- design/30-operator-handoff-live-server.md (what the operator is told)
- server/app/worker.py (graceful stop on SIGTERM, commit 88bd430)

STATE ON 16 OCT 2026, EVENING
- CUT OVER 16 Oct 2026 14:39 UTC. Open jobs were 0; the PC server and workers were stopped (code, .env and .spool kept as rollback); vw2-worker enabled on the VM ("started 5 workers"); operator settings C:\Coworkspace\VideoWizard-Operator\.claude\settings.json now set VW2_SERVER_URL=https://8-234-82-225.sslip.io. The operator's existing sign-in token works on the VM (shared database), so no reconnect was needed; `vw next` for VW-2 answered through the VM (stage: delivery). The operator must restart Claude Code once to pick up the setting. GCE VM `vw2`, project sm-project-435806, zone asia-south1-a, e2-standard-4, 100 GB, Ubuntu 24.04, static IP 8.234.82.225 (address `vw2-ip`), firewall rule `vw2-allow-web` (80/443, tag vw2-web). SSH: gcloud compute ssh vw2 --zone asia-south1-a --project sm-project-435806.
- Public URL will be https://8-234-82-225.sslip.io (free IP hostname, A record only; SK asked for a default Google domain; *.run.app exists only for Cloud Run and has AAAA records). VW2_APP_ORIGIN on the VM is already set to it.
- Running on the VM: vw2-server (127.0.0.1:8002, commit e918715, migrations applied, /api/meta OK), FFmpeg/ffprobe n9.0.2 in /usr/local/bin, spool /var/lib/vw2/spool, render-cache cleanup cron. vw2-worker installed but DISABLED.
- HTTPS: Caddy with a Let's Encrypt certificate for 8-234-82-225.sslip.io (obtained 16 Oct 14:32 UTC, renews itself). From SK's PC: curl -4 https://8-234-82-225.sslip.io/api/meta -> 200 in 0.45 s; plugin's httpx client -> 200 in 1.6 s; no IPv6 offered.
- Code reaches the VM as a git bundle (repo is private; the VM holds no GitHub credential): on the PC `git bundle create vw2.bundle origin/main main`, gcloud compute scp it to /tmp, then on the VM `sudo -u vw2 git -C /opt/vw2/app pull /tmp/vw2.bundle main`.
- Everything still runs on SK's PC at http://localhost:8002 until cut-over.
- Pushed: graceful stop (88bd430), tickets 12 and 13 fixes plus these handoffs (e918715). Only server/tests/_diag_hang.py (scratch diagnostic) is uncommitted.
- VW-2 (VK Nardep): assembly film rendered (job bc95f76a, ready 11:59 UTC). No open jobs. Tickets 11, 12, 13 have no resolution note; 14 resolved (storage limit raised to 800 MB).

WHEN THE DEPLOYMENT TEAM HANDS BACK
1. Check their step 9 output; from this PC also run:
   - curl -4 https://<domain>/api/meta  (server_version, app_origin = https://<domain>)
   - Resolve-DnsName <domain>  (A record only, no AAAA)
   - python -c "import httpx; print(httpx.get('https://<domain>/api/meta', timeout=10).json())"  (the plugin's own client)
2. Confirm you can reach the VM: gcloud compute ssh <vm> --zone <zone> --tunnel-through-iap.
3. Confirm vw2-worker is disabled on the VM (systemctl is-enabled vw2-worker -> disabled).

CUT-OVER (only with SK's explicit yes, at a stage boundary)
1. Open-job check (Supabase project VideoBuilder, myaibwryhhkunghfxqye):
   select status, count(*) from vw2_jobs where status in ('queued','running','submission_unknown','storage_pending') group by status;  -- must be empty
2. Tell SK, then stop the PC workers and the PC server (leave code, .env and .spool untouched: they are the rollback).
3. On the VM: sudo systemctl enable --now vw2-worker; journalctl -u vw2-worker -n 20 shows "started 5 workers".
4. Operator switch (design/30): add "env": {"VW2_SERVER_URL": "https://<domain>"} to C:\Coworkspace\VideoWizard-Operator\.claude\settings.json, then the operator runs /vw:vw connect once and approves the link. The saved session (%LOCALAPPDATA%\vw2\session.json) still names localhost; the env var takes precedence.
5. Operator asks /vw:vw what is next for the open run (vw next); you confirm the request reached the VM (journalctl -u vw2-server).

ROLLBACK
Drain VM workers (sudo systemctl stop vw2-worker; waits up to 40 min for running jobs), confirm the open-job query has no storage_pending, remove VW2_SERVER_URL from the operator settings, start the PC server and workers. Same database and storage; nothing moves.

UPDATES ON THE VM (after cut-over)
- Tell SK what changes and that workers restart. Run tests only for what changed, commit, push.
- Bundle and copy main (see STATE), then on the VM: sudo -u vw2 git -C /opt/vw2/app pull /tmp/vw2.bundle main && sudo -u vw2 /opt/vw2/venv/bin/pip install -r /opt/vw2/app/server/requirements.txt && sudo systemctl restart vw2-server vw2-worker
- The worker restart drains: running jobs finish first (up to 40 min). Then curl https://<domain>/api/meta.
- Plugin updates: compile-check, sync to ~/.claude/plugins/cache/vw-local/vw/0.1.0 as before. No change for the VM.
- Logs: journalctl -u vw2-server / -u vw2-worker. Spool: /var/lib/vw2/spool (paid-call journals; only spool/render is auto-cleaned after 7 days).
- A job stuck 'running' after a force-kill or crash: clear it by hand (analysis: POST /api/jobs/{id}/release).

WORKING RULES (CLAUDE.md)
Requirements before code; wait for SK's approval; tests first; "not covered" list. Minimal, no enterprise guardrails. Tell SK before restarting anything. Never print or commit secrets. Never modify videowizard-beta.

Start by reading, then tell SK where the deployment stands and what you need from him.
```
