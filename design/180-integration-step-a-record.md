# 180 — Integration step A: the record of every generation, and a hand-in that says how it was made

12 Nov 2026. Approved by SK ("Approved, build"). Requirements: `videobuilder-v4/integration/step-a-requirements.md` (second version); parent `videobuilder-v4/integration/requirements.md`.

## Why

The new AI video process (a Blender guide, a GPT image still, a Gemini edit) is being built into the application step by step. Every later step writes into one record per attempt of a shot. This step lays that record and uses it for the one thing that exists today: a finished file handed in.

SK, 12 Nov: the application is still with developers and testers, so there is no per-film switch between an older way and the new one. Each step replaces its part of the older way and deletes it in the same step.

## What changed

- **`vw2_generations`** (migration 014): one row per attempt of a shot (`run_id`, `shot_id`, `attempt`, `how`, `verdict`, `record`). `record` is a list of dated entries. The application never updates or deletes a row in this step.
- **`server/app/generations.py`**: `opened` (a new attempt with its first entry, numbered next for the shot) and `of_shot` (all attempts, oldest first).
- **`visuals_stage.add_asset`** takes `made`: how the file was made, required, at most 2,048 characters, refused (never cut) beyond. The record row is written before the file is placed, so a failed write places nothing.
- **`visuals_stage.generations_of`** and `GET /api/runs/{run}/visuals/shots/{shot}/generations`: the attempts of a shot; rows of a shot the plan no longer holds are still read; a shot with neither rows nor a place in the plan is refused.
- **The page and the status**: a handed-in shot says "made outside; checks skipped" with the words given; files handed in before this release are marked too (from the shot's own data).
- **The chat tool**: `vw visuals asset … --made "…"` (refused before anything is sent when missing) and `vw visuals generations --shot S`. The command is `generations` because `vw visuals record` already records gaps.
- Server 0.93.0, plugin 0.79.0, minimum plugin 0.79.0.

## Older way

A hand-in without a description: retired, refused with the way to give one (design/35 old ways 37).

## Tests

`server/unit/test_step_a_generations_pure.py` (16), `plugin/tests/test_step_a_generations.py` (4), two page assertions. The page states were rebuilt; their film now names a motion style, without which no state past the treatment could be built since design/179.

## Not covered

- The procedure text does not mention `--made`: two tests hold the visuals instructions to their length and layout, and the refusal names the exact command. The guide's instruction texts are rewritten in the steps that build the new process.
- `server/tests` (they need Docker): their three hand-in calls were updated, not run.
- The limits in one place (step D); the admin page (step F).
- Four plugin tests fail on Windows on every commit (line endings, a Mac path); not from this change.
