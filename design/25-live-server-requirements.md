# 25 — Live server: requirements and host recommendation (for SK's approval)

16 Oct 2026. Nothing is deployed, nothing on this PC has been stopped or changed. Brief: [24-live-server-handoff.md](24-live-server-handoff.md).

## The requirement, restated

Run the VideoWizard v2 server and its 5 workers on an always-on cloud host, against the **same** Supabase database and storage bucket, so a run carries on when this PC is off. The operator's `vw` plugin talks to the new server over HTTPS. This PC stays runnable as the rollback. VW-2 is not disturbed: the switch happens only on SK's yes, at a stage boundary with no open job.

## What I found while reading (these shape the plan)

| # | Finding | Why it matters |
|---|---|---|
| F1 | The spool is not a cache only. Voice, analysis and image jobs write their **paid provider responses** to `VW2_SPOOL` before storing (`worker.py`, `analysis_jobs.py`, `visual_workers.py`). A `storage_pending` job is retried from those local files; if they are gone it becomes `PROVIDER_UNKNOWN` ("do not regenerate"). | The spool must sit on a **persistent disk** that survives restarts. Cloud Run's disk is in memory and lost when an instance is replaced. Also: two worker sets (PC + cloud) must never run at once, because a job journaled on one machine cannot finish on the other. |
| F2 | The worker has **no SIGTERM handling**. On a stop, Python dies mid-job; the parent's `finally` that stops the 4 children does not run. | A killed render stays `running` forever: `jobs.claim` never reclaims an expired `running` render or voice job (only analysis does, with its heartbeat). Every restart must drain first. |
| F3 | `Pillow` and `jsonschema` are imported by the server but **missing from `requirements.txt`**. | A clean install on a new host would fail at render / validation. Present on this PC only by accident. |
| F4 | This PC renders with **FFmpeg 9.0**. Ubuntu's packaged FFmpeg is 6.1. | Different filters/encoder defaults can change films. The host should use a pinned static FFmpeg build of the same major version. |
| F5 | Supabase pooler host is `aws-0-ap-south-1` = **Mumbai**. | Host goes in Mumbai: workers make many small DB calls. |
| F6 | v1's slow uploads were this PC's broken **IPv6** (8 AAAA addresses tried first, each timing out). `*.run.app` publishes AAAA records. | Give the new host an **IPv4-only** DNS name (A record, no AAAA). Test from this PC with the plugin's own HTTP client. |
| F7 | Operator clip uploads go straight from the PC to Supabase via signed URLs, not through the server. | The move fixes slow **film** uploads (server → Supabase in the same city) but not an ISP block of `supabase.co` on the operator's line. |
| F8 | `gcloud` is installed here (account deepa@digitalseo.in, project `sm-project-435806`) but its login has expired. | Someone must run `gcloud auth login` once interactively before I can create anything. |

## Unstated but expected requirements

1. Same git commit on PC and host at cut-over. Migrations run at server start; the same commit makes them a no-op on the second machine, so the PC stays a working rollback.
2. Spool on the VM's persistent disk (F1). Never run PC and cloud workers at the same time.
3. Server and workers start on boot and restart after a crash (systemd). Note: the worker deliberately exits after 5 consecutive connection failures; systemd will restart it after 60 s instead of it staying down.
4. Worker drains on SIGTERM: finish the current job, then exit; parent passes the signal to its children (F2). systemd waits up to 30 minutes for a drain before killing.
5. HTTPS with an automatic certificate (Caddy). `VW2_APP_ORIGIN` = the new https origin, so connect links open the right page.
6. uvicorn bound to 127.0.0.1 behind Caddy, `--proxy-headers`. Only 80/443 open to the internet.
7. Add `Pillow` and `jsonschema` to `requirements.txt`, pinned to this PC's versions (F3).
8. Static FFmpeg/ffprobe 9.x on the host; `VW2_FFMPEG_EXECUTABLE` / `VW2_FFPROBE_EXECUTABLE` point at it (F4).
9. Secrets: `server/.env` copied to the host by file transfer (never printed, pasted or committed), root-owned, mode 600, loaded by systemd. PC-only values replaced on the host: FFmpeg paths, `VW2_SPOOL`, `VW2_APP_ORIGIN`; `VW2_STORAGE_LOCAL_DIR` stays empty.
10. Spool growth: the render cache (`.spool/render`) is cleaned daily of files older than 7 days. Voice/analysis/image journals are never auto-deleted.
11. Logs readable by the builder over SSH (`journalctl`).
12. Host clock in UTC with NTP (default). The code already uses DB `now()` and UTC.
13. Operator side: `VW2_SERVER_URL` set to the new origin in the operator profile's settings, then one connect. No plugin code change is needed (`vw.py server_url()` already prefers the env var).

## Edge cases and failure modes

| Case | Handling |
|---|---|
| Job `queued`, `running`, `submission_unknown` or `storage_pending` at cut-over | No cut-over. One SQL count on `vw2_jobs` must be 0 first; I show SK the result. |
| Both machines' workers running | Cut-over order: stop PC workers → confirm 0 running → start host workers. The host's workers stay disabled until that point. |
| Smoke-testing the host before cut-over | Host server only (no workers). Read-only checks plus a connect. Nothing that queues a job, or the PC's workers would pick it up. |
| This PC's IPv6 to the new host | A record only. Test from this PC: `curl -4`, `curl -6` (must fail fast or not resolve), and a `httpx` GET with the plugin's own client. |
| Operator's ISP blocks the new domain or IP | Same test from the operator's line before cut-over. If blocked, stay on the PC. |
| ISP blocks `supabase.co` again | Not solved by this move (F7). Listed under "not covered". |
| Restart during a render or paid call | SIGTERM drain (req. 4). Deploys only after I tell SK and the job count is 0 or draining. |
| Hard crash or VM kill mid-render | Render row stuck `running` (F2). Manual release by the builder; not automated (see "not covered"). Paid voice/analysis calls recover from their spool journals on the persistent disk. |
| Disk full | 100 GB disk + render-cache cleanup (req. 10). A render that hits a full disk fails as it does today. |
| 5 parallel 1080p renders | 4 vCPU / 16 GB: renders queue on CPU, slower but no memory failure. Resize is one stop/start if needed. |
| GCP maintenance | E2 VMs live-migrate without a reboot; a rare reboot is handled by systemd + drain. |
| Certificate renewal | Caddy renews automatically. |
| Clean install misses a package | Run the full server test suite once on the host (Docker + postgres:17, as on this PC) before cut-over. |
| Different FFmpeg output | Render one known review film on the host after cut-over is approved; compare duration and a frame against the PC's copy. |
| Rollback | Drain host workers → set operator `VW2_SERVER_URL` back to `http://localhost:8002` → start PC server and workers. Same database and storage, so nothing moves back. Condition: 0 `storage_pending` on the host. |

## Decisions for SK (one recommendation each)

Prices are list prices as I know them, before tax; I will confirm on the order page before creating anything.

### 1. Host — recommend one Google Compute Engine VM

| Option | Monthly (approx.) | Renders | Disk / spool | Restarts | Verdict |
|---|---|---|---|---|---|
| **GCE e2-standard-4 (4 vCPU, 16 GB), Mumbai, 100 GB balanced disk, Ubuntu 24.04** | **~US$130 (~₹11,000)** | Full vCPUs, no time limit | Persistent | Only when we restart | **Recommended** |
| GCE e2-standard-2 (2 vCPU, 8 GB) | ~US$70 | About half the speed with 2+ renders | Persistent | Same | Cheaper start; resize later is one stop/start |
| Cloud Run, CPU always on, 1 instance 4 vCPU 16 GiB | ~US$200–270 | OK | **In-memory, lost on instance replace** (breaks F1) | Platform restarts at will, 10 s SIGTERM grace | No |
| AWS Lightsail Mumbai 4 vCPU 16 GB | ~US$84 | Burstable CPU: long renders throttle | Persistent | Same as VM | New account and billing |
| DigitalOcean Bangalore 4 vCPU 8 GB | ~US$48 | Shared CPU | Persistent | Same as VM | New account; not same city as Supabase |

Why the GCE VM: same Google account and billing as v1, `gcloud` already on this PC, same city as Supabase, persistent disk for the paid-call journals, no request or CPU time limits on 10-minute renders, and we choose when it restarts.

### 2. Domain and HTTPS — recommend a subdomain, e.g. `vw2.digitalseo.in`
A record only (no AAAA) to the VM's static IP; Caddy issues the certificate. `VW2_APP_ORIGIN=https://vw2.<domain>`. Cost: static IP ~US$3/month while attached, certificate free. **Need from SK:** which domain, and who can add the A record.

### 3. Region — recommend `asia-south1` (Mumbai)
Same city as the Supabase project (ap-south-1) and close to the operator.

### 4. Access — recommend public HTTPS with the existing login
The operator's IP changes and the Mac needs it at delivery, so an address allow-list would break things. Only 443/80 open; SSH closed to the internet and reached through `gcloud compute ssh --tunnel-through-iap`. Cost: none.

### 5. Updates — recommend a 10-line `deploy.sh` on the VM, run by the builder over gcloud SSH
1. I tell SK what is changing and that workers will restart.
2. Script prints open jobs from `vw2_jobs`; stops if any are `running` unless SK said go.
3. `git pull` (read-only GitHub deploy key), `pip install -r requirements.txt`, `systemctl restart` (workers drain first).
4. Prints the server version from the health route.

Plugin updates stay as today (compile check, then sync the installed copy).

### 6. Cut-over for VW-2, and rollback
1. Build and smoke-test the host with **workers off** while VW-2 continues on the PC.
2. When VW-2 sits at a stage boundary (e.g. SK reviewing a film) and the open-job count is 0, I ask SK for a yes.
3. Stop PC workers, then the PC server. Start host workers.
4. Set operator `VW2_SERVER_URL` to the new origin; reconnect once; operator checks run status.
5. Rollback as in the table above. The PC keeps its `.env`, code and spool untouched.

## What I will build after approval (tests first)

- Test: worker loop exits after the current tick when SIGTERM arrives, and the parent forwards it to children. Then the ~10-line change in `worker.py`.
- `requirements.txt`: add Pillow and jsonschema.
- On the host only: systemd units (server, workers), Caddyfile, `deploy.sh`, cleanup cron. These live in a small `deploy/` folder in the repo.
- Host acceptance: full pytest on the host; IPv4/IPv6 + httpx checks from this PC; connect flow; one test render after SK's yes.

## Not covered (proposed)

- ISP blocking `supabase.co` for the operator's own uploads (would need uploads proxied through the server; separate change).
- Automatic recovery of a render or voice job stuck `running` after a hard crash; the builder releases it by hand.
- Monitoring/alerting beyond systemd restarts. Optional one-liner if SK wants it: a GCP budget alert at US$150.
- Moving the PC's spool cache; sources re-download from storage.
