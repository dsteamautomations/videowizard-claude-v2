# design/135: each picture step reads only the guidebook sections it uses (design/134 finding 15)

2 Nov 2026. Status: **the keep-list below waits for SK's approval. Nothing is built.**

SK, 2 Nov: "this is the first step to make things better (wherein we encourage the AI to read only the relevant ones, which increases its focus)". The method was approved before this list: sections are pulled from the existing guidebooks by their heading when the step's files are packed (`library.steps`), with no split files, so there is still one copy of each text. The library snapshot is `server/library/vwlib-2026-10-29-3d60877d3d23/library/`.

## The rules used to choose
1. **A step's own playbook stays whole** (video-frame, web-app, diagram-in-states, video-clip). It is the step's instructions.
2. **A reference guidebook keeps the section the map (VW-MAP.md) names** for that step.
3. **A model fact sheet keeps Part B (how the model reads words) and Part C (evidence).** Part A is what the server sends to the model's API (models, settings, price, errors); the operator's AI never calls the API. The exception is a sub-section the map names (the Omni sheet's A5, for the start image's size).
4. **Sections that VideoWizard overrides or never uses are dropped**, because reading a rule the server forbids invites the mistake: audio, transitions, quality settings, transparent cut-outs, extending or editing clips, draft workflows, ad style libraries. Each is listed in VW-MAP's "Where VideoWizard overrides the library".
5. **"Evidence" and "Built from" sections are dropped everywhere.** They record where the text came from and teach nothing about writing.
6. **Held design/131 work is not touched:** de-slop.md stays whole, and the always-open files stay (see the option at the end).

## The keep-list, by step (words read: today → after)

| Step | Today | After | What is kept | What is dropped |
|---|---|---|---|---|
| Reference picture (a person, an object, a place) | 9,087 | about 3,640 | video-frame playbook; GPT sheet Part B and C; consistent-character-frames **Section 1 (the person variables)** | the character guide's nine-image workflow, style presets and eight batch rules (overridden: one sheet at the film's frame); the GPT sheet's Part A, B8 cut-outs and B9 quality |
| Frame from a clip | 782 | 150 | gap-fill **section 3 (the boundary-frame method)** | the rest of gap-fill (the step writes no prompt) |
| Scene still | 11,443 | about 5,320 | video-frame playbook; GPT sheet B and C; animatic-keyframes **section 2 (the keyframe card)**; gap-fill; de-slop (whole, held) | the animatic guide's density ladder, emotion, loaded frame, race-spot board and its other sections |
| Diagram still (labelled picture without figures; rare on motion films) | 8,444 | about 4,700 | web-app playbook; GPT sheet B and C; craft **section 5 (diagram grammar)**; 05-information (the examples, whole) | craft's seventeen other principles (posters, UI, multi-panel boards, JSON prompts) |
| Graphic state | 6,255 | about 2,550 | diagram-in-states playbook; GPT sheet B and C; craft **section 5** | craft's other principles |
| Start image of a video | 18,960 | about 5,070 | video-frame playbook; GPT sheet B and C; animatic **keyframe card**; gap-fill; character guide **Section 1**; Omni sheet **A5 (what goes in)** | the rest of the Omni sheet (it is for the take, not the picture); the animatic and character guides' other sections |
| End image | 5,393 | about 3,190 | video-frame playbook; GPT sheet B and C; gap-fill **section 3** | gap-fill's other sections |
| Video take | 9,955 | about 5,780 | video-clip playbook; camera-lighting vocabulary **without 8 (sound) and 11 (transitions)**; gap-fill; still-to-motion **when to use, pipeline, motion prompt formula, gotchas**; Omni sheet Part B and C **without B4 (editing a clip), B10 (extending), B12 (audio), B13 (draft workflow)** | the Omni sheet's Part A; still-to-motion's ad style libraries; the sound and transition vocabularies (every take is one silent, unbroken shot) |

Every step also reads the three always-open files (5,247 words): the rulebook, the VideoWizard answer form and deterministic-checks.md. Unchanged unless SK chooses the option below.

## The word-list (deterministic-checks.md): kept, trimmed (SK, 2 Nov: "I would like to retain this, but if there is an option to reduce or trim the words, we can try that")
It is copied from an advertising tool on GitHub (kwistzzqq-byte/image2-ads-studio, copied 19 Oct). VW-MAP names only its **section 1, the vague-word replacement table** (RULEBOOK rule 2). The always-open set keeps section 1 (about 490 words with the title) and drops sections 2 to 8 (about 2,050 words: presence checks, the ad tool's execution and repair rules, per-task generation requirements, **manufacturability rules for built signage**, and its compiled prompt order). design/131 C6 (retiring the `lint` field) stays on hold.

## Where the kept text comes from (SK's question, 2 Nov)
Read in each file's own provenance lines:

| Kept text | Source | Checked against real films? |
|---|---|---|
| video-frame, video-clip, web-app and diagram-in-states playbooks; gap-fill; RULEBOOK | written for this library on 19 to 21 Oct, assembled from the copied files | each says "draft, untested on a real job"; VideoWizard's corrections live in VW-MAP's overrides table and the server's checks |
| GPT Image and Gemini Omni fact sheets, Part B | written on 19 Oct from OpenAI's and Google's own pages, each line marked verified or third-party | Part C "Evidence from our jobs" is still empty in both |
| VideoWizard answer form | the VideoWizard variant, 22 Oct (design/69, approved by Revathi) | used on every picture; checked by the server |
| animatic-keyframes section 2, **the keyframe card** | **copied word for word from GitHub** (smixs/visual-skills, CC BY 4.0, 19 Oct) | **no**. It still carries the source author's race-advert rules ("amber-ban repeated" in the light field; a sound field, though every take is silent; captions like "proof-of-speed") |
| consistent-character-frames **Section 1, the person variables** | **copied from GitHub** (motiful/product-shots, MIT, 19 Oct), a fashion e-commerce method | **no**. It asks for a bag, jewellery, a studio backdrop colour, a 3:4 frame and a reference photo, where VideoWizard describes a worker from words at the film's frame |
| de-slop | copied word for word from GitHub (smixs/visual-skills) | held with design/131 |
| still-to-motion sections, camera-lighting vocabulary | copied from GitHub (coreyhaines31/marketingskills; smixs/visual-skills) | no |

**Recommendation:** the two copied sections a start image and a scene still read are replaced by short VideoWizard versions, written for documentary films of real work, before the trimming goes live: a still-picture card (about 150 words, with no sound, no race rules and no advert captions) and a person description for workers (about 150 words: build, age, skin, hair, work clothes and their wear, footwear, what they carry; at the film's frame, from words). They go into a new library snapshot (design/89 batch 4), SK approves their wording first, and the free comparison then shows the old and new reading side by side.

## How it is built, after approval
1. `library.STEPS` names a section by its heading, for example `('library/video/craft/animatic-keyframes.md', '## 2. The keyframe card')`. The packer copies from that heading to the next heading of the same level. A file with no heading named is copied whole.
2. **Test:** every named heading exists in the pinned snapshot, and each step's packed text contains the kept sections and none of the dropped ones. A renamed heading fails the test; a step never silently receives nothing.
3. **Free comparison:** the operator's Claude writes the prompts for three real VW-12 shots (a start image, a scene still, a take) twice, with today's reading and with the trimmed reading, and the two are compared side by side. No paid picture.
4. **Old way (design/35):** a whole guidebook per step is retired for runs prepared after the deploy. A run already in its visuals stage keeps its written files until `vw visuals prepare` runs again.
5. Server deploy only: the plugin writes whatever the server packs.
