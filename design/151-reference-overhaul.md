# design/151 — References made the kept way: frames unchanged, people as character sheets, things by the kept Nano Banana method

Status: requirements note, 4 Nov 2026, for SK's approval before any code. Sources: SK's words of 4 Nov (three parts, quoted below), the kept prompt `nano-banana-reference-prompt-kept-v6-2026-11-04.md` (version 6 and its three trials), design/79 (the round), design/119 rule 2 (sheets), design/111 F11 (golden pictures), design/124 decision 5 (no picture of a real person to the picture AI), design/134 (drawn shots), `visuals_stage.py`, `visual_workers.py`, `library.py`, `visuals.html`, the version 3 visuals texts, `vw.md`. Not deployed until SK says so, and a contradiction check (section 6) comes before the deploy.

## 1. What SK asked (restated)

1. **A thing the footage shows keeps today's way.** Its frame is grabbed, shown on the page, the operator agrees, and only then is anything generated.
2. **A person who needs a character sheet gets it from Gemini**, from a prompt that carries everything known about them: who they are in the film and why they look as they do (trade, place, age, build, garments, how they are worn, hair), several poses, a close-up of the face. People look different from one another, side workers included. Every worker the script speaks of is counted; today some were missed.
3. **An AI reference of a thing is made strictly by the kept method** (the version 6 preamble: real photographs decide, one way of doing it, a set of two to four separate pictures when one cannot carry the subject, the four notes at the end). It runs **silently**: the operator is not asked per element; the results of every element are shown **in one shot**; the operator says yes, no, or asks for a correction; a correction starts another round.
4. Nothing here may contradict another rule; the check is a gate before the deploy (section 6).
5. Where the downstream use of these pictures changes, SK decides (section 5, the questions in section 8).

## 2. How it works today (the parts that change)

- **The round (design/79).** For every element at once: pass 1, its footage frames with Approve the frame / Search (Google Images through Apify, ten pictures) / Ignore; pass 2, ticks on the searched pictures with a note each; then the assistant writes one **sheet** per element (`image --kind sheet`, the server adds "the views … each labelled; the thing alone on plain ground"); then, for a thing, a **golden picture** (`--kind isolated --golden`, made from the sheet and one frame): the one close picture every shot binds. A person's sheet is written from words only (design/124 decision 5) and is itself the person's golden picture.
- **The picture AI call** (`_gemini_image`): one prompt, the parents as Image 1..N, no search tool, the **first** image part of the answer kept, the rest dropped.
- **Downstream readers of the sheet and the golden picture:** keyframe parents (a start inherits the element's sheets, Gemini's cap of five character pictures and the fourteen-picture ceiling), `bind` and `bind_advice`, the drawn route's `brief_pictures` (sheets, components, golden, style), components (made from the golden in the approved style), `image_check` (a sheet is checked for its labelled views and "nothing but the thing"), the page's element state ("sheet approved" is the step's done mark), the operator's notes under picks (applied to the sheet), the stale-sheet mark when a source changes, the "sources changed" re-make.

## 3. What changes

### 3.1 Frames (SK part 1): unchanged
Pass 1 of the round stays as it is for the frames: grab, show, Approve the frame. The **Search** verdict and pass 2 go (section 3.3).

### 3.2 People (SK part 2): the character sheet
- The server writes the person's prompt itself from the plan: the person's `description` (the fixed layer), `requirements`, the film's place and category (the film record), the scene outfits, the role the beats give them, and a **why** line per trait it can justify from the script or the footage ("a mason of thirty, Tamil Nadu village site: a cotton lungi folded to the knee because he kneels on the plinth"). The assistant's answer form stays for the words only the plan does not hold.
- The sheet is a **set of separate pictures**, never a collage: a full-length front, a full-length three-quarter or working pose, a close-up of the face; a fourth when the plan's `required_views` asks for it. Each is its own reference row of kind `sheet`, grouped by a `set` id; the person alone on plain ground, no labels in the picture.
- **Distinct people.** Before the round, the server compares every pair of people on build, age band, hair, skin and garment colour family (the plan already demands different colour families unless a uniform); two people who match on all of them are refused with the pair named: the plan corrects the description. The prompt of each person also names the others in one line ("not like P2: taller, grey hair") so the model keeps them apart.
- **Every worker from the script.** `vw visuals check` lists every person the script's sentences and the recorded treatment act with (the group words and named people of `visual_contract`) who has no element; a side worker with a beat is an element with a sheet (design/124-b already names up to three background workers). The question of whether this is a warning or a refusal is Q4.
- design/124 decision 5 holds: no footage frame or web picture of a person goes to the picture AI; a speaker (real person to camera) never gets an AI picture.

### 3.3 Things (SK part 3): the kept method, silent, shown in one shot
Things are every non-person, non-graphic element: object, place, animal, material, process, technique.
- **The assistant writes the subject block only** (what the picture must represent, from the plan's requirements, facts, sizes and the shot's needs) and the cosmetics the plan fixes (place, light, camera height). The **server** adds the kept preamble verbatim, the set line, the four-notes request, and the film's category and place; it refuses a subject block that describes *how* the work is done (the preamble forbids it: "I am not going to describe how the work is done"). The library's `reference` step points at the kept prompt instead of the continuity-kit playbook.
- **One paid call per thing, with Google Search on**: the request carries `tools: [{google_search: {}}]` and `responseModalities: ['TEXT','IMAGE']` (the search tool needs TEXT on). Every image part of the answer is kept as its own reference row (kind `sheet`, same `set`), the text parts are stored as the picture's **notes** (method chosen, findings, contradictions, sources with URLs) and the grounding sources with them. Up to four pictures, as SK saw in the app; the API's count is a test item (section 7).
- **Silent.** `vw visuals round` prepares everything: frames for the things the footage has (pass 1 as today) and the generated sets for every thing at once, no question per element; cost told once up front (elements × the Pro-tier price × up to four, against the cap).
- **Shown in one shot.** The page's References step shows every element's set in one view: the pictures, the notes under them, one verdict per element: **Yes** (approves the set), **No** (rejects it, with optional words), or **Correct it** (words required). **Done** records all at once with the words. Every No or Correct it element goes into the next round, the correction words added to the subject block as "the operator's correction", the rejected pictures never parents (design/71 P6 holds).
- **Retired for new films:** the Search verdict, pass 2, Apify Google Images picks and their notes, the watermark line, "sources changed" on a pick. Films started before this release keep them (film NULL, design/35). The functions stay for them; `vw visuals search` and `pick` are refused on a new film by name ("retired by design/151: references are made by the kept method").

### 3.4 Downstream (what follows from a set instead of one sheet)
Proposals, each to confirm with SK (section 8):
- **The golden picture of a thing** is the picture of the set the operator ticks on the page before Yes (Q2: always the tick; Yes without a tick is refused). No separate golden call (today's `--golden` call from the sheet is retired for new films). An exact object's golden picture still carries its approved frame: the frame is Image 1 of the set's call.
- **A person's identity pictures** for shots: the face close-up and the full-length front (two of the set) are what a keyframe inherits; the other poses are available by name. This keeps Gemini's cap of five character pictures for two or three people in a shot.
- **Drawn shots and components** read the golden picture as today.
- `image_check` on a set picture: the kept method's checks (one way only; the subject fills the frame, the setting a hint; nothing floats; no person, no text) replace the labelled-views and plain-ground lines for things; a person's set keeps plain ground and no labels.
- The page's element state reads "set approved" where it read "sheet approved"; `elState` and the step's done mark count the set.

## 4. Unstated but expected
- One round for all elements, two page visits at most (design/79's promise kept).
- Nothing paid from a click; the cost said before the round.
- Every verdict recorded with the operator's words (design/99).
- The decision log (design/145) gets the round, each set, each verdict and each correction round.
- A thing whose footage frame was approved and which cites the footage (`identity: exact`) gets its set made from the frame (Image 1) by the kept method, so the AI picture matches the client's own thing; a representative thing gets no frame.
- The library of prompts (`work/visuals/library/`) gains the kept prompt file as the `reference` step's reading.
- Old films: untouched; their sheets, picks and golden pictures keep working.

## 5. Downstream uses that change (to consult SK)
| Use today | After | Decision |
|---|---|---|
| One sheet per thing, labelled views, then a golden picture made from it | A set of 2–4 pictures; one of them is the golden | Q2 |
| A person's one sheet, the golden picture, inherited by every keyframe | A set of 3–4; two inherited by default | Q3 |
| A thing with a frame: sheet from the frame and picks, golden from sheet + frame | The set made from the frame by the kept method | Q1 |
| Web picks and their notes shape the sheet | Gone on new films; the operator's correction words shape the next round | Q5 |
| `image_check` lines for a sheet (views labelled, plain ground) | The kept method's checks for things | section 3.4 |

## 6. Contradiction check (the gate before deploy)
Each rule below is checked against the build before a deploy; a contradiction stops it.
1. design/124 decision 5 and (c): no picture of a real person to the AI; no AI picture of a speaker. Held: people from words only; the frame parent is for things.
2. design/119 rule 2 (labelled views on a sheet) contradicts the kept method ("no borders, numbers or captions inside any picture"): rule 2's labels are retired for new films; the views are named in the notes instead.
3. design/119 rule 8: measure before the first picture. Held: the set call is refused while a size is unknown and a frame is approved, as today's non-sheet calls are. (Today a sheet is exempt; the set is not, since it is the golden picture too.) To confirm: Q6.
4. design/111 F11: the golden picture made from the approved sheet. Replaced on new films by section 3.4; old films keep it.
5. design/71 F2 prompt lint (no logo, model name, size, resolution): the kept preamble passes it (checked: no model words, no sizes). The notes may name sites; they are stored, never sent back as a prompt.
6. design/71 P6: a rejected picture is never a parent. Held.
7. design/120 Gemini caps (fourteen inputs, five characters): a set's call sends at most the frame; shot calls use two per person.
8. design/91 N9 world line and light measure: a set picture is a reference, not a picture in the film: no world line (as a sheet today).
9. design/35 old ways: every retired function refused by name on new films; films with `film` NULL untouched.
10. design/125 word budget: the step texts gain pointers only; the how lives in the tool's answers.
11. SK 2 Nov, all categories: the preamble is generic; the cosmetics come from the film record and the plan, never a fixed place.
12. One flow, two front ends: the verdicts are server functions; the page and `vw visuals round --verdicts` call the same.

## 7. Edge cases and failure modes
- The image call returns one picture only, or text only (a refusal, a block): the element row shows it with the words; the round goes on; the element is listed for the next round. No retry paid without the operator's Yes to the round's "make again" list.
- Search grounding not available on the model id in `.env`: the call fails with the provider's message; the server does not fall back to an ungrounded call silently (the method depends on the photographs); the operator is told.
- A thing with no photographs to be found (the kept file's trials): the notes say so; the operator judges.
- More than four pictures in an answer: the first four kept, noted.
- Cap reached mid-round: the elements not made are listed; nothing silent.
- A plan with no things and no people: the round completes at once.
- Two people identical on every compared trait: refused before any payment, both named.
- The operator corrects a thing three times: the third round is made like any other; no limit, each paid and told.
- Concurrency: one round at a time per film (as today); a second `round` while one generates is refused.
- An old film (film NULL) calling the new path: refused with "this film uses the earlier references"; its own path untouched.
- A reference row of kind `sheet` without `set` (old films) reads everywhere as today.

## 8. Questions for SK (asked one per message)
- Q1. A thing with an approved footage frame: is its AI set still made (from the frame, by the kept method), or is the frame enough and no AI picture is made for it? **SK, 4 Nov: yes, made from the frame.**
- Q2. Of a thing's set, which picture is the golden one that shots bind: the first unless the operator ticks another, or always the operator's tick? **SK, 4 Nov: always the operator's tick.** Yes on a thing's set needs one ticked picture; Done is refused naming the things without a tick.
- Q3. A person's set into a shot's prompt: the face close-up and the full-length front by default (the others by name), given Gemini's cap of five character pictures? **SK, 4 Nov: yes, those two.**
- Q4. A person the script acts with but the plan lacks: a warning on `vw visuals check`, or a refusal until the element is added?
- Q5. The Google Images search (Apify) and the picks: retired on new films outright, or kept as a fallback the operator can ask for after two rejected rounds?
- Q6. Measure first: a thing with an approved frame and a size still unknown is refused its set until measured (today a sheet is exempt). Keep the refusal?
- Q7. The cosmetics (place, light, camera height): the server from the plan's foundation and the footage measure, or the assistant per element?

## 9. Tests first (outline)
`test_design151_refs_pure.py`: the server's person prompt carries description, outfits, why lines and the others' one-line differences; identical people refused; the subject-block "how" refusal; the preamble and set line added verbatim; the call carries the search tool and TEXT+IMAGE; every image part stored as a set row, notes and sources kept; the first picture is golden (or the tick); the one-shot page verdicts; a correction round carries the words and never a rejected parent; retired calls refused by name on new films and allowed on old; `image_check` lines per kind; keyframe inheritance of two per person; cap and failure rows. Page tests for the one-shot view. CLI tests for `round --verdicts`. Wording tests. A live test on the VM against the real model (count of images per answer, grounding on) before any film uses it.

## 10. Not covered (deliberately)
- Graphics and the style sheet: unchanged.
- Takes, HyperFrames, drawn scenes: read the golden picture as today.
- Backfilling old films' references.
- Images in the brand library (parked).
- The Apify search as a tool outside the round (kept for old films only).

## 11. Older ways (design/35)
Retired on new films: the Search verdict and pass 2 of the round, `vw visuals search` and `pick` in the round, the labelled-views sheet line, the separate golden call, web-pick notes and the watermark line. Kept until the last film started before this release is closed: all of them, by `film` NULL.
