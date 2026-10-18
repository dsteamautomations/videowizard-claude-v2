# 47 — Stage 12 (delivery) improvements: requirements (approved by SK 18 Oct 2026, implemented the same day)

Source: the stage 12 review run with the stage review prompt on 18 Oct 2026 and SK's decisions on its 5 findings. No delivery has run on this server. SK declined the real Resolve dry run (12.1: the first real run is the test) and kept the two-machine wording of the steps (12.2). This note builds the three that remain: 12.3, 12.4, 12.5. Nothing here makes a paid call; the server change is text only.

## Decisions carried from the review
- The finishing checklist and OPEN-EDIT say what the film is: −16 LUFS with a −3 dBTP ceiling, one subtitle cue per sentence, the measured loudness on the checklist (12.3).
- The Mac step downloads the bundle three files at a time with a progress line each (12.4).
- `vw close` keeps `logs/` and moves the guard log into it (12.5).
- Left as they are: the Resolve step unexercised against Resolve (12.1), the steps' two-machine wording (12.2).

## A. Server changes (`server/`)

| # | What changes | Why | Where |
|---|---|---|---|
| 12.3 | `checklist_of`: the Fairlight bus line becomes "Master bus: the approved film is rendered to −16 LUFS integrated (the narration's target; v2 adds no music) with a −3 dBTP ceiling; it measured <integrated> LUFS, peak <true peak> dBTP" (the numbers from the assembly output's `loudness.check`, "not measured" when absent); the A4 music line keeps its ducking figures. `bundle`: OPEN-EDIT's line 3 becomes "Subtitles.srt has one cue per narrated sentence, shifted by the approved pauses." | The editor reads what the film is, not the blueprint's figures for a film with music. | `stage3/delivery.py` (`checklist_of` gains the assembly summary's loudness; `bundle`) |
| — | `SERVER_VERSION` 0.13.0 → 0.14.0. | | `config.py` |

## B. Plugin changes (`plugin/`)

| # | What changes | Why | Where |
|---|---|---|---|
| 12.4 | `cmd_delivery --run`: the originals, normalised copies and narration are downloaded with a pool of three (as media uploads, design/41 5.4), one line per finished file on stderr: "downloaded k/n name (MB)"; a failed download stops before dispatch with the file named (the ledger stays reserved; `--close` or run again). The dead branch (`if False`) is removed; the manifest is read from `work/manifest.json` or downloaded when absent. | About 1 GB on VW-3's scale, faster and visible. | `vw.py` `cmd_delivery` |
| 12.5 | `cmd_close`: `work/guard.log` is moved to `logs/guard.log` before `work/` is deleted; `logs/` is kept always (the `--keep-logs` flag stays accepted and changes nothing). The closing line says "logs/ kept (guard log inside)". | The record of blocked calls survives the run. | `vw.py` `cmd_close` |
| — | `plugin.json` 0.12.0 → 0.13.0. | | `.claude-plugin/plugin.json` |

## C. Procedure text
Unchanged (12.2). vw.md's delivery sentence gains "(the bundle files download three at a time; `vw close` keeps logs/ with the guard log)".

## D. Unstated but expected
- A bundle built before this change keeps its old checklist; the next `vw delivery bundle` rewrites the generated files.
- The loudness line reads the assembly output recorded with design/46; an assembly recorded before it has no `loudness.check` and the line says "not measured".
- The pooled download writes each file to its final path only when complete (the downloader already writes whole files); a rerun of `--run` after a failed download repeats the download of files that are missing or whose hash differs, as today.
- Nothing on the server changes for 12.4 and 12.5.

## E. Edge cases
| Case | Expected |
|---|---|
| bundle after an assembly with `loudness.check` | the checklist line carries its integrated and peak figures |
| bundle after an assembly without it | "not measured" |
| OPEN-EDIT | names one cue per sentence and the pauses |
| `--run` with 12 bundle files | three in flight, twelve "downloaded k/12" lines, then dispatch |
| one download fails | stops before dispatch naming the file; the ledger is reserved; `--close` then `--run` again, or `--run` again after the line is back |
| `vw close` on a run with blocked calls | `logs/guard.log` holds them; `logs/` remains; `work/` and the unretained `out/` files are gone |
| `vw close` on a run with no guard log | `logs/` kept, nothing moved |

## F. Tests (written first)
Layer one, `plugin/tests/test_delivery_cli.py` (new): the pooled download with a fake downloader (order, the progress lines, a failure stops before the dispatch mark); `cmd_close` moves the guard log and keeps `logs/` (a run folder in `tmp_path`, the server faked).
Layer one, `server/unit/test_delivery_pure.py` (new, no database): `checklist_of` with and without the loudness check; the OPEN-EDIT text is built by a pure function `open_edit_text(run)` and names sentences.
Layer two, `server/tests/test_stage3.py` (Docker): the bundle's checklist carries the measured loudness and OPEN-EDIT the sentence line.

## G. Not covered
- The Resolve adapter against the real application (12.1, declined).
- `server/tests` cannot run on this Mac; compile check only until a Docker machine runs them.

## H. Deploy order
1. Server (`deploy-server.sh`, workers restart): tell SK first.
2. Plugin (`deploy-plugin.sh`); the operator restarts Claude Code.
3. design/35: a row.

## I. Estimate
Half a day in all.
