# design/87 — Builder handoff, 23 Oct 2026: where the build stands, for a new Claude Code login

Written when SK moved the builder session to another Claude account (same PC, same folders). A fresh session reads this first, then `CLAUDE.md`, then `design/72` for the deploy steps on this PC.

## 1. Live and pushed

| | Server | Plugin | Commit |
|---|---|---|---|
| Live on the VM (deployed 22 Oct night) | 0.31.0 | 0.29.0 | c6f42b5 |
| Pushed to `main`, **not deployed** | 0.32.0 | 0.30.0 | 7667563 (design/86) |

Tests at 7667563: `server/unit` 191 pass; `plugin/tests` 228 pass plus the 3 known Windows-only failures (test_intake ×2, test_start_defect_paths). Deploy only on SK's word; after a deploy: a row in design/35, a line in design/49, the findings file.

## 2. What design/86 does (built, waiting for the deploy word)

From the VW-6 image review (`../image-generation-review-2026-10-23.md`, 11 of 24 keyframes right the first time). SK approved all seven corrections on 23 Oct.

- **K1** the end prompt posted with its start (`--end-answer`, row `end_answer`); the server queues the end itself when the start is approved (`approve_reference(..., conn)`), once.
- **K2** `server/app/image_check.py`: after an image job is retained, Gemini Flash reads the candidate against its answer form's checklist plus three fixed lines; the code checks size and parent; a must failing queues one fix round (`fix_of`), never twice, never for a fix; a check error never blocks. Called from `visual_workers.finalize_image`.
- **K3** the Takes step: one turn line per video shot (whose turn, how long) and a counter at the top (`shotState` in `visuals.html`).
- **K4** `--variants 2` for a start keyframe: two jobs, names `-a` / `-b`.
- **K5** `library.check_prompt` refuses an edit whose "Change only:" holds more than two sentences.
- **K6** `end_targets` in the packet: each subject's end state as one sentence.
- **K7** `context` in the packet: the gap's words, the treatment's picture line, the intended visuals, the neighbouring shots' boundary states, earlier rejections. For the assistant only, never sent to the image model. `prepare` now copies the intended visuals onto the session.
- **K8** `exact_patterns` in the packet; the step says an exact object gets one close reference.
- **K9** `vw visuals feedback` opens with rounds per approved picture, per kind.

Not verified: Gemini's judgement on real pictures (VW-7 is the check); the page in a browser; `server/tests` (Docker).

## 3. Open, in order

1. **Deploy design/86** (server 0.32.0, plugin 0.30.0) on SK's word; the operator restarts Claude Code afterwards. `gcloud auth login` first: the token had expired on 23 Oct.
2. **design/85 G4**, Omni's scene extension, its own note and deploy (specified in design/85).
3. **VW-6**: the seven takes were to be prepared again with `--continuity` and taken again (text given to SK on 22 Oct); the visuals outputs recorded with placeholder stills during the dry run must be reset by the builder before real takes are recorded, on SK's word.
4. **L51** Gemini analysis cost against Google's billing export for 20 Oct.
5. **L9** the library handoff after a full stage.

## 4. Where things are

- Repo: `C:\Coworkspace\Review Videobuilder Tool\videowizard-v2` (GitHub `dsteamautomations/videowizard-claude-v2`, `main`).
- Reports beside the repo in `C:\Coworkspace\Review Videobuilder Tool\`: `vw6-pass-findings-2026-10-22.md` (L32–L54), `image-generation-review-2026-10-23.md`, `ai-video-pipeline-2026-10-22.md`, `parallelism-audit-2026-10-22.md`, `vw6-image-prompts-2026-10-22.md`.
- Design notes this week: 73 to 86. The release record is design/35 (last row 72), the live-run log design/49.
- The previous session's full transcript (if ever needed): `C:\Users\Deepa\.claude\projects\C--Coworkspace-Review-Videobuilder-Tool\c82dbf31-2aef-4461-b390-03faef416617.jsonl`.

## 5. SK's standing rules (also in memory)

No local server or local operator: deploy to the VM and test there. Run both pytest suites separately before every push and check the real exit code. One question per message. Never print or commit secrets. Requirements note and SK's go before code; a "not covered" list with every piece of work.
