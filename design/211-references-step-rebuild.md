# 211. The References step, rebuilt

17 Nov 2026. **Status: a design note. Nothing is built. No code was changed.** It is the one shared agreement of three builders who work at the same time and are merged afterwards.

SK's words: "combine everything, start the implementation, and run the trial after all the fixes." The trial is limited to 5 to 10 pictures.

Sources: `design/_work/references-step-revised-analysis-17-nov.md` (the 33 gaps), `requirement-reference-finder-17-nov.md`, `refs-review/A`, `B`, `C`, `mistakes-and-learnings-treatment-plan-17-nov.md`, and the code named in section 3.

---

## 1. Scope: every gap

Part A finds the footage pictures. Part B makes the sets. Part C is what the operator sees and decides.

| # | Gap | In this build |
|---|---|---|
| 1 | A model looks at every footage picture first | A |
| 2 | The analysis sub-clips are passed on | A (the digest) |
| 3 | A model's reading replaces the word match | A; the word match stays as the way back |
| 4 | One frame per view; each answered; all used | A finds them, C asks each, B uses all as inputs |
| 5 | A frame rule | A (one rule, held by the server, given to every helper) |
| 6 | "No picture" tells the truth and shows the closest | A gives the facts, C says them |
| 7 | The set is made from the footage picture | B |
| 8 | "Make a clean set from this frame" | B (the answer), C (the button) |
| 9 | The size check is repaired | B |
| 10 | All three pictures checked, against footage, plan and drawing | B |
| 11 | A clear failure is made again once by itself | **Not built.** Decision 2 below replaces it: nothing paid happens without the operator. The failure and a recommendation are shown |
| 12 | The page shows the check and the image model's notes | C, from B's data |
| 13 | The plan's views drive the three pictures | B |
| 14 | A request per kind | B |
| 15 | Each thing placed where the film uses it | B |
| 16 | The fixed text generic for every category | B |
| 17 | A person's pictures follow the plan; relative heights | B in part: picture 2 follows the plan. Relative heights: **not built** (the plan has no field for them; every height on VW-24 is "unknown") |
| 18 | Each line shows description, shots, recommendation | C, from B's facts |
| 19 | Grouping, folding, "accept the proposals" | C |
| 20 | Which things deserve a set | B (the proposal on each row), C (shown). No hard rule: Claude proposes, the operator confirms |
| 21 | Related things made together | **Not built** (decision 9): it asks what a reference is for; a talk first |
| 22 | A trial of two or three sets before the rest | B (two goes), C (the line) |
| 23 | Approved references tied to every shot | B in part: a still whose shot names a thing with an approved reference that is not among its pictures gets a warning. The AI video route: **not built** (it is another step) |
| 24 | A stated use for sets of places and ways of working | **Not built** (decision 9). These sets are still made, with their own request |
| 25 | The step-1 comment reaches the picture | B (into the request), C (the box only where a set can follow) |
| 26 | The failure text names the right cause | B |
| 27 | A partial set shown as it is | B (the facts), C (the words) |
| 28 | "No" and "Correct it": rewrite; a limit | B, C |
| 29 | "Leave it out" says what it costs | C, from B's facts |
| 30 | A second send never spends | B |
| 31 | Step 1 shows the money the shots still need | C |
| 32 | A plan changed after the sets marks the old sets | A (search again only what changed), B (the mark) |
| 33 | The page and the chat use the same words | C |

Cropping a small thing out of a frame is not built.

## 2. The new flow

| # | What happens | Who |
|---|---|---|
| 1 | The plan is accepted. The server says the references come next | Server program |
| 2 | The tool fetches the digest: for every clip, what happens in each part, with seconds | Server program |
| 3 | Claude splits the things into groups of about five and starts helpers, up to six at a time. With five things or fewer it works alone | Claude |
| 4 | Each helper reads the digest, names the likely moments, asks for small trial frames, looks at each, and records what it saw. It keeps the best frame for each view, up to three per thing. Where nothing fits it records "not found", what it searched, and the closest frame | Claude helper; the server cuts the frames |
| 5 | Claude writes the round file: for each thing a proposal with its reason. It adds words only for what the plan does not say | Claude |
| 6 | The server refuses a footage picture with no recorded look, and a thing with no search record | Server program |
| 7 | Step 1 on the page: the doubtful things first, then the rest by kind. Each line shows the plan's description, the shots that use the thing, the footage pictures with what Claude saw, and Claude's proposal. The operator answers the doubtful ones and may accept the rest in one click, with the total price | Operator |
| 8 | "Done": the first three sets are ordered. The others wait | Server program, on the operator's word |
| 9 | The server writes each request from the plan, by kind of thing, with the film's footage pictures as inputs | Server program; the image model makes the pictures |
| 10 | The server's check looks at all three pictures of each set | Gemini |
| 11 | A helper looks at all three pictures against the footage, the plan and the views asked, and records a recommendation | Claude helper |
| 12 | Step 2 on the page: the three sets, each with the footage picture beside it, both results, the image model's notes, and Claude's recommendation. One line offers "make the other sets", with the price | Operator |
| 13 | On that click the other sets are made, checked and looked at (steps 9 to 11), and judged the same way | Server program, Gemini, Claude helper, operator |
| 14 | "No" or "Correct it": Claude rewrites the request from the operator's words; the server keeps the earlier one; the set is made again. After three makes the operator is told | Operator, Claude, server program |
| 15 | Every thing is approved, taken from footage, or left out: the round is complete | Server program |

Nothing paid happens at steps 2 to 7.

---

## 3. THE CONTRACT

Names here are final. A builder who needs another name asks the master thread; nobody renames alone.

### 3.0 Rules that hold for all three parts

1. **Round version.** A round created after this change carries `session['round']['v'] == 2`. `visuals_stage.round_v2(session)` returns that. Every new behaviour is behind it. A round without `v` (VW-24) runs the code of today, unchanged, to its end. A round file sent again while an older round is at step 1 creates an older round again. Only a film with no round gets `v: 2`.
2. **New code lives in two new files.** `server/app/ref_find.py` (part A) and `server/app/ref_sets.py` (part B). `visuals_stage.py` (V below) is edited by part B only.
3. **One "what next".** For a v2 round every "what next" sentence is a constant of the server (section 3.9) and travels in the answer as `then`. The tool prints `then`; it adds no sentence of its own. For an older round the tool prints what it prints today.
4. **A refusal is a named constant.** Each refusal in this note is a module constant (a format string) with the name given. A test asserts the message equals the formatted constant.
5. **Step 0 is done** (one commit on `main`, 17 Nov 2026; the three worktrees are cut from it). It holds: the two new files with every function of this section (its signature, its docstring, `NotImplementedError`) and every "what next" and refusal constant with its text; `V.round_v2`; in `plugin/scripts/vw.py` the words `digest`, `trial`, `look` in `VISUALS_WHAT`, their entries in `VISUALS_FLAGS` (`digest: set()`, `trial: {'file','element','clip','at'}`, `look: {'file'}`), `rest`, `rewrite`, `looks` in the `round` entry, the argparse flags `--rest` (store_true), `--rewrite <file>`, `--looks [file]`, and for each new command a body that says "not built yet" and sends nothing (a builder replaces that body, nothing else of the parser); the two helper files as shells with their front matter, and their names in the guard's `VW_HELPERS`; three empty wording scripts `scripts/d211a_wording_v3.py`, `d211b_…`, `d211c_…` (`PAIRS`, `RETIRED`, `COMMANDS`, `apply(prompt, parts)`, `main()`), registered in `scripts/c1_split_v3.py` in that order; the shared fixture `server/unit/d211_fixture.py` (section 6.0); and two tests of step 0 itself (`server/unit/test_design211_step0_pure.py`, `plugin/tests/test_design211_step0.py`), which pin the names and signatures. A builder who must change a signature changes that test in the same commit and tells the master thread.
6. **Generated files are not committed by a builder:** `server/procedures/v3.json`, `plugin/commands/vw.md`, `server/retired-sentences.json`, the word-count pin, `SERVER_VERSION`, `PLUGIN_MIN_VERSION`, `plugin.json`, `design/35-decision-log.md`. The merger runs the three wording scripts once, after the merge, and commits these.

### 3.1 The digest (A)

- **Built by** `ref_find.digest(store, run, outputs) -> dict`, on request, from the same analysis outputs `V.prepare` reads (V:130-141: every `analysis` output not `excluded`, its `.evidence.json`, contract `clip-log-v1`). `V.prepare` is not changed. Clips left out of the edit are in; the operator's explicit exclusions are not.
- **Stored at** `V.key(run, 'digest.json')` (`<run id>/visuals/digest.json`). Reused while `stamp` (sha256 of the sorted `unit:evidence key` list) is unchanged.
- **Shape:**

```json
{"contract": "vw2-refs-digest-v1", "stamp": "<sha256>", "built_at": "<iso>",
 "clips": [{"clip": "<analysis unit = the media id `vw visuals frame --clip` takes>", "name": "<file name>", "duration_s": 42.1,
            "overview": "<clip_overview>", "light": "<lighting_and_weather>",
            "entities": [{"name": "", "kind": "", "first_seen_s": 0.0, "last_seen_s": 0.0, "description": "", "uncertainty": ""}],
            "parts": [{"id": "<sub_clip_id>", "in_s": 0.0, "out_s": 0.0, "hero_s": 0.0, "grade": "A|B|C|REJECT", "role": "<shot_role>",
                       "size": "<native_shot_size>", "angle": "<camera_angle>", "action": "<visual_action_observed>",
                       "uncertain": "<visual_action_uncertainty>", "props": ["<world_landmarks_and_props>"], "people": 0,
                       "defects": [{"defect": "", "in_tc": "", "out_tc": "", "description": ""}]}]}],
 "not_searched": [{"clip": "<media id>", "name": "", "reason": "no analysis"}]}
```

  `in_s`/`out_s` are `max_usable_window.in_s`/`out_s`; `hero_s` is `hero_frame_s`. `not_searched` lists every media clip with no analysis output.
- **Endpoint:** `GET /api/runs/{run_id}/visuals/digest` → `ref_find.digest_answer(store, run, outputs)`: `{'digest': <above>, 'things': [<thing>], 'rule': ref_find.FRAME_RULE, 'limits': {'trials_per_thing': 8, 'kept_per_thing': 3, 'things_per_helper': 5, 'helpers': 6}, 'then': <3.9>}`. A `<thing>` is `ref_sets.thing_facts(...)` (3.5) plus `'found': <result or None>` (3.3) for every element the round takes (not `graphic`, not `animal`).
- **Command:** `vw visuals digest`. It writes, in the run folder: `work/visuals/digest/index.json` (one row per clip: `{clip, name, duration_s, overview, entities: [names], file}`), `work/visuals/digest/clips-N.json` (the clips, 25 to a file, by the existing `rows_files(folder, 'clips', rows, cap=25)`), and `work/visuals/refs/things.json` (`{things, rule, limits}`). For long footage a helper reads the index and only the files that mention its things.
- **No digest** (`clips` empty while the run has media): `then` is `ref_find.FIND_WORDS`; the older command `vw visuals elements` gives the hints; every frame still needs a look. `ref_find.footage(store, run, outputs) -> bool` says whether the run has any analysed clip; a film with none skips the search and needs no search record.

### 3.2 Trial frames (A)

- **Endpoint:** `POST /api/runs/{run_id}/visuals/trials`, body `{frames: [{element_id, clip, at_s}]}` (1 to 8 rows). The frames are cut before the run's lock (`ref_find.cut_trials(store, run, outputs, frames)`, as `visuals_search` does with `search_rows`), one download per clip per call; they are recorded under the lock (`ref_find.trial_record(store, user, run, outputs, frames, cut)`).
- **A trial frame:** a JPEG, long side 640 px, quality 80 (`page_flow.shrink`, imported, not changed), stored at `<run id>/visuals/trials/<trial id>.jpg`. `trial id = 't' + sha1('<clip>:<at_s rounded to 0.1>')[:12]` (`ref_find.trial_id(clip, at_s)`), so the same moment asked twice, or for two things, is one frame.
- **Recorded in** `V.key(run, 'trials.json')`: `{'trials': {<trial id>: {'id', 'clip', 'at_s', 'key', 'sha256', 'elements': [eid], 'looks': {eid: <look>}, 'at', 'by'}}}`. Not in `session['references']`. **A trial frame is not a reference**: it is never approved, never an input of a picture, and reaches the operator only as the "closest" picture of a thing that was not found.
- **Returns:** `{'trials': [{'id', 'clip', 'at_s', 'key', 'elements'}], 'failed': [{'clip', 'at_s', 'reason'}], 'left': {eid: <trial frames still allowed>}, 'then': ref_find.TRIAL_NEXT}`. A moment that cannot be cut is in `failed`; the others go on.
- **Command:** `vw visuals trial --file <rows {element, clip, at}>` or `--element E --clip C --at S`. Each frame lands at `work/visuals/trials/<element>/<trial id>.jpg` (the existing `_download`).
- **Limits and refusals:** `TRIAL_TOO_MANY` (over 8 rows in a call); `TRIAL_LIMIT` (over 8 distinct trial frames for one thing; the frames of a thing whose `fingerprint` changed are dropped first and the count starts again); `TRIAL_UNKNOWN_CLIP` (the clip is not the run's, or the time is outside it).

### 3.3 The look record and the search record (A)

**A look** (the same shape for a footage frame and for a set picture):

```json
{"who": "helper|assistant", "at": "<iso>", "view": "<view name>", "verdict": "pass|weak|fail", "seen": "<one line, at most 300 characters>",
 "trial": "<trial id or null>", "ref": "<reference id or null>"}
```

For a frame, `trial` is set and `ref` is set once the frame is kept. For a set picture, `ref` is the picture's reference id and `trial` is null.

- **Endpoint:** `POST /api/runs/{run_id}/visuals/looks`, body:

```json
{"by": "helper|assistant",
 "things": [{"element": "PAN", "clips": ["<clip ids searched>"], "note": "<one line>", "not_searched": "<reason, or absent>",
             "looks": [{"trial": "<id>", "view": "side", "verdict": "pass|weak|fail", "seen": "…", "keep": true, "closest": false}]}]}
```

  Function: `ref_find.look_record(conn, store, user, run, outputs, things, by) -> dict`. For each `keep` row it makes the full-size frame through the existing `V.add_reference` (kind `frame`, the trial's clip and second, a request id made from run, element and trial) and writes on that reference the new fields of 3.4.
- **The search record,** one per thing, in `session['found'][eid]`: `{'result': 'found|weak|none|not_searched', 'by', 'at', 'fingerprint', 'clips': [ids], 'note', 'kept': [reference ids, in view order], 'closest': <trial id or None>}`. The **server** decides `result`: a kept frame with `pass` → `found`; kept frames all `weak` → `weak`; no kept frame → `none`; `not_searched` given → `not_searched`. `closest` is the row marked `closest` (at most one, only when nothing is kept).
- **Returns:** `{'recorded': [eid], 'refused': {eid: message}, 'results': {eid: result}, 'kept': {eid: [reference ids]}, 'left': [eids of the plan with no search record], 'then': ref_find.LOOK_MORE or LOOK_ALL}`.
- **Command:** `vw visuals look --file <file>`.
- **Refusals** (the whole thing's row is refused, the other things are recorded): `LOOK_UNKNOWN_TRIAL` (no such trial frame was taken for this thing: a look is recorded only for a frame that was fetched); `LOOK_VERDICT`; `LOOK_SEEN` (empty or over 300 characters); `LOOK_VIEW` (a kept frame names no view); `KEEP_FAIL` (a frame with `fail` cannot be kept); `KEEP_LIMIT` (over 3 kept for a thing, or two for one view); `LOOK_NOTHING` (no look, no clip and no `not_searched` reason).
- **Where the server refuses to show a frame.** `ref_find.round_frames(session, plan, eid, named) -> [reference ids]` is called by `V.round_start` for every row of a v2 round. It returns the thing's frames that have a look, in view order, and refuses: `FRAME_NO_LOOK` (a named frame has no look) and `NOT_SEARCHED` (the run has footage and the thing has no search record). Both front ends go through `round_start`, so no frame reaches the operator without a look.
- **For part C and part B to read:**
  - `ref_find.frames_of(session, eid) -> [{'ref', 'view', 'verdict', 'seen', 'weak'}]`: the looked frames that are `candidate` or `approved`, in view order.
  - `ref_find.found_all(store, run, session, plan) -> {eid: {'result', 'by', 'at', 'clips': <count>, 'clip_names': [first five], 'not_searched': [clip names of the digest's list], 'note', 'closest': {'trial', 'key', 'view', 'seen'} or None, 'stale': bool}}`. `stale`: the thing's `fingerprint` differs from the one searched.
  - `ref_find.fingerprint(element) -> str`: sha256 of `name, kind, identity, description, requirements, required_views, size`.
  - `ref_find.not_this(conn, store, user, run, outputs, eid, ref_id, quote) -> {'next': <reference id or None>}`: the frame is rejected with the operator's words; the best other looked trial frame of the same view (`pass` before `weak`, never `fail`) is kept in its place, without a new search.
  - `ref_find.that_is_it(conn, store, user, run, outputs, eid, trial_id, quote) -> {'ref': <reference id>}`: the "closest" frame becomes a kept frame, `weak`, on the operator's word.

### 3.4 The frame as a reference; the answers to a footage picture

New fields on a `frame` reference of a v2 round (`session['references'][fid]`): `view` (str), `look` (a look), `weak` (bool), `trial` (trial id). The search record (`session['found']`) holds what was searched; it is per thing, not per picture.

The golden picture of a thing taken from footage is the first kept frame in view order (today: `approved[0]`, which has no order).

Step-1 answers (the stored answer of a thing, `session['chat_round'][eid]`, gains `words` and `pics`):

| Answer | `choice` | Level | What the server does |
|---|---|---|---|
| Use it as the reference | `approve` | the line | Free. The frames not marked "not" are approved; no set |
| Make a clean set from it (paid) | `clean` | the line | A set is made from those frames (3.6). Refused without a looked frame: `CLEAN_NO_FRAME` |
| Have a set made (paid) | `approve` | the line, when the thing has no frame, or is a person, or has approved drawings | As today |
| Leave it out / No set needed | `ignore` | the line | As today |
| Not this picture | `pics: {<reference id>: 'not'}` | one picture | `ref_find.not_this`; the line comes back with the next best, or with "none was found" |
| That is it | `pics: {<trial id>: 'use'}` | the closest picture | `ref_find.that_is_it`; the line comes back with it as a footage picture |

An answer that only holds `pics` has `choice: 'pics'` and leaves the line open. A person who is shown in a made picture has no "Leave it out".

### 3.5 The element row of a v2 round; the proposal (B)

The round file (`out/reference-round.json`), one row per thing: `{element_id, rec, reason, doubt?, first?, prompt?, frames?}`.

- `rec`: `footage` (use the footage picture) · `clean` (a clean set from it) · `set` (have a set made) · `no_set` (no set needed: its words carry it) · `leave` (leave it out).
- `reason`: one line, required, at most 300 characters.
- `prompt`: only what the plan does not say. It may be empty. The older `HOW_WORDS` refusal is not applied.
- `first`: true on up to three rows: the sets made in the first go.

`V.round_start` stores per thing (`session['round']['elements'][eid]`); existing fields keep their meaning:

| Field | Meaning |
|---|---|
| `frames` | from `ref_find.round_frames` |
| `prompt` | the assistant's added words, may be `''` |
| `rec`, `reason` | the proposal |
| `doubt` | true when the row says so, or a kept frame is `weak`, or the result is `none` with a closest picture, or `not_searched`, or the thing is `identity: exact` with `rec` not `footage`/`clean`, or a cause stands (`V.set_cause`) |
| `first` | bool |
| `clean` | the step-1 answer was `clean` |
| `operator_words` | list: the step-1 comment, then the words of each "No" or "Correct it"; the latest goes into the request |
| `round` | (existing) how many times the set was made: the makes count |
| `rewrite_due` | `{'words', 'set', 'at'}` while a remake waits for Claude's rewrite |
| `history` | `[{'n', 'set', 'added', 'operator', 'at'}]`: each earlier request |
| `parts` | the request parts of the last make (3.6) |
| `set_look` | `{'who', 'at', 'set', 'recommend': 'use|remake|doubt', 'golden': <reference id or None>, 'reason'}` |
| `reopened` | `'new'` or `'left_out'`: back with the operator after a second send |
| `made` | (existing) gains `'fp'`: `ref_find.fingerprint` plus the place used |

Round level: `v: 2`, `go` (1 or 2), `rest` (the things whose set waits for the second go).

Refusals of `round_start` (every faulty row in one answer, not the first only): `REC_MISSING`, `REC_UNKNOWN`, `REC_NO_FRAME` (`footage` or `clean` without a looked frame), `REC_PERSON` (a person shown in a made picture: `set`), `REASON_MISSING`, `FIRST_TOO_MANY`, and A's `FRAME_NO_LOOK`, `NOT_SEARCHED`.

`rec` to the step-1 answer, for "Accept the proposals": `footage → approve`, `clean → clean`, `set → approve`, `no_set → ignore`, `leave → ignore`.

**Facts of a thing**, for A's `things.json`, B's request and C's lines: `ref_sets.thing_facts(plan, session, element) ->`

```json
{"id": "", "name": "", "kind": "", "identity": "exact|representative", "real_person": false,
 "description": "", "requirements": "", "sizes": [{"part": "", "measure": "", "value": null, "unit": "", "status": ""}],
 "views": ["", "", ""], "signs": [""],
 "shots": [{"gap": "", "shot": "", "size": "CU", "way": "image|video|footage|…"}], "shots_made": 0, "closest": "CU",
 "scene": {"gap": "", "scene": "", "place": "<location_time>"}}
```

`shots`: every shot of `all_scenes(gap)` that names the thing, in the film's order. `shots_made`: those not `footage`. `closest`: the tightest `size` among them. `scene`: the scene of its first shot (None when no shot names it).

### 3.6 The set request (B)

`ref_sets.set_request(plan, run, session, element, row) ->`

```json
{"prompt": "<the full text>", "views": [{"name": "<short label>", "ask": "<the sentence of that turn>"}],
 "inputs": [{"ref": "<reference id>", "role": "footage|drawing|photo", "view": ""}], "search": true,
 "lines": [{"check": "", "weight": "must", "pass_when": ""}], "parts": {…}}
```

`V.generate_image` calls it for a set of a v2 round (the branch at V:3741-3753) and sends `prompt`, the inputs as parents in that order, `views` (the `ask` sentences), `view_names` (the `name` labels) and `search`. The worker writes `view` on each of the three pictures. For a v2 set the generic "Sizes:" line (V:3954-3958) is not added again.

`parts` (each placed by the server; stored on the row; shown by C on request):

| Key | From |
|---|---|
| `kind`, `subject` | the element's kind and name |
| `description`, `requirements` | the plan, word for word |
| `sizes` | the plan's sizes with their status: `confirmed` and `measured` as numbers, `proposed` as "about …", `unknown` left out |
| `material` | `V.material_sentence` of an approved spec |
| `signs` | a place's first two `signs_of_use`, unless `staged_clean` |
| `place` | the scene of its first shot; a place's own description for a place; never the film's first scene |
| `look`, `category` | `foundation.appearance`; `V.category_of(run)` |
| `added` | the row's `prompt` (Claude's words; where they differ from the description, the request says they win) |
| `operator` | the latest of `operator_words`, as "The operator's words: …" |
| `views`, `inputs`, `source` | the three views; the inputs; `footage` or `web` |

**Inputs.** The thing's approved footage frames not marked "not" (up to 3, view order), then its approved drawings, as today. A person: their photo, only with the recorded permission, as today. With a footage input the request says the film's own picture wins over any web photograph and the web serves only what the frame does not show; a `weak` frame is named as such ("take its form, colour and material; show it whole and clean"). With no footage input the request says the set is made from web photographs because the film shows none. Search stays on in both cases.

**Views.** `ref_sets.views_for(element, plan) -> [{'name', 'ask'}]`, always three; `ref_sets.view_names(element) -> [str]`. The plan's `required_views` come first (two that read the same are one); the kind's own views fill the rest, never one already present:

| Kind | Views where the plan names none | May show | Setting and light |
|---|---|---|---|
| person | 1 full-length front, at ease · 2 the plan's first view, else full-length from the side, at ease · 3 the face | the person alone | plain ground. Pictures 1 and 3 are fixed: later steps read them by position |
| object, material | whole and at rest · as the film uses it · the detail that shows how it is made | no person; a hand only in the "in use" view | its scene's place as a soft hint; the scene's light |
| place | the whole place · from the other side · its fixed things | no person as the subject | the place is the subject; its own light and time |
| technique, process | the action at its key moment · the result just after · the tool meeting the material | hands and forearms; no face | its scene's place; the scene's light |

The fixed text is generic: no "site", no "trade", no "how the work is done", no "natural daylight". It keeps the two ideas of SK's text of 4 Nov: a reference must be correct, and it shows one consistent real thing, never a mix of two.

### 3.7 The checks (B)

- **Repair.** `image_check.code_checks`: when the request's size is a record (`{'aspect', 'tier'}`, every Gemini picture), the line passes when the picture's width over height is within 2 % of the aspect; `pass_when` says "the picture is 16:9". A string size is compared as today.
- **All three.** `visual_workers.finalize_image` marks each picture of a set `check_pending` with the set's lines; `check_image` checks each picture (one Gemini call each). Each picture gets its own `check`, in today's shape: `{'code': [...], 'lines': [{'check', 'weight', 'pass', 'seen'}], 'must_failed': [...], 'model', 'error'?}`. This holds for every set made after the release, of an older round too (stored, not shown there).
- **The lines of a v2 set** (`set_request(...)['lines']`), all `must`:

| Line | Kinds | Passes when |
|---|---|---|
| `the view` | all | the picture shows what its turn asked (the `ask` sentence) |
| `same as picture 1` | all, pictures 2 and 3 | the same thing as picture 1 in every detail both show (picture 1 is sent with it) |
| `matches the footage picture` | when a footage picture was an input | the form, colour and material of the footage picture |
| `matches the description` | all | it agrees with the plan's description |
| `drawn fact: …`, `a photograph, not a drawing` | when drawings were inputs | as today |
| `one thing only` | object, material, technique, process | nothing of a second variant is mixed in |
| `nothing floats` | all but person | nothing stands where it could not really stand |
| `no text` | all | no caption, number, label, logo or watermark |
| `no person` | object, material | no person and no face; a hand only in the "in use" view |
| `the place is the subject` | place | the place as its view asks, not one object of it |
| `the action is shown` | technique, process | hands and the tool doing it; no face |
| `one person`, `plain ground` | person | as today |

  The fixed line `a real face` is left out for a person's set made from their own permitted photo.
- **For part C:** `ref_sets.set_facts(session, plan, eid, row) ->`

```json
{"pictures": [{"ref": "", "n": 1, "view": "", "check": {"state": "pass|fail|none", "failed": [{"check": "", "seen": ""}], "error": null}, "look": {…}}],
 "inputs": [{"ref": "", "role": "", "view": ""}], "from": "footage|web",
 "notes": "<the image model's notes>", "sources": [{"url": "", "title": ""}],
 "partial": {"made": 2, "asked": 3, "missing": ["the face"]},
 "rec": {"do": "use|remake|doubt", "golden": "<ref or null>", "reason": ""},
 "makes": 1, "makes_left": 2, "asked": "<the operator's words of the last remake, or null>",
 "history": [{"n": 1, "set": "", "added": "", "operator": ""}], "changed": false,
 "fail": {"cause": "refused|no_picture|timeout|limit|other", "model": "<the model's own id>", "text": "<one plain sentence naming the provider, the model and the cause>"}}
```

  `partial`, `rec`, `asked` and `fail` are null when they do not apply. `changed`: the plan's fields of this thing changed since the set was made (`made.fp`), or its spec or photo did (today's `_spec_changed`).

### 3.8 The two goes, the looks at a set, the remake (B)

**States of a v2 round** (`V._round_pass(session, rd)`; the stored `rd['pass']` keeps today's four values):

| State | Meaning | Whose turn |
|---|---|---|
| `1` | step 1 is open | operator |
| `'making'` | a set is being made | nobody: wait |
| `'looking'` | no set is being made; a made set has no complete look | Claude (helpers) |
| `'rewrite'` | none of the above; a row has `rewrite_due` | Claude |
| `2` | sets wait for the operator, or `rest` is not empty | operator |
| `'complete'` | every thing approved, from footage or left out, and `rest` empty | |

**Where the server refuses to show a set.** In `'looking'` the functions both front ends call get no set to show. `V.round_sets` and `V.set_answer` also refuse an answer to a set with no complete look: `SET_NO_LOOK`. A look is complete when the row's `set_look.set` is the row's set and each of its pictures has a look.

| Pass | Function | Endpoint | Command |
|---|---|---|---|
| Send the round | `V.round_start` | `POST …/visuals/round` | `vw visuals round --file out/reference-round.json` |
| Step 1 recorded: the first go | `V.round_done(…, verdicts)`; a verdict is `{'verdict': 'approve|clean|ignore', 'words'}` | `POST …/round/done` | the page; `vw visuals round --verdicts <file> --quote` |
| The sets to look at | `ref_sets.looks_due(store, run, outputs)` | `GET …/visuals/round/looks` | `vw visuals round --looks` |
| The looks recorded | `ref_sets.round_looks(store, user, run, outputs, sets, by)` | `POST …/visuals/round/looks` | `vw visuals round --looks <file>` |
| The second go | `ref_sets.round_rest(conn, store, user, run, outputs, quote)` | `POST …/visuals/round/rest` | the page; `vw visuals round --rest --quote "<their words>"` |
| The sets judged | `V.round_sets` | `POST …/round/sets` | the page; `vw visuals round --sets <file> --quote` |
| The rewrite sent, the remake made | `ref_sets.round_rewrite(conn, store, user, run, outputs, rows)` | `POST …/visuals/round/rewrite` | `vw visuals round --rewrite out/round-rewrites.json` |
| A thing back after a second send, answered | `ref_sets.round_reopen(conn, store, user, run, outputs, eid, verdict, words, quote)` | (through the page and the chat only) | |

- **The first go.** `round_done` orders the sets of the rows marked `first` that the answers still ask for; with fewer than three it adds the first row of each other kind, in the plan's order, up to three. The others go to `rest`. With three sets or fewer in all there is no second go.
- **`looks_due`** returns `{'sets': [{'element_id', 'name', 'set', 'facts': thing_facts, 'request': <the prompt sent>, 'inputs': [{'ref', 'role', 'view', 'key'}], 'pictures': [{'ref', 'n', 'view', 'key', 'check'}], 'notes'}], 'then'}`; the keys are the 1600 px copies (`page_flow.sized(store, key, 'zoom')`, imported, not changed). The tool writes `work/visuals/sets/looks.json` and the pictures under `work/visuals/sets/<element>/`.
- **`round_looks`** body: `{by, sets: [{element_id, set, recommend: 'use|remake|doubt', golden, reason, pictures: [{ref, view, verdict, seen}]}]}`. Refusals: `LOOK_SET_UNKNOWN` (not the row's set now), `LOOK_PICTURES` (a picture of the set has no look), `LOOK_VERDICT`, `LOOK_SEEN`, `LOOK_GOLDEN` (not a picture of the set). It returns `{'recorded': [eid], 'refused': {eid: message}, 'left': [eid], 'then'}`; a refused set does not stop the others. One picture's check for the page is `ref_sets.check_summary(session, ref)`.
- **`round_rest`** refusals: `REST_NOT_NOW` (the round is not at state 2 of its first go), `REST_NONE`, `REST_CAP` (the limit has no room for all of them: none is ordered, the sentence gives the figures).
- **"No" and "Correct it".** `round_sets` rejects the pictures as today, appends the words to `operator_words`, sets `rewrite_due`, and orders nothing. `round_rewrite` takes `{element_id, prompt}`, moves the earlier request to `history`, stores the new `prompt`, clears `rewrite_due` and orders the set: the operator's click was the word for the spend. Refusals: `REWRITE_NOT_DUE`, `REWRITE_EMPTY`, `REWRITE_SAME` (the same words as before would buy the same picture). `corrections` stays empty in a v2 round.
- **Three makes.** With `round >= 3` a "No" or "Correct it" is held, not recorded: `MAKES_LIMIT`. The line then offers: use one of these, your own picture, or leave it out.
- **No spend on a second send.** `V._round_merge` for a v2 round orders nothing. A thing the operator left out, or one new in the plan, gets `reopened` and goes back to the operator as an open line. A thing whose set was not made gets its new `prompt` and its error cleared, and stays "not made" with its paid button.
- **`V.set_make`** (`vw visuals round --make E`) needs the operator's words in a v2 round: `MAKE_NO_QUOTE`.
- **A plan changed after the sets.** `set_facts(...)['changed']` marks the set; `V.set_make` accepts it as it accepts a changed spec today.

### 3.9 Every "what next" sentence of a v2 round

One constant each; the answer carries it as `then`. Figures in braces are filled in.

| Constant (module) | Said when | The sentence |
|---|---|---|
| `FIND_START` (`ref_find`) | no round yet, the plan is accepted; by `V.round_due`, by `GET …/digest`, and by the page's `_after` | "The references come next. Run `vw visuals digest`. Then find each thing in the footage: start `vw-reference-finder` helpers, about 5 things each, up to 6 at a time (with 5 things or fewer, do it yourself). Each takes trial frames (`vw visuals trial`), looks at them and records what it saw (`vw visuals look`)." |
| `FIND_WORDS` (`ref_find`) | the run has footage and no digest | "This run has no digest of its footage, so the search is by words only: `vw visuals elements` names the likely clips. Every frame still needs a look (`vw visuals trial`, then `vw visuals look`). Tell the operator the footage was searched by words only." |
| `TRIAL_NEXT` (`ref_find`) | after `trial` | "Read each trial frame, then record what you saw: `vw visuals look --file <file>`. A trial frame is not a reference." |
| `LOOK_MORE` (`ref_find`) | after `look`, things left | "{n} thing(s) recorded. {left} are not searched yet: {ids}." |
| `LOOK_ALL` (`ref_find`) | after `look`, none left | "Every thing is searched. Write out/reference-round.json, one row per thing (element_id, rec, reason; `prompt` only for what the plan does not say; `first` on three things of different kinds), and send it: `vw visuals round --file out/reference-round.json`." |
| `ROUND_POSTED` (`ref_sets`) | after `round --file`, a new round | "The round is posted for {n} things, {d} of them doubtful. Run `vw visuals page`: the operator answers step 1 there, in one visit; in the chat (`vw visuals next`) only where the page cannot be shown." |
| `GO1_MAKING` (`ref_sets`) | step 1 recorded, `rest` not empty | "Step 1 is recorded. The first {k} sets are being made (about ₹{x}); {r} more wait for the operator's word. Wait: `vw visuals status --wait 900`." |
| `ALL_MAKING` (`ref_sets`) | step 1 recorded, no `rest`; also after `round --rest` | "{k} set(s) are being made (about ₹{x}). Wait: `vw visuals status --wait 900`." |
| `SETS_LOOK` (`ref_sets`) | state `'looking'` | "The sets are back. Look at them before the operator does: `vw visuals round --looks` lists them and fetches the pictures. Start `vw-set-look` helpers, about 5 sets each (with 5 sets or fewer, look yourself); each records its looks: `vw visuals round --looks <file>`. No set is shown to the operator before its look is recorded." |
| `SETS_PAGE` (`ref_sets`) | state `2`, after the looks | "Every set has its look. Run `vw visuals page`: the operator judges the sets there, in one visit." |
| `REWRITE_DUE` (`ref_sets`) | state `'rewrite'` | "{n} set(s) wait for your rewrite. For each, write the request again from the operator's words, the check and your look: out/round-rewrites.json, rows {element_id, prompt}. Send it: `vw visuals round --rewrite out/round-rewrites.json`. The sets are made then, not before." |
| `REWRITE_MAKING` (`ref_sets`) | after `round --rewrite` | "{n} set(s) are being made again (about ₹{x}). Wait: `vw visuals status --wait 900`." |
| `MERGE_ASK` (`ref_sets`) | a round file sent again after step 1 | "The round is past step 1: nothing was made. {n} thing(s) are back with the operator as open lines. Run `vw visuals page`." |
| `REST_LEFT` (`page_flow`) | the page is recorded, nothing else waits, `rest` not empty | "The first sets are judged. {r} more are not ordered: the operator orders them on the page (`vw visuals page`), or leaves them." |
| `REFS_HERE`, `REFS_GO`, `SETS_WAIT`, `SETS_STAND`, `SETS_NONE`, `ROUND_NEXT`, `ROUND_REFUSED` (`page_flow`, existing) | as today | unchanged, except `SETS_WAIT`: for state `'looking'` the page says `ref_sets.SETS_LOOK`, for `'rewrite'` `ref_sets.REWRITE_DUE` |

`page_flow.REFS_START` is replaced by `ref_find.FIND_START` for a film with no round; `V.round_due` returns the same constant.

### 3.10 The page and the chat (C)

**One function, two front ends.** `chat_flow._round_items(ctx, every)` stays the one builder of the questions; the page's `_refs_lines` and `_sets_lines` and the chat's `vw visuals next` read it. Every sentence shown to the operator comes from one table in `chat_flow` used by both. `chat_flow.round_accept(ctx, quote)` is "Accept the proposals" for both.

**New fields a line may carry** (all optional; a line of an older round has none and is drawn as today):

| Field | Shape | Drawn by `decisions.html` as |
|---|---|---|
| `group` | str | a folding heading; lines with the same `group` under it; a group whose lines are all answered folds |
| `rec` | `{'do', 'label', 'reason'}` | "Claude proposes: {label}. {reason}", above the buttons; the matching button is the first |
| `warnings` | `[str]` (exists for a gap) | "Read before you answer" |
| `pics[].note` | str | under the picture: what Claude saw |
| `pics[].weak` | bool | a tag "weak" on the picture |
| `pics[].choice`, `pics[].choice_label` | str | a button under the picture. `use:<id>` on a set picture is the line's answer, as today. `not:<id>` and `use:<trial id>` are kept in the answer's `pics` map |
| `pics[].ref_only` | bool | shown first, to compare with; no button |
| `check` | `{'state': 'pass|fail|none', 'by', 'lines': [str]}` | one line when it passed; an open list when it failed; "the check did not run" for `none` |
| `notes` | `{'title', 'text', 'sources': <count>}` | folded |
| `earlier` | `[pic]` | folded: "The set before" |
| `changes`, `asked` | (exist) | "Made again as you asked: '…'" |
| `partial` | str | a plain line: "Two of three pictures came back; missing: the face." |
| `cost` | str | under "Leave it out": which shots lose the thing |
| `comment_hint` | str | the comment box's own hint; no `comment` where no set can follow |

**The answer document** of the page gains `pics: {<id>: 'not'|'use'}`. `main.PageAnswer` gains `pics: dict[str, str]` (at most 8). `vw visuals page --record` passes it on.

**Step 1 ("References"), in this order:**

1. `key: 'refs:proposals'`, `item: 'round1:all'`, shown while a routine line is unanswered. `text`: how many things have a proposal, how many are doubtful, and what accepting does ("has {s} sets made (about ₹{x}), takes {f} footage pictures as they are, leaves {l} out"). One button: `{'label': 'Accept the {n} proposals (paid, about ₹{x})', 'choice': 'accept_all'}`. It never covers a doubtful line.
2. The doubtful lines, `group: 'Doubtful: answer these yourself'`.
3. The other lines, `group` by kind: People, Things, Materials, Places, Ways of working.

A thing's line: `key: 'ref:<eid>'`, `item: 'round1:<eid>'`, `title`, `state`, `group`, `ask`, `text` (the plan's description; then "Used in {n} shots; the closest is {size} ({gap}, shot {id})." or "No shot of the plan names it."; then the footage sentence), `rec`, `warnings` (a real, named person with no photo; the client's own thing; a size not known; a cause that stands; "the plan changed since the search"), `pics` (each footage picture: `label` its view, `note`, `weak`, `choice: 'not:<fid>'`), `buttons` (the choices of 3.4, each paid one with the price), `comment` and `comment_hint` only where a set can follow, `own`, `cost`, `kept`, `kept_note`.

The footage sentence, from `ref_find.found_all`: `found` or `weak`: "From your footage: {n} picture(s)." · `none`: "None was found in your footage. Searched: {clips} clips ({clip_names}…). The closest is shown." (its picture with `choice: 'use:<trial id>'`, `choice_label: 'That is it'`) or "…Nothing close was seen." · `not_searched`: "Your footage was not searched for it: {note}." · clips of the digest's `not_searched` are named. The words "has no picture of it" are not used.

**Step 1 summary:** "{n} things: {a} to answer, {k} kept. Spent so far ₹{s} of the ₹{c} limit. These sets: up to ₹{x}. The plan's shots still need about ₹{y}. Left after both: ₹{z}." `y` is `V.budget(...)['planned']['inr']`. When `z` is below zero the round's `note` says so before "done". It warns; only today's refusal (the sets alone pass the limit) blocks.

**Step 2 ("References: the sets"), in this order:**

1. `key: 'sets:rest'`, `item: 'rest:<round at>'`, while `rest` is not empty: `text` "These are the first {k} sets. {r} more are not ordered yet. Look at these first: a fault here would repeat in all of them." One button `{'label': 'Make the other {r} sets (paid, about ₹{x})', 'choice': 'rest'}`.
2. Sets with a failed check, or a recommendation other than `use`: `group: 'Doubtful: look at these first'`.
3. The other sets, by kind. Then the lines not made, being made, being looked at ("Claude is looking at it"), waiting for the rewrite ("The assistant is writing its request again from your words"), and recorded. A thing taken from footage at step 1 is listed here, recorded and folded, with its pictures.

A set's line: `key: 'set:<eid>'`, `item: 'set:<eid>:<set id>'`, `text` (description and the "used in" sentence), `rec` (from `set_facts.rec`), `pics` (first the inputs, `ref_only`, labelled "From your footage: {view}" or "Drawing"; then the set's pictures, `label` "{letter} · {view}", `note` Claude's look, `choice: 'use:<ref>'` for a thing), `check` (`by`: "The program's check (Gemini)"; `lines`: "Picture {letter}: {check}: {seen}"), `notes`, `partial`, `earlier`, `changes`/`asked`, `buttons`, `comment`, `own`. With `makes_left == 0` the buttons "No" and "Correct it" are not offered and the text says the set was made three times.

A set that was not made: its text is `set_facts.fail.text`, or the cause that stands.

**New choices `page_record` handles:** `accept_all` (→ `chat_flow.round_accept`), `clean`, `pics` with the `pics` map (→ `ref_find.not_this`, `ref_find.that_is_it`, before the line's own answer), `rest` (→ `ref_sets.round_rest`), and for a `reopened` thing `approve` / `ignore` (→ `ref_sets.round_reopen`). `_plan_step` treats `'looking'` and `'rewrite'` as the sets step.

**Refusals of part C** (constants of `chat_flow`): `ACCEPT_NONE` (no routine line is left to accept); `PIC_UNKNOWN` (a picture mark names a picture that is not on that line). Any other choice gets today's "Not an answer to this line".

### 3.11 The helpers and the guard

| | `vw-reference-finder` (A) | `vw-set-look` (B) |
|---|---|---|
| File | `plugin/agents/vw-reference-finder.md` | `plugin/agents/vw-set-look.md` |
| Front matter | as `vw-drawing.md`: `tools: Read, Write, Bash`, `model: opus`, `effort: high` | the same |
| Given | its thing ids; `work/visuals/refs/things.json`; `work/visuals/digest/index.json` | its element ids; `work/visuals/sets/looks.json`; the folder of each set |
| Does | reads the digest files that mention its things; writes `work/visuals/refs/<group>.trials.json`; `vw visuals trial --file …`; reads each frame; writes `work/visuals/refs/<group>.looks.json`; `vw visuals look --file …`; fixes what the server refuses | reads each set's three pictures, its inputs, its request and the thing's facts; writes `work/visuals/sets/<group>.looks.json`; `vw visuals round --looks <file>` |
| Judges by | the rule in `things.json` | does each picture show its view; is it the film's thing (against the footage picture); does it agree with the plan; do the three agree; what did the image model change |
| Returns | one line per thing: found, weak, not found, not searched | one line per set: use (which picture), make again (why), or doubtful |
| Never | approves, calls a picture model, shows the operator anything | approves, orders a set |

`ref_find.FRAME_RULE` (the one text of the rule; it travels in `things.json`): "A frame is a good reference when the thing is whole, not covered, large enough to read, sharp, and its shape and size can be read. Weak: one of these fails and the thing is still recognised. Fail: the thing is not in the frame or cannot be recognised."

**Guard** (`plugin/hooks/guard.py`, done in step 0): `VW_HELPERS` gains `vw:vw-reference-finder`, `vw-reference-finder`, `vw:vw-set-look`, `vw-set-look`. Nothing else changes: a helper's calls pass the same guard, which already allows one `vw` command per call and files inside the run folder.

### 3.12 Instructions

Changed only by the three wording scripts; each sentence below is the anchor of one script and of no other. Replaced sentences go to `server/retired-sentences.json`. The merger runs the scripts and raises `BEFORE['visuals']` in `server/unit/test_design125_stage7_c_pure.py` once.

| Part `picture-search` of `v3.json` (and the same sentence in `vw.md`, Visuals) | Script |
|---|---|
| "`vw visuals elements` shows where each is seen in the footage … (`vw visuals frame --file`, free)." | a: the digest, the helpers, trial frames and looks |
| "A clip frame is free and exact … never a blurred one for identity." | a: the rule is the server's; a frame is kept through its look |
| "Then the round, once any drawing set is approved: … the why line);" up to "the operator answers step 1 there." | b: the row is a proposal with its reason; `prompt` only for what the plan does not say |
| "The server writes a person's sheet … full length, working pose, the face;" | b: the views of 3.6 |
| "`vw visuals status --wait 900` between the two steps …" | b: the states of 3.8; follow `then` |
| "Step 1: each thing gets the footage picture or Ignore this; Done approves the frames and makes every set at once … the drawings)." | b: the answers of 3.4; two goes; made from the footage picture |
| "Step 2, when every set is back: … come back for another step 2." | b: the looks first; the rewrite; three makes |
| "`vw visuals round --verdicts` … never use them to answer for the operator." | b: the new verdict `clean`; `--rest`, `--make` with the operator's words |
| "Done on step 1 is not undone …" | b: only the first sets are ordered then |
| "The operator answers both steps on the page … is their word." and "In the chat, one at a time …" | c: the proposals, the doubtful first, the same words in the chat |
| `vw.md`, The web: "…except the plugin's helpers the steps name (…)" | a: both new helpers named |
| new sentence, part `picture-search` | b: "A round whose answer has no `v` is an older round: follow the tool's answers." |

`chat_flow.LOOK_ONLY` stays for pictures shown in the chat.

---

## 4. THE SPLIT

A file not listed is edited by nobody. "Region" means the builder edits only inside it.

| File | A | B | C |
|---|---|---|---|
| `server/app/ref_find.py` | all | | |
| `server/app/ref_sets.py` | | all | |
| `server/app/visuals_stage.py` | **nothing** | see below | **nothing** |
| `server/app/image_check.py` | | all (`code_checks`, `lines_of`) | |
| `server/app/visual_workers.py` | | all (`finalize_image`, `check_image`, `refusal`, the messages of `process_image` 238-249, `_gemini_set`) | |
| `server/app/page_flow.py`, `server/app/chat_flow.py`, `plugin/pages/decisions.html` | | | all |
| `server/app/main.py` | new routes and their bodies in one block directly after `visuals_elements` (line 1773) | new routes and their bodies in one block directly after `visuals_round_aside` (line 1814); the body of `visuals_round_make` | `PageAnswer` (1483-1490) only |
| `plugin/scripts/vw.py` | one new block `if a.what in ('digest', 'trial', 'look'):` directly after the `elements` block (ends line 2488) | inside the `round` block (2499-2537) and `_round_one` (1966-1992) | inside the `page` block (2383-2470) |
| `plugin/hooks/guard.py` | nobody: step 0 added both helpers | | |
| `plugin/agents/vw-reference-finder.md` | all (the shell's body) | | |
| `plugin/agents/vw-set-look.md` | | all (the shell's body) | |
| `scripts/d211a_wording_v3.py` / `d211b_…` / `d211c_…` | a | b | c |
| `server/unit/test_design211a_*_pure.py`, `plugin/tests/test_design211a_*.py` | all | | |
| `server/unit/test_design211b_*_pure.py`, `plugin/tests/test_design211b_*.py` | | all | |
| `server/unit/test_design211c_*_pure.py`, `plugin/tests/test_design211c_*.py` | | | all |
| `server/unit/d211_fixture.py`, the two step-0 tests, `scripts/c1_split_v3.py`, the word and flag lists and the argparse lines of `vw.py`, and the files of 3.0 rule 6 | the master thread and the merger only | | |

**`server/app/visuals_stage.py`, part B only.** Every edit is a branch on `round_v2(session)`; the older path is left word for word.

| Function (line today) | Edit |
|---|---|
| `round_due` (2106) | returns `ref_find.FIND_START` for a film with no round |
| `round_start` (3163) | v2: the row fields of 3.5, `ref_find.round_frames`, every faulty row in one refusal |
| `_from_footage` (3202) | v2: `clean` makes a set; frames marked "not" are out; the golden picture is the first in view order |
| `_round_merge` (3223) | v2: orders nothing (3.8) |
| `_round_pass` (3268) | v2: the states of 3.8 |
| `_queue_sets` (3276) | v2: no appended corrections; `made.fp`; `parts` |
| `round_sets` (3312), `set_answer` (3425) | v2: `SET_NO_LOOK`, `rewrite_due`, `MAKES_LIMIT`, the round stays open while `rest` is not empty |
| `_fail_words` (3447), `_set_state` (3683) | v2: the cause and the model from the job |
| `set_make` (3512) | v2: `MAKE_NO_QUOTE`; a changed plan |
| `round_done` (3573) | v2: the verdict `clean`, the words, the first go |
| `generate_image` (3730), only the set branches: 3739-3753, 3917-3920, 3954-3958 | v2: `ref_sets.set_request` |
| `generate_image`, after 3860 | the warning of gap 23, for a still (`visual_type: image`), in `warns` |
| `_queue_image` (4308), line 4322 | `view_names` beside `views` |

Not edited by anyone: `KEPT_*`, `THING_VIEWS`, `PERSON_VIEWS`, `set_views`, `thing_prompt`, `person_prompt`, `_place_look`, `with_faces`, `add_reference`, `element_matches`, `elements_answer`, `prepare`. They serve the older round and the way back.

**What C reads from A and B** (and nothing else of theirs): `ref_find.frames_of`, `found_all`, `not_this`, `that_is_it`, `FIND_START`; `ref_sets.thing_facts`, `set_facts`, `round_rest`, `round_reopen`, `SETS_LOOK`, `REWRITE_DUE`; `V._round_pass`, `V.round_v2`, `V.budget`, and the row fields of 3.5. C builds against `server/unit/d211_fixture.py`.

**What A reads from B:** `ref_sets.thing_facts`, `ref_sets.view_names`. **What B reads from A:** `ref_find.round_frames`, `frames_of`, `fingerprint`, `FIND_START`.

---

## 5. Expected though not said, edge cases, failures

### 5.1 Expected though not said

- A step that shows nothing new to an older round: VW-24's page looks and behaves as today.
- Every answer on the page is one log line with the operator's words, as today, the new choices too.
- A paid button carries its price. "Accept the proposals" carries the total.
- The chat way back shows the same lines, pictures and words.
- A person's footage picture goes to the image model only with the recorded permission, as today.
- No secret is written to any file; the helpers get no key.
- Nothing in the fixed texts is tied to one kind of film.

### 5.2 Edge cases

| Case | Handling |
|---|---|
| A film with no footage | No search, no search record needed; every thing is "a set" or "no set needed" |
| The plan names no thing | No round, as today |
| One to five things | No helper; Claude does the same commands itself |
| 300 clips or more | The digest is in files of 25 clips; a helper reads the index first |
| More than 80 things | The round takes at most 80 rows (today's limit); said in the refusal. Not changed |
| A clip with no analysis | Named as not searched on every line it could matter to; never "none was found" |
| The same frame is best for two things | One trial frame, a look per thing, one reference per thing |
| Two views found only in one clip | Two frames of that clip are allowed |
| Two kept frames for one view | Refused (`KEEP_LIMIT`) |
| Only a weak frame exists | Kept as weak, shown as weak, the line is doubtful; the operator may use it or have a clean set made from it |
| The same moment asked twice | The same trial frame; not counted twice |
| Several helpers call the tool at once | Every write takes the run's lock, as today; trial frames are cut before the lock, so helpers do not wait on each other's cutting |
| Two helpers given the same thing | The later search record replaces the earlier; kept frames over the limit are refused |
| A helper stops half way | Its things have no search record; the server names them (`left`); Claude searches them or records "not searched" with the reason |
| The run is taken over on another machine | Looks, search records, kept frames and requests are on the server. `vw visuals digest` writes the files again with each thing's result, so only what is left is done |
| A run in the middle of its round at the release (VW-24) | An older round: unchanged to its end. New: the repaired size check and the check on three pictures for sets made after the release |
| The operator rejects a footage picture | The next best that was already seen is shown; no new search. None left: "none was found", with the paid and the leave-out choice |
| The operator answers on an older page copy | An answer to a line that changed is stale, as today |
| A set comes back with one or two pictures | Shown as it is; the look covers what came; the missing view is named |
| The limit is reached in the second go | None of the second go is ordered; the sentence gives the figures; the first sets stay |
| The limit is reached at a remake | The answer is held and waits, as today |
| The plan changes after the search | `stale` on that thing's search record; its line warns; only that thing is searched again; its old trial frames are dropped |
| The plan changes after a set was made | The set is marked; "Make it again (paid)" is offered; nothing is made by itself |
| A thing the plan no longer names | Left out of the questions, as today; it does not hold the round open |
| The round file is sent again after step 1 | Nothing is ordered; new and left-out things go back to the operator |
| A real person is in the frame of a thing | Allowed for a thing, as today |
| "Accept the proposals" clicked, then one line changed | The line's own answer wins; the later answer stands |

### 5.3 Failure modes

| Failure | Handling |
|---|---|
| A trial frame cannot be cut | That moment is named in `failed`; the others go on |
| The server is slow under six helpers | A helper waits and tries once more (the tool's existing retry); the trial measures the load |
| Helpers cannot be started on a machine | Claude works thing by thing; slower, same result |
| A look is claimed for a frame never fetched | Refused: the trial id must exist |
| The digest cannot be built | The word search as the way back; the operator is told |
| The set-look helper fails or is stopped | The round stays at "looking"; the sentence tells Claude to look itself. No set reaches the operator without a look |
| The server's check does not run (no key, a model error) | The page says "the check did not run"; Claude's look still stands; nothing is blocked |
| The image model refuses or returns nothing | The line names the provider, the model and the cause; "Make it (paid)" or "Leave it out" |
| The image model fails on picture 2 or 3 | A partial set, shown as it is |
| Claude does not send the rewrite | The round stays at "rewrite"; the sentence repeats on every status |
| A rewrite equal to the earlier request | Refused |
| A page too large for one document | Today's trimming (`_round_page`) holds: the later lines wait for the next "done" |

### 5.4 Checked against the ten mistakes that matter most

| # | The mistake | In this design |
|---|---|---|
| 1 | Faults the program could catch reach the operator; a flag not shown | Three pictures checked; the false failure removed; both results on the line; doubtful lines first |
| 2 | Exact words retyped by the assistant | The server places the plan's words, views and place; the assistant adds only what is new |
| 3 | Instructions and program disagree | A way of working may show hands in the request, in the check and in the instruction; one test pins the three |
| 4 | The same fact asked more than once | Not solved for overlapping sets (gap 21, not built). The proposal "no set needed" lowers it |
| 5 | An outside source wins, the note hidden | The film's own picture wins over the web; the image model's notes are on the line |
| 6 | The assistant decides alone | Every proposal is shown with its reason; the request parts are stored and can be shown; nothing paid without the operator |
| 7 | A figure guessed | Sizes come from the plan with their status; an unknown size is left out, not written by the assistant |
| 8 | Rules that fit one kind | A request and check lines per kind; generic fixed text |
| 9 | What the operator is shown | Description, shots, reason, grouping, folding, "made again as you asked", the earlier set |
| 10 | Cost shown in part; faults after the money | Three figures at step 1; free looks before step 1; three sets before the rest; a remake only with a changed request |

---

## 6. Tests first

Database-free tests in `server/unit/`, plugin tests in `plugin/tests/`, page checks on a local copy of the page. Each "what next" sentence and each refusal has its own test.

### 6.0 The shared fixture (step 0)

`server/unit/d211_fixture.py` (written; plain data, no import of the application, so the plugin tests import it too): `plan()`, `digest()`, `trials()`, `session(state)` for each state of 3.8 (`'1'`, `'making'`, `'looking'`, `'2'`, `'rewrite'`, `'complete'`), `older_session()` (a round without `v`, at step 2), `specs_approved(s, p, spec_digest)`. One plan with a person (MASON), an object with two kept frames, one weak (TROWEL), an object not found with a closest frame (FAN), a material with a spec (BRICK), a place (STREET), a way of working (T_LAY), a thing with approved drawings (TILE), and an animal (DOG). The first go is MASON, STREET, T_LAY; the made sets carry their checks, their looks and the image model's notes. All three parts import it; a change to it goes through the master thread.

### 6.1 Part A (`test_design211a_*_pure.py`, `plugin/tests/test_design211a_*.py`)

- Digest: a clip with sub-clips gives the part fields; a clip without sub-clips gives an empty `parts`; an excluded clip is absent; a media clip with no analysis is in `not_searched`; the same inputs give the same `stamp` and no rebuild; a new clip rebuilds.
- No digest: `then` is `FIND_WORDS`. No footage: `footage()` is false and `round_frames` asks for no search record.
- Trial: the id is the same for the same moment; the frame is 640 px at most; it is not in `session['references']`; a failed moment is in `failed` and the others are recorded; `left` counts down. Refusals, one test each: `TRIAL_TOO_MANY`, `TRIAL_LIMIT`, `TRIAL_UNKNOWN_CLIP`. A changed fingerprint drops the thing's trial frames.
- Look: `result` is decided by the server for each of the four cases; a kept frame gets `view`, `look`, `weak`, `trial`; `closest` is stored only when nothing is kept. Refusals, one test each: `LOOK_UNKNOWN_TRIAL`, `LOOK_VERDICT`, `LOOK_SEEN`, `LOOK_VIEW`, `KEEP_FAIL`, `KEEP_LIMIT`, `LOOK_NOTHING`. One refused thing does not stop the others.
- `round_frames`: view order; `FRAME_NO_LOOK`; `NOT_SEARCHED`.
- `frames_of`, `found_all` (each result, `stale`), `fingerprint` (changes with each of its fields, not with others), `not_this` (next best of the same view, `pass` before `weak`, none left), `that_is_it`.
- "What next", one test each: `FIND_START`, `FIND_WORDS`, `TRIAL_NEXT`, `LOOK_MORE`, `LOOK_ALL`.
- Two calls for the same thing in a row leave one consistent record.
- Plugin: `vw visuals digest` writes the index, the clip files of at most 25 and `things.json`; `vw visuals trial` puts each frame under `work/visuals/trials/<element>/`; a flag the command does not read is refused by name; the guard allows `vw-reference-finder` and `vw-set-look` and still blocks another helper name; the helper file has the front matter of 3.11 and names no rule text of its own; with no helper the same commands work one by one.
- Wording: each anchor of script a is found once; the retired sentences are in `retired-sentences.json`.

### 6.2 Part B (`test_design211b_*_pure.py`, `plugin/tests/test_design211b_*.py`)

- `thing_facts`: shots in film order, `shots_made`, `closest`, `scene` of the first shot, none when no shot names it.
- `views_for`: the plan's views first; two that read the same are one; filled to three by kind; a person's pictures 1 and 3 fixed.
- `set_request`, for each kind: the description and requirements word for word; sizes with status (`unknown` absent, `proposed` as "about"); the place of the thing's own scene, never the first scene's; a place gets its signs unless `staged_clean`; the operator's latest words present, earlier ones absent; a footage input changes `source`, the text and `search` stays on; a weak frame is named weak; no word of the list "site", "trade", "how the work is done", "natural daylight" in any request; a way of working's request allows hands and its lines do not forbid them.
- `round_start` v2: stores the fields of 3.5; `doubt` in each of its cases; every faulty row in one refusal. Refusals, one test each: `REC_MISSING`, `REC_UNKNOWN`, `REC_NO_FRAME`, `REC_PERSON`, `REASON_MISSING`, `FIRST_TOO_MANY`. An empty `prompt` is accepted.
- An older round: `round_start`, `round_done`, `round_sets`, `_round_merge`, `_queue_sets` and the request text give byte for byte what they give today (pinned against the fixture's older round).
- The first go: three marked; fewer marked and filled by kind; three or fewer sets in all; a marked thing left out by the operator.
- `round_done` v2: `clean` makes a set from the frames (`CLEAN_NO_FRAME` without one); the step-1 words reach `operator_words` and the request; frames marked "not" are not inputs and not golden.
- States: one test per state of 3.8 and per change between them.
- Looks at a set: complete and incomplete; `SET_NO_LOOK` in `round_sets` and in `set_answer`. Refusals, one test each: `LOOK_SET_UNKNOWN`, `LOOK_PICTURES`, `LOOK_VERDICT`, `LOOK_SEEN`, `LOOK_GOLDEN`.
- The second go: `REST_NOT_NOW`, `REST_NONE`, `REST_CAP` (none ordered).
- Remake: "No" orders nothing and sets `rewrite_due`; the rewrite moves the earlier request to `history` and orders once; `REWRITE_NOT_DUE`, `REWRITE_EMPTY`, `REWRITE_SAME`; the fourth make is `MAKES_LIMIT`.
- Second send: nothing ordered; a left-out thing and a new thing are `reopened`; a not-made thing keeps its paid button. `MAKE_NO_QUOTE`.
- Checks: the size line passes for 2752×1536 against `{'aspect': '16:9'}` and fails for 1536×2752; a string size as today; each picture of a set gets its own check; the lines by kind of 3.7; no `a real face` line for a permitted photo.
- `set_facts`: `partial`, `fail` (the provider and model of the job, never "OpenAI" for a Gemini job), `changed` for a changed description, spec and photo, `makes_left`.
- The warning of gap 23 on a still; none on a set.
- "What next", one test each: `ROUND_POSTED`, `GO1_MAKING`, `ALL_MAKING`, `SETS_LOOK`, `SETS_PAGE`, `REWRITE_DUE`, `REWRITE_MAKING`, `MERGE_ASK`.
- Plugin: `round --rest`, `--rewrite`, `--looks` with and without a file; for a v2 answer the tool prints `then` and no line of its own; for an older answer it prints today's line; the set-look helper file.
- Wording: each anchor of script b found once; retired sentences listed; the instruction, the request and the check agree on hands for a way of working.

### 6.3 Part C (`test_design211c_*_pure.py`, `plugin/tests/test_design211c_*.py`, page checks)

- Step 1 lines from the fixture: the order (proposals, doubtful, by kind); each field of 3.10; the footage sentence for each result; "has no picture of it" appears nowhere; a person shown in a made picture has no "Leave it out"; the comment box only where a set can follow; `cost` names the shots.
- "Accept the proposals": covers every routine line, no doubtful one; the total price; `ACCEPT_NONE` when none is left; a later answer to one line wins.
- The answer `pics`: "not" calls `not_this` and the line comes back open; "that is it" calls `that_is_it`; `PIC_UNKNOWN`; an answer with both a picture mark and a line choice.
- Step 1 summary: the four figures; the warning when the rest is below zero; no block.
- Step 2 lines: the `rest` line while `rest` is not empty; doubtful sets first; the inputs before the set's pictures; `check` for pass, fail and none; `notes`; `partial`; `earlier` and "made again as you asked"; no "No" at `makes_left == 0`; a thing from footage listed as recorded; the words for "looking" and "rewrite".
- `page_record`: `accept_all`, `clean`, `pics`, `rest`, a `reopened` thing; a stale answer; a refusal kept on its line.
- `then` after each record, one test each: `REFS_HERE`, `REFS_GO`, `SETS_WAIT`, `ref_sets.SETS_LOOK`, `ref_sets.REWRITE_DUE`, `REST_LEFT`, `SETS_STAND`, `SETS_NONE`, `ROUND_NEXT`, `ROUND_REFUSED`, `ref_find.FIND_START`.
- The chat: for the same fixture the chat item of each line has the same question, text and button labels as the page line.
- An older round: the lines of both steps equal today's, field for field.
- Page checks on a local copy with the fixture's round: groups fold; the proposal and its button; a weak tag; a picture button toggles and is saved with the answer; the check list; the folded notes and earlier set; a line of an older round draws as today.
- Wording: each anchor of script c found once.

### 6.4 After the merge (the merger)

The three reviews of design/207 before any deploy: instructions against the program, this note against what was built, and defects. Then the whole `server/unit` suite and the plugin tests of the three parts.

---

## 7. The trial after the build

**On what.** A copy of VW-24 as a test run of its own, taken up to the accepted plan, with no round. VW-24 itself is not read for writing and not touched: its round, its sets and its spend stay as they are.

**What is run.**

1. The digest of the copy.
2. The finder on ten things: the pan, the stone heap, the trowel, the brick, the bucket, the cement bag, the roof tile, the mason, one place, and one thing the footage does not show (the fan regulator).
3. The round for those ten, step 1 on the page.
4. Two or three sets, 6 to 9 pictures (about ₹70 to ₹105 on the copy's own limit): one thing made from its footage picture (the trowel), one place, one way of working. Then the check, the look, and step 2 on the page.

**What it measures.**

| Question | Measure |
|---|---|
| Does Claude find the film's own pictures? | Good frames and views found per thing; the two frames SK named as bad are refused or marked weak |
| How long does it take? | Minutes for ten things; helpers used; the server's load while they run |
| How many paid sets would not have been needed? | Of VW-24's sets for these ten, how many a footage picture replaces |
| Do the sets now match the film? | The trowel's handle and the bucket against the footage |
| Are the three pictures three views? | No two near-identical; the plan's views present |
| Do the checks tell the truth? | No false size failure; a way of working with hands passes; real faults are named |
| Does the page let the operator decide? | SK answers step 1 and step 2 once; time taken; what was unclear |

No release to the team before SK has seen the trial.

---

## 8. Decisions taken by default, not covered, not verified

### 8.1 Decisions taken by default (SK can change any)

From the master thread:

1. A Claude helper looks at every footage frame and at all three pictures of every set. The server's Gemini check is kept, repaired and run on all three. Both results are shown. The server shows no frame and no set before a look is recorded.
2. No paid action without the operator. A set that fails a check is not made again by itself. A second send of the round file orders nothing.
3. Sets are made in two goes: three first, then "make the rest" in one click with the price.
4. A set is made from the film's approved footage pictures when they exist (up to 3, with the drawings). Web photographs are the fallback and the request says so.
5. A footage picture may be answered: use it, make a clean set from it (paid), not this picture, or leave the thing out.
6. Each line shows the description, the shots, how close, and Claude's proposal with its reason; lines are grouped and fold; "Accept the proposals" covers the routine lines with the total price; doubtful lines come first and are never covered.
7. No hard rule for which things deserve a set: Claude proposes "no set needed" with a reason, the operator confirms.
8. Requests per kind; the plan's views drive the pictures; each thing is placed in the scene of its first shot; generic fixed text; the server places the plan's words.
9. Sets of places and ways of working are still made. Related things together, their later use, and cropping are not built.
10. "No" and "Correct it": Claude rewrites the request; the earlier one is kept; at most three makes.
11. The texts of gap group E are corrected.
12. The older ways below.

Added by this note:

13. **VW-24 gets nothing new on its page**, not even the check results: its round is an older round. The alternative (show the checks on VW-24 too) is a small change SK can ask for.
14. **A person's pictures 1 and 3 stay fixed** (full length from the front; the face), because later steps read them by position. The plan's views drive picture 2 only.
15. **"No set needed" and "Leave it out" record the same thing.** Only the words on the line differ.
16. **A person shown in a made picture has no "Leave it out"**: SK already decided every such person gets a sheet.
17. **A "No" with no words still needs a changed request**: Claude rewrites from the check and its look. The same request is refused.
18. **The money figures warn; they do not block.** Only the sets alone passing the limit blocks, as today.
19. **SK's request text of 4 Nov is reworded** to be generic. Its two ideas are kept. SK reads the new text before the trial.
20. **Web search stays on** for a set made from a footage picture, for what the frame does not show; the text says the film's picture wins.
21. **Limits:** 8 trial frames and 3 kept frames per thing, 5 things per helper, 6 helpers at a time, as the requirement proposed.
22. **Gap 23 in part:** a warning on a still, nothing on the AI video route.
23. **No "accept all" at step 2:** each set is judged by the operator.
24. **Step 0:** one small commit before the three builders start. It is done.

### 8.2 The older ways (for `design/35-decision-log.md`, rows 103 to 112; written by the merger)

| # | The older way | Where | Kept | Retired, or kept until |
|---|---|---|---|---|
| 103 | Where a thing is seen, by word match | `visuals_stage.element_matches`, `vw visuals elements` | as the way back for a run with no digest | **Kept as the way back (design/211).** No longer what the instructions tell the assistant to use |
| 104 | A footage frame taken into the round with no look | `vw visuals frame`, `visuals_stage.round_start` | for a round started before design/211 | **Retired for a new round at release:** refused by name (`FRAME_NO_LOOK`). Kept until the last older round is complete (VW-24) |
| 105 | One request text, three fixed views and the first scene's place for every kind | `KEPT_PREAMBLE`, `KEPT_COSMETICS`, `THING_VIEWS`, `PERSON_VIEWS`, `_place_look`, `thing_prompt`, `person_prompt` | for the sets of an older round | Kept until VW-24's round is complete; then deleted |
| 106 | The assistant types the whole subject block | `round_start` (`prompt` required, `HOW_WORDS`) | for an older round | **Retired for a new round at release:** `prompt` holds only what the plan does not say |
| 107 | Every set ordered at "Done" of step 1 | `round_done` | for an older round | Kept until VW-24's round is complete |
| 108 | "No" makes the set again with the same request; corrections appended | `_queue_sets` | for an older round | Kept until VW-24's round is complete |
| 109 | A second send of the round file orders the missing sets at once | `_round_merge` | for an older round | Kept until VW-24's round is complete |
| 110 | The check on picture 1 of a set only | `visual_workers.finalize_image` | none | **Retired at release** for every set made from then on |
| 111 | The size check that compared the request's record with the picture's pixels | `image_check.code_checks` | none | **Retired at release:** it failed every picture |
| 112 | "Your footage has no picture of it"; a Gemini failure named "OpenAI"; "three pictures" on a partial set | `page_flow._refs_lines`, `_sets_lines`, `visual_workers.refusal` | the page's two sentences for an older round | The failure text: **retired at release** for every film. The two page sentences: kept until VW-24's round is complete |

### 8.3 Not covered

- Gaps 11, 21, 24, and the parts of 17 and 23 named in section 1. Cropping.
- "People who read alike" by a word list (`traits`), the "not this" list, and the lint of material words: wrong-actor cases of review B that are not among the 33 gaps.
- More than 80 things in one round.
- A per-run limit on trial frames cut at one time. Added if the trial shows the server needs it.
- The step-2 pictures of an older round: no look, no check shown.
- What a reference of a place or a way of working is used for later.
- The video route's use of references.

### 8.4 Not verified

- Nothing was run. Every line number was read on `main` at 972c524 and will move.
- That an analysis output's `unit` is always the media id `vw visuals frame --clip` takes. Today's `elements` flow relies on it; I did not trace it in `analysis.py`.
- How `scripts/c1_split_v3.py` rebuilds `v3.json`: read in part. Rule 6 of 3.0 rests on it.
- That Gemini's check gives a useful answer on "same as picture 1" and "matches the footage picture". The trial shows it.
- That six helpers at once do not overload the server. The trial shows it.
- That a helper finds a frame better than the word match did. The trial shows it.
- How the copy of VW-24 for the trial is made. I found no tool for copying a run.
- Where the trial runs. Deploys are on hold until SK says yes each time.
- The cost of three checks per set (three Gemini Flash calls). Not priced.
- `plugin/pages/decisions.html` was read from line 275 on; its picture row (`thumbs`) only by its callers.
