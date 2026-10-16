# 26 — Deployment instructions: VideoWizard v2 on a Linux VM

For the deployment team. 16 Oct 2026. Background and reasoning: [25-live-server-requirements.md](25-live-server-requirements.md).

> **Two hard rules**
> 1. **Do not start the worker service** (`vw2-worker`) until SK or the builder says "cut over". A live client run (VW-2) is being processed by workers on SK's PC against the same database. Two sets of workers at once can lose paid work.
> 2. **Never print, paste, commit or chat secret values.** Move the settings file as a file (step 5).

## 1. What you are deploying

| Item | Value |
|---|---|
| Git repo | `https://github.com/dsteamautomations/videowizard-claude-v2` — **private**, branch `main`. Ask SK for read access (or add a read-only deploy key to the repo). |
| App folder | `server/` inside the repo |
| Runtime | Python **3.12** (Ubuntu 24.04 ships it) |
| Web server | FastAPI via uvicorn, one process, port 8002 on 127.0.0.1, behind HTTPS (Caddy) |
| Workers | **One** service running `python -m app.worker`. It starts **5 worker processes** itself (`VW2_WORKERS`, default 5). Gemini analysis is capped at 5 at a time (`VW2_ANALYSIS_CAP`, default 5). Do not run more than one worker service. |
| Jobs the workers run | Gemini clip analysis (long API calls), ElevenLabs narration, FFmpeg renders (about 10 min each, 1080p), uploads to Supabase Storage |
| Database | Supabase Postgres (already live, Mumbai). Migrations run automatically when the server starts. Nothing to create. |
| File storage | Supabase Storage bucket (already live). Nothing to create. |
| Data on the VM | Only the spool folder (step 4). It holds saved provider responses for paid calls: **must be on persistent disk, never deleted wholesale.** |

## 2. Machine

| Setting | Value |
|---|---|
| Provider | Google Compute Engine, project: **confirm with SK** (SK's PC uses `sm-project-435806`) |
| Region / zone | `asia-south1` (Mumbai), any zone |
| Machine type | `e2-standard-4` (4 vCPU, 16 GB) |
| Disk | 100 GB balanced persistent disk |
| OS | Ubuntu 24.04 LTS |
| IP | Reserve a **static external IPv4** address |
| Firewall | Open 80 and 443 to all. Port 22 only from Google IAP (`35.235.240.0/20`); connect with `gcloud compute ssh --tunnel-through-iap`. |
| Time zone | Leave UTC |

## 3. DNS

One **A record** (IPv4) for the chosen subdomain, e.g. `vw2.digitalseo.in` → the static IP. **Do not add an AAAA (IPv6) record**: SK's PC cannot reach IPv6 hosts reliably and the operator tools would stall. Domain to use: **confirm with SK**.

## 4. Install

```bash
sudo apt update && sudo apt install -y python3.12-venv git caddy xz-utils

# FFmpeg 9.0 static build (SK's PC renders with 9.0; Ubuntu's packaged 6.1 must NOT be used)
# Use a static Linux x86_64 GPL build of FFmpeg 9.0 (e.g. BtbN/FFmpeg-Builds), copy ffmpeg and ffprobe to /usr/local/bin.
ffmpeg -version | head -1      # must say version 9.0...
ffprobe -version | head -1

sudo useradd --system --create-home --home-dir /opt/vw2 vw2
sudo mkdir -p /var/lib/vw2/spool && sudo chown -R vw2:vw2 /var/lib/vw2

sudo -u vw2 git clone https://github.com/dsteamautomations/videowizard-claude-v2.git /opt/vw2/app
cd /opt/vw2/app/server
sudo -u vw2 python3.12 -m venv /opt/vw2/venv
sudo -u vw2 /opt/vw2/venv/bin/pip install -r requirements.txt
```

## 5. Settings file (secrets)

The app reads `/opt/vw2/app/server/.env` (this file is git-ignored). SK copies his current `server/.env` to you **as a file** through a private channel; you place it there and lock it:

```bash
sudo chown vw2:vw2 /opt/vw2/app/server/.env && sudo chmod 600 /opt/vw2/app/server/.env
```

**Note for SK before sending:** one line in the PC's `.env` looks like the tail of a long key that wrapped onto its own line. Check every key is on a single line before handing the file over.

Settings (all prefixed `VW2_`). Values come from SK's file; only the four marked rows are different on the VM.

| Setting | Required | On the VM |
|---|---|---|
| `VW2_DATABASE_URL` | yes | same as PC (Supabase session pooler, Mumbai) |
| `VW2_SHARED_SUPABASE_URL` | yes | same as PC (employee login) |
| `VW2_SHARED_SUPABASE_SERVICE_KEY` | yes | same as PC |
| `VW2_APP_ID` | yes | same as PC |
| `VW2_SESSION_HOURS` | yes | same as PC |
| `VW2_DEFAULT_PROCEDURE_VERSION` | yes | same as PC |
| `VW2_STORAGE_SUPABASE_SERVICE_KEY` | yes | same as PC |
| `VW2_STORAGE_BUCKET` | yes | same as PC |
| `VW2_ELEVENLABS_API_KEY` | yes | same as PC |
| `VW2_GEMINI_API_KEY` | yes | same as PC |
| `VW2_OPENAI_API_KEY` | yes | same as PC |
| `VW2_HF_API_KEY` | no | empty on PC; leave empty |
| **`VW2_APP_ORIGIN`** | yes | **change** to `https://<your subdomain>` (no trailing slash) |
| **`VW2_SPOOL`** | yes | **add** `/var/lib/vw2/spool` |
| **`VW2_STORAGE_LOCAL_DIR`** | — | **must be absent or empty** (otherwise files go to local disk instead of Supabase) |
| **`VW2_FFMPEG_EXECUTABLE`, `VW2_FFPROBE_EXECUTABLE`** | no | not set on PC; leave unset if ffmpeg/ffprobe are in `/usr/local/bin` |
| `VW2_WORKERS`, `VW2_ANALYSIS_CAP` | no | leave unset (default 5 and 5) |

## 6. Services (systemd)

`/etc/systemd/system/vw2-server.service`

```ini
[Unit]
Description=VideoWizard v2 server
After=network-online.target
Wants=network-online.target

[Service]
User=vw2
WorkingDirectory=/opt/vw2/app/server
ExecStart=/opt/vw2/venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8002 --proxy-headers
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

`/etc/systemd/system/vw2-worker.service`

```ini
[Unit]
Description=VideoWizard v2 workers (5 processes)
After=network-online.target vw2-server.service
Wants=network-online.target

[Service]
User=vw2
WorkingDirectory=/opt/vw2/app/server
Environment=VW2_SPOOL=/var/lib/vw2/spool
ExecStart=/opt/vw2/venv/bin/python -m app.worker
Restart=on-failure
RestartSec=60
# Graceful stop: SIGTERM goes to the main worker only; it passes it to its 4 child workers. Each finishes its current
# job (an analysis can take up to 30 min), claims nothing new, then exits. FFmpeg renders are not interrupted.
KillMode=mixed
TimeoutStopSec=40min

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now vw2-server
sudo systemctl disable vw2-worker     # stays OFF until cut-over
```

## 7. HTTPS (Caddy)

`/etc/caddy/Caddyfile`

```
vw2.example.com {
    request_body max_size 600MB
    reverse_proxy 127.0.0.1:8002 {
        transport http {
            read_timeout 15m
            write_timeout 15m
        }
    }
}
```

Replace the hostname, then `sudo systemctl reload caddy`. Caddy gets and renews the certificate itself.

## 8. Spool cleanup (daily)

Only the render cache is cleaned. **Never delete anything else in the spool**: those files are saved responses from paid API calls.

```bash
echo '30 3 * * * vw2 find /var/lib/vw2/spool/render -type f -mtime +7 -delete' | sudo tee /etc/cron.d/vw2-spool
```

## 9. Checks before handing back (workers still OFF)

On the VM:

```bash
systemctl status vw2-server --no-pager          # active (running)
journalctl -u vw2-server -n 50 --no-pager       # no errors; migrations applied
curl -s https://<subdomain>/api/meta            # JSON with server_version and app_origin = https://<subdomain>
dig +short AAAA <subdomain>                     # must print nothing
sudo -u vw2 /opt/vw2/venv/bin/python -c "import PIL, jsonschema; print('ok')"
df -h /var/lib/vw2                              # ~100 GB
```

Do **not** sign in through the operator tools, start a run, or start `vw2-worker`. Any job created now would be picked up by the workers on SK's PC.

## 10. Hand back to SK / the builder

Send (no secrets):
- the HTTPS URL and the static IP,
- the output of the step 9 checks,
- SSH access for the builder (IAM role on the project for `deepa@digitalseo.in` with IAP tunnel access, or an SSH key you add),
- the VM name, zone and project.

## 11. Cut-over (done together, on SK's signal)

The builder checks that no job is open:

```sql
select status, count(*) from vw2_jobs
where status in ('queued','running','submission_unknown','storage_pending') group by status;   -- must return no rows
```

Then, in this order:
1. Builder stops the workers and server on SK's PC.
2. On the VM: `sudo systemctl enable --now vw2-worker`, then `journalctl -u vw2-worker -n 20` shows `started 5 workers`.
3. Builder points the operator tools at `https://<subdomain>` and reconnects once.

**Rollback:** stop `vw2-worker` on the VM only when the query above returns no rows, then the builder restarts the PC server and workers and points the operator back. Database and files are shared, so nothing is copied back.

## 12. Updates later

Run only after the builder has told SK. A restart waits for running jobs to finish (up to 40 minutes), so it can take a while; that is normal:

```bash
cd /opt/vw2/app && sudo -u vw2 git pull
sudo -u vw2 /opt/vw2/venv/bin/pip install -r server/requirements.txt
sudo systemctl restart vw2-server vw2-worker
curl -s https://<subdomain>/api/meta
```

## Known limits

- If a job takes longer than 40 minutes after a stop, systemd force-kills it and that job stays `running`; the builder clears it by hand. A hard crash or VM kill does the same.
- If the operator's internet provider blocks `supabase.co`, clip uploads from the PC still fail; this server move does not change that path.
