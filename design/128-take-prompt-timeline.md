# design/128: the take prompt carries the plan's timeline and end state (approved by SK 1 Nov 2026; built in server 0.77.9)

Source: the G07-S4-SH1 standalone test, 1 Nov 2026 (`../g07-s4-sh1-test/g07-s4-sh1-timeline-test.md`). The same start picture and the same wrapper were used throughout:

| Prompt | Take | Result |
|---|---|---|
| events in one sentence | take 1 | the hand breaks the brick, the brick vanishes |
| the same events with seconds | A, B | the break lands on time and the brick stays |
| + the picture's gender | C | no worse |
| + an end state for the broken piece | D, D2 | 2 of 2 pass |
| A + `thinking_level: high` | AH | worse |

## Requirement

From now on, the text sent to Omni for a take (`motion_text`, server) carries what the plan already knows:
- **when** each beat happens, in seconds;
- **what is left at the end** and must stay in view;
- a **warning** when the motion prompt's pronoun contradicts the one person in the shot.

**VW-12 is not touched.** Its prepared and submitted takes keep their frozen prompts, and a VW-12 shot prepared again after the deploy also gets today's prompt. The flow is unchanged: same stages, steps, commands and pages. The operator's Claude writes the motion prompt exactly as now.

## Changes

| # | Change | Where |
|---|---|---|
| T1 | **Timeline from the beats.** After the motion prompt, one line per beat of every acting subject, in time order, in seconds from the shot's start (one decimal): `0.0–2.0 s: <subject name>: <action>; <result>.` The block opens with "The events happen in this order and at these times:" and closes with "Then hold until <N> s." when the take is longer than the last beat. | `video_providers.motion_text`; the beats go into the request record at `prepare_take` (`visuals_stage.py`), like `changes` today |
| T2 | **End state from the change list.** One line: "By the end and until the last frame: <what 1>; <what 2>; each stays where it is, in plain view." It comes from `shot.changes[].what`, which the plan already requires on every acting video shot (design/91 N1). | `motion_text`, from the record's `changes` |
| T3 | **Pronoun warning.** When the shot has exactly one person and that person's description says man or woman, a he/his/him or she/her/hers in the motion prompt that contradicts it adds a warning to `prepare-take`'s reply. It is never a refusal. | `prepare_take` |
| T4 | **Gate: VW-12 keeps the old builder.** The request record gets `prompt_version: 2`; runs in `OLD_PROMPT_RUNS = {'VW-12'}` (a server constant) are prepared without T1 and T2. A request that has no `prompt_version` is read as 1. | `prepare_take` |
| T5 | **Thinking stays off.** `thinking_level` is not added to the Omni request (take AH was worse). This is a note in the Omni fact sheet's Part C; there is no code. | library note |

Old ways (design/35): **the take prompt without a timeline** is kept for VW-12 only, until VW-12 closes; then the constant is emptied and the old way is retired. "A motion prompt in one sentence" is not refused: T1 adds the times whatever the operator's Claude writes.

## Unstated but expected

- The seconds come from the beats' film frames and the session's fps, the same arithmetic `prepare_take` already uses for `changes[].at_s`.
- Names come from the plan's elements (`name`), never ids.
- The digest of the request changes because the text changes. That is expected: a prepared take is frozen, so nothing already prepared changes.
- The shot's review (Gemini's marks with seconds) reads the same beats, so the timeline it checks against is now the one Omni was given.

## Edge cases and how each is handled

| Case | Handling |
|---|---|
| A shot with no acting subject (held subjects, ambient only) | No timeline block and no end-state line; the prompt stays as today |
| Two subjects whose beats overlap | Both lines, in start order; overlap is allowed (two people at work) |
| A beat starting after the take ends (impossible: `validate_plan` refuses beats outside the shot) | Not handled again |
| The take is longer than the placement (8 s for 7.7 s) | The last line is "Then hold until 8 s." |
| The motion prompt already names its own seconds | Both are sent; `prepare-take` warns: "the motion prompt names its own times; the plan's timeline is sent too: make them agree" |
| A change whose `beat_id` is missing from the beats | That change is still in the end-state line (it names what, not when) |
| No changes on the shot | No end-state line (already a plan warning, design/91) |
| More than one person, or a description with no gender | No pronoun check |
| A pronoun about an object or an animal (it) | Not checked; only he/his/him/she/her/hers |
| An end-image shot (`end_state_exact`) | Timeline and end state are added too; they describe the path to the end image |
| Very long beat text | Each beat's action is already capped at 3000 characters by the plan; Omni's context is 1M tokens |
| A request record from before the deploy (no `prompt_version`) | Read as version 1; it is never rebuilt |
| VW-12 after it closes | The constant is emptied in a later release; no data migration |

Failure modes: if building the timeline raises (bad plan data), `prepare_take` refuses with the shot and the beat named. It never sends a prompt with a half-built block. Nothing here touches payment, keys or retries.

## Tests first (server/unit, pure)

1. A shot with two beats gives two timeline lines with the right seconds (from frames and fps) and in time order.
2. Overlapping beats of two subjects are both listed, in start order.
3. A take longer than the last beat adds "Then hold until N s.".
4. Changes give the end-state line; no changes gives no line.
5. A held-only shot gives today's prompt exactly (the old text, byte for byte).
6. A VW-12 request gives today's prompt exactly; another run gets T1 and T2.
7. The pronoun warning: one man described and "her" in the prompt warns; "his" does not; two persons never warn.
8. A motion prompt with its own seconds warns.
9. The G07-S4-SH1 shape (one engineer beat plus brick beats) produces a block equivalent to the one in take D.

## Not covered

- server/tests (Docker suite): run if Docker is up on this PC, else listed as not run.
- Whether the plan's beats for real shots are fine-grained enough. A shot planned as one beat ("tests the brick") gets one line, which is no better than today. The test of that is the first new run.
- The "no one touches the brick" lines from take A: shot-specific, and take B showed they weren't needed.
