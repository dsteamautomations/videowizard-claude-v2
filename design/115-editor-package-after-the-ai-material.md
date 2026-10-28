# design/115 — The editor's package once the AI material exists

Status: SK's requirement, restated by the builder and corrected on 28 Oct 2026 after SK's second instruction moved the milestone: it comes after the AI videos and images are generated, not after the footage mapping. What exists and what is new are the builder's reading; the questions wait for SK before any code.

## The requirement (SK, 28 Oct 2026)

A run moves through these stages in order: the client name and the script; the brief; the script stage; the voiceover; the media uploaded and analysed; the real footage placed against the narration; the rest marked as gaps and approved; the AI shots; the AI images; the illustrations; and the final cut, where the real footage and the filled gaps become one film.

**The milestone** is the point where the AI material exists: every gap has its selected asset (an AI take, an AI still, a drawn graphic or a stretch of footage), the voiceover is final, and the real footage is mapped. It comes before the server assembles the final cut.

**At that milestone** the tool offers one exportable package, a zip, downloaded to a Mac that runs DaVinci Resolve Studio. The editors hold the original high-resolution camera files; the tool holds low-resolution copies. The package holds:

1. the voiceover narration, the final accepted one;
2. for every piece of real footage: the camera file's name, the exact start and end second to cut in the source file, and its start and end on the final film's timeline; the low-resolution copies themselves are not needed, since Resolve cuts the originals from these times;
3. the AI videos that were generated, the AI images where they are used, and anything the tool generates later (a VFX file, for example);
4. the captions: the narration's words, timed to the final film, in a file Resolve imports;
5. one file that tells Resolve where every clip sits, so that Resolve places everything on the timeline by itself: the camera cuts on the originals, the AI files in their slots, the voiceover on its track, the captions on a subtitle track.

The editors take the package, add the VFX, and finish on the originals. The server's own assembly of the film stays as the operator's proof copy and for the checks; it is no longer the deliverable.

## What exists today (design/107, slices 1–3, live)

- The bundle: `Media/Camera/`, `Media/AI/`, `Media/Voiceover/`, `Timeline/` with the FCPXML and an EDL, `Relink-list.csv` (name, hash, frame rate, timecode, original name per camera file), `OPEN-EDIT.md`, the manifest; written after the film is assembled and approved.
- The Studio route: `vw delivery open` opens Resolve, creates the project, imports the timeline, saves `.drp` and `.drt`, reads the timeline back frame for frame. The free route imports by hand.
- The relink check: `vw delivery relink-check --originals "<folder>"` compares every camera file with the originals: match, renamed, timecode moved (a relinked timeline is written), trimmed or another rate (listed with frame grabs), two candidates (asks), missing.
- The media stage records timecode, reel and original name per copy, warns on a copy without timecode or at another rate, and asks once "originals or copies".
- Every placed stretch of footage keeps the file name, source in and out, film in and out, crop; the narration's words are timed in film frames.

## What is new

| # | Change |
|---|---|
| H1 | **The trigger.** The bundle is available as soon as every shot of every accepted gap has its selected asset (the takes selected, the stills placed, the sequences and drawings approved), before the server's assembly and the final approval. The final approval keeps its own place after the proof copy. |
| H2 | **No proxies.** `vw delivery download --no-camera` leaves `Media/Camera/` out: the timeline, the relink list, the narration, the AI files, the captions and the README travel; the camera cuts link to the originals at the relink. |
| H3 | **Captions.** `Timeline/VW-n.srt` from the timed narration words: one cue per sentence, broken at the recorded pauses, at most two lines of 42 characters; and a subtitle track in the FCPXML that names the same cues. |
| H4 | **One step on Studio.** `vw delivery open --originals "<folder>"` runs the relink check and imports the relinked timeline, so Resolve opens with the camera cuts on the originals. |
| H5 | **The cut list for people.** `Timeline/Cut-list.csv`: one row per camera cut: file, source in and out (seconds and timecode), film in and out (seconds and timecode), crop; the gaps' AI files as rows too, so the whole film reads top to bottom. |
| H6 | **VFX, later.** A shot field `vfx` with a note; a VFX track in the FCPXML with a marker at each such shot; `Media/VFX/` in the layout for files when they exist. Not in this release unless SK says so. |

## Questions for SK

1. H1: "every shot placed" is the trigger; a run with one gap still open gets the bundle refused with the open shots named. Recommendation: yes.
2. H2: `--no-camera` as the default on the operator's PC, the camera copies only on request. Recommendation: yes; the copies are low resolution and the editor has the originals.
3. H3: SRT with the cue rule above. Recommendation: yes; Resolve imports SRT directly.
4. H4: the relink inside `vw delivery open` on Studio. Recommendation: yes.
5. H6 now or later. Recommendation: later, when the first VFX shot is planned.

## The test

Not VW-3 or VW-4: neither has AI material. VW-9 reached the first cut; filling its gaps with stills cut from its own footage frames costs nothing and gives a run where every shot is placed, so the bundle, the download, the Studio import, the readback and the relink against a folder of originals can all be exercised on Revathi's Mac before VW-7 reaches this point. VW-7 is the first real test once its takes are selected.

## Not covered until built

- Nothing is built; this note is the agreement on the words.

## SK's answers (28 Oct 2026)

"Proceed": the five recommendations stand. 1. The trigger is every shot placed; an open shot refuses the bundle by name. 2. `--no-camera` is the default on the operator's PC. 3. SRT with the cue rule. 4. The relink inside `vw delivery open` on Studio. 5. VFX later. Regular lane: tests first, full suites, deploy on SK's word; the test run is decided after the build.
