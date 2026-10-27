# 107 — Handing the film to the editor: a timeline file, a checked download, and relinking to the originals

Requested by Revathi, 26 Oct 2026. For SK.
The operator's own PC runs Resolve Studio, so Step F's Studio route is the one used day to day. The free route is still built, because an editor's PC may run free Resolve.
The editor's original file names will be similar to the copies' names, not always identical. §6 handles that.
Numbered after the repo at server 0.52.0 (design/101–105) and note 106.
Keeps everything design/105 adds to the bundle (AI-shots.md, the Editor's table, OPEN-EDIT points 4 and 5).
Reverses two earlier decisions: "No FCPXML round trip" (design/16 §2) and "the Resolve step is driven by scripting on the Mac" (design/16 §1, design/17 §3, design/47 12.1).
Every item in this note is required. None is optional.
Every rule here is generic. It must work for any run, any client, any camera and any length of film.

---

## 1. Why this note

What is built today:
- The server renders the whole film with FFmpeg (design/46). The operator watches, listens and approves. This stays as it is.
- The server writes a bundle with a manifest (design/16, 47). This stays, with the changes below.
- `vw delivery resolve` then drives Resolve by scripting to place every clip and export a .drt (`plugin/scripts/resolve_bridge.py`).

Why the Resolve step has to change:
- Resolve 21.1 removed scripting from the free version. Blackmagic's notes say: "We have moved the ability to script in Python to the Studio version." ([Puget Systems, 10 Sep 2026](https://www.pugetsystems.com/blog/2026/09/10/how-davinci-resolve-free-v21-1-scripting-changes-affect-puget-bench/))
- So the step fails on any PC that runs free Resolve 21.1, which covers most editors.
- The step has never been run against real Resolve (design/47 12.1).
- It is written for a Mac. The operator's PC runs Windows.

The second problem: the editor gave the operator compressed copies of the camera files.
- VideoWizard analysed and cut those copies.
- The editor must finish on the full-quality originals.
- The editor must not have to find and cut the same moments again by hand.

---

## 2. The idea in one paragraph

The server writes the edit as a **timeline file** (FCPXML) that any editor can import into Resolve, free or Studio.
The file says, for every cut, "this file, from this frame to this frame, at this place in the film".
It does not hold the picture.
So the editor can point the timeline at the full-quality originals (Resolve's **Relink**), and every cut moves to the originals by itself.
For that to work, VideoWizard must record each camera file's name, length, frame rate and timecode at the media stage, and check them again before handover.

---

## 3. The operator's flow, step by step

### Step A — The film is approved (unchanged)
- The FFmpeg film is rendered, watched, listened to and approved, as today (design/46).

### Step B — A confirm before any download
- The delivery step opens with this message:
  "Please make sure this computer has DaVinci Resolve installed. Without it, the downloaded files cannot be opened as an edit."
- It has one button: "Resolve is installed — download the edit".
- Before the download starts, the plugin checks the PC:
  - Is Resolve installed? Which version?
  - Is it Studio or free?
  - Is there enough free disk space for the whole bundle (sizes from the manifest)?
- The answer is shown in plain words. Examples:
  - "Resolve 21.1 Studio found. 3.2 GB needed, 140 GB free."
  - "Resolve 21.1 (free) found. The edit will open by one import step, shown at the end."
  - "Resolve not found. Install it, then press the button again." (The download does not start.)
- The check works on Windows and on Mac. Paths, install locations and the version read are written for both.

### Step C — Download into one folder
- The bundle downloads into `runs/VW-n/edit/` in the operator folder.
- Three files at a time, one progress line per file (design/47 12.4, kept).
- The folder layout is fixed for every run (see §4).

### Step D — Count and cross-check
After the download, the plugin checks everything and shows one report before going further:
- Every file in the manifest is present. The count matches ("142 of 142 files").
- Every file's size and fingerprint (sha256) match the manifest.
- The voiceover is present and is byte-identical to the approved voiceover (design/16 D7).
- Every cut in the timeline points at a file that is in the folder. None is missing.
- The timeline's total length equals the approved film's length, to the frame.
- The number of cuts equals the approved film's number of cuts.
- Any failure names the file or the cut, and stops here. Running the step again downloads only what is missing or wrong.

### Step E — Write the timeline with this computer's paths
- An FCPXML file needs the full path of each file on the computer that opens it.
- So the server sends the timeline with folder-relative paths, and the plugin writes the final FCPXML after the download, with the real paths of `runs/VW-n/edit/`.
- Windows paths and Mac paths are both handled (drive letters, spaces, non-English characters in names).

### Step F — Open it in Resolve
Two routes, chosen by what Step B found. Both are built.
- **Resolve Studio found:** the plugin opens Resolve, creates a project named after the run, imports the FCPXML, and saves the project. It exports a Resolve project file (.drp) and a timeline file (.drt) into `Timeline/`. It reads the timeline back and compares it with the plan, cut by cut (design/17 A47, kept: tolerance 0 frames).
- **Free Resolve found:** the plugin shows three short steps: open Resolve, make a new project, File > Import > Timeline and pick `Timeline/<run>.fcpxml`. Then it asks the operator to play the start, the middle and the end next to the approved film, and confirm they match (see the reference track in §5).

### Step G — Hand over
- The plugin zips `runs/VW-n/edit/` into one file for the editor, with `OPEN-EDIT.md` on top.
- The final approval (design/17 A42) changes its "timeline verified" point to: "the timeline matched the film" (Studio: by the readback; free: by the operator's check in Step F).

---

## 4. What the editor gets (fixed layout, every run)

```
VW-n-edit/
  OPEN-EDIT.md                 how to open it and how to relink (plain steps)
  Approved-film.mp4            the film the operator approved
  Timeline/
    VW-n.fcpxml                the edit, for Resolve, Premiere or Final Cut
    VW-n.edl                   the same cuts as a plain list (file, timecode in/out)
    VW-n.drp, VW-n.drt         only when Step F ran on Resolve Studio
  Media/
    Camera/                    the camera files as uploaded (the compressed copies)
    AI/                        the AI videos and stills, final quality
    Voiceover/                 the approved voiceover
  Subtitles.srt
  Finishing-checklist.md       includes the Editor's table (design/105)
  AI-shots.md                  the AI-shot list for the upload label (design/105), when the film has AI shots
  Relink-list.csv              one line per camera file (see §6)
  manifest.json                every file with size and fingerprint
```

Notes:
- The AI files and the voiceover are made by VideoWizard. The bundle holds the only copy of each, so they never need relinking. (AI takes are 720p; the Editor's table already tells the editor to upscale them, design/105 E11.)
- Only `Media/Camera/` gets swapped for the originals.
- The EDL is there so a person can read the cut list. It also gives a second way in if an FCPXML import ever fails.

---

## 5. What the timeline file must contain

- Video track 1: every camera cut and every AI clip, at its exact frame.
- Each camera cut carries the file name, the source in and out (as timecode, using the file's own start timecode), the zoom, position and rotation the solver chose (design/17 A13).
- Zoom and position are written relative to the frame (scale to fit), not in pixels. Then they stay right when a 720p copy is swapped for a 4K original.
- AI stills are placed as stills held for their slot length.
- Audio track 1: the voiceover, unchanged.
- Audio track 2: the nat-sound pieces, with their levels and 4-frame fades written in the file. The checklist still lists them, in case an editor's import drops them.
- Audio tracks 3 and 4: present and empty, with their names (design/17 C7).
- A top video track named "REFERENCE – approved film", holding `Approved-film.mp4`, switched off. The editor turns it on to compare any moment with what was approved.
- Markers: one per cut (shot id, option), one per finishing item, one per sound-effect cue (design/16, kept).
- Clip colours for colour groups (design/17 A14, kept).
- The timeline's frame rate and size match the approved film.

The checks in Step D and the readback in Step F compare this file with the assembly plan. A timeline that differs from the film in any cut is refused, naming the cut.

---

## 6. Relinking to the full-quality originals

### What VideoWizard records at the media stage (new)
For every camera file the operator uploads, the media stage records:
- file name (with and without extension)
- length in frames
- frame rate
- width and height
- start timecode, from the file's metadata (empty when the file has none)
- reel or tape name, from the metadata (empty when absent)
- the camera's original file name, when the metadata carries one

This goes into `Relink-list.csv` and the manifest. The timeline uses the same names and timecode.

### What the editor does (written in OPEN-EDIT.md, in plain steps)
1. Open the timeline as in Step F. It plays with the compressed copies.
2. In the Media Pool, select the camera clips, right-click, Relink, and pick the folder that holds the originals.
3. Resolve matches by file name and timecode. Every cut moves to the original. When the originals' names differ from the copies', import `Timeline/VW-n-relinked.fcpxml` from the relink check instead; it already points at the originals.
4. Turn on the reference track and spot-check a few cuts.
5. In Project Settings, set "Mismatched resolution files" to "Scale entire image to fit", so zoom and position stay right on the larger originals.

### The relink check (new command)
Before the editor relinks, anyone with the originals folder runs:
`vw delivery relink-check --run VW-n --originals "<folder>"`
It reads each original with the same probe the media stage uses, and compares it with `Relink-list.csv`. It prints one line per camera file:
- "C0120: name, length, frame rate and timecode match. Relinks as is."
- "C0120: the copy has no timecode; the original starts at 14:23:10:05. A corrected timeline is written."
- "C0120: the copy is 312 frames shorter than the original. This clip must be lined up by hand (cuts listed below)."
- "C0120: no original with this name. Look for a renamed file."

What it does with each case:
- **Everything matches:** nothing to do.
- **Timecode differs, length and frame rate match** (the copy was re-encoded and lost or reset its timecode): it writes `Timeline/VW-n-relinked.fcpxml`, with each cut's source in and out moved to the original's timecode. The editor imports that one instead.
- **Extension differs** (copy .mp4, original .MOV): it writes the relinked timeline pointing at the original's real name.
- **Length or frame rate differs** (the copy was trimmed or converted): it names the clip, and lists every cut that uses it with the time inside the clip and a frame grab, so the editor finds the moment in seconds. It also adds these to the finishing checklist.
- **Name similar, not identical** (for example `C0120.mp4` and `C0120.MOV`, `C0120_proxy.mp4` and `C0120.MXF`, or `A001_C012_0315XY.mov` and `A001C012_0315XY_001.mov`): it matches by the name with case, extension and common copy endings such as `_proxy`, `_lowres`, `_compressed`, `-1`, `(1)` removed, and then confirms the match by length, frame rate and timecode. A confirmed match is listed as "copy C0120_proxy.mp4 = original C0120.MXF (length, frame rate, timecode agree)". When one copy matches two originals, or a name match fails the length check, it lists the candidates and asks the operator to pick; it never guesses. It then writes the relinked timeline pointing at the originals' real names, so the editor does not rely on Resolve's own name matching.
- **No original found:** it names the clip and says which cuts use it.

### Prevent the problem on future runs (new)
- At the media stage, after the upload, the step asks once: "Are these the camera originals, or copies made by an editor?"
- When the answer is "copies", it records that, and the delivery step reminds the operator to get the originals' folder or the relink check before handover.
- When copies have no timecode, or a frame rate different from the run's footage, the media stage says so at upload, naming the files. A good copy keeps the original's name, length, frame rate and timecode. The step text says this to the operator in one line, so they can ask the editor for copies like that.

---

## 7. What is removed or changed in the current build

- `vw delivery resolve` as the only route: replaced by Steps B to F. The Resolve scripting code (`resolve_bridge.py`) is kept only for the Studio route in Step F, and changes from "append clips one by one" to "import the FCPXML, then read back".
- design/16 "No FCPXML round trip": reversed. FCPXML is now the main handover.
- "On the Mac" wording in steps, `bundle()`'s next line and OPEN-EDIT: replaced by "on the operator's computer (Windows or Mac)".
- `vw pull`'s default folder `~/VideoWizard/runs/VW-n`: replaced by the operator folder's `runs/VW-n/edit/`.
- The bundle's folder names (`Media/Originals`, `Media/Normalised`): renamed to `Media/Camera`, `Media/AI` as in §4.
- Final approval's "DRT verified" point: becomes "the timeline matched the film" (§3 Step G).

---

## 8. Edge cases

| Case | Expected |
|---|---|
| No Resolve on the PC | Step B stops before any download, says "Resolve not found" |
| Free Resolve 21.1 | Steps C–E run; Step F shows the import steps and the side-by-side check |
| Resolve Studio | Step F imports, saves .drp and .drt, reads back, 0 frames tolerance |
| Not enough disk space | Step B stops, shows needed and free space |
| One file's fingerprint differs after download | Step D names it, downloads it again on the next run |
| A cut points at a file not in the bundle | Step D names the cut and stops |
| Timeline length differs from the film by 1 frame | Step D refuses, names the first cut that differs |
| Run folder path with spaces or Tamil/Hindi characters | FCPXML paths encoded correctly; Resolve finds every file |
| Camera copies all relink as is | relink check: all lines "match" |
| Copies lost their timecode | relink check writes the corrected timeline |
| One copy trimmed at the start | relink check names it, lists its cuts with times and frame grabs, adds them to the checklist |
| Original is 4K, copy 720p | cuts land at the same frames; zoom and position correct with "scale entire image to fit" |
| Original .MOV, copy .mp4 | relinked timeline points at the .MOV |
| Copy `C0120_proxy.mp4`, original `C0120.MXF`, length and timecode agree | matched and listed; relinked timeline points at `C0120.MXF` |
| One copy name fits two originals | both listed; the operator picks; nothing written until then |
| Name matches but length differs | not matched by name alone; listed as trimmed or wrong file |
| An AI still in a slot | held for the slot length in the timeline |
| Same camera file used in five cuts | one line in Relink-list.csv; five cuts move together on relink |

---

## 9. Tests

Written first.
- FCPXML writer: from a plan with camera cuts, AI clips, stills, nat sound and markers, the file imports and reads back with the same cuts (a pure parser of our own FCPXML, plus one Resolve import by hand).
- Paths: Windows and Mac paths, spaces, non-English names.
- Step D checks: missing file, wrong fingerprint, cut pointing nowhere, length off by one frame.
- Relink check: a fake originals folder for each case in §6 (match, no timecode, different extension, trimmed, missing).
- Media stage: timecode, reel and frame rate recorded for a file with metadata and for one without.

By hand, before first use, on the operator's Windows PC:
- One real run's edit opened in free Resolve 21.1 by import, and in Resolve Studio by the plugin.
- The relink done with a folder of originals for at least two camera files.

---

## 10. For the builder (prompt)

Build design/107. Read it with design/16, 17, 46, 47 and 105; where they differ, 107 wins. Keep every file and section design/105 adds to the bundle. Keep the FFmpeg film and its approval exactly as they are. Replace the scripting-only Resolve step with: the confirm and PC check (Windows and Mac), the download into `runs/VW-n/edit/`, the count and cross-check, the FCPXML written with this computer's paths, the two open routes (Studio by the plugin with readback; free by import with the side-by-side check), and the zip for the editor in the fixed layout of §4. Add the media-stage metadata record, `Relink-list.csv`, and `vw delivery relink-check` with all five outcomes in §6. Every item is required. Write the tests in §9 first. Report what you could not test.

---

## Builder's reading (27 Oct 2026), for SK's approval before any code

**Checked against the code at main 67e1590 (server 0.54.0, plugin 0.48.0).** Nothing here is built.

### What exists that 107 builds on
- `delivery.resolve_events` already gives every cut as file, source in/out, record in/out, zoom, pan, tilt, rotation, colour group, marker and nat-sound intervals. The FCPXML and the EDL are written from it.
- `delivery.bundle` writes the manifest, the SRT, the finishing checklist (with design/105's Editor's table), `AI-shots.md` and OPEN-EDIT. The layout changes as §4 says; the contents stay.
- The plugin's media probe records per clip: name, length, frame rate, width, height, rotation, codec, bit rate. It does **not** record the start timecode, the reel name or the camera's original file name (§6 adds them; ffprobe gives `tags.timecode` and `reel_name` when the file has them).
- `resolve_bridge.py` (194 lines) drives Resolve by scripting, append by append. It becomes the Studio route only: import the FCPXML, save, export, read back.
- Downloads: design/108's `_download` (streamed, parallel, verified) is what Step C uses.
- No run has reached delivery on this server yet, so nothing here can be tried on a real film until one does.

### How big it is, and the order
107 is three releases' worth of work. I propose to build it in three slices, each with its own tests first, its own diff shown, its own commit on SK's word, and no deploy until SK says so:

| Slice | What | Where | Testable here? |
|---|---|---|---|
| **1. The files** | The FCPXML writer (§5: video track with every cut, stills held, transform relative to the frame, A1 voiceover, A2 nat sound with levels and fades, A3 and A4 empty and named, the reference track switched off, markers, colour groups, the film's frame rate and size), the EDL, `Relink-list.csv` from the media summary, the new bundle layout (§4) with folder-relative paths, OPEN-EDIT rewritten for the new flow (relink steps, "on the operator's computer"). The manifest keeps `resolve_events`. | server | Yes: a pure parser of our own FCPXML, every §9 case for the writer |
| **2. The operator's PC** | Step B (the confirm; Resolve found or not, Studio or free, version, free disk, Windows and Mac), Step C (download into `runs/VW-n/edit/`), Step D (count, fingerprints, voiceover identical, every cut points at a present file, length and cut count equal the film), Step E (the FCPXML rewritten with this PC's paths; spaces and non-English names), the free route's three steps and side-by-side check, Step G (the zip). `vw pull`'s folder. | plugin | Yes, with a fake PC; the real Resolve detection only on a PC that has Resolve |
| **3. Studio, relink, the media stage** | Step F's Studio route (import the FCPXML by scripting, save, export .drp and .drt, read back at 0 frames), the media stage's timecode, reel and original name, the "originals or copies?" question and the copies warning, `vw delivery relink-check` with the five outcomes of §6 and `VW-n-relinked.fcpxml`, the final approval's wording. | plugin and server | Relink check yes (a fake originals folder); the Studio route only on Revathi's PC |

### What I cannot test here
- **This PC has no Resolve** (checked: nothing under Program Files or ProgramData). The two by-hand tests of §9 (a real edit opened in free Resolve by import, and in Studio by the plugin; a relink with two originals) are Revathi's, on her PC, after slice 2 and slice 3.
- A real film through delivery: no run has reached it.

### Two things 107 asks for that import will only partly honour
- **Clip colours and the nat-sound fades.** Resolve's FCPXML import keeps clips, cuts, transforms, markers and audio levels well; clip colours and 4-frame audio fades are kept inconsistently across versions. Both are written, and the checklist keeps listing them (107 §5 already says so for the fades). The editor may have to redo the colours by hand.
- **Transform on relink to a larger original.** Written relative to the frame as §5 says; it also needs the editor's Project Setting "scale entire image to fit" (§6 step 5), which a file cannot set.

### One point to decide later, not now
- Step B stops the download when Resolve is not found. On a PC that only collects the files for an editor elsewhere, that blocks the handover. Revathi's PC has Studio, so it does not arise today; if it ever does, one flag (`--no-resolve`) would allow the download with the free route's text. Not built unless SK asks.

### Slice 1 as built (27 Oct 2026)

Server 0.55.0, plugin unchanged. Not committed or deployed.

- **`stage3/timeline.py` (new):**
  - `fcpxml()`: FCPXML 1.9. One format per frame rate (the film's, and each camera file's own), one asset per file with a folder-relative `file://./` link, one gap the length of the film as the primary story, every cut connected on lane 1 at its film frame with its source start in the file's own time, `adjust-transform` (scale, position, rotation, relative to the frame) only where the cut has one, the voiceover on lane -1 (role dialogue.voiceover), each nat-sound interval on lane -2 in its place (role effects.nat-sound), the approved film on lane 2 switched off as "REFERENCE – approved film", a marker per cut (with its colour group in the note), per finishing item and per sound cue; the film's size and rate.
  - `read_fcpxml()`, `timeline_frames()`, `differences()`: our reader, frame for frame, for Step D's cross-check and Step F's readback (0 frames tolerance).
  - `with_base()`: the folder-relative links rewritten with a computer's path (Windows drive letters, Mac paths, spaces and other scripts encoded), for Step E.
  - `edl()`: CMX 3600, source and record timecodes at the film's rate, `FROM CLIP NAME` per cut.
  - `relink_csv()`: one line per camera file the film uses: name, stem, extension, frames, fps, width, height, duration, start timecode, reel, original name (the last three empty until slice 3 records them), sha256, bytes, cuts.
- **`stage3/delivery.py`:**
  - `layout()`: `Media/Camera/`, `Media/Camera/Stabilised/`, `Media/AI/`, `Media/Voiceover/`, `Timeline/`, as §4.
  - `resolve_events` names files by the layout, carries each cut's `kind` (camera, movie, still) and `clip_id`, and names a still's real file (`.png`, not `.mp4`).
  - The bundle writes `Timeline/VW-n.fcpxml`, `Timeline/VW-n.edl` and `Relink-list.csv`; the manifest adds `timeline_file`, `film_frames` and `cuts` for Step D. Its contract is `vw2-delivery-bundle-v2`.
  - OPEN-EDIT rewritten: open by import, the reference track, the EDL, the checklist and the Editor's table, the AI-shot list, then relink in four steps; "on the operator's computer, Windows or Mac".
- **Not honoured by the file itself, listed in the checklist as before:** empty named A3 and A4 (FCPXML has no empty tracks; the Studio route adds them in slice 3), clip colours (in the marker notes), the nat-sound levels and 4-frame fades (the render sets them; the file places the pieces).
- **Known until slice 3:** the old `vw delivery resolve --run` reads `Audio/narration.mp3` from the bundle, which is now `Media/Voiceover/narration.mp3`; that step was never run against Resolve and is replaced by slices 2 and 3.
- **Tests:** `server/unit` 481 passed, 11 of them new in `test_design107_s1_pure.py`.
- **Not covered:** a real film through the bundle (no run has reached delivery); an import into Resolve by hand (Revathi's PC, after slice 2).
