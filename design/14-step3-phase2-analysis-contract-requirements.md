# 14 — Step 3 (design/11 Phase 2): the clip-log-v1 analysis contract — requirement list for SK's approval

Source of truth: `model-test/run_both.py` (prompt, schema), `model-test/solve_stage15.py` (solver), `model-test/out/3.8-flash.*` (fixture), design/12 §A (fields to add), design/13 §6 (decisions). Written 14 Oct 2026 after steps 0–2.

## 1. Restated requirement
Replace the v1 `source-evidence-v2` analysis contract with the blueprint's per-clip log. One Flash 3.8 request per clip, AGENTIC, sends the blueprint Stage 1 prompt with the run's project config (brief production inputs, beats, speaker policy, ffprobe metadata) and the Stage 1 schema; the server validates strictly, runs the deterministic Stage 1.5 solver (eligibility, crop rectangle, Resolve transforms, cumulative zoom), stores one evidence file per clip under `contract_version: clip-log-v1` with the 10-line summary card, and the stage output summarises it. Planning refuses runs made under the new contract until step 4 replaces it; runs made under the old contract keep working as today.

## 2. Unstated but expected
- Identity, receipts, caps, retry, recover, exclude, cost rows: unchanged mechanics; only prompt, schema and gate change. New `analysis_key` for every clip (prompt and schema digests change), stated in the stage steps.
- Schema is built in code from one definition; the wire form (enums as descriptions) and the strict validator share it. The identity digest uses the strict form.
- The nine blueprint fields missing from the experiment (12 §A.11) are added: `is_variable_frame_rate_vfr`, `rotation_flag_deg`, `duration_tc`, `creation_timestamp` (inputs, from step 2 media), `target_runtime_seconds` (input), event `frame`, `hero_frame_index`, `active_speech_tc_range`, `settle_buffer_applied_in_tc` (model), plus the defect enum and the block rename to `technical_qc_and_remediation`. `gemini_sampling_fps` is dropped; `processing_mode` is recorded instead.
- Solver additions from 12 §A: `effective_post_crop_shot_size`, strip `SLOW_MO_ELIGIBLE` when source fps < 50, `ui_path` text for the editor, server override of `max_safe_zoom_limit` from resolution (2.0 for 4K→1080p, 1.35 for 1080p).
- Head-inside-body sanity rule (11 §6.2): head box inside body box and body width < 0.6, else the sub-clip's `tc_confidence` becomes `NEEDS_BOUNDARY_CHECK` and a gap is recorded.
- Policy is an input to the solver: a speaker-policy change re-runs the solver only (`vw analysis resolve-policy`, unpaid), never the paid call.
- `vw analysis show --unit <id>` prints the summary card; the operator never reads the full log.
- Speaker policy mapping (document question set aside, default proposed): camera audio excluded → Mode 3 (no speaker audio, no speaker video); camera audio allowed → Mode 2 (speaker audio kept, speaker video replaced) unless brief `show_speaker_video` is true → Mode 1. **Default to confirm.**
- Audio removed for analysis (`--understand-audio no`) keeps the old sentence in the prompt; the log must then report MOS/no speech.
- Evidence file size: a 46-clip run stays in storage, never in a row; the 256 KB body guard is untouched.

## 3. Edge cases (each is a test)
| # | Case | Expected |
|---|---|---|
| E1 | fixture log (Flash C0120) through gate + solver | retained; 3 sub-clips; eligibility AS_IS / REJECT_VIDEO_KEEP_AUDIO_CONTEXT / AS_IS as in the experiment |
| E2 | sub-clip with an invalid enum value | that sub-clip excluded with reason; others retained; stage output counts it |
| E3 | wrong `clip_id` or `filename` | identity error → outcome `identity_mismatch`, no retry |
| E4 | `summary_card_lines` not exactly 10 | gap recorded, log retained |
| E5 | no speech anywhere | all speech blocks null; accepted |
| E6 | speaker visible (`mouth_visible`) but `speaker_crop_module` null | REJECT_VIDEO_KEEP_AUDIO_CONTEXT with reason; no crash |
| E7 | boxes outside 0–1 or zero width | solver rejects with reason; gate flags the sub-clip |
| E8 | blueprint CLIP_04 example boxes | crop 1.45x, position −431.3 / −7.8 (blueprint's own numbers) |
| E9 | speaker overlaps the action box (C0120 SUB_02) | infeasible, reason given |
| E10 | cumulative zoom over `max_safe_zoom_limit` | `within_safe_zoom_limit` false → REJECT_VIDEO_KEEP_AUDIO_CONTEXT |
| E11 | head box outside body box / body width ≥ 0.6 | NEEDS_BOUNDARY_CHECK + gap |
| E12 | timecode `HH:MM:SS:FF` inconsistent with seconds or frame at source fps | gap, not failure |
| E13 | `in_frame > out_frame` or `out_frame ≥ duration_frames` | gap, sub-clip excluded from eligibility |
| E14 | source fps < 50 with SLOW_MO_ELIGIBLE | option stripped by the solver |
| E15 | wire schema | no multi-value `enum` remains; strict schema digest stable across runs |
| E16 | identity digest | changes when a schema field is added; unchanged when only a description changes in the wire form |
| E17 | `--understand-audio no` | prompt carries the audio-removed sentence; a log claiming speech → gap |
| E18 | policy change after analysis | solver re-run, eligibility changes, no paid call, same evidence file version bumped |
| E19 | run analysed under source-evidence-v2 | planning works as today; `vw analysis show` says old contract |
| E20 | run analysed under clip-log-v1 | planning prepare refused: "planning for clip-log-v1 arrives with step 4" |
| E21 | empty `unavailable_or_uncertain` with nullable blocks filled | accepted; summary says "model reported no uncertainty" |
| E22 | 429/503 on generate | one automatic retry as today |
| E23 | live probe (skipped unless key present) | text-only `generateContent` with the full wire schema returns 200 |

## 4. Failure modes
- Gemini 400 "invalid argument" → schema too big or too many enums: the job is `rejected` with the HTTP status and the schema digest; nothing retries. The live probe test (E23) exists to catch it before a run.
- Non-JSON or non-finite answer → `retained_unstructured`, raw kept, never resubmitted.
- Worker crash between generate and store → `storage_pending` from the spooled response, as today.
- Solver exception on malformed boxes → caught per sub-clip, logged as a gap, never fails the clip.

## 5. Tests first
Unit: schema builder and wire form (E15, E16); solver (E6–E11, E14); timecode checks (E12, E13); gate on the fixture with mutations (E1–E5, E17, E21). Integration (fake Gemini answering with the fixture body): full `vw analysis start` → status → show (E1, E18, E19, E20). Live: E23 skipped by default.

## 6. Not covered in step 3
Planning on the new contract (step 4). Flex pricing. STATIC mode. Tamil transcription quality. The media-pool CSV.

## 7. Defaults proposed for the set-aside questions (say no to any)
- Speaker policy mapping as in §2.
- Beats come from the script stage (done in step 2).
- `learned_client_rules`: empty list per client until step 4's feedback loop writes them; stored per client id.
