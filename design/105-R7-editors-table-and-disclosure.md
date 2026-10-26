# design/105 — Release 7: the editor's table and the AI-shot disclosure (course E-a, E-b, E-c)

26 Oct 2026. Course handover batch E and `course-review/editor-table-notes.md`, as planned for Release 7. **Nothing is built until SK approves this note.**

## 1. How it stays simple and breaks nothing

- **Delivery only.** Everything here is written into the delivery bundle, from data the server already holds. The film, the assembly and the takes are not touched.
- **The colour match (E-a) is a note, not a grade, in this release.** The handover asks for a small ffmpeg correction of each AI segment at assembly. That changes the rendered film, and its amounts can't be tuned before a film has the measurements. So this release writes the measured difference into the editor's table, where the editor grades by eye (rule E7). The automatic correction comes later, once a delivered film shows the numbers. This is the same order C3's detail check followed.
- **Nothing is applied automatically.** The editor decides (the editor-table notes say the same).

## 2. What changes

**The AI-shot disclosure (E-c).** The bundle gains `AI-shots.md`.
- It lists every AI shot in the film with its timecode and kind: AI video, AI still, or graphic. Drawn graphics are listed apart.
- It closes with: "When uploading, tick the platform's AI-generated or altered-content option."
- OPEN-EDIT points to it.

**The editor's table (E-b).** The finishing checklist gains an "Editor's table" section.
- Each line is `[timecode] [shot] what to do (why, rule)`.
- The lines are grouped by kind: look, sound, text, finishing.
- The data-ready rules come first, as the notes order them. The rules the checks already feed come next.

| Rule | Trigger, from data the server has | The line |
|---|---|---|
| E5 Layered sound | every AI video and AI still in the film (they are silent) | "layer sound under it: near, middle, far, from what the scene shows" (with the scene's ambient line when it has one) |
| E6 Text in the edit | an AI video shot whose narration names a number (digits or a percent) | "'{the number}' is spoken over a video shot: overlay it in the edit; it is not drawn in the take" |
| E7 Colour (the E-a note) | the picture's measured light line (N9) failed | "{brighter/warmer/… by …} than the footage beside it: match the grade by eye" |
| E8 Grain | the picture's fine-detail line (design/104 C3) failed | "{ratio} of the footage's fine detail: add fine grain to match" |
| E10 Paint-out | an approved picture whose "nothing extra" line failed | "the check saw: {what it saw}: paint it out if it distracts" |
| E11 Upscale | the film has AI takes (720p) and the film is larger | "N AI takes are 720p: use Resolve's Super Scale 2× on them before the final render" (once) |
| E13 Music beats | always, once | "If music is added, move cuts within ±4 frames of a beat where the narration allows" |
| E15 End card | always, once | "End card: place the client's own logo file (never drawn by AI)" |
| E16 AI label | the film has an AI video or an AI still | "Upload with the AI label: see AI-shots.md" (once) |
| E17 Social export | the brief's frame is 9:16, or it names a social platform | "For Reels or TikTok: export 1080p 30 fps, not 4K 60 fps" (once) |

## 3. Left out, and why

- **E-a's automatic grade:** see section 1. The note (E7) comes first.
- **E1 shake on impact, E2 fade at chapter changes, E3 speed ramp, E4 pace by trimming, E12 cutaways over a speaker, E14 reverse a clip.** These need new readings of the plan: the beat's verb, the chapters, the spare take length against the narration's pace, jump cuts inside a speaker clip. The notes put them second. They get their own short note after the first delivered film shows whether the editor uses the table.
- **E9 handheld wobble.** It needs a probe of how steady a take came out. Not built.

## 4. Tests first

- **E-c:**
  - a film with an AI video, an AI still, a graphic sequence and footage lists the three AI shots with their timecodes and kinds, and the footage is left out;
  - the upload line is there;
  - OPEN-EDIT points to the file.
- **E-b:**
  - each rule writes its line when its trigger is present, and stays silent when it isn't (E5, E6, E7, E8, E10, E11, E16, E17);
  - E13 and E15 appear once;
  - the lines are grouped by kind with timecodes.
- **The rest:** a film with no AI shot gets no AI-shot list and no AI lines, and the bundle's other files are unchanged.
- **Suites:** `server/unit` and `plugin/tests`. The plugin doesn't change.

## 5. Not covered

- Whether editors use the table. The first delivered film is the test, and lines the editor ignores get dropped (the notes).
- `server/tests` (Docker).

## 6. Release

Server 0.52.0 (on 0.51.0). Not committed or deployed until SK says so.

## As built (26 Oct 2026)

Server 0.52.0 (on 0.51.0), plugin unchanged. Not committed or deployed.

**`stage3/delivery.py`:**
- `ai_kind` and `ai_shots` (with `ai_shots_md`) write `AI-shots.md` when the film has AI shots. Footage frames, client files and web photos held as stills are not AI.
- `editors_table` and `editors_table_md` cover E5, E6, E7, E8, E10, E11, E13, E15, E16 and E17. They are appended to `Finishing-checklist.md` as the "Editor's table" section, and to the JSON with `section: editor`.
- `visuals_info` reads each shot's narration, ambient line, placed picture and its check lines. It is empty when the run has no visuals.
- OPEN-EDIT gains point 4 (the table), and point 5 (AI-shots.md) when there are AI shots.

**Tests:** `server/unit` 446 passed, 5 of them new in `test_design105_pure.py`, and the older bundle tests pass unchanged. `plugin/tests` 267 passed, with the 3 known Windows-only failures.

**Not covered, added:** no live run has reached assembly yet, so the bundle hasn't been made on a real film with these sections. The first delivered film is the check.
