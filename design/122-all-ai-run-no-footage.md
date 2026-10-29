# 122 — A run with no footage: everything made by AI (scenario 3)

Status: **plan with SK's four answers, 29 Oct 2026; waiting for the go-ahead to build. Nothing built.**

## The requirement, restated
Some films have no real shoot at all. VideoWizard must still make them: the script, the voice and the narration as today, then every picture of the film made in the Visuals stage (AI stills, AI video, graphics, drawn diagrams), then assembly and delivery as today.

The very first question of a new run, before the client name, is which material exists:
1. **Video and photos from a real shoot**: today's flow, unchanged.
2. **Photos only**: not built yet (design/121 discussion; scenario 2 comes later).
3. **Nothing: everything AI**: this note.

## What the code does today (read 29 Oct 2026)
The film's backbone is the real video. These stages exist only to turn clips into a first cut: **media** (the clips), **analysis** (the AI's notes on each clip), **options** (the clip choices per scene, and the narration timing), **master** (the operator's film, with blanks), **first cut** (that film, approved). Visuals fills only the blanks; assembly puts the fills into the master's blanks.

What breaks with no footage:

| Where | What it needs | What happens with no footage |
|---|---|---|
| Stage order (`core.compute_next`) | every stage in the procedure, in order | media refuses with no clips; the run is stuck at media |
| Visuals prepare (`visuals_stage.gaps_source`) | a master output | refused: "Visuals needs a finalized plan" |
| Visuals timing (`gap_timing`, `ensure_timing`) | the options package's narration in frames | **silent**: no sentences or words, so cuts on pauses, pictures on their words and the timing checks all switch off without saying so |
| Visuals units (`declared_units`) | the master's `units.visuals` | the visuals step is treated as one item, not per gap |
| Assembly (`stage3/assembly.py`) | the master plan, the options package and session (narration audio, pieces, timeline) | refused: "needs an accepted master" |
| Delivery (`stage3/delivery.py`) | master, media, options package (subtitles come from it) | refused: no media |
| Footage look (`footage.py`) | the clips | prints "Your footage: camera unknown…", which is misleading |
| Light line, frames from clips, reuse rules, footage neighbours | clips | quietly skipped, or refused only if the assistant tries (`frame`, `clip`) |
| Assistant's instructions (visuals) | "footage first", "grab a frame for every element", match the footage's light | wrong for this run: there is no footage |

## The approach: one small "AI first cut" step that writes what the later stages read
Rather than teaching visuals, assembly and delivery a second way of working, the server makes, in one step, the same records the skipped stages would have left, with nothing in them except the narration and one blank over the whole film. The later stages then run unchanged.

**Why this way:** visuals, assembly and delivery are the largest and most tested parts; changing them in many places is where new bugs come from. One step that fills the records once is smaller and easier to check.

### Step by step
1. **The first question (start).**
   - A new run field, `footage` (`shoot` | `photos` | `none`), chosen once at `vw start` and never changed, stored like the image model (design/120): a database column with a check, required by the server, refused by the chat tool when missing ("Ask the operator what material exists… No run was created.").
   - The chat tool's start guidance asks it **first**, before the client name, then the image model, then the client as today.
   - `photos`: refused at start for now with "Photos only is not available yet; choose shoot or none" (until scenario 2 is built). *Open question 1.*
2. **Stage order.** For a `none` run, `compute_next` skips media, analysis, options, master and first cut, and puts one new stage after voice: **AI first cut** (`ai_first_cut`). Today's runs are untouched (the skip applies only when `footage = none`).
3. **The AI first cut step** (server, one command `vw ai-cut record --quote "…"`, the operator's yes):
   - Reads the approved voice: narration audio, `timing.json` (words with seconds), the length.
   - Computes the narration in frames with the same functions options uses today (`stage2/narration.py`: `plan`, `word_rows`, `sentences`), at the film's frame rate and size (25 fps, 1920×1080 by default, as options uses).
   - Writes, with the shapes the later stages already read:
     - an options session and package: the narration (key to the audio, pieces, sentences), the timeline, `sub_clips: []`, `beats` (one per narration passage, from the script), `clips: {}`;
     - a master plan: one gap event from frame 0 to the end, `gaps: [{shot_id: 'GAP_ALL', start_frame, end_frame, passage_ids: all, reason: 'AI film: no footage | narration: …'}]`, `units: {visuals: ['GAP_ALL']}`, its digest;
     - a master film and a first-cut film: a black picture with the narration (one ffmpeg call), because these stages require a file;
     - the first-cut output from the same summary.
   - **One gap or several?** One gap over a 3-minute film is a very large single unit for the visuals page and plan. *Open question 2:* split the blank at the script's paragraphs (one gap per paragraph, as options proposes scenes today). Recommended: one gap per paragraph.
4. **Visuals with no footage.**
   - `gaps_source`: take the gaps from this first cut (it carries the digest, fps and size).
   - `gap_timing`: falls back to the voice timing when there is no options package, so timing is never silently empty.
   - The footage line says "No footage: an AI film" instead of "camera unknown".
   - The look: there is no footage to match, so the treatment proposes the look (palette, contrast, light) for every gap; this rule already exists for a gap with no footage beside it (design/103 A7) and now applies to the whole film.
   - The assistant's instructions get a short paragraph for a `none` run: no frames from clips, no "footage first", web pictures and generated pictures only; the treatment proposes the film's look once; the light and colour check compares pictures with each other, not with footage.
5. **Assembly and delivery.** Unchanged code paths, reading the records step 3 wrote. Two small guards: delivery reads `media.summary.copies` and `media.summary.clips` only when a media output exists; the editor's package lists no camera clips.
6. **No cost cap on any film (SK).** `check_cap` no longer refuses (all runs); the estimate and the spend so far are still shown, on the page and in status. The procedure text loses "the server refuses a paid call that would pass it", and the tests of the cap's refusal change to "shown, not refused".

### Found while reading for the build (29 Oct 2026, no code changed)
- The master builder (`stage2/stage.py` `build_master`) already turns every scene with no chosen clip into one blank, and the options step already makes one scene per script paragraph (`NR.paragraph_scenes`). With no clips at all, the existing code gives exactly SK's answer 2: one blank per paragraph. The AI-cut step reuses it instead of new gap code.
- The options package can be built with no clips (`package.build` with empty rows); the options "prepare" refuses only because it insists on analysed clips, so the AI-cut step calls the narration part and the package builder directly.
- The master check (`validate_master`) accepts a film that is all blanks (it checks runtime against the scenes' lengths only).
- `core.output` records a stage only when it is the next one; the AI-cut step needs a small helper that records the skipped stages' outputs in one go, inside the same step.

## Edge cases and failure modes
- **Old runs:** no `footage` value. Treated as `shoot`, so nothing changes for them.
- **A `none` run with clips put in `in/` by mistake:** media is skipped, so they are never read; the start line says so.
- **Voice not approved yet:** the AI-cut step refuses until the voice is recorded.
- **Voice redone after the AI cut:** today's "revise makes later stages stale" applies; the AI cut is made again from the new narration, and visuals sees the new gaps (the existing stale-plan checks apply).
- **Narration with long silences or very short passages:** gap edges fall on narration pauses (existing timing functions); a passage shorter than the shortest shot (about 2 s) is merged with its neighbour.
- **Very long films:** many gaps; the reference round and the cap already work per run, so no new limit, but the cap matters (question 3).
- **No pauses between scenes:** options is where the operator approves pauses; with options skipped there are none. *Open question 4:* keep a short scenes-and-pauses approval inside the AI-cut step (same screen and rules as options), or none. Recommended: none for now.
- **The page and the chat tool both work:** the AI-cut step is one server function both call (the repo's "one flow, two front ends" rule).
- **The ₹ cap refuses partway through the film:** existing behaviour (the server refuses the paid call and says the spend); the run waits for SK to raise the cap.
- **Assembly with zero camera clips:** never run before; the first full test run is the real check (see "not covered").

## Tests (written first)
- start refused without `--footage`; `photos` refused; `none` and `shoot` stored and never changed;
- `compute_next`: a `none` run goes voice → ai_first_cut → visuals; a `shoot` run unchanged; an old run (no value) unchanged;
- the AI-cut step: refused before voice; writes the master, first cut, options package and session in the shapes visuals, assembly and delivery read (built from a recorded voice fixture); gaps cover the film with no hole and no overlap; units list every gap;
- visuals `prepare` on a `none` run: gaps from the AI cut, timing present, footage line "No footage";
- assembly `prepare` and `build` with one all-fill gap and zero camera events;
- delivery bundle with no media output.

## Not covered by this plan
- Scenario 2 (photos only) and photos in scenario 1.
- A full run end to end on the VM: needs a real script, voice and paid pictures; to do as the first test run after the deploy, with SK's go-ahead.
- Background music and sound effects: as today (assembly's existing behaviour).

## Open questions for SK (one at a time)
1. ~~At start, show "Photos only"…?~~ **Answered (SK, 29 Oct 2026): show it, refuse it with "not available yet".**
2. ~~One blank or one per paragraph?~~ **Answered (SK, 29 Oct 2026): one blank per script paragraph** (step 3's master gaps: `GAP_P01`, `GAP_P02` … in film order, each from its paragraph's first word to the next paragraph's first word, the last to the end; `units.visuals` lists them all).
3. ~~The cost cap for an AI film?~~ **Answered (SK, 29 Oct 2026, final): no spending limit on any film**: with a real shoot, photos only, or all AI. The server never refuses a paid call for the cap; the treatment still shows the estimated cost, and every paid step is still announced. (SK first said all-AI films only, then corrected it to all films the same day.) A limit may come back later as a feature request.
4. ~~A scenes-and-pauses approval in the AI-cut step?~~ **Answered (SK, 29 Oct 2026): not now.** No added silences; cuts follow the narration's own pauses. May be added later if films feel rushed.

**All four answered. The plan is ready for SK's go-ahead to build.**
