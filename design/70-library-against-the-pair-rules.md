# design/70 — How the image library and the segment-pair rules were combined, and what the recheck found

Status: a read-only review, 21 Oct 2026, for SK's reviewers. Nothing was changed. Sources: the library bundle `vwlib-2026-10-21-4f88379be109` (RULEBOOK, the video-frame and video-clip playbooks, gap-fill, consistent-character-frames, animatic-keyframes, diagram-in-states, still-to-motion, the GPT Image 2.5 and Gemini Omni fact sheets, VW-MAP); VideoWizard's visuals prompt and steps (`server/procedures/v2.json`), the packet instructions (`visuals_stage.packet`), the server's fixed lines (`video_providers.motion_text`), and design/66, 67, 68.

## 1. The two sets of instructions

**The scenario rules** (VideoWizard's own, design/66 and 67): a video passage longer than the generator makes is cut into segments at the start or end of an action; every take runs from a start image to an end image, both approved; the end image is an edit of the start, one small action on, with the start's identity references sent again; segments share a boundary picture only within one continuous shot; the start and end prompts are written together and the start is composed for the whole segment; positions are held against named landmarks and the camera only changes their screen projection; the end state is written per subject; the motion follows each subject's ordered beats.

**The general craft** (the library): the rulebook for every job, the playbooks per kind of job, the fact sheets per model, the job form and the answer form with its checklist, the feedback record.

## 2. How they are combined: three layers that do not repeat each other

| Layer | What it holds | Where it lives |
|---|---|---|
| The server fixes and appends | the image model and size, the generator, the pictures sent and their order, audio off, the duration, "use the first image as the starting frame, the second as the ending frame", no captions, preserve the identities | `visuals_stage`, `video_providers.motion_text`; VW-MAP's override table says the server wins where it and the library disagree |
| The packet instructs per shot | the three composition instructions: both prompts written together, the start composed for the whole segment, the end one small action on with positions named and nothing else changed, the motion from the beats; the library block naming the step's files and the filled job form | `visuals_stage.packet` (design/67, 68) |
| The library teaches before the prompt is written | the rulebook, the playbooks, the guides and the fact sheets, read once per step; every prompt written in the answer form and linted | `work/visuals/library/` (design/68) |

## 3. Where the two already agree

Twelve library rules are carried by VideoWizard's rules:

- first and last frame with the same aspect, light and traits, only the move's change differing (video-frame §4);
- headroom for the move (video-frame §2);
- a frame approved before anything moves (RULEBOOK §16.1, video-frame §1);
- longer stories as several clips (RULEBOOK §16.3, video-clip §2);
- the reference sheet in every later call (RULEBOOK §12, GPT B7, consistent-character-frames);
- "change only X" in an edit (RULEBOOK §8.1, GPT B5);
- graphic states as edits of the previous state, two to four, one change per state (diagram-in-states §2);
- exact quoted words, short copy, every character read, a misspelt candidate regenerated (RULEBOOK §4, GPT B4/B10);
- the boundary-frame method and "not every gap is a continuation" (gap-fill §3, §4);
- the motion brief as movement, not a retelling of the frame (video-clip §4);
- Omni's first frame, the path between, the final frame (Omni B9);
- the model, size, audio and route overrides (VW-MAP).

## 4. What VideoWizard adds that the library does not have

- Cuts placed where an action begins or ends, never at round seconds.
- An end image on every take; the library's default is one frame.
- The end image as an edit of the start, the start's sheets added by the server, "one small action further on".
- A boundary picture shared between generated segments, images counted as segments plus one per continuous passage; the library's boundary frame applies to real footage only.
- Start and end prompts written together, the start composed for the whole segment with nothing placed where the end must remove it.
- Positions held relative to landmarks; the end state written per subject (landmark, side of frame, facing, pose, what it holds, work progress).
- Subject reconciliation, ordered beats per subject, non-acting subjects held in place.
- Kling and Seedance through Higgsfield with first and last images.

## 5. What the recheck found missing

### 5a. In the files the child reads, but nothing of ours asks for them

The first pass on VW-6 shows whether the child applies them on its own.

1. Omni's source tags at the top of a video prompt (Omni B7).
2. "One continuous shot, no jump cuts" on every take (video-clip §2, Omni B2).
3. One named camera move and an environment motion per clip (RULEBOOK §16.2–16.3, video-clip §4).
4. The five identity traits written out in image and clip prompts (RULEBOOK §12, GPT B7).
5. A named keep-list in every edit prompt (RULEBOOK §8.1, §7.4); our "names only the change" contradicts this if read literally.
6. The standing line "render only explicitly requested image text", with each label's place and "exactly once" (RULEBOOK §4.2–4.3, GPT B4).
7. The five-line theme block repeated in every frame prompt, and the keyframe card before generating (video-frame §3.4, §4; animatic-keyframes §2).
8. For graphic states: plan the last state first and reserve its space in state one; hold each state at least three seconds; list every existing label in quotes in each edit's keep-list (diagram-in-states §2–3, §6).

### 5b. Needing the server or the flow (queued as L30, next batch)

1. The end-image prompt must name the pictures by number ("Image 1 is the start; images 2 onward are identity only"), because the server adds the start's sheets after the prompt is written (RULEBOOK §7.1–7.2, GPT A5).
2. No cap on the inputs against GPT Image's limit of 16 (GPT A5).
3. Size: a footage frame used as a start is 1920×1080 while the end image is edited at 1536×864, so the pair differs in size; a 9:16 film has no size at all; the end should be edited at the start's own size (video-frame §7, GPT A4).
4. The shared boundary is still a hard cut at assembly; the library says never promise an invisible join, so a planned cut or a short dissolve belongs there (gap-fill §4).
5. A frame that shows a recognisable face is refused by both image models; footage-first needs the gap-fill fallback, the frame as a look reference only (gap-fill §4, GPT A7, Omni A5).
6. A retry after drift restarts from the approved start, not from the candidate chain (RULEBOOK §8.3, diagram-in-states §2).

Two more are review practice rather than rules: after a take, check labels, traits and palette in the final seconds and regenerate from the approved frame rather than patch (RULEBOOK §16.7, video-clip §8); and the real-person consent id the library requires, which VideoWizard does not record (open for SK).

## 6. Reading

The library supplies the general craft of making a picture. The packet supplies the scene-specific rules of making a start and end pair for a segment. The server fixes what neither should decide. The gaps are at the seam: a handful of library lines the child must remember to write, and six mechanics the server should own.
