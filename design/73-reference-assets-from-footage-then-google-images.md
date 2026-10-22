# design/73 — Reference assets: from the footage first, then Google Images; people from the footage allowed

Status: the builder's assessment of SK's proposal of 22 Oct 2026 ("getting reference images"), with the requirements it would need. For SK's review; nothing built. Sources: SK's text of 22 Oct; the visuals prompt and steps (`server/procedures/v2.json`, section 5 and step 4); `visual_contract.Element`; the clip log's entities (`clip_log/schema.py`); `visuals_stage.add_reference` (frame, supplied, web), `generate_image` (isolated, sheet, keyframe, state); the library's continuity kit and consistent-character-frames; design/68, 70, 71.

## 1. SK's proposal, in one paragraph

Once the plan names the shots, the assistant knows which entities will be on screen (people, tools, materials, places). Two steps before any picture is generated: (1) take each entity's look from the footage, which the analysis stage has already labelled, and build a reference sheet from it; (2) only when the footage has nothing for an entity, search Google Images (through the Apify account), show the top ten, let the operator choose, and build the reference sheet from the choice. People from the client's footage may be used as they are (the video permission covers it); an invented person may take dress, build and look from a web image, changed a little; a real public figure is kept exact only when the operator asks. Placement: after the prompts are written, before generation.

## 2. What exists today, and the gap

| SK's step | Today | The gap |
|---|---|---|
| Entities per shot | The plan's `elements` (person, object, place, graphic, animal; exact or representative; requirements; required views), derived by the assistant from the shots. | None: the list exists. |
| Known from the footage | The analysis stage's clip log names every entity per clip (`name`, `kind`, `first_seen_s`, `last_seen_s`, `description`); the visuals package carries these as `world_evidence` per clip; the prompt says "footage first: search the clip analyses first" and `vw visuals frame --clip --at` grabs a frame, free. | The match is the assistant's reading of up to 46 clip logs. Nothing on the server says "element E1 (the mason's hands) is seen in clips 12, 19, 31 at these seconds". On VW-6 the assistant grabbed eight frames by reading; a mechanical list would be faster and complete. |
| A reference sheet from the footage | `vw visuals image --kind sheet --parents <frame refs>` edits a sheet from approved frames; the library's continuity kit says what a sheet holds. | Allowed, not asked for: the step says a sheet is generated "only the views the plan needs". Nothing says "a sheet from the footage frames before any invented look". |
| Not in the footage: the web | The web rule: the assistant proposes a search with the warning, the operator says yes, the assistant searches (WebSearch, gated by `vw web --ok`), shows what it found, the operator downloads the picture, `vw visuals web --element E --file in/<name> --url <https> --quote`. | Manual and slow: the operator downloads by hand; WebSearch is text search, not image search; the picture goes in as a reference of kind `web` with its URL, which is right. |
| Google Images through Apify | Nothing. Apify is not a server dependency; no key on the VM. | New route: the server calls an Apify Google Images actor with the assistant's keywords, stores the top ten thumbnails with their source URLs, the page shows them, the operator picks, the pick becomes a `web` reference with its URL and the operator's words, as today. |
| People | design/68 §6: no consent id exists; a real face is a look reference only (design/71 P5). | SK's decision of 22 Oct settles the open question: people in the client's footage may be used, the video permission covers it. |

## 3. Assessment

**Agree with the two steps and the order.** Footage first is already the rule; what is missing is the mechanical half: the server naming where each element is seen, so the assistant does not read every clip log, and the step asking for a sheet from those frames before any invented look. That alone would have saved most of the reading on VW-6's references step.

**Google Images through Apify is worth building, as a server route.** The present web route works but costs the operator a download per picture. An image search answered as ten thumbnails on the visuals page, with one click to choose, keeps the operator's approval (design/02 decision 10) and the web gate (design/48 O.1: the operator's yes before any search, every call logged) and removes the hand work. Keywords stay short, as SK says: the assistant writes two to four words from the element's name and the client's region, never a sentence. The server keeps the source URL and the operator's words on the reference, as the `web` kind does today, so the record says where every look came from.

**People.** SK's rule gives the policy; the model gives the limit. GPT Image refuses to edit a picture with a recognisable face (design/71 P5 reports the refusal in words). So a footage frame of a person works as a reference for a *generated* picture (the model is asked for a representative person with that dress, build and look) and not as a parent for an *edit* of that frame. The sheet route handles it: a sheet is generated from the frames, with the prompt saying "a representative mason in this dress and build, not a likeness". A public figure kept exact is the one case where the frame itself must drive the picture; that case is rare in client films and stays an operator instruction, not a default. The first pass shows whether the models accept a face among several reference inputs at all.

**Placement.** The right place is the references step (step 4, section 5 of the prompt): after the plan is accepted, so the elements and every shot's subjects are known, and before any keyframe prompt, because the keyframe prompt names its pictures (Image 1 and the sheets) and the job form lists them. That is the same point SK describes ("after the prompts are done, before generation") read with the plan as the prompt: the shot descriptions and the elements are written, the picture prompts are not. The treatment and the plan do not change.

**One flow, two front ends.** The match list, the search and the pick are server functions; the page shows the thumbnails and takes the click, `vw` prints the list and takes the choice with the operator's words.

## 4. What would change (requirements, for SK's approval)

| | Change | Where |
|---|---|---|
| R1 | **Where each element is seen.** At `propose`, and on `GET /visuals/elements`, the server matches each plan element against the clip logs' entities by name and kind (plain word overlap, no model call) and lists per element the clips and seconds where it is seen, with the clip's description, best first; `vw visuals prepare`/`propose` writes `work/visuals/elements.json`; the page lists it under each element. Footage frames stay a click or a `frame` call away. | `visuals_stage.element_matches`, `main.py`, `vw.py`, `visuals.html` |
| R2 | **A sheet from the footage first.** The references step says: for a person, object or place with a footage match, grab one to three frames and generate the sheet from them (`image --kind sheet --parents F1,F2`), the prompt naming the frames by number and asking for a representative look where a face is present; only an element with no footage match goes to the web. | the prompt (section 5), step 4 |
| R3 | **Google Images search.** `vw visuals search --element E --keywords "…" --quote "<the operator's yes>"` and the page's search box call `POST /visuals/search`: the web gate applies (the yes recorded as `vw web --ok` does today, and logged); the server calls the Apify Google Images actor with the keywords, keeps the top ten (thumbnail, source page, image URL, size) under `visuals/search/<id>.json`, and answers them; the page shows the ten with the source; `vw` prints ten lines. Apify's token lives in `server/.env` (`VW2_APIFY_TOKEN`), never in the plugin. A search is a paid call on the Apify account, informed, not asked, after the web yes. | `visuals_stage.search`, `apify.py`, `main.py`, `vw.py`, `visuals.html`, `config.py` |
| R4 | **The pick becomes a reference.** `vw visuals pick --search S --n 3 --element E --quote "…"` and the page's click: the server downloads the chosen image (HTTPS, public address, size limits as `transfer` does), stores it as a reference of kind `web` with its source URL and the operator's words, as `add_reference` does for a hand download today. The sheet is then generated from it as in R2. | `visuals_stage.pick`, `main.py`, `vw.py`, `visuals.html` |
| R5 | **People.** The prompt's reference passage: a person in the client's footage may be used; the frame is a parent for a sheet only where the model accepts it, else a reference for a generated representative person in that dress and build; an invented person from a web picture takes dress, build and look, changed a little, never the likeness; a public figure kept exact only on the operator's instruction, recorded with the reference. design/68 §6's consent line is closed by SK's decision. | the prompt, step 4, design/68 §6 |
| R6 | **Keywords.** The step says two to four words, the element's name and the region or the client's trade, nothing else; a Tamil or local name is searched as given when the operator gives it. | step 4 |
| | Server 0.27.0, plugin 0.25.0. | |

Not changed: the treatment, the plan, the keyframe and take steps, the library, the cap (an Apify call is not on the visuals meter; SK to say if it should be).

## 5. Tests first

- `test_visuals_stage_pure.py`: `element_matches` lists clips and seconds for an element seen in two clips, best first, and an empty list for one seen nowhere; matching is by word overlap and kind; a `pick` stores a `web` reference with the URL and the words and refuses an index outside the ten.
- `test_apify_pure.py`: the actor call's body from keywords; the answer's ten rows from a fake response; a non-HTTPS or private image URL is refused.
- `test_visuals_cli.py`: `search` without the web yes is refused locally; `search` posts the keywords; `pick` posts the index and the words; prepare writes `elements.json`.
- The prompt within 3,500 words; the page renders the element list and the ten thumbnails.

## 6. Not covered

server/tests (Docker); whether the image models accept a face among several references (the first pass shows it); the quality of Google Images for a local tool name (SK's kadapari example is the first live check); the Apify actor's price per search.

## 7. Where it sits in the queue

The builder's suggestion to SK (22 Oct): run the small queued items first (design/68 part B L6 and L7, L24 to L29, L31: about half a day, all seen on VW-6 already), then the first pass with the new rules, then this note with what the pass shows about faces and sheets. If SK prefers this note first, it goes before the pass; the test pass is then the check for both.
