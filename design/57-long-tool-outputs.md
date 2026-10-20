# design/57 — Defect 17: a long tool output the assistant cannot read

Status: proposed, 20 Oct 2026. Defect 17, VW-6 at the media stage, 46 clips (47 files, one duplicate) in `runs/VW-6/in/`.

## What happened

`vw stage media prepare` printed 32 KB of JSON: the full probe of every clip (sha256, codec, frame rate, colour transfer, rotation, audio channels … about 640 characters a clip). The desktop app keeps any tool output over roughly 30 KB out of the conversation: it writes the output to a file under `~/.claude/projects/<operator project>/<session>/tool-results/` and shows the assistant the first 2 KB. The guard allows reads inside the active run only, so the assistant could not open that file. Its other attempts were rightly blocked (a redirect into the run folder is command chaining; the terminal tool is not the vw tool). It filed the defect. Nothing was uploaded; nothing is wrong on the server.

The same per-clip detail was already on disk inside the run, in `work/media-clips.json` (prepare writes it, record reads it), which the assistant may read; nothing told it so.

The record step has the same exposure, measured on VW-3's stored row (46 clips): the summary is 20 KB and the file references 11 KB, over the limit together. `vw stage media record` prints the whole output row the server returns, whose summary carries thirteen fields per clip and a file reference per clip. At 46 clips that is near the same limit.

## Change

1. **Prepare prints a listing, not the probe** (`plugin/scripts/stages_av.py` `media_prepare`). The returned `clips` carry what the operator confirms: `name`, `duration_s`, `mb`, `sound` (yes/no), and `transcoded_from_vfr` when true. The full probe stays in `work/media-clips.json`, named in the output as `detail_file`. A `listing` string gives one line per clip in file-name order (`C0032_02881492.mp4 · 3.8 s · 2.7 MB · sound`) and ends with the totals, so the assistant can show the operator the list as it is. At 46 clips the output is about 6 KB.
2. **Record prints the receipt, not the row** (`plugin/scripts/vw.py` `cmd_stage`): for media, the printed JSON is the row without `summary.clips` and `files`, plus `clips_recorded` and `total_mb`. The server keeps the full row; the summary line already names the next stage. Other stages print as today.
3. ~~The guard lets the assistant read its own parked tool outputs.~~ Dropped on SK's word (20 Oct): the guard is not the problem and is not touched; the tool prints less, so nothing gets parked.
4. **The media step text** (`server/procedures/v2.json`, step 1): "`vw stage media prepare` prints one line per clip (name, length, size, sound); the full probe is in work/media-clips.json."

Not changed: the server, the page, the record's server-side summary (analysis needs the per-clip fields).

## Tests first

`plugin/tests/test_media.py`: prepare's `clips` carry only the five confirmation fields, `listing` has one line per clip and the totals, `detail_file` names the work file, the work file still holds the full probe; the record print (via `test_cmd_stage_prints_progress_lines_and_passes_the_flags`) omits `summary.clips` and `files` and carries `clips_recorded`. `plugin/tests/test_media.py::test_media_prompt_and_steps_are_v2` checks the new sentence.

## Not covered

server/tests (Docker). The persisted-output threshold is the desktop app's, not documented; the listing is sized well under it rather than to it. The analysis status output at 46 units is measured when the stage runs; if it is long, that command prints less, as media now does.

## Versions

Plugin 0.19.0 → 0.19.1; server 0.20.1 → 0.20.2 (the step sentence lives in the procedure the server serves). VW-6 continues at media after both deploys and the operator's restart: `vw stage media prepare` again (the clips are unchanged, the hashes are reused only if nothing moved; it probes again, about a minute), confirm the list, the camera-sound question, record.
