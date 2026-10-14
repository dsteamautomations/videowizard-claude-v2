# VideoWizard v2 — target architecture proposal (for approval, nothing built yet)

Date: 14 Oct 2026. Status: **proposal**. Nothing in the repo, skill, workspace or database has been changed.

## 1. What I understood you want

| # | Your requirement | My reading |
|---|---|---|
| 0 | "For a while this will be the editor module as well. It will also create the child module." | Claude Code (this session type) is the **builder** for now: it writes the server and it produces the **execution module** that operators run. Later the builder role may move; the design must not depend on it staying here. **Please confirm this reading.** |
| 1 | Development and execution both happen | Two roles, two credentials, two machines/profiles. The builder never operates runs; the executor never changes code. |
| 2 | 3–4 operators at a time, logged in, separated | Per-user login, per-run ownership, one run cannot be driven by two executors at once. |
| 3 | The end user sees only the conversation | No procedure text, prompts, scripts, SQL, logs or internal files visible or editable by the operator. |
| 4 | Minimum on the website; internal processing data deletable | The site is a ledger plus approvals plus downloads. Working data lives on the executor machine and is deleted when the flow closes. |
| 5 | Server records the output of every stage; in-between work stays local | Each stage ends with a **stage output** committed to the server. Everything before that is local scratch with logs. |
| 6 | Each flow has its own file set: retained, uploaded or deleted | A per-run workspace with a manifest that says, per file, retain / upload / delete. |
| 7 | Images from OpenAI (GPT Image 2.5) via API key | Server-side provider module, key held on the server only. The agent never sees the key. Exact model id to be confirmed against OpenAI docs at build time. |

## 2. Redefined roles

The words Mother and Child stay, but they stop meaning "two chats with prose instructions".

| Role | Today | Proposed |
|---|---|---|
| **Mother** | A Codex chat that builds code, deploys, patches live data, and also writes the Child's instructions and watches its runs | **Builder.** Claude Code in the repo. Produces two versioned artefacts: the **server release** and the **executor plugin release**. Has no production run credentials. Never touches a live run. Reads defect tickets the executor files; never gets pasted chat. |
| **Child** | A Codex chat loaded with `SKILL.md` (prose) that interprets the published procedure and calls a connector | **Executor plugin.** A Claude Code plugin (commands, hooks, scripts) installed read-only on the operator's machine. Every stage is a script with a fixed contract. The model's discretion is limited to conversation and creative content (narration wording, shot descriptions, review notes). Tool allow-list enforced by hooks: the plugin's scripts only. No shell, no cloud CLIs, no database, no repo. |
| **Operator** | Implicit | The logged-in human. Talks to the executor in chat; approves in the browser (see §3.3). |
| **Server** | FastAPI + Supabase holding full run state, procedure text, and a wide UI | **Ledger + gatekeeper.** Owns the state machine, pins the procedure version per run, stores stage outputs and approvals, holds provider keys, enforces attempt caps and stop rules. UI is minimal. |

## 3. The architecture in one picture

```
 Operator laptop (one per person)                          Server (Supabase + small API)
 ┌───────────────────────────────────────────┐             ┌──────────────────────────────────┐
 │ Claude Code + executor plugin vX.Y (RO)   │  stage out  │ Ledger: runs, stage_outputs,     │
 │   /start /intake /brief /script /voice    │ ──────────▶ │   approvals, files, defects      │
 │   /media /analysis /plan /edit /visuals   │  next?      │ Gatekeeper: state machine,       │
 │   /assemble /deliver /close               │ ◀────────── │   version pin, attempt caps,     │
 │ runs/VW-11/  work/ (scratch, deleted)     │  approval   │   approval tokens                │
 │              out/  (uploaded)             │   token     │ Providers: ElevenLabs, Gemini,   │
 │              logs/ (deleted on close)     │             │   OpenAI images, video gen (keys)│
 └───────────────────────────────────────────┘             │ Web UI (minimal): login, my runs,│
          │ Resolve/FFmpeg on this or the Mac               │   stage output view, Approve,    │
          ▼                                                 │   Download, Close run            │
 Builder machine: Claude Code in repo → releases server vN + plugin vX.Y; reads defects   ◀───┘
```

### 3.1 The server decides what happens next
One endpoint answers "what can this run do now": `GET /runs/{id}/next` → allowed actions, who must act (operator / browser approval / background job / builder), attempts used of the cap, and the pinned procedure version. The executor plugin calls it before every step and shows the operator one sentence. The model never infers the order from text.

### 3.2 A run is pinned to a procedure version
`runs.procedure_version` is set at creation. Builder releases do not touch live runs. Adopting a newer version is an explicit `adopt` action the operator confirms, and the server lists what becomes stale. This removes the VW5 problem (19 releases under one run, one paid re-analysis).

### 3.3 Approvals and paid actions are two-phase and browser-side
The executor asks the server to **propose** (script, voice, analysis, image/video generation, delivery). The server shows it in the minimal UI with an **Approve** button. Approval creates a one-time token the executor must present to proceed. The model cannot write the approval itself. That closes the 1.6-second script acceptance and the "approved the script as whole" misread.

### 3.4 Stage outputs, not full snapshots
A stage output is a small record: run, stage, version, hashes and storage keys of the retained files, who approved, when. The server stores only these plus the retained files. No per-action full-state copy (today: VW5 19.8 MB across 333 copies). Intermediate work (frames, previews, candidate takes, logs) stays in `work/` and `logs/` and is deleted at `/close`.

### 3.5 Per-run workspace with a manifest
```
runs/VW-11/
  manifest.json   # per file: retain | upload | delete ; stage ; hash ; uploaded_at
  out/            # files that will be uploaded as stage outputs
  work/           # scratch; wiped on close
  logs/           # executor logs; uploaded as one archive on close (optional), then wiped
```
`/close` runs: verify every `upload` file has a server receipt → delete `work/` and `logs/` → leave `out/` only if the manifest says retain. A run can move to another machine (e.g. the Resolve Mac): `/pull VW-11` rebuilds the workspace from the ledger.

### 3.6 Stop rules live on the server
Per step: an attempt cap (default 2 for paid steps, 3 for others). On breach the server returns `NEEDS_USER_DECISION` with the options (retry once more / go back one stage / file a defect / stop). The executor must show it and wait. No agent-side loops; no human loop-breaking.

### 3.7 Defects go through a queue, not through you
When the executor hits an error outside its contract (5xx, provider failure, storage limit) it files a **defect record** (run, stage, request id, server error, local log excerpt) and stops. The builder reads the queue, reproduces against a copy of the run, and ships a fix as a release. The operator sees "waiting for builder; ticket #n".

### 3.8 Hiding the logic from the operator
- Procedures and prompts live on the server, fetched by scripts at run time, never written into the workspace.
- The plugin installs into a read-only location; the workspace contains only outputs and scratch.
- Hooks block the model from using Bash/Edit/Write outside the plugin's scripts and the run folder.
- Claude Code still shows tool calls in its UI. If that is too much exposure, Phase 3 wraps the same plugin scripts in a small Agent SDK app with a plain chat window. The plugin is built so that this is a packaging change, not a rewrite. **Decision needed (see §7).**

### 3.9 Concurrency (3–4 operators)
Supabase auth per user (exists). Runs are owned; a run has one active executor lease (machine id + user, renewed per step, expires). A second executor gets "run is active on <machine> until <time>; take over?" Provider rate limits and job queues are shared and fair-queued (analysis fair queue exists).

### 3.10 Images via OpenAI
A provider module on the server, same shape as ElevenLabs/Gemini today: the executor submits a prepared, approved request; the server calls OpenAI with its stored key, stores the result, records cost. The key is never on the operator machine or in any log.

## 4. What changes vs today

| Area | Today | Proposed | Reuse? |
|---|---|---|---|
| Auth, sessions, employees | Supabase, cookie sessions | Keep | Yes |
| Storage | Supabase Storage with offloaded state values | Keep for retained files only | Yes |
| Provider modules (ElevenLabs, Gemini, video providers) | Backend modules | Port; add OpenAI images | Mostly |
| Run state | One big JSON, full copy per revision | Stage-output ledger, small rows | **Replace** |
| Procedure | 54 definition rows, prose skill, hard-coded versions in 6 modules | Versioned procedure bundle; one pin per run | **Replace** |
| Workflow order | Known only through Voice; prose after | Server state machine, `next` endpoint | **New** |
| Approvals | Agent writes `paid_authorized:true` | Browser approval token | **Replace** |
| Operator skill | 178-line prose changelog + connector | Plugin: commands + hooks + scripts | **Replace** |
| Frontend | 10 run pages, components polling every 5–10 s | 5 pages: login, my runs, stage output, approve, downloads | **Replace** |
| Workers | Analysis/video/voice/media pollers writing per poll | Keep the job model; backoff; one event per state change | Partly |
| Mac/Resolve step | Separate package + scripts | Same plugin with assembly commands; run `/pull` on the Mac | Mostly |
| Mother ↔ Child handoff | You paste messages | Defect queue + releases | **New** |

Honest sizing: this is a **new core with ported edges**, not a refactor. The current backend has ~100 modules shaped around the big-state model; most of that code will not carry over.

## 5. Unstated requirements I would add

1. **Audit trail**: every approval, paid call and stage output records who/when/cost. Needed for 3–4 operators sharing budgets.
2. **Cost caps** per run and per day, enforced server-side before any paid call.
3. **Resumability**: an executor crash or laptop sleep must resume from the last stage output with no paid re-run.
4. **Preflight** at `/start`: storage limits, file size caps, provider keys valid, DB healthy, plugin version matches server. VW5 and VW10 both lost hours to limits a preflight would catch.
5. **Secrets hygiene**: provider keys only in server secrets; logs scrub tokens; operator machines hold only a session token.
6. **Retention policy**: what counts as "retain" per stage (final film, approved assets, stage outputs, approval records); everything else deleted; a server-side purge after N days for closed runs' scratch archives.
7. **Role-based views**: operator sees own runs; admin sees all runs and the defect queue; builder sees defects and releases, not run content beyond what a ticket includes.
8. **Versioned, testable procedures**: each stage script has a contract test; a release cannot ship if the plugin and server contract versions disagree.
9. **Operator takeover**: explicit handover of a run between people/machines with a recorded reason.

## 6. Edge cases and failure modes

| Case | Handling |
|---|---|
| Two executors on one run | Lease on the run; second one must take over explicitly; lease expiry 15 min |
| Network drops mid-upload | Chunked upload with server receipt per file; `/close` refuses to delete until every receipt exists |
| Executor crashes mid-stage | Stage is atomic on the server; local `work/` kept; `/resume` continues from the last stage output |
| Plugin version ≠ run's pinned version | Server refuses the step and names the version to install; `adopt` is the only way forward |
| Builder release while runs are live | No effect on pinned runs; dashboard shows "n runs on older versions" |
| Paid call times out with unknown outcome | Idempotent request ids (keep today's model); reconcile before any retry; never resubmit without reconcile |
| Provider refuses or rate-limits (OpenAI, ElevenLabs, Gemini) | Server maps to `NEEDS_USER_DECISION` with the provider message; no agent-side retry loops |
| Operator says something ambiguous ("looks fine", "approved") | Never an approval; the executor points to the browser Approve button |
| Operator asks the executor to debug / run SQL / check logs | Hooks block it; the executor offers to file a defect |
| Disk full / huge inputs | Preflight checks free space vs declared input size; cap per file and per run |
| Same person opens two chats on the same run | Second chat sees the lease and refuses to act |
| Secret rotation | Keys live only on the server; rotation needs no operator action |
| Closed run needs reopening | `/reopen` restores from ledger; scratch is gone by design, so only stage outputs exist |
| Time zones | Server stores UTC; UI shows operator's zone; stage output timestamps are UTC |
| Resolve not installed / Mac offline | Assembly stage shows "needs the Resolve executor"; run waits; no retries |
| Permissions | Operator cannot read another operator's run or any procedure text; admin role for oversight |
| Partial stage output (some shots done) | Stage outputs are per unit where the stage is per unit (per shot); the stage completes when all units have outputs |
| Log leakage of prompts/keys | Logs are structured; prompt bodies and keys are never logged; only ids and hashes |

## 7. Decisions I need from you before anything is built

1. **Operator surface.** (a) Claude Code desktop + plugin now (tool calls visible, nothing editable), with (b) an Agent SDK chat app as a later packaging step. My recommendation: start with (a), build the plugin so (b) is a wrapper.
2. **Core strategy.** New core with ported edges (my recommendation) vs incremental refactor of the current backend. Incremental keeps the big-state model that causes the DB load and the drift.
3. **Where the Resolve/assembly step runs.** Same plugin on the Mac via `/pull`, or keep a separate Mac package. Recommendation: same plugin.
4. **Retention list per stage.** What is retained on the server when a run closes. My default: final film, approved narration, approved images/videos, every stage output record, approval records, cost ledger. Everything else deleted.
5. **Who is admin.** You only, or also a second person.
6. **Confirm my reading of requirement 0** (this Claude Code setup is the builder for now, and it produces the executor plugin).

## 8. Suggested order of work (after approval)

1. Ledger + state machine + `next` endpoint + version pin + approval tokens (server core).
2. Executor plugin skeleton: `/start`, `/next`, workspace manifest, hooks allow-list, `/close`.
3. Port stages one at a time behind contract tests: intake → brief → script → voice → media → analysis → planning → visuals (with OpenAI images) → assembly → delivery.
4. Minimal web UI.
5. Defect queue and builder workflow.
6. Optional SDK-wrapped operator app.

Each step gets the requirement/edge-case list and tests first, per your working rules.

## Not covered

- Cost estimates and timelines (depends on decisions in §7).
- Exact OpenAI image model id and pricing (to be confirmed against current OpenAI docs at build time).
- Migration of VW5/VW10 history into the new ledger (likely export-only, not live migration).
- Any change to how DaVinci Resolve is driven; only where that step runs.
