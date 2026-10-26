# design/103 — Release 5: the plan learns light, air, size, shot size and the camera's reason (course batch A; design/93 G1, G2)

26 Oct 2026. Course handover batch A (`course-review/HANDOVER-course-learnings-for-builder.md`, section 2) and design/93 G1 and G2, as planned for Release 5. **Nothing is built until SK approves this note.**

## 1. How it stays simple and breaks nothing

- **Warnings, never refusals.** Every new field has a default, so every plan valid today stays valid. Every new rule is a warning in this release, as design/89 C4 did. The handover asked for this, and VW-7 is mid-run.
- **No re-acceptance, and no take goes stale.** design/101 left the ambient line out of the gap's and the take's fingerprints. The new fields here (`light`, `air`, `size`, `camera_reason`, `claim`, an element's `size`) are left out the same way. A run that adds them doesn't re-accept, re-bind or regenerate anything.
- **The check lines for these fields** (the light from the stated side, the light kept through a take, the air in a busy scene, the relative size) belong to Release 6 (course C5), as planned. This release only gives the plan the fields and tells the models.

## 2. What changes

| ID | Rule | Plan field | Warning (validate_plan) | Where it goes |
|---|---|---|---|---|
| A1 | **One light per scene** (C03-1): the sources against the scene's landmarks, the main one, hard or soft, colour, strength | `Scene.light` | A scene with a non-graphic shot and no light | Packet (scene); every new take gets "The light does not change: {light}."; a keyframe prompt in that scene that doesn't carry the sentence word for word gets a warning |
| A2 | **Something in the air, lit by that light** (C03-12): dust, smoke, haze, steam, or "clean" in a lab; matched to the footage when there is any | `Scene.air` | none (a busy scene with no air comes in Release 6 as a check line) | Packet (scene); the take's ambient sentence (design/101) already carries what drifts |
| A3 | **Shot size as data** (C03-5): EWS, WS, MWS, MS, MCU, CU, ECU, the footage analysis's own words | `Shot.size` | (1) a scene's first shot is not EWS, WS or MWS; (2) three shots of one size in a row; (3) a close size (MCU, CU, ECU) of a subject not yet seen wider in the scene. A stated reveal passes (`size_reason`). | Packet (shot) |
| A4 | **The camera's reason** (C08-4): what the viewer should feel or read, and why this angle, size and move give it | `Shot.camera_reason` | A non-graphic shot with no reason | Packet (shot); the procedure's plan step gets the meaning table in one sentence ("eye level is honest, low is powerful, high is vulnerable, a slow push draws in, handheld feels raw; no angle has one fixed meaning") |
| A5 | **Real size on every asset** (C03-6): height, width, depth or length, each with its source and status (confirmed, measured, unknown), never invented | `Element.size` (a list of the existing `Dimension`) | A person, object, animal or material with no size (a place is optional; a process or graphic doesn't need one) | Packet (elements); the reference step's text says to fill it from the client's material, `measure` on footage frames, or a maker's sheet; the References step on the page shows the element's sizes |
| A6 | **Non-speaking angles for speakers** (C08-3) | — | — | The procedure's plan step: when footage shows a person speaking to camera, offer non-speaking angles of them (listening, hands at work, profile, from behind), footage first |
| A7 | **The film's look without footage** (C05-9) | — | — | The procedure's treatment step: when a gap has no real footage beside it, the treatment proposes its look (palette, contrast, saturation, muted and true to life by default); the operator approves it with the treatment. The look picture and its binding wait for the first fully-AI film (handover 1a). |
| G1 | **Graphic seconds in a row** (design/93): graphics back to back inside a gap | — | above 8 s; above 12 s the warning says it will be refused from the next release | `validate_plan` |
| G2 | **Claims about real things prefer real pictures** (design/93, with design/64 A.3) | `Shot.claim` ('', 'visible', 'invisible') | a `visible` claim on a graphic route | `validate_plan` |

**On the page:**
- The shot's facts show its size, its camera reason, and its scene's light and air.
- The References step shows each element's sizes.

## 3. Left out, and why (keeping it simple)

- **A3's footage sizes.** The rules read the plan's own shots. Reading the real clips' sizes into the sequence (handover rules 1 and 5), and the one-step rule (4), come later if the warnings prove useful.
- **A5's drawings reading sizes, and the scale reference.** The scale reference is D3, in Release 6. A drawing's numbers already come from its approved drawing spec (design/89 D4).
- **A6's warning.** It needs speaker clips detected in the footage. For now the rule is procedure text only.
- **G1 across gaps.** Gaps are separated by footage, so graphics in a row are counted inside a gap only.

## 4. Runs in progress

Plans keep working unchanged. A run that revises its plan to add the fields:
- gets the new warnings until each field is filled;
- re-accepts nothing;
- keeps its ready takes selectable.

## 5. Tests first

- **Schema:** each field defaults to empty, an old plan passes unchanged, and an absent field stays absent.
- **Warnings:** each fires and each clears. A1 (no light). A3: rule 1, rule 2, rule 3, and a reveal passing. A4 (no reason). A5: a person with no size warns, a place doesn't. G1: 5 + 4 s warns, 4 + 3 s doesn't, a footage shot between resets the count, and above 12 s the warning names the next release. G2 (a visible claim on a graphic).
- **Fingerprints:** a plan with the new fields gives the same gap digest and the same preparation digest as without them.
- **Take text:** "The light does not change: …" once when the scene has a light, and nothing otherwise.
- **Keyframe prompt:** a prompt without the scene's light sentence gets the warning.
- **Procedure:** the A4, A6 and A7 sentences.
- **Page:** the size, reason, light, air and element sizes show, the script parses, and a browser check runs on a local copy with VW-7's data.
- **Suites:** `server/unit` and `plugin/tests`. The plugin doesn't change: the assistant's plan schema comes from the server.

## 6. Not covered

- Whether the models follow the light sentence. Release 6's check lines measure it.
- `server/tests` (Docker).

## 7. Release

Server 0.50.0 (on 0.49.0). Not committed or deployed until SK says so.

## As built (26 Oct 2026)

Server 0.50.0 (on 0.49.0), plugin unchanged. Not committed or deployed.

**What changed:**
- **Fields:**
  - `Scene.light`, `Scene.air`;
  - `Shot.size` (EWS to ECU), `Shot.size_reason`, `Shot.camera_reason`, `Shot.claim`;
  - `Element.size` (a list of `Dimension`).

  Absent stays absent in the stored plan.
- **Warnings:** `validate_plan` → `course_warnings` gives `light_missing`, `camera_reason_missing`, `element_size_missing`, `size_open`, `size_repeat`, `size_close_first`, `graphics_run` (above 8 s; above 12 s it names the next release) and `claim_visible_graphic`.
- **Fingerprints:** `note_free_gap`, `note_free_scene` and `note_free_elements` replace design/101's `without_ambient`. The new fields stay out of the gap digest and the preparation digest.
- **Takes and prompts:**
  - a new take in a lit scene gets "The light does not change: {light}." after its continuity line;
  - a keyframe prompt without its scene's light sentence gets a warning (`light_warning`).
- **Procedure:** the treatment step gets A7, the plan step A1 to A4, A6 and G2, and the reference step A5.
- **Page:** a shot's facts show its size, camera reason, light and air, and the References step shows each element's sizes.

**Checks:**
- `server/unit`: 434 passed, 9 of them new in `test_design103_pure.py`.
- `plugin/tests`: 267 passed, with the 3 known Windows-only failures.
- **Live plans** under the new code: VW-7's and VW-9's plans validate. All 18 and all 8 of their accepted gap digests are unchanged, and all 26 and all 3 of their bindings hold. VW-7 shows 23 light, 37 camera-reason and 8 element-size warnings, and one graphics run.
- **Page:** a browser check on a local copy with VW-7's data, with sample values added, showed every line and no script error.
