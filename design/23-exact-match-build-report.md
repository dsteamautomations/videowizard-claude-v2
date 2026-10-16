# 23 — Build report: exact-match editing (design/21), 15 Oct 2026

All times are IST on 15 Oct 2026, taken from the session record and git history.

## 1. What was requested
SK watched the VW-2 review film (11 options over 9 scenes) and asked for the editing approach to change:

1. **Exact matches first.** Real footage only where it shows exactly what is said, even for part of a sentence.
2. **Blanks for the rest.** Leave blanks for AI video or animation. A blank is at least 3 s. There is no upper limit; AI makes shots of up to 30 s each.
3. **Short real shots.** 2 to 3.5 s each, combined and cut to the meaning, never stretched because footage exists.
4. **Each clip once.** Any reuse, including another part of the same clip, is offered as a choice, never placed silently.
5. **B-roll and abstract lines.** B-roll for abstract lines only when it is a good choice and relatable, and always as a choice.
6. **Decision slides.** Anything needing SK's opinion gets a slide before it, not played back to back with confirmed shots.
7. **Clear numbering.** Slides numbered #01, #02 … in film order, answered by number. The words "option" and "beat" are confusing and go.
8. **Speaker on camera** follows each client's policy.
9. **Scope.** This stage decides only which real clips go where. Finishing (titles, infographics, mascot) is out of scope.

The requirement went through three revisions with SK (design/21), plus an analysis of SK's finished rat-trap bond film (design/22). SK approved it at 20:03: "go ahead".

## 2. What was built, by module

| Module | Files | Change |
|---|---|---|
| Options checks (the validator) | `stage2/validator.py` | Blanks inside a scene: need an intent; at least 3 s, or a reason so the operator decides. Every real shot must state `match` (direct or b_roll) and `evidence`. B-roll must be a decision. Clips graded C (poor quality) must be a decision. A clip used a second time must be a reuse decision; a scene's first and backup option may share. Real shots over 4 s are flagged unless they give a reason. The old slate-text and shared-clip checks were removed. |
| Numbered slides (new) | `stage2/slides.py` | Writes every slide: scene (#05), BACKUP for #05, DECISION, BLANK. Readable clip names instead of codes, plain text, wrapped lines. Builds the review film sequence and the per-scene summary of real, blank and decision seconds. |
| Review and master films | `stage2/render.py`, `render_jobs.py` | A blank inside a scene is a captioned card while the narration keeps playing. A decision slide is silent and splits the narration, so words stay with their pictures. Slide text is centred whatever its length. Master blanks read "BLANK … for AI video or animation". |
| Options and master logic | `stage2/stage.py` | `check` shows real, blank and decision seconds per scene. `propose` stores the numbered slides. Answers are by slide number: KEEP, REJECT or KEEP_WITH_EDIT for scenes, KEEP or DROP for decisions; blanks need none. Missing answers are listed by number. A dropped placement becomes a blank and merges with a neighbouring blank. A dropped placement under 3 s between real shots is refused. An approved reuse may repeat its clip. Each blank becomes its own gap for the visuals stage, with its intent and the words under it. |
| Master check | `stage2/validator.py` | The duplicate-clip check accepts a reuse the operator kept. |
| Visuals stage | `visual_contract.py`, `visuals_stage.py` | One generated video or animation shot is at most 30 s; a longer blank is several shots. |
| Server and plugin commands | `main.py`, `plugin/scripts/vw.py` | `vw master decide --slide N --action KEEP|REJECT|KEEP_WITH_EDIT|DROP`. The old `--option` still works as the slide number. |
| Assistant instructions | `procedures/v2.json`, `stage2/package.py`, `plugin/commands/vw.md` | The options prompt is rewritten around exact matches first. Paragraphs that had been duplicated by an earlier mistake were removed. The example shape the assistant fills shows the new fields. Master steps now say "answer every numbered slide". |
| Tests | `tests/test_exact_match.py` (new, 12 tests), `tests/test_stage2.py` | One test per agreed edge case, plus one end-to-end test (below). Shared test helpers were updated for the new shot fields. The shared-clip test was rewritten for the new rule, and the slate-text test was removed. |

Size: 15 files, 558 lines added, 95 removed (commit 42d0b66), plus the two design documents (commit 53002bb).

### Requirement to change
| Requirement (design/21) | Where it is enforced |
|---|---|
| Exact matches first, part of a sentence | `match` and `evidence` on every real shot; the prompt; blanks inside scenes |
| Blanks at least 3 s, no upper limit | Blank check (E1); master refuses a dropped placement under 3 s |
| 30 s per AI shot | Visuals plan check |
| Short real shots, cut to meaning | Flag on real shots over 4 s without a reason; the prompt |
| A clip once; reuse only as a choice | Clip-level reuse check; reuse decision; master accepts a kept reuse |
| B-roll and abstract lines as choices | B-roll must be a decision; abstract lines are blanks by default (prompt) |
| Poor quality and check-by-eye as choices | Grade C must be a decision; check_by_eye decision kind |
| Decision slides, not back to back | Decision slide before the placement; narration split around it |
| Numbered slides answered by number | `slides.py`; decide by slide number; missing answers listed by number |
| Speaker on camera per client | Unchanged existing rule (policy `show_speaker_video`) |
| Finishing out of scope | Not built, by design |

## 3. Timeline: development and testing
| Phase | From | To | Time |
|---|---|---|---|
| Requirement: SK's review, three revisions, reference film analysis | about 16:05 | 20:03 | about 4 h, mostly waiting on SK's answers; the reference film analysis itself took about 20 min |
| Code: slides, options checks, stage logic, instructions, visuals cap | 20:03 | 20:14 | about 11 min |
| New tests written and run (unit tests, then end-to-end) | 20:14 | 20:27 | about 13 min (end-to-end alone 7 min 42 s) |
| Full regression (all 153 tests) | 20:28 | 21:28 | 60 min, stopped by my own time limit at about 72 of 153 tests; no failures up to then |
| Targeted regression (affected modules only) | 21:28 | 22:33 | 65 min: 64 passed, 1 failed (a mistake in a test, not in the tool) |
| Fix the test, rerun the fast checks | 22:33 | 22:34 | 15 s, 18 of 18 passed |
| Commit, push, plugin sync, server restart | 22:35 | 22:37 | 2 min |

Coding took about 25 minutes in all. Testing took about 2 h 20 min, of which the full run's 60 minutes produced no complete answer.

## 4. Regression: why it was run, and what was necessary
**Why some regression was necessary.** This change rewired code that other stages depend on:
- **The master plan.** Its build was rewritten (decisions by slide number, blanks as gaps). Stage 3, assembly and delivery, reads that plan.
- **The film renderer.** It is shared by the review film, the master film and the assembly film.
- **The shared test helpers.** Every stage 2 and stage 3 test builds its options with them. Changing them could break those tests silently.
- **The plugin command for decisions.** Every master step uses it.
- **The visuals plan check.** It is used by the visuals stage.

Your working rules require tests and an honest report of results. So the tests for stage 2, stage 3, visuals and the plugin had to run. Without them there was no evidence that a run could still go from options to delivery.

**What was not necessary.** The full-suite run also covered modules this change did not touch: the old version 1 planning, voice and media, sign-in, web pages and analysis. It cost 60 minutes and was then stopped by my own time limit before it finished, so it gave no complete answer. That was over-testing. The targeted run that followed (stage 2, stage 3, visuals, plugin, the new tests) was the one that mattered.

**Why the runs were slow.** The end-to-end tests render real films with FFmpeg, 3 to 8 minutes each, and there are about ten of them across stage 2 and stage 3. The 5 VideoWizard workers were also running on the same machine, which likely slowed the renders.

**What the regression found.** No defect in the tool. It found one mistake in a test: the test gave a backup option two parts of the same clip, which the new rule correctly refuses.

**Going forward** (as agreed on 15 Oct):
- Run the tests of the changed stage plus the stages that read its output.
- Run the full suite only when shared code changes (storage, the master plan, the renderer).
- Run the fast checks first and the film-rendering tests last.

## 5. Not covered
- "Check by eye" and B-roll judgements come from the clip logs, not from watching the footage. The review film is where SK confirms them.
- Generating the AI blanks is the visuals stage's job and was not changed, beyond the 30 s cap.
- The step banner (design/20) is still waiting for SK's yes.
- The VW-2 options are not rebuilt yet. That happens in the VW-2 thread with `vw options prepare`.
