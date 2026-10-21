# design/60 — L18 scenes need chapters, L19 a waiver refreshes the package, L20 the brief's safety answer is the first policy

Status: approved by SK, 21 Oct 2026 (the three gaps from VW-6's options stage, design/49). SK is starting a new run to test them; nothing here changes VW-6.

## L18 — scenes must name chapters when the brief has them

**Today** `validate_scenes` (server/app/stage2/narration.py) accepts a scenes file in which no scene names a chapter, even when the brief has nine. After approval the coverage matches footage to beats by chapter only, so every beat reads ZERO COVERAGE. On VW-6 the child had written the chapter under a `chapter` key the shape does not have; 80 seconds, two scene records and two package rebuilds later it had re-recorded with `process_stages`.

**Change.** One more rule in `validate_scenes`: when the brief has chapters and no scene carries one, refuse: `Every scene names the chapter it covers under process_stages, from the brief's list (A, B, C); none of the scenes has one.` A scene that covers no chapter is still allowed as long as one scene names one; a brief without chapters is untouched. Nothing else in coverage or matching changes. The chapterless-film fallback (coverage from the model's own fits when the brief has no chapters) is noted in design/49 and not built.

**Tests first** (server/unit/test_stage2_pure.py): with the brief's chapters given, scenes with none are refused and the message names `process_stages` and the list; one tagged scene passes; with no chapters in the brief, untagged scenes pass.

## L19 — the policy reply says to rebuild the package

**Today** after `vw analysis policy --waive …` the re-check runs on the retained logs, but `vw options check` reads the options package built before the waiver and refuses the same sub-clips until `vw options prepare` runs again. The reply says only "Poll `vw analysis status`."

**Change** (text only). The reply (plugin/scripts/vw.py) ends: `…Poll \`vw analysis status\`; when it is done, run \`vw options prepare\` again if the options package exists: the check reads the package.` The analysis step's policy sentence (server/procedures/v2.json) gains the same clause.

**Tests first** (plugin/tests/test_analysis_cli.py): the policy reply names `vw options prepare`; the step text test checks the clause.

## L20 — "no brand or safety rules" at the brief waives PPE flags from the start

**Today** the brief's rules go to Gemini with every clip, but the model still marks missing gloves, open-toed sandals or a missing hard hat as risk flags, and the options check refuses any sub-clip with any risk flag. The waiver exists (`vw analysis policy --waive`), but nothing connects the brief's answer to it, so the operator is asked again at options, by flag name, guessing the names. On VW-6 the brief said "No brand or safety rules" and SK waived five names at 13:30.

**Change.** In `analysis_jobs.start`, when the brief's `production.brand_and_safety_rules` is empty and the start policy carries no `waived_risk_flags`, the policy gets `waived_risk_flags = PPE_WAIVERS` and `waiver_note = "the brief recorded no brand or safety rules"`. `PPE_WAIVERS` is one server constant of substrings matched the way the solver already matches waivers (`solver.waived`, case-insensitive substring): `ppe, glove, helmet, hard_hat, hardhat, footwear, sandal, barefoot, boot, goggle, eye_protection, mask, harness, vest, high_vis`. The flags travel as they do after a re-policy: into the request's `policy` and `identity.speaker_policy` (so the analysis key reflects them) through `analysis.build_request_clip_log`, and the solver applies them at retain. A brief with any rule at all gets no automatic waiver; an operator waiver given on the start command wins. The start reply carries `waived_risk_flags` and the tool's summary line says `risk flags waived from the brief (no safety rules): ppe, glove, …` so the operator sees it at once; `vw analysis policy` can still narrow or widen it later.

**Not changed:** the brief step and its question; the model's prompt; the options check; VW-6's recorded policy.

**Tests first.** server/unit/test_analysis_policy_pure.py (new): `analysis_jobs.start_policy(policy, production)` adds the PPE waivers and the note when the rules are empty, leaves the policy alone when a rule exists or when waivers were given; `solver.waived` accepts `missing_ppe_gloves`, `open_toed_sandals`, `no_hard_hat` and rejects `competitor_logo`, `staged_scene` against `PPE_WAIVERS`; `analysis.request_policy(policy, production)` (the speaker policy plus the waivers) carries `waived_risk_flags` and `waiver_note` when present and nothing extra when not. plugin/tests/test_analysis_cli.py: the start summary line names the waived flags when the server returns them and says nothing about waivers when it does not.

## Not covered

server/tests (Docker). The next run is the live check for all three: a scenes file with a wrong key, a waiver mid-options, and a brief with no rules on site footage.

## Versions and deploy

Server 0.20.3 → 0.20.4 (L18, L19 step text, L20); plugin 0.19.3 → 0.19.4 (L19 reply, L20 summary line). Both deploys before the new run starts; the workers restart; the operator restarts Claude Code once.
