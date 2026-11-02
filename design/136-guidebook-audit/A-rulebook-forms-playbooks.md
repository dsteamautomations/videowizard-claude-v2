# Audit A: RULEBOOK, VideoWizard answer form, video-frame, web-app, diagram-in-states, gap-fill

Bundle: `videowizard-v2/server/library/vwlib-2026-10-29-3d60877d3d23/library/`. Context read: `VW-MAP.md` (override table and fixed motion lines). Read-only audit.

Word counts are body words per section (heading line excluded, counted with `awk NF`), so file totals are slightly below `wc -w` (which counts headings). Where a section mixes tags, it is split into ↳ sub-rows so the totals are honest; sub-row counts are per line or table row. "VW-MAP row" names the row of "Where VideoWizard overrides the library" by its first words.

Kept = GENERAL + CATEGORY + PICTURE-KIND. Remove or convert = SOURCE-SPECIFIC + OUTDATED + REDUNDANT + OVERRIDDEN + PROVENANCE.

---

## 1. library/RULEBOOK.md

| file § heading | words | tag | evidence (≤ 20 words) | action | generic rewrite |
| --- | --- | --- | --- | --- | --- |
| RULEBOOK § title + Status | 52 | PROVENANCE | "Status: first draft, 2026-10-19. Short on purpose." | Cut to nothing; the title says what it is. | |
| RULEBOOK § 1 Before writing anything | 90 | (mixed, see ↳) | | | |
| ↳ 1.1 read whole job form, `needs_input` | 17 | GENERAL | "If a required field is missing, answer `needs_input`. Do not guess." | Keep. | |
| ↳ 1.2 open only what INDEX.md says | 16 | REDUNDANT | "Open only what `INDEX.md` says for this job. Five to nine files." | Remove; VW-MAP opening paragraph already replaces INDEX.md and says "Five to nine files per step" (agree). | |
| ↳ 1.3 look at every picture, two lines each | 31 | GENERAL | "Write two lines on each: what is in it, any text read letter by letter" | Keep; drop "Check the tag" (answer form dropped `seen`, `tag_ok`). | |
| ↳ 1.4 decide the model | 26 | OVERRIDDEN | "Decide the model from the job form or the 'when to pick' rules" | Remove. VW-MAP row "GPT Image or Nano Banana per job": the film's picture AI is fixed at film creation. | |
| RULEBOOK § 2 Every instruction checkable | 65 | GENERAL | "Rewrite every vague word from the brief into visible facts before it reaches the prompt" | Keep. Core rule, any category. | |
| RULEBOOK § 3 Canvas before subject | 46 | GENERAL | "State the deliverable, the aspect and the layout first" | Keep, but "the aspect" is the server's (RULEBOOK 13); say "the layout first". | |
| RULEBOOK § 4 Exact words | 121 | (mixed, see ↳) | | | |
| ↳ 4.1 every string in quotes | 18 | OVERRIDDEN | "Every string that must appear goes in quotes, exactly as approved." | Rewrite to point at `exact_text`. VW-MAP row "Exact words in quotes": words go in `exact_text`; quote nothing else. | |
| ↳ 4.2 where, how big, how many times | 16 | OVERRIDDEN | "Say where it sits, how big, in what type feel. Say how many times: once." | Remove; `exact_text` carries `place` (landmark) and `size_pct`. VW-MAP rows "Exact words" and "Centre… as a place". | |
| ↳ 4.3 standing no-extra-text line | 36 | GENERAL | "Close with the standing line… Every prompt. Even prompts with no text" | Keep; answer-form lint 2 requires it. Could shorten to one sentence. | |
| ↳ 4.4 short copy | 22 | GENERAL | "one to five words renders best; long copy goes to a reserved area" | Keep. | |
| ↳ 4.5 regional script | 15 | SOURCE-SPECIFIC | "Regional-script copy is reserved, not rendered, until a test on that model says otherwise." | Convert ("regional" is the source agency's Indian-market framing). | Copy in a script not yet tested on the model is typeset later, not rendered. |
| ↳ 4.6 read every character after | 14 | GENERAL | "read every character in the whole frame, not only the headline." | Keep. | |
| RULEBOOK § 5 Never generated as final | 53 | OVERRIDDEN | "The client's logo: reserve an empty area, composite the real file afterwards." | Remove. VW-MAP rows "Logo reserve" (never drawn, no reserved area unless the plan asks; DISAGREES on reserving) and "Charts, data visualisation" (AI graphic carries words only). App screens and alpha cutouts are web/e-commerce, not VW steps. | |
| RULEBOOK § 6 Never invent | 59 | GENERAL | "No price, date, phone number, address, award… that is not in the job form." | Keep. Vocabulary leans ad ("ingredient claim, efficacy claim") but the rule serves every category. | |
| RULEBOOK § 7 Reference pictures | 151 | (mixed, see ↳) | | | |
| ↳ 7.1 number pictures, give each a job | 35 | GENERAL | "give each one a job in words, using that model's own convention" | Keep the role sentence (lint 5 is the assistant's). Drop `@Image 1`, `<FIRST_FRAME>`: the server writes the tags (VW-MAP fixed line 1). | |
| ↳ 7.2 take / do not take | 28 | GENERAL | "take only the colours and light from Image 2; do not copy any object from it" | Keep. | |
| ↳ 7.3 do not restate | 18 | GENERAL | "Do not restate what a reference already shows." | Keep. | |
| ↳ 7.4 keep-list as nouns | 24 | GENERAL | "Build the keep-list from the picture itself, as nouns a checker can tick" | Keep; swap the packaging example "NET WT 200 G" for a neutral one. | |
| ↳ 7.5 count and kind limits | 25 | OVERRIDDEN | "Stay within the model's count and kind limits. Never send a first frame together with references" | Remove. VW-MAP row 1: server sets input limits; answer-form lint 5. | |
| ↳ 7.6 shelf references | 21 | OVERRIDDEN | "A reference from the shelf is for structure only." | Remove. VW-MAP opening: the shelf "is never opened during a run". | |
| RULEBOOK § 8 Edits | 92 | (mixed, see ↳) | | | |
| ↳ 8.1 one change per turn, repeat keep-list | 18 | GENERAL | "One change per turn. Name the region, the change and the keep-list." | Keep; VW-MAP row "Edits" confirms (agree). This is the one home for the rule. | |
| ↳ 8.2 order: ratio first | 20 | OVERRIDDEN | "Order when several changes are wanted: ratio first, then copy, then props" | Remove. Ratio is the server's (VW-MAP row "placement"); several changes are refused (row "Edits"). | |
| ↳ 8.3 retry from last approved | 19 | GENERAL | "retry from the last approved file, not from the drifted one. Never stack repairs." | Keep. | |
| ↳ 8.4 composite for untouched pixels | 27 | GENERAL | "Prompting cannot promise untouched pixels." | Keep the fact; the composite step is not a VW step, so cut that half. | |
| ↳ 8.5 mask is guidance | 8 | GENERAL | "A mask is guidance, not a boundary." | Keep. | |
| RULEBOOK § 9 Words | 112 | GENERAL | "Words that hurt: 'stunning', 'epic', 'masterpiece', 'best quality', '8K'" | Keep. This is the anti-outdated rule; style anchors to technique is sound for every category. | |
| RULEBOOK § 10 Negatives | 56 | GENERAL | "a short, targeted list of what the model tends to add wrongly for this job" | Keep. | |
| RULEBOOK § 11 Real photographs | 100 | (mixed, see ↳) | | | |
| ↳ capture as fact, imperfections, no glow | 85 | PICTURE-KIND | "state the capture as a fact, 'a real phone photo', '35mm colour negative, lab scan', never as a style" | Keep with the photoreal-still step (keyframe next to footage, de-slop). | see next row |
| ↳ "name it twice" | 15 | OUTDATED | "name every way the subject differs from the model's ideal, and name it twice" | Rewrite whole section (repetition for emphasis is an older-model habit). | For a still that must pass as a real photograph, state the capture as a fact ("a phone photo", "a 35mm film scan"), name three imperfections and where they sit, ask for low micro-contrast, and exclude HDR, bloom, glossy skin and even backgrounds. Describe once how a person differs from an idealised face. |
| RULEBOOK § 12 Series and characters | 41 | REDUNDANT | "send it with every later call and repeat the five fixed traits in words each time" | Remove; video-frame §2 "continuity kit" and §8 drift row say the same (agree). For people, VW-MAP rows "A person's reference picture" and "Nine-photo series" and fixed line 7 (server writes person lines) narrow it. | |
| RULEBOOK § 13 Settings versus words | 37 | REDUNDANT | "go in the API settings, not in the prompt words, unless that model's fact sheet says" | Remove; VW-MAP row 1 and answer-form lint 8 cover it. DISAGREES on the "unless" exception: VW refuses size words always. | |
| RULEBOOK § 14 People, consent and compliance | 112 | (mixed, see ↳) | | | |
| ↳ 14.1 consent id, no public figures | 26 | OVERRIDDEN | "No identifiable person without a consent id on the job form." | Remove the consent-id half (VW-MAP rows "A person's reference picture" and "Compliance C09"); keep "no public figures, no lookalikes" as one line. | |
| ↳ 14.2 never change body, skin, age | 22 | GENERAL | "Never change body shape, skin colour, apparent age or gender." | Keep; applies when describing a person from footage. | |
| ↳ 14.3 sector rules | 35 | OVERRIDDEN | "registration numbers for real estate… licence numbers for food. The full list is DIRECTION section 5d." | Remove. VW-MAP row "Compliance C03 and C18" (mandatory text not checked); DIRECTION 5d not in bundle; the per-step row already routes to `agency/compliance-checklist.md`. Also source-specific (Indian sector rules). | |
| ↳ 14.4 festival work | 29 | SOURCE-SPECIFIC | "no deities on products, food, footwear or packaging… tricolour imagery follows the Flag Code" | Convert (Indian festival / packaging client rules). | Sacred and national symbols: none on products, food or clothing; no religious text; a national flag follows that country's flag rules. |
| RULEBOOK § 15 After generation | 112 | (mixed, see ↳) | | | |
| ↳ check most expensive mistake first | 75 | GENERAL | "Check the most expensive mistake first. People: eye spacing, nose, hairline, skin tone, hands." | Keep; drop "Storyboards" (not used, VW-MAP row "Storyboard grids") and "numbers" under infographics (row "Charts"). | |
| ↳ checklist and feedback record | 37 | REDUNDANT | "The verdict goes into the feedback record with what went wrong" | Remove; answer form `checklist` row says it (agree); VW-MAP row "The application writes the feedback record" (server writes it). | |
| RULEBOOK § 16 Video | 174 | (mixed, see ↳) | | | |
| ↳ 16.1 frame is a brief | 31 | REDUNDANT | "It carries the shot number, the camera move it must leave room for, and the continuity anchors." | Remove; video-frame §1 says it nearly word for word (agree). | |
| ↳ 16.2 clip prompt carries camera, audio, single-scene line | 39 | OVERRIDDEN | "one camera move, what the subject does, what the environment does, the audio" | Rewrite to "only what the subjects and surroundings do". VW-MAP row "The clip prompt carries the camera move…". | |
| ↳ 16.3 one move, one action | 15 | GENERAL | "One primary camera move per shot. One main action. Longer stories are several clips." | Keep; agrees with the Omni 3–10 s row. | |
| ↳ 16.4 show, do not tell | 20 | GENERAL | "'His jaw locks' works; 'he is scared' does not." | Keep. | |
| ↳ 16.5 timing windows | 18 | OVERRIDDEN | "Timing in windows of three seconds or more" | Remove. VW-MAP row "Each video model's own prompt shape… timed windows". | |
| ↳ 16.6 audio and dialogue | 18 | OVERRIDDEN | "Audio is described or switched off. Dialogue is short… in quotes." | Remove. VW-MAP row "Audio described, dialogue in quotes…": never. | |
| ↳ 16.7 check the hold after animation | 33 | GENERAL | "A shot that broke is regenerated from the approved frame, not patched" | Keep. | |
| RULEBOOK § 17 The lint before `ready` | 17 | REDUNDANT | "The ten rules are in `forms/answer-form.md`." | Remove or repoint; names the master form, which is not in the bundle. The VW cut's lint table is the live one (agree on "fail twice, `needs_input`"). | |
| RULEBOOK § Where this came from | 63 | PROVENANCE | "`00-method/craft.md` sections 1 to 15 and 18; `00-method/prompting-guide.md`…" | Remove. Its last sentence (style anchors, short negatives) repeats §9 and §10. | |

## 2. library/forms/answer-form.videowizard.md

| file § heading | words | tag | evidence (≤ 20 words) | action | generic rewrite |
| --- | --- | --- | --- | --- | --- |
| answer-form § title + Status | 61 | PROVENANCE | "22 Oct 2026 (design/69, approved by Revathi)… The master library's form is untouched." | Cut to one line: "The server fixes model, settings, inputs and files; the answer holds only what the assistant alone knows." | |
| answer-form § Three possible answers | 75 | GENERAL | "`needs_input` Something required is missing or contradictory. Nothing is sent" | Keep. | |
| answer-form § The fields of a `ready` answer | 375 | (mixed, see ↳) | | | |
| ↳ field table | 323 | GENERAL | "`exact_text`… `place` (`landmark_id`…) and `size_pct`… Words in quotes… not an entry here are refused." | Keep. Fix the `exact_text` row's "(letter for letter, also in the prompt)": it DISAGREES with VW-MAP "go only in the answer's `exact_text`" (see contradictions). | |
| ↳ "About fifteen fields. Dropped…" | 52 | PROVENANCE | "Dropped from the full form because the server has them: `job_id`, `round`, `playbook_used`…" | Remove; tells the writer what not to fill, which the table already shows by omission. | |
| answer-form § `needs_input` | 22 | GENERAL | "At most five. `can_proceed_with_defaults` as in the full form." | Keep; define `can_proceed_with_defaults` here (the full form is not in the bundle). | |
| answer-form § `refused` | 13 | GENERAL | "`reason`: `no-consent`, `policy`, `rights`, `impossible`." | Keep. | |
| answer-form § The lint before `ready` | 268 | (mixed, see ↳) | | | |
| ↳ rows 2, 5, 7, 9 + header + fail line | 151 | GENERAL | "The end image names its pictures: Image 1 is the start, images 2 onward its identity sheets." | Keep: these are the assistant's checks. | |
| ↳ rows 1, 3, 4, 6, 8, 10 (server checks) | 117 | REDUNDANT | "No consent ids exist in VideoWizard, so a real person's picture is never sent" | Collapse to one line "the server checks the rest". Repeats VW-MAP rows "placement", "Logo reserve", "A person's reference picture", "A model name", "`checked_by`" (agree). | |
| answer-form § Example, status ready | 170 | GENERAL | "The mason, now one step to the left of the wall's near corner, facing the camera" | Keep; it models landmark-plus-distance placement well. Scene is documentary; one example of another category (product or narrative) would show genericity. `files_opened` paths ("always/…", "start/…") do not match bundle paths. | |

## 3. library/playbooks/video-frame.md

| file § heading | words | tag | evidence (≤ 20 words) | action | generic rewrite |
| --- | --- | --- | --- | --- | --- |
| video-frame § title + Version/Status | 63 | PROVENANCE | "Version 0.1, written 2026-10-19. Status: draft, untested on a real job." | Remove; the "read with" list repeats VW-MAP's per-step table. | |
| video-frame § 1 What this playbook covers | 74 | REDUNDANT | "Every frame is a brief: it carries a shot number, the camera move it must leave room for" | Remove. Repeats RULEBOOK 16.1 (agree); the "Added 2026-10-21" cross-refs repeat VW-MAP routing. Task list names `storyboard`, `cover-frame`, which VW does not use. | |
| video-frame § 2 Decisions already taken | 329 | (mixed, see ↳) | | | |
| ↳ Order of work | 39 | OVERRIDDEN | "The client approves the shot order on the storyboard, where changes are cheap." | Remove. VW-MAP row "Storyboard grids, cover frames, handoff notes": not used. | |
| ↳ Aspect | 38 | OVERRIDDEN | "16:9 or 9:16 for Omni; Seedance's six ratios." | Remove. VW-MAP rows "placement" and "A choice of video model". | |
| ↳ Model | 72 | OVERRIDDEN | "GPT Image 2.5 Sunburst for keyframes… Nano Banana 2.1 for storyboard grids, continuity sheets" | Remove. VW-MAP row "GPT Image or Nano Banana per job". | |
| ↳ Everything critical locked in the still | 33 | GENERAL | "The video model amplifies any ambiguity in the still." | Keep. Best line in the file. | |
| ↳ Continuity kit approved first | 47 | REDUNDANT | "A character sheet and a product sheet, each with five traits that must never change" | Merge into one home (RULEBOOK §12 says the same, agree). VW-MAP row "Nine-photo series…" fixes the sheet's shape. | |
| ↳ Headroom for the move | 57 | GENERAL | "A push-in needs margin around the subject; a pan needs the subject off-centre in the direction of travel" | Keep; applies to the start image when `camera_move` names a move. | |
| ↳ (table header) | 14 | GENERAL | | counted with kept rows | |
| ↳ One shot per call | 29 | OVERRIDDEN | "Grids are for storyboards only." | Remove. VW-MAP row "Nine-photo series…" (one picture per call) and "Storyboard grids". | |
| video-frame § 3 Before writing | 128 | (mixed, see ↳) | | | |
| ↳ 3.1 the shot list | 43 | OVERRIDDEN | "number, intended seconds, action, camera move, voice-over or caption reference, transition to the next shot" | Remove. VW-MAP row "Storyboard grids…": the visual plan carries shot, seconds, camera; no transitions (row "Audio described…"). | |
| ↳ 3.2 placement and model | 14 | OVERRIDDEN | "The video placement and model, so the aspect and accepted size are known." | Remove. VW-MAP rows 1 and "placement". | |
| ↳ 3.3 person sheet with consent id | 26 | OVERRIDDEN | "the approved sheet tagged `person` with its consent id" | Remove. VW-MAP row "A person's reference picture" (decision 5); answer-form lint 6 "No consent ids exist". | |
| ↳ 3.4 visual theme in five lines | 28 | OVERRIDDEN | "palette with hex values… motion language. Written once and repeated verbatim in every frame prompt." | Remove. VW-MAP row "Nine-photo series…" ("the style comes from the approved style picture") and row "A handheld or moving camera". Verbatim repetition is also an old-model habit. | |
| ↳ 3.5 i2v vs first/last pair | 17 | OVERRIDDEN | "Which shots… need a first and last frame pair." | Remove. VW-MAP row "A first and a last frame for every move". | |
| video-frame § 4 Task notes | 454 | (mixed, see ↳) | | | |
| ↳ continuity-kit | 104 | OVERRIDDEN | "front, three-quarter and side at equal scale… Recipe P038 is the pattern" | Replace with the VW sheet: plan's `required_views`, labelled, film's frame (VW-MAP row "Nine-photo series"). Keep only the five-trait naming for people (person from words) and objects. P038 is shelf. | |
| ↳ storyboard | 119 | OVERRIDDEN | "One grid image at the video's aspect, one panel per shot… needs `high` quality on GPT Image." | Remove. VW-MAP rows "Storyboard grids" and "Images at a chosen quality". | |
| ↳ keyframe | 93 | PICTURE-KIND | "A frame that cannot name its beat, function, emotion and implied motion is not ready." | Keep with the start-image step. Cut "sound under the frame" (VW: no sound) and "panel id" (storyboard term). Frozen motion residue (smear, streak) suits narrative/ad stills, not a start image a take will move. | |
| ↳ keyframe-set | 43 | CATEGORY:advertisement-product | "The same product or character across several locations with the same palette and light." | File under advertisement-product; not a VW-MAP step. Seeds P055, P058 are shelf. | |
| ↳ first-last-frame | 64 | OVERRIDDEN | "the camera whip-pans right from the drummer to reveal the dancer" | Remove. VW-MAP row "A first and a last frame for every move": end image is an edit in one region, same framing, no camera move. DISAGREES. | |
| ↳ cover-frame | 31 | OVERRIDDEN | "reframed to the platform's cover or thumbnail size… reads at 160 px." | Remove. VW-MAP row "Storyboard grids, cover frames". (Social-ugc thumbnail rule otherwise.) | |
| video-frame § 5 Writing the prompt | 233 | (mixed, see ↳) | | | |
| ↳ keyframe template | 192 | OVERRIDDEN | "Target aspect ratio: {16:9 \| 9:16}. Mode: {edit with identity \| multi-reference}… subject at left third" | Replace. Aspect/mode in words (RULEBOOK 13, VW-MAP row 1), theme verbatim with hex and "handheld" (row "A handheld…"), "left third" (row "Centre… as a place"), `{brand preamble}` (agency brand kit). Optional VW-safe skeleton in the next column. | Image roles. Layout first: where the subject stands by landmark and distance, headroom for the named move. Then subject, the one anchor the eye lands on, foreground/midground/background jobs, the beat as an object's state. Exact text: none or `exact_text` entries. Short targeted constraints. Standing no-extra-text line. |
| ↳ storyboard grid variant | 41 | OVERRIDDEN | "For a storyboard grid, replace the Shot and Beat lines with the grid statement" | Remove. VW-MAP row "Storyboard grids". | |
| video-frame § 6 Handoff to the video model | 71 | OVERRIDDEN | "shot number and intended seconds; the camera move… the audio reference; the transition to the next shot" | Remove. VW-MAP row "Storyboard grids, cover frames, handoff notes": not used. Its last sentence (do not re-describe the frame) repeats RULEBOOK 7.3. | |
| video-frame § 7 Checklist lines | 134 | (mixed, see ↳) | | | |
| ↳ traits, object, palette/light, headroom, no captions, card | 82 | GENERAL | "Headroom suits the camera move named in the shot list. must." | Keep; reword "product" to "object" so it is not ad-only. | |
| ↳ aspect/size, storyboard, first-last lines | 52 | OVERRIDDEN | "First and last frame: same aspect, same light, same traits; only the move's change differs." | Remove. Rows "placement", "Storyboard grids", "A first and a last frame" (no move between). | |
| video-frame § 8 What goes wrong on frames | 188 | (mixed, see ↳) | | | |
| ↳ header + "props cross cell boundaries" | 37 | PICTURE-KIND | "Equal invisible cells with internal space; one figure per cell" | Keep with the reference-sheet step (multi-view sheet). | |
| ↳ character drifts | 29 | REDUNDANT | "Kit as Image 1 every call; five traits repeated in words; 'do not redesign the character'" | Remove; RULEBOOK §12 says it (agree). | |
| ↳ frame fights the camera move | 19 | REDUNDANT | "State headroom from the shot list" | Remove; repeats §2 Headroom row. | |
| ↳ grid repeats, panel order, panel no beat | 59 | OVERRIDDEN | "Grid repeats one flattering composition" | Remove. VW-MAP row "Storyboard grids". | |
| ↳ square then cropped | 23 | OVERRIDDEN | "Frame generated square then cropped to 9:16" | Remove. Server sets size (row "placement"). | |
| ↳ hairstyle reinterpreted | 21 | SOURCE-SPECIFIC | "'Hairstyle structure intact, no loose hair, no reinterpretation'" | Convert ("no loose hair" is one source project's look). | Hairstyle changes on a person: name the hairstyle's structure and say it does not change. |
| video-frame § 9 Evidence | 24 | PROVENANCE | "None yet. Core status also needs the motion hold recorded on at least two animated shots" | Remove. | |
| video-frame § 10 Built from | 34 | PROVENANCE | "`DIRECTION.md` sections 5h and 6 video fields, scenarios A39 to A44" | Remove. | |

## 4. library/playbooks/web-app.md

VW-MAP routes this file only for the diagram shot ("`playbooks/web-app.md` (process-explainer)"). Almost everything else is website, app-store, email or brand-kit work: deliverables VideoWizard never makes.

| file § heading | words | tag | evidence (≤ 20 words) | action | generic rewrite |
| --- | --- | --- | --- | --- | --- |
| web-app § title + Version/Status | 69 | PROVENANCE | "This is the thinnest area in the library; several tasks here are written from first principles" | Remove. | |
| web-app § 1 What this playbook covers | 30 | SOURCE-SPECIFIC | "`landing-hero`, `icon-set`, `spot-illustration`, `device-mockup`, `app-store-panel`… `brand-board`" | Remove; web-agency task list, no VW step. | |
| web-app § 2 Decisions already taken | 326 | (mixed, see ↳) | | | |
| ↳ Nothing here is shippable UI | 55 | SOURCE-SPECIFIC | "Icons and illustrations are redrawn as vectors; screens are built by the web team." | Remove (web-team workflow). | |
| ↳ Real screenshots stay real | 37 | CATEGORY:advertisement-product | "The screen contents are never regenerated." | Keep, filed under advertisement-product (an app shown in a video). | |
| ↳ Model | 52 | OVERRIDDEN | "GPT Image 2.5 Sunburst for anything with screen text… Nano Banana 2.1 for icon sets" | Remove. VW-MAP row "GPT Image or Nano Banana per job". | |
| ↳ Quality | 19 | OVERRIDDEN | "`medium` for icons, illustrations and heroes." | Remove. VW-MAP row "Images at a chosen quality" (always high). | |
| ↳ Reserved text side | 52 | SOURCE-SPECIFIC | "usually the left 45 percent on desktop… Live text is accessible, editable and indexable." | Remove (website hero layout). | |
| ↳ Device names | 27 | REDUNDANT | "Devices are described, never named… Compliance C08." | Remove; RULEBOOK §9 "Real brands… never go into a client prompt" (agree). | |
| ↳ Palette lock | 19 | SOURCE-SPECIFIC | "Brand colours by name and hex from the preamble; nothing else." | Remove (brand-kit preamble); VW style comes from the approved style picture. | |
| ↳ Sets are one call / grid | 51 | OVERRIDDEN | "generated as one grid in one call so the style holds, then cut up" | Remove. VW-MAP row "Nine-photo series… batch generation" (one picture per call). | |
| ↳ (table header) | 14 | SOURCE-SPECIFIC | | counted with removed rows | |
| web-app § 3 Before writing | 138 | (mixed, see ↳) | | | |
| ↳ 3.1 placement names | 15 | OVERRIDDEN | "`website_hero_16x9` plus `website_hero_mobile_4x5`, `email_header`, `appstore_screenshot`" | Remove. VW-MAP row "placement". | |
| ↳ 3.2 page purpose and headline | 27 | REDUNDANT | "so the image can leave room for it and not say the same thing" | Remove; diagram-in-states §3.1 (the narration under the shot) is VW's version (agree in spirit). | |
| ↳ 3.3 icons, 3.5 wireframe, 3.6 brand style line | 82 | SOURCE-SPECIFIC | "If the kit has none, the job form says 'none' and Claude proposes one" | Remove. | |
| ↳ 3.4 real screenshots and captions | 14 | CATEGORY:advertisement-product | "the real screenshots, tagged `scene`, and the exact captions" | Keep with device-mockup. | |
| web-app § 4 Task notes | 555 | (mixed, see ↳) | | | |
| ↳ landing-hero | 73 | SOURCE-SPECIFIC | "Describe the empty side as a surface, not as nothing: 'a plain warm off-white wall'" | Convert; keep only the empty-space insight. | Describe empty space as a surface ("a plain off-white wall, no objects"), never as nothing. |
| ↳ icon-set | 73 | SOURCE-SPECIFIC | "The output is an atlas to be redrawn in vectors; say so." | Remove. | |
| ↳ spot-illustration | 58 | SOURCE-SPECIFIC | "people without facial features if the brand's style is flat… gallery… No. 142" | Convert (gallery not in bundle; brand-specific). | Pin an illustrated style by its technique, the same in each picture of the film: solid colour blocks, no gradients, no shadows, simplified proportions. |
| ↳ device-mockup | 72 | CATEGORY:advertisement-product | "the screen shows Image 1 exactly, fitted to the screen shape with no stretching" | Keep, filed under advertisement-product. | |
| ↳ app-store-panel | 58 | SOURCE-SPECIFIC | "Captions are claims; they go through C01. Sizes per store from the channel sheet row" | Remove. | |
| ↳ process-explainer | 61 | PICTURE-KIND | "Three or four stages in a row or a 2x2, each with one label… thin arrows, reading order stated." | Keep (the routed part). Change "label in quotes" to `exact_text`; drop P-recipe refs (shelf) and the "live text pages" sentence (web). | |
| ↳ email-header | 38 | SOURCE-SPECIFIC | "The simplest background that survives image-blocking." | Remove. | |
| ↳ wireframe-to-concept | 70 | SOURCE-SPECIFIC | "a 2x2 board of four directions with equal gutters for a sign-off meeting, as in P074" | Remove. | |
| ↳ brand-board | 52 | SOURCE-SPECIFIC | "palette swatches with hex values as text… a card, a bag, a screen" | Remove. | |
| web-app § 5 Writing the prompt | 297 | SOURCE-SPECIFIC | "Pixmind's realism cues: a status bar time, one item checked off… {brand preamble}… Target aspect ratio" | Convert the screen part (named outside source "Pixmind", brand preamble, aspect in words against RULEBOOK 13, logo reserve against VW-MAP). Remove the icon-set shape. | A screen in a shot: the real screenshot is Image 1, shown exactly and fitted to a described device, no added icons, bars or notifications. Name the device's look, surface, angle and light. Describe the product as if it exists, never as concept art. No real brand or device names. |
| web-app § 6 Checklist lines | 139 | (mixed, see ↳) | | | |
| ↳ screen identical; reading order/arrows | 32 | CATEGORY:advertisement-product / PICTURE-KIND | "Screen content identical to Image 1 when a screenshot was placed" | Keep each with its step (device-mockup; diagram). | |
| ↳ reserved side, icon set, set style, hero crops, header | 73 | SOURCE-SPECIFIC | "Both hero crops from one master; subject position consistent between them." | Remove. | |
| ↳ captions letter by letter; no real brand | 27 | REDUNDANT | "No real device, app or brand name or logo visible. must." | Remove; RULEBOOK 4.6 and §9 (agree). | |
| ↳ output size | 13 | OVERRIDDEN | "Output size per the channel row or the web team's spec." | Remove. VW-MAP row "placement". | |
| web-app § 7 What goes wrong on web-app jobs | 232 | (mixed, see ↳) | | | |
| ↳ header + screen redesigned + concept-art look | 80 | CATEGORY:advertisement-product | "The screen gets redesigned or gains icons" | Keep with device-mockup; drop "Pixmind lines 8 and 9" source refs. | |
| ↳ icons drift, hero invades, wireframe strokes | 84 | SOURCE-SPECIFIC | "Hero subject invades the text side… 'no objects in the left 45 percent'" | Remove. | |
| ↳ invented testimonials/checkout UI | 22 | REDUNDANT | "Invented testimonials, availability or checkout UI on a landing concept" | Remove; RULEBOOK §6 "Never invent" (agree). E-commerce example. | |
| ↳ small UI text soft | 25 | OVERRIDDEN | "`high` quality on GPT Image; 2K on Nano Banana" | Remove. VW-MAP rows "Images at a chosen quality", row 1 (server size). | |
| ↳ real brand's interface leaks from shelf | 21 | REDUNDANT | "A real brand's interface style leaks from a shelf prompt" | Remove; RULEBOOK §9 (agree); the shelf is never opened (VW-MAP opening). | |
| web-app § 8 Evidence | 24 | PROVENANCE | "Promotion needs acceptance on two briefs from two different clients… by the web team" | Remove. | |
| web-app § 9 Built from | 56 | PROVENANCE | "`gallery/ui-ux-mockups.md` No. 103 to 107; `gallery/ui-and-ad-additions.md` UI section" | Remove. | |

## 5. library/video/diagram-in-states.md

| file § heading | words | tag | evidence (≤ 20 words) | action | generic rewrite |
| --- | --- | --- | --- | --- | --- |
| diagram § title + Version/Status | 33 | PROVENANCE | "Version 0.1, written 2026-10-21 for VideoWizard (design/65, decision S1). Status: draft, untested." | Remove. | |
| diagram § 1 What this covers | 88 | PICTURE-KIND | "Nothing moves inside a state… plan a build (parts appear) or a reveal (parts get highlighted)" | Keep. Drop "chart": VW-MAP row "Charts, data visualisation" sends charts to the drawn route. | |
| diagram § 2 Decisions already taken | 259 | (mixed, see ↳) | | | |
| ↳ Model | 40 | OVERRIDDEN | "GPT Image 2.5. Flare (generate) for state 1; Sunburst (edit) for every later state" | Remove. VW-MAP rows "GPT Image or Nano Banana per job" and "Images at a chosen quality" (no Flare drafts). | |
| ↳ header + Count, Hold, Plan the last state first | 110 | PICTURE-KIND | "Write the full final diagram in words before generating state 1" | Keep. Strong, model-agnostic. | |
| ↳ One change per state | 21 | REDUNDANT | "Each state adds or highlights one idea. RULEBOOK rule 8" | Fold into one line; RULEBOOK 8.1 (agree). | |
| ↳ Keep-list repeated in full | 33 | REDUNDANT | "Every edit prompt names everything that must not change." | Fold; RULEBOOK 8.1 "Repeat the keep-list every turn" (agree). | |
| ↳ Retry from last approved | 30 | REDUNDANT | "Never edit a state that drifted; go back to the last approved one." | Fold; RULEBOOK 8.3 (agree). | |
| ↳ Text | 25 | OVERRIDDEN | "Exact strings in quotes, short, large." | Rewrite to `exact_text`. VW-MAP row "Exact words in quotes" names "diagram-in-states section 6". | |
| diagram § 3 Before writing | 99 | PICTURE-KIND | "The final state in words (the 'end picture'): canvas and aspect, background, every part, each label exactly" | Keep. Fix 3.2's "(left third, centre, lower band…)": VW-MAP row "Centre… as a place" refuses those; use landmarks. Drop "aspect" (server). | |
| diagram § 4 Writing the prompts | 249 | PICTURE-KIND | "Change only: add {the new part} at {position}… Keep exactly as in Image 1: canvas, background, every existing part" | Keep both templates. Edit: drop "for a 16:9 documentary film" (documentary-only), "Target aspect ratio: 16:9" and "Mode: generate/edit" (settings in words, RULEBOOK 13). The "alternative, to be tested" paragraph (41) is an untested experiment: move to the test log until it passes. | |
| diagram § 5 Checklist lines | 92 | (mixed, see ↳) | | | |
| ↳ label, carry-over, one change, reserved space, end picture, read time | 78 | PICTURE-KIND | "State k shows everything in state k-1 at the same place, size and colour. must." | Keep. | |
| ↳ aspect line | 14 | OVERRIDDEN | "Aspect 16:9 (or the film's format) at the size the renderer expects. must." | Remove. VW-MAP row "placement". | |
| diagram § 6 What goes wrong, and the fix | 111 | (mixed, see ↳) | | | |
| ↳ restyle, no room, colour shift, too many words | 93 | PICTURE-KIND | "No room for the next part | Plan the end picture first; reserve named empty space in state 1" | Keep. | |
| ↳ labels re-spelt | 18 | OVERRIDDEN | "List every existing label in the keep-list, in quotes" | Rewrite "without quotes". VW-MAP row "Exact words in quotes": "a keep-list names labels without quotes". DISAGREES. | |
| diagram § 7 Evidence | 21 | PROVENANCE | "The first VideoWizard sequence (VW-6) is the first test." | Remove. | |
| diagram § 8 Built from | 30 | PROVENANCE | "`models/gpt-image/FACT-SHEET.md` A1, B1, B4, B5 and the failure table" | Remove. | |

## 6. library/video/gap-fill.md

| file § heading | words | tag | evidence (≤ 20 words) | action | generic rewrite |
| --- | --- | --- | --- | --- | --- |
| gap-fill § title + Version/Status | 23 | PROVENANCE | "Version 0.1, written 2026-10-21 for VideoWizard. Status: draft, untested." | Remove. | |
| gap-fill § 1 What this covers | 70 | GENERAL | "The AI shot must look as if it came from the same camera on the same day" | Keep. Serves any film cut from real footage (documentary, product, training, UGC). | |
| gap-fill § 2 Read the neighbours first | 215 | (mixed, see ↳) | | | |
| ↳ grade, light, grain, lens, blur, place rows + plain-facts line | 185 | GENERAL | "Write these as plain facts. 'Cinematic' and 'high quality' make the AI shot look less like the real one." | Keep. | |
| ↳ Camera behaviour row | 30 | REDUNDANT | "Nothing: the take is locked off unless the shot's `camera_move` names its one move" | Remove the row; VW-MAP row "A handheld or moving camera" (agree; already reconciled). | |
| gap-fill § 3 The boundary-frame method | 145 | (mixed, see ↳) | | | |
| ↳ intro + step 1 grab last frame | 45 | GENERAL | "Use it as the reference for the gap's start image (a place or an object), or as the start image itself." | Keep; add "only when no person is in it" (VW-MAP row "A person's reference picture"). | |
| ↳ step 2 end image | 42 | REDUNDANT | "An end image only where the final state must be exact: write it with the start as `end_prompt`" | Remove; VW-MAP row "A first and a last frame" word for word (agree). | |
| ↳ step 3 motion brief | 32 | REDUNDANT | "a motion brief that describes only what the subjects and the surroundings do" | Remove; VW-MAP row "The clip prompt carries…" (agree). | |
| ↳ "In VideoWizard: `vw visuals frame`…" | 26 | REDUNDANT | "`vw visuals frame --element E --clip <id> --at <seconds>` grabs the frame (free)." | Remove; VW-MAP per-step row "Frame grab from a clip". | |
| gap-fill § 4 Cautions | 171 | (mixed, see ↳) | | | |
| ↳ size/aspect, exact continuity, not every gap | 126 | GENERAL | "Never promise an invisible join." | Keep. | |
| ↳ Real people | 45 | REDUNDANT | "A footage or web picture of a person is never sent to the picture AI" | Remove; VW-MAP row "A person's reference picture" (agree). | |
| gap-fill § 5 Checklist lines | 73 | GENERAL | "Grade, light and grain match the neighbouring real shots, compared side by side. must." | Keep. | |
| gap-fill § 6 Evidence | 16 | PROVENANCE | "None yet. Record each gap fill's verdict in the feedback log" | Remove. | |
| gap-fill § 7 Built from | 29 | PROVENANCE | "`playbooks/video-frame.md` (first-last-frame), `playbooks/video-clip.md` sections 4 and 8" | Remove. | |

---

## Totals per file (body words)

- **RULEBOOK.md**: 1,553 total (1,647 by `wc`); kept (GENERAL + CATEGORY + PICTURE-KIND) 885; remove or convert 668.
- **answer-form.videowizard.md**: 984 total (1,016 by `wc`); kept 754; remove or convert 230.
- **video-frame.md**: 1,732 total (1,791 by `wc`); kept 359; remove or convert 1,373.
- **web-app.md**: 1,866 total (1,920 by `wc`); kept 281 (device-mockup and screen rows as advertisement-product, process-explainer as PICTURE-KIND); remove or convert 1,585.
- **diagram-in-states.md**: 982 total (1,032 by `wc`); kept 717; remove or convert 265.
- **gap-fill.md**: 742 total (782 by `wc`); kept 499; remove or convert 243.
- **All six**: 7,859 total; kept 3,495 (44 %); remove or convert 4,364 (56 %). Most of the removal is OVERRIDDEN text in video-frame and off-scope web deliverables in web-app.

## Contradictions between files

1. **Quotes.** RULEBOOK 4.1 ("every string… in quotes") and diagram-in-states §2 Text and §6 ("list every existing label in the keep-list, in quotes") vs VW-MAP ("a keep-list names labels without quotes"). The answer form's `exact_text` row says text is "also in the prompt", but VW-MAP says words "go only in the answer's `exact_text`". The VW-MAP and the form disagree with each other about whether the string also appears in the prompt.
2. **Settings in words.** RULEBOOK 13 (aspect and mode go in settings, not words) vs the templates in video-frame §5, web-app §5 and diagram-in-states §4, which all write "Target aspect ratio: …" and "Mode: …" into the prompt. Answer-form lint 8 has the server refuse size words.
3. **Place words.** VW-MAP refuses "centre" and "left third" as a place. video-frame §5 ("subject at left third for a pan right") and diagram-in-states §3.2 ("left third, centre, lower band") prescribe them.
4. **End frame and camera.** video-frame §4 first-last-frame ("the camera whip-pans right… to reveal the dancer") and §7 ("only the move's change differs") vs gap-fill §3 step 2 and VW-MAP (the end is an edit in one region, same framing, no camera move).
5. **Consent ids and tags.** video-frame §3.3 ("sheet tagged `person` with its consent id") and RULEBOOK 14.1 vs answer-form lint 6 ("No consent ids exist in VideoWizard"). RULEBOOK 1.3 ("Check the tag") vs the answer form, which dropped `seen` and `tag_ok`.
6. **Logo.** RULEBOOK §5 and web-app §5 `{logo reserve}` ("reserve an empty area") vs VW-MAP ("Never drawn, no reserved area unless the plan asks").
7. **Video prompt content.** RULEBOOK 16.2, 16.5, 16.6 (camera move, audio, timed windows, dialogue in the clip prompt) vs gap-fill §3 step 3 and VW-MAP (motion brief is only what subjects and surroundings do; no sound). gap-fill already follows VW; the RULEBOOK does not.
8. **Camera style.** video-frame §3.4 and §5 theme ("motion language {handheld | locked off | dolly}") vs gap-fill §2 Camera row and §5 ("The camera is steady").
9. **Model and quality per playbook.** video-frame §2 (Nano Banana for sheets), diagram-in-states §2 (GPT Image Flare then Sunburst) and web-app §2 (Sunburst vs Nano Banana; `medium` quality) all name different models and qualities. VW-MAP overrides all three (film's picture AI, always high).
10. **Lint location.** RULEBOOK 17 points to `forms/answer-form.md` (not in the bundle) while VW-MAP points to `answer-form.videowizard.md`.
11. **Charts.** diagram-in-states §1 includes "chart" as a graphic-states subject. VW-MAP sends any number, size or count to the drawn route, and RULEBOOK §5 lists "real data charts" as never generated.
12. **Style source.** video-frame §3.4 and web-app §2 (palette by hex, repeated verbatim in every prompt) vs VW-MAP ("the style comes from the approved style picture"). diagram-in-states §3.4 and §6 also want hex in every prompt. Not overridden for graphics, but it does not fit the approved-style-picture rule.
