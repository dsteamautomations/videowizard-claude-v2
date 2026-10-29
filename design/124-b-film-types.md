# Work item 7: rules that misfire by film type (preparation, treatment, plan, picture search)

Read-only review, 29 Oct 2026. Sources: `server/procedures/v3.json` (stage visuals: `prompt` sections and `steps[n]`), `server/app/visual_contract.py`, `server/app/visuals_stage.py`, design/122, design/124. Anything SK has already decided in design/124 (Changes 1–9, the opening-gap rule, Note D, A2–A4 answers, the spending limit) is not raised again.

Film types: **F1** opens on footage / opens on a gap · **F2** human story / technical record · **F3** no footage (design/122) · **F4** short gap (~3 s) / long gap (30 s+) · **F5** no people / person speaking to camera · **F6** busy / quiet.

Enforced: **R** = the server refuses, **W** = the server warns, **no** = text only.

---

1. **A footage clip in the plan is treated as an AI still or an AI video**
   - Rule: the plan has no "footage" shot type. A clip stretch fills an `image` or a `video` shot (visuals_stage.py:3742). The treatment's `footage` route counts only as `still` (visuals_stage.py:310: "a frame shown in the film is a still in the plan"). Still length (visual_contract.py:641-645): "still of {s} s: at most 4 s; fill the stretch with several different stills or a moving shot".
   - Misfires: films with spare footage (F1 footage-led, F2 human story), and long gaps (F4). Example: an 8 s stretch of real footage of the mason, planned as `image`, is warned as an over-long still and told to move 5 %. Planned as `video`, it gets refused above 10 s ("every take is Gemini Omni"), refused at propose unless the treatment says `video`, needs gaze, headings, measured positions and three fixed landmarks for real footage, counts as AI video in the cost and `ai_run`, and footage stills also collect `light_missing`, `camera_reason_missing` and `activity_missing`.
   - Server: R and W.
   - Fix: give the plan a footage shot (for example `visual_type: footage` or `source: clip`, matching the treatment route). It keeps the timing, crop, reuse and no-repeat rules and skips the rules made for generated pictures: still length and motion, the video form, the Omni cap, `ai_run`, cost, life, light and camera reason.

2. **A busy scene needs a full person record for every background worker, and other rules then contradict that**
   - Rule: prompt §4: "Plan beats for every visible person, animal or object that acts, including secondary and background subjects (a background subject with beats is an element …)". life_missing (visual_contract.py:590-592) asks for "secondary or background subjects with beats". `Group.items` max_length=30 (:188), and `different` needs one trait per head (:786).
   - Misfires: F6 busy (a site with 15–40 workers). Each worker becomes an element with a description, a size (W), an outfit per scene (R), measured positions, headings, gaze and beats. A crowd of more than 30 cannot be `different`. `same` writes "all alike", which gives a crowd of clones. A background worker described as "mixing mortar in the background" also trips the `passer_by` warning (visual_contract.py:1003-1005: "never a named element with a sheet"). Meanwhile steps[2] lets the scene's ambient line cover "people in the background at work". The same crowd is therefore both required as elements and warned against being elements.
   - Server: R (outfit, description, groups) and W (life_missing, passer_by, element_size_missing).
   - Fix: only background people who do a planned action that matters are elements with beats. The rest of a busy scene is the ambient line plus one `groups` entry (count, mode `varied`, a few traits used in rotation). `life_missing` accepts that, and `passer_by` does not fire on an element that has beats.
   - **NEEDS-SK** (where to draw the line between a named worker and the crowd).

3. **A living thing that stays put must still move a body-length**
   - Rule: visual_contract.py:718-720: "{id} is a living thing that stands still from start to end; give it a small move (its end position a body-length or so from its start, against a landmark)". Prompt §4: "a living thing that is not the actor moves a body-length by the end".
   - Misfires: F5 (the listening angle the guide itself offers for a person speaking to camera), F6 quiet (a person seated at a desk, a craftsman bent over a bench while someone else acts, a sleeping dog, a cow lying down). Example: the client listening across a table must walk a body-length in 4 s, or the plan is refused.
   - Server: R.
   - Fix: a living subject that holds may keep its position when `hold_reason` names its small life (breathing, a head turn, hands). The body-length move stays the default for a standing figure in a normal or busy scene.

4. **Every place must look occupied or in use, even when the film wants it clean**
   - Rule: visual_contract.py:867-869: "{id} is a place the film shows: give signs_of_use, two or more traces of work or living". Prompt §4 adds the must line "the place looks occupied or in use" to every place picture. steps[2]: "never staged empty unless the treatment says so". The server has no way to record "unless".
   - Misfires: F6 quiet (a finished show home at handover, a new empty room, a product in a clean showroom), F2 technical (a plan view of a site). Example: a handover film that must show a spotless new flat is refused without two "traces of living", and every picture of it is checked for looking lived in.
   - Server: R and a must line.
   - Fix: give a place a `staged_clean` reason (like `studio_background`, approved with the treatment). Then `signs_of_use` is optional and the must line becomes "clean and unused, as planned". Every other place keeps today's rule.

5. **Ordinary words read as craft techniques**
   - Rule: visual_contract.py:392-395 and 787-792 (`TECHNIQUE_VERBS`): "the technique '{tech}' … is not an element: add it (kind technique …) so it joins the reference round". The patterns `point(s|ed|ing)?`, `drill(s|ed|ing)?`, `paint(s|ed|ing)?`, `tie(s|d)?`, `polish…`, `mould…` also match nouns and gestures.
   - Misfires: F2 human story, F2 technical record, F5 person speaking. Example: "the engineer points at the crack", "picks up the drill", "adjusts his tie" or "dips the brush in paint" are each refused until a technique element (POINTING, DRILLING, TYING, PAINTING) exists. That element then joins the reference round as a Google search for masonry pointing.
   - Server: R.
   - Fix: match only when the word is the beat's working action. Exclude "point(s) at/to", and bare nouns after "the / a / his / in" (drill, paint, tie, polish, mould).

6. **Size words, including non-size words, force a size comparison, even on charts**
   - Rule: visual_contract.py:396 and 793-799: "its claim or descriptor is about size ({word}): give the subject a size value and name compare_to, a thing in frame to read it against". The list includes light, less, fewer, short and wide, and the check runs on every visual type.
   - Misfires: F2 technical record (a drawn chart "25 % fewer bricks" or "less cement" needs a `compare_to` element in frame), F6 quiet ("a light, airy room", "a short walk to the gate", "a wide verandah"). Example: the descriptor "light" on an empty-room still is refused for lacking a measured size.
   - Server: R.
   - Fix: skip graphic and drawn shots, which show size by their figures. Drop light, less, fewer and short, or require the word to be about the subject's own size.

7. **Graphic time limits clash with "a build takes six to ten seconds"**
   - Rule: prompt §4: "six to ten seconds for a diagram that builds" and "read its text twice". Against it: graphics_run (visual_contract.py:1025-1026, 1051-1053): "above 8 s, break it with a camera shot"; graphic_unbuilt (:646-648) on any diagram over 4 s; `all_graphics` (:890).
   - Misfires: F2 technical record, F4 long gap, F3 (no camera shot exists). Example: a three-state build of 9 s, which the guide recommends, warns `graphics_run`. A 12-word text card held 6 s so it can be read twice warns that it should be built in states. A 30 s explanation of a cavity wall cannot avoid `graphics_run` and `all_graphics`, although the guide says "a technical record may lean on graphics".
   - Server: W.
   - Fix: exempt `graphic_kind` title and text from `graphic_unbuilt`. Count one build as one graphic, and warn `graphics_run` only beyond about 12 s, or when the treatment did not call the film a technical record.
   - **NEEDS-SK** (the threshold).

8. **The close-up refusal fires on any framing containing the letters "close"**
   - Rule: visual_contract.py:652-655: `if 'close' in shot.framing.lower()` → "close on what fact {id} describes, and that fact is unknown: … frame the shot wider". It checks every fact of every element in the shot.
   - Misfires: F6 quiet and F5 no people. Framings such as "wide, gate closed", "enclosed courtyard" or "close to the far wall" are refused because a background element has an unknown fact.
   - Server: R.
   - Fix: test `shot.size` in MCU/CU/ECU (or the word "close-up"), and only the facts of the shot's subject.

9. **"No people" in a framing demands a group of people**
   - Rule: visual_contract.py:776-781: `GROUP_WORDS` is matched against framing and appearance → "shows several {people}: give groups an entry". Negation is not read.
   - Misfires: F5 no people, F6 quiet. Example: the framing "empty site at dawn, no workers yet" is refused until a `groups` entry for "workers" (count ≥ 2) is added. That entry then writes a "workers" line into the prompt.
   - Server: R.
   - Fix: ignore a group word that follows no, without, empty of or before the; or count only subjects and objects.

10. **Every video shot gets a warning whatever it does**
   - Rule: visual_contract.py:823-828. `end_state` fires on every shot with changes and no exact end, which is the decided default. `changes_missing` fires on every shot without changes.
   - Misfires: everywhere. Worst in F6 quiet and F5 no people. Example: an ambient-only shot (fronds moving, steam rising) legitimately changes nothing and is still told to list changes. Every normal action shot is told about start-only. The operator sees a warning on every video shot.
   - Server: W.
   - Fix: `changes_missing` only when a subject acts. Drop the `end_state` warning, since start-only is the agreed default and the check already needs `changes`.

11. **Shot-size order ignores the footage beside the gap**
   - Rule: visual_contract.py:1035-1042: "a new place opens wide or medium-wide, unless a reveal is stated", and "a {CU} of a subject not seen wider in this scene yet".
   - Misfires: F1 opens on footage and F4 short gap. Example: a 3 s close insert of mortar between two footage shots that already showed the mason wide is warned twice. The same happens to a quiet product detail cut into footage of the product.
   - Server: W.
   - Fix: count the neighbouring footage (`gap_neighbours`) as the wider view when the scene's `boundary_continuity` continues that footage's place. The rule stays for a scene that really opens a new place.

12. **AI angles of a real person speaking to camera become a stranger**
   - Rule: steps[2]: "When footage shows a person speaking to camera, offer non-speaking angles of them (listening, hands at work, profile, from behind), footage first, AI only where none exists."
   - Misfires: F5 speaking to camera. Since decision 5, the AI "profile" or "from behind" of the client's MD is made from words. It shows a representative person, cut between real shots of the MD. That clashes with prompt §2: "provided it does not pretend to be the client's own site, people …".
   - Server: no.
   - Fix: for an identified speaker, AI only for hands or a back view where identity is not asserted, or a take from their own footage frame as the start image (allowed per SK's yes on decision 5). Otherwise use footage only.
   - **NEEDS-SK.**

13. **Rules tied to footage remain in a film with no footage**
   - Rule: prompt §4, appearance: "its texture line, sharp or soft, comes from the recorded footage character in the package, never from an assumption; measured from the clips". Also: "matched to the footage beside it"; the real-light line "from … the measured light of the approved footage frames"; `ai_run` (visual_contract.py:885-886) and `all_graphics` (:890) advise "a frame from the footage"; scenes must explain "continuity with the real footage on both sides".
   - Misfires: F3 (impossible: no clips, no measured light, no neighbours). Also the edges of an F1 film that opens or ends on a gap. design/122 step 4 plans one short paragraph and Change 3 puts the look in the Direction box, but these sentences still say the opposite.
   - Server: W (advice only).
   - Fix: when `footage = none`, each of these sentences takes the Direction box's look instead of the footage, and the warnings drop the "frame from the footage" advice. Write this as conditions on the sentences themselves in v3, not as a paragraph that overrides them.

14. **The treatment counts a mixed gap's seconds as its first route, and all of it as video**
   - Rule: visuals_stage.py:442-446: `first = routes_[0]` gets all the gap's seconds, and `if 'video' in routes_: video_seconds += e['seconds']`. The prompt asks the treatment for "the seconds of graphics", but the server never computes them.
   - Misfires: F4 long gap and F2 human story mixes. Example: a 30 s gap of footage, 6 s of AI video and an 8 s graphic is shown as 30 s of footage, costed as 30 s of AI video, and shows 0 s of graphics.
   - Server: computed and shown to the operator.
   - Fix: when an entry lists its shots or segments with seconds, add them per route. Otherwise keep today's sum.

15. **Short AI runs in long gaps and in a film with no footage**
   - Rule: prompt §4: "Consecutive AI video in a gap under 12 s (ai_run): break it with a frame, still or graphic; shots 3–5 s". Against it, §1 says Omni makes 3–10 s and a passage is split "where an action begins or ends".
   - Misfires: F4 long gap and F3 human story. A 40 s paragraph of a mason's day has no footage to break with, so it must alternate stills and video every 12 s. One continuous 8 s action breaks "3–5 s".
   - Server: W (12 s only; 3–5 s is not checked).
   - Fix: keep the 12 s break where footage exists. In F3, or when the treatment says so, allow a longer run and drop "3–5 s" in favour of "split where an action begins or ends".
   - **NEEDS-SK.**

16. **Three fixed landmarks even when none is in frame**
   - Rule: visual_contract.py:800-805: "names three fixed things of the background in fixed (landmark ids; all of them when the scene has fewer than three)". The server writes them into the prompt.
   - Misfires: F6 quiet product and close work shots. Example: an ECU of hands pointing a joint must name the gate, the stack and the wall, none of them visible. The prompt then asks for them, which pushes the model to widen.
   - Server: R.
   - Fix: name only the landmarks in frame, and allow fewer (down to none) at MCU or closer.

17. **A gaze at the camera is refused**
   - Rule: visual_contract.py:771: "gaze target is a landmark of the scene or a named element".
   - Misfires: F5 (an AI shot where a worker looks up into the lens; a presenter in F3).
   - Server: R.
   - Fix: accept `camera` as a gaze target.

18. **Different colours for two people, even in uniform**
   - Rule: steps[3]: "Two people in one film wear clothes of different colour families, unless the footage fixes their clothes."
   - Misfires: F3 and F6 busy, when the brief fixes a uniform (the client's blue overalls) but there is no footage. The rule forces different colours. It also clashes with `groups` mode `same` ("one uniform").
   - Server: no.
   - Fix: "unless the footage or the brief fixes their clothes (a uniform)".

19. **A conceptual graphic is asked for a drawing spec**
   - Rule: visual_contract.py:677-680, spec_missing: "a drawing of a real object … needs a drawing_spec". It is skipped only for title or text, or when production_method contains label, title, chart, icon and similar.
   - Misfires: F2 (an idea graphic, for example "heat leaving a house", which the guide says is "a picture, never shapes"). It warns unless the right word happens to be in production_method.
   - Server: W.
   - Fix: skip it when `depicts` or `claims` name no real object and no figure, instead of relying on keywords.

20. **"Next step of a process" warning fires on figures of speech**
   - Rule: visual_contract.py:666-668: narration starting "then / next / once / after that", or containing "on top of".
   - Misfires: F2 ("On top of that, the cost falls", "Once, this was farmland"): the warning asks for `carries_over` where there is no process.
   - Server: W.
   - Fix: fire only when the shot or the one before has acting subjects (a real process).

21. **"frame" read as footage**
   - Rule: visual_contract.py:980 and 1000: `FOOTAGE_CITED = \b(footage|frame)\b` → "a thing the footage shows is identity exact".
   - Misfires: F2 technical and F3. A size sourced as "maker sheet, door frame 2100 mm", or in a no-footage film, warns that the element must be exact with a footage frame.
   - Server: W.
   - Fix: match "footage", "clip" or "frame of/from clip" only.

---

## Dead weight

- **`MAX_GENERATED_SHOT_S = 30` refusal** (visual_contract.py:603-605). It can never bind, because the Omni 10 s refusal (:702-705) refuses the same shots first. Remove it.
- **`end_state` warning** (:823-825). It fires on the decided default, start-only, so it carries no information (see item 10).
- **The treatment's `activity_level` per gap** (steps[1]; visuals_stage.py:432). It is stored but never compared with the plan's scene levels, and it means nothing for a graphic-only gap. Either compare it at propose or drop it.
- **`boundary_continuity` "with the real footage on both sides"** (prompt §4; required field, :308). There is nothing to fill for a gap at the film's start or end, or in F3. Make it "the neighbouring pictures, footage or planned".
- **Person rows offered "Search" in the round** (steps[3]). Since decision 5, a web picture of a person is never sent to the picture AI, so a person search serves only as a description aid. Default person rows to the footage picture or Ignore, with Search optional for the description. **NEEDS-SK.**

Counts: 21 misfires (refused: 8, refused and warned: 2, warned: 8, shown in the estimate: 1, text only: 2), 5 dead-weight items, 5 tagged NEEDS-SK (items 2, 7, 12, 15, and the person-search row).
