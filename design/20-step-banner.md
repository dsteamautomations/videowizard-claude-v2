# 20 — "Where am I" step banner (proposal, awaiting SK's approval)

Date 15 Oct 2026. Raised by SK during VW-2: the operator cannot tell which step the run is on or what comes next.

## Requirement (restated)
At any moment in the operator chat, the operator can see: the current step number and name out of the total, what the run is waiting on, and the next step.

SK's format, extended by one line:

```
Step 7 of 12 · Options  →  next: Master
Waiting on: your yes to the scenes and pauses
```

## What already exists
- The server already computes the current step for every run (the `next` endpoint): stage name, open units, whether it is blocked.
- The stage order is fixed per procedure version (version 2 has 12 steps: Intake, Brief, Script, Voice, Media, Analysis, Options, Master, First cut, Visuals, Assembly, Delivery).
- A run page already exists at `http://localhost:8002/runs/VW-2`, listing stages and outputs.

## Where to show it (options)
| Option | Where it appears | Reliability | Effort |
|---|---|---|---|
| A. Banner in replies (recommended) | Top of every assistant reply that reports status or moves the run | High if the server writes the banner text and every `vw` response carries it; the assistant only copies it | Small |
| B. Run page tracker (recommended) | Browser tab, a row of 12 steps with the current one highlighted | Always right; needs the operator to keep the tab open | Small |
| C. Hook that injects the step each turn | Assistant context before each operator message | Makes A work even when no `vw` command ran that turn; one server call per message | Small |
| D. Claude Code status line | Bottom bar of the terminal | Always visible in the terminal CLI; not confirmed to show in the desktop app's Code tab | Small, uncertain value |

Recommendation: A + B now. Add C only if the banner is missed in practice.

## Unstated but expected requirements
1. The server is the single source of the banner text, so the plugin, the chat and the run page never disagree.
2. Steps use friendly names, not internal names (`First cut`, not `first_cut`).
3. Numbering is fixed per procedure version. A skipped step keeps its number and says "skipped".
4. Per-clip steps show progress: `Step 6 of 12 · Analysis (38 of 46 clips) → next: Options`.
5. Long steps show their sub-steps: Options = scenes → options → review film → your yes.
6. "Waiting on" says who acts next: you, the server (a job running), or a decision after repeated failures.
7. The banner costs no paid call.

## Edge cases
| Case | Banner behaviour |
|---|---|
| Run closed | `Run VW-2 closed · all 12 steps done` |
| All steps done, not closed | `All 12 steps done → next: close the run` |
| Step blocked after three failures | `Step 7 of 12 · Options · needs your decision (retry, revise, report, stop)` |
| Revision makes later steps stale (going back) | Number moves back to the revised step; banner adds `(revised: later steps will be redone)` |
| Visuals skipped (no gaps) | `Step 10 of 12 · Visuals · skipped (no gaps)` then moves on |
| Version 1 run (has Planning) | Uses the version 1 step list and its own total |
| Background job running (analysis, render) | `Waiting on: the server (render 2 of 2)` |
| Run taken over on another machine | Banner names the active machine; no step actions from here |
| No active run in the workspace | `No run open · start one with /vw start` |
| Server unreachable | Last known banner, marked `(offline: last known at 14:05)` |

## Failure modes
- Assistant forgets to print it: mitigated by the ready-made text in every response; option C if it recurs.
- Banner text and run page disagree: impossible by design, both read the same server function.
- Server down: the plugin shows the last saved banner from the local run manifest with the offline mark.

## Tests (after approval)
One test per edge case row above, on the server function; one plugin test that every `vw` response carries the banner; one run page test for the highlighted step.
