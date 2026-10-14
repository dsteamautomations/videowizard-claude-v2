# Slice: visuals (direction, references, images via OpenAI, local assets, video takes) — requirement list for approval

Source: `_work/v1-late-stages-spec.md` §3. v1 reached 24 procedure releases here; the plan below keeps the contracts that made shots checkable and replaces the two things that never worked as designed: image generation (done by hand in the operator's ChatGPT tool, undisclosed cost) and the 23-action command surface.

Unit of work: **one shot inside a gap**. The stage completes when every gap shot has a selected take or a local asset.

## 1. What is built

| Part | Content |
|---|---|
| Base | gaps come from the latest of: the approved first cut (when the Mac slice exists) or the finalized plan's gap shots (until then). Each gap: `{shot_id, start_frame, end_frame, requirement}`. |
| Procedure content | v1 `visuals-visual-1.18.0` prompt ported verbatim as one document, then **split into four stage prompts** with the same wording: direction, references, motion, review. The plan contract (`visual_contract.Plan`: foundation/world/exclusions, elements, gaps with choices, scenes, shots, beats, landmarks) and its validator ported as is. |
| Direction | `vw stage visuals prepare` → the model writes `out/visual-plan.json` → `vw visuals check` (tiling of each gap by shots, beats chain states, landmarks named, held subjects unchanged, continuity notes) → the operator selects a choice per gap and accepts in chat (`vw visuals accept --gaps … --quote`). `retire` = slice-1 `revise` on the stage. `gap_digest` scoping kept so unrelated edits don't invalidate accepted gaps. |
| Reference library (per run) | kinds `frame` (exact-PTS still from a clip, server worker, unpaid), `supplied` (operator file), `web` (operator-supplied bytes + URL), and **generated**: `isolated` / `sheet` / `keyframe` made by the server through **OpenAI GPT Image 2.5** (`vw visuals image --element … --prompt … [--parents ref,ref] [--edit]`), paid, informed. Server stores original + normalized PNG, the prompt, model, parents' hashes, cost; status `candidate` → `approved` by the operator's verbatim yes on the exact hash. |
| Bind | per shot: every element covered by 1–20 approved references; subject selectors kept (element → reference → text). Editable-text graphics dropped (matrix F-35). |
| Preparation packet | `vw visuals packet --shot` = foundation + scene + shot + approved references (download links) + fixed image/video instructions + chosen generator. The model composes the keyframe request from it (through `vw visuals image`, not by hand). |
| Video takes | `vw visuals generator --shot --provider --model` (catalog: Google Omni via the Interactions API as default; Higgsfield Kling/Seedance if `VW2_HF_API_KEY` is set). `vw visuals prepare-take --shot --start-image --end-image --motion "…" --duration N --subject element=text …` → immutable request (motion subject contract: reconciliation keys must equal the shot's subjects). `vw visuals take --shot` submits **one paid job** (informed); worker submits once with an idempotency key, polls with backoff (30 s → 5 min, no event rows), downloads the MP4, ffprobe evidence, `timing_matches_placement`. Durations are integers in seconds requested, exact placement frames kept separately; assembly trims. |
| Review / select | `vw visuals fetch --job` → operator watches → `vw visuals review --job --decision accepted|rejected --notes` → `vw visuals select --shot --job`. One selected take per shot; staleness when plan/refs/preparation change. |
| Local assets | `vw visuals asset --shot --file movie.mp4|still.png` (kinds movie/still only): probed, hashed, uploaded through the existing signed-URL + receipt path (one PUT, no chunk protocol), recorded as the shot's output. |
| Stage output per shot | files: selected take MP4 (or asset) + keyframes used; summary: gap, placement frames, generator/model, duration evidence, cost of images + takes. |

## 2. Unstated requirements in scope
1. Image generation parameters recorded on the reference row: model, size, quality, prompt, parents, response id; the PNG hash is what the operator approves.
2. OpenAI calls run in the worker with the server key; the plugin never holds it. Cost from the response usage.
3. One active video job per shot; a second `take` while one is open → 409 `JOB_OPEN`.
4. A take whose decoded duration differs from the placement by more than one frame is still `ready` but flagged; the review step must carry `timing_notes` (v1 rule).
5. Reference approval and take selection are the operator's yes in chat, stored verbatim (no browser button).
6. Retained on close: approved references, selected takes, local assets, the visual plan versions. Rejected takes and candidate references are deleted on close.
7. Model: `gpt-image-2.5` endpoint and parameters confirmed against OpenAI docs at build; if the account lacks the model, the server reports `MODEL_UNAVAILABLE` and the operator can fall back to `supplied` references.

## 3. Edge cases (tests; providers faked)
| # | Case | Expected |
|---|---|---|
| V1 | visual plan whose shots do not tile a gap | refused with frames missing |
| V2 | beats whose end state does not match the next beat's start | refused naming the beat |
| V3 | accept gap A; edit the foundation text only | gap A stays accepted (digest unchanged) |
| V4 | accept gap A; change A's scene | A becomes unaccepted; B untouched |
| V5 | `image` generate (faked OpenAI) | candidate reference with prompt, model, hash, cost; `approve` with exact hash → approved |
| V6 | `image --edit` with two approved parents | parents' hashes recorded; new candidate |
| V7 | approve with a wrong hash | 409 |
| V8 | bind a shot with an element lacking references | refused naming the element |
| V9 | prepare-take with a subject key not in the shot | refused (motion subject contract) |
| V10 | take submitted; worker killed before response | `submission_unknown`; recover reads the receipt; no second submit |
| V11 | provider returns a 5.0 s take for a 4.2 s placement | ready, `timing_matches_placement=false`; review without `timing_notes` refused |
| V12 | second `take` on the same shot while one is open | 409 JOB_OPEN |
| V13 | select a take, then change the shot's preparation | selection stale; `next` lists the shot open again |
| V14 | local asset still 1920×1080 for a 16:9 gap | recorded; summary has placement and crop |
| V15 | all 3 gap shots selected | stage complete; `next` = assembly |
| V16 | frame reference at t=12.48 s | PNG from the exact PTS ≥ t; sha recorded |
| V17 | web reference without `selection_reply` | refused |
| V18 | OpenAI model unavailable (faked 404) | `MODEL_UNAVAILABLE`; operator told; supplied references still work |

## 4. v1 failure modes → v2 mechanism
| v1 | v2 |
|---|---|
| Images generated in the operator's own ChatGPT tool, cost unknown, hashes self-reported | server-side OpenAI call, hash computed by the server, cost recorded |
| 23-action `POST /visuals` enum, 24 prompt releases | one command per decision; prompt split into four stage prompts with frozen schemas; version pinned per run |
| `"21/5"` duration string crashed the worker; Omni ignores fractional seconds | integer seconds requested, exact placement frames stored separately; assembly trims |
| 339 reconcile events + 162 worker events per run in the DB | poll with backoff, one row update per state change |
| 38-minute takes from storage-pending loops | storage retry capped (3) → `NEEDS_USER_DECISION` |
| 4 MiB chunk upload protocols (local assets, movies, first cut) | one signed PUT + receipt |
| references shared across runs by client | per run (matrix F-16 dropped); re-upload to reuse |

## 5. Not in this slice
Assembly, Resolve, final delivery (next slice with the Mac stages). Editable graphics, timing overlays (dropped). Higgsfield is optional and untested unless you supply the key.

## 6. From you
- `VW2_OPENAI_API_KEY` (and confirm the account has GPT Image 2.5 access).
- Google video generation: confirm the Gemini key's project has access to the Omni video model through the Interactions API (v1 default). If not, Higgsfield becomes the default and needs `VW2_HF_API_KEY`.
- Confirm that references are per run, not shared across a client's runs.
