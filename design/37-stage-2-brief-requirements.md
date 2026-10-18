# 37 — Stage 2 (brief) improvements: requirements (approved by SK 18 Oct 2026, implemented the same day)

Source: the stage 2 review run with the stage review prompt on 18 Oct 2026, SK's decisions on its 8 findings, and the optimisation round that added 2.9. All nine go ahead. Nothing here makes a paid call. VW-3 is past the brief and is not affected; every server change is backward compatible with the 0.2.0 plugin.

## Decisions carried from the review
- "Process stages" are presented to the operator as **chapters of the film**; the data key `process_stages` stays (analysis, options and delivery read it). An empty list is allowed; the four generic default names are removed (2.1).
- A repeat client's latest brief answers come back as **recommendations with one confirming question**; the two **language questions are asked on every film**, with no default in the tool (2.2, 2.8).
- Learned client rules reach analysis and are shown at the brief (2.3); one server function returns the **effective rules** for a run (2.7).
- **Allow-list guard** with SK's web rule (2.4): see §C.
- Brief prompt: minimal cut of the v1 mechanics plus one paragraph (2.5); production values presented before the yes (2.6).
- `next` computed from rows already fetched (2.9).

## A. Server changes (`server/`)

| # | What changes | Why | Where |
|---|---|---|---|
| 2.1 | Brief step 3 presents, under the five decisions, **"Chapters of the film (from the script; correct if needed; none is allowed)"** as a numbered list; the same yes covers it. The output shape's example for `process_stages` becomes `["chapter names in film order, or empty"]`. | A film-wide vocabulary chosen unseen. | procedures/v2.json brief `steps`, `output_shape` |
| 2.2 | `POST /api/runs` answer gains `last_brief` for the resolved client: from the client's most recent run that has a current brief output, `{run: code, production: {...}, answers: {...}, questions: [{id, question}]}`; `null` when none. | Repeat clients answer the same questions every film. | core.py (`last_brief(conn, client_id)`), main.py `create_run` |
| 2.3 | `analysis_jobs._inputs` sets `production['learned_client_rules']` from the client-rules table through `effective_rules` (2.7), so the field Gemini's request already reads is filled. `POST /api/runs` answer also gains `client_rules` (the learned rules, `[{rule, source_run, at}]`) for the brief to show. | The field has been empty since it was written; the brief never sees the rules. | analysis_jobs.py, core.py, main.py |
| 2.5 | Brief prompt, minimal edit: remove the paragraphs on `save_brief` / `accept_brief`, "the connector adds the digest", "the backend saves this as a proposal", browser acceptance, "reopen context and compare persisted values", "never fall back to a legacy workflow or paid API"; "employee" → "operator" (five places); the deferred-work sentence becomes "Do not add coverage, feasibility or production-readiness work; those belong to later stages."; "Do not research a client from its name or invent a client profile" → "Do not invent a client profile. If a fact about the client or a claim in the script would change a decision, propose a web search with the warning in the steps; never search on your own."; new paragraph **Production values**: chapters from the script, shown for approval, empty allowed; brand and safety rules, speaker on camera, field languages and narration language are the operator's words, asked on every film; last time's answers for this client, when given, are recommendations and never answers; target length only if the operator gives one. Placeholders `{last_brief}` and `{client_rules}` before the JSON instruction, filled by the plugin ("none" when empty). | Stale v1 mechanics; production never mentioned; SK's 2.4 wording. | procedures/v2.json brief `prompt` |
| 2.6 | Brief step 3 adds a **production block** after the five decisions and the chapters: field languages, narration language, speaker on camera, target length or "from the narration", brand and safety rules, rules remembered for this client, and which values are last time's answers. Step 2 says: ask the two language questions and the rules question on every film, in one message, with last time's answers as the recommendation when the client has them; ask once "same as last time, or changes?" for the rest of the production values. | The yes covered values the operator never saw. | procedures/v2.json brief `steps` |
| 2.4 | Brief steps gain the **web rule** sentence (also in vw.md, §C): "Before any web search or fetch, say in chat: 'I am deviating from the usual procedure. I want to search the web for X, because Y. The result may affect Z.' Search only after the operator says yes; afterwards say what you searched and show what you found. Nothing from the web enters out/brief.json unless the operator has seen it." | SK's rule. | procedures/v2.json brief `steps` |
| 2.7 | New `core.effective_rules(conn, run, outputs)` → `{'brief_rules': [...], 'waived_flags': [...], 'learned': [{rule, source_run, at}], 'effective': [...]}`: brief rules from the current brief output's production; waived flags from the latest analysis output's policy (`waived_risk_flags`, matched case-insensitively as the solver does); learned from `vw2_client_rules`; `effective` = brief rules not matched by a waiver plus learned rules. Used by: analysis request (`brand_and_safety_rules` = effective, `learned_client_rules` = learned), options prepare (replaces `learned_rules`), visuals prepare (the package's `brief` gains `effective_rules`). | Three copies of one list. | core.py, analysis_jobs.py, stage2/stage.py, visuals_stage.py |
| 2.9 | `get_run` calls `compute_next` with the rows it already fetched; `core.output` returns next computed from its rows plus the inserted row (attempts for that stage cleared); `post_output` stops calling `next_for`. | Four needless round trips per stage. | core.py, main.py |
| 1.x | Intake prompt: "the application removes the lines you name" → "the tool removes…"; "this application has always been in" → "this tool has always been in". | Cosmetic leftover from stage 1's audit. | procedures/v2.json intake `prompt` |
| — | `SERVER_VERSION` 0.3.0 → 0.4.0. | Visible on `/api/meta`. | config.py |

## B. Plugin changes (`plugin/`)

| # | What changes | Why | Where |
|---|---|---|---|
| 2.1 | `BLUEPRINT_DEFAULTS['process_stages']` becomes `[]`; `brief_record` refuses when the list equals the four old generic names ("chapters must come from the script or be empty"). | No film gets the generic names. | stages_text.py |
| 2.2, 2.3 | `vw start` stores `last_brief` and `client_rules` from the server's answer in the manifest; `brief_prepare` fills `{last_brief}` (production values and answers, one per line) and `{client_rules}` in the prompt and returns both under `inputs` so the assistant shows them. Old servers: both "none". | Recommendations and rules in front of the assistant. | vw.py `cmd_start`, `make_workspace`; stages_text.py |
| 2.8 | `production_inputs` requires `field_speech_languages` (non-empty list) and `narration_language` (non-empty string); no default for either; the refusal names the two questions. `defaults_applied` can no longer contain them. | Asked on every film; no guessed languages. | stages_text.py |
| 2.4 | **Allow-list guard** (§C): hooks.json matcher becomes all tools (empty matcher); `guard.py` allows by name and blocks the rest; blocked calls logged to `work/guard.log`. | SK's decision. | hooks/hooks.json, hooks/guard.py |
| 2.4 | vw.md gains the **web rule** paragraph (the same sentence as the steps) and operator-CLAUDE.md one line: "Web searches only after the warning and the operator's yes; connectors and the browser are not available here." | Instruction layer of the rule. | commands/vw.md, operator-CLAUDE.md |
| — | `plugin.json` 0.2.0 → 0.3.0. | | .claude-plugin/plugin.json |

## C. The allow-list guard (2.4), precisely
Allowed, in this order of checks:
1. `Bash`: only the vw command, as today (sentinel check first).
2. `Read`, `Glob`, `Grep`, `Write`, `Edit`, `MultiEdit`, `NotebookEdit`: only inside the active run folder, as today (sentinel check on writes).
3. `AskUserQuestion`, `TodoWrite`, `TodoRead`, and the desktop app's own turn tools (`mcp__ccd_turn__update_plan`, `mcp__ccd_turn__wrap_up`, `mcp__ccd_view__show_pane`): always.
4. `WebSearch`, `WebFetch`, `ToolSearch`: always at the guard; the warning-and-yes rule is an instruction (the guard cannot tell who asked).
5. `Skill`: only when the skill named is `vw:vw`.
Blocked, with one reason each, written to the log: every `mcp__…` tool not listed above (connectors, browser pane `mcp__Claude_Browser__*`, `mcp__claude-in-chrome__*`, `mcp__computer-use__*`, session and host tools), `Agent`/`Task` (subagents) **until the subagent check below passes**, `Workflow`, `SendMessage`, `CronCreate`, `ScheduleWakeup`, `EnterWorktree`, `NotebookEdit` outside the run, and any tool name the guard does not know.
Log: one line per blocked call appended to `runs/<code>/work/guard.log` (or `runs/guard.log` when no run is active): `time · tool · reason · path or first 80 characters of the command`; never file contents. The guard stands down in the builder checkout as today.
Subagent check (SK's condition): in the operator folder, after the plugin deploy, ask the assistant to "use a subagent to run git status" and to "use a subagent to read ~/.vw2/session.json"; both must appear in guard.log as blocked. Only then is `Agent` moved to the allowed list in a follow-up commit. The two routes from the 17 Oct transcripts: reads of Claude Code's own tool-results files are blocked by the read rule (outside the run folder); subagents are blocked until the check passes.

## D. Unstated but expected
- A new plugin against an old server: `last_brief` and `client_rules` absent → "none"; a new server against the 0.2.0 plugin: extra answer fields ignored. No crash either way.
- `effective_rules` with no analysis output yet (the brief and options stages before analysis) returns the brief rules plus learned rules, no waivers.
- Chapters empty: options scenes carry no chapter tag and the analysis prompt gets an empty list, as the code already allows.
- The web rule text is identical in the steps, vw.md and operator-CLAUDE.md, so a change is made in three places; noted so it is not forgotten.
- The guard's allow-list names tools of the desktop app; a Claude Code CLI session in the operator folder uses a subset and is unaffected.

## E. Edge cases
| Case | Expected |
|---|---|
| brief.json with `process_stages` = the four generic names | refused: "chapters must come from the script or be empty" |
| brief.json without `field_speech_languages` or `narration_language` | refused, naming the two questions to ask |
| first film of a client | `last_brief` null; prompt shows "none"; the steps' questions asked; no "same as last time" question |
| repeat client, operator says "same as last time" | the words stored as the answer; values copied from the recommendation by the assistant into the proposal |
| a rule waived at analysis | `effective_rules` drops the brief rule whose text contains the waived flag; options and visuals see the effective list; the brief output is unchanged |
| learned rule added at master, then a new run | the new run's analysis request carries it; the new run's brief shows it |
| assistant calls `mcp__supabase__execute_sql` or the browser pane in the operator folder | blocked, one line in guard.log |
| assistant calls WebSearch | allowed by the guard; the warning before it is checked by reading the chat (not testable in code) |
| assistant uses `Skill` for `vw:vw` | allowed; any other skill blocked |
| no active run, blocked call | logged to runs/guard.log |
| GET run / POST output | same answers as before, fewer statements (verified by behaviour, not by counting) |

## F. Tests (written first)
Layer one, `plugin/tests/` (run on this Mac): `test_guard.py` extended: connectors blocked, browser pane blocked, WebSearch/WebFetch/ToolSearch allowed, AskUserQuestion and the turn tools allowed, Skill only for vw:vw, Agent blocked, unknown tool blocked, guard.log written with one line per block and nothing when allowed, stand-down unchanged; `test_hooks_wiring.py`: matcher is all tools; `test_brief.py` (new): languages required, generic chapters refused, empty chapters accepted, `{last_brief}` and `{client_rules}` filled and "none" on a first film, prompt has no `save_brief`/`accept_brief`/"employee"/"connector"/"backend"; `test_stage_calls.py`: start stores `last_brief` and `client_rules` in the manifest and tolerates their absence.
Layer two, `server/tests` (Docker): T7 updated (languages supplied; chapters shown in the proposal; `last_brief` null on the first start and filled on a second start for the same client; `client_rules` after a learned rule is inserted); new `test_effective_rules` (brief rules, waiver drops one, learned added, no analysis output yet); `test_analysis` extended: the request carries `learned_client_rules` and effective `brand_and_safety_rules`; `test_stage2` extended: options prepare's rules come from `effective_rules`; `test_core`: `get_run` and `post_output` answers unchanged (next present) after 2.9.

## G. Not covered
- server/tests cannot run on this Mac; compile-check only until a Docker machine runs them.
- The warning-before-search behaviour is the model's; the guard and the tests prove tool access, not the warning.
- The subagent check is done by hand in the operator folder after deploy (see §C); until then `Agent` is blocked.
- The statement counts of 2.9 are checked by reading the code, not by a test.

## H. Deploy order
1. Server first (`deploy-server.sh`, workers restart): tell SK first.
2. Plugin (`deploy-plugin.sh`); the operator restarts Claude Code; then the subagent check by hand.
3. design/35: rows for the stage 2 decisions, the 2.4 decision in full, and the parameter 13 standing rule.

## I. Estimate
Server A: about 1 day (2.7 and its three consumers are the bulk). Plugin B and C: about 1 day including the guard tests. Deploys and the subagent check: an hour.
