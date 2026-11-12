# 183 — A clip the analysis model refuses keeps its reason and does not block

12 Nov 2026. SK's requirement, from defect 48 (VW-21, the first user run on 0.94.0). Built locally with unit tests; **not committed, not deployed**: SK is collecting a set of fixes from this run first.

## What was wrong

The clip `DJI_20241219103046_0091_D00000000_00000000.mp4` (21 s) was refused by Gemini with HTTP 400 in VW-18, VW-19 and VW-21, eight times on four keys. The tool kept only "HTTP 400": the provider's own message was read by the transport and then dropped. The clip stayed "rejected", the stage could not finish, and the operator had to retry, exclude it by hand or file a defect.

## What changed

- **The reason is kept.** A rejected analysis job stores the provider's answer (`result.provider_error`; already bounded and cleaned of keys and addresses by the transport) and its error line says it: `Provider rejected the request (HTTP 400): INVALID_ARGUMENT: …`. `analysis_jobs.provider_reason`, `rejected_error`.
- **The clip is set aside by the server and the stage goes on.** A refusal that is the clip's own (HTTP 400 or 413) records the clip as excluded with the reason (`summary.set_aside`), and writes a line in the run's decision log. `analysis_jobs.set_aside_reason`, `_set_aside`, in `finalize`.
- **The operator is told the name and the reason.** `vw analysis status` lists every clip set aside, by name, with the reason, and says what the operator may do: go on, have it tried again (`vw analysis retry --unit`), or stop and file a defect when the clip matters. `vw.set_aside`.
- **A retry that passes brings the clip back**: its set-aside record gives way to the analysis.

## The cause of defect 48, and the fallback (added the same day)

Reproduced on the builder PC by Claude's script outside the application, with the app's own transport, the exact saved request and the same file (checksum). Gemini's reason: `INVALID_ARGUMENT: Request contains an invalid argument.` One setting changed per send: agentic mode off: accepted; agentic with a JSON answer but no schema: accepted; no thinking setting, no resolution setting, the file without its data track: all refused. So the clip is refused only when **agentic video mode and the answer schema are sent together**; the file is sound (AI Studio accepts it). Why this clip and not the other long ones is not known. Agentic used about 149,000 tokens, plain about 17,000.

- **A refused agentic request is sent once more in plain mode** (the mode a clip of 15 s or less gets), by the server, on a new transport (a failed transport refuses every further call). `analysis_jobs.generate`. Only for a 400 that is the clip's own; a key, quota or service fault is raised as before. The kept analysis carries `plain_fallback` in its summary.
- Only when plain mode is refused too is the clip set aside, with the second refusal's reason.
- Proven on the real clip through this code: refused in agentic mode, answered in plain mode (16,052 characters, valid JSON).

## Not set aside

- A fault of the key, the account or the service (401, 403, 404, 429, 5xx, a spending or quota limit, "API key not valid" under a 400): the existing key rotation, waits and retries apply.
- The last footage of the film: when no other clip is kept or still being analysed, the clip stays rejected and the stage stops, with the reason shown.
- Any refusal while recording the set-aside: the clip stays rejected, as before.

## Older way

A rejected clip blocking the analysis stage until the operator acts: retired for refusals that are the clip's own. Retry and exclude by hand stay.

## Tests

`server/unit/test_design183_rejected_clip_pure.py` (13), `plugin/tests/test_design183_set_aside.py` (1); one older test updated (`test_design125_pure.py`, marked). Server unit suite 1,467 passed.

## Not covered

- Why Gemini refuses this one clip in agentic mode with the schema, and not other long clips.
- The plain-mode answer of a long clip may be less detailed than an agentic one; not compared.
- The database part of the set-aside (`_set_aside`) has no unit test; its decisions are tested as plain functions. `server/tests` (Docker) not run.
- No page shows the analysed clips, so the name and reason appear in the chat and in the decision log only.
- The first cut does not repeat the list of clips set aside.
- Versions are not raised yet; that is done when the set is committed.
