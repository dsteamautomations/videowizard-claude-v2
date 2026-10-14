# Slice: analysis (Gemini 4 Argon) + planning — requirement list for approval

Source for what v1 did: `_work/v1-late-stages-spec.md` (extracted 14 Oct 2026 from the latest v1 definitions, modules and incident docs). This is the first of the two stages where v1 broke; every v1 failure mode is mapped to a v2 mechanism in §5.

Two checkpoints inside one slice: **A** analysis (worker, paid), then **B** planning (chat model is the planner; server checks the contract; one paid inspection path).

---

## A. Analysis: one Gemini 4 Argon request per clip

### What is built
| Part | Content |
|---|---|
| Procedure content | v1 `analysis-0.7.6` prompt blocks 1–6 (≈37 k chars) and the evidence schema `source-evidence-v2.schema.json` + extensions (`additional_analysis`, `claim_evidence`, `world_markers`, `evidence_limits`) ported **verbatim** into `procedures/v1.json` under `analysis`. Template tokens (`[FILM_TYPE_OR_UNSPECIFIED]`, `[COMPLETE_SCRIPT_WITH_PASSAGE_IDS]`, …) filled by the server from the brief, script and media outputs. |
| Start | `vw analysis start` asks the operator four things and passes them as flags: camera audio in the film (allowed / excluded), let the model hear audio (yes / no), film type (free text), anything to exclude (clip names or none). One call creates one job per clip (`unit = media id`), paid, informed. |
| Provider call | `gemini-4-argon`, `thinking_level: MEDIUM`, `media_resolution: HIGH`, JSON output constrained by the schema, `max_output_tokens 65536`, Files API upload of the original (or an `-an` silent copy when audio is not to be understood). Video processing: `static` for clips ≤ 5 min (1 fps, frame-level timestamps), `agentic` above 5 min; per-run override. No `temperature` (ignored by Argon). Flex inference if the generate endpoint accepts it; confirmed at build. |
| Gate, not repair | v1's `derive()` + `usable_view()` ported: identity gate (envelope and source identity must equal the request) → schema gaps → content gaps → salvage independent valid rows → `evidence = {usable, excluded_rows, …}`. Planning only ever reads `usable`. |
| Storage | **Nothing large in a row.** Per clip: `analysis/<media>.response.json` (raw, journaled locally first, then stored), `analysis/<media>.evidence.json` (≈100 KB). The job row holds status, digests, usage, cost; the stage output per unit lists the two files and a small summary (counts of usable rows, coverage, gaps, descriptive name). |
| Worker | the existing jobs loop gains a `gemini` family: claim with lease (45 min, renewed on each phase), phases download → (silent copy) → upload → generate (streamed) → gate → store → stage output. Local fsync receipt after each phase so a killed worker resumes from the last receipt, never re-pays. Global cap 3 concurrent generations (Tier-1 spend ceiling), per-run cap 4, runs take turns. |
| Outcomes (defined once) | `retained` (JSON parsed, identity ok) · `retained_unstructured` (text kept, not JSON; terminal) · `rejected` (provider 4xx; terminal) · `failed` (terminal: empty/incomplete/identity mismatch) · `submission_unknown` (dispatched, outcome unknown) · `storage_pending` (result journaled, store retry only). Only `retained` produces a stage output. |
| Retries | automatic: one capacity retry (429/503 before any partial output, backoff 5→60 s). Everything else is explicit: `vw analysis retry --unit <id> --note "…"` for terminal failures (max 3 per clip, server-counted → `NEEDS_USER_DECISION`); `vw analysis recover --unit <id>` re-reads receipts for `submission_unknown`/`storage_pending`; `vw analysis resolve --unit <id> --note` sets aside an unknown attempt after the operator checked the account. A failed clip never pauses its siblings. |
| Operator view | `vw analysis status` (per clip: status, phase, elapsed, cost), `vw analysis show --unit` (summary + limitations), run page lists clips with status. Descriptive name shown; renaming dropped (matrix F-20). |
| Deploy safety | worker handles SIGTERM by finishing the current phase receipt and releasing its lease; the server's `GET /api/admin/jobs` + `POST /api/jobs/{id}/release` (admin) replaces v1's hand SQL for stuck claims. |

### Unstated requirements in scope
1. Job identity = digest(run, clip sha, script digest, brief digest, prompt digest, schema digest, audio policy, film type, exclusions). Same inputs → same job → result reused; `reanalyze` needs an explicit `--again` and no open job.
2. A clip over 200 MB or over 1 h is refused at media stage, not here. A clip with no audio track gets `audio: no_track` without failure.
3. Evidence files are retained on close (they are the planner's input and the record of what was paid for).
4. Cost recorded per clip from usage metadata (input/output tokens, model); shown in status.
5. `next` reports `units_open`, `units_done`, `units_failed`; the stage completes when every non-excluded clip is `retained` or explicitly set aside (`vw analysis exclude --unit --note`, recorded in the stage summary so planning knows).

### Edge cases (tests; provider faked)
| # | Case | Expected |
|---|---|---|
| A1 | 3 clips, all succeed | 3 jobs → 3 unit outputs; `next` = planning; evidence files in storage; cost on each |
| A2 | worker killed after upload receipt, before generate | restart resumes at generate; one upload, one generate |
| A3 | worker killed after generate, before store | restart resumes from the journaled response; **no second generate** |
| A4 | provider 429 once, then OK | one automatic retry, then retained |
| A5 | provider 429 three times | `rejected`; no automatic third attempt; `vw analysis retry` counts toward the cap |
| A6 | response is text, not JSON | `retained_unstructured`, no auto-resubmit, operator told |
| A7 | response identity mismatch (wrong source id) | `failed`; retry allowed |
| A8 | response with 2 invalid rows out of 40 | retained; `excluded_rows` lists the 2 with reasons; usable has 38 |
| A9 | lease expires (worker vanished) | job → `submission_unknown`; recover finds the receipt → `storage_pending` → retained |
| A10 | 6-minute clip | request uses `agentic`; 2-minute clip uses `static` |
| A11 | `understand_audio = no` | silent copy uploaded; prompt carries the audio-removed note |
| A12 | same inputs, `start` again without `--again` | no new job; existing results reused |
| A13 | 10 clips, global cap 3 | never more than 3 generating at once; all complete |
| A14 | one clip excluded by the operator | stage completes with 2 outputs + 1 exclusion in summary |

---

## B. Planning: the chat model plans, the server checks

### What is built
| Part | Content |
|---|---|
| Procedure content | v1 `editing-0.8.3` planner prompt and `inspector_prompt`, the plan contract `direct-gemini-edit-v3`, `flash_schema` and `assessment_schema` ported verbatim. |
| Settings | `vw stage planning prepare` first asks: output fps (24/25/30), resolution, and the workflow-situation answers that matter (camera audio under b-roll: avoid/allow; still images allowed: yes/no; anything else from v1's 13 fields only if the prompt references it). Stored verbatim in the stage summary. |
| Package | server builds `planning-package.json` on demand (inputs: brief, script passages, narration `timing.json` bound to the script, media list, per-clip `evidence.usable` views) and stores it as a file; the plugin downloads it to `work/`. Never a DB blob. |
| Scene groups | the model proposes word-range scenes from the narration timing; the operator confirms in chat (`vw planning scenes --file out/scenes.json --quote`). This is the only passage route (v1's three routes collapse to this one). |
| Draft | the model writes `out/plan.json` (`direct-gemini-edit-v3`); `vw planning check` runs the ported mechanical validator locally **and** on the server: shots tile `duration_frames`, natural-speed equality, integer decimation, crop inside source at output aspect, every video shot cites ≥1 usable evidence row of the same source overlapping its interval, gaps carry a basis, pauses only at passage ends, combinations and alternative_review cover every passage, review cards readable. Invalid → refused with the list (counts as an attempt, cap 3). |
| Clarification | questions in the draft are routed: `user` → asked in chat (`vw planning answer`), `mechanical` → computed by the server (source range / crop / pause arithmetic), `inspect` → unpaid frame extraction (`vw planning frames`, PyAV, ≤24 stills) or **paid** inspection (`vw planning inspect --question`, Gemini 4 Argon on ≤3 clips or the stills, informed not gated). Answers accumulate into the ledger the server derives. |
| Revision & finalize | `vw planning revise --file out/plan.json` (any number of versions; each immutable, digest-chained to the ledger) then `vw planning finalize --file out/assessment.json` (7 flags, component reviews for every video shot, remaining limitations) → stage output `plan.json` + `ledger.json` + `assessment.json` + `certificate` summary {plan_digest, ledger_digest, fps, resolution, gaps[]}. Acceptance: the operator's yes in chat. |
| Handoff | `GET /api/runs/{id}/planning/handoff` = compiled edit (`compiled-edit-v2`: shots in seconds with source sha/fps, narration pieces, pauses, mapped words) for the Mac slice. Narration pieces are **frame-aligned before export** (v1's open Resolve precision bug). |

### Unstated requirements in scope
6. Plan files are stored as retained files; the row holds digests. The 32.9 MB read and 6–8 MB commit of v1 cannot recur because nothing is read except `usable` views and nothing is written except files + digests.
7. `revise` of planning reopens at the draft with the previous plan available (`vw view --stage planning`); analysis is untouched. Revising media/analysis after a plan marks the plan stale (slice-1 rule; planning is paid only through inspection, so the cost list is small).
8. Paid inspection is informed, not gated; capped at 10 questions per plan version.
9. The planner prompt is the model's whole instruction; the server never calls a model for planning.

### Edge cases (tests)
| # | Case | Expected |
|---|---|---|
| P1 | plan whose shots do not reach `duration_frames` | refused: gap listed with frames missing |
| P2 | shot speed mismatch (source 50 frames @25 vs timeline 60 @30) | refused: natural-speed rule |
| P3 | shot cites evidence of another clip | refused: evidence overlap |
| P4 | crop outside source | refused |
| P5 | pause not at a passage end | refused |
| P6 | three invalid drafts | fourth → `NEEDS_USER_DECISION` |
| P7 | scene groups covering words out of order | refused |
| P8 | mechanical question (crop arithmetic) | answered by the server without the model |
| P9 | paid inspection on 2 clips (faked) | job → retained answer; ledger lists it; cost recorded |
| P10 | finalize with a shot lacking component reviews | refused naming the shot |
| P11 | revise planning after finalize | new version; certificate regenerated; later stages stale |
| P12 | narration timing whose words mismatch the script | prepare refused: binding error names the passage |
| P13 | handoff narration pieces | every piece start/end on a frame boundary at the output fps |

---

## 5. v1 failure modes → v2 mechanism

| v1 failure (spec §1.6 / §2.5) | v2 |
|---|---|
| Deploy killed worker; stale claims blocked both runs for hours | lease + phase receipts + SIGTERM drain; admin `release` instead of SQL |
| Statement timeouts: 32.9 MB analysis rows, 5 MB enqueue batches, 6–8 MB state commits | rows carry digests; raw/evidence/package/plan are files; `usable` views read per clip |
| 512 MiB backend OOM restoring planning state | nothing restored; files fetched on demand by the plugin |
| Receipt persistence failures → uncertain attempts | local fsync receipt per phase; idempotent finish |
| Recovery semantics patched 4 times | six outcome classes defined once (§A); explicit commands per class |
| Three passage/scene routes | one: operator-confirmed scene groups |
| No route for corrections after the single revision | unlimited digest-chained versions |
| Resolve rounding of fractional narration pieces | pieces frame-aligned in the handoff |
| 50 MB storage cap discovered mid-run | preflight at `start` (already) + media stage limit |

## 6. Not in this slice
Mac execution, review render, first cut (next slice after visuals, unchanged order unless you prefer Mac first); video naming; v1's payload-offload flags (unneeded); any provider other than Gemini.

## 7. From you
- `VW2_GEMINI_API_KEY` in `server/.env`, and the **Gemini API tier** (Tier 1 has a $10 / 10-minute ceiling; the global cap of 3 is sized for it).
- Confirm the four analysis questions above are the ones you want asked (v1 had 13 situation fields; I trimmed to those the prompt uses).
- Confirm order: visuals next, then Mac stages (or swap).
