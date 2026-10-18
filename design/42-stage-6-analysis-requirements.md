# 42 — Stage 6 (analysis) improvements: requirements (approved by SK 18 Oct 2026, implemented the same day)

Source: the stage 6 review run with the stage review prompt on 18 Oct 2026 and SK's decisions on its 7 findings. Already done the same day, outside this note: the concurrency cap is a server setting and the live VM runs cap 15 with 18 workers after ten and twenty clips at once passed clean (design/35 row 29); the MEDIUM-thinking trial showed half the sub-clips, so HIGH stays (row 30). Dropped on re-reading the consumer: sub-beats at analysis (6.3), because the coverage report matches footage to approved scenes by chapter, not by beat. Acknowledged, no change: the re-solve's history (6.6) and the constants (6.7). This note builds the two that remain: 6.1 and 6.2. Nothing here makes a paid call. VW-3 is past analysis; every change is backward compatible with the 0.7.0 plugin and the 0.8.1 server.

## Decisions carried from the review
- `vw analysis status --wait N` polls inside the tool and reports a rough time left (6.1).
- Start reads the sound answer recorded at media; the film-type question is dropped for clip-log runs; two optional questions remain (6.2).

## A. Server changes (`server/`)

| # | What changes | Why | Where |
|---|---|---|---|
| 6.1 | `GET /api/runs/{id}/analysis` answer gains `cap` (the current `global_cap()`), so the tool can estimate the queue; and, per unit that is retained, `elapsed_seconds` already present in `cost` stays as is. | The estimate needs the cap. | analysis_jobs.py `status` |
| 6.2 | `AnalysisStart.camera_audio` becomes optional; `start()` uses the flag when given, else the media output's `summary.camera_audio`, else refuses with `ANALYSIS_POLICY`: "camera audio was not recorded at media; pass --camera-audio allowed\|excluded". `film_type` stays optional (default ''), used only by the version-1 request builder, as today. The policy stored on the job records where the value came from: `camera_audio_source: 'flag' \| 'media'`. | The answer given at media is used; the unused question goes. | main.py `AnalysisStart`, analysis_jobs.py `start` |
| — | `SERVER_VERSION` 0.8.1 → 0.9.0. | | config.py |

## B. Plugin changes (`plugin/`)

| # | What changes | Why | Where |
|---|---|---|---|
| 6.1 | `vw analysis status --wait N` (seconds, default 0): polls the status endpoint every 15 s until no unit is `queued`, `running` or `storage_pending`, or any unit is `submission_unknown`, `rejected`, `failed` or `retained_unstructured` (a decision is needed), or N seconds pass. Reuses `wait_for_jobs`'s shape with the analysis endpoint. The summary line: counts, then the estimate: average `elapsed_seconds` of the retained units (288 s when none yet, VW-3's average) × ceil(open units ÷ cap) → "12 retained, 5 running, 29 queued; about 25 min left"; with units needing a decision: "…; 2 need a decision: <unit ids>"; when the wait expired with work still open: "…; run again with --wait". Exit 0 in every case. | One turn instead of sixty. | vw.py `cmd_analysis`, parser (`--wait`) |
| 6.2 | `vw analysis start` no longer requires `--camera-audio` or `--film-type`. When `--camera-audio` is absent it posts nothing for it and the server fills from media; the answer carries `camera_audio` and `camera_audio_source`, and the tool's line says "camera audio: allowed (from the media stage)". The `ask_operator` message is replaced by: the tool proceeds, and the steps tell the assistant to ask, in one message before starting, "should the model listen to the clips' audio (default yes), and any clip to leave out (default none)?", passing `--understand-audio no` and `--exclude` only when the operator says so. | Two questions with defaults instead of four. | vw.py `cmd_analysis` |
| — | `plugin.json` 0.7.0 → 0.8.0. | | .claude-plugin/plugin.json |

## C. Procedure text (`server/procedures/v2.json`, analysis `steps`)
- Step 1: "Before starting, ask in one message: should the model listen to the clips' audio to understand them (default yes), and is there any clip to leave out (default none)? The camera-sound answer comes from the media stage; say it back ("camera audio: allowed, as you said at media"). Then `vw analysis start [--understand-audio no] [--exclude <clip> …]`: one paid Gemini 3.8 Flash request per clip; tell the operator, do not ask."
- Step 2: "Wait with `vw analysis status --wait 600`; report its line (counts and about how long is left); repeat until every clip is retained or excluded, or a clip needs a decision."
- Steps 3–5 unchanged; the mention of polling every minute goes. vw.md's analysis paragraph follows the same wording.

## D. Unstated but expected
- A new plugin against the 0.8.1 server: start without `--camera-audio` is refused by the old server's required field; the assistant passes the flag from the media summary it can read in the run folder (out/media.json has it since design/41). The order server-then-plugin keeps that window to minutes.
- A run whose media was recorded before design/41 (VW-3) has no `camera_audio` in its summary; start refuses with the message above and the assistant asks, as today.
- The estimate is rough by design: queue order favours runs with fewer active jobs, and clips differ in length; the line says "about".
- `--wait` never retries, recovers or excludes; it reads.

## E. Edge cases
| Case | Expected |
|---|---|
| start with media `camera_audio: excluded` and no flag | request identity `camera_audio: excluded`, source `media`; the line says so |
| start with `--camera-audio allowed` and media says excluded | the flag wins, source `flag` |
| start, no flag, media has no value | refused `ANALYSIS_POLICY` naming the flag |
| `--wait 600`, 46 clips, cap 15, 12 retained averaging 280 s | returns when settled or at 600 s; "about N min left" from ceil(open ÷ 15) × 280 s |
| a clip turns `failed` during the wait | returns at once: "1 needs a decision: <unit>" |
| all retained | "46 retained, 0 running; done" and exit 0 |
| status answer without `cap` (old server) | estimate uses 15 |
| `vw analysis start` twice | reuse as today (same analysis key) |

## F. Tests (written first)
Layer one, `plugin/tests/test_analysis_cli.py` (new): `--wait` with faked status answers (settles after two polls; a decision case returns at once; timeout says run again; the estimate line with and without `cap`; no sleeping without `--wait`); `start` without flags posts no `camera_audio` and prints the source from the answer; `start` with the flag posts it; the steps and vw.md carry `--wait 600` and the two-question wording and no "every minute".
Layer two, `server/tests/test_analysis.py` (Docker): A1 extended: media recorded with `--camera-audio allowed`, start without the flag → identity `camera_audio: allowed`, policy `camera_audio_source: media`; start with no flag and no media value → 422; status answer carries `cap` equal to the setting.

## G. Not covered
- server/tests cannot run on this Mac; compile-check only until a Docker machine runs them.
- The estimate's accuracy is checked on the next live analysis, not by a test.

## H. Deploy order
1. Server (`deploy-server.sh`, workers restart): tell SK first.
2. Plugin (`deploy-plugin.sh`); the operator restarts Claude Code.
3. design/35: a row.

## I. Estimate
Plugin with tests: about half a day. Server: an hour. Deploys: an hour.
