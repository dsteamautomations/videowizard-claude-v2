# Kling 4.0 watch file

Status: watch file, opened 2026-10-19. Kling 4.0 is wanted but cannot be called through an API yet, as far as Kling's own pages show. Nothing here is a verified API fact. Every line is marked `[third-party]`, `[Kling, via search snippet]` or `[gap]`. When Kling publishes API access, this file becomes a fact sheet in the same three-part form as the others, written from Kling's own documentation.

Re-check monthly. Next check: 2026-11-19. What to check is in section 4.

Decision in `models/CHOSEN-MODELS.md`: third video model, wanted; Omni 1.1 Flash and Seedance 2.5 carry video work until then.

---

## 1. What is known about Kling 4.0 on 2026-10-19

| Item | What was found | How sure | Source |
| --- | --- | --- | --- |
| Announcement | Announced in October 2026. Sources disagree on how far it has rolled out: one says fully live from October 15, others say early access, or only the Flash variant and only to some users. | Low | [third-party: kie.ai, techpilot.ai, apimaster.ai, pixverse.ai blogs seen in search, 2026-10-19] |
| Clip length | Up to 30 seconds in one pass. | Medium | [third-party, several sources agree] |
| Keyframes | Up to 10 keyframes in one generation. | Medium | [third-party] |
| References | "Omni Reference" inputs, up to 15 items: images, videos and character subjects. | Medium | [third-party] |
| Flash variant | Kling 4.0 Flash: 720p ceiling, 20 seconds, no keyframes. Reached only through the yearly Ultra app plan at launch. | Low | [third-party] |
| API | Not announced as an API model at launch. Kling's developer pricing page, as read by a third party on 2026-10-13, said prepaid API packages do not support 4.0. One reseller advertises a 4.0 API; treat with caution. | Medium that there is no official API yet | [third-party] |
| API price | None published by Kling. One third-party figure of 15 credits per second at 1080p. | Low | [third-party] |
| Kling's own API page | https://kling.ai/document-api/updates/api is script-rendered and returned only its title to a plain fetch on 2026-10-19. Read it in a browser at the next check. | | [gap] |

## 2. What is live today: Kling 3 by API

If a Kling job is needed before 4.0 opens, Kling 3 is callable. Recorded from search results, not from a fetched Kling page. [Kling and Alibaba Cloud pages, via search snippet, 2026-10-19]

- Modes: text-to-video; image-to-video from a first frame; image-to-video from first and last frames; reference-to-video on the omni model (`kling-v3-omni` on Alibaba Cloud's listing).
- Output: 720p and 1080p.
- Access: Kling's own API, Alibaba Cloud Model Studio, or resellers. Which of these is open to Indian users is not checked. [gap]
- Price: varies by provider; figures seen start around $0.075 to $0.106 per second. [third-party]

## 3. Wording habits recorded for Kling 3, likely to carry to 4.0

From the raw notes in this folder. All third-party; none tested here. Keep them as the starting point for Part B when the 4.0 sheet is written. [third-party: `issastash.md`, `smixs--visual-skills.md`]

- Think in shots, not clips. Up to 6 shots in one generation on 3.0; label them `Shot 1: ... Shot 2: ...` or write a clearly sequenced paragraph.
- Anchor each subject early with a name and a description, and never rename it.
- Bind dialogue to a visible action: describe the physical action that identifies the speaker, then attribute the line. Attribute every line of audio.
- Describe motion explicitly for both subject and camera, over time: "tracks alongside, pushes in, holds, pans left, freezes when she stops".
- Use linking words to force order between lines: "immediately, then, after a beat, suddenly".
- Elements and Omni mode: reusable named characters, props and locations referenced with `@Name`; up to 3 reference images per element; build three angles per character.
- A "Style Bible" line repeated verbatim on every prompt in a project.
- Image-to-video: lock first, then move. Describe only what changes.
- Dialogue languages supported on 3.0: Chinese, English, Japanese, Korean, Spanish; other languages are auto-translated to English. Plan regional dialogue accordingly.
- Known failures on 3.0: multi-shot collapsing into one take; lip-sync drift; wrong voice chosen; two similar characters blending; music appearing despite "no music"; image quality dropping when Elements are enabled; morphing on fast motion.

## 4. Monthly check list

1. Open https://kling.ai/document-api/updates/api in a browser. Does it list a 4.0 model? Record the model id, modes, durations, resolutions and the date.
2. Open Kling's developer pricing page. Does it list 4.0 in API packages? Record the per-second price with the date.
3. Check whether Kling's API is open to accounts in India. If not, check whether OpenRouter lists a Kling 4.0 slug at https://openrouter.ai/api/v1/videos/models.
4. If the API is open: write the full fact sheet from Kling's documentation, Parts A, B and C, in the form of `video/models/seedance/FACT-SHEET.md`. Move this file's section 3 into Part B as third-party lines.
5. If not: update the date at the top and the table in section 1, and set the next check one month on.

## 5. Why this model is wanted

Kling 4.0 is listed as wanted because of the keyframe count and the reference set: ten keyframes and fifteen tagged references in one 30-second generation would let a storyboard become one clip with the product and a character held across shots. Until it is reachable, Seedance 2.5 covers long tagged-reference clips and Omni covers short clips from one approved frame. [house reasoning]

Last check: 2026-10-19. Next check: 2026-11-19.
