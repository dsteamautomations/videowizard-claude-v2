# 182 — Integration step E: planning, the redo ladder, the film and the editor's package

12 Nov 2026. Built on SK's word (the approved requirements, `videobuilder-v4/integration/requirements.md`, Step E), unit tests only, not deployed.

## What changed

### The plan check, for an AI video shot (`visual_contract.py`)

- **The limits are the guide take's, stated once** (`video_generators.GUIDE`, lengths in `guide_spec`): a take is 3 to 15 s (SK, 10 Nov; was 10). A shot over 15 s is refused: split it.
- **A shot may be a short cut**: at least 1 s on screen (was 2). Several short shots, each with its own guide, still and take, are how one planned action is cut (SK's rule of 10 Nov: after a failed second try, cut shots).
- **One still per AI video shot** in the count of pictures; no end picture, no start shared with the shot before.
- **At most four people** in one AI video shot (a default, not a proven limit); a crowd is not yet available.
- **A camera that circles a person is refused.**
- **`recipe`** is a field of the shot (`walker`, `one_action_close`, `transfer_close`); any other word is refused. A transfer is a close shot (MCU, CU or ECU) and ends in the hand, never set down.
- **No forced small move**: a living thing that stays put from start to end is accepted (the method's rule 9; was refused).
- **Warnings no longer raised for AI video**: the ambient line (`ambient_missing`), more people in a busy scene (`life_missing`), a look as the only change (`look_only`), three shots at one size (`size_repeat`), a close shot not seen wider (`size_close_first`). They stay for every other route.

### When a take is wrong (`guide.py`)

- **The cause, before another take is paid for** (`vw guide cause`): the still, the guide, the words, or none of these. Asked in order: the words are never the cause when the take's first frame did not match the still.
- **The ladder** (SK, 10 Nov): a cause that can be named gets one more take with one thing changed. After two rejected takes from one camera, or a fault with no nameable cause, a third try is refused with the ways forward: cut the shot, another angle, or leave it out. A new camera in the scene is a new start. A clip that was never a take (the guide came back unedited) is not counted.

### The film and the editor's package (`stage3/`)

- **A take's in point** is chosen when it is selected (`select --in-s`; with none, the slot sits in the middle of a guide take), kept on the selection, recorded with the gap, and used by the early package (made before the assembly) and as the assembly's default start. Before: every take was placed from its first frame, and a start chosen later never reached the editor.
- **The offset's unit fault is fixed**: it is chosen and checked in film frames and now becomes the take's own frames once, at the render (it was used unconverted: late by a frame or two in a 24-frame take).
- **An AI take is declared without sound** in the timeline, and the package notes say so.
- **The final bundle also ships the raw take** (`Media/AI/Raw/`), beside the trimmed piece.
- **A take at another frame rate than the film** is said to the operator on its fill (`rate_note`).
- The editor's notes: a slow walk may be sped up to 1.15 times, never above 1.2; grain light or none (the editor's table said "fine grain to match"); a small lettering error is patched frame by frame.
- The six-frame cross-fade between two takes needed the first take's end picture; a guide take has none, so it no longer happens. Its code goes in step F.

### The treatment and the instructions

- The treatment record carries `rerun_allowance_inr` (30 % of the AI video seconds at the take's price), shown beside the estimate.
- The assistant's visuals instructions (`scripts/d181_wording_v3.py`, chained in `c1_split_v3.py`): an AI video shot is made from a guide; a take is 3 to 15 s; a shot may be a short cut; one still per shot; the three kinds and what is not yet available; the takes are paid for only on the operator's word; the cause and the ladder. The older take's passages (bind, packet, start and end image, prepare-take, take) are gone. 10,916 words before, 10,613 after.
- `plugin/commands/vw.md` names the new commands.

## Tests

New: `test_step_e_film_pure.py` (9), `test_step_e_plan_pure.py` (8), seven ladder tests in `test_guide_route_pure.py`, one in the plugin. Thirteen older tests asserted the changed rules; each is updated in place and marked "integration step E" with what it asserted before. Server unit suite 1,459 passed; plugin 470 passed and the same 4 Windows-only faults.

## Not covered

- **The plan does not refuse a missing `recipe`, a second activity by one person, or a second changing thing.** They are caught when the scene is written (the scene names its recipe; the checks before spend). Making them plan refusals breaks several hundred existing test plans; it belongs with the deletion of the older way's tests in step F.
- **The size rules have thinner test cover for stills**: the older tests used AI video shots as their examples, and now assert that those shots are not warned.
- The warnings `cut_off_pause`, `message_repeated`, `state_changed` and the look-alike report still fire on AI video shots.
- No warning yet for an action of 9 s or more (it is in the instructions only): a new warning kind would touch 28 test modules that use long shots.
- The treatment's estimate still prices an AI video shot's still at the film's own picture price, not GPT image's; the re-run allowance is a separate line, not part of the estimate.
- The lens, the camera position, the pace and the hand are in the scene description, not the plan; the plan carries only the kind of shot.
- Nothing here has run on the server; the page was not tested (SK: unit tests only until the end).
