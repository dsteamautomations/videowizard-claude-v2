# 176 — Gemini Omni 1.2 Flash: what changed, and the plan to rerun yesterday's cartoon test on it (6 Nov 2026)

SK, 6 Nov: two developments: good results from Seedance 2.0 and Seedance 2.0 Flash (names to be confirmed); and Gemini Omni 1.2 Flash, the successor to 1.1. To test 1.2, go back to yesterday morning's cartoon-edit test (the mason scene, design/157–165), where character and activity consistency and the brick pick-up lagged, and where we decided to keep counting off camera and use staging, multi-angle and close-ups instead.

## 1. The documents of yesterday morning's round, gathered

| Note | What it holds | Assets |
|---|---|---|
| design/153, 154, 155 | the branch's scope; SK's park-thread lessons; the phase-by-phase double check that chose the edit path (cartoon video in, live action out) | `156-assets/omni_test.py` (the runner, model `gemini-omni-1.1-flash`) |
| design/156 | the gate test on the park scene: the edit path drifts timing without seconds; frames give exact cuts; the baseline is strong | prompts A/B/D, key moments |
| design/157–160 | the mason scene: the first cartoon and shot list (the pile always on the mason's left); direction loss; colour tags and pace; facing and tool contact, video with or without dense frames | `draw.py`, `shot-list.md`, prompts, key moments, `references.png` (the mason, the helper, the tools) |
| design/162–164 | numbers and labels; no cut between a state and its change; twenty frames alone | prompts, sixteen-moment sheets |
| **design/165** | **the inference: the cartoon controls staging, never counting**; the rules §2; tests T1–T5 (the hand-off T3 passed; T4 SK's staging passed; counts of a pan failed) | `tests4.py`, prompts t1–t5, review strips at 480 px |
| design/166 | five barrels; text-only controls proved the cartoon is not the cause of count drift | prompts, strips |
| **design/167, 168** | **the direction SK agreed**: D1 establish wide then cut tight on the action, hands and one object, no count stated, a shot that needs a true count is footage or a still; D7 the documentary default of one or two angles; the drawing rules G1–G8; the face rules E1–E6 (never crop a face to hide a count) | |
| design/161, 169 | the consolidated requirements; the four VW-12 scenes run by hand, all clean | `169-assets`: scenes.py, prompts, marks, strips |

Still on this PC (scratchpad): the cartoons `cartoon-c/d/e/f.mp4` and `cartoon-f-24fps.mp4` (the mason, 10 s), `anim-test/cartoon.mp4` (the park), the four VW-12 cartoons; the Omni 1.1 outputs M1, M2, V1, V2 and the VW-12 takes; the three mason photographs.

## 2. Gemini Omni 1.2 Flash, from Google's own pages (read 6 Nov) and the API

- **Name**: `gemini-omni-1.2-flash`, generally available on 5 Nov 2026 (the API lists it beside `gemini-omni-1.1-flash` and `gemini-omni-flash-preview`; the VM's key sees all three). From **3 Dec 2026** every call to 1.1 is routed to 1.2 at 1.2's rates, so the server's `OMNI` constant changes one way or another.
- **Length**: **3–15 s** in whole seconds (`response_format.duration: "15s"`), default 10 s; a duration set here overrides any length in the text. First-and-last-frame interpolation and per-turn extension: 3–10 s. **Extension** continues a video by 3–10 s a turn up to **30 s total**, using the last 10 s as context, appending only.
- **References**: **up to 6 reference images** (up to 3 per character, up to 2 characters) for likeness, attire and objects; reference **videos** for visual likeness only, audio ignored: up to 3 clips of ≤3 s for a 3–10 s video, 1 clip for 11–15 s; only for new videos, not for edits or extensions.
- **Editing**: an uploaded video of **≤15 s** (Files API) edited by a prompt; multi-turn editing of model-made videos via `previous_interaction_id`; simple edit prompts, "keep everything else the same". Not available in the EEA, Switzerland and the UK for uploaded videos.
- **Output**: 16:9 or 9:16; **360p, 720p (default), 1080p and 4k (upscaled)**; native audio; `delivery: "uri"` for files over 4 MB; SynthID.
- **The `task` parameter** (`video_config.task`: `text_to_video`, `image_to_video`, `reference_to_video`, `edit`, `extend`) only as a fallback when the natural-language prompt does not select the mode. **`<FIRST_FRAME>` and the other control tags are deprecated** (our server's `motion_text` still writes them: an old way to retire on 1.2).
- **Not supported**: system instructions, temperature, negative-prompt fields (put "do not X" in the prompt), audio inputs, reasoning across several videos, YouTube sources, voice editing.
- **Prompting** (Google's guide): say "in a single unbroken scene, one continuous shot, no scene cuts" or the model cuts on its own; "no dialogue, no embellishments, no extra sound effects"; **timing in natural language works** ("after 3 seconds, a woman enters", "every 2s cut to a new frame") and a timecode syntax too; describe the audio or it invents one; for edits keep prompts short.
- **Price**: $12.00 per 1M output tokens, "30% lower" than 1.1; rate limits doubled (tier 1: 8 a minute, 40 a day; tier 2: 16 and 200; tier 3: 40 and 2,000).
- **Google's own claim** that matters to us: "improved character and subject consistency across up to 6 reference images". That is exactly what lagged yesterday.

What 1.2 does **not** change: the edit path's inputs (cartoon video ≤15 s + photographs + text) and the reference-video limits are the same as 1.1; counting is not mentioned anywhere.

## 3. The retest, as SK framed it

Rerun yesterday's mason test on 1.2 with the same inputs, so the only variable is the model:

| # | Run | Inputs | What it measures |
|---|---|---|---|
| O1 | the mason cartoon edit, exactly as design/163's best run (the no-cut cartoon `cartoon-f-24fps.mp4`, the three photographs, the timecoded prompt) | model `gemini-omni-1.2-flash`, duration 10 s, 720p, edit | character and activity consistency against yesterday's V-runs; the brick pick-up; the pan's state |
| O2 | the same with the shortcut arrangement of design/167 D1: the scene rewritten with no count in view, wide to establish then tight on hands and one object, a face shot, two or three angles with cuts named by the second | the same cartoon re-cropped, or text only with the three photographs | whether the agreed grammar plus 1.2 gives a clean take |
| O3 | the 15 s single-call length: the mason scene at 15 s with 6 references (3 of the mason, 3 of the helper) | reference_to_video, no cartoon | the new consistency claim, and 15 s in one call |

Tooling: `omni_test.py` needs the model name, `response_format.duration`, and `resolution` as options (three lines). Runs go on the VM as yesterday (the key is there; SK's gcloud login is fresh). Review on half-second strips at 480 px (design/167 D8). Each run about ₹90 at 10 s; 1.2 is said to be 30% cheaper.

Seedance 2.0 and 2.0 Flash: **accessed through OpenRouter** (SK, 6 Nov; the marketplace of design/173's screenshot). Their OpenRouter model ids and prices are read from OpenRouter's model list before any run; an OpenRouter key is needed on the VM or this PC (not yet placed). They run through OpenRouter's API, not Google's, so the runner gets a second transport.

## 4. The failure pack: what Omni 1.1 got wrong, with the exact inputs, so 1.2 is judged on the same cases

Everything below is in `176-assets/`: the cartoons that went in (`cartoons/`), the three mason photographs and the two park stills (`photographs/`), the prompts as sent (`prompts/`), four Omni 1.1 outputs to compare against (`omni-1.1-outputs/`), the shot list (`mason-shot-list.md`) and the runner (`omni_test.py`, model name to change). Every output's half-second strips are in the original `15x-assets` folders.

| Case | Note | Inputs (as sent to 1.1) | What 1.1 got wrong | What 1.2 must do better |
|---|---|---|---|---|
| **F1 park, cartoon edited** | 156 (runs A1, A2) | `cartoons/park-cartoon-156.mp4` + the two park stills + `prompts/156-A-park-edit.txt`; 10 s, edit | cuts drifted 0.2–1.3 s, the last cut missing or late; **one tumbler instead of two** in the close-up; the yawn half-raised | cuts within 0.1 s of the cartoon; two tumblers held through the close-up |
| **F2 mason, frames path** | 157/158 (M1, M2) | ten cartoon frames + 3 photographs + `prompts/157-frames.txt` | **bricks went back into the pan** (M1); **the hands reached into the empty pan again and again** (M2): activity consistency lost in shot 3 | one direction of transfer; an empty pan stays empty; no idle reaching |
| **F3 mason, video path, first try** | 158 (V1, V2) | `cartoons/mason-cartoon-157.mp4` + 3 photographs + `prompts/158-video.txt` | the pan's inside read as **grey mortar** (V1); **an invented wide shot at 9.33 s** (V2); filler at the end; the wall taller than drawn | the pan stays a pan; no invented cut; the closing seconds hold the drawn action |
| **F4 mason, colour tags** | 159 (CF frames, CV video) | `cartoons/mason-cartoon-c-159-colour-tags.mp4` + 3 photographs + `prompts/159-video-colour-tags.txt` | frames: **a blue-purple tint leaked onto a brick**, an invented cut at 8.75 s, **the mason behind the wall in shot 2**; video: the mason **faced the camera and turned in a split second at 1–2 s**, **the mortar thrown at the foot of the wall** at 4 s (SK's findings) | facing held from the first frame; the trowel's mortar lands on the course; nothing leaks from the tags |
| **F5 mason, facing and contact** | 160 (DV, DVF) | `cartoons/mason-cartoon-d-160-facing-contact.mp4` + 3 photographs + `prompts/160-video-facing.txt` (DVF: + 12 dense frames) | DV was the cleanest of nine, but **the pile lost bricks between the walking shot and the close shot** (SK); DVF: **the pan emptied by 7 s, lifted at 7.5 s, set down, lifted again at 9.5 s**; the wall "under construction" at 7–8 s and the pan tilting in mid-air | the pile's size the same across the cut; the pan lifted once, at its second |
| **F6 mason, numbers and labels** | 162 (EVF) | `cartoons/mason-cartoon-e-162-numbers-labels.mp4` + 12 frames + 3 photographs + `prompts/162-video-numbers-labels.txt` | **the pan arrived empty at the cut to the close shot**; the six bricks never reached the pile: the state was lost at the cut | the pan's six bricks survive the cut and arrive on the pile |
| **F7 mason, no cut** | 163 (video), 164 (twenty frames) | `cartoons/mason-cartoon-f-163-no-cut-24fps.mp4` + 13 frames + 3 photographs + `prompts/163-video-no-cut.txt` | continuity held for the first time, but **two or three bricks still in the pan when it was lifted** (pace the model's own, about 1.2–1.5 s a pair against the drawn 0.9); 164: the push-in became a cut | the pan empty at the lift; the push-in stays a move |
| **F8 new bricks on an old heap** | 165 T2 | the T2 cartoon (regenerate with `165-assets/tests4.py`) + 3 photographs + `prompts/165-t2-new-on-old.txt` | tracking held (new stayed visibly new), but **the push-in became a cut at 5.6 s** and **the pan still held two or three new bricks at the lift** | the move stays a move; the pan empty |
| **F9 the pan's own count** | 165 T5 (t5f, t5v) | the T5 cartoon + the helper's photograph (+ the tools photograph, wrongly) + `prompts/165-t5-pan-count.txt` | **the pan started at about four, not six**; the running total loose; **a tripod drawn into the scene** from "the camera on a tripod"; **a trowel and a mortar board pulled in** by the tools photograph | the start count six; the total exact; no equipment from words; nothing from a photograph not in the shot (send only the helper's) |
| **F10 five barrels** | 166 (t6a; t6at text only) | the T6a cartoon + the worker's photograph + `prompts/166-t6a-barrels.txt` | **the plank did not empty while the row grew**: the total not conserved; the cartoon's cut at 3.5 s ignored; the same drift without the cartoon (text only) | the plank empties as the row grows to five |

What held on 1.1 and must not regress on 1.2 (the same cases): identity from two or three photographs in every run; the cartoon's framing, cuts and seconds on the video path (within 0.1 s); the fixed left-to-right order through three angles; one object passed hand to hand (165 T3); SK's staging of hands and one brick with the heap's edges out of frame (165 T4); the barrels' direction and no stacking (166).

**The rerun protocol per case**: the same files, the same prompt text, `model = gemini-omni-1.2-flash`, `response_format.duration` set to the cartoon's length (10 s; 6 s for T1, 8 s for T3), 720p, one run, judged on half-second strips at 480 px beside the cartoon and beside the 1.1 output. Then the same case with the agreed shortcut (design/167 D1) where the case was a count: wide to establish, tight on hands and one object, a face shot, the heap's edges out of frame.

## 5. Double-check of this note (SK: "go through everything once")

- The documents: all seventeen notes 153–169 listed in §1 with their assets; the cartoons, the outputs and the photographs copied into `176-assets` (29 MB); the prompts of every failing case copied under their note numbers. The T1–T6 cartoons were not kept as files; `165-assets/tests4.py` regenerates them.
- Omni 1.2's facts (§2) come from Google's own guide, changelog, models, pricing and rate-limit pages read on 6 Nov and from the API's model record (`thinking: true`, 131,072 input tokens, 65,536 output tokens, generateContent). Three limits that matter and were easy to miss: reference videos ≤3 s and only on new videos; first-and-last-frame runs capped at 10 s; the control tags deprecated.
- Seedance: via OpenRouter (§3); nothing read yet.
- The runner's three changes (§3): the model name, `duration`, `resolution`; the Files API upload and the polling are unchanged from 1.1.

## 6. The rerun regrouped by safe and not safe (SK, 6 Nov)

SK: "not safe" means the kinds of shot Omni 1.1 kept getting wrong, which we agreed to stop asking for; "safe" means the shortcut we moved to (design/167 sections 1, 2 and D1). The rerun tests both: whether 1.2 fixes the not-safe ones, and whether it keeps the safe ones. Same inputs as sent to 1.1, `gemini-omni-1.2-flash`, 720p, duration set to the cartoon's length. The pack (exact inputs in send order, 1.1's output beside them, every picture checked against the size in its 1.1 request) is outside git at `../omni-1.2-rerun-pack/`, 148 MB.

**Not safe** (design/167 section 2): ten runs.

| # | 1.1 run | Failure it tests | 167 item |
|---|---|---|---|
| N01 | 156 A1 | one tumbler instead of two after the cut; cut drift | 2.3, 1.3 |
| N02 | 158 V2 | empty seconds filled; an invented wide shot at 9.33 s; pan read as mortar | 2.5, 2.7 |
| N03 | 159 CV | the mason's split-second turn at 1-2 s; mortar thrown at the wall's foot | 1.2, 1.5 |
| N04 | 160 DV | the pile loses bricks across the cut | 2.1, 2.3 |
| N05 | 162 EVF | the pan arrives empty after the cut | 2.3 |
| N06 | 163 FVF | bricks still in the pan at the lift; the model's own pace | 2.1, 2.4 |
| N07 | 165 T2 | the push-in read as a cut; bricks left at the lift | 2.6, 2.1 |
| N08 | 165 T5 (video only) | the pan starts at four, not six; a tripod from words; tools from a photograph | 2.1, 3.5, 3.6 |
| N09 | 166 t6a | the plank does not empty as the row grows to five | 2.1 |
| N10 | 166 t6at (text only) | the same, without a cartoon: the model's own count | 2.2 |

**Safe** (design/167 section 1 and D1): four runs, as a regression check.

| # | 1.1 run | What held on 1.1 | 167 item |
|---|---|---|---|
| S1 | 165 T4 (t4v) | SK's staging: wide, then tight on hands and one object, nothing to count | 1.11 |
| S2 | 165 T3 | one brick passed hand to hand three times | 1.7 |
| S3 | 165 T1 | two bricks onto three, one at a time | 1.8 |
| S4 | 166 t6b | new blue drums beside old white ones keep the transfer legible | 1.9 |

**Left out**: the frames-only runs (157 M1/M2, 159 CF, 164 G20), since D9 retired that path; and the frames variants of N04 and N08 (160 DVF, 165 t5f), which only added dense frames (167 item 3.3). The two T4 tasks that ended "failed" with no reason are an API refusal, not an output mistake, and are not part of this test.

**Runner**: `176-assets/omni_test.py` gains `--model` and `--duration`, and follows redirects for a video delivered by link. Cost about 14 runs at roughly Rs 63 each (Rs 90 on 1.1, 30% lower), about Rs 880.

## Not covered

- No run yet; this note gathers and plans.
- Seedance via OpenRouter: model ids, prices and an API key still to come.
- Google's page was read whole except its code samples, which repeat the REST shape our runner already uses.
