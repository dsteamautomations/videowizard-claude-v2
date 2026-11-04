# 152 — Glossary of the process words: stages, steps, substeps (4 Nov 2026)

SK, 4 Nov 2026: "i am going to revise the process steps so i need to know the exact WORD or TERM that you use. this way we dont unknowingly make a mistake."

This file lists every word the system uses for a level of the process, exactly as it is spelled in the code, the procedure (instruction version 3) and the design notes with flowcharts (design/00, 01, 124, 125, 126, visuals-flowchart). Read section 1 first: the same English word ("step", "stage", "phase") means different things in different places, and a revision that renames one copy and not the other breaks a test or a server check. Section 7 lists those clashes.

Spelling matters: the code names are in backticks exactly as stored (`first_cut` with the underscore, `picture-search` with the hyphen, `plan-join` with the hyphen). A word in plain text is what the operator reads in chat or on a page.

## 1. The levels, from the top

| Level | The word used | Where it is the exact spelling | What it names |
|---|---|---|---|
| The whole thing | **run** (code `VW-18`) | `vw2_runs`, `vw start`, `vw pull <code>`, `vw close` | one film from script to delivery; also called "the film" in chat |
| The order of work | **procedure** (version `v3`; "instruction version 3") | `server/procedures/v3.json`, `vw2_procedures`, `run.procedure_version` | the pinned list of stages a run follows; a run never changes version |
| Level 1 | **stage** | `v3.json` → `stages[].name`; `vw2_stage_outputs.stage`; `vw stage <name> prepare/preview/record`; `vw revise --stage`; `vw view --stage` | the 12 named stages of section 2 |
| Level 2 (every stage) | **step** | `v3.json` → each stage's `steps` list (numbered 1.. in the prompt); the chat tool's `stage <name> prepare | preview | record` | what the assistant does inside a stage, in order; design/125 and 126 number them `7.2`, `8.1.1` ("sub-steps") |
| Level 2 (visuals only) | **phase** | `design/visuals-flowchart.md` (1 PREPARATION … 8 REVIEW AND RECORD); design/126 "Phase 1 — Preparation", "9.1.1" | the eight blocks of the visuals stage on its flowchart |
| Level 2 (visuals instructions) | **part** | `v3.json` → the visuals stage's `parts[].name`; the files `work/visuals/part-<name>.md` and the **common part** (`prompt.md`) | how the visuals instructions are split for reading, one part per step (design/124 C2) |
| Level 3 (visuals instructions) | **section** | the numbered headings inside the parts (`1. PREPARATION` … `11. DRAWN SHOTS WITH HYPERFRAMES`); the steps say "part-later.md, sections 5 and 9" | the numbered chapters of the visuals text |
| Level 2 (visuals page) | **step** (again) | `visuals.html` → `STEPS=[['treatment','Treatment'],['plan','Plan'],['references','References'],['pictures','Pictures'],['takes','Takes'],['record','Record']]` | the six tabs on the visuals page's rail |
| Inside the reference round | **pass** (older films) / **step 1, step 2** (kept films) | `session.round.pass` = `1`, `2`, `'making'`, `'complete'`; the page and the chat say "Step 1", "Step 2" on a kept film, "pass 1", "pass 2" on an older one | the two halves of the round |
| Inside a stage that repeats | **unit** | `vw2_stage_outputs.unit`, `vw2_attempts.unit`, `vw revise --unit`, `vw analysis … --unit` | one clip at analysis; one gap or shot elsewhere; `None` for a whole-stage output |
| Inside visuals, the work | **gap** → **scene** → **shot** → **take** | `plan.gaps[]`, `scenes[]`, `shots[]` (`vw visuals accept --gaps`, `--shot S`, `vw visuals take --shot`) | a gap is a hole in the master film; its plan has scenes with shots; a shot's video is a take |
| Inside the script | **beat**, **passage**, **sentence**, **word id** | `BEAT_01 …`, `passage_ids`, `first_word_id`, `after_word_id` | the script's numbering that options, master and visuals bind to |
| Inside the brief | **chapters** (stored as `process_stages`) | `brief.production.process_stages`, `scenes[].process_stages` | the film's chapters ("Mixing the mortar"); **not** the process's stages: see section 7 |
| A try at a step | **attempt** (and its **cap**) | `vw2_attempts`, `v3.json` → `cap` per stage, `/next` "attempts used of the cap" | how many times a stage may be redone before the server stops it |
| Background work | **job** | `vw2_jobs` (`status`: `queued`, `running`, `storage_pending`, `submission_unknown`, then done or failed), `vw <stage> jobs`, `vw visuals fetch --job` | a paid or long call run by a worker |

## 2. The twelve stages (instruction version 3), in order

The exact names are the `name` field in `v3.json`; the server, the database and `vw stage <name>` use them unchanged. The second column is what chat and the design notes call the stage in words.

| # | Exact name | Called in words | Chat commands of the stage (the top-level `vw` word) | Its record (what ends it) | Its steps or substeps, as the procedure and design/125–126 number them |
|---|---|---|---|---|---|
| 0 | (before any stage) | **Start** ("Stage 0", design/126) | `vw start`, `vw clients`, `vw category <name>` | — | 0.1 the picture AI asked first; 0.2 starting the film: client and script |
| 1 | `intake` | Intake | `vw stage intake prepare / preview / record --title` | `stage intake record` | 1.1 Prepare; 1.1.1 a scanned page; 1.2 the proposal (removals, three titles); 1.3 Preview and the one question; 1.4 Record with the chosen title; then the **category** (`vw category`) |
| 2 | `brief` | Brief | `vw stage brief prepare / record`, `vw brand fetch` | `stage brief record` | 2.1 Prepare; 2.2 the five decisions; 2.3 questions and constraints; 2.4 the chapters; 2.5 production values; 2.6 the directory; 2.7 presentation and the one question; 2.8 Record; 2.9 the web rule |
| 3 | `script` | Script | `vw stage script prepare / record`, `vw web` | `stage script record` | 3.1 Prepare; 3.2 the narration against the brief; 3.3 facts and claims; 3.4 a web check of a claim; 3.5 presenting; 3.6 the decisions, the record and the beats |
| 4 | `voice` | Voice | `vw stage voice prepare / record --job`, `vw voice direct prepare / record`, `vw voice catalog / models / preview / add-library / audition / narrate / jobs / fetch / recover / resolve / tweak / history / pronounce`; the **voices page** (Browse, Try, Narrations, Final) | `stage voice record` (or "Make this the final narration" on the page) | 4.1 Prepare; 4.2 the direction (and the **test passage**); 4.3 recommending and finding voices; 4.4 **tryouts** on the page; 4.5 paid steps said, not asked; 4.6 the chat way; 4.7 the full **narration** and making it final |
| 5 | `media` | Media | `vw stage media prepare / record`, `vw shape` | `stage media record --camera-audio --copies` (the upload) | 5.1 Prepare (the clip list); 5.2 the list confirmed; the **shape** (film and AI video); 5.3 the camera-sound question; 5.4 originals or editor's copies; 5.5 Record: the upload |
| 6 | `analysis` | Analysis, "the clip study" | `vw analysis start / status / show / retry / recover / resolve / exclude / policy`, `vw library show` | none: "analysis has no acceptance step" | 6.1 before starting; 6.2 the clip study (**agentic** over 15 s, **plain** under); 6.3 waiting; 6.4 failures and automatic retries; 6.5 eligibility and crops; 6.6 moving on |
| 7 | `options` | Options, "the first cut and its review film" (module `stage2`) | `vw options prepare / coverage / scenes / check / propose / second-look / join-second-look / library / frames / inspect / render / status / show / log / fetch / record` | the first answer on the **review page** approves the options (also `vw master decide`) | 7.1 Prepare: the package for reading; 7.2 scenes and pauses; 7.3 the coverage report; 7.4 writing the first cut (**round 1** exact matches, **round 2** B-roll); 7.4.1 doubtful boundaries; 7.5 the tool's check; 7.6 the **second look**, one helper per scene; the **library round**; 7.7 the review film and page |
| 8 | `master` | Master, "the master film" (module `stage2`) | `vw master slides / decide / rule / build / render / status / fetch / record` | `master record` records the master **and** the first cut together | 8.1 answering the shots (**slides**: KEEP, REJECT, TRIM); 8.1.1 a trim turned into frames; 8.2 building the master; 8.3 rendering; 8.4 approval; 8.5 a client rule from a rejection note; 8.6 the gaps handed to the visuals stage |
| 9 | `first_cut` | the first cut | `vw first-cut record` (retired: "recorded with the master") | written by `master record` | one step: retired |
| 10 | `visuals` | Visuals | `vw visuals <what>` (section 3) and `vw motion <what>` | `vw visuals record` (per gap), then `vw next` | section 3 |
| 11 | `assembly` | Assembly, "the proof copy" (module `stage3`) | `vw delivery bundle` first (the **editor's package**), then `vw assembly prepare / choose / stabilize / build / render / status / fetch / review / record` | `assembly record` records the review and the output together | the editor's package; prepare (the **fills** table); choose (offset, trim, hold_last, accept-as-is); stabilize; build; render; the operator watches and listens; record or review (changes / rejected) |
| 12 | `delivery` | Delivery | `vw delivery bundle / status / check / download / open / confirm / zip / relink-check / resolve / final`, `vw pull <code>`, `vw close` | `delivery final`, then `close` | bundle; on the operator's computer: pull, check, download, open, confirm, zip, relink-check; back on the build machine: the five questions and final; close (**retention**) |

Retired stage names that still appear in old notes and are refused by name: `planning` (version 1's planning stage, design/35 row 2; `vw planning` answers "retired"), `edit` and `assemble` / `deliver` (design/00's slash-command sketch), `plan` as a stage (it is now a visuals step).

Commands that belong to no stage: `vw connect`, `vw whoami`, `vw next` (also `--take-over`), `vw output`, `vw view`, `vw revise`, `vw decide --decision retry|revise|defect|stop`, `vw defect`, `vw upload`, `vw log`, `vw library show|mark|unmark|remark`, `vw web`, `vw pull`, `vw close`, and the four film-record words (`vw category`, `vw shape`, `vw colours`, `vw font`; design/137 and 139).

## 3. The visuals stage, every level

### 3a. Phases (the flowchart, `design/visuals-flowchart.md`)

`1. PREPARATION` · `2. TREATMENT` · `3. DETAILED PLAN` · `4. PICTURE SEARCH` · `5. REFERENCE SHEETS AND GOLDEN PICTURES` · `6. SHOT PICTURES (start images, stills, graphic states, drawn scenes)` · `7. VIDEOS (takes)` · `8. REVIEW AND RECORD`. design/126 calls them "Phase 1", "Phase 2", "Phase 3" and numbers their substeps `9.1.1` … `9.3.x`.

### 3b. Parts (the instruction split, `v3.json` → visuals `parts[].name`, files `part-<name>.md`)

`preparation` · `treatment` · `plan` · `picture-search` · `later`, plus the **common part** (`prompt.md`), read at every step. The split is checked by `scripts/c1_split_v3.py --check`; every wording script (`scripts/dNNN_wording_v3.py`) must find its anchor sentences inside these parts.

### 3c. Sections (the numbered headings inside the parts)

| Section | Heading, exact | In part |
|---|---|---|
| 1 | `1. PREPARATION` | `preparation` |
| 2 | `2. TREATMENT` | `treatment` |
| 3 | `3. THE DETAILED PLAN` ("in three steps: foundation, elements, gaps") | `plan` |
| 4 | `4. THE PICTURE SEARCH` | `picture-search` |
| 5 | `5. GENERATED REFERENCES, SHEETS AND GOLDEN PICTURES` | `later` |
| 6 | `6. SHOT IMAGES AND VIDEO` | `later` |
| 7 | `7. CHECKS AFTER A TAKE` | `later` |
| 8 | `8. REVIEW OF A TAKE OR A SEQUENCE` | `later` |
| 9 | `9. THE LATER STEPS, IN ORDER` | `later` |
| 10 | `10. BRAND` | `later` |
| 11 | `11. DRAWN SHOTS WITH HYPERFRAMES` | `later` |

### 3d. The procedure's eight steps for visuals (`v3.json` → visuals `steps`, the chat tool's pointers)

1 Preparation (`vw visuals prepare`) · 2 Treatment (`vw visuals treatment --file`, then `--accept` / `--send-back`) · 3 The detailed plan (`plan-base.json`, helpers write `out/plan-gaps/`, `vw visuals plan-join`, `vw visuals check`, `vw visuals propose`, `vw visuals accept`) · 4 The picture search (`vw visuals elements`, `vw visuals frame --file`, `vw visuals round`, `vw visuals status --wait 900`) · 5 References made by the picture AI, reference sheets and golden pictures · 6 Shot pictures and videos (and the checks after a take, section 7) · 7 Review and record (`vw visuals record`, then `vw next`) · 8 Brand.

### 3e. The page's steps (the rail on the visuals page, `visuals.html` → `STEPS`)

| id | Label shown |
|---|---|
| `treatment` | Treatment |
| `plan` | Plan |
| `references` | References |
| `pictures` | Pictures |
| `takes` | Takes |
| `record` | Record |

### 3f. The reference round (design/79, design/121, design/151)

- **round**: one for every element at once (`vw visuals round --file out/reference-round.json`, `--verdicts`, `--picks`, `--sets`, `--undo`).
- **pass** (an older film: `pass` = `1` then `2` then `'complete'`): pass 1 verdicts `approve | search | ignore`; pass 2 the **picks** ticked on the page (`vw visuals pick`, `nothing-fits`, `round --picks`); then one **sheet** per element and the **golden** picture (`image --golden`, retired on kept films).
- **step 1 / step 2** (a kept film, design/151: `round.kept` = true, `session.refs` = `'kept'`): step 1 verdicts `approve | ignore`; Done queues every **set** (`pass` = `'making'`); step 2 verdicts `yes | no | correct` with `words` and the **golden tick** (`round --sets`, page act `round-sets`); then `'complete'`.
- A **set**: two to four pictures of a thing, or three of a person (full length, working pose, the face); rows `set`, `set_n`; sibling ids `<id>-2`, `<id>-3`, `<id>-4`.
- **Reference kinds** (`REF_KINDS`): `frame`, `supplied`, `web`, `isolated`, `sheet`, `keyframe`, `state`, `style`, `component`. Reference **status**: `candidate`, `generating`, `approved`, `rejected`.

### 3g. The plan's own words (`visual_contract.py`)

- Element **kind**: `person`, `object`, `place`, `graphic`, `animal`, `material`, `process`, `technique`.
- Graphic kind: `diagram`, `chart`, `map`, `title`, `text`.
- Treatment **route** (`TREATMENT_ROUTES`): `footage`, `still`, `graphic_sequence`, `video`, `drawn` (said as "footage", "still", "graphic sequence", "AI video", "drawn"; design/124 C5 "five ways to make a picture").
- A graphic sequence's **state** actions: `appear`, `build`, `move`, `highlight`, `fade`.
- Gap words on the page and in chat: a treatment line is **accepted** or **sent back** (`accepted`, `sent_back`); a plan gap is **accepted** (`vw visuals accept --gaps`); a finished gap is **recorded** (`vw visuals record`); a round or a take is **complete**.
- Shot work words: `bind` (references to a shot), `packet` (the shot's request), `generator` (provider and model per shot), `prepare-take`, `take`, `draw`, `scene` (an SVG scene), `still`, `clip`, `asset`, `sequence`, `reuse`, `spec` (drawing and material specs), `measure`, `unplace`, `review` (`--decision`), `fix`, `note`, `ask` / `answer` (the operator's questions), `not-this`, `feedback`, `footage` (camera, support, look), `font`, `budget`.
- Motion (design/130, HyperFrames): `vw motion brief / upload / check / snapshot / verdict / render / status / rule`.

## 4. The words of the flow between stages (design/125 and 126's flowchart)

These are the arrows: what each stage hands on. A revision that moves one of these moves a server check.

| From | Hands on | To |
|---|---|---|
| Intake | kept narration; removed duration lines; removed picture notes ("the team's intended picture" per scene); the chosen title | Brief, Script, Voice; Brief; Visuals treatment; the run's name |
| Brief | purpose, message, ending; tone; chapters; footage languages (may be none); speaker on camera; frame shape, where it plays; client rules, directory | Script; Voice; Analysis and Options; Analysis; Analysis and Options (the crop rule); the finished film; every later stage |
| Script | final spoken words; paragraphs as beats; claims (figures the message rests on, `claims.json`) | Voice; Options, Master, Visuals; Visuals |
| Voice | delivery direction (tags); final narration and word timings | the narration; Options, Master, Visuals (gap times) |
| Media | the clips; camera sound allowed or excluded; originals or editor's copies | Analysis; Analysis, Options, the film's sound; Assembly (relink) |
| Analysis | per clip: usable pieces, grades, best-fitting beats, people, speech, safety flags, chapter | Options; the tool's eligibility and crops |
| Options | scenes → coverage (direct / related / chapter) → first cut → the tool's check → second look → review film | Master |
| Master | slide answers → master film → the gaps | Visuals |
| Visuals | the recorded gaps (takes, stills, drawn scenes, states) | Assembly (the editor's package first) |
| Assembly | the proof copy, approved | Delivery |

## 5. The architecture words (design/00, design/01)

- **Ledger** (runs, stage outputs, approvals, files, defects) and **gatekeeper** (the state machine, version pin, attempt caps): the server. One route answers "what can this run do now": `GET /api/runs/{id}/next` (`vw next`); the **"what next" message** is its one sentence.
- **Executor plugin**: the `vw` tool; **operator**: the person in chat and on the pages; **builder**: this folder; **helper**: a sub-agent the assistant runs (`vw-plan-gaps`, `vw-scene-review`), the only two the operator guard allows.
- **Stage output** (`vw output`, `vw2_stage_outputs`, with `stale`), **revise** (`vw revise --stage`, marks later outputs stale, `vw2_revises`), **decide** (`vw decide --decision retry | revise | defect | stop` when a stage is blocked), **defect** (`vw defect`, `vw2_defects`, `open` blocks every write), **claim** / **adopt** / **take-over** (who holds a run), **close** (retention).
- The pages: `runs` (my runs), `run` (one run: stage outputs, Approve, Download, Close), `review` (the options' and master's slides), `visuals`, `voices` (and `voices2`), `defects`, `connect`, `login`.
- Workspace folders on the operator's machine: `runs/<code>/in/` (inputs), `work/` (scratch, deleted at close), `out/` (uploaded), `logs/`, `edit/` (the delivery download).

## 6. Where each word is the exact spelling (what a rename must touch)

| Word | Files that hold it as code |
|---|---|
| stage names | `server/procedures/v3.json` (`stages[].name`), every `vw2_stage_outputs.stage` row of every run (never renamed in place: a new procedure version instead), `plugin/scripts/vw.py` (the `stage` parser and the per-stage parsers), `server/app/core.py` (`stage_table`, `revise`), `server/app/library.py` |
| a stage's steps | `v3.json` → `steps` (the text the chat tool prints at `prepare`); the wording scripts `scripts/d1NN_wording_v3.py` and their tests `server/unit/test_design1NN_*_pure.py` (exact anchor sentences; a changed sentence fails the test by design) |
| visuals parts | `v3.json` → `parts[].name`; `scripts/c1_split_v3.py`; `server/app/visuals_stage.py` (`prepare` writes `part-<name>.md`); the word budget in `server/unit/test_design125_stage7_c_pure.py` |
| visuals sections | the headings inside the part texts; the steps' pointers ("part-later.md, sections 5 and 9") |
| page steps | `server/app/templates/visuals.html` (`STEPS`, `step==='…'`); `design/129` UX1 |
| chat subcommands | `plugin/scripts/vw.py` (`VISUALS_WHAT`, `VISUALS_FLAGS`, each `add_parser`); `plugin/commands/vw.md` (the operator's command text); `plugin/tests/` |
| server routes | `server/app/main.py` (`/api/runs/{run_id}/<stage>/<step>`), `server/app/web.py` (page acts: `accept`, `answer`, `approve`, `pick`, `record`, `reject`, `revise`, `round-done`, `round-picks`, `round-sets`, `round-undo`, `search`, `select`, `supply`, `treatment`, …) |
| the flow's arrows | design/125 and 126 (the flowchart at the top), `design/visuals-flowchart.md` |

## 7. Clashes: one word, several meanings (read before renaming)

1. **step**: (a) a stage's numbered step in the procedure; (b) the six tabs of the visuals page (`treatment`, `plan`, `references`, `pictures`, `takes`, `record`); (c) design/125–126's numbered substeps (`7.2`, `9.1.4`); (d) the kept round's "Step 1 / Step 2"; (e) `vw stage <name> prepare | preview | record`, where the three are called "steps" of the stage tool. Renaming any one of these in prose does not rename the others.
2. **stage**: the 12 procedure stages; but `stage2` and `stage3` are module names (options + master = `stage2`, assembly = `stage3`, from the first system's numbering) and appear in routes (`/api/runs/{id}/stage2`) and in storage (`<run>/stage2/` = the first cut's working files). They are not stages 2 and 3.
3. **process_stages** in the brief = the film's **chapters**, nothing to do with the process. Chat always says "chapters".
4. **phase**: the visuals stage's eight phases (flowchart) and also design/124's tidy-up "Phase A / B / C" and "Part A / B / C" (work plans, not process levels).
5. **part**: the five visuals instruction parts (and the common part); design/124's "Part A/B/C"; the voices page's "four steps".
6. **pass**: the older round's `pass 1 / 2`; a kept film says step 1 / step 2 but the field is still `round.pass` (`1`, `2`, `'making'`, `'complete'`). Also "pass 1 / pass 2" of the design/124 wording work.
7. **round**: the reference round (visuals); the options' "round 1 / round 2" of writing the first cut; the **library round** (`vw options library`, "stage2" in `brandlib.py`); a correction round of sets (design/151).
8. **record**: every stage's closing command (`stage X record`, `options record`, `master record`, `visuals record`, `assembly record`, `first-cut record`), also `vw voice direct record` and the page act `record`; the **decision log** is `vw log` (design/142), not a record.
9. **first cut**: the `first_cut` stage (written by `master record`) and "the first cut" the assistant writes at options 7.4 (`out/options.json`, before the review film). The master film is cut from the approved options.
10. **review**: the **review page** (`review.html`: the options' and the master's slides); `vw visuals review` (a take's decision); `vw assembly review` (changes or rejected); the **second look** (`vw options second-look`) is not a review.
11. **plan**: the visuals detailed plan (`vw visuals plan`, `plan-join`, `out/plan-base.json`) and the retired `planning` stage (version 1). "The plan" in chat is always the visuals plan.
12. **sheet**: a reference `sheet` (a generated picture of an element; on a kept film the set's rows are `sheet` rows too) and the **sheet** of design/135's guidebook table. **Slides** are the review page's cards, not sheets.
13. **direction**: the voice direction (`vw voice direct`, `out/direction.json`) and the treatment's **Direction** box (design/124 C3, `direction` in the treatment file).
14. **check**: `vw options check` (the first cut), `vw visuals check` (the plan), `vw motion check`, `vw delivery check` (Resolve and disk), the checks after a take (section 7), `scripts/c1_split_v3.py --check` (the builder's).
15. **prepare**: the first step of most stages (`stage X prepare`, `options prepare`, `visuals prepare`, `assembly prepare`, `voice direct prepare`) and `visuals prepare-take`.
16. **library**: the brand-generic library (`vw library`, design/147), the options' library round (`vw options library`), the visuals library (`/visuals/library`, design/68) and the voice library (ElevenLabs).

## Not covered

- Words inside prompts sent to the models (the analysis instruction, the direction prompt, the picture prompts): not process levels; left out.
- The older procedure versions (v1, v2) and `videowizard-beta`: retired; their words appear only in the design history.
- Page texts other than the step rail (button labels, waiting lines): not listed; they follow the words above.
