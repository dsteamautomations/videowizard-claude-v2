# design/85 — Long gaps: the blank-length check, the AI-run warning, shorter AI shots, and Omni's scene extension

Status: requirements note, builder, 22 Oct 2026; SK: "write design/85 with all four; build the checks with design/84, then the extension in its own deploy". Sources: VW-6's fill table (BEAT_01 27.6 s, BEAT_03-B1 22.4 s, BEAT_04 26.0 s, each three or four AI shots back to back), `stage2/validator.py`, `visual_contract.validate_plan`, the Omni fact sheet B10.

## Why

A single AI shot of seven seconds between two real clips passes; four in a row do not. Each take drifts a little from its neighbour, the cuts between them have no real picture to anchor on, and a synthetic run of twenty seconds is long enough to notice. The length of the run is the fault, not only each take. The run is decided twice: at options, where the blank is left; at the plan, where the blank is filled.

| | Change | Where |
|---|---|---|
| G1 | **E2 at options.** A blank over 12 s is flagged (never refused): "a run of AI pictures that long reads as synthetic; find a footage cut-in, a B-roll clip or a frame that relates and split it, or say in intent why it must stay whole". The step says to act on E2 as on E1. | `validator.long_blank_flag`, step text |
| G2 | **`ai_run` at the plan.** In one gap, consecutive video shots (no still, frame or graphic between) over 12 s together are warned with the shots named: break the run with a footage frame, a still or a graphic. | `visual_contract.validate_plan` |
| G3 | **Shorter AI shots.** The same warning and the step say: inside such a gap the AI shots run three to five seconds, not eight; more cuts read as edited film and hide the drift. | the warning, step text |
| G4 | **Omni's scene extension** (its own deploy, after this one). Where one scene must run long, the take is grown in steps of 3 to 10 s with `previous_interaction_id` and "the scene continues" (fact sheet B10) instead of independent takes joined at shared pictures: one continuous shot up to 30 s. Needs: a `segments` list on the preparation (motion per step, the end picture only on the last), the provider's extend call and its polling per step, the assembly boundary rule off inside an extended scene, the cost per step on the ledger, the page's take row showing the steps. Its note follows once G1–G3 and design/84 are on VW-6. | later |
| | With design/84: server 0.31.0, plugin 0.29.0. | |

Tests first: `test_stage2_pure.py` (E2 at 13 s, none at 12 s, grouped under E2); `test_visuals_pure.py` (three 10 s video shots warn once, broken runs do not, a single 30 s shot warns); `test_visuals_cli.py` (the step and command texts). Not covered: server/tests (Docker); the effect on a film (the next run's plan is the check).
