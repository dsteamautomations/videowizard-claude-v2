# 125 — Review of the whole flow on VW-11, stage by stage (started 29 Oct 2026)

SK and the assistant review every stage of VideoWizard on the film VW-11 ("Rat-Trap Bond Masonry - Documentary Explainer v6", client VK Nardep), one step at a time, from the first step that ran. Every change SK agrees is added here. **Nothing here is built until SK says so.**

## The flowchart (grows as we go)

```
[Script document from the client]
      ▼
1. Intake  ── kept narration ─────────────► Brief, Script, Voice
      │    ── removed duration lines ──────► Brief (the document's own timings)
      │    ── removed picture notes ───────► Visuals: treatment ("the team's intended picture" per scene)
      │    ── chosen title ────────────────► the run's name
      ▼
2. Brief   ── purpose, message, ending ────► Script stage (does the narration fit?)
      │    ── tone ────────────────────────► Voice (how the narration is spoken)
      │    ── chapters ────────────────────► Analysis (each clip tagged) and Options (scenes mapped)
      │    ── footage languages ⚠ ─────────► Analysis (what speech to listen for)
      │    ── speaker on camera ───────────► Analysis and Options
      │    ── frame shape, where it plays ─► the finished film
      │    ── client rules, directory ─────► every later stage
      ▼
3. Script  ── final spoken words ──────────► Voice (recorded from exactly these words)
      │    ── paragraphs as beats ─────────► BEAT_01 … used by options, master and visuals
      │    ── figures the message rests on ─ ✗ not passed on; the visuals stage researches
      │                                       its own facts (e.g. Scene 5's strength graphic)
      ▼
4. Voice   ── delivery direction (tags) ───► every tryout and the narration (⚠ opening tag doubled)
      │    ── final narration (301 s) ─────► Analysis, Options and Master (the film is cut to it)
      │    ── word timings per beat ───────► Options (where scenes and pauses fall), Visuals (gap times)
      ▼
5. Media   ── 46 clips (uploaded, not studied) ─► Analysis (one paid study per clip)
      │    ── camera sound allowed/excluded ⚠ ──► Analysis, Options, the film's sound
      │    ── originals or editor's copies ─────► Assembly hand-off (relink to the originals at the end)
      ▼
6. Analysis ── per clip: usable pieces, grades ─► Options (which footage goes where)
      │     ── per piece: best-fitting beats ────► Options and the coverage check
      │     ── people, speech, safety flags ─────► the tool's eligibility and crops
      │     ── chapter of each clip ─────────────► Options (scenes mapped)
      │     ⚠ only 8 clips at once (15 allowed); all 8 workers busy, nothing else can start
      ▼
7. Options  (next)
```

Where something has gone wrong: marked with ⚠ in the stage notes below.

---

## Before stage 1 — ⚠ VW-11 is on the old instructions

- **What I found (I read it in the database and on the server):** VW-11 was started at 18:15 on 29 Oct, after the new release went live (17:37), but it is on **instruction version 2**. The server's settings file still says version 2 (`VW2_DEFAULT_PROCEDURE_VERSION=2`), so every new film still starts on the old instructions.
- **Effect:** no effect on the intake (its instructions are identical in both versions). From the visuals stage on, VW-11 would get the old, untidied, unsplit instructions.
- **Done by SK (29 Oct 2026):** the settings line now reads 3 and the server restarted at 18:31 IST. I read it: the server's line says 3, and VW-11 and VW-10 are both on version 3 in the database.

## Stage 1 — Intake (reviewed 29 Oct 2026)

### What happened on VW-11
78 lines removed (document title, durations, 9 scene headings, the Visuals/Narration labels, the picture bullet lists); 35 lines of narration kept. Three titles offered; the operator chose title 1 ("Yes, title 1"). Ten duration lines kept aside for the brief; nine scenes of the team's intended pictures kept aside for the visuals stage. No AI call paid; about two minutes from start to approval.

### Findings
- Nothing paid, no keys, nothing to run in parallel.
- ⚠ The question "which picture AI does this film use (GPT Image or Nano Banana)?" is written inside the intake's steps, saying "ask before starting the run". The assistant reads the intake steps only after the run is started, so the sentence comes too late; the start instructions do not mention it. The same paragraph also carries picture-making details (14 pictures by kind, region edits, green background) that mean nothing at the intake.
- Change-history label in the text the AI reads: "(design/120)" in the intake steps.
- Small contradiction: the steps ask for "notes", the prompt's answer shape lists only removals and titles.
- Out of date: the operator command text calls version 2 "the current default".

### Agreed changes (SK, 29 Oct 2026: "make that into change documentation and keep it ready"; not built, SK starts the build)

All four go into **instruction version 3 only** (version 2 films keep their wording) and into the chat tool's text. None of them touches a shot's fingerprint, so nothing prepared goes stale. Nothing is paid.

#### Change I1 — The picture-AI question asked at the start, not inside the intake
- **The problem:** "Before `vw start`, ask the operator which image model this film uses" sits inside the intake's steps, which the assistant reads only after the film has been started. The start instructions never mention the question.
- **What changes:** the start instructions ask it: before starting a film, the assistant asks the operator which picture AI the film uses (GPT Image or Nano Banana), and says the choice is fixed for the film. The sentence leaves the intake steps.
- **The picture details** in the same paragraph (a Nano Banana prompt takes up to 14 pictures by kind: 6 of things, 5 of people, 3 of style; a region edit is said in words, with the server copying the start back outside the region; a component is made on chroma green, which the server keys out) are written only here today. They are **moved word for word** into the visuals instructions' "later" part (pictures), not deleted. They are reviewed again when we reach that phase.
- **For the builder:**
  - `server/procedures/v3.json`: in `intake.steps[2]`, cut from "Before `vw start`, ask…" to the end of the sentence about chroma green. Add the picture details to `visuals.parts.later` beside the other picture-request rules.
  - `plugin/commands/vw.md`, "Starting a run": add "Before `vw start`, ask the operator which picture AI this film uses, GPT Image or Nano Banana (`--images openai|gemini`); the choice is recorded on the run and never changes."
  - Tests: v3's intake steps no longer mention `--images`; the details appear exactly once in v3 (in `parts.later`); v2 is unchanged.

#### Change I2 — The change-history label removed
- **What changes:** "(design/120)" goes from the intake steps. The same label goes from the `--images` help text of `vw start`, which the assistant can read.
- **For the builder:** `server/procedures/v3.json` (intake steps) and `plugin/scripts/vw.py` (the `--images` help). Test: no "design/" in v3's intake text.

#### Change I3 — "notes" shown in the answer the AI writes
- **The problem:** the steps ask for `notes` (a short explanation of what was removed), and the record keeps it, but the prompt's example answer shows only `remove` and `titles`.
- **What changes:** the prompt's example answer gets `"notes": "a short explanation of what was removed"`, as in the answer shape.
- **For the builder:** `server/procedures/v3.json`, `intake.prompt`, the JSON example at the end. Test: the prompt's example and `output_shape` have the same three keys.

#### Change I4 — "version 2, the current default" corrected
- **What changes:** the operator command text says the options and master path is for version 2 **and 3**, and that version 3 is the current default (three places).
- **For the builder:** `plugin/commands/vw.md`, lines 38 ("moves to options (procedure version 2)"), 40 ("version 2 runs use options and master") and 44 ("procedure version 2, the current default"). No test; a wording check by eye.

#### Build rules (from SK's review prompt)
Tests first. A trace of old and new wording for I1–I3, with an independent check. No number lost (14, 6, 5, 3 in I1).

### Not covered
- Speaker names in a script (for example "RAVI:" before a person's line) would be kept as spoken words, under "when in doubt, keep it". This is not proposed: it is rare, and the operator sees the cleaned script before approving.

## Stage 2 — Brief (reviewed 29 Oct 2026)

### What happened on VW-11
The assistant proposed the five decisions (purpose, audience, message, tone, ending), nine chapters from the script, and the production values. This client has an earlier brief, so the assistant offered last time's answers; the operator replied "Same, approve" (one reply answered the question and approved). The audience came from the script, not the client directory (which says youth, volunteers, spiritual seekers and donors). This was correctly recorded as a difference. Target length left empty, so it comes from the narration (about 4,800 characters, roughly 5 minutes); the document's "5–6 minutes" was only a hint, as the rule says. Footage speech: Tamil; narration: English; speaker not shown. No AI call paid, about three minutes.

### Findings
- Nothing paid, no keys, nothing to run in parallel. The instructions are not over-constrained.
- ⚠ **"Nobody speaks in the footage" cannot be recorded.** The tool refuses an empty list of footage languages, so a film with silent footage, or no footage (design/122), forces the operator to name a language that isn't there. Further on, the analysis already treats an empty list as "English", so nothing breaks there.
- Out of date (from the first system, when a separate AI wrote the brief): "a malformed proposal gets at most one correction with this same prompt, then explain the issue and offer supplied input or a pause" and "do not silently accept model defaults". Today the assistant writes the file itself and fixes it until the tool accepts it.
- Label: the prompt's heading "VW-BRIEF v2.0".
- Written twice: what to ask the operator on every film is in the prompt and in the steps, and the steps' list leaves out "speaker on camera" and "where it plays and the frame shape". It is not a real disagreement, but the AI has to merge the two copies itself.

### Agreed changes (SK, 29 Oct 2026: "I approve … B1, B2, and B3"; not built, SK starts the build)

#### Change B1 — An empty list of footage languages allowed
- **What changes:** the operator can say "nobody speaks in the footage" (or "there is no footage"); it is recorded as an empty list. The question is still asked on every film; only the answer "none" becomes possible.
- **For the builder:** `plugin/scripts/stages_text.py`, `production_inputs`: a key that is present counts as answered (an empty `field_speech_languages` list allowed; `narration_language` still required). Procedure text (v3 brief steps): "the languages spoken in the footage (an empty list if nobody speaks or there is no footage)". Tests: an empty list is recorded; a missing key is still refused.

#### Change B2 — The first system's leftovers and the label removed
- **For the builder:** v3 brief prompt: remove "# VW-BRIEF v2.0", the "at most one correction…" sentence and "Do not silently accept model defaults." Test: none of the three is in v3's brief text; v2 unchanged.

#### Change B3 — One list of what to ask on every film
- **What changes:** the steps carry the one list: brand and safety rules, footage languages, narration language, speaker on camera, where it plays and the frame shape. The prompt keeps the principle ("these are the operator's words, asked on every film") and points to the steps.
- **For the builder:** v3 brief prompt and `steps[1]`. Trace old and new wording; no condition lost (16:9 and no destinations unless they say; muted or not; last time's answers as a recommendation, asked once).

## Stage 3 — Script (reviewed 29 Oct 2026)

### What happened on VW-11
The assistant checked the narration against the brief and proposed **no changes** (9 passages, 4,783 characters). Its assessment named three figures the message rests on, taken from the script and not checked: "nearly twenty-five percent fewer bricks", "up to three storeys", and minimum brick strengths of 20, 35 and 75 kg/cm² for one, two and three storeys. The operator replied "Keep, approve". The record split the text into 9 beats (BEAT_01 … BEAT_09), to which the voice is bound. No AI call paid, about three minutes. (I cannot see the chat on the operator's laptop, so I do not know whether a web check of the figures was offered.)

### Findings
- Nothing paid, no keys, nothing to run in parallel. Not over-constrained in practice: "no change" is allowed and happened.
- Leftovers from the first system, as in the brief (B2): "on malformed output make at most one correction…"; names of the first system's gates the AI has never seen ("normalize, check, remediate, filmability, lock or per-line tagging gates"; "VO/DIALOGUE/ACTION tagging"); the heading "VW-SCRIPT-PREPARATION v2.1".
- Written twice: "the record step rebuilds the text from the cleaned script plus the accepted changes and refuses anything else" is in the prompt and in the steps, and "verify the agreed changes are present" asks the AI to do what the tool already does.
- ✗ Not connected: the figures the message rests on are named here, then dropped. The visuals stage will need the same figures with a source (Scene 5's "graphic showing strength requirements for different building heights" shows exactly 20, 35 and 75 kg/cm²) and finds them again on its own.

### Agreed changes (SK, 29 Oct 2026: "Yes, approve all"; not built, SK starts the build)

#### Change S1 — The first system's leftovers and the label removed
- **For the builder:** v3 script prompt: remove the heading "# VW-SCRIPT-PREPARATION v2.1", the sentence "Do not reproduce normalize, check, remediate, filmability, lock or per-line tagging gates.", "Do not require VO/DIALOGUE/ACTION tagging of every physical line from the operator." and "On malformed output make at most one correction with this same prompt; then explain and offer user-supplied text or pause." Keep "Voice consumes the accepted prepared spoken text…". Test: none of these in v3's script text; v2 unchanged.

#### Change S2 — The tool's own check said once
- **What changes:** the "rebuilds the text… refuses anything else" rule stays in the steps only; the prompt's "Verify the agreed changes are present and all unaccepted changes are absent…" paragraph becomes one line: "The tool checks that only the accepted changes are applied; do not critique again."
- **For the builder:** v3 script prompt. Trace old and new wording; no condition lost.

#### Change S3 — The figures handed on to the visuals stage
- **What changes:** the script's record keeps the list of figures the message rests on, each with what the operator decided (checked on the web, or kept as the client's figure). The visuals preparation shows that list beside the narration, so a graphic shows the same figure the voice speaks, and a figure already checked is not searched again.
- **For the builder:** `out/script.json`: an optional `claims` list (text, checked: true/false, source when checked); `script_record` keeps it in the summary; `vw visuals prepare` writes it into the preparation files. Procedure text: one line each in the script steps and the visuals preparation part. Tests: claims recorded; claims shown in preparation; a script without claims records as today.
- **Fingerprint:** I did not find the preparation files in a shot's fingerprint; the builder confirms before building.

## Stage 4 — Voice (reviewed 29 Oct 2026)

### What happened on VW-11
First the delivery direction: the assistant wrote the "best fit" list of delivery tags (register [measured], with changes only at the turns: [confident], [with weight on the figures], [matter-of-fact], [thoughtful], [quietly proud]; 10 tags in all) and three test passages; the chosen test passage is the brick-strength figures. On the voices page two voices were tried on that passage ("UD - Narrator" and "Reyaansh – Deep, Gripping Suspense Voice"), then one full narration with Reyaansh on Eleven v4 (stability 0.5, similarity 0.75). SK made it final on the page. 301 seconds, 9 beats, the whole script (4,783 characters; ElevenLabs billed 2,179 characters, its own count). About ten minutes.

### Findings
- ⚠ **The opening tag is said twice.** The narration text starts "[measured] [measured] As the demand…". The tool puts the film's register at the top, and the assistant also tagged the first sentence [measured]. Probably harmless to the sound (tags are not spoken), but it is the kind of repeat the direction prompt forbids ("a tag only where the delivery changes"), and the AI cannot see that the tool adds the top one.
- **Two copies that disagree:** the voice prompt says a tryout passage is "about 45 to 70 words"; the direction prompt and the tool say 50 to 100 words. The tool refuses outside 50 to 100, so that copy wins.
- **Written twice:** the chat-only way of choosing a voice (four questions, catalogue, audition) is in the prompt and again in the steps, in different words.
- **Labels:** "VW-VOICE v4", "VW-DIRECTION v1" and "(design/54 B)" in the text the AI reads.
- **Keys and parallel work:** tryouts and narrations are separate jobs picked up by the workers at the same time (the two VW-11 tryouts started together). One ElevenLabs key; no more needed for one film at a time.
- **Fingerprint:** nothing here is part of a shot's fingerprint. The direction's own record is made from the register and the tags chosen, not from the text sent, so V1 does not mark the VW-11 narration stale.

### Agreed changes (SK, 29 Oct 2026: "Yes, approve all"; not built, SK starts the build)

#### Change V1 — A tag that repeats the one already in force is not sent
- **What changes:** when a sentence's tag is the same as the one already in force (the register at the top, or the previous tag), the tool leaves it out of the text it sends. One line in the direction prompt: "the register is placed at the top for you; do not repeat it on the first sentence."
- **For the builder:** `server/app/voice_direction.py`, `apply`: skip a tag equal to the tag in force at that point. Direction prompt (v3). Tests: register [measured] plus a first-sentence [measured] gives one tag; a different first tag is kept; `digest` unchanged for the same direction.

#### Change V2 — One copy of the chat path, with the tool's word limits
- **What changes:** the prompt keeps the principles (recommend from the brief; never infer accent, gender, age or nationality from the client's name; only the operator's listening decides; paid steps are information, not a question; jobs never resubmitted). The chat path's how-to stays in the steps only. "About 45 to 70 words" becomes "the chosen test passage (50 to 100 words)".
- **For the builder:** v3 voice prompt (FIND and COMPARE paragraphs) and steps. Trace old and new; no condition lost (one to six voices, 3,000 characters, one question per message, the four values repeated for a yes, at most three narrations).

#### Change V3 — Labels removed
- **For the builder:** v3 voice prompt and direction prompt headings; "(design/54 B)" in the steps. Test: no "design/" or version heading in v3's voice text.

## Stage 5 — Media (reviewed 29 Oct 2026)

### What happened on VW-11
46 clips, 13 min 23 s of footage, 919 MB, uploaded in about ten minutes, three at a time. Two frame rates (25 and 50 frames a second), all with a timecode. Camera sound: **excluded** from the film ("can be used for analysis in the next steps"). Clips: **editor's copies** ("camera originals but compressed … the originals are identified by a handover file … at the very last step"), which matches the hand-off and relink already designed (design/107). Nothing paid; nothing studied yet.

### Findings
- Nothing paid, no keys. Parallel work: uploads already run three at a time; on VW-11 the operator's internet is the likely limit, so no change proposed.
- ⚠ **The camera-sound question can be skipped.** The stage's instructions ask it once and the tool takes the answer, but the tool does not require it (it does require the originals-or-copies answer), and the operator command text's media paragraph does not mention the question or its flag at all. An assistant following that paragraph records no answer, and the analysis then has to ask again or guess. On VW-11 it was asked and answered.
- **Written twice:** the tool's facts (200 MB a clip, frame-rate conversion, three uploads at a time, resume by running record again) are in the prompt and again in the steps.
- **Label:** "(design/107)" in the steps.
- **Film types:** a film with no footage gets stuck at this stage today; design/122 already skips it for such a film. Nothing to add here.
- **Fingerprint:** nothing here is part of a shot's fingerprint.

### Agreed changes (SK, 29 Oct 2026: "Yes, approve both"; not built, SK starts the build)

#### Change M1 — The camera-sound answer required, like the copies answer
- **What changes:** the tool refuses to record the media without the operator's answer on camera sound (allowed or excluded), with the same kind of message as the copies question. The operator command text's media paragraph names both questions.
- **For the builder:** `plugin/scripts/stages_av.py`, `media_record`: refuse when `camera_audio` is not allowed/excluded ("Ask the operator once: may the camera sound be used in the film? Then `--camera-audio allowed` or `--camera-audio excluded` with `--note`"). `plugin/commands/vw.md` media paragraph: add the question and `--camera-audio … --note`. Tests: record refused without it; recorded with it.

#### Change M2 — The tool's facts written once, and the label removed
- **For the builder:** v3 media prompt keeps the rules (names and bytes preserved; a probe is not an analysis; identical files once; the camera-sound question); the facts stay in the steps only. Remove "(design/107)". Trace old and new; no number lost (200 MB, three at a time, 30 minutes).

## Stage 6 — Analysis (reviewed 29 Oct 2026, while it was running)

### What happens
For each clip, one paid request to Gemini 3.8 Flash: it watches the clip and writes a detailed log (the usable pieces with exact in and out points and a grade, the people and any speech with a translation, camera movement, the chapter, which narration beats each piece fits, safety flags such as missing helmets) plus a 10-line summary card. The tool, not the AI, then decides what may be used and how to crop around a speaker. Nothing to approve; failed clips are retried or left out on the operator's word.

### What happened on VW-11 (at 19:58, while running)
46 clips queued at 19:56: 1 finished, 8 being studied, 37 waiting. The first (a 3.8-second clip of a finished brick vault) took 2 minutes: one usable piece, grade B, fits beats 3 and 9, no people, the camera's chatter muted (camera sound excluded at media). Its request used about 54,000 extra "look again" tokens for a 4-second clip.

### How it ended (checked at 20:35)
45 clips retained, 1 failed: C0119 (27 s), "Provider reported an error in its stream; no retry was made". The run waits for the operator: retry it or leave it out (`vw analysis retry` / `exclude`, on their word). 34 minutes in all; on average 5 minutes and about 390,000 extra "look again" tokens a clip. 28 of the 45 are 15 seconds or shorter, and those still averaged 4 min 40 s and about 290,000 extra tokens each (A2's gain).

### Findings
- ⚠ **Keys and parallel work (points 8 and 9): only 8 clips run at once, not 15.** The server is set to allow 15 analysis calls at once, but it has only 8 workers (each running one job), so 8 is the real limit. While VW-11's analysis runs, all 8 workers are taken: nothing else (a voice tryout, a picture or a render for another film) can start until clips finish. The server has room: 4 processors, 15 GB of memory, about 1 GB in use; an analysis worker mostly waits for Gemini. Keys: 5 Gemini keys used in turn; 15 at once is 3 per key, and 10 and 20 at once were tested clean earlier (design/35 row 29). No more keys needed.
- **Every clip is studied in "agentic" mode** (the AI may look again at parts of the clip), even a 4-second one. A setting that would switch this on only for clips over 5 minutes exists but is overridden. A proposal of 15 Oct (design/18 item 3: short clips of 15 s or less studied in the plain mode, after a paid comparison on three short clips shown to SK) was never done. On VW-2 the agentic mode cost 200,000 to 780,000 extra tokens per clip almost regardless of length. On VW-11, 28 of 45 clips are 15 seconds or shorter.
- **Out of date:** the operator command text says "up to fifteen clips run at a time" (8 today). It is true again with A1.
- **Jargon in the text the AI reads:** "the blueprint Stage 1 contract (clip-log-v1)" means nothing to the assistant at this step.
- The prompt sent to Gemini has no change-history labels and no contradiction with the stage's steps (I read it). Changing that prompt changes every clip's request record, so a re-analysis would not reuse the old logs: no change to it is proposed.
- **A provider error is not retried by itself** (1 clip of 46 on VW-11): the operator retries it with one command. Left as it is: rare, and a retry is paid.
- **Fingerprint:** nothing here is part of a shot's fingerprint.

### Agreed changes (SK, 29 Oct 2026: all three; A2 with no comparison test, "I'm convinced by your reasoning"; not built, SK starts the build)

#### Change A1 — Enough workers for 15 clips at once, with room to spare
- **What changes:** the live server runs 18 workers instead of 8: 15 for clip studies, 3 kept free so a voice, a picture or a render never waits behind an analysis. On VW-11 (45 clips at about 5 minutes each) the analysis took 34 minutes with 8 at once; with 15 at once it would take about 16, and less with A2.
- **For the builder:** VM `server/.env`: `VW2_WORKERS=18` (SK sets it, as with the version line); then a worker restart, which waits for running jobs to finish (up to 40 minutes): do it when no analysis is running. Check after: `vw analysis status` on the next film shows up to 15 running. If 15 analysis calls must leave room by rule, the server's start-up could warn when workers are fewer than the analysis cap plus 3 (one line); not proposed unless SK wants it.

#### Change A2 — Short clips studied in the plain mode, after a comparison
- **What changes:** clips of 15 s or less are studied in the plain mode; longer ones keep agentic. No comparison test first (SK, 29 Oct 2026). Applies to the next film; a running analysis keeps its mode.
- **For the builder:** procedure setting (v3 analysis) `processing_mode: auto` with `agentic_over_seconds: 15`. Tests: a 15 s clip is STATIC, a 15.1 s clip AGENTIC; a job already queued keeps its frozen mode. Not covered: whether the plain mode finds as many usable pieces on short clips (SK chose not to test first); watch the first film's short-clip logs.

#### Change A3 — Wording
- **For the builder:** `plugin/commands/vw.md`: "up to fifteen clips at a time" stays (true after A1). v3 analysis steps: "The log follows the blueprint Stage 1 contract (clip-log-v1)" removed.


#### Change A4 — A clip that fails for a passing reason is retried by itself, up to three times (SK, 29 Oct 2026)
- **SK's words:** "an auto retry of up to three trials can be factored in instead of waiting for the user to come and click the retry."
- **What changes:** a clip study that fails for a passing reason is put back in the queue by the server, up to **three automatic retries** after the first try (four tries in all), each on the next Gemini key. Only after the third automatic retry fails does the clip wait for the operator, as today.
- **Passing reasons (retried):** the provider's error inside its stream (VW-11's C0119); an answer cut off or empty; a busy or rate-limited service (HTTP 429 or 503; today's single "capacity retry" is folded into the three).
- **Not retried (the same request would fail the same way, and each try is paid):** a request the provider refuses as wrong (HTTP 400, 401, 403, 404, 413), a spending or billing limit with only one key, an answer blocked for safety, an answer that does not match the form or the clip, an answer kept unstructured, a failure on our side before the request was sent, and an outcome unknown after sending (it may already have been paid: recovered from its receipt, as today).
- **Edge cases:** the count follows the clip, not the row, so a retry never resets it; an operator's explicit retry (`vw analysis retry`, at most as today) is one paid try with no automatic retries after it; an automatic retry is not counted as an operator retry; a running analysis is not disturbed (a retry is a new queued row, as the capacity retry is today); no wait between tries (the next key is used; a rate-limited key is already cooled).
- **For the builder:** `server/app/analysis_jobs.py`, `finalize`: the capacity-retry branch becomes one rule for the passing reasons with `auto_retries` (1 to 3) and `auto_retry_of` on the new row's request; `retry_of`/`retry_note` not copied onto an automatic row. v3 analysis steps: one sentence. Tests: a stream error queues retry 1, then 2, then 3, and the fourth failure queues nothing; a blocked answer, a 400 and an unknown outcome queue nothing; an explicit retry's failure queues nothing; the operator's retry count ignores automatic rows.
- **Not covered:** money: in the worst case a clip is paid four times instead of once.

---

## The build (29 Oct 2026, on SK's word: "group the recommendations … and run one build"; commit, no deploy until SK approves)

Built together: I1–I4, B1–B3, S1–S3, V1–V3, M1–M2, A2–A4. **A1 is not code:** SK sets `VW2_WORKERS=18` in the VM's `server/.env` at deploy time (a worker restart, when no analysis is running).

### What was built
- **Wording, version 3 only** (`scripts/d125_wording_v3.py`, 29 exact replacements and 2 settings; trace `design/125-wording-trace.md`): I1 (the picture-AI question out of the intake; its details now in the visuals "later" part: 6 of things, 5 of people, 3 of style, the region said in words, chroma green), I2, I3, B1–B3, S1–S3, V1–V3, M2, A2 (`processing_mode: auto`, agentic over 15 s), A3, A4. Version 2 untouched. `scripts/c1_split_v3.py --check` passes (it now applies the two visuals sentences after the C2 fixes).
- **Server:** V1 (`voice_direction.apply`: a tag equal to the one in force is not sent; the direction's digest unchanged); S3 (`visuals_stage.script_claims`, the package's `script_claims`); A4 (`analysis_jobs.finalize` and `passing_failure`: up to three automatic retries; the stream-error message no longer says "no retry was made"). Server 0.75.0.
- **Chat tool:** B1 (`production_inputs`: an empty list of footage languages is an answer); M1 (`media_record` refuses without the camera-sound answer); S3 (`script_record` keeps `claims`, checked; `claims.json` in work/visuals/); I2 (the `--images` help); `commands/vw.md` for I1, I4, M1. Plugin 0.62.0.
- **Tests:** new `server/unit/test_design125_pure.py` (26) and `plugin/tests/test_design125.py` (6); four older tests changed to the agreed rules (an empty footage-language list now allowed; the camera-sound answer now required; claims.json in the package listing; the split check knows the design/125 stages). Server unit 817 passed; plugin 336 passed, 3 known Windows-only failures.
- **Independent check** (a helper that did not write the wording, comparing the trace with the change field by field): every replacement matches its agreed change; no number, condition, command or flag lost. Three small slips fixed: the Gemini region sentence moved after the `--region` sentence it adds to; "the provider's sample of every voice" and "one exact contiguous excerpt" restored; "finished clips are skipped" restored in the media steps (29 replacements in all). Left as they are: the `prompt_origin` labels (never sent to the AI), and two older tensions this change did not create (the brief's "do not require destination… to finish" against asking where it plays; the voice's "gender and age only if the operator cares" against the chat path asking them).
- **Numbers check:** every number missing from version 3 after the change is a change-history or version label (design/120, 54, 107; v2.0, v2.1, v4, v1; clip-log-v1, Stage 1), "45 to 70" replaced by "50 to 100" (V2), 300 replaced by 15 (A2), or a second copy whose first copy stays (14 pictures, 200 MB).

### Not covered
- Server tests that need Docker (`server/tests`): not run here.
- Python 3.9 for the chat tool: compiled under 3.12 only.
- A2 without a comparison (SK's choice): watch the first film's short-clip logs.
- A4 in the worst case pays four times for one clip.
- **Deployed 30 Oct 2026** on SK's word (design/35 row 113): server 0.75.0, plugin 0.62.0; version 3 on the live server carries the new wording (checked: agentic over 15 s, the automatic-retry step, no brief label). A1 done the same day on SK's word: `VW2_WORKERS=18` in the VM's `server/.env`, server and workers restarted with nothing running; 18 worker processes up.
- Before the deploy it read: On deploy: SK sets `VW2_WORKERS=18` (A1) in the VM's `server/.env`; the restart waits for running jobs; the plugin deploy needs the operator's Claude Code restart and the Vw switch turned off in the desktop app's list afterwards. Films already on version 3 (VW-10, VW-11) read the new wording from their next step.
