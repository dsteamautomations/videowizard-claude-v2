# design/96 — Release 2: fair checks

25 Oct 2026. Release 2 of the combined revision (`VW2-revision-plan-2026-10-24.md`). It builds:
- design/93's X1–X4 (fix pictures) and J1–J3 (checks per step and per graphic type);
- the course's C1 (an edit names its pictures).

SK decided X1 on 25 Oct: "no automatic fix rounds; a fix only when the operator or the assistant asks, showing the cost." **Nothing is built until SK approves this note.**

Read against server 0.42.0. On VW-7, 4 automatic fix pictures were made: 2 approved, 1 rejected, 1 waiting, and none is in the film.

## 1. The requirement, restated

A picture is checked only against what its own step and its own kind of graphic should show. A failed check marks the picture. A paid fix picture is made only when someone asks for it, and its cost is shown before and after. Both front ends get the same rules from the server.

## 2. What changes

| # | Rule | Where |
|---|---|---|
| X1 | **No automatic fix rounds.** The worker saves the check and stops. A fix is made on request: **"Try a fix (₹4)"** on the card, or `vw visuals fix --ref R`. It is one edit for the first failed must line, at the image price, inside the cap. It is offered only on a candidate with a failed must line that is not itself a fix and has no fix yet. The reply names the line it fixes and the cost. | `visual_workers.check_image`, `image_check.queue_fix` (now `request_fix`), a route, page, `vw.py` |
| X2 | **A fix is labelled as one:** "fix of keyframe-TOWN · for 'label: Rat-trap bond' · ₹4". The fix records the line it was made for (`fix_for`). In a sequence it still stands in for its original (design/95 F1); rejecting it brings the original back. | page view, page |
| X3 | **The spend counts fixes apart:** "images: 14 requested + 2 fixes". A job made as a fix records it (`fix_of` in the job's reference). Earlier fix jobs are known by their "-fix" name. | `visuals_spend`, page, `vw visuals budget` |
| X4 | A fix is never made for a line the check could not decide (no pass or fail), or for a line J1–J2 no longer give the picture. The fix takes only failed must lines. | `request_fix` |
| J1 | **Per-step lines.** A state of a graphic sequence is checked only against what its step shows. The step is the picture's place in its shot's chain: 1 for the first picture made for the shot, then 1 more per parent of the shot. A claim, a word, or what the drawing depicts goes to the first state whose `what_appears` or `words` contains it; one that no state names goes to the last state. A state keeps the lines of the states before it. The spec's relationships, sizes and label go to the last state. The facts, the state carried over and the fixed lines apply to every state. A still diagram is one state: it has every line, as today. | `visuals_stage._graphic_lines` |
| J2 | **Rules by graphic type.** A shot gets `graphic_kind`: `diagram` (the default, so plans in progress stay valid), `chart`, `map`, `title` or `text`. Only a `diagram` has the leader-line rule on its labels. A `title` or `text` card is checked for its exact words, their spelling and size, and readability: no claim, word, depiction or spec lines, and titles at 6 % of the frame height. A `chart` or `map` keeps its claims and depiction, with labels that need no leader line. The plan step says which kind to choose. | `visual_contract.Shot`, `_graphic_lines`, `server/procedures/v2.json` |
| J3 | **A state that passes its own lines shows green:** "state 1 of 3 · ok", or "state 2 of 3 · 1 to look at". | page |
| C1 | **An edit names its pictures** (course C03-2). When an edit sends the pictures it names (`--parents`), the prompt must name "Image 1" to "Image N", one per picture. Ranges count ("images 2 onward", "images 2–4"). The pictures the server adds behind an end image's start don't count. **A warning this release, refused from the next**, as the handover says. | `library.image_names_missing`, `generate_image` |

## 3. Edge cases and failures

| Case | Handling |
|---|---|
| A fix requested for a picture with no failed must line, a fix of a fix, or a second fix | Refused: "nothing to fix: no must line failed", "a fix is not fixed again: reject it and make a new picture", "a fix of this picture is already made: <id>". |
| A fix past the film's cap | Refused by the cap, as for any picture (design/65 B7). |
| A fix requested for an approved or rejected picture | Refused: only a candidate is fixed. |
| A check still running when Try a fix is pressed | Refused: "the check is still running". The button shows only once the check is saved. |
| The check could not run (no key, a transport error) | No failed line, so no fix is offered. The error shows as today. |
| A state made before shots were recorded | Its step can't be read, so it keeps every line, as today. |
| A state deeper than the plan's states | Treated as the last state. |
| A plan in progress with no `graphic_kind` | `diagram`: the same lines as today, except per-step (J1). |
| A `title` with a drawing spec | The spec is ignored for checking (a warning says so). |
| Two people pressing Try a fix | The run's lock serialises them; the second gets "already made". |
| VW-7 | Every shot is filled and the spend is unchanged. Its 4 old fix pictures count as fixes in the spend (by name). |

## 4. Tests first

`server/unit/test_design96_r2_pure.py`:
- X1: a failed must line no longer queues a fix in `check_image`; `request_fix` makes one, with the line and the cost; each refusal in section 3.
- X2: the fix records `fix_for`; the page view carries it.
- X3: the spend counts a job with `fix_of`, and an old "-fix" job, as fixes.
- X4: a line with no decision never starts a fix.
- J1: a 3-state graphic sequence: state 1 has no claim named only in state 3's `what_appears`, and state 3 has it; a word in state 2's `words` is on states 2 and 3, not 1; an unnamed claim is only on the last state; a still diagram has every line.
- J2: a `title` gets no leader-line, claim or depicts lines, and has the exact text at 6 %; a `diagram` keeps leader lines; a `chart` has labels without leader lines; a plan without `graphic_kind` validates as `diagram`.
- C1: an edit with 3 named parents and only "Image 1" in the prompt warns, naming Images 2 and 3; "images 2 onward" passes; a generate (no parents) is not checked; an end image's added sheets don't count.

`plugin/tests/test_visuals_cli.py`: `fix --ref` posts and prints the line and the cost; `budget` prints the fixes apart. The page: the template carries "Try a fix", the fix label and "state N of M".

## 5. Not covered

- How often the checks' verdicts are right. That is the model, not the rules; VW-8 will tell.
- `server/tests` (Docker).
- The pages beyond reading their content.

## As built (25 Oct 2026)

Server 0.43.0, plugin 0.41.0. The minimum plugin is 0.41.0, because the procedure now names `vw visuals fix`, which 0.41.0 brings. Not yet committed or deployed.

- `visual_workers.check_image` saves the check and nothing else. `image_check.queue_fix` is gone. `visuals_stage.request_fix` takes its place, with a route (`POST …/references/{id}/fix`), the page action `fix` and `vw visuals fix --ref R`.
- `_queue_image` records `fix_of` on the job; `visuals_spend` returns `fixes`. The page view carries `fix_for`.
- `_step_filter` (J1) and the `graphic_kind` rules in `_graphic_lines` (J2); `Shot.graphic_kind`, default `diagram`.
- `library.image_names_missing` (C1), warned in `generate_image`. A fix round is not checked.
- The page:
  - "Try a fix (₹4)" on a failed candidate;
  - "fix of <picture> · for '<line>' · ₹4" on a fix;
  - "images: N requested + M fixes" beside the spend;
  - "state N of M · ok" or "· k to look at".
- The tool: `fix`, and `budget` prints the fixes apart.
- The procedure's visuals prompt and steps, and `commands/vw.md`, name `graphic_kind`, the per-step check, Image 1 to Image N, and the fix on request.

Tests: `server/unit` 329 passed (19 new in `test_design96_r2_pure.py`). Older tests changed to the approved rules:
- the automatic fix is gone (`test_l60_busy_pure`, `test_image_check_pure`);
- the spend has `fixes` (`test_visuals_stage_pure`);
- the fix label (`test_visuals_page_pure`);
- an edit names its style sheet as Image 1 (`test_batch89b_pure`);
- the minimum follows the plugin (`test_design95_pure`).

`plugin/tests` 249 passed, with 3 known Windows-only failures. Plugin compile-checked. The page script parses.
