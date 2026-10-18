# 41 — Stage 5 (media) improvements: requirements (approved by SK 18 Oct 2026, implemented the same day)

Source: the stage 5 review run with the stage review prompt on 18 Oct 2026 and SK's decisions on its 6 findings. Five go ahead (5.1–5.5); 5.6 confirmed the constants (the 200 MB per-clip ceiling stays until a real shoot hits it). Nothing here makes a paid call. VW-3 is past media and is not affected; every change is backward compatible with the 0.6.0 plugin and the 0.7.0 server. Two items carry to the stage 6 review: analysis reading the recorded sound answer as its default, and whether the film type comes from the brief.

## Decisions carried from the review
- The **source-audio answer** is recorded at media with the operator's words (5.1).
- The media **prompt** is cut to four rules and the tool's facts (5.2).
- Prepare **hashes in chunks and uses a pool** (5.3); the upload says its **size up front and reports each clip** (5.4); a clip **changed since prepare is refused** (5.5).

## A. Plugin changes (`plugin/`)

| # | What changes | Why | Where |
|---|---|---|---|
| 5.1 | `vw stage media record` gains `--camera-audio allowed\|excluded` and `--note "<the operator's words>"`; the media summary gains `camera_audio` (or null when not given) and `camera_audio_note` (empty string when none). Not required: a record without the flag still succeeds, so analysis asks as today. | The answer asked once at media is kept. | vw.py parser (`stage` gains `--camera-audio`, reuses `--note`), `cmd_stage` (media record call passes both), stages_av.py `media_record` |
| 5.3 | `media_prepare`: `sha256` computed in 1 MB chunks (new helper `file_sha256(path)` in stages_av.py); size check, hash and probe run for three clips at a time through `ThreadPoolExecutor(max_workers=3)`; variable-frame-rate transcodes run through a second pool of two after the first pass; results are assembled in file-name order and duplicates removed in that order (the first name wins, as today). A `Refused` raised in a worker surfaces as the same refusal. | Whole-file reads and serial work on a laptop. | stages_av.py `media_prepare` |
| 5.4 | Prepare's answer gains `total_bytes` and `total_mb`, and its message says "N clips, M MB; the upload reports when it is done". Record prints one line per finished clip to stderr as it completes: `uploaded 12/46 clip-name (34 MB)`; the final summary line is unchanged. | A silent seven minutes; no trace of where a dropped upload stopped. | stages_av.py `media_prepare`; vw.py `upload_file` (an optional `progress` callback) and the media record call |
| 5.5 | Prepare stores each clip's `bytes` and `mtime` (of the file in `in/`, not the transcoded copy) in work/media-clips.json; record re-stats every clip before uploading and refuses when any size or mtime differs: "The clips changed since prepare (name, name); run `vw stage media prepare` again." | A swapped clip went up under the old hash. | stages_av.py `media_prepare`, `media_record` |
| — | `plugin.json` 0.6.0 → 0.7.0. | | .claude-plugin/plugin.json |

## B. Server changes (`server/`)

| # | What changes | Why | Where |
|---|---|---|---|
| 5.2 | Media prompt replaced (about 90 words): the four rules kept from v1, "preserve the clips' names and bytes; a probe of metadata is not an analysis, do not describe what a clip shows; identical files are listed once; ask the source-audio policy once, record it with `--camera-audio` and the operator's words", plus the tool's facts: clips in runs/<code>/in/, 200 MB each, variable-frame-rate clips converted before upload, re-run record to resume, nothing is analysed at this stage. Steps: step 1 adds "prepare reports the clip count and total MB; tell the operator and that the tool reports when the upload is done"; step 3 becomes "`vw stage media record --camera-audio allowed\|excluded --note \"<their words>\" --quote \"<their reply>\"`…". | v1 library text naming a library, a UI and a page. | procedures/v2.json media `prompt`, `steps`, `prompt_origin` |
| — | `SERVER_VERSION` 0.7.0 → 0.8.0. | | config.py |

## C. Unstated but expected
- A new plugin against the 0.7.0 server: the two new summary fields are stored like any summary field; nothing reads them until stage 6's change lands. A new server against the 0.6.0 plugin: the steps name a flag the old plugin lacks; the assistant gets an argparse refusal and asks at analysis as before. The order server-then-plugin keeps that window to minutes.
- The pool keeps the clip list in file-name order; the operator's chat list and the units for analysis are unchanged in order.
- Transcodes happen after all hashes and probes, so the clip list is complete before the slow part starts; two at a time because ffmpeg uses several cores itself.
- Progress lines go to stderr, which the tool already uses for its summary; the JSON on stdout is unchanged.
- The mtime check uses the operating system's modification time; copying a clip again with the same bytes refreshes the mtime and forces a prepare, which is a few seconds. Acceptable.

## D. Edge cases
| Case | Expected |
|---|---|
| record with `--camera-audio allowed --note "no speech, site noise only"` | summary `camera_audio: allowed`, `camera_audio_note` as given |
| record without the flag | summary `camera_audio: null`, note empty; analysis asks as today |
| 46 clips, none VFR | hashes and probes three at a time; list order equal to today's; same ids |
| two VFR clips among ten | transcoded two at a time after the first pass; `transcoded_from_vfr` as today |
| a clip over 200 MB | refused before anything else, as today (M1) |
| a clip replaced after prepare, same size | refused at record naming the clip |
| a clip touched (copied again) after prepare | refused at record; prepare again is seconds |
| upload interrupted after 12 clips | stderr shows `uploaded 12/46 …`; the refusal names the clip; re-run record skips the 12 (M2) |
| a worker in the prepare pool raises `Refused` | the same refusal and message as today |
| prepare message | "46 clips, 876 MB; the upload reports when it is done" |

## E. Tests (written first)
Layer one, `plugin/tests/test_media.py` (new, runs on this Mac; ffmpeg and ffprobe are at `~/.local/bin`): `file_sha256` equals a whole-file hash; prepare on six generated clips keeps file-name order and the same ids as a serial run, reports count and MB, stores bytes and mtime; a duplicate is listed once; a clip over 200 MB refused; record refuses after a same-size replacement and after a touch, naming the clip; record stores `camera_audio` and the note, and null/empty without the flag; `upload_file` calls the progress callback once per file and `cmd_stage`'s media branch prints `uploaded k/n name (MB)` lines (upload faked); a `Refused` inside the pool surfaces unchanged; the prompt and steps are clean of "library", "UI", "page", "backend", "teammates", "50 videos" and carry `--camera-audio`.
Layer two, `server/tests` (Docker): M2/M4/M5/M6 unchanged; one assertion added: the recorded summary carries `camera_audio` when the flag is given.

## F. Not covered
- server/tests cannot run on this Mac; compile-check only until a Docker machine runs them.
- Real-line upload behaviour is unchanged by this batch; the progress lines are verified with a faked upload.
- Stage 6's use of the recorded sound answer is its own note.

## G. Deploy order
1. Server (`deploy-server.sh`, workers restart): tell SK first.
2. Plugin (`deploy-plugin.sh`); the operator restarts Claude Code.
3. design/35: a row.

## H. Estimate
Plugin with tests: about half a day. Server: half an hour. Deploys: an hour.
