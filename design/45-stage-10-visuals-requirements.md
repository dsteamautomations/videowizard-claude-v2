# 45 — Stage 10 (visuals) improvements: requirements (approved by SK 18 Oct 2026, implemented the same day; the prompt text awaits SK's reading before deploy)

Source: the stage 10 review run with the stage review prompt on 18 Oct 2026 and SK's decisions on its 9 findings. Measured on VW-3, which stands at this stage: the prompt is v1's ported word for word (12,940 words, no v2 command named); the plan proposed on 17 Oct asks for 19 animations and 1 diagram among 28 shots, which v2 cannot make; a video shot needs four yeses; the timing check is a millisecond; a 23.6 s shot is clamped to a 10 s take. Dropped by SK: contact sheets (10.8; design/27 is closed). Nothing here makes a paid call by itself. VW-3's plan v1 stays valid: the warnings of 10.2 and 10.7 are warnings, and `check` is free; the assistant re-presents the plan with the route counts and SK's answer to the animation question before accepting any gap.

## Decisions carried from the review
- The visuals prompt is rewritten for v2 at about 3,000 words; SK reads it before it ships (10.1).
- Image, diagram and animation shots are warned as the operator's files; the assistant asks once per run before proposing; AI stills or AI video by default (10.2).
- `vw visuals still --shot --ref` fills a still shot from an approved reference (10.3).
- Two yeses per shot: bind without a quote, select with the review; `accept --gaps all`, `record --gaps all` (10.4).
- `image --file`, `take --shots`, `status --wait`, worker backoff capped at 60 s (10.5).
- A take at least as long as its placement matches; notes only for a shorter one (10.6).
- A shot longer than the generator's maximum is warned at check and refused at prepare-take (10.7).
- The world evidence is written one clip per line (10.9).

## A. The rewritten prompt (10.1)
One document in `server/procedures/v2.json`, sentinel line first, about 3,000 words (test: at most 3,500), in this order:
1. **What this stage makes.** The gaps of the first cut; the four routes and who makes each: a frame or clip from the footage (free), a generated still (GPT Image 2.5, paid, informed), AI video from a generated keyframe (Omni 3–10 s by default; Kling 3–15 s, Seedance 4–30 s when chosen), a hand-made file from the operator (`vw visuals asset`). A shot of type image, diagram or animation is the operator's file unless it is filled by an approved still. The animation question of 10.2.
2. **Direction and treatment** (from DIRECTING BRIEF and ONE DIRECTION, ONE CONNECTED PROPOSAL, trimmed): the treatment first, in conversation, then scenes, shots and beats as one progression across the existing film; choices only where a real alternative exists.
3. **Plain language** (from CONCRETE MEANING WITHOUT JARGON and STRUCTURED, CONCISE PROPOSALS, trimmed): what the viewer sees, in complete sentences; each fact in one field; no labels or boilerplate in fields.
4. **Pictures against words** (from TREATMENT AND PICTURES AGAINST WORDS, THREE KINDS OF STATEMENT, WORLD COVERAGE, COMPLETENESS, trimmed): the whole visible world, every subject accounted for, states and beats that chain, continuity with the real footage on both sides.
5. **Elements and references** (from MATERIAL COVERAGE and REFERENCE SHEETS, trimmed): exact against representative identity; frames from clips first (`vw visuals frame`), the operator's files (`supply`), web images with SK's web rule (the warning, the operator's yes, their bytes and the URL, `web`), generated references last (`image`); every candidate shown and approved by hash.
6. **Shot images and video** (from SHOT IMAGES AND VIDEO and REVIEWED VIDEO REQUEST, trimmed): the packet, the keyframe composed with every subject in place, the motion prompt written after looking at the keyframe, every subject reconciled, the generator chosen with `vw visuals generator` when the default does not fit the length.
7. **Checks** (from CHECKS AND RECOVERY, the three lines that are about the plan): meaning, subjects, layout and scale, identity, continuity, placement timing; a take shorter than its placement needs timing notes; what the server enforces (tiling, beats, digests, hashes, one open job per shot) in one paragraph.
8. **Review of a take** (from RETAINED VIDEO REVIEW, trimmed): what to look at before showing it; the operator's yes selects it.
Dropped entirely: APPROVED LOCAL ASSETS AND EDITABLE TIMED GRAPHICS, EDITORIAL TIMING PROPOSALS, AUTHORIZED FRESH START, SELECTABLE VIDEO GENERATOR (replaced by one sentence in 6), OBJECTS DEPICTED WITHIN APPROVED PLACE REFERENCES (one sentence in 5: the selector), APPROVED PARENT INPUT HASHES, EDITABLE TEXT LAYERS, ASSEMBLED-MOVIE REVIEW CHECKPOINT, and every `visual-command`, `backend`, `connector`, `browser`, `Codex`, `local_assets` and `editable text` wording. `prompt_origin` becomes "design/45, written 18 Oct 2026 from v1 visuals-visual-1.18.0". SK reads the text (sent as a file) before the server deploy.

## B. Server changes (`server/`)

| # | What changes | Why | Where |
|---|---|---|---|
| 10.2 | `validate_plan` adds a warning per shot of type image, diagram or animation: "shot S (animation, 11.4 s): the operator supplies this file (`vw visuals asset`), or an approved still fills it (`vw visuals still`)". `check` and `propose` answer `routes: {video: n, still_or_file: n, seconds: {...}}`. | The stage must not stall on files nobody planned to make. | `visual_contract.py`, `visuals_stage.check`/`propose` |
| 10.3 | `POST /api/runs/{id}/visuals/still` {shot_id, reference_id, quote}: the reference must be approved and the shot of type image, diagram or animation in an accepted gap; the shot's asset becomes `{kind: 'still', key, sha256, bytes, reference_id, quote}`; a selected take for the shot is dropped as `add_asset` does. `record_gap` names the file `<shot>-asset.png` as today. | A generated still fills a shot without a download and upload. | `visuals_stage.still_from_reference`, `main.py` |
| 10.4 | `bind`: `quote` optional (stored when given); the approved references are the yes. `select_take(job_id, quote, notes=None)`: when `notes` is given, an accepted review with those notes is recorded first, then the selection (the same checks as today); without notes the latest review must be accepted, as today. `accept(gap_ids)`: `['all']` means every gap of the current version; a gap with choices and no selection is refused by name before anything is accepted. `record_gaps(gap_ids, quote)`: `['all']` records every accepted gap whose shots all have a selection or an asset and that is not recorded yet; answers `recorded` and `skipped` with the reason per gap; a named gap that is not ready is refused as today. | One yes per picture, one per take; gaps in one go. | `visuals_stage.bind`, `select_take`, `accept`, `record_gap` (+ `record_gaps`), `main.py` |
| 10.5 | `submit_takes(shot_ids)`: each shot checked and queued as today (an open job on one shot refuses that shot and queues the rest; the answer lists `queued` and `refused`). Worker backoff: `retry_in = min(1, 0.5 × polls)` minutes (30 s, then 60 s). | Many takes in one call; a finished take seen within a minute. | `visuals_stage.submit_take` (list), `main.py`, `visual_workers.process_take` |
| 10.6 | `timing_matches_placement = duration_seconds ≥ placement exact seconds − 0.001`; the evidence adds `shortfall_seconds` (0 when none). `review_take` requires `timing_notes` only when the take is shorter. | Takes are whole seconds; assembly trims. | `visual_workers.process_take`, `visuals_stage.review_take` |
| 10.7 | `validate_plan` warns per video shot longer than the default generator's maximum: "shot S is 23.6 s; the default generator makes at most 10 s: split it, or choose Seedance (up to 30 s) with `vw visuals generator`". `prepare_take` refuses when the exact placement exceeds the chosen generator's maximum ("shot S is 23.6 s, longer than Gemini Omni's 10 s: split the shot or choose another generator") instead of clamping; rounding up to the minimum stays. | No silent 10 s take for a 24 s shot. | `visual_contract.py`, `visuals_stage.prepare_take` |
| — | `SERVER_VERSION` 0.11.0 → 0.12.0. | | `config.py` |

## C. Plugin changes (`plugin/`)

| # | What changes | Why | Where |
|---|---|---|---|
| 10.3 | `vw visuals still --shot S --ref R --quote "…"`. | | `vw.py` |
| 10.4 | `bind` sends the quote only when given; `select --job J [--notes "…"] --quote "…"`; `accept --gaps all`; `record --gaps G1 G2 … \| all --quote` (the old `--gap G` keeps working). | | `vw.py`, parser |
| 10.5 | `image --file out/images.json`: a list of `{element, kind, prompt, name?, parents?, size?, quality?}`, one request each in order, stops at the first refusal and answers `queued`, `refused`, `remaining` (as `master decide --file`). `take --shots S1 S2 …` (or `--shots all` for every prepared shot without an open job). `status --wait N`: polls `GET visuals` every 15 s until no job is queued, running, submitted or storage_pending, or a job is failed, rejected, cancelled or submission_unknown, or N seconds pass; the line: "2 images, 3 takes open; 1 take ready" / "all done: 8 ready" / "2 need a decision: J1 (failed: …), J2 (submission_unknown)". | One submit and one wait per batch. | `vw.py` `cmd_visuals`, parser (`--shots`, `--wait`) |
| 10.9 | `_download` writes `work/visuals-package.json` through the reading-copy writer with `world_evidence` one clip per line (no keys dropped). | Far fewer lines. | `vw.py` `_download`, `reading_copy` (rows argument) |
| — | `plugin.json` 0.10.0 → 0.11.0. | | `.claude-plugin/plugin.json` |

## D. Procedure text (`server/procedures/v2.json`, visuals `steps`)
1. "Run `vw visuals prepare`: it downloads work/visuals-package.json (the world evidence one clip per line) and the direction prompt in work/visuals-package.prompt.md; read both."
2. "Before authoring, settle the treatment in conversation. Author out/visual-plan.json (foundation, elements, gaps with scenes, shots and beats). `vw visuals check --file …` until valid; it answers the routes: how many shots are AI video, how many need a still or a file. Then ask the operator one question, once per run: 'N shots are planned as hand-made animations or diagrams: shall the editor make them, or shall I plan them as AI stills or AI video?' Without a choice for hand-made work, plan them as AI stills (`vw visuals still`) or AI video and check again. `vw visuals propose --file …`; present the treatment and each gap; `vw visuals select --gap G --choice C` where offered; `vw visuals accept --gaps all --quote "…"` (or the gaps they named)."
3. "References per element, in this order: a frame from a clip (`frame`, free), the operator's file (`supply`), a web image (propose the search with the warning; on their yes search; they download the picture; `web --file --url --quote`), a generated image (`image --file out/images.json` for several at once, or `--element … --prompt …`; paid OpenAI GPT Image 2.5; inform, do not ask). `vw visuals status --wait 300` while images generate. Show each candidate (`fetch --ref`) and record their yes: `approve --ref R --sha <sha> --quote "…"`."
4. "Per shot: `bind --shot S --refs E1=R1,R2 E2=R3` (no quote: the approved references are the yes), `packet --shot S`. Video shots: `generator --shot S --provider --model` only when the shot is longer than the default makes (the check warns); `prepare-take --shot S --start R --motion "…" --subject E1="…"` for each; then `take --shots all` (paid; inform) and `status --wait 600` until every take is ready; `fetch --job J`, let the operator watch, and on their yes `select --job J --notes "<what you checked>" --quote "…"`; on a no `review --job J --decision rejected --notes "…" --quote "…"` and prepare again. Still shots: `still --shot S --ref R --quote "…"` with an approved picture. Hand-made files: `vw upload --stage visuals --file out/x.mp4` then `asset --shot S --file out/x.mp4 --kind movie --quote "…"`."
5. "`vw visuals record --gaps all --quote "<their yes>"` records every gap whose shots are done; repeat as the rest finish. `vw next` moves on when all gaps are recorded."
vw.md's visuals paragraph follows the same wording.

## E. Unstated but expected
- A 0.10.0 plugin against the 0.12.0 server: every old command still works (`bind` with a quote, `record --gap`, `take --shot` through the single path, the old timing rule only tightened in the assistant's favour).
- VW-3 continues on its plan v1: `check` shows 20 shots as the operator's files; the assistant asks the animation question; on an AI answer it re-plans those shots and proposes v2.
- The animation question is asked once per run; the answer is written into the plan's `foundation.production_constraints` as a rule so a later check and the record carry it.
- `status --wait` never submits, recovers or resolves.
- The still from a reference is the approved PNG as stored; assembly contain-pads and holds it, as for an uploaded still.
- The prompt rewrite changes no schema; a plan valid today stays valid.

## F. Edge cases
| Case | Expected |
|---|---|
| plan with 19 animation, 1 diagram, 8 video shots (VW-3) | `check` valid with 20 route warnings and `routes: {video: 8, still_or_file: 20}` |
| a 23.6 s video shot with the default generator | a warning at check; `prepare-take` refused naming 10 s and Seedance; with Seedance chosen, prepared at 24 s |
| a 2.2 s video shot | prepared at 3 s (the minimum), no refusal |
| `still --shot S --ref R` with R a candidate, not approved | refused |
| `still` on a video shot | refused: "a video shot takes a take; use `prepare-take`" |
| `bind` without a quote, all references approved | bound; with one candidate reference → refused as today |
| `select --job J --notes "…" --quote "yes"` on a ready take with no review | an accepted review recorded, then selected |
| a take of 4.0 s for a 3.4 s placement | `timing_matches_placement: true`, `shortfall_seconds: 0`; `select` without timing notes allowed |
| a take of 3.0 s for a 3.4 s placement | false, shortfall 0.4; `select`/`review accepted` without `--timing` refused |
| `accept --gaps all` with one gap having choices and no selection | refused naming it; nothing accepted |
| `record --gaps all` with 3 of 21 gaps complete | 3 recorded, 18 skipped with "shot S has no selection or asset" |
| `take --shots all` with one shot's job open | the others queued, that one listed under `refused` with JOB_OPEN |
| `image --file` with the second entry naming an unknown element | first queued, stops; `remaining` lists the rest |
| `status --wait 600` while 3 takes run | polls every 15 s; returns when all are ready or one fails; the line counts them |
| worker polling a take | retries after 30 s, then every 60 s |
| the rewritten prompt | ≤ 3,500 words; none of the v1 words; names `vw visuals frame`, `image`, `still`, `take`, `select`, `asset`, `record` |

## G. Tests (written first)
Layer one, `plugin/tests/test_visuals_cli.py` (new): `image --file` in order with a stop; `take --shots all` and a list; `status --wait` (ready, a failed job, expiry); `still`; `bind` with and without a quote; `select` with notes; `accept`/`record` with `all`; the reading copy of the visuals package writes `world_evidence` one clip per line and keeps every key; the steps and vw.md carry the new wording; the prompt's word count and forbidden words.
Layer one, `server/unit/test_visuals_pure.py` (new, no database): `validate_plan` route warnings and length warning on a synthetic plan; the timing rule (`timing_evidence(duration, placement)` as a pure function); the backoff function.
Layer two, `server/tests/test_visuals.py` (Docker): V11 rewritten for the new rule; `still` from an approved reference and its record; `bind` without a quote; `select` with notes; `accept all`, `record all` with a skipped gap; `take` on a list with one open job; `prepare-take` refusal over the maximum.

## H. Not covered
- `server/tests` cannot run on this Mac; compile check only until a Docker machine runs them.
- The rewritten prompt's effect on plan quality: SK reads it before deploy and judges it on VW-3's re-plan.
- Provider waits, costs and failure rates are still unmeasured on this server.

## I. Deploy order
1. The rewritten prompt sent to SK as a file; SK's yes on the text.
2. Server (`deploy-server.sh`, workers restart): tell SK first.
3. Plugin (`deploy-plugin.sh`); the operator restarts Claude Code.
4. design/35: a row; design/27 marked closed.

## J. Estimate
The prompt: a day. Server with tests: a day. Plugin with tests: half a day. Deploys: an hour.
