# VideoWizard v1 — late stages, functional specification

Source: `videowizard-beta` (read-only), latest published definitions `analysis-0.7.6`, `editing-0.8.3` + `editing-review-1.2.0`, `visuals-visual-1.18.0`; backend modules and operator package `VideoWizardOperator-0.9.7`; `docs/*.md`, `PROJECT-ISSUES-AND-HANDOFF-2026-09-26.md`, `APPLICATION-PLAN.md` (read for numbers only). Audience: v2 builder. Describes behaviour, not code.

Conventions used below. "Chat model" = the operator Codex/Claude conversation running the connector. "Code" = FastAPI backend + workers + Mac/Windows helper scripts. "Paid" = a provider call that costs money. All server state is one JSON `state` blob per run, committed by `videowizard_commit(expected_revision, request_id, fingerprint)` — every mutation is idempotent-by-request-id and optimistic-locked by run revision; identical request replays return the saved result, a changed body under the same id is `REQUEST_CONFLICT`. This one protocol underlies every stage.

---

## 1. ANALYSIS (per-clip Gemini analysis)

### 1.1 Inputs / outputs

| | |
|---|---|
| Inputs | accepted brief + accepted script (paragraph-split into `P001..Pnnn` passages); linked ready videos (sha256, metadata: duration, fps, w/h, audio_streams); per-run policy `source_audio_policy` (allowed/excluded), `understand_audio` (true/false), optional `context` {film_type, output, workflow_situation, visual_plan, planned_visual_slots, excluded_sources} |
| Unit | one job per (run, media) — the whole original is sent as one window `window_id=full`, `requested_interval=[0,duration]`. No chunking. |
| Paid call | 1 × Gemini `gemini-3.8-flash`, `thinkingLevel=HIGH`, `mediaResolution=MEDIA_RESOLUTION_HIGH`, `temperature=1.0`, `mediaProcessing=AGENTIC`, `maxOutputTokens=65536`, `responseMimeType=application/json` + `responseJsonSchema` (the expanded schema), streamed. Preceded by a Files-API resumable upload (private, resumable with receipt). |
| Output | `videowizard_analysis_jobs` row: `status`, `snapshot` (frozen prompt/schema/expected/identity/source/context), `result = {review:{status, raw, result, identity_errors, gaps, evidence}, provider:{finish_reason, usage…}, model, raw_digest, result_digest}`, `checkpoint` (event log, raw deltas, upload receipt, failure), `attempt_history`. Plus `descriptive_name` → auto display name in the shared media library. |
| Sizes (VW-5, 42 clips, Sep 2026) | `result` 3.93 MB total ≈ **94 KB/clip**; `checkpoint` 17.25 MB ≈ 410 KB/clip (contains full raw answer twice: deltas + final); `attempt_history` 7.39 MB; full rows 32.9 MB ≈ 780 KB/clip. Enqueue snapshot (prompt ≈37 KB prompt blocks + manifest + schema) ≈ 114 KB/job → 45 jobs = 5.12 MB inline before payload offload. |

### 1.2 What is sent

Prompt = 6 `prompt_blocks` (≈37 k chars) with 5 template tokens substituted once (`[FILM_TYPE_OR_UNSPECIFIED]`, `[AUDIENCE_AND_PURPOSE]`, `[STYLE_AND_INTENDED_TAKEAWAY]`, `[COMPLETE_SCRIPT_WITH_PASSAGE_IDS]`, `[MEDIA_BRIEF_AND_SOURCE_MANIFEST_WITH_WINDOW_MAPPING]`) + `naming_prompt` + (if situation enabled) a `USER-CONFIRMED WORKFLOW SITUATION` block + (if `understand_audio=false`) an "audio removed" note. The manifest JSON embeds the full accepted brief, accepted script, workflow_situation, delivery output, collection (all sibling source ids/hashes), excluded_sources, the actual settings, and the media_brief with planned_visual_slots (`user_supplied` or `exact_passage_level_reservations_not_supplied`).

Prompt block themes: (1) base evidence contract, source clock, speech transcription/translation, visual events grouped coarsely, readable text, separation observation/speech/interpretation/recommendation, editorial_ideas kinds; (2) `additional_analysis` (10 string fields: attempts, crop_guidance, clean_handles, continuity, preview_frames, speech_action_links, shorter_explanations, script_support, workflow_acknowledgement, unavailable) + "focused editing scan"; (3) editorial inference rules + `claim_evidence` rows; (4) consistency checks + rules G01–G07; (5) structured `script_support.claims`; (6) `world_markers` + `evidence_limits` (release 0.7.3+).

Audio policy: `understand_audio=false` → ffmpeg strips audio (`-an`) and the silent copy is uploaded; `source_audio_policy=excluded` → model may still hear audio but must not propose `source_audio` ideas (rows are later rejected by the gate anyway).

### 1.3 The evidence contract (`source-evidence-v2.schema.json` + extensions) — what each part is used for later

| Section | Shape | Used downstream for |
|---|---|---|
| envelope | `contract_version, request_id, script_id, sources[1]` | identity gate: must equal the frozen request or the whole response is `identity_mismatch` |
| `sources[0]` identity | `source_id, window_id, media_kind, clock=original_source_seconds, requested_interval, review_status` | identity gate; `review_status != complete` → gap |
| `coverage.visual[]` / `coverage.audio[]` | intervals with `status` (reviewed/unreviewed/inaccessible) / `state` (speech, omitted_background_speech, silence, non_speech, unintelligible, inaccessible, no_track, not_applicable) | first-pass limitations shown to planner; contradiction with local audio metadata is an identity error |
| `scope_omissions[]` | field (speech/visible_text/visual_details), interval, reason | limitations |
| `entities[]` | id, kind (person/object/speaker/other), label, uncertainty | referenced by visual_events actor/object ids, speech speaker_id; world_markers entity_ids |
| `speech[]` | interval, speaker_id, language, original_text, english_translation, transcription_status | planning: source speech evidence; required for `source_audio_segments`; only `clear` rows usable |
| `visual_events[]` | interval, label, description, actor_ids, object_ids, context_result, camera_framing, uncertainty | **the main currency**: every plan shot must cite ≥1 usable `visual_events/visible_text/entities` row of the same source overlapping the excerpt; relied-on component reviews need these collections |
| `visible_text[]` | interval, location, original_text, translation, legibility | same; only `clear` legibility usable |
| `interpretations[]` | category, claim, evidence_refs | planner context; cannot by itself support a visual property |
| `editorial_ideas[]` | kind ∈ best_take/action_span/story_moment/source_audio/script_use/future_visual, passage_ids, evidence_refs, interval, reason, details{alternative_refs, alternative_interval, must_keep_setup, visible_result, story_role, sound_type, …, asset_status} | provisional leads for the planner; `future_visual` must be `planned_not_created`; `source_audio` rejected when policy excluded |
| `visual_slot_guidance[]` | slot_id, passage_ids, intended_kind, asset_status, origin (user_supplied/agent_proposal), preserve_reservation | planner: reservations for generated video/blank/still |
| `unresolved[]` | interval, field, issue | limitations |
| `additional_analysis` (ext) | 9 free-text strings + `script_support.claims[{passage_id, script_clause, claim_id, support_classification ∈ directly_seen/spoken_claim/illustrative/uncertain, editorial_use}]` | provisional_analysis for planner prose; script_support validated against claim basis (visual→directly_seen/uncertain, speech→spoken_claim/uncertain, inference→illustrative/uncertain) |
| `claim_evidence[]` (ext) | id, target_paths (RFC6901 pointers into sources[0] or additional_analysis), claim, basis_type ∈ visual/speech/script/inference/unknown, time_scope, start_s/end_s, cues[{time_s, cue}], limits | traceability; later omission/role explanations may cite |
| `world_markers[]` / `evidence_limits[]` (ext 0.7.3+) | category enum (people, wardrobe, place_era, environment, architecture, tools_props, vehicles, animals, signage_language, material_state, condition, other), observation, entity_ids, interval, evidence_refs(≥1), uncertainty / subject, kind ∈ not_visible/ambiguous/not_established, limitation | Visuals stage: world sheet / casting / exclusions |
| `descriptive_name` | string | auto-naming of the media library item |

Validation is **gate, not repair**: `derive()` → identity errors (blocking) → schema gaps + content gaps (non-blocking, listed) → `usable_view()` salvages independent valid rows (id unique, timing inside window, required text present, references resolve to other usable rows, no cycles) and emits `evidence = {usable[], excluded_rows[{collection,item_id,index,reasons}], provisional_analysis, claim_evidence, script_support, visual_slot_guidance, coverage, scope_omissions, unresolved, world_markers, evidence_limits}`. Planning only ever reads `evidence.usable`.

Note: AGENTIC mode rejects the `category` enum, so the wire schema moves the enum into a description; the frozen validator still enforces it (`provider_schema_adapter=world-category-string-v1`).

### 1.4 Queue, claim, retry, recovery

| Topic | Behaviour |
|---|---|
| Job identity | `job_id = uuid5(analysis_key)`; `analysis_key = digest(identity)` where identity = run, source sha, script digest, brief digest, definition digest (prompt/model/settings only — procedure text changes do **not** invalidate), schema digest, metadata digest, audio policy, understand_audio, context digest, optional `generation` (reanalyze request id). Same inputs → same job → reused ("completed identical work is reused"). `is_current` re-derives the key against 0.7.0–0.7.3 candidates so additive releases don't invalidate frozen results. |
| Enqueue | `videowizard_analysis_enqueue` SQL, one batch per request; policy row stores audio policy + context. `reanalyze:true` needs new request id and no running/unknown jobs. Optional `ANALYSIS_PAYLOAD_STORAGE=true` offloads prompt/passages/manifest into one gzip object per batch (`{run}/analysis-inputs/{sha}.json.gz`, read-back verified) — queue JSON 5.12 MB → 1.36 MB for 45 jobs. |
| Statuses | queued → running → retained ∣ retained_unstructured ∣ identity_mismatch ∣ failed ∣ submission_unknown ∣ storage_pending ∣ stale |
| Claim (fair queue) | SQL advisory lock; expired `running` leases (45 min, renewed on every checkpoint) → `submission_unknown`; `storage_pending` first (no capacity); global cap **3** = running + submission_unknown-with-dispatch_possible; among `queued`, order by (active_count per run, last_claimed_at per run, created_at) so runs take turns. Worker: 3 threads, heartbeat row `videowizard_workers.analysis`. |
| Per-attempt pipeline | restore snapshot → recovered payload? (server checkpoint, then local `.analysis-spool` receipt) → stale check (source/policy/context still current) → download original (sha-verified, ≤ MEDIA_MAX_BYTES 200 MiB, 600 s) → optional silent copy → Files upload (resumable, receipt checkpointed) → `dispatch_intent` → streamed generate (soft wait 60 s, terminal deadline `ANALYSIS_DEADLINE_SECONDS` clamped 120–2400 s) → `response_received` → finish_reason must be STOP, raw must equal parsed → `review_response` → local receipt → `completed_payload` → final patch. Events journaled locally (fsync) and batched to DB (`BufferedCheckpoints`: 2 s / 256 KB batches, critical events synchronous). |
| Retained | `retained` = JSON parsed, identity ok, evidence derived (gaps may be non-empty). `retained_unstructured` = text kept but not JSON (STOP/MAX_TOKENS). Both are terminal; only `retained` feeds Planning. |
| Automatic retry | none, except: initial collection may do **one** bounded capacity retry (attempt 1, `capacity_fallback` true, classified `retry_candidate` e.g. 429/503, no partial raw) with backoff 5→60 s, `max_attempts_per_source=2`. |
| Explicit retry (`retry-failure`) | body: `user_instruction`, `max_attempts_per_source` 2..20, `persistent`, `backoff_seconds`, `max_backoff_seconds`, `accept_unknown_remote_outcome`. Eligible only for proven terminal failures: model_json/empty_response with STOP, incomplete_response, upload-phase connection error before dispatch, reconciled `provider_stream_error`, or an explicitly abandoned `transport_error` interruption (one replacement, never persistent). Never retries a retained result. |
| `recover` | reconciles `provider_stream_error` → failed (audit only) or re-queues `submission_unknown/failed` as `storage_pending` when a payload is recoverable from checkpoint/raw/local receipt. Never generates. |
| `retry-preparation` | re-queue when failure happened before any dispatch (upload receipt only). |
| `record` | returns frozen prompt/schema/context + every attempt's raw/result/error/performance (phase timings: download, attachment, upload_and_media_readiness, generation, validation, local_journal, database_checkpoint, final_database_save). |

### 1.5 Human decisions and where

| Decision | Where | Mechanism |
|---|---|---|
| camera audio in output? audio used for understanding? film type, output fps/resolution, workflow situation, visual slots, excluded sources | chat (first question of the flow) | start body `source_audio_policy`, `understand_audio`, `context` |
| start analysis (one approval, no second) | chat → connector `analyze` or browser button "Analyze linked videos" | `POST /analysis` |
| reanalyze | chat | `reanalyze:true` |
| retry a failed source, abandon an interrupted one | chat | `retry-failure` with verbatim `user_instruction` |
| rename a clip | browser analysis page (Edit) | `/name`; auto-name is applied once from `descriptive_name` |
| read findings | browser analysis page shows counts (completed/running/queued/saving/needs attention/not requested), plain message + next action, worker heartbeat age, jobs ahead, per-job on-demand result; chat model reads `analysis` summary and `record` | |

### 1.6 Known failure modes (v1) and mitigation

| Failure | Mitigation in v1 | Verdict for v2 |
|---|---|---|
| Deploy kills worker mid-generation; old worker's claims look alive; 3 unknown jobs block both runs (39+42 queued) | lease expiry → submission_unknown; unknown-with-dispatch_possible reserves capacity; manual scoped SQL set-aside; later: recover/retry-failure/accept_unknown_remote_outcome; fair queue | Keep leases + "unknown reserves capacity"; **add** graceful drain on deploy and an admin "release slot" action instead of SQL. |
| Statement timeouts (SQLSTATE 57014, authenticator statement_timeout 8 s): Planning read of full analysis rows 32.9 MB; planning commit of 6–8 MB state; 5.12 MB enqueue batch | narrow projections (`select=id,...,evidence:result->review->evidence`), 5-job revalidation batches, payload offload to object storage, planning value offload (>32 KB values become artifact refs), compact state (7.9 MB → 140 KB) | **Design out**: never store prompt/raw/checkpoint in the job row; one object per artefact; row holds digests + small status. |
| Receipt persistence failure → uncertain attempts (3 originals) | structured failure logging, local fsync receipt before DB, recover from receipt | keep local receipt + idempotent finish |
| Memory 512 MiB exceeded on backend (Oct 7) from restoring full Planning state on analysis GETs | `expand_planning=False` on analysis reads | keep reads scoped |
| Incomplete/MAX_TOKENS answers | retained_unstructured, no auto-resubmit | keep 65536 max tokens; consider lower temperature |
| Supabase free plan 50 MB global object cap while bucket says 200 MiB | product decision; not fixed | v2: check storage ceiling in preflight |
| IPv6 first-resolution stalls (169 s/connect) on operator PC | `VIDEOWIZARD_API_ADDRESS_FAMILY=ipv4` opt-in | client-side; keep option |

### 1.7 Definition history 0.7.0 → 0.7.6 (7 files)

Model/settings/prompt blocks unchanged across 0.7.0–0.7.2 (5 blocks, 33 k chars); 0.7.3 added block 6 (world_markers/evidence_limits) and `evidence_extensions=world-context-v1`; 0.7.4–0.7.6 changed only `procedure` text (recovery rules: stream-error reconciliation, transport-error replacement, failed source does not pause siblings; concurrency text). Procedure steps grew 7 → 18. So: **prompt stable, operations patched 4 times** — the operational envelope was the unstable part.

### 1.8 Chat model vs code (Analysis)

| Chat model does | Code does |
|---|---|
| asks the audio/situation/film-type questions, records verbatim replies | validates situation contract, builds frozen prompt/schema, identity key |
| triggers start/reanalyze/retry with user instruction | queueing, fairness, leases, upload, streaming, journaling, validation gate, salvage view, naming |
| reads `record`/status, explains failures, decides to recover vs retry | never retries on its own except one capacity retry |
| nothing editorial — all findings come from Gemini | — |

Keep as-is: whole-clip single request, schema-constrained JSON, salvage-don't-repair gate, idempotent request ids, local receipt. Patched repeatedly: recovery semantics (4 procedure revisions, 4 SQL migrations: controls, concurrency, fair queue, recovery, interruption), row size.

---

## 2. PLANNING / EDIT PLAN

### 2.1 Pipeline and state machine (session keyed by `context_digest`)

| Step | Action (`POST /editing/planning`, envelope `request_id, expected_revision, context_digest, action, document`) | Who authors | Result |
|---|---|---|---|
| settings | `GET/POST /editing/settings` (workflow_situation 13 fields + output {fps rational string, resolution [w,h] even}) | chat asks user, saves verbatim | `editing.settings` (binding digest) |
| prepare | `prepare {context_digest}` | code | `build_inputs` → `videowizard-editing-inputs-v1` document (accepted inputs, narration file + timing, policy, sources, analyses[{id, evidence, evidence_binding}]) → `package()` → **planning package** = `{context, context_digest, schema, prompt, inspector_prompt}` saved as artifact; `evidence_validation` receipt (5-job batches re-derive every analysis) |
| scene groups | `preview_scene_groups {scenes[{first_word_id,last_word_id,title,reason}]}` → `set_scene_groups {scenes, proposal_digest}` | chat model groups narration words into scenes (no model call) | new session with server-assigned `P001..` passages + timing windows; required before first draft (1.1+). Legacy: `preview_passages/restore_passages` (DOCX/scene-heading recovery). |
| authorize | `authorize {verbatim_reply, scope, clarification_authorized, paid_inspection_authorized}` | operator records user delegation | immutable |
| draft | `check_draft {content_base64}` (stateless) → `accept_draft {content_base64}` | **chat model is the sole planner** (`planner_engine=chatgpt_session`, `planner_api_requests=0`); writes `direct-gemini-edit-v3` JSON offline | first valid draft immutable; invalid → `rejected_candidates[]` |
| clarification | questions in draft `clarification_questions[]` {id, recipient ∈ flash/user/codex, sequence_id, shot_id, property, question, why_needed, what_answer_changes, inspect[{source_id,start_s,end_s}] ≤3 sources} | chat model | |
| answers | `answer_user {question_id, answer, verbatim_reply}`; `answer_mechanical {question_id, check{kind ∈ source_range/crop/narration_pause}}` (arithmetic only) | user / code | |
| frames (unpaid) | `extract_frames {question_id, source_id, times[1..24]}` → server worker PyAV decodes first frame ≥ t, PNG + PTS manifest (`targeted-frames-v1`); `resume_frames` continues partial | code | only for contact_state/object_identity/person_hand_association |
| inspect (paid) | `authorize_inspection {draft_digest, question_ids, verbatim_reply}` then `inspect {question_ids}` → `planning_inspector` worker: per question one Gemini Flash call (same model/settings as analysis) with ≤3 uploaded originals **or** the extracted stills; schema `flash_schema` (answers[{question_id,status ∈ answered/partly_answered/unanswerable, answer, observations[{source_id,start_s,end_s,visual_observation,relevant_speech,limits}], interpretation, uncertainty, inspection_method, sampling_rate}], inspection_limits) or frame schema (frames[{frame_id, answer yes/no/unclear, visible_cue, limits}]) | code (paid) | job statuses queued/running/retained/needs_review/storage_pending/submission_unknown/failed_pre_dispatch; `recover`, `resume_inspection` |
| review answers | `review_answers {response_digest, fields[{path,value_digest,scope ∈ inside_target/outside_target_excluded/uncertain/metadata, reason}], excluded_observation_ids}` — every prose field once | chat model | |
| ledger | `prepare_ledger {}` → `edit-clarification-v1` ledger {observations, inspector_answers, user_permissions, mechanical_answers, frame_results, unchecked_properties, answer_field_review} | code derives | `ledger_digest` |
| revision | `accept_revision {content_base64, ledger_digest}` — exactly one | chat model | immutable |
| editorial corrections (1.1 addendum) | `check_editorial_correction {content_base64, parent_plan_digest, ledger_digest, reason}` → `accept_editorial_correction {+check_digest}` — append-only versions before certificate; reports `inspection_reuse` (same_inspected_target vs retained_not_applicable per original question) | chat model | |
| finalize | `finalize {assessment}` per `assessment_schema`: 7 boolean flags all true, plan/context/ledger(/inspection_reuse) digests, assessment text, remaining_limitations ≥1, `unresolved_relied_on_claims=[]`, `component_reviews` for **every** video shot in recommendation + alternatives × 6 components (object_identity, person_hand_association, contact_state, movement_sequence, timestamp_mapping, question_scope) each {status, relied_on, reason, evidence_refs[str]} | chat model (same conversation; no second critic) | certificate `videowizard-execution-review-v1` {plan_digest, ledger_digest, artifact_hashes, provisional_execution_ready:true, final_film_approved:false} |
| authorize_execution | `{certificate_digest, verbatim_reply, scope}` | operator records user | `editing.accepted = {document: compiled-edit-v2, binding, approval}`; `editing.preparation` |
| handoff | `GET …/{context_digest}/handoff` → {plan, context, certificate, authorization} | | consumed by Mac |

### 2.2 The plan contract (`direct-gemini-edit-v3`, per sequence)

| Field | Content |
|---|---|
| `contract`, `experiment_id`(=run id), `fps` (integer at native route; string in 0.8.3 package), `duration_frames` | |
| `shots[]` (contiguous, zero-origin, end-exclusive, must reach `duration_frames`) | `id, kind ∈ video/gap, source_id, source_start_frame, source_end_frame` (native frames), `timeline_start_frame, timeline_end_frame` (film frames), `crop_px {x,y,width,height}∣null` (output aspect, inside source), `passage_ids[]`, `reason, uncertainty, visible_talking ∈ absent/uncertain/not_applicable(/present if allowed)`, `evidence_refs[{source_id, collection, item_id}]`. Rule: `(src_end-src_start)/native_fps == (tl_end-tl_start)/fps` (natural speed) **and** native/fps stride integer (exact decimation, e.g. 100→50). Gap: all source fields null, no refs. |
| `narration_pauses[]` | `{after_passage_id, additional_frames>0, reason}` — only at the last mapped word of a passage (`allowed_pause_boundaries`), in order; `duration_frames = baseline + Σ additional_frames` |
| `source_audio_segments[]` (only when situation allows sound) | `{id, source_id, source_start_frame, source_end_frame, timeline_start_frame, timeline_end_frame, content ∈ speech/ambient/both, evidence_refs, reason}`; cannot overlap narration or each other; speech needs `speech` evidence; `source_speech_under_b_roll=avoid` forces same-source picture in sync |
| `sequence_reason`, `unresolved[]` | |
| `decision_notes` | `shot_decisions[]` per video shot {meaning_and_support, new_information, duration_reason, crop_tradeoff, limitations, role/source_audio_role (a_roll/b_roll/context_dependent/neither/uncertain), required_companion, script_connections[{passage_id, script_clause (verbatim substring), connection, evidence_refs}], relevance, action_support[{description, evidence_ref, coverage ∈ full/partial/uncertain}], reuse{earlier_shot_ids, reason}}; `combinations[]` (every passage with ≥2 placements) {shot_ids, first_shot_establishes, following_shots_add[], better_than_single_shot, unintended_meaning_and_treatment}; `story_check{opening, progression, new_information, action_readability, pace_and_ending}`; `important_omissions[{source_id, contribution, reason, evidence_refs}]`; `factual_conflicts[]` |
| `alternatives[]` | each a full sequence with `id, title, tradeoff, passage_ids` (contiguous), `narration_window {source_start_s, source_end_s, baseline_duration_frames = ceil(span×fps)}` chosen in silence around the passages, own shots/pauses/notes |
| `alternative_review[]` | one row per contiguous passage group covering all passages once: {title, recommendation_reason, status ∈ alternatives_available/no_relevant_footage/no_added_information/brief_conflict/insufficient_evidence/user_reserved, reason, candidates[{source_id, frames, evidence_refs, comparison}], alternative_ids} |
| `gap_decisions[]` | one per gap {shot_id, basis ∈ user_reserved/no_suitable_evidence/uncertain, reason} |
| `clarification_questions[]`, `review_explanations[]` (viewer-readable cards: why/shows/limitations, no internal IDs) | |

"Gaps" = explicit black intervals in the recommendation where no supported footage exists; they carry a basis and later become `future_visual_requirements` (the Visuals stage's units of work). Removing a proposed shot in review also yields a gap of identical duration.

### 2.3 Narration timing binding

- Source of truth: voice stage `timing.json` on the accepted narration file: `recording{path,sha256,duration_s}`, `provenance{method, checked_by, boundaries_checked:true}`, `words[{id,text,start_s,end_s,passage_id}]`, `segments[]` (partition of the recording, speed 1), `natural_boundaries_s[]`, `trailing_hold_s`. `script_characters_match` must be true.
- `narration_binding.bind_timing`: recording sha must equal accepted narration file; per passage, timed word tokens must equal script tokens (casefold, apostrophes).
- `narration_timing.derive_timing`: mapped_words (source→timeline), sentence_windows (first/last word per passage), edit_windows (passage onset → next onset), pauses, frame_count = ceil(runtime×fps), explicit `frame_padding_s`. Half-open seconds, never quantized.
- Planning context publishes `mapped_words` (timeline==source for the recommendation), `passage_windows` (source bounds incl. existing silence, `baseline_duration_frames`), `allowed_pause_boundaries`, `audio_segments=[accepted-narration 0..duration]`. `apply_pauses` splits the narration at chosen boundaries and shifts every later segment/word by cumulative added frames; validates every mapped word binds to exactly one shifted segment. Alternatives subtract their `narration_window.source_start_s` from timeline clocks only.
- Clocks are explicit and distinct everywhere: narration `source_seconds`, film `film_frames`, video `native_source_frames`, review `presentation_frames`.

### 2.4 What the Mac does (editing-0.8.3 execution + review-1.2.0)

Artefacts exchanged: handoff JSON (plan+context+certificate+authorization) → `execution_document()` = `videowizard-compiled-edit-v2` {film_fps, resolution, sequences[{id, compiled{shots with seconds + source sha/fps/w/h, audio_segments, mapped_words, passage_windows, applied_narration_pauses, narration}, decision_notes, context}], alternatives}.

| Mac step | Helper | Produces |
|---|---|---|
| reserve/dispatch/report | `resolve_execute.py RUN --cache C --output O --sequence -1∣0 [--resume ID ∣ --inspect-execution ID ∣ --close-inspected ID --authorization … --previous-process-stopped]` ↔ `POST /editing/execution {reserve, dispatch, report, inspect, close_inspected, close_reserved}`; artefacts `POST /editing/artifacts` (kinds resolve_payload, resolve_script, execution_report, timeline_export, project_export, review_media, rendered_review, review_metadata, execution_inspection, approved_delivery; ≤20 MiB each, 4 MiB chunk bundles up to 2.5 GB) | `native_executions[id]` status reserved → dispatched → placements_reported ∣ needs_inspection → closed_unverified |
| grouped review render | `grouped_review.render` (FFmpeg; avc1 BT709 yuv420p; 5-second silent explanation cards before each option; narration plays intact; cache fingerprinted per segment) | `review.mp4`, `options.json`, `options.md`, `presentation.json`, `local-review.json`, `.render-stages/` |
| timeline import | `direct_edit_resolve.build_payload` → Resolve SDK ImportMedia/CreateEmptyTimeline/AppendToTimeline → Export DRT → reopen + compare (`drt_reopen_verified`, `project_exported`) | `payload.json`, `timeline.drt`, readback |
| visual review feedback | `review-command {check, save, authorize_render, record_render}` with proposal {base_digest, parent_revision, feedback_confirmation, changes[{action ∈ accept_recommendation/suggest_changes/remove_proposed_option, reference, verbatim_feedback, start_frame, end_frame, replacement_shots[], assessment}], unresolved_visual_choices} → `render_visual_revision.py` (FFmpeg only; placeholders for gaps) | `visual_revisions[id]` {feedback_applied → ready_to_render → local_review_ready}, `future_visual_requirements[]` |
| first cut | `retain_first_cut.py --revision R --receipt local-review.json [--approval …]` 4 MiB resumable parts ≤2 GiB | `first_cuts` saved_on_server; this is the Visuals stage's base |

### 2.5 Failure modes (Planning/execution)

| Failure | Mitigation | v2 |
|---|---|---|
| 32.9 MB analysis read + 6–8 MB state commit timeouts (ISS-04, #12) | projections, bounded batches, artifact refs for values >32 KB, `compact_payload` | design state as small refs from day one |
| single-passage import (single newlines → P001) lost scene structure | passage-recovery v1/v2, then format-independent scene groups | keep scene groups as the only route |
| no route for corrections after the one revision | editorial-correction addendum (append-only versions) | plan for N versions from the start |
| Resolve `AppendToTimeline` rounds fractional source endpoints to whole 24 fps media frames (≤38.7 ms error per narration piece), end-frame off-by-one, fractional MP3 placement, PCM diagnostic | detected via readback; still OPEN (VW10 `needs_inspection`); narration check scripts v1–v3 | v2: cut narration into frame-aligned pieces *before* import or deliver narration as one continuous track and only place pictures |
| MP3 declared length > decoded (44 ms short) | ≤100 ms EOF reconciliation with receipts | keep |
| import appended whole batch before checking first item; replay risk | import-only recovery, never replay dispatched import; inspect/close flow | keep "never replay" |
| 78 review cards = 33 min of reading | fixed 5-second cards | keep |
| uploading everything before local review | upload only approved deliverables | keep |
| connector rejected `review-1.1.0` (numeric-only version check) | fixed 0.8.15 | version strings free-form |
| 338 MB download 500 (fixed Content-Length) | chunked streaming | keep |

### 2.6 Definition history

`editing-0.8.0` (checkpoint-only, no execution) → `0.8.2` (full Section 2: Codex planner, clarification, certificate, grouped review, Resolve) → `0.8.3` (procedure 1.1: settings schema, scene groups required, editorial corrections; prompt text unchanged). `editing-review-1.0.0 → 1.1.0 → 1.2.0`: visual-only feedback meanings, then revision procedure + render helper, then first-cut approval/upload. Core planner prompt essentially frozen since 0.8.2; the *process around it* was patched (scene grouping, corrections, recovery).

### 2.7 Chat model vs code (Planning)

| Chat model does | Code does |
|---|---|
| asks settings questions; groups scenes; **authors the entire plan** (shots, crops, pauses, alternatives, all explanations, questions); reviews inspector prose field by field; writes the semantic assessment + component reviews; records verbatim delegations; drives Mac helpers | builds package/prompt (prompt is published but no model API is called by the server); schema + mechanical checks (coverage, speed equality, decimation, crop aspect, evidence overlap, combinations coverage, alternative_review coverage, gap decisions, review-card readability); frame extraction; paid Flash inspection; ledger derivation; certificate; execution document; Resolve import/readback; renders |
| never: alter trims, repair plans, choose footage | never: judge editorial quality |

Keep: contract-first validation, clocks, immutable drafts, evidence refs per shot, review cards with narration intact. Over-patched: passage/scene mapping (3 routes), narration import precision, state size.

---

## 3. VISUALS (visual completion for gaps)

### 3.1 Inputs/outputs

| | |
|---|---|
| Base | approved **first cut** (`visual_revision_current` with `first_cuts[...].approval`): its `future_visual_requirements` = gaps {shot_id, start_frame, end_frame, requirement}; optional accepted **timing overlay** (`propose_timing/accept_timing`: complete pause schedule + per-gap `duration_frames` changes → recompiled sequence; accepting resets accepted gaps/selections/bindings) |
| Unit of planning | the run's whole set of gaps in one **plan** (`videowizard-visual-plan-v1`, ≤4 MiB) |
| Unit of production | one **shot** inside a gap (image/video/diagram/animation); video shots → one paid take at a time |
| Outputs | immutable plan versions (artifacts), reference library rows (`videowizard_visual_references`, client-shared when approved), bindings per shot, video preparations (immutable requests), `videowizard_video_jobs` + events, take reviews/selections, local assets (ZIP ≤2 GiB), assemblies, movie uploads, resolve executions, final candidates |

### 3.2 Plan contract (`visual_contract.Plan`)

`foundation{treatment, appearance, world[Rule], exclusions[Rule], specifications, production_constraints, editing_constraints}` (Rule = {id, statement, scope, source}); `elements[{id, name, kind ∈ person/object/place/graphic/animal, identity ∈ exact/representative, requirements, required_views}]`; `gaps[{gap_id (= first-cut gap shot_id), title, intent, treatment_fit, scenes[] ∣ choices[2]{id,title,formats,description,why,tradeoff,source_strategy,candidates,scenes} + recommended_choice + decision_reason, candidates[SourceCandidate{media_id, start_s,end_s, use ∈ clip/still_in_film/generation_reference}]}]`; `scene{id,title,purpose,location_time,layout,landmarks[{id,description}],boundary_continuity,shots[]}`; `shot{id, start_frame,end_frame (must tile the gap exactly), visual_type ∈ image/video/diagram/animation, narration, purpose, relation ∈ illustration/explanation/evocation/counterpoint/anticipation/bridge/context, framing, camera, focus, subjects[{element_id, role, screen_position, start/end State{position{landmark_id,relation}, facing, pose, holding[], progress}, behaviour ∈ acts/holds, hold_reason, beats[{id,start_frame,end_frame,action,target,path,result,start,end}], continuity_note}], element_ids[], information_progression, appearance, production_method, review_notes}`. Validator: beats chain states, landmarks named, held subjects unchanged, subject state changes between shots warn unless `continuity_note`. `gap_digest` = foundation + gap + used elements (+ sequence_rules) so unrelated edits don't invalidate acceptance.

Decisions: `propose` (chat model, no acceptance) → `select {gap→choice_id}` → `accept gap_ids` (verbatim reply) → `retire` (restart, retains named rules). `stale` when first cut, timing or upstream inputs change.

### 3.3 Reference library

| Kind | How made | Paid? |
|---|---|---|
| `frame` | `visual_reference_worker` decodes exact PTS frame from a ready client video (queued → candidate; retry on failed) | no |
| `supplied` | user bytes (PNG/JPEG/WebP ≤16 MiB, ≤24 MP) uploaded by connector | no |
| `web` | HTTPS URL + `selection_reply` required; bytes uploaded by connector (server never fetches) | no |
| `isolated` / `sheet` / `keyframe` | **generated**. Route A: any model with `generation{model,prompt}` + approved `parent_ids` (never used in practice). Route B (1.9.1+): `codex_builtin_image` receipt {provider OpenAI, tool image_gen, model null/`not_exposed_by_tool`, operation generate/edit, prompt, authorization{user_chat, verbatim_reply}, output_sha256, reference_inputs[{path, sha256, role, reference_id?}], history} — i.e. **images were generated by the operator's ChatGPT/Codex built-in image tool, outside the backend; the server only verifies hashes and stores original + normalized PNG**. No image API was ever wired (prompt: "The user named GPT Image 2.5 for images; verify actual tool capability"). | operator-side, undisclosed |

Approval: owner approves exact `sha256` with verbatim reply (original bytes accepted when the normalization proof exists → `verified_original_normalization`, 1.9.3). Status candidate → approved. Lineage repair: `authorization_addenda` (builder script).

Bind (`POST /visuals/bind`): per shot, every `element_id` covered by 1–20 approved references **or** an `editable_graphics{mode:editable_text, text verbatim from element.requirements}` (1.9.4); `subject_selectors{element→{ref→text}}` allow an object element to use a place reference (1.9.2). Produces `bindings[shot] = {gap_digest, references{element→[{id, sha256, subject_selector?}]}, editable_graphics}`.

Preparation packet (`GET /visuals/shots/{id}/preparation`): foundation + scene + shot + refs (with `/image` URLs) + fixed `image_instruction` / `video_instruction` / `checks[]` / `compositing_instruction` + chosen generator. This packet is what the operator reads to compose keyframes (by hand with the built-in tool) and to write the motion prompt.

### 3.4 Video takes

| Step | Contract |
|---|---|
| choose generator | `select_generator {shot_id, provider, model}` from catalog: **default `google/gemini-omni-1.1-flash` (3–10 s, prompt-requested duration, end image ok)**, `higgsfield/kling-video/v3.0/std/image-to-video` (3–15 s, integer seconds), `higgsfield/bytedance/seedance-2.5/image-to-video` (4–30 s, 480p/720p/1080p). Needs reconfirmation when plan changes. Admin connection checks: Omni = GET model record; Higgsfield = request a signed upload URL. |
| prepare_video | `Prepare{shot_id, start_image{reference_id,sha256}, end_image?, motion_prompt, subject_reconciliation{element_id→text} (keys must equal exactly `shot.subjects[].element_id` — the **motion subject contract**, see docs/video-motion-subject-contract.md), image_inspection, continuity_notes, duration_seconds 3–30 within model range, timing_reconciliation, aspect_ratio 16:9/9:16, resolution 720p/1080p (null for Kling)}` → immutable `videowizard-video-request-v1` record incl. `placement{start_frame,end_frame,film_fps,duration_seconds (exact Fraction string)}`, `effective_prompt` (= motion_prompt + reconciliation + continuity + "use first image as start… no captions, no narration/music, preserve identities"), `base_preparation_digest`. No provider call. |
| submit_video | `{preparation_id, paid_authorized:true}` + verbatim reply → SQL `videowizard_video_commit` inserts job (`V02-authorize`), one active job per shot. |
| worker (`video_worker`) | claim (`V03-worker`, lease 10 min; expired `submitting` → submission_unknown `V03-submit`): preflight (plan/refs/images unchanged) → build wire request (Google: `POST …/v1beta/interactions` `{model, background:true, store:true, input:[images…, text], response_format:{type:video, aspect_ratio, resolution}}`; Higgsfield: upload images to signed URLs, `{image_url, prompt, duration, last_image_url∣end_image_url, …}` with Idempotency-Key) → write local `attempt.json` intent → submit once → `response.json` + storage receipt → status submitted → poll (`in_progress`) → completed: download MP4 (≤200 MB), sha, artifact, ffprobe evidence {duration_seconds, timing_matches_placement (1 ms tolerance), creative_approval:false} → `ready` (`V05-retain`); otherwise failed/cancelled (`V04-reconcile`). `recover_video` → recover_pending (re-read receipt only); `cancel_video`. |
| review/select | `review_video {job_id, artifact_sha256, decision accepted/rejected, watched_video:true, notes, timing_notes (required if duration mismatch)}` → `select_video {job_id, review_id}` (one per shot; context digest of plan/fps/preparation/images; stale detection) → `clear_video_selection` |

Known failure: V01A/V03A/V14 — placement duration stored as Fraction string `"21/5"`, worker did `float()` → ValueError → stuck storage_pending; fixed in worker only; takes were 5.00 s vs 4.20 s requested → `timing_matches_placement=false` (Omni does not honour fractional durations; assembly must trim/hold).

### 3.5 Local assets (1.18)

`videowizard-local-asset-v1` manifest {plan_id, shot_id, kind ∈ movie/still/design, duration_frames, fps, resolution, picture, files{name→{sha256,size,role}}, approval{verbatim_reply,file,sha256}, provenance, crop (still), background, layers[rectangle/text/image with frame ranges, exact font files], graphic_element_ids, reference_ids}; ZIP packed by `local_assets.py pack`, uploaded register → chunk(4 MiB) → finish (server unpacks and verifies every member hash) → `ready`. Purpose: let the operator deliver hand-made designs/stills/composites (V02, V07, V13A, V13B) without a provider job, keeping editable recipes for Resolve.

### 3.6 Definition history 1.0 → 1.18 (24 files)

| Release(s) | What changed (from `adaptations` list + migrations) |
|---|---|
| 1.0 | combined scenes/shots/beats, world/exclusions, references, bind, preparation packet; "Higgsfield chosen, not configured"; GPT Image 2.5 named for images |
| 1.1–1.5 | explanations, structure, clarity, choices (focused 2-way alternatives), no quotas |
| 1.6/1.6.1 | ~4-second pacing guideline |
| 1.7–1.8 | one connected director proposal; authorized restart (`retire`) |
| 1.9–1.9.5 | world/exclusion categories; comprehensive world proposal; treatment refresh; 1.9.1 built-in image receipts; 1.9.2 subject selectors; 1.9.3 parent input hashes; 1.9.4 editable text layers; 1.9.5 editorial timing overlays |
| 1.10 | per-shot generator selection, Omni default, video jobs/worker |
| 1.11 | take review + selection |
| 1.12–1.15 | assembly prepare/authorize/record; assembly review; movie retention + range playback; static text graphics compositing |
| 1.16 | portable bundle + once-only Resolve import (Text+) |
| 1.17 | final export/package approval + retention |
| 1.18 | local assets |

Pattern: prompt grew by accretion (26 headed sections); 1.0–1.9.5 were **planning-quality patches** to the chat model's output; 1.10–1.18 were **new pipeline stages** bolted onto the same `POST /visuals` command with a 23-value `action` enum.

### 3.7 Human decisions and paid calls (Visuals)

| Decision | Where | Paid call behind it |
|---|---|---|
| accept treatment/gaps, select choice, retire | chat (browser shows plan read-only) | none |
| approve reference image bytes | chat or browser gallery | image generation happened in the operator's own tool (undisclosed cost) |
| generator choice | chat or Visuals page | none |
| `submit_video` | chat verbatim or Visuals page checkbox | **1 video generation** (Google interactions API or Higgsfield) |
| take accept/select | chat or Visuals page (after watching) | none |
| assembly authorize/review, movie upload permission, Resolve timeline permission, final approval | chat/Visuals page | none |

### 3.8 Chat model vs code (Visuals)

| Chat model does | Code does |
|---|---|
| writes treatment, world, scenes/shots/beats, elements; picks references (frame times, web URLs); **generates reference sheets/keyframes with its built-in image tool**; writes motion prompt + subject reconciliation; watches takes and records decisions; packs local assets; drives Windows/Mac helpers | validates plan structure (frame tiling, beats, landmarks), gap digests, acceptance scoping; reference store/normalize/approve; bind coverage; packet assembly; video request freezing; provider submit/poll/retain with idempotent spool; ffprobe evidence; selection staleness; assembly compilation |

---

## 4. ASSEMBLY + FINAL DELIVERY

| Step | In | Code/Helper | Out |
|---|---|---|---|
| `prepare_assembly` | `{shots[Placement{shot_id, job_id, source_start_seconds, end_policy trim/hold_last, fit contain, reason} ∣ LocalPlacement{shot_id, asset_id, reason}], graphics[Graphic{shot_id, element_id, text (verbatim), frames, font_name, font_sha256, size, x,y,w,h, padding, line_spacing, align, colour, background}]}` | server replaces only `gap` intervals of the first-cut compiled sequence with `assembled-<shot>` video shots (or `remaining` sub-gaps); audio identity must be byte-identical; immutable `videowizard-video-assembly-v1/v2/v3` record | `assemblies[id]` prepared |
| `authorize_assembly {assembly_id, graphics_reviewed}` after `preview_assembly_graphics.py --fonts map.json` (layout-N.png) | verbatim reply | | ready_to_render |
| render | `render_video_assembly.py RUN --assembly ID --cache C --output O` (Windows): per take `normalize` = trim/hold_last/fps conversion (frame dup/drop, no interpolation)/contain-pad/BT709 check (rejects untagged colour or rotation); local asset movie copied, still → crop/resize static clip; graphics composited from PNG layers; narration copied without re-encode | | `assembly-<16>/review.mp4`, `normalized.json`, `local-review.json` |
| `record_assembly {movie_sha256, duration_frames, film_fps, graphics_digest}` | | | local_review_ready |
| `review_assembly {movie_sha256, decision accepted/changes_requested/rejected, watched_video, listened_audio, notes, frame_notes[], acknowledge_unfinished, parent_review_id}` | user after watching | | reviews[] |
| movie retention | `retain_video_assembly.py --receipt local-review.json` → `/movie-upload {authorize, begin, chunk, verifying, finish, failure}` 4 MiB parts ≤2 GiB | | `saved_on_server`; `/movie` with HTTP range playback |
| portable bundle | `assembly_bundle.py --render-folder … --destination …` (Windows) | copies hash-verified footage, narration, normalized clips, fonts, graphic PNGs, manifest.json | folder → Mac |
| Resolve import | `resolve_assembly.py --bundle … --output … [--verify-only ∣ --authorization "…" ∣ --resume ID ∣ --inspect ID ∣ --close ID …]` ↔ `assembly_resolve {reserve, dispatch, report, inspect, close}` | new timeline `VW-assembly-<id>`, media bins (01 Original footage/02 Narration/03 Review timelines), Fusion Text+ per graphic on its own track, local design states as Fusion Loader/Background/RectangleMask/TextPlus, DRT export + reopen compare (`drt_reopen_verified`, `editable_text_verified`, `local_assets_verified`) | `resolve_executions[id]` placements_reported |
| final | `final_delivery.py prepare RUN --assembly A --execution E --movie final.mp4 --output … [--bundle …]` → `propose_final {movie_sha256, archive_sha256, timeline_sha256, size, duration_frames, film_fps, project_id, timeline_id, manifest(videowizard-final-package-v1: files[], local_assets[])}` → `review_final {decision approved…, watched_video, listened_audio, native_text_checked, native_reopen_checked, movie_matches_timeline, notes}` → `final_delivery.py upload` (chunks, `finish` verifies ZIP inventory + every member hash, ZIP_STORED only) | eligibility: current assembly, no unresolved ranges, all planned graphics done, native attempt placements_reported with text+DRT verified, latest review accepted | `final_candidates[id]` saved_on_server → `GET /deliveries` / `/deliveries/{id}` (ZIP: Approved-film.mp4/.mov, Approved-timeline.drt, Media/…, fonts, manifest.json, OPEN-EDIT.md) |

Human decisions: accept assembled movie (watched + listened), permit upload, permit new Resolve timeline, final approval (5 explicit checks). Paid calls: none. Failure modes: Mac SDK/font/Text+ behaviour never validated end-to-end by development ("Windows synthetic tests do not establish Mac SDK compatibility"); native narration precision bug (§2.5) applies equally here.

---

## 5. Cross-cutting: what the chat model does vs what code does

| Stage | Chat model | Code |
|---|---|---|
| Analysis | asks policy questions; triggers; interprets failures | everything else incl. the only paid model call (Gemini 3.8 Flash) |
| Planning | **is the planner**: writes the whole plan + questions + assessment; reviews inspector prose | contracts, arithmetic, frame extraction, paid Flash inspection (same model), certificate, Resolve import, FFmpeg review render |
| Visuals | **is the director**: treatment/world/scenes/beats; picks & (with its own tool) **generates** reference images; writes motion prompts; reviews takes | plan validator, reference store, bind, request freezing, paid video generation (Omni/Higgsfield), retention, selection |
| Assembly/final | authors placements/graphics; watches; approves | compile, render, bundle, Resolve, package verification, deliveries |

Paid provider surface in v1: Gemini 3.8 Flash (analysis + inspection), Gemini Omni 1.1 Flash video (interactions API), Higgsfield Kling/Seedance; images only via operator's built-in OpenAI image_gen. v2 plan: images via OpenAI GPT Image 2.5 API → the reference "generated kinds" + receipt route maps 1:1 (model becomes known, output hash verified server-side, prompt/parents stored by the server instead of operator-reported).

## 6. Keep as-is vs patched-over (summary)

| Keep | Why |
|---|---|
| idempotent request id + fingerprint + optimistic revision on every mutation | solved every "unknown outcome" case; replay returns saved result |
| whole-clip analysis with schema-constrained JSON + salvage gate (`usable` vs `excluded_rows`) | robust to partial garbage without re-paying |
| evidence refs per shot, explicit clocks, natural-speed equality, gaps as first-class | made plans mechanically checkable |
| immutable artefacts by digest; small refs in state | fixed the timeouts once adopted |
| "never replay a dispatched paid/native operation; reserve → dispatch → report/inspect → close" | the only thing that made Resolve and provider failures recoverable |
| local fsync receipt before DB write (analysis, inspector, video spool) | survived deploy kills |

| Patched repeatedly | Count | v2 lesson |
|---|---|---|
| analysis recovery semantics | 4 procedure releases, 5 SQL migrations | define outcome classes (rejected / failed-terminal / unknown-dispatched / retained) once |
| state size / DB timeouts | ISS-04, #12, payload offload, value offload, compact payloads, replay actor | artefact store from day one; rows carry digests |
| passage/scene mapping | 3 routes (paragraphs, passage recovery v1/v2, scene groups) | scenes = operator-chosen word ranges, nothing format-derived |
| Visuals prompt | 24 releases, 26 sections | split into small stage prompts with stable schemas |
| Resolve native precision | 20 (fractional MP3), 21 (PCM), 18 (off-by-one), VW10 24→25 fps rounding | frame-align narration pieces before import or keep narration continuous |
| operator package/connector drift (0.8.12 → 0.9.7) | ~15 packages | server-published instructions worked; local helpers kept drifting — minimize local code |

## 7. Not covered

- Earlier stages (intake, brief, script, voice, media upload) except where their outputs (timing.json, media metadata) feed these stages.
- Frontend page internals beyond what the operator sees on the analysis and visuals pages.
- Exact text of the 1.18 visuals prompt sections beyond their headings; exact wording of planning prompt paragraphs (quoted by theme only).
- Operator connector internals (`connector.py` pending-request store, encryption), Mac setup scripts, `mac_preflight`.
- Voice-stage timing extraction (how `timing.json` is produced) and the editing-0.8.0 legacy `videowizard-edit-plan-v1` contract (superseded by compiled-edit-v2).
- Live-run data (VW-5/VW-8/VW10 current status) — only historical numbers quoted from docs.
- Cost figures: none recorded in the repo.
