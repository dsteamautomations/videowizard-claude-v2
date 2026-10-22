# design/82 — The small fixes from the 22 Oct pass: the record of a reference still, the ledger from tokens, the retry on a provider error, the pinned models

Status: requirements note, builder, 22 Oct 2026; SK: "recollect everything and then start the implementation" (taken as the go for these, which are L48, L49 and L52 of the findings file). Sources: `visuals_stage.record_gap`, `visuals_spend`, `visual_workers.process_image`, `process_take`, `jobs.claim`, `config.py`; OpenAI's image guide and API reference (22 Oct), Google's pricing page.

| | Change | Where |
|---|---|---|
| U1 | **A still set from a reference records.** The asset branch of `record_gap` registers the file in the uploads table as the take branch and the bindings do; the record then finds it. | `visuals_stage.record_gap` |
| U2 | **The ledger from tokens.** An image job with tokens costs `input × $8/M + output × $30/M` (every input token at the image rate; the text share is a fraction of a rupee); a job without tokens costs the flat image price; a take costs its seconds at the video price. Rupees per dollar is a setting. Defaults: image ₹4, video ₹8.9 a second (5,792 tokens a second at $17.50/M), ₹88 a dollar. `budget` and the page show the same figures. | `visuals_stage.prices`, `visuals_spend`, `config.py` |
| U3 | **A provider error is retried.** A 429 or a 5xx from OpenAI puts the image job back in the queue with a delay of 1, 2 then 4 minutes; after the third attempt it is rejected as today. `claim` honours the delay. | `visual_workers.process_image`, `jobs.claim` |
| U4 | **The models are pinned** to `gpt-image-2.5-flare-2026-09-08` and `gpt-image-2.5-sunburst-2026-09-08` (verified on the API reference, 22 Oct). | `visuals_stage.IMAGE_MODELS` |
| U5 | **A take keeps its usage.** When the provider's result carries `usage`, it is stored on the job's cost beside the seconds. | `visual_workers.process_take` |
| | Server 0.30.0 with design/80. | |

Tests first (`test_visuals_stage_pure.py`, `test_visual_workers_pure.py`): the asset branch registers the file; the spend of a job with tokens, one without and a take; a 429 goes back to the queue with the delay and the fourth attempt is rejected; the pinned ids; the usage kept. Not covered: server/tests (Docker); the live prices in rupees (SK sets them in `server/.env` if the defaults are off).
