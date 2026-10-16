# 24 — Handoff prompt: move VideoWizard v2 to a live server

Paste the block below as the first message of a new Claude Code chat opened in `C:\Coworkspace\Review Videobuilder Tool`.

```text
You are the builder for VideoWizard v2. Repo: C:\Coworkspace\Review Videobuilder Tool\videowizard-v2 (GitHub: dsteamautomations/videowizard-claude-v2). Task: move the VideoWizard v2 server and workers from this Windows PC to a live server, so runs no longer depend on this machine being on.

READ FIRST
- videowizard-v2/README.md, design/02-videowizard-v2-build-plan.md, design/23-exact-match-build-report.md (latest state), design/24-live-server-handoff.md (this brief).
- server/app/config.py (setting names only), server/app/worker.py, server/app/storage.py, .claude/launch.json, plugin/scripts/vw.py (server_url, connect flow).
- Read-only, never modify: videowizard-beta/backend/Dockerfile (v1 ran on Google Cloud Run) and videowizard-beta/docs/local-asset-connection-diagnostic.md (IPv6 timeouts from this PC to v1's host).

HOW IT RUNS TODAY (this PC)
- Server: FastAPI, from videowizard-v2/server: python -m uvicorn app.main:app --port 8002. Migrations and procedure bundles apply at startup.
- Workers: python -m app.worker, 5 processes (VW2_WORKERS), analysis concurrency 5 (VW2_ANALYSIS_CAP). Jobs: Gemini 3.8 Flash clip analysis (long calls), ElevenLabs narration, FFmpeg renders (review film about 10 min; master and assembly at full 1080p), uploads to storage.
- Database: Supabase Postgres via the pooler (tables vw2_*). Files: Supabase Storage bucket videowizard-voice. Both are already in the cloud, so moving compute moves no data.
- Secrets: server/.env, git-ignored. Never print, commit or paste a value; put them in the host's secret store.
- FFmpeg and ffprobe are required (FFMPEG_EXECUTABLE, FFPROBE_EXECUTABLE). The render spool (server/.spool, VW2_SPOOL) caches source clips and per-film work folders and can reach several GB.
- Operator side: the vw plugin runs in C:\Coworkspace\VideoWizard-Operator. It finds the server through VW2_SERVER_URL or the session's saved server (default http://localhost:8002); sign-in uses the connect flow and APP_ORIGIN. Installed plugin copy: ~/.claude/plugins/cache/vw-local/vw/0.1.0 (sync with cp -r plugin/. after a compile check).
- The DaVinci Resolve step runs on the Mac once, at delivery. Unchanged by this move.

PROBLEMS THIS MOVE SHOULD SOLVE OR RESPECT
- Renders upload films from this PC over a slow line (a 513 MB film timed out on 15 Oct). From a cloud host these uploads should be fast.
- The operator's internet provider blocked supabase.co for a time on 15 Oct. The operator's own clip uploads still go from the PC to Supabase.
- IPv6 connection timeouts from this PC to v1's host (see the diagnostic doc). Check the new host's address works from this PC.
- The worker has no graceful shutdown on SIGTERM (design/08 asked for it). Check this before choosing a host that restarts containers.

LIVE RUN: DO NOT DISRUPT
VW-2 (client VK Nardep) is in progress at step 7, options; its second review film is ready for SK. Do not stop the local server or workers, and do not point the operator at the new server, without SK's explicit yes. Plan the cut-over at a stage boundary with no job queued, running or storage_pending (table vw2_jobs). Keep the local server runnable as the rollback. Local spool caches need not move; sources re-download from storage.

WORKING RULES (CLAUDE.md)
- Requirements before code: restate the requirement, list unstated requirements, edge cases and failure modes, and wait for SK's approval. Then tests first, then build, then a "not covered" list.
- Minimal: the cheapest control that works, no enterprise guardrails.
- Tell SK before restarting anything. Run only the tests for what changed. Compile-check plugin scripts before syncing. Never modify videowizard-beta.

DECISIONS TO PUT TO SK (one recommendation each, with monthly cost)
1. Host: one always-on Linux VM (server, workers, FFmpeg and disk together) or Google Cloud Run like v1 (needs always-on CPU for workers and long renders, request time limits, temporary disk), or another option. Compare render speed, disk and cost.
2. Domain and HTTPS (APP_ORIGIN for sign-in).
3. Region: near the Supabase project and India.
4. Access: public with the existing login, or limited to known addresses.
5. How the builder deploys updates and restarts with notice.
6. Cut-over plan for VW-2, and rollback.

Start by reading, then reply with the requirement list and your host recommendation for SK's approval. Deploy nothing before that approval.
```
