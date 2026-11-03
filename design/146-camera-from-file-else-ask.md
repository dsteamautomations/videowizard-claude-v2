# design/146: the camera is pulled from the file; asked once only when the file has none (3 Nov 2026, SK: "Approve, build it")

**The question SK asked:** VW-18's visuals line said "camera not known". Does Gemini not give the camera because we asked it for a fixed set of fields, and would it if asked?

**The test (two real VW-18 clips, C0032 and C0138, on the server):**
- Gemini receives the decoded pictures and sound only. The file's tags (maker, model, lens, encoder) never reach it. Asked outright, it answered for both clips: make null, model null, source "none", confidence 0. A camera field in the analysis would get guesses or "unknown".
- The files themselves say why: every VW-18 clip was **exported from DaVinci Resolve Studio** (encoder tag), and an export drops the camera's maker tag. The Sony-style names (`C0032_…`) survived. The operator had answered "original but compressed" at media.

So the camera comes from the file when the file has it, and from the person who shot the clips when it does not. Nothing else can supply it.

## What changed

1. **Media prepare** keeps each file's `encoder` tag beside the maker, and prints `camera_unknown_note` when clips carry no maker and their name settles nothing: "No camera information in N clip(s) (exported by DaVinci Resolve Studio): …". The count stays within the prepare answer's size cap, so the list is in the note, not a field.
2. **Media record** refuses without `--shot-on "<their words>"` when such clips exist, like the copies and camera-sound answers. Never asked when the files say it. The answer is recorded on the media output as `shot_on`.
3. **The server's footage measure** (`footage.camera_of`) reads, in this order: the file's maker tag; a file name that names a camera (DJI_, IMG_, PXL_…); **the operator's answer**, classified with the same maker lists (Sony FX3 → cinema camera, Sony A7 → mirrorless, iPhone → phone, DJI → drone; words with no known maker are shown as given); then the unclassified Sony name pattern; then "not known", now saying who exported the file.
4. **The instructions** (v3 media step, `vw.md`) say when to ask and how to record it.

The retired `--camera <class>` flag of design/126 stays refused by name; the new answer is `--shot-on`, free words.

## Older ways (design/35)
- Films past media (VW-16 at its re-run has media recorded; VW-17, VW-18): no answer recorded, so "not known" and the visuals-page correction, as today.

## Tests
- Server: the answer fills a tagless clip; a tag and a camera-naming file name still win; the exporter is named in the evidence; `measure` takes the answer; the line shows it. (`test_footage_pure.py`)
- Plugin: prepare names the clips and the exporter; record refuses without the answer when needed, keeps it, and passes it through `cmd_stage`. (`test_media.py`)

## Not covered
- A wrong answer is taken as given, like the other media answers.
- VW-18 itself: its media is recorded; the camera can still be corrected on the visuals page.
- Not deployed (SK confirms deploys).

## The shoot team's cameras as ready choices (SK, 3 Nov 2026)

SK gave the two cameras the shoot team uses, so nobody types them each time. The media note offers them, and the assistant asks with the question tool: **Raj's footage** (Fujifilm X-T4), **Pandi/DS footage** (Sony FX30, ILME-FX30, with the Tamron 17-70 mm f/2.8 and the Sony E 50 mm f/1.8), or **another camera**. `--shot-on raj` or `--shot-on pandi` records the full words; any other words are recorded as given. The presets live in `plugin/scripts/stages_av.py` (`CAMERA_PRESETS`); a new camera is one line there. The server classifies them as today: the X-T4 a mirrorless camera, the FX30 a cinema camera.
