# 34 — Where VideoWizard can run work in parallel (analysis for SK, 17 Oct 2026, revised; no changes made)

## First: how "film renders", "workers" and "analysis" map to the twelve stages
The walkthrough names stages. Two of the three items are not stages but machinery underneath them.

| Item | What it is | Which stages it belongs to |
|---|---|---|
| **Analysis** | Stage 6 | Stage 6 only |
| **Film renders** | A background job that builds a film from the plan. Three stages each trigger one: the **review film** in stage 7 (options), the **master film** in stage 8 (master), the **assembly film** in stage 11 (assembly). The three films are not sub-steps of one process; they are one film per stage, made the same way. | 7, 8, 11 |
| **Workers** | Five background processes on the live VM. Every job that is not a chat reply runs on one of them: the narration (stage 4), clip analysis (6), the three film renders (7, 8, 11), reference images and video takes (10). Each worker takes one job at a time, from any stage. | 4, 6, 7, 8, 10, 11 |

So a change to "film renders" touches one piece of code used by three stages, and a change to "workers" touches every background stage at once. That is why each needs its own safe approach.

## What already runs in parallel
| Where | Today | Limited by |
|---|---|---|
| Media upload (stage 5) | 3 clips at a time | The operator's upload speed |
| Analysis (stage 6) | 5 clips at a time | Gemini's rate limits for the key and plan; 5 workers |
| Images and takes (stage 10) | Up to 5 jobs at a time, one per free worker | OpenAI and video-generator limits; free workers |

## The three candidates, re-examined

### 1. Film renders (stages 7, 8, 11)
**Today:** inside one worker, each shot is cut and encoded one after another, then joined; then the narration and natural sound are mixed, the film is muxed and its loudness measured. The review film is then re-encoded as a 720p copy.

**Rethinking, with a finding that changes the plan:** the live VM has 4 virtual CPUs. The encoder already uses several CPU cores for one shot. Encoding four shots at once on four cores gains little; it mostly shares the same cores. On a larger machine, or on the PC, it would gain more. So "render shots in parallel" is not a safe first move on the VM.

What is unknown is **where render time actually goes**. VW-2's 32-minute assembly render on the PC included downloading 46 clips and 27 takes over a slow line; on the VM those downloads are fast. The time may be mostly encoding, or mostly the loudness measurement and the 720p copy. Nobody has measured it.

**Safe approach, in order:**
1. **Measure first.** One render on the VM with timings per phase (download, cut shots, mix, mux, loudness, 720p copy). Half a day, no code change to the film itself.
2. **Then the cheapest lever that measurement points to.** Likely candidates: skip the 720p copy for the master and assembly films (already so), a faster encoder preset for review films only (the review film is for choosing, not delivery), and parallel shots only if encode time is small per shot and cores are idle.
3. **If parallel shots are still wanted:** a pool of 2–4 shot jobs, duplicates removed first (the same shot used twice must be cut once), the join order kept exactly, and a test that the frame count and durations match the serial render. Output bytes will differ slightly between runs; that is normal for this encoder and must not be a test.
4. **A note for safety:** a render job holds a 20-minute lease and never renews it. Nothing re-claims an expired render today, so a long render is harmless. If workers are ever changed to re-claim expired jobs, renders must renew their lease first, or a 30-minute render would be started twice.

### 2. Workers (stages 4, 6, 7, 8, 10, 11)
**Today:** the five workers are identical. Each loop takes, in turn, a voice job, then an analysis job, then an image or take job, then a render job. A worker busy with a 20-minute render cannot take a 30-second image job meanwhile. In VW-2's visuals stage that showed as images waiting while renders ran.

**Rethinking:** reserving workers by kind is simple and safe: each worker process gets a list of the job families it may take. For example 3 workers for analysis, images and takes; 2 for renders and voice. The database already hands out jobs one at a time, so no two workers can take the same job. The risk is only mis-sizing: too few render workers and films queue. A setting, not code, decides the split, and it can change with a restart.

**Safe approach:** one setting on the VM naming each worker's families; a test that a worker never takes a family outside its list; deploy with a worker restart at a quiet moment.

### 3. Analysis (stage 6)
**Today:** at most 5 clips analysed at once across all runs, a setting on the VM. Each analysis is a long Gemini call (minutes per clip) with retries on capacity errors already built in.

**Rethinking:** raising 5 to 8 or 10 is one setting and no code. The only question is Gemini's side: requests per minute, concurrent requests and tokens per minute for this key and plan. If the cap is set above what Gemini allows, clips fail with capacity errors and retry, which is slower than running 5 cleanly. I will not quote Gemini's numbers from memory.

**Safe approach, as SK decided:** check Gemini's official documentation for the current limits of this plan, or run a small test with about 10 ten-second videos at the higher cap and count capacity errors. Only then change the setting. No test starts until SK says so.

### 4. Options planning (stage 7)
Stays serial. The rules are film-wide (each clip used once, numbering in film order, continuity between neighbouring scenes); SK agreed.

## Limits in the Claude application (operator chat)
- One chat is one assistant; within a turn it can issue several `vw` commands and run commands in the background, so queueing 10 image or take jobs back to back is already possible.
- Parallel sub-assistants are possible but each re-reads the large packages (the options package is about 200,000 tokens), each counts against the plan's usage allowance, and each inherits the workspace guard (only `vw`). Usage allowance and context size are the real ceilings, not a count of parallel tasks.
- Conclusion unchanged: parallelism belongs in the server and the providers, not in splitting the assistant's thinking.

## Quantum of change and time (estimates)
| # | Change | Files | Time | Gain |
|---|---|---|---|---|
| P0 | Measure where render time goes on the VM (timings per phase in the render record) | 1 edited (render job), 1 test | ~½ day | Decides P1 |
| P1 | Render shots in parallel, 2–4 at a time, duplicates cut once, order kept | 1 edited (render), 1 test | ~½ day | Small on the 4-core VM; real on a bigger machine. Do only if P0 says so. |
| P1b | Faster encoder preset for review films only | 1 line, 1 test | ~1 h | Likely the better lever for the 10-minute review film |
| P2 | Workers reserved by family (a setting per worker) | 2 edited (worker, claiming), 1 setting, 1 test | ~½ day | Quick image and take jobs stop waiting behind renders |
| P3 | Analysis 5 → 8–10, after the Gemini check SK decided on | 0 code; 1 setting | ~1 h plus the check | Analysis of 46 clips about 40% faster |
| P4 | Queue several takes or images with one command | 1 edited (plugin), 1 test | ~2 h | Fewer steps |
| P5 | Assembly prepare stops downloading takes (design/33 D2) | 1 edited, 1 test | ~1 h | Removes about a minute |
| **Total** | | **about 6 files edited, 5 new tests, 2 settings** | **about 2 days** | |

Deploying needs a worker restart on the live VM, done only with SK's yes (design/29).

## For VW-3's options step now
The step is mostly the assistant's own work plus one review film render. Without changes, the time-saver is on SK's side: answer scene, pause and slide questions in batches.
