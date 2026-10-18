# 40 — Narration segmentation for long scripts: requirements (approved by SK 18 Oct 2026, implemented the same day)

Source: stage 4 review finding 4.3 and SK's decisions of 18 Oct (design/35 rows 25–26): warn now, segment as its own piece of work right after the stage 4 batch, before the stage 5 review. Server only. Paid: each piece is one ElevenLabs request, so a long script costs the same characters as it would in one request; nothing is synthesised twice.

## The problem
Eleven v4 accepts 10,000 characters per request (the other models are of the same order). The server refuses a longer narration, the prompt forbids splitting, and the script stage now warns (design/39). VW-3's script was 4,777 characters, about five minutes of speech; a ten-minute film sits at the limit and a longer one has no path. The rest of the system, options, subtitles and the Resolve timeline, consumes one narration file and one timing file keyed on words with passage ids, and must keep doing so.

## What changes, in one paragraph
A narration whose text exceeds the model's per-request limit is synthesised as consecutive **pieces**, split at paragraph boundaries (sentence boundaries inside a paragraph that is itself too long), each a separate timed request journaled before anything else under a key derived from the piece's identity. The worker then concatenates the pieces' audio into one MP3 with one re-encode, measures each piece's decoded duration, offsets the pieces' character timings and builds the same timing file as today over the full text. One job row, one narration file, one timing file, one cost. A killed worker resumes at the first piece not yet journaled; a piece's unknown outcome stops the job with everything already journaled retained, and a new narration of the same text, voice, model and settings reuses the journaled pieces instead of paying for them again.

## A. Server changes (`server/`)

| # | What changes | Where |
|---|---|---|
| S1 | New module `narration_pieces.py` (stdlib only, importable without the database): `split_for_narration(text, limit)` → list of piece texts: split at paragraph separators (`\n\s*\n`) packing whole paragraphs under the limit in order; a paragraph over the limit is split at sentence ends (`. ! ?` followed by space) packed under the limit; a single sentence over the limit raises `ValueError` (refused at submission as today, `VOICE_LENGTH`). The pieces, joined by the separators that were cut, reproduce the text exactly (the function returns the pieces with their character offsets into the full text). `piece_identity(snapshot, piece_text)` → sha256 over voice_id, model_id, settings, format, text. `merge_alignments(full_text, pieces)` where each piece carries its offset, its alignment and its decoded duration → one alignment over the full text: each piece's character times shifted by the sum of the previous pieces' decoded durations; the separator characters between pieces take the boundary time; `normalized_alignment` likewise when every piece has one, else omitted. | server/app/narration_pieces.py |
| S2 | `submit_voice`: for a narration, `pieces = split_for_narration(text, available['max_characters'])`; the snapshot gains `pieces: [{offset, characters}]` (texts derived from the text, not stored twice); the length refusal applies only when splitting fails. Auditions unchanged. | server/app/jobs.py |
| S3 | `process_voice` for a timed narration iterates the pieces: journal paths `SPOOL/piece-<identity>.response.json` and `.mp3` (shared across jobs with the same identity); a journaled piece is never synthesised again; each response decoded, checked as MP3, journaled; after the last piece: `concat_mp3(piece_paths, out_path)` with ffmpeg (concat demuxer, one re-encode to mp3_44100_128), `inspect_audio` on every piece and on the result, `merge_alignments`, then `timing_evidence`, `clamp_words`, `check_words` exactly as today on the merged alignment; cost = the sum of the pieces' `character-cost` headers (fallback: the snapshot's characters). A one-piece narration takes the same path, so there is one code path. Headers kept per piece in `piece-<identity>.meta.json`; the job's result gains `pieces: [{identity, characters, duration_s, request_id, history_item_id}]`. | server/app/worker.py |
| S4 | Failure per piece: provider rejected → job `failed` (pieces journaled so far retained); provider unknown → job `submission_unknown` with `result.pieces_done` set; the recovery rule stays: history audio has no alignment, so a narration is narrated again, and S3's identity journal makes the re-run pay only for the missing pieces. `recover_voice` for a narration says so in its message. `storage_pending` retries as today. | server/app/worker.py |
| S5 | The 20-minute lease: a job renews it after every piece (`update vw2_jobs set lease_until = now() + 20 min where id = …`), so a five-piece narration cannot be re-claimed while it is still working. | server/app/worker.py, jobs.py |
| S6 | Voice prompt: the sentence "If the whole script exceeds the model's limit…" is gone already (design/39); add one: "A long script is narrated in pieces and joined by the server; nothing changes for you." Script-stage warning text (design/39 4.3): "The script has N characters; it will be narrated in P requests and joined." (plugin, one line). | procedures/v2.json, plugin/scripts/stages_text.py |
| — | `SERVER_VERSION` 0.6.0 → 0.7.0; `plugin.json` 0.5.0 → 0.6.0 (the warning text only). | config.py, plugin.json |

## B. Unstated but expected
- Pieces are synthesised one after another in the worker. Parallel pieces would need the provider's concurrency limit confirmed from ElevenLabs's documentation first (design/35 rule 11's logic); listed as a later lever, not done here.
- The re-encode is one LAME pass over the concatenated decode; the encoder delay at the start is inside the clamp tolerance the timing already allows; the pieces' own padding is inside their measured durations, so word times never run past the audio.
- A word is never split: pieces end at paragraph or sentence ends, and the word regex runs over the full text, so passage ids and word ids are identical to a one-request narration of the same text.
- The subtitles and the Resolve timeline read only the merged timing; they do not change.
- Storage keys and file names are unchanged (`narration.mp3`, `.timing.json`); the result's `pieces` list is additional.
- Old journal files keyed by job id (today's scheme) are read for jobs that are already `storage_pending` at deploy time; new jobs use the identity scheme. No such job exists today.

## C. Edge cases
| Case | Expected |
|---|---|
| 4,777-character script (VW-3) | one piece; result identical to today's, plus `pieces` with one entry |
| 24,000 characters, nine paragraphs | three or four pieces at paragraph ends; one MP3; words for every passage; cost = sum of the pieces |
| one paragraph of 12,000 characters | split at sentence ends into two pieces |
| one sentence of 10,500 characters | refused at submission: "one sentence exceeds the model's limit; split it in the script stage" |
| worker killed after piece 2 of 4 | resume synthesises pieces 3 and 4 only (two provider calls) |
| provider unknown on piece 3 | job `submission_unknown`, pieces 1–2 journaled; a new narration of the same text and voice pays for pieces 3–4 only |
| provider rejects piece 1 | job `failed` with the provider message; nothing journaled |
| ffmpeg concat fails | job `storage_pending` (pieces retained), retried in 10 minutes, never re-synthesised |
| narration text changed after a failed attempt | different identities; nothing reused |
| audition of 3,000 characters | unchanged path |

## D. Tests (written first)
Pure, no database, run on this Mac from a new folder `server/unit/` (its own conftest, no Docker; needs `pydantic-settings` and `httpx` in the `.venv`): `split_for_narration` on every row of §C's first four cases plus exact round-trip of pieces to text; `piece_identity` stable and different per voice/model/settings/text; `merge_alignments` on two synthetic pieces (offsets, separator times, monotonic order, `validate_alignment` passes, `timing_evidence` words cover all passages). The concatenation test (`concat_mp3` + `inspect_audio` durations add up within the tolerance) needs ffmpeg, which this Mac has at `~/.local/bin`, so it runs here too.
Docker layer, `server/tests/test_voice_media.py`: V5 long script (three pieces with the fake provider, which returns a 2-second tone per piece): result `pieces` has three entries, `duration_s` about 6, timing words span all passages, cost is the sum, `FakeEleven.calls` shows three synthesis calls; V6 kill after piece 1 (mode switches to unknown on the second call): job `submission_unknown`, `pieces_done` 1, then a new narration makes two calls only; V7 one sentence over the limit refused at submission; V1 unchanged (one piece).

## E. Not covered
- Docker tests run elsewhere; on this Mac `server/unit` runs in full, concatenation included.
- ElevenLabs's per-plan concurrency is not consulted; pieces are sequential.
- A live long narration on the VM is the only proof of the MP3 join's audibility; the first long script is listened to with that in mind.

## F. Deploy order
1. Server (`deploy-server.sh`, workers restart): tell SK first.
2. Plugin (`deploy-plugin.sh`) for the warning text; the operator restarts Claude Code.
3. design/35: a row.

## G. Estimate
About one day: S1–S3 half a day, S4–S5 and the tests the rest. Deploys an hour.
