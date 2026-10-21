# design/68 — The image prompt library inside the visuals stage

Status: Revathi's note of 21 Oct 2026 (bundle `videowizard-library-bundle-2026-10-21`, version `vwlib-2026-10-21-4f88379be109`, the second zip with the marketingskills licence), rewritten by the builder the same day against the code after design/65, 66 and 67, with SK's decisions of 21 Oct. Approved by SK for part A. Decided with Revathi: the chat assistant writes the prompts; the server never calls a model to write them. The proposer's own text is in the bundle's `handoff/66-image-library-in-visuals.md`; this note is what gets built.

## 1. Why

The packet a shot gets before composition carries three fixed instructions (start, end, motion, design/67) and nothing else about how to write a prompt for GPT Image 2.5, Omni, Kling or Seedance. SK's image prompt library holds that know-how: a rulebook, playbooks per kind of job, fact sheets per model, a job form and an answer form with a checklist, and a feedback record. This note puts the library in front of the assistant at every generated picture and take, without changing who writes the prompt, and makes the prompt travel with its answer form so the record can be kept.

## 2. What the bundle is

`library/` (25 files at the library's own paths; `diagram-in-states.md`, `gap-fill.md`, `higgsfield/NOTES.md` and `record-template.videowizard.yaml` are new drafts), `VW-MAP.md` (which files each visuals step opens; where VideoWizard overrides the library), `FIELD-SOURCES.md` (where each job-form field comes from in a run), `MANIFEST.json` (version, fingerprint, sha256 per file; the manifest covers the library and the two maps, not the README, the handoff texts or the licences), `licences/` (every third-party source, the smixs NOTICE, the marketingskills MIT text, `SOURCES.md`). Checked on 21 Oct: all 27 listed files present with their hashes.

## 3. Where the proposer's note and the code differ, and what this note does about it

| | In the note | In the code today | Here |
|---|---|---|---|
| a | design/66 | design/66 is the video-segments change, 67 the packet pair | This is design/68 |
| b | "the two fixed instruction sentences stay" | three since design/67 | the library block sits beside the three |
| c | `prepare-take --end` when the final state matters | the end image is required; generated from the start as its parent; the server sends the start's references behind it | VW-MAP's end-image row is read with that: the end keyframe is always an edit with identity; `mode` is decided by the server |
| d | the ₹1,000 cap; "the page's buttons unchanged"; `spend_cap_usd` at SK's rate | ₹5,000, the setting alone (L26 queued removes the raise from both front ends); no exchange rate exists | the job form carries no spend field; the server's cap check decides |
| e | the feedback record on approve, reject or regenerate | a picture has no reject verdict, only a take | part B adds a reject-with-words on a reference, both front ends |
| f | the handoff when the stage is recorded | gaps are recorded one at a time | part B builds it when the last gap is recorded, and on demand |
| g | the guard protects the library files | the guard knows the sentinel `VW-PROCEDURE`, not folders | the plugin writes each library file with the sentinel as its first line |
| h | read the library for every picture and take | 60 images and 18 takes on VW-6 | the files are written once per step at prepare and read once per step; the packet names the step's files, it does not repeat their text |
| i | `mandatory_text` from the client card | the card has no such field | left empty; `industry` and the brand fields come from the card |

## 4. Part A, built now (the child waits at the references step of VW-6)

| | Change | Where |
|---|---|---|
| L1 | `library/`, `licences/`, `VW-MAP.md`, `FIELD-SOURCES.md`, `MANIFEST.json` copied to `server/library/vwlib-2026-10-21-4f88379be109/`. A refresh adds a folder beside it; old folders stay while a run uses them. The server never writes there. | repo |
| L2 | The visuals session records `library_version` at `prepare` and keeps it. A session from before this release reads the latest version. | `visuals_stage.prepare`, `library_version_of` |
| L3 | A small `library.py`: the versions on disk, `latest`, the manifest check, the step map coded from VW-MAP (`reference`, `frame`, `still-scene`, `still-diagram`, `state`, `start`, `end`, `take`, plus the always-open files and the compliance checklist), the job form filled from the run per FIELD-SOURCES with what the server has, and the answer lint. `GET /api/runs/{id}/visuals/library` returns the session's version with every step's task, playbook, file paths and texts, VW-MAP and FIELD-SOURCES. The packet gains a `library` block: version, the shot's steps, their tasks, the file paths, the model sheet for the shot's generator, and the filled job form. The three instructions stay. | `library.py`, `visuals_stage.packet`, `main.py` |
| L4 | `vw visuals prepare` fetches the library and writes `work/visuals/library/always/`, `work/visuals/library/<step>/`, `VW-MAP.md`, `FIELD-SOURCES.md` and `steps.json`, one file per library file, each beginning with the sentinel line. The packet file `work/packet-<shot>.json` carries the job form as today it carries the rest. | `vw.py` |
| L5 | `vw visuals image` and `vw visuals prepare-take` take `--answer out/answers/<id>.json` (in `image --file` lists, an `answer` path per item). The server lints what can be checked mechanically: `status` is `ready`; `prompt` equals the prompt sent; `checklist` has at least one `must` line; every `exact_text` string appears in the prompt. The answer is stored with the reference or the take request. Without `--answer` the call works as today. | `library.check_answer`, `generate_image`, `prepare_take`, `main.py`, `vw.py` |
| L8 | One paragraph in the visuals prompt (the library per step, the answer form and `--answer`, VW-MAP's overrides, the `suggestion` line), paid for by trimming; the reference and per-shot steps name the folder and the flag. `vw.md` names `--answer`. | `v2.json`, `vw.md` |
| | Server 0.25.0, plugin 0.23.0. | |

The job form, as the server fills it: `job_id` `<run code>-<shot>-<n>`, `client_code`, `requested_by` agent, `round`, `playbook`, `task`, `mode`, `industry` (card), `placement`/`video_aspect` (the brief's frame), `video_seconds` (video shots), `request` (the words under the shot, the shot's purpose), `purpose` (the gap's intent, the treatment fit), `audience` (brief), `style_direction` (foundation and shot appearance), `copy` (the shot's information progression and the states' words; the assistant extracts the exact strings), `text_mode` rendered, `logo` none, `images` (the bound references with tags), `images[].keep` (the element's requirements), `brand_preamble` (from the card's brand fields), `hard_constraints` (the foundation's exclusions and the brief's effective rules), `avoid` (rejected takes' notes for the shot), `model` fixed, `finish` final, `variants` 1, `checked_by` person, `trial` false. No consent ids, no spend field, no mandatory text.

## 5. Part B, after the first pass, with L24–L26

L6 the checklist beside each picture and take on the page and in `fetch`; L7 the feedback record written on approve, on a new reject-with-words for a reference, and on a take's select or reject, with `library_version` and the answer's `suggestion`, served as YAML; L9 the library handoff (the run's records plus `LIBRARY-HANDOFF.md`: version, verdict counts per task and model, repeated failures with the fix that worked, suggestions grouped by file), built when the last gap is recorded and on demand, linked by `record` and on the page; it reports only.

## 6. Open decisions for SK, carried

Real people (no consent id exists; a real face from a frame is a look reference only and is never edited); Higgsfield as a route in the library; prices in INR behind the meter.

## 7. Tests first (part A)

- `test_library.py`: `latest()` names the folder; an unknown version is refused; every file the step map names exists in the version; the manifest check passes on the copied folder and reports a changed file; the job form from a fake run fills every field above; an unknown step is refused; `check_answer` passes a ready answer whose prompt and exact text match, refuses a status other than ready, a prompt that differs, a checklist without a must line, and a missing exact string.
- `test_visuals_stage_pure.py`: the packet carries the library block (version, steps start/end/take for a video shot, the generator's sheet, the job form) and the three instructions; `generate_image` and `prepare_take` store a valid answer, refuse a prompt mismatch, and work without one; `library_version_of` reads the session or the latest.
- `plugin/tests`: prepare writes the library files per step with the sentinel first line; `image --answer` and `prepare-take --answer` post the answer from the file.
- The prompt within 3,500 words; `v2.json` parses; plugin compile; server compile.

## 8. Not covered

server/tests (Docker). The playbooks are version 0.1 and the four new guides are drafts; VW-6 is their first use. Whether the assistant's prompts improve with the library open is the first pass's judgement. The answer form's other lint rules (banned phrases, model names inside the prompt, picture roles) stay the assistant's own.

## 9. Order

Tests → change → compile checks → show SK the diff and the prompt paragraph → commit and push → tell SK → deploy the server (0.25.0, the workers restart) and the plugin (0.23.0, SK restarts the operator's Claude Code) → design/35 row 60, design/49 line.
