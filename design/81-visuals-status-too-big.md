# design/81 — Defect 21: `vw visuals status` is too big to read; a short answer with the job ids

Status: requirements note, builder, 22 Oct 2026, from defect 21 (VW-6, 13:56 UTC). Waits for SK's go. Sources: `vw.py` (`status`, `emit`, `readable_json`), `visuals_stage.status`.

## 1. What is wrong

`vw visuals status` prints the server's whole status: every gap with its plan and words, every reference with its checklist, every job with its checklist. On VW-6 that is over 100 KB. The assistant's shell keeps an output that long in a file outside the run folder, which it may not read, so the assistant never sees the job ids, and `vw visuals fetch --job` and `select --job` need them. `--gap` and `--shot` exist on the command but `status` ignores them. Seven paid Omni takes sit ready and cannot be fetched or selected; the run refuses every write while the defect is open.

## 2. The change

| | Change | Where |
|---|---|---|
| T1 | `status` writes the full answer to `work/visuals/status.json` with `readable_json` (one value a line, long texts in files beside it) and prints a short answer: the state, the plan digest, the round, the spend, and the **jobs as one line each** (`id`, `unit`, `provider`, `status`, the error's first 80 characters, `ready` with the file's seconds), the references as counts per element and state. `--shot S` keeps only that shot's jobs and references; `--gap G` only that gap's. The summary line is unchanged. | `vw.py` |
| T2 | `fetch --job` and `select --job` accept the shot id in place of the job id when the shot has exactly one ready take (`--job BEAT_04-S2`), so the common case needs no UUID at all. | `vw.py` |
| | Plugin 0.28.0. No server change. | `plugin.json` |

## 3. Tests first

`test_visuals_cli.py`: `status` on a large faked answer prints under 4 KB, names every job id and writes `work/visuals/status.json`; `--shot` narrows the jobs; `fetch --job <shot>` resolves to the one ready take and refuses when there are two.

## 4. Not covered

server/tests (Docker); the assistant's shell limit itself (the answer is short enough by a wide margin, which is the only defence).
