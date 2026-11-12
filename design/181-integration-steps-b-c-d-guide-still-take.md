# 181 — Integration steps B, C and D: the guide, the still, the take

12 Nov 2026. Approved by SK ("Yes, build"), built as one piece on his word, unit tests only, not deployed (the integration is deployed once, at its end).
Requirements: `videobuilder-v4/integration/requirements.md`, Steps B, C and D. The flow in plain words, for the consultant: `videobuilder-v4/integration/guide-flow.md`.

## What an AI video shot is now

1. A helper writes a **scene description** (data, never code): the set as boxes in metres, box people with their paths and the acting hand's points, props, the camera, the sun, the one action's seconds, the recipe and a real-process note.
2. The server checks it **before anything is rendered or paid** (`app/guide_spec.py`, plain arithmetic): support, reach, the right hand, clashes, speed, crossing paths, the first frame; warnings for the rules on trial.
3. The server's Blender renders **three check frames**. A **fresh checker** gives a verdict; the server counts the rounds. A pass queues the **render**: every frame at the fastest setting in chunks (the job's claim renewed between them), the first frame again at full quality.
4. The **still**: GPT image 2.6 on every film; Image 1 is the guide's first frame; then approved pictures, each with its job; the layout numbers and the people count are written by the server from the scene.
5. The **overlay** (the guide's edges in red over the still) is made by the server; the operator approves the exact file on it, or it is repaired by a masked edit, or rejected.
6. The **take's words** are kept as a draft; what the tests showed to fail is refused by name.
7. **Shoot**, on the operator's word only: one Gemini Omni 1.2 edit of the guide (the guide uploaded, then the guide, the still and the words, the length in the request). The same request is never sent twice.
8. The returned clip is **checked in code** (real footage, as long as the guide, first frame against the still); a clip that fails is not a take. Then the reading, the contact sheet, the first-frame pair and the **scorecard** of eight lines with one thing to watch.
9. Selecting: a blocked clip cannot be selected; a failed scorecard line or an unread take needs the operator's written reason. Every step is an entry in the shot's record of generations (design/180); a verdict closes the attempt.

## Where it lives

| File | What |
|---|---|
| `server/app/guide_spec.py` | The scene description: its shape, where everything is at a moment, the camera, the checks, the layout numbers. Standard library only; Blender imports it |
| `server/blender/guide_scene.py` | The one script Blender runs: builds the scene from the description, renders the asked frames |
| `server/app/guide.py` | The server steps both front ends call: `set_scene`, `verdict`, `request_still`, `approve_still`, `reject_still`, `set_prompt`, `shoot`, `status`, `file`, `view` |
| `server/app/guide_worker.py` | Blender calls, the strip, the overlay, the blocking checks, the sheets, the scorecard; its own `tick` in the worker loop |
| `server/app/video_providers.py` | `Provider.upload` (Files API on the take's own key) and the guide branch of `build` |
| `server/app/image_check.py` | `GUIDE_TAKE_LINES`: the reading lines of a guide take |
| `server/app/video_generators.py` | `GUIDE` and `STILL`: the models and limits, stated once (the lengths with the scene description) |
| `server/app/main.py`, `web.py`, `templates/visuals.html` | Nine routes under `/visuals/guide/`, three page actions, the guide box on a shot's card |
| `plugin/scripts/vw.py` | `vw guide scene|status|frames|verdict|still|look|repair|approve|reject|prompt|shoot` |
| `plugin/skills/guide`, `plugin/agents/vw-guide-scene.md`, `vw-guide-check.md` | The instruction, the builder, the fresh checker; the guard lets them through |

Jobs: provider `guide` (check frames and renders, free, one at a time), `guide-still` (the picture, counted in the film's spend), and the take as an ordinary `video` job with a `kind: guide` snapshot, so the journal, the single submit, the polling and the review are the existing ones.

## Older ways (design/35)

- 38: the picture-to-video take (`vw visuals prepare-take`, `vw visuals take`): retired, refused by name with the new command.
- 39: a start picture composed from words for an AI video shot (`vw visuals image --kind keyframe --shot <video shot>`): retired, refused by name.

Their code (`prepare_take`, `submit_take`, the end image, the motion text, the pair check) is still in the files, unreachable for an AI video shot; it is deleted with its tests in step F, when nothing else reads it.

## Tests

Server: `test_guide_spec_pure.py` (47), `test_guide_route_pure.py` (44), `test_guide_worker_pure.py` (19). Plugin: `test_guide_cli.py` (11). The whole server unit suite: 1,435 passed. The plugin suite: 469 passed, and the same 4 Windows-only faults as on every commit.

Tried by hand on the VM (no deployment, nothing restarted): the Blender script built and rendered two test scenes as the service user (a walk with three people; a close shot with an arm and a held prop), about 4 s a frame.

## Not covered

- **Nothing here has run on the server as the application.** No real guide job, still or take has been made by this code; Blender, GPT image and Gemini are faked in every test. The first real ones are made after the one deployment.
- The thresholds are starting values: the clip against its guide (4 %), the first frame against the still (3 % shift, 3 % zoom), the length (0.6 s).
- The page's guide box was written without the page test suite (SK: unit tests only); it runs with all suites at the end.
- The assistant's instructions (the visuals procedure text) still describe the older take; the refusals name the new command and the `vw:guide` skill holds the new flow. The procedure text is rewritten with the planning changes (step E).
- The plan check and the treatment still follow the older rules (step E): a guide must be at least as long as its slot, so a shot cannot yet be made as several cuts.
- The still has no automatic reading of its own; the operator judges it on the overlay. The masked repair's region is one rectangle.
- Marks (ground band, side stripes) are a switch in the scene; the comparison on the first shot is made on the first film.
- Depth of field, motion blur, jointed arms, lanes: not built; no recipe of the three needs them.
- `server/tests` (they need Docker) were not run.
