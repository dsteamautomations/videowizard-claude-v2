# VideoWizard v2 — build plan

Date: 14 Oct 2026. Decisions from the proposal are locked as recommended (see §1). This document is the one to change if the build changes. The reusable pattern behind it is [01-architecture-pattern.md](01-architecture-pattern.md).

## 1. Locked decisions

| # | Decision | Choice |
|---|---|---|
| 1 | Operator surface | Claude Code desktop + executor plugin now. Agent SDK chat app later, as a wrapper, if tool-call visibility is still a problem. |
| 2 | Core strategy | New core in a new folder (`videowizard-v2`); port auth, storage and provider modules from `videowizard-beta`. |
| 3 | Resolve step | Same plugin on the Mac; `/vw pull <run>` rebuilds the workspace there. |
| 4 | Retention on close | Keep: final film, approved narration, approved images and videos, every stage-output record, approvals, cost per paid call. Delete: everything else. |
| 5 | Admin | You. One `is_admin` flag. |
| 6 | Builder for now | This Claude Code setup, in the `videowizard-v2` repo. It produces the executor plugin. |
| 7 | Images | OpenAI GPT Image 2.5 via a server-side provider module; key in server environment. Model id confirmed against OpenAI docs when that stage is built. |
| 9 | Paid actions (decided 14 Oct) | **Information, not a gate.** The executor tells the operator what a step costs and proceeds. No approval button, token or question for paid work. Cost is recorded on the stage output. Attempt caps stay (loop protection, not money). |
| 10 | Stage acceptance | Given **in chat**, not in the browser. The executor asks "approve the script? (yes / changes)" and commits only an explicit yes to that question, storing the operator's reply verbatim. Ambiguous replies are asked again. Trade-off accepted: a misread is possible; it is caught by the recorded quote and by revise. |
| 8 | Video assessment (analysis stage) | **Superseded 14 Oct 2026 evening: `gemini-3.8-flash`, thinking HIGH, AGENTIC on every clip (design/11 Phase 1; design/13 §6).** Original: **Gemini 4 Argon** (`gemini-4-argon`) replaces `gemini-3.8-flash`. See §5a. Planning stays on its current Gemini model unless you say otherwise. |

## 2. Proportionality for this build

Approvals: no browser Approve button, no paid gate (decisions 9–10). Acceptance of a stage is the operator's explicit yes in chat, stored verbatim.

Everything in [pattern §3](01-architecture-pattern.md#3-proportionality-build-only-what-the-tool-needs) applies. Specifically **not** built in v2: roles beyond owner/admin, lease timers, spend caps, key rotation, purge jobs, audit tables, CI version gates, client-side throttling, redaction tooling. If a run shows the need, add the single cheapest thing.

**Asked of the operator at `/vw start`** (trusted, not checked; revised 14 Oct 2026 after the first live start: only the client is asked at start, the title is chosen at intake, input files are asked for by the intake/media steps when they need them, the assembly machine is asked at the Mac stage, and provider spend caps are a one-time setup note in the operator guide). Original list: title and client; input files already in `runs/<id>/in/` and under 200 MB each; provider spend caps set on ElevenLabs, Google and OpenAI dashboards; which machine runs assembly; whether to keep logs on close (default no).

## 3. Stages

Carried over from v1 with two merges (noted). Per stage: output, acceptance (in chat), paid (informed, not gated), per-unit, attempt cap.

| # | Stage | Output record contains | Acceptance | Paid (informed) | Per-unit | Cap |
|---|---|---|---|---|---|---|
| 1 | intake | source text hash, numbered source, client | yes (chat) | no | no | 3 |
| 2 | brief | brief.json | yes | no | no | 3 |
| 3 | script | script.json (passages) | yes | no | no | 3 |
| 4 | voice | chosen voice id, narration.mp3, timing.json | yes (chat; listen via download link) | yes, informed | no | 2 |
| 5 | media | list of linked media ids + hashes | yes | no | no | 3 |
| 6 | analysis (Gemini 4 Argon, §5a) | per-media analysis.json | no (starts on media approval) | yes | per media | 2 |
| 7 | planning | plan.json (scenes, shots, gaps) | yes | yes (Gemini planning calls) | no | 2 |
| 8 | edit | review render (movie) + editable timeline ref | yes (chat; watch via download link) | no | no | 2 |
| 9 | first_cut | first-cut file hash | yes | no | no | 2 |
| 10 | visuals | per shot: references, generated images (OpenAI), local assets, generated video takes, selected take | yes per shot batch | yes (images, video) | per shot | 2 per shot |
| 11 | assembly | assembled timeline + preview movie | yes | no | no | 2 |
| 12 | delivery | final film hash, package | yes | no | no | 1 |

Merged from v1: *editing settings* folds into planning inputs; *visual review* folds into edit (the review is the approval). The v1 "visual direction / references / local assets / video generation" sub-steps become units inside `visuals`, each with its own stage-output row, so a run can stop and resume mid-stage without paid re-runs.

**Allowed order:** strictly 1→12. Going back: `/vw view <stage>` is read-only; `/vw revise <stage>` reopens it (blocked with a cost list if paid work after it would be discarded, until the operator confirms in chat). No skipping.

## 4. Data model (Supabase, Postgres)

Reuse: `auth` users, employee/session tables, Storage bucket. New tables (replace all `videowizard_*` state tables):

```
runs            id, code, title, client, owner_id, procedure_version, stage, status(open|closed),
                active_machine, created_at, closed_at
stage_outputs   id, run_id, stage, unit (null or shot id/media id), version, files jsonb [{name,key,sha256,bytes}],
                summary jsonb (small), cost_cents, accepted_by, accepted_at, accepted_quote, created_at, stale bool
-- no approvals table: acceptance is recorded on the stage output (accepted_by, accepted_at, accepted_quote)
attempts        run_id, stage, unit, count            -- one row per (run, stage, unit)
jobs            id, run_id, stage, unit, provider, request jsonb, request_id (idempotent), status,
                result jsonb, error, created_at, updated_at   -- background provider work
defects         id, run_id, stage, error, log_excerpt, status(open|fixed), created_at
procedures      version, stage, document jsonb       -- prompts + stage contract; one version = one bundle
```

No full-state snapshot anywhere. The run's current state is derived from `stage_outputs` (latest non-stale per stage/unit).

## 5. Server API (FastAPI, small)

```
POST /runs                         create (pins procedures.current)
GET  /runs                         mine (admin: all)
GET  /runs/{id}                    run + latest outputs
GET  /runs/{id}/next               {stage, unit?, actions[], actor(operator|browser|job|builder), attempts, cap, version}
POST /runs/{id}/output             {stage, unit?, files[], summary, accepted_quote?} → stage_output (quote required when the stage needs acceptance)
POST /runs/{id}/jobs               {stage, unit?, provider, request} → job (server calls provider with its key; cost recorded)
GET  /jobs/{id}
GET  /runs/{id}/stages/{stage}     view (read-only)
POST /runs/{id}/revise             {stage, unit?, confirm_quote?} (quote required when paid work after it would be discarded)
POST /runs/{id}/adopt              {version}
POST /runs/{id}/close              verifies receipts for all retained files
POST /runs/{id}/defects
GET  /procedures/{version}/{stage} executor scripts only (session-bound); never written to disk by the plugin
POST /files/sign                   signed upload URL for a retained file
```

Idempotency: every write carries a client `request_id`; replay returns the stored result (keep v1's receipt idea, without storing full responses). Attempt caps: `output` and `jobs` increment `attempts`; on `count > cap` return `409 NEEDS_USER_DECISION {options:[retry, back, defect, stop]}`.

Providers behind `/jobs`: ElevenLabs (voice), Gemini 4 Argon (analysis), Gemini (planning), OpenAI GPT Image 2.5 (images), existing video providers (takes). Keys in server env. Workers: one background loop per provider family, polling the provider with backoff, writing one `jobs` row update per state change, no event table.

### 5a. Analysis provider: Gemini 4 Argon (checked against Google docs, 14 Oct 2026)

| Item | Value | What it means for the build |
|---|---|---|
| Model id | `gemini-4-argon` (stable; "latest update October 2026") | One constant in the analysis provider module |
| SDK | Python `google-genai` ≥ 2.30.1 (or raw REST as v1 does) | v1 calls REST directly; keep that, no SDK needed |
| Inputs | text, image, video, audio, PDF; output text; structured JSON output supported | Same shape as today's per-media analysis |
| Context | one shared 1,048,576-token limit for input + output; default output cap 65,536 streaming / 32,768 non-streaming | Fine for per-clip analysis; no long-decode needed |
| Thinking | `thinking_level`: LOW / MEDIUM (default; Google names "video understanding" here) / HIGH | Use MEDIUM; v1 used HIGH on 3.8-flash |
| Removed params | `thinking_budget`, `MINIMAL`, `frequency_penalty`, `presence_penalty`, `candidate_count` → HTTP 400; `temperature`, `top_p`, `top_k` ignored; explicit caching unsupported | **v1's worker sends `temperature` and `thinkingConfig.thinkingLevel`** (`analysis_worker.py:222`); drop `temperature`, keep thinking level, keep `mediaResolution` |
| Video modes | `processing: "static"` (default, 1 fps, `fps` and `start_offset`/`end_offset` adjustable) or `processing: "agentic"` (model navigates the video itself; recommended for > 5–10 min; up to 88% fewer tokens on long content) | Default **static** for source clips (most are short); **agentic** automatically when a clip is longer than 5 min. Flag per job, overridable per run. |
| Files | Files API up to 20 GB (paid); inline under 20 MB | Keep v1's Files API upload path |
| Pricing (per 1M tokens) | $2 in / $10 out until 30 Nov 2026, then **$4 / $20**. Batch and Flex: half price. 3.8-flash for comparison: $0.75 / $3.75 | ~2.7× today's cost now, ~5× from December. Analysis is not latency-sensitive: **use Flex inference** ($1/$5 now, $2/$10 later), which brings it back to about today's cost |
| Tier / limits | Not on the free tier or the AI Pro plan. Spend limit per 10 minutes: Tier 1 $10, Tier 2 $50, Tier 3 $200. Per-model RPM/TPM shown only in your AI Studio account | VW5 ran 42 clips at once; on Tier 1 a 10-minute $10 ceiling could throttle a batch. Worker concurrency becomes a run-level setting (default 4); the operator checks the tier at `/vw start` |

Static tokens for reference: ~100 tokens per second of video at low media resolution, ~300 at high. A 2-minute clip ≈ 12k–36k input tokens.

## 6. Executor plugin (`vw`)

Installed read-only in the operator's Claude Code profile. One slash command with sub-commands:

```
/vw start        preflight (4 checks) → asks the §2 questions → POST /runs → creates runs/<code>/{in,out,work,logs,manifest.json}
/vw next         GET next → runs the matching stage script → shows one sentence to the operator
/vw back <stage> /vw adopt <version>   /vw pull <code>   /vw close
```

Stage scripts (`scripts/stage_<name>.py`): read inputs from `in/` and the ledger, fetch the procedure for the pinned version in memory, do the work (the model is called by the script for creative text through the server's prompt, or the script asks the chat model via Claude Code for text only), write files to `out/`, call `/propose` or `/output`. Scripts never shell out to cloud CLIs or touch the repo.

Two hooks:
- `PreToolUse` Bash: allow only `python <plugin>/scripts/*.py …`; deny everything else.
- `PreToolUse` Edit/Write: allow only paths under `runs/<active code>/`.

Operator profile: separate `CLAUDE.md` with five lines (no reports unless asked; no debugging; file a defect and stop; approvals happen in the browser; one run at a time). Separate memory directory. Your global rules file is not loaded in this profile.

Workspace manifest per file: `{path, stage, action: retain|upload|delete, sha256, uploaded_at}`. `/vw close` refuses while any `upload` file lacks a server receipt, then deletes `work/` and `logs/` (logs uploaded first only if the operator said so at start).

## 7. Web UI (server-rendered HTML from FastAPI, 5 pages)

login · my runs · run page (stage list, latest output per stage, Download) · defects (admin) · close/delete files (admin). No approve button. Polling only on the run page while a job is pending, every 10 s, stops otherwise.

## 8. Builder workflow

- Repo `videowizard-v2`: `server/`, `plugin/`, `web/`, `supabase/`, `design/`.
- Releases: `server vN`, `plugin vX.Y`; the server stores `plugin_min_version`; `/vw start` compares and prints the install command if behind.
- Defects: builder reads `defects`, reproduces against a copied run in a local database, fixes, releases, marks fixed. No live-data SQL.
- Builder profile has no production keys; local `.env` points at a local Supabase.

## 9. Build order (each slice: requirement list → tests → implement). Re-cut 14 Oct: slices merged at the owner's request.

1. **Core** (done 14 Oct): tables, `runs`, `next`, `output` with chat acceptance, view/revise, attempts + 409, idempotent `request_id`, v1 login ported.
2. **Plugin + web UI** (was 2+3): browser connect flow (v1 ported), server-rendered pages (login, connect approve, my runs, run view, defects), `/vw` command, `vw.py` CLI, two hooks, operator `CLAUDE.md`, workspace manifest, `claim`/`pull`/`close`.
3. **Text stages + voice + media** (was 4+5): intake → brief → script first (end-to-end checkpoint shown to the owner), then voice (ElevenLabs port) and media upload via signed URLs.
4. **Analysis** (Gemini 4 Argon) and **planning** (Gemini): jobs table + one worker per provider family.
5. **Visuals**: references, OpenAI GPT Image 2.5, local assets, video takes.
6. **Edit / first_cut / assembly / delivery** on the Mac via `/vw pull`.
7. **Defects** admin workflow (table exists since slice 1; builder process).
8. Optional: Agent SDK operator app.

Web UI decision (14 Oct): pages are served by FastAPI as HTML templates; no Next.js.

## 10. Edge cases carried into every slice

From the proposal §6, trimmed to what is built: crash → resume from last stage output; upload without receipt blocks close; plugin version behind → refuse with install command; paid job with unknown outcome → reconcile by `request_id` before any retry; provider 4xx/5xx/429 → `NEEDS_USER_DECISION`; ambiguous chat approval → never an approval; second machine → "take over? y/n"; `/vw back` marks later outputs stale; UTC on the server, local time in chat.

## Not covered

- Migration of VW5/VW10 into v2 (export the final files by hand; the v1 database stays until you retire it).
- Any change to the creative logic of the stages (prompts and procedures are ported from v1's latest versions).
- Timelines and cost; the first slice will give a feel for pace.
- The Agent SDK app (slice 10) is designed for, not planned.
