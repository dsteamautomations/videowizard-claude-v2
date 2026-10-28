# design/119 — References that reach the model: nine rules from VW-7's rejections (requirements, 28 Oct 2026)

Source: design/118 (the assessment, corrected) and the dump of VW-7's sixteen rejected shot pictures with SK's notes. SK approved the nine items one by one in plain words on 28 Oct ("Approved move to main thread and start implementation"), with two standing instructions: **nothing here is an adjustment for VW-7**; every rule is general and applies to the next run as to this one; and **no deploy until VW-7 is complete**. The four-picture cap of design/111 F21 is already removed (0.69.0, commit 723012b); this note builds on that.

## 1. The requirement

Where a reference or a size exists for a thing in a shot, it reaches the image model in the form that works (the picture, cropped to the thing; the size as a number beside the thing; an exclusion naming what a style picture must not lend), the check reads what the model saw, and the plan cannot describe a thing the footage shows in words that contradict the footage.

## 2. The nine rules

| # | Rule | Where |
|---|---|---|
| 1 | **Cropped parents.** Any picture named with a prompt may carry `region` (left, top, width, height as fractions of the frame, the design/111 F11 shape). The server crops before the upload, stores the crop beside the reference (`<ref>-crop-<hash>.png`), sends the crop as Image k, and the check receives the crop as that reference, so it sees what the model saw. | `generate_image` (`parents` becomes a list of `{id, region?}` or ids), `_queue_image`, `process_image`, `image_check.run_check` |
| 2 | **Server-cued reference sheets.** When an element's sources are approved (web, supplied or frames) and it has no sheet, the server cues "sheet for E: write it now" the way it cues the golden picture; the sheet prompt gets server lines: each `required_views` view labelled; "the thing alone on plain ground, nothing else"; one job line per source. The check gets one must line per required view and one for "nothing but the thing". | `sheet_due` beside `golden_due`, status and page items, `generate_image` for kind sheet |
| 3 | **Exclusion lines written by the server.** For a reference sent for its style or look (a place picture, the style, a sheet of another element used for look), the server reads that reference's own stored prompt, takes its Details sentence's things, and adds "Image k also shows a bicycle and a clay pot: show neither". | `generate_image`, a helper `also_shows(ref)` |
| 4 | **Inventory as a must, per object.** One failing line per object that any sent reference's record names (its Details, its inventory) and the shot did not ask for, so a leaked bicycle fails by name instead of inside one long inventory line. | `inventory` lines in `_graphic_lines` / picture lines |
| 5 | **A reference goes in only when its thing is in the shot.** A parent whose element is not among the shot's `element_ids` (or the style, or a person in frame, or the picture being edited) is refused by name. The order rule stays; the cap is gone; `MAX_INPUTS` 16 is the ceiling. | `generate_image` |
| 6 | **Element sizes into the prompt.** Every element in the shot with a size gets a sentence beside its name: "the broom is about 600 mm long"; the check's real-size line stays. | `generate_image`, `size_sentence(element)` |
| 7 | **A footage-shown thing carries its frame.** An element whose fact `source` or size `source` cites the footage (a frame id, or the words footage or frame) must be `identity: exact` and have an approved frame before any picture of it is made: the plan warns, the References step refuses the picture. | `validate_plan` warning, `generate_image` refusal |
| 8 | **Height words and measure first.** A scene layout saying "knee height", "waist height", "chest height" or "head height" of a thing gives a must line ("the plinth reaches the person's knee; the rest of the person is above it") and a prompt sentence; an element with an unknown size that has an approved footage frame is measured (`vw visuals measure`) before its first picture: the References step refuses until a measurement exists for it. | `picture_lines`, `generate_image` |
| 9 | **Passers-by in words.** A background person who only passes is never a named element with a sheet; the scene describes them in words, different in every scene; the "no two alike" rule applies to them. | procedure text, plan warning when a person element has `role: passer-by`-like wording ("passer", "walking by") in its requirements |

## 3. Unstated but expected

- Nothing changes for a run with no sizes, no facts citing footage and no style parents: the prompts read as before plus the size sentences where sizes exist.
- A crop is a view of an approved picture; it needs no approval of its own and inherits the parent's approval and identity; the stored crop file lets the operator see it on the picture's card.
- Rule 5 never refuses the style picture, a person's sheet when that person is in frame, or the start when an end is made from it.
- Rule 7's words are matched in `source` strings case-insensitively; a frame id in `source` counts; "web" or "standard" sources do not trigger it.
- Rule 8 measures only what has a frame to measure on; an element with no frame and an unknown size is unchanged (design/106's `tried` rules).
- The existing material sentence (F10) stays; rule 6 adds sizes of non-material elements.
- The sheet cue (rule 2) does not make the sheet; the assistant writes the prompt, as for the golden picture (design/111 answer 4).
- Plugin: `--parents` accepts `id` or `id@left,top,width,height`; nothing else changes on the operator's side.

## 4. Edge cases

| Case | Handling |
|---|---|
| `region` outside 0..1, zero area, or a third of the frame is not required here (a crop may be small) | refused: "region is left,top,width,height in fractions, inside the frame"; no upper bound on a crop |
| region on a reference that is itself a crop | crops are not references; the id is always the parent's |
| the same reference twice with two regions | allowed; two Images, two job lines |
| crop smaller than 64 px either way | refused: "too small to send" |
| a reference with no stored prompt (a frame, a supplied or web picture) under rule 3 | no exclusion line; nothing to read |
| Details sentence absent or free-form | `also_shows` takes nouns after "Details:" up to the next labelled block; empty → no line |
| the things in Details are the shot's own things (the plan asked for them) | left out of the exclusion |
| rule 4 line names an object the shot does ask for | not emitted (the shot's inventory wins) |
| rule 5: an element in frame through a group or a scene landmark, not `element_ids` | refused with the list; the planner adds the element or drops the picture |
| rule 6: a size with value None | no sentence (D6: no figure for an unknown) |
| rule 6: several sizes on one element | one sentence listing them |
| rule 7: a fact citing footage for an element of kind person | persons keep their sheet as identity; the rule applies to non-persons |
| rule 7: the frame approved after the plan warned | the warning clears on the next plan check; the refusal reads the session |
| rule 8: a height word about the person, not a thing ("a man of medium height") | the regex needs "<thing> at <word> height" or "<word>-high <thing>"; a person's height is not a line |
| rule 8: the measure tool answers "cannot tell" | the size stays unknown; the picture is refused until the operator measures by hand or the plan drops the size |
| rule 9: a named element whose requirements say "passer-by" | plan warning naming it; not refused (the operator may want a recurring person) |
| the model's own 16-picture limit after crops and the server's added sheets | the existing refusal names the count |

## 5. Failure modes

- Crops make the model worse on identity (a cropped face): rule 1 is per parent on the planner's choice; the check reads the crop; a bad crop is rejected like any picture.
- Rule 5 blocks a legitimate look reference (a picture of another element used for its light): the planner lists that element in the shot, which is what the plan should say anyway.
- Rule 7 catches a `source` that says "footage" loosely: the warning says which word; the planner rewords or adds the frame.

## 6. Tests, written first, one file per set

- `test_design119_a_pure.py` (rules 5, 6, 3): a parent of an element not in the shot refused by name; the style, a person in frame and the start allowed; a size sentence per element with sizes, none for an unknown; `also_shows` on a stored Details sentence, nothing for a frame, the shot's own things left out, the line in the prompt.
- `test_design119_b_pure.py` (rule 4): one must line per object from a reference's record not asked by the shot; the shot's own objects excluded; a leaked object fails by name.
- `test_design119_c_pure.py` (rule 1): region on a parent → a crop stored and sent (worker: the file sent is the crop), refusals (outside, tiny), two regions of one reference, the check reads the crop.
- `test_design119_d_pure.py` (rule 2): `sheet_due` lists an element with approved sources and no sheet; the cue text; the server lines on a sheet prompt; the check lines per required view.
- `test_design119_e_pure.py` (rules 7, 8, 9): the plan warning for a footage-cited element that is not exact; the refusal without a frame; the height-word line and sentence; the measure-first refusal; the passer-by warning.
- Plugin: `--parents id@l,t,w,h` parsed; the procedure's new sentences load; 3.9 parse.
- Page: `node --check`; the crop shown on the card (text check).

## 7. Order and commits

One commit per set, in the order of the test files (a: 5, 6, 3; b: 4; c: 1; d: 2; e: 7, 8, 9), then the procedure and the as-built. Server 0.70.0 at the end, plugin 0.57.0. Full suites after each set. No deploy.

## 8. Not covered until built

- Nothing is built; this note is the agreement on the words.
- Whether more pictures with exclusion lines beat four without them is not measured; the first run after the deploy tells.

## 9. As built (28 Oct 2026, server 0.70.0, plugin 0.57.0; not deployed), one commit per set

- **Set A (rules 5, 6, 3).** `generate_image`: a parent whose element is not in the shot's `element_ids` (nor the picture's own element, the style, or a keyframe/state of the start chain) is refused by name; `size_sentence` writes every known size of the shot's elements under "Sizes:" (materials keep their F10 sentence); `also_shows(parent, own)` reads a look parent's stored prompt for its "Details:" sentence, drops camera notes and the shot's own things, and the prompt gets "Image k also shows …: show none of them".
- **Set B (rule 4).** Each such thing is a must line `not shown: <thing>` on the picture's checklist.
- **Set C (rule 1).** `ImageGenerate.crops` {parent id: region}; `check_crop` (inside the frame, no upper bound); `cropped_parent` crops with Pillow at queue time, stores `<id>-crop-<sha8>.png`, and the request's parent entry carries `key` (the crop), `crop` and `full_key`; the worker sends what the entry names; `image_check._model_check` reads the crop for that parent. Plugin: `--parents K1,L2@l,t,w,h`.
- **Set D (rule 2).** `sheet_due` beside `golden_due` in `status`; `sheet_block` on a sheet's prompt; `sheet_lines` (one must per required view, "nothing but the thing") on its checklist.
- **Set E (rules 7, 8, 9).** `visual_contract.footage_cited` and the plan warnings `footage_identity` and `passer_by` in `course_warnings`; `generate_image` refuses a picture of a footage-cited thing without an approved frame, and a picture (other than the sheet) of a thing with a frame and an unknown size until it is measured; `height_lines` and `height_sentence` from the scene's layout.
- **Procedure.** The F21 sentence extended with the nine rules.
- **Tests.** `test_design119_a..e_pure.py` (3, 2, 6, 3, 5), the plugin's `_parents_and_crops` test; the suites after each set.

**Not covered.** The look of a prompt with ten pictures against four (the first run after the deploy); the page shows no crop yet (the crop file is stored and named in the generation record; a card view is a later line); `also_shows` is a heuristic over the planner's own "Details:" sentence and finds nothing in a prompt written without one; the height regex reads "<thing> at <word> height" and "<word>-high <thing>" only.
