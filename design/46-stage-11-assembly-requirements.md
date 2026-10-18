# 46 — Stage 11 (assembly) improvements: requirements (approved by SK 18 Oct 2026, implemented the same day)

Source: the stage 11 review run with the stage review prompt on 18 Oct 2026 and SK's decisions on its 7 findings. No assembly has run on this server (VW-3 stands at visuals); the numbers are VW-3's master render rate (19 timeline frames per second of wall time at 1080p) and VW-3's plan (28 fills). Finding 11.1 is a defect of mine from design/44 8.3: since server 0.12.0 the assembly film would render at 1280×720. Nothing here makes a paid call.

## Decisions carried from the review
- The assembly film renders at 1920×1080 again; the plan kind is `assembly` (11.1).
- Prepare reads each take's recorded evidence and downloads only files without it (11.2).
- The defaults are confirmed once; `choose` is for exceptions, with a file; frame notes take a time (11.3).
- `vw assembly status --wait N` (11.4).
- `record --quote` with the watched-and-listened words records the accepted review and the output (11.5).
- A true-peak limiter at −3 dBTP on the mix of master and assembly films; the record and the fetch line report the numbers (11.6).
- One segment cache per run for master and assembly pieces, deleted at close (11.7).

## A. Server changes (`server/`)

| # | What changes | Why | Where |
|---|---|---|---|
| 11.1 | `assembly.render` writes the plan with `kind: 'assembly'`. `render_film`: the whole-narration path (one gain, `apad`) runs for `master` and `assembly`; `WATCHED_SIZE` stays `{review, master}`; the codec line for assembly stays the full one. `render_jobs.process` is unchanged (it passes the plan's kind). | The delivered film must be the full one. | `stage3/assembly.py`, `stage2/render.py` |
| 11.2 | `visual_workers.probe` adds `color_transfer`, `color_primaries`, `rotation_deg` and `issues` (as `assembly.probe_file` computes them). `visuals_stage.record_gap` copies the take's evidence into the shot record as `media: {kind: 'movie', duration_s, fps, width, height, color_transfer, color_primaries, rotation_deg, issues}`; a still from a reference (10.3) records `media: {kind: 'still'}`. `assembly.prepare` uses `shot['media']` when present and probes (downloads) only a fill without it (a hand-made movie, or a gap recorded before this change). | Seconds instead of minutes; no download to fail. | `visual_workers.py`, `visuals_stage.py`, `stage3/assembly.py` |
| 11.4 | `assembly.render` stores `frames` on the render entry (events' and fills' timeline frames); `assembly.status` adds `render_rate_fps` (the same query as stage 2). | The tool's estimate. | `stage3/assembly.py` |
| 11.5 | `assembly.record(quote)`: when the latest review does not accept the current film but the quote contains "watch" and "listen", an accepted review with empty notes and the film's hash is appended first, then the output is recorded; without the words and without an accepted review, refused as today naming the words. | One yes, one call. | `stage3/assembly.py` |
| 11.6 | `render_film`: for `master` and `assembly` the mix passes through `alimiter` with a −3 dBFS ceiling (linear 0.708, `level=false`) before the mux; the record adds `loudness_check: {integrated_lufs, true_peak_dbfs, peak_ceiling_dbtp: -3, peak_inside, integrated_target_lufs: -16, integrated_inside}`, inside = peak ≤ −3 dBTP measured by `ebur128`, integrated within ±1.5 LU of −16. `assembly.record` copies `loudness_check` into the summary. | No clipped peaks in a delivered film; the numbers shown against the targets. The integrated target is the narration's −16: v2 adds no music, so the blueprint's −14 master figure (which assumes A4) cannot be met and is not claimed. | `stage2/render.py`, `stage3/assembly.py` |
| 11.7 | `Renderer(work, timeline, fast, cache=None)`: the cache folder is given; `render_jobs.process` uses `CACHE / <run_id> / 'cache'` for `master` and `assembly` plans and the per-film folder for `review` (its pieces carry slide labels); the per-film work folder is still deleted after a verified upload (design/43 7.7); `vw close` removes `CACHE / <run_id>`. | A change round re-encodes only the changed fills. | `stage2/render.py`, `stage2/render_jobs.py`, `core.close` (or wherever close deletes storage) |
| — | `SERVER_VERSION` 0.12.0 → 0.13.0. | | `config.py` |

## B. Plugin changes (`plugin/`)

| # | What changes | Why | Where |
|---|---|---|---|
| 11.3 | `vw assembly choose --file out/fills.json`: a list of `{shot, offset?, end?, accept_as_is?}`, one request each in order, stops at the first refusal (`recorded`, `refused`, `remaining`, as `master decide --file`). `--frame-note` accepts `mm:ss:note` and `mm:ss.f:note` (25 fps) as well as `frames:note`. `prepare` prints one table line per fill: "VS1 slot 85 f, take 100 f, trim from 0" / "AN3 slot 290 f, still, hold" / "VS4 … colour untagged: needs --accept-as-is". | One answer for the defaults. | `vw.py` `cmd_assembly`, parser (`--file`) |
| 11.4 | `vw assembly status --wait N`: `wait_for_film(run, 'assembly', wait_s, path='/stage3')`; the line names the assembly film and `vw assembly fetch`. | | `vw.py` |
| 11.5 | `record` prints "Assembly recorded (watched and listened); next `vw delivery bundle`". | | `vw.py` |
| 11.6 | `fetch` prints the loudness line from the record: "mix −15.8 LUFS (target −16), peak −3.0 dBTP (ceiling −3): inside" or "… outside: <which>". | The operator hears the film and sees the numbers. | `vw.py` |
| — | `plugin.json` 0.11.0 → 0.12.0. | | `.claude-plugin/plugin.json` |

## C. Procedure text (`server/procedures/v2.json`, assembly `steps`)
1. "`vw assembly prepare`: it lists every gap fill on one line (slot frames, what the take or asset covers, the default: trim from frame 0, or hold the last frame when the take is short; issues such as untagged colour or rotation) and the shots the logs flagged as shaky."
2. "Show the operator that table and ask once: any fill to change (start offset, trim or hold), any flagged shot to stabilise with FFmpeg (counted in the zoom cap), and for each fill with an issue whether to use it as it is or swap it in visuals. Record only the exceptions: `vw assembly choose --shot S --offset f --end trim|hold_last [--accept-as-is]`, or several in `out/fills.json` with `--file`; `vw assembly stabilize --sub X --choice ffmpeg`. The defaults need no command."
3. "`vw assembly build`, `vw assembly render` (A1 narration with one measured gain, A2 nat sound at the blueprint band, a −3 dBTP ceiling on the mix, no music), `vw assembly status --wait 900` until the film is ready, `vw assembly fetch` (it prints the loudness against the targets). The operator watches AND listens."
4. "On their yes (it must say watched and listened): `vw assembly record --quote \"<their words>\"` records the review and the output together. On changes: `vw assembly review --decision changes --notes \"…\" [--frame-note mm:ss:note] --quote \"…\"`, change the choices the notes name, build and render again (only the changed fills are re-encoded). On a no: `--decision rejected` and `vw revise --stage visuals` or `--stage master` as the notes say."
vw.md's assembly paragraph follows the same wording.

## D. Unstated but expected
- A 0.11.0 plugin against the 0.13.0 server: every old command works; `review accepted` then `record` still passes (the accepted review is simply there).
- Gaps recorded before this change have no `media` on their shots; prepare downloads and probes them as today.
- The limiter acts on the mixed film only; the narration file in the bundle stays byte-identical to the approved narration (design/16 D7).
- The integrated figure is reported against −16 LUFS (the narration's target); a film is "outside" when the mix drifts more than 1.5 LU from it or the peak exceeds −3 dBTP after limiting (which `ebur128` true-peak measurement would show; the sample ceiling is −3 dBFS).
- The per-run cache holds the master's and the assembly's pieces until `vw close`; a run never closed keeps them (the VM has 87 GB free; a sweep is not built).
- `--wait` never re-renders or records; it reads.

## E. Edge cases
| Case | Expected |
|---|---|
| an assembly plan rendered | 1920×1080, preset medium, the whole narration under it, loudness measured, `loudness_check` in the record |
| a master plan rendered | 1280×720, fast, as design/44 |
| prepare with every fill a take recorded after this change | no download; the fills' media from the visuals records |
| prepare with one hand-made movie asset | only that file is downloaded and probed |
| `choose --file` with VS1 ok and VS9 unknown | VS1 recorded, stops at VS9, `remaining` listed |
| `--frame-note 0:40:too short` | frame 1000; `--frame-note 1000:too short` unchanged |
| `status --wait 900` | polls every 15 s; "assembly film rendering, about M min left"; "assembly film ready: `vw assembly fetch`" |
| `record --quote "yes"` with no accepted review | refused: must say watched and listened |
| `record --quote "yes, watched it and listened"` with no review | an accepted review appended, the output recorded |
| `record` after `review --decision changes` and a new render | the quote's words record the new film |
| a mix peaking at +0.2 dBFS before the limiter | after: peak ≤ −3 dBFS sample, `peak_inside: true` |
| second assembly render after one fill changed | the unchanged footage and fills come from the run cache; only the changed fill is encoded |
| `vw close` | `spool/render/<run>` removed |

## F. Tests (written first)
Layer one, `plugin/tests/test_assembly_cli.py` (new): `choose --file` order and stop; frame-note time parsing; `status --wait` on the stage 3 path (ready, failed, expiry); the record and fetch lines; the steps and vw.md wording.
Layer one, `server/unit/test_stage2_pure.py` extended: `render_film('assembly', …)` renders 1920×1080 with the whole-narration path and a `loudness_check`; a plan whose narration tone peaks at 0 dBFS renders with the mix peak at or under −3 dBFS; `Renderer` uses the cache folder it is given; `probe` reports colour tags and rotation on a synthetic file.
Layer two, `server/tests/test_stage3.py` (Docker): D10 rewritten (`record` with the words and no review records both; without the words refused); prepare after a take recorded with evidence makes no storage read of the take (the fake store counts reads); `status` carries `frames` and `render_rate_fps`; the second render after a `choose` reuses the cache (the cache folder holds the first render's pieces).

## G. Not covered
- `server/tests` cannot run on this Mac; compile check only until a Docker machine runs them.
- The limiter's audible effect and the loudness of a delivered film: judged by SK on VW-3's assembly.
- The time saved by the cache: measured on the first change round.

## H. Deploy order
1. Server (`deploy-server.sh`, workers restart): tell SK first. 11.1 goes live with it.
2. Plugin (`deploy-plugin.sh`); the operator restarts Claude Code.
3. design/35: a row; design/33 D2 and design/34 P5 marked done.

## I. Estimate
Server with tests: a day. Plugin with tests: half a day. Deploys: an hour.
