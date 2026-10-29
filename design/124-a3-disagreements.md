# Visuals stage instructions: places where two copies disagree

Sources: `v3_guide.txt` (the main guide, sections 0–8; "G§n" plus the file line) and `v3_steps.txt` (the step list; "S-STEP n" plus the file line). The server code is in `server/app/visual_contract.py` (VC) and `server/app/visuals_stage.py` (VS), plus `library.py` and `config.py` where named. Quotes are exact. A "…" marks text left out of a quote.

The list is ordered by how badly each one could mislead the assistant. The worst come first: those where following one copy makes the server refuse the work.

---

## DISAGREEMENTS

### 1. Labels: typed into the prompt, or only through `exact_text`?
- **Copy A** (G§1, line 17): "Put every label, number and caption in the prompt exactly as it must read, keep labels short, and check each one on the candidate before approval"
- **Copy A2** (S-STEP 3, line 11): "For a diagram, chart or labelled picture write every label and number in the prompt exactly and check each on the candidate before asking for approval."
- **Copy B** (S-STEP 3, line 11): "Words to be read in a picture (a title, a label, a sign, a word on a bag) go only through the answer's `exact_text` … quoted words in the prompt that are not an entry are refused". G§2 line 24 agrees with B: "Put each label in the answer form's exact text: each becomes a checked line."
- **Server:** it refuses. `library.py:199-205` (`check_quoted`) rejects any quoted words of two or more in the prompt that are not an `exact_text` entry. It is called at VS:2211 and VS:2216. `library.py:180` refuses an entry that has no place or size. The server then writes the "Render exactly this text…" block into the prompt itself (VS:2278-2280).
- **Resolution:** Keep B and reword A and A2 to: "Put every label, number and caption in the answer's `exact_text` (text, place, size); the server writes it into the prompt; check each on the candidate." Copies A and A2 lead straight to a refusal.

### 2. "Text is not a reason to choose a route" against "exact figures must be drawn"
- **Copy A** (G§1, line 17): "Text is not a reason to choose or avoid a route: current image models write accurate text." In the same section, line 13 lists the AI still as "a diagram, a chart or a labelled picture". G§2 line 24 gives the sample label "25 % fewer bricks", which contains a number.
- **Copy B** (S-STEP 4, line 14): "A graphic with measurements, quantities, sequences or labels that must be exact takes the drawn route … a diagram or build with exact sizes or numbers that is not drawn is refused".
- **Server:** it refuses. VC:626-629 refuses a `diagram` or `animation` shot (an AI graphic) when any claim contains a digit or its drawing spec has a known size. The message is "an AI-painted graphic is for a look, never for a figure". Words alone are not checked. This means B's "labels that must be exact" asks for more than the server enforces, and A's "a chart" as an AI still almost always fails, because a chart carries numbers.
- **Resolution:** Merge into: "Words alone do not decide the route (image models write words accurately); any figure (a number, size or count) in a graphic's claims or spec takes the drawn route, so charts and measured diagrams are drawn." The server enforces exactly this line.

### 3. An end image where several things change: "made whole" or refused?
- **Copy A** (S-STEP 3, line 11): "an end where several things change, or the framing, is made whole as before."
- **Copy B** (same paragraph): "Every end image is an edit inside one region of its start (several places or the framing itself: a start-only take instead)". G§6 line 47 describes the end image with no region at all: "generate it from the start image as its parent (`--kind keyframe --parents <start>`) with a prompt that names only the change".
- **Server:** it refuses. VS:2253-2256 refuses any end keyframe without `--region`, with the message "Several places, or the framing itself: make the shot start-only (end_state_exact false)". VS:2274-2275 warns when an `end_prompt` has no `--end-region`.
- **Resolution:** Delete A and add the region to G§6: "an end image is an edit inside one region (a third of the frame at most); if several places or the framing change, make the shot start-only."

### 4. Background people: named elements with beats, or "never a named element"?
- **Copy A** (G§4, line 37): "Plan beats for every visible person, animal or object that acts, including secondary and background subjects". G§5 line 40 adds: "Derive the named elements from the planned shots, secondary subjects and props included".
- **Copy B** (S-STEP 3, line 11): "A background person who only passes is never a named element with a sheet: the scene says them in words, different in every scene."
- **Server:** it follows A. VC:711 refuses with "Every visible subject must be a required shot element", and VC:729 requires beats for every acting subject, background subjects included. VC:593 warns when a normal or busy scene has no secondary or background subject. VS:1164-1177 (`sheet_due`) asks for a sheet for any element that has an approved source.
- **Resolution:** Merge into: "A background subject with beats is an element (no reference sheet unless it has a source picture); a passer-by without beats lives only in the scene's words (its ambient line)." As things stand, B tells the assistant to do something the plan check refuses.

### 5. A frame showing a face: "never a parent", yet person sheets are made from frames
- **Copy A** (G§5, line 41): "A frame that shows a recognisable face is a look reference only, never a parent: the image models refuse to edit it." Line 43 says the same: "A person from the footage or the web is never a parent for an edit nor copied". S-STEP 3 repeats it twice.
- **Copy B** (G§5, line 43): "Every person, object or place gets one generated reference sheet from its footage frames, else from the operator's picks". S-STEP 3, line 11 gives the command: "one sheet per element from its approved frames and picks (`image --kind sheet --parents F1,W2`". Copy B also differs from itself: the guide says "frames, else picks" while the steps say "frames and picks".
- **Server:** it follows B. VS:1164-1177 (`sheet_due`) tells the assistant to write `--kind sheet --parents <every approved frame, supplied and web picture>`, people included. No code was found that refuses a face frame as a parent.
- **Resolution:** SK decides. Either "a person's sheet is generated from words (posture, dress, build) with the frames shown only as look references", or "a sheet may take the frames as parents; no other picture may". In both cases, state whether a sheet uses frames and picks or frames first.

### 6. The client's own object: frame sent once (golden) or in every shot?
- **Copy A** (S-STEP 3, line 11): "a client's own object sends its footage frame here and never again".
- **Copy B** (G§5, line 40): "a shot that shows it sends one of those frames as a parent, never words alone". S-STEP 3 (end of line 11) also says: "When a shot shows a client material at medium or closer, bind its footage frame as the texture reference".
- **Server:** it is split. VS:2148-2151 refuses a golden picture of an exact client object when no footage frame is a parent. VS:2693 then skips the per-shot "send the frame" gate once a golden picture exists, which matches A. But `bind_advice` at VS:3165-3166 still advises binding the frame as the texture reference, whether or not a golden picture exists, which matches B.
- **Resolution:** Keep A for pictures. Reword B to: "before its golden picture exists, a picture of the client's object sends a footage frame; afterwards the golden picture carries it." Either remove the texture-bind advice when a golden picture exists, or state that it applies to the video bind only.

### 7. Which picture is Image 1: the golden picture, the scene parent, or the sheet?
- **Copy A** (S-STEP 3, line 11): "Every later picture of the element has the golden picture as Image 1".
- **Copy B** (S-STEP 3, line 11): "Up to sixteen pictures go in with a prompt (the model's limit), in this order: the picture edited or the scene parent, one identity sheet per person in frame, then every approved frame, golden picture or supplied reference". G§5 line 43 adds: "the sheet, not the frames or the picks, is what shots bind", and S-STEP 3 says "the sheet is what shots bind".
- **Server:** it follows A. VS:2224-2225 refuses a keyframe or isolated picture (other than an end) of an element that has a golden picture unless that golden picture is the first parent.
- **Resolution:** Merge into: "Image 1 is the golden picture of the element the picture is for (an end image: its start); then the person sheets; then the other references." Also change "the sheet is what shots bind" to "the golden picture (a person: the sheet)".

### 8. Is the style sheet a parent of every graphic, including later states?
- **Copy A** (G§2, line 24): "made once as a style sheet (`vw visuals image --element _STYLE --kind style`), approved, a parent of every graphic." S-STEP 2 line 8 says: "approve it and name it in every graphic's --parents".
- **Copy B** (G§2, line 24): "each later state is generated from the previous one as its parent (`vw visuals image --kind state --parents R`)".
- **Server:** VS:2153 refuses with "A state is generated from the previous state: give one parent." A later state therefore cannot also name the style.
- **Resolution:** Reword A to: "a parent of every graphic's first (or only) picture; later states inherit it through the chain."

### 9. Who makes the end image, and from what?
- **Copy A** (G§5, line 43): "Post a start's end prompt with it (`end_answer`): the server makes the end from the approved start and checks every picture first."
- **Copy B** (S-STEP 3, line 11): "The end image of a video shot: `image --element E --kind keyframe --parents <start keyframe> --prompt "<only what changes>"`, as soon as the start candidate exists; show the pair together and approve both." G§6 line 47 and S-STEP 4 agree with B.
- **Server:** it allows both. VS:2155-2157 lets an end use a candidate start as its parent, and VS:2243-2252 queues an end that the server makes from the approved start.
- **Resolution:** SK picks one default. B (the assistant makes the end from the start candidate, and the pair is approved together) appears in three places. Copy A should become "or post `end_prompt` with the start and the server makes it after approval", or it should be dropped.

### 10. The order of picture sources: Google before or after the operator's own picture?
- **Copy A** (G§5, lines 40-43): "Gather only the references the plan needs, in this order:" 1) a frame from a clip; 2) "A picture from the web: the round's searches, or `vw visuals search`; their own file with `supply`."; 3) a generated reference.
- **Copy B** (S-STEP 3, line 11): "References per element, in this order: a frame from a clip (…), the operator's file (`supply`), for what the footage lacks, Google Images on their yes (…), a generated image".
- **Server:** no order is enforced. `sheet_due` (VS:1172) treats frame, supplied and web sources alike.
- **Resolution:** Keep B (footage, the operator's own picture, Google on their yes, AI). Copy A folds the operator's file into "web" and leaves out "on their yes".

### 11. The operator's yes to a web size figure: per spec, once per run, or not at all?
- **Copy A** (S-STEP 2, line 8): "a standard or a manufacturer's sheet on the web, on the operator's yes, with its URL and figure".
- **Copy B** (S-STEP 2, line 8, later): "a standard or a maker figure from the web (one warning and yes covers every spec of the run)".
- **Copy C** (G§0, line 6): "What never needs a question: a paid step (announce, never ask), a fact that can be measured or sourced".
- **Server:** it enforces none of these. VC:156 is only a comment ("a web source on the operator's yes"), and VC:373 only matches the word "standard/maker" in `tried`.
- **Resolution:** Keep B ("one warning and one yes covers every web figure of the run"). Remove "on the operator's yes" from A, and add to C: "except the run's one yes for web figures".

### 12. Spec approval: per shot with their words, or one table for the run?
- **Copy A** (S-STEP 2, line 8): "Show the operator the spec as a table and record their words: `vw visuals spec --shot S --quote "…"` (or on the page)."
- **Copy B** (S-STEP 2, line 8, later): "they approve every spec of the run in one table (`vw visuals spec` with no --shot, or the page)". G§2 line 24 says "The operator approves the spec as a table (`vw visuals spec`)".
- **Server:** it supports both. `approve_spec` (VS:2457, per shot, "no words needed") and `approve_specs` (VS:2534, the whole run).
- **Resolution:** Keep B as the default and delete A's per-shot command, or recast it as "for a single late spec". The two copies differ on whether words are needed.

### 13. The cost cap: who can change it?
- **Copy A** (G§6, line 50): "The film has a cap, ₹5,000 unless the operator sets another".
- **Copy B** (same sentence): "the builder changes the cap on SK's word."
- **Server:** it follows B. `config.py:50` sets `VISUALS_CAP_INR = 5000.0`, and `cap_of` (VS:378-379) reads `session['cap_inr']`, which no command sets (no setter found). The refusal at VS:386-387 reads "the cap is a setting the builder changes on SK's word".
- **Resolution:** Reword to "The film has a cap of ₹5,000; only the builder changes it, on SK's word." The operator cannot set it. (The `config.py` comment still says "unless the operator raises it"; tidy it with the same change.)

### 14. When gaps are accepted: after the plan, or at the end?
- **Copy A** (G§8, line 61): "Accept gaps with `vw visuals accept --gaps all --quote "…"` (or the gaps the operator named) and record them when every shot has a selected take, a still or an asset".
- **Copy B** (S-STEP 2, line 8): "`vw visuals accept --gaps all --quote "…"` (or the gaps they named). Then read every gap's words in `vw visuals status` before any picture." G§2 line 27 agrees: "After the acceptances, read every gap's words".
- **Server:** it follows B. Pictures and the reference round work on accepted gaps (S-STEP 3, "for accepted gaps only").
- **Resolution:** Remove "Accept gaps … and" from G§8 so it reads "Record the gaps when every shot has …". Acceptance belongs to the plan step.

### 15. One change per edit, or two at most?
- **Copy A** (G§5, line 43): "One change, two at most, per edit."
- **Copy B** (S-STEP 3, line 11): ""Image 1 is the [element]. Repeat it exactly; change nothing about it. The only change is: …""
- **Server:** it follows B. VS:2225 says "name it first in --parents and change one thing", and an end edit takes one region (VS:1207).
- **Resolution:** Keep "one change per edit".

### 16. Showing a picture twice: never, or allowed with the operator's words?
- **Copy A** (G§4, line 37): "The film never shows one picture twice: a return is reimagined (`return_of`, `differs_by`)."
- **Copy B** (S-STEP 2, line 8): "A plain reuse only when the reimagined shot adds nothing: `vw visuals clip|still … --reuse "<reason>" --considered …` … it then waits for the operator's own words".
- **Server:** VC:897-900 checks `return_of` and `differs_by`. The `--reuse` path exists (S-STEP 2), so the server follows B.
- **Resolution:** Add B's exception to A: "…reimagined; a plain reuse only with the operator's words (STEP 2)."

### 17. When to pick a longer generator (Kling or Seedance)
- **Copy A** (G§1, line 16): "Kling (3–15 s) and Seedance (4–30 s) are chosen per shot with `vw visuals generator` only when one action cannot be cut."
- **Copy B** (S-STEP 4, line 14): "`generator --shot S --provider … --model …` only when the shot is longer than the default makes (the check warns)".
- **Server:** VC:706-708 warns when a shot is longer than the default's maximum and suggests "split it, or choose …". It does not ask whether the action can be cut.
- **Resolution:** Merge into: "only when a shot is longer than the default makes and its one action cannot be cut; otherwise split it." Copy B alone invites switching generator instead of splitting.

### 18. The input-picture limit and the image model
- **Copy A** (S-STEP 3, line 11): "Up to sixteen pictures go in with a prompt (the model's limit)". G§1 line 13 and S-STEP 3 name "GPT Image 2.5" as the image model.
- **Server:** VS:36 sets `MAX_INPUTS = 16` for GPT Image. When the run's image model is Gemini (VS:2169-2175), it allows at most 14, with per-kind caps.
- **Resolution:** Reword to "up to the image model's limit (16 for GPT Image, 14 for Gemini, by kind); the server names the excess". Drop the fixed model name, or say "the run's image model".

### 19. Does a graphic push in by default, or only "when the shot asks"?
- **Copy A** (G§1, line 14): "assembly plays the states as a build with a short dissolve between them and, when the shot asks for it, a slow push."
- **Copy B** (G§4, line 37): "A still moves 5 % (`motion`; a graphic only push_in; `none` needs `motion_reason`)". S-STEP 2 says "Every still and graphic state moves 5 %".
- **Server:** it follows B. The default motion is `push_in` (VC:475), and `none` needs a reason (VC:635).
- **Resolution:** Reword A to "…with a short dissolve between them and a slow push-in (motion none only with a reason)."

### 20. How the film opens: on the strongest picture, or wide?
- **Copy A** (S-STEP 1, line 5): "The first gap opens on the strongest picture of the film's subject, not a neutral establishing shot."
- **Copy B** (S-STEP 2, line 8): "a new place opens wide, a close-up comes after the subject is seen wider".
- **Server:** no check either way.
- **Resolution:** Merge into: "the first gap opens on the strongest picture of the subject (a wide of the subject at work, not an empty establishing view)." This keeps "wide first" without making it neutral. SK should confirm.

### 21. A graphic held longer than 4 s: a build of states, or a drawn animation too?
- **Copy A** (G§4, line 37): "a graphic over 4 s is a build." S-STEP 2 line 8: "a graphic over 4 s is a build of 2 to 4 states."
- **Server:** VC:648-650 warns with "over 4 s a graphic is a build of 2 to 4 states (an animation shot) or a drawn animation". The drawn route (S-STEP 4) is also a legal answer, and is required when the graphic has figures (item 2).
- **Resolution:** Reword to "a graphic over 4 s is a build of 2 to 4 states or a drawn animation."

### 22. Placing an AI still: approval alone, or `vw visuals still`?
- **Copy A** (G§1, line 13): "approved by the operator and held for the shot (`vw visuals still`)."
- **Copy B** (G§6, line 49): "approving the picture made for it (`image --shot S`) places it, in one step (… `vw visuals still --shot S --ref R --quote "…"` is for a footage frame or a picture approved before)". S-STEP 4 agrees.
- **Server:** it follows B (approval places the picture).
- **Resolution:** Reword A to "approved by the operator for its shot, which places it".

### 23. Who writes the light into the prompt
- **Copy A** (G§4, line 34): "state that light in the prompt (soft overcast light, muted greens)."
- **Copy B** (G§4, line 37): "the real-light line (composed once per run from the footage character and the measured light of the approved footage frames) goes under every keyframe and isolated prompt" and "you write the picture, the server writes the rules".
- **Server:** it does both. It appends the real-light line, and `light_warning` (VS:3172-3173) warns when a keyframe does not name the scene's light word for word.
- **Resolution:** Merge into: "name the scene's light (its `light` field) word for word in the prompt; the server adds the measured real-light line under it."

### 24. Questions to the operator: one at a time, or a list?
- **Copy A** (G§0, line 6): "stop, ask one question with the concrete choices and the paid cost of each". The record goes through `vw visuals ask`.
- **Copy B** (G§0, line 6): "Missing facts are asked once, as one list, before the first picture." S-STEP 3 adds "questions the drafts raise are asked after the round as one list". G§4 line 35 says "a consequential unknown, recorded as a specific question in open_questions".
- **Server:** `vw visuals ask` holds each question on its item, and derived writes are refused until it is answered. Whether `open_questions` blocks anything was not checked.
- **Resolution:** Merge into: "missing facts: one list, once, before the first picture; any later fork: one question through `vw visuals ask`"; and state that `open_questions` items are also raised with `ask`. (SK's standing rule is one question per message, so SK decides whether the "list" may stand.)

### 25. Shot length: two to eight seconds, against generator minimums
- **Copy A** (G§4, line 37): "Shots run two to eight seconds as a rule."
- **Copy B** (G§1, line 16): "Gemini Omni is the default generator and makes 3 to 10 seconds". G§4 line 37 adds "Consecutive AI video in a gap under 12 s (ai_run) … shots 3–5 s", and S-STEP 4 says "A shot under 4 s with no visible action is a moving still".
- **Server:** VC:888-889 warns on runs over 12 s ("three to five seconds each"), and VC:641 warns on short AI video with no action.
- **Resolution:** Reword A to "shots run 2–8 s as a rule (AI video at least 3 s, 3–5 s inside an AI run)". The difference is minor.

---

## SAME RULE TWICE (merge later, no decision needed)

| Topic | Place A | Place B |
|---|---|---|
| Paid steps are announced, never asked | G§0 line 6 | G§1 13, G§5 43, G§6 48/50; S-STEP 3, S-STEP 4 |
| A graphic sequence: 2–4 states, each from the previous | G§1 line 14 | G§2 line 24; S-STEP 3 (state command) |
| End image only when `end_state_exact` | G§1 line 16 | G§2 21; G§6 47; S-STEP 1; S-STEP 4 |
| Images a treatment entry needs (one start per segment, end only if exact) | G§2 line 21 | S-STEP 1 line 5 |
| Treatment recorded before any plan | G§2 line 21 | S-STEP 1 ("Nothing else before this"); S-STEP 2 (propose refused) |
| Revision words are not a yes; the gap is re-proposed | G§2 line 27 | S-STEP 2 line 8 |
| `depicts` per graphic in the treatment | G§2 line 24 | S-STEP 1; S-STEP 2 |
| `activity_level` (per scene / per gap) | G§4 line 37 | S-STEP 1; S-STEP 2 |
| `claims` / `claims_left_out`; `words` per state | G§2 line 24 | S-STEP 2 line 8 |
| Labels short phrases with units, 4 % / titles 6 % | G§2 line 24 | S-STEP 2; S-STEP 4 (SVG text 4 %) |
| Drawing spec: unknown size never invented, "illustrative, not to scale" | G§2 line 24; G§4 line 37 | S-STEP 2 (twice); S-STEP 4 |
| The four sources for a size and `tried` | G§4 line 37 | S-STEP 2 (twice); S-STEP 3 (element size) |
| Still limits: 4 s moving, 3 s frozen, state 5 s, push_in for graphics | G§4 line 37 | S-STEP 2; S-STEP 4 (text stills) |
| Cuts in pauses; a picture starts on its words | G§4 line 37 | S-STEP 2 |
| Return reimagined (`return_of`, `differs_by`) | G§4 line 37 | S-STEP 2 |
| Fill the frame; crop past 1.35× | G§4 line 34 | S-STEP 2 |
| Transitions: 8-frame dissolve at graphics, cut elsewhere | G§4 line 34 | S-STEP 2 |
| `changes` list and `min_s` per beat | G§4 37; G§6 47 | S-STEP 2 |
| `visual_facts`, `fact_ids`, unknown fact never invented | G§4 line 34 | S-STEP 2 |
| `message` / `adds` | G§4 line 34 | S-STEP 2 |
| `studio_background` only when the treatment allows | G§4 line 34 | S-STEP 2 |
| Name the shot a picture is for (`--shot`) | G§5 line 40 | G§6 49; S-STEP 3 |
| Edits name Image 1…N with a job line | G§5 line 43 | S-STEP 3 (twice) |
| Fix only on request (`vw visuals fix`, paid) | G§5 line 43 | S-STEP 3 |
| Show each candidate (`fetch`) and approve by sha with words | G§5 line 44 | S-STEP 3 |
| After a drift or rejection: end from the approved start; state from the last approved state | G§6 line 47 | S-STEP 3 |
| Write the next shot's answers while a wave generates | G§6 line 47 | S-STEP 3 |
| Bind, then packet, then start; start never before packet | G§6 line 47 | S-STEP 3; S-STEP 4 |
| Prepare-take marks shown to the operator, who approves the pair | G§6 line 47 | S-STEP 4 |
| Still placed on approval; `unplace` | G§6 line 49 | S-STEP 4 |
| `sequence --shot S --quote`, states shown together | G§6 line 49 | S-STEP 4 |
| Gemini reads each take first; operator watches; select/review | G§8 line 60 | S-STEP 4 |
| A supplied file only on the operator's instruction | G§1 line 17 | S-STEP 4 |
| Sheet for each element is what shots use; sheet regenerated | G§5 line 43 | S-STEP 3 (twice: "Then one sheet per element" and "Then one sheet per person, object or place") |
| A frame with a face is never a parent | G§5 line 41; G§5 line 43 | S-STEP 3 (twice); see item 5 for the conflict |
| Record gaps when all shots are done | G§8 line 61 | S-STEP 5 |
| Library: read always/ once, then a step's folder | G§6 line 52 | S-STEP 0; S-STEP 3 |
| Cap refusal: stop and tell the operator | G§6 line 50 | S-STEP 3 ("the server refuses a call that would pass the cap") |
