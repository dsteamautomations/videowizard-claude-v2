# 18 — Next batch of fixes (collected, not yet built)

Items agreed with SK, to be built together with tests in the next fix batch.

| # | Stage | Fix | Why | Raised |
|---|---|---|---|---|
| 1 | options | Validator checks slate line 1's duration and shot count: `OPTION #n \| BEAT_ID (RANK) \| d.ds (N Shots)` must state the option's real length in seconds (one decimal, from its timeline frames) and its real number of events. | The sample run's line 1 read `x.xs (2 Shots)` and was accepted, because only the start of the line was checked. | 15 Oct 2026 |
| 2 | media | Upload three clips at a time instead of one (thread pool in the plugin's media record; each clip keeps its own retry). | VW-2's 876 MB took ~45 min on a flaky line; a clean serial upload at ~3.5 MB/s is ~5 min, parallel ~2 min. | 15 Oct 2026 |
| 3 | analysis | Short clips go STATIC: clips of 15 s or less (or 10 s if SK prefers) are analysed in STATIC mode, longer ones stay AGENTIC (procedure setting `processing_mode: auto` with `static_up_to_seconds`). **Before switching:** a paid comparison on three of VW-2's short clips, STATIC vs their AGENTIC logs from VW-2 (sub-clips, boundaries, speaker detection), shown to SK. Applies from the next run; a running analysis keeps its frozen mode. | VW-2: AGENTIC cost ~200k–780k tool-use tokens per clip almost regardless of length (3.8 s clip: 198k); a STATIC pass on a 3 s clip used ~900 video tokens. 28 of VW-2's 46 clips are ≤ 15 s. | 15 Oct 2026 |
