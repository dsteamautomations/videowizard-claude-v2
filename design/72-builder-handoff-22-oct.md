# design/72 — Builder handoff, 22 Oct 2026

For the team member who continues the builder work on another laptop. Written by the builder on 22 Oct 2026 at SK's request. Everything below is in this repository (`dsteamautomations/videowizard-claude-v2`, branch `main`); the working tree was clean and equal to `origin/main` when this was written. Read `CLAUDE.md` first: it holds the roles, the working rules, the defect loop, the deploy scripts and the tools, and it is binding.

## 1. Where things stand

- **Live.** Server 0.25.1 (commit fbddb40), plugin 0.23.0 (98f9f65). VM `vw2`, 18 worker processes (the VM's `server/.env` sets `VW2_WORKERS=18`; the analysis cap needs 15). Both services clean at the last check.
- **The live run.** VW-6 (NARDEP Rat-Trap Bond, 46 clips) is at the visuals stage in a **first pass on its first three gaps** (BEAT_01, BEAT_02-B1, BEAT_02-B2): treatment recorded, plan v1 proposed, the three gaps accepted, seven footage frames approved as references, the first generated images made on 22 Oct. SK is reviewing them and will send findings. The first pass was a test expedient, not a product feature: the stage is per gap and the run stays at visuals until every gap is recorded.
- **Held for SK.** design/71 (the six L30 items plus the VideoWizard answer form) is written and committed, waiting for SK's review of the first images; SK's findings join it or become design/72's successor. Nothing of it is built.
- **Queued for the next batch** (built together at an idle point, after SK approves): design/68 part B (the checklist beside each picture on the page, the feedback record with a picture reject, the library handoff zip), L24 to L31 (listed at the end of design/49: boundary shared only within one continuous shot; treatment routes from the shot list; no cap raise on either front end; write while images generate with one approval wave per shot; a draft shown after a recorded treatment; the page refreshing when idle; bind-before-packet said plainly), and design/71.
- **Open decisions for SK**, carried from the library: real-person consent (none recorded; a real face is a look reference only), Higgsfield as a route in the library, the real prices in rupees behind the visuals meter (the settings hold the builder's estimates, ₹20 an image, ₹8 a second).

## 2. Design notes that need attention, in reading order

| Note | Why it matters now |
|---|---|
| `CLAUDE.md` | the rules; the deploy scripts; the tools on the Mac |
| design/49 | the live-run log: every finding, timing and candidate (L-numbers), newest at the end |
| design/35 | one row per deployed release, newest at the end (row 61 is the last) |
| design/65 | the visuals stage as agreed: four routes, the treatment as a record, graphic sequences, the cap, the visuals page |
| design/66, 67 | AI video in segments with a start and an end image; the three packet instructions; the start's references sent again |
| design/68 | the image prompt library in the stage (part A built; part B queued); §3 lists the proposer's note against the code |
| design/69 | the VideoWizard answer form, approved by Revathi, to be built in design/71 |
| design/70 | the library against the pair rules, for the reviewers |
| design/71 | the held requirements note for L30 and the form |
| design/62, 63 | the review page (options and master), the pattern the visuals page follows |
| design/52, 54, 55 | the voice stage and the voices page |
| design/48 | why the run refuses every write while a defect is open |
| design/29 | the VM: how it was set up and how updates travel |

## 3. The voice stage, what changed (20 Oct)

- design/52: the stage rebuilt around direction first. The operator picks a voice, records a direction with test passages, hears up to three full narrations, chooses, downloads.
- defect 16 and the standing rule **one flow, two front ends**: a library voice is saved to the ElevenLabs account inside the shared server function both front ends call (`voices.ensure_on_account` from `jobs.submit_voice`), never by a procedure instruction. The rule is in `CLAUDE.md`.
- design/54 and 55: the voices page `/runs/<code>/voices2` in four steps (Browse, Try, Narrations, Final), live provider search with filters, tryouts with tags, concurrent narrations in different voices, the direction recorded with three test passages (`--passage`). The first voices page and the voice catalogue mirror were removed (server 0.20.0); `/runs/<code>/voices` redirects.
- Small fixes: the VOICE_NOT_ON_ACCOUNT message names the catalogue command (L11); the Direction model's `register` field renamed (L13); the voices page audio route restored after the cleanup had dropped it (found by the review page work).

## 4. The visuals stage, what changed (20 to 22 Oct)

- design/65 (server 0.22.0, plugin 0.21.0): every picture is made in the pipeline, no hand-made route. Four routes: footage frame, AI still, AI graphic sequence, AI video. A graphic that moves is two to four states of one drawing, each generated from the previous as its parent, approved as one, played with dissolves at assembly. The treatment is a recorded step the plan is checked against (`propose` refuses without it or when a route departs). A cap per film on paid calls. The script's own Visuals lines are kept at intake and shown to the planner. The visuals package is read per section under `work/visuals/`. The visuals page `/runs/<code>/visuals`: treatment, gaps, pictures, sequences, takes, spend.
- design/66 (0.23.0 / 0.22.0): AI video is planned in segments cut where an action begins or ends, at most what the generator makes; every take has a start and an end image; the end is generated from the start as its parent; consecutive segments of one continuous shot share their boundary picture, so images are counted as segments plus one; `prepare-take` refuses without the end; the cap default is ₹5,000.
- design/67 (0.24.0): three fixed instructions in the composition packet (start written with the end in mind and composed for the whole segment; end with positions against landmarks and nothing else changed; motion); the server sends the start keyframe's own identity references behind it when an end keyframe is generated.
- design/68 part A (0.25.0 / 0.23.0): Revathi's image prompt library (snapshot `vwlib-2026-10-21-4f88379be109`, with licences) under `server/library/`, read by the server and never written; `library.py` (versions, manifest check, the step map from VW-MAP, the job form filled from the run per FIELD-SOURCES, the answer lint); the session records the library version; `GET /visuals/library`; the packet carries a library block beside the three instructions, digested without it; `vw visuals prepare` writes the library per step under `work/visuals/library/` behind the procedure sentinel; `image` and `prepare-take` take `--answer`, optional.
- defect 19 (0.25.1): the packet route runs inside the stage guard, so a packet asked before `bind` is a 422 with its message, not a 500.
- Earlier, the review page (design/62, 63) made the options and master decisions clickable on `/runs/<code>/review`; the visuals page copies its pattern.

## 5. Testing on a laptop

- Clone the repo. Make a virtualenv with Python 3.12 if you can (3.9 runs everything except modules with 3.10 annotations such as `app.web`): `pip install -r server/requirements.txt` (pytest is in it) and `pip install -r plugin/requirements.txt`.
- Run the two suites **separately**; one combined command breaks collection: `python -m pytest server/unit -q` and `python -m pytest plugin/tests -q`. Counts at this handoff: 131 and 211.
- `server/tests` needs Docker (a throwaway `postgres:17`); it has never run on the builder's Mac. List it under "not covered" in every note, as the notes do.
- Before every push: `for f in $(find plugin -name '*.py'); do python -m py_compile "$f"; done` with a Python 3.9, since the plugin's hooks run under the operator's 3.9. Compile the changed server files too.
- The visuals prompt in `server/procedures/v2.json` has a word budget of 3,500 (a plugin test checks it); the file round-trips byte for byte with `json.dumps(indent=2, ensure_ascii=False)` plus a trailing newline, so edit it by loading and dumping that way.
- Check the exit status of a test run before committing; a run piped into `tail` once hid a failure.

## 6. Deploying from a new laptop

Both scripts refuse to run when the working tree is dirty or local `main` is not exactly `origin/main`. Commit and push first.

**Server** (`./scripts/deploy-server.sh`, anything under `server/`):
1. Install the Google Cloud SDK and run `gcloud auth login` with SK's account; project `sm-project-435806`. The SDK needs Python 3.10+; the script and `~/.zprofile` on the builder's Mac point it at the SDK's own CPython (`CLOUDSDK_PYTHON`). On a laptop with Python 3.12 that line is unnecessary; if `gcloud` is not on PATH in a non-login shell, `source ~/.zprofile` (or the equivalent) first.
2. Tell SK before running it: the workers restart, and the restart drains running jobs first, up to 40 minutes. Check nothing is running on the live run.
3. The script bundles `main`, copies it to the VM over IAP, pulls, installs requirements, restarts `vw2-server` and `vw2-worker`, then polls `/api/meta` and prints `server_version`. Bump `SERVER_VERSION` in `server/app/config.py` so the release is visible there.
4. Afterwards: `curl -s https://8-234-82-225.sslip.io/api/meta`; on the VM `systemctl is-active vw2-server vw2-worker` and `journalctl -u vw2-server -u vw2-worker --since "5 min ago" -p warning`. SSH: `gcloud compute ssh vw2 --zone asia-south1-a --project sm-project-435806 --tunnel-through-iap`.
5. The VM's `server/.env` is the only copy of the secrets and the worker count. It is never in git and never pasted into chat. Edit it only by hand on the VM with `sed` or an editor, and never print it.

**Plugin** (`./scripts/deploy-plugin.sh`, anything under `plugin/`):
1. The script runs the bundled Claude Code binary, whose path is hard-coded at the top of the script and in `CLAUDE.md` (`.../claude-code/<version>/<hash>/claude.app/Contents/MacOS/claude`). On another laptop find the equivalent path (or a `claude` on PATH) and change the `CLAUDE=` line, in a commit.
2. It compiles every plugin file, updates the marketplace `vw-local`, uninstalls and reinstalls `vw@vw-local` at user scope (a plain update is a no-op unless the version changes), disables it at user scope again, and checks the installed commit equals `main`. Bump `plugin/.claude-plugin/plugin.json`.
3. The operator must restart Claude Code in the operator folder afterwards. Nothing changes on the VM.

**After any deploy:** a row in design/35 and a line in design/49; for a defect, a resolution line appended to `log_excerpt` in Supabase (project VideoBuilder, `myaibwryhhkunghfxqye`, table `vw2_defects`) in the form `Resolution (builder, <date>): …` and `status` set to `fixed`, because the run refuses every write while a defect is open (design/48).

## 7. Working with SK

Requirements note first (design/NN), then SK's approval, tests first, then the change, a self-review, commit and push, tell SK before any restart, deploy, log, resolve the defect, give SK the text the operator pastes. SK approves each deploy explicitly. Never modify `videowizard-beta`. Trial runs are disposable: never design for old runs or old flows. Keep a "not covered" list with every piece of work. SK reads the operator's screen, not the builder's tool calls: answers go in plain English with the paste text ready.
