# Seedance 2.5 fact sheet, reached through OpenRouter

Status: written 2026-10-19 from OpenRouter's pages and API listing, ByteDance's launch post and model page, and the official-guide material already copied into this folder. Marks: `[verified: page]` read on that page on 2026-10-19. `[ByteDance]` from ByteDance's own post. `[third-party]` from other users' notes in this folder, including the smixs file that records ByteDance's Dreamina and Jimeng guides of 2026-07-31. `[test]` means nobody states it and we must try it. Part C is empty until jobs run.

Pages used, short names:
- OR = https://openrouter.ai/bytedance/seedance-2.5 and its text version https://openrouter.ai/bytedance/seedance-2.5/llms.txt
- ORL = https://openrouter.ai/api/v1/videos/models (live listing)
- ORD = https://openrouter.ai/docs/guides/overview/multimodal/video-generation
- ORS = https://openrouter.ai/docs/client-sdks/go/models/components/videogenerationrequest and .../inputreference
- ORR = https://openrouter.ai/blog/insights/seedance-2-5-review/ (OpenRouter's own review, dated September 3, 2026)
- BD = https://seed.bytedance.com/en/blog/one-take-creation-flexible-referencing-introducing-seedance-2-5 (July 31, 2026)
- BDM = https://seed.bytedance.com/en/seedance2_5

Why OpenRouter: ByteDance's own API is not open to Indian users. OpenRouter's request shape is what the application sends, so this sheet records OpenRouter's fields, not ByteDance's. Decision in `models/CHOSEN-MODELS.md`.

---

## Part A. The API: what the application sends

### A1. Model id and status

| Item | Value | Source |
| --- | --- | --- |
| Slug to send | `bytedance/seedance-2.5` | [verified: OR, ORL] |
| Pinned version | `bytedance/seedance-2.5-20260807` (canonical slug). Use it in production so a silent update does not change results. | [verified: ORL] |
| Released on OpenRouter | August 7, 2026 | [verified: ORR, ORL created date] |
| ByteDance release | July 31, 2026. "the new-generation video creation model". | [ByteDance: BD] |
| Providers behind the slug | Not named on the page. "A listed value can still be refused by whichever provider serves the call." | [verified: OR] |
| EU in-region routing | "Not currently available for this model." | [verified: OR] |
| Zero data retention | Not possible for video: the provider keeps output briefly for pickup. | [verified: ORD] |

### A2. How to call

All on `https://openrouter.ai/api/v1`, header `Authorization: Bearer <key>`. [verified: OR, ORD]

1. `POST /videos` with the JSON body in A3. Returns `202` with `id`, `polling_url`, `status: "pending"`.
2. `GET /videos/{id}` until status is `completed`, `failed`, `cancelled` or `expired`. OpenRouter suggests polling every 30 seconds. Completed responses carry `usage.cost` in USD and `unsigned_urls`.
3. `GET /videos/{id}/content?index=0` to download, with the same bearer header.
4. Or set `callback_url` (https only) and receive a webhook with events `video.generation.completed`, `.failed`, `.cancelled`, `.expired`. Verify the `X-OpenRouter-Signature` when a signing secret is set.

"Generation typically takes 30 seconds to several minutes." A job that is never picked up expires with "Job exceeded maximum time to live"; the time limit is not published. [verified: ORD]

Decision for this library: poll, 30 seconds apart, and download within the hour. [house decision]

### A3. Settings on every call

| Field | Allowed values | Default | Notes | Source |
| --- | --- | --- | --- | --- |
| `model` | `bytedance/seedance-2.5` | | | [verified: OR] |
| `prompt` | text | required unless `frame_images` is set | | [verified: OR] |
| `duration` | integer 4 to 30, whole seconds | not stated on OpenRouter; ByteDance's native default is 5 | Set it every time. | [verified: ORL; third-party for the default] |
| `resolution` | `480p`, `720p` | not stated | No 1080p, no 4K on 2.5. | [verified: OR, ORL] |
| `aspect_ratio` | `16:9`, `4:3`, `1:1`, `3:4`, `9:16`, `21:9` | not stated | | [verified: OR, ORL] |
| `size` | 480p: `854x480`, `752x560`, `640x640`, `560x752`, `480x854`, `992x432`. 720p: `1280x720`, `1112x834`, `960x960`, `834x1112`, `720x1280`, `1470x630` | | Use instead of resolution plus aspect ratio. Only these twelve. | [verified: OR, ORL] |
| `frame_images` | list of `{"type":"image_url","image_url":{"url":...},"frame_type":"first_frame"|"last_frame"}` | | https URL or base64 data URL. One first, optionally one last. | [verified: OR, ORD] |
| `input_references` | list of reference assets: image, video or audio | | Page text shows only `{"type":"image_url","image_url":{"url":...}}`. The SDK schema has three kinds: image, video, audio, "only honored by providers that support them", and names ByteDance Seedance 2 and newer as one that does. Exact field names for video and audio entries are not printed anywhere; confirm with one trial call. | [verified: OR, ORS] [test] |
| `generate_audio` | true or false | true for this model | Audio is made in the same pass. Turning it off costs the same. | [verified: ORL, ORR] |
| `seed` | integer | | "determinism isn't guaranteed". Use it to stay in the same neighbourhood, not to repeat a clip. | [verified: OR] |
| `callback_url` | https URL | | Webhook instead of polling. | [verified: OR] |
| `provider.options.<slug>.parameters` | `watermark`, `req_key`, `output_format` | | The only passthrough keys allowed for this model. ByteDance's `output_format` takes `mp4` or `mov`; third-party notes recommend `mov` when a clip will be edited or extended repeatedly. | [verified: ORL; third-party] |
| Not available through OpenRouter | ByteDance's `ratio: adaptive`, `camera_fixed`, `bitrate_mode`, `return_last_frame`, `content.role` | | They exist on ByteDance's native API. They are not in OpenRouter's allowed passthrough list, so do not send them. | [verified: ORL; third-party for the native names] |

Mode rule: "If both `frame_images` and `input_references` are sent, `frame_images` wins and the request is treated as image-to-video" and the references have no visible effect. Never send both. [verified: ORD, ORR]

Editing and extending: OpenRouter's generic request schema has `previous_job_id`, "the ID of a completed video job to edit or extend", accepted "only by models that support continuation". The Seedance page does not list it. OpenRouter's review describes edit and extend as sending the footage as a video reference and writing the change in the prompt: "Continue the same shot for 10 more seconds." Try `previous_job_id` first; fall back to a video reference. [verified: ORS, ORR] [test]

### A4. What comes out

- One mp4, 24 frames per second, 4 to 30 seconds, at the chosen size. Audio included unless turned off. [verified: OR, ORR]
- Maximum 30 seconds in one generation. ByteDance says a clip can be extended twice; OpenRouter does not document extension limits. [ByteDance: BDM] [test]
- Download link form: `unsigned_urls` need the bearer key and work "for as long as the output is available"; signed `urls` expire at `expires_at`. Treat signed links as secrets. [verified: ORD]

### A5. What goes in

| Input | Limit | Source |
| --- | --- | --- |
| Reference images | ByteDance: up to 30 in one pass. OpenRouter publishes no count. | [ByteDance: BD; verified: OR] |
| Reference videos | ByteDance: up to 10 clips. Third-party notes: each 2 to 30 seconds, 30 seconds total. OpenRouter publishes no count. | [ByteDance: BD; third-party] |
| Reference audio | ByteDance: up to 10 clips; third-party notes say 30 seconds total. Only honoured by providers that support it. | [ByteDance: BD; verified: ORS; third-party] |
| Image file size and type | Not published by OpenRouter. Third-party notes: each image up to 4K and 30 MB. | [third-party] [test] |
| First and last frame | One of each, through `frame_images`. Third-party notes: aspect ratio locks to the first image; a mismatched last frame is stretched. | [verified: OR; third-party] |
| Stable counts | Third-party record of ByteDance's guide: 1 to 5 subjects inside a reference video is reliable, 6 to 10 is possible but unstable; 1 to 8 subjects across reference images reliable; a video to edit should be 20 seconds or shorter. | [third-party] |

### A6. Price

OpenRouter bills by video tokens. [verified: ORL, ORR]

| Rate | Value | Source |
| --- | --- | --- |
| Video tokens | $0.0000107 per token | [verified: ORL] |
| Video tokens when a video reference is sent | $0.0000064 per token, about 40 percent less | [verified: ORL, ORR] |
| Without audio | same as with audio | [verified: ORL] |
| Tokens per clip | width × height × 24 × seconds ÷ 1024 | [verified: ORR] |

What that means per second and per clip, worked from the formula:

| Size | Per second | 10-second clip | 30-second clip | Source |
| --- | --- | --- | --- | --- |
| 480p (854x480) | about $0.10 | about $1.03 | about $3.08 | [verified: ORR] |
| 720p (1280x720) | about $0.23 | about $2.31 | about $6.93 | [verified: ORR] |
| 720p with a video reference | about $0.14 | about $1.38 | about $4.16 | [verified: ORR] |

Portrait and landscape at the same pixel count cost the same. Video-reference jobs are authorised at a flat $2 up front; the final charge follows the token count. Failed generations are not billed. [verified: ORR, OR]

What the application must do: store `usage.cost` from every completed job.

### A7. Limits, waits, errors

- Rate limits: not published. A `429` means rate limited; retry with backoff. [verified: OR]
- Error codes: `400` malformed or unsupported value, with the supported values listed; `401` bad key; `402` out of credits; `403` spend limit or blocked; `404` unknown model or job; `429` rate limited; `500` could not submit; `502` upstream failure, not billed. A job that fails after acceptance shows `status: "failed"` with an `error` message, for example "Content policy violation." [verified: OR, ORD]
- Latency: "usually takes from 30 seconds to a few minutes"; longer and higher-resolution clips take longer. [verified: ORR, ORD]
- Known gaps ByteDance admits: "physical plausibility of complex motions" and "stability of scenes involving interactions among multiple subjects". [ByteDance: BD]
- Watermark: a `watermark` passthrough exists; default not stated. Set it to false explicitly and check the first output. [verified: ORL] [test]
- Provenance marking: not stated by OpenRouter or ByteDance. [gap]

---

## Part B. How this model reads words

### B1. Prompt shape

ByteDance's base formula, as recorded from its guide: [third-party, recording ByteDance's guide]

```text
<Subject> performs <primary action or event> in <scene and environment>.
The visuals feature <visual style>.
Use <shot size, camera angle, camera movement, or cuts>.
Audio includes <dialogue, ambience, sound effects, or music>.
```

For long or reference-heavy clips, the fuller shape is: reference declaration, one-line summary, plot by timeline, global tail. OpenRouter's review says the same in plainer words: "A 30-second prompt reads more like a shot list than a description." [third-party; verified: ORR]

House shape for our main case, an approved still animated into a short clip:

```text
@Image 1 is the first frame; keep its composition, product, label text and colours exactly.
{One line: subject, place, what happens.}
Camera: {one move}. {Shot size.}
0-{n}s: {one action, one visible end state}.
Audio: {ambience and one sound} | Pure video, no subtitles, no background music.
One continuous shot, no cuts of any kind.
```

Clip length, aspect and resolution go in the settings, not in the words. Third-party notes say ByteDance's 2.5 guide states this too, except in the separate Ultra Long mode which OpenRouter does not expose. [third-party; verified: ORD]

### B2. Naming the pictures, clips and sounds you send

ByteDance's own examples refer to each asset by its upload order and give it a job in words: "Scene reference: @Image 4." "The lead vocalist must strictly follow @Image 5." "Edit @Video 1. Keep the characters, actions, and visual style unchanged." "Refer to @Clay Render 1 for camera movement". [ByteDance: BD]

Rules recorded from ByteDance's guide: [third-party]
- Bind one asset to one subject: "<Character A> corresponds to @Image 1. Use only the appearance, hairstyle, and clothing." The forbidden pattern is "@Images 1 through 4 define four characters respectively", because it never says which is which.
- Add exclusions for what must not bleed in: "Do not use the image background." "Do not use the person's identity, clothing, or scene from the video."
- Do not re-describe what a reference already defines. If a video defines the motion, say only which attributes to inherit.
- Mention the same asset again at the points where it matters; repeated mentions increase accuracy.
- Order matters: most important reference first.

The `@` tag is a convention inside the prompt text, not an API field. The application sends the files in order in `input_references`; the prompt counts them from 1 in that order: `@Image 1` is the first image, `@Video 1` the first video, `@Audio 1` the first audio. Spelling varies across sources (`@Image 1`, `@Image1`, `@image1`); ByteDance's post uses `@Image 1` with a space. Use that. [ByteDance: BD; third-party]

Our tag list maps as: `approved` or `product` used as the opening picture → `frame_images` with `first_frame`; `product`, `person`, `style`, `scene` as references → `input_references` and `@Image N` with its job written out; a short clip of a person or product → `@Video N`. Never mix `frame_images` with references in one call. [house mapping; verified: ORD]

### B3. Timing and the 30-second structure

- "Second-level timestamp control. `[0-4s] ...` beat windows are honored as timing, not just ordering." Windows of 3 seconds or more; shorter ones execute unreliably. One core action and one camera move per window. Ranges consecutive, no overlap. [third-party, recording ByteDance's guide]
- Always state the visible end state of each window; "the end state is what the model steers toward". [third-party]
- ByteDance's own examples use "0–5s, 6–10s, 11–20s" segments and relative triggers. [ByteDance: BD]
- OpenRouter's review: "Order the beats and time them." [verified: ORR]
- A 10-second product clip needs two or three windows at most. Do not fill 30 seconds unless the brief has that much ordered action.

### B4. Audio, dialogue and on-screen text markers

ByteDance's guide gives dedicated markers, recorded in the smixs file: music in round brackets `(Soft piano plays)`, sound effects in angle brackets `<A bell rings>`, dialogue in curly brackets `{Hello, welcome back.}`, on-screen titles in `【 】`. Dialogue formula: language, accent, delivery, speaker, then the line in curly brackets. "Short lines sync better than long ones." [third-party; verified: ORR]

To stop unwanted sound and captions, ByteDance's reliable line is "Pure video, no subtitles, no background music", repeated in the closing lines. ByteDance's post says 2.5 "Reduced uncontrolled subtitles and background music". [third-party; ByteDance: BD]

### B5. One take versus cuts

Default behaviour is a multi-shot story: 2.5 "organizes multiple shots into a story with setup, development, turning points, and resolution". For one shot write "One continuous shot, no cuts of any kind" and give a camera path that never motivates a cut. If montage keeps leaking in, use a 10 to 15 second window where one-takes are stable. [ByteDance: BD; third-party]

For intended cuts, name the transition and add ByteDance's anti-jump-cut clause: "prohibit rigid cutting, prohibit objects appearing out of thin air". [third-party]

### B6. Camera words

Understood without translation: extreme wide, wide, medium, close-up, extreme close-up; push in, pull out, pan, lateral move, follow shot, orbit, dive, dolly out, tilt, handheld shake; low angle, overhead, first-person; one-take, dolly zoom, aerial, FPV, bullet time, speed ramp. ByteDance's own examples open with "One-take handheld gimbal tracking shot." and use "circular pans", "micro-FPV", "push-in", "top-down". One primary camera move per window. [third-party; ByteDance: BD]

### B7. People

ByteDance's realistic-human formula: age and ethnicity, skin tone and texture, three or four facial details, gaze, hair, clothing and fabric, build and emotion. Always append "retaining real fine pores and skin texture", which is ByteDance's own fix for plastic skin. Two to four observable cues per emotional change; emotion words alone leave the model guessing. Multi-person scenes: bind each person to their own image and write "Clothing colors, hairstyles, and facial features must all be distinct." [third-party, recording ByteDance's guide]

Our consent rule applies before any of this: no identifiable person without a consent id.

### B8. Editing a clip

ByteDance's edit pattern, from its guide and post: name the source as the sole master, state the one change and its scope, list everything to keep, close with the catch-all. [third-party; ByteDance: BD]

```text
Edit @Video 1. Within <the whole video | 4-10s>, <replace | remove | adjust> <one thing>.
@Video 1 is the sole editing master: it defines the characters, scene, actions, composition, camera, occlusion, audio and event order.
@Image 1 defines <what the replacement looks like>.
Modify only <the object or region>.
Keep everything else from @Video 1 unchanged: people, props, scene, camera movements, cuts, event order, audio.
```

- For filmed footage, list the keep-items before the change, down to focal length and floor perspective. The longer the keep-list, the less drift. [third-party]
- Source clips of 20 seconds or less. Longer ones stall. [third-party]
- One edit target per pass. [third-party]
- When the source has speech, anchor timing to the words, not to seconds. [third-party]
- Localisation pattern: "Replace the narration in @Video 1 with natural fluent <language> ... Keep the original camera movement, blocking, performance pacing, scene, and product." [third-party]

### B9. Extending a clip

- ByteDance's example opens: "Extend the video. Continue from the visuals and subjects in @Video 1..." and keeps "characters, scene, visual style, and sound effects consistent". [ByteDance: BD]
- Minimal prompt that practitioners report working: "Extend the video. Keep character identity, facial structure, body proportions, lighting, art style, and the space fully unchanged. Only change camera movement; do not redesign character or action." [third-party]
- The new prompt applies only to the appended part. Boundary frames connect visually, not pixel-identically. [third-party]
- How many times: ByteDance's model page says a clip can be extended twice. [ByteDance: BDM]

### B10. Physics

Declare the physics regime, narrate consequences not just actions, forbid the known failure by name, and gate events on triggers: "Three seconds after she presses the button..." A chain where each step forces the next is also a check: a broken chain shows a failed generation at a glance. [third-party, recording ByteDance's guide]

### B11. Draft and finish

"Draft at 480p and finish at 720p. The prompt does not change between the two." A 480p draft of a 10-second clip costs about one dollar; the 720p finish about two and a quarter. [verified: ORR]

### B12. Failure habits and the fix that worked

| Habit | Fix | Source |
| --- | --- | --- |
| Cuts appear in a requested one-take | "One continuous shot, no cuts of any kind"; shorter window | [third-party] |
| Random subtitles or music | "Pure video, no subtitles, no background music" in the closing lines | [third-party; ByteDance: BD] |
| Two people blend into twins | Bind each to its own `@Image N`; write that features, clothing and hair must be distinct | [third-party] |
| Plastic skin | "retaining real fine pores and skin texture" | [third-party] |
| Complex motion or multi-subject interaction breaks | ByteDance names both as open weaknesses. One subject, one action per window. | [ByteDance: BD] |
| An object appears in an impossible place in the back half | State the world's hard constraints in the closing lines; watch the whole clip | [third-party] |
| Edit ignored or stalls | Source ≤20s; name `@Video 1` as sole master; one target | [third-party] |
| References had no effect | `frame_images` was also sent; it wins. Send one or the other. | [verified: ORD, ORR] |
| Same seed, different clip | Expected. Seed is not a repeat button. | [verified: OR] |
| Unsupported value | `400` lists the allowed values; pick from A3 | [verified: ORD] |
| Output "reads as review material" | OpenRouter's own verdict: treat results "as material to review rather than as finals". Our QA step applies. | [verified: ORR] |

### B13. When to pick this model over Omni

Pick Seedance 2.5 when the job needs: a single take longer than 10 seconds, many tagged references at once, a clip of the client's own footage edited or extended, or an aspect that Omni lacks such as 1:1, 4:3 or 21:9. Pick Omni when 1080p or 4K is needed, when the clip is 10 seconds or shorter, or when cost per second matters: Omni at 720p is about 10 cents a second, Seedance about 23. [verified: ORR; Omni sheet]

### B14. What this model should not be asked for as final

The client's real logo, legal text, word-exact speech for compliance, and anything above 720p. [house rule; verified: OR]

---

## Part C. Evidence from our jobs

Empty. Fill from `feedback/records/` once jobs run.

| Measure | Value |
| --- | --- |
| Clips run | 0 |
| First-try pass rate | |
| Average attempts | |
| Average `usage.cost` per clip, by size and duration | |
| Did `input_references` accept a video entry, and with which field names? | |
| Did `previous_job_id` work for extension? | |
| Did the watermark passthrough default to off? | |
| Wording that failed here and what replaced it | |

Last check against OpenRouter and ByteDance pages: 2026-10-19. Next check due: 2027-01-19, or when ByteDance opens its own API to Indian users.
