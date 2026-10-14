# Slice: intake → brief → script, then voice + media — requirement list for approval

Two checkpoints inside one slice: **A** text stages (shown to the owner as the first end-to-end run), then **B** voice (ElevenLabs port) and media upload.

## A. Text stages (intake, brief, script)

### What is built
| Part | Content |
|---|---|
| Procedure content | v1's latest `intake-0.4.0`, `brief-0.4.0`, `script-0.5.0` prompts and step lists moved into `server/procedures/v1.json` under each stage as `procedure` (steps) and `prompt`; served by `GET /api/procedures/{version}/{stage}` to executor sessions only, never written to disk by the plugin |
| Stage scripts | `plugin/scripts/stage_intake.py`, `stage_brief.py`, `stage_script.py`: fetch the procedure, read inputs from `in/` (intake) or the previous stage output, hand the prompt + inputs back to the model through the `/vw` command (the model writes the proposal into `out/`), validate the proposal's shape, record with `vw output` |
| Model work | The chat model (Claude Code) does the text work, as the v1 Codex session did. No paid API call in these stages |
| Intake inputs | pasted text, TXT/MD/DOCX, text PDF (v1 `extraction.py` ported); original file kept in `out/source.*` as a retained file; client name as free text |
| Stage outputs | intake: `source.txt`, `intake.json` (title, cleaned script, notes, client); brief: `brief.json`; script: `script.json` (passages with ids; content digest) |
| Acceptance | one question per stage in chat; reply stored verbatim |

### Unstated requirements in scope
1. The script's `content_digest` is stored in its output so voice and later stages can detect a changed script (v1 behaviour).
2. Revise of intake/brief/script follows slice-1 rules (free before voice; blocked with cost list after).
3. The model must show the operator the cleanup notes and the title alternatives together (v1 step 7), in chat, before asking the one acceptance question.
4. `GET /api/procedures/...` is refused for browser sessions (procedure text stays out of the UI).

### Edge cases (tests)
| # | Case | Expected |
|---|---|---|
| T1 | intake with a DOCX containing tables | tables included; images/headers not; warning listed |
| T2 | PDF with an unreadable page | warning names the page; no invented text; model must ask for a readable copy |
| T3 | source over 20 MB | refused before upload |
| T4 | script proposal missing a passage id or empty passage | stage script refuses to record; counts as an attempt |
| T5 | accept script, then revise brief | script output stale; `next` = brief; no cost list (nothing paid) |
| T6 | browser session calls `/api/procedures` | 403 |
| T7 | run through intake → brief → script with the test client | three outputs, three quotes, `next` = voice |

## B. Voice (ElevenLabs port) and media

### What is built
| Part | Content |
|---|---|
| Voice | v1 `elevenlabs.py`, `voice_catalog.py` (9 filters, paging, previews, add library voice, models), `voice_timing.py`, auditions and full narration from `voice.py` and `voice_worker.py`, ported behind `POST /api/runs/{id}/jobs` with `provider: elevenlabs`; one worker loop; cost recorded on the job and the stage output |
| Voice stage output | `voice.json` (voice id, model, settings), `narration.mp3`, `timing.json`; acceptance after the operator listens (download link on the run page) |
| Storage | `POST /api/files/sign` → signed PUT URL to the Supabase bucket; the plugin uploads from `out/`, then `POST /api/files/receipt` marks the file received after a server-side size+hash check; `close` now verifies against the server |
| Media | operator puts clips in `in/`; `stage_media.py` hashes, probes (ffprobe), uploads via signed URLs, records `media.json` listing clips with ids, durations and `units` for analysis; 200 MB per file, v1's limit |
| Downloads | run page links to retained files via short-lived signed GET URLs |

### Unstated requirements in scope
5. Dropped per the matrix: voice drafts, voice effects, voice lab, cross-run media library, descriptive naming. Kept: catalog filters, previews, add library voice, auditions, narration, timing, recover of an uncertain job by `request_id`.
6. Narration is bound to the script's `content_digest`; a changed script makes the voice output stale automatically (through revise).
7. Media `units` are declared as `summary.units.analysis = [media ids]` so the analysis stage (next slice) is per-clip from day one.
8. Upload resumes by re-running the stage script: files already receipted are skipped.

### Edge cases (tests)
| # | Case | Expected |
|---|---|---|
| V1 | audition for 3 voices | 3 jobs, cost recorded, previews downloadable |
| V2 | narration job with unknown outcome (worker killed between submit and result) | reconcile by `request_id`; no second charge |
| V3 | ElevenLabs 429 / 5xx | job `failed` with provider message → `NEEDS_USER_DECISION`; no automatic retry loop |
| V4 | narration shorter than the script's passages | timing check fails; refused; operator told which passage |
| M1 | upload of a 201 MB file | refused before upload |
| M2 | upload interrupted; stage script re-run | only missing files uploaded; receipts unchanged |
| M3 | receipt with wrong hash | 409; file not marked received |
| M4 | duplicate clip (same sha256) | recorded once, listed once in units |
| M5 | `close` with every file receipted | server verifies receipts; closes |
| M6 | clip without an audio track | probe records it; no failure |

## Not in this slice
Analysis, planning, any Gemini call, images, Mac stages, Agent SDK app. Voice features dropped in the matrix.

## From you
Keys in `server/.env` (see `.env.example`), the deploy target, and confirmation of `voice-0.5.7` as the voice version to port. Part A needs none of them.
