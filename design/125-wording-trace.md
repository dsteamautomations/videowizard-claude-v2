# 125 — wording trace, instruction version 3

Every agreed wording change, old text → new text, in the order applied. Made by `scripts/d125_wording_v3.py`.

## I1, I2 — intake, steps[2]

**Old:**

>  The client is already on the run (chosen at `vw start` from the directory). Before `vw start`, ask the operator which image model this film uses, GPT Image (openai) or Gemini Nano Banana (gemini): `vw start --client … --images openai|gemini`; the choice is recorded on the run and never changes (design/120); on a gemini run a prompt takes up to 14 pictures by kind (6 of things, 5 of people, 3 of style), a region edit is said in words (the server still copies the start back outside the region), and a component is made on chroma green that the server keys out.

**New:**

>  The client and the film's picture AI are already on the run (both chosen at `vw start`).

## I1 — visuals, parts.later

**Old:**

> (16 for GPT Image, 14 for Gemini, by kind; the server names the excess)

**New:**

> (16 for GPT Image; 14 for Gemini, by kind: 6 of things, 5 of people, 3 of style; the server names the excess)

## I1 — visuals, parts.later

**Old:**

> name the landmark in the prompt); the server masks it and copies the start back outside it.

**New:**

> name the landmark in the prompt); the server masks it and copies the start back outside it. On a Gemini film a region edit is also said in words (the server still copies the start back outside the region), and a component is made on chroma green, which the server keys out.

## I3 — intake, prompt

**Old:**

>   "titles": ["...", "...", "..."]
> }

**New:**

>   "titles": ["...", "...", "..."],
>   "notes": "a short explanation of what was removed"
> }

## B2 — brief, prompt

**Old:**

> # VW-BRIEF v2.0 — purposeful, low-friction Brief
> 
> 

**New:**

> (removed)

## B2 — brief, prompt

**Old:**

>  Do not silently accept model defaults. A malformed
> proposal gets at most one correction with this same prompt, then explain the issue
> and offer supplied input or a pause.

**New:**

> (removed)

## B3 — brief, prompt

**Old:**

> Brand and safety rules,
> whether the speaker may be seen on camera, the languages spoken in the footage and the
> narration language are the operator's words, asked on every film. Ask in the same
> message where the film plays and its frame shape (production.format: frame 16:9, 9:16,
> 1:1 or 4:5; destinations such as YouTube or Instagram; whether it is watched muted);
> 16:9 and no destinations unless they say.

**New:**

> Brand and safety rules,
> whether the speaker may be seen on camera, the languages spoken in the footage, the
> narration language, and where the film plays and its frame shape (production.format:
> frame 16:9, 9:16, 1:1 or 4:5) are the operator's words, asked on every film in one
> message; the list is in the steps.

## B1, B3 — brief, steps[1]

**Old:**

> Ask the operator, in one message, on every film: the brand and safety rules (for example: no competitor logos, PPE required or not, nothing staged; an empty list if none), the languages spoken in the footage, and the narration language.

**New:**

> Ask the operator, in one message, on every film: the brand and safety rules (for example: no competitor logos, PPE required or not, nothing staged; an empty list if none), the languages spoken in the footage (an empty list if nobody speaks or there is no footage), the narration language, whether the speaker may be seen on camera, and where the film plays and its frame shape (16:9, 9:16, 1:1 or 4:5; destinations such as YouTube or Instagram; watched muted or not; 16:9 and no destinations unless they say).

## S1 — script, prompt

**Old:**

> # VW-SCRIPT-PREPARATION v2.1 — one meaningful wording pass
> 
> 

**New:**

> (removed)

## S1 — script, prompt

**Old:**

>  Do not reproduce
> normalize, check, remediate, filmability, lock or per-line tagging gates.

**New:**

> (removed)

## S1 — script, prompt

**Old:**

> 
> Do not require VO/DIALOGUE/ACTION tagging of every physical line from the operator.

**New:**

> (removed)

## S1 — script, prompt

**Old:**

> On malformed output make at most one correction with this same prompt; then
> explain and offer user-supplied text or pause. 

**New:**

> (removed)

## S2 — script, prompt

**Old:**

> The record step rebuilds the text from the
> cleaned script plus the accepted changes and refuses anything else, so every edit
> must be a listed change with an exact before that occurs once; anchor an insertion
> on a short before excerpt rather than an empty one.

**New:**

> Every edit must be a listed change with an exact before that occurs once; anchor an insertion on a short before excerpt rather than an empty one.

## S2 — script, prompt

**Old:**

> Verify the agreed changes are present and all unaccepted changes are absent. This
> is verification of the agreed edit, not a second critique or another round of
> mandatory recommendations.

**New:**

> The tool checks that only the accepted changes are applied; do not critique again.

## S3 — script, steps[1]

**Old:**

> Every edit must be a listed change with an exact before that occurs once.

**New:**

> Every edit must be a listed change with an exact before that occurs once. When the assessment names figures or claims the message rests on, list them in `claims` (each {text, checked: true or false, source when checked}); the visuals stage reads them, so a graphic shows the figure the narration speaks.

## S3 — visuals, parts.preparation

**Old:**

> Read prompt.md, gaps.json and intended-visuals.json first,

**New:**

> Read prompt.md, gaps.json and intended-visuals.json first, and claims.json (the figures the narration rests on, and whether the operator had them checked: a picture or graphic shows the same figure, and a checked one is not searched again),

## V3 — voice, prompt

**Old:**

> # VW-VOICE v4 — choose a narrator, direct the delivery, record once
> 
> 

**New:**

> (removed)

## V2 — voice, prompt

**Old:**

> FIND. For a repeat client the last voice comes first; then the favourites (`vw stage voice prepare`
> lists them with where each was used; `vw voice history --voice ID` says more); then the catalogue.
> On "compare", ask one question per message and wait for each answer, your recommendation first
> with its reason from the brief: gender; age group; accent (language and accent are different
> things; never from the client's name); register (warm, authoritative, conversational, measured).
> Repeat the four values and ask for a yes. Only then one `vw voice catalog` call, library scope,
> with exactly those filters; the answer is one line per voice. The voices page is the default from here
> (the catalog prints its link with the same filters; the operator signs in): there they play the
> provider's sample of every voice, shortlist, audition, pick, narrate and make a narration final;
> `vw next` and `vw stage voice prepare` tell you what they did there. Or continue in chat:
> `vw voice preview` gives a sample link; a library voice is saved to the account automatically
> when it is auditioned or narrated (no custom slot is used); `vw voice add-library` is only
> for a voice the catalog never listed.
> Never substitute a curated three for the matching results, and never say an incomplete search
> exhausted the catalogue. No name-only matching: a voice is its exact id.
> 
> COMPARE. Propose one to six account voices, one supported model, settings and
> one exact contiguous excerpt of the accepted script, about 45 to 70 words and at
> most 3,000 characters; every candidate reads the same excerpt. Present voices,
> reasons, model, settings and the excerpt together. Auditions are paid: say what
> will be generated and proceed. A description justifies a recommendation; only the
> operator's listening establishes a preference. Never claim to have heard anything.
> 
> 

**New:**

> FIND. For a repeat client the last voice comes first; then the favourites (`vw stage voice prepare`
> lists them with where each was used); then the catalogue. The voices page is the default (the operator
> signs in: they play the provider's sample of every voice, shortlist, audition, pick, narrate and make a narration final; `vw next` and
> `vw stage voice prepare` tell you what they did there); the chat path is in the steps.
> Never substitute a curated three for the matching results, and never say an incomplete search
> exhausted the catalogue. No name-only matching: a voice is its exact id.
> 
> COMPARE. Propose one to six account voices, one supported model and settings; every candidate
> reads the chosen test passage (one exact contiguous excerpt of the accepted script, 50 to 100 words and at
> most 3,000 characters). Present voices, reasons, model, settings and the passage together. Auditions
> are paid: say what will be generated and proceed. A description justifies a recommendation; only the
> operator's listening establishes a preference. Never claim to have heard anything.
> 
> 

## V3 — voice, direction_prompt

**Old:**

> # VW-DIRECTION v1 — how the narration should be delivered
> 
> 

**New:**

> (removed)

## V1 — voice, direction_prompt

**Old:**

> the register tag at the top governs them. A list of forty tags on forty sentences is wrong.

**New:**

> the register tag at the top governs them. A list of forty tags on forty sentences is wrong.
> The register is placed at the top for you; do not repeat it on the first sentence.

## V3 — voice, steps[1]

**Old:**

> the direction and the test passage (design/54 B): run

**New:**

> the direction and the test passage: run

## V2 — voice, steps[3]

**Old:**

> Chat fallback: one question per message, recommendation first with its reason from the brief, and wait for each answer: gender; age group; accent; register. Repeat the four and ask for a yes. Then one `vw voice catalog --gender … --age … --accent … [--search <name>] [--page N]` call

**New:**

> Chat fallback: one question per message, recommendation first with its reason from the brief, and wait for each answer: gender; age group; accent (language and accent are different things; never from the client's name); register (warm, authoritative, conversational, measured). Repeat the four and ask for a yes. Only then one `vw voice catalog --gender … --age … --accent … [--search <name>] [--page N]` call, library scope, with exactly those filters (one line per voice; it prints the voices page link with the same filters; `vw voice history --voice ID` says more about a favourite)

## V2 — voice, steps[3]

**Old:**

> A library voice is saved to the account automatically when it is auditioned or narrated (no custom slot is used).

**New:**

> A library voice is saved to the account automatically when it is auditioned or narrated (no custom slot is used); `vw voice add-library` is only for a voice the catalog never listed.

## M2 — media, prompt

**Old:**

>  Facts of the tool: clips go in runs/<code>/in/, at most 200 MB each; a variable-frame-rate clip is converted to constant frame rate before upload and reported; prepare reports the clip count and total MB; the upload runs three clips at a time with retries and reports each finished clip; re-run record to resume an interrupted upload, finished clips are skipped.

**New:**

>  The tool's facts (size limit, conversion, upload, resume) are in the steps.

## M2 — media, steps[1]

**Old:**

>  (design/107).

**New:**

> .

## M2 — media, steps[2]

**Old:**

> Re-run record to resume an interrupted upload.

**New:**

> Re-run record to resume an interrupted upload; finished clips are skipped.

## M2 — media, steps[2]

**Old:**

> uploads with receipts, prints one line per finished clip

**New:**

> uploads with receipts, three clips at a time with retries, prints one line per finished clip

## A2, A3 — analysis, steps[0]

**Old:**

> (agentic); tell the operator, do not ask. The log follows the blueprint Stage 1 contract (clip-log-v1); the server computes eligibility and crops.

**New:**

> (agentic for a clip over 15 seconds, plain for a shorter one); tell the operator, do not ask. The server computes eligibility and crops.

## A4 — analysis, steps[2]

**Old:**

> A failed clip: tell the operator the reason from status.

**New:**

> A clip that fails for a passing reason (an error in the provider's stream, an answer cut off or empty, a busy service) is retried by the server up to three times on its own; only then does it reach you. A failed clip: tell the operator the reason from status.

## A2 — analysis, settings

**Old:** `processing_mode: AGENTIC`, `agentic_over_seconds: 300`

**New:** `processing_mode: auto`, `agentic_over_seconds: 15`

## S3 — script, output_shape

**New:** `claims: [{text, checked, source}]`

