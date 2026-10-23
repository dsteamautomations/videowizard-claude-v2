# design/88 — The footage character is measured, not asked

Status: proposed by Revathi, 23 Oct 2026; approved by SK the same day ("go ahead and build"); built as server 0.33.0, plugin 0.31.0. It replaces the question added by design/77 L42 and keeps that change's purpose: the theme's texture must come from the real footage, never from an assumption.

## Why

design/77 L42 was added because on VW-6 the assistant assumed phone footage when the clips came from a professional cinema camera, and that assumption reached all 44 prompts. The fix was to ask the operator at the media step: camera (cinema, mirrorless, phone or mixed), support (handheld, tripod, gimbal or mixed) and look (natural, graded or log). The answer is used only at visuals (`visuals_stage.footage_character`, in the package and in every packet).

The operator should not have to answer this. Everything it asks is in the files or in the analysis, and by the time visuals starts both are on the server:
- **Camera.** The probe already reads the codec, pixel format, bit rate and colour transfer (`plugin/scripts/stages_av.py`, `probe`). `footage_guess` already turns them into a guess. Cameras and phones also write maker and model tags (for example `com.apple.quicktime.make` and `model`, or Sony and Canon metadata), which the probe does not read yet.
- **Support.** The analysis records each sub-clip's `movement_type` (Static, Pan, Tilt, Dolly, Handheld, Gimbal, Digital_Zoom) and `stabilization_needed` (`clip_log/schema.py`).
- **Look.** The analysis records each clip's `contrast_profile` (Flat_Low_Contrast, Standard_Normal, High_Contrast). The probe's `color_transfer` shows log or HLG curves.

The question also comes at the wrong time: at media, before analysis, though it is used only at visuals, after analysis.

## Changes

| # | What changes | Where |
|---|---|---|
| F1 | The probe also reads the maker and model tags from the format and stream tags, when present. The media record's per-clip summary keeps `codec`, `pix_fmt`, `bit_rate`, `make` and `model` beside the fields it already keeps (`color_transfer` is there today). | `plugin/scripts/stages_av.py` (`probe`, `record` summary) |
| F2 | A server function `measured_footage(outputs, analyses)` works out, **per clip**: `camera` (from make and model when present, else from codec, bit depth and bit rate, using `footage_guess`'s rule), `support` (the commonest `movement_type` of its sub-clips: Static, Pan or Tilt counts as tripod; Handheld counts as handheld; Gimbal or Dolly counts as gimbal; `stabilization_needed` counts toward handheld), and `look` (log when `color_transfer` names a log or HLG curve or the contrast is Flat_Low_Contrast; else natural; graded only when a clip carries a grading tag or the operator says so). Each value carries its evidence in a few words. It also gives a film summary: the most common value of each, or `mixed` with the counts. | `visuals_stage` (new function) |
| F3 | `visuals prepare` puts the measured footage character in the package, film summary and per-clip map, in place of the operator's answer. Each packet carries the character of the **neighbouring clips** of its gap (the clip before and the clip after in the first cut), not only the film summary, so a shot matches what sits beside it (the library's `video/gap-fill.md`). | `visuals_stage.prepare`, `packet`, `packet_context` |
| F4 | The operator is **told, not asked**. Prepare's answer and the visuals page show one line, for example "Your footage: cinema camera (Sony, 10-bit), mostly handheld, flat log look", with a "Correct this" control. A correction is stored with the operator's words and wins over the measurement for the rest of the run, on both front ends. | `visuals_stage`, `vw.py`, `templates/visuals.html` |
| F5 | The media step drops the question. `--camera`, `--support`, `--look` and the note flag stay accepted for one release and are stored as a correction if given, so an operator mid-run is not refused. The media steps in `v2.json` and `vw.md` lose the sentence. | `server/procedures/v2.json`, `plugin/commands/vw.md`, `vw.py` |
| F6 | A run recorded before this release (whose media summary lacks the new fields) gets what can be measured from what it has (`color_transfer`, the analysis), and its recorded answer, if any, stands as the correction. | `measured_footage` |
| — | Server and plugin versions bumped. | |

## Not changed

The visuals prompt's rule that the theme's texture comes from the footage character, how the character is used in the packet, and the camera-sound question at media (that one is a permission, not a measurement, and stays).

## Tests first

- The probe reads make and model from an iPhone-style and a Sony-style tag set, and gives none for a file without them.
- `measured_footage`: a ProRes 10-bit clip with a log transfer and mostly Handheld sub-clips gives cinema, handheld, log; an iPhone HEVC clip with Static sub-clips and a normal contrast gives phone, tripod, natural; three clips of two kinds give `mixed` with counts; a clip with no analysis yet gives camera and look from the probe and support `unknown`.
- The packet carries the neighbours' character for a gap between two different clips.
- A correction with words wins over the measurement on both front ends, and an old run's recorded answer stands as the correction.
- The media record works with and without the old flags, and the steps no longer name them.

## Not covered

- server/tests (Docker).
- Maker and model tags differ by camera brand and are sometimes stripped by editing or transfer apps. The codec, bit depth and bit rate rule is the fallback, and the operator's correction is the backstop.
- "Graded" cannot be reliably told apart from "natural" by measurement. It is reported only from a tag or a correction.
- How well Gemini's `movement_type` matches the real support on short clips. VW-6's clips are the first check against what SK knows of them.

## Builder's notes (23 Oct, at the build)

- **The file name is a second clue**, before the codec rule: VW-7's clips carried no maker tags (`C0…` from a Sony, `DJI_…` from a drone) and the old rule called 1080p h264 at 22 Mbit/s phone footage. The order is now maker and model tags, then the file name, then codec, bit depth and bit rate. A Sony XAVC brand or a DJI or GoPro encoder tag names the maker when the make tag is missing.
- **`drone` is a camera value** (the correction offers it too): a DJI clip is neither a phone nor a mirrorless, and with no analysis yet its support is gimbal.
- **The film summary** takes the value two thirds of the clips share, else `mixed` with the counts; unknowns do not vote.
- **The neighbours** come from the master plan's events: the clip just before and just after each gap (a sub-clip id is `clip:sub`). A run without a master (procedure version 1) has none.
- **A fix to design/86 in the same release.** The packet's digest, which `select-take` compares, included design/86's `context` (earlier rejections among it): rejecting any picture of an element would have made its prepared takes unselectable. The digest now leaves out `context` and `footage_character`; they inform the writer and never make a prepared take stale. Takes prepared under 0.32.0 (none known) would need preparing again.
- The code is `server/app/footage.py` (pure, `test_footage_pure.py`), `visuals_stage.prepare`, `gap_neighbours`, `footage_view`, `correct_footage`, the route `POST /visuals/footage`, the page's act `footage`, `vw visuals footage`.
