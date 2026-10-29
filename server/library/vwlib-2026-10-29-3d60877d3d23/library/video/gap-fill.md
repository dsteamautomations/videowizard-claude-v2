# Gap fill: AI clips that sit between real footage

Version 0.1, written 2026-10-21 for VideoWizard. Status: **draft, untested.** Read it with `playbooks/video-frame.md` (keyframe, first-last-frame), `playbooks/video-clip.md` (clip-from-frame) and the video model's fact sheet.

## 1. What this covers

A film cut from a client's real footage has gaps that AI frames and clips fill. A gap fill is judged by its neighbours: the viewer sees real shot, AI shot, real shot. The AI shot must look as if it came from the same camera on the same day, unless the film deliberately changes medium (a diagram, for example). This note covers the look match and the boundary-frame method.

## 2. Read the neighbours first

Before writing a frame prompt, look at the last frame of the real shot before the gap and the first frame of the real shot after it. Write one line on each of:

| Property | What to note | How it goes into the prompt |
| --- | --- | --- |
| Grade | Warm or cool, contrast, saturation, black level | "warm daylight grade, medium contrast, slightly lifted blacks" |
| Light | Time of day, sun or overcast, key direction | "overcast late morning, soft light from frame-left" |
| Grain and sharpness | Phone-clean, compressed, grainy, soft | "fine digital noise, slightly soft, phone camera" |
| Lens | Wide or tight, depth of field | "wide phone lens, deep focus" |
| Camera behaviour | Locked off, handheld, gimbal | Nothing: the take is locked off unless the shot's `camera_move` names its one move; the server writes the Camera line |
| Motion blur | Present on movement or not | "natural motion blur on fast hand movement" (clip prompt) |
| Place and people | Site, materials, clothing | from the run's world rules and reference sheets |

Write these as plain facts. "Cinematic" and "high quality" make the AI shot look less like the real one.

## 3. The boundary-frame method

When the gap continues the same action or place as its neighbours:

1. Grab the last frame of the real shot before the gap. Use it as the reference for the gap's start image (a place or an object), or as the start image itself.
2. An end image only where the final state must be exact: write it with the start as `end_prompt`, an edit inside one region of the start, same framing, no camera move. The server makes it after the operator approves the start.
3. Generate the clip from the start, with a motion brief that describes only what the subjects and the surroundings do (playbook video-clip, section 4; VW-MAP for the lines the server writes).

In VideoWizard: `vw visuals frame --element E --clip <id> --at <seconds>` grabs the frame (free). The frame is approved like any reference. Then `prepare-take --start R1`.

## 4. Cautions

- **Size and aspect.** Real footage is often 1080p; the video models work at their own sizes and aspects (fact sheets, section A5). A frame used as the start image is resized by the model. Check that nothing important sits at an edge that may be cropped.
- **Real people.** A footage or web picture of a person is never sent to the picture AI: the person's sheet is made from words, describing the person from their footage pictures (VW-MAP). Recognisable people may also be blocked on the video model (Omni A5).
- **Exact continuity is not guaranteed.** The first frame of the AI clip will be close to the boundary frame, not identical. The editor cuts on it as a normal cut, or uses a short dissolve. Never promise an invisible join.
- **Not every gap is a continuation.** When the narration moves to a new idea, a clean cut to a different picture is better than forcing continuity. Use the method only where the action or place carries over.

## 5. Checklist lines

- Grade, light and grain match the neighbouring real shots, compared side by side. must.
- Place, materials and clothing agree with the neighbours and the world rules. must.
- With the boundary-frame method, the clip's first frame is recognisably the boundary frame. must.
- No picture of a real person sent to the picture AI. must.
- The camera is steady: locked off, or the one move the shot's `camera_move` names. must.

## 6. Evidence

None yet. Record each gap fill's verdict in the feedback log with the neighbour shots named.

## 7. Built from

`playbooks/video-frame.md` (first-last-frame), `playbooks/video-clip.md` sections 4 and 8; `video/craft/camera-lighting-vocabulary.md`; `00-method/de-slop.md`; RULEBOOK rules 11 and 14; the VideoWizard visuals prompt (continuity with the real footage on both sides of a gap).
