# design/114 — A pool of API keys on the server, and more workers, for four operators at once

Status: requirements for SK's approval, 28 Oct 2026, against `main` at server 0.63.0. Asked by SK on 27 Oct: four operators with their own Claude accounts make eight films this week, two each; OpenAI image keys from two paid organisations and Gemini Tier 3 keys from several paid projects are available; "when one key is blocked by its quota, the other comes in".

## What is asked (restated)

The server spends the API quota for every run; the operators hold no key. Today one OpenAI key and one Gemini key serve every run, and a quota hit stalls or fails the job. Wanted: several keys per provider on the server, used in turn, so that a key that is rate-limited or out of quota is set aside for a while and the job goes on with the next one at once; and enough worker processes that four operators' pictures, checks and takes do not queue behind one another. No key ever reaches the plugin or a chat.

## What exists

- Keys: `VW2_OPENAI_API_KEY` and `VW2_GEMINI_API_KEY` in `server/.env` on the VM (`SecretStr`, read through `settings()` at every call). Eleven call sites: the image worker (`_openai`), the picture, take, figure, not-this, measure and pair checks, the analysis jobs, the Omni take provider and the generator catalogue. ElevenLabs, Higgsfield and Apify have one key each and are not in scope (low volume).
- Workers: one service `vw2-worker` that starts `VW2_WORKERS` processes (5 today); each process ticks every family (voice, analysis, images, takes, renders) and claims one job at a time with a lease and "skip locked", so the processes already share the queue safely.
- Quota handling: an image call answering 429 or 5xx goes back to the queue after 1, 2 then 4 minutes and the fourth attempt is rejected (design/82 U3); a Gemini check that fails is recorded undecided and never re-run (design/92); an analysis job classed `quota_limit` or `spending_or_billing_limit` is rejected; an Omni take on 429 is "unknown", recovered by hand.

## The change

| # | Change | Where |
|---|---|---|
| P1 | **The pool.** `VW2_OPENAI_API_KEYS` and `VW2_GEMINI_API_KEYS`, comma-separated, beside the old names (an old single key is the pool's first entry, so nothing changes until the lists are set). `keys.pick(kind)` returns the next key in turn with its index, skipping keys that are cooling; `keys.cool(kind, index, seconds)` sets one aside after a 429 or a quota answer (60 s on a rate limit, 10 minutes on a quota or billing answer, 1 hour on 401/403: a revoked key); when every key is cooling, the caller gets none and the job waits as today. Cooling is kept in each worker process's memory (each process learns a cooling key on its own first 429; no shared state, no table). | `keys.py` (new), `config.py` |
| P2 | **Images.** `_openai` takes its key from the pool; on 429 it cools that key and retries the same request on the next key at once, within the same attempt, up to the number of keys; only when every key is cooling does the request go back to the queue on the existing 1, 2, 4-minute path. 5xx keeps the existing path. The job's result records `key_index` ("openai:2"), never the key. | `visual_workers.py` |
| P3 | **Gemini.** One helper, `gemini.transport(model, …)`, wraps the transport with a pooled key; a 429 or a `RESOURCE_EXHAUSTED` answer cools the key and the call is made again on the next key at once. Every Gemini site uses it: the six checks (unchanged in what they ask; a check that fails on every key stays undecided as today), the analysis jobs (a quota answer is retried on the next key before it is classed rejected), the Omni take submission and the generator catalogue. The record carries `key_index` ("gemini:3"). | `analysis_jobs.py`, `image_check.py`, `visuals_stage.py`, `video_providers.py`, `video_generators.py` |
| P4 | **Seen.** `/api/meta` shows the pool sizes and the indexes cooling right now; the worker log says "openai key 2 cooling 60 s (429)" when it happens; `vw status` for a run shows nothing new (keys are the server's business). | `main.py`, `worker.py` |
| P5 | **Workers.** `VW2_WORKERS` raised to 8 (four operators, two jobs each in flight; the analysis cap stays as set); a setting, no code. The VM's memory is checked before (each worker is a Python process of about 150 MB). | `.env`, design/26 |

## Where the keys go, and how many

- All keys go into `/opt/vw2/app/server/.env` on the VM, by SK, as a file edit over `gcloud compute ssh` (`sudo -u vw2 nano /opt/vw2/app/server/.env`), never pasted in chat or committed; then `sudo systemctl restart vw2-server vw2-worker`. The existing `VW2_OPENAI_API_KEY` and `VW2_GEMINI_API_KEY` lines stay.
- OpenAI: both keys, one from each paid organisation (`VW2_OPENAI_API_KEYS=…,…`). Two keys from one organisation would share one limit; two organisations pool.
- Gemini: four Tier 3 keys from four projects (`VW2_GEMINI_API_KEYS=…,…,…,…`): one per two workers, with the fourth as headroom for the daily per-project quotas; more can be added any time by editing the line.

## Unstated but expected

- A deploy with the lists unset behaves exactly as today (a pool of one). The spend ledger is unchanged (prices are per image and per second, not per key). A cooling key is never a failure of the job; the operator sees only that the picture took a little longer. The checks stay tolerant and never block.
- Keys are stripped of whitespace; an empty entry is ignored; a list with no usable key gives the existing 503 "configure the key" answer.

## Edge cases and failure modes

- A key revoked mid-run (401/403): cooled for an hour, logged by index, the job goes on with the next key; all keys revoked: the existing configuration error. A key with a typo: the same path. Every key cooling at once: the image request requeues (1, 2, 4 minutes) and the check stays undecided; nothing is rejected for a cooling alone. Two worker processes hitting the same key's limit in the same second: both cool it; no harm. A 429 whose body says a daily quota: the longer cooling. The pool order is rotated per call, so one slow key does not take every call. OpenAI 5xx: the existing path, no key cooling. A Gemini call that fails for a reason other than quota (a safety block, a bad request): no cooling, the existing handling.

## Questions for SK (answer in order, or say "go with the recommendations")

1. **Cooling times.** Recommendation: 60 s on a rate limit, 10 minutes on a quota or billing answer, 1 hour on a revoked key; constants in `keys.py`, tuned if the week shows otherwise.
2. **Shared cooling.** Recommendation: in each worker process's memory, no table: a second process learns the same key in one more 429, which costs nothing.
3. **Workers.** Recommendation: 8, after checking the VM's free memory; 12 if the VM has it and the week's queue says so.
4. **Analysis jobs.** Recommendation: a quota answer is retried on the next key once before the job is rejected (today it is rejected at once).

## Tests first

- P1: `pick` goes round in turn; a cooling key is skipped; after its time it returns; every key cooling gives none; the old single key alone is a pool of one; whitespace and empty entries are dropped.
- P2: a 429 on key 1 is retried on key 2 in the same attempt with the same request; key 1 is cooling afterwards; every key cooling sends the job to the 1-minute requeue; the result carries `key_index`; a 5xx keeps the old path.
- P3: a `RESOURCE_EXHAUSTED` from Gemini on key 1 is retried on key 2 for a check, an analysis job and an Omni submission; a check that fails on every key is undecided; the record carries `key_index`.
- P4: `/api/meta` lists pool sizes and cooling indexes; the log line is written.
- P5: nothing to test in code; the memory check is on the VM before the setting changes.

## Not covered (known before the build)

- Live quota behaviour of the providers (sampled on the week's runs, not benchmarked). OpenAI's per-organisation limits are not read from the API. ElevenLabs, Higgsfield and Apify stay on one key each. server/tests (Docker).

## SK's answers (28 Oct 2026)

1. Cooling: 60 s on a rate limit, 10 minutes on a quota or billing answer, 1 hour on a revoked key; constants in `keys.py`.
2. Cooling is kept in each worker process's memory; no shared table.
3. Workers: 8, after the VM's free memory is read; 12 only if the week's queue shows waits and the memory allows.
4. An analysis job retries once on the next key before a quota answer rejects it. All four answered on 28 Oct: build P1–P5, tests first, commit and push per rule, tell SK before the deploy.

## As built: P1–P5 (28 Oct), server 0.64.0

- P1 `keys.py`: `pool(kind, settings)` reads the single key then the comma-separated list (`VW2_OPENAI_API_KEYS`, `VW2_GEMINI_API_KEYS`), stripped, without doubles; `each(kind)` hands the keys out in turn from where the last call left off, the cooling ones last (when every key is cooling, the one back soonest, so the provider itself answers); `cool(kind, index, reason)` sets a key aside for 60 s (rate), 10 minutes (quota or billing), 1 hour (revoked), in this process's memory, with a log line "gemini key 2 cooling 60 s (rate)"; `reason_of(status, category)` names the reason; `gemini(factory, model, use, settings, **kw)` makes the transport on one key, runs the call, and on a 429, a quota answer or a revoked key cools it and runs the call again on the next key, raising the last error when every key failed; `sizes()` for the meta.
- P2 `_openai`: the image request goes to the keys in turn; a 429 or a revoked key cools it and the same request goes to the next key at once, within the attempt; when every key answers a limit the last answer comes back and the job requeues as before (design/82 U3). The retained result records `key_index`.
- P3: the picture, take, drawn, figure, not-this, measure and pair checks go through `keys.gemini` (the take check's upload and read on one key, both redone on the next); a run with no key still gets "no Gemini key on the server" and an undecided check. The analysis jobs pick the next key per job, keep `key_index` on the upload receipt (a receipt made with another key is ignored and the clip uploaded again: files are per project), cool the key on a limit, quota or revocation, and (answer 4) take the one capacity retry on a quota answer too when the pool has more than one key. The Omni take provider picks the next key and cools it on a 429, 401 or 403 answer; the generator check reads the first key of the pool.
- P4 `/api/meta` carries `keys: {pools, cooling}` (sizes and indexes, never keys), the server process's own view.
- P5: `VW2_WORKERS=8` is a line in the VM's `.env`, set at the deploy after the free memory is read.
- Tests: `test_design114_pure.py` (4: the pool's parsing, the turn and the cooling, the image retry within the attempt, the Gemini retry with the index on the record). Server unit suite 604. Not covered: the analysis and Omni paths are exercised by their existing tests with one key only; the live behaviour is sampled on the week's runs.
