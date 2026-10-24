# design/93 — The visuals page from an operator's seat

Status: proposed by Revathi, 24 Oct 2026 (sent as design/92; saved as design/93 because 92 holds the L60 fix of the same day), from operating VW-7's visuals stage (server 0.39.0). For SK's approval. Nothing built. Every rule is for any film. Use the next free number if 92 is taken.

**In one paragraph.** Operating the visuals page on a real run showed three kinds of problem:
- **The plan.** Long runs of graphics pass every check (section 1).
- **The page.** Pictures are too small, approval boxes are far from the picture, and each shot lists other shots' pictures. Actions are confusing and it is unclear what is waiting (sections 2–7, 10–11).
- **The automatic checks.** They judge pictures against the wrong shot or the wrong step, and start paid fix pictures on their own (sections 7–9).

On VW-7 the page's "Use for the shot" placed pictures in the wrong shots, a web picture among them. That needs a repair before the run continues (section 12, L5).

## 1. A long run of graphics passes every check

**Seen on VW-7.** BEAT_02-B2 was drafted as 20 s of graphics only: a cutaway build in 3 steps (11.36 s), then a map build in 2 steps (8.64 s). Each step is under the 5 s state limit (design/89 B1), so nothing warned, yet the passage plays as one long lecture. The map illustrates "used in thousands of buildings across India", a claim about real buildings that the footage can show.

| # | Change | Where |
|---|---|---|
| G1 | **A cap on consecutive graphic seconds.** Graphic shots in a row (any graphic route: sequence, still diagram, drawn graphic), inside a gap or across gaps with no footage or AI scene between them, warn above about **8 s** and are refused above about **12 s**, unless the treatment gives a reason. | `visual_contract.validate_plan`, treatment check |
| G2 | **Claims about real things prefer real pictures.** A claim about things that exist and can be filmed (buildings, people, products, places, results) is shown with footage first, then an AI scene. A graphic is used only for what a camera cannot show (inside, flow, numbers, comparison, sequence) — the rule of design/64 A.3, now checked: the planner tags each step's claim as `visible` or `invisible`, and a `visible` claim on a graphic route warns. | prompt, plan schema (claim `kind`), `validate_plan` |
| G3 | **The split per gap on the treatment.** Each gap's row on the Treatment step shows its seconds and shots per route (graphic, video, still, footage), the same table the assistant gives in chat, so the operator sees the split before approving. Both front ends read one server function. | `visuals_stage` (treatment view), `templates/visuals.html` |

## 2. Approving a picture while seeing it

**Seen on VW-7.** To approve a picture on the visuals page (the graphic style sheet, a reference sheet), the box for the operator's words and the Approve and Reject buttons sit at the very bottom of the page. The operator must scroll away from the picture to type, and cannot see what they are approving while they write.

| # | Change | Where |
|---|---|---|
| P1 | **The words box and its Approve and Reject buttons sit beside the picture being approved**, inside the same panel, or stay fixed on screen while the picture is in view. The picture stays visible while the operator types. | `templates/visuals.html` (every step with an approval) |
| P2 | Applies to everything approved on the page: the graphic style sheet, reference sheets, frames and web picks, stills, graphic sequences, start and end pairs, takes, the treatment and the plan's gaps. One shared approval panel, so the behaviour is the same everywhere. | `templates/visuals.html` |
| P3 | On a narrow window the panel stays fixed at the bottom of the screen, below the picture, and never scrolls away from it. | page CSS |

## 3. The reference sheet shown among its sources

**Seen on VW-7.** On the References step, an element's footage frames, its web picks and its generated reference sheet all appear together, so the sheet sits small at the foot of the sources.

**Why they are together today.** The sheet is generated from the ticked frames and picks (design/79, 80). Seeing them side by side is how the operator checks that the sheet is faithful to its sources. That reason holds only while the sheet waits for approval.

| # | Change | Where |
|---|---|---|
| R1 | **While a sheet waits for approval:** the sheet is shown large in the panel, with its sources as a small strip of thumbnails beside it for comparison (only the ticked ones, not every candidate). | `templates/visuals.html` |
| R2 | **Once the sheet is approved:** the element shows only the sheet. The sources fold into a "sources (n)" line that opens on a click. Untried candidates and unused search results are hidden. | `templates/visuals.html` |
| R3 | Before the sheet exists, the step shows the sources as today, since choosing them is the task. | — |

## 4. Pictures large enough to judge

**Seen on VW-7** (Revathi, operator). The thumbnails on the visuals page are too small to judge brick patterns, joints, labels and spelling.

| # | Change | Where |
|---|---|---|
| V1 | **Click any picture to open it full size**, with zoom (wheel, pinch, +/−) and pan, at the picture's native resolution. Arrow keys move to the next and previous picture in the same element, shot or sequence. | `templates/visuals.html` (one shared viewer) |
| V2 | **The picture under review is shown large by default**, close to the full width of the content area. Thumbnails stay only for choosing among candidates. A start and end pair, or the states of a sequence, can be viewed side by side at the same size, so differences are easy to see. | `templates/visuals.html` |
| V3 | **The approval panel (P1) stays visible next to the enlarged picture**, in the viewer too, so the operator can approve or reject without closing it. | `templates/visuals.html` |

## 5. Knowing where to look

**Seen on VW-7.** When the assistant asks for a review, the operator cannot tell which step, tab or section holds it. The visuals stage has element sheets, the style sheet, graphics, stills and, later, takes.

| # | Change | Where |
|---|---|---|
| W1 | **Every request for a verdict carries a direct link** to the exact picture or section, both in the assistant's chat message and in the tool's printed line. The link names the step, the type, the shot or element, and the item, e.g. `/runs/VW-7/visuals#pictures/graphics/B02B_S1/state-1`. The page opens on that step, scrolls to the item and highlights it. | `vw.py` (every command that waits for a verdict prints the link), `visuals_stage` (the link built by the server, so both front ends agree), `templates/visuals.html` (anchors) |
| W2 | **Labels by type and shot** on every section and item, e.g. "Graphics · B02B_S1 · Hollow cavities", "Reference sheet · MASON", "Take · B01_S3 · segment 2". | `templates/visuals.html` |
| W3 | **A "waiting for your verdict" marker** on each item that needs the operator, and a count per step in the step line ("Pictures · 3 waiting"). A "next waiting" button jumps to the next one. **At the top of the page**, a counter for the whole stage ("6 pictures waiting for your verdict") opens a list of links, one per waiting item with its label, each jumping to it. | `templates/visuals.html`, the page's data view |
| W4 | The assistant's message names the same label and gives the link, never only "on the page". This is a step sentence in `v2.json`, and the link itself comes from the server (one flow, two front ends). | `server/procedures/v2.json` (visuals steps), `vw.md` |

## 6. Web pictures are guides, never candidates for the film

**Seen on VW-7.** Under a shot (B01_S2), the approved web reference for an element ("web-TOWN-4 · web") sits next to the AI still made for the shot, and the web picture has its own "Use for the shot" button. That suggests the web picture could go into the film. We do not own it: it was only a guide for generating our own picture.

| # | Change | Where |
|---|---|---|
| U1 | **No shot actions on web pictures.** "Use for the shot" (and any other action that places a picture in the film) is never offered on a reference of kind `web`. Under a shot, the references that guided it appear in a separate **"References used"** strip: small, labelled by element and source ("TOWN · web · guide only"), with no buttons. | `templates/visuals.html` |
| U2 | **The server refuses it too**, so neither front end can do it: `still` (and any placement function) refuses a reference of kind `web` with "a web picture is a guide only; it cannot appear in the film". Footage frames, operator-supplied files and our own generated pictures stay allowed. | `visuals_stage.still_from_reference`, placement functions |
| U3 | **The candidate is marked as such:** the picture that would go into the film carries a clear label and its actions, e.g. "AI still for this shot · approve or reject", with the approval panel (P1) beside it. | `templates/visuals.html` |

## 7. Under each shot, only that shot's pictures

**Seen on VW-7.** Each shot box lists every picture of every element the shot uses. Under B01_S4 (a title over a real wall frame) appear B05B_S2's wall-face still and the rat-trap web reference, because they belong to an element the title also uses.

| # | Change | Where |
|---|---|---|
| S1 | A shot box shows **only the pictures made for that shot**: its start and end images, its graphic states, its still, its takes. A picture belongs to a shot when it was generated, placed or bound for that shot id. | the page's data view (`visuals_stage`), `templates/visuals.html` |
| S2 | The shot's approved references (sheets, frames, web guides) sit in the separate **"References used"** strip of U1, with no shot actions, **collapsed by default** ("References used (4)"). Pictures made for other shots never appear, even when they share an element. Seen again later on VW-7: every cutaway drawing of the film appeared under B09A_S1. | `templates/visuals.html` |

**Also seen on VW-7: pictures checked against the wrong shot.** Under B01_S6 ("a rat-trap wall beside a solid conventional wall, 'Fewer materials, same strength'"), the page shows graphics made for B06C_S1, B02B_S3, B03B_S1, B02B_S1 and B06D_S1. Each one is marked red against B01_S6's claim, including pictures already approved in their own shot. The same happens under B01_S4, B09A_S1 and other shots that share an element. This causes four problems:
- the description says one thing while the candidates show another
- correct pictures look faulty
- the card ("keyframe-CUTAWAY") does not say which shot it was made for
- it is easy to approve or reject in the wrong place

| # | Change | Where |
|---|---|---|
| S3 | **Every picture records the shot it was made for** (the generation request carries the shot id). That record decides where it is listed (S1). | `visuals_stage.generate_image` (shot id required for shot pictures), the data view |
| S4 | **Checks run, and are shown, only against the picture's own shot:** its description, its claims and its narration words. A picture's check result is stored once, with that shot, and never recomputed or displayed against another shot. If today's page re-runs the Gemini check per shot it is listed under, that is also paid work done several times, and it stops. | `image_check`, the data view |
| S5 | **Every card names its shot and title,** for example "B02B_S3 · Better thermal performance · keyframe", not only "keyframe-CUTAWAY". | `templates/visuals.html` |
| S6 | If a picture shared with another shot must appear (for example, a footage frame used as a background), it goes in a separate, collapsed **"Made for other shots"** strip, with no checks and no actions, linking to the shot where it lives. | `templates/visuals.html` |

## 8. The automatic fix pictures ("-fix")

**What makes them.** Since design/86 K2, when the automatic check fails a `must` line on a new picture, the worker makes **one fix round on its own**: an edit of the picture with the one change the failed line asks for. It is named after the original plus "-fix" (`image_check.queue_fix`). No one asks for it. It is a paid GPT Image call, so it is counted in the spend and in the image count, which is why one picture more than requested appeared.

**Seen on VW-7.** "state-TITLE-fix" and "keyframe-RTB_WALL-fix" appeared under B01_S4. Nobody asked for them, and one has a line drawn across the bricks. That line is most likely the fix round obeying an unfair check line (section 9: "label … leader line"), which shows the cost of a wrong check: a paid picture that makes things worse.

| # | Change | Where |
|---|---|---|
| X1 | **No automatic fix rounds.** A failed check marks the picture and shows the failed lines. A **"Try a fix (₹…)"** button on the card (and `vw visuals fix --ref R`) makes the fix round only when the operator or the assistant asks, saying the cost. One flow, two front ends. | `image_check.queue_fix` (called only on request), `visuals_stage`, page, `vw.py` |
| X2 | **A fix picture is labelled as one:** "automatic fix of <picture> · for <failed line> · ₹<cost>". It stays out of the candidates until the operator chooses it over the original. | `templates/visuals.html`, the data view |
| X3 | **The spend shows fix rounds separately** ("images: 14 requested + 2 fixes"), so no count rises without a visible reason. | spend view |
| X4 | A fix round is never started by a line that the check itself marks as uncertain, or by any line excused under section 9. | `image_check` |

## 9. The check judges each step on what that step should show

**Seen on VW-7.** On a title card built in steps, the first step is marked red for things that only appear in a later step ("depicts the film's subject named in a title", "word: innovative") and for "label … leader line", a diagram rule that does not apply to a title. A correct picture looks faulty, and per section 8 it can trigger a paid fix.

| # | Change | Where |
|---|---|---|
| J1 | **Per-step checklists.** A graphic sequence's checklist lines are assigned to the step where each thing first appears (from the plan's `states[].what_appears`). A step is checked only against its own lines and those of the earlier steps it keeps. The film-subject line (design/91 N10) and the narration-word lines (N8) attach to the step that shows them, never to step 1 by default. | `image_check.lines_of` (per state), `visuals_stage.sequence`, plan schema |
| J2 | **Rules by graphic type.** The leader-line and part-label rules (N13) apply only to diagrams with drawn parts. A title card, a text card or a quote is checked for spelling, size and legibility only. The planner marks each graphic's type: `diagram`, `chart`, `map`, `title`, `text`. | plan schema (graphic `type`), `image_check` |
| J3 | A step that passes its own lines shows green, even if the whole sequence is not finished. The sequence shows "step 1 of 3 · ok". | page |

## 10. Check results fold into one line

**Seen on VW-7.** The red and green check lines under each picture take most of the space.

| # | Change | Where |
|---|---|---|
| K1 | Each picture shows **one summary line**, for example "3 passed · 1 to look at", coloured by the worst result. It expands on a click to the full lines. A failed `must` line also shows its text in the summary, so the main problem is visible without expanding. | `templates/visuals.html` |

## 11. One clear action at a time

**Seen on VW-7.** "Approved", "Use as a state", "Approve the sequence" and "Use for the shot" appear together and are confusing.

| # | Change | Where |
|---|---|---|
| A1 | **A single picture for a shot** (a still, a start or end image): **Approve** or **Reject with reason**, nothing else. Approving places it in the shot. The separate "Use for the shot" step goes; the server does both in one call, from both front ends. | `visuals_stage` (approve-and-place in one function), page, `vw.py` |
| A2 | **A sequence of states:** the states are shown in order, numbered, side by side. One **Approve the sequence** and one **Reject with reason** (naming the step). No ticking, and no "use as a state" on individual pictures. The order comes from the plan. | `visuals_stage.sequence` (states taken from the plan in order), page |
| A3 | **Reference pictures** (frames, web picks, sheets) keep their own Approve and Reject on the References step only. Elsewhere they appear only in the folded "References used" strip with no actions (U1, S2). | page |
| A4 | **After each verdict, one line says what happens next,** for example "Approved: this appears at 0:14–0:17 in the film", "Rejected: the assistant will make a new start image with your note", or "Approved: the video take for B01_S3 is the next step". | the act reply, page, `vw.py` |
| A5 | A picture shows only the actions valid **now**. An approved picture shows "Approved · in the film at 0:14" and an Undo, with no other buttons. | page |

## 12. Placing pictures in the right shot

**Seen on VW-7.** Because each shot box lists other shots' pictures (section 7), its "Use for the shot" button placed pictures in the wrong shots:
- a web reference we do not own (0775c50c) went into B02B_S5
- B06D_S1, B04_S5 and B05B_S6 received pictures made for B02B_S1, B04_S3 and B05B_S4

The H5 rule (no shared start image, design/89) then blocked the right shots from using their own pictures. Its message asked the operator to compose another picture, instead of saying the picture was already in a wrong shot.

| # | Change | Where |
|---|---|---|
| L1 | **Approving places** (A1, restated as the rule): when a picture made for a shot is approved, it goes into that shot. There is no separate placing step on the page. | `visuals_stage`, page |
| L2 | **The server refuses a placement into any shot other than the one the picture was made for.** It refuses web references outright (U2). It accepts a footage frame only when the plan names that frame as the shot's picture, never a frame grabbed as an element's reference. Moving a picture to another shot is a deliberate reuse with the operator's words (design/89 H). This holds from chat too. | `visuals_stage.still_from_reference`, placement functions |
| L3 | **H5's refusal says where the picture is and how to undo it:** "This picture is already in B06D_S1. Remove it there first", with a **Remove** button on the page and a `vw visuals unplace --shot B06D_S1` line in chat. | `visuals_stage`, page, `vw.py` |
| L4 | **Sequence errors name the card:** "state 2 (keyframe-TITLE-b) looks the same as state 1 (keyframe-TITLE-a)", with both cards highlighted. With A2 there is no ticking, so a stray picture cannot become a state. | `visuals_stage.sequence`, page |
| L5 | **Repair VW-7 before it moves on:** list every placement whose picture was made for another shot or is a web reference. Today these are B02B_S5 (web 0775c50c), B06D_S1, B04_S5 and B05B_S6, plus any others the list finds. Show the list to the operator, then remove those placements on their words, so the right shots can take their own pictures. | a one-off check through `vw visuals status`, the operator's words; no database edits by hand |

## Tests first

- G1: graphics of 5 + 4 + 4 s in a row warn; 5 + 5 + 4 + 4 s are refused without a reason and pass with one; a 3 s footage shot between them resets the run.
- G2: a `visible` claim on a graphic route warns.
- G3: the treatment view carries seconds and shots per route per gap, equal to the chat answer.
- P1–P3: the template renders the approval panel inside each approvable item's panel (Jinja render test); the route-exists test covers its actions.
- V1–V3: a click on any picture opens the shared viewer at native size with the approval panel; arrows move within the element or shot.
- W1–W4: every command that waits for a verdict prints a link that opens the right step and item; the item carries its type-and-shot label and the waiting marker; the step line counts waiting items.
- U1–U3: a shot's view renders web references in the "References used" strip with no actions; `still` with a web reference is refused with the message; a generated still renders with the candidate label.
- S1–S6: a shot box lists only pictures generated, placed or bound for its shot id; another shot's still of a shared element does not appear (or appears only in the collapsed "Made for other shots" strip, without checks or actions); a picture's check is stored with its own shot and shown nowhere else; no check is run twice for the same picture; every card carries its shot id and title.
- X1–X4: a failed `must` no longer queues a fix; `fix --ref` queues one and says its cost; the spend line counts fixes apart; an excused line never starts a fix.
- J1–J3: a 3-step title whose subject line belongs to step 3 passes step 1; a title is not checked for leader lines; a diagram still is.
- K1: a picture with 3 passed and 1 failed `should` line renders the one-line summary, expanding to four lines; a failed `must` shows its text in the summary.
- A1–A5: approving a shot's still places it in one call; a sequence is approved in plan order with one call and no ticks; every verdict reply carries a 'what happens next' line with the film time; an approved picture renders only its status and Undo.
- W3 (top counter): the page header counts the stage's waiting items and lists a link per item.
- L1–L4: approving a shot's picture places it; placing a picture made for another shot is refused without a reuse approval; a web reference is refused; an element's reference frame is refused, a footage frame the plan names for the shot is accepted; H5's refusal names the shot holding the picture and `unplace` clears it; a sequence error names both cards.
- L5: the placement audit lists placements whose picture was made for another shot or is a web reference.
- R1–R2: an element with a pending sheet renders the sheet with only its ticked sources; an approved sheet renders alone with a folded sources line.

## Order

1. **Now, before VW-7 continues:** L5 (the repair), then S1–S6, L1–L4, A1–A2 and U1–U3, so pictures can no longer land in the wrong shot.
2. **X1–X4 and J1–J3**, so the checks stop marking correct pictures red and stop making paid pictures on their own.
3. **P1–P3, V1–V3, W1–W4, K1, A3–A5 and R1–R3**, for the page's usability.
4. **G1–G3**, the planning rules, for the next film.

## Not covered

- server/tests (Docker).
- How the fixed panel behaves on every screen size. The first check is the operator's laptop on VW-7.
