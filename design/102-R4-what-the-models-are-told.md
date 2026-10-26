# design/102 — Release 4: what the assistant and the models are told (course batch B)

26 Oct 2026. Course handover batch B (`course-review/HANDOVER-course-learnings-for-builder.md`, section 2), approved by SK for the handover on 24 Oct. The audit of 26 Oct found none of it built. **Nothing is built until SK approves this note.**

## 1. Two decisions, so the release stays simple and breaks nothing

- **The rules live in server text, not a new library snapshot.**
  - The handover put some of this text into a new library snapshot folder: the keyframe card, the playbooks, the camera vocabulary.
  - A snapshot means copying the whole library and moving every new run onto it.
  - Instead, each rule goes where the server already speaks: the take wrapper, the packet, and the procedure's steps.
  - That keeps "one flow, two front ends", and it reaches VW-7 at once. Its library stays as it is.
- **New packet guidance goes in the packet's context.** The packet's instruction texts are part of each prepared take's fingerprint. Changing them would make every ready take on every run unselectable (found in design/101). The context is outside that fingerprint, so the new lines go there, as design/101's M5 did.

## 2. What changes

| ID | Rule (course source) | Text, in short | Where |
|---|---|---|---|
| B3 | Natural, unhurried motion (C05-5) | A fixed line in every new take: "Natural, unhurried motion; no sudden, exaggerated or floating movement." Subtle means **how** things move, not how much: a busy site stays busy. | `video_providers.motion_text` |
| B1 | Three layers, and parallax (C03-4) | "On a wide or medium scene shot, name a foreground, a midground and a background. When the camera travels, write the parallax: what is near slides past faster than what is far." | packet context |
| B2 | Acting where the face is hidden (C05-2) | "Where a face is hidden or small, carry the action in the hands, shoulders and posture, beat by beat." | packet context |
| B4 | Handheld matched to the neighbours (C05-6) | From the clips on either side of the gap (already in the packet): when one is handheld, "ask for slight handheld micro-movement in the take"; when they are tripod, gimbal or drone, "keep the camera steady". Nothing when unknown. | packet context |
| B8 | Imperfections per shot; work leaves traces (C03-3, part) | "Two or three imperfections at their places in this shot, not copied from the scene. Work leaves traces: tools, offcuts, mortar droppings, footprints on an active site; signs of use in a finished house." | packet context; procedure plan step |
| B10, B13 | Framing options (C07-2; 03 L10) | "Thirds by default, the centre only on purpose; use leading lines and give a moving subject room ahead. To show a task, a first-person frame with the hands in front is an option." | packet context |
| B5 | People told apart at a glance (C05-3) | "Two people in one film wear clothes of different colour families, unless the footage fixes their clothes." | procedure reference step |
| B6 | Fewest references (C05-4) | "Bind only what the shot's subjects and place need, and say why each reference is bound." | procedure pictures and takes step |
| B7 | Sharp frames as references (C03-8) | "Grab the sharpest frame, the subject large and evenly lit; never a blurred frame as an identity source." | procedure reference step |
| B9 | Props by context (C07-3) | "Show what is normal for the work and the region (a tea glass on a site); never what the setting forbids (no smoking, flame or spark near fuel, gas or chemicals), and no unsafe practice shown as the right way." Guidance only: no refusal, no check. | procedure plan step |
| B11 | The opening shot carries the subject (C08-1) | "The first gap opens on the strongest picture of the film's subject, not a neutral establishing shot." Guidance. | procedure treatment step |
| B12 | Sheet layouts (C03-9) | **Not a rule yet.** The handover says to trial it first (a six-angle against a three-angle person sheet, compared on the takes). The note asks for the trial on the next run's first person, done by hand; the layout becomes a rule only after it works. | — |

The packet's context gains one block, `guidance`, holding the lines for the shot. Lines that don't apply are left out:
- a graphic shot gets none;
- a close-up gets no layers line;
- B4 appears only when the neighbours' support is known.

## 3. Runs in progress

- **New takes** carry B3, from the next take prepared. Takes already prepared keep their text and stay selectable.
- **The packet guidance** shows at the next `vw visuals packet` for any shot. Nothing on a run is re-accepted, re-bound or regenerated.

## 4. Tests first

- **B3:**
  - the take text carries the motion line once;
  - a take prepared before the release keeps its stored text;
  - a plan with no change keeps the same preparation digest.
- **Packet:**
  - `context.guidance` has the right lines for a wide video shot, a close-up and a graphic shot;
  - B4 says handheld beside a handheld clip, steady beside a tripod clip, and nothing when the support is unknown;
  - the preparation digest is unchanged by the guidance.
- **Procedure:** the treatment, plan, reference and pictures-and-takes steps carry their sentences.
- **Suites:** `server/unit` and `plugin/tests` run. The plugin doesn't change; it reads the procedure and the packet from the server.

## 5. Not covered

- Whether the models follow the new lines. The take check and the operator's verdicts on the next takes will show it.
- B12, until its trial.
- The library snapshot. The library keeps its 21 Oct text, which doesn't contradict these lines.
- `server/tests` (Docker).

## 6. Release

Server 0.49.0, built on design/101 (0.48.0, committed, not deployed). The two can deploy together on SK's word. Not committed or deployed until SK says so.

## As built (26 Oct 2026)

Server 0.49.0 (on 0.48.0), plugin unchanged. Not committed or deployed.

**What changed:**
- **B3:** a fixed line in `motion_text`, after the motion and its ambient line.
- **Packet:** `shot_guidance(shot, neighbours)` writes `context.guidance`:
  - B1 is left out on a close-up;
  - every line is left out on a graphic;
  - B4 is given only on a video shot whose neighbours' support is known.
- **Procedure:** steps 1 to 4 end with their sentences (B11; B8, B9; B5, B7; B6).

**Tests:** `server/unit` 425 passed, 6 of them new in `test_design102_pure.py`. `plugin/tests` 267 passed, with the 3 known Windows-only failures. A test confirms the guidance leaves the preparation digest unchanged.
