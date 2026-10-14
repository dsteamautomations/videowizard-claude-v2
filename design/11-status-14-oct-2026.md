# 11 — Build status, 14 Oct 2026 (slices 1–7 of design/02 §9)

Built = code, tests and push done. Live = exercised against the real services or in your VW-1 run. Open = what remains inside the slice.

| # | Slice | Scope | Built | Tests | Live | Open |
|---|---|---|---|---|---|---|
| 1 | Core | tables, runs, `next`, stage outputs with chat acceptance, view/revise, attempt caps → 409, idempotent `request_id`, v1 login | ✅ | test_core 30, test_auth 3 | ✅ VW-1 (login, start, acceptance quotes) | — |
| 2 | Plugin + web UI | connect flow, server-rendered pages (login, connect, runs, run, defects list), `/vw:vw` command, `vw.py`, guard hook, operator CLAUDE.md, claim/pull/close | ✅ | test_web 8, test_plugin 16 | ✅ VW-1 (connect, runs page, defect filed) | `vw pull` on the Mac untried (needs slice 6); defects page is list-only |
| 3 | Text + voice + media | intake (titles, line removal), brief (questions/answers), script (before/after changes), voice (ElevenLabs catalog, auditions, narration with timing), media (probe, dedupe, 200 MB signed upload) | ✅ | test_stages_text 7, test_voice_media 10 | ✅ VW-1 through voice narration; media 46 clips uploaded; 200 MB upload verified | voice stage record and media record still to be exercised by you in VW-1 |
| 4 | Analysis + planning | one Gemini 4 Argon job per clip (v1 prompt and evidence gate), caps and recovery, 3 concurrent; planning on the v1 plan contract (scenes, draft, questions, inspections, ledger, finalize, handoff) | ✅ | test_analysis 14, test_planning 5 | analysis ✅ running now in VW-1 (13 retained, 3 running, 30 queued at the time of writing); planning not yet live | planning stage live run; `VW2_WORKERS` setting so workers are not started by hand |
| 5 | Visuals | direction plan (v1 contract v3), references (frame/supplied/web/OpenAI GPT Image 2.5), bindings, video takes (Google Omni default, Higgsfield optional), local assets, one output per gap | ✅ (today) | test_visuals 5 (V1–V18 except cancel) | ❌ providers faked; OpenAI key and model ids validated only; Google video model visible on the account | live smoke of one image and one take before you reach the stage; take cancel deferred |
| 6 | Mac stages | edit, first cut, assembly, delivery via `/vw pull` on the Mac; assembly machine asked here | ❌ not started | — | — | whole slice; design doc first (requirements list → your approval) |
| 7 | Defects admin | resolve/close defects, admin release of stuck jobs, page actions | ❌ not started (table, filing and listing exist from slices 1–2) | — | defect 1 filed in VW-1 and still open | whole slice (small) |

Slices 8 (Agent SDK operator app) and 9 are out of scope by your decision today.

## Walkthrough fixes today (all pushed)

| Found in VW-1 | Fix |
|---|---|
| start asked for title and free-text client | client from the shared Active directory, title chosen at intake (v1 flow) |
| start asked three pre-flight questions | removed; files asked for by intake/media, assembly machine at slice 6, spend caps a one-time note |
| drift check intake→media (design/10) | brief required questions, script change shape, voice and media prompts ported, contiguous excerpt, ≤ 6 auditions |
| narration failed on a 0.16 s MP3 padding overshoot | tolerance 1 s, overshoot recorded; recover re-processes a retained response without paying |
| analysis one clip at a time | three worker processes; server cap 3 holds |

## Traceability (design/05)
55 rows: 30 ticked, 14 dropped by agreement, 11 open. The open rows are all slice 6 and 7 (F-26–F-29, F-36, F-37, F-40 and the procedure-publishing admin).

## Next
1. You finish VW-1 to the end of planning; I fix what the run shows, in one batch.
2. Live smoke of one image and one video take (visuals) before you reach that stage.
3. Slice 6 requirements list for your approval, then build; slice 7 with it.

## Addendum, 14 Oct 2026 late: implementation run (design/13 §4 order)

| Step | What | State |
|---|---|---|
| 0 | real VW-1 fixtures; defect 2 fixed at the producer; one word rule; `VW2_WORKERS` | done, pushed |
| 1 | Flash 3.8, HIGH, AGENTIC, no temperature; inspection model from the procedure; token details in cost | done, pushed, live smoke passed |
| 2 | script beats; brief production inputs; per-beat narration durations; media probe fields + VFR transcode | done, pushed |
| 3 | clip-log-v1 contract: schema (strict + wire), prompt, Stage 1.5 solver, gate, summary card, `vw analysis show`, `vw analysis policy` (unpaid re-solve); procedure version 2; planning refuses v2 runs until step 4 | code done; live schema probe accepted; pipeline tests running |
| 4 | Stage 2A/2B replaces planning | next; requirements list to write |
| 5 | assembly + delivery, Resolve once | after 4 |
