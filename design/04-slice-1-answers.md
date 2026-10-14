# Slice 1 — answers to your five questions, and how v2 addresses the v1 findings

## Q1. New tables?

Yes. Same Supabase project (VideoBuilder), new tables with the prefix **`vw2_`**: `vw2_runs`, `vw2_stage_outputs`, `vw2_approvals`, `vw2_attempts`, `vw2_jobs`, `vw2_defects`, `vw2_procedures`, `vw2_sessions`, `vw2_receipts`. The existing `videowizard_*` tables are not read, written or dropped. When you retire v1 you drop them in one statement.

## Q2. Login: am I redoing it? No.

- **"Stub"** means a temporary stand-in used only by the tests. The tests run against a throwaway local Postgres in Docker, which cannot reach your shared employee directory, so a test inserts a session row directly and calls the API with that token. Nothing about it ships.
- **"Real login"** means **your existing login, ported unchanged**: username + bcrypt password from the shared `employees` table (field `ef-02` / `ef-11`), and the role (`Admin` / `Member`) from `apps.members` for this app id. That is `backend/app/auth.py` today (`sign_in`, `current_user`, `require_admin`). I will copy it into v2 in **slice 1**, not slice 3, so there is no confusion. The only addition is the `kind` of a session (`browser` or `executor`), which v1 already stores in `videowizard_sessions.kind`.
- Roles: your `Admin` becomes v2's admin; `Member` is an operator. No new role table.

## Q3. Going back: view vs revise

You are right that one "Back" button mixes two things. Split them:

| Action | What it does | When allowed | Cost |
|---|---|---|---|
| **View** | Read-only screen of any earlier stage's output | Always, from the run page; no state change | None |
| **Revise** | Reopen a stage to change its output | Depends on what sits after it (rules below) | May obsolete later work |

Revise rules, decided by the server from the stage table:

1. **Nothing paid after that stage** (e.g. you are at *script* and want to change the *brief*): allowed. Later text stages are marked stale and are redone; they are cheap model calls.
2. **Paid work exists after that stage** (e.g. change the *script* after narration was generated, or the *brief* after images were generated): **blocked by default.** The server replies with the list of paid outputs that would become obsolete and their recorded cost. The operator can then choose **Discard and redo**, which is a browser approval like any paid action. Nothing is lost until that approval exists.
3. **Per-unit revise** covers most real cases without triggering rule 2: redo *one* shot's images or *one* clip's analysis, leaving the others intact. This is how "redo scene 4" works.
4. **Run attributes** (title, client name, notes) are not stage outputs and can be edited at any time; they never obsolete anything.

What I will not build: partial edits inside an approved output (for example fixing one word of a script after narration exists). If that need shows up, the cheap answer is a per-passage re-narration unit, as v1 had, not an edit of the approved script.

## Q4. Too many reads and writes: what changes

| v1 behaviour (from the review) | v2 rule |
|---|---|
| Every action rewrites the whole run `state` and stores a full copy as a revision (VW5: 19.8 MB over 333 copies; VW10: 150–300 KB per action) | No run state blob. A stage output is one small row: stage, unit, file hashes + storage keys, short summary, approval id. A run like VW10 (44 actions) becomes roughly 44 rows × ~2 KB ≈ 100 KB in the database; the files live in storage. |
| Planning rewrote four 150–260 KB documents 55–63 times each | Intermediate planning documents stay in the executor's `work/` folder. Only the final plan is uploaded, once, as a file. |
| Video worker wrote 2 event rows + 2 job updates per provider poll (339 "storage pending" events on one run) | No event table. One `jobs` row, updated only when the state changes; polling the provider with backoff. |
| UI polled full-run endpoints every 5–10 s on every page, forever | The run page polls `next` (a few hundred bytes) every 10 s only while an approval or job is pending, then stops. |
| Request receipts stored the full response JSON | Receipts store status code + a small response; never request bodies. |
| Definitions fetched from the database on every call | Procedure bundle loaded once per version and cached in memory. |
| Workers listed all active runs every few seconds (fixed on 12 Oct) | Kept fixed: workers claim by job row, not by scanning runs. |

## Q5. "Propose body larger than 256 KB" explained

It is a deliberate guard, not a capacity limit. `propose` carries the JSON the browser shows on the Approve screen (a summary, a few numbers, file hashes). If a client sends more than 256 KB it means someone is pushing a whole plan, analysis or script blob into the database again, which is the v1 habit from Q4. The server refuses (413) so the mistake is caught in development, not in production three weeks later. Large content goes to storage via `/files/sign`; the database keeps the hash and a short excerpt. The number is a setting; 256 KB is generous (a full script is ~20 KB).

## How this approach addresses the critical v1 findings

| # | v1 finding (review ref) | Evidence | How v2 addresses it | Slice |
|---|---|---|---|---|
| 1 | No run-level version pin; procedure republished under live runs (19 visuals releases during VW5; paid re-analysis) | 02 §2, 03 RC2 | `vw2_runs.procedure_version` set at creation; releases never touch live runs; `adopt` is an explicit, confirmed step | 1 |
| 2 | After Voice the app does not know the stage order; `next_action` is "follow the published procedure" | 01 M2, `operator.py:66-81` | `GET /runs/{id}/next` computed from a stage table; every write re-checks it; the agent cannot skip or reorder | 1 |
| 3 | Approvals and paid flags written by the agent (`paid_authorized: true`); 1.6-second script acceptance | 01 M3, 03 RC3 | Two-phase: executor proposes, a browser session approves, token required on commit; executor sessions cannot approve | 1 |
| 4 | No attempt caps outside Analysis; loops ended only by you | 01 M5, 02 §4 | Server counts attempts per (stage, unit); over the cap → `409 NEEDS_USER_DECISION`; no silent retry | 1 |
| 5 | Full-state snapshot per action; planning docs rewritten 55–63×; per-poll event rows | 06 A1, A2, A9 | Stage-output rows, files in storage, intermediate work local, one job row per job | 1, 5, 6 |
| 6 | UI polling of full runs every 5–10 s, never stops | 06 A3, A4, A5 | Polls `next` only while something is pending | 3 |
| 7 | Skill is a changelog with run-specific lines; versions in the skill disagree with the server | 01 §7, M8 | No prose procedure in the plugin; procedure content lives on the server per version; plugin checks `plugin_min_version` at start | 2 |
| 8 | Operator becomes a developer when something breaks (70 min of infra debugging in a VW10 chat) | 02 §3 | Hooks restrict the executor to its own scripts and run folder; blockers become defect tickets | 2, 9 |
| 9 | Global `~/.codex/AGENTS.md` and shared memory load developer rules into operator chats; unrequested MD files | 04 | Separate operator profile with its own five-line `CLAUDE.md`; your global rules are not loaded there | 2 |
| 10 | Mother/Child relay through you; one-symptom-at-a-time fixes (7.5 h review-render loop) | 02 §4 | Defect queue; builder reproduces on a copied run; fix ships as a release | 9 |
| 11 | SQL functions pasted forward across 12 migrations; live bodies not rebuildable | 06 B1 | Each function defined once per file; a migration that changes a function replaces it in full | 1 |
| 12 | Expired lease → `submission_unknown`, needs a human; stuck jobs after redeploy | 06 C1, 02 §1 | Jobs reconcile by `request_id` before any retry; a stuck job becomes `NEEDS_USER_DECISION`, never a silent state | 6 |
| 13 | Prompt sources ignored by `.gitignore`; fresh clone fails tests | 05 | Procedure bundles are versioned JSON in the repo and loaded by a migration; nothing ignored | 1 |
| 14 | Infrastructure limits rediscovered per run (50 MB cap on VW5, again on VW10) | 02 §1 | Four-check preflight at `/vw start` plus operator confirmations | 2 |

Not addressed by design (proportionality): per-user rate limits, audit tables, spend caps in code, lease timers. See pattern §3.
