# Handoff — Wan 3.0 as the AI-video generator for VideoWizard v2 (written 6 Nov 2026, after the 5 Nov session)

## Goal: what we are trying to build

Move the visuals stage's `video` route (AI video takes) from Gemini Omni to **Wan 3.0 Omni through the Wan CLI**, as an **experiment first** (SK's framing, 5 Nov): reusable scripts, scenarios run and retested until the method is final, then integrated into the main flow. No operator-level or builder-level change until SK says "integrate".

The method under test, in one line: the plan's scene and shot → an **environment picture** per scene (the place with nobody in it) → the people's and things' **set pictures** → a **staging video** that fixes positions, facing, hands and timing (a Blender blockout; the cartoon method of design/153–169 is parked) → one Wan call with the pictures tagged `@Image1…`, the staging video as `@Video1`, and a short text in **Alibaba's prompt formula** (design/173 §3) written under **SK's right-handed staging rules** (design/175) → the take, reviewed on half-second strips.

Three notes hold the plan and the evidence: design/170 (the integration plan: what leaves the video route, what stays, the environment reference, the 18-point second review, estimate 12–14 days), design/171 (Wan test rounds on VW-18), design/172 (Blender). HyperFrames (`drawn` route, `vw motion`) is untouched and stays its own step. Gemini Omni stays in the catalogue as the kept older way (design/35 rule).

## Current state

- **Nothing is built or deployed.** Live server unchanged (0.90.3 / plugin 0.76.2; design/151's 0.90.5/0.76.3 built, not deployed; deploys on hold without SK's explicit yes).
- **Wan CLI 0.0.3** installed globally on this PC (Node 24 present), logged in by SK to the account (site intl, Premium). **256 credits** left of 1,202 at the start; 3 credits per second of output at 720P; a video reference is billed too (about double); Thinking Mode (a brief file attached) about 2.5×.
- **The VM has no Wan key and no Node.** `VW2_WAN_ACCESS_KEY` goes into `server/.env` on the VM only at build part (ii); SK adds it when told.
- **Test round results (design/171, 5 Nov):** round 1, eight runs on VW-18's real plan text and sets: identity, place, action order and length all held; a **30 s call with three shots cut at the named seconds held** (W3, W7, W8). Round 2 (SK's changes: steps not seconds, right hand, smart duration): order and hand held; smart duration without seconds ran 2–3× long. Counts of identical things drift in every form. A reference's pose and contents leak. "Smoke only, no flame" in the text removes an invented flame.
- **Blender (design/172):** SK built the plinth scene from my brief (two renders: `plinth_blender.mp4`, `plinth_motion.mp4`). With the render as `@Video1`, Wan followed the staging and timing **second for second** with the real look from the photographs (B1, B2, A1). Smart duration then takes the video's length.
- **Alibaba's formula (design/173, 174):** the mason atom (three shots, the pile always left of the mason) written in the formula and run once (M1): the three shots at their seconds, the fixed order, identity and sound all held; the mason faced the camera in shot 2; the pan was not emptied. The prompt was then revised with the right-handed rules (not run).
- **SK's right-handed staging rules (design/175, memory `feedback-right-handed-staging`)** bind every prompt from now on: handles and openings face right; camera over the right shoulder or right profile; the left hand given a resting task; action flows left to right.
- **Open question:** whether the website's chat-canvas "agent" is the CLI's Thinking Mode (`--file`/`--url` → `thinkMode: true`) or a site-side planner. Every task on the account so far is a plain "normal" task with the prompt unchanged; one website run in the chat canvas, then its record read (`createScene`, `thinkMode`, `finalPrompt`), settles it. The CLI (0.0.3) has no agent command.

## Files in flight / active files

Repository `videowizard-v2` (`main`, pushed through e74c201; `codex-review/` has two untracked files not mine):

| File | What |
|---|---|
| `design/170-wan-integration-plan.md` | the plan: §2 where Wan enters, §2a what leaves the video route, §2c the take text and tagging, §3 the environment reference, §4 the test round, §5 build parts, §8 the second review |
| `design/171-wan-test-round-vw18.md` + `171-assets/` | rounds 1 and 2 (§1–§8), every prompt (`wan-prompts-review.md`), strips, logs, scripts |
| `design/172-blender-scene-plinth.md` + `172-assets/` | the Blender brief (§1 to paste), results §4–§5, both renders, the simplified agent-mode prompt |
| `design/173-wan-model-facts.md` | Wan 3.0 / Prime / 2.7, parameters, Alibaba's formula, what it changes for us |
| `design/174-mason-atom-alibaba-formula.md` + `174-assets/` | the mason atom in the formula, its four pictures, the M1 result, the right-handed revision (`prompt-mason-alibaba-righthand.txt`) |
| `design/175-right-handed-staging-rules.md` | SK's four rules |
| `design/161`, `167`, `168`, `169` | the parked cartoon method (learnings that carry over: no counts, timecoded text, strips at 480 px) |

Scratchpad (this session only, `…\scratchpad\vw18\`): `wan_test.py` (submit, poll with `result get`, save, credits; **never `--dry-run`**; calls the CLI's JS entry through Node), `strips.py`, `gen_env.py` (environment pictures on the VM), `pull.py` (run data from storage), `resume.py`, `run6.sh`/`run2.sh`/`run_r2.sh`, `prompts/`, `env/`, `pics/` (VW-18's 47 pictures), `out/` (every MP4 and strip), `blender-in/`, `agent/`, `mason/`. Copies of the scripts, prompts and strips are in the `1xx-assets` folders; the MP4s are not in git (SK has them all).

## Changes

All on `main`, all design notes and assets, **no code** in `server/` or `plugin/`:
- 5 Nov: design/161 rewritten whole; 169 dry run; 170 plan (+2c, +§8); 171 (+§7, +§8); 172 (+§4, +§5, assets); 173; 174 (+result, +revision); 175.
- Memory: `vw2-animatic-round-5-nov` (parked), `vw2-wan-integration-5-nov`, `feedback-right-handed-staging`.
- This PC: `@wan-ai/cli` installed globally; SK's Wan login saved in `~/.wan/config.json` (never read, never printed).

## Failed attempts

- **`--dry-run` submitted real tasks** on CLI 0.0.3 (two paid 5 s tasks). Removed from the script; tags are checked locally.
- **The Windows `wan.cmd` shim cut a multi-line prompt** at its first line break and dropped every flag after it. Fixed by calling `node …/@wan-ai/cli/dist/index.js` with an argument list.
- **Rate limit `blocked`** ("feeling uninspired") on two submissions; a retry after 20 s succeeded. Submissions are now staggered 20–25 s.
- **A launcher that exited** killed its child poller (W7); `resume.py` re-polls a task id.
- **Git-Bash paths** (`/c/…`) handed to Python failed `isfile`; inputs are copied into the scratchpad with plain paths.
- **Credits before/after** is unreliable with several jobs in flight (logs show 294 or negative); the balance across a round is the true cost.
- **Smart duration without seconds** ran 10–20 s for 4–8 s shots (round 2); keep an explicit duration, or a staging video.
- **Counting** failed in every form (round 1: 3→5; round 2: 2→5; M1: the pan not emptied): the model's limit, not the prompt's.
- **A reference picture's wrong contents leak**: the pointed wall came out flat because the technique set picture shows a flat wall; the pan kept its mortar despite "without the mortar".
- **The environment picture added nothing** where the place's set picture already was the camera's view (the kiln, W6).
- **An invented flame** in the kiln trench (W8), fixed by "smoke only, no flame" in the text.
- **The right hand forced by text** made a left-to-right sweep look awkward (SK): the hand is a staging fact; now the rules of design/175 and the staging video decide it.
- **The cartoon method** (29 Omni runs, design/153–169): controlled staging but not counts; parked by SK on 5 Nov evening in favour of Wan.

## Next steps

1. **Read SK's agent-mode task** once he makes one in the website's chat canvas: `wan task list --page-size 5 --media-type video --output json`, compare `createScene`, `thinkMode`, `finalPrompt` with run A1 (`71e03506`). Decide whether the CLI reaches it (brief file) or not.
2. **Run the right-handed mason prompt** (`174-assets/prompt-mason-alibaba-righthand.txt`, four pictures in tag order) when SK says so: 30 credits at 720P, or test at 480P (about a quarter).
3. **Next Blender scenes**: the kiln hand-over (two figures, a pass between them) and the pointing close-up (hands only), briefs in the shape of design/172 §1 with the right-handed rules applied to object placement and camera; then a 30 s three-shot blockout. SK renders; the MP4 goes in as `@Video1`.
4. **Cheaper tests**: 480P for test runs (design/173); Prime for finals is website-only.
5. **When SK says "integrate"**: design/170's build parts in order, (i) the environment reference per scene (with the rule: a set picture that already is the camera's view may stand in), (ii) the Wan provider + key on the VM + Node/CLI install + concurrency cap + credits as cost, (iii) the Wan take text in Alibaba's formula under the right-handed rules, prepare-take without a start image on `wan`, the plugin and page changes, the wording script, (iv) audio/video input fields. Tests first; the full suite on the VM; deploy only with SK's explicit yes.
6. **Still to settle with SK**: the rupee price of a credit; whether the staging video is built by a helper from the plan (Blender in background mode on the server) or by the operator by hand for now.
