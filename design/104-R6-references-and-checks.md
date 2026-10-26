# design/104 — Release 6: references that carry the real thing, and the remaining check lines (course D1–D3, C2–C5)

26 Oct 2026. Course handover batches D and C (`course-review/HANDOVER-course-learnings-for-builder.md`), as planned for Release 6. **Nothing is built until SK approves this note.**

## 1. How it stays simple and breaks nothing

- **Every new picture line is a should line.** It reports, but never blocks a picture and never starts a fix round (design/96 X1). The one new **must** line is for takes and comes from the handover (the light kept through a take, C5). A failed take line only marks the take, as today.
- **New lines apply to new pictures and takes only.** Pictures already checked keep their checks.
- **References are advised, not bound automatically.** The packet tells the assistant which footage frame to bind and why. Binding stays the assistant's step, approved as today.
- **Nothing touches a fingerprint.** The advice sits in the packet's context. The new lines sit on the picture's own checklist.

## 2. What changes

### References that carry the real thing (batch D)

| ID | Rule | Where |
|---|---|---|
| D1 | **The texture reference** (C03-3). A client material (an exact object or material element) shown at MS or closer, or at an unstated size, binds an approved footage frame of that material: "take only its surface: its colour, wear and joints". | Packet context `bind_advice`, naming the frame ids |
| D2 | **The location's look reference** (C08-2). A shot in a place that has an approved footage frame of that place binds it: "take only its light and colour". This is the colour source at generation (handover 1b). | Packet context `bind_advice` |
| D3 | **The scale reference** (C03-7). For each exact object: a footage frame with a hand or a person beside it; else an edit placing it beside two or three objects of the same shoot at true relative size, with no text. | Procedure, reference step |

### The check lines (batch C)

| ID | Line | Kind | Applies to |
|---|---|---|---|
| C2 | "wear: materials show their real age and wear (uneven colour, chipped and worn edges, irregular joints, dust where work happens); clothes on people doing dirty work are soiled; skin shows texture" | should | Every scene picture (added to the fixed scene lines) |
| C3 | **Measured detail, in code, with no model call:** the picture's edge energy against the footage frames beside its gap, as N9's light line does for colour. It fails when the picture is more than 40 % smoother, and it always reports the ratio so the threshold can be tuned. It runs only when at least 3 footage frames exist. | should | Keyframes and isolated pictures |
| C4 | "frozen person: no person stands frozen while others move" | should | Every take |
| C5 (A1) | "light: the main light comes from where the scene's light says; shadows fall opposite" | should | A picture in a scene with a light line |
| C5 (A1) | "light kept: the light keeps its direction and brightness through the shot" | **must** | A take in a scene with a light line |
| C5 (A2) | "air: {the scene's air} is visible, lit by the light" | should | A picture in a scene whose air is given and is not "clean" |
| C5 (A3) | "shot size: the picture is a {size}" | should | A picture for a shot with a size |
| C5 (A5) | "real size: {element} is {its sizes}, true against the person and the place" | should | A picture showing an element with a size |

## 3. Left out, and why

- **C3's threshold, tuned.** VW-7 was reset this morning and has one approved footage frame, so its pictures can't be measured against their footage. The line ships as a should line with the handover's 40 % and reports every ratio, so the first runs with footage frames give the numbers to tune it.
- **B5's sheet check line** (clothes of two people in different colour families). One picture can't show the other person's clothes. The rule stays in the procedure (design/102).
- **Automatic binding.** The assistant binds, as today, and the packet says what.

## 4. Tests first

- **D1, D2:**
  - the packet's `bind_advice` names a material's approved frame for an MS shot, and not for a WS shot;
  - it names a place's approved frame;
  - it names nothing without approved frames;
  - the preparation digest is unchanged.
- **D3:** the procedure carries the sentence.
- **C2:** a scene picture's lines include wear; a graphic's don't.
- **C3:**
  - smoother than 0.6 of the footage fails;
  - close to the footage passes;
  - fewer than 3 frames runs no line;
  - a graphic gets none.
- **C4:** every take is asked the frozen-person line.
- **C5:**
  - at generation, the picture's checklist gains the light, air, size and real-size lines only when the fields are given;
  - a take in a lit scene is asked "light kept" as a must;
  - a take without a light line isn't.
- **Suites:** `server/unit` and `plugin/tests`. The plugin doesn't change.

## 5. Not covered

- Whether the model check reads these lines reliably. Each is a should line, so its "seen" text will show it on the first pictures.
- `server/tests` (Docker).

## 6. Release

Server 0.51.0 (on 0.50.0). Not committed or deployed until SK says so.

## As built (26 Oct 2026)

Server 0.51.0 (on 0.50.0), plugin unchanged. Not committed or deployed.

**What changed:**
- **D1, D2:** `bind_advice(plan, session, shot)` sits in the packet's context. D3 sits in the procedure's reference step, with a pointer to the advice.
- **C2:** `wear` joins the fixed scene lines.
- **C3:** `detail_line` measures edge energy against the footage frames; it fails below 0.6, needs 3 or more frames, and reports the ratio. It runs after N9's light line.
- **C4:** `frozen person` joins the fixed take lines, so there are six.
- **C5:**
  - `picture_lines` adds light, air, shot-size and real-size should lines to a new keyframe or isolated picture;
  - a take in a lit scene is asked `light kept` (must).

**Tests:**
- `server/unit`: 441 passed, 7 of them new in `test_design104_pure.py`.
- Three older expectations were updated to the approved rule: the take-line count (5 to 6) in `test_design91_b1_pure` and `test_design101_pure`, and the fixed scene lines (+ wear) in `test_image_check_pure`.
- `plugin/tests`: 267 passed, with the 3 known Windows-only failures.
