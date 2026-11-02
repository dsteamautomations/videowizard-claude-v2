# design/137: the film's video category, chosen at the start (proposal, waits for SK)

2 Nov 2026. SK: "Yes, I want this follow-up." design/136 made each picture step read a guidebook's general part plus the film's own category part, but nothing records a film's category yet, so every film reads as documentary-explainer.

## Requirement
The operator names the film's category when the film is started, the same way the picture AI and the drawn route are named today:
`vw start … --category documentary-explainer | advertisement-product | training-education | social-ugc | narrative-story`.
The server keeps it on the film (a column on the run, like `drawn_route`), and the visuals step's guidebooks are read for that category.

## Unstated but expected
- **Default:** documentary-explainer when `--category` is not given, so today's way of starting a film keeps working and gives today's result.
- **One flow, two front ends:** the server's create-run step takes it, so the run page and the chat tool share one place. If the web page ever starts films, it sends the same field.
- **Shown back:** `vw status` and the run line name the category, so the operator can see it.
- **Scope:** only the guidebooks read at the visuals step use it today. The brief, script and options stages do not change.

## Edge cases and how each is handled

| Case | Handling |
| --- | --- |
| A name that is not one of the five | `vw start` refuses it and lists the five, before anything is created |
| A film started before this change (no category recorded) | read as documentary-explainer, never an error |
| The wrong category chosen | **Proposed:** it can be changed until the visuals stage is prepared (`vw category <name>`), then it is fixed, because the guidebooks were written to the operator's folder for that category. Alternative: fixed at the start, like the drawn route; a wrong one means a new film. **SK's call.** |
| A film whose category has no "For …" part in a guidebook | it reads the general part, as today |
| A guidebook version older than design/136 (a pinned run) | it has no category parts, so it is read whole, as today |

## Failure modes
A missing or unknown value never stops a step: the server reads documentary-explainer.

## Tests first
1. `vw start --category training-education` sends the category; a bad name is refused with the five listed; no `--category` sends none.
2. The server keeps it on the new run; with no value, the run's category is documentary-explainer.
3. The visuals step's pack is read for the run's category (an advertisement film gets the advertisement parts and not the documentary ones).
4. If changing is allowed: it is refused once the visuals stage is prepared, with one line saying why.

## Lane and deploy
Regular. A database column (migration `011_video_category.sql`), the server, the plugin. **Built, tested and committed; not deployed until SK approves** (SK, 2 Nov 2026: deployments on hold).

## Not covered
- What each category changes beyond the visuals guidebooks (the brief, the script, the cut): a later decision, per category.
