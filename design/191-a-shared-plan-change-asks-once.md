# design/191: a change to the plan's shared part is asked once, not once per gap

**Status:** requirements approved by SK on 13 Nov 2026. No code written. For the thread that is building the code fixes.

**Written by:** the monitor of the user runs VW-21 and VW-22 (read-only on the runs).

## 1. What happened (VW-22, 13 Nov 2026, UTC)

| Time | Event |
|---|---|
| 02:18 | Plan version 1 proposed |
| 02:24 to 02:47 | SK accepted all 14 gaps in the chat, one question each (23 minutes) |
| 02:50 | SK's "Yes" on the mortar's material spec was refused ("'illustrative' is earned only after all four sources were tried") |
| 02:50 to 03:06 | The assistant removed the unresearched sizes from the mortar and sand specs; a helper changed the drawings of two shots (B04_S01, B04_S05) |
| 03:06 | The check passed; plan version 2 proposed. All 14 acceptances were dropped and the chat began asking gap 1 of 14 again, although the assistant itself said gap 1 was unchanged |

SK's words: "why is the plan redoing it, it's again asking for gaps 1 to 15".

## 2. The cause in the code

- `server/app/visuals_stage.py:341-345` (`propose`): an accepted gap survives a new version only if `acc['digest'] == gap_digest(plan, gap)`.
- `server/app/visual_contract.py:1422` (`gap_digest`): the digest of every gap holds `plan['foundation']` (whole), `plan['sequence_rules']` (whole), the gap without its notes, and the elements the gap uses without their notes.
- Left out of the digest already (line 1226): an element's `size` and `material_spec` (`ELEMENT_NOTES`), a shot's `size`, `size_reason`, `camera_reason`, `claim`, `warning_answers`, `scene_svg`, `scene_motion`, `drawing_spec` (`SHOT_NOTES`), a scene's `ambient`, `light`, `air` (`SCENE_NOTES`).
- So one changed word in the foundation or in a sequence rule changes the digest of every gap.
- `server/app/chat_flow.py:103` (`_plan_items`): the chat asks every gap that is not in `session['accepted']`, one at a time.
- Not seen: which shared part changed in VW-22 (the plan files are in storage). The spec edits alone are notes and would have dropped nothing.
- The same digest is compared in other places, which a shared change therefore also breaks: `visuals_stage.py:882`, `:2115` (accept), `:2132` (revise), `:2162` ("Accept gap … before working on its shots"), `:3607`, `:3624`, `:4015` and `:4106` (reference bindings).

## 3. Requirement

When a new plan version changes only a part that all gaps share, the operator answers **one question**, not one per gap. A gap whose own shots are unchanged is never asked again by itself. Every question about a changed plan says **what changed**.

## 4. What the fix does

1. **Two fingerprints per gap.** One for the gap's own content (the gap without notes and the elements it uses without notes), one for the shared part (the foundation and the sequence rules). Today they are one.
2. **Own content changed:** the gap is asked again, as today. The question lists what changed: which shots, and which fields, in words.
3. **Only the shared part changed:** those gaps are put behind one question: "The film's shared rules changed: … . N gaps have the same shots as you accepted. Accept the change for all of them?" with the buttons Accept and Change this.
   - Accept re-accepts all N under the new version, with the operator's words recorded on each.
   - Change this takes the operator's words and sends them back as a revision, as today.
4. **Nothing is silently kept.** Until that one question is answered, those gaps count as not accepted, and work on their shots is refused, as today.
5. **Both front ends.** The chat and the visuals page call the same server step (working rule: one flow, two front ends).

## 5. Unstated but expected

- The run log gets one line for the shared acceptance, naming the gaps it covered and what changed.
- The list of what changed is computed by the server from the two plan versions, never written by the assistant.
- Old way (SK's rule of 30 Oct): "a shared change asks every gap again" is retired and listed in design/35.
- Plans accepted before this release keep working: an acceptance without the split fingerprint is treated as today (asked again on any change).

## 6. Edge cases

| Case | Handling |
|---|---|
| Shared part and a gap's own content both changed | That gap is asked by itself; the shared question covers only the unchanged gaps |
| Shared part changed, no gap was accepted yet | No shared question; gaps are asked as normal |
| Only notes changed (sizes, material specs, drawing specs, warning answers) | Nothing is asked, as today |
| A gap removed or added in the new version | Removed: its acceptance is dropped. Added: asked as a new gap |
| A gap with alternatives whose choice was made | The choice is kept when the gap's own content is unchanged |
| Two new versions before the operator answers | The question compares the last accepted version with the current one |
| The shared change is very long | The first 10 changes are listed, then "and N more"; the full list is on the visuals page |
| The operator answers Change this with no words | Refused: words are required |
| References already bound to shots of those gaps | Kept after the shared Accept (today a new digest unbinds them) |
| Two answers at the same moment (chat and page) | The run lock decides; the second sees the question already answered |

## 7. Failure modes

- The earlier plan version cannot be read from storage: the server falls back to today's behaviour (each gap asked) and says so in its answer.
- The comparison fails on an unexpected shape: the same fallback, never a silent keep.

## 8. Tests first

- Unit tests, one per row of section 6.
- Unit tests for the list of changes: a foundation edit, a sequence rule edit, a shot edit.
- One plugin test that the chat shows the single question and its two buttons.

## 9. Not covered

- Why the assistant's edit touched a shared part at all in VW-22: not seen, and not fixed by this.
- The first acceptance of 14 gaps, one question each (23 minutes): unchanged. A way to accept several gaps at once would be a separate change.
- VW-22 itself: this helps the run in progress only after a deployment, which needs SK's explicit yes and restarts the workers.

## 10. Related findings from the same runs (not part of this change)

- VW-21, 12 Nov 10:50: a plan re-proposed after acceptance moved on with two gaps silently back to "to accept"; SK did not notice until the page said "Plan · 2 waiting". The "what changed" line of this design covers that too.
- The full lists: `videobuilder-v4/learnings/first-user-run-12-nov.md` (VW-21) and `videobuilder-v4/learnings/vw22-user-run-13-nov.md` (VW-22).

## 11. Other places an approval is dropped when the plan changes (builder's audit, 13 Nov 2026)

Read in the code, not run. Line numbers are `server/app/visuals_stage.py` unless named.

**A. Same cause as this design (one shared change, every gap at once)**

| # | What the operator loses | Where | In this design? |
|---|---|---|---|
| A1 | Every gap acceptance | `propose` :342-345 | Yes |
| A2 | Every "Change this" the operator asked for and the assistant has not yet answered: the words are dropped as if the gap had been proposed changed | `propose` :346-349 | **No: add** |
| A3 | Every shot's reference binding, with the operator's words on it; it stays void even after the gap is accepted again, so each shot is bound again | `bind` :4015, `packet` :4106, `_keyframe_gates` :3624 | Yes (section 6) |
| A4 | Everything that waits on those gaps' shots (pictures, stills, takes, the word to record) disappears from the chat until the gaps are accepted again; nothing says why | `_accepted_shots` :882, `locate` :2162, `_shots_with` :3607 | Yes, by the one question; the "why" line is **to add** |
| A5 | A gap already recorded into the film is asked again | `chat_flow._plan_items` asks every gap not in `accepted`, recorded or not | **No: add** (a recorded gap with unchanged own content is never asked) |

Kept through a new version, as they should be: selected takes, placed assets, approved references, approved specs, recorded gaps, guides and their stills.

**B. The same kind of loss, from another cause**

| # | What happens | Where | Proposal |
|---|---|---|---|
| B1 | A chosen way of a gap (an offered choice) is kept by its id. If the new version renames or removes that choice, reading the gap fails ("Resolve the focused visual alternative") and the whole chat step stops with an error | `visual_contract.chosen_scenes` :1435, called from `chat_flow._gap_rows` | **Fix:** a choice id the gap no longer has counts as not chosen; the choice is asked again |
| B2 | A treatment line is asked again when any field of its entry changes, and the card says only "changed since you last saw it", not what changed | `_line_digests` :584, `_carry_lines` :595 | **Fix with this design:** the same "what changed" list for a treatment line |
| B3 | A gap whose own content changed goes back to "to accept" with no notice (VW-21, 12 Nov) | `propose` :342 | Covered by "what changed" |
| B4 | The first-step answers of a reference round given in the chat are dropped if the round is posted again before the last one is answered | `chat_flow._round_items` (`chat_round` keyed by the round's time) | Small; **fix:** keep the answers of elements the new round still has |
| B5 | An approved spec loses its approval when the spec is edited | `spec_digest` :3283 | By design (one spec, the operator must see the new values); add what changed |
| B6 | An approved still loses its place when the shot's guide scene changes; the still is made again (paid) | `guide.py` :215, :280 | By design (one shot); no change |

## 12. Built (13 Nov 2026, local with the pending set, not committed, not deployed)

- **Two fingerprints:** `visual_contract.gap_own_digest` and `shared_digest`; an acceptance now keeps `own`, `shared` and its plan `version` beside the full `digest`.
- **A new version:** `visuals_stage.new_version` and `_carry_acceptances` (called by `propose`). Own shots unchanged and only the shared part changed: the acceptance moves to `shared_pending`; the gap counts as not accepted. Own content changed: dropped, and the version it was accepted in is kept (`was_accepted`) for the list of changes.
- **The one question:** `shared_change` (its gaps and the list of changes), `accept_shared` (every gap accepted under the new version with the operator's words, the shots' reference bindings kept, one log line), `revise_shared` (the words wait for the assistant; the question returns when the shared part is proposed changed; a shared part put back restores every acceptance).
- **What changed:** `_diff` (computed by the server from the two versions), `gap_changes` for a gap asked again, the first 10 lines then "and N more" in the chat; the full list in `status` and on the visuals page (`shared_change`).
- **Section 11:** A2 (a revision is answered only when the gap's own content is proposed changed), A4 (the question says the work on those shots waits), A5 (a recorded gap with unchanged shots is kept, with a log line), B1 (a chosen way the gap no longer offers is asked again), B2 (a treatment line asked again lists what changed, in the chat and on the card), B4 (a first-step answer of the reference round is kept while that thing's footage pictures are the same).
- **The page:** the gaps show "to accept: only the shared rules changed" and the list of changes; the administrator ticks them and accepts with the page's own Accept (the same acceptance on the server).
- **Instructions:** the plan part (`scripts/d191_wording_v3.py`). **Old way:** row 50 of design/35.

Checked: `server/tests/check_shared_change.py`, one case per row of section 6 and per item of section 11, on the real decision functions with a store kept in memory; passes. It leaves out the plan's validation and the database.

Not covered, beyond section 9:
- `server/tests/test_visuals.py` (needs Docker; not running on this PC on 13 Nov): not run against this change.
- The page's badge and list: written, not opened in a browser.
- A run that is in the middle of a reference round's first step at the deployment: the first-step answers kept in the chat so far are asked again once (the kept shape changed).
