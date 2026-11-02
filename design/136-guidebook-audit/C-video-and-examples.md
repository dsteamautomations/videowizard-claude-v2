# Audit C: video-clip, camera-lighting-vocabulary, still-to-motion-pipeline, 05-information

Library: `videowizard-v2/server/library/vwlib-2026-10-29-3d60877d3d23/library/`. Override rows are cited by the VW-MAP "Where VideoWizard overrides the library" row's "Library says" text (short names below) or "Fixed lines" item number.

Override short names used: **model-per-film** (picture AI and settings are the server's), **Omni-only** (Gemini Omni only, 3–10 s), **one-request-shape** (Omni's shape, no Seedance template or `@Image` roles), **brief-only-motion** (no Camera line, Audio line, one-take line, length, picture tags in the brief), **no-audio-no-cuts** (no sound, dialogue, music, cuts, transitions), **steady-camera** (locked off unless `camera_move` names one move), **start+end-image** (start image every shot, end image only as a region edit), **person-from-words**, **exact_text** (words to be read only in `exact_text`, quote nothing else), **drawn-route** (numbers/charts take the drawn route), **landmark-place** ("centre" refused), **film-frame** (size from `production.format.frame`), **one-generation** (no draft-then-final), **storyboard/plan** (the plan carries shot, seconds, camera).

Word counts are body words under each heading (headings themselves excluded), counted with awk.

---

## 1. `playbooks/video-clip.md` (in-house, "Version 0.1 ... draft, untested")

| file § heading | words | tag | evidence (≤ 20 words) | action | generic rewrite |
|---|---|---|---|---|---|
| (preamble under title) | 63 | PROVENANCE | "Version 0.1, written 2026-10-19. Status: draft, untested on a real job." | Remove; keep only "read with the Omni fact sheet" as a pointer if needed. | — |
| §1 What this playbook covers | 31 | OVERRIDDEN | "`clip-from-frame`, `clip-from-text`, `clip-edit`, `clip-extend`" | VW-MAP routes only `clip-from-frame` (take); start+end-image means no text-only clip; edit/extend are not VW tasks. Reduce to one line: clip from an approved start image; next to footage see gap-fill. | — |
| §2 Decisions already taken | 412 | OVERRIDDEN | "Seedance 2.5 for a single take over 10 seconds"; "Omni: draft at 360p"; "Audio: Described or switched off" | Rows Which model (Omni-only), Draft and final (one-generation), Settings vs words + One take (brief-only-motion), Audio (no-audio-no-cuts), Real people (person-from-words) are overridden. Keep only "Frame first" and "Motion hold is checked" (GENERAL). Audio row: OVERRIDDEN today; keep filed under advertisement-product / social-ugc / narrative-story if the system ever allows sound. | A clip showing a real product, place or recurring person starts from an approved frame, never from text. After animation, check label, traits, palette and text against that frame; a broken shot is regenerated from the frame, not patched. |
| §3 Before writing | 87 | OVERRIDDEN | "shot number, seconds, action, camera move, audio reference, transition" | storyboard/plan supplies shot, seconds, camera; audio and transition never exist (no-audio-no-cuts); source-clip edits not a VW task. Remove. | — |
| §4 The motion brief | 140 | OVERRIDDEN | "1. Camera: one move ... 4. Audio: room tone ... 6. The single-scene line, and the length" | Items 1, 4, 6 and the "sound anchor" detail are exactly what brief-only-motion forbids. Items 2, 3, 5 and the "Cinematic ... do not render" line are the heart of a VW brief: convert. | The start image already holds identity, composition and text; the brief says only what moves. Name the subject's one physical micro-action and its visible consequence, and one or two surrounding motions (steam, fabric, leaves). Bodies and consequences render; "cinematic", "dynamic" and named emotions do not. |
| §5 Writing the prompt | 327 | OVERRIDDEN | "<FIRST_FRAME> ... Camera: {one move} ... Audio: ... In a single unbroken scene, no scene cuts. {n}s." | Omni template = server's Fixed lines 1, 8, 11, 13; Seedance template = one-request-shape; quoted label = exact_text. Keep the rules "consequences" and "no contradictions"; "models weight the first third" is an old-model claim, drop it. | Lead with the subject and its action. Describe consequences, not just actions: tyres kick up water; the lid actually unscrews. Never pair contradictions ("still pond" with "flowing water"). Do not re-describe what the start image already shows. |
| §6 Camera and light words both models understand | 91 | REDUNDANT | "handheld micro-shake, whip pan ... Omni's own extras: 'oner', ... 'webcam style'" | Subset of camera-lighting-vocabulary §1, §2, §4–§6 and §10 (agrees); its extras (handheld, smartphone zoom, webcam) DISAGREE with steady-camera. Remove; point to the vocabulary file for `camera_move` and light. | — |
| §7 Task notes | 292 | OVERRIDDEN | "clip-edit ... not in the EEA, Switzerland or the UK"; "UGC style ... handheld, vertical ... dialogue" | clip-from-text, edit, extend not VW tasks (start+end-image); UGC handheld = steady-camera; Dialogue = no-audio-no-cuts. UGC and Dialogue: OVERRIDDEN today; keep filed under social-ugc / narrative-story / advertisement-product if sound and handheld are ever allowed. Keep the product line as CATEGORY:advertisement-product. | For a product, motion belongs to hands or surroundings; the product never deforms and its label stays sharp and readable throughout. |
| §8 Checklist lines for clips | 122 | GENERAL | "The one camera move happened and nothing else. must." | Keep. Trim the audio line to "no sound, captions or dialogue appeared"; drop "aspect and resolution as set" (server's). | — |
| §9 What goes wrong on clips, and the fix | 251 | OVERRIDDEN | "Omni `delivery: \"uri\"` above 720p"; "Seedance poll every 30 seconds"; "References had no effect on Seedance" | Most rows are server API handling, Seedance (Omni-only), edits (not VW), faces (person-from-words), or fixes the server already writes (single-scene, audio, length). Keep two rows as GENERAL. | Label softens in motion: slow the move, or regenerate from the frame. Motion ignored in a short take: lengthen toward 5 s or more and give the action a speed. |
| §10 Evidence | 18 | PROVENANCE | "None yet. Core status needs motion hold recorded" | Remove. | — |
| §11 Built from | 27 | PROVENANCE | "`video/models/gemini-omni-1-1/FACT-SHEET.md`; `video/universal-rules/square-zero-labs.md`" | Remove (keep in a sources file). | — |

**Totals video-clip.md:** 1,861 body words (1,926 with headings); kept as-is 122 (GENERAL §8); to remove or convert 1,739. After conversion the rewrites above keep about 190 words of rule.

---

## 2. `video/craft/camera-lighting-vocabulary.md` (copied from github.com/smixs/visual-skills, CC BY 4.0)

| file § heading | words | tag | evidence (≤ 20 words) | action | generic rewrite |
|---|---|---|---|---|---|
| (provenance block + director-name warning) | 104 | PROVENANCE | "Source repository: https://github.com/smixs/visual-skills ... Commit: `92be33a5...`" | Move to sources file. The warning "replace or describe the aesthetic before client use" becomes moot once §7 is converted. | — |
| # Camera, lighting, color, sound vocabulary (intro) | 18 | GENERAL | "\"Cinematic\" is not a direction. \"35mm, slow push-in, warm window key from frame-left\" is." | Keep. | — |
| Contents | 34 | PROVENANCE | "1. Framing 2. Camera movement 3. Lens language ..." | Navigation only; remove. | — |
| §1 Framing | 46 | GENERAL | "extreme wide shot ... over-the-shoulder ... locked-off frame" | Keep; usable for start images and the plan. | — |
| §2 Camera movement | 129 | GENERAL | "Pick one dominant move per 5-second shot. Layer one subtle secondary move at most." | Keep the list for choosing `camera_move` and the "name alone is not a direction" rule. Drop "handheld micro-shake" (steady-camera), "one-take shot" (Fixed line 11), and the "secondary move" clause (server line: "nothing else about the frame changes"). | — |
| §3 Lens language | 46 | GENERAL | "35mm. Natural documentary. 50mm. Intimate, human perspective." | Keep (start-image writing). | — |
| §4 Light sources | 69 | GENERAL | "cold refrigerator light, harsh overhead kitchen LED ... under-counter kitchen LED" | Keep; list leans on the source repo's kitchen/thriller scenes (3 kitchen items, police strobe). Add daylight, office, classroom, studio sources when next edited. | — |
| §5 Light direction | 34 | GENERAL | "window key light, motivated practical (the light source is visible in frame)" | Keep. | — |
| §6 Light quality | 50 | GENERAL | "hard shadow, soft diffused ... teal shadows, clean commercial lighting" | Keep; overlaps §7's palette terms slightly (agree). | — |
| §7 Color discipline | 118 | SOURCE-SPECIFIC | "Fincher cold ... Deakins natural ... Wong Kar-wai ... Glazer neon ... Safdie chaotic" | Convert: keep the concrete-colour rule and the ban rule; replace director-named palettes with descriptions (the provenance line itself flags them). | Name the palette in concrete colours, never "cinematic colours": "cold blue-grey shadows, desaturated skin, black negative space". A banned colour stays banned in every take of the sequence. Describe a look by its colours and light, never by a director's name. |
| §8 Sound categories | 126 | OVERRIDDEN | "Even if the model does not generate audio, sound description helps structure rhythm." | no-audio-no-cuts and Omni-only (Veo, Seedance, Kling lines). Writing sound into a VW brief contradicts Fixed line 11. OVERRIDDEN today; keep the three word lists filed under advertisement-product / narrative-story / social-ugc if the system ever allows sound; drop the per-model lines regardless. | — |
| §9 Blocking language | 86 | GENERAL | "Who moves. Where they start. Where they end. What object they touch. What they look at." | Keep. In VW "where they start" is the start image, and gaze/heading may already come from the plan (Fixed line 9), so the brief names the end position and contact. | — |
| §10 Translating uncommon terms | 108 | GENERAL | "keep the term **and** translate it into observable change, or the model guesses" | Keep; in VW the translation belongs in the plan's `camera_move` for camera terms. video-clip §6 repeats the rule (agrees). | — |
| §11 Transition vocabulary | 202 | OVERRIDDEN | "Named transitions every current model understands ... Seedance 2.5 honors them explicitly" | no-audio-no-cuts (named transitions) and Omni-only. VW cuts in the edit. Remove; if multi-shot generation is ever allowed, file under advertisement-product / social-ugc. | — |

**Totals camera-lighting-vocabulary.md:** 1,170 body words (1,222 with headings); kept 586; to remove or convert 584 (§7 conversion keeps about 50).

---

## 3. `video/still-to-motion-pipeline.md` (copied from github.com/coreyhaines31/marketingskills, MIT; ad-creative skill)

| file § heading | words | tag | evidence (≤ 20 words) | action | generic rewrite |
|---|---|---|---|---|---|
| (provenance block) | 75 | PROVENANCE | "Source repository: https://github.com/coreyhaines31/marketingskills ... treat them as unverified and dated." | Move to sources file. | — |
| # Motion-Style Video Ads (Faceless, Fully Generated) | 94 | SOURCE-SPECIFIC | "Cost per finished video is roughly $3–6 in API calls; wall-clock ~15 minutes." | Convert: drop ad framing, cost, TTS/captions pipeline; keep the principle (VW-MAP routes faceless explainers here). | For a faceless explainer the still carries the idea: one literal, slightly surreal visual per beat. Motion only makes it breathe; never ask the take to tell the story. |
| When to use | 52 | CATEGORY: documentary-explainer, advertisement-product, social-ugc | "Concept/explainer ads ... Top-of-funnel social video (9:16 Reels/Shorts/TikTok ...)" | Keep, filed there; strip funnel/platform jargon. "NOT for ... a real product shot as evidence" agrees with video-clip §2 Frame first. | — |
| Pipeline (provider-agnostic) | 217 | OVERRIDDEN | "VO + captions: one continuous TTS take ... loudness-normalize to `I=-16:TP=-1.5:LRA=11`"; provider table "Veo 3.1 ... Seedance 2.0" | Narration and assembly are VW's own (no-audio-no-cuts; Fixed line 11 "No captions"); provider table = model-per-film + Omni-only; per-placement export = film-frame. Keep step 2–3 essence. | One still per beat; the series takes its look from the approved style picture. In each take, motion belongs to the objects already in the frame and the composition never changes. |
| The style library | 26 | SOURCE-SPECIFIC | "keep ONE style per campaign so the account builds a recognizable visual identity" | Convert to "One style per film" (already what the approved style picture enforces: REDUNDANT with VW-MAP sheet row, agrees). | One style per film, so every beat reads as one series. |
| A. Screen-print collage | 97 | SOURCE-SPECIFIC | "(editorial, \"In a Nutshell\" docu energy)"; "No gradients, no glow, no 3D, no photorealism, no extra text." | Named outside channel as anchor; quoted `"<LABEL>"` breaks exact_text; "near the bottom" breaks landmark-place; 5-item No-list is an old habit (and the file's own gotchas say negatives backfire). Convert. | Flat screen-print collage poster: one saturated {colour} ground, newsprint grain; a grayscale halftone cutout of {subject doing the concept} as a die-cut paper sticker with torn edges and soft shadow; two to four flat accent shapes; a torn-paper label band; matte risograph, limited palette, flat print only. |
| B. Flat vector explainer | 69 | PICTURE-KIND | "Flat vector explainer illustration ... solid `<BRAND COLOR>` background ... No outlines, no 3D, no photorealism" | Keep as an explainer-still style; on conversion move the label to exact_text with a landmark place, and cut the No-list to a positive "completely flat 2D". | — |
| C. Papercraft diorama | 66 | PICTURE-KIND | "every element hand-cut from colored construction paper with visible paper thickness" | Keep; same label/No-list conversion as B. | — |
| D. Pop-art comic | 57 | PICTURE-KIND | "Ben-Day halftone dots shading, flat process colors ... 1960s printed comic aesthetic" | Keep; same conversion. | — |
| E. Claymation | 60 | PICTURE-KIND | "visible fingerprints and clay texture ... warm soft studio lighting like a stop-motion film set" | Keep; same conversion. | — |
| Brand-flexible styles (token-driven) | 135 | CATEGORY: advertisement-product, training-education | "resolve these from the brand's guidelines: FIELD ... INK ... ACCENT ... TYPE FEEL" | Keep filed there (brand-token films). "Keep the accent genuinely scarce — one element per frame" is GENERAL design advice; the "gradients only on borders" example is one brand's constraint, drop it. | — |
| F. Monoline editorial | 94 | PICTURE-KIND | "drawn entirely in elegant thin single-weight `<INK>` lines ... the style of a premium tech company blog" | Keep; drop "premium tech company blog" anchor, quoted label, 6-item No-list. | — |
| G. Swiss typographic | 98 | PICTURE-KIND | "the words \"`<LABEL>`\" set enormous ... filling the upper two thirds" | Keep for title cards; label to exact_text; "upper two thirds"/"lower third" fall under landmark-place. | — |
| H. Wireglow | 86 | PICTURE-KIND | "(dark keynote — dev-tool / dark-mode brands) ... near-black `<FIELD>` background with subtle film grain" | Keep; rename without "dev-tool" (it fits any dark-ground film); same conversion. | — |
| I. Duotone screenprint (+ motion notes for the tier) | 145 | PICTURE-KIND | "two-color screenprint — `<INK>` for the shadows and `<ACCENT>` for the highlights"; "I as grain shimmer + slow push" | Keep the style; the motion notes duplicate "Motion prompt formula" (agree) and "slow push" is a camera move the server writes (brief-only-motion), move it to `camera_move`. | — |
| Motion prompt formula | 90 | PICTURE-KIND | "Every element that is visible now is the only thing that ever appears; the composition stays exactly as it is." | Keep (animated poster stills). Drop "gentle push-in" (camera = plan/server) and "No camera whip, no scene change ... no added text" (Fixed lines 8, 11 already say it). | — |
| Hard-earned gotchas | 178 | GENERAL | "negative prompts make it worse (\"no hands\" is an attention trap). Never mention hands" | Keep hands, final-2-seconds QC, one dominant motion. Captions/TTS bullets OVERRIDDEN (VW narration, no captions). "Ad-specific" bullet: CATEGORY advertisement-product / social-ugc (sound-off hook); per-aspect export is film-frame. | — |
| Compliance | 31 | CATEGORY: advertisement-product, social-ugc | "check platform AI-content disclosure requirements (Meta and TikTok label AI-generated media)" | Keep filed there; "Don't fabricate statistics or testimonials" is GENERAL but concerns narration, not the picture brief. | — |

**Totals still-to-motion-pipeline.md:** 1,670 body words (1,787 with headings); kept 1,161 (but every PICTURE-KIND formula still needs the quoted-label, place and No-list conversion); to remove or convert 509.

---

## 4. `prompts/05-information.md` (no provenance line in the file; MANIFEST says snapshot of `prompts/05-information.md`; "Images 2.5" gallery style)

| file § heading | words | tag | evidence (≤ 20 words) | action | generic rewrite |
|---|---|---|---|---|---|
| # Infographics, education & presentations | 72 | OVERRIDDEN | "Images 2.5 workflow focus ... Requested ratios are creative targets; verify actual output dimensions." | model-per-film and film-frame: the server picks model and size. Remove; add a provenance line (missing). | — |
| P025 · Three-stage rain garden explainer (header block) | 72 | GENERAL | "Verify labels, counts, directional arrows and numerical relationships independently of visual polish." | Keep the production check once for the whole file; drop "Target: 3:2" (film-frame) and the test-note "Observed review". | — |
| P025 › Prompt | 90 | PICTURE-KIND | "Asset: ... Target aspect ratio: 3:2. Mode: generate. ... Exact panel labels: \"COLLECT\", \"SLOW\", \"SOAK\"." | Keep as a labelled-diagram example (any category). Drop the Asset/Target/Mode line (settings in prompt: model-per-film); move quoted labels to `exact_text` (exact_text). | — |
| P025 › Next edit | 25 | GENERAL | "Increase only the arrow contrast; keep all stages and wording." | Keep; matches VW one change per edit. | — |
| P026 · Coffee tasting wheel for beginners (header) | 71 | REDUNDANT | "Best for: Teaching cards ... Production check: Verify labels, counts, directional arrows" | Identical boilerplate to P025 header (agrees). Remove. | — |
| P026 › Prompt | 87 | PICTURE-KIND | "three equal outer sectors labeled \"FRUITY\", \"NUTTY\", \"COCOA\", surrounding the central title" | Keep (sector diagram); same Asset-line and exact_text conversion. | — |
| P026 › Next edit | 20 | GENERAL | "Change only the fruity-sector accent to muted pink." | Keep. | — |
| P027 · Transparent demo-data bar chart (header) | 76 | REDUNDANT | "Bars visually approximate the 20:30:40 relationship; use a charting tool for exact quantitative publication." | Boilerplate as P025; its own review admits the drawn route is needed. Remove. | — |
| P027 › Prompt | 102 | OVERRIDDEN | "a three-bar chart. Exact fictional values ... heights proportional to 20:30:40" | drawn-route: an AI graphic never carries a chart or figure (VW-MAP names P027). Remove; reading it invites the mistake. | — |
| P027 › Next edit | 26 | OVERRIDDEN | "Highlight only June in orange, preserving values and bar geometry." | Goes with P027 (drawn-route). Remove. | — |
| P028 · Fictional neighborhood walking map (header) | 82 | REDUNDANT | "Production check: Verify labels, counts, directional arrows and numerical relationships" | Boilerplate as P025. Remove; keep the useful observation "dotted path interrupted" only as a review hint if wanted. | — |
| P028 › Prompt | 90 | PICTURE-KIND | "a square park in the center, library north, café east and station south" | Keep (illustrated map); "in the center" alone is refused by landmark-place: anchor the park by a landmark. Same Asset-line and exact_text conversion. | — |
| P028 › Next edit | 24 | GENERAL | "Change only the route color to dark blue without moving its path." | Keep. | — |
| P029 · Plant life-cycle classroom card (header) | 77 | REDUNDANT | "Direction arrows connect each row but omit the wrap between rows" | Boilerplate as P025; the wrap failure is already fixed inside the P029 prompt. Remove. | — |
| P029 › Prompt | 106 | PICTURE-KIND | "Make the reading order explicit with three arrows: top-left to top-right, top-right to bottom-left" | Keep (staged grid; the explicit arrow order is a strong pattern). Same conversion. | — |
| P029 › Next edit | 28 | GENERAL | "Enlarge only the root illustration in the second panel while preserving labels." | Keep. | — |
| P030 · Workshop process slide (header) | 68 | REDUNDANT | "Four equal cards, labeled stages and three connecting arrows form a clear sequence." | Boilerplate as P025. Remove. | — |
| P030 › Prompt | 85 | PICTURE-KIND | "Four horizontal cards read \"SKETCH\", \"PROTOTYPE\", \"TEST\", \"REFINE\", each with one original simple illustration" | Keep (process slide). Same conversion. The closing line "Render only explicitly requested image text..." repeats in all six prompts: keep once. | — |
| P030 › Next edit | 23 | GENERAL | "Change only the final card accent to deep green." | Keep. | — |

**Totals 05-information.md:** 1,224 body words (1,301 with headings); kept 650 (all five kept prompts still need the Asset-line drop and quotes-to-`exact_text` move); to remove or convert 574.

---

## Totals across the four files

| File | Body words | Kept | Remove or convert |
|---|---|---|---|
| playbooks/video-clip.md | 1,861 | 122 | 1,739 |
| video/craft/camera-lighting-vocabulary.md | 1,170 | 586 | 584 |
| video/still-to-motion-pipeline.md | 1,670 | 1,161 | 509 |
| prompts/05-information.md | 1,224 | 650 | 574 |
| **All** | **5,925** | **2,519** | **3,406** |

---

## Contradictions between files (and with VideoWizard)

1. **Negative wording.** still-to-motion "Hard-earned gotchas" says negative prompts make it worse ("no hands" is an attention trap); yet its own nine style formulas each end in a 4–7 item "No ..." list, video-clip §9 fixes unwanted audio by forbidding it ("Pure video, no subtitles, no background music"), and camera-lighting §7 models bans ("no warm yellow tones"). Pick one rule: describe what is there; ban only what a test shows appears.
2. **Camera in the brief.** video-clip §4/§5 put "Camera: {one move}" in the brief; still-to-motion's motion formula adds "gentle push-in" and tier notes "slow push"; camera-lighting §2 allows "one subtle secondary move" and lists handheld micro-shake; video-clip §6 offers "handheld", "webcam style". VW: the server writes the Camera line from `camera_move`, steady unless one move is named, "nothing else about the frame changes".
3. **Sound.** camera-lighting §8 says sound description helps "even if the model does not generate audio"; video-clip §4 requires an Audio line and a "sound anchor" in every shot. VW sends no sound and writes "No dialogue. No music." itself. Both files invite the mistake.
4. **Quoted words in the picture.** video-clip §5 (`label "{text}"`), every still-to-motion formula (`"<LABEL>"`), and every 05-information prompt quote the words to render. VW: words go only in `exact_text`, quote nothing else.
5. **Place words.** 05-information P028 "park in the center" and still-to-motion "near the bottom", "upper two thirds", "lower third" vs VW landmark-place ("centre" alone is refused by `check_prompt`).
6. **Beat length.** video-clip §2 "one beat per 3 to 5 seconds" vs video-clip §9 "lengthen to 5 seconds or more" when motion is ignored vs still-to-motion "5–8 s per beat". VW allows 3–10 s; the files disagree with each other on the short end.
7. **Text-only clips.** video-clip §2/§7 allow text-only clips for "faceless explainers" and §5 sends still-to-motion formulas for a "text-only clip", but still-to-motion is a still-first pipeline (never text-only). VW: a start image for every shot.
8. **Charts.** 05-information P027 teaches an AI bar chart; VW drawn-route forbids it, and P027's own review says to use a charting tool.
9. **Series consistency.** still-to-motion: pass beat 1 as the reference for later beats; video-clip: send the kit and repeat five traits. VW: the approved style picture sets the look and people come from word-built sheets (person-from-words). Agree in intent, disagree in mechanism.
10. **Aspect.** 05-information targets 3:2 / 1:1 / 4:5 per prompt and still-to-motion exports 9:16 + 4:5 + 1:1 by regenerating stills; VW uses one film frame (default 16:9).
11. **Agreement worth noting.** video-clip §4 "named emotions do not render" and camera-lighting §9 "what their body reveals emotionally" agree: show emotion through posture and action (the §9 example "shoulders collapsed" does this). camera-lighting §10 and video-clip §6 agree on "keep the rare term and translate it".
