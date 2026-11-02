# design/142: build requirements for SK's design/140 and design/141 answers (VW-16 options review and Revathi's feedback), 2 Nov 2026, for SK's approval

Sources:
- `design/140-vw16-options-review.md` section 5 (SK's 10 answers);
- `design/141-options-feedback-combined.md` section 6 (SK's 4 answers on Revathi's 8 points).

Paths are relative to the repository. Every change works for any film and any category, and none is written for VW-16.

**Lane and deploy.** Regular. This builds on main, which already holds the design/139 build (server 0.83.0, plugin 0.69.0, **not deployed**). This release would be server 0.84.0 and plugin 0.70.0. Built, tested and committed after SK approves this list; **not deployed until SK says so**.

**Films open today and what they keep.**
- **VW-16:** its first cut is proposed and on the review page; it is not touched. A new options proposal on any film follows the new rules (the decision log, the reasons in the cut, the timing markers). The older rules stay for options proposed before this release (design/35).
- **VW-13 and VW-17:** follow the new rules from their next options proposal.
- **VW-12:** to be deleted.
- **Picture notes:** these films' intake is done, so they carry none (nothing to keep).
- **Analysis:** a clip analysed before this release keeps its record. A re-run (`vw analysis --again`) is a new paid analysis.

---

## R1. One decision log per run, for every stage (design/141 point 2, Q1)

**Requirement**
1. **Kept on the server with the run:** a new table `vw2_log` (migration `012_decision_log.sql`). One row per entry:
   - when;
   - stage;
   - what it was about (a clip, sub-clip, scene, shot, element, picture or take);
   - kind: decision, refusal, flag, approval, retry, exclusion, override or workaround;
   - the rule by name, or "no rule";
   - the text;
   - who (server, assistant or operator), and the operator's words where there are any.
2. **The server writes its own entries at two places**, which together cover every write step of every stage. The table survives closing the run (the files' retention does not touch it).
   - **Every write under `/api/runs/{run}/`** (one wrapper beside the receipts, `core.with_receipt`): what the step did, what it was about, and the operator's words. A check that comes back "rejected" or with flags to act on records them by rule.
   - **Every refusal** (the `Problem` handler): its code and message. It is written on its own connection, so it is kept even though the refused step rolls back.
3. **Stage-specific server entries:**
   - **Analysis:** per clip, retained or excluded, the sub-clips thrown out with their reason, and the eligibility and crop verdicts.
   - **Options:** the cut's own reasons (R2), copied in when the cut is proposed.
4. **The assistant adds its judgement calls** with `vw log --about <id> --rule "<name or no rule>" "<what and why>"` (stage taken from the run). Each stage's instruction names the moments to log:
   - every choice between clips, pictures or takes;
   - every empty slot;
   - every case no rule covers;
   - every workaround.
5. **Readable as one story:** `GET /api/runs/{run}/log` as Markdown, ordered by time, grouped by stage. `vw log --show` and a link on the run's page.
6. **The hand-kept `work/log-<stage>.md`** in the operator folder stays until this is live, then is retired (design/35; the operator folder's `CLAUDE.local.md` is changed by SK's team).

**Edge cases**

| Case | Handling |
| --- | --- |
| A refused step rolls back its work | the refusal entry is written on its own connection, so it stays |
| The same request sent twice (a receipt replay) | logged once, by its receipt |
| A run with thousands of entries | one table, indexed by run and time; the Markdown is streamed |
| Secrets or keys in a request body | only the step's plain name, the ids it was about and the operator's words are logged, never whole bodies |
| `vw log` on a closed run | refused (the run is closed), like every write |
| `vw log` without text | refused |
| The log cannot be written (a database error) | the step itself still succeeds; the failure is written to the server's journal (the log is a record, not a gate) |

**Tests**
1. A write step records one entry, with the ids and the operator's words.
2. A refused step records its refusal, and the entry survives the rollback.
3. A replayed request is not logged twice.
4. `vw log` records an assistant entry, and is refused without text or on a closed run.
5. The Markdown lists entries by stage and time.
6. No request body is copied whole.

---

## R2. The first cut carries its own reasons (design/141 point 2)

**Requirement**
1. **Every blank** names the clips considered: `considered: [{sub_clip_id, why}]`, where `why` is one of:
   - wrong action, wrong object, already used, claim or number, too short, unusable crop, contradicts the words;
   - other, with words.
   When no eligible piece fits the scene's sentences at all, the blank says `none_fit` with one line instead.
2. **A shot with alternatives** says `preferred_because`.
3. **The check refuses** a blank without either, and a shot with alternatives without its reason.
4. **The package lists the sub-clips the analysis ruled out**, with the analysis's reason (on VW-16, the 13 of 98 not eligible).
5. The options shape in `shapes.json` shows the fields.

**Edge cases**
- A blank right after a scene with no direct footage: `none_fit` with the coverage line.
- A clip named in `considered` that does not exist: refused.
- The same clip both used and listed as considered in one scene: allowed (another part of it may not fit).

**Tests**
1. A blank without reasons is refused.
2. `none_fit` passes.
3. An unknown clip is refused.
4. An alternative without `preferred_because` is refused.
5. The package lists the ruled-out sub-clips with their reasons.

---

## R3. "Stays visible" matched by word and by meaning (design/140 Q1; design/141 point 6)

**Requirement**
1. Spaces, underscores and hyphens count as the same when the carry-over text is compared with a clip's landmark labels. "steel bars" then matches `reinforcement_steel_bars`.
2. Where the words still differ, the event may carry `carries_over_seen: "<why this label is the same thing>"` (for example "reinforcement_steel_bars is the rebar"). That answers the flag.
3. The flag stays to act on only when neither the words match nor a reason is given.
4. The instruction says the text is compared with the clip's landmark labels, and how.

**Tests**
1. "steel bars" matches `reinforcement_steel_bars`.
2. "rebar" with a reason passes.
3. "rebar" without a reason is flagged.

---

## R4. Timing markers, the camera move and the order of the timing rules (design/140 Q2, Q3; design/141 Q2)

**Requirement**
1. **Every real shot names both markers** (`illustrates_word_id`, `action_word_id`), or for each missing one a reason (`marker_reasons: {illustrates, action}`). The check refuses a shot with neither. The reason is shown on that shot's slide.
2. **The order when they clash:** the whole action (G2), then starting 6 to 12 frames before the word (B1), then the action landing on its word (B2). A B2 miss with a reason becomes information on the slide; without a reason it stays to act on.
3. **The analysis instruction** (`server/app/clip_log/prompt.py`):
   - the action peak covers the action only and ends when it is complete, never inside a camera move;
   - a pan, whip, push-in or shake is reported in a new field per sub-clip, `camera_moves: [{start_frame, end_frame, kind}]`, unless the move is part of the action;
   - the schema gains the field.
4. **The server lets a shot end before a reported camera move** that starts inside the logged peak, when the action is complete, with the reason shown. This covers analyses made before the instruction change only where a move was reported. For older records without the field, G2 applies as today.

**Edge cases**
- A sentence with no action word: the reason says so.
- A camera move that is the action (a tracking shot following a worker): not reported, and the peak includes it.
- A move ending after the clip's last frame: clipped to the clip.

**Tests**
1. A shot without markers or reasons is refused.
2. A reason passes and shows on the slide.
3. The B2 order: with a reason it is information; without, it is to act on.
4. A peak ending in a reported move may end at the move.
5. Without a reported move, G2 is unchanged.
6. The schema validates `camera_moves`.

---

## R5. The two noisy flags (design/140 Q4)

**Requirement**
1. **Colour (R10).** The server measures each clip's look once, at options prepare, and caches it with the session:
   - about five frames per clip, taken with ffmpeg;
   - brightness, warmth (red against blue) and colour strength, averaged with Pillow (already installed).
   Clips within a set distance are one group. Log footage is compared only with log footage. Gemini's `color_match_group_id` is no longer used for R10 or N14's place check.
2. **Cut point (R1).** Inside B1's window (6 to 12 frames before the illustrated word), the shot starts at a natural cut point when one is there. R1 fires only when a natural cut point was in that window and was not used. The instruction says so.

**Edge cases**
- A clip shorter than five frames: its frames are all used.
- A frame that cannot be read: skipped. A clip with none readable has an unknown look and never trips R10.
- Very dark or very bright clips: the warmth is read only where the frame has light.

**Threshold.** The distance is set so VW-16's one-yard, one-day footage comes out as one group (SK's answer). That needs VW-16's clips, which are on the server. The setting is checked there with a read-only script at deploy, with SK's approval. Until then the test uses fixed sample pictures.

**Tests**
1. Pictures of one look form one group, and a clearly different one splits.
2. Log footage stays apart.
3. R1 fires only when a cut point was in the window and unused.
4. Prepare caches the looks, so a second prepare does not grab again.

---

## R6. The second look sees the shot as cut (design/140 Q5; design/141 point 8, Q4)

**Requirement**
1. A new server step takes stills from a given in and out of a sub-clip (free):
   - the first, middle and last frame;
   - one every second, or **every half second** for a shot under a state or a claim.
   The shot is marked by its step's `claim: true` in the cut, by a check_by_eye note, or by the assistant's `state: true` on the event.
2. `vw options second-look` uses the cut's own in and out for every shot and alternative, instead of the logged piece's edges.
3. **Taken again when the cut changes.** After `join-second-look`, the tool lists the scenes whose cut points changed and tells the assistant to run `vw options second-look --scene <id>` for them. Stills of an unchanged shot are reused.

**Edge cases**
- A shot shorter than a second: first, middle and last only.
- An in or out outside the clip: refused (the check names it first).
- A grab that fails: noted in the scene file, never fatal (as today).
- A long shot (10 s at half seconds): 21 stills, a fair number for one helper.

**Tests**
1. Stills are taken from the cut's in and out.
2. Half-second stills on a claim or state shot.
3. Changed scenes are listed after the join; `--scene` re-grabs only those.

---

## R7. The second-look helper knows the rules (design/140 Q7)

**Requirement:** `plugin/agents/vw-scene-review.md` lists:
- the five note kinds (reuse, check_by_eye, poor_quality, join, other);
- the timing rules a fix must keep: the whole action peak (with R4's camera-move exception), starting 6 to 12 frames before the word, and R4's order;
- the new reasons a fix must carry (R2, R3, R4).

**Test:** the agent file names the five kinds and the rules (a wording test).

---

## R8. Scenes and chapters (design/140 Q6, Q8; design/141 points 1, 4, 5, 7)

**Requirement**
1. **The refusal says what it checks** (`server/app/stage2/narration.py:131`): "No scene names a chapter under process_stages. Name the chapters each scene covers, from the brief's list; a scene that covers none (an opening, a closing, a title) may leave it empty."
2. **A scene may name every chapter it covers.** In `plugin/commands/vw.md`, "the one chapter it covers" becomes "the chapters it covers". A paragraph is split only where its second chapter runs two sentences or more. The reason for each split, and for each paragraph kept together although it covers two chapters, is shown with the scene list.
3. **The scenes shape goes into `shapes.json`**, with the pauses at the top of the file. A pause put inside a scene is refused by name instead of dropped silently.
4. **Every chapter of the brief is covered or dropped on purpose.** The scenes step refuses until each brief chapter is named by a scene or listed in `dropped_chapters: [{chapter, reason}]` with the operator's words.

**Tests**
1. The new refusal wording.
2. A list of two chapters on one scene passes.
3. A pause inside a scene is refused by name.
4. An uncovered chapter is refused until it is placed or dropped with words.
5. `shapes.json` holds the scenes shape.

---

## R9. The client's picture notes are kept (design/141 point 4, Q3)

**Requirement**
1. **At intake**, a new removal kind `picture_note` keeps the line out of the narration (as today) but records it, with the line it sits under, in the intake record (`picture_notes: [{text, under_line}]`).
2. **At the options package**, each note is attached to the scene whose sentences hold its line. A note before the first spoken line goes with the first scene; one after the last goes with the last.
3. **At the scenes step**, the chapters check (R8.4) shows the notes behind any uncovered chapter, so the operator sees "this topic is in the client's picture notes but no scene carries it".
4. **At the visuals stage**, a gap's packet context lists the picture notes of its scene, for its blanks.
5. A dropped note is listed with the operator's reason (R8.4); none is dropped silently.

**Edge cases**
- A document with no picture notes: nothing changes.
- A note that names no topic (a camera direction): kept as a note, and offered at visuals like any other.
- A film whose intake is already done: no notes (nothing to carry).

**Tests**
1. Intake records notes with their lines.
2. The package attaches each note to its scene, including before-first and after-last.
3. The visuals packet lists them.
4. A film without notes is unchanged.

---

## R10. Smaller fixes (design/140 Q9, B10; design/141 points 3c, 3e, 3g)

1. **Long commands keep their output in the run folder.** The tool writes each command's answer to `work/last/<command>.json` as well as printing it, so a command run in the background can be read.
2. **The frame base is stated.** Every source frame in the pieces files carries its seconds beside it. The package's reading notes say source frames are at the clip's own rate (`source_fps`) and timeline frames at the film's rate.
3. **`vw options check`** ends with "the full list is in `vw options status`" when it reports information flags.
4. **Wording:**
   - the options instruction says a B-roll shot named by a step needs its own "why";
   - the analysis instruction says to start without asking (B10);
   - every stage's instruction names the moments to `vw log` (R1.4).
   - The old wording goes on the retired list.

**Tests:** the output file is written; the seconds sit beside the frames; the check line; the wording tests.

---

## Older ways (design/35)

| Older way | Kept until |
| --- | --- |
| Options proposed without reasons, markers or chapter coverage (VW-16's current cut) | that film's next options proposal, or its close |
| Gemini's colour group in R10 | retired at deploy: R10 is information only, and its new reading applies to every new check |
| The second look at the logged piece's edges | retired |
| The hand-kept stage logs in the operator folder | retired once R1 is live (SK's team removes the `CLAUDE.local.md` request) |
| Analyses without `camera_moves` | until those films close; G2 applies as today |

## Build order

1. R1 (the log: table, the two server hooks, `vw log`, the Markdown).
2. R2 and R3 (the cut's reasons, carry-over matching).
3. R4 (markers, the order, the camera move).
4. R5 (colour and cut-point flags).
5. R6 and R7 (the second look).
6. R8 and R9 (scenes, chapters, picture notes).
7. R10, then the wording and the full test run.

Tests are written first for each step, with one commit per step.

## Self-review (2 Nov)

1. **The claim tag is the assistant's, not the server's.** A step's `claim` is set in the cut (`steps[].claim`); R6 now says so. The `state: true` mark covers states that are not claims ("undisturbed").
2. **`vw log` is a new top-level command.** It is not `vw options log`, which downloads one clip's analysis log; the help text says which is which.
3. **The two server hooks were checked:** `core.with_receipt` serves the write steps, and the `Problem` handler in `main.py` every refusal. The refusal entry needs its own connection, because the request's transaction rolls back (R1, edge cases).
4. **R5's threshold cannot be set on this PC** (the clips are on the server). It is flagged for the deploy, as SK's answer asked for it to be tuned on VW-16.
5. **R8.4 refuses scenes until every chapter is placed or dropped.** That is stricter than today, and it is what point 4 asked for ("never dropped silently").
6. **Every R names what open films keep**, and nothing changes VW-16's current cut.

## Not covered

- **The colour threshold on real footage** is checked on VW-16 at deploy (the clips are on the server); the unit test uses sample pictures.
- **The Docker server suite** is not run, as before.
- **VW-16's current cut** is not re-made: the new rules apply from its next proposal.
- **The log's view on the web page** is a download link, not a page of its own.
