# design/130: HyperFrames motion route for drawn shots, with a fact-check loop

1 Nov 2026. Status: **plan for SK's approval. Nothing is built, committed or deployed.**
Inputs: the HyperFrames test bench (`hyperframes-test/`, three shots, 1 Nov), SK's elevation fact check on shot 2 (`hyperframes-test/shot2-vw12-BEAT_07-B1-S1/refinements.txt`), and the fact-check proposal (`.../fact-check-loop-proposal.md`).
Older way: the drawn route v2 (design/117: SVG scene, server frame stepping in Chromium, Gemini sheet check and fix passes) is **kept until the pilot film passes (phase 5)**, chosen per run. After that it is retired by refusal (section 9).

## 1. The request, restated

Replace how drawn shots are made with the route that won the test bench: Claude writes a HyperFrames composition (HTML + GSAP) for each drawn shot, the VM renders it to an MP4 of the shot's exact frame count, and a fresh checker compares the frames with the brief, universal truths and the subject's rules, redoing the shot when it fails. It must work for every operator, not just one machine. Shots are built in parallel by separate helpers, as the three test shots were.

## 2. What exists today (inventory)

All references are in `videowizard-v2/`.

**Planning (unchanged by this plan)**
- A blank becomes a drawn shot with `visual_type: drawn` (`server/app/visual_contract.py:255`).
- The plan stores `claims` (`:278`), `drawing_spec` (dimensions, relationships, view, label; `:133`, `:280`), `narration` (`:257`) and `start_frame`/`end_frame` (`:253-254`). The palette is `foundation.graphic_style.palette` (`visuals_stage.py:3737`).
- Plan checks: figures need the drawn route (`visual_contract.py:668-671`), and the spec rules (`:715-742`).

**Authoring (replaced)**
- The drawing instructions live in the server's procedure text, `server/procedures/v3.json` stage 9 part 4 ("takes the drawn route…", `:295`). The plugin's own files say nothing about drawn shots.
- The operator's Claude writes one SVG file of data, with no code. `vw visuals scene --shot S --file x.svg` uploads it (`plugin/scripts/vw.py:1761-1775`).
- On upload, `svg_scene.check` (`server/app/svg_scene.py:116-195`) enforces: allowed tags only, no script or animation, `ref:` pictures, Noto Sans or the brand font, text at least 4 % of the frame height, at most 8 words.
- Motion is a list of five actions: appear, build, move, highlight, fade (`DrawnAction`, `visual_contract.py:199-206`), timed by `at_s` or a narration word.

**Render (replaced)**
- `visuals_stage.render_drawn` (`:3703-3755`) makes a free `vw2_jobs` row with provider `drawn`.
- `visual_workers.process_drawn` (`:429-523`) hands it to `drawn.py`. Playwright Chromium sets each element's state per frame, takes a screenshot and pipes it to ffmpeg (libx264, crf 18, exact frame count, film fps).

**Checks (replaced or reused)**
- A contact sheet: one frame every 0.5 s (`drawn.py:277-302`).
- Gemini 3.8 Flash reads the sheet against `drawn_asks` (claims, spec relationships, exact text, view) plus `DRAWN_FIXED` (`image_check.py:210-250`).
- Then up to 2 fix passes that patch the SVG (`drawn_fix`, `:253-273`; `DRAWN_PASSES=3`).
- Still failing → "held" (`visuals_stage.py:3686-3687`). Selecting a held shot needs `--notes`.

**Into the film (kept)**
- A selected drawing goes forward as a `take` movie (`record_gap`, `visuals_stage.py:4200-4222`). Assembly writes it at the timeline fps with exact length (`stage3/assembly.py:113-262`).

**Operator layer (constrains everything)**
- The guard (`plugin/hooks/guard.py`) lets the operator's Claude run only `python vw.py …` in Bash (`:105-113`). The only skill it allows is `vw:vw` (`VW_SKILLS`, `:24`), and the only helpers are `vw-scene-review` and `vw-plan-gaps` (`VW_HELPERS`, `:25`). Files can be written only inside the active run.
- So today an operator's Claude cannot run `npx hyperframes` or load the HyperFrames skill.
- Laptops have Python 3.12, FFmpeg and Git, but no Node (`design/31:10-27`).
- The VM has Playwright Chromium and FFmpeg 9, but no Node (`design/116:42`). `deploy-server.sh` does no system installs.
- The server calls Gemini, OpenAI, ElevenLabs and Apify, but never Claude. Claude runs only on the operators' laptops.

## 3. Your questions, answered

**How does it fit the current flow?** It replaces stage 9's drawn route from "write the SVG" to "select the take". Everything before it stays the same: the plan, the claims, the drawing spec, the references and the word timing. Everything after it stays the same too: select, held, assembly and delivery. The drawn shot still enters the film as a movie of its exact slot length.

**If the skill is installed in one account, does everyone get it?** No. Claude Code loads skills from the machine it runs on: the user's own folder, the project folder, or an installed plugin. Installing the skill in one account or on one laptop gives it to nobody else. Our operators get everything through the `vw` plugin, so the route ships **inside the plugin**. Every laptop gets it on the next plugin update. The server's minimum plugin version (`config.py:28`) already turns away laptops that have not updated.

The heavy tools (Node, the HyperFrames CLI, Chrome) are installed **once, on the VM**, not on laptops. The operator's Claude reaches them through `vw motion …` commands, which the guard already allows. So the same pinned version renders every film, whoever runs it.

**Multiple agents?** Yes. The main assistant writes one brief per drawn shot and runs a builder helper per shot, three or four at once. This is the same pattern as `vw-plan-gaps` and `vw-scene-review` today (`v3.json:222`, `:285`). A fresh checker helper then checks each shot. A helper cannot start other helpers, so the main assistant runs the loop.

## 4. The new route, step by step

1. **Brief (server, deterministic).** `vw motion brief --shot S` writes `work/motion/S/brief.md`, built from the plan. It contains:
   - the narration and the word cue times (from `drawn.cue_seconds`);
   - the exact frame count, fps and size;
   - the palette and fonts;
   - every label word for word, the claims and the spec;
   - the approved reference pictures, downloaded next to it;
   - the shot's approved rules (step 2).

   It is the same shape as the test bench's `prompt.txt`, which worked. The folder starts empty apart from the brief. (`hyperframes init` refuses a non-empty folder; all three test sessions hit this.)
2. **Rules (helper `vw-motion-rules`, fresh Claude, before any frame exists).** From the brief, the film's subject and the subject rule file, it writes `rules.md`: numbered rules in three groups (from the brief, universal truths, subject practice). For example: "an opening has a lintel bearing on both sides"; "no vertical joint runs through more than two courses".
   - **Precise mode:** the plan's claims and spec already state what must be true. The helper only adds universal truths, and no operator stop is needed.
   - **Open mode:** the operator reads the list once on the page and ticks, strikes or adds to it before building.
   - One helper per shot, all at once.
3. **Build (helper `vw-motion-shot`, one per shot, 3-4 at once).** It follows the plugin's motion skill (section 5).
   - It first builds the key frame as a still. If the shot has no reference picture, `vw motion snapshot` sends that still to a checker before any animation is made. This is the sketch gate: it catches a structural error such as a wrong view or a missing lintel when it is cheapest to fix.
   - Then it animates. `vw motion check` and `vw motion snapshot --at …` run the HyperFrames check and snapshots **on the VM** and bring the findings and PNGs back into `work/motion/S/`. The helper fixes until the check shows no errors, then runs `vw motion submit`.
4. **Submit and render (server).** The project is zipped (at most 10 MB) and stored at `<run>/visuals/motion/<sha>.zip`.
   - The server refuses it if any of these fail:
     - the length is not the slot's frame count at the film fps, or the size is not the film's;
     - a script or font loads from the network (GSAP and fonts are served from the VM; any other URL is refused);
     - an image is not a `ref:` picture of the run;
     - a label in the brief is missing from the composition's text, word for word (HTML text can be checked exactly, unlike SVG paths or AI stills);
     - the HyperFrames check has errors.
   - A `motion.json` timing file is generated from the word cues ("label X appears by 1.76 s"), so the HyperFrames check verifies the narration timing itself.
   - A worker job (provider `motion`) runs the pinned `hyperframes render --fps <film fps> --quality delivery`, checks the frame count with ffprobe, and makes the contact sheet with the existing `drawn.sheet`.
   - At most 2 motion renders run at once (`VW2_MOTION_CAP`), so renders don't starve analysis and takes on the 4-CPU VM. Each render took 35-66 s on the PC.
5. **Fact check (helper `vw-motion-check`, fresh Claude that never saw the build).** It gets the beat frames, zoomed crops of each part the brief names (made by `vw motion snapshot --zoom`) and the rules. It:
   - describes each frame as a stranger would;
   - marks every rule pass or fail, with the place and the fix;
   - writes `check-<round>.json`, which `vw motion verdict` sends to the server.
6. **Redo.** A failed shot goes back to a builder helper with only the failed rules. This is at most 2 redo rounds (the same cap as today's `DRAWN_PASSES=3`). A shot that still fails is **held**, with its open rules shown. The existing held logic applies: selecting it needs `--notes`.
7. **Present.** The visuals page's Takes step shows the movie, the sheet and the rule list with ticks, using today's `drawnPasses` box. The operator selects as today.
8. **Learn.** When the operator or SK corrects a shot, the correction is saved as a rule in the subject rule file in the library (`library/subject-rules/<subject>.md`, for example `rat-trap-bond.md`, seeded with shot 2's four corrections). The next shot on that subject starts with it.

## 5. What ships in the plugin

- `plugin/skills/motion/`: the HyperFrames `hyperframes` skill at a pinned version (0.8.226, Apache 2.0, licence and notice kept), with its references.
  - Its CLI lines are rewritten to the `vw motion` commands.
  - Our rules are added: film fps and size, the exact frame count, fonts from the brief, labels word for word, no music, `ref:` pictures only.
  - Left out for now: the registry skill (it needs `npx` on the laptop) and `media-use` (shots are silent).
- `plugin/agents/vw-motion-shot.md` (Read, Write, Edit, Bash for `vw` only, the `vw:motion` skill; opus, high).
- `plugin/agents/vw-motion-rules.md` and `vw-motion-check.md` (Read, Write; opus, high).
- `guard.py`: add `vw:motion` to `VW_SKILLS` and the three helpers to `VW_HELPERS`. Bash stays `vw.py`-only, with no change to that rule.
- `vw.py`: `motion brief | snapshot | check | submit | verdict | status | download`. `draw`, `scene` and `font` stay for runs on the older way.
- `server/procedures/v3.json` stage 9: the drawn paragraph is rewritten for the motion route, chosen by the run's route (section 9).
- Plugin version bump and a raised `PLUGIN_MIN_VERSION`. Each laptop runs `/plugin marketplace update vw-local` and restarts. SK checks the desktop plugin list after the deploy (the 29 Oct incident).

## 6. What changes on the server and the VM

| File | Change |
| --- | --- |
| `visual_contract.py` | `scene_motion {sha256, rules_sha}` beside `scene_svg`; `DrawnAction` is not needed on motion runs (timing lives in the composition and `motion.json`) |
| new `motion.py` | Unzip and validate, label match, timing file, run the pinned CLI (check, snapshot, render) with timeouts, frame count |
| `visuals_stage.py` | `set_motion`, `render_motion`, `motion_check`/`motion_snapshot` (quick jobs outside the run lock, as design/92 L60), verdict record, held rule extended to open rules |
| `visual_workers.py` | provider `motion` in `tick`; cap `VW2_MOTION_CAP` |
| `image_check.py` | Gemini `drawn_fix` and the sheet read are not used on motion runs; `drawn_asks` wording seeds the rules helper |
| `main.py` | routes `/visuals/motion/*`; `/api/meta` reports `hyperframes: <version>` |
| `templates/visuals.html` | Takes step: the rule list with ticks, rounds, held reasons |
| `stage3/delivery.py` | drawn movies listed as graphics, not "AI video" (found on the way, `ai_kind` `:93`; a one-line fix, see section 11) |
| VM (root, by hand, SK's yes) | Node 22 LTS, `/opt/vw2/hyperframes` with `hyperframes@0.8.226` and a lock file, a vendored GSAP, Noto Sans (Latin, Devanagari, Tamil for design/123) and the brand font as local files, Chrome via `hyperframes browser ensure` or pointed at `/opt/vw2/browsers` (phase 0 decides) |

## 7. Requirements check

**Unstated but expected**
- Exact frame count and fps of the film; 1920x1080 unless the film says otherwise; H.264 that assembly accepts; no audio.
- The same composition renders the same frames on every run (HyperFrames seeks a paused timeline; the check refuses `Math.random`, timers and network).
- Fonts and GSAP never come from the network on the VM.
- Labels exactly as the plan states; numbers only from the claims and the spec.
- Each shot's brief, rules, project, check rounds and verdicts are kept, so a shot can be repeated or audited.
- Token use per shot is recorded (a helper's finish note reports its tokens), so cost is known after the pilot.
- The new `vw motion` code in `plugin/` stays Python 3.9-compatible (the Mac builder runs 3.9); the zip is made with the standard library only.

**Edge cases**
- A very short shot (3 s) or a long one (20 s+): the brief's states must fit. The check's `line_unread` warning and the timing file show crowding.
- Hindi or Tamil labels (design/123): the fonts must hold those scripts. HyperFrames' bundled fonts are Latin only, so the brief names local Noto fonts.
- The narration is re-voiced after a render: word cues move, the shot is marked stale (the existing "plan changed since render" refusal), the timing file is redone and the helper retimes.
- The operator's Claude usage limit is hit mid-shot: the project stays in `work/motion/S/` with `REVIEW.md`. A new helper continues from the files, not from memory.
- A helper stops or returns nothing: the main assistant re-runs it once, then reports the shot to the operator.
- Two helpers on the same shot: one folder per shot, and submit refuses a second upload while a render of that shot is queued.
- A project that is too big, holds external URLs, or uses non-`ref:` images: refused at submit with the reason.
- The checker and the builder disagree round after round: the cap of 2 redo rounds, then held with the open rules.
- The VM is busy: renders queue behind the cap, and `vw motion status` says so.
- Mac and Windows paths in the zip: forward slashes only; names checked on the server.

**Failure modes and handling**
- Render fails (Chrome, Node, timeout): one automatic retry, then the job fails with the log tail on the page. Nothing paid is lost (renders cost ₹0).
- The check finds errors: submit is refused with HyperFrames' own `Fix:` lines.
- The fact check fails: a redo round; after 2 rounds the shot is held.
- A HyperFrames upgrade changes behaviour: the version is pinned on the VM and in the skill. An upgrade is its own release with the three test shots re-rendered and compared.

## 8. Phases

| Phase | What | Done when |
| --- | --- | --- |
| 0. VM spike (SK's yes for the root installs) | Install Node 22 and the pinned CLI in `/opt/vw2/hyperframes`; render the three test-bench projects on the VM with workers running | Same frame count; frames match the PC renders by eye; render time and memory measured with 18 workers up |
| 1. Server | `motion.py`, routes, validator, label match, timing file, render job, cap, sheet | Tests first (section 7 list); `server/unit` passes |
| 2. Plugin | Skill bundle, three helpers, guard entries, `vw motion` commands, procedure text | `plugin/tests` passes; the guard tests show `npx` is still blocked and `vw motion` allowed |
| 3. Fact-check loop | Rules and check helpers, verdict record, held with open rules, subject rule files with the rat-trap seed | **Blind test:** the checker, given only the brief and shot 2's v1 frames, finds at least 3 of SK's 4 corrections |
| 4. Page | Takes step: rules, ticks, rounds | Side-by-side click check as UX1 |
| 5. Pilot | One fresh film, or VW-12's drawn shots again, on the motion route | SK and the team judge against the SVG renders; time and tokens per shot recorded |
| 6. Retire | Default route becomes motion; the SVG route is refused for new runs | Old-ways row closed in design/35 |

Builds go through the regular lane: tests first, full suites, deploy on SK's word, one deployer.

## 9. Older ways

- **Drawn route v2 (SVG + frame stepping + Gemini fix):** kept until phase 6, because open films and the pilot comparison need it.
  - A run picks its route at `vw start --drawn motion|svg`. Like `--images`, the choice is fixed for the run.
  - At phase 6 a new run asking for `svg` is refused: "the SVG drawn route is retired; drawn shots use vw motion". The SVG upload, `drawn_fix` and `DrawnAction` code is removed in the release after that.
  - A new row goes in design/35's old-ways list.
- **`scene_drawn`:** already retired (design/117). No change.
- **Test-bench skills in `hyperframes-test/.claude/skills`:** these stay as the bench only and never reach operators.

## 10. Not covered

- **Claude on the server (Agent SDK):** authoring stays on the operators' Claude, as today. A server-side author would need an Anthropic key and per-token billing; that is a later decision.
- **Registry blocks and `media-use`:** they need `npx` on the laptop; add them when a shot needs one.
- **Sound in drawn shots:** shots stay silent, as the brief says.
- **The 8-frame dissolve for drawn movies** (`assembly.py:24-36` counts them as non-graphic, so they get hard cuts): unchanged; a separate question for SK.
- **Cost per shot:** measured in the pilot, not estimated here.

## 10a. Phase 0: the exact VM steps (for SK's yes)

Read-only check on 1 Nov, 20:3x IST: there is no Node on the VM; it has 4 CPUs and 16 GB (about 14.7 GB free); `/opt/vw2` needs sudo. No service is restarted, and nothing in `/opt/vw2/app` or the venv changes.

```bash
# 1. Node 22 LTS from NodeSource (root)
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt-get install -y nodejs
node -v

# 2. The pinned CLI in its own folder, owned by the service user
sudo mkdir -p /opt/vw2/hyperframes && sudo chown vw2:vw2 /opt/vw2/hyperframes
sudo -u vw2 bash -lc 'cd /opt/vw2/hyperframes && npm init -y && npm install --save-exact hyperframes@0.8.226'

# 3. Telemetry off, the pinned Chrome, the health check
sudo -u vw2 bash -lc 'cd /opt/vw2/hyperframes && npx hyperframes telemetry disable && npx hyperframes browser ensure && HYPERFRAMES_FFMPEG_PATH=/usr/local/bin/ffmpeg HYPERFRAMES_FFPROBE_PATH=/usr/local/bin/ffprobe npx hyperframes doctor --json'

# 4. Trial: the three test-bench projects (copied without their MP4s) rendered in /tmp/hf-trial, with the 18 workers up
#    render --fps 25 --quality delivery --workers 2; then ffprobe each for frames 76, 139 and 227; log time and peak memory (/usr/bin/time -v)
```

Recorded in the trial: whether the GSAP CDN and Google Fonts were fetched over the network (the motion route must not need them; phase 1 serves them from the VM), and whether the pinned Chrome runs without new system packages.

### Phase 0 result (1 Nov 2026, on SK's "okay proceed")

**Done on the VM:**
- Node v22.23.4 and npm 10.9.9 (NodeSource apt source, package `nodejs`).
- `/opt/vw2/hyperframes`, owned by `vw2`: `hyperframes@0.8.226` saved exact, with its lock file.
- Its own `HOME` at `/opt/vw2/hyperframes/home`. The npm cache and the pinned Chrome live there: `chrome-headless-shell` linux-152.0.7977.30, under `home/.cache/hyperframes/chrome/`.
- Telemetry is off (`telemetry disable`, plus `HYPERFRAMES_NO_TELEMETRY=1` on each call).
- No new system packages were needed for Chrome. The app, the venv and the services were untouched. `vw2-server` and `vw2-worker` stayed active throughout, with 19 worker processes up.

**`doctor --json`:** ok for the version, Node, CPU (4), memory (14.2 GB free), disk (86.8 GB), `/dev/shm`, FFmpeg/FFprobe 9.0.2 (via `HYPERFRAMES_FFMPEG_PATH`/`HYPERFRAMES_FFPROBE_PATH`) and Chrome. Not ok, and not needed:
- Docker;
- whisper, Kokoro and MusicGen (optional media);
- the "archive extractor", which only media imports use.

**The trial:** the three test-bench projects in `/tmp/hf-trial`, rendered with `render --fps 25 --quality delivery --workers 2`, as `vw2`.

| Shot | Frames (ffprobe) | Render (CLI) | Wall clock | Peak memory, CLI process |
| --- | --- | --- | --- | --- |
| shot1, 3.04 s | 76, 1920x1080, 25/1 | 9.7 s | 12.0 s | 385 MB |
| shot2 (v2), 5.56 s | 139, 1920x1080, 25/1 | 14.0 s | 16.5 s | 383 MB |
| shot3, 9.08 s | 227, 1920x1080, 25/1 | 16.2 s | 18.5 s | 390 MB |

- **Speed:** three to four times faster than on SK's PC (35 to 66 s).
- **Memory:** Chrome's own processes are not in the peak column. HyperFrames' note is about 256 MB per Chrome worker, so a render at `--workers 2` is under 1 GB.
- **Same frames as the PC:** five frames per shot compared with the PC renders differ by 0.0 to 0.95 levels out of 255 on average. At most 0.23 % of pixels differ by more than 40, all of it edge smoothing on text and dashed lines. They are visually identical.
- **Network:** the render logs name no fetch, but the test compositions load GSAP from the jsdelivr CDN. A render on the VM therefore depends on the network today. Phase 1 serves a pinned GSAP (and the fonts) from `/opt/vw2/hyperframes` and refuses external URLs.

### Phase 1 result (1 Nov 2026): the server side, built and tested, not committed or deployed

- **New `server/app/motion.py`:**
  - the upload rules (zip, files, no network, no clocks or random, fonts, `assets/ref/<id>.png` approved pictures only, the root's length, fps and size);
  - the labels read word for word from the visible text;
  - the timing sidecar (`index.motion.json`, `appearsBy` at the cue plus 0.6 s);
  - preparing the folder with the server's GSAP, fonts and pictures;
  - the CLI calls `check`, `snapshot` and `render`, and the sheet frames.
- **Contract:** `scene_motion {sha256, labels, cues}` on a shot; `motion_needs` (cues inside the shot, one scene kind per shot).
- **Run:** `drawn_route` (`svg` by default, or `motion`, fixed at creation; migration `010_drawn_route.sql`). `draw` and `scene` refuse on a motion film; the `motion` calls refuse on an SVG film.
- **Stage functions:**
  - `set_motion`: the upload;
  - `motion_tool`: check or snapshot, as provider `motion` jobs, never takes;
  - `render_motion`: a `drawn` job with request kind `motion`, so review, select, held and assembly are unchanged;
  - `motion_job`: status, findings and snapshots for the helper.
- **Worker:** `process_motion` (check, render, frames and size as must lines, sheet), `process_motion_tool`, and `renders_free` (the cap `MOTION_CAP`=2 over drawn and motion jobs).
- **Routes:** `POST /visuals/motion/upload`, `/visuals/motion/tool`, `/visuals/motion/render`, `GET /visuals/motion/jobs/{id}`. `/api/meta` reports `hyperframes`.
- **VM:** `gsap@3.15.0` saved exact in `/opt/vw2/hyperframes` (`MOTION_GSAP`).
- **Tests:** `server/unit/test_design130_p1_pure.py` (25 tests), and `test_design120_a_pure.py` updated for the new column. The full `server/unit` suite passes: 991, 4 skipped.
- **Checked against the real CLI on the VM** (the motion.py file run from `/tmp` with a stub config; the deployed app untouched), on shot 2:
  - the rules and the labels pass;
  - check 9.9 s (ok; one warning, file size);
  - snapshot 3.8 s;
  - render 16.3 s; the sheet frames are read from it;
  - a sidecar cue at 0.5 s gives `motion_appears_late` ("appears at 1.79s but should be visible by 0.5s"), so the timing is really checked.
- **Two CLI behaviours noted:**
  - `snapshot --at` also writes a frame near the end; pairing by order keeps only the asked times.
  - `--zoom` wrote full frames, not a crop. Crops for the checker are made in phase 3 instead.
- **Not covered:** `server/tests` (Docker) not run; Hindi and Tamil fonts are not on the VM yet (only Noto Sans Latin plus the brand font).

### Phases 2 to 4 result (1 Nov 2026): plugin, fact-check loop, page; built and tested, not committed or deployed

**Plugin 0.66.0** (the server's minimum raised to 0.66.0):
- `plugin/skills/motion/`: our `SKILL.md`, the HyperFrames contract with `vw motion` steps, plus `references/format.md` and `motion.md` copied unchanged at 0.8.226, and `NOTICE.md` (Apache 2.0).
- Three helpers: `vw-motion-rules` (rules before any frame), `vw-motion-shot` (the builder) and `vw-motion-check` (the fresh checker, Read/Write/Glob).
- `vw motion brief | upload | check | snapshot (--at, --crop) | verdict | render | status | rule`, and `vw start --drawn svg|motion`.
- Guard: `vw:motion` allowed, the three helpers allowed, the plugin's `skills/` folder readable (never writable). Bash is still `vw.py` only, so `npx`, `node` and `hyperframes` stay blocked.
- `vw.md` and `operator-CLAUDE.md` name the helpers.

**Server 0.79.0:**
- `motion_brief` (the brief from the plan, with the subject's rules).
- `motion_verdict`: verdicts per shot by round.
- Select holds a motion drawing until it has a clean verdict of its rendered project.
- Subject rules: `server/subject_rules/rat-trap-bond.md`, seeded with SK's four corrections and the masonry truths; `vw motion rule` adds to it in storage, with the operator's words.
- Snapshot crops at twice their size for the checker.
- `take_jobs` never lists a helper's check or snapshot as a take.
- The Takes step shows the latest fact check rule by rule (`factCheck` in `visuals.html`).

**Procedure:**
- `scripts/d130_wording_v3.py` adds section 11 (the loop: brief, rules, build, snapshots with crops, check, verdict, at most two redo rounds, render, rule) to the visuals part "later", chained into `c1_split_v3.py --check`.
- The visuals stage's word budget rose 10,227 → 10,488 (+261, `test_design125_stage7_c_pure.py`).

**Old ways:** design/35 row 21 (the SVG route, kept until phase 6).

**Tests:**
- `server/unit`: 997 passed, 4 skipped (`test_design130_p1_pure.py` 31 tests; `test_g2…` and `test_release0782…` follow the new minimum).
- `plugin/tests`: 387 passed, 4 failed. The 4 failures are the same on a clean HEAD (3 Windows-only plus `test_master_cli` slides): they pre-date this work.
- `c1_split_v3.py --check`: ok. The page script passes `node --check`.

**The blind test (phase 3 gate):** a fresh `vw-motion-rules` and a fresh `vw-motion-check`, with the exact helper texts, were given only shot 2's brief (`prompt.txt`, with no subject rules) and v1's frames at 0.5, 2, 3 and 5 s plus five crops.

- The rules helper wrote 73 rules: 42 from the brief, 17 truths, 14 subject. Its four questions included "the brief says continuous cavities; real rat-trap bond closes them".
- The checker failed 19 rules. Against SK's four corrections:
  - **no lintel:** found (rules 45, 70);
  - **wall beside the window not solid:** found (rule 66);
  - **straight joints at the T-junction and the corners:** found (48, 68, 69);
  - **cavities read as holes in the bricks:** missed. It saw "pale blue rectangles … set inside the stretchers" and passed it, because the brief's rule said "ghosted behind the face".
- **Result: 3 of 4, the gate passes.** It also found faults SK did not list: uneven joints at the zone edges, two headers side by side, and the leader stopping on a cavity.

**Changed after the test, and not measured again** (a re-run on the same shot would be tuned to it):
- The checker gets Glob; it had to guess the snapshot file names.
- The rules leave out what the server checks (length, fps, sound, cue seconds); 8 of the 19 fails were such rules, unseeable in a still.
- Both helpers judge "does it read as what it is"; the structure is judged on the finished state, not mid-build.
- On a real run the seeded subject rules carry the cavity rule.

**Not covered:**
- No end-to-end run on the VM yet: it needs the deploy. `vw motion` against the live server, and a `vw-motion-shot` helper started from the plugin, are untested. The builder helper's work matches the test-bench sessions, which were not run as plugin helpers.
- The page change is checked by script syntax and the existing page tests, not seen with live data.
- `server/tests` (Docker) not run. Hindi and Tamil fonts are not on the VM. `--zoom` is unused.
- The operator ticking rules.md in open mode is an instruction in the procedure, not a page control.

## 11. Found on the way (separate from this plan)

- **Graphics listed as AI video:** `stage3/delivery.py:93` lists every selected drawn movie as "AI video" and leaves it out of the "Graphics" list. This is true on the live route today, not only after this plan.
- **Stale design notes:** design/31 and design/29 describe the plugin update with stale lines ("version stays 0.1.0", the cache sync).
