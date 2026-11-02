# Audit D: GPT Image fact sheet, Omni fact sheet, deterministic checks, compliance checklist

Bundle: `videowizard-v2/server/library/vwlib-2026-10-29-3d60877d3d23/`. Read-only audit, 2 Nov 2026. Word counts are `wc -w` per heading block (heading line to the next heading of any level). Override rows are cited by their "Library says" wording in VW-MAP "Where VideoWizard overrides the library" (OV-1 = first row, ... OV-23 = last row, in table order):

OV-1 picture model per job · OV-2 quality · OV-3 choice of video model · OV-4 each video model's prompt shape · OV-5 clip prompt carries camera/audio/single-scene/length · OV-6 audio, dialogue, several shots, transitions, timed cuts · OV-7 handheld camera · OV-8 first and last frame for every move · OV-9 person reference picture · OV-10 nine-photo series/3:4/fixed views · OV-11 one change per turn · OV-12 exact words in quotes · OV-13 charts · OV-14 "centre" as a place · OV-15 model name in prompt · OV-16 storyboards · OV-17 draft at low size · OV-18 placement from channel sheet · OV-19 logo reserve · OV-20 checked_by / second person · OV-21 C09 · OV-22 C03 and C18 · OV-23 application writes feedback record.

---

## 1. `library/models/gpt-image/FACT-SHEET.md` (2,820 words)

| file § heading | words | tag | evidence (quote ≤ 20 words) | action | generic rewrite |
| --- | --- | --- | --- | --- | --- |
| Title + status + page list | 90 | PROVENANCE | "This is the most preferred image model family. Decision in `models/CHOSEN-MODELS.md`." | Keep one line: source pages + check date. Drop the model-preference line (OV-1: server picks). | — |
| Part A heading | 9 | SERVER-ONLY | "The API: what the application sends" | Remove the whole Part A from the run sheet except the three lines kept below; move to a server doc. | — |
| A1 Models | 132 | SERVER-ONLY | "`gpt-image-2.5-flare` ... Drafts, bulk variants, everyday posts." | Remove. Also OV-2 ("Flare for drafts") and OV-17 forbid drafts. "everyday posts" is social-ad wording. | — |
| A2 Two ways to call | 157 | SERVER-ONLY | "Decision for this library: Image API. We want the prompt sent exactly as written" | Remove; keep one fact as a line under Part B: the picture prompt reaches the model unrewritten. | — |
| A3 Settings on every call | 338 | SERVER-ONLY | "`quality` ... Send an explicit value." / "`moderation` ... Keep `auto` for client work." | Remove. OV-1 (size, background) and OV-2 (quality) already make these the server's. | — |
| A4 Size rules | 137 | SERVER-ONLY | "A 4:1 banner is not possible here; that is a Nano Banana job." / "9:16 story 1080x1920 fails" | Remove. Contradicts OV-1 (film's picture AI makes every picture) and OV-18 (size from the frame); "feed/story/hero" placements are ad-channel specific. | — |
| A5 Pictures sent in with an edit | 107 | SERVER-ONLY | "Order matters. The prompt says "Image 1", "Image 2"; the application must send them in that order." | Remove limits, file sizes, mask; keep the order line (the prompt names pictures by number). | — |
| A6 Price | 140 | SERVER-ONLY | "store `usage.output_tokens` and `usage.input_tokens` on every record" | Remove. | — |
| A7 Limits, waits, errors | 135 | SERVER-ONLY | "A complex prompt can take "up to 2 minutes". Design the application to wait" | Remove waits, rate limits, verification. Keep one line: a blocked prompt is rewritten, never resent unchanged. | — |
| Part B heading | 8 | GENERAL | "How this model reads words" | Keep. | — |
| B1 Prompt shape | 167 | OVERRIDDEN | "Exact text: "{string 1}" {position, size, style}; "{string 2}" ... No other text." | Convert. Quoted text in the prompt breaks OV-12; "Target aspect ratio" and "Mode" are server fields (OV-1, FIELD-SOURCES `mode`). The answer form is the real shape. | For complex pictures write labelled parts: Scene (place, time, ground), Subject (the one thing), Details (materials, light direction and softness, camera feel, palette, layout), References (Image N = its role), Constraints (what must hold, what must not appear). Words to be read go only in `exact_text`. |
| B2 Words that hurt | 154 | GENERAL | "Praise words add nothing ... "masterpiece", "best quality", "8K", "ultra-detailed"" | Keep: this is the anti-outdated rule (quality tags). Swap the "like an Apple ad" example for a neutral one. REDUNDANT with `00-method/de-slop.md` and deterministic-checks §1 (they AGREE). | — |
| B3 Words that help | 119 | GENERAL | "Camera terms work as cues for the look, not as physics: "50mm feel", "eye level"" | Keep. | — |
| B4 Exact text in the image | 135 | OVERRIDDEN | "Put the words in quotes." / "use `medium` or `high` quality at least" / "Render the tagline exactly once" | Convert: quotes break OV-12, quality advice breaks OV-2; "tagline", "card text" are ad wording. | Words to be read go in `exact_text`, each with its place and size; keep each string short; say how many times it appears; spell an unusual word out only if it came back wrong; no other text. Read every character afterwards and check translations for leftover words. |
| B5 Edits: keeping the rest unchanged | 206 | GENERAL | "Say "change only X", then list what to preserve by name: identity, geometry, layout, lighting, labels." | Keep. Consistent with OV-11. Product line is general enough (any film with an object). | — |
| B6 Several pictures in one call | 122 | GENERAL | "Number each input and give it a purpose: subject, style, clothing, background." | Keep, trim: drop the mask line (SERVER-ONLY) and the jacket/golden-hour fashion example (third-party house form). Note OV-9: a person's picture is never an input. | — |
| B7 Series and characters | 62 | GENERAL | "Make one reference image, then pass it into every later call and repeat the defining details" | Keep. Matches the sheet-first flow; the reference is the approved generated sheet, never footage (OV-9). | — |
| B8 Transparent cutouts | 60 | OVERRIDDEN | "set `background` to `transparent` with `png` or `webp`. Both." | Remove: OV-1 gives the background to the server; VW sheets are "alone on plain ground" (OV-10). | — |
| B9 Quality setting method | 129 | OVERRIDDEN | "Start at an explicit `medium`. If the result falls short, step up one." | Remove (OV-2: always high, never pass `--quality`). | — |
| B10 Failure habits and the fix | 279 | REDUNDANT | "Restate the full preserve list each turn" / "raise quality one step" / "add a mask on Image 1" | Cut to the rows not already in B4-B8: historical staging, diagram labels, candid look, character drift. Text, edit, transparency rows repeat B4/B5/B8 (AGREE) but carry quality and mask fixes that are OVERRIDDEN/SERVER-ONLY. | — |
| B11 Not to be asked for as final | 43 | REDUNDANT | "Final typography, legal text, real data charts, shippable app screens, the client's real logo." | Remove: RULEBOOK §"The client's logo..." (line 31) says the same (AGREE); charts also OV-13. | — |
| Part C Evidence from our jobs | 91 | SERVER-ONLY | "Empty. Fill from `feedback/records/` once jobs run." | Remove from the run sheet (OV-23: server writes feedback). | — |

**Totals, GPT Image sheet:** 2,820 words. Kept for the operator's AI ≈ 840 (Part B core, rewritten B1/B4, two one-line facts from A2/A5/A7). To remove, convert or leave to the server ≈ 1,980 (all Part A, B8, B9, B11, Part C, half of B10).

---

## 2. `library/video/models/gemini-omni-1-1/FACT-SHEET.md` (4,238 words)

Context: OV-5 says the motion brief is "only what the subjects and the surroundings do"; the server writes the tags, Camera, ambient, continuity, single-scene, no-sound, identity and length lines. No VideoWizard step edits or extends a clip (VW-MAP lists only `prepare-take`/`take`, and OV-3 splits long passages into new shots).

| file § heading | words | tag | evidence (quote ≤ 20 words) | action | generic rewrite |
| --- | --- | --- | --- | --- | --- |
| Title + status + page list | 183 | PROVENANCE | "Every line is marked. `[verified: page]` means the words were read on that Google page" | Keep one line (source, date). 16 URLs go to the shelf copy. | — |
| Part A heading | 9 | SERVER-ONLY | "The API: what the application sends" | Remove Part A from the run sheet except lines kept below. | — |
| A1 Model ids and status | 175 | SERVER-ONLY | "Veo 3.1 Lite, Fast and Standard are not a fallback." | Remove (OV-3: Omni only, server catalog). | — |
| A2 How to call | 108 | OVERRIDDEN | "The prompt is sent exactly as Claude writes it; nothing rewrites it." | Remove. OV-5 names this exact line as wrong: the server wraps the brief in fixed lines. | — |
| A3 Settings on every call | 452 | SERVER-ONLY | "`response_format.aspect_ratio` ... Only these two. No 1:1, no 4:5." | Remove. One prompt-relevant fact ("no negative prompt field; put control in the words") is already B3. | — |
| A4 What comes out | 198 | SERVER-ONLY | "One video with an audio track, mp4. Length 3 to 10 seconds at 24 frames per second." | Remove (server sends no sound, OV-6; extension unused). | — |
| A5 What goes in | 354 | SERVER-ONLY | "Image pixel size: Not published." / "Uploading ... images containing certain recognizable people is not supported." | Remove limits and types. Keep two lines: brief in English ("other languages have not been evaluated"); recognisable people are refused. NOTE: VW-MAP's start-image row sends readers to "the Omni sheet A5 for its accepted size", but A5 has no size; the 16:9/9:16 rule is in A3 and B7, and the server sets size anyway (OV-18). Fix the pointer. | — |
| A6 Price | 221 | SERVER-ONLY | "At $1 per 10-second clip" / "Google AI Studio use is free, so manual trials can happen there." | Remove. | — |
| A7 Limits, waits, errors | 306 | SERVER-ONLY | "Decision: background plus poll every 10 seconds." | Remove waits, codes, tiers. Keep: a blocked prompt is rewritten, never resent unchanged; every clip carries SynthID (feeds compliance C16). | — |
| Part B heading | 8 | GENERAL | "How this model reads words" | Keep. | — |
| B1 Prompt shape | 226 | OVERRIDDEN | "Camera: {one move ...}. ... Audio: {room tone and one sound} ... {N}s." | Convert (OV-4, OV-5, OV-6). The `<FIRST_FRAME>`, Camera, Continuity, Audio, single-scene and length lines are all server lines. Google's "less prescriptive than Veo" point is the today's-model rule worth keeping. | The start image already holds who, where, the look and any text. Write only what moves: the subject's one action with one physical detail, then one or two movements in the surroundings. Do not retell the picture. Omni needs less spelling-out than older video models. |
| B2 Defaults you must override | 191 | OVERRIDDEN | "End the prompt with a length, as Google's own examples do: "10s"" | Remove. Single scene, no audio, length are server lines (OV-5, OV-6, fixed lines 11 and 13); aspect is SERVER-ONLY. Writing them duplicates the server text. | — |
| B3 Negatives go in the prompt text | 53 | GENERAL | "Keep negatives short and specific." | Keep. The today's-model negative rule. | — |
| B4 Editing a clip | 200 | GENERAL | "Simple prompts work best for video editing. Overly descriptive prompts can lead to unintended changes." | Shelve: no VW step edits a clip; `previous_interaction_id` is SERVER-ONLY. Return when a clip-edit step exists. | — |
| B5 Timing inside the clip | 98 | OVERRIDDEN | ""Every 2s cut to a new frame." Timecode form: "[0-3s] A person is walking"" | Convert: cuts and timed windows are OV-4/OV-6; plain-language timing of one action inside one shot is not forbidden. | Inside the take an action may be timed in plain words ("after about three seconds she sets the cup down"). No cuts, no timecode windows, no frame counts. |
| B6 Text inside the video | 97 | OVERRIDDEN | "Say exactly what any visible text reads ... Quote it." / "One word on the screen at a time" | Convert: quoting breaks OV-12; animated words contradict fixed line 11 "No captions or overlay text". | Text already in the start image stays as it is; never ask the take to add, change or animate words. Video text is unreliable: check every character survived the motion. |
| B7 Naming the pictures and clips | 321 | SERVER-ONLY | "`[# Sources <FIRST_FRAME>@Image1 <LAST_FRAME>@Image2]`" / "a 1:1 or 4:5 start frame must be re-framed" | Remove: fixed lines 1 and 12 write the tags and the "Use Image1..." sentence; OV-4 bans per-model tags in the brief. Points at `BUILD-PLAN Part 3`, not in the bundle. | — |
| B8 Image to video | 84 | GENERAL | "Vague prompts like "make it move" produce less compelling results than detailed descriptions" | Keep the motion-detail sentence; drop "camera movement" from it (OV-5). | — |
| B9 First and last frame | 67 | OVERRIDDEN | "specify the exact camera movement or transition path ... Close with "One continuous shot, no jump cuts."" | Convert (OV-8: end image is an edit of one region, no camera move; fixed lines 11-12). | With an end image, describe the action that carries the start into the end. The camera does not move between them; the server adds the frame lines. |
| B10 Extending a clip | 138 | OVERRIDDEN | ""Camera slowly pulls out, forgotten dusty catacombs, dramatic music score."" | Remove: OV-3 splits long passages into new 3-10 s shots; music is OV-6. | — |
| B11 Camera and continuity words | 173 | OVERRIDDEN | ""whip-pans" ... "natural smartphone zoom", "film camera", "webcam style"" / "the length goes in the words" | Convert. Camera words: OV-5 (server writes Camera from `camera_move`) and OV-7 (no handheld/phone looks); REDUNDANT with `video/craft/camera-lighting-vocabulary.md`. The duration paragraph DISAGREES with VW: VW sides with the third-party "never put duration in the prompt". Keep the third-party craft line minus "sound anchor". | Lead with the subject and the action; describe what is seen, not what it means; one physical micro-action and one movement in the surroundings per shot. |
| B12 Audio and speech | 92 | OVERRIDDEN | "Dialogue: name the speaker and quote the line" | Remove (OV-6: no sound, no dialogue, no music). | — |
| B13 Draft workflow | 66 | OVERRIDDEN | "generate 3-4 draft variations in 360p" | Remove (OV-17, OV-2, FIELD-SOURCES `finish: final`, `variants: 1`). | — |
| B14 Failure habits and the fix | 276 | REDUNDANT | "Drift across several edits ... regenerate from the approved frame" / "Use client staff only with consent" | Cut to three rows: drift (compare with the approved, regenerate from the approved start), complex motion (one action per take), text (check characters). Cuts/audio/length/uri/timeout rows are server; the faces row DISAGREES with OV-9/OV-21. | — |
| B15 Not to be asked for as final | 42 | OVERRIDDEN | "Generate the clip with a reserved area and composite in an editor." | Remove: OV-19 (no reserved area unless the plan asks); rest REDUNDANT with RULEBOOK line 31 (AGREE). | — |
| Part C Evidence from our jobs | 100 | SERVER-ONLY | "Did the prompt-text length hold? Did `duration` hold?" | Remove (OV-23). | — |

**Totals, Omni sheet:** 4,238 words. Kept for the operator's AI ≈ 410 (B3, B8, rewritten B1/B5/B6/B9/B11, three B14 rows, four one-line facts from A5/A7). To remove, convert or leave to the server ≈ 3,830. Over 90% of this sheet is API detail or guidance the server now overrides.

---

## 3. `library/agency/deterministic-checks.md` (2,584 words)

Source: `kwistzzqq-byte/image2-ads-studio`, an advertising-image tool (storefront signs, roll-up banners, posters, e-commerce shots). RULEBOOK §2 and answer-form lint 7 depend on §1 and §2, so those two need converting, not deleting.

| file § heading | words | tag | evidence (quote ≤ 20 words) | action | generic rewrite |
| --- | --- | --- | --- | --- | --- |
| Title + provenance | 74 | PROVENANCE | "Source repository: https://github.com/kwistzzqq-byte/image2-ads-studio ... Licence: Apache-2.0" | Keep a two-line provenance (repo, licence; the licence file stays in `licences/`). | — |
| §1 Banned vague phrases (intro) | 42 | SOURCE-SPECIFIC | "`STYLE_REWRITE_RULES` and `ENGLISH_REPLACEMENTS` in `deterministic-prompt.ts`" | Convert: describe the rule, not the source code. | Rewrite every vague style word into things you can see in the picture, and list each rewrite in the answer. A word with no visible meaning is deleted. |
| §1a English patterns | 121 | SOURCE-SPECIFIC | "`Apple style` ... light gray or pure white background, centered product, soft shadow, minimal text" | Convert to the generic table below. Row analysis follows this table. | see proposed table |
| §1b Chinese-only patterns | 264 | SOURCE-SPECIFIC | "commercial studio-shoot style ... neutral background, soft key light, realistic shadow, clear product material" | Convert. Four rows DUPLICATE 1a word for word (Apple, premium, ins, cinematic); the "like X / similar to X / X style" rows are the one truly generic idea. | see proposed table |
| §2 Presence checks | 188 | SOURCE-SPECIFIC | "`typographySpecified` ... headline, font, type, readable, information area, selling point" | Convert. Keyword-presence checks reward keyword stacking (OUTDATED habit). `typographySpecified` forces a text term on a picture with no words. `compositionSpecified` accepts "center", which OV-14 refuses. "door, window, boundary" is signage. Still the RULEBOOK §2 floor, so rewrite it. | Every picture prompt says: where the subject sits (a landmark and a distance); where the light comes from and how soft it is; the main materials or surfaces; the words to be read, or that there are none; how each reference is used, or that there is none. |
| §3 Deterministic execution requirements | 171 | REDUNDANT | "This block is appended to every compiled prompt" / "door/window/wall boundaries, or product identity" | Remove. Restates §1 and §2 (AGREE) and RULEBOOK §2. Appending meta-instructions to the image prompt is an older-model habit; "image sections, text areas" is ad layout. | — |
| §4 Repair-once rule | 98 | SOURCE-SPECIFIC | "the request stops with status 422 and the message ... after one repair attempt." | Remove. Their server loop; VW's `library.check_prompt` refusal and the operator's yes/no replace it. | — |
| §5 No-invention rule | 202 | REDUNDANT | "do not invent prices, dates, phone numbers, addresses, or promises the user did not provide." | Remove: seven variants of RULEBOOK §"No price, date, phone number..." (line 35) (AGREE). Its "reserve clean text areas" DISAGREES with OV-19 (no reserved area unless the plan asks). "Remove concrete brands, prices ... slogans" is their template-authoring rule. | — |
| §6 Generation requirements per task type | 369 | SOURCE-SPECIFIC | "The image must look like a real advertising production deliverable, not pure concept art." | Remove. The shared line is wrong for documentary, training and story films. Task types are print/signage. Salvage one line under CATEGORY:advertisement-product from `ecommerce_main_image` and `product_ad`. | Product pictures: the product is large and unobstructed; never change its shape, packaging, label or identity; never add an efficacy, price or certification claim. |
| §7 Manufacturability rules for built signage | 719 | SOURCE-SPECIFIC | "Do not turn the display stand into an ordinary landscape poster" / "Do not invent floor or area numbers" | Remove (28% of the file). Long template negative lists are also OUTDATED (DISAGREES with Omni B3 "keep negatives short"). Salvage one GENERAL line for places. | Anything built (a sign, a stage, a shelf, a bridge) must look physically buildable: no floating parts. When a picture shows a real place, keep its walls, doors, windows and perspective. |
| §8 Compiled prompt section order | 336 | SOURCE-SPECIFIC | "Generate one commercially usable advertising image from the following production brief." | Remove. A third prompt shape that conflicts with the answer form and the GPT B1 shape; its "Avoid" union of all template negatives is a long negative list (OUTDATED). | — |

### §1 row by row: generic or ad-tool specific

| Source row | Trigger (vague word) | Replacement given | Verdict |
| --- | --- | --- | --- |
| 1a/1b `Apple style`, "similar to Apple", "like Apple style" | Brand name | "centered product ... minimal text, crisp edges" | Ad-tool specific: a brand trigger and a product-pack-shot replacement; "centered" breaks OV-14. Keep only as an example of the generic "like <brand>" row. |
| 1a/1b `premium style` / `luxury style` / `high-end feel` / "premium feel" | Generic vague word, used in every category | "25% negative space, thin dividers, rim light" | Trigger generic; replacement ad-layout specific ("thin dividers", "25% negative space" are poster grid). Keep trigger, replace answer. |
| 1a/1b `Instagram style` / `ins style` | Platform label | "centered subject, soft shadow, a few lifestyle props" | Trigger generic (social labels appear in any brief); replacement is a product-lifestyle shoot. Keep trigger, replace answer. |
| 1b "influencer style" | Platform label | "photo-friendly focal area ... concise text area" | Ad specific ("text area"). Merge into the social-label row. |
| 1b "big-brand feel" | Ad wording | "large subject scale, single dominant color" | Ad specific. Merge into the premium row. |
| 1a/1b `cinematic style` / `cinematic look` / "cinematic feel" | Generic vague word | "warm-cool contrast lighting, foreground-midground-background depth, low-key tonal layers" | Generic; the replacement imposes one look (low-key, warm-cool). Keep trigger, ask for the facts instead of fixing them. |
| 1b "commercial studio-shoot style" | Product-shoot wording | "neutral background, soft key light ... clear product material" | Ad/product specific; generic once "product" becomes "subject". |
| 1b "similar to X", "like X" | Any comparison | "use explicit composition, material, lighting, color, and typography hierarchy" | Generic (best row). Drop "typography hierarchy" (ad poster term). |
| 1b "reference X style" | Style reference | "extract only the reference image composition, material, lighting, color" | Generic; matches GPT B6 "give the reference one role". |
| 1b "X style" (1-12 chars + Chinese "style") | Any style label | "explicit composition, material, lighting, color, and typography hierarchy" | Generic; merge with "like X". |

### Proposed generic table (replaces §1a and §1b)

| Vague word in the brief | Write instead (visible facts, chosen for this shot) |
| --- | --- |
| stunning, beautiful, epic, masterpiece, best quality, 8K, ultra-detailed, hyper-realistic, flawless, perfect | Delete. If something is meant, name one fact: the light ("overcast daylight"), a surface ("chipped paint"), a material ("brushed aluminium"). |
| premium, luxury, high-end, big-brand | The materials and their finish, how many objects, how much plain space around the subject, the light's direction and softness. |
| cinematic, filmic, dramatic | Light direction and contrast, what is near, middle and far, the lens feel ("long lens, shallow depth"), the colour of the light. |
| Instagram / influencer / social / UGC style | The capture as a fact ("a phone photo at eye level"), the setting, the light source, the objects named. |
| studio shot, commercial look, professional | Background colour and material, where the main light sits and how soft it is, the shadow it casts. |
| like <brand, film, artist>, similar to X, X style | The traits taken from X, written as facts: layout, materials, light, colour, lettering. Never the name. |
| in the style of the reference picture | Which one the reference gives (layout, light, colour, texture or medium); describe the subject separately. |
| centre, middle, left third | A landmark and a measured distance in a unit the picture shows (OV-14). |
| modern, clean, minimal | The count of elements, the background, the margin, the line and surface qualities. |

---

## 4. `library/agency/compliance-checklist.md` (759 words)

VW-MAP opens this file only "when the client's industry carries compliance lines (healthcare, education, real estate, finance, restaurant)". Yet C01, C08, C09, C12, C13, C14, C16 and C17 apply to every film. Gating them by industry hides general rules.

| file § heading | words | tag | evidence (quote ≤ 20 words) | action | generic rewrite |
| --- | --- | --- | --- | --- | --- |
| Title + status | 75 | OVERRIDDEN | "Run before generation and again before delivery. A second person signs it." | Keep "run before and after; ids go in `compliance_flags`". Drop second signer (OV-20) and the pointer to `DIRECTION.md` 5d (not in bundle). | Run before generation and before delivery. The ids that apply go in the answer's `compliance_flags`; the operator alone decides. |
| Before generation | 410 | GENERAL | "C01 `claims-sourced` Every factual claim in the copy has a written source from the client." | Split by id (below). Indian regulators (ASCI, RERA, FSSAI, SEBI, DMR Act, Flag Code) are the agency's own market, not an outside project: keep them but under the industry each serves. | — |
| After generation | 239 | GENERAL | "C12 `text-letter-by-letter` Every string read letter by letter against the brief." | Split by id (below). | — |
| Sign-off | 35 | OVERRIDDEN | "second_person" | Remove: OV-20 (operator signs alone), OV-23 (server writes the record). | — |

Per id (rows inside the two sections):

| Id | Tag | Evidence | Action / rewrite |
| --- | --- | --- | --- |
| C01 claims-sourced | GENERAL | "Every factual claim in the copy has a written source from the client." | Keep, move to the always-open set: documentary and training claims need it most. Rewrite: "Every factual claim shown or narrated has a written source." |
| C02 no-superlatives | CATEGORY:advertisement-product | ""best", "No. 1", "guaranteed", "100 percent"" | Keep under advertisement. |
| C03 mandatory-text-present | OVERRIDDEN (OV-22) | "Real estate: the project's RERA registration number." | Remove while OV-22 stands. |
| C04 no-health-outcome-claims | CATEGORY:advertisement-product (healthcare) | "No cure, treatment or outcome claim." | Keep under industry healthcare; "practitioner consent for any likeness" is met by OV-9. |
| C05 no-education-guarantees | CATEGORY:advertisement-product (education) | "No guaranteed placement, marks or ranks." | Keep under industry education (advert claims, not training content). |
| C06 no-return-promises | CATEGORY:advertisement-product (finance) | "No promised returns; risk disclaimer present." | Keep; the disclaimer half is OVERRIDDEN by OV-22. |
| C07 no-alcohol-tobacco | GENERAL | "Not produced." | Keep (house policy, any film). |
| C08 no-third-party-marks | GENERAL | "No third-party logos, competitor product shapes, franchise characters" | Keep; drop "shelf templates have their real brands replaced" (source-tool wording). |
| C09 consent-on-file | OVERRIDDEN (OV-21) | "No public figures or lookalikes." | Remove the consent-id part (OV-21). Keep "No public figure or lookalike, no identifiable child" as GENERAL: a person described in words can still come out as a lookalike, which decision 5 does not cover. |
| C10 festival-motif-check | SOURCE-SPECIFIC | "applies when `festival_sheet` set" | `festival_sheet` is not a VW job-form field (FIELD-SOURCES). Rewrite: "Religious and national symbols are used respectfully and as local law requires (in India, the Flag Code)." |
| C11 retouch-decline-list | SOURCE-SPECIFIC | "applies when photo-fix" / refers to `agency/retouching/README.md` | No VW step is photo-fix and the README is not in the bundle. Keep one line as CATEGORY:documentary-explainer: "Never add or remove people or events in a picture presented as the real event." |
| C12 text-letter-by-letter | GENERAL | "No added copy, however decorative." | Keep. Agrees with GPT B4/B10. |
| C13 no-invented-badges | REDUNDANT | "No invented badges, seals, awards, star ratings" | Same as RULEBOOK line 35 (AGREE). Keep the id, drop the restated text. |
| C14 no-lookalike-background-text | REDUNDANT | "No readable background text that resembles a real brand" | Same as RULEBOOK line 35 (AGREE). Keep the id only. |
| C15 platform-policy | CATEGORY:social-ugc | "no fake interface elements such as play buttons" / "Meta and Google ad policies" | Keep under social and advertisement. |
| C16 disclosure-label | GENERAL | "Disclosure label for realistic generated imagery where the platform, the sector or the client requires one." | Keep; add that every Omni clip carries SynthID (Omni A7). Drop "property enhancements" (real-estate example, file under that industry). |
| C17 rights-to-deliver | GENERAL | "no stock elements without licence; source licences on file" | Keep; points at `_sources/SOURCES.md`, not in the bundle. |
| C18 mandatory-text-rendered | OVERRIDDEN (OV-22) | "Mandatory text from C03 is present and legible" | Remove while OV-22 stands. |

**Totals, compliance checklist:** 759 words. Kept for the operator's AI ≈ 400 (C01, C02, C04-C08, C09 lookalike line, C12-C17, short header), with eight general ids moved out of the industry gate. To remove or convert ≈ 360 (second signer, sign-off block, C03, C18, consent-id part of C09, C10/C11 conversion).

---

## 5. Per-file summary

- **GPT Image FACT-SHEET:** 2,820 words total; ≈ 840 kept for the operator's AI; ≈ 1,980 removed, converted or left to the server.
- **Omni FACT-SHEET:** 4,238 words total; ≈ 410 kept; ≈ 3,830 removed, converted or left to the server.
- **deterministic-checks.md:** 2,584 words total; ≈ 265 kept (as generic rewrites: §1 table, §2 floor, one advertisement line, one built-structure line, provenance); ≈ 2,320 removed or converted.
- **compliance-checklist.md:** 759 words total; ≈ 400 kept; ≈ 360 removed or converted.

## 6. Contradictions between files (and with VW-MAP)

1. **Quoted words.** GPT B1/B4 ("Put the words in quotes") and Omni B6 ("Quote it") vs OV-12 (words only in `exact_text`, quote nothing else). deterministic-checks §2 `typographySpecified` also forces a text term on every prompt, even a picture with no words.
2. **Three prompt shapes.** GPT B1 (Asset/Scene/Subject/.../Constraints), Omni B1 (`<FIRST_FRAME>`/Camera/Audio/{N}s), deterministic-checks §8 (User Brief/.../Avoid). None matches the answer form plus the server's fixed lines (OV-4, OV-5).
3. **Quality and drafts.** GPT B4/B9/B10 (medium first, raise one step), GPT A1 (Flare for drafts) and Omni B13 (360p drafts) vs OV-2 and OV-17 (always high, one final generation).
4. **Length in the prompt.** Omni B2/B11 say the length goes in the words, overriding a third-party "never put duration in the prompt"; VW sides with the third party for the brief because the server appends "{n}s" (OV-5, fixed line 13).
5. **"Centre".** deterministic-checks §1a ("centered product", "centered subject") and §2 (`compositionSpecified` accepts "center") vs OV-14 (refused).
6. **Reserved areas.** GPT B11 / Omni B15 ("reserved area and composite") and deterministic-checks §5 ("reserve clean text areas") vs OV-19 (no reserved area unless the plan asks).
7. **Real people.** Omni B14 ("Use client staff only with consent") and compliance C09 (consent record id) vs OV-9/OV-21 (no real person's picture is ever sent). The lookalike risk of a words-only person is in none of them.
8. **Negatives.** Omni B3 ("Keep negatives short and specific") vs deterministic-checks §7/§8 (template negative lists unioned into a long Avoid block).
9. **Model per job.** GPT A4 ("A 4:1 banner ... is a Nano Banana job") vs OV-1 (the film's one picture AI makes every picture).
10. **Category bias.** deterministic-checks §6 ("must look like a real advertising production deliverable") is applied to every compiled prompt in the source, which is wrong for documentary, training and story films. GPT B2 points readers to that table as the general vague-word fix.
11. **Wrong pointer.** VW-MAP sends the start-image step to "the Omni sheet A5 for its accepted size"; Omni A5 says pixel size is "Not published", and the 16:9/9:16 rule lives in A3 and B7.
12. **Prompt rewriting.** Omni A2 ("sent exactly as Claude writes it") vs OV-5 (server wraps the brief). GPT A2 makes the same claim for pictures, which still holds there.
13. **Signer.** compliance header and sign-off (second person) vs OV-20 (operator alone).
14. **Agreements worth keeping in one place.** No-invention (deterministic §5, compliance C13/C14, RULEBOOK line 35), not-final assets (GPT B11, Omni B15, RULEBOOK line 31), letter-by-letter checking (GPT B4, compliance C12) all agree. Each should live once, in the RULEBOOK, with the others pointing to it.
