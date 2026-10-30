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
- **Older way:** retired in this release for version 3 (the intake no longer asks; the details moved to the pictures part). Version 2's intake text: kept until instruction version 2 is retired (old-ways list, item 1), because films on version 2 keep their own text.
- **The problem:** "Before `vw start`, ask the operator which image model this film uses" sits inside the intake's steps, which the assistant reads only after the film has been started. The start instructions never mention the question.
- **What changes:** the start instructions ask it: before starting a film, the assistant asks the operator which picture AI the film uses (GPT Image or Nano Banana), and says the choice is fixed for the film. The sentence leaves the intake steps.
- **The picture details** in the same paragraph (a Nano Banana prompt takes up to 14 pictures by kind: 6 of things, 5 of people, 3 of style; a region edit is said in words, with the server copying the start back outside the region; a component is made on chroma green, which the server keys out) are written only here today. They are **moved word for word** into the visuals instructions' "later" part (pictures), not deleted. They are reviewed again when we reach that phase.
- **For the builder:**
  - `server/procedures/v3.json`: in `intake.steps[2]`, cut from "Before `vw start`, ask…" to the end of the sentence about chroma green. Add the picture details to `visuals.parts.later` beside the other picture-request rules.
  - `plugin/commands/vw.md`, "Starting a run": add "Before `vw start`, ask the operator which picture AI this film uses, GPT Image or Nano Banana (`--images openai|gemini`); the choice is recorded on the run and never changes."
  - Tests: v3's intake steps no longer mention `--images`; the details appear exactly once in v3 (in `parts.later`); v2 is unchanged.

#### Change I2 — The change-history label removed
- **Older way:** retired in this release (the label is removed).
- **What changes:** "(design/120)" goes from the intake steps. The same label goes from the `--images` help text of `vw start`, which the assistant can read.
- **For the builder:** `server/procedures/v3.json` (intake steps) and `plugin/scripts/vw.py` (the `--images` help). Test: no "design/" in v3's intake text.

#### Change I3 — "notes" shown in the answer the AI writes
- **Older way:** retired in this release (the example is replaced).
- **The problem:** the steps ask for `notes` (a short explanation of what was removed), and the record keeps it, but the prompt's example answer shows only `remove` and `titles`.
- **What changes:** the prompt's example answer gets `"notes": "a short explanation of what was removed"`, as in the answer shape.
- **For the builder:** `server/procedures/v3.json`, `intake.prompt`, the JSON example at the end. Test: the prompt's example and `output_shape` have the same three keys.

#### Change I4 — "version 2, the current default" corrected
- **Older way:** retired in this release (the old wording is replaced).
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
- **Older way:** retired in this release (an empty list was refused; now it is an answer).
- **What changes:** the operator can say "nobody speaks in the footage" (or "there is no footage"); it is recorded as an empty list. The question is still asked on every film; only the answer "none" becomes possible.
- **For the builder:** `plugin/scripts/stages_text.py`, `production_inputs`: a key that is present counts as answered (an empty `field_speech_languages` list allowed; `narration_language` still required). Procedure text (v3 brief steps): "the languages spoken in the footage (an empty list if nobody speaks or there is no footage)". Tests: an empty list is recorded; a missing key is still refused.

#### Change B2 — The first system's leftovers and the label removed
- **Older way:** retired in this release (the sentences are removed).
- **For the builder:** v3 brief prompt: remove "# VW-BRIEF v2.0", the "at most one correction…" sentence and "Do not silently accept model defaults." Test: none of the three is in v3's brief text; v2 unchanged.

#### Change B3 — One list of what to ask on every film
- **Older way:** retired in this release (two lists became one).
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
- **Older way:** retired in this release.
- **For the builder:** v3 script prompt: remove the heading "# VW-SCRIPT-PREPARATION v2.1", the sentence "Do not reproduce normalize, check, remediate, filmability, lock or per-line tagging gates.", "Do not require VO/DIALOGUE/ACTION tagging of every physical line from the operator." and "On malformed output make at most one correction with this same prompt; then explain and offer user-supplied text or pause." Keep "Voice consumes the accepted prepared spoken text…". Test: none of these in v3's script text; v2 unchanged.

#### Change S2 — The tool's own check said once
- **Older way:** retired in this release.
- **What changes:** the "rebuilds the text… refuses anything else" rule stays in the steps only; the prompt's "Verify the agreed changes are present and all unaccepted changes are absent…" paragraph becomes one line: "The tool checks that only the accepted changes are applied; do not critique again."
- **For the builder:** v3 script prompt. Trace old and new wording; no condition lost.

#### Change S3 — The figures handed on to the visuals stage
- **Older way:** retired in this release (a script recorded without claims reads as none; nothing to keep).
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
- **Older way:** retired in this release (the repeated tag is no longer sent).
- **What changes:** when a sentence's tag is the same as the one already in force (the register at the top, or the previous tag), the tool leaves it out of the text it sends. One line in the direction prompt: "the register is placed at the top for you; do not repeat it on the first sentence."
- **For the builder:** `server/app/voice_direction.py`, `apply`: skip a tag equal to the tag in force at that point. Direction prompt (v3). Tests: register [measured] plus a first-sentence [measured] gives one tag; a different first tag is kept; `digest` unchanged for the same direction.

#### Change V2 — One copy of the chat path, with the tool's word limits
- **Older way:** retired in this release (one copy of the chat path).
- **What changes:** the prompt keeps the principles (recommend from the brief; never infer accent, gender, age or nationality from the client's name; only the operator's listening decides; paid steps are information, not a question; jobs never resubmitted). The chat path's how-to stays in the steps only. "About 45 to 70 words" becomes "the chosen test passage (50 to 100 words)".
- **For the builder:** v3 voice prompt (FIND and COMPARE paragraphs) and steps. Trace old and new; no condition lost (one to six voices, 3,000 characters, one question per message, the four values repeated for a yes, at most three narrations).

#### Change V3 — Labels removed
- **Older way:** retired in this release.
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
- **Older way:** retired by refusal in this release: record without the camera-sound answer is refused, naming `--camera-audio allowed|excluded`.
- **What changes:** the tool refuses to record the media without the operator's answer on camera sound (allowed or excluded), with the same kind of message as the copies question. The operator command text's media paragraph names both questions.
- **For the builder:** `plugin/scripts/stages_av.py`, `media_record`: refuse when `camera_audio` is not allowed/excluded ("Ask the operator once: may the camera sound be used in the film? Then `--camera-audio allowed` or `--camera-audio excluded` with `--note`"). `plugin/commands/vw.md` media paragraph: add the question and `--camera-audio … --note`. Tests: record refused without it; recorded with it.

#### Change M2 — The tool's facts written once, and the label removed
- **Older way:** retired in this release.
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
- **Older way:** retired in this release (8 workers became 18).
- **What changes:** the live server runs 18 workers instead of 8: 15 for clip studies, 3 kept free so a voice, a picture or a render never waits behind an analysis. On VW-11 (45 clips at about 5 minutes each) the analysis took 34 minutes with 8 at once; with 15 at once it would take about 16, and less with A2.
- **For the builder:** VM `server/.env`: `VW2_WORKERS=18` (SK sets it, as with the version line); then a worker restart, which waits for running jobs to finish (up to 40 minutes): do it when no analysis is running. Check after: `vw analysis status` on the next film shows up to 15 running. If 15 analysis calls must leave room by rule, the server's start-up could warn when workers are fewer than the analysis cap plus 3 (one line); not proposed unless SK wants it.

#### Change A2 — Short clips studied in the plain mode, after a comparison
- **Older way:** retired for version 3 (short clips no longer agentic). Version 2's setting: kept until instruction version 2 is retired (old-ways list, item 1), because films on version 2 keep their own text.
- **What changes:** clips of 15 s or less are studied in the plain mode; longer ones keep agentic. No comparison test first (SK, 29 Oct 2026). Applies to the next film; a running analysis keeps its mode.
- **For the builder:** procedure setting (v3 analysis) `processing_mode: auto` with `agentic_over_seconds: 15`. Tests: a 15 s clip is STATIC, a 15.1 s clip AGENTIC; a job already queued keeps its frozen mode. Not covered: whether the plain mode finds as many usable pieces on short clips (SK chose not to test first); watch the first film's short-clip logs.

#### Change A3 — Wording
- **Older way:** retired in this release.
- **For the builder:** `plugin/commands/vw.md`: "up to fifteen clips at a time" stays (true after A1). v3 analysis steps: "The log follows the blueprint Stage 1 contract (clip-log-v1)" removed.


#### Change A4 — A clip that fails for a passing reason is retried by itself, up to three times (SK, 29 Oct 2026)
- **Older way:** retired in this release: the single capacity retry is folded into the three automatic retries; old rows keep `capacity_retry_of` only as history (never read).
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

---

## Stage 7 — Options, and the review page (started 30 Oct 2026, from SK's screenshot of VW-11's review page)

### What happened on VW-11
- The failed clip C0119 was retried by the operator on 29 Oct (21:17 IST) and kept at 21:23.
- **Options prepare** 21:24:45; **scenes approved** 21:27:02 ("Yes, approve", 9 scenes, no pauses); the assistant (Claude, in the operator's chat, not Gemini: Gemini wrote the clip logs at the analysis) then wrote the whole first cut, passed the tool's check and sent it to render at **21:32:15**: about **5 minutes** for 9 scenes and 46 clips. Render 2.5 minutes. The operator's first answer (#1A KEEP, 21:44) approved the options.
- The cut: 7 options for 9 scenes (scenes 3 and 4 declared blank), **no backups**, 40 slides: 7 scene slides, 14 decisions, 19 blanks; 41 flags from the tool's check; 292.9 s.

### How the slides are numbered today (I read it in the code)
- Each **option** (the assistant's whole edit of one scene) gets the next running number; a **backup** (a second edit of the same scene) gets the next number too, labelled "BACKUP for #N". Inside an option, the **decisions** (a piece the operator should keep or drop: B-roll, reuse, check by eye, poor quality, a doubtful join) and the **blanks** (a stretch left for AI video or animation) get the option's number and a letter in film order: 1A, 1B, 1C…
- Answers: a scene slide takes Keep, Reject (the whole scene becomes AI-filled, or its backup is used) or Keep with edit (trim or shift a shot); a decision takes Keep or Drop (a dropped piece becomes a blank); a blank takes none.

### Findings
- ⚠ **The scene slide repeats its own decisions.** Scene 1 has two pieces of footage and both are decisions (1A, 1C); its "1" row asks Keep, Reject or Keep with edit about the same two pieces. Its answer and theirs can disagree (Keep 1 and Drop 1A and 1C). A scene row is useful only for footage the assistant was sure of (no question asked about it), and for trims.
- ⚠ **Slide numbers are not scene numbers.** A scene declared blank takes no number, so on VW-11 slide #3 is Scene 5 and slide #7 is Scene 9; with a backup, every later number shifts by one more.
- **Backups:** none on VW-11. Today a backup of scene 2 would appear as the next number ("#3 BACKUP for #2"), which reads as a different scene.
- **One pass, many decisions at once:** the assistant chose every piece for every scene in a single pass of about 5 minutes; nothing asks it to look again before the operator sees the film.
- **Which Claude model and thinking level wrote the options (SK's question, 30 Oct):** VideoWizard does not set either. Neither the plugin nor the operator folder's settings name a model or a thinking level (I read both), so it is whatever is chosen in the Claude app on the operator's laptop (VW-11 ran on Uma's laptop, which I cannot see).
- **How the assistant reads at this step today:** the whole film at once: the instructions (about 1,100 words), the narration, every clip's 10-line card and every usable piece's row, 25 rows a file (about 17,000 words of reading per file on VW-6), then all 9 scenes written in one go.

### Proposed for the second look (waiting for SK, one question at a time)
- **O0 — Pin the model and the thinking level** in the operator folder's settings, so every operator machine works the same (the strongest model, high thinking), instead of whatever each laptop has chosen. **Older way:** retired in this release (each laptop's own model and level replaced by the folder settings).
  - **Agreed (SK, 30 Oct 2026: "High everywhere"):** Claude Opus 5.5 at high thinking for every step. For the builder: the operator folder's `.claude/settings.json` gets `"model": "claude-opus-5-5"` and `"effortLevel": "high"` (on every operator machine, and in the operator setup guide, `vw2-operator-setup-windows.md` and `-mac-windows.md`); the plugin's helpers (O6) declare `model: opus` and `effort: high`; never set `CLAUDE_CODE_EFFORT_LEVEL` on an operator machine (it overrides every level). Test on one operator laptop, in the desktop app's Code tab, that the session shows Opus 5.5 and high before rolling out.
- **O4 — A second look, scene by scene, with only that scene in front of the assistant:** after the tool's check passes and before the film is rendered, the tool writes one small file per scene: its narration sentence by sentence with times; the pieces chosen for it; every other piece whose notes say it fits that scene (direct match first), with its "what is seen" line. The assistant takes one scene at a time and, for each shot, puts the sentence and the picture side by side: does the picture show what the words say, at that moment? is there a better piece not chosen? does the cut fall where an action ends?
- **O5 — Look at the pictures, not only the notes:** for every chosen piece and every decision, the assistant looks at a few still frames (free; the tool already makes them) before keeping it.
- **O6 — Helpers, one scene each, at the same time:** the second look for each scene done by a separate helper given only that scene's file and frames (as design/124 Change 9 does for the visuals plan); the main assistant joins their fixes and runs the tool's check again. Same time as one scene, fresh attention per scene.
- **Measured first pass:** about 5 minutes for 9 scenes; the second look is expected to add about as much again, with no paid call.

### SK's questions of 30 Oct (model per step; several shots under one sentence)

**Model and thinking per step: what Claude Code allows (checked in its documentation by a helper, 30 Oct):**
- The operator folder's settings can set the model (`"model"`) and the thinking level (`"effortLevel"`: low, medium, high, xhigh) as the default for every session started there. The operator can still change them during a session; only an organisation-wide (admin) setting can lock them. The plugin itself cannot set them.
- A step can run at its own model and thinking level by handing it to a **helper** shipped with the plugin (its definition names the model and the level), or through the step command's own settings for that turn (to be tested). Claude Opus 5.5 defaults to medium thinking.
- Not confirmed: that the desktop app's Code tab honours the folder's model and thinking settings: to be tested on one operator machine.

**Several shots under one sentence (counted on VW-11's first cut, on the server):**
- 45 sentences: 22 have real footage, 23 are left for AI pictures. Of the 22: 13 have one shot, 7 have two, 2 have three. **9 sentences combine shots from different clips**: encouraged by the instructions ("several short real shots may run together; 2 to 3.5 s each is normal").
- **Two parts of the same clip: none.** 28 shots from 28 different clips. The instructions forbid it unless the operator approves each case: "each clip appears once in the film … any other second use, including another part of the same clip, is a decision of kind reuse". So the setup SK used before (two moments of one long clip under one sentence) is actively discouraged today.

#### Proposed O7 — Two moments of one clip allowed inside one scene
- **Older way:** retired in this release (a same-scene second part is no longer a reuse question; reuse elsewhere stays a question).
- **What changes:** a second part of the same clip may be used without a question when it is in the same scene, does not overlap the first part, and shows a later moment of the action (the start of the course, then the finished course). Two such parts never sit side by side unless the shot size changes (the existing rule against a jump cut); otherwise another shot goes between. A use in another scene stays a reuse question, as today.
- **For the builder:** options instructions (rule 4) and the tool's reuse check: a same-scene, non-overlapping second part is not a reuse; the "same size side by side" check covers the jump cut.

#### O1 — A scene row asks only what its parts do not (agreed, SK 30 Oct 2026: "Yes, remove them")
- **Older way:** kept until VW-11's master is recorded, because its 13 answers were given on the old rows; from the next film, retired (Keep/Reject on such a scene row refused, naming its parts).
- **What changes:** when every piece of footage in a scene already has its own question (a decision), the scene row shows no Keep / Reject: its parts decide it (on VW-11, Scene 1: 1A and 1C). When some footage was used without a question, the scene row keeps Keep / Reject (the only place to turn that footage down). "Trim a shot" (today's Keep with edit) stays on every scene row.
- **For the builder:** `stage2/slides.py`: a scene slide records whether it has any shot without a decision (`sure_shots`); `stage2/stage.py` `needs_answer`: a scene slide with none needs no answer and is kept unless all its decisions are dropped (then it becomes blank, as today's dropped pieces do); `master decide` refuses Keep/Reject on such a slide by name and still takes a trim; the review page shows only "Trim a shot" there; the chat path (`vw master decide`, `vw.md`) says the same. Tests: scene 1's shape (two decisions, no sure shot) needs no scene answer and builds from its decisions; a scene with one sure shot still needs its answer; a trim on a scene with no sure shot is applied.

#### O2, O3 — Slides carry their scene's number; a second version is "second choice" (agreed, SK 30 Oct 2026: "Yes, scene numbers")
- **Older way:** kept until VW-11's master is recorded (its slides keep the old labels); from the next film, retired.
- **What changes:** a slide's number is its scene's number (Scene 5 is #5, its parts 5A, 5B…), never its place in the list. A scene with no footage keeps its number as one row ("made with AI", nothing to answer), so no number is skipped. A second version of a scene is "#5 – second choice", its parts 5-2A, 5-2B…, shown right under its first version.
- **For the builder:** `stage2/slides.py`: `no` from the beat's position in `pk['beats']`; a backup's `no` is `f"{n}-2"` (a third, `-3`), its parts `f"{n}-2{letter}"`, and its head line "second choice" instead of "BACKUP for #N"; a declared-blank scene gets a `blank_scene` slide (no answer, `needs_answer` false); the review film's slates, the page and `vw master slides` follow. Answers are stored by slide label: a film whose slides were answered under the old labels keeps them (the label scheme is read from the stored slides; no relabelling of a film in progress). Tests: VW-11's shape (scenes 3 and 4 blank) gives #1, #2, #3 (blank scene), #4 (blank scene), #5…#9; a backup of scene 2 is "2-2" with parts "2-2A"; conflict and missing-answer messages name the new labels.

#### O4, O5, O6 — The second look at the first cut (agreed, SK 30 Oct 2026: "Yes, all three")
- **Older way:** retired in this release (one pass alone is replaced by the pass and the second look).
- **What changes:** after the tool's check passes and before the film is rendered, every scene gets a second look, each by its own helper at the same time (Opus 5.5, high thinking), with only that scene in front of it: its sentences with their times, the pieces chosen, the other pieces whose notes say they fit (direct matches first) with their "what is seen" line, and a few still frames of each chosen piece and each decision. For each shot: does the picture show what the words say at that moment; is there a better piece not chosen; does the cut fall where an action ends. The helper returns its fixes for that scene (or "no change" with one line why); the main assistant joins them, runs the tool's check again and renders. About 5 minutes more; no paid call.
- **For the builder:** chat tool: `vw options second-look` writes `work/options/scenes/<beat>.json` per scene (sentences and times, chosen events, candidate pieces with their cards' "what is seen" and beat fit, frame paths) and the frames through the existing free frame grab; a plugin helper `agents/vw-scene-review.md` (`model: opus`, `effort: high`, read-only tools plus writing its scene's fix file `out/second-look/<beat>.json`); `vw options join-second-look` applies the fixes to `out/options.json` (one scene's events replaced; a fix that breaks the scene's length refused by name). Procedure text (options steps): the second look between `check` and `render`, one helper per scene, named in the steps. Tests: one file per scene with its own sentences only; the join replaces only that scene; a fix of the wrong length is refused.

#### O8 — Each slide says what it means; a second choice is coloured (agreed, SK 30 Oct 2026: "Implement that if it's an easy thing to do"; it is)
- **Older way:** retired in this release (black cards and no hints).
- **What changes:**
  - Every row on the review page carries one short line saying what it is and what each answer does, for example: scene row: "the whole scene as cut; Keep uses it, Reject makes this scene with AI"; decision: "one doubtful piece; Keep uses it, Drop leaves an AI stretch in its place"; second choice: "another way to cut scene 5; keep only one of 5 and 5-2"; AI stretch: "made with AI later; nothing to answer".
  - A second choice is shown in **blue**: its card in the review film has a deep blue background instead of black, and its rows on the page carry a blue mark, so the operator sees at once that it is an alternative to the scene just watched, not the next scene. (Blue rather than red: red reads as an error.)
- **For the builder:** `stage2/render.py` `slate_png`: a `background` argument (black by default; deep blue for a second choice); `stage2/slides.py` passes it per slide and adds a `hint` per slide type; `templates/review.html` shows the hint under each slide's title and a blue mark on second-choice rows. Tests: a second choice's card is drawn on blue, every other card on black; every slide has a hint; the page shows them.
- **O7 agreed (SK, 30 Oct 2026: "Yes, allow it").**

### Helpers (several agents at once): where they are used today (SK's question, 30 Oct)
- **The instructions name helpers in one place only:** the visuals stage's detailed plan (design/124 Change 9: "helpers, your own agents, a few gaps each"). No other step asks for them, and the plugin ships no helper of its own, so a helper today runs on whatever model the session uses.
- **Did VW-11's assistant use helpers at the options step?** It cannot be seen from here: the server records the commands, not the assistant's chat, which lives on the operator's laptop. The instructions did not ask for helpers there, and the 5 minutes it took for 9 scenes suggest one pass by one assistant.
- **Can the server ask for them?** Yes: each step's instructions come from the server, which is how the visuals plan already asks. Naming the helper in the step's text is what makes it reliable (the assistant chooses to delegate; a named helper and a named step leave no doubt).
- **Where helpers fit in the stages reviewed so far:** intake, brief, script, voice and media: no (short, one decision each). Analysis: already parallel on the server (15 Gemini calls at once). Options: the first pass stays one assistant (no clip may appear twice, which needs the whole film in view); the second look per scene (O6). Visuals plan: already named (Change 9). The later phases (picture and video requests per shot) are looked at when they are reviewed.

#### O9 — The plan's helpers shipped with the plugin, on Opus 5.5 at high thinking (agreed, SK 30 Oct 2026: "Yes, ship them")
- **Older way:** retired in this release ("your own agents" in the plan instructions replaced by the named helper).
- **What changes:** the visuals plan's gap helpers become a named helper shipped with the plugin (like O6's scene helper), so they always run on Opus 5.5 at high thinking, whatever the session uses; the plan instructions name it.
- **For the builder:** `plugin/agents/vw-plan-gaps.md` (`model: opus`, `effort: high`; reads the base plan and the package, writes only its own files in `out/plan-gaps/`); v3 visuals plan part: "your own agents" becomes "the `vw-plan-gaps` helper". Test: the agent file's model and effort; the part names it.

### Stage 7 walked step by step (SK, 30 Oct 2026: "we did up till the analysis stage")
O0–O9 came from SK's screenshot of the review page, not from a walk through the stage. The stage is now walked sub-step by sub-step with the revised review prompt, from VW-11's data; O0–O9 are not raised again.

| # | Sub-step | Words | Tool checks | VW-11 |
|---|---|---|---|---|
| 7.1 | **Prepare**: the package written for reading (instructions, scenes, narration, words, cards, usable pieces, 25 rows a file) | 77 | – | 21:24:45 |
| 7.2 | **Scenes and pauses** proposed and approved (one per paragraph, title, chapter, pauses up to 4 s) | 148 | refused if not at a sentence start | 9 scenes, no pauses, "Yes, approve" 21:27 |
| 7.3 | **Coverage report** shown, scene by scene: exact real match, related, nothing | 42 | – | – |
| 7.4 | **Writing the first cut**: rules 1–11 and the editor rules (exact match, short shots, abstract ideas blank, each clip once, decisions, steps, one place per process) | 1,123 (the prompt) + 144 | – | 7 scenes cut, 2 declared blank |
| 7.4.1 | Doubtful boundaries: free frames or a paid closer look | (in 7.4) | – | no paid look used |
| 7.5 | **The tool's check**: refusals and flags by rule; fix and resend | (in 7.4) | about 35 refusals, 22 kinds of flag | 41 flags, 14 decisions |
| 7.6 | **Rendering the review film** and the page link | 85 | – | 2.5 min, 292.9 s film |

### Stage 7: what is agreed and waiting to be built
O0 (Opus 5.5, high thinking everywhere), O1 (scene row asks only what its parts do not), O2-O3 (scene numbers; "second choice"), O4-O6 (the second look, scene by scene, with frames, by helpers), O7 (two moments of one clip in a scene), O8 (hints; blue second choices), O9 (the plan's helpers shipped on Opus 5.5 at high thinking). Nothing built yet.

---

## Stage 8 — The master (started 30 Oct 2026, with SK's revised review prompt: vw2-notes/124-c4-review-prompt.md)

### Where VW-11 is (read on the server, 30 Oct)
The operator answered 13 of 21 slides on the review page in about 6½ minutes (21:44–21:50 IST, 29 Oct), all KEEP; waiting: #7 (Scene 9) and its decisions 7A–7H. No master built, nothing rendered, no defect filed.

### The map of the stage (sub-steps; words of instructions; server refusals)
Instructions: three steps, 454 words (283 + 142 + 29), and a second copy in the operator command text (179 words). The review page carries its own help lines.

| # | Sub-step | Words | Server refusals |
|---|---|---|---|
| 8.1 | **Answering the slides** | 283 | 5 (decide) |
| 8.1.1 | The review film and page: the link, what each slide shows | | 0 |
| 8.1.2 | Scene slides: Keep, Reject, Keep with edit | | in 8.1.5 |
| 8.1.3 | Decision slides: Keep or Drop; blanks need nothing | | in 8.1.5 |
| 8.1.4 | The first answer approves the options | | 0 |
| 8.1.5 | Each answer checked (a slide that exists, an allowed answer, a trim within the shot) | | 5 |
| 8.1.6 | The chat path instead of the page (question tool, four slides a message) | | 0 |
| 8.1.7 | Turning "trim the start a little" into frames | | 5 (the edit) |
| 8.2 | **Building the master** | 142 (shared with 8.3–8.5) | 7 |
| 8.2.1 | Every slide answered (a decision inside a rejected scene needs none) | | 1 |
| 8.2.2 | Trims applied; the scene must keep its exact length | | 1 |
| 8.2.3 | Both versions of one scene kept: refused | | 1 |
| 8.2.4 | A dropped piece becomes a blank; neighbouring blanks join; a blank under 3 s refused | | 1 |
| 8.2.5 | The same clip in two kept scenes: swapped to the scene's other version, or refused | | 3 |
| 8.3 | **Rendering the master film** (render, wait, fetch) | | 0 |
| 8.4 | **Approval**: the operator watched and listened; the master and the first cut recorded together | | 2 |
| 8.5 | **Client rules** from rejection notes (on the operator's yes) | | 0 |
| 8.6 | **Gaps handed to the visuals stage** (scenes with no kept version, blanks, dropped pieces) | 29 | 0 |

### Assumed without checking (so far)
- The page and the chat path call the same server step (the "one flow, two front ends" rule); not yet read for the master.
- VW-11's 13 answers were given on the page, not in chat (the record does not say which front end).

### Parking list (outside this stage)
- Stage 7's agreed changes O0–O9: build interrupted on SK's word (30 Oct) to review this stage first; they are built together later. O1–O3 also change this stage's wording ("a scene's backup is the next number", the scene slides' answers): to be carried into the build.
- design/visuals-flowchart.md (the review prompt's one flowchart for the visuals stage): created when this review reaches the visuals stage; until then the flow's flowchart lives at the top of this document.

### 7.1 — Prepare: the package Claude reads (reviewed 30 Oct 2026)

**What happened on VW-11 (read on the server):** prepare ran at 21:24:45, two minutes after the last clip study finished; free, a few seconds. The package holds 9 scenes, 45 sentences, 673 timed words, 46 clip cards, 121 usable pieces (115 usable as they are, 5 usable only for their sound because a speaker faces the camera, 1 refused), coverage for 9 scenes.

**What Claude is asked to read before writing the cut (sizes as written for reading; tokens estimated at 4 characters each):**

| Part | Size | About |
|---|---|---|
| Usable pieces, 121 rows of 44 details each (5 files of 25) | 240 KB | 60,000 tokens |
| Narration: 45 sentences and 673 timed words | 94 KB | 23,000 tokens |
| Clip cards, 46 × 10 lines | 78 KB | 20,000 tokens |
| Scenes (beats) | 18 KB | 4,500 tokens |
| Coverage | 7 KB | 1,800 tokens |
| Instructions | 7 KB | 1,700 tokens |
| Everything else (rules, places, project, policy) | 4 KB | 1,000 tokens |
| **Total** | **about 450 KB** | **about 110,000 tokens** |

**Findings**
- ⚠ **The "what next" message skips the scenes step.** Prepare tells the assistant "present the coverage report, then author out/options.json" whenever the script has more than one paragraph, even when the scenes are not yet approved; the steps say the scenes come first, "always". On VW-11 the assistant did the scenes first anyway (approved 21:27), and the tool refuses a cut before the scenes are approved, so nothing broke. Same kind of contradiction as design/124 Change 1.
- ⚠ **Too much to read at once (point 11).** About 110,000 tokens are read before a single choice is made; the largest part is 44 details on each of 121 pieces, most of them for the editor (eye position, energy, colour group, lighting, handles), not for choosing which piece goes under which words. The choice needs a dozen of them (what is seen, which scenes it fits and how well, grade, length, shot size, the action's peak, the result shown, pairing, risk).
- **Labels in the text the AI reads:** "design/19", "design/21", "design/91" in the steps and the prompt (the rule codes R1, R5, B1, E2, N14, N17 stay: the tool's flags are grouped by them).
- Nothing paid, no keys, nothing to run in parallel, no decision taken here, no block that costs quality (the 6 pieces left out follow the brief: the speaker is not to be seen). Not part of a shot's fingerprint.

**Assumed without checking:** that the assistant read every file whole, as told (its chat is on the operator's laptop); the token figures are estimates from the sizes.

**Proposed (waiting for SK)**
- **P1 — Prepare's message names the scenes first** when they are not approved. Hurts: every film, mildly (time). Work: one line and a test. Breaks nothing; undo by reverting the line. Operator: nothing. Success: on the next film the message after prepare says "propose the scenes". **Older way:** retired in this release.
- **P2 — The labels removed** from the options text (shorter; no rule lost). Work: three replacements with the trace. Success: no "design/" in the options text. **Older way:** retired in this release.
- **P3 — A lighter first read:** the pieces' files carry only the dozen details the choice needs, grouped by scene (each scene's file: its sentences and the pieces that fit it, direct fits first; a piece that fits no scene listed once at the end); the full row stays in the stored package and is printed on demand (`vw options show`). Expected: the reading falls from about 110,000 to about 40,000 tokens. Hurts: every film with many clips. Work: the reading files only (the server's check and the stored package unchanged). Breaks: nothing stored; films in progress unaffected (the reading files are rewritten at each prepare). Undo: the old reading files. Operator: nothing. Success: on a copy of VW-11's package, every piece the assistant chose is in the lighter files with the details its choice cites, and the reading measures under half. **Older way:** retired in this release (the old reading files are no longer written; the stored package keeps every detail, by design).

| Decided | Parked | Open |
|---|---|---|
| P3 agreed without a trial (SK, 30 Oct: "Yes but without a trial") | the propose message's "then `vw options record`" (out of date since the first answer approves): at 7.6 | P1, P2; the crop rule (below) |

#### 7.1, point 13 — the 6 pieces left out: the crop rule is there, but too narrow (SK: "if you can crop the video so that the person who is speaking is left out, then you can use it")
I read the server's crop rule and re-ran its calculation for each piece. The rule SK describes exists: a piece where someone talks is kept with that person cropped out, if the crop works. It failed on all five pieces of VW-11 where it was tried (the sixth was graded unusable by the clip study):

| Piece | Scene | Who is seen | Heard? | Why the crop failed |
|---|---|---|---|---|
| C0109 | 6 | two silent workers | no | the "speaker" stands above the work, and the crop only cuts from the sides |
| C0093 | 6 | one silent worker | no | the same |
| C0128 | 7 | a person explaining | yes, in Tamil | the same: the speaker's head is above the work |
| C0120 | 6 | a worker at the right edge | background chatter | a side crop works, but trims 7 % off the top of the area to keep, and the rule allows nothing |
| C0124 | 6 | a worker at the right edge | background chatter | the same, 2 % off one side |

So three things narrow it: (1) a silent worker whose face is visible counts as a speaker (the clip study's own instruction says silent workers stay in full frame, but the server treats any visible mouth as talking); (2) the crop is only tried from the sides, never from the top or bottom; (3) not one percent of the area to keep may be trimmed.

**Proposed (waiting for SK)**
- **P4 — A silent worker is not a speaker:** a person counts as talking only when they look at the lens, or their mouth is seen and speech is heard in the piece. Rescues C0109 and C0093 (in full frame). **Older way:** retired in this release; films already analysed keep their old eligibility until their next free re-check (`vw analysis policy`).
- **P5 — Crop from the top or the bottom too:** when the speaker's head is above (or below) the work, the crop cuts it off that way, within the same zoom limit (1.35 on this footage). Rescues C0128 (zoom 1.22). **Older way:** retired in this release (same re-check note as P4).
- **P6 — Up to 10 % of the area to keep may be trimmed at its edge** by the crop. Rescues C0120 (zoom 1.28, 7 % off the top) and C0124 (zoom 1.20, 2 % off one side). **Older way:** retired in this release (same re-check note as P4).
- Together: all five pieces back on VW-11's footage (checked with a scratch copy of the calculation, not with the server's tests). Hurts: every film with people at work and the speaker hidden. Work: the crop rule (one server file) and its tests; the clip study's prompt unchanged. Breaks: nothing paid (eligibility is recomputed free: `vw analysis policy` re-checks without a new clip study). Films in progress: the rule applies at the next re-check; VW-11's cut is already approved, so it applies from the next film unless SK asks to re-check VW-11 (it would reopen the options). Undo: the old rule. Operator: nothing. Success: on VW-11's logs, the five pieces become usable with the crops listed above, and no piece showing a talking face becomes usable uncropped.
- **P4, P5, P6 agreed (SK, 30 Oct 2026: "Yes I approve them all")**, from the next film.

#### Where VW-11 stands (read on the server, 30 Oct; nothing has changed since 29 Oct 21:50 IST)
| Sub-step | Done? | When (IST, 29 Oct) | Recorded words |
|---|---|---|---|
| 7.1 Prepare | done | 21:24 | – |
| 7.2 Scenes and pauses | **approved** | 21:27 | "Yes, approve" (9 scenes, no pauses) |
| 7.3 Coverage report | shown (not recorded; part of the chat) | 21:27–21:32 | – |
| 7.4–7.5 First cut written and checked | done | by 21:32 | 7 scenes cut, 2 declared for AI; 41 flags, 14 decisions |
| 7.6 Review film rendered | done | 21:32–21:34 | 292.9 s |
| Options approved | **approved by the first slide answer** | 21:44 | "first answer #1A KEEP" |
| 8.1 Answering the slides | **in progress: 13 of 21** | 21:44–21:50 | all KEEP; waiting #7 and 7A–7H |

### 7.2 — Scenes and pauses (reviewed 30 Oct 2026)

**What happened on VW-11 (read on the server):** the assistant proposed 9 scenes, one per paragraph, with titles and chapters, and no pauses; approved at 21:27 ("Yes, approve"), 2 minutes 17 seconds after prepare. Nothing paid.

| Scene | Title | Chapters | Length | Sentences |
|---|---|---|---|---|
| 1 | The housing challenge | Housing construction today | 26.2 s | 2 |
| 2 | Bricks on edge, cavities inside | **two**: Conventional flat brickwork; Cavities inside the wall | 30.7 s | 5 |
| 3 | Why it is different | none | 46.6 s | 8 |
| 4 | Environmental benefits | none | 24.8 s | 4 |
| 5 | Quality bricks | Bricks and brick testing | **54.8 s** | 8 |
| 6 | Construction process | **two**: Preparing the plinth and mortar; Laying bricks on edge | 47.5 s | 9 |
| 7 | Junctions and sill course | Junctions and sill course | 21.9 s | 3 |
| 8 | Pointing and curing | Pointing and curing | 17.4 s | 3 |
| 9 | More with less | Finished exposed-brick homes | 31.4 s | 3 |

**Findings**
- Nothing went wrong; the tool's 14 scene checks (a scene starts at a sentence, in order, with a title and a chapter from the brief; pauses after a sentence end, at most 4 s, with a reason) all passed. The assistant read only the three small files the step names (point 11: fine).
- **Two scenes cover two chapters each (2 and 6).** A scene is the unit of everything after it: one scene slide, one Keep or Reject, one second-look helper (O6), one gap's timing for the visuals. A scene that mixes the plinth preparation and the laying of bricks (47.5 s, 9 sentences) can only be kept or thrown away whole, and gives one helper two subjects.
- **No pauses**, which suits this film: camera sound is excluded, so a pause would be dead silence.
- Scenes 3 and 4 have no chapter (abstract: why it is different, environmental benefits) and both became AI-only scenes: the missing chapter already signals "no footage here".
- Label in the text the AI reads: "(design/19)" (goes with P2). The operator command text repeats this step's rules in the same meaning (no disagreement).
- Not part of a shot's fingerprint, but the scenes set every later timing: a change of scene boundaries after the first cut redoes the cut and the visuals gaps (as today; this proposal changes only new films).

**Assumed without checking:** that the 9 scenes were shown to the operator with their lengths before "Yes, approve" (the chat is on the operator's laptop).

**Proposed (waiting for SK)**
- **P7 — One chapter per scene:** a paragraph that covers two chapters is split where the second chapter begins (on VW-11: scene 2 into two scenes of about 15 s, scene 6 into the plinth and mortar, then the laying). The tool warns, not refuses, when a scene lists two chapters. Hurts: films whose paragraphs mix steps of a process (common in process films). Work: one sentence in the step and one warning in the scene check. Breaks: nothing; only new films. Undo: remove the warning. Operator: one or two more scene slides per film. Cost and time: none. Success: on the next process film, no scene lists two chapters, and each scene's slide is about one step. **Older way:** retired in this release.

| Decided | Parked | Open |
|---|---|---|
| P7 agreed (SK, 30 Oct 2026: "Yes, one chapter") | – | – |

### 7.3 — The coverage report (reviewed 30 Oct 2026)

**What happens:** before writing the cut, the assistant shows the operator, scene by scene, how much footage fits: pieces that match directly or are related, by grade, with alerts ("zero coverage"). The server computes it; the chat shows it (not recorded on the server).

**What VW-11's report said (read in its package):**

| Scene | "Direct" pieces | "Related" pieces | Alert | Pieces used in the cut |
|---|---|---|---|---|
| 1 | 4 | 0 | – | 2 |
| 2 | 13 | 0 | – | 4 |
| 3 | **0** | **0** | **ZERO COVERAGE** | 0 (declared AI) |
| 4 | **0** | **0** | **ZERO COVERAGE** | 0 (declared AI) |
| 5 | 4 | 0 | – | 2 |
| 6 | 57 | 0 | – | 8 |
| 7 | 13 | 0 | – | 3 |
| 8 | 3 | 0 | – | 2 |
| 9 | 21 | 0 | – | 7 |

**Findings**
- ⚠ **A block that cost the film two scenes of real footage (point 13).** Once the scenes are approved, the server throws away the clip study's own judgement of which scene each piece fits (kept aside, unused) and replaces it with one rule: a piece fits a scene when its chapter is the scene's chapter; "related" is emptied. Scenes 3 and 4 have no chapter (they are about ideas: why it is different, the environment), so no piece can fit them, the report says ZERO COVERAGE, and the assistant declared both scenes AI-only: **71 seconds of AI video**. Yet the clip study had matched scene 3 with **19 pieces directly (12 clips, mostly finished exposed-brick homes, which the narration names: "the exposed brick pattern is visually attractive") and 43 more as related (25 clips)**, and scene 4 with 1 direct and 4 related. Made 15 Oct (design/19), for scenes that differ from the script's paragraphs: the clip study only knows the paragraphs.
- **"Direct" means "same chapter", not "shows what is said".** Scene 6 shows 57 direct pieces: every piece of its two chapters. The report reads as 57 exact matches when it is 57 pieces of the right activity.
- Nothing paid; no keys; no helpers; nothing in a shot's fingerprint. Words: 42; nothing written twice.

**Assumed without checking:** that the report shown in chat was the server's coverage as stored (the chat is on the operator's laptop); that the scene 3 matches are good pictures for its words (the clip study's word, not checked by eye).

**Proposed (waiting for SK)**
- **P8 — Keep the clip study's matches:** a piece fits a scene when the clip study matched it to a paragraph inside that scene (direct or related, as it said), or when its chapter is the scene's chapter; the report shows the three kinds apart (direct, related, same chapter). A scene with no chapter keeps the clip study's matches. Hurts: every film with a scene about an idea (common in explainers) and every report's "direct" count. Work: the package's fit rule and the report (one server file) and tests. Breaks: nothing stored; films in progress keep their approved cut (VW-11 would need its options reopened to gain scenes 3 and 4: SK's choice). Undo: the old rule. Operator: a more honest report. Cost and time: none; fewer AI seconds to make and pay for later (VW-11: up to 71 s). Success: on VW-11's package, scene 3 shows 19 direct and 43 related pieces, scene 6 shows its clip-study matches apart from its same-chapter pieces. **Older way:** retired in this release (the chapter-only rule; the clip study's matches, kept aside unused until now, are used).

| Decided | Parked | Open |
|---|---|---|
| P8 agreed (SK, 30 Oct 2026: "Yes, keep them"); VW-11 is not reopened ("don't worry about VW-11") | – | – |

### 7.4 — Writing the first cut (reviewed 30 Oct 2026; O4–O9 and P3 already decided are not raised again)

**What happened on VW-11 (read in its saved cut):** 7 scenes cut, 2 declared AI-only (scenes 3 and 4, "zero coverage"). Of the narration's 301 s: **105 s real footage (35 %)**, **196 s for AI (65 %)**: 125 s of blanks inside the cut scenes plus 71 s of the two AI-only scenes. 28 real shots from 28 clips (median 3.6 s; 5 over 4 s, each with a reason); 17 direct matches and 11 B-roll; 14 questions for the operator (11 B-roll, 2 check by eye, 1 other); 19 blanks; the assistant's self-check passed all its points; 41 warnings from the tool (7.5).

**Prompts that create prompts (point 7):** each blank's "what it must show" travels on: the master turns it into the gap's description that the visuals stage reads (with the narration). Real examples:
- 1B (7.2 s): "Rapid urban housing construction: workers laying conventional flat brick walls, families looking at a house being built, rising stacks of bricks and cement bags" (the team's own intended pictures, copied).
- 2A (12 s): "Introduce Rat-Trap Bond Masonry: a mason laying bricks on edge in a neat exposed-brick wall, with a simple graphic of fewer bricks and the same strength": a video and a graphic asked for in one blank; the treatment decides the method later, so it is harmless.
- Clear and consistent with the visuals' own rules; no change proposed.

**Findings**
- ⚠ **Rule 3 blanked a sentence that names something visible (block, point 13).** "Abstract ideas (savings, cost, comfort, strength claims) are blanks by default" (exact-match editing, design/21). The assistant applied it to the whole of scene 3 ("claims … are blanks; scenes 3 and 4 are gaps", its self-check), including "since the exposed brick pattern is visually attractive, plastering is often unnecessary", which the clip study had matched directly to finished exposed-brick homes (7.3). P8 brings those pieces back into the report; rule 3's wording would still push them out.
- **The operator command text's copy of the warnings to act on is out of date:** it lists R5, B1, B2, rule 11, E1, E2; the steps (and the tool) also name N17 and N14 (the step and the place). The steps are what the tool follows.
- 65 % AI is within the rules ("a large share of blanks is fine") but it is the film's largest cost later: at today's estimate (₹8.9 a second of AI video) about ₹1,750 for 196 s, before pictures.
- Reading (point 11): decided (P3). Decisions at once (point 12): about 70 choices in one pass (9 scenes, 28 shots, 19 blanks, 14 questions); decided (O4–O6, the second look by scene). Helpers (point 14): decided (O6). Keys: none. Fingerprint: none.

**Assumed without checking:** that the 19 "direct" scene-3 pieces show exposed brick walls clearly enough to sit under that sentence (the clip study's word).

**Proposed (waiting for SK)**
- **P9 — An abstract idea is a sentence with nothing to show:** rule 3 keeps blanks for savings, cost, comfort and strength claims, but a sentence inside such a scene that names something the camera can see (an exposed brick wall, the cavities, a finished house) is matched like any other. Hurts: explainers with claim scenes (common). Work: one sentence of rule 3 (no longer than now) and its test. Breaks: nothing; new films. Undo: the old sentence. Operator: possibly more B-roll questions. Cost: less AI video. Success: on the next explainer, a "claims" scene keeps its directly matched footage for the sentences that name visible things. **Older way:** retired in this release.
- **P10 — The command text points to the steps for the warnings** instead of listing them (one list, the tool's; shorter). **Older way:** retired in this release.

| Decided | Parked | Open |
|---|---|---|
| – | a dropped question's blank is described by the question itself ("in place of dropped #1A: Open the film on the aerial…?"), which tells the visuals stage little: at 8.2.4 | P9, P10 agreed (SK, 30 Oct 2026: "Yes, P9 and P10") |

### 7.4.1 — Doubtful boundaries: frames or a paid closer look (reviewed 30 Oct 2026)
On VW-11 the assistant looked at **no frames** (free) and asked for **no paid closer look**: all 28 shots and the 2 "check by eye" questions were decided from the clip notes alone, and those 2 went to the operator without the assistant looking first. Covered by O5 (the second look looks at frames); nothing new.

### 7.5 — The tool's check (reviewed 30 Oct 2026)

**What happened on VW-11 (read in the saved cut):** the accepted cut carried 41 warnings and no refusal. By kind:

| Kind | What it says | Count | The instructions say |
|---|---|---|---|
| R1 | a shot does not start at a natural cut point | 17 (of 28 shots) | information only when shots are cut to the meaning across clips |
| R10 | the colour group changes inside a scene | 13 | information only (same) |
| R4 | the energy drops inside a scene | 5 | information only (same) |
| R8 | the same landmark in three shots in a row | 3 | information only (same) |
| N17 | a step shown by a clip of another chapter; a claim shown by footage | 3 | act on: another clip, a blank, or a question |

**Findings**
- **38 of the 41 warnings are the information-only kinds** that this film's style (short shots cut to the meaning across clips) sets off on almost every shot: R1 fired on 17 of 28. The tool already groups them by kind with three examples each (design/43), so the reading is small; still, the assistant is handed 38 warnings to read past to find the 3 it must act on.
- **Out of date (point 17):** one N17 warning still says "warned in this release; refused from the next", a promise from 25 Oct that was never kept (the same as design/124 A2 group 3, which fixed the visuals' copies).
- The 3 N17 warnings were left in the accepted cut; scene 9 carries 7 questions, which may be how they were answered (not checked: the chat is on the operator's laptop).
- How many check rounds the assistant needed is not recorded (the round count is cleared when the cut is proposed). Nothing paid; no keys; no helpers; nothing in a shot's fingerprint.

**Assumed without checking:** that the 3 N17 warnings were answered by questions to the operator; the number of check rounds.

**Proposed (waiting for SK)**
- **P11 — The check's answer to the assistant leads with what it must act on:** the act-on warnings listed in full; the four information-only kinds as one line of counts ("38 for information: R1 17, R10 13, R4 5, R8 3"), stored as today for the editor. Hurts: every film cut to the meaning (most). Work: the grouping (one server function) and a test. Breaks: nothing stored. Undo: the old grouping. Operator: nothing. Success: on VW-11's cut, the answer lists the 3 N17 warnings and one count line. **Older way:** retired in this release.
- **P12 — The "refused from the next release" promise removed** from the N17 warning. **Older way:** retired in this release.

| Decided | Parked | Open |
|---|---|---|
| 7.4.1: covered by O5; P11, P12 agreed (SK, 30 Oct 2026: "Yes, both") | – | – |

### 7.6 — The review film and the page link (reviewed 30 Oct 2026)

**What happened on VW-11:** the review film was made on the server in 2.5 minutes (21:32–21:34), free: 292.9 s, 33 MB. Each scene and each question opens with a 3-second card (21 cards: 7 scenes, 14 questions); blanks are cards under the continuing narration. The page link was given; the first answer (21:44) approved the cut.

**Findings**
- ⚠ **The two AI-only scenes are not in the review film at all, and there is nothing to answer about them (point 13: a choice taken from the operator).** The film is built from the scenes that have a cut; scenes 3 and 4 (71 s, declared "zero coverage") are skipped: the film is 292.9 s, not the narration's 301 s plus cards. The operator never hears those 71 seconds with "for AI" on screen and cannot send the decision back. On VW-11 that decision came from the coverage block (7.3, fixed by P8). O2 adds a row on the page for such a scene, with nothing to answer.
- **Out of date (parked at 7.1):** after the cut is proposed the tool says "`vw options render`, let the operator watch, then `vw options record --quote`"; the steps say the first slide answer approves the cut and the run moves on by itself (record only for an explicit approval).
- The step's own text (85 words) is right. Nothing paid; no keys; rendering is one job (2.5 min); nothing in a shot's fingerprint.

**Proposed (waiting for SK)**
- **P13 — An AI-only scene is shown and can be sent back:** the review film plays its narration under one card ("Scene 3 · made with AI · no footage chosen"), and its row on the page (O2) takes Keep (AI) or Reject with a note ("look for footage: …"), which sends that scene back to the assistant to try footage, as a rejected scene does today. Hurts: every film with an AI-only scene. Work: the review film's item list and the slide (two server files) and tests. Breaks: nothing stored; films in progress keep their film. Undo: the old list. Operator: one more answer per AI-only scene. Cost and time: the film is longer by those scenes (VW-11: about 74 s more). Success: on a copy of VW-11's cut, the film is about 367 s and shows scenes 3 and 4 with their cards and narration. **Older way:** replaced by the simpler P13 below.
- **P14 — The message after the cut is proposed says what the steps say:** "render; the operator watches and answers the slides on the page; the first answer approves the cut". **Older way:** retired in this release.

| Decided | Parked | Open |
|---|---|---|
| P13, P14 agreed (SK, 30 Oct 2026) | – | – |

#### Why the AI-only scenes were left out (root cause; SK's question, 30 Oct)
- **Two ways to leave a scene to AI exist side by side.** The first version of this stage (14 Oct, design/15 and 17) allowed only whole scenes: a scene was either cut from footage or **declared a gap** as a whole, and the stage's scope was "which real clips to use"; a declared gap had nothing to review, so the review film and the slides were built from the cut scenes only. On 15 Oct (design/21, exact-match editing) blanks inside a scene were added, each shown as a card under the continuing narration; but the older whole-scene path stayed, and the film and the slides were never extended to it. I read both in the code: the film is built by going through the cut scenes; a declared gap is not one, so it is never visited.
- On VW-11 the coverage block (7.3: zero coverage for scenes with no chapter) sent the assistant down that old path for scenes 3 and 4.
- **A simpler P13 (proposed):** retire "declare a scene as a gap". An AI-only scene is written as a cut made of one blank (the scene's length, "what it must show"). The existing code then gives it its slide, its card with the narration playing, and Keep / Reject, with no new path; Reject sends it back to the assistant, as for any scene. The tool refuses a declared gap from then on (one message: "write it as one blank").
- **Simpler P13 agreed (SK, 30 Oct 2026: "Yes, simpler way"):** the declared-gap path retired; an AI-only scene is one blank. For the builder: `stage2/validator.py` refuses `gaps` ("write an AI-only scene as one blank of the scene's length"); the options steps and prompt (rule on gaps) say the same, shorter; `scene_summary`'s "declared blank" note goes; tests: a one-blank scene gets its slide, its card under the narration and Keep/Reject; a declared gap is refused by name. This replaces the first P13's card-and-row. **Older way:** retired by refusal in this release: a declared gap is refused ("declare a gap is retired; write it as one blank"). Films whose cut already holds a declared gap (VW-11) keep it until their master is recorded.

### Stage 7 closing table (30 Oct 2026)
| Decided | Parked | Open |
|---|---|---|
| O0–O9 (from the screenshot); P1–P14 (walk-through), P13 in its simpler form | a dropped question's blank described by the question itself: at 8.2.4 | – |

---

## The old-ways check, stages 1 to 7 (SK's rule of 30 Oct 2026)

SK's rule: every change states its older way (retired, or kept until a date with a reason); kept ones go on the list in design/35; a retired way is refused by name. Applied here:
- **Every change in this document now carries its "Older way" line** (41 lines: I1–I4, B1–B3, S1–S3, V1–V3, M1–M2, A1–A4, O0–O9, P1–P14 and the simpler P13).
- **The code of stages 1 to 7 was searched** (intake, brief, script, voice, media, analysis, options and the review page; server and chat tool) for older paths kept beside newer ones, and the open films were counted by instruction version (9 open: VW-3 to VW-9 on version 2, VW-10 and VW-11 on version 3; none on version 1). Found, and put on design/35's list:
  - **Due now (nothing uses them):** instruction version 1 with the whole planning stage; the separate first-cut record (before design/44); deciding by option number and cuts without slides (before design/21); the explicit options approval beside "the first answer approves" (with P14).
  - **Waiting on SK:** instruction version 2, kept only for VW-3 to VW-9, which SK dropped on 29 Oct but which are still open in the database; three more older ways (footage character at media, Kling/Seedance takes, old guide snapshots) go with it.
  - **Kept for VW-11 until its master is recorded:** its old slide rows and labels (O1–O3) and its declared gaps (P13).
- **Retire by refusal:** each retired way above gets a one-line refusal naming the new way when it is removed.
- Not checked in this audit: the visuals stage's code beyond what design/124 recorded (it was not part of stages 1 to 7).

- **VW-3 to VW-9 closed (SK, 30 Oct 2026: "Yes, close them"; 09:27 IST).** The server's own close refuses a film that was never delivered, so they were closed in the database (status closed, closed time set), after checking none had a job queued or running; reopening is setting the status back. Their render caches on the server were not cleared (disk space only). Open films now: VW-10 and VW-11, both on version 3. Instruction version 2 and the three older ways tied to it are now **due** on design/35's list.

---

## The stage 7 build (30 Oct 2026, on SK's word "Yes, build now"; commit, no deploy until SK approves)

Built by three builders working on separate files, then checked and joined: (A) the options and master server and the review page; (B) the crop rule and the older ways due; (C) the chat tool, the helpers and the wording. Server 0.76.0, plugin 0.63.0.

### What was built
- **Review page and options (A):** O1 (a scene whose footage is all questions takes only a trim; its parts decide it), O2/O3 (scene numbers; "N-2", "second choice"), O7 (a later, non-overlapping part of a clip in the same scene is not a reuse; side by side at the same size refused), O8 (a hint on every slide; a second choice's scene card on deep blue, a blue mark on its rows; "Keep with edit" is now "Trim a shot"), P1, P7 (warning), P8 (the clip study's matches kept: on VW-11 scene 3 shows 19 direct and 43 related), P11 (`act_on` and `for_information`; on VW-11: 3 to act on, "38 for information: R1 17, R10 13, R4 5, R8 3"), P12, P13 simpler (a declared gap refused; an AI-only scene is one blank with its slide, card and Keep/Reject), P14.
- **Crop rule (B):** P4, P5, P6: on VW-11's footage C0109 and C0093 become usable as they are, C0128 with a top crop (zoom 1.22), C0120 (1.28) and C0124 (1.20) with a side crop.
- **Chat tool and wording (C):** P3 (the reading, grouped by scene: VW-11's 394 KB → 189 KB, about 98,600 → 47,100 tokens), O4–O6 (`vw options second-look`, the `vw-scene-review` helper on Opus at high thinking, `vw options join-second-look`), O9 (the `vw-plan-gaps` helper), the operator guard lets only these two helpers run, the wording of P2, P7, P9, P10, P13, P14, O1–O3, O4–O6, O7, O9 and the first-cut step (script `scripts/d125_stage7_wording_v3.py`, trace `design/125-stage7-wording-trace.md`; options 1,619 → 1,617 words, master 454 → 453, first cut 53 → 13), O0 in both operator setup guides (`"model": "claude-opus-5-5"`, `"effortLevel": "high"`, never set `CLAUDE_CODE_EFFORT_LEVEL`).
- **Older ways retired by refusal (A, B, C, and the lead):** instruction versions 1 and 2 for new or adopted films; the planning stage, its endpoints, `vw planning` and `v1.json`; the version-1 evidence contract; the separate options approval; the separate first-cut record; deciding by option number; cuts without stored slides; the footage answer from media; Kling, Seedance and the Higgsfield branches; the older guide snapshot; the visuals stage reading a planning output; unused evidence modules; the old video-service key setting. Every refusal names the new way (messages in design/35's list).

### Choices the builders made inside SK's decisions (for SK to confirm)
- **O1:** a scene decided by its parts only when it has no second choice (with two versions both answer-free, the operator could not pick one).
- **O7:** two parts of one clip side by side at the same size is **refused** (read from "never side by side").
- **O8:** only the second choice's own scene card is blue; its question and blank cards stay black.
- **P6:** 10 % per edge of the must-keep area (C0128 loses 7.3 % on each side, 14.6 % of the width in all).

### The independent check (a helper that did not write the wording)
Every change in version 3 is in the trace, and version 2 is unchanged. It found six problems, all fixed (`scripts/d125_stage7_fixes_v3.py`, appended to the trace):
1. a contradiction: the E2 rule (split a long blank with footage) against an AI-only scene: E2 now says an AI-only scene is included and gives the way out ("or say in intent why it must stay whole"); the prompt's second list of flags removed (the steps hold the one list);
2. the master step's scene-decided-by-its-parts wording now matches the code: it needs no answer, takes a trim if wanted, and only without a second choice; an AI-only scene keeps Keep/Reject;
3. rule 3 keeps "by default" and the B-roll gate ("only when clearly relevant, relatable to the words, and nothing in it wrong");
4. "keep one of the two" restored for a second choice;
5. the act-on flags listed with "each says what to do" (their messages carry the explanation);
6. the per-scene file limit said ("a large scene continuing in pieces-<scene>-2.json").
Also in the command text: the paragraph's "versions 2 and 3" heading, the reuse wording (another scene), and two sentences said twice. **Word counts:** options 1,619 → 1,607, master 454 → 448, first cut 53 → 13; the command text's options paragraph 437 → 428. Left as noted: options keep their internal numbers 1..N beside the slides' scene numbers (`vw options show --option n`).

### Tests
Server unit 872 passed, 4 skipped (browser tests); chat tool 349 passed, 3 known Windows-only failures; `c1_split_v3.py --check` ok; every chat-tool file compiles. New: `test_design125_stage7_a_pure.py` (28), `_b_pure.py` (14), `_c_pure.py`, plugin `test_design125_stage7.py` (13); older tests adapted to the retired ways.

### Not covered
- The Docker tests (`server/tests`): Docker was not running; `test_stage2.py` and `test_visuals.py` still use declared gaps and the planning stage (on design/35's list, item 15).
- A real render of a blue card, a browser look at the page, a real run of the helpers, and whether the desktop app honours the helpers' and the folder's model and thinking settings (to test on one operator laptop).
- The second look's still frames show a piece's own edges, not a trimmed shot's edges (the free frame grab takes the piece's in and out).
- The shared test environment on this PC was found broken (files deleted from the temporary folder); the tests ran on the system Python 3.12 and a fresh environment.

- **Deployed 30 Oct 2026** (design/35 row 114): server 0.76.0, plugin 0.63.0, main @ 0dc9f47; live version 3 checked (the AI-only scene rule, the second look, the first-cut step). The operator restarts Claude Code; Vw off in the desktop app's list.
