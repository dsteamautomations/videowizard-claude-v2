# 39 — Stage 4 (voice) improvements: requirements (approved by SK 18 Oct 2026, implemented the same day)

Source: the stage 4 review run with the stage review prompt on 18 Oct 2026 and SK's decisions on its 7 findings. Six go ahead (4.1–4.6); 4.7 confirmed the constants. Narration segmentation for scripts over the per-request limit (4.3) is **not** in this batch: SK scheduled it as its own requirements note right after this batch is deployed, before the stage 5 review. Nothing here makes a paid call by itself. VW-3 is past voice and is not affected; every change is backward compatible with the 0.4.0 plugin and the 0.5.0 server.

## Decisions carried from the review
- Voice prompt cut to its core; the v1-to-vw mapping step removed (4.1).
- A repeat client's **last voice** comes back as the recommendation with one question; the voice stage receives the brief's five decisions and the languages (4.2).
- **Warning** at script acceptance when the text exceeds the model's per-request limit; segmentation later (4.3).
- `vw voice jobs --wait` polls inside the tool (4.4); audition batches through the pool, model list cached on the server (4.5).
- The submission line names the model and settings; the operator's reason for the choice is stored as `choice_note` and shown next film (4.6).

## A. Server changes (`server/`)

| # | What changes | Why | Where |
|---|---|---|---|
| 4.1 | Voice prompt replaced by its core, about 450 words, keeping v1's proven rules word for word where they still apply: recommend qualities from the brief's purpose, audience, message, tone and ending; language and accent are different, never inferred from the client's name; browse the catalogue with filters (`vw voice catalog --language … --accent … --gender … --age … --use-case …`), never substitute a curated three, never claim an incomplete search exhausted the catalogue; library voices are added by exact identity with `vw voice add-library`; one to six auditions on one exact contiguous excerpt of the accepted script, the same excerpt for every candidate, about 45–70 words, at most 3,000 characters; model and settings per model (v4: stability and similarity only, start 0.5 / 0.75; v2: stability, similarity, style, speed, speaker boost; v3: stability 0, 0.5 or 1), never silently switched; a description justifies a recommendation, only the operator's listening establishes a preference; never claim to have heard anything; never regenerate a successful candidate, never replace a queued or uncertain job, a `submission_unknown` job is recovered, never resubmitted; narration is the complete accepted script and nothing else; after narration ask the operator to listen for pronunciation, pace, complete wording and the intended delivery; the narration is never re-recorded after acceptance; for a repeat client propose the last voice first (4.2). Removed: every screen, browser and player reference, every v1 tool name, effects, voice lab, migration notes, operator package notes, "Codex". Steps: step 1 loses the mapping table; step 2 unchanged; step 3 gains `--wait`; a new sentence for the repeat-client question. | 3,115 words, nine tenths unreachable. | procedures/v2.json voice `prompt`, `steps`, `prompt_origin` |
| 4.2 | `POST /api/runs` answer gains `last_voice` for the resolved client: from the client's most recent run with a current voice output, `{run, voice_id, name, model_id, settings, choice_note}`; `null` when none. | The client's narrator carries over. | core.py (`last_voice`), main.py |
| 4.5 | `ElevenLabs.models()` result cached in-process for 600 s (module-level, time-stamped); `submit_voice` uses it. The per-voice identity lookup stays per job. | Twelve provider calls per six auditions. | elevenlabs.py |
| — | `SERVER_VERSION` 0.5.0 → 0.6.0. | | config.py |

## B. Plugin changes (`plugin/`)

| # | What changes | Why | Where |
|---|---|---|---|
| 4.2 | `vw start` stores `last_voice` in the manifest; `voice_prepare` adds to `inputs`: `brief` (the five decisions and constraints), `narration_language`, `field_speech_languages`, `last_voice`; the summary line says "last voice for this client: <name> (<model>)" when present. | The stage sees what the prompt tells it to use. | vw.py `make_workspace`, stages_av.py `voice_prepare`, `cmd_stage` (voice extra) |
| 4.3 | `script_record` adds `length_warning` to the summary and the tool's summary line when `len(text) > 10000` (Eleven v4's per-request limit, the one constant in elevenlabs.py): "The script has N characters; Eleven v4 narrates at most 10,000 per request and segmentation is not built yet. Shorten or split the film before voice." Not a refusal. | The operator learns before voice, not at the refusal. | stages_text.py |
| 4.4 | `vw voice jobs --wait N` (seconds, default 0): the tool polls `GET /api/runs/{id}/jobs?stage=voice` every 5 s until no job is in an open status (`queued`, `running`, `storage_pending`, `submission_unknown`) or N seconds pass; the summary line counts ready, failed, unknown and still-open jobs; exit 0 either way (the assistant reads the counts). | One turn instead of a polling loop. | vw.py `cmd_voice`, parser |
| 4.5 | `vw voice audition` submits the batch through `ThreadPoolExecutor(max_workers=3)` (the same pool as uploads); errors surface on the main thread as today. | Serial submission in front of parallel work. | vw.py `cmd_voice` |
| 4.6 | The audition and narration summary lines name the model and settings from the first job's request snapshot: "Submitted 3 paid ElevenLabs audition job(s) on eleven_v4 (stability 0.5, similarity_boost 0.75)…". `vw voice narrate --note "<the operator's words on the choice>"` writes `work/voice-choice.json`; `voice_record` copies it into the summary as `choice_note` (empty string when none). | Shown default; the reason kept. | vw.py, stages_av.py |
| — | `plugin.json` 0.4.0 → 0.5.0. | | .claude-plugin/plugin.json |

## C. Unstated but expected
- A new plugin against the 0.5.0 server: `last_voice` absent → "none"; a new server against the 0.4.0 plugin: the extra answer field is ignored.
- `last_voice` names a voice that may since have been removed from the ElevenLabs account; the identity check at submission refuses it as today, and the assistant falls back to the catalogue. The steps say so.
- The length warning uses the v4 constant, not the live model list (the script stage makes no provider call); if the operator later narrates on v2 or v3, the server's live check still applies.
- `--wait` never resubmits and never recovers; it only reads. A `submission_unknown` job ends the wait early with its id named, so the assistant runs `vw voice recover`.
- The three-thread pool submits at most three audition jobs at once; the provider's concurrency limit is not approached by six jobs on five workers, as today.
- `choice_note` is the operator's words, never the assistant's; `--note` is optional and the steps ask for it in the same message as the narration.

## D. Edge cases
| Case | Expected |
|---|---|
| first film of a client | `last_voice` null; prompt shows "none"; the catalogue path as today |
| repeat client, operator says "same voice" | narration submitted with that voice; no audition; `choice_note` may be empty or the words given |
| repeat client, operator wants to compare | auditions as today, last voice included if the operator wishes |
| last voice no longer on the account | the identity check refuses; the assistant says so and returns to the catalogue |
| script of 10,001 characters recorded | recorded with `length_warning` in the summary and in the tool line |
| `vw voice jobs --wait 120` with one job queued then ready after 20 s | returns in about 20 s; summary "1 ready" |
| `--wait 30` with a job still running after 30 s | returns at 30 s; summary "1 still running; run again" |
| `--wait` and a job turns `submission_unknown` | returns at once naming the job; the assistant recovers it |
| six auditions submitted | three at a time; six job ids in the answer in voice order |
| one of the six refused by the server (unknown voice) | the batch stops with that refusal; the jobs already created are listed |
| `vw voice narrate --note "warmer, clearer on the numbers"` | work/voice-choice.json written; the voice summary carries `choice_note` after record |
| voice prompt | no "employee", "browser", "application", "save_voice_plan", "generate_", "choose_voice", "accept_voice", "effects", "lab", "Codex", "package" |

## E. Tests (written first)
Layer one, `plugin/tests` (run on this Mac): `test_voice.py` (new): `voice_prepare` inputs with and without `last_voice`; `script_record` length warning at 10,001 characters and none at 10,000; `cmd_voice jobs --wait` with a faked job list that turns ready after two polls (sleep patched), the timeout case and the `submission_unknown` case; audition batch of six goes through the pool and keeps voice order, a refusal in the batch surfaces; the narration summary line names model and settings from the snapshot; `--note` writes the file and `voice_record` copies it; the prompt and steps clean of the words in §D's last row and carrying "same voice as last time". `test_stage_calls.py`: start stores `last_voice` and tolerates its absence.
Layer two, `server/tests` (Docker): test_voice_media V1 extended: after the voice record, a second `vw start` for the same client returns `last_voice` with the voice, model and settings; a `models()` cache test with a counting fake provider (two submissions within the window call the provider once); test_core: `last_voice` null on a first film.

## F. Not covered
- server/tests cannot run on this Mac; compile-check only until a Docker machine runs them.
- The prompt's behaviour on a real catalogue browse is the model's; the rules are verified by text, not by a run.
- Narration segmentation: its own note after this batch (SK, 18 Oct).

## G. Deploy order
1. Server (`deploy-server.sh`, workers restart): tell SK first.
2. Plugin (`deploy-plugin.sh`); the operator restarts Claude Code.
3. design/35: a row for the stage 4 decisions and the segmentation schedule.

## H. Estimate
Plugin B with tests: about half a day. Server A: about two hours (the prompt cut is the bulk). Deploys: an hour.
