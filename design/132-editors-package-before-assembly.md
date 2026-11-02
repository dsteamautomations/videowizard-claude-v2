# design/132: the editor's package first, then the assembly (enforced)

2 Nov 2026. Status: **approved by SK (2 Nov) and built (server 0.80.0, plugin 0.67.0); not deployed.** Regular lane. Build results in §8.

**Source:** SK, 2 Nov 2026: "The below has to be done and enforced. Editors package first then followed by assembly." Watch list A7 (VW-12 monitoring P15).

**Older way:** today the operator instructions put the assembly first and `vw delivery bundle` after it (procedure v3 "assembly" and "delivery", `plugin/commands/vw.md` "Assembly and delivery"). The server allows the early package (design/115 H1) but does not require it, so an operator who follows the instructions never makes it. **Retired at this deploy for every open run.** No film is kept on the old order: all films up to VW-11 are closed, and VW-12 is being deleted.

## 1. The request, restated

Once every gap's visuals are recorded, the editor's package (design/115, the early bundle) is made first. The server's assembly (the proof copy) can start only after that package exists and matches the recorded visuals. The instructions say this order, and the server refuses the other order, so a laptop with old instructions is stopped too.

**Not in this change:** dropping the server's assembly altogether (watch list C2). That is still SK's separate decision. Until then the assembly stays as the proof copy, after the package.

## 2. What exists today

- `server/app/stage3/delivery.py` `bundle()`: before an assembly output exists it calls `bundle_early()`. That makes the editor's package (narration, camera cuts by name and time, the raw AI files, FCPXML, EDL, SRT, cut list, relink list, OPEN-EDIT) and saves `session['bundle'] = {..., 'early': True}`. Once the assembly is recorded, the same call makes the full bundle with Approved-film.mp4.
- `main.py` `/delivery/bundle` already accepts the run in the `assembly` stage.
- `server/app/stage3/assembly.py` `prepare()` and `build()` never look at the bundle.
- `assembly.record()` returns `next: vw delivery bundle` (the full bundle); that stays.

## 3. The changes

| # | Change | Where |
|---|---|---|
| E1 | **The gate.** `assembly.prepare()` and `assembly.build()` refuse with 409 unless the session holds an early package that matches the recorded visuals: "The editor's package comes first: run `vw delivery bundle`, then the assembly." | `stage3/assembly.py` (one helper, called from both) |
| E2 | **What "matches" means.** `bundle_early()` also saves the inputs it was made from: the master plan digest and the id of each gap's recorded visuals output. The gate compares them with the run's current ones. A gap re-recorded after the package (a take swapped during the assembly review, say) makes the package out of date, so the gate refuses with the gap named until `vw delivery bundle` is run again. | `stage3/delivery.py` `bundle_early` |
| E3 | **The instructions in the new order.** The procedure v3 delivery and assembly steps, and `vw.md`, say: after the last `vw visuals record`, `vw delivery bundle` (the editor's package) and the operator's computer steps for it (`vw delivery check`, `download`, `open --originals`). Then the assembly as the proof copy. Then `vw delivery bundle` again for the full package with the approved film, and `vw delivery final`. | `scripts/d132_wording_v3.py` chained into `c1_split_v3.py --check`; `plugin/commands/vw.md` line 48 |
| E4 | **The hint after the visuals.** When `vw visuals record` records the last open gap, its reply says next: `vw delivery bundle` (the editor's package). | `visuals_stage.record_gaps` / `record_gap` reply; the `vw.py` message |

Both front ends go through the same server functions (CLAUDE.md "one flow, two front ends"), so the gate covers the chat path and any page.

## 4. Requirements check

**Unstated but expected**
- The full bundle after the assembly record works as today. The gate applies only before an assembly output is recorded.
- The early package's refusal while a gap is open ("The package waits for every shot: …") stays as it is.
- `assembly choose` and `stabilize` are not gated: they only record choices. `render`, `review` and `record` already need a build, so gating `prepare` and `build` covers them.
- The refusal names the exact next command, so an operator on old instructions knows what to do.

**Edge cases**
- **A run already in assembly with no early package** (prepared or built under the old order): its next `prepare` or `build` is refused until `vw delivery bundle` is run. Nothing already rendered is lost.
- **A run whose assembly is already recorded:** no gate. `vw delivery bundle` makes the full bundle as today.
- **A gap re-recorded after the package:** refused until the package is re-made (E2). The re-made package replaces the old one, and the manifest key is the same.
- **The master plan changed after the package** (a new plan version): the digest differs, so the gate refuses.
- **An early package made before this release** (no saved inputs): treated as out of date, with one `vw delivery bundle` to refresh it. Cheap, and no guessing.
- **Two calls at once** (bundle and prepare): both run under the run lock (`_s2`), so the gate reads either the old session or the new one, never half of one.
- **The package's own failure** (a missing camera file, a storage error): the bundle call fails as today, and the assembly stays refused. The operator reports it or files a defect.

**Failure modes**
- **The operator skips the laptop steps** (download and open on Resolve): the gate checks only that the package was made on the server. The download on the operator's computer is not enforced (see §7).
- **Old instructions on a laptop:** the server refusal is the enforcement. The new wording reaches a laptop after `vw visuals prepare` is re-run (A3, SK's action).

## 5. Tests (written first)

`server/unit/test_design132_pure.py`:
- The gate refuses `prepare` with no package and names `vw delivery bundle`.
- `prepare` passes with a matching early package.
- A gap re-recorded after the package: refused, with the gap named.
- A different master digest: refused.
- An early package with no saved inputs: refused.
- `build` is gated the same way.
- After an assembly record, `bundle()` still takes the full path (unchanged).
- `bundle_early` saves the inputs it was made from.

Plus:
- The procedure: the d132 wording script, the split check, and the visuals and assembly word budgets.
- `plugin/tests`: the `vw.md` order (the bundle named before `assembly prepare`).
- The version pins: server 0.80.0, plugin 0.67.0 (`PLUGIN_MIN_VERSION` unchanged; the plugin change is wording only).

## 6. Older ways

| Older way | What happens |
|---|---|
| Assembly first, then `vw delivery bundle` (procedure v3, `vw.md`) | Retired at this deploy for every open run; the server refuses it by name. |
| An early package with no saved inputs (made before this release) | Accepted as a package, but it counts as out of date for the gate: one re-run refreshes it. |

## 7. Not covered

- **The download and open on the operator's computer are not enforced.** Enforcing them would need the laptop to report back (for example `vw delivery confirm` for the early package). Add this if SK wants the editor's receipt, not only the package, to gate the assembly.
- Dropping the server assembly (C2): SK's separate decision.
- The Docker database suite (`server/tests`) is not run (B1); unit tests and compile checks only.

## 8. Build (2 Nov 2026)

- **Found while building:** `delivery.bundle()` loaded the stage 3 session without `create=True`, so the early package failed with "Run `vw assembly prepare` first" on a run with no assembly yet. design/115's early package could never be made before the assembly. Fixed: the bundle creates the session.
- **Server:**
  - `stage3/assembly.py`: `early_inputs`, and `package_first`, called at the start of `prepare` and `build`.
  - `stage3/delivery.py`: `bundle_early` saves `inputs`.
  - `visuals_stage.record_next`: after the last gap, next is `vw delivery bundle`.
  - `SERVER_VERSION` 0.80.0.
- **Procedure:** `scripts/d132_wording_v3.py` adds the package as the assembly's first step and makes the delivery's bundle "again … the full package". It is chained into `c1_split_v3.py --check`, which now also allows the assembly and delivery stages to differ from the base.
- **Plugin:**
  - `commands/vw.md`: the package before `vw assembly prepare`.
  - `vw.py`: the record line prints the server's next step.
  - `plugin.json` 0.67.0; `PLUGIN_MIN_VERSION` unchanged at 0.66.0.
- **Tests:**
  - `server/unit/test_design132_pure.py`: 11 tests, all failing before the change and all passing after. Server unit suite: 1010 passed, 4 skipped.
  - `plugin/tests/test_design132.py`: 2 tests. Plugin suite: 389 passed, 4 failing, the same 4 that fail on HEAD (3 Windows-only, plus the `test_master_cli` slides).
  - `c1_split_v3.py --check`: ok. Compile checks: ok.
- **Not run:** the Docker database suite (B1). No live run yet: the first new film's package and assembly will show the gate.
