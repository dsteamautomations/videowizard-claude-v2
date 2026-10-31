# 126 — wording trace, instruction version 3

Every agreed wording change of design/126 (IN1, BR1-BR3, SC1-SC5, AN1, OP2, OP3, U5), old text → new text, in the order applied. Made by `scripts/d126_wording_v3.py`; version 2 untouched. Line breaks inside the stored prompts are shown as they are.

## IN1 — intake, prompt (15 → 0 words)

**Old:**

>  That is the situation this tool has
> always been in and it survives it easily.

**New:**

> (removed)

## IN1 — intake, prompt (17 → 0 words)

**Old:**

> Preserve spoken words exactly so the chosen script has an honest, inspectable relationship to its original source.

**New:**

> (removed)

## IN1 — intake, prompt (7 → 4 words)

**Old:**

> Return only JSON, no prose around it:

**New:**

> Write this to out/intake.json:

## BR1 — brief, prompt (7 → 7 words)

**Old:**

> Where not supplied, label it a recommendation.

**New:**

> Where not supplied, its reason says so.

## BR1 — brief, prompt (10 → 0 words)

**Old:**

>  Do not rewrite
>   intake to force this stage to pass.

**New:**

> (removed)

## BR2 — brief, prompt (10 → 0 words)

**Old:**

> Do not turn every missing fact into a required answer. 

**New:**

> (removed)

Kept copy: prompt: "Only consequential unresolved questions may be required.".

## BR2 — brief, prompt (6 → 0 words)

**Old:**

> Do not re-ask
> questions already answered. 

**New:**

> (removed)

Kept copy: prompt: "ask again only if their meaning or underlying source actually changed, explaining why.".

## BR2 — brief, prompt (18 → 0 words)

**Old:**

> Each question has a stable id, question, why it matters, an optional recommendation
> and a boolean required flag. 

**New:**

> (removed)

Kept copy: brief step 1 and the answer shape (`questions` with id, question, why, recommendation, required).

## BR2 — brief, prompt (8 → 0 words)

**Old:**

> Never prefill an answer because it seems
> obvious. 

**New:**

> (removed)

Kept copy: prompt: "A recommended answer is never a human answer."; step 1: "Never fill `answers` yourself".

## BR3 — brief, prompt (54 → 21 words)

**Old:**

> Return a proposal containing purpose, audience, message, tone, ending, constraints,
> reasons keyed by the five field names, questions and production. Do not include
> answers or approval. The file is the proposal; present its meaning and open
> questions in readable chat, not JSON the operator has to copy. Ask for one grouped
> acceptance or corrections.

**New:**

> The file is the proposal; present its meaning and open questions in readable chat, not JSON the operator has to copy.

## SC1 — script, prompt (24 → 15 words)

**Old:**

> exact title and client, any
> previously accepted prepared script, exact supplied wording and notes, prior
> proposals and the operator's decisions. Read all current inputs.

**New:**

> exact title and client, and the directory facts the prepare prints. Read all current inputs.

## SC2 — script, prompt (52 → 22 words)

**Old:**

> Defer Treatment, shots, media study, visual achievability, AI makeability, material
> coverage and filmability. Missing footage is not a defect in narration. Do not gate
> this stage on visual plans, casting, location, voice selection or provider settings.
> No voice generation, paid call or automatic progression into Voice is authorized by
> accepting a script.

**New:**

> Pictures and footage come later: missing footage is not a defect in narration. Accepting a script starts no voice or paid call.

## SC3 — script, steps[2] (11 → 13 words)

**Old:**

> Search only after the operator says yes; show what you found;

**New:**

> Search only after the operator says yes; show what the source page says;

## SC3 — script, steps[2] (9 → 6 words)

**Old:**

> I want to check X in the script, because

**New:**

> I want to check X, because

## SC4 — script, prompt (24 → 0 words)

**Old:**

> After the operator decides, each change carries decision: accepted, rejected, or
> reworded with operator_wording; rejected changes stay in the file and are not
> applied. 

**New:**

> (removed)

## SC4 — script, prompt (9 → 0 words)

**Old:**

> Unaccepted edits must not leak into the final text. 

**New:**

> (removed)

## SC5 — script, prompt (92 → 37 words)

**Old:**

> Return the complete proposed spoken_text, optional notes, a concise assessment and
> changes containing before, after and reason. Use exact before excerpts from the
> current working wording and show the corresponding proposed wording; insertions or
> deletions can use an empty before or after. Keep unchanged text exact. Changes can
> cross physical lines; there is no fixed-row constraint. Make the full proposal
> consistent with the listed changes. Every edit must be a listed change with an exact before that occurs once; anchor an insertion on a short before excerpt rather than an empty one.

**New:**

> Use exact before excerpts from the current working wording and show the proposed wording; a deletion has an empty after; anchor an insertion on a short before excerpt. Keep unchanged text exact. Changes can cross physical lines.

## AN1 — analysis, steps[0] (90 → 73 words)

**Old:**

> Before starting, ask in one message: should the model listen to the clips' audio to understand them (default yes), and is there any clip to leave out (default none)? The camera-sound answer comes from the media stage; say it back ("camera audio: allowed, as you said at media"). Then `vw analysis start [--understand-audio no] [--exclude <clip name> …]`: one paid Gemini 3.8 Flash request per clip (agentic for a clip over 15 seconds, plain for a shorter one); tell the operator, do not ask. The server computes eligibility and crops.

**New:**

> Run `vw analysis start [--understand-audio no] [--exclude <clip name> …]` without asking: the clip list was confirmed at media, and the model listens to the clips' sound unless the operator said there that it must not be used even for analysis. One paid Gemini 3.8 Flash request per clip (agentic for a clip over 15 seconds, plain for a shorter one); tell the operator, do not ask. The server computes eligibility and crops.

## OP2 — options, steps[1] (15 → 14 words)

**Old:**

> a scene covers one chapter: a paragraph covering two is split where the second begins

**New:**

> list every chapter the paragraph covers; split a paragraph only when the operator asks

## OP3 — options, steps[3] (8 → 9 words)

**Old:**

> E2, N17, N14; each says what to do

**New:**

> E2, N17 (claims), N14; each says what to do

## U5 — visuals, parts.picture-search (3 → 3 words)

**Old:**

> the two-to-six-word keywords

**New:**

> the two-to-twelve-word keywords

## U5 — visuals, parts.picture-search (11 → 11 words)

**Old:**

> <two to six words: the thing and its place or trade>

**New:**

> <two to twelve words: the thing and its place or trade>

## U5 — visuals, parts.picture-search (6 → 6 words)

**Old:**

> <stock site, outside the six words;

**New:**

> <stock site, outside the twelve words;

## Words read by the assistant, per field

| Field | Before | After |
|---|---|---|
| intake prompt | 716 | 681 |
| brief prompt | 1060 | 975 |
| script prompt | 642 | 515 |
| script steps | 300 | 299 |
| analysis steps | 328 | 311 |
| options steps | 521 | 521 |
| visuals parts.picture-search | 579 | 579 |


## Numbers and conditions (checked after the run)

- Numbers: no digit or figure disappeared in any pair (old vs new compared token by token; AN1 keeps "3.8" and "15 seconds").
- Conditions removed, each kept elsewhere or approved as retired: IN1 none (the never-rewrite and high-bar rules stay); BR1 "Do not rewrite intake…" (the gate leftover, retired); BR2 four sentences, each with its kept copy listed above; BR3 "Do not include answers or approval" (step 1: "Never fill `answers` yourself"); SC2 "Do not gate…" (now "Pictures and footage come later"); SC4 "rejected changes … are not applied", "Unaccepted edits must not leak" (step 3 and the tool's rebuild); SC5 "insertions or deletions can use an empty before" (the tool still accepts an unambiguous empty-before insertion); AN1 the question and the camera-sound say-back (approved text; the camera-sound answer is still taken from media by the server).
- Word counts differ from design/126's estimates for the brief (975, design said 973) and analysis step 0 (90 → 73 words; design/126 estimated 64, a miscount of 9 words): every approved sentence was removed or replaced as written.
- SC5 follow-up (lead, after the independent check): the script stage's `output_shape` still said `"before": "exact excerpt of the current wording (empty for an insertion)"`, the contradiction SC5 removes from the prompt; now `"(an insertion anchors on a short excerpt)"`. The tool still accepts an empty-before insertion when its words occur once.