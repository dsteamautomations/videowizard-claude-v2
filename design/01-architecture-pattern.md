# Agent-operated application: the reusable pattern

Use this for any app where a person talks to an AI agent and the agent drives the application. It is written to be copied into the next project and edited. VideoWizard v2 is the first use; see [02-videowizard-v2-build-plan.md](02-videowizard-v2-build-plan.md) for the specific build.

## 1. The three parts

```
 Operator machine                         Server                          Builder machine
 ┌──────────────────────────┐   outputs   ┌──────────────────────┐  releases  ┌──────────────────┐
 │ Agent + executor plugin  │ ──────────▶ │ Ledger + gatekeeper  │ ◀───────── │ Agent in the repo│
 │ runs/<id>/ out work logs │ ◀────────── │ (state, approvals,   │ ──────────▶│ (builds server + │
 │                          │   next?     │  keys, providers)    │  defects   │  plugin)         │
 └──────────────────────────┘             └──────────────────────┘            └──────────────────┘
```

| Part | Job | Never does |
|---|---|---|
| **Builder** | Writes the server and the executor plugin. Ships numbered releases. Reads defect tickets. | Operate a run. Hold production run credentials. Patch live data by hand. |
| **Executor plugin** | Runs on the operator's machine inside the agent. One script per stage with a fixed input/output contract. Keeps a per-run workspace. | Decide the order of stages. Hold provider keys. Debug the server. Read procedure text into the workspace. |
| **Server** | Decides what is allowed next. Pins the procedure version per run. Stores stage outputs and retained files. Calls paid providers with its own keys. Counts attempts. | Store scratch. Expose procedure text to the operator. Trust an approval written by the agent. |

The operator (human) talks to the executor in chat and approves in the browser.

## 2. The seven rules

1. **The server owns the order.** One endpoint, `GET /runs/{id}/next`, returns the allowed actions, who must act, and attempts used. The executor calls it before every step. The agent never infers the order from prose.
2. **One version per run.** A run is pinned to a procedure version at creation. Releases never change a live run. Moving a run forward is an explicit `adopt` step.
3. **Approvals are browser-side.** Anything paid or irreversible is *proposed* by the executor and *approved* by a button in the server UI. The approval token is required on the next call. The agent cannot approve.
4. **Stage outputs are the record.** A stage ends with one small record (files by hash, who approved, when). Everything else is scratch on the operator machine, deleted on close.
5. **Attempts are capped on the server.** On breach, the server returns `NEEDS_USER_DECISION` and the executor stops and asks. The human is never the loop breaker.
6. **Executor and builder are separated by permissions, not instructions.** Hooks restrict the executor's tools to its own scripts and run folder. Separate agent profile, separate `AGENTS.md`/`CLAUDE.md`, separate memory. The builder profile has no production run credentials.
7. **Blockers become tickets.** The executor files a defect record and stops. The builder fixes and releases. Nobody relays chat between agents.

## 3. Proportionality: build only what the tool needs

This pattern is for a small team (one builder, a few operators). Default to the cheap version of every control. Reach for the heavier one only when a real run has shown the need.

| Concern | Build this (cheap) | Do **not** build (enterprise) | Or ask the operator to ensure |
|---|---|---|---|
| Who can see a run | `owner_id` on the run; an `is_admin` flag on the user | Roles, permissions tables, per-stage visibility | — |
| Two people on one run | `active_machine` on the run; a second `/start` asks "take over? y/n" | Lease tables, expiry timers, takeover reasons | One person per run at a time |
| Spend | Record cost per paid call in the stage output | Daily caps, budgets, alerts | Set spend caps on each provider's dashboard |
| Secrets | Keys in server environment only; never log request bodies | Rotation flows, vaults, scrubbing pipelines | — |
| Preflight | 4 checks at `/start`: logged in, plugin version matches, free disk ≥ declared input, provider keys present | Health dashboards, synthetic checks | Files under the size limit, Resolve installed on the Mac, enough disk |
| Retention | A manifest per run; `/close` deletes scratch; a "delete run files" button for admin | Scheduled purge jobs, legal-hold logic | Download what you want to keep before closing |
| Audit | Stage outputs + approvals already say who/when | Separate audit log, tamper-evidence | — |
| Tests | Tests for each stage contract and for the state machine | CI gates that block releases on version drift | Install the plugin version the server names |
| Rate limits | Provider's own 429 → `NEEDS_USER_DECISION` | Client-side throttling, queues per user | Run fewer jobs in parallel if the provider complains |
| Log hygiene | Structured logs with ids and hashes, no prompt bodies | Redaction tooling | — |

Rule of thumb: if a control exists only because "an enterprise would have it", drop it. If it exists because a run lost hours without it, keep it.

## 4. Things to ask the operator at `/start` instead of checking in code

Collect these as inputs; trust the answers.

- Run title, client, which machine will do each heavy step (e.g. the Resolve Mac).
- Confirmation that input files are under the limit and already in the run's `in/` folder.
- Confirmation that provider spend caps are set.
- Who approves (if not the operator).
- Whether to retain scratch logs on close (default no).

## 5. Starting a new app from this pattern

1. List the stages and, for each: inputs, output files, does it need approval, is it paid, is it per-unit (per shot, per page…).
2. Write the state machine as a table (stage → allowed next, who acts, attempt cap). This table *is* `next`.
3. Define the stage-output record and the workspace manifest.
4. Write the plugin skeleton: `/start`, `/next`, `/close`, `/pull`, one script per stage, two hooks (tool allow-list, path allow-list).
5. Port providers behind the server with keys in environment.
6. Minimal UI: login, my runs, stage output, approve, download, close.
7. Defect queue: one table, one form, one list for the builder.
8. Only then: the stages themselves, one at a time, tests first.

## 6. Signs you are drifting back

- Procedure text appears in a skill or in the workspace.
- A release changes the behaviour of a live run.
- The agent writes `approved: true` anywhere.
- An operator chat runs `gcloud`, SQL, or reads source.
- A human is pasting messages between two agents.
- A Markdown report appears that nobody asked for.
