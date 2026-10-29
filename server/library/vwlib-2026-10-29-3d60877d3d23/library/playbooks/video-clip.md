# Video clips playbook

Version 0.1, written 2026-10-19. Status: draft, untested on a real job. One file for every video clip made through an API: from an approved frame, from text, an edit of a clip, or an extension. The video model's fact sheet is read in full alongside this file; it holds the settings, the tag syntax and the wording habits. Built-from list at the end.

## 1. What this playbook covers

Tasks on the job form: `clip-from-frame`, `clip-from-text`, `clip-edit`, `clip-extend`. The stills a clip needs are the video-frame playbook.

Added 2026-10-21, draft and untested: clips that sit between real footage follow `video/gap-fill.md`.

## 2. Decisions already taken

| Decision | Value | Why |
| --- | --- | --- |
| Frame first | A clip that must show a real product, a real place or a recurring character starts from an approved frame, never from text alone. Text-only clips are for mood, b-roll and faceless explainers. | Text-only invents packaging, labels and faces. |
| Which model | Omni 1.1 Flash for clips of 10 seconds or less from one approved frame, and for anything that needs 1080p or 4K. Seedance 2.5 for a single take over 10 seconds, for many tagged references at once, for editing or extending the client's own footage, and for 1:1, 4:3 or 21:9. Kling 4.0 when its API opens. | Fact sheets, B13 of the Seedance sheet. |
| Draft and final | Omni: draft at 360p, finish at 720p or above. Seedance: draft at 480p, finish at 720p. Same prompt both times; a re-run is a new generation, so compare again. | Both vendors say so. |
| Length | The shortest length that fits the action. One beat per 3 to 5 seconds. Longer stories are several clips cut together, or one Seedance take with timed windows. | Universal rules; both sheets. |
| Settings versus words | Aspect, resolution and audio on or off go in the settings. Length goes in the settings where the API takes it; on Omni it also goes at the end of the prompt in words until a test says the field holds. No model name in the prompt. | Square-Zero-Labs rule; Omni sheet B2. |
| One take unless cuts are wanted | Both models default to several shots. Every prompt says "in a single unbroken scene, no scene cuts" unless the shot list asks for cuts. | Omni sheet B2; Seedance sheet B5. |
| Audio | Described or switched off. Never left to default. Dialogue short, attributed to a visible action, in quotes. Music by kind. Voice editing is not available. | Both sheets. |
| Real people | None generated. A client's own footage edited only with consent ids; dialogue on uploaded footage cannot be added. | Compliance C09; Omni sheet A7. |
| Motion hold is checked | After animation, the product label, the character traits, the palette and any text are checked against the approved frame. A shot that broke is regenerated from the frame, not patched in the video tool. | DIRECTION 5h step 7. |

## 3. Before writing

1. The shot list entry: shot number, seconds, action, camera move, audio reference, transition. From the video-frame playbook's handoff.
2. The approved frame, tagged `first-frame`, and the kit tagged `approved`. For a last frame, tagged `last-frame`.
3. The video placement and aspect, and the finish resolution.
4. For an edit or extension: the source clip tagged `source-clip`, 10 seconds or less for Omni uploads, 20 seconds or less for Seedance edits, and the one change wanted.
5. Audio intent: ambience, music by kind, dialogue lines, or silence.

## 4. The motion brief

The frame already holds identity, composition, text and product. The clip prompt is a motion brief, not a retelling. It names six things:

1. Camera: one move, named from the vocabulary in section 6.
2. Subject motion: what the subject does, with one physical micro-action.
3. Environment motion: one or two things that move: steam, fabric, leaves, light flicker.
4. Audio: room tone and one sound, or music by kind, or "No dialogue. No music."
5. Continuity: the product label, colours and text in frame stay unchanged; the five character traits.
6. The single-scene line, and the length in words where the model needs it.

Every shot owns at least three concrete details: one environmental pressure, one physical micro-action, one sound anchor or visual motif. "Cinematic", "dynamic", "beautiful lighting" and named emotions do not render; bodies and physical consequences do.

## 5. Writing the prompt

Omni, from an approved frame:

```text
<FIRST_FRAME> {one line naming the scene as it is in the image}.
Camera: {one move}, {shot size}.
{Subject} {does one thing: micro-action with a consequence}. {Environment motion, one or two.}
Keep the product label "{text}", its colours and the text in frame unchanged. {Five traits if a person.}
Audio: {room tone and one sound} | No dialogue. No music.
In a single unbroken scene, no scene cuts. {n}s.
```

Seedance, from an approved frame, with references:

```text
@Image 1 is the first frame; keep its composition, product, label text and colours exactly. {@Image 2 defines the character's appearance, hairstyle and clothing; do not use its background.}
{One line: subject, place, what happens.}
Camera: {one move}. {Shot size.}
0-{a}s: {one action, visible end state}. {a}-{n}s: {one action, visible end state}.
Audio: ({music by kind}) <{one sound effect}> {dialogue in curly brackets, attributed} | Pure video, no subtitles, no background music.
One continuous shot, no cuts of any kind.
```

Rules that matter most for clips:

- Lead with subject and action. Style words at the end. Models weight the first third of the prompt.
- One primary camera move per shot; a subtle micro-adjustment at most on top.
- Describe consequences, not just actions: tyres kick up water; the lid actually unscrews. A broken chain shows a failed generation at a glance.
- Timing: Omni takes natural language and timecodes; Seedance takes windows of 3 seconds or more with one action and one camera move each and a stated end state.
- No contradictions: "still pond" with "flowing water", "close-up" with "wide landscape".
- Reference roles stated with exclusions; do not re-describe what a reference already shows.
- For a text-only clip, add the scene and subject lines first, then the same camera, motion, continuity and audio lines; and send the still-to-motion style formulas from `video/still-to-motion-pipeline.md` when it is a faceless explainer: one literal visual per beat, motion only makes it breathe.

## 6. Camera and light words both models understand

Framing: extreme wide, wide, medium wide, medium, medium close-up, close-up, extreme close-up, macro insert, over-the-shoulder, POV, profile, low angle, high angle, top-down, locked-off. Movement: static, slow push-in, pull-back, tracking, lateral tracking, handheld micro-shake, whip pan, tilt, crane, orbit, dolly zoom, snap-zoom. Light: one motivated source with a direction and a quality: window key from frame-left, soft; practical lamp, warm; overcast, flat; neon rim, cool. Omni's own extras: "oner", "locked off", "punch in", "natural smartphone zoom", "webcam style". For a rare term, keep the term and translate it into the visible change.

## 7. Task notes

**clip-from-frame.** The default. One approved frame, one move, one beat. Omni up to 10 seconds; Seedance 4 to 30. For a product: the camera moves, the product does not deform; "the label stays sharp and readable throughout".

**clip-from-text.** Mood b-roll, faceless explainers, abstract transitions. No real product, place or person. Describe the capture as a fact for realism, or a named illustration style for stylised work. Five to twelve concrete nouns.

**clip-edit.** Omni: short prompts, "Keep everything else the same", multi-turn with the previous interaction id; uploads of 10 seconds or less, not in the EEA, Switzerland or the UK. Seedance: name the source as the sole master, one change, a long keep-list, source of 20 seconds or less. One edit per pass. Compare to the approved clip, not the last edit.

**clip-extend.** Omni: "Continue the scene" or "The scene continues", 10-second steps to 40 seconds, references allowed to introduce a character, timestamps relative to the extension's start, audio described if it must change. Seedance: "Extend @Video 1 forward", continuity list, new content, "keep each subject as the same continuous instance". ByteDance says twice. The original is kept as its own version; the extended file is new.

**UGC style.** From `agency/ugc-video-formulas.md` and the UGC pack: "shot on a smartphone, handheld, vertical", natural light, direct address, one or two short lines of dialogue, imperfect but believable. The person must be fictional or consented, and AI-generated testimonials are disclosed. A real product on screen starts from its photo.

**Dialogue.** Name the speaker by a visible action first, then the line in quotes. Short lines sync better. Supported languages differ by model; regional dialogue is tested before promised. Omni: multi-turn extension of a generated clip can add speech; uploaded footage of someone already talking cannot.

## 8. Checklist lines for clips

- One scene, no cuts, unless cuts were asked for. must.
- Product label, colours and any text in frame held through the whole clip against the approved frame. must.
- Character traits held throughout; no second character; no identity drift. must.
- The one camera move happened and nothing else. must.
- Audio as specified: no unwanted music, dialogue or captions; dialogue attributed and in sync. must.
- Length within one second of the request; aspect and resolution as set. must.
- No extra objects appearing or vanishing; no impossible placement in the back half. must.
- Physics chain holds: each action's consequence visible. should.
- The approved frame is recognisable as the clip's first frame, when one was sent. must.

## 9. What goes wrong on clips, and the fix

| Habit | Fix | Seen in |
| --- | --- | --- |
| Several shots when one was wanted | The single-scene line; shorter window; a camera path that never motivates a cut | both sheets |
| Unwanted music, captions or voice | Name the audio or forbid it; "Pure video, no subtitles, no background music" | both sheets |
| Label or text softens in motion | "The label stays sharp and readable throughout"; slower move; regenerate from the frame | house rule |
| Character drifts | Kit sent; traits repeated; "same continuous instance" | Seedance B9; Omni B7 |
| Edit changed what was not mentioned | Shorter edit prompt; "Keep everything else the same"; longer keep-list | Omni B4; Seedance B8 |
| Length wrong | Length in settings and, for Omni, in words; record which held | Omni sheet [test] |
| Clip too big to return | Omni `delivery: "uri"` above 720p | Omni A3 |
| Request times out | Omni background and poll; Seedance poll every 30 seconds | both sheets |
| References had no effect on Seedance | A first frame was also sent; send one or the other | Seedance A3 |
| Face blocked | Recognisable people are refused; use consent-covered staff and expect refusals | Omni A5 |
| Motion ignored in a very short clip | Lengthen to 5 seconds or more; name the move with a speed | smixs Seedance notes |

## 10. Evidence

None yet. Core status needs motion hold recorded on at least two animated shots per the evidence protocol.

## 11. Built from

`video/models/gemini-omni-1-1/FACT-SHEET.md`; `video/universal-rules/square-zero-labs.md`, `smixs--visual-skills.md`, `muraterdogan0.md`; `video/craft/camera-lighting-vocabulary.md`; `video/craft/dramaturgy.md` sections 1, 2, 7, 11; `video/shot-vocabulary.md`; `video/packs/product-ads.md`, `ecommerce-first-frames.md`, `ugc-ads.md`; `agency/ugc-video-formulas.md`; `video/still-to-motion-pipeline.md`; `DIRECTION.md` section 5h steps 6 to 8; `models/nano-banana/smixs--visual-skills.md` keyframes section.
