# VideoWizard v2: defaults the process assumes

Read-only sweep, 2 Nov 2026, of the working tree at `C:\Coworkspace\Review Videobuilder Tool\videowizard-v2` (last commit c0af300). Paths are relative to that folder. Each file:line was checked against the file.
"Asked" means the operator is asked before the value applies. "Told" means an instruction or printed line tells the operator the value, but nobody asks. "Silent" means nothing tells the operator.
Pure technical fallbacks are left out: timeouts, retries, leases, workers, page sizes, caches, spool paths and limits on body size or zip size.

## Table, by stage in process order

| # | stage | what is assumed (plain English) | the default value | where (file:line) | operator asked / told / silent | what it affects |
|---|---|---|---|---|---|---|
| 1 | start | The procedure version is used when the operator does not name one | `'3'` | server/app/config.py:15; server/app/core.py:163 | silent | which instructions and which analysis contract the film gets |
| 2 | start | How drawn shots are made, when `--drawn` is left out | `'motion'` (HyperFrames) | server/app/main.py:116 | silent. `vw start` sends nothing when the flag is absent (plugin/scripts/vw.py:640), and the comment there still says "SVG scenes unless the operator chose motion". The start line prints the route afterwards (vw.py:656) | the look of every drawn or labelled graphic; fixed for the life of the film |
| 3 | start | A run row with no drawn route (an older film) is treated as | `'svg'` | server/app/visuals_stage.py:3857 | silent | the drawn route of older films |
| 4 | start | The film title is left empty | `''` | server/app/main.py:113 | silent | labels only |
| 5 | brief | The ending carries no sales call to action | no CTA | server/procedures/v3.json:43 | silent (an instruction to the AI) | the script's ending |
| 6 | brief | The film's frame shape and where it plays, when the operator does not say | 16:9, no destinations | server/procedures/v3.json:47, :48 | told. The brief's production block shows it, and the operator corrects it if needed | aspect ratio of pictures and takes; the editor's notes |
| 7 | brief | The frame shape anywhere code reads the brief and finds no frame | `'16:9'` | server/app/visuals_stage.py:3401; server/app/library.py:118, :264 | silent | picture size, take aspect, job form |
| 8 | analysis | The languages spoken in the field and the narration language, when the brief leaves them empty | `['en']` / `'en'` | server/app/analysis.py:78 | silent | how the analysis reads speech in the clips |
| 9 | analysis | The analysis listens to each clip's sound | `understand_audio = True`; `--understand-audio yes` | server/app/main.py:158; plugin/scripts/vw.py:2722; server/procedures/v3.json:196 ("without asking") | told, not asked | analysis quality and the paid request (sound attached) |
| 10 | analysis | The analysis model, and that it is started without asking | `gemini-3.8-flash`, thinking HIGH, media resolution HIGH | server/procedures/v3.json:186-189, :196 | told ("tell the operator, do not ask") | cost and quality of every clip's analysis |
| 11 | analysis | A clip longer than this many seconds goes agentic (dearer) | 15 s in v3. The code's fallback is 300 s | server/procedures/v3.json:191; server/app/analysis.py:34 | told in summary ("agentic for a clip over 15 seconds") | analysis cost per clip |
| 12 | analysis | Show the speaker on camera only when the brief says so AND camera sound is allowed. Otherwise the speaker is never shown | the derived mapping | server/app/analysis.py:40-44 | silent (it follows the operator's two answers) | whether A-roll of the speaker can appear |
| 13 | analysis | The project's timeline given to the analysis | 1920x1080, 25 fps, 16:9 | server/app/analysis.py:38 | silent | the framing the analysis judges crops against, even on a 9:16 film |
| 14 | voice | The speech model for a narration or audition from the CLI | `eleven_v4` | plugin/scripts/vw.py:2719 | told ("Present voices, reasons, model, settings", v3.json:152) | how the narration sounds |
| 15 | voice | The speech model and settings when a request carries none. Every audition and narration made on the voices page carries none | `eleven_v4`, stability 0.5, similarity 0.75 (v2: style 0, speed 1, speaker boost on) | server/app/jobs.py:34-35; server/app/elevenlabs.py:13-15; page calls at server/app/voices.py:478, :500 | silent on the page. Told in the CLI flow (v3.json:152, "start at 0.5 / 0.75") | the voice the film is narrated in |
| 16 | voice | The pause added after each paragraph when the target beat lengths are computed | 0.8 s | server/app/voices.py:120, :133 | silent | the pacing of the beats |
| 17 | options | When no scene split is approved, the server splits one scene per script paragraph, titled with its first six words | paragraph scenes | server/app/stage2/stage.py:121-123; server/app/stage2/narration.py:190-207 | silent on that path. The instruction proposes the same default to the operator (v3.json:220, asked) | scene boundaries, beats and timing of the cut |
| 18 | options / master | The film's timeline: size and frame rate | 1920x1080, 25 fps | server/app/stage2/stage.py:19 (used at :160, :459, :855, :919) | silent. The brief's frame is never read here, so a 9:16, 1:1 or 4:5 brief still gets a 16:9 master | the delivered film's shape and frame rate |
| 19 | options / master | After this many review rounds, the assistant suggests turning the failing scenes into blanks | 3 rounds | server/app/stage2/stage.py:300-307 | asked (the assistant proposes it and asks) | how much AI picture replaces footage |
| 20 | options / master | A blank (AI) passage is at least this long; a long one, and a long real shot, are flagged | 3 s min; 12 s long blank; 4 s long real shot | server/app/stage2/validator.py:10, :11, :19 | told (as check flags) | shot lengths and how much AI picture is used |
| 21 | visuals | The film's spending cap on visuals | ₹5,000 per film | server/app/config.py:50; server/app/visuals_stage.py:393, :396-402 | told when the cap is hit; raised only "on SK's word" | how many pictures and takes a film can have |
| 22 | visuals | The prices the cap is counted at: image, video per second, and the dollar rate | ₹4 per image, ₹8.9 per second, ₹88 per $; GPT Image $8/$30 per M tokens; Gemini $0.134 per picture ($0.24 at 4K) | server/app/config.py:23-26, :47-49; server/app/visuals_stage.py:344, :372, :375 | silent (the comment says they are the builder's estimates until SK sets them in .env) | the budget shown and when the cap stops work |
| 23 | visuals | The picture model within the film's chosen picture AI | GPT Image: `gpt-image-2.5-flare-2026-09-08` (generate), `…sunburst…` (edit). Gemini: `gemini-3-pro-image` | server/app/visuals_stage.py:32, :2869, :2872; server/app/config.py:22 | silent (the operator picks only openai or gemini) | look and cost of every picture |
| 24 | visuals | Picture quality, when the request does not name one | `'high'` | server/app/visuals_stage.py:2874 | silent | cost and look of GPT Image pictures |
| 25 | visuals | Picture size: Gemini tier, and the GPT size for the frame. A 1:1 or 4:5 brief falls back to 16:9 | Gemini `2K`; GPT 1536x864 (16:9) or 1088x1936 (9:16) | server/app/config.py:23; server/app/library.py:15, :262-264; server/app/visuals_stage.py:2867 | silent | resolution, cost, aspect of pictures |
| 26 | visuals | Number of candidates per picture | 1 | server/app/visuals_stage.py:2459 | silent (2 only when asked for) | cost and choice |
| 27 | visuals | The picture kind when `vw visuals image` gets no `--kind` | `'keyframe'` | plugin/scripts/vw.py:1784, :1803 | silent | which checks and prompt rules apply |
| 28 | visuals | The video generator for a take | Gemini Omni 1.1 Flash (the only one) | server/app/video_generators.py:10-12; server/app/visuals_stage.py:3343 | silent (no choice exists) | look and cost of every AI video take |
| 29 | visuals | A take's length: the shot rounded up to whole seconds, and at least the generator's minimum | ceil(shot), min 3 s | server/app/visuals_stage.py:3553 | silent (derived from the plan) | cost of each take |
| 30 | visuals | Take resolution | `'720p'` | server/app/visuals_stage.py:3589 | silent | sharpness of AI video in a 1080p film |
| 31 | visuals | Take aspect ratio. `PrepareTake` defaults to 16:9, `body_dict` dumps the defaults, and the plugin never sends the field. So the brief's frame fallback in `default_aspect` is never reached, and a 9:16 film gets 16:9 takes | `'16:9'` | server/app/main.py:373, :641-644, :1244; server/app/visuals_stage.py:3397-3401, :3588 | silent | shape of every AI video take |
| 32 | visuals | A take is made from the start image alone, unless the plan marks the end state exact | `end_state_exact = False` | server/app/visual_contract.py:293; server/procedures/v3.json:295 ("start-only is the default, with no warning") | silent | whether the take ends where the plan intends |
| 33 | visuals | A still or graphic moves unless the plan says otherwise | `motion = 'push_in'`, 5 % across the shot | server/app/visual_contract.py:302; server/app/stage2/render.py:139; server/app/visuals_stage.py:810, :4546, :4558 | silent (the planner may change it; `none` needs a reason) | the movement of every still and graphic |
| 34 | visuals | A shot under 4 s with no visible action is a moving still | moving still | server/procedures/v3.json:295 | silent (an instruction to the AI planner) | which route short shots take |
| 35 | visuals | No camera move named means a locked-off camera on a tripod | `camera_move = ''` → locked off | server/app/visual_contract.py:292; server/app/image_check.py:183 | silent | camera behaviour in AI takes |
| 36 | visuals | The join into a shot, when the planner chose none: an 8-frame dissolve where a graphic meets non-graphic, a cut everywhere else. Takes of one gap that share a picture dissolve over 6 frames | `transition_in = ''` → dissolve 8 f / cut; 6 f between takes | server/app/visual_contract.py:326; server/app/stage3/assembly.py:20-21, :30-35, :57-58 | silent | the transitions of the film |
| 37 | visuals | A graphic is a "diagram" when no kind is given | `graphic_kind = 'diagram'` | server/app/visual_contract.py:286; server/app/visuals_stage.py:2622 | silent | which checks a graphic gets (leader lines) |
| 38 | visuals | A section drawing is shown as a cutaway unless a view is given | `cutaway` | server/app/visual_contract.py:141, :775 | silent | the view of drawings |
| 39 | visuals | Composition rule given to the AI | rule of thirds; the centre only on purpose | server/app/visuals_stage.py:3464 | silent | framing of every AI picture |
| 40 | visuals | The look of a gap with no real footage beside it | muted and true to life | server/procedures/v3.json:280 | asked (proposed in the treatment, which the operator approves) | colour and contrast of AI gaps |
| 41 | visuals | The font of drawn shots when no brand font is supplied | Noto Sans | server/app/drawn.py:26-27; server/procedures/v3.json:295 | silent | the typography of graphics |
| 42 | visuals | The highlight colour in drawn scenes | `#FFC43D` | server/app/drawn.py:20, :128 | silent (not taken from the brand palette) | the look of graphics |
| 43 | visuals | The stock search source shown in the page box | `'pexels'` | server/app/visuals_stage.py:2038, :698 | silent (pre-filled; the operator can change the word) | where stock pictures come from |
| 44 | visuals | Reference rounds per film | one round | server/procedures/v3.json:290 | silent | cost, and how often references are revisited |
| 45 | visuals | How far a reused footage clip may be cropped, when the analysis gave no limit | 1.0 (no crop) | server/app/visuals_stage.py:129, :4260 | silent | framing of reused footage |
| 46 | visuals | Job-form fields the server fills when the client card or brief is empty | industry `other`; audience `general`; logo `none`; mandatory text `none`; variants 1; finish `final` | server/app/library.py:131, :135, :137, :141; FIELD-SOURCES.md:13-14, :17, :21-23, :30 | silent | the prompt sent to the picture AI |
| 47 | visuals / assembly | The film's frame rate when the session has none | 25 | server/app/visuals_stage.py:133, :182, :282, :796, :4199 | silent | timing of shots and take lengths |
| 48 | assembly | Each fill's start and end: offset 0; trim when the take is long enough, else hold the last frame | `offset 0`, `trim` / `hold_last` | server/app/stage3/assembly.py:193, :195; main.py:455-456; plugin/scripts/vw.py:2423, :2432 | told (`assembly prepare` lists each default, v3.json:308) | which frames of each take play |
| 49 | assembly | Stabilisation of a clip, when `--choice` is left out | `'leave'` | plugin/scripts/vw.py:2434 | silent | shaky footage left as is |
| 50 | assembly | A picture fills the frame by cropping up to this enlargement; past it, it keeps bars | 1.35× | server/app/stage2/render.py:151; server/app/stage3/assembly.py:19 | silent | framing, and whether bars appear |
| 51 | assembly | Narration loudness target, mix peak ceiling, camera-sound level and fades | −16 LUFS ±1.5; −3 dBTP; camera sound peaks at −27 dBFS; 4-frame fades | server/app/stage2/render.py:16-18, :137-138, :379-380 | silent | how the film sounds |
| 52 | delivery | Camera copies are left out of the download | left out | plugin/scripts/vw.py:2760; server/app/stage3/delivery.py:330; server/procedures/v3.json:307 | told | what the editor receives |

## Owner's decisions (cited to SK or a design note), so they are not taken for accidents

| # above | default | source in the code |
|---|---|---|
| 2 | Drawn route `motion` by default | main.py:116 "design/130 §12 (SK, 1 Nov 2026)". The plugin comment at vw.py:640 is stale (it still says SVG) |
| 21 | ₹5,000 cap per film | config.py:50 "SK, 21 Oct 2026, design/66" (memory notes "cap removed" on 28 Oct; the code still enforces it, so the live .env value may differ) |
| 22 | Gemini image prices | config.py:24-26 "design/120 … 28 Oct 2026". The INR prices are "the builder's estimates (21 Oct 2026)", not SK's figures (config.py:45-46) |
| 23 | Picture models; Gemini id | config.py:22 design/120 (SK's exact id goes in .env); visuals_stage.py:32 design/82 U4 |
| 28, 30 | Gemini Omni only; 720p | video_generators.py:12 and visuals_stage.py:3589 "design/124 A4 decision 5"; library.py:19 "(SK)" |
| 33 | 5 % push-in | render.py:139 "design/89 B2 (SK, 23 Oct)" |
| 36 | 8-frame graphic dissolve, cut elsewhere | assembly.py:21 "design/91 N16, SK 23 Oct" |
| 32 | Start image only | visuals_stage.py:3530 "design/66 C2, narrowed by design/112 S1"; design/124 decision 9 |
| 43 | Pexels | visuals_stage.py:2038 "design/121 change 5: SK chose it after the real test (29 Oct)" |
| 19 | Suggest blanks after 3 rounds | stage2/stage.py:304 "Agreed with SK on 16 Oct" |
| 7, 25 | Size follows the brief's frame | visuals_stage.py:2863, library.py:262 "design/71 P3" |
| 52 | No camera copies by default | vw.py:2760 "design/115" |
| 9, 10 | Analysis starts without asking, listens to sound | v3.json:196 (procedure text); main.py:157 "design/42 6.2" |
| 1 | Version 3 is the default | config.py:15; core.py:153 design/35 Old ways 1, 2 |

Not defaults, recorded for contrast: the picture AI (`image_provider`) is required and refused when missing (main.py:115; visuals_stage.py:347-352, "design/126 ST1: no default picture AI"). Camera audio is required at media or analysis (analysis_jobs.py:113-114). The film category is read at intake and confirmed in chat, "no default" (commit c0af300, design/137).

## Findings worth a look (silent and likely unintended)

1. **#31 Take aspect.** Every AI take is 16:9 even on a 9:16 brief. The Pydantic default in `PrepareTake` (main.py:373) is always dumped into the body, so the brief fallback in `default_aspect` is dead code.
2. **#18 and #13 Timeline.** The master, the analysis and the timeline are fixed at 1920x1080, 25 fps. None of them reads the brief's frame, so a 9:16, 1:1 or 4:5 film is cut at 16:9.
3. **#25 Picture size.** A 1:1 or 4:5 brief silently gets 16:9 pictures, because `SIZES` holds only 16:9 and 9:16.
4. **#15 Voice model on the page.** Narrations and auditions made on the voices page always use Eleven v4 at 0.5 / 0.75. The page never offers a model or settings.
5. **#2 Drawn route.** The plugin's comment and the server's default disagree; the server's `motion` wins.
6. **#17 Scene split.** Without an approved scene split, the cut uses one scene per paragraph without telling the operator.
7. **#42 Highlight colour.** The highlight is a fixed yellow and is not taken from the client's palette.
