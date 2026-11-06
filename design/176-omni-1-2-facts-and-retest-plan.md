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

Seedance 2.0 and 2.0 Flash: not reachable from here until SK names the service and the exact model names; they are not Gemini models.

## Not covered

- No run yet; this note gathers and plans.
- Google's page was read whole except its code samples, which repeat the REST shape our runner already uses.
