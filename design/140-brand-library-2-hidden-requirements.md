# design/140 part 2: brand-generic library, hidden requirements from the code

Status: for SK's review, 2 Nov 2026. No code written. Part 1 (`140-brand-library-1-requirement.md`) is the requirement this reads against. Each section has three parts: what the code does today, what that implies (the hidden requirements), and edge cases and failure modes with a proposed handling. Open questions are at the end. Every proposed handling waits for SK's approval.

## 0. SK's words mapped to the stages in the code

| SK's words | Stage in procedure v3 | Where it lives |
|---|---|---|
| "videos and images are uploaded" | `media` | `plugin/scripts/stages_av.py` `media_prepare` / `media_record` |
| "studied by Gemini Flash 3.8" | `analysis` (one paid clip-log request per clip, no acceptance step) | `server/app/analysis.py`, `analysis_jobs.py`, `clip_log/` |
| "the analysis stage will happen" (after the new question) | `options` (Stage 2A: Claude places the clips from the logs) | `server/app/stage2/stage.py` `prepare`, procedure v3 `options` |
| "the processing stage" | `options` and `master` (the review film and the KEEP / REJECT / TRIM answers) | `stage2/stage.py`, review page |
| "brand" | the run's `client_id` (the client directory row) | `core.py` `create_run`, `vw2_runs.client_id` |

**So the new question sits between `analysis` and `options`.** Today `vw next` moves from analysis to options with nothing to approve.

---

## 1. What already exists and can be reused

| Need | Already in the code | Reuse |
|---|---|---|
| A store per client that outlives a film | `vw2_client_rules` (`core.client_rules`, written at `master rule --add`) | Same pattern: one table keyed by `client_id` |
| Exact duplicate detection | Clip id = first 16 hex of the file's sha256 (`stages_av.py:133`); identical files in one batch are already listed once | A sha256 match against the brand's library costs nothing, and runs at `media prepare`, before any paid call |
| Near-duplicate detection by picture | `lookalike.py`: 64-bit difference hash, `video_hashes` for video segments (used at render, design/89 H6) | Can fingerprint a clip's frames for free, before analysis |
| Claude looking at a clip when the text is unclear | `vw options frames --sub S` (free still frames); `vw options inspect` (paid) | Use the free frames for the "look for clarification" step |
| Eligibility and crops for a new film | `clip_log/solver.py` `solve(log, policy, clip, timeline)` is pure, with no paid call | Re-solve a library clip under the new film's policy and frame shape |
| Place first, then recheck | options round 1 (exact matches) → round 2 (B-roll from this batch's unused clips) → the second look (`vw-scene-review` per scene with stills) | This is SK's Pass 1, step 1 and step 2 |
| Proposals the user can refuse | Review page / `vw master decide`: KEEP / REJECT / TRIM per shot; `alternatives` shown after a REJECT; an AI shot answered KEEP AI / Find footage | The UI for Pass 2 (section 6) |
| Render reading a clip from any key | `stage2/render_jobs.py:24` uses `clip['key']` when given | A library clip can render from its original film's storage key |

## 2. What does not exist today (gaps the requirement depends on)

1. **Images are not uploaded at `media`.** `media_prepare` accepts only `VIDEO_SUFFIXES` (`stages_av.py:14`). Images enter only at `visuals`, as `supplied` references tied to one element, and Gemini never studies them.
2. **The Gemini study is video-only and script-bound.** `build_request_clip_log` sends `video/mp4` with this film's beats, brief, client profile, speaker policy and timeline. The log's `primary_fit_for_beats` / `secondary_fit_for_beats` name *this film's* beats. The options package (`package.coverage`, `scene_fits`) is built from those fields.
3. **No cross-film reading of clips.** `options prepare` reads only this run's `analysis` outputs. Seven places read a clip as `{run_id}/media/{name}`, ignoring any other key:
   - `analysis_jobs.py:334` and `:412`
   - `stage2/stage.py:379` (`options frames`)
   - `stage3/delivery.py:224` and `:300` (the editor's package originals)
   - `visuals_stage.py:1936` (a frame reference from a clip) and `:4572`
4. **Runs are owner-only.** `core.load_run` refuses another owner's run, and the file route `/api/runs/{run_id}/files/{key}` refuses a key outside the run's prefix. A library shared by a brand crosses owners.
5. **No step between analysis and options** that waits for an answer.

---

## 3. Part A: the "which files are brand-generic" question

### Hidden requirements
- A1. **The step is a gate.** `options prepare` (or `vw next`) is refused until the question has been answered. "None" is a valid answer and is recorded like any other.
- A2. **Server function, both front ends** (CLAUDE.md "one flow, two front ends"). The shortlist and the recording live in one server function. The chat path calls it, and the page path calls it if a page ever shows it. It is not a procedure sentence only.
- A3. **Claude reads text first.** It reads the clip's summary card (`summary_card_lines`, `clip_overview`, `descriptive_name`, `editorial_ideas`, `entities`), not the full log (procedure rule: never read the full log). When the text is unclear, it uses the free `frames` first.
- A4. **What "generic" means needs a written test**, filed as a generic rule, not a documentary one. Proposal: a clip is generic when nothing in it ties it to this film's one event, so it would read true in another film of the same brand. Examples of what makes a clip *not* generic: a dated event, a named person speaking about this topic, a one-off site state. Examples of generic: the brand's premises, products, logo shots, staff at work, establishing shots.
- A5. **The answer is recorded with the operator's words** (`--quote`), like every other operator decision.
- A6. **Existing UI.** In chat that is the question tool: 2 to 4 options per question, at most 4 questions per message, `multiSelect`, plus "Other" for files Claude did not suggest. A shortlist of more than 16 files needs more than one message.
- A7. **Only analysed clips are offered.** A clip that is excluded, or failed, at analysis has no description. Decision needed (Q5).

### Edge cases and failure modes
| Case | Proposed handling |
|---|---|
| Batch of one clip, or every clip clearly film-specific | Claude says so in one line and asks "mark any anyway?" (A1 still records the answer) |
| Claude shortlists nothing | Same question, with no suggestions: the user can still name files |
| A huge batch (e.g. 60 clips) | Shortlist shown in groups of 4 per question, 4 questions per message; files named by clip name |
| The user names a file that does not exist in the batch, or names it ambiguously | Refused with the list of clip names; asked again |
| The user marks a clip that was excluded at analysis | Depends on Q5 |
| The user changes their mind after options started | Re-marking allowed at any time (section 4, B6); the current film's package is not rebuilt |
| Analysis re-run after marking (retry, recover, policy change) | The mark is kept by clip id (sha256); the library points at the newest retained log |
| A clip added to the batch after marking (media re-recorded) | The new clip is asked about before options can run again |
| The gate breaks a film already past analysis | Old ways: films already past `analysis` on release day skip the question. Their clips enter the library only if SK wants a backfill (Q7) |
| The recording call fails (network, server) | Nothing is half-written: the marks are saved in one transaction; the gate stays shut; Claude retries or reports |
| A defect is open on the run | Refused like every other write (design/48) |

---

## 4. Part B: the library store

### Hidden requirements
- B1. **Keyed by `client_id`**, never by owner. Any team member making a film for that client sees the brand's library. This crosses `load_run`'s owner check, so the library read needs its own client-scoped check.
- B2. **One row per file per brand** (sha256 + `client_id`), linked to the film or films it was uploaded for. The same file uploaded to two films of one brand is one library entry with two film links.
- B3. **What the row holds.** The server's rule (design, `analysis.py` header) is that nothing large lives in a database row. Proposal: the row holds the short description (`descriptive_name`, `clip_overview`, the summary card lines, `entities` names), the generic flag, the film link, the storage key of the media file, and the key of the evidence file holding the full Gemini log. SK's "all the Gemini descriptions" is then the row plus that one file.
- B4. **Every file of the batch is stored, generic or not** (part 1, 2.1). The non-generic rows still feed the near-duplicate check (Part C), but are never proposed in Pass 2.
- B5. **Contract version stored.** A log of an older clip-log contract cannot be read by a newer options package. A row whose contract is retired is skipped when proposals are made (old ways rule: name it as retired).
- B6. **Unmarking.** A wrong mark must be reversible: an "unmark" command and a re-mark. A film that already placed the clip keeps it.
- B7. **Files must outlive their film.** Closing a run (all films closed, memory 30 Oct) or deleting one by hand (VW-12) must not delete media a library row points at. Proposal: deleting a run by hand keeps its library media, or marks the row `missing`.
- B8. **Brand = client.** Part 1: never reused across clients. A client with several trade names (`dba_names`) is one brand unless SK says otherwise.

### Edge cases and failure modes
| Case | Proposed handling |
|---|---|
| A run with no `client_id` (an old run) | Nothing is stored, and the question is skipped with one line |
| A client renamed or merged in the directory | Keyed by `client_id`, so a rename changes nothing; a merge is a manual move (not covered) |
| Two films of one brand mark at the same time | Upsert on (client_id, sha256); the last mark wins; both film links kept |
| The same file is marked generic in film A and not in film B | Generic wins (it was marked once); B's answer adds the film link only |
| Storage write succeeds and the DB write fails, or the reverse | One transaction for the rows; the media is already stored under the film's key, so there is no new file write to fail |
| The evidence file for a log is missing in storage | The row is stored without it and is never proposed (no description to match) |

---

## 5. Part C: near duplicates

### Hidden requirements
- C1. **Check exact duplicates first:** a sha256 equal to a brand library row. This is free and certain, and runs at `media prepare`.
- C2. **Where "stopped at the processing stage" can happen.** A description exists only after the paid Gemini study, so a check built on descriptions cannot save the study's cost. Checks that can run *before* the paid call:
  - the sha256 match (C1),
  - the `lookalike` frame fingerprint (free, already in the code).

  Proposal:
  - At `media prepare`, list the duplicates and near duplicates with the library file each matches.
  - The operator decides per file: skip it (its library row is used instead, with no new analysis) or keep it.
  - The description is compared only as a second opinion after analysis (Q2).
- C3. **Brand only.** The same check never runs against another client's files.
- C4. **The thresholds are tuning knobs.** `BITS_PICTURE = 6` was tuned for re-encoded stills, and a moving clip needs its own value. Leave it as a named constant to tune on real footage.

### Edge cases and failure modes
| Case | Proposed handling |
|---|---|
| A trimmed or re-encoded copy of a library clip | Fingerprint match → listed as a near duplicate, never skipped silently |
| Two clips of the same place shot on different days (similar, not the same) | Fingerprint may match: the operator decides; nothing is dropped without them |
| A near duplicate *within* the batch, not in the library | Listed the same way (today only identical files are merged) |
| A flat or dark clip that cannot be fingerprinted (`dhash` returns None) | Not compared; never counted as a match |
| The skipped file was the better copy (higher resolution) | The listing shows both resolutions; the operator keeps it |
| The fingerprint step fails (ffmpeg error) | Reported per file; the upload carries on, unchecked |

---

## 6. Part D and E: Pass 1 and Pass 2 in options

### Pass 1 (Claude alone): already built
- D1. Pass 1 step 1 is options round 1 (exact matches), plus round 2 (B-roll from this batch's unused clips). Step 2 is the second look. **Nothing changes in Pass 1** unless SK wants this batch's own B-roll moved out of it (Q3).
- D2. **The library must not influence Pass 1.** The package read in rounds 1 and 2 holds this batch only, so this film's own footage is placed on its merits first.

### Pass 2 (proposals): new
- E1. **Matching library clips to this film's words.** A library log's beat fits name *another* film's beats. The options package cannot use them. Two ways:
  - (a) Claude matches from the stored description and the free frames. No paid call, but no `primary_fit` evidence.
  - (b) A new paid Gemini request per candidate library clip, against this film's script.

  Proposal: (a), labelled `match: library` with the description fields as evidence (Q4).
- E2. **Re-solve eligibility and crops** for every library clip under this film's policy (camera audio, waived flags, show speaker) and frame shape (16:9 or 9:16), with `solver.solve`. A clip ineligible here is never proposed.
- E3. **The server's rules apply unchanged:**
  - each clip once in the film,
  - no B-roll into a claim blank,
  - the shot-size steps, lighting and screen direction,
  - `max_usable_window`.
- E4. **Gap proposals:** library clips into blanks left after Pass 1.
- E5. **Swap proposals:** a library clip for a shot Pass 1 filled, only with a stated reason it serves the words better.
- E6. **Nothing is placed without a yes.** A rejected proposal returns the shot to its Pass 1 state (the current clip, or the blank).
- E7. **Existing UI, mapped.** Proposal:
  - A *gap* proposal is a footage shot carrying a new note kind `library` (KEEP / REJECT; REJECT → the blank).
  - A *swap* proposal shows the library clip as the shot, with the current clip as its alternative. REJECT brings back the current clip, as a rejected shot already brings back its kept alternative today.
  - Both appear on the review page and in `vw master decide`.
- E8. **The review page must play library clips.** That needs the file route and the render/frames/delivery paths to accept the original film's key (gap 3), checked by client, not by run.
- E9. **Rounds.** A proposal the user rejected is not offered again in the next options round unless the user asks.
- E10. **The editor's package lists library originals** with their source film, so an editor can find them (`stage3/delivery.py:224/300`).

### Edge cases and failure modes
| Case | Proposed handling |
|---|---|
| The brand has no library, or none eligible | Pass 2 says so in one line and is skipped |
| A large library (hundreds of clips) | The shortlist is filtered first by eligibility (E2) and by description text against the blank's `intent`; only the top few per blank reach Claude |
| A library clip that is the same file as one in this batch (sha256) | The batch copy wins; the library copy is never proposed beside it |
| A library clip's media is missing in storage (deleted run) | Never proposed; the row is marked `missing` |
| The library clip's frame rate or resolution differs from this film's | Handled as any batch clip (the render already conforms rates) |
| A library clip shows something the brief's brand or safety rules forbid now (rules changed since it was marked) | E2's re-solve applies the current rules; ineligible → not proposed |
| The user accepts a swap, then rejects the library clip in a later round | Back to the Pass 1 clip |
| Every proposal rejected | The film is exactly Pass 1 (part 1, 3.4) |
| A library clip is unmarked while a film is reviewing it | The film keeps the proposal it shows; new rounds no longer offer it |

---

## 7. Part F: images

- F1. Today there is no upload and no Gemini study for images at `media` (gap 1). "Images handled the same way" therefore means new work:
  - `media` accepts image files,
  - a Gemini *image* request with its own short description schema (the clip-log schema is video-shaped: sub-clips, time codes, audio),
  - images carried into options as still shots.
- F2. A still placed in the film needs a hold length and motion. The visuals stage already has stills with motion (`still`, `frame` references), so the shot form exists downstream.
- F3. SK's note "let us not complicate things there" is read as: images follow the same flow with the smallest new piece. Confirm under Q1.

---

## 8. Failure modes across the feature

| Failure | Handling |
|---|---|
| The server is restarted mid-question (a deploy) | The answer is recorded in one call; nothing is half-written; the gate stays shut until it is recorded |
| The library read fails at options | Options carries on with Pass 1 only, and says Pass 2 could not run; never blocks the film |
| Gemini key failure during analysis (defects 43-45) | Unchanged: no description → that clip is not shortlisted |
| A client's library grows past what a package can hold | Filtering in E-table row 2; a named constant for the cap |
| Two operators answer the same film's question at once | The run's advisory lock (`load_run(lock=True)`) serialises them |

---

## 9. Open questions for SK (one per message in chat)

1. **Images (F1).** Should images be uploaded and studied at `media` / `analysis` in this change, or is this change video-only, with images following later?
2. **Duplicate check timing (C2).** Should the duplicate check run *before* the paid study (sha256 + frame fingerprint, saves the cost), with the description comparison only as a second opinion after?
3. **Pass 1 B-roll (D1).** Today round 2 already fills blanks with B-roll from this batch. Does that stay in Pass 1, with the library as a new round after the second look?
4. **Matching library clips (E1).** Should Claude match library clips from the stored description and free frames (no paid call), or should a paid Gemini request re-study each candidate against the new script?
5. **Excluded clips (A7).** Can a clip excluded at analysis (not used in this film) still be marked brand-generic? It has a description only if its study succeeded.
6. **UI for proposals (E7).** Is the mapping acceptable: a gap proposal is a shot with a `library` note; a swap shows the library clip with the current clip as its alternative?
7. **Backfill.** Should the clips of films already made for a brand (VW-3 to VW-15) be offered for marking, or does the library start empty from the next film?
8. **Unmark (B6).** Who may unmark a library file: any team member on that brand, or only SK?

## 10. Not covered by this document

- **Cost figures.** The paid re-study in Q4(b) is not priced here.
- **Retention policy.** How long a closed brand's library is kept is not decided.
- **Merging two clients' libraries in the directory.** A manual job if it ever happens.
- **The web page for the marking question.** Part 1 says existing UI, which today is the chat question tool. A page is not proposed.
- **Server tests.** These need Docker with `postgres:17`; the test plan follows SK's approval of this list.

## 11. SK's answers (3 Nov 2026)

- **Q1 (images):** **Video first.** This change marks, stores and proposes video clips; images follow as a later change on the same library.
- **Q2 (duplicates):** **Before the study.** At media prepare, an exact match (sha256) and a near match by frame fingerprint are listed against the library file each matches; the operator decides per clip to skip it (its library row serves, no new paid study) or keep it. The description is compared after the study only as a second opinion.
- **Q3 (where the library sits):** **After the second look.** This film's own clips are placed and rechecked exactly as today; one new round then proposes library clips for the remaining blanks and as swaps.
- **Q4 (matching):** **From the stored description and the free stills, no paid call.** Proposals are labelled `library` with the description as evidence; the operator's yes is the check.
- **Q5 (excluded clips):** **Yes, when studied.** An excluded clip with a description can be marked; one whose study failed cannot.
- **Q6 (how proposals appear):** **The mapping as proposed.** A gap proposal is a shot marked `library` (Keep takes it, Reject leaves the blank); a swap shows the library clip as the shot with the current clip as its alternative (Reject brings the current clip back). The review page and `vw master decide` as they are.
- **Q7 (backfill):** **Start empty.** The library fills from each client's next film; a backfill of a chosen client can be asked for later as its own task.
- **Q8 (unmarking):** **Any team member on that client's films, with their words.** A film that already placed the clip keeps it.

All eight answered (3 Nov 2026). The build list follows in design/147.
