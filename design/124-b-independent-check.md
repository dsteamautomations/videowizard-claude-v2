# Independent check: visuals stage, old v3 (git HEAD) against new v3 (working tree)

Scope: `server/procedures/v3.json`, stage `visuals`, `prompt` + `steps`. OLD = `git show HEAD:...`, NEW = working tree. Code checked: working-tree `server/app/visual_contract.py`, `server/app/visuals_stage.py`, `plugin/scripts/vw.py`.

Mechanical checks (script, unit = sentence or "; " clause):
- Common part (old sections 0, 1, 3 and the cap paragraph) is word for word in NEW A–D. Only the "How to read this" line and new headings were added.
- Later text (NEW sections 5–10) against old guide sections 5–8 and old steps 3–6: every NEW unit is found word for word in OLD except the headings, the connector "References made by the picture AI, the fourth source after the round:", and the two sentences named in the trace (`changes` for acting shots; `short_route` in `warning_answers`). Every other old later unit is present. **Verified.**
- New steps list: 8 short pointers. Old step text was moved into the guide (sections 1–4 and 9–10). Nothing is left only in the steps.

---

## PROBLEMS

### P1. New contradiction with the code: a warning that no longer exists (section 6, later text)
- Old/new (unchanged): "a shot whose final state must be exact says so in the plan (`end_state_exact: true`; the check warns when a shot with a change list is left start-only, so it is a choice)"
- Code: the `end_state` warning was removed under the approved dead-weight fix / film-type item 10 (visual_contract.py:854, "no end_state warning on the default").
- Why it matters: the AI is told a warning will flag start-only shots. None comes, so it may wait for one or answer one that never appears. This sentence sits in the "byte-identical" later text, so the trace's two-sentence list missed it.
- Fix: replace the bracket with "(`end_state_exact: true`; start-only is the default, no warning)". This adds a third later sentence to the trace.

### P2. Number or condition changed: "(warned when missing)" claims checks that do not exist
- Old: "Every shot lists the claims … (`claims`) and … (`descriptors`)"; "A shot that carries a claim says how it shows it (`evidence`)"; "a shot names the facts it rests on (`fact_ids`)"; "Every shot names the message it carries (`message`)"; step 2 "a claim its kind (visible … invisible …)".
- New (section 3, Meaning): "Per shot (warned when missing): `claims` and `descriptors` …; `evidence`; `claim`, visible … or invisible; `fact_ids` …; `carries_over` …; `message` …"
- Code: `claims_missing` fires only on a non-graphic shot with narration (683). `evidence_missing` fires only when the shot has claims (686). `facts_missing` fires only when the shot shows a material or a process (679). `carries_over_missing` fires only on the next step of a process with acting subjects (689). Nothing warns on a missing `message` or a missing `claim` kind.
- The same over-claim appears in section 3, Elements: "Every person, object, animal and material has its real size (… warned when missing)". `element_size_missing` covers person, object and animal only (1038); a material's sizes live in its `material_spec`.
- Why it matters: the old condition "a shot that carries a claim" for `evidence` is lost. The text also promises a safety net that is not there.
- Fix: "Per shot: `claims` and `descriptors` (warned when missing on a shot with narration); `evidence` when it carries a claim (warned); … `fact_ids` (warned on a shot of a material or process) …". Drop "warned" for `message` and `claim`. In Elements, drop "material" from the warned list or say "(a material: its material_spec)".

### P3. Lost: what counts as evidence
- Old (P33): "A shot that carries a claim says how it shows it (`evidence`): a test, a table, or the result in a scene, never an unrelated picture."
- New: "`evidence`;" with no definition.
- Why it matters: the ban "never an unrelated picture" is a content rule. The server's warning only fires when the field is empty, not when the evidence is unrelated.
- Fix: "`evidence` (a test, a table, or the result in a scene, never an unrelated picture)".

### P4. Lost: what the ambient line is
- Old (step 2): "Give every scene with a video shot its ambient line: one line saying what moves around the action (leaves and fronds in the breeze, dust or smoke in the air, people in the background at work) … or 'still' when nothing else should move; the server writes it into every take and the take check asks for it."
- New: "A scene with a video shot has its ambient line (warned without), from the setting and the neighbouring footage, or 'still'".
- Why it matters: "ambient line" is used in four new rules (crowd, passer-by, groups), but the text never says what goes in it, or that every take is checked against it.
- Fix: insert ": one line on what moves around the action (leaves in the breeze, dust in the air, people at work behind), written into every take and checked".

### P5. Lost: what a light line holds, and the light-and-colour check
- Old (step 2): "Give each scene its light once (light: the sources against the landmarks, the main one, hard or soft, colour, strength)". Old (P33): "The check measures each picture's light and colour against the footage beside it and marks a large jump."
- New: "every scene its `light` once (warned without) …". Neither the content of the line nor the measured check is mentioned.
- Why it matters: the AI writes the light line; without the list it may write a mood word only. The `light_missing` message carries the list, but only when the field is empty.
- Fix: "its `light` once (the sources against the landmarks, the main one, hard or soft, colour, strength; warned without) …; each picture's light and colour is measured against the footage beside it".

### P6. Lost: part of the before-proposing review
- Old (P54): "Before proposing: … every shot's route (section 1) and length against its generator, every graphic sequence's states; exact placement timing."
- New: "Before proposing, review each passage's meaning and treatment fit, every subject's beats, layout and scale against the landmarks, identity against the references, and continuity with the neighbours and across shots."
- The trace's pass 2 (F37.11) marks this "rewritten as" with no reason. The check does enforce parts of it: video over 10 s (729), 2–4 states (638), gap coverage (876).
- Fix: append "every shot's route and length against its generator, every sequence's states, and exact placement timing".

### P7. Meaning changed: who allows a clean place
- Old (step 2): "never staged empty unless the treatment says so".
- New: "unless approved clean (a show home …), the reason in `staged_clean`".
- Film-type item 4 says "approved with the treatment". The new text names no approver. The code only checks that `staged_clean` is not empty (896), so the AI could set it itself.
- Fix: "unless the treatment approves it clean (…), the reason in `staged_clean`".

### P8. Lost entirely, still refused by code (the AI learns them only by failing)
- Old: "every count that changes is named in `changes`". Refused at visual_contract.py:786–793. NEW: none.
- Old: "a carriable thing is an object, never fixed". Refused at 836. NEW: none.
- Smaller field details, kept only in the refusal messages:
  - facing heading (`landmark_id`, `edge`, `camera_side`);
  - props fields (holder, start place, end in_hand / set_down + position / carried_out + cause);
  - gaze parts (`head_turn`, `mouth`);
  - the person's fixed layer (build, age, skin, hair, posture, garments);
  - `view` values (cutaway, plan, side, elevation);
  - `tried` "with why each failed";
  - "match" = the same shape or movement across the cut;
  - motion values (push_out, pan_left, pan_right).
- Fix: add the two refused rules to "Refused:" in section 3: "an object count that changes without its `changes` entry; a carriable thing in `fixed`". The field details may stay with the schema and messages if SK accepts that (Part B item 3).

### P9. Approved fix possibly not applied: the treatment's `activity_level`
- Film-types dead-weight row: the treatment's `activity_level` "is stored but never compared … Either compare it at propose or drop it". SK approved "the 4 dead-weight fixes".
- New section 2 still asks for `activity_level` per gap. visuals_stage.py neither checks it nor compares it (grep: no `activity_level` in visuals_stage.py).
- Fix: confirm with SK whether this row was one of the four. If it was: drop it from the treatment entry, or add the comparison at propose.

### P10. Server messages contradict the new `warning_answers` rule (Change 7)
- New, section 3: "two graphics in a row … the second's `warning_answers` saying why". New, section 9: "needs its reason in its `warning_answers` (kind short_route), never in the purpose".
- Code: `graphics_back_to_back` says "the second shot's purpose must say why it stays a graphic" (894). `short_route` says "say in purpose why … ('because …')" (661–662), and it is silenced by a "because" found in the purpose (`ROUTE_REASON`, 658).
- Fix: point both messages to `warning_answers` and stop reading `purpose` for `short_route`.

### P11. Unapproved addition
- New, section 3: "Warned unless size_reason states a reveal: … three shots in a row at one size …".
- No old sentence and no decision covers it. It is true to code (`size_repeat`, visual_contract.py:1072, already in HEAD), and the trace's "server's names" list does not mention it.
- Fix: keep it and record it in the trace for SK's nod, or remove it.

### P12. Small losses (low impact)
- "a gap under revision skipped" (the wait's drafting): new says "accepted gaps only". This is implied, since a revised gap is no longer accepted.
- Picked web pictures: "show them" lost.
- Labels: "readable on a phone" lost.
- Foundation: "if not, add the missing recommendations or name the question" lost. Now reads "the foundation alone should let another director work".
- `visual_facts` meanings lost: the fields (looks, how, setting, tools); confirmed = from the client or a standard; observed = in the footage.
- Fix: restore in a few words each, or accept as trimmed.

No numbers were found changed apart from decision (b) ("six to ten seconds" → the 8 s run). All of these survive: 4 %/6 %, 1.35×, 60 s, 10 %, 12 s, 3–5 s, 2–4 states, 3 s, 8 frames, 25 clips, 900 s, one in four, 3 : 1.5 : 1, two or more signs, three fixed, 5 %, 4/3/5 s.

---

## Marks, per old unit of the four phases

Unit split: sentences and "; " clauses, 342 units. Old guide P19–P26, P33–P36, P39–P41, P54; old steps 0–2 and the four-phase part of step 3. The counts are approximate where a unit carries several rules.

| Mark | Count |
|---|---|
| kept (same meaning, possibly reworded or moved) | ~246 |
| shortened-and-enforced (code line confirmed) | ~45 |
| changed-by-decision | ~37: Changes 1, 3, 6, 7, 8, 9; Note D; A3 5/9/20; SK (a), (b), (c), (d), (e); film-type items 1, 3, 4, 5, 6, 7, 8, 9, 11, 13, 14, 16, 17, 18, 19, 20, 21; dead weight `boundary_continuity` |
| LOST | 11 (P3, P4, P5 ×2, P6, P8 ×2 rules, P12 ×4) |
| MEANING CHANGED | 2 (P2 `evidence` condition, P7 who approves clean) |
| NUMBER OR CONDITION CHANGED | 1 group (P2 "warned when missing") |
| unapproved addition | 1 (P11) |
| new contradiction | 2 (P1 in the text against the code; P10 server messages against the text) |
| approved fix not applied (to confirm) | 1 (P9) |

Later text: unchanged except the two named sentences. The connector and headings are as the trace says. P1 is a third sentence there that the approved fixes made untrue.
