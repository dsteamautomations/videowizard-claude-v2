# 173 — Wan 3.0: the model, its versions and its parameters, from three sources (5 Nov 2026)

SK asked for everything about the Wan AI models from (a) a screenshot of a model marketplace listing and (b) OpenArt's "Wan 3.0 Prompt Guide" (Sameer Sohail, 25 Aug 2026). This note extracts both and sets them beside what the Wan CLI itself told us (design/170 §1, design/171). Where a source says something our runs contradict, the run wins and the line says so.

## 1. The models and versions

| Model | Where seen | What it is | Inputs | Output | Date | Price seen |
|---|---|---|---|---|---|---|
| **Wan 3.0** (`modelVersion 3_0`, CLI name `wan3.0`) | the screenshot ("Alibaba: Wan 3.0", 15% off); OpenArt; the CLI's default for every video command | Alibaba's video model: text to video, image to video, **reference-guided** video; makes the whole video in one go so faces, products and light hold through the length; sound made with the picture | up to **20 reference files**: 10 pictures, 5 video clips (≤15 s together), 5 audio clips (≤15 s together), plus one document or one web page; a start frame and an end frame can be set beside the references | **2–30 s**, 480p / 720p / **1080p** | listed 24 Aug 2026 | **from $0.0425 a second** (the marketplace) |
| **Wan 3.0 Prime** | the screenshot ("Alibaba: Wan 3.0 Prime"); OpenArt's "Quality level: Standard or Prime" | "a fast-mode variant of Wan 3.0"; on OpenArt the higher quality level that "costs more credits" | text to video and **first-frame image to video** only (no reference files named in the listing) | as Wan 3.0 | listed 27 Aug 2026 | **from $0.068 a second** |
| Wan 2.7 | OpenArt's comparison and FAQ; the CLI's `--model wan2.7` | the previous model: picture references, start and end frames, uploaded audio; shorter clips (per-video crop 1–5 s) | pictures, start/end frames, an audio file | shorter | | |
| Wan 2.7 Pro / 2.7 Flash | the CLI's image commands | image models (`wan2.7-pro`, `2.7-image-flash`), not video | | | | |

What the CLI gives us: `wan3.0` is the default on `text2video`, `frame2video`, `reference2video`, `videoedit` and `omni2video`; **there is no Prime switch in the CLI (0.0.3)**; Prime is a quality level on the website and on marketplaces. Every run of ours was Wan 3.0 standard (design/171).

Marketplace prices in rupees at about ₹84 to the dollar: Wan 3.0 ≈ ₹3.6 a second, Prime ≈ ₹5.7 a second. On our Wan account the price is **3 credits a second at 720P**, and the rupee price of a credit is still SK's to tell (design/170 §7, question 3).

## 2. The parameters (OpenArt's settings, with the CLI's flag beside each)

| Setting | OpenArt's options | The CLI flag | Note |
|---|---|---|---|
| Resolution | 480p, 720p, 1080p | `--resolution 480P/720P/1080P` | OpenArt: 1080p costs about four times 480p; test at 480p, finish at 1080p |
| Length | 2–30 s, or let the model pick | `--duration N` or `--smart-duration=true` | our runs: smart duration without seconds in the text ran 2–3× long (design/171 §8); with a staging video it took the video's length (design/172 §4) |
| Aspect ratio | 16:9, 9:16, 1:1, 4:3, 3:4, or let the model pick | `--ratio` (plus `adaptive`) | |
| Quality level | Standard or Prime | none | |
| Videos per run | up to 8 | one per call; 8 in flight on the account | |
| Audio | on or off | `--audio-output=true/false` | off still writes a silent AAC track (design/171) |
| Camera | a picked move (OpenArt's control) | none; in the text | |
| Auto Polish | rewrites the prompt before it runs | none in the CLI; Thinking Mode (`--file`/`--url`) is a different thing | OpenArt: switch it off once the prompt is exact, it can reword the @ labels and time ranges |
| Start / end frame | set beside the references | `frame2video --first-frame --last-frame` (not Omni) | |
| References | 10 images, 5 videos, 5 audios, one document or URL | `--images`, `--videos` + `--video-ranges`, `--audios` + `--audio-ranges`, `--file` or `--url` | the document or URL turns Thinking Mode on and is billed about 2.5× (design/172 §5) |

## 3. Alibaba's own prompt formula, as OpenArt reports it

1. **Start with three things**: a subject, a place, a movement ("A red fox walks across a snowy field at sunrise"). Then add, one at a time, the look of the shot, the style, the sound.
2. **Label every reference with its @ tag** (`@Image1 is the woman. @Image2 is the coffee shop. @Audio1 is her voice.`); the model "will not guess"; a reference may be named more than once to control where it shows up; say which picture opens and which closes the video when frames are set.
3. **Number the shots and give each a time range**: a one-line summary, then `Shot 1 [0-5s]: …`, `Shot 2 [5-12s]: …`; one clear thing per range; widen a rushed range and leave the rest.
4. **Write the sound as three separate things**: voice lines (the words, then how they are said), sound effects (the thing, what it does, the room), music (the kind and the style).
5. **On-screen words in quotation marks**, short, with a place named ("a white title at the bottom"); for exact spelling start from a picture that already carries the words.
6. **Three things the model decides unless told**: voice lines ("no voice lines in the whole video"), music ("no background music"), the number of shots ("one continuous take"). Length and shape likewise when left blank.
7. **From a start picture, say less**: only what moves and what the camera does; "fixed shot" to hold the camera, else it moves on its own.
8. **Edit with a plain instruction**: name the one change, "everything else stays the same".
9. **Four mistakes**: describing a still picture; references unlabelled; stacked camera moves; sound never switched off.
10. **Known limits** (OpenArt): on-screen spelling and sound texture still improving; an uninvited cut sometimes; small details slip when many people and props share a scene: keep a shot to a few people and objects.

## 4. What this confirms or changes in our method (design/170 §2c, design/171, design/172)

- **Confirmed**: the @ tags in file order with a plain name beside each; the numbered shots with time ranges for a 30 s sequence (our W3, W7, W8 used exactly this shape and held their cuts); "one continuous shot" for a single take; sound off; few people and objects per shot.
- **Confirmed by the page, learnt by us the hard way**: with no length given the model picks its own (our round 2 ran long); with a start picture the text should say less (our Blender runs needed only a short text).
- **New from the page, worth one test each**: naming the same reference twice to place it; "fixed shot" as the camera hold phrase; 480p for test runs at a quarter of the cost (our rounds ran at 720P throughout; a 480P test round would have cost a quarter); Prime for the final take once the staging is right.
- **Not in the page, from our runs**: counts of identical things drift (design/165, 171); a reference's pose and contents leak; the environment picture per scene; the Blender staging video fixes positions and timing (design/172).
- **The comparison table's claim** that Wan 3.0 takes 20 references matches the CLI's limits (10 + 5 + 5, plus one file or URL).

## Not covered

- The screenshot's marketplace is not named in it; its prices are "from" prices and may differ by resolution and length.
- Prime was not run; the CLI has no switch for it.
- OpenArt's Director mode (scenes planned up to 5 minutes) is OpenArt's own feature, not Wan's.
