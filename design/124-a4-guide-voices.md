# The prompt-writing guide against the server, the instructions and SK's decisions (design/124 A4, the guide)

Snapshot read: `server/library/vwlib-2026-10-21-4f88379be109/` (licences skipped). Read only; nothing in the repository changed.
Checked against: `server/app/library.py` (what is sent, the checks), `video_providers.py`, `visuals_stage.py`, `visual_contract.py`, `config.py`, `plugin/scripts/vw.py`, `server/procedures/v3.json` (visuals), design/124 (decisions 5, 9, 20; A2; A3) and `design/124-a3-disagreements.md`, design/122.

## What the assistant actually receives

- Always (`library.py:14` ALWAYS): `RULEBOOK.md`, `forms/answer-form.videowizard.md`, `agency/deterministic-checks.md` (the whole file), plus `VW-MAP.md` and `FIELD-SOURCES.md` (`library.py:91`, written by `vw.py:231-232`) and `agency/compliance-checklist.md` (`vw.py:229`, the plugin writes it for every film).
- Per step (`library.py:24-41`, `step_files` 100-105): every file listed for the step is sent whole, every time. The "Open when" conditions in VW-MAP (de-slop only for a photographic look, consistent-character-frames only for a person, still-to-motion only for a faceless explainer, gap-fill only next to footage) are not applied by the server: the files go out unconditionally.
- Never sent (no effect on prompts): `forms/answer-form.md`, `forms/job-form.md`, `feedback/README.md`, `feedback/record-template*.yaml`, `MANIFEST.json`. Yet two sent files point the assistant to `forms/answer-form.md` (item 15).

Counts: 24 numbered items below (7 tagged NEEDS-SK), plus 4 leads re-checked and found already handled, and 1 place where the guide is right and the server or the instructions are not.

---

## The list, worst first

### 1. The video request: the guide tells the assistant to write lines the server writes itself, and they can contradict each other
- **Guide.** `playbooks/video-clip.md` §5 (Omni template): "Camera: {one move}, {shot size}. … Audio: {room tone and one sound} | No dialogue. No music. In a single unbroken scene, no scene cuts. {n}s." §4 lists camera, audio, the single-scene line and the length as part of the brief. `RULEBOOK.md` §16.2 says the same. `video/models/gemini-omni-1-1/FACT-SHEET.md` A2: "The prompt is sent exactly as Claude writes it; nothing rewrites it."
- **Disagrees with.** `video_providers.py:19-35` (`motion_text`) wraps the assistant's brief: it adds the `[# Sources <FIRST_FRAME>@Image1 …]` tag line (23), a "surroundings stay alive" line (25), "Natural, unhurried motion…" (26), subject reconciliation and continuity (27-28), "Camera: … nothing else about the frame changes" or "Camera: locked off on a tripod; the frame does not move, drift, zoom or slide." from the plan's `camera_move` (30), the light line (32), "In a single unbroken scene, one continuous shot, no scene cuts, no jump cuts. No dialogue. No music. No captions or overlay text." (33), "Use Image1 as the starting frame… Preserve the depicted identities." (34) and the length "{n}s" (35). Nothing refuses camera words in the brief (`prepare_take` 3218 runs only `check_prompt`).
- **Effect.** Every take carries duplicated lines; worse, a brief that says "Camera: slow push-in" on a shot planned locked off goes to the paid model with "Camera: locked off on a tripod; the frame does not move" a few lines later. The model gets two opposite camera orders.
- **Fix.** Add a VW-MAP override line: "The motion brief is only what the subjects and the surroundings do; never write the picture tags, a Camera line, an Audio line, the one-take line or the length: the server writes them from the plan." Reword Omni A2 to "VideoWizard wraps the brief in its own lines (VW-MAP)".

### 2. VW-MAP's own list of the server's fixed video lines is out of date
- **Guide.** `VW-MAP.md` "Fixed lines the server appends": "Every video prompt gets: the subject reconciliation, the continuity notes, the requested duration, "Use the first image as the starting frame", the end-frame line when one is sent, and "Do not render editorial captions or overlay text into the video. Do not create narration, dialogue or music. …"". `video/models/higgsfield/NOTES.md` §2 quotes an older wording still: ""Requested duration: N seconds. Use the first image as the starting frame.""
- **Disagrees with.** `video_providers.py:23-35` (item 1): today's lines are different words and there are more of them (tags, ambient, natural motion, camera, light, gaze/heading/tool lines, the one-take line).
- **Effect.** The one place meant to stop duplicates names lines that no longer exist and leaves out the camera, light and one-take lines, so item 1 happens.
- **Fix.** Rewrite the VW-MAP section to list today's lines word for word (or by name: tags, ambient, natural motion, reconciliation, continuity, person lines, camera, gaze/heading/tool, light, one-take/no dialogue/no music/no captions, Image1/Image2 roles, length); remove the duplicate list from higgsfield NOTES §2 and point it to VW-MAP.

### 3. Audio, dialogue, music, several shots and transitions are asked for; the server switches all of them off
- **Guide.** `RULEBOOK.md` §16.6: "Audio is described or switched off. Dialogue is short, attributed to a visible action, and in quotes." `video-clip.md` §7 "Dialogue. Name the speaker by a visible action first, then the line in quotes." `video/craft/camera-lighting-vocabulary.md` §8: "Even if the model does not generate audio, sound description helps structure rhythm." §11: "Name the transition and the exact moment it fires. One transition type per cut." `video/models/kling/FACT-SHEET.md` §3: "Think in shots, not clips. Up to 6 shots in one generation on 3.0; label them `Shot 1: ... Shot 2: ...`". `seedance/FACT-SHEET.md` B4: music in `()`, effects in `<>`, dialogue in `{}`.
- **Disagrees with.** `video_providers.py:33` "No dialogue. No music. No captions or overlay text." and "no scene cuts, no jump cuts"; `:108` Kling `sound='off', multi_shots=False`; `:111` Seedance `generate_audio=False`. VW-MAP covers audio ("Always off, no narration, dialogue or music") but says nothing about shots, cuts or transitions, and it sends the assistant to Kling "section 3" by name.
- **Effect.** Sound lines and "Shot 1: / Shot 2:" or transition words in a brief fight the server's one-take, no-sound lines.
- **Fix.** Add a VW-MAP override row: "Several shots, cuts, transitions, sound and dialogue: never; every take is one unbroken shot with no sound (the server adds the line and switches sound off)." Change VW-MAP's Kling pointer from "section 3" to "section 3, except the multi-shot and audio lines".

### 4. Each video model's own prompt shape and tag syntax; the server sends one shape to all three `NEEDS-SK`
- **Guide.** `video-clip.md` §5 gives a separate Seedance template ("@Image 1 is the first frame; … 0-{a}s: {one action, visible end state}. …"); `seedance/FACT-SHEET.md` B2: "ByteDance's post uses `@Image 1` with a space. Use that."; B1: "Clip length, aspect and resolution go in the settings, not in the words." VW-MAP sends the assistant to "Seedance: … Part B".
- **Disagrees with.** `video_providers.py:20-23` builds "the library's Omni house shape" for every provider, including the Omni-only `[# Sources <FIRST_FRAME>@Image1]` tag (no space) for Kling and Seedance on Higgsfield, and appends the length in words (35) as well as the `duration` field (106).
- **Effect.** An assistant following the Seedance sheet writes `@Image 1` roles and timed windows inside a prompt that already starts with Omni tags; Kling and Seedance receive Omni syntax they may ignore or misread.
- **Fix.** Add a VW-MAP override: "One prompt shape for every video model (Omni's); the Seedance and Kling sheets' tags and templates are background only." SK decides separately whether the server should send per-model tags (a server change, not a guide change).

### 5. A guide template puts the video model's name into the picture prompt; the server refuses it
- **Guide.** `playbooks/video-frame.md` §5: "Asset: keyframe, shot {n} of {total}, for {video model} at {aspect}. Target aspect ratio: {16:9 | 9:16}."
- **Disagrees with.** `library.py:16` MODEL_WORDS ('omni', 'kling', 'seedance', …) and `:215-217`: "The prompt names a model …: the server chooses the model; describe the picture only." `RULEBOOK.md` §13 agrees with the server: "No model name inside a prompt."
- **Effect.** Every start image written from the template is refused once and rewritten.
- **Fix.** Reword the template line to "Asset: keyframe, shot {n} of {total}, at {aspect}."

### 6. A person's reference from footage pictures (decision 5: a person's sheet is made from words)
- **Guide.** `video/consistent-character-frames.md` Principles 1: "**Reference image is mandatory** — every image-generation call MUST pass `REFERENCE_IMAGE` as image input. Pure text descriptions are not allowed". `video/gap-fill.md` §3.1: "Grab the last frame of the real shot before the gap. Use it as the reference for the gap's first frame, or as the start image itself." `video-frame.md` §3.3: "the approved sheet tagged `person` with its consent id". `RULEBOOK.md` §14.1 and `compliance-checklist.md` C09 ask for consent ids. `answer-form.videowizard.md` lint 6: "a real face is a look reference only, never edited."
- **Disagrees with.** Decision 5 (design/124, SK 29 Oct): "the sheet is made from that description; a footage or web picture of a person is never sent to the picture AI." Stage instruction (v3 visuals): "A person from the footage or the web is never a parent for an edit nor copied". (Not built yet: `sheet_due`, `visuals_stage.py:1164-1176`, still lists every approved frame as a sheet source.)
- **Effect.** The guide pushes the assistant to send a person's footage frame with every call, the opposite of SK's decision; "look reference" is read as "send it, but don't edit it".
- **Fix.** Add a VW-MAP override line: "A person's sheet is made from words: describe the person from their footage pictures (use the fourteen variables of consistent-character-frames Section 1 as the checklist) and send no footage or web picture of a person; objects and places keep theirs." Reword lint 6 to "a real person's picture is never sent". `NEEDS-SK`: does decision 5 also cover the video AI, i.e. may a boundary footage frame that shows a person be a take's start image (gap-fill §3.1)?

### 7. "GPT Image for every image": the image model is chosen per film (design/120)
- **Guide.** `VW-MAP.md` overrides: "GPT Image 2.5 for every image: Flare to generate, Sunburst to edit | The server only calls OpenAI images (`visuals_stage.IMAGE_MODELS`)." Also "Images default to 1536×864, `high`." `FIELD-SOURCES.md` `model`: "Fixed by the server: GPT Image 2.5 for images". `00-method/de-slop.md` §2: "Nano Banana has no constraints slot". Model rows in `video-frame.md` §2, `web-app.md` §2 ("Nano Banana 2.1 for icon sets…") and `diagram-in-states.md` §2.
- **Disagrees with.** `visuals_stage.py:347-349` `provider_of(run)`: the run's image model, GPT Image or Gemini (`config.py:21` `gemini-3-pro-image`, Nano Banana Pro). On a Gemini film: 14 inputs with per-kind caps, not 16 (`:2169-2175`, `:2359`); no transparent output, a green key instead (`:2130`); no mask, the region in words (`:2237`); size is an aspect plus `2K`, not 1536×864 (`:2618-2620`). The only image sheet sent is GPT Image's (`library.py:18`), whose A4 sizes, A5 mask, B8 transparency and 16-input limit are wrong for that film. A2 group 4 (SK approved): "Correct to "the film's picture AI (GPT Image or Nano Banana)"".
- **Effect.** On a Nano Banana film the assistant writes to the wrong model's habits and limits, with no sheet for the model actually used. (Server side, for the builder: `library.job_form` at `library.py:131` still writes the GPT model id into the job form on a Gemini film.)
- **Fix.** Reword the VW-MAP row to "The film's image model (GPT Image or Nano Banana Pro, chosen when the film is created); the server picks the model, size, input limits and background"; same in FIELD-SOURCES. `NEEDS-SK`: add a Nano Banana Pro fact sheet to the next snapshot, sent on Gemini films instead of the GPT sheet?

### 8. The answer form's exact text is "one string per line"; the server refuses a string without place and size
- **Guide.** `answer-form.videowizard.md` field table: "`exact_text` | The copy strings that must appear in the image, one per line, letter for letter. The server checks each is in the prompt."
- **Disagrees with.** `library.py:167-193`: an entry is `{text, place, size_pct}`; "a bare string (the old form) loads with no place, and a new picture refuses it"; `check_exact_places` refuses an entry with no `place.landmark_id` or `place.region`, or no `size_pct`.
- **Effect.** An answer written from the form is refused for every picture with text.
- **Fix.** Reword the row: "`exact_text`: one entry per string to be read: `text` (letter for letter, also in the prompt), `place` (a landmark id of the scene or a frame region) and `size_pct` (its height as a percent of the frame)."

### 9. Quoted words outside the exact-text field
- **Guide.** `video/diagram-in-states.md` §6: "Labels re-spelt or reflowed on edit | List every existing label in the keep-list, in quotes". `RULEBOOK.md` §4.1: "Every string that must appear goes in quotes, exactly as approved." `00-method/craft.md` §1 "Exact text goes in quotes".
- **Disagrees with.** `library.py:199-205` `check_quoted`: quoted words of two or more not in `exact_text` are refused ("anything to be read in the picture goes in exact_text with its place and size"). Stage instruction (A3 item 1, approved): words to be read go only through `exact_text`.
- **Effect.** A keep-list with quoted labels ("keep "Mortar bed" and "Brick course"") is refused.
- **Fix.** Add a VW-MAP override line: "Words to be read go in `exact_text`; quote nothing else in a prompt; a keep-list names labels without quotes."

### 10. AI charts and numbered diagrams are taught; the server refuses any figure in an AI graphic
- **Guide.** The still-diagram step sends `00-method/craft.md` §5 "Data visualization mini-schema … Provide exact labels, panel names, legend values, units, and axis labels" and `prompts/05-information.md` (P027 "Transparent demo-data bar chart"). `diagram-in-states.md` §2: "Text is not a reason to avoid this route."
- **Disagrees with.** `visual_contract.py:626-629`: a diagram or animation shot whose claims carry a digit or a known size is refused: "an AI-painted graphic is for a look, never for a figure". A3 item 2 (approved): "any figure (a number, size or count) in a graphic's claims or spec takes the drawn route, so charts and measured diagrams are drawn."
- **Effect.** The step's guide files coach the assistant towards plans the plan check refuses.
- **Fix.** Add a VW-MAP override line: "A number, size or count in a graphic takes the drawn route; an AI graphic carries words only, never a chart." Remove P027 from the snapshot (see the trim list).

### 11. The end image: a camera move between start and end, a footage frame as the end, made at once as a pair
- **Guide.** `video-frame.md` §4 first-last-frame: "The first holds the composition at the start of the move, the last at its end. … "the camera whip-pans right from the drummer to reveal the dancer"". `gap-fill.md` §3.2-3: "grab its first frame as the reference for the end image. … Then `prepare-take --start R1 [--end R2]`." `VW-MAP.md` per-step row: "End image of a video shot (`image --kind keyframe`, `prepare-take --end`)".
- **Disagrees with.** `visuals_stage.py:2683-2685`: "The end image moves the camera …: the camera does not move between the start and the end". `:2255`: "An end image is an edit inside one region of its start". Decision 9: "the end image is made by the server after the operator approves the start" from `end_prompt`/`end_answer`/`end_region`. A2 group 1: "a start picture; an end picture only where it must be exact".
- **Effect.** An end written from the guide is refused (camera move, no region), or made from the wrong source (a footage frame, an unapproved start).
- **Fix.** Reword first-last-frame and gap-fill §3 for VideoWizard: "a start image; an end only where the final state must be exact, written with the start as `end_prompt` (an edit inside one region, same framing, no camera move); the server makes it after the start is approved." Reword the VW-MAP end row to name `end_prompt`, and gap-fill's command to `prepare-take --start R1` (`--end R2` only for an exact end).

### 12. Picture quality: "medium" and "draft first" against the server's one high-quality picture `NEEDS-SK`
- **Guide.** `de-slop.md` §6: "On GPT Image 2.5 stay at `quality: medium` for this kind of work." GPT sheet B9: "Start at an explicit `medium`. … Once it passes, test one step down". GPT sheet A1: Flare for "Drafts". Video drafts: `video-clip.md` §2 "Omni: draft at 360p, finish at 720p or above. Seedance: draft at 480p"; Omni B13 "3-4 draft variations in 360p"; Seedance B11.
- **Disagrees with.** `visuals_stage.py:2626` `'quality': body.get('quality') or 'high'`; the chat tool accepts `--quality` (`vw.py:1315`, 1553), so the assistant can lower it. VW-MAP: "Draft at low size, then final | One generation per attempt at the run's size" (covers drafts, but not quality).
- **Effect.** An assistant following de-slop passes `--quality medium` on photographic stills; following B9 it may re-run a passed picture one step down (paid).
- **Fix.** Add a VW-MAP override line: "Quality is the server's (high); never pass `--quality`." SK decides: always high, or medium for photographic stills as de-slop advises?

### 13. Words the rulebook bans are recommended elsewhere in the same bundle
- **Guide.** `craft.md` §3 example: ""style": "hyper-realistic commercial photography"", "render_flags": ["8K_UHD", "sharp_foreground", …]; §1: "If it must be readable, say `crisp`, `legible`"; §10: "`MAPPA-style digital 2D animation`, `Studio Pierrot Naruto-Shippuden aesthetic`." `camera-lighting-vocabulary.md` §7: "Fincher cold. … Deakins natural." `deterministic-checks.md` §1 replacements: "centered product, soft shadow, minimal text, crisp edges". GPT sheet B3: "say so: "photorealistic" or "real photograph"".
- **Disagrees with.** `RULEBOOK.md` §9: "Words that hurt: … "8K", "ultra-detailed", "hyper-realistic" …" and "Style anchors: translate a named studio, director, painter, magazine or brand into the visible technique". `de-slop.md` §3 bans `crisp`, `sharp focus`, `8K`; §4 "Do not ask for "realistic"".
- **Effect.** Two files in the same step folder give opposite advice; the assistant has to guess.
- **Fix.** Add a VW-MAP line: "RULEBOOK §9 wins over craft.md §1, §3 and §10, the camera vocabulary's named palettes and the replacement table's "crisp"." Better: drop craft §3 and §10 from the snapshot (trim list).

### 14. A race-spot project's look is sent with every scene still and start image
- **Guide.** `video/craft/animatic-keyframes.md` (sent at still-scene and start): "Constraint specific to the source author's project; not a general rule." then "cold combative palette … faces absent or unusably fragmented"; §7 "One motivated source dominates; about 70 % of the frame stays unlit"; intro: "a single drawn image that must carry one story-beat with **no motion and (usually) no face**."
- **Disagrees with.** `gap-fill.md` §1: "The AI shot must look as if it came from the same camera on the same day"; the server's measured real-light line under every keyframe (A3 item 23); people at work are the subject of most films (decision 20: "opens on the subject at work").
- **Effect.** Low-key, faceless, cold frames next to daylight phone footage, if the assistant follows the file.
- **Fix.** Trim the file to the keyframe card (§1-2) and the image-prompt section without the race rules, or add a VW-MAP line: "animatic-keyframes: the card only; its project constraints never apply."

### 15. VW-MAP and the rulebook name an answer form the assistant never receives
- **Guide.** `VW-MAP.md` "Always open": "`library/forms/answer-form.md` | The shape of the answer and the lint before `ready`." `RULEBOOK.md` §17: "The ten rules are in `forms/answer-form.md`."
- **Disagrees with.** `library.py:14`: ALWAYS sends `library/forms/answer-form.videowizard.md` ("design/71 F1: the VideoWizard cut of the form"); answer-form.md is never sent.
- **Effect.** The assistant is told to open a file it does not have; the VideoWizard cut does carry the ten-rule table, so no rule is lost, only a wasted search.
- **Fix.** Reword the VW-MAP row to `library/forms/answer-form.videowizard.md`, and add a line: "RULEBOOK §17's ten rules are the table in answer-form.videowizard.md."

### 16. Which video model to use: the guide decides, the server and the plan decide
- **Guide.** `RULEBOOK.md` §1.4: "Decide the model from the job form or the "when to pick" rules in the fact sheets." `video-clip.md` §2: "Omni 1.1 Flash … for anything that needs 1080p or 4K. Seedance 2.5 … for 1:1, 4:3 or 21:9. Kling 4.0 when its API opens."
- **Disagrees with.** `video_generators.py:10-21`: Omni by default, Kling 3.0 Standard (3-15 s) and Seedance 2.5 (4-30 s) on Higgsfield; VideoWizard films are 16:9 or 9:16 only. A3 item 17 (approved merge): another generator "only when a shot is longer than the default makes and its one action cannot be cut; otherwise split it."
- **Effect.** Invites switching generator for resolution or aspect reasons that do not exist here.
- **Fix.** Add a VW-MAP override row: "Model choice | Omni by default; Kling or Seedance only when a shot is longer than Omni's 10 s and its one action cannot be cut | `video_generators.CATALOG`; the server fixes resolution and aspect."

### 17. Kling, Veo and Higgsfield facts are out of date `NEEDS-SK`
- **Guide.** `kling/FACT-SHEET.md` title "Kling 4.0 watch file" and "Omni 1.1 Flash and Seedance 2.5 carry video work until then." `camera-lighting-vocabulary.md` §8: "For Veo, wrap sound in syntax." `higgsfield/NOTES.md`: "server 0.21.3", "Status: **draft, untested, for SK's decision.**", open question 1 "Is Higgsfield a chosen route?", question 2 "VideoWizard's ₹1,000 visuals cap".
- **Disagrees with.** `video_generators.py:14-16` calls Kling 3.0 Standard on Higgsfield today; Veo is shut down (Omni sheet A1) and not a route; server is 0.72.0 (`config.py:20`); A2 group 6 lists R1193, R1252, R1800, R1866, R1895, R1906, R1910 for this snapshot.
- **Effect.** The Kling shot gets advice for a model it is not using; stale questions read as open decisions.
- **Fix.** Replace the Kling watch file in the bundle with a short "Kling 3.0 on Higgsfield as VideoWizard calls it" note; remove the Veo line; refresh higgsfield NOTES to today's server. SK answers NOTES Q1 (is Higgsfield a chosen route), Q3 and Q4 or marks them closed.

### 18. The spending cap: ₹1,000 in the guide, ₹5,000 in the code, none by SK's decision `NEEDS-SK`
- **Guide.** `VW-MAP.md`: "The ₹1,000 visuals cap (design/65 S6); the operator approves each result." `answer-form.videowizard.md` lint 10: "the estimated cost under the spend cap | The server's cap check." `FIELD-SOURCES.md` `spend_cap_usd`. higgsfield NOTES Q2.
- **Disagrees with.** `config.py:50` `VISUALS_CAP_INR = 5000.0`, refused in `visuals_stage.py:382-388`; design/122 question 3 (SK, 29 Oct): "no spending limit on any film" (not built yet).
- **Effect.** Wrong figure today; the whole rule goes when design/122 is built.
- **Fix.** Remove the cap from the VW-MAP reason ("the operator approves each result" stays), lint 10, FIELD-SOURCES and NOTES in the same release as design/122. SK confirms the timing.

### 19. consistent-character-frames is a nine-photo fashion method; the server makes one sheet in the film's frame with the plan's views
- **Guide.** Principles 7-8: "**Pause for style selection** … present the 3 presets (do not auto-pick a default)." "**Batch generate by default** — produce all 9 images in a single batch". Section 1: default aspect 3:4. Rule 1: every prompt carries a `[Reference image: …]` header. `craft.md` §7: "front/side/back views"; `video-frame.md` §4: "front, three-quarter and side".
- **Disagrees with.** `visuals_stage.py:1181-1191` `sheet_block`: one sheet with "the views {required_views}" from the plan, "each labelled; … alone on plain ground"; one picture per call at the film's frame (`_queue_image`, `:2614-2626`); `library.image_names_missing` (`library.py:252`) wants "Image k" names, not a header. Stage instruction: questions one at a time; the style comes from the approved style picture.
- **Effect.** A style-preset question to the operator, a 3:4 or nine-picture plan, or three different fixed view sets, none of which the server makes.
- **Fix.** Trim the file to Section 1's variable table (used for decision 5's description) and Rule 3 (hairstyle); add a VW-MAP line: "a sheet shows the plan's `required_views`".

### 20. Pointers to files that are not in the bundle
- **Guide.** `RULEBOOK.md` §14.3: "The full list is DIRECTION section 5d." `craft.md` §0: "Open `gallery/README.md`, then read nearby cases". `animatic-keyframes.md` intro: "`seedance.md` / `kling.md` / `veo.md` to animate each locked frame". `camera-lighting-vocabulary.md` §11: "templates in `seedance-25.md` §10". `video-frame.md` §3.1: "A shot list template is in the job form notes"; §4: "the thumbnail rules from the social playbook".
- **Disagrees with.** The bundle (none of these files is in it); VW-MAP: "Everything not in this bundle is the library's shelf and is never opened during a run."
- **Effect.** Dead ends; the assistant may say a rule "is missing" in its `suggestion` every time.
- **Fix.** Add a VW-MAP line: "A file or section named in a library file but not in this bundle is not available; work from what is here." (Optionally remove craft §0.)

### 21. FIELD-SOURCES describes a job form the server does not fill that way
- **Guide.** `FIELD-SOURCES.md`: `mode` "`edit-with-identity` when an approved person sheet is attached"; `mandatory_text` "From the client card's mandatory lines, if any"; `variants` "1"; `avoid` "Earlier rejected pictures for this shot, with the operator's reasons"; "Names in code are as of server 0.21.3 plus design/65."
- **Disagrees with.** `library.py:123` (end step is always `edit-with-identity`, state always `edit`), `:139` `'mandatory_text': 'none'`, `:142` `avoid` = the foundation's `editing_constraints`, `:143` `variants: 1` while `visuals_stage.py:2238-2240` allows two for a start; server 0.72.0.
- **Effect.** The assistant reads the form's values against a description that does not match; compliance C03 ("The sector's mandatory text is in the copy list") can never be met because the form always says none.
- **Fix.** Rewrite the four rows to what `library.job_form` does and drop the version line. `NEEDS-SK` (server side): should `mandatory_text` really come from the client card, as FIELD-SOURCES and C03 say?

### 22. Handoff notes, storyboards and cover frames that VideoWizard does not use
- **Guide.** `video-frame.md` §6: "What travels with every frame, in the answer form's notes: shot number and intended seconds; the camera move; …; the audio reference; the transition". §4 storyboard and cover-frame; §2 "The client approves the shot order on the storyboard".
- **Disagrees with.** `answer-form.videowizard.md` has no notes field; VW-MAP: "Storyboard grids, cover frames | Not used". The plan carries shot, seconds and camera.
- **Effect.** Small: the assistant may invent a notes field or plan a storyboard step.
- **Fix.** Add "Answer-form notes: not used; the plan carries the handoff" to the VW-MAP override table, or trim §4 storyboard/cover-frame and §6 from the snapshot.

### 23. The compliance checklist expects a second signer and consent ids
- **Guide.** `compliance-checklist.md` Status: "A second person signs it." C09: "No real person unless client staff with a written consent record id."
- **Disagrees with.** VW-MAP: "`checked_by` person or auto | Always person: the operator's yes or no"; `FIELD-SOURCES.md`: "VideoWizard has none today, so real faces are not edited"; decision 5. The checklist is written for every film (`vw.py:229`), not only for the five industries VW-MAP names.
- **Effect.** Rules the operator cannot meet; noise on films with no compliance industry.
- **Fix.** Add a VW-MAP override: "Compliance: the operator alone signs; C09 is met by decision 5 (no real person's picture is sent)." Builder note: write the checklist only for the industries VW-MAP lists.

### 24. "Centre" as a composition word; the server refuses a bare centre
- **Guide.** `deterministic-checks.md` §2: "`compositionSpecified` | composition, subject, center, left, right, …". `diagram-in-states.md` §2: "where each part sits (left third, centre, lower band…)".
- **Disagrees with.** `library.py:224-228`: "centre/center/middle" with no landmark and measured distance is refused ("say the landmark and how far from it").
- **Effect.** An occasional refusal of a diagram state that places a part "in the centre".
- **Fix.** Add a VW-MAP line: "A place is a landmark and a measured distance; "centre" alone is refused."

---

## Leads re-checked and found already handled (keep as they are)
- RULEBOOK §1.2 "Open only what `INDEX.md` says": VW-MAP line 3 already reads "Where `RULEBOOK.md` says "open only what INDEX.md says", read "what this map says"".
- RULEBOOK §5 "reserve an empty area" for the logo: VW-MAP's logo row overrides it, and `check_prompt` (`library.py:212-214`) refuses a logo.
- Storyboard grids, cover frames, low-size drafts: VW-MAP override rows cover them (only the cap reason is wrong, item 18).
- Audio switched off: VW-MAP's audio row is right; only cuts and transitions are missing (item 3).

## Where the guide is right and the server or the instructions are not
- One change per edit. `RULEBOOK.md` §8.1 "One change per turn", GPT sheet B5, `answer-form.videowizard.md` "`single_change` … the one change" agree with A3 item 15 (approved: "Keep "one change per edit""). But `library.py:232-236` lets an edit name two changes, and the v3 visuals instruction says "One change, two at most, per edit." Keep the guide; correct the server check and the instruction.

---

## Guide files the assistant receives that are mostly irrelevant to VideoWizard (candidates to trim)

Shares are approximate (by section length).

| File | Sent at | Relevant share | What is relevant | What is not |
| --- | --- | --- | --- | --- |
| `playbooks/web-app.md` | still-diagram | about 15 % | the process-explainer task note and prompt lines | heroes, icon sets, device mockups, app-store panels, email headers, wireframes |
| `prompts/05-information.md` | still-diagram | about 20 % | the structure of P025 and P030 (staged explainer, process slide) | classroom cards, tasting wheel, walking map; P027's chart is a refused route (item 10) |
| `agency/deterministic-checks.md` | always | about 30 % (sections 1-2) | the vague-word table and the presence checks | sections 3-8: ad-agency task types, signage manufacturability, compiled prompt order; VW-MAP itself says "section 1" |
| `video/consistent-character-frames.md` | reference, start | about 15 % | the variable table (for decision 5's description) and the hairstyle rule | the nine-frame fashion series, three style presets, crop table, batch rule, 3:4 |
| `video/craft/animatic-keyframes.md` | still-scene, start | about 30 % | the keyframe card and the image-prompt order | the race-spot palette and faceless rules, the 18-26 panel staircase, the worked race example |
| `video/still-to-motion-pipeline.md` | take | about 25 % | the style formulas and the motion formula | script, TTS, captions, loudness and assembly (VideoWizard does these elsewhere) |
| `00-method/craft.md` | still-diagram, state | about 35 % | sections 1, 2, 5 (diagram grammar without the chart schema), 12, 13 | gallery routing, JSON render flags, UI specs, poster hierarchy, studio style anchors |
| `video/models/seedance/FACT-SHEET.md` | take (Seedance) | about 45 % | Part B wording habits | Part A (40 %): OpenRouter calls, prices, polling, watermark (higgsfield NOTES: Part A "does **not** apply") |
| `video/models/gemini-omni-1-1/FACT-SHEET.md` | take (Omni, the default) | about 50 % | Part B camera, motion and continuity habits | Part A (42 %): calls, prices, edit and extend; B12-B13 audio and drafts |
| `video/models/kling/FACT-SHEET.md` | take (Kling) | about 20 % | section 3 wording habits, minus multi-shot and audio | the Kling 4.0 watch notes and monthly check |
| `models/gpt-image/FACT-SHEET.md` | every picture step | about 55 % (none on a Nano Banana film) | Part B | Part A (40 %): API settings, prices, waits, which the server owns |
| `playbooks/video-frame.md` / `playbooks/video-clip.md` | picture and take steps | about 55 % each | keyframe, continuity kit, motion brief, checklists | storyboard, keyframe-set, cover frame, handoff notes; clip-from-text, clip-edit, clip-extend, UGC, dialogue |
| `agency/compliance-checklist.md` | every film | about 40 %, and only for the five industries | sector lines C01-C08 | second signer, consent ids, delivery sign-off |

Not covered: the guide files were checked against the server code and the documents named above, not by running any prompt; whether the paid models actually misread duplicated or conflicting lines (items 1-4) is inferred from the text, not tested. The 683 unflagged library rows of the rule list were not re-read one by one; only the 200 flagged rows and the leads were.
