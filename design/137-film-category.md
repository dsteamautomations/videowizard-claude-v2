# design/137: the film's video category, read from the script and confirmed by the operator (proposal, waits for SK)

2 Nov 2026. design/136 made each picture step read a guidebook's general part plus the film's own category part. Nothing records a film's category yet.

SK, 2 Nov 2026: "Right after the script is got, there can be a prediction based on the script as to whether this is a documentary film or what category it is … 'From your script I have identified your category to be this. Do you want to change it to any of the following?' … this can happen in Claude itself. There won't be a need for a separate UI. Assuming it by default is a bit dangerous because many people might forget to give that."

## Requirement
1. **At intake, once the script is in**, the operator's assistant reads it and names the category it fits, with one line why: "From your script I have identified your film as a training film (it teaches a step-by-step method to masons). Do you want to change it to one of these: documentary or explainer, advertisement or product, social clip, story?"
2. **The operator answers in chat** (the question tool, the five as buttons). Their answer and their words are recorded on the server: `vw category <name> --quote "<their words>"`.
3. **No default.** The brief stage does not start until the film has a category. A film without one is refused by name, with the command to record it.
4. The visuals step reads the guidebooks for the recorded category (design/136).

The five: documentary-explainer, advertisement-product, training-education, social-ugc, narrative-story.

## Unstated but expected
- **No extra model call or cost:** the assistant already reads the whole script at intake; naming the category is part of that step.
- **One flow, two front ends:** the server's step records it, so a page could do the same later.
- **Shown back:** `vw status` and the run line name the category.
- **Scope:** only the visuals guidebooks use it today. What each category changes in the brief, script or cut is a later decision.

## Edge cases and how each is handled

| Case | Handling |
| --- | --- |
| A name that is not one of the five | refused, listing the five |
| The operator gives no words | refused: the record carries the operator's own words, like every approval |
| The script mixes two categories (a training film that also sells) | the assistant names the one the film's purpose fits and says the other in its one line; the operator chooses |
| The operator wants to change it later | allowed until the visuals stage is prepared, again with their words; then fixed, because the guidebooks were written to the operator's folder for that category; the refusal says so |
| A film started before this change (no category) | asked at its next stage step: the brief (or the visuals preparation for a film already past the brief) is refused until it is recorded; never read silently as documentary |
| A guidebook version older than design/136 (a pinned run) | it has no category parts, so it is read whole, as today |

## Failure modes
A film without a category stops at the next stage with one line naming `vw category`. Nothing is assumed.

## Tests first
1. `vw category training-education --quote "yes"` records it with the words; a bad name, or no words, is refused.
2. The brief stage is refused for a film with no category, naming the command; it starts once one is recorded.
3. The visuals preparation is refused for a film with no category; the guidebooks are read for the recorded one (an advertisement film gets the advertisement parts and not the documentary ones).
4. A change after the visuals stage is prepared is refused, saying why.
5. The intake instructions tell the assistant to name the category with its reason and ask, with the five as choices (the wording test keeps it shorter than or equal to the words it replaces).

## Lane and deploy
Regular. A database column (migration `011_video_category.sql`), the server, the plugin and the intake instructions. **Built, tested and committed; not deployed until SK approves** (SK, 2 Nov 2026: deployments on hold).

## Older way (design/35)
"Every film reads as documentary" (design/136's default) is retired by this change: a film with no category is asked, never assumed.

## Not covered
- What each category changes beyond the visuals guidebooks.
