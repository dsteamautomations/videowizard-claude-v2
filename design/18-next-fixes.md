# 18 — Next batch of fixes (collected, not yet built)

Items agreed with SK, to be built together with tests in the next fix batch.

| # | Stage | Fix | Why | Raised |
|---|---|---|---|---|
| 1 | options | Validator checks slate line 1's duration and shot count: `OPTION #n \| BEAT_ID (RANK) \| d.ds (N Shots)` must state the option's real length in seconds (one decimal, from its timeline frames) and its real number of events. | The sample run's line 1 read `x.xs (2 Shots)` and was accepted, because only the start of the line was checked. | 15 Oct 2026 |
