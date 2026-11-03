# design/148: the plan step's Set A (SK, 3 Nov 2026)

From the VW-18 plan review (`vw18-plan-root-cause-2026-11-03.md` in the review folder): 57 minutes from treatment to proposal, 24 check refusals one at a time, two helpers relaunched for nothing. Set A is the five fixes that need no rule decision. Set B (the rule questions B1-B8) follows one at a time.

SK approved Set A as one batch on 3 Nov, with A3 as "the guard lets the helpers hand back, plus the fallback sentence". Deploys stay on hold (no deploy without SK's yes).

## A1. The plan check lists every error

**Today.** `visual_contract.validate_plan` is 114 `need()` calls; the first failure raises and `check` returns one sentence. VW-18: 24 round trips of ~30 s.

**Change.** Errors are collected per item and reported together:
- the Pydantic shape check stays first and alone (nothing below can run on an invalid shape);
- top-level duplicates (`unique`) stay fail-fast;
- each element, each visual fact, each gap and each scene is one item: its first failure is recorded, the rest of that item is skipped, the next item runs;
- when a scene of a gap failed, the gap's "shots cover the exact gap" check is skipped (its cursor is incomplete);
- when anything was recorded, the cross-plan checks after the gap loop (returns, repeated messages, pacing, warnings) are skipped and the collected errors are raised as one `ValueError`: `N things to fix:` then one numbered line per error, each message word for word.
- `check` returns `error` (the joined text, as today) and `errors` (the list).

**Older way.** Fail-fast is retired; the messages themselves do not change, so the 147 unit assertions that match a message still hold.

**Known limit.** A skipped scene does not record its outfits, so the next scene of the same person may be refused for a colour change that is not one. Fixing the first error and running `check` again clears it. Listed, not hidden.

## A2. `plan-join` names the new things still to complete

**Today.** The helper brief says a new thing is `new_elements: [{id, name}]`. `plan-join` copies those stubs into `elements`; `check` then refuses them (VW-18 refusal 1, `lorry_driver`).

**Change.** The join still succeeds; its result carries `incomplete: [ids]` and its message ends with "N new things need kind, identity and requirements before check: lorry_driver, …". Where the fix goes (gap file or joined file) is B7, not decided here.

## A3. The helpers can hand back, and the fallback is written down

**Today.** `guard.py` allows only the listed tools; a helper's `SubagentHandback` and the main assistant's `SendMessage` fall to "not available". Every helper ends in silence; a `Glob` without a `path` is blocked too. VW-18: two helpers relaunched for nothing, ~12 minutes.

**Change.**
- `SubagentHandback` joins `ALWAYS` in the guard: the plugin's own helpers may report. `SendMessage` stays blocked (not asked for).
- One sentence added (not changed) to part-plan and to `vw-plan-gaps.md`: when a helper's report does not arrive, its file under `out/plan-gaps/` (read by full path) is the proof it finished; never relaunch a helper whose file exists.

## A4. Shape errors in the tool's voice

**Today.** A Pydantic failure reaches the operator as "3 validation errors for Plan elements.53.kind Field required [type=missing, input_value=…] For further information visit https://errors.pydantic.dev/…".

**Change.** `check` and `propose` turn it into one line per object: "elements[53] lorry_driver: missing kind, identity, requirements". The object's `id` is read from the document at the error's path when it has one.

## A5. `return_of` names the nearest id

**Today.** `return_of: BEAT_02-B2-S3` with a shot `BEAT_02-B2-s3` is refused as "not an earlier shot". The id is looked up exactly downstream, so accepting it silently would break the later lookup.

**Change.** The refusal adds "did you mean BEAT_02-B2-s3?" when an id differs only in case.

## Tests first
- `server/unit/test_design148_pure.py`: A1 (three independent errors in one call; the error list; a skipped scene does not stop the next gap; a valid plan unchanged), A4 (the Pydantic line), A5 (the suggestion).
- `plugin/tests/test_design148.py`: A2 (the join lists the stubs and still writes the plan), A3 (the guard passes `SubagentHandback`, still blocks `SendMessage`).

## Built, 3 Nov 2026
Server 0.88.0, plugin 0.74.0; not deployed (deploys on hold). The procedure sentence is `scripts/d148_wording_v3.py`, chained in `c1_split_v3.py --check`; the visuals word cap in `test_design125_stage7_c_pure.py` rises by its 21 words. One more place found while building: `_research_warning` turns a `need()` refusal into a warning by catching it, so it runs with the collector off (`_plain`), or the warning would also have been listed as an error (caught by `test_design106d_pure`).

## Not covered
- The server's database tests (Docker) are not run for this change; nothing here touches the database.
- Four plugin tests fail before and after this change alike (`test_intake` ×2, `test_master_cli::test_slides_prints_the_review_page_link`, `test_start_defect_paths::test_start_script_refuses_hidden_and_system_places`): Windows path and encoding cases, not this work.
- B1-B8 (the rules) and the per-gap digest.
- The relaunched lean `gaps-01`: which version VW-18 joined is not recorded.
- `Glob` without a path stays blocked; the fallback sentence says Read by full path.
