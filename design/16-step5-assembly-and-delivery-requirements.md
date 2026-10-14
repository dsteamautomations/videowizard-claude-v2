# 16 — Step 5: assembly and delivery (Resolve once, at the end) — requirement list for SK's approval

Sources: slice 6 walk-through (this morning, 14 Oct 2026), blueprint v3.2 §4 step 2 (track routing and loudness), §4 step 3 (API vs human finishing), §5.1 edge rules 3 and 6, §6.4 (SRT), §6.5 (finishing checklist); design/12 §B; v1 late-stage spec §4 (what the Mac scripts did); decisions: MP4 only, SRT added, no music, Resolve 21.1.1, Resolve used once from the finished film, shake flagged and optionally stabilised with FFmpeg. Written 14 Oct 2026 after step 3; to be read with design/15.

## 1. Restated requirement
After the master film is approved (step 4) and every gap has a selected take or asset (visuals, slice 5), two stages finish the film:

- **assembly**: the operator chooses, per gap, how the take or asset fills it (trim, hold last frame, fit by contain) and whether a shot still flagged for shake is left, stabilised with FFmpeg, or swapped. The server builds the assembly plan from the master plan plus the gap fills, normalises each generated take (fps by frame drop/duplicate, pad to fit, colour check), and renders the complete film with FFmpeg: V1 picture, A1 narration untouched, A2 nat sound with 4-frame fades at the blueprint levels, A3 silent (its cues go to the human list), A4 absent. The operator watches and listens; an explicit yes records the assembly with the film's hash.
- **delivery**: the server writes the bundle (approved MP4, narration, every normalised source clip and asset with hashes, the master and assembly plans, SRT, finishing checklist, manifest) to storage with receipts. On the Mac, `vw pull VW-n` rebuilds the run folder, and `vw delivery resolve` builds one Resolve timeline from the bundle: media bins, V1 cuts with the solver's zoom and position on cropped shots, A1 narration, A2 intervals, markers for every A3 cue and every finishing item; exports the DRT; reopens it and compares; uploads DRT, project export and the verification report. Reserve, dispatch, report, close: never replayed. Back on Windows, `vw delivery final` checks the five points with the operator (watched, listened, SRT read, DRT verified, package complete) and records the delivery; the run closes with the agreed retention.

## 2. Unstated but expected
- The approved film is the FFmpeg render the operator watched; Resolve renders nothing. The Resolve timeline is the editable package, verified by DRT reopen, and the report states any difference between timeline and film (cut count, duration) rather than asking the operator to assert it.
- Audio identity: the narration track in the assembly is byte-identical to the approved narration (no re-encode); A2 and A3 never overlap speech (A2 intervals come only from the logs' clean intervals).
- Loudness targets from the blueprint are applied at render: A1 −16 LUFS integrated with −3 dBTP ceiling, A2 −24 to −30 dBFS peak, master −14 LUFS integrated; measured with ffmpeg `loudnorm`/`ebur128` and written into the assembly record.
- Generated takes (visuals) normalised as v1 did: trim or hold-last-frame to the exact placement frames, fps conversion by drop/duplicate (no interpolation), contain-pad to 16:9, reject untagged colour or rotation with a named reason.
- Local assets: movie copied without re-encode when it already matches the timeline; still → static clip of the placement length.
- Stabilisation: only for shots whose log has `stabilization_needed` or a `camera_bump` defect; FFmpeg `vidstab` two-pass on that shot only; the stabilisation zoom counts toward the cumulative zoom cap (solver constant 1.08); if the cap is exceeded the shot is left alone and listed for the editor.
- Finishing checklist items come from the logs and the plan: stabilisation left to the editor, voice isolation recommended, HLG/HDR colour space transform, Smart Reframe where a hands-only crop clipped the action (edge rule 3), every A3 cue with timecode and description, "add music on A4, duck under narration".
- SRT: one cue per beat from the narration timing (measured per-beat in/out), aligned to the master timeline.
- Bundle size: individual files ≤ 200 MB as today; a bundle larger than the Mac's free space is refused at `vw pull` with the sizes.
- Mac prerequisites checked by `vw delivery resolve --check` before any reservation: Resolve 21.1.1 running with scripting enabled, the Python module importable, fonts not needed (no Text+ graphics in v2), bundle hashes verified.
- The Resolve adapter targets 21.1.1 (`DaVinciResolveScript`: ImportMedia, CreateEmptyTimeline, AppendToTimeline with mediaType=1 for video-only, SetProperty ZoomX/ZoomY/Pan/Tilt, AddMarker, Export DRT). No FCPXML round trip.
- Close: retention = final film, approved narration, approved images and takes, DRT and report, every stage output record, approvals, cost; everything else deleted (plan §1 decision 4).
- Optional, not in the main path: `vw delivery resolve --preview` at first cut, same adapter, no approval (the middle option offered this morning). Built only if you tick it below.

## 3. Edge cases (tests; Resolve faked except one Mac run)
| # | Case | Expected |
|---|---|---|
| D1 | master with two gaps filled by one take (3 s for a 1 s placement) and one still asset | assembly plan: take trimmed to the placement frames, still held; render duration = sum of beats |
| D2 | take at 24 fps on a 25 fps timeline | frame-duplicated to 25, no interpolation, noted in the record |
| D3 | take 9:16 for a 16:9 slot | contain-padded; noted |
| D4 | take without colour tags or with rotation | refused with the shot named; operator chooses swap or accept-as-is |
| D5 | shot flagged `stabilization_needed`, operator chooses FFmpeg | stabilised, zoom ×1.08 recorded, within cap |
| D6 | same, but cap exceeded | left untouched, listed on the finishing checklist |
| D7 | narration bytes | assembly A1 sha256 == approved narration sha256 |
| D8 | A2 interval overlapping a speech window in the log | refused |
| D9 | loudness | A1 integrated within ±1 LU of −16, master within ±1 LU of −14, A2 peaks inside the band |
| D10 | operator records assembly without watched+listened words | refused (quote must contain the yes to both, as the stage question asks) |
| D11 | revise visuals after assembly | assembly and delivery stale; re-render required |
| D12 | bundle | manifest lists every file with sha256; a missing file refuses the bundle; `vw pull` verifies hashes |
| D13 | Resolve step twice | second `resolve` refused: already dispatched; `--inspect` shows the report; `--close` needed before any replacement |
| D14 | Resolve import readback differs (cut count or duration) | report says so; final approval shows it; operator decides |
| D15 | SRT | cue times equal per-beat narration in/out shifted to the timeline; text equals beat text |
| D16 | finishing checklist | contains every A3 cue and every flagged item; nothing invented |
| D17 | final without the five answers | refused listing the missing ones |
| D18 | close | retained keys present, everything else gone, run closed |
| D19 | Mac preflight fails (Resolve not running) | refused before reservation with the check that failed |
| D20 | one real Mac run on a 3-beat film | DRT exported and reopened; report uploaded; package downloadable |

## 4. Failure modes
ffmpeg render error → attempt counted, stderr in the message; storage read-back mismatch → STORAGE problem, nothing recorded; Resolve crash mid-import → dispatched state kept, `--inspect` reads what Resolve has, operator closes or resumes, never auto-replayed; Mac loses connection after dispatch → same.

## 5. Tests first
Normaliser unit tests (D2–D4), stabilisation gate (D5, D6), audio rules (D7–D9), bundle and manifest (D12), Resolve ledger with a fake adapter (D13, D14, D19), SRT and checklist (D15, D16), end-to-end D1, D10, D11, D17, D18 through the plugin. D20 by hand on the Mac, once, before you use it.

## 6. Not covered in step 5
Music. Text graphics on V3. Resolve rendering. MOV. Preview timeline unless ticked. Multiple delivery formats.

## 7. Decisions to confirm (defaults applied unless you object)
- Stabilisation default when a flagged shot is left untouched by the operator: leave it, list it for the editor (no automatic FFmpeg stabilisation).
- Bundle keeps the normalised take copies and the originals; the Resolve timeline uses the normalised copies (so timeline = film).
- Optional preview timeline at first cut: **not built** unless you tick it.
- Mac workspace path and Python: `vw pull` creates `~/VideoWizard/runs/VW-n`; Resolve's bundled Python module path from Resolve 21.1.1 defaults.
