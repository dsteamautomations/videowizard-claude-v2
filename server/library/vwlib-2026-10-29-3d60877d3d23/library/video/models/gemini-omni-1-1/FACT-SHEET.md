# Gemini Omni 1.1 Flash fact sheet

Status: written 2026-10-19 from Google's own pages. Every line is marked. `[verified: page]` means the words were read on that Google page on 2026-10-19. `[Google, conflict]` means two Google pages disagree and both are shown. `[third-party]` means the line comes from other users' notes in this library, not from Google. `[test]` means Google does not say and we must try it. Part C is empty until jobs run.

Pages used, short names:
- O = https://ai.google.dev/gemini-api/docs/omni (page dated 2026-09-23)
- M = https://ai.google.dev/gemini-api/docs/models/gemini-omni-flash (2026-08-27)
- $ = https://ai.google.dev/gemini-api/docs/pricing (2026-10-16)
- C$ = https://cloud.google.com/gemini-enterprise-agent-platform/generative-ai/pricing
- I = https://ai.google.dev/api/interactions-api
- D = https://ai.google.dev/gemini-api/docs/deprecations
- CH = https://ai.google.dev/gemini-api/docs/changelog
- L = https://ai.google.dev/gemini-api/docs/rate-limits
- E = https://ai.google.dev/gemini-api/docs/api-errors
- CL = https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/gemini/omni-1-1-flash (2026-10-16)
- CT = https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/video/generate-videos-from-text
- CC = https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/content-credentials
- MC = https://deepmind.google/models/model-cards/gemini-omni-flash/
- PG = https://deepmind.google/models/gemini-omni/prompt-guide/
- PP = https://deepmind.google/models/gemini-omni/
- B = https://blog.google/innovation-and-ai/technology/developers-tools/build-with-gemini-omni-1-1-flash/ (2026-08-27)

This is the main video model in use. Decision in `models/CHOSEN-MODELS.md`. The raw material behind this sheet is `vendor-notes.md` in this folder; this sheet is the only file read during a job.

---

## Part A. The API: what the application sends

### A1. Model ids and status

| Id | Where | Status | Source |
| --- | --- | --- | --- |
| `gemini-omni-1.1-flash` | Gemini API, direct | Stable. "generally available to developers on the paid tier of the Gemini API". Released August 27, 2026. "No shutdown date announced". | [verified: M, $, D, CH] |
| `gemini-omni-flash-preview` | Gemini API | The earlier model. Shutdown date October 22, 2026. Replacement: `gemini-omni-1.1-flash`. Do not use. | [verified: D, CH] |
| `gemini-omni-1.1-flash-preview` | Google Cloud Agent Platform only | Preview. Same release date. Not our route. | [verified: CL] |

No dated snapshots exist for this model, unlike GPT Image. [verified: M, CL]

Veo: the three Veo 3.1 preview models shut down on October 22, 2026 and Google names `gemini-omni-1.1-flash` as the "Recommended replacement" for each. Veo 3.1 Lite, Fast and Standard are not a fallback. [verified: D]

Google calls the page and the family "Gemini Omni Flash" and uses the name "1.1" rarely. The id is what matters. [verified: O, M]

### A2. How to call

| Route | Notes | Source |
| --- | --- | --- |
| Gemini API, Interactions API | `POST https://generativelanguage.googleapis.com/v1beta/interactions` with header `x-goog-api-key`. Body: `model`, `input`, `response_format`, `generation_config`, `previous_interaction_id`, `background`, `store`, `stream`. Python `client.interactions.create(...)`, JavaScript `ai.interactions.create({...})`. | [verified: O, I] |
| Google Cloud Agent Platform | Same model as a Preview, through GenerateContent API or Interactions API, with Cloud terms, Cloud pricing and Cloud ids. | [verified: CL] |

Decision for this library: Gemini API, direct, with one Google key shared with Nano Banana. The prompt is sent exactly as Claude writes it; nothing rewrites it. [verified: O; house decision]

### A3. Settings on every call

| Setting | Allowed values | Default | Notes | Source |
| --- | --- | --- | --- | --- |
| `model` | `gemini-omni-1.1-flash` | | | [verified: O] |
| `input` | one string, or a list of parts: `{"type":"text","text":...}`, `{"type":"image","data":<base64>,"mime_type":...}` or `{"type":"image","uri":<Files API uri>}`, `{"type":"video","uri":<Files API uri>}` or inline base64 | | Media parts come before the text part in every Google example. Order of images sets their numbers. Google recommends the Files API for video because files are large. | [verified: O] |
| `response_format.type` | `"video"` | | Optional in Google's examples. | [verified: O, I] |
| `response_format.aspect_ratio` | `"16:9"`, `"9:16"` | `16:9` | Only these two. No 1:1, no 4:5. | [verified: O, I, CL] |
| `response_format.resolution` | `"360p"`, `"720p"`, `"1080p"`, `"4k"` | `720p` | 1080p and 4k are "upscaled". 360p is for drafts. | [verified: O, I] |
| `response_format.delivery` | `"inline"`, `"uri"` | inline | Use `uri` for outputs over 4 MB, which means anything above 720p. Then poll the Files API until `ACTIVE`. | [verified: O, I] |
| `response_format.duration` | string | not stated | The API reference lists the field with no values. The Omni guide never uses it. The Cloud guide says integers 3 to 10 followed by `s`, for example `"10s"`, for the Cloud id. Google's own Python SDK docstring says the type "is not supported in Gemini API". | [Google, conflict: I, CT, github.com/googleapis/python-genai] [test] |
| `generation_config.video_config.task` | `text_to_video`, `image_to_video`, `reference_to_video`, `edit`, `extend` | inferred from the prompt | Google: "We recommend relying primarily on prompting and using the `task` parameter only when prompting doesn't work", because `task` "adds some constraints". | [verified: O, I] |
| `previous_interaction_id` | id of an earlier call | | Carries the generated video into the next turn for an edit or extension without re-uploading. Fails with 400 if that call is still `in_progress`. | [verified: O, I] |
| `background`, `store`, `stream` | true or false | | Google: set all three to `false` "for faster, synchronous unary generation". But `store=false` means the video "won't be editable in subsequent turns". Our loop edits, so keep `store=true`. | [verified: O] |
| Not supported on the Gemini API | system instructions, temperature, `top_p`, stop sequences, negative prompt field | | Put all control in the prompt words. The Cloud page lists temperature and topP defaults for its own id; ignore them. | [verified: O; CL] |

Files API, for videos to edit or extend: upload with `client.files.upload`, poll `client.files.get` while state is `PROCESSING` (Google's example sleeps 10 seconds), stop on `ACTIVE`, treat `FAILED` as an error, then pass `{"type":"video","uri":file.uri}`. [verified: O]

### A4. What comes out

- One video with an audio track, mp4. Length 3 to 10 seconds at 24 frames per second. [verified: M, O]
- Where it is: SDK field `interaction.output_video.data` (base64) or `.uri`. In raw REST, read `steps` → the `model_output` step → the `video` part. [verified: O, I]
- With `delivery: "uri"` the part carries a Google-hosted `uri`; poll `files.get` until `ACTIVE` (Google's example sleeps 5 seconds), then download. Fetching the interaction again later returns inline base64 even if `uri` was asked; the `uri` is only guaranteed in the first response or the stream. [verified: O]
- Status values of an interaction: `queued`, `in_progress`, `requires_action`, `completed`, `failed`, `cancelled`, `incomplete`. [verified: I]
- Extension: appends to the end only. Each extension uses "the last 10s of your original video as context". Total length up to 40 seconds. Google's Omni guide says each continuation is "3 to 10 second"; the blog and the consumer guide say "10-second increments". [Google, conflict: O vs B, PG] [test]
- "Some of the final frames in your input video will be edited to make the transition seamless." Keep the approved clip; the extended file is a new version. [verified: O]

### A5. What goes in

| Input | Limit | Source |
| --- | --- | --- |
| Images per call | 10 | [verified: CL; the Gemini API page states no count] |
| Image file size | 20 MB inline. An older Cloud page says 20 GiB for the earlier model; treat 20 MB as the working limit. | [Google, conflict: CL vs older Cloud page] |
| Image types | png, jpeg, webp, heic, heif | [verified: CL] |
| Image pixel size | Not published. Google: "use high-resolution images". No crop or pad rule is published for a mismatched aspect. Output aspect is set by `aspect_ratio`, not inferred from the image on the Gemini API. | [verified: O; gap] [test] |
| Videos per call | 3 | [verified: CL] |
| Uploaded video length for edit or extend | 10 seconds or less, "unless extending videos generated by the model in multi-turn" | [verified: O, CL] |
| Video types | flv, quicktime, mpeg, mpegs, mpg, mp4, webm, wmv, 3gpp | [verified: CL] |
| Video references | up to 3 clips, up to 3 seconds each; "any audio in a video reference is ignored"; "work best with likenesses" | [verified: O] |
| Audio input | Not supported on the API. "Uploading audio references is unsupported in the current version of the API." The Cloud page marks Audio "Not supported". The consumer apps accept audio; the API does not. | [verified: O, CL, M] |
| People | "Uploading and editing images containing certain recognizable people is not supported." Minors: not in the European Economic Area, Switzerland and the United Kingdom. | [verified: O] |
| Region rules | Editing or extending uploaded videos is not available in the EEA, Switzerland and the UK. Editing videos the model generated is. | [verified: O] |
| Not accepted | YouTube links as a source. Reasoning across several videos: "may result in degraded model performance". | [verified: O] |
| Language | "English (EN) is fully supported, but other languages have not been evaluated". | [verified: O] |

### A6. Price

Billing is by output tokens. Google states the token rate per second of video for each resolution on the Cloud pricing page, and prints a per-second dollar table only as an image on the launch blog. The two agree.

| Resolution | Tokens per second of video | Price per second | Ten-second clip | Source |
| --- | --- | --- | --- | --- |
| 360p | 1,931 | $0.03 | $0.30 | [verified: C$; B image table] |
| 720p | 5,792 | "approximately $0.10" | $1.00 | [verified: $, C$, B] |
| 1080p | 8,688 | $0.15 | $1.50 | [verified: C$; B image table] |
| 4k | 17,376 | $0.30 | $3.00 | [verified: C$; B image table] |

Rates per million tokens, paid tier: video output $17.50; text output including thinking $9.00; input $1.50 for text, image, video and audio. Input is counted at 1,120 tokens per image and 5,792 tokens per second of input video. [verified: $, C$]

No free tier for this model. No batch pricing for Omni. Google AI Studio use is free, so manual trials can happen there. [verified: $]

What the application must do: store the `usage` token counts from every response so the feedback log can report real cost per usable clip.

### A7. Limits, waits, errors

- Context window 1,048,576 tokens on the Gemini API. The Cloud page lists 131,072 in and 57,920 out for its own id. Prompts are never near either. [verified: M, CL]
- Rate limits: not published per model. "can be viewed in Google AI Studio" on the account's own dashboard. Tier spend caps per rolling 10 minutes: Tier 1 $10, Tier 2 $50, Tier 3 $200. At $1 per 10-second clip, Tier 1 allows about ten clips per 10 minutes. Check the dashboard before the first batch. [verified: L]
- Generation time: "Video generation times vary based on duration, resolution, and current API load." The Cloud guide says "Video generation can take over a minute to complete." Ordinary HTTP requests "typically close after 60 seconds". So either run with `background=true` and poll `GET /v1beta/interactions/{id}`, or set a long client timeout. Decision: background plus poll every 10 seconds. [verified: O, CT, background-execution page] [house decision]
- Errors: standard codes on the errors page, among them `rate_limit_exceeded` 429, `deadline_exceeded` 504, `invalid_request` 400. Retry only 429, 408 and 5xx. Never retry a 400 unchanged. A blocked generation returns a block code; no video-specific codes are published. [verified: E, troubleshooting page]
- Safety: "Omni applies content safety filters to both input prompts and generated video (which vary by region). Prompts that violate usage policies are blocked." [verified: O]
- Provenance: "All generated videos include SynthID watermarking". C2PA Content Credentials are documented for the Cloud ids, not stated for the Gemini API id. No disclosure duty for developers is written on any Google page read; our own disclosure policy applies. [verified: O, CC; gap]
- Voice: "Voice editing is not supported." You cannot extend an uploaded video where someone is talking to add dialogue. Multi-turn extension of a generated video can add speech. [verified: O, MC]

---

## Part B. How this model reads words

### B1. Prompt shape

Google's own guidance is lighter than for Veo: "With Veo, you need to share precise instructions to get the best results. But with Gemini Omni, you don't have to be as prescriptive with your prompt." It asks for five things: shot framing and camera motion, style, lighting, location, action. "Write prompts with details like scene description, camera movement, lighting and mood for best results." [verified: PG, O]

House shape for our main case, an approved still animated into a clip. The frame already holds identity, composition, text and product. The prompt is a motion brief, not a retelling of the picture. [third-party: `models/nano-banana/smixs--visual-skills.md` Keyframes section; agrees with Google's image-to-video note]

```text
<FIRST_FRAME> {one line naming the scene as it is in the image}.
Camera: {one move: static | slow push in | pull back | pan left | tracking shot | orbit}.
Subject motion: {what the subject does, with one physical detail}.
Environment motion: {steam, light flicker, fabric, leaves; one or two}.
Continuity: keep the product label, colours and the text in frame unchanged. {five character traits if a person}.
Audio: {room tone and one sound} | No dialogue. No music.
In a single unbroken scene, no scene cuts. {N}s.
```

For a fresh text-to-video clip, add the scene and subject lines first, then the same camera, motion, continuity and audio lines.

### B2. Defaults you must override

| Default | What to write | Source |
| --- | --- | --- |
| Several shots and a story: "By default Omni Flash will try to create a video with a few different shots." | "In a single unbroken scene", "In a single continuous shot", "No scene cuts", or "continuous smooth shot" | [verified: O] |
| An audio track is generated by default | Describe the audio you want, or "No dialogue. No embellishments. No extra sound effects." For music: "Include calm background music" or "No music, just realistic sound." | [verified: O, PP] |
| Landscape 16:9 | Set `aspect_ratio` to `"9:16"` in the settings for stories and shorts. Not in the prompt. | [verified: O] |
| Task inferred from the prompt | Usually fine. Set `task` only when a prompt keeps being misread. | [verified: O] |
| Clip length picked by the model | End the prompt with a length, as Google's own examples do: "10s", "Entire story in 10 seconds". Also try the `duration` field. Record which one held. | [verified: PP, PG examples] [test] |

### B3. Negatives go in the prompt text

There is no negative-prompt field. "you can put your negatives in the regular prompt: e.g., "Do not do X"". Google's own examples: "Don't add seahorses. No voice cuts at the end. Don't add text." and "no hands". Keep negatives short and specific. [verified: O, PP]

### B4. Editing a clip

- "Simple prompts work best for video editing. Overly descriptive prompts can lead to unintended changes." [verified: O]
- Always close with "Keep everything else the same." Google's examples: "Make the phone invisible. Keep everything else the same." "Add a cat that jumps onto his lap, he begins to pet it. Keep everything else the same." [verified: O]
- One change per turn. Send `previous_interaction_id`. Each turn makes a new video; "the model applies the edit while preserving the parts of the video you want to keep". [verified: O]
- Short edit prompts Google shows working: "Make this video anime", "Change the lighting to be more dramatic", "Change the text on the sign to say "Omni Flash"", "Put a fashionable hat on this person", "Change the camera angle to be over the violinist's shoulder". [verified: O, PG]
- Event-triggered edits on real footage: "When the hand opens, reveal ... No music, just realistic sound." and "keep the video the same until the hand opens". [verified: PP]
- Known limit from the model card: "maintaining complete consistency throughout edits ... remains a challenge." Compare every edit against the approved version, not the previous edit. [verified: MC]

### B5. Timing inside the clip

"You can prompt for things to happen at specific times in the video, there is no precise syntax needed and you can use natural language." Examples: "After 3 seconds, a woman enters the scene." "Every 2s cut to a new frame." Timecode form: "[0-3s] A person is walking / [3-6s] They stop and turn around / [6-10s] They start running". Frame counts work too: "every half a second (12 frames at 24fps)". [verified: O, PP]

In an extension, "0s refers to the beginning of the extended part of the video." [verified: O]

### B6. Text inside the video

- Say exactly what any visible text reads, even background signs: "There is a street sign that says: "This is an AI generation by Omni"". Quote it. [verified: O]
- Word-by-word animated text works: "One word on the screen at a time: "did, you, know, ..." Each word appears for 1s with a different animated style. No dialogue." [verified: O]
- Model card: "rendering perfectly accurate text remains a challenge." Read every character after generation. Our rule stands: the client's logo and legal text are never generated. [verified: MC; house rule]

### B7. Naming the pictures and clips you send

Google binds media to roles with tags. Two forms. [verified: O]

Simple form, when roles are obvious:
- `<FIRST_FRAME>`: "use the image as the starting frame of the video".
- `<LAST_FRAME>`: "use the image as the final frame of the video to transition to. Must be used with `<FIRST_FRAME>`".
- `<IMAGE_REF_N>`: "use the image as a reference". Numbering starts at 0. Example: "in the style of <IMAGE_REF_0> a woman <IMAGE_REF_1> is walking".
- `<VIDEO_REF_N>`: "use the video as a character or object reference". Numbering starts at 0.

Declared form, for several inputs with several roles, placed at the start of the prompt:
- `[# Sources <FIRST_FRAME>@Image1 <LAST_FRAME>@Image2]`
- `[# Sources <FIRST_FRAME>@Image1 <LAST_FRAME>@Image1]` makes a loop.
- `[# Sources <VIDEO_0>@Video1]` names the video to edit. `[# Sources <PREVIOUS_VIDEO>@Video1]` names the previous turn's video to extend.
- `[# References <IMAGE_REF_0>@Image1 <VIDEO_REF_0>@Video1]`
- Media handles `@Image1`, `@Video1` count from 1; `<IMAGE_REF_N>` counts from 0. So the second uploaded image is `@Image2` and can be `<IMAGE_REF_1>`.
- Close with a plain sentence: "Use Image1 as the starting frame. Use Image2 as a reference for the video generation." or "Use the given image(s) as references for video generation. The images should not be used as literal initial frames."

Without tags, with two images, the first is the start frame and the second the end frame. With reference images and no tags, "the model will decide how to use the image". Use tags on every client job so nothing is left to the model. [verified: O; house rule]

Our tag list maps as: `approved` and `product` for a start frame → `<FIRST_FRAME>`; `product`, `person`, `style` as references → `<IMAGE_REF_N>`; a short clip of a person or product → `<VIDEO_REF_N>`. Only two aspect ratios exist, so a 1:1 or 4:5 start frame must be re-framed to 16:9 or 9:16 before it is sent. [house mapping; see BUILD-PLAN Part 3]

### B8. Image to video

"For best results with image-to-video, use high-resolution images and provide specific motion descriptions. Vague prompts like "make it move" produce less compelling results than detailed descriptions of the camera movement, subject motion, and environmental effects." Google names the use: "bringing product shots, illustrations, or photographs to life". A drawing can guide motion without appearing: "turn this into realistic footage, using the drawing only as a guide for movement, do not show the drawing in the final video". [verified: O]

### B9. First and last frame

"Clearly define what is in your initial frame, specify the exact camera movement or transition path that takes place in between, and state precisely what the final frame should reveal." Best for "complex camera orbits, zoom transitions, or seamless looping clips". Same image as both frames gives a loop. Close with "One continuous shot, no jump cuts." [verified: PG, B, O]

### B10. Extending a clip

- Phrases that work: "Extend this video", "The scene continues", "Continue the scene: the camera pans across the mountains". [verified: O]
- Say whether the scene continues or cuts: "Show the same characters in the next scene". [verified: O]
- Describe the audio in the extension, "especially if you need it to change: "The music continues into the chorus"". [verified: O]
- References can be added during an extension: "The person shown in the reference image enters the scene", "The dog in the reference video <VIDEO_REF_0> jumps onto the sofa". [verified: O]
- Google's own chains use one camera verb and one beat per extension: "Camera slowly pulls out, forgotten dusty catacombs, dramatic music score." [verified: B]
- Set `task: "extend"` only if the prompt alone does not trigger extension mode. [verified: O]

### B11. Camera and continuity words Google uses

Camera: "one continuous shot" or "oner"; "static", "locked off", "fixed"; "push in", "punch in", "dolly zoom"; "tracking shot"; "whip-pans"; "slow push-in", "pulls back in one continuous movement"; "360-degree orbital rotation"; "snap-zoom"; "natural smartphone zoom", "film camera", "webcam style". Continuity: "Seamless video. One continuous shot, no jump cuts.", "Flawless continuity.", "continuous unbroken shot", "Maintain the microscope lens effect throughout the entire video." [verified: PG, B, PP]

Third-party rules that agree with Google and that we keep: one primary camera move per shot; lead with subject and action; describe what the camera sees, not what the story means; details intensify emotion, so each shot carries one environmental pressure, one physical micro-action and one sound anchor. [third-party: `video/universal-rules/smixs--visual-skills.md`, `video/universal-rules/muraterdogan0.md`]

One third-party rule does not apply here: "never put duration in the prompt". For Omni, Google's own examples end prompts with "10s", and the `duration` field is unconfirmed, so the length goes in the words until a test says otherwise. [third-party rule from `video/universal-rules/square-zero-labs.md`, overridden by verified: PP, PG]

### B12. Audio and speech

- Describe music by kind: "high energy techno beat", "a low tinny radio broadcast in the background, playing a song". [verified: O]
- Dialogue: name the speaker and quote the line: "The man in the blue sweater replies: "Did your father go out on the boat too?"". [verified: PG, B]
- Sound synced to action: "Add harp sounds synchronized to when I touch each fern leaf." [verified: PP]
- Voice editing is not supported; dialogue cannot be added to uploaded footage of someone already speaking. [verified: O]

### B13. Draft workflow

Google: "generate 3-4 draft variations in 360p, varying one thing at a time and compare them side by side." 360p is "up to 60% faster" and "a third of the cost" of 720p. Then run the chosen prompt again at 720p or above. A re-run is a new generation, not an upscale of the draft, so compare again. [verified: B; house note]

### B14. Failure habits and the fix that worked

| Habit | Fix | Source |
| --- | --- | --- |
| Several shots when one was wanted | "In a single unbroken scene. No scene cuts." | [verified: O] |
| Unwanted music, voice or effects | Name the audio, or "No dialogue. No music." | [verified: O] |
| An edit changed things you did not mention | Shorten the edit prompt to one sentence, add "Keep everything else the same." | [verified: O] |
| Drift across several edits | Compare to the approved clip, not the last edit; regenerate from the approved frame | [verified: MC; house rule] |
| Text in frame misspelled | Quote the exact words; check every character; never rely on it for logos or legal text | [verified: O, MC; house rule] |
| Complex motion breaks | Model card names "generating scenes with complex motion" as a challenge. One action, one camera move per clip. | [verified: MC; third-party] |
| Length not what was asked | Write the length at the end of the prompt; try `duration`; record which held | [test] |
| Blocked: a face | Recognisable people are refused. Use client staff only with consent, and expect refusals. | [verified: O] |
| Clip too big to return | `delivery: "uri"` for anything above 720p | [verified: O] |
| Request times out | `background=true` and poll | [verified: background-execution page] |
| Extension transition looks off | Expected: Google edits "some of the final frames" to blend. Keep the approved original as its own version. | [verified: O] |

### B15. What this model should not be asked for as final

The client's real logo, legal text, long copy, and any speech that must be word-exact. Generate the clip with a reserved area and composite in an editor. [house rule]

---

## Part C. Evidence from our jobs

Empty. Fill from `feedback/records/` once jobs run.

| Measure | Value |
| --- | --- |
| Clips run | 0 |
| First-try pass rate | |
| Average attempts | |
| Average output tokens per clip, by resolution | |
| Did the prompt-text length hold? Did `duration` hold? | |
| Did the label and text survive the motion? | |
| Wording that failed here and what replaced it | |

Last check against Google's pages: 2026-10-19. Next check due: 2027-01-19, or when the deprecations page changes.
