# 17 — Review additions to steps 4 and 5 (supersedes the conflicting lines in 15 and 16)

Date: 14 Oct 2026, late. Method: my own cross-check of design/15 and 16 against document 12 §B/§C, the open traceability rows (F-26–F-29, F-36, F-37) and the v1 late-stage spec, plus an independent second read against blueprint §3–7 that was not shown my lists. Together they found 52 items and 7 contradictions. Everything below is now part of the requirement lists; where I took a decision it is marked **default**, and six items are yours to decide (§5).

## 1. Contradictions resolved

| # | Problem | Resolution |
|---|---|---|
| C1 | 15 put beats on a measured + 0.8 s grid (which re-cuts the narration into pieces) while 16 required the narration byte-identical and continuous | **A1 is one continuous file, never cut.** A beat's timeline window is its first word's start to the next beat's first word's start (last beat: to the end of the recording). The natural gaps in the recording are the breathing pauses; no pause is inserted. `target_beat_frames` is that window in timeline frames. The step 2 `breathing_pause_s` field stays recorded but is not applied. D7 becomes: the film's A1 stream decodes to the same sample count and ±0.5 LU of the approved narration. |
| C2 | A1 "untouched" and "normalised to −16 LUFS" | A1 loudness is **measured** at voice record and written into the voice output. If it is within ±1 LU of −16 it is left alone; otherwise one gain change is applied at render and recorded. Never a re-encode. |
| C3 | Q4 "no duplicate sub-clip in the master" vs R8 "no reuse within 20 s" | Options stage: R8 (no reuse within 20 s, controlled sharing flagged). Master stage: Q4, zero duplicates. R8 is the options rule, Q4 the master rule. |
| C4 | "narration continuous across slates" | Each option plays its own beat's narration window; the review film repeats each beat once per option. Slates are silent. |
| C5 | SRT and finishing checklist produced at master (15) and at delivery (16) | Produced **once, at delivery**, from the master record plus the assembly record. Master shows a preview checklist in chat only. |
| C6 | slow-motion flags carried for assembly but never used | **Dropped** for v2. Stated in 16 §6. |
| C7 | A4 "empty" vs "absent" | FFmpeg films have no A4. The delivered Resolve timeline has empty A3 and A4 tracks with their names, so the editor finds them. |

## 2. Additions to step 4 (options and master)

- Package: the model reads summary cards first; `vw options log --unit <id>` fetches one full log on demand (A6). The package carries entity and landmark unification (A1): the validator checks every landmark named in an option exists in the logs. Learned client rules are a **hard filter** when written as exclusions, and shown otherwise (A2).
- Coverage report is a **separate step before options**: `vw options coverage` writes it, the operator sees it (counts of A/B by primary and secondary fit, reshoot alerts, per-beat confidence from the uncertainty fields, every planned shared clip with its "nothing else fits" line); only then `vw options propose` (A3). A beat shorter than every candidate's minimum hold is reported as uncoverable (A52).
- Boundary check: unpaid frame extraction first (`vw options frames`, reusing planning's extractor), paid `vw options inspect` second, question fixed to "zero residual lip movement in `in_tc ± 1.0 s`" (A4, A5).
- New validator rules: G13 SECONDARY must differ from PRIMARY in sub-clip set or in shot size/angle; G14 landmark names exist in logs; G15 frames agree with timecodes on every event in/out; G16 hold-last-frame or freeze only on `still_frame_dynamic_zoom_eligible` sub-clips; G17 hands-only crop allowed (head box as the exclude box) when a critical action's only clip has the speaker on camera, else the event is flagged for Smart Reframe / Magic Mask / clean plate on the checklist instead of rejected (A7, A27, A28, A17).
- Mode 1 and 2 (speaker shown or voice kept): **default = cuts on one picture track**, no V2 overlay model. An ELIGIBLE_A_ROLL_SPEAKER event is an ordinary cut; Q1 then checks only Mode 3/4. Stated as a deviation from the blueprint's V1/V2 layout (A9). See §5 if you want overlays.
- Slate format fixed to the blueprint's three lines: `OPTION #n | BEAT_ID (RANK) | d.ds (N Shots)`; `Clips: SUB… (d.ds SIZE[ Crop z.zzx])…`; `[WARNING: SHARED CLIP] …` or blank (A8).
- Option event fields added: `append_media_type` (always VIDEO_ONLY), `rotation_angle`, `timeline_marker` {name, note, colour}, `human_finishing_tasks[]`, A2 interval `description` and `target_peak_dbfs`, per beat `a1_timeline_in_frame`; `timeline_settings` from the run (A21). Master events record `approved_from_option` (A25). Each option stores its reasoning and the best unchosen candidate; `vw options show --option n` prints them (A33, R15).
- Runtime check compares the sum of beats with `target_runtime_seconds` when the brief gave one; a difference is a flag, not a refusal (A19). Q3 names the three zoom factors (crop × rotation × stabilisation).
- Editor rules corrected to document 12: R1 in at a natural cut point **and** out just after an accent, with the VO word that names the action aligned to the accent where word times allow (A30); R2 first shot on the beat boundary, later shots 6–12 frames before the phrase they support (A31); R4 adds the cross-film curve (hook and result beats highest, setup lowest; three consecutive same-energy beats flagged) (A32).
- Feedback: structured, one decision per option (`vw master decide --option n KEEP|REJECT|KEEP_WITH_EDIT [--note]`); a missing decision is refused by name; KEEP on both options of a beat is refused; `vw master rule --add "…"` records an explicit learned rule beyond rejection reasons (A22, A23). Micro-edits may trim or extend, validated against hold, peak and window (A24). Refused operator feedback does not count toward the proposal cap (A51).
- Master render applies the same levels as assembly (C2 rule for A1, A2 band) so the approved first cut sounds like the final (A11). First cut approval requires the watched-and-listened words (A50).
- Codec spec for every film: H.264 High, yuv420p, BT.709 tags, AAC 48 kHz stereo, MP4 faststart (A45). Per-segment render cache keyed by event digest so a revise re-renders only changed segments (A45).
- Native fps ≠ timeline fps (30/50/60 on 25): source frames are converted by exact integer decimation when the ratio is integer, otherwise by nearest-frame mapping with the mapping recorded per event; the validator checks `source_frames == timeline_frames × ratio` (A46). G11 is in timeline frames; windows in source frames; the conversion is explicit.
- Tests added: one row per validator rule and QC point (A35); the real Flash C0120 log plus two synthetic logs as the fixture (A34); package size bound for 46 clips (<4 MB) and the 256 KB body guard untouched; feedback-only revise re-renders nothing but the master; A1 sample count equals the decoded narration.

## 3. Additions to step 5 (assembly and delivery)

- Assembly placements carry the take's start offset when it is longer than the slot; a take shorter than the slot is held on its last frame or refused when hold is not eligible (A38, A39). Swapping a shot at assembly re-runs the validator (A36).
- Assembly review outcomes: accepted; changes requested with frame notes → new assembly version with the notes carried into the next render; rejected → back to visuals or master as named (A40).
- Horizon rotation applied by FFmpeg at render, `RotationAngle` set in Resolve, rotation zoom counted (A13). Colour groups set as Resolve clip colours and listed on the checklist (A14). HLG footage: FFmpeg tonemaps to BT.709 for the film and the checklist carries the Resolve CST item (A18).
- Stabilised shots: the stabilised render is in the bundle and the Resolve timeline uses it with zoom reset (A48).
- Resolve import is idempotent by file path; a resumed import never duplicates media (A12). Readback compares per event: record in/out, source in/out, zoom, position, rotation; tolerance 0 frames for cuts (A47). Verbatim operator authorisation recorded before dispatch (A44). A2 fades and levels are not reproducible through the scripting API; the report states that the timeline carries A2 clips at unity and the checklist lists the fades (A15). Delivered timeline has empty A3 and A4 tracks (A37).
- Checklist items added: master-bus limiter −14 LUFS / −1 dBTP, Deliver-page subtitle choice (burn-in vs SRT), colour groups, Magic Mask / clean plate where flagged (A16, A17).
- Final eligibility: current assembly, Resolve report for this film's hash, DRT verified, no pending revise, then the five answers (A42). Deliverable is a ZIP (stored, hashes verified on finish) with `OPEN-EDIT.md` inside, plus the loose MP4 (A43).
- Media-pool CSV included in the bundle (one line per clip with stage, shot, grade, colour group, beat ids as keywords), since Resolve is used (A26). See §5.
- Large films: the per-file cap stays 200 MB for sources; films and bundles use multipart upload to storage (Supabase resumable, 6 MB parts) with the same receipt (A41). See §5.
- Non-16:9 targets are **not** supported in v2 (A49); stated.
- Tests added: idempotent re-import, per-event readback, A1 duration vs decoded narration, large film upload, HLG tonemap, rotation, swap re-validation, changes-requested path.

## 4. Traceability
F-26, F-27 (execution + artefacts) → step 5 ledger and bundle; F-28 (review feedback) → step 4 master; F-29 (first cut) → step 4; F-36, F-37 → step 5; F-40 (procedure publishing admin) → slice 7, not here.

## 5. Your decisions (defaults in bold)
1. V3 graphics and callouts inside `text_safe_zone` (blueprint V3, editor rule R13): **not built in v2**; the editor adds them from the checklist. Yes to build it?
2. Mode 1/2 overlays (speaker A-roll on V1 with B-roll on V2): **cuts on one track**. Yes to the overlay model?
3. Media-pool CSV in the bundle: **yes, included**.
4. Films over 200 MB: **multipart upload**, or trim the cap problem by limiting film length?
5. Learned client rules table per client id: **yes**.
6. Preview Resolve timeline at first cut: **not built**.
