# design/94 — Release 1: the right picture in the right shot

24 Oct 2026. Release 1 of the combined revision (`VW2-revision-plan-2026-10-24.md`). It builds design/93's S1–S5, L1–L4, A1–A2 and U1–U3, plus the check-lines bug behind S4. SK approved A1 on 24 Oct: approving a shot's picture also places it. **Nothing is built until SK approves this note.**

Read against server 0.40.0. VW-7, read-only on 24 Oct:
- 52 generated pictures (keyframes and states) record their shot.
- 4 have no shot: all automatic fix pictures (`-fix`), which never carried one.
- No placement holds another shot's picture or a web picture (design/93 L5, done).

## 1. The requirement, restated

A picture made for a shot is listed, checked, approved and placed **only in that shot**. Approving it places it in one step. A sequence's states come in the plan's order without ticking. A web picture is a guide and never goes into the film. Both front ends get the same rules from the server.

## 2. What changes

| # | Rule | Where |
|---|---|---|
| R1.1 (S3) | A keyframe or a state must be made for a shot (`shot_id`). A state with no `shot_id` takes its parent's shot. A fix picture takes the shot of the picture it fixes, both when it is made and when the page reads an old one (VW-7's four). Element references (isolated, sheet, style) have no shot. | `generate_image`, `image_check.fix_body`, `page_view` |
| R1.2 (S4, the bug) | A picture's check lines come from **its own shot only**: claims, what it depicts, the spec's relationships and sizes, the spec's label, and the spec-approval warning. An element reference made for no shot gets the element's facts and the label lines, and no shot's claims. | `_graphic_lines` |
| R1.3 (S1, S5) | A shot box lists only the pictures made for that shot, plus the one placed in it. Each card reads "B02B_S3 · Better thermal performance · keyframe". | `page_view` (adds `shot_id` per reference), `templates/visuals.html` |
| R1.4 (S2, U1, U3) | Under each shot, a folded **"References used (n)"** strip shows the approved references of the shot's elements: frames, supplied files, web picks, isolated pictures and sheets. Each is labelled "TOWN · web · guide only", with no buttons. The shot's own candidate is labelled "AI still for this shot · approve or reject". | template |
| R1.5 (U2) | The server refuses to place a web picture: "a web picture is a guide only; it cannot appear in the film". | `still_from_reference` |
| R1.6 (A1, L1) | **Approving places it.** Approving a picture made for a still shot puts it in that shot, in the same call, from the page and from `vw visuals approve`. The reply names the shot. If the shot already holds a picture, the new one replaces it, and the reply names the one taken out (it stays approved). If the placement would be refused, nothing is approved, and the reply says why. Start and end images of a video shot are unchanged: the take is what gets placed. | `approve_reference`, `vw.py`, page |
| R1.7 (L2) | Placing a picture made for another shot is refused, with a message naming that shot. Moving it on purpose takes the operator's words (`--move "<their words>"`, in chat only: the page no longer lists other shots' pictures): the picture's shot changes to the new one, and it is refused if the picture is on screen elsewhere (H5). A picture with no shot recorded is placed with a warning this release, and refused from the next. A footage frame stays placeable under the reuse rules (design/89 H2–H4), as today (SK, section 4). | `still_from_reference`, `vw.py` |
| R1.8 (L3) | H5's refusal says "This picture is already in B06D_S1. Remove it there first: `vw visuals unplace --shot B06D_S1`, or Remove on the page". A new `unplace` takes a shot's still, sequence or clip out, with the operator's words, and records who, when and their words in the session. The picture stays approved. | `visuals_stage.unplace`, a route, `vw.py`, page |
| R1.9 (A2, L4) | **A sequence in the plan's order.** The server builds the state order from the shot's own pictures, which are not rejected: the first state has no parent among them, and each next state is made from the one before. The page shows the states numbered, with one Approve the sequence and one Reject, and no ticking or "use as a state". `--refs` becomes optional in chat; when given, it must match the server's order. Errors name the cards, for example "state 2 (state-TITLE-b) looks the same as state 1 (keyframe-TITLE-a)". | `sequence`, page, `vw.py` |
| R1.10 | Page: "Use for the shot" goes from the shot's candidates. It stays only on an approved, unplaced picture made for that shot (pictures approved before this release). | template |

## 3. Edge cases and failures

| Case | Handling |
|---|---|
| A picture made before shots were recorded (VW-7: 4 fix pictures) | Read-time inheritance from the original (R1.1). Any other with no shot: listed in a folded "No shot recorded" strip under each shot of its element, placeable with `still` and a warning (R1.7). |
| A keyframe or state requested with no shot | Refused, naming `--shot` (warned since 0.37.0, design/91 batch 2). A state takes its parent's shot first. |
| A shot id that is not in the current plan | Refused by `locate`, as today. |
| Approve, then the placement fails (H5, a gap not accepted, the route is not still) | Nothing is approved and nothing is saved; the reply carries the refusal. The approval and placement are one session save, under the run lock. |
| Approving a picture whose shot is a graphic sequence | Approved only; the sequence is approved with its own button (R1.9). |
| Two not-rejected pictures for the same state (a retry and its original, or a fix and its original) | `sequence` refuses, naming both cards: "two pictures for state 2: X and Y; reject one". |
| The shot's chain is shorter or longer than the plan's states | Refused, naming the count and the cards. |
| A sequence whose pictures record no shot (made before 0.38.0) | `--refs` is used as today, with a warning; refused from the next release. |
| `unplace` on a shot holding nothing | Refused: "B06D_S1 holds no picture." |
| `unplace` on a recorded gap | Refused: "B06D_S1's gap is recorded; reopen the gap first", the rule `record_gap` already uses. |
| Approving the same picture twice | The second call is a no-op for placement (already in the shot); the approval is stamped again, as today. |
| A web picture already placed in a run in progress | None exist (VW-7 checked). Only new placements are refused. |
| Two people approving at once | Each action takes the run lock, as today. |
| Paid work | None added. R1.2 changes lines only; no check is re-run. |

## 4. SK's decisions for this release

- **A1 (24 Oct):** approving a shot's picture places it in that shot.
- **L2, footage frames (24 Oct):** any approved footage frame stays placeable as a still, as today, under the reuse rules (design/89 H2–H4). The plan gets no `frame` field. design/93 L2's "only when the plan names that frame" is not built.

## 5. Tests first

`server/unit/test_design94_r1_pure.py`:
- R1.1: a keyframe without `shot_id` is refused; a state with no `shot_id` takes its parent's; a fix's body carries its original's shot; `page_view` gives an old fix its original's shot.
- R1.2: a CUTAWAY keyframe for B01_S6 carries B01_S6's claims and none of B02B_S1's; an isolated graphic picture carries no shot's claims; the spec warning names only the named shot.
- R1.3: `page_view` carries each reference's `shot_id`.
- R1.5: `still` with a web reference is refused with the message.
- R1.6: approving a picture made for a still shot places it in one call; with a picture already placed, it replaces it and names the old one; with H5 refusing, the picture stays a candidate and nothing is saved; a video shot's keyframe is approved and not placed.
- R1.7: placing B02B_S3's picture in B01_S6 is refused naming B02B_S3; with `move` words it is placed and its shot changes; a picture with no shot is placed with a warning.
- R1.8: H5's refusal names the shot and `unplace`; `unplace` clears the asset and records the words; an empty shot and a recorded gap are refused.
- R1.9: the sequence is built in parent order without refs; refs in another order are refused; two pictures for one state are refused, naming both; a look-alike names both cards; no shot recorded falls back to refs with a warning.

`plugin/tests/test_visuals_cli.py`: `approve` prints the shot it placed; `unplace` posts with the words; `sequence` without `--refs`; `still --move`.

The page: a Jinja render test that a shot box carries only its own pictures and the folded References strip with no buttons.

## 6. Not covered

- S6 ("Made for other shots"): nothing today needs it. Frames already sit in the References strip, and S1 removes the other shots' pictures.
- design/93 X, J, P, V, W, K, R, G, A3–A5: Releases 2, 3 and 5.
- `server/tests` (Docker), as before.

## 7. As built (24 Oct 2026)

Server 0.41.0, plugin 0.39.0. Not yet committed or deployed.

- `visuals_stage`: `made_for`, `state_chain`, `_state_order`, `_place_still` (the placement on a loaded session, shared by `still` and `approve`), `unplace`. `generate_image` takes the parent's shot for a state, an end image or a fix, and refuses a keyframe or state with none. `_graphic_lines` reads its own shot only.
- `image_check.fix_body` carries the shot. Routes: `POST /visuals/unplace`, the page action `unplace`, `still` takes `move`, `sequence` takes no `reference_ids`.
- The page: a shot box lists its own pictures (candidates under "AI still for this shot · approve or reject: approving places it in the shot"); folded "No shot recorded (n)" and "References used (n)" strips; Remove on a placed picture, clip or sequence; numbered states with one Approve the sequence; cards read "shot · title · kind · name".
- `vw`: `approve` says where the picture went and what it replaced; `unplace`; `still --move`; `sequence` without `--refs`.
- The procedure (visuals prompt and steps) and `commands/vw.md` say approving places it, `unplace`, `--move`, the sequence without `--refs`, and that a web picture never goes into the film.
- A placement that replaces a clip stretch names the clip in `replaced`.

Tests: `server/unit` 300 passed (16 new in `test_design94_r1_pure.py`; 19 older tests changed to the approved rules: a keyframe names its shot, a gap is accepted before a shot is named, isolated graphics checked against a named shot, the sequence warning for pictures with no shot, H5's new wording). `plugin/tests` 244 passed, 3 failed: the known Windows-only `test_intake` ×2 and `test_start_defect_paths`. Plugin compile-checked. The page script parses (`node --check`).

Not covered by the tests: the page in a browser (checked only by its text and a parse); `server/tests` (Docker); VW-7's own session against the new page (first seen after the deploy).
