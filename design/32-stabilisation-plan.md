# 32 — From VW-2 to a stable build: how I would go about it (proposal for SK, 17 Oct 2026)

## What VW-2 taught us
VW-2 reached assembly in about a day and a half, with 14 tickets. Grouped by cause:

| Cause | Tickets | What it says about the build |
|---|---|---|
| **Outside limits nobody checked up front** | 3 (ElevenLabs credits), 4 (internet provider blocked Supabase), 5 and 6 (dropped uploads), 14 (Supabase upload size) | The tool did not check its limits before starting, and it reported failures as bare codes or timeouts |
| **Bugs that only show at real scale** | 7 (storage cache), 9 (lost writes with 5 workers), 12 (shared file, 70-second request) | The tests use tiny synthetic films; real runs have 46 clips, 27 takes and 278 MB films |
| **A feature change not carried through every later stage** | 13 (blank gap names, after the exact-match change) | Each change was tested up to the stage it touched, not through delivery |
| **Instructions written for the old v1 tool** | 8 (unreadable package), 11 (v1 visuals text) | The assistant followed instructions the v2 tool cannot carry out |
| **Plain mistakes** | 10 (option defined twice); also the 15 Oct syntax error | Now guarded by tests |

Found without tickets: a render failure nobody was told about, Supabase's error hidden behind "400", duplicated server routes, sound left on generated takes, and the test setup stalling on this PC.

**Never exercised yet:** delivery and the real DaVinci Resolve step on the Mac. VW-2 stopped at assembly.

## How I would go about it

### 1. Freeze, then close what is open (about 1 day)
- No new features until the build is declared stable. Ideas go on a list.
- Close ticket 11 properly: rewrite the visuals instructions for v2, refuse text graphics on video shots, add `--selector`.
- Run tickets 12 and 13's test runs to the end, once the test setup is fixed (next point).
- Fix the test setup stall on this PC, so a test run is trustworthy again.
- Finish VW-2 through delivery and the Resolve step. This proves the last two stages on real data.

### 2. Fix the patterns, not just the tickets (about 2 days)
- **Check the limits before a run starts.** A `vw` preflight checks: storage upload limit against the largest file the run will make; ElevenLabs credits against the script length; Gemini, OpenAI and video generator keys work; FFmpeg is present. A run that would fail later fails at the start, with a clear message.
- **No hidden failures.**
  - Supabase's own message instead of a bare code.
  - A long step reports "still working" instead of a timeout.
  - A failed background job is shown by `vw next` and `vw status`, so it is never silent.
- **Large files are resumable.** Films and clips upload in chunks that survive a dropped line. Supabase recommends this for files over 6 MB.
- **Every stage's instructions are checked against v2's real commands.** Visuals is known to be wrong; check the others the same way.
- **Generated takes are silent,** and the contact sheets you approved go in.

### 3. Go live (done 16 Oct by the live-server thread)
- Live on GCE VM `vw2` since 16 Oct 14:39 UTC (design/29). The PC server and workers must not run.
- A **scripted smoke run** on the live server: a 30-second script, 3 short clips, one real voice, real analysis, 2 real images and 1 real video take, through to delivery. It costs very little and takes about 20 minutes. It proves the live machine, storage, keys and limits end to end. Repeat it after every deploy.

### 4. The test round: a full production run on the live server (VW-3)
- A real project the size of VW-2, run start to finish, including delivery and the Resolve step on the Mac.
- Run as the team will run it: the operator thread only, no builder repairs in between.
- Record per stage: time, cost, retries, tickets, and anything the operator had to work around.

### 5. Deliberate failure checks (before declaring stable)
Each of these must recover or explain itself, never lose work or fail silently:
- a worker stopped in the middle of a render;
- the internet dropped during a large upload;
- storage refusing a file;
- a provider out of credit;
- the server restarted during a long step;
- two images or takes finishing at the same moment.

## When I would call the build stable
1. VW-3 runs from intake to delivery, including Resolve, with **no code-defect tickets**. Outside problems (credit, network) are allowed only if the tool caught and explained them.
2. Every failure in section 5 recovers or gives an actionable message.
3. Large files work on the live server: at least a 1 GB clip upload and a 500 MB film.
4. The full test suite passes reliably in one run, and a changed stage's tests run in under 15 minutes.
5. Baselines are written down: minutes per clip for analysis, render minutes per film minute, upload speed, cost per finished minute.

## Rough timeline
| Step | Time |
|---|---|
| 1. Freeze and close open work, finish VW-2 | about 1 day, plus SK's time for VW-2 |
| 2. Fix the patterns | about 2 days |
| 3. Go live and the smoke run | depends on the live-server thread; the smoke run itself is under an hour |
| 4. VW-3 full run | as long as a real project; about a day of operator time |
| 5. Failure checks | about half a day |

I would like to hear SK's own list before fixing this plan. Anything on it slots into the acceptance criteria above.
