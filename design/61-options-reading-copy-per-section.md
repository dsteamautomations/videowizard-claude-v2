# design/61 — L17: the options package for reading, one file per section

Status: SK said go ahead, 21 Oct 2026 (candidate from VW-6's options stage, design/49).

## What happened on VW-6

`vw options prepare` downloaded the package as one reading file, `work/options-package.json`: 414 KB, 2,631 lines, thirteen sections one after another. Nothing told the assistant where a section starts, so it read by guessed line offsets: 11 reads before the scenes file (3 past the end, 3 refused as too large), then 14 more to get the sub-clip table after the package was refreshed and had moved. About a minute of reading twice, and a large slice of the assistant's working memory, on a stage whose output SK judged good.

## Change (plugin, and two step sentences in the procedure)

1. **One file per section** under `work/options/`, written by a new `options_reading_files(ws, data)` in `plugin/scripts/vw.py`, replacing the single file for the options package only (the visuals package keeps `reading_copy`):
   - `prompt.md` — the direction prompt (as the `.md` sidecar today)
   - `beats.json` — the beats with frames
   - `narration.json` — the narration without its words: sentences one row per line, pieces, pauses, frame counts
   - `words.json` — the words, one row per line (needed only for pauses and word timing)
   - `shapes.json` — the shapes of scenes.json and options.json
   - `coverage.json` — the coverage report
   - `cards.json` — the clip summary cards, one card per line
   - `sub-clips-1.json`, `sub-clips-2.json`, … — the eligible sub-clips, one row per line, **25 rows a file** (about 22 KB, under the reader's limit with room)
   - `rest.json` — contract, landmarks, learned rules, policy, project, timeline
   The folder is emptied of earlier `.json`/`.md` files first, so a refresh never leaves a stale part. `entities` is still left out; per sub-clip row `sfx_cues` and `editorial_ideas` are still dropped, and so now are the fields that serve the master build and the DaVinci UI, never a placement decision: `ui_path, crop_rect, position, zoom, source_width, source_height, source_fps, horizon_rotation_deg, stabilization_needed, log_sub_clip_id, fit_source, risk_flags_waived`. Everything the assistant reads to choose a shot stays (fit limits, outcome, handles, pairing, landmarks, colour, sound, peaks, grades, flags). The stored package on the server is unchanged.
2. **The prepare and scenes replies list the files** with their row counts and what each is for (`scenes`: beats, narration, shapes; `placements`: coverage, cards, sub-clips, words for pauses), and the summary line names the folder.
3. **Step text** (`server/procedures/v2.json`): step 1 names the folder and the files and says "read a file whole, never by line offsets"; the scenes step says to read `beats.json`, `narration.json` and `shapes.json` only; the authoring step names `coverage.json`, `cards.json` and the `sub-clips-N.json` files.

Reads on a 46-clip run: scenes step 3 files; placements 5 sub-clip files plus coverage and cards. No offsets, no refusals.

## Tests first

`plugin/tests/test_options_cli.py`: `options_reading_files` on a package with 30 sub-clips writes two sub-clip files of 25 and 5 rows one per line, drops the named fields and keeps `landmarks`, `grade`, `handles`; `narration.json` has the sentences one per line and no words; `words.json` has the words one per line; `prompt.md` holds the prompt; `entities` is nowhere; a stale `sub-clips-9.json` is removed; the returned list has a row count and a purpose per file. The download test uses the new function for the options package and `reading_copy` for the visuals package. The step-text test checks the folder, "never by line offsets" and the file names in the three steps.

## Not covered

server/tests (Docker). The new run's options stage is the live check: count the reads.

## Versions and deploy

Plugin 0.19.4 → 0.19.5; server 0.20.4 → 0.20.5 (the step text). Both deploys before the new run reaches options; the workers restart; the operator restarts Claude Code once.
