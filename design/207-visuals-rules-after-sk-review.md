# design/207: the visuals rules after SK's review of steps 1 and 2

**Status:** built on 16 Nov 2026 (server 0.104.0, plugin 0.89.0, plugin minimum raised to 0.89.0: every laptop updates); **not deployed**; SK's deployment word awaited.

**Requirement, with SK's points, the analysis and the decisions D1 to D7:** `design/_work/requirement-visuals-rules-review-16-nov.md`. The earlier note `design/_work/requirement-ai-video-any-kind-of-shot.md` is taken into it. SK approved on 16 Nov ("i agree with all your recommendations. go ahead").

## What is built

| # | SK's point | Built |
|---|---|---|
| 1 | Show the world of the film | The plan page opens with "The world of this film", read only: the look, the world rules, what is not shown, the graphic style, every person, place, thing and material |
| 2 | The plan check goes back and forth | The check reports one fault per shot and the plan-wide faults in one answer; it also reports a way the treatment did not name; a checklist for the part the assistant writes alone; the helper's checklist gains shot sizes |
| 3 | Clothes and time | Clothes may change when the time changes (later the same day, another day, another season, years later); face, build and hair never change |
| 4 | A real speaker | The refusal is gone. A person is their own likeness (the operator's photo with their recorded permission) or a stand-in. A refused photo: another photo, or a stand-in |
| 5 | Sizes of materials | Unit sizes only for a material laid as repeating units; a liquid or loose material says its amount or coverage |
| 6 | A human for scale | A person first, else a thing of fixed size; the sentence now reaches the prompt of a still and of an AI video's starting picture |
| 7 | People and "crowd" | Up to ten named background people, each described; every named person gets a sheet; the word is gone; `varied` retired |
| 8 | No circling camera | Refusal removed |
| 9 | No picture twice | The same person may return; the same set-up may not; a footage reuse no longer waits for the operator; 60 s or a quarter of the film |
| 10 | A drawing of a real object | To the convention of its field and to scale, else "not to scale"; the four-sources test is gone; a missing view is a note |
| 11 | Framing warnings | Written as instructions; the three warnings go to the assistant only; a place shown just before is remembered |
| 12 | Look or expression | The dead warning is deleted; a look is framed close with the face in frame |
| 13 | Everyday things and period | The world rule in the instructions; a living extra is carried by words, with no sheet; notes to the assistant for the same extra twice in a row and for several kinds of animal in one shot |
| 14, 15 | Parts Three and Four | The Direction placed by the server; warnings for more still than accepted, stills over a tenth at the plan, a card of words in a documentary; the reasons accepted at the treatment shown under each gap; the contradicting sentences reworded; building-site examples replaced |
| 16a | Any kind of AI video | `recipe: other`; a thing travels along a timed `path` in the scene description; more than four people, a run and overlapping paths warn |
| 16b | Cost limit | ₹750 a minute of film, lowest ₹1,500; `vw visuals cap` for the owner; the plan page shows the estimate against the limit |

Old ways 81 to 90 are in `design/35-decision-log.md`.

## Where

- Plan check: `server/app/visual_contract.py`.
- Plan page, carry-over, cost: `server/app/page_flow.py`, `chat_flow.py`, `visuals_stage.py` (`check`, `propose`, `prepare`, `carried_warnings`, `cap_for`, `set_cap`), `config.py`, route `/visuals/cap`.
- Pictures: `visuals_stage.py` (`likeness`, the round, `_reuse_gate`, the size line), `guide.py`, `templates/visuals.html`, `web.py`, route `/visuals/likeness`.
- The guide: `server/app/guide_spec.py`, `server/blender/guide_scene.py`, `guide_drawing.py`, `plugin/skills/guide/SKILL.md`, `plugin/agents/vw-guide-scene.md`.
- Instructions: `scripts/d207_wording_v3.py`, `server/procedures/v3.json` (the visuals stage: 12,241 to 13,272 words), `plugin/commands/vw.md`, `plugin/agents/vw-plan-gaps.md`, 24 rows in `server/retired-sentences.json`.
- Commands: `vw visuals likeness`, `vw visuals cap`; `vw visuals reuse` retired by name.

## Tests

Server `server/unit`: 1,835 pass (new: `test_design207_checker_pure.py`, `test_design207_page_cost_pure.py`, `test_design207_pictures_pure.py`, `test_design207_guide_pure.py`). Both check files pass. Plugin: 503 pass; the same 7 tests fail on the builder PC with and without this change.

## Not verified

- **The Blender drawing of a thing on a path was not run** (no Blender on the builder PC). The script is compile-checked only. Try one on the VM after the deploy.
- **The visuals page** (the permission line on a person's card; the reuse box removed) was not seen in a browser. The page tests were updated as text and not run (no Chromium here).
- **No real picture or take was made:** a sheet from a real photo, and a picture service refusing a photo, are tested with stand-in data only.
- The world block and the reasons under a gap on the artifact page were not seen on claude.ai.
- Nothing was run against a real plan.

## Not covered, and known limits

- **The picture prompt library was not changed.** Three of its lines still pull against the world rule ("every object earns its place"). The library is a fingerprinted snapshot; the sentence goes into its master and a new snapshot is cut, as its own step.
- A real, named person shown as a stand-in is told to the operator only when the assistant marked the person as real and named (`speaker: true`).
- A circling camera can be planned, but the guide's camera is fixed.
- A moving animal in an AI video shot; sound and lip sync on takes; editing the world of the film by the operator.
- A brick filed with no unit sizes but with words in its description passes without a note: the server cannot tell a brick from water.
- "The same set-up twice" compares the plan's words, not the pictures.
- A thing passing through another thing is not checked in the guide, only a person against a thing.
- Instruction version 2 (older films) still carries the old sentences.
- The visuals instructions grew by 1,031 words.

## The critic's review before the deploy (16 Nov, asked by SK)

Three read-only reviewers checked the build before any deploy: the instructions against the server and the tool, the requirement against what was built, and the merged code for defects. No crash on real data was found. 22 findings were fixed in commit 18b5458, each with a test (`server/unit/test_design207_review_pure.py`, `plugin/tests/test_design207_review.py`). The four that could not wait:

1. A storage hiccup could rewrite a running film's cost limit, including the owner's figure.
2. The guide checker's brief was not updated: a shot with nobody in it failed its checks and was never drawn.
3. "Not to scale" with every size known was told by the instructions and refused by the server.
4. A real person's footage frame could reach the picture service with no recorded permission, through an AI video's starting picture.

Also fixed: the dead end when a photo is given after the reference step is complete; the operator's plain lines now shown on the plan page ("Read before you answer"); texts that sent the operator to the server's page; who runs `vw visuals cap`; when a permission can be recorded; people who read alike named at the check, all pairs at once; and twelve small ones.

Left open on purpose: a film already in progress meets two of the new refusals on its next proposal (the current films are test runs); the world of the film is not on the chat card; `session_of(create=True)` returns an empty session when the read itself fails (an older weakness, not from this change).

Released together with design/208 (the word page, from the stage-fixes thread; its old-way rows are 91 to 96).
