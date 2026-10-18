# 43 — Stage 7 (options) improvements: requirements (approved by SK 18 Oct 2026, implemented the same day)

Source: the stage 7 review run with the stage review prompt on 18 Oct 2026 and SK's decisions on its 8 findings. Measured on VW-3 (the only run in the live database): the third review film took 16 min 14 s to render, of which 11 min was encoding 110 pieces at 1080p and 3.6 min re-encoding the film to the 720p copy the operator watches; the package the assistant reads is 552 KB, 20,854 lines on disk; the slides read "Scene 1: BEAT_01"; the master record wrote five identical rejection notes into client C-086's rules. Nothing here makes a paid call. VW-3 is past options; every change is backward compatible with the 0.8.0 plugin and the 0.9.0 server. Finding 7.5 is a master-stage change built in this batch by SK's decision.

## Decisions carried from the review
- Review films render at 1280×720 with a fast preset from the first piece; no copy pass, no loudness pass; the master keeps 1080p (7.1).
- `vw options status --wait N` polls inside the tool and says about how long is left (7.2).
- The scene proposal is a fixed step: titles, chapters and pauses, one yes; beats never show their ids (7.3).
- The assistant's reading copy of the package leaves out entities, SFX cues and editorial ideas and writes tables one row per line; the stored package is unchanged (7.4).
- Rejection notes stay on the run; a client rule is stored only through the confirmed rule command; the five C-086 rows are deleted (7.5).
- Check and propose answers group flags by rule; the prompt names the flags to act on (7.6).
- A film's render work folder is deleted once its upload is verified (7.7).
- Render and record refuse a version whose package changed (7.8).

## A. Server changes (`server/`)

| # | What changes | Why | Where |
|---|---|---|---|
| 7.1 | `render_film(kind='review', …)` builds its `Renderer` on a 1280×720 timeline (fps unchanged) and `video_args` use `-preset veryfast -crf 23` for review films; `review_proxy` and the final `loudness` pass are skipped for review films (`record['mix']` is `None`, `record['codec']` says "1280x720 review"). Master and assembly films are untouched. Crops are fractions of the frame, labels and slates size from the timeline height, so nothing else changes. | The operator only ever watches a 720p copy; today it costs a 1080p render plus a full re-encode. | `stage2/render.py` |
| 7.2 | `render()` stores the plan's frame count on the session's render entry (`frames`: slates 75 each, cards and events their timeline frames). `render_jobs.process` times the render and writes `elapsed_s` and `frames_per_s` into the result record. `status()` adds `render_rate_fps`: `frames_per_s` of the most recent ready render job on the server (any run; `null` when none). | The tool's estimate needs the frames and a measured speed. | `stage2/stage.py` `render`, `status`; `stage2/render_jobs.py` |
| 7.3 | `paragraph_scenes` titles each default beat by the first six words of its paragraph ("As the demand for affordable housing…"), so `prepare` without approved scenes never shows a beat id. `propose` refuses with `NOT_ALLOWED` "propose the scenes first (`vw options scenes`)" when the session has no approved scenes. `set_scenes` is unchanged: a scene's `process_stages` holds the chapter it covers, validated against the brief's chapters (an empty list stays allowed). | Readable slides; the chapter mapping from stage 2 drives the fits (design/19 A5). | `stage2/narration.py`, `stage2/stage.py` `propose` |
| 7.5 | `record_master` no longer inserts rejection notes into `vw2_client_rules`; it inserts only the session's `extra_rules`. `add_rule` requires `quote` (the operator's confirmation) and stores it with the rule (`{'rule', 'quote', 'by'}`); `source_run` as today. `learned_rules_added` counts only those. | Client memory holds what the client wants, not answers to slides. | `stage2/stage.py` `add_rule`, `record_master`; `main.py` `RuleBody.quote` |
| 7.6 | `group_flags(flags)` → `[{'rule': 'R1', 'count': 46, 'examples': [first three]}]`, rule taken from the text after the tag (`R1`, `R10`, `B1`, `G5`, `rule 11`, `E1`, …). `check` answers `flags_by_rule` and the total; `propose` answers the same and stores the full list on the version as today. | 121 lines per check become a dozen. | `stage2/validator.py` (`group_flags`), `stage2/stage.py` `check`, `propose` |
| 7.7 | `render_jobs.process` removes the film's work folder (`CACHE / <out_key stem>`) after the upload is verified and the normalised segments are uploaded; `sources` stays. A failed render keeps its folder (the rerun reuses the pieces, as the comment says). | 6 GB per run left behind for good. | `stage2/render_jobs.py` |
| 7.8 | `current()` also returns the version's `package_digest` (from the version file); `render(kind='review')` and `record_options` refuse with `NOT_ALLOWED` "the package changed since version N; `vw options check` and `propose` again" when it differs from `session['package']['digest']`. | A clear refusal instead of a failed render after a re-solved clip. | `stage2/stage.py` `current`, `render`, `record_options` |
| — | `SERVER_VERSION` 0.9.0 → 0.10.0. | | `config.py` |

Data: with SK's yes already given (7.5), the five C-086 rows whose rule starts with "Rejected option #" and `source_run = 'VW-3'` are deleted from `vw2_client_rules` after the deploy; logged in design/35.

## B. Plugin changes (`plugin/`)

| # | What changes | Why | Where |
|---|---|---|---|
| 7.2 | `vw options status --wait N` (seconds, default 0): polls `GET /api/runs/{id}/stage2` every 15 s until the review render is `ready` or `failed` (or there is no render), or N seconds pass. Line: "review film rendering, about M min left" with M = max(0, frames ÷ rate − waited) ÷ 60, rate = `render_rate_fps` from the answer or 20 when absent; "review film ready: `vw options fetch`"; "review film failed: <error>"; on expiry "still rendering; run again with --wait". Exit 0 in every case. The same loop takes `--film master` for stage 8 (not wired in the steps yet). | One turn per render instead of dozens. | `vw.py` `cmd_options`, parser (`--wait`) |
| 7.4 | `_download` writes `work/options-package.json` through a new `reading_copy(path, data)`: drops `entities`, and `sfx_cues` and `editorial_ideas` from every sub-clip row; writes `sub_clips`, `narration.words` and `narration.sentences` one row per line (compact JSON per row); everything else as `readable_json` today (long texts still move to `.md` files beside it). The downloaded bytes from the server are not changed; `vw options log --unit` still fetches a full log with everything. | About 40 % fewer tokens and about 2,500 lines instead of 20,854. | `vw.py` `reading_copy`, `_download` |
| 7.5 | `vw master rule --add "<line>" --quote "<their yes>"`; refused without the quote. | The rule is the operator's. | `vw.py` `cmd_master`, parser (`--quote` exists) |
| — | `plugin.json` 0.8.0 → 0.9.0. | | `.claude-plugin/plugin.json` |

## C. Procedure text (`server/procedures/v2.json`)
Options `steps`:
- Step 1 unchanged except the last words: "… and prints the direction prompt. The sub-clip table and the words are one row per line."
- Step 2 becomes: "Scenes and pauses (design/19), always: propose the scenes in one message, default one per paragraph, each starting at a sentence start, with a short title, the chapter it covers (from the brief's chapters; none when the brief has none) and any pauses (after a sentence-ending word, total silence wanted, at most 4 s, with a reason). Write out/scenes.json: `scenes` = [{first_word_id, title, process_stages: [chapter]}], `pauses` = [{after_word_id, seconds, reason}]. Present the scenes with their lengths and every pause with its reason; on the operator's yes `vw options scenes --file out/scenes.json --quote "…"`. Nothing is re-recorded and nothing paid runs. `vw options propose` is refused until the scenes are approved."
- Step 4 adds: "`check` and `propose` return the flags grouped by rule; act on R5 (hold), B1 and B2 (word timing), rule 11 (a long real shot) and E1 (a short blank); R1, R10, R8 and R4 only inform when shots are cut to the meaning across clips."
- Step 5: "`vw options render`, then `vw options status --wait 900` and report its line; repeat until the film is ready; `vw options fetch` and let the operator watch out/review.mp4. Then `vw options record --quote "<their yes>"`."
Options prompt, EDITOR RULES paragraph, one sentence added: "Flags come grouped by rule: act on R5, B1, B2, rule 11 and E1; R1, R10, R8 and R4 inform."
Master `steps`, step 2 adds: "Rejection notes stay with this run. When a note states a preference that should hold for this client's future films, propose one line and, on the operator's yes, `vw master rule --add "<line>" --quote "<their yes>"`."
vw.md's options and master paragraphs follow the same wording.

## D. Unstated but expected
- A 0.8.0 plugin against the 0.10.0 server: `propose` is refused until scenes are approved; the old steps already describe the scenes command, so the assistant can comply. The order server-then-plugin keeps that window to minutes.
- A run with scenes approved before this change (none in flight) keeps them; `prepare` does not reset approved scenes.
- The review film's picture is the same resolution the operator watches today; its file is smaller than today's copy at the same crf is not promised (crf 23 veryfast at 720p against crf 28 fast today), only the time.
- The rate estimate is rough: the first review after the deploy uses the last 1080p render's rate (slower than the new speed) until one 720p render has run; the line says "about".
- The reading copy is for the assistant only; the server, master build and assembly read the stored package, which still carries the SFX cues.
- `--wait` never re-renders or records; it reads.
- Deleting the work folder loses nothing: the film is verified in storage before the folder goes.

## E. Edge cases
| Case | Expected |
|---|---|
| review render of VW-3's v3 plan after 7.1 | the same 12,642-frame film at 1280×720; expected about 4–5 min (measured on the next live render, not by a test) |
| `vw options status --wait 900`, frames 12,642, rate 40 fps, 60 s waited | "about 4 min left"; returns when ready |
| `--wait` and the render fails | returns at once with the error line, exit 0 |
| `--wait` with no `render_rate_fps` in the answer (old server) | rate 20 |
| `prepare` on a nine-paragraph script, no scenes yet | beats titled "As the demand for affordable housing…" (first six words), `next` says propose scenes |
| `propose` before any scenes approved | 409 NOT_ALLOWED naming `vw options scenes` |
| scenes.json with a chapter not in the brief | refused as today ("process stage … is not in the brief") |
| reading copy of VW-3's package | no `entities`, no `sfx_cues` or `editorial_ideas` in any row; 118 sub-clip lines, 673 word lines, 45 sentence lines |
| `check` on VW-3's v3 | `flags_by_rule` with R1 46, R10 29, B1 20, R4 11, B2 11, R8 4 and three examples each; total 121 |
| master decide REJECT with a note, then record | no row in `vw2_client_rules`; `learned_rules_added` 0 |
| `vw master rule --add "no alternate takes" --quote "yes"` then record | one row, `learned_rules_added` 1; without `--quote` refused |
| a ready render | its work folder is gone, `sources` remains |
| a failed render | its work folder remains |
| `prepare` again after a re-solved clip, then `vw options render` | refused: "the package changed since version 3; check and propose again" |
| `prepare` again with nothing changed, then render | same digest, proceeds |

## F. Tests (written first)
Layer one, `plugin/tests/test_options_cli.py` (new): `--wait` with faked status answers (ready after two polls; failed returns at once; expiry says run again; the estimate line with and without `render_rate_fps`; no sleeping without `--wait`); `reading_copy` on a fixture package drops the three keys, keeps everything else, writes the three tables one row per line, and the fake server answer still carries them; `master rule` without `--quote` refused and with it posted; the options and master steps and vw.md carry the scenes-always wording, `--wait 900`, the flag names and the rule command.
Layer one, `server/unit/test_stage2_pure.py` (new, no database): `group_flags` on the 121-flag list shape; `paragraph_scenes` titles by first six words; `render_film` on a one-slate review plan with the Mac's ffmpeg produces 1280×720 and no copy file, and the master plan 1920×1080 (two short renders, a few seconds each).
Layer two, `server/tests` (Docker): `test_stage2.py` end-to-end: `propose` refused before scenes, accepted after; status answer carries `frames` and `render_rate_fps` after the first render; the render work folder is removed after `ready`; S16 rewritten: REJECT with a note adds no rule, `master rule --add --quote` adds one; a re-prepare with a changed analysis output then `render` → 409; `test_exact_match.py` render test asserts the review record's codec line and `mix: None`.

## G. Not covered
- `server/tests` cannot run on this Mac; compile check only until a Docker machine runs them.
- The review film's speed after 7.1 is measured on the next live render, not by a test.
- Whether the flag guidance changes what the assistant writes is seen on the next run.

## H. Deploy order
1. Server (`deploy-server.sh`, workers restart): tell SK first.
2. Plugin (`deploy-plugin.sh`); the operator restarts Claude Code.
3. Delete the five C-086 rows; design/35: a row.

## I. Estimate
Server with tests: a day. Plugin with tests: half a day. Deploys and the data fix: an hour.
