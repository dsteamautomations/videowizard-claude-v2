# design/89 — Pictures that follow the narration, move, and are drawn to the facts

Status: proposed by Revathi, 23 Oct 2026, from her review of VW-6's assembly film (server 0.32.0). For SK's approval. Nothing built. Every rule is written for **any film and any subject**; VW-6 appears only as the evidence. design/88 (the footage character measured, not asked) is a separate note and stays separate.

## Evidence from VW-6 (measured on the assembly film, 5:20, 60 shots)

- **Timing.** In the opening gap (0:00–0:28) the cuts fall at 8.0 s and 16.0 s, not at the sentence ends (14.6 s and 20.3 s, from the audio's pauses). The product name is spoken over the wrong picture, and its title arrives 1.5 s after the name has been said.
- **Frozen pictures.** 29 shots are completely still, adding up to 183 of 320 s (57%). Fifteen of them run over 5 s, and the longest are a diagram held for 23.7 s (2:40–3:04), another for 14 s (4:52–5:06) and a drone shot frozen as a frame (0:16–0:22).
- **Graphics.** A 7.5 s comparison diagram (0:42–0:50) is one still, shows one of the narration's two claims, leaves a third of the frame empty, and is factually wrong: the two walls are drawn at different thicknesses where they should be equal, and the brick proportions are not real ones.
- **Sound.** AI shots are silent, and they carry no sound-effect notes for the editor. Real clips get both.

## A. The narration's timing reaches the planner and the page

**Why.** The planner receives a gap's words and total seconds, but not when each sentence or word is spoken inside it. The word timings exist (the voice stage records them, and assembly uses them for subtitles). They never reach visuals.

| # | Change | Where |
|---|---|---|
| A1 | Each gap carries its narration as timed sentences (start and end, relative to the gap and to the film), plus the word timings, built from the voice stage's timing file and any approved pauses. Shown in the package, in every packet (the gap and the neighbouring sentences), and on the Treatment and Plan steps of the visuals page. | `visuals_stage.prepare`, `packet`, `templates/visuals.html` |
| A2 | Rules in the prompt: a cut falls in a pause between sentences or phrases, never inside a word. A picture that shows something the narration names starts on or just before that word. A shot's purpose names the words it covers. A title or label starts on the word it names. | `server/procedures/v2.json` (visuals prompt) |
| A3 | The plan check warns when a cut is more than about 0.3 s from a pause, when a shot's named subject is spoken while another picture is on screen, and when a title or label misses its word by more than 0.5 s. | `visual_contract.validate_plan` |

## B. Pictures move; stills are short

**Why.** The limits are warnings only, and diagrams always pass them. Stills are held frozen at assembly with no movement. The footage route can place only a single frame, never a moving stretch of a clip.

| # | Change | Where |
|---|---|---|
| B1 | Hard limits, refused rather than warned: a photographic still (AI or a footage frame) runs at most **3 s**. A stretch that needs longer is filled with several different stills or a moving shot, never one still held. One state of a graphic runs at most 6 s. A graphic on screen longer than about 4 s must be a build of 2 to 4 states or a drawn animation (section E). | `visual_contract.validate_plan` |
| B2 | Every still and every graphic state gets gentle movement at assembly by default: a slow push or pan of about 3–5% across the shot, its direction chosen by the planner from the composition (`motion: push_in, push_out, pan_left, pan_right, none`). `none` must be stated with a reason. | `stage2/render.py`, `stage3/assembly.py`, plan schema |
| B3 | The footage route can place a moving stretch of any clip, used or unused (clip id, in and out), as well as a frame. A frame of a clip that moves is used only as a reference or a deliberate freeze, and is marked as one. | `visuals_stage` (new `clip` fill), assembly, plan schema |
| B4 | The check reports the film's frozen share (seconds of stills with `motion: none`, plus graphic holds) and warns above a share set per run (default 25%). The treatment shows the expected share before approval. | `validate_plan`, treatment |

## C. Graphics say what the narration says, in one look

| # | Change | Where |
|---|---|---|
| C1 | **Claim coverage.** For every graphic, the planner lists the claims spoken over it, and the graphic's checklist has one `must` line per claim. Gemini's check fails a graphic that shows none of a claim. A claim left out on purpose is named, with the reason. | prompt, answer form, `image_check` |
| C2 | **One graphic style per film.** Before the first graphic, the planner proposes a style sheet: palette from the client card, line weight, label type and size, background, and how the frame is filled. The operator approves it once, it is rendered as a reference picture, and every graphic is bound to it. It replaces the empty-space habit: the graphic fills the frame unless the composition says otherwise. | treatment step, references, packet |
| C3 | Builds are planned against the narration's timing (A1): each state starts on the words it illustrates. | prompt, `validate_plan` |
| C4 | **The checklist is never skipped.** The answer form (with its checklist) becomes required for every generated picture, graphic state and take; today it is optional, and without it Gemini checks only the three fixed lines. A picture request without an answer is refused, after one release in which it only warns, so a run in progress is not broken. | `visuals_stage.generate_image`, `prepare_take`, `vw.py` |

## D. Technical drawings come from a sourced spec

**Why.** A diagram of a real object (a wall section, a machine part, a joint, a circuit, a road profile) is only as right as its measurements. An image model paints proportions by eye, and even a drawing made by code is wrong if its numbers are guessed.

| # | Change | Where |
|---|---|---|
| D1 | **A drawing spec before any technical drawing.** The planner writes, per drawing: the parts; each dimension with its unit; the relationships that must hold ("same thickness", "the cavity is inside the wall"); and for each number, its source and its status. | plan schema (`drawing_spec` on a shot), prompt |
| D2 | **Sources, in this order.** (1) The client's own material: script, brief, documents, supplied drawings. (2) The footage, measured: Gemini reads frames that show a thing of known size and estimates the rest, giving the clip and the time. (3) An authoritative web source (a standard, a manufacturer's sheet, a textbook), under the web rule (warning and the operator's yes), with the URL and the figure kept. (4) A reference image the operator approves, for shapes hard to put into numbers. | prompt; the new library guide (D6); `visuals_stage` (a measure call on frames) |
| D3 | **Status per number:** `confirmed` (client or standard), `measured` (footage), or `unknown`. An unknown number is never invented: the drawing is labelled "illustrative, not to scale" and shows no figure for it. | `validate_plan` |
| D4 | **The operator approves the spec as a table** (part, size, source, status) on the page or in chat, before the drawing is made. One approval per spec. | page, `vw.py`, server function shared by both |
| D5 | **The check compares the drawing with the spec and the reference:** proportions, relationships, labels. A failed relationship line is a `must`. | `image_check` |
| D6 | A library guide, `video/technical-drawing-spec.md` (draft, untested), written into the master library and the next snapshot: the spec format, the source order, the status rules, and worked examples from three unrelated domains. | image prompt library |

## E. A new route: graphics drawn by code

**Why.** A sample made on 23 Oct (`rattrap-code-sample.mp4`, 10 s, no paid call) showed what code gives that a painted image cannot: exact scale, nothing drifting between steps, exact text, real motion (parts appearing in order, arrows travelling), timing to the second, and free edits. It also showed the limit: code is exact, not right. It needs D's spec.

| # | Change | Where |
|---|---|---|
| E1 | A fifth route, **drawn graphic**, for diagrams, charts, maps, timelines and technical drawings. The planner writes a **declarative scene**, not executable code: a canvas, the style sheet (C2), shapes (rectangle, line, arrow, circle, polygon, text, image, group and repeat) in real units with one scale, and a timeline of actions (appear, build in order, move along a path, highlight, fade), each keyed to a time or a narration word (A1). The server validates and renders it. No model-written code ever runs on the server. | plan schema, a new `drawn.py` renderer (Pillow and ffmpeg, already on the server) |
| E2 | The renderer outputs the shot's exact frames at the film's size and frame rate. The result is reviewed and approved like a take. Edits are re-renders at no cost and are not counted against the cap. | `visuals_stage`, page (Takes step) |
| E3 | Route choice in the prompt: drawn graphic for anything with measurements, quantities, sequences or labels that must be exact; AI still or AI video for scenes with people, places and materials; an AI-painted illustration only where a painterly look is wanted and nothing must be exact. | prompt |
| E4 | The AI-image graphic sequence (design/65 S1) stays available, but stops being the default for technical diagrams. AI video for graphics stays off. | prompt |

## F. Sound for AI shots

| # | Change | Where |
|---|---|---|
| F1 | Every AI shot (still, take, graphic) carries sound-effect notes written by the planner from the shot's beats, in the same form analysis gives real clips (`target_track: A3`, start, end, description, `HUMAN_TO_SOURCE`). They reach the editor's finishing checklist like the real clips' notes. Free. | plan schema, `stage2`/`stage3` cue collection, delivery checklist |
| F2 | Optional, after a test on a few shots: an AI take's own audio is kept as quiet ambient sound on A2, as nat sound from real clips is. A short Gemini check on the **selected** take first finds the clean stretch and drops any music or voice. The motion prompt then names one sound tied to the action. Decide for Kling and Seedance (sound on, or Omni only). | `video_providers.motion_text`, assembly, a short check prompt |

## H. No repeated pictures

**Why.** The first cut already refuses a second use of any clip, even another part of it, unless the operator approves a `reuse` decision with a reason (`stage2/validator.py`, design/21 rule 7). The visuals stage has no such rule. Its prompt says footage not used in the edit may be used, but nothing checks it against what the first cut already shows. On VW-6, frames of identical or near-identical pictures appear twice:
- the drone shot, as a frozen frame at 0:16–0:22 and moving at 0:54–0:59
- the plinth wall at 3:10–3:14 and 3:22–3:26
- one shot at 3:58–4:02 and 4:34–4:40
- the arched brick wall at 2:26–2:30 and 4:46–4:49

| # | Change | Where |
|---|---|---|
| H1 | **One ledger of what the film shows.** Every placed source is recorded in one list shared by the first cut and visuals: a clip stretch (clip, in, out), a footage frame (clip, time), an AI picture or take (its id and its composition parent). | `stage2` output, `visuals_stage` session |
| H2 | **The same rule in visuals as in the first cut.** A footage frame or clip stretch from a clip already on screen anywhere in the film (first cut or visuals) is a reuse. It is refused unless the operator approves a reuse with a reason. "Not used in the edit" means not in the ledger, not just not in the first cut. | `validate_plan`, `visuals_stage.frame`, the new clip fill (B3) |
| H3 | **Never a frozen frame of a clip that plays elsewhere.** A frame of a clip that is also shown moving is refused, even with a reuse approval. Use a different clip or the moving stretch. | `validate_plan` |
| H4 | **When a reuse is approved, it must not look like one:** at least 60 s apart in the film, a different stretch of the clip (no overlap in source time), and a clearly different framing (a crop of at least 30%, or a different part of the frame). | `validate_plan`, assembly crop |
| H5 | **AI pictures do not repeat either.** Two shots never share a start image or a composition. References (a person's or object's identity) may repeat, which is the point of them, but each shot's framing, angle or action must differ, and the plan states how. | prompt, `validate_plan` (same keyframe on two shots refused) |
| H6 | **A look-alike check on the built film.** Before the operator watches the assembly, every pair of shots is compared by a cheap picture fingerprint, at the start, middle and end frame. Pairs that look alike are listed with their times, whatever their source, and the plan check shows the same list at the plan stage for the pictures already made. Diagrams in one approved style are compared by content, not by background, so a shared style is not flagged. | `stage3/assembly.py`, `visuals_stage` |
| H7 | **A return is reimagined, not repeated.** When the narration comes back to something already shown (it reinforces a point, recalls an earlier step, or the film's flow is better served by seeing the subject again), the planner may show that subject again. It does so as a **reimagined shot**: the same subject from a different angle, perspective, distance or moment. The earlier picture is used as the identity reference, never as the frame. The route is any that fits: another clip that shows the subject from elsewhere, or an AI still or take composed anew. The plan marks the shot `return_of: <earlier shot>` with the reason, and states what is different (for example, "the same wall from ground level, looking up, where the first was a wide side view"). This is the preferred way to show a subject twice. A plain reuse of the same footage (H2, H4) is allowed **only when a reimagined shot has been tried and offers nothing new**: the plan must name the reimagined option it considered and say why it adds nothing. It still needs the operator's explicit approval with their words, on the page or in chat, through the same server function. Without that approval the server refuses it. The look-alike check (H6) treats a return as a repeat if it still looks like the original. | prompt, plan schema (`return_of`, `differs_by`), `validate_plan` |

## I. Library

The rules above that are about writing pictures, not about VideoWizard's server, also go into the image prompt library: timing to narration in `playbooks/video-clip.md` and `video-frame.md`; claim coverage and the graphic style sheet in `playbooks/web-app.md` (process-explainer); and the technical drawing spec as its own guide (D6). They are marked draft and untested, and the next snapshot picks them up.

## Tests first

- A1: a gap with three sentences yields three timed sentences that match the timing file; the packet carries the gap's and the neighbours'.
- A3: a cut 1 s inside a sentence warns; a cut in a pause does not; a title 1.5 s after its word warns.
- H2: a visuals frame from a clip the first cut shows is refused without a reuse approval, and passes with one. H3: a frame of a clip shown moving elsewhere is refused even with approval. H4: an approved reuse 30 s apart is refused. H5: two shots with the same start image are refused. H7: a shot marked `return_of` with a `differs_by` passes; without `differs_by` it is refused; a plain reuse without a named reimagined alternative, or without the operator's approval, is refused; a return whose built frames look like the original is listed by H6. H6: two identical shots in a built film are listed with their times; two different diagrams in one style are not.
- B1: a 3.5 s photographic still is refused; two different 3 s stills filling 6 s pass; a 7 s diagram with one state is refused; a 7 s build of three states passes.
- B2: a still renders the shot's exact frames with a push; `none` without a reason is refused.
- B3: a moving clip stretch fills a shot with its in and out frames.
- B4: a plan with 40% frozen time warns at the 25% default.
- C1: a graphic whose checklist misses a spoken claim is refused at check. C4: an image request without an answer warns in the first release and is refused after it.
- D3: a drawing spec with an `unknown` dimension and a figure shown is refused; with "illustrative, not to scale" it passes.
- E1: a scene with a forbidden key (anything executable) is refused; a valid scene renders N frames exactly; a word-keyed action starts on that word's frame.
- F1: AI shots' notes appear in the delivery checklist beside the real clips' notes.

## Not covered

- server/tests (Docker).
- Gemini's accuracy when measuring from frames (D2.2). The operator's spec approval is the backstop.
- How viewers respond to the default push on every still (B2). Start at 3% and adjust.
- Whether the declarative scene format is rich enough for every domain. Start with the listed shapes and add one when a real film needs it.
- F2 depends on a listening test of Omni's audio.

## Order

1. A (timing), B (motion and limits) and H (no repeats). These change every film most.
2. C and D (graphics content, style and spec).
3. E (drawn route).
4. F and I.

## SK's decisions (23 Oct 2026, one at a time) and the builder's corrections

These override the sections above where they differ.

| | Decision |
|---|---|
| B2 | Every still and graphic state moves by **5 %** across its shot. **Graphics (diagram, animation) move closer only** (`push_in` or `none`), never sideways, so labels never slide out of frame. `none` needs a reason. |
| B4 | The frozen share warns above **10 %** of the film (counting only what is marked `none` and graphic holds), shown on the treatment; a film that needs more goes ahead with a reason. |
| F | **F1 is built.** **F2 stays off**, tested on five Omni takes from the next film that allows camera sound; AI sound always follows the media step's camera-sound answer. |
| E | **Yes: the drawn graphic is the default route for technical diagrams**, built after D. |
| B1 | A still **with movement at most 4 s**; a still marked `none` **at most 3 s**; a graphic state **at most 5 s**; a graphic on screen over about 4 s is a build or a drawn animation. All **warn for one release, then refuse**. |
| H4 | An approved reuse: **at least 60 s apart** and **a different stretch** of the clip; its framing differs **only within the clip's safe enlargement** (the analysis's `max_safe_zoom_limit`). Where that is too small for a clearly different framing (a crop of 30 %, i.e. 1.43×; 1080p footage allows 1.35×), the plain reuse is **refused** and the planner uses a reimagined shot (H7). |

Builder's corrections from reading the code (`../design-88-89-review-2026-10-23.md`):

- **A1** reads the film-time words and sentences from the options package (`pk['narration']`, timeline frames with the approved pauses already in), not the voice stage's `timing.json`, which is in narration time.
- **C4** matters more than stated: a picture sent without an answer form gets **no** check today, not three fixed lines.
- **H2** goes in `add_reference` and the placement functions; there is no `visuals_stage.frame`.
- **H5** refuses a shared **start** image only; the end image of one segment is the start of the next within one continuous shot by design (design/67, 71 P4).
- **E2** puts drawn graphics on the Takes step, which today lists only video shots; a font file on the VM is checked before E.
- **F2**, when tested, changes design/84's "No dialogue. No music." line and assembly's take audio (dropped today).
