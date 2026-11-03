# design/149: the plan step's Set B (SK's answers, 3 Nov 2026)

Set A (design/148, built f47d4f4, not deployed) fixed the mechanics. Set B is the rules SK decided one at a time on 3 Nov, from the VW-18 root-cause table (`vw18-plan-root-cause-2026-11-03.md`, review folder). Build plan below, for SK's approval before code. Deploys stay on hold.

Terms used throughout: **writer** = the main assistant (writes `plan-base.json`) and the four `vw-plan-gaps` helpers (write the gaps); never the operator. **part-plan** = the visuals procedure's plan part in `server/procedures/v3.json`, changed only through a `scripts/d149_wording_v3.py` chained in `c1_split_v3.py --check`, with the visuals word cap in `test_design125_stage7_c_pure.py` raised by the words added. **the brief** = `plugin/agents/vw-plan-gaps.md`. **the checker** = `visual_contract.validate_plan`.

## B1. The open questions are asked before the helpers plan
**SK:** ask before the helpers run; each question with its fitting choices and why each fits.
**Change.** (a) The common visuals sentence "Missing facts: one list, once, before the first picture" becomes: one list, once, after `plan-base.json` and before the helpers; the answers go into `plan-base.json` as visual facts (status confirmed, source "the operator: <their words>"); "no preference" keeps the plan's proposal and stays an open question; each question through the question tool with two to four fitting choices, one line each on why (the footage, the brief, the client card, the region), the plan's proposal first. (b) Part-plan's order of work gains the step between plan-base and the helpers. No schema change: `visual_facts` and `open_questions` exist.
**Checker.** None. **Older way.** The list after the proposal is retired by the sentence.
**Clears.** Refusal 19, process flaw 5.

## B2. A change of clothes is a change of garment or colour, and the outfit line is clean
**SK:** both (the checker compares the clothes; the writer is told the clean form).
**Change.** (a) Checker: `_outfit_key(text)` reads garment words and colour words from fixed lists (`OUTFIT_GARMENTS`, `OUTFIT_COLOURS`); two outfit texts are "the same" when their keys match. When either text yields no key (clothes written outside the lists), the literal compare stays: strict where unsure. (b) Part-plan and the brief: the outfit text is garments and colours only, identical for a person across scenes; framing notes go in the shot's `focus`, open questions in `open_questions`.
**Tests.** Same garments and colours with a bracketed note: no refusal; a colour change: refused; clothes outside the lists, different text: refused.
**Clears.** Refusals 11, 20, 21.

## B3. `repeating` is retired; `kind: material` says it
**SK:** option 2.
**Change.** `Element.repeating` leaves the model; the checker's material rule reads `kind == 'material'` only; a plan carrying `repeating` is refused by name: "`repeating` is retired (design/149): a thing built from identical units is `kind: material`". Design/111 F10's tests move to `kind`. VW-18's proposed plan carries no `repeating` (checked); live plans are checked for the word before the deploy.
**Older way.** Refused by name, per design/35.
**Clears.** Refusal 4.

## B4. A size claim lives in the claim field; a size word in the description is a descriptor
**SK:** 2 alone, no warning.
**Change.** Checker line "SIZE_WORDS in claims + descriptors" reads `shot.claims` only. One sentence in part-plan: a size the film asserts goes in `claims` (value and `compare_to` required); a size word in `descriptors` or a beat describes and is not checked.
**Tests.** "thin" in descriptors alone passes; "thin" in claims without value and `compare_to` refused (existing test kept).
**Clears.** Refusal 18.

## B5. Techniques are named once at plan-base; a stray verb warns
**SK:** option 3.
**Change.** (a) Part-plan, order of work: at plan-base the main assistant names the film's techniques as elements (`kind: technique`) from the treatment and the footage; the helpers plan against them. (b) Checker: a beat verb on `TECHNIQUE_VERBS` with no technique element becomes a warning, kind `technique_unnamed`, answerable in `warning_answers` ("add it, or say why this film needs no reference picture for it"); added to the answerable kinds.
**Older way.** The refusal is retired.
**Clears.** Refusal 17.

## B6. A figure the film states is never "unknown" (revised; needs SK's re-confirmation)
**Found while building:** the checker already refuses `illustrative` when nothing is unknown (design/111 F19). VW-18 passed because all 24 dimensions on its 11 drawings were marked unknown, including the strength figures the narration speaks (20, 35, 75 kg/cm²) and the brick proportions a standard gives.
**Proposed rule.** A drawing spec dimension whose value the shot's narration or `claims` state as a number is `confirmed` with source "the script" (or the brief), never `unknown`. Checker: a spec dimension with status unknown while the shot's narration or claims carry a number with the same unit (kg/cm², mm, cm, m, %, storeys, a count) is refused: "the narration states {figure}: the spec's {part} {measure} is confirmed from the script, not unknown". Part-plan: one sentence saying so.
**Not covered by the rule.** A size that is known from a standard but not spoken (brick 190 × 90 × 90) stays unknown until the research step; that is design/124 C2's existing path (`spec_unresearched`), and it works only if the research is done. The blanket label on VW-18 was a symptom of research deferred, not of the label rule.
**Clears.** Process flaw 3 (its real cause).

## B7. The gap files are the master; the join refuses to overwrite hand edits
**SK:** option 1 with the guard; option 2 dropped.
**Change.** (a) Part-plan: a fix after a refusal goes into the gap file (its helper for judgement, the main assistant for a field or a spelling), then `plan-join`, then `check`; `out/visual-plan.json` is never edited by hand. (b) `plan-join` refuses when `out/visual-plan.json` is newer than every gap file: "the joined plan was edited after the last join; put the edits into the gap files, or `--rebuild` to drop them"; `--rebuild` is a new flag.
**Residual (accepted).** A helper that rewrites its whole file drops a small fix the main assistant put there; the next `check` catches it.
**Clears.** Process flaw 2.

## B8. A shape checklist in the helper brief; the digest held
**SK:** 2 now, 3 on the next film's evidence.
**Change.** The brief gains a fixed checklist (about thirty lines): `outfit` per person per scene, in the clean form (B2); `props` for anything held, with its end; the container of anything that arrives in one (B9); `groups` for more than one of a thing in frame; `changes` when a count moves; `drawing_spec` on a drawn shot with figures, a stated figure never unknown (B6); `states` only on animation shots; a size claim in `claims` with value and `compare_to` (B4); the film's techniques from plan-base (B5); new things in `new_elements` with id and name, completed by the main assistant after the join (A2); `return_of` with the exact id; a subject's `end` and every prop's end (B9).
**Measure.** The next film's `check` refusals of the eleven "written, not applied" kinds. If they persist, the per-gap digest (option 3) is the next design.

## B9. Nothing in the frame vanishes
**SK:** approved as written.
**Change.** (a) Part-plan and the brief, the principle: everything in the shot at its start is accounted for at its end, still there at a stated place or gone by a stated action of someone; anything that moves or is moved is a named thing of the shot (a subject or a prop). (b) Checker, new, a warning kind `container_unnamed`: a subject's or prop's start `relation` reads "in/inside/on a|the <noun>" and no element of the shot has that noun in its id or name: "the <noun> carries it: name it as a prop with its end, or say it is scenery". A warning, not a refusal, because "in the yard" is not a container. (c) The take prompt (`visuals_stage` take brief, `end_state`): today only `changes[].what`; it gains the end state of every subject (position against its landmark, pose) and the end of every prop (`in_hand` / `set_down` at … / `carried_out` by …), so the model is told where things are when the take ends.
**Already there.** Every subject carries a required `end: State`, so an early-finishing subject (the horse) already has an end written; the brief now says what it is for.
**Clears.** The disappearing basket; the horse.

## Build order and tests
1. Wording script `d149_wording_v3.py` (B1, B2b, B4, B5a, B6, B7a, B9a) + word cap. Test: `c1_split_v3.py --check`, `test_design125_stage7_c_pure`.
2. Checker (B2a, B3, B4, B5b, B6, B9b): `server/unit/test_design149_pure.py`, one test per rule plus the old-way refusal for `repeating`; design/111 F10 and F15 tests updated.
3. Take prompt end state (B9c): a unit test on the take brief's `end_state` lines.
4. Plugin: `plan-join` refusal and `--rebuild` (B7b), the brief's checklist and principle (B8, B9a): `plugin/tests/test_design149.py`.
5. Full server unit suite and plugin tests; compile checks; commit and push. Server 0.89.0, plugin 0.75.0. Not deployed.

## Built, 3 Nov 2026
Server 0.89.0, plugin 0.75.0; not deployed (deploys on hold). Tests: `server/unit/test_design149_pure.py` (8), `plugin/tests/test_design149.py` (3); the full server unit suite 1146 passed; plugin 416 passed with the four pre-existing failures. Three older tests moved to the new rules, each marked with SK's answer: design/111 F10 (`repeating` now refused by name), design/124-b item 6 (a size word in descriptors describes), design/111 F14 (the technique verb warns). B9c: `end_places` in `visuals_stage.py` adds one line per subject and prop to the take prompt's end state only where the plan gives an end, so design/128's held-only prompt stays byte for byte.

## B10, held for SK's wording
A size unknown from the script may be proposed from a named standard or maker figure (status `proposed`, source "recalled: <standard>, to confirm"), offered in the B1 list with its alternatives and the footage measure first; confirmed by the operator it may shape a drawing; a figure written on screen as a number needs the script, the client's document or a web check; client-specific sizes are never proposed from recall. Not built.

## Not covered
- Database tests (Docker): nothing here touches the database.
- The four pre-existing plugin test failures on this PC (listed in design/148).
- B8 option 3 (the digest), held for the next film's count.
- Whether the operator's answers (B1) should also be offered to the client's next film, as learned rules are: not asked, not built.
- The research step that B6 leans on (`spec_unresearched` → research after the picture round) is unchanged; if it is skipped, unknown sizes stay unknown.
