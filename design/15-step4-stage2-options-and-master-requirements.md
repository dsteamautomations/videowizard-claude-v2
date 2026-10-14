# 15 — Step 4: Stage 2A/2B replaces planning — requirement list for SK's approval

Sources: blueprint v3.2 Sections 3–6 (options, slates, feedback, track routing, edge rules, 8-point QC, payloads), design/12 §B–§C (dispositions, 15 editor rules), design/13 §6 decisions (chat model + validator; blueprint review film; no music; Resolve once at the end). Written 14 Oct 2026 after step 3.

> **Read with design/17** (review additions, 14 Oct late): it adds items and resolves contradictions for step 4; where 17 differs from this file, 17 wins.

## 1. Restated requirement
A new stage pair replaces the v1-ported planning stage for runs on procedure version 2:

- **options** (Stage 2A): from the clip logs and summary cards, the chat model writes a coverage and gap report and, per beat, a PRIMARY and where possible a SECONDARY option, numbered across the film. Each option is an ordered mini-sequence of sub-clip events with source in/out (tc and frame), timeline in/out, speed, transform from the solver, colour group, A2 nat-sound intervals, A3 cues, a 3-line slate and a shared-clip warning. The server validates every option mechanically (grammar rules, the 15 editor rules, the 8-point QC) and refuses or flags. The server then renders the **review film** with FFmpeg: 75-frame slate before each option, narration on A1, retained nat sound on A2, nothing else. The operator watches it.
- **master** (Stage 2B): the operator's per-option decisions (KEEP, REJECT, KEEP_WITH_EDIT with a note) come in as the stage acceptance text. The server audits collisions, validates micro-edits, builds a fresh master plan (slates and rejected options stripped, rippled to zero), renders the **master film** (A1 narration, A2 nat sound with 4-frame fades, A3 cues as a human-to-source list, A4 empty), writes the SRT and the human finishing checklist, appends rejection reasons to the client's learned rules.

The master plan's gaps (beats with no kept option and no fallback) are the visuals units, as the planning certificate's gaps were. The first-cut stage records the master film with its hash. Nothing of this touches Resolve.

## 2. Unstated but expected
- Same server mechanics as every stage: `prepare` downloads a package, `check` validates without saving, `propose` saves a version, acceptance is a quoted yes, attempt cap 3 on `propose`, revise reopens.
- The package the chat model reads: project config, beats with measured durations (step 2), every retained clip's summary card, the list of eligible sub-clips with their solver output (a compact table, not the full logs), `learned_client_rules` for the client, and the paid boundary-check tool (`vw planning inspect` reused as `vw options inspect`, same jobs).
- The chat model cites the log field for every choice and states what the log cannot establish (12 §C.4); the validator's pass/fail per QC point is recorded beside the model's own.
- Speed: 100 % only in this step; SLOW_MO and SPEED_WARP options are carried as flags for assembly, not applied here.
- Every event's transform is the solver's `crop_rect` applied by FFmpeg (crop + scale), the Resolve zoom/position values are written into the plan for the final timeline.
- Narration pieces per beat come from the voice timing (frame-aligned, as planning did); beat boundaries are the timeline grid.
- Protocol B (unscripted) is **not** built; `script_mode` is always SCRIPTED in v2.
- Fallback hierarchy for zero coverage (edge rule 5): stay on A-roll if Mode 1; else a same-stage detail shot; else the beat is a **gap** for the visuals stage (the "flagged graphic card" of the blueprint becomes a visuals gap, since v2 has that stage).
- The review film and master film are files in storage with receipts, downloaded with `vw options fetch` / `vw master fetch` for the operator to watch locally (no web player, as agreed for voice).
- Old runs (procedure version 1) keep the old planning stage; the stage table of version 2 replaces `planning` with `options` and `master`. Edit/first_cut of slice 6 collapse into `master` + `first_cut` (first_cut = approve the master film).

## 3. Validator rules (mechanical, model-independent)
Grammar (blueprint §3 step 3): G1 inside `max_usable_window`; G2 `must_include_action_peak` kept; G3 duration ≥ `min_comprehension_hold_s`; G4 `pairing_constraints` honoured (MUTUALLY_EXCLUSIVE_WITH); G5 shot size changes ≥ 1 step between adjacent shots and never 3 of the same size; G6 `exit_eye_grid` → next `entry_eye_grid` or a neutral buffer; G7 `subject_screen_direction` preserved or a Toward/Away/Neutral shot between; G8 no Hard_Sun → Soft_Overcast cut inside a beat; G9 0 video handles on speaker-trimmed edges; G10 only eligible sub-clips (client_safe, not REJECT_*, within zoom limit); G11 option duration = target_beat_frames (±0); G12 numbering sequential, PRIMARY before SECONDARY per beat.
Editor rules (12 §C.5) as mechanical checks where derivable: R1 cut on action (in at a `natural_cut_point` or ±6 frames of one when the sub-clip has any); R2 pre-roll 6–12 frames before the beat's first VO word; R4 energy non-decreasing toward the beat's accent (flag, not refuse); R5 hold +1.0 s for WS/EWS, −0.5 s allowed for CU/ECU; R6 eye-trace at beat boundaries (flag); R8 no landmark dominant in >2 consecutive shots, no sub-clip reused within 20 s; R9 pause > 1.2 s in narration: current shot extended or nat-sound sub-clip placed (flag); R10 colour group change inside a beat flagged; R14 confidence from uncertainty fields, NEEDS_BOUNDARY_CHECK primaries trigger the frame check before the paid one; R15 best unchosen candidate per beat listed with the rule that excluded it (required field). R3, R7, R11, R12, R13 are prompt rules for the chat model, checked only where a field exists.
QC (blueprint §5.2): Q1 lip-flap (no ELIGIBLE_A_ROLL_SPEAKER events when show_speaker_video false); Q2 = G1–G3 + G9; Q3 cumulative zoom; Q4 shared clips slated in 2A, none duplicated in 2B; Q5 runtime = sum of beats, no gaps, no 1-frame cuts; Q6 no speech inside A2 intervals (intervals come only from `clean_nat_sound_intervals`), every MOS segment has an A2 or A3 bed (flag); Q7 = G7, G8, process prerequisites in order; Q8 brand rules: `risk_flags` empty on every kept sub-clip, VO lines checked by the model.

## 4. Edge cases (tests)
| # | Case | Expected |
|---|---|---|
| S1 | fixture: three synthetic clip logs (wide establishing, process action, talking head with crop) + 3 beats | coverage report lists A/B counts per beat; options validate; review film renders with 6 slates |
| S2 | beat with zero coverage, Mode 3 | report alerts; beat becomes a gap; options exist for the other beats |
| S3 | option exceeds `max_usable_window` by 1 frame | refused: G1 names the event |
| S4 | option drops the action peak | refused: G2 |
| S5 | two same-size shots then a third | refused: G5 |
| S6 | Hard_Sun → Soft_Overcast inside a beat | refused: G8 |
| S7 | sub-clip used in two options without a warning line | refused: Q4 (2A) |
| S8 | option duration ≠ target frames | refused: G11 |
| S9 | ELIGIBLE_A_ROLL_SPEAKER event under Mode 3 | refused: Q1 |
| S10 | A2 interval not from `clean_nat_sound_intervals` | refused: Q6 |
| S11 | proposal missing the best-unchosen list | refused: R15 |
| S12 | third invalid proposal | NEEDS_USER_DECISION (cap 3) |
| S13 | feedback KEEP on two options sharing a sub-clip | collision: auto-swap to an unused backup when one exists, else refused with the pair named |
| S14 | KEEP_WITH_EDIT trimming below the hold or past the peak | refused with the bound |
| S15 | KEEP_WITH_EDIT valid trim | master event adjusted, ripple correct, runtime still equals beats |
| S16 | REJECT with a reason | reason appended to the client's learned rules (per client id); next run's package shows it |
| S17 | all options rejected for a beat | master has a gap for that beat; visuals units declared |
| S18 | master film | duration = sum of beats; A2 fades 4 frames; A3 list emitted; A4 absent; SRT has one cue per beat with narration timing; finishing checklist lists stabilisation/HLG/smart-reframe items from the logs |
| S19 | review film | 75 frames per slate, 3 lines, ASCII only; narration intact and continuous across slates (slates are silent inserts, narration pauses) |
| S20 | version-1 run | old planning untouched |
| S21 | paid boundary check | reuses the inspection job path; result attached to the option |
| S22 | revise after master | options reopen; master and first cut stale |

## 5. Failure modes
Render failure (ffmpeg error) → stage attempt counts, file kept, message with ffmpeg stderr; missing narration piece for a beat → refused at prepare; a sub-clip's media file missing from storage → refused naming the clip; feedback referencing an unknown option number → refused.

## 6. Tests first
Validator unit tests per rule (S3–S11, S13, S14); fixture logs; end-to-end S1, S2, S15–S19 through the plugin with the fake Gemini unchanged (no paid call in this step except S21 with the fake inspector).

## 7. Not covered in step 4
Protocol B. Music. Slow motion applied. Resolve. Graphics on V3 beyond the slate. The media-pool CSV.

## 8. Decisions to confirm (defaults applied unless you object)
- Review film slate: white text on black, 3 lines, 75 frames, silent; the narration does not play under slates.
- The `edit` and `first_cut` stages of version 2 become `master` (render + approve) and `first_cut` (hash-bound approval of the master film), so slice 6's edit step is this step.
- Learned client rules are stored per client id in a new table `vw2_client_rules`, appended only, shown in every later package for that client.
