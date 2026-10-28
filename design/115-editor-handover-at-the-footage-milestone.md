# design/115 — The editor's package at the footage milestone

Status: SK's requirement, restated by the builder on 28 Oct 2026 and confirmed by SK (timing and captions). What exists and what is new are the builder's reading; the questions wait for SK before any code.

## The requirement (SK, 28 Oct 2026)

A run moves through these stages in order: the client name and the script; the brief; the script stage; the voiceover; the media uploaded and analysed; the real footage placed against the narration; the rest marked as gaps and approved; the AI shots; the AI images; the illustrations; and the final cut, where the real footage and the filled gaps become one film.

The point where the voiceover is final and the real footage has been mapped against it, with the gaps marked and approved, is a milestone of its own.

At that milestone the tool produces one exportable package for the real editors: a zip file, offered as a download, a drive link or a storage place. The editors hold the original high-resolution videos; what the tool received are low-resolution copies. The package holds:

1. the voiceover narration, the final accepted one;
2. for every piece of real footage: the video file's name, the exact start and end second to cut in the source file, and its start and end on the final film's timeline;
3. the captions: the narration's words, timed to the final film, in a file DaVinci Resolve imports.

The editors take the package and add the rest themselves.

## What exists today

- The narration: the final accepted voiceover is a stored audio file of the voice stage, with its words timed in film frames (the same timing the plan check and the drawn route use).
- The footage: every placed stretch keeps the uploaded file's name (never renamed), its hash, the source in and out seconds, and its start and end frame on the film; the first cut's own footage is recorded the same way in the first-cut events. The crop, when one was used, is kept too.
- The gaps: the accepted gap records give the film's timeline between the footage.
- The handover of design/107 writes all of this as an FCPXML timeline at the end of the run, for Resolve, with relinking to the originals.

## What is new

- The milestone itself: a named point after the gaps are accepted, recorded on the run, with its own command and page button.
- The package at that point: one zip with the narration audio, a cut list (one row per footage stretch: file name, source in and out in seconds and timecode, film in and out in seconds and timecode, the crop if any), the captions as an SRT file built from the timed narration words, and a short README naming the run, the film's frame rate and length, and the narration file's hash. The gaps appear in the cut list as rows marked "gap: AI picture to come", so the editor sees the whole timeline.
- Delivery: the zip saved under the run's storage and offered as a download link from the page and from `vw`; a drive copy only if SK wants one.

## Questions for SK

1. Cut list form: a CSV (opens in Excel and Resolve's own tools) beside a human-readable text version, or the CSV alone? Recommendation: both; the CSV is the one that is read by a machine.
2. Timecode base: the film's frame rate (25 fps on VW-7) from 00:00:00:00 at the film's start. Recommendation: yes; the frame rate is written in the README.
3. Captions: one SRT line per narration sentence, broken at the recorded pauses, at most two lines of 42 characters each. Recommendation: yes; Resolve imports SRT directly into a subtitle track.
4. Also the FCPXML of design/107 in the zip, cut to the footage and the gaps as empty slots, so the editor can import the timeline rather than retype the cut list? Recommendation: yes, it costs little since design/107 writes it.
5. Where: a download link from the page and `vw` (as design/107's download works), no drive upload in this release. Recommendation: yes.

## Not covered until built

- Nothing is built; this note is the agreement on the words.
