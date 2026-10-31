# 126 — Review of the whole flow on VW-12, stage by stage (started 30 Oct 2026)

SK and the assistant review every stage of VideoWizard on the fresh film **VW-12** ("Rat-Trap Bond Masonry - Documentary Explainer v7", client VK Nardep, Uma's laptop, picture AI Gemini / Nano Banana, instruction version 3), one sub-step at a time, with SK's review prompt (vw2-notes/124-c4-review-prompt.md) applied to every stage. VW-13 (Revathi's PC, GPT Image) is used only to compare. Everything decided in design/125 is not raised again. **Nothing here is built until SK says so.**

## The flowchart (continues design/125's; grows as we go)

```
[Script document from the client]
      ▼
0. Start   ── picture AI asked first (I1) ──► the run (VW-12: gemini, VW-13: openai) ✓ seen
      │    (reviewed on VW-12: ST1 no silent GPT Image; ST2 "as in v1" removed)
      ▼
1. Intake  ── kept narration ─────────────► Brief, Script, Voice   (reviewed: 78/78 removals right; IN1 prompt trimmed)
      │    ── removed duration lines ──────► Brief (the document's own timings)
      │    ── removed picture notes ───────► Visuals: treatment ("the team's intended picture" per scene)
      │    ── chosen title ────────────────► the run's name
      ▼
2. Brief   ── purpose, message, ending ────► Script stage (does the narration fit?)
      │    ── tone ────────────────────────► Voice (how the narration is spoken)
      │    ── chapters ────────────────────► Analysis (each clip tagged) and Options (one chapter per scene, P7)
      │    ── footage languages (may be none, B1) ► Analysis (what speech to listen for)
      │    ── speaker on camera ───────────► Analysis and Options (the crop rule, P4–P6)
      │    ── frame shape, where it plays ─► the finished film
      │    ── client rules, directory ─────► every later stage
      ▼
3. Script  ── final spoken words ──────────► Voice
      │    ── paragraphs as beats ─────────► Options, Master, Visuals
      │    ── figures the message rests on (claims, S3) ► Visuals (claims.json)
      ▼
4. Voice   ── delivery tags (no repeat, V1) ► the narration
      │    ── final narration, word timings ► Options, Master, Visuals
      ▼
5. Media   ── clips; camera sound required (M1); originals or copies ► Analysis, Assembly
      ▼
6. Analysis ── per clip: pieces, grades, beats, people, chapter ► Options
      │     (15 at once, A1; plain mode ≤ 15 s, A2; up to 3 automatic retries, A4)
      ▼
7. Options ── scenes ► coverage (direct / related / chapter, P8) ► first cut ► tool's check (act-on first, P11)
      │     ► second look per scene by helpers (O4–O6) ► review film (AI-only scenes as one blank, P13)
      ▼
8. Master  ── slide answers ► master film ► gaps to Visuals
      ▼
9. Visuals (design/121, 124; its own flowchart in design/visuals-flowchart.md)
```

VW-12's position is kept in the table below. ⚠ marks where something went wrong on VW-12.

## Where VW-12 is (read in the database, 30 Oct 2026, 11:07 IST)

| Step | Done? | When (IST) | Operator's recorded words |
|---|---|---|---|
| 0 Start (picture AI: gemini) | done | 10:59:20 | – |
| 1 Intake | approved | prepared 10:59:54, recorded 11:03:00 | "Rat-Trap Bond Masonry - Documentary Explainer v7 / Approved the cleaned script" |
| 2 Brief | approved | prepared 11:04:10, recorded 11:06:49 | "Same, approve" |
| 3 Script onwards | not started | – | – |

No paid job, no defect. VW-13 at the same time: intake approved 11:04:20 (title 2), brief not yet recorded.

## Stage 0–1 — Start and Intake

### The map of the stage (waiting for SK's yes)

Words and checks are the version 3 instructions and the chat tool's refusals (I read both: `server/procedures/v3.json`, intake; `plugin/scripts/stages_text.py`). "Rules" is my own count of separate instructions.

| # | Sub-step | Rules | Words | Tool refusals | VW-12 |
|---|---|---|---|---|---|
| 0.1 | The picture AI asked before the film starts (I1) | 1 | 34 (command text) | 0 | gemini recorded |
| 0.2 | `vw start`: client, script copied in | 3 | about 140 (command text) | client must match one Active client | 10:59:20 |
| 1.1 | Prepare: the text taken out of the document, numbered, the titles already used shown | 3 | 64 | 4 (no document, wrong file named, two documents, unreadable) | 10:59:54 |
| 1.1.1 | A scanned page: ask for a readable copy | 1 | 22 | 0 | not needed |
| 1.2 | The proposal: which lines are not the script, up to three titles | about 14 | 716 (prompt) + 41 | 7 (file missing or not an object; removals not a list; bad shape; not a line number; a blank line; unknown kind) | 78 removed, 35 kept, 3 titles |
| 1.3 | Preview and show the operator; one question (title, approve or corrections) | 6 | 110 | 1 (prepare first) | – |
| 1.4 | Record with the chosen title | 3 | 32 | 6 (prepare first; source changed; no titles; no `--title`; title length; nothing left) | title 1, 11:03:00 |

Total for the stage: about 31 rules, 985 words, 18 refusals. Nothing paid.

### Assumed without checking
- That the picture AI was asked in chat before the run (the database shows gemini; the chat is on Uma's laptop).
- The rule counts are my own reading.

### 0.1 — The picture AI asked before the film starts (reviewed 30 Oct 2026)

**What happened on VW-12 (read in the database):** the run was created at 10:59:20 with picture AI `gemini`; prepare ran 34 seconds later. VW-13: `openai`. Nothing paid.

**Findings (I read the code: `plugin/scripts/vw.py` start, `server/app/main.py` and `core.py` run creation, `visuals_stage.provider_of`)**
- Works as agreed (I1): the chat tool refuses to start a film without the answer ("Ask the operator which image model…; no run was created"), and the server refuses a run without it too. The question now sits in the start instructions, where the assistant reads it before starting.
- Nothing written twice that disagrees; no label in the text the AI reads (the help text's "(design/120)" went with I2). Not paid; no keys; nothing to run in parallel; no helper; not part of a shot's fingerprint.
- **Block (point 13), deliberate:** the choice can never change on a film (SK, 28 Oct, design/120: two groups compare the two picture AIs on the same script). A wrong answer means a fresh film. Recommend **keep**: it is asked first, so a wrong answer costs only the few minutes of intake and brief.
- ⚠ **Older way (point 15): two silent fallbacks to GPT Image** kept only for films started before the choice existed (28 Oct): the server's run-creation function defaults to `openai` (never reached: the request must name one), and the visuals stage reads a film with no picture AI as `openai` ("runs from before the choice are openai"). Every such film is closed (VW-3 to VW-11); both open films carry their choice.

**Assumed without checking:** that the operator was asked in chat (the chat is on Uma's laptop; the database shows the answer).

**Proposed (waiting for SK)**
- **ST1 — The two fallbacks to GPT Image removed:** a film without a picture AI is refused by name ("this film has no picture AI; it is chosen at `vw start --images`"), never silently given GPT Image. Hurts: no film today (rare, and only by mistake). Work: two lines and one test. Breaks: closed films' visuals pages could no longer be opened for pictures (closed, never delivered). Undo: the two lines. Operator: nothing. Cost and time: none. Success: a run row with no picture AI is refused by name in the visuals stage; VW-12 and VW-13 unchanged. **Older way:** retired in this release.

| Decided | Parked | Open |
|---|---|---|
| keep the fixed choice (recommended); ST1 agreed (SK, 30 Oct 2026: "Yes, approve ST1") | – | – |

**For the builder (ST1):** `server/app/core.py` `create_run`: no default for `image_provider`; `server/app/visuals_stage.py` `provider_of`: refuse (`Problem`) when the run has none, naming `vw start --images`. Test: a run dict without `image_provider` is refused by name; `openai` and `gemini` pass through.

### 0.2 — Starting the film: client and script (reviewed 30 Oct 2026)

**What happened on VW-12 (read in the database):** started 10:59:20 for VK Nardep (an Active client of the directory, as required); the script document was in the film's folder when prepare ran 34 seconds later (stored as `original.txt`, 7,271 bytes). Whether it came with `--script` or was pasted in chat is not recorded. Nothing paid.

**Findings (I read `plugin/scripts/vw.py` start, `server/app/core.py` run creation and client matching, `plugin/commands/vw.md` "Starting a run")**
- Works: 9 refusals, each with what to do (a file the tool may not read; not a TXT, MD, Fountain, DOCX or PDF; no picture AI; too little disk space; the folder already exists; a retired or unknown instruction version; no single Active client matches; the copy failed). A partial client name that fits exactly one client is accepted and said back to the operator with the client's directory card.
- ⚠ **Change-history label in the text the assistant reads (point 16):** the command text opens "Starting a run" with "(as in v1: …)", "v1" being the first system, which the assistant has never seen.
- Owner: both fresh films are recorded as SK's, although Uma and Revathi ran them (they sign in with SK's account). Nothing in this stage depends on it; noted only.
- Not paid; no keys; nothing to run in parallel; no helper; not too much to read (one paragraph); one decision; no block; not part of a shot's fingerprint. Film types: a film with no script document cannot start (design/122 covers films without footage, not without a script): out of scope.

**Assumed without checking:** how the script reached the folder; that the operator saw the directory card line.

**Proposed (waiting for SK)**
- **ST2 — "(as in v1: …)" removed** from the start paragraph: "Starting a run (as in v1: the script is the first input, the client is mandatory, the title is chosen later)." becomes "Starting a run: the script is the first input, the client is mandatory, the title is chosen later." Words: 23 → 20. Hurts: nothing today (a meaningless word to read past). Work: one replacement, checked by eye. Breaks: nothing. **Older way:** retired in this release.

| Decided | Parked | Open |
|---|---|---|
| ST2 agreed (SK, 30 Oct 2026: "Yes, approve ST2") | – | – |

**For the builder (ST2):** `plugin/commands/vw.md` line 13, the replacement above; checked by eye.

### 1.1 — Prepare (reviewed 30 Oct 2026)

**What happened on VW-12 (read in the database):** prepare ran at 10:59:54 on one document, with no extraction warning and no scanned page; the tool printed the intake prompt, the counts and the titles already used for VK Nardep (the earlier films' titles, up to "… v6"), and wrote the numbered document to a file the assistant reads in parts. Free, a few seconds.

**Findings (I read `plugin/scripts/stages_text.py` `intake_prepare` and the v3 intake steps)**
- Works: the 4 refusals say what to do (no document; a wrong file named; two documents, never picked silently; an unreadable file). The document is never pasted into the prompt; the assistant reads it in parts.
- What the assistant reads here: the prompt (716 words), the five steps (269 words) and the document (113 numbered lines, about 7,300 characters): small (point 11).
- The prompt's history label ("ported verbatim 14 Oct 2026") is stored beside the prompt but not printed to the assistant (I read what prepare returns).
- Nothing paid; no keys; nothing parallel; no decision; no block; no helper; no older way; nothing written twice; not part of a shot's fingerprint. **Nothing to change.**

### 1.1.1 — A scanned page: ask for a readable copy (reviewed 30 Oct 2026)
Not reached on VW-12 (a text document, no scanned page). Nothing to discuss.

| Decided | Parked | Open |
|---|---|---|
| 1.1 and 1.1.1: no change | – | – |

### 1.2 — The proposal: which lines are not the script, and three titles (reviewed 30 Oct 2026)

**What happened on VW-12 (I read the stored document and the assistant's proposal on the server):** the document has 127 lines. The assistant (Claude, in the operator's chat) proposed 78 removals: the document title (as "other"), the suggested duration, and for each of the 9 scenes its heading, its duration, the "Visuals" and "Narration" labels and the picture bullets (4 to 8 per scene). **Every removal is right and no spoken line was removed** (I compared line by line: the 35 kept lines are exactly the narration; blank lines kept). Titles: "… Documentary Explainer v7" (recommended; the client already has a v6), "… Benefits, Materials and Construction", "… Building Smarter, Building Sustainably v2". The notes field is filled (I3 works). Prepare to record: about 3 minutes, including the operator's reading. Nothing paid. VW-13 (the same document) chose the third title.

**Findings (I read the v3 intake prompt and step 2)**
- Decisions in one go (point 12): 78 removals and 3 titles, but one repeating pattern per scene, and the operator reads the cleaned script before approving: no second pass needed.
- Prompts that write prompts (point 7): none here.
- ⚠ **Leftovers from the first system (point 18), as in the brief and script (B2, S1):** the prompt was written for a separate AI that returned an answer (ported 14 Oct); today the assistant writes a file and talks to the operator. "Return only JSON, no prose around it:" is out of date (step 2 already says write it to out/intake.json).
- **Said twice (point 17):** "never rewrite a line" is said three times in the prompt ("YOU NEVER REWRITE A LINE…", "You return line NUMBERS… you do not tidy anything", and "Preserve spoken words exactly so the chosen script has an honest, inspectable relationship to its original source") and once more in step 2; "That is the situation this tool has always been in and it survives it easily." repeats the sentence before it (a wrongly kept line costs nothing).
- No label printed; nothing paid; no keys; nothing parallel; no block; no helper; no older way; not part of a shot's fingerprint. Film types: a clean script (nothing to remove) is allowed ("an empty list … is the right answer"); speaker names stay under "when in doubt, keep it" (design/125, not proposed).

**Assumed without checking:** that the operator saw the removals grouped by kind before approving (the chat is on Uma's laptop).

**Proposed (waiting for SK)**
- **IN1 — The intake prompt trimmed of its leftovers:** remove "That is the situation this tool has always been in and it survives it easily." and "Preserve spoken words exactly so the chosen script has an honest, inspectable relationship to its original source."; "Return only JSON, no prose around it:" becomes "Write this to out/intake.json:". Words: 716 → 681. No rule lost (never rewrite, the high bar for removing, the answer shape all stay). Hurts: nothing today (VW-12's proposal was right); it is a tidy-up. Work: three replacements with the trace and a test. Breaks: nothing; films already past the intake are untouched. Undo: the old text. Operator: nothing. Success: on the next film the proposal is as clean as VW-12's. **Older way:** retired in this release.

| Decided | Parked | Open |
|---|---|---|
| IN1 agreed (SK, 30 Oct 2026: "Yes, approve IN1") | – | – |

**For the builder (IN1):** `server/procedures/v3.json` `intake.prompt`: the three replacements above, with a trace; test: none of the two sentences in v3's intake prompt, "out/intake.json" in it, the high-bar and never-rewrite sentences still there.

### 1.3 — Preview and the one question to the operator (reviewed 30 Oct 2026)

**What happened on VW-12:** the cleaned script is 35 spoken lines, under the step's 40-line limit, so the whole of it is shown in chat. The operator's recorded answer has two parts, "Rat-Trap Bond Masonry - Documentary Explainer v7" and "Approved the cleaned script" (the title and the approval in one reply, as the step asks). About 3 minutes from prepare to the answer. Free.

**Findings (I read `intake_preview` and its message, and step 3)**
- Works: the preview is the exact script the record will keep (the same removal code), and the message after it says "ask the operator to read it before approving", matching the step.
- Considered, not proposed: showing the operator all 78 removed lines is long, but it is the only place a spoken line wrongly marked as a picture note would be seen; keeping it is the safer choice.
- Nothing paid; no keys; nothing parallel; one question; no block; no helper; no older way; no label; nothing written twice; not part of a shot's fingerprint. **Nothing to change.**

**Assumed without checking:** what the chat showed (it is on Uma's laptop); the recorded answer suggests the question tool with two answers.

| Decided | Parked | Open |
|---|---|---|
| 1.3: no change | – | – |

### 1.4 — Record with the chosen title (reviewed 30 Oct 2026)

**What happened on VW-12 (read in the database):** recorded at 11:03:00 with the operator's words; the run's name became "Rat-Trap Bond Masonry - Documentary Explainer v7" (from the suggestions). Kept for later stages: the cleaned script (35 lines), the original document, the 10 timing lines (for the brief) and the team's intended pictures for all 9 scenes, each with its heading and the first words of its narration (for the visuals stage). Free.

**Findings (I read `intake_record` and the server's record)**
- Works: the 6 refusals say what to do (prepare first; the document changed since prepare; no titles; no chosen title; title too long; nothing left). The server sets the run's name from the chosen title.
- Noted, not proposed: VW-12 and VW-13 (the same client, prepared within a minute) could not see each other's titles, and VW-12's third suggestion is exactly the title VW-13 chose. Two films with one name is possible only when two films of one client start together (a test setup); not worth a check.
- Nothing paid; no keys; nothing parallel; no block; no helper; no older way; no label; nothing written twice; not part of a shot's fingerprint. **Nothing to change.**

| Decided | Parked | Open |
|---|---|---|
| 1.4: no change | – | – |

### Stage 0–1 closing table (30 Oct 2026)
| Decided | Parked | Open |
|---|---|---|
| ST1 (no silent GPT Image), ST2 ("as in v1" removed), IN1 (intake prompt trimmed, 716 → 681 words); the fixed picture AI kept | – | – |

---

## Stage 2 — Brief

### Where VW-12 is
Prepared 11:04:10, recorded 11:06:49 IST with "Same, approve" (2 min 39 s). Free. (The script and voice stages have started since; reviewed after this one.)

### The map of the stage (waiting for SK's yes)

Words: the v3 brief prompt (1,060) by section, and the steps (462). Refusals: the chat tool's record (I read `brief_record` and `production_inputs`). "Rules" is my count.

| # | Sub-step | Rules | Words | Tool refusals | VW-12 |
|---|---|---|---|---|---|
| 2.1 | Prepare: the script, the client's last brief, the rules remembered for the client, the directory card, the document's timing lines | 3 | 32 + 151 (the prompt's opening) | 0 | 11:04:10 |
| 2.2 | The five decisions (purpose, audience, message, tone, ending), each with a reason | about 18 | 195 + 99 | 2 (file; the five must be filled) | five written |
| 2.3 | Questions: only those that change a decision; constraints only as supplied | about 12 | 141 + 68 | 3 (questions and answers' shape; an id; a required question unanswered) | 1 question |
| 2.4 | The chapters: what the footage will show, in film order | 6 | 197 (production values, shared with 2.5) + part of step 1 | 2 (generic names; identifiers like "Chapter 3") | 15 chapters |
| 2.5 | Production values asked on every film in one message (rules, footage languages, narration language, speaker on camera, where it plays and the frame shape, length only if given); last brief's answers as the recommendation | about 10 | step 1 (230) + 50 | 10 (format 4; languages 3; length, speaker, lists 3) | "Same, approve" |
| 2.6 | The directory's words against the operator's and the script's | 5 | 105 | 2 (list shape; each difference's fields) | 1 difference (audience, by the script) |
| 2.7 | Presentation in a fixed order and one question: approve or changes | 6 | 120 + 54 | 0 | – |
| 2.8 | Record on an explicit yes | 2 | 18 | (the refusals above run here) | 11:06:49 |
| 2.9 | The web rule: say why before any search, only on a yes | 4 | 62 | 0 | no search recorded |

Total: about 66 rules, 1,522 words, 19 refusals. Nothing paid.

### 2.1 — Prepare (reviewed 30 Oct 2026)

**What happened on VW-12 (read in the database and the code):** prepare ran at 11:04:10. The assistant was given the cleaned script, the title and client, the document's 10 timing lines ("Suggested Duration: 5–6 Minutes" and one per scene) as a hint, the client's directory card, no remembered client rules (none exist for any client yet), and the client's latest brief: **VW-10's** (29 Oct 18:26), chosen when the film was started. Its answers became the recommendation: website and YouTube, 16:9, not muted, Tamil in the footage, English narration, speaker not shown, no brand rules; VW-12 recorded exactly these. Free, a few seconds.

**Findings (I read `brief_prepare`, `core.last_brief`, the v3 brief step 0 and the prompt's opening)**
- Works: the latest brief is taken from any film of the client, open or closed, so dropping VW-10 did not lose the client's answers (VW-10's "YouTube, website only" carried over; VW-11's had Facebook).
- What the assistant reads here: the prompt (1,060 words), the steps (462), the script (about 4,800 characters), the card and the last brief: moderate, no overload (point 11).
- The opening's "current Brief, previous questions, exact human answers" reads like the first system's redraft loop, but it still holds when the operator asks for changes (the file keeps the questions and answers): not proposed.
- Nothing paid; no keys; nothing parallel; no decision; no block; no helper; no older way; no label; not part of a shot's fingerprint. **Nothing to change.**

**Assumed without checking:** that the chat showed the operator which film the recommendation came from (the step says "which values are last time's answers"; the chat is on Uma's laptop).

| Decided | Parked | Open |
|---|---|---|
| 2.1: no change | – | – |

### 2.2 — The five decisions (reviewed 30 Oct 2026)

**What happened on VW-12 (I read the stored brief on the server):** the assistant wrote the five decisions, each with a reason tied to the script:
- **Purpose:** viewers understand what rat-trap bond is, why it saves bricks, mortar and money while staying strong and cooler, and what good practice it needs (bricks, laying on edge, clean cavities, junctions and sills, curing). Reason: the script's first half persuades, the second explains how.
- **Audience:** "Recommendation: people in India who build or decide on homes and small buildings (homeowners, self-builders, masons, site engineers, rural housing workers), who know ordinary brickwork but are new to rat-trap bond." Reason: crushing strengths, guide strings, seven days of curing.
- **Message:** the cavities are the point: fewer bricks and less mortar, cooler and cheaper, as strong as ordinary bonds, if the bricks are good and the work careful. Reason: "these cavities are not empty spaces wasted".
- **Tone:** calm, clear documentary; practical, quietly confident, respectful of the mason's craft; figures plainly, no hype.
- **Ending:** awareness, as the script has it; no call to action added.
All five are specific and grounded; nothing invented. The operator approved them with the production answer ("Same, approve"; the one-reply approval was noted on VW-11 in design/125).

**Findings (I read the prompt's five-decision and reasons sections, 294 words, and every brief stored so far)**
- ⚠ **A rule that spoils the record (point 6):** "Where not supplied, label it a recommendation" makes the assistant write the word into the audience itself. After the operator approves, the stored audience still begins "Recommendation: …" on **8 of the 11 films** (VW-3, 4, 5, 6, 8, 10, 12, 13). That field is read later by the script and voice steps, the options step and the prompt guide, where it reads as not yet decided. The chat already shows it as a recommendation, and a difference from the directory is recorded with who decided it.
- **Out of date (point 18):** "Do not rewrite intake to force this stage to pass." is from the first system, where a stage had to pass a gate; the assistant cannot change a recorded intake.
- Too many rules (point 6, otherwise): about 18 rules on five fields, most of them "avoid empty words" rules; the output was good, so no other trim proposed.
- Decisions at once (point 12): five, each reasoned: fine. Nothing paid; no keys; nothing parallel; no block; no helper; no older way; no label; not part of a shot's fingerprint.

**Proposed (waiting for SK)**
- **BR1 — "Recommendation" said in the reason, not written into the audience; the gate leftover removed:** "Where not supplied, label it a recommendation." becomes "Where not supplied, its reason says so." (7 words → 7); "Do not rewrite intake to force this stage to pass." removed. Prompt 1,060 → 1,050 words. Hurts: most films (8 of 11), mildly (a misleading word read by later steps). Work: two replacements with the trace and a test. Breaks: nothing; films already past the brief keep their stored wording. Undo: the old text. Operator: nothing (the chat still says it is a recommendation). Success: the next film's stored audience has no "Recommendation:" and its reason says it came from the script. **Older way:** retired in this release.

| Decided | Parked | Open |
|---|---|---|
| BR1 agreed (SK, 30 Oct 2026: "Yes, approve BR1") | – | – |

**For the builder (BR1):** `server/procedures/v3.json` `brief.prompt`: the two replacements above, with a trace; test: neither old sentence in v3's brief prompt, "its reason says so" in it.

### 2.3 — Questions and constraints (reviewed 30 Oct 2026)

**What happened on VW-12 (stored brief):** one question, marked required: the production values, with last time's answers (VW-10) as the recommendation, the document's own "5 to 6 minutes" as a hint, and a request to confirm the brand and safety rules. Answered "Same, approve". No question about the five decisions (none needed); constraints empty (none supplied). Free.

**Findings (I read the prompt's questions and constraints sections, 209 words, and the tool's question checks)**
- Works: zero creative questions is allowed and happened; the tool refuses a required question with no answer, and the answer is stored in the operator's words.
- **Said twice or more (point 17):** four sentences of this section repeat what is said elsewhere: the question's fields ("a stable id, question, why it matters, an optional recommendation and a boolean required flag": also in step 1 and the answer shape); "Never prefill an answer because it seems obvious" (step 1: "Never fill `answers` yourself"; and "A recommended answer is never a human answer" just before it); "Do not re-ask questions already answered" (the redraft sentence: "ask again only if their meaning … actually changed"); "Do not turn every missing fact into a required answer" ("Only consequential unresolved questions may be required").
- Small tension, harmless: "only consequential questions may be required", yet the production question is required on every film (step 1 asks it every time); the operator answers it either way.
- Nothing paid; no keys; nothing parallel; no block; no helper; no older way; no label; not part of a shot's fingerprint.

**Proposed (waiting for SK)**
- **BR2 — The four repeated sentences removed** from the questions section (each keeps its other copy, named above). Prompt 1,050 → 1,007 words. Hurts: nothing today; less to read past. Work: four removals with the trace (each removed sentence listed beside the copy that stays) and a test. Breaks: nothing; films past the brief untouched. Undo: the old text. Operator: nothing. Success: the next film's questions are as on VW-12 (production asked, answers in the operator's words, no creative question unless needed). **Older way:** retired in this release.

| Decided | Parked | Open |
|---|---|---|
| BR2 agreed (SK, 30 Oct 2026: "Yes, approve BR2") | – | – |

**For the builder (BR2):** `server/procedures/v3.json` `brief.prompt`: the four removals, with a trace listing each beside the copy that stays; test: none of the four in v3's brief prompt, each kept copy still present.

### 2.4 — The chapters (reviewed 30 Oct 2026)

**What happened on VW-12 (stored brief):** 15 chapters, in film order, named plainly: Housing construction today; Conventional flat brickwork; Bricks on edge and the hollow cavities; Exposed-brick walls and cool interiors; Brick kilns and brick transport; Brick quality and strength testing; Preparing the plinth and mortar; Setting guide strings; Laying bricks on edge; Keeping the cavities clean; Checking line, level and plumb; Junctions, corners and sill course; Pointing the joints; Curing the walls; Completed rat-trap bond homes. Made fresh from this script, not copied (VW-10 had 14, VW-13 has 14, VW-11 had 9, from the same script). Free.

**Findings (I read the prompt's production section, step 1, the tool's chapter checks, and the options step that uses the chapters)**
- Works: plain names of what the camera will see, in film order; none is an argument of the script; the tool refuses generic names and numbered labels ("Chapter 3").
- **What it connects to (seen on the flowchart):** each clip is tagged with one chapter at the analysis, and at the options step **a scene covers one chapter: a paragraph covering two is split where the second begins** (P7, design/125). VW-12's 15 chapters fall on 9 paragraphs, so its options step may cut about 15 scenes; script paragraph 6 alone covers five chapters (plinth and mortar, guide strings, laying, clean cavities, line and level) in 6 sentences, so some scenes may be one sentence of 5 to 8 seconds. Each scene gets a slide, an answer and a second-look helper (O6). Not a fault yet: to watch at options (parked).
- Chapters made before the footage is seen: "Brick kilns and brick transport" may have no clip; that only means AI pictures later (P8 keeps the clip study's own matches too). No change.
- Nothing paid; no keys; nothing parallel; no block; no helper; no older way; no label; nothing written twice; not part of a shot's fingerprint. Film types: an empty list for a film with no steps is allowed. **Nothing to change here.**

| Decided | Parked | Open |
|---|---|---|
| 2.4: no change | 15 chapters on 9 paragraphs with P7: watch the scene count and the shortest scene at options 7.2 | – |

### 2.5 — Production values asked on every film (reviewed 30 Oct 2026)

**What happened on VW-12 (stored brief):** asked in one message, with VW-10's answers as the recommendation: Tamil spoken in the footage; English narration; speaker not shown; length from the narration (the document's "5 to 6 minutes" given as a hint; the narration is about 4,800 characters, about 5 minutes); 16:9, website and YouTube, watched with sound; no brand or safety rules. Answer "Same, approve"; recorded exactly so. Free.

**Findings (I read step 1, the prompt's production paragraph and the tool's `production_inputs` and `format_inputs`)**
- Works: one list, in the steps (B3 of design/125); the prompt points to it. The tool requires both language answers on every film (an empty footage list now allowed, B1; not needed here), refuses wrong shapes, and fills 16:9 with no destinations when the operator says nothing, as the step says.
- What it connects to: footage languages → the clip study (what speech to listen for); speaker not shown → the crop rule at analysis and options (P4–P6); frame shape → the finished film; brand and safety rules → every later stage (none here, though the clip study flags missing helmets: the client said none, so the flags stay information).
- Nothing paid; no keys; nothing parallel; one question; no block; no helper; no older way; no label; nothing written twice; not part of a shot's fingerprint. **Nothing to change.**

**Assumed without checking:** that the operator read the full list before "Same, approve" (the chat is on Uma's laptop; the stored question shows every value).

| Decided | Parked | Open |
|---|---|---|
| 2.5: no change | – | – |

### 2.6 — The directory against the operator and the script (reviewed 30 Oct 2026)

**What happened on VW-12 (stored brief):** one difference recorded: the audience. The directory says "youth, volunteers, rural communities, spiritual seekers, and donors interested in national development"; the brief chose "homeowners and self-builders, masons, site engineers and rural housing and development workers in India", decided by the script (crushing strengths, guide strings, curing are written for builders). No operator words (the operator did not speak to it). Free.

**Findings (I read the prompt's directory paragraph, 105 words, and the tool's two checks)**
- Works: the order is the agreed one (the operator's words first, the script second, the directory only where neither has spoken, as a recommendation); the difference is said once and recorded with who decided it. The same difference appears on every film of this client (VW-10 to VW-13), as expected: the directory describes the organisation, the script a film for builders.
- Nothing paid; no keys; nothing parallel; one decision; no block (the warning never stops the brief); no helper; no older way; no label; nothing written twice; not part of a shot's fingerprint. **Nothing to change.**

**Assumed without checking:** that the chat said "This differs from the directory…" to the operator (Uma's laptop).

| Decided | Parked | Open |
|---|---|---|
| 2.6: no change | – | – |

### 2.7 — Presentation and the one question (reviewed 30 Oct 2026)

**What happened on VW-12:** prepare 11:04:10 to the recorded answer 11:06:49 (2 min 39 s). One reply, "Same, approve", answered the production question and approved the brief (noted on VW-11, design/125; not raised again). What the chat showed is on Uma's laptop. Free.

**Findings (I read step 2, 120 words, and the prompt's closing paragraph, 54 words)**
- Works: the step fixes the order (five decisions with reasons, chapters numbered, the production block, open questions) and ends on one question.
- **Said twice, in the first system's words (points 17 and 18):** the prompt's closing paragraph repeats step 1 and step 2: "Return a proposal containing purpose, audience, message, tone, ending, constraints, reasons keyed by the five field names, questions and production. Do not include answers or approval." (step 1 lists the same fields and says "Never fill `answers` yourself"; "Return a proposal" is the wording of the separate AI of 14 Oct) and "Ask for one grouped acceptance or corrections." (step 2: "Ask one question: approve, or changes?"). Its middle sentence ("The file is the proposal; present its meaning and open questions in readable chat, not JSON the operator has to copy.") is said only here and stays.
- Nothing paid; no keys; nothing parallel; one question; no block; no helper; no older way; no label; not part of a shot's fingerprint.

**Proposed (waiting for SK)**
- **BR3 — The closing paragraph cut to its one sentence said nowhere else:** "The file is the proposal; present its meaning and open questions in readable chat, not JSON the operator has to copy." Prompt 1,007 → 973 words. No rule lost (each removed sentence has its copy in step 1 or 2). Work: one replacement with the trace and a test. Breaks: nothing; films past the brief untouched. Undo: the old paragraph. Operator: nothing. Success: the next brief is presented as VW-12's, with one question. **Older way:** retired in this release.

| Decided | Parked | Open |
|---|---|---|
| BR3 agreed (SK, 30 Oct 2026: "Yes, approve BR3") | – | – |

**For the builder (BR3):** `server/procedures/v3.json` `brief.prompt`: the closing paragraph replaced by its one kept sentence, with a trace; test: "Return a proposal" and "grouped acceptance" not in v3's brief prompt, the kept sentence present.

### 2.8 — Record (reviewed 30 Oct 2026)
Recorded at 11:06:49 with "Same, approve"; the tool's 19 refusals ran here and none fired. Nothing to discuss.

### 2.9 — The web rule (reviewed 30 Oct 2026)
Not reached at the brief on VW-12 (no search proposed there). Nothing to discuss; the same rule is used at the script stage, where VW-12 did search (3.4).

### Stage 2 closing table (30 Oct 2026)
| Decided | Parked | Open |
|---|---|---|
| BR1 ("Recommendation" in the reason, not the audience; gate leftover removed), BR2 (four repeated sentences removed), BR3 (closing paragraph cut); brief prompt 1,060 → 973 words | 15 chapters with P7: at options 7.2 | – |

---

## Stage 3 — Script

### Where VW-12 is (read in the database, 30 Oct, about 11:56 IST)
| Step | When (IST) | Operator's recorded words |
|---|---|---|
| 3 Script | prepared 11:08:24, recorded 11:13:52 | "Yes, approve" |
| 4 Voice | recorded 11:33:29 | "Made final on the voices page by SK" |
| 5 Media | recorded 11:39:51 | "1. List is complete and correct / 2. Camera sound can be used for analysis only but not for the film / 3. Camera originals but compressed" |
| 6 Analysis | running: 44 clip studies finished between 11:43 and 11:55 | – |

### The map of the stage (waiting for SK's yes)

Words: the v3 script prompt (642) by paragraph and the steps (300). Refusals: the chat tool's record (I read `script_record`). "Rules" is my count.

| # | Sub-step | Rules | Words | Tool refusals | VW-12 |
|---|---|---|---|---|---|
| 3.1 | Prepare: the cleaned script, the approved brief, the directory's action, contact and name patterns | 4 | 46 + 115 | 0 | 11:08:24 |
| 3.2 | Checking the narration against the brief; wording changes only when useful | about 16 | 193 + part of step 1 | 0 | no change proposed |
| 3.3 | Facts and claims: nothing invented; the figures the message rests on listed as claims (S3) | about 10 | 117 + one sentence of step 1 | 1 (claims' shape) | 6 claims, 3 checked |
| 3.4 | A web check of a claim, only on the operator's yes | 3 | about 55 (step 2) | 0 | 3 claims searched; one disagreed (strength), wording kept |
| 3.5 | Presenting the changes and one question | 5 | 81 + about 30 | 0 | "Yes, approve" |
| 3.6 | The operator's decision on each change; record; paragraphs numbered as beats | about 10 | 136 + 88 | 9 | 11:13:52, 9 beats |

Total: about 48 rules, 942 words, 10 refusals. Nothing paid (the web search is the assistant's own).

### 3.1 — Prepare (reviewed 30 Oct 2026)

**What happened on VW-12:** prepare ran at 11:08:24, 1½ minutes after the brief. The assistant was given the cleaned script (4,783 characters, 9 paragraphs), the title and client, the brief's five decisions, constraints (none) and answers, English narration, no brand rules, the 15 chapters, and from the directory only the client's contact details (no action instructions or name patterns exist for this client). The ending is awareness only, so the contact details were rightly not used. Free, a few seconds.

**Findings (I read `script_prepare`, `directory_for_script`, step 0 and the prompt's first three paragraphs)**
- Works: the directory gives the script step only what it may use (action instructions, contact details for an ending that asks for an action, how the name is written); the rest of the card stays out.
- ⚠ **Out of date (point 18):** the prompt's first paragraph says the input includes "any previously accepted prepared script, exact supplied wording and notes, prior proposals and the operator's decisions". Prepare prints none of these (I read what it returns: title, client, script, brief, answers, narration language, rules, chapters, directory); it is the first system's redraft input. Step 0 lists what is really printed.
- What the assistant reads: 642 + 300 words of instructions and a 4,800-character script: small (point 11). Nothing paid; no keys; nothing parallel; no decision; no block; no helper; no older way; no label; not part of a shot's fingerprint.

**Proposed (waiting for SK)**
- **SC1 — The input list says what prepare gives:** "…exact title and client, any previously accepted prepared script, exact supplied wording and notes, prior proposals and the operator's decisions. Read all current inputs." becomes "…exact title and client, and the directory facts the prepare prints. Read all current inputs." Prompt 642 → 634 words. No rule lost (wording the operator supplies in chat is still covered by the third paragraph's "explicitly supplied prepared wording"). Hurts: nothing today; one less thing to look for that is not there. Work: one replacement with the trace and a test. Breaks: nothing; films past the script untouched. Undo: the old text. Operator: nothing. Success: the next script assessment, as VW-12's, names only real inputs. **Older way:** retired in this release.

| Decided | Parked | Open |
|---|---|---|
| SC1 agreed (SK, 30 Oct 2026: "Yes, approve SC1") | – | – |

**For the builder (SC1):** `server/procedures/v3.json` `script.prompt`, first paragraph: the replacement above, with a trace; test: "prior proposals" not in v3's script prompt.

### 3.2 — Checking the narration against the brief (reviewed 30 Oct 2026)

**What happened on VW-12 (read in the database):** no change proposed. The assessment: the narration already fits the brief (what rat-trap bond is, why the cavities matter, the good practice it needs, a calm factual voice, an awareness ending, no call to action). Prepare to record 5½ minutes, including the web check (3.4). Free.

**Findings (I read the prompt's paragraphs on starting wording, the brief check and what to defer, 193 words, and every script recorded so far)**
- Works as intended: "no finding is a valid result" and the assistant did not invent changes. Across the 10 films recorded, **one change was ever proposed (VW-6), and none accepted**: the client's script is the script; the real value of this stage now is the claims (3.3, 3.4).
- ⚠ **The first system's wording (point 18):** the paragraph on what to defer still speaks of gates: "Defer Treatment, shots, media study, visual achievability, AI makeability, material coverage and filmability. Missing footage is not a defect in narration. Do not gate this stage on visual plans, casting, location, voice selection or provider settings. No voice generation, paid call or automatic progression into Voice is authorized by accepting a script." (52 words); its meaning fits in two sentences.
- Decisions at once (point 12): one check of 9 paragraphs against five decisions: fine. Nothing paid; no keys; nothing parallel; no block; no helper; no older way; no label; not part of a shot's fingerprint.

**Proposed (waiting for SK)**
- **SC2 — The "defer" paragraph said in plain words:** it becomes "Pictures and footage come later: missing footage is not a defect in narration. Accepting a script starts no voice or paid call." (52 → 22 words; prompt 634 → 604). No rule lost: nothing visual is judged here; accepting starts nothing paid. Hurts: nothing today. Work: one replacement with the trace and a test. Breaks: nothing; films past the script untouched. Undo: the old paragraph. Operator: nothing. Success: the next script check, as VW-12's, judges only the words. **Older way:** retired in this release.

| Decided | Parked | Open |
|---|---|---|
| SC2 agreed (SK, 30 Oct 2026: "Yes, approve SC2") | – | – |

**For the builder (SC2):** `server/procedures/v3.json` `script.prompt`, the "Defer…" paragraph replaced as above, with a trace; test: "filmability" and "gate" not in v3's script prompt, the two new sentences present.

### 3.3 — Facts and claims (reviewed 30 Oct 2026)

**What happened on VW-12 (read in the database):** the first film to record claims (S3 of design/125 at work; VW-13 recorded 5). Six claims:
| Claim | Checked? |
|---|---|
| Nearly 25 % fewer bricks | yes: about 25 % (Canada Masonry Design Centre study), the draft Indian standard says about 16–20 %; wording kept |
| Brick strength 20 / 35 / 75 kg/cm² for one, two, three storeys | no |
| Up to three storeys can be built safely | yes: the draft Indian standard says load-bearing walls up to three storeys have been built |
| Strength comparable to conventional bonds | yes: **measured lower** than English bond (about 16–50 % lower); wording kept by the operator |
| Used in thousands of buildings across India | no |
| Walls cured at least seven days | no |

**Findings (I read step 1's claims sentence, the prompt's facts paragraph, 117 words, the tool's claims check, and how the visuals stage reads them)**
- Works: nothing invented; each figure the message rests on is listed with its state and source; the visuals stage reads them as claims.json ("a picture or graphic shows the same figure, and a checked one is not searched again").
- Connection (flowchart): the one figure a graphic will draw (the 20 / 35 / 75 table; the team's intended picture for scene 5 is "a graphic showing strength requirements") is one of the three not checked. Nothing is lost: an unchecked figure is researched at the visuals stage.
- Noted: "checked" means "looked up", not "confirmed": the strength claim is checked and contradicted, and its source says so in words the visuals stage reads; keeping the wording was the operator's decision. No change.
- Nothing paid; no keys; nothing parallel; no block; no helper; no older way; no label; nothing written twice; not part of a shot's fingerprint (the builder confirmed for S3). **Nothing to change.**

| Decided | Parked | Open |
|---|---|---|
| 3.3: no change | the 20 / 35 / 75 graphic: watch at visuals that it is researched before it is drawn | – |

### 3.4 — A web check of a claim, on the operator's yes (reviewed 30 Oct 2026)

**What happened on VW-12 (read in the database):** three claims were looked up (fewer bricks, three storeys, comparable strength); each source reads "Web search 2026-10-30 (**search results only**)": the assistant read the search results' short extracts, not the pages. One finding went against the script (strength measured lower); the operator kept the wording. All within the 5½ minutes of the stage. Free. VW-13 looked up none.

**Findings (I read step 2, the claims sources, and what reads the assessment)**
- Works: the search happened inside the rule (the stored sources say what was searched and found; the operator decided).
- ⚠ **A check from search extracts only (point 5):** a claim looked up this way is stored as checked, and the visuals stage then does not search it again ("a checked one is not searched again"), so a figure drawn later may rest on a two-line extract. Step 2 says "show what you found", not where it was read.
- Noted, no change: the assessment still says "the figures … have not been checked", written before the search; nothing reads the assessment after the record (I searched the code), and the claims carry the true state.
- Nothing paid (the assistant's own search); no keys; nothing parallel; no block; no helper; no older way; no label; not part of a shot's fingerprint.

**Assumed without checking:** that the operator was asked before the search (the step requires it; the chat is on Uma's laptop).

**Proposed (waiting for SK)**
- **SC3 — A check reads the source page:** in step 2, "Search only after the operator says yes; show what you found;" becomes "Search only after the operator says yes; show what the source page says;", and "I want to check X in the script, because" becomes "I want to check X, because". Step 2: 84 → 83 words. Hurts: films whose claims are checked (VW-12 so far), and through them the visuals' graphics. Work: one replacement with the trace and a test. Breaks: nothing; films past the script keep their claims. Undo: the old words. Operator: nothing (a page may take a few seconds longer). Success: the next checked claim's source names a page, not "search results only". **Older way:** retired in this release.

| Decided | Parked | Open |
|---|---|---|
| SC3 agreed (SK, 30 Oct 2026: "Yes, approve SC3") | – | – |

**For the builder (SC3):** `server/procedures/v3.json` `script.steps[2]`: the two replacements above, with a trace; test: "the source page" in v3's script step 2, "show what you found" not.

### 3.5 — Presenting and the one question (reviewed 30 Oct 2026)

**What happened on VW-12:** with no change proposed, the assistant presented the assessment and the claims (with the three checked ones' findings); the operator answered "Yes, approve" (recorded 11:13:52). What the chat showed is on Uma's laptop. Free.

**Findings (I read step 2 and the prompt's presenting paragraph, 81 words)**
- Works: one question, approve or changes.
- **Said twice (point 17):** the presenting paragraph repeats step 3 and the tool: "After the operator decides, each change carries decision: accepted, rejected, or reworded with operator_wording; rejected changes stay in the file and are not applied." (step 3 says the same, and to build the text from the accepted changes only) and "Unaccepted edits must not leak into the final text." (the tool rebuilds the text and refuses any other, and the prompt already says "The tool checks that only the accepted changes are applied").
- Nothing paid; no keys; nothing parallel; no block; no helper; no older way; no label; not part of a shot's fingerprint.

**Proposed (waiting for SK)**
- **SC4 — The two repeated sentences removed** from the presenting paragraph (each kept in step 3 or the tool's line). Prompt 604 → 570 words. Work: two removals with the trace and a test. Breaks: nothing; films past the script untouched. Undo: the old text. Operator: nothing. Success: the next film's changes, when there are any, carry their decisions as today (the tool refuses otherwise). **Older way:** retired in this release.

| Decided | Parked | Open |
|---|---|---|
| SC4 agreed (SK, 30 Oct 2026: "Yes, approve SC4") | – | – |

**For the builder (SC4):** `server/procedures/v3.json` `script.prompt`, presenting paragraph: the two removals, with a trace; test: neither sentence in v3's script prompt; step 3's decision sentence and the "tool checks" line still present.

### 3.6 — The decisions, the record and the beats (reviewed 30 Oct 2026)

**What happened on VW-12 (read in the database):** recorded at 11:13:52 with "Yes, approve": no change, so the recorded text is the cleaned script exactly (its fingerprint equals the intake's); 4,783 characters split into **9 beats** (BEAT_01 … BEAT_09, one per paragraph), which the voice is bound to; the 6 claims kept. None of the 9 refusals fired. Free.

**Findings (I read step 3, the prompt's answer-format paragraph, 92 words, its last two paragraphs, and the tool's change check)**
- Works: the tool rebuilds the text from the accepted changes and refuses any other (9 refusals, each saying what to quote or add).
- ⚠ **A contradiction inside one paragraph (point 17):** "insertions or deletions can use an empty before or after" and, three sentences later, "anchor an insertion on a short before excerpt rather than an empty one". The tool accepts both (an empty-before insertion only when its words occur once; otherwise it asks for an anchor), so the anchor is the safe one to say.
- **Said twice and leftovers (points 17, 18):** "Return the complete proposed spoken_text, optional notes, a concise assessment and changes containing before, after and reason." (step 1); "Every edit must be a listed change with an exact before that occurs once" (step 1, word for word); "Make the full proposal consistent with the listed changes." (the tool refuses otherwise); "there is no fixed-row constraint" (the first system's rows).
- Not paid; no keys; nothing parallel; no block; no helper; no older way; no label; not part of a shot's fingerprint (the beats are, later, through the voice; nothing here changes them).

**Proposed (waiting for SK)**
- **SC5 — The answer-format paragraph said once, without the contradiction:** it becomes "Use exact before excerpts from the current working wording and show the proposed wording; a deletion has an empty after; anchor an insertion on a short before excerpt. Keep unchanged text exact. Changes can cross physical lines." (92 → 37 words; prompt 570 → 515). No rule lost (each removed sentence is in step 1 or enforced by the tool; empty-before insertions still pass the tool when unambiguous). Work: one replacement with the trace and a test. Breaks: nothing; films past the script untouched. Undo: the old paragraph. Operator: nothing. Success: the next film with a change records it on the first try. **Older way:** retired in this release.

| Decided | Parked | Open |
|---|---|---|
| SC5 agreed (SK, 30 Oct 2026: "Yes, approve SC5") | – | – |

**For the builder (SC5):** `server/procedures/v3.json` `script.prompt`, the answer-format paragraph replaced as above, with a trace; test: "fixed-row" and "can use an empty before" not in v3's script prompt; step 1's "Every edit must be a listed change…" still present.

### Stage 3 closing table (30 Oct 2026)
| Decided | Parked | Open |
|---|---|---|
| SC1 (input list as given), SC2 ("defer" paragraph in plain words), SC3 (a check reads the source page), SC4 (two repeats removed), SC5 (answer format said once, no contradiction); script prompt 642 → 515 words | the 20 / 35 / 75 graphic: at visuals | – |

---

## Stage 4 — Voice

### What happened on VW-12 (read in the database)
| Sub-step | When (IST) | What |
|---|---|---|
| Direction recorded | before 11:22 | register "[measured, quietly confident]", tags at the turns, the test passage on the brick-saving figures |
| Two tryouts, same passage, two voices | 11:22:25 → 11:22:45 (20 s, at the same time) | 264 characters billed each |
| One full narration, Reyaansh on Eleven v4 (stability 0.5, similarity 0.75) | 11:25:09 → 11:26:09 (1 min) | 294.4 s, 9 beats, 4,783 characters sent, 2,197 billed |
| Made final on the voices page | 11:33:29 | "Made final on the voices page by SK" |
V1 at work: the narration sent opens with one register tag, not two (11 tags in all).

### The map of the stage (waiting for SK's yes)

Words: the v3 voice prompt (550), the direction prompt (688) and the steps (607). Refusals: the server's voice and direction checks and the chat tool's record (I read `server/app/voices.py`, `voice_direction.py`, `plugin/scripts/stages_av.py`). "Rules" is my count.

| # | Sub-step | Rules | Words | Refusals | VW-12 |
|---|---|---|---|---|---|
| 4.1 | Prepare: the script, the brief, the client's last voice, the favourites, the voices page link | 3 | 42 + 53 | 2 (an accepted script first; script in storage) | – |
| 4.2 | The direction: the register, a tag only where the delivery changes, up to three test passages of 50–100 words | about 20 | 143 + 688 | 6 (register and tags; passages; the chosen passage; tweaks) | register + 10 tags; one passage |
| 4.3 | Recommending and finding voices: last voice, favourites, the account and the library; never guessing from the client's name | about 10 | 120 + 202 | 4 (a voice not on the account; library saves and restores) | Reyaansh (VW-11's voice) and one other |
| 4.4 | Tryouts on the page: one to six voices on the chosen passage, at the same time | 6 | 73 | 4 (step; at least one voice; at most six; a voice twice) + 1 (direction first) | 2 tryouts, 20 s |
| 4.5 | Paid steps said, not asked; jobs waited for, never resubmitted; models and settings | 8 | 57 + 129 | 0 | Eleven v4, 0.5 / 0.75 |
| 4.6 | The chat way instead of the page (one question a message) | 7 | 178 | 0 | not used |
| 4.7 | The full narration, listened to, made final; word timings per beat | 8 | 67 + 93 | 6 (script changed; no timing for a beat; not found; not ready; record checks) | 294.4 s, final on the page |

Total: about 62 rules, 1,845 words, 23 refusals. Paid: ElevenLabs, 2,725 characters billed in all (2 × 264 + 2,197).

### 4.1 — Prepare (reviewed 30 Oct 2026)

**What happened on VW-12:** prepare gave the assistant the accepted script (4,783 characters, 9 passages), the brief's five decisions, English narration and Tamil in the footage, the client's last voice (Reyaansh, from VW-11's brief client), the favourites, the voices page link, the voice prompt and the direction prompt. Free, a few seconds. (The prepare time is not stored for the voice.)

**Findings (I read `voice_prepare`, step 0 and the prompt's opening)**
- Works: the last voice is proposed first, then the favourites; the page link is given.
- ⚠ **The "what next" message gives the wrong order (point 19, the other voices):** prepare's message says "Agree a voice with the operator (one question per message, the voices page or the catalog), then the direction, then narrate and record." Step 1 says the opposite: "First, before any voice is discussed, the direction and the test passage", and the server refuses a tryout before the direction ("Ask the assistant for the direction and the test passage first"). On VW-12 the assistant followed the steps (direction first), so nothing broke. Same kind of slip as P1 of design/125.
- What the assistant reads: the voice prompt (550), the direction prompt (688), the steps (607) and the script: moderate, no overload. The prompt's history label ("VW-VOICE v4 … design/52") is stored, not printed.
- Nothing paid; no keys; nothing parallel; no decision; no block; no helper; no older way; not part of a shot's fingerprint.

**Assumed without checking:** that VW-11's voice was the last voice offered (the record of the offer is in the chat on Uma's laptop; VW-12 used the same voice).

**Proposed (waiting for SK)**
- **VO1 — The message gives the steps' order:** "First the direction and test passage, then a voice (the voices page, or one question per message), then narrate and record." (23 → 17 words.) Hurts: every film, mildly (the assistant must notice the steps disagree). Work: one line and a test. Breaks: nothing. Undo: the old line. Operator: nothing. Success: on the next film, prepare's message names the direction first. **Older way:** retired in this release.

| Decided | Parked | Open |
|---|---|---|
| VO1 declined (SK, 30 Oct 2026: "Leave it"): the message keeps its order | – | – |

### 4.2 — The direction (reviewed 30 Oct 2026)

**What happened on VW-12 (I read the stored direction on the server):** recorded at 11:16 IST with "Best fit, passage 1". The kind of film: a documentary explainer. Two lists: **best fit**, register "[measured, quietly confident]" and 10 tags on 45 sentences, only at the turns (the answer to the opening problem [confident]; "these cavities are not empty" [with quiet emphasis]; the first figure and the strength table [with weight on the figures]; the instructions [clear, unhurried]; the close [thoughtful], [quietly proud]); **experimental**, "[warm, conversational]", a builder's-tip reading. Three test passages of 65–73 words (the figures; the turn on the cavities; the close); passage 1 chosen (72 words: 25 %, comparable strength, three storeys). Free.

**Prompts that write prompts (point 7):** the tags are the request the voice service reads. Real example, the tryout text: "[measured, quietly confident] [with weight on the figures] The technique can reduce brick consumption by nearly twenty-five percent…" (the register, then the passage's own first tag). Clear, within the vocabulary, no pause or reaction tag. What it sounded like is only known to the operator's ears.

**Findings (I read step 1, 143 words, the direction prompt, 688 words, and the server's direction checks)**
- Works: few tags, at the turns; the server checks the tags and passages (6 refusals).
- **First system's wording (point 18):** "Return only JSON:" (step 1 already says write out/direction.json), as IN1 at the intake.
- **Said twice (point 17):** the prompt's "WHAT YOU SAY TO THE OPERATOR" repeats step 1's presentation ("Present the kind of film in one line, the register of each list, then each list as rows: the sentence's first four or five words, the tag, the reason in a short phrase. Then the one line on the experimental idea. Ask: best fit, experimental, changes, or none."), and its question leaves out the test passage, which step 1 asks in the same question. Its last two sentences ("None" is valid; never claim to have heard anything) are said only here and stay.
- Decisions at once (point 12): 45 sentences, two lists, three passages: one pass, and the operator hears the result; no second pass needed. Nothing paid; no keys; nothing parallel; no block; no helper; no older way; no label; not part of a shot's fingerprint (the direction's digest binds the narration, not a shot).

**Proposed (waiting for SK)**
- **VO2 — The direction prompt said once:** "Return only JSON:" becomes "Write out/direction.json:"; the repeated presentation sentences removed, keeping "'None' is a valid answer: the voice reads the script as it is. Never claim to have heard anything; only the operator's listening establishes what a voice does with a tag." Direction prompt 688 → about 640 words. No rule lost (step 1 holds the presentation and the one question with the passage). Work: two replacements with the trace and a test. Breaks: nothing; the recorded direction and its digest unchanged. Undo: the old text. Operator: nothing. Success: the next direction is presented as VW-12's, with one question naming the list and the passage. **Older way:** retired in this release.

| Decided | Parked | Open |
|---|---|---|
| VO2 declined (SK, 30 Oct 2026: "Leave it") | – | – |

### 4.3 — Recommending and finding voices (reviewed 30 Oct 2026)

**What happened on VW-12 (read in the database):** two voices were tried: **Reyaansh – Deep, Gripping Suspense Voice** (the client's last voice, from VW-11) and **Arijit M – Engaging Reels Creator**, both from the account, on the voices page. Reyaansh was chosen. Free (the tryouts are 4.4).

**Findings (I read step 2, the prompt's RECOMMEND and FIND paragraphs, 202 words, and the server's voice checks)**
- Works: the last voice came first; the page was used (the default), so the chat way's catalogue reading did not happen; the choice was the operator's by ear, as the rules require (never from the client's name, never claimed as heard by the assistant).
- Noted, no change: the chosen voice's own label says "suspense", the brief's tone says "calm, measured"; the operator heard both and chose; the direction's register sets the delivery. The ear decides, as agreed.
- Nothing paid; no keys; nothing parallel; one decision (the operator's); no block; no helper; no older way; no label; nothing written twice that disagrees; not part of a shot's fingerprint. **Nothing to change.**

| Decided | Parked | Open |
|---|---|---|
| 4.3: no change | – | – |

### 4.4 — Tryouts on the page (reviewed 30 Oct 2026)

**What happened on VW-12 (read in the database):** two tryouts (Arijit M, Reyaansh) queued at 11:22:25 and both ready at 11:22:45: **20 seconds, at the same time**; the same text for both (the chosen passage with its tags, 601 characters sent), Eleven v4 at 0.5 / 0.75; ElevenLabs billed 264 characters each (its own count). No failure.

**Findings (I read the server's tryout checks and the job rows)**
- Parallel work (point 9): yes, the two tryouts ran side by side. Keys (point 8): one ElevenLabs key; enough for one film's tryouts (and the two fresh films ran their voices at different times). The server refuses a tryout before the direction, with no voice, with more than six voices, or the same voice twice.
- Cost and time (point 10): 528 characters billed, 20 seconds.
- Nothing else to raise: no block, no helper, no older way, no label, not part of a shot's fingerprint. **Nothing to change.**

| Decided | Parked | Open |
|---|---|---|
| 4.4: no change | – | – |

### 4.5 — Paid steps said, not asked; jobs; models and settings (reviewed 30 Oct 2026)

**What happened on VW-12 (read in the database):** three paid jobs (two tryouts, one narration), all on Eleven v4 at the default 0.5 / 0.75, all ready on the first try; none resubmitted, none recovered, none failed. Whether each submission was announced with its model, settings and characters is in the chat on Uma's laptop.

**Findings (I read step 4, 57 words, and the prompt's MODELS AND SETTINGS and JOBS paragraphs, 129 words)**
- Works: the defaults were used; jobs were waited for, not replaced.
- Small repeat, not proposed (the same meaning, no disagreement): "Wait with `vw voice jobs --wait 180`" and "recovered, never resubmitted" are in both step 4 and the JOBS paragraph.
- Keys, parallel work, cost and time: covered at 4.4 and 4.7. No block, no helper, no older way (Eleven v3 and Multilingual v2 are still offered models, not older ways), no label, not part of a shot's fingerprint. **Nothing to change.**

| Decided | Parked | Open |
|---|---|---|
| 4.5: no change | – | – |

### 4.6 — The chat way (reviewed 30 Oct 2026)
Not reached on VW-12 (the voices page was used). Nothing to discuss.

### 4.7 — The full narration and making it final (reviewed 30 Oct 2026)

**What happened on VW-12 (read in the database):** one narration, Reyaansh on Eleven v4 (0.5 / 0.75), queued 11:25:09, ready 11:26:09 (**1 minute**): the whole script in one piece, 4,783 characters sent with 11 tags (one register tag at the top: V1 works), 2,197 characters billed (ElevenLabs' count). Result: **294.4 s**, word timings for all 9 beats (BEAT_05 the longest, 52.6 s; BEAT_08 the shortest, 16.9 s), each beat given a 0.8 s breathing pause. Made final on the voices page at 11:33:29 (7 minutes after it was ready, for a 5-minute narration): "Made final on the voices page by SK".

**Findings (I read step 5, the prompt's NARRATE paragraph, 160 words, the server's narration checks and the tool's beat timing)**
- Works: one piece, timed per word; the record refuses a narration made for another script version and a beat with no timed words. VW-11's narration of the same script was 301 s; VW-12's is 294.4 s (a different direction; the doubled tag gone).
- Noted, not proposed: the page records its own fixed words, "by SK", because the operators sign in with SK's account; the operator here was Uma (as at 0.2).
- Keys and parallel work: one job, one key: nothing to split. Cost: 2,197 characters billed (with the tryouts, 2,725 for the stage). No block (at most three narrations a film, not reached), no helper, no older way, no label, nothing written twice that disagrees. Fingerprint: the narration's timings feed every later timing; nothing here changes them. **Nothing to change.**

| Decided | Parked | Open |
|---|---|---|
| 4.6 not reached; 4.7: no change | – | – |

### Stage 4 closing table (30 Oct 2026)
| Decided | Parked | Open |
|---|---|---|
| no change in the voice stage; VO1 and VO2 declined (SK) | – | – |

---

## Stage 5 — Media

### What happened on VW-12 (read in the database)
Prepared 11:36:07, recorded 11:39:48 (about 3½ minutes). 46 clips, 802.7 s (13 min 23 s): the same footage as VW-11. Camera sound **excluded** (M1: answered and required); copies: **editor's copies**; the operator's words: "1. List is complete and correct / 2. Camera sound can be used for analysis only but not for the film / 3. Camera originals but compressed". Nothing paid.

### The map of the stage (waiting for SK's yes)

Words: the v3 media prompt (91) and steps (286). Refusals: the chat tool's prepare and record (I read `stages_av.py`). "Rules" is my count.

| # | Sub-step | Rules | Words | Tool refusals | VW-12 |
|---|---|---|---|---|---|
| 5.1 | Prepare: one line per clip; identical files once; variable frame rates converted; rotation read | 6 | 90 + 45 | 1 | 46 clips listed, 11:36 |
| 5.2 | The list confirmed with the operator; nothing described | 3 | about 20 + 46 | 0 | "List is complete and correct" |
| 5.3 | The camera-sound question, required (M1) | 2 | about 25 | 1 (no answer) | excluded |
| 5.4 | Originals or editor's copies; the copies note | 3 | about 60 | 1 (no answer) | copies |
| 5.5 | Record: upload three at a time with receipts and retries, resume, clips become the analysis units | 5 | 90 | 2 (a clip changed since prepare; upload failure) | recorded 11:39:48 |

Total: about 19 rules, 377 words, 5 refusals. Nothing paid.

### 5.1 — Prepare (reviewed 30 Oct 2026)

**What happened on VW-12 (read in the database):** 46 clips listed, 919 MB, 3.8 s to 95 s each (28 of them 15 s or less, which the analysis now studies in the plain mode, A2); 45 at 50 frames a second and 1 at 25; every clip with a timecode; none converted, none rotated; no identical files. Free, seconds.

**Findings (I read `media_prepare`, `footage_guess`, `copies_note`, step 0 and the prompt)**
- Works: the listing, the 200 MB limit, three clips probed at a time, the copies note (one clip's frame rate differs from the rest, so the note is printed).
- ⚠ **An older way still speaking (points 15 and 19):** prepare still prints a guess at the footage ("looks professional …" or "looks like phone footage …") ending "**the operator confirms the camera, the support and the look at record**". That was the way of 22 Oct (design/77 L42: the footage described at the media step); since design/88 the footage is measured at the visuals stage, and the same prepare's message and step 1 say "**Do not ask what the footage is**". The guess contradicts both. It is also wrong for VW-12: the clips are compressed copies (h264, about 6 Mbit/s) of camera originals, so the rule's bit-rate test reads "looks like phone footage".
- ⚠ **The same older way at record:** `vw stage media record` still accepts `--camera`, `--support`, `--look` and `--footage-note` ("accepted for one release", design/88, 25 Oct) and stores them in the media record, where nothing reads them since the visuals fallback was removed (old-ways item 6): an answer given there is silently lost. The record's empty `footage_character` field is old-ways item 13 ("next release that touches media").
- Nothing paid; no keys; nothing parallel beyond the three-at-a-time probe; no block; no helper; no label; not part of a shot's fingerprint.

**Proposed (waiting for SK)**
- **ME1 — The media step's footage guess and footage flags retired:** prepare no longer prints the guess; `media record` refuses `--camera`, `--support`, `--look` and `--footage-note` with one line ("the footage is measured at the visuals stage; correct it there with `vw visuals footage`"); the record's empty `footage_character` field goes (old-ways item 13, due now: this touches media). Hurts: every film (a contradicting line the assistant must ignore; a misleading "phone footage" guess). Work: the chat tool's media prepare and record, and their tests (the test of the guess removed). Breaks: nothing stored is read; films past the media step untouched. Undo: the old code. Operator: nothing. Success: on the next film, prepare prints no footage line, and `media record --camera …` is refused by name. **Older way:** retired by refusal in this release (design/77 L42's footage at media).

| Decided | Parked | Open |
|---|---|---|
| ME1 agreed (SK, 30 Oct 2026: "Yes, approve ME1") | – | – |

**For the builder (ME1):** `plugin/scripts/stages_av.py`: `footage_guess` and its call removed from `media_prepare`; `media_record` drops `footage` and the `footage_character` field; `plugin/scripts/vw.py`: `stage media record` refuses `--camera`, `--support`, `--look`, `--footage-note` with the one line above (the `--camera` of `vw delivery` is a different flag and stays); `plugin/tests/test_media.py`: the guess test replaced by "no footage line" and "the flags refused by name". design/35 old-ways items 6 and 13 marked done.

### 5.2 — The list confirmed (reviewed 30 Oct 2026)
"1. List is complete and correct" (recorded in the operator's words); nothing described. Nothing to discuss.

### 5.3 — The camera-sound question (reviewed 30 Oct 2026)

**What happened on VW-12:** asked and answered: "Camera sound can be used for analysis only but not for the film", recorded as **excluded** with those words (M1 at work: the record would have refused without it). Free.

**Findings (I read step 1, the prompt's sentence and the tool's refusal)**
- Works, and the meaning carries through: "excluded" keeps the camera sound out of the film, while the clip study still listens to it (for speech in Tamil and for safety), which is what the operator asked.
- Noted, no change: the stored note joins this answer and the copies answer in one line ("…; Camera originals but compressed"); harmless, both answers are stored on their own too.
- Nothing paid; no keys; nothing parallel; one question; no block; no helper; no older way; no label; not part of a shot's fingerprint. **Nothing to change.**

| Decided | Parked | Open |
|---|---|---|
| 5.2, 5.3: no change | – | – |

### 5.4 — Originals or editor's copies (reviewed 30 Oct 2026)

**What happened on VW-12:** "3. Camera originals but compressed", recorded as **copies**. The copies note was due (one clip at 25 frames a second among 45 at 50); every clip keeps a timecode, and the names keep the camera's clip number with a suffix (for example C0032_02881492.mp4). Free.

**Findings (I read step 1, the tool's refusal and `copies_note`)**
- Works: the answer is required (refused without it) and leads to the hand-off designed in design/107 (the film is relinked to the originals at the very end); the same answer as VW-11.
- Nothing paid; no keys; nothing parallel; one question; no block; no helper; no older way; no label; not part of a shot's fingerprint. **Nothing to change.**

**Assumed without checking:** that the operator was told the one-line copies note (the chat is on Uma's laptop).

| Decided | Parked | Open |
|---|---|---|
| 5.4: no change | – | – |

### 5.5 — Record: the upload (reviewed 30 Oct 2026)

**What happened on VW-12 (read in the database):** prepare 11:36:07 to record 11:39:48: the 46 clips (919 MB) uploaded with a receipt each, three at a time, inside about 3½ minutes including the operator's answers (VW-11: about 10 minutes for the same footage: the operator's internet is the limit, as noted in design/125). No interruption, no clip refused. The 46 clips became the analysis units; the first clip study was queued at 11:42:06. Free.

**Findings (I read step 2, `media_record` and `upload_file`)**
- Works: receipts per file, resume by running record again (finished files skipped), a clip changed since prepare refused.
- Parallel work (point 9): three uploads at once; at VW-12's speed no change needed.
- Nothing paid; no keys; no block; no helper; no older way (ME1 covers the footage flags); no label; not part of a shot's fingerprint. **Nothing to change.**

| Decided | Parked | Open |
|---|---|---|
| 5.5: no change | – | – |

### Stage 5 closing table (30 Oct 2026)
| Decided | Parked | Open |
|---|---|---|
| ME1 (the footage guess and flags at media retired by refusal; old-ways items 6 and 13 closed) | – | – |

---

## Stage 6 — Analysis (the clip study)

### What happened on VW-12 (read in the database)
- **Finished:** all 46 clips retained, first queued 11:42:06, last done 11:55:38: **13½ minutes** (VW-11: 34 minutes with 8 at once; A1 at work). No failure, **no automatic retry needed** (A4 not tested by this run).
- **A2 at work (short clips in the plain mode):** the 28 clips of 15 s or less took **75 s** each on average (VW-11: 4 min 40 s) with **no "look again" tokens** (VW-11: about 290,000 each); the 18 longer clips, studied in the agentic mode, took 349 s each on average with about 587,000 "look again" tokens each.
- Model Gemini 3.8 Flash, high thinking, high resolution. The brief recorded no safety rules, so the safety-gear flags were waived from the start (the policy says so).

### The map of the stage (waiting for SK's yes)

Words: the v3 analysis steps (328; the request sent to Gemini is the server's, unchanged since design/125 and not proposed for change there). Refusals: the server's analysis jobs (I read `server/app/analysis_jobs.py`, 19). "Rules" is my count.

| # | Sub-step | Rules | Words | Server refusals | VW-12 |
|---|---|---|---|---|---|
| 6.1 | Before starting: one message (listen to the clips' sound? any clip to leave out?), the camera-sound answer said back; start | 5 | 90 | 5 | started 11:42 |
| 6.2 | The clip study: one paid Gemini request per clip, 15 at once; plain mode for 15 s or less, agentic above | 4 | (in 6.1) | 4 | 46 studied, 13½ min |
| 6.3 | Waiting: the status line, never reading the evidence files | 3 | 37 | 0 | – |
| 6.4 | Failures: up to three automatic retries; then the operator's retry, recover or leave out | 6 | 86 | 7 | none |
| 6.5 | Eligibility and crops computed by the server; a free re-check (`policy`) and waived safety flags | 5 | 95 | 3 | safety flags waived |
| 6.6 | Moving on: nothing to approve; the next step is options | 2 | 20 | 0 | – |

Total: about 25 rules, 328 words, 19 refusals. Paid: 46 Gemini requests (the money figure is read at 6.2).

### 6.1 — Before starting (reviewed 30 Oct 2026)

**What happened on VW-12 (read in the database):** media recorded 11:39:48; the first clip study queued 11:42:06 (2 min 18 s later). The study was started with the model listening to the clips' sound and no clip left out; camera sound excluded, taken from the media answer. Free.

**Findings (I read step 0, 90 words, and the server's start checks)**
- Works: the camera-sound answer is taken from the media step, not asked again; the start refuses without it, with every clip excluded, or with jobs still open.
- ⚠ **A question the operator answered two minutes earlier (point 5):** step 0 asks, in one message, "should the model listen to the clips' audio (default yes), and is there any clip to leave out (default none)?". At the media step the operator had just said "List is complete and correct" and "Camera sound can be used **for analysis** only". Both answers were already given; the question costs a round trip on every film (most of VW-12's 2 minutes before the start, by the times).
- Nothing paid yet; no keys; no block; no helper; no older way; no label; not part of a shot's fingerprint.

**Assumed without checking:** that the question was asked on VW-12 and that the 2 minutes went to it (the chat is on Uma's laptop).

**Proposed (waiting for SK)**
- **AN1 — Start without asking again:** step 0 becomes "Run `vw analysis start [--understand-audio no] [--exclude <clip name> …]` without asking: the clip list was confirmed at media, and the model listens to the clips' sound unless the operator said there that it must not be used even for analysis. One paid Gemini 3.8 Flash request per clip (agentic for a clip over 15 seconds, plain for a shorter one); tell the operator, do not ask. The server computes eligibility and crops." (90 → 64 words.) The flags stay for an operator who asks. Hurts: every film (one question, about 2 minutes). Work: one step's wording, the trace and a test. Breaks: nothing; a running or finished analysis is untouched. Undo: the old step. Operator: one question fewer; to leave a clip out they say so at the media list. Success: on the next film the clip study starts within seconds of the media record, with no question. **Older way:** retired in this release (the second question).

| Decided | Parked | Open |
|---|---|---|
| AN1 agreed (SK, 30 Oct 2026: "Yes, approve AN1") | – | – |

**For the builder (AN1):** `server/procedures/v3.json` `analysis.steps[0]` replaced as above, with a trace; test: v3's analysis step 0 has no question and keeps `--understand-audio no` and `--exclude`.

### 6.2 — The clip study (reviewed 30 Oct 2026)

**What happened on VW-12 (read in the database):** 46 Gemini 3.8 Flash requests, 13½ minutes in all, none failed. 28 clips of 15 s or less in the plain mode (75 s each, no "look again" tokens); 18 longer clips agentic (349 s each, about 587,000 "look again" tokens each).

**The comparison A2 skipped, made free from two real runs (SK chose no paid test on 29 Oct; VW-11 studied the same 46 clips, all agentic):**
| Clips | Usable pieces VW-11 | Usable pieces VW-12 | Grade A 11 → 12 | Grade B 11 → 12 |
|---|---|---|---|---|
| 28 short (VW-12 plain, VW-11 agentic) | 49 | 43 (−12 %) | 35 → 36 | 15 → 9 |
| 18 long (agentic both times) | 66 | 65 (−2 %, the run-to-run difference) | 45 → 43 | 23 → 20 |
The plain mode found the same grade-A pieces on short clips and about six fewer grade-B ones, for about a quarter of the time and none of the "look again" cost.

**Cost (point 10):** about 11.0 million input tokens and 0.96 million output and thinking tokens for the film; the 18 long clips are about 98 % of the input (their "look again" tokens). The money: no Gemini 3.8 Flash price is set in the server's code (I searched), so I cannot give rupees from the records.

**Findings:** keys (point 8): 5 Gemini keys used in turn, 15 at once (A1): no change. Prompts that write prompts: none (the request is fixed in the server). The request sent to Gemini is unchanged (design/125: changing it voids every stored log). No block, no helper, no older way, no label, not part of a shot's fingerprint. **Nothing to change; A2 confirmed by the comparison.**

**Assumed without checking:** that the grade-B pieces the plain mode missed were not ones the cut needed (VW-11's cut is closed; VW-12's options will show).

| Decided | Parked | Open |
|---|---|---|
| 6.2: no change | the six fewer short-clip B pieces: watch at options whether a scene lacks footage VW-11 had | – |

### 6.3 — Waiting (reviewed 30 Oct 2026)
The status line and "never read the evidence files"; what was reported is in the chat on Uma's laptop. Nothing to discuss.

### 6.4 — Failures and automatic retries (reviewed 30 Oct 2026)
Not reached on VW-12 (no clip failed, so A4's automatic retries were not used). Nothing to discuss; A4 stays untested on a real film.

### 6.5 — Eligibility and crops (reviewed 30 Oct 2026)

**What happened on VW-12 (read in the database and in C0128's stored evidence):** 112 pieces: **108 usable as they are**, 3 usable only for their sound, 1 refused (VW-11: 115, 5, 1 of 121). Safety-gear flags waived from the start (no safety rules in the brief). The crop rule of design/125 (P4–P6), live for the first time, on the five pieces it was meant to rescue:
| Piece | VW-11 | VW-12 |
|---|---|---|
| C0109 (two silent workers) | out | **usable (2 pieces)**: P4, a silent worker is not a speaker |
| C0093 (one silent worker) | out | **usable (3 pieces)**: P4 |
| C0120 (worker at the right edge, chatter) | out | **3 usable**, 1 sound only |
| C0124 (worker at the right edge, chatter) | out | **usable (2 pieces)** |
| C0128 (a mason explaining in Tamil) | out | **still out** (sound only) |

**Why C0128 is still out (I re-ran the rule by hand on its stored boxes):** this time the clip study drew the work to keep across **96 % of the frame's width** (VW-11's study drew it narrower). A crop from the top must start below the mason's head (34 % down) and keep the frame's shape, so it is 66 % wide and cuts 15 % off each side of the work, more than the 10 % P6 allows, at a zoom of about 1.5 (the limit is 1.35). The rule worked as built; the footage does not allow the crop.

**Findings (I read `server/app/clip_log/solver.py` and step 4)**
- Works: four of the five pieces are back; nothing usable shows a speaking face.
- Noted, not proposed: when both crops fail, the stored reason names only the side crop ("Speaker horizontally overlaps…"), not why the top crop failed; nobody acts on that text.
- Free (the server computes it; a re-check is free). No keys; no block (the speaker rule follows the brief: "speaker not shown"); no helper; no older way (old-ways item 11 covers films analysed before P4–P6); no label; not part of a shot's fingerprint. **Nothing to change.**

| Decided | Parked | Open |
|---|---|---|
| 6.3, 6.4 not reached / nothing; 6.5: no change | – | – |

### 6.6 — Moving on (reviewed 30 Oct 2026)
Nothing to approve; the run moved to options when every clip was retained. Nothing to discuss.

### Stage 6 closing table (30 Oct 2026)
| Decided | Parked | Open |
|---|---|---|
| AN1 (start without asking again); A1, A2, P4–P6 confirmed on real data; A4 untested (no failure) | six fewer short-clip grade-B pieces: watch at options | – |

---

## Stage 7 — Options (the first cut and its review film)

**Live code changed during this review:** design/127 (the review page and film by scene and shot) was deployed on 30 Oct by another session (server 0.77.0, plugin 0.64.0, main 5c5cfdf with its page hotfix). VW-12 cut its options before and after that deploy; this stage is read on the live code.

### What happened on VW-12 (read in the database)
| Step | When (IST) | What |
|---|---|---|
| Scenes approved | before 12:27 | 9 scenes (not about 15, as feared at 2.4), 1 pause; "Yes, approve" |
| First cut, version 1, rendered | 12:27:11 → 12:29:43 | (before design/127) |
| First cut, version 2, rendered | 15:08:53 → 15:11:41 | after design/127's deploy; review film 377.4 s |
| Options approved | 15:45 | "first answer #1.3 KEEP" (slide 1.3: scene 1, shot 3, in design/127's numbering) |
| Master rendered | 16:03 → 16:05 | (stage 8) |

**The cut (version 2):** 9 options, 25 real shots, 20 AI shots, 8 alternatives. Of the narration's about 296 s: **81 s direct footage + 37 s B-roll = 118 s real (40 %)**, **179 s for AI (60 %)** (VW-11: 35 % real, 65 % AI, with scenes 3 and 4 wholly AI). Scene 3 now has 7 s of real footage; scene 4 has 5.5 s of B-roll; no scene is AI-only.

### The map of the stage (waiting for SK's yes)

Words: the live v3 options prompt (1,271) and steps (521). Refusals and warnings: the tool's check (counted again at 7.5). "Rules" is my count, done at each sub-step.

| # | Sub-step | Words | VW-12 |
|---|---|---|---|
| 7.1 | Prepare: the package for reading, grouped by scene (P3) | 90 | before 12:27 |
| 7.2 | Scenes and pauses, one chapter per scene (P7) | 162 | 9 scenes, 1 pause |
| 7.3 | The coverage report: direct, related, same chapter (P8) | 40 | – |
| 7.4 | Writing the first cut in two rounds (exact matches, then fill), rules 1–11 (P9: an idea vs a visible thing) | 155 + 1,271 | 25 real, 20 AI shots |
| 7.4.1 | Doubtful boundaries: free frames or a paid closer look | (in 7.4) | no paid look |
| 7.5 | The tool's check: act-on warnings first (P11) | (in 7.4) | to read |
| 7.6 | The second look, one helper per scene (O4–O6) | (in 7.4) | to read: whether helpers ran |
| 7.7 | The review film and page (design/127: by scene and shot), the first answer approves | 74 | two versions; approved 15:45 |

Total: 1,792 words of instructions. Free except a paid closer look (none used).

### 7.1 — Prepare: the package for reading (reviewed 30 Oct 2026)

**What happened on VW-12:** prepare wrote the reading files from the stored package (9 scenes, 45 sentences, 46 clip cards, 112 pieces). Free, seconds. I rebuilt VW-12's reading files on this PC from its stored package with the live chat tool's own code (tested, not estimated):

| Part | Size | About (4 characters a token) |
|---|---|---|
| Pieces, by scene (12 files) | 211 KB | 53,000 tokens |
| Word timings (2 files; read only for pauses) | 68 KB | 17,000 tokens |
| Coverage, narration, scenes, prompt, shapes, the rest | 49 KB | 12,000 tokens |
| **Total** | **328 KB** | **about 82,000 tokens** (65,000 without the word files) |

**Findings (I read `options_reading_files`, `pieces_by_scene` and step 0)**
- Works: one file per scene with its sentences and the pieces that fit, direct first (P3); a piece's full row on demand.
- ⚠ **Too much to read again (point 11):** P3 measured about 47,000 tokens on VW-11's package; VW-12's is about 65,000 without the word files. The cause is P8 (the clip study's matches kept): a piece is now listed under every scene it fits, so the 112 pieces fill **343 rows** (150 direct, **177 related**, 15 same chapter). The related rows alone are 103 KB (about 26,000 tokens): more than the direct ones, for pieces the cut uses least.
- Nothing paid; no keys; nothing parallel; no decision; no block; no helper; no older way; no label; not part of a shot's fingerprint.

**Proposed (waiting for SK)**
- **OP1 — A related piece in one short line:** in each scene's file, the direct and same-chapter pieces keep their row; a related piece is listed in one line (its id, clip, grade, length and what is seen, once per clip); its full row is printed on demand (`vw options show --sub`, as today). Expected on VW-12: pieces 211 KB → about 130 KB; the reading about 65,000 → 45,000 tokens (without the word files). Hurts: every film with many clips (the reading before any choice). Work: the reading files only (the stored package and the server's check unchanged) and a test. Breaks: nothing stored; films in progress get it at their next prepare. Undo: the old rows. Operator: nothing. Success: on VW-12's package, every piece its cut used is in the files, the related ones in one line each, and the reading measures under 50,000 tokens. **Older way:** retired in this release (the full related rows; the stored package keeps every detail).

| Decided | Parked | Open |
|---|---|---|
| OP1 agreed (SK, 30 Oct 2026: "Yes, approve OP1") | – | – |

**For the builder (OP1):** `plugin/scripts/vw.py` `pieces_by_scene`: a piece whose fit is `related` is written as one short row (`sub_clip_id`, `clip_name`, `grade`, `duration_s`, `fit`, and `seen` once per clip); direct and chapter rows unchanged. Test on a package copy: related rows carry only those keys; every direct row unchanged; VW-12's pieces files under 140 KB.

### 7.2 — Scenes and pauses (reviewed 30 Oct 2026)

**What happened on VW-12 (I read the stored package):** 9 scenes, one per paragraph, each naming **one** chapter (The housing need: Housing construction today; What rat-trap bond is: Bricks on edge and the hollow cavities; Why it is different: Exposed-brick walls and cool interiors; Environmental benefits: Brick kilns and brick transport; Quality bricks: Brick quality and strength testing; The construction process: Laying bricks on edge; Structural details: Junctions, corners and sill course; Pointing and curing: Pointing the joints; Conclusion: Completed rat-trap bond homes). One pause: 2 s after word 608, "sets the conclusion apart from the technical steps". Approved "Yes, approve". Free.

**Findings (I read step 1, the scene check, and the pieces' chapters in the package)**
- ⚠ **P7 (one chapter per scene) was met in name only (point 6: a rule the AI cannot follow cleanly):** P7 says "a paragraph covering two [chapters] is split where the second begins", and the tool warns only when a scene **lists** two chapters. Paragraph 6 covers five chapters (plinth and mortar, guide strings, laying, clean cavities, line and level); the assistant listed one, "Laying bricks on edge", and split nothing, so the warning stayed silent. Six chapters are named by no scene; three of them carry footage: **Checking line, level and plumb (19 pieces), Preparing the plinth and mortar (7), Keeping the cavities clean (4)**. Those 30 pieces reached scene 6 only through the clip study's own matches (P8), which is why scene 6 still got the most footage (33 s).
- What P7 was for (one slide and one answer per step) is now given by design/127: the review page answers shot by shot. Keeping nine scenes was the better outcome (fewer slides, no one-sentence scenes).
- The pause: 2 s of silence (camera sound is excluded), approved by the operator. Fine.
- Nothing paid; no keys; nothing parallel; no helper; no label; not part of a shot's fingerprint (scenes set later timings; this changes new films only).

**Proposed (waiting for SK)**
- **OP2 — A scene lists every chapter its paragraph covers; no forced split:** step 1's "a scene covers one chapter: a paragraph covering two is split where the second begins" becomes "list every chapter the paragraph covers; split a paragraph only when the operator asks", and the tool's two-chapter warning goes. Effect: a piece's "same chapter" fit counts for every step of the paragraph (on VW-12, the 30 pieces above). Hurts: process films whose paragraphs hold several steps (common). Work: one sentence of step 1, one warning removed, a test. Breaks: nothing; new films. Undo: the old sentence and warning. Operator: nothing (the shot-by-shot page gives the per-step answer). Cost and time: none. Success: on the next process film, its process scene lists all its chapters and the report's same-chapter count includes those pieces. **Older way:** P7 (design/125, 30 Oct) retired in this release, replaced by design/127's per-shot answers.

| Decided | Parked | Open |
|---|---|---|
| OP2 agreed (SK, 30 Oct 2026: "Yes, approve OP2") | – | – |

**For the builder (OP2):** `server/procedures/v3.json` `options.steps[1]`: the sentence replaced as above (trace); the scene check's two-chapter warning removed (`stage2`), its test replaced by "a scene listing three chapters passes without a warning". design/35: P7 listed as retired by OP2.

### 7.3 — The coverage report (reviewed 30 Oct 2026)

**What happened on VW-12 (read in the stored package):**
| Scene | Direct | Related | Same chapter | Alert |
|---|---|---|---|---|
| 1 The need for better building | 1 | 24 | 2 | – |
| 2 What rat-trap bond is | 37 | 37 | 0 | – |
| 3 Why it is different | **17** | 36 | 1 | – (VW-11: zero coverage) |
| 4 Environmental benefits | **1** | 0 | 0 | – (VW-11: zero coverage) |
| 5 Quality bricks | 4 | 4 | 0 | – |
| 6 The construction process | 66 | 16 | 0 | – |
| 7 Structural details | 12 | 32 | 0 | – |
| 8 Pointing and curing | 1 | 7 | 0 | – |
| 9 Conclusion | 7 | 18 | 11 | – |

**Findings (I read the coverage in the package and step 2)**
- **P8 works:** no scene shows zero coverage; "direct" now means the clip study matched the piece to that paragraph, not merely the same chapter; scenes 3 and 4 have footage to choose from, and both got some in the cut (7 s and 5.5 s).
- Not recorded on the server (shown in chat); 40 words; nothing paid; no keys; no block; no helper; no older way; no label; not part of a shot's fingerprint. **Nothing to change.**

| Decided | Parked | Open |
|---|---|---|
| 7.3: no change | – | – |

### 7.4 — Writing the first cut (reviewed 30 Oct 2026)

**What happened on VW-12 (I read the stored cut, version 2, proposed 15:08 IST):** 9 scenes cut, none AI-only. **25 real shots** (16 direct matches, 9 B-roll), median 4.2 s; **20 blanks** for AI (3.4 to 18.6 s); 8 alternatives offered on shots; 3 notes for the operator; every self-check point passed.
- **P9 works:** scene 3's "the exposed brick pattern is visually attractive" is shown by real footage (C0134, an unplastered exposed-brick finish); the scene's claims (thermal barrier, 25 %, strength, three storeys) are blanks for graphics.
- **O7 used:** one clip (C0104) appears twice in scene 6, on parts that do not overlap and at different shot sizes.
- **Blanks with footage nearby (checked, not a fault):** "plinth swept and wetted" (4.2 s) and "guide strings stretched" (3.5 s) are blanks; I read the 30 pieces of those chapters: none shows a plinth being cleaned or wetted (they sweep brick courses) and none shows guide strings, so the exact-match rule is right.

**Prompts that write prompts (point 7):** each blank's "what it must show" becomes the visuals stage's gap description. Real examples: "Graphic: brick strength matched to building height; a single-storey house with 20 kg/cm² minimum crushing strength…", then "Graphic continues: two storeys 35 kg/cm², three storeys 75 kg/cm²"; "Water curing: a worker sprays and wets a finished rat-trap bond wall, the brickwork darkening with water". Clear, one picture each, the narration's own figures. One to note: scene 3's "studies show performance comparable to conventional bonds" carries a claim the web check found generous (3.3); keeping the wording was the operator's choice, and the graphic will say what the voice says.

**Findings**
- Decisions at once (point 12): about 70 in one pass (9 scenes, 25 shots, 20 blanks, 8 alternatives): the second look (O4–O6) is for this; whether it ran is 7.6.
- Too much to read: OP1. Nothing paid (no closer look); no keys; no block; no helper here; no older way; no label; not part of a shot's fingerprint. **Nothing to change.**

**Assumed without checking:** that the 8 alternatives and 3 notes reached the page as questions (7.7 reads the page).

### 7.4.1 — Doubtful boundaries (reviewed 30 Oct 2026)
No paid closer look on VW-12 (the cut's inspection cost is empty); whether free frames were looked at is in the chat. Nothing to discuss.

| Decided | Parked | Open |
|---|---|---|
| 7.4, 7.4.1: no change | – | – |

### 7.5 — The tool's check (reviewed 30 Oct 2026)

**What happened on VW-12 (I read the stored cut's warnings):** 47 warnings, no refusal left. For information (P11 counts them in one line): R1 16 (a cut not at a natural cut point), R10 12 (colour group changes), R4 4 (energy drops): 32. To act on: **N17 10**, E2 4 (an AI blank over 12 s), R5 1 (a wide shot held under 4 s): 15. P12 at work (no "refused from the next release" promise).

**The 10 N17 warnings, read one by one:** each says "step … is shown by a clip of the stage X; the scene narrates Y: the right step? **(the operator decides)**". The tool has already refused any such shot without a reason (the assistant gave one for each), so this warning comes after the reason. Then:
- **Nothing takes it to the operator:** the cut carries 3 questions for the operator (a soft focus, rough bricks, mortar over the cavity), none of them from N17; the review page does not show the check's warnings. "The operator decides" is never true.
- **Most are false alarms from the one-chapter scenes (7.2):** scene 6's "attention is given to maintaining alignment, level" shown by a clip of "Checking line, level and plumb", and "care is taken to prevent mortar from falling into the cavities" shown by "Keeping the cavities clean", are the right steps; they fire only because scene 6 named one chapter. OP2 removes these. Others are idea sentences shown by finished homes (scenes 2, 3, 4), which P9 allows.

**Findings (I read `stage2/validator.py`'s N17 check and the step's act-on list)**
- ⚠ **A warning that asks for a decision nobody is asked (point 19, the other voices):** N17's chapter warning ends "(the operator decides)" and is listed with the warnings to act on, after the tool has already required the reason it wants.
- E2: the four long blanks are graphics that build ("Graphic continues…") or a summary graphic; the visuals stage breaks AI video over 12 s anyway. No change.
- Nothing paid; no keys; nothing parallel; no block; no helper; no older way; no label; not part of a shot's fingerprint.

**Proposed (waiting for SK)**
- **OP3 — N17's chapter warning counted for information:** once the shot has its reason (already required), the "shown by a clip of another stage" warning is counted with R1, R10, R4 and R8 in the one information line, and its "(the operator decides)" goes. N17's claim warning ("a claim shown by footage") stays to act on. On VW-12: act-on 15 → 5 (with OP2 the count line also shrinks). Hurts: every process film (warnings to read past). Work: the warning's text and its group (one server file) and a test. Breaks: nothing stored. Undo: the old group. Operator: nothing. Success: on VW-12's cut, the act-on list is the 4 E2, the 1 R5 and no N17 chapter warning. **Older way:** retired in this release.

| Decided | Parked | Open |
|---|---|---|
| OP3 agreed (SK, 30 Oct 2026: "Yes, approve OP3") | – | – |

**For the builder (OP3):** `server/app/stage2/validator.py`: the "shown by a clip of the stage …" N17 flag gets its own kind counted in `for_information`, without "(the operator decides)"; the claim N17 flag stays act-on. Test on VW-12's cut: `act_on` holds 4 E2 and 1 R5 only. The options step's act-on list (v3 steps[3]) says "N17 (claims)" (trace).

### 7.6 — The second look, one helper per scene (started 30 Oct 2026)

**What the server shows (read in storage):** the timeline: package 11:57; scenes 12:00 and 12:01 (two versions); first cut version 1 proposed **12:27** (26 minutes after the scenes; VW-11's one pass took 5); version 2 proposed 15:08 after design/127's deploy, with 8 of 9 scenes cut differently. **Neither stored cut records whether a second look ran:** the helpers' files (`out/second-look/<scene>.json`) stay on the operator's laptop and `join-second-look` leaves no mark in the cut. The 26 minutes fit a second look, but that is a guess.

**SK, 30 Oct 2026: "Skip, go to 7.7".** Not verified whether the second look ran on VW-12.

| Decided | Parked | Open |
|---|---|---|
| 7.6 skipped by SK | the second look leaves no mark on the server (its run and fixes cannot be read after the fact) | whether the helpers ran on VW-12 |

### 7.7 — The review film and page (reviewed 30 Oct 2026)

**What happened on VW-12 (read in storage and in the run's session):** version 2's review film rendered 15:08:53 → 15:11:41 (2.8 min, free): **377.4 s** for 296 s of narration, built from 95 items (17 slates: 9 scenes and 8 alternatives; 20 AI cards under the narration; 33 footage pieces with their label strip). The operator answered on the page from 15:45:46 to 16:02:03 (**16 minutes, 28 answers**): 25 shots (20 Keep, 5 Reject: 1.2, 6.1, 6.7, 8.1, 9.4, none with a note) and 3 alternatives taken; the first answer (#1.3 Keep) approved the options, and the run moved to master by itself (design/127 and P14 at work).

**Prompts that write prompts (point 7):** each AI card shows the words and "For AI: …" (the blank's description), so the operator reads the request the visuals stage will get.

**Findings (I read `stage2/slides.py` and the render list)**
- Works: scene numbers and shot numbers (1.3, 6.7), alternatives opening only when their shot is rejected, AI-only shots needing no answer.
- ⚠ **Words run together on the cards:** the card text is cleaned to plain letters by dropping every character outside basic English (`ascii_text`), so a dash disappears with no space: VW-12's first card reads "a major **challengehow** to build", from "challenge—how". The same happens to any dash (—, –) and to curly quotes and apostrophes (’ is dropped: "it’s" → "its"). The script has dashes in scenes 1 and 2.
- Nothing paid; no keys; rendering is one job; no block; no helper; no older way; no label; not part of a shot's fingerprint.

**Proposed (waiting for SK)**
- **OP4 — Dashes and curly quotes kept readable on the cards:** before the cleaning, a dash becomes " - " and curly quotes become straight ones. Hurts: every film whose narration has dashes or apostrophes (most). Work: one line in `ascii_text` and a test. Breaks: nothing stored; a film's next render shows it. Undo: the old line. Operator: nothing. Success: VW-12's first card reads "challenge - how". **Older way:** retired in this release.

| Decided | Parked | Open |
|---|---|---|
| OP4 agreed (SK, 30 Oct 2026: "Yes, approve OP4") | – | – |

**For the builder (OP4):** `server/app/stage2/slides.py` `ascii_text`: before the NFKD cleaning, "—" and "–" become " - ", "’" and "‘" become "'", "“" and "”" become '"'. Test: "challenge—how" gives "challenge - how"; "it’s" gives "it's".

### Stage 7 closing table (30 Oct 2026)
| Decided | Parked | Open |
|---|---|---|
| OP1 (related pieces in one line), OP2 (a scene lists every chapter; P7 retired), OP3 (N17's chapter warning for information), OP4 (dashes and quotes on the cards); P8, P9, P13, P14, O7, design/127 seen working | the second look leaves no mark on the server | whether the second look ran on VW-12 (7.6, skipped by SK) |

---

## Stage 8 — The master

### What happened on VW-12 (read in the database and storage)
| Step | When (IST) | What |
|---|---|---|
| Answers on the review page | 15:45:46 → 16:02:03 (16 min) | 28 answers: 20 shots kept, 5 rejected (1.2, 6.1, 6.7, 8.1, 9.4; no reasons), 3 alternatives taken; no trim |
| Master built and rendered | 16:03:08 → 16:05:20 (2.2 min) | 296.28 s, loudness −16.4 LUFS, peak −2.6 dB |
| Master and first cut approved | 16:19:26 (14 min after the film was ready) | "Watched and listened to the master, approved" |
| Gaps handed to visuals | 16:19 | **12 gaps**, 3.5 to 45.6 s; neighbouring blanks joined (scene 5: one 45.6 s gap); 2 rejected shots without an alternative became gaps ("in place of rejected Scene 6 · Shot 1: …", "… Scene 8 · Shot 1: …") |
| Visuals started | 16:20 | (stage 9) |

### The map of the stage (agreed: SK, "Yes, start at 8.1")

Words: the live v3 master steps (478; the first-cut step 13). Refusals: the stage's checks (I read `stage2/stage.py`).

| # | Sub-step | Words | VW-12 |
|---|---|---|---|
| 8.1 | Answering the shots (page by default; chat with the question tool, four a message): Keep, Reject, Trim; alternatives after a Reject; the first answer approves the options | 289 | 28 answers in 16 min, on the page |
| 8.1.1 | A trim turned into frames | (in 8.1) | none |
| 8.2 | Building the master: a rejected shot takes its kept alternative or becomes a blank; neighbouring blanks join; blanks under 3 s, trims that change a scene's length and a clip used twice refused | 163 (with 8.3–8.5) | built |
| 8.3 | Rendering, waiting, fetching | (in 8.2) | 2.2 min |
| 8.4 | Approval: watched and listened, master and first cut recorded together | (in 8.2) | 16:19 |
| 8.5 | A client rule from a rejection note (on the operator's yes) | (in 8.2) | no note, no rule |
| 8.6 | The gaps handed to the visuals stage | 26 | 12 gaps |

Total: 491 words. Nothing paid.

### 8.1 — Answering the shots (reviewed 30 Oct 2026)

**What happened on VW-12 (read in the run's session):** on the review page (design/127 live since 14:30; its page fault, the page stuck at "Loading", fixed at 15:21, before the operator began). 28 answers in 16 minutes (15:45:46 → 16:02:03), about 35 s each, in film order: 20 shots kept; 5 rejected, none with a reason (1.2, 6.7 and 9.4 then took their alternative; 6.1 and 8.1 had none to take); no trim. The first answer approved the options.

**Findings (I read step 0, 289 words, and the session's answers)**
- Works: one answer per shot, alternatives offered only after a Reject, scene headers and AI shots needing nothing, the first answer approving.
- Noted for 8.6: the reason for a Reject is optional and none was given, so the two rejected shots without an alternative reach the visuals stage described only by their words (see 8.6).
- Nothing paid; no keys; nothing parallel; no block; no helper; no older way; no label; not part of a shot's fingerprint. **Nothing to change.**

### 8.1.1 — A trim turned into frames
Not reached on VW-12 (no trim). Nothing to discuss.

| Decided | Parked | Open |
|---|---|---|
| 8.1, 8.1.1: no change | – | – |

### 8.2 — Building the master (reviewed 30 Oct 2026)

**What happened on VW-12 (read in the master record):** built at 16:03 with no refusal: rejected shots 1.2, 6.7 and 9.4 took their kept alternative; 6.1 and 8.1 had none and became blanks; neighbouring blanks were joined (scene 3's five blanks became two gaps of 21.3 and 16.4 s; scene 5's four became one of 45.6 s). Free.

**How a rejected shot's gap is described (I read `stage2/stage.py`, the build):** "in place of rejected Scene 6 · Shot 1: Construction begins with proper preparation of the plinth surface. The" (the shot's title and the words spoken under it), then joined with the next blank's description. VW-12's two:
- "in place of rejected Scene 6 · Shot 1: Construction begins with proper preparation of the plinth surface. The; Plinth top swept clean of dust and loose material…"
- "in place of rejected Scene 8 · Shot 1: Since the brickwork often remains exposed, pointing is carried; Pointing: on a finished exposed rat-trap bond wall, a mason fills…"

**Findings**
- Works: the refusals (a scene sent back to find footage, a blank under 3 s, a trim that changes a scene's length, a clip used twice) and the joining.
- ⚠ **The parked item of design/125 (8.2.4), still true (point 7, prompts that write prompts):** a rejected shot's gap tells the visuals stage only the words (which it gets anyway, after "| narration:"). It does not say **what the rejected footage showed** (what the operator turned down, so the picture does not repeat it), and **the operator's reason, when given, is dropped**: the build reads the answer's action but never its note (the note is used only to propose a client rule, 8.5).
- Nothing paid; no keys; nothing parallel; no block; no helper; no older way; no label. Fingerprint: the gap's description is what the visuals stage plans from; this changes only new masters.

**Proposed (waiting for SK)**
- **MA1 — A rejected shot's gap says what was turned down and why:** "in place of rejected Scene 6 · Shot 1 (it showed: <the piece's 'what is seen'>; the operator: <their reason, when given>)". The words stay in the gap's narration part, not repeated. Hurts: every film with a rejected shot and no alternative (VW-12: 2). Work: one line in the build and a test. Breaks: nothing stored; masters already recorded keep their gaps. Undo: the old line. Operator: nothing (a reason, when they give one, now reaches the pictures). Success: on VW-12's answers, gap 6's description carries the rejected clip's "what is seen" line and no narration fragment. **Older way:** retired in this release.

| Decided | Parked | Open |
|---|---|---|
| MA1 agreed (SK, 30 Oct 2026: "Yes, approve MA1") | – | – |

**For the builder (MA1):** `server/app/stage2/stage.py`, the build's rejected-shot blank: `intent` = f"in place of rejected {title} (it showed: {the piece's card overview}" + (f"; the operator: {note}" if the answer has a note) + ")"; the words no longer repeated in the intent. Test: a rejected shot without an alternative gives that intent, with and without a note.

### 8.3 — Rendering the master (reviewed 30 Oct 2026)
16:03:08 → 16:05:20 (2.2 min, free): 296.28 s, loudness −16.4 LUFS, peak −2.6 dB (the mix rule's target −16). Nothing to discuss.

### 8.4 — Approval (reviewed 30 Oct 2026)
Recorded 16:19:26, 14 minutes after the film was ready, with "Watched and listened to the master, approved" (both said, as the step requires); master and first cut recorded together. Nothing to discuss.

### 8.5 — A client rule from a rejection note
Not reached (no reason given on any Reject; no rule added). Nothing to discuss.

### 8.6 — The gaps handed to the visuals stage (reviewed 30 Oct 2026)

**What happened on VW-12 (read in the master record):** **12 gaps, 185.9 s (63 % of the film)**, from 3.5 s (guide strings) to 45.6 s (scene 5: a brick close-up, the strength graphic in two parts, the testing machine); each gap carries the cut's descriptions in order, joined by ";", then the narration under it. The visuals stage started at 16:20.

**Findings (I read step 2, 26 words, and the gaps)**
- Works: every AI stretch and every rejected shot without an alternative became a gap with its description; joined gaps keep each description in order, so the visuals plan sees the cut's intended shots.
- The 2 rejected-shot gaps: MA1. A 45.6 s gap is long, but the visuals stage already breaks AI video over 12 s with footage or stills (its own rule).
- Nothing paid; no keys; no block; no helper; no older way; no label. **Nothing else to change.**

| Decided | Parked | Open |
|---|---|---|
| 8.3–8.6: no change beyond MA1 | – | – |

### Stage 8 closing table (30 Oct 2026)
| Decided | Parked | Open |
|---|---|---|
| MA1 (a rejected shot's gap says what was turned down and why; design/125's parked 8.2.4 item closed) | – | – |

---

## Stage 9 — Visuals

The visuals stage has its own flowchart: `design/visuals-flowchart.md` (created 30 Oct 2026 from design/121 and 124, then grown phase by phase). Phases 1–4 were reviewed on earlier films (design/121, 124); on VW-12 each phase is walked again by its sub-steps with the review prompt, without raising again what was decided there.

### Where VW-12 is (read in the database and storage, 30 Oct, about 17:00 IST)
| Step | When (IST) | What |
|---|---|---|
| 1 Preparation | 16:20–16:21 | package written (240 KB) |
| Defect 34 | filed 16:43, fixed 16:48 (by another session, server only) | "vw next reports paid: openai-images" on a Nano Banana film; a fixed label, the pictures already followed the run's choice |
| 2 Treatment and after | not started | – |

### Phase 1 — Preparation: the map (waiting for SK's yes)

Words: the live v3 visuals common part (1,168, read at every step) and the preparation part (151) and step (20). VW-12's package as stored: world files 85 KB (46 clips), the parts 54 KB, source 42 KB, plan form 27 KB, footage look 14 KB, brief 4 KB, intended pictures 3 KB, claims 1 KB.

| # | Sub-step | Words | VW-12 |
|---|---|---|---|
| 9.1.1 | `vw visuals prepare`: the package as files, the parts per step, the prompt guide per step | 151 + 20 | 16:20, 240 KB |
| 9.1.2 | What to read first: prompt.md, gaps, intended pictures, claims; the world files at the plan | (in 9.1.1) | – |
| 9.1.3 | The footage look, measured from the clips, told in one line; corrected on the page | (in 9.1.1) | "camera not known, tripod, natural look" |
| 9.1.4 | The page link and the "what next" message (with the paid line of defect 34) | (in 9.1.1) | defect 34 |
| 9.1.5 | The common part (sections A–D) read at every step | 1,168 | – |

Free; nothing paid at this phase.

**SK, 30 Oct 2026:** "We will review this again with the prompt as we have many additional checks added." The visuals stage is reviewed separately, phase by phase, with the review prompt (vw2-notes/124-c4-review-prompt.md, with its added checks); this map and the flowchart are its starting point. design/126 ends here: stages 0–8 reviewed on VW-12.

**SK, 30 Oct 2026: "1 Preparation - step"** — the phase named; its review starts here, with every point of the prompt (1–22). From the rule list (design/124-a0): 21 preparation rules (7 in the steps, 1 in the guide, 6 server refusals, 7 "what next" lines); two of them flagged as contradicting in October (R2191/R2290: plan before treatment), fixed by design/124 Change 1 (I read the live server's message: treatment first, then the plan).

### 9.1.1 — `vw visuals prepare` (reviewed 30 Oct 2026)

**What happened on VW-12 (read in storage):** session 16:20, package 16:21 (240 KB): 12 gaps with timed narration and neighbours, 9 intended-picture scenes, 6 claims, the brief with its rules, the footage look (14 KB, per clip), 46 world files (85 KB: people, objects and landmarks per clip), the plan form (27 KB), the video tools, the instructions (common part and 5 parts, 54 KB). Free, seconds. The chat tool wrote one file per section and the prompt guide per step.

**Findings (I read the server's `visuals_stage.prepare`, the chat tool's `visuals prepare` and its message, the preparation part, 151 words, and step 0)**
- Works: one "what next" (treatment, then the plan: Change 1); the instructions split by step (C2): the chat tool says "read prompt.md once, then part-<step>.md when you reach that step"; the version-1 evidence retired by refusal (design/125).
- ⚠ **The other voice is behind (point 19):** the chat tool's message says "Read prompt.md, gaps.json and intended-visuals.json first"; the preparation part (since S3, design/125) says those **and claims.json** (the figures, checked or not). The message's own read list is a third copy (the step says it too) and the one that is out of date.
- Too much input (point 11): read first, about 1,500 words of instructions plus the gaps, intended pictures and claims: fine; the 85 KB of world files wait for the plan (as the part says).
- Nothing paid; no keys; nothing parallel; no decision; no block; no helper; no older way; no label in the part; not part of a shot's fingerprint.

**Proposed (waiting for SK)**
- **VI1 — The chat tool's message points to the part instead of its own list:** "Read prompt.md, gaps.json and intended-visuals.json first." becomes "Read prompt.md, then part-preparation.md (what to read first)." (9 → 8 words). One list (the part's, with claims.json) instead of three. Hurts: every film (the claims can be missed at the treatment). Work: one line of the chat tool and a test. Breaks: nothing. Undo: the old line. Operator: nothing. Success: on the next film, the message after prepare names part-preparation.md and the assistant reads claims.json before the treatment. **Older way:** retired in this release.

| Decided | Parked | Open |
|---|---|---|
| VI1 agreed (SK, 30 Oct 2026: "Yes, approve VI1") | – | – |

**For the builder (VI1):** `plugin/scripts/vw.py`, `visuals prepare`'s message: the replacement above; test: the message names part-preparation.md and no longer lists gaps.json.

### 9.1.2 — What to read first (reviewed 30 Oct 2026)
Covered by VI1 (one list, the part's, with claims.json). The world files are read at the plan, as the part says. Nothing else to discuss.

### 9.1.3 — The footage look, measured and told (reviewed 30 Oct 2026)

**What happened on VW-12 (read in the package):** "Your footage: camera not known, tripod, natural look (measured from the clips)": camera unknown on 45 clips (Sony's "C0123" file names are deliberately not classified: they can be a mirrorless or a cinema camera), drone on 1; support tripod on 32, gimbal 10, handheld 4 (two thirds is the bar: tripod); look natural on all 46. No correction recorded.

**Findings (I read `server/app/footage.py` and where the result is used)**
- Works as designed (design/88): measured, told in one line, corrected only with the operator's words (on the page or `vw visuals footage`); its three refusals (no words; no value; a value outside the list) are in place.
- "Camera not known" costs nothing: the camera is used only to add a phrase ("mirrorless camera") to the picture requests' texture line, and an unknown camera is simply left out (I read the one place it is used). The operator may still correct it.
- Nothing paid; no keys; no block; no helper; no older way (ME1 retires the media step's guess); no label. **Nothing to change.**

### 9.1.4 — The page link and the "what next" message (reviewed 30 Oct 2026)

**What happened on VW-12:** the page link and the footage line were given (the chat tool's message carries both). At 16:43 the operator filed **defect 34**: `vw next` said "paid: openai-images,video" on a Nano Banana film. The other session's fix (16:48, server only, d1335eb): a wrong label, not a wrong model (the pictures follow the run's choice); `vw next` now names the run's own picture AI. I read the defect and its resolution in the database.

**Findings:** fixed already; the instruction file's own `paid` field still reads "openai-images,video" (the fix computes the line per run instead). Nothing else; **nothing to change** here.

### 9.1.5 — The common part, read at every step (reviewed 30 Oct 2026)

**What it is:** sections A–D (stop and ask, never guess; the routes; the shared rules; the reading guide), 1,168 words, read with every part. Tidied in design/124 (Phase B, C1).

**Findings (I read it whole)**
- No "design/" label inside it (searched), no contradiction with the preparation part.
- **One version label left (point 16):** its heading reads "VW-VISUALS v2.0 — direction, references, pictures and takes for the blanks of the first cut" on instruction version 3; "v2.0" means nothing to the assistant (the same kind of heading BR2, SC… removed in design/125).
- Nothing paid; no keys; no block; no helper; no older way; not part of a shot's fingerprint.

**Proposed (waiting for SK)**
- **VI2 — The version label removed from the heading:** "VW-VISUALS v2.0 — direction, references, pictures and takes for the blanks of the first cut" becomes "Visuals: direction, references, pictures and takes for the blanks of the first cut" (15 → 13 words). Work: one replacement (the split check `c1_split_v3.py` updated) and a test. Breaks: nothing. Undo: the old heading. **Older way:** retired in this release.

| Decided | Parked | Open |
|---|---|---|
| 9.1.2–9.1.4: no change; VI2 declined (SK, 30 Oct 2026: "Leave it") | – | – |

### Phase 1 closing table (30 Oct 2026)
| Decided | Parked | Open |
|---|---|---|
| VI1 (the chat tool's message points to the part's reading list); VI2 declined; defect 34 already fixed by another session | – | – |

**Where VW-12 is next (read on the server, 17:07 IST):** the treatment's draft was sent at 16:42 (its direction begins "By the end the viewer should understand that the hollow cavities are the point of rat-trap bond…"); no gap accepted yet, no picture made. Phase 2 is reviewed once the operator has accepted the treatment.

### Phase 2 — Treatment

**What happened on VW-12 (read in the run's visuals session):** the treatment was recorded at 16:42 IST; every line accepted on the page ("accepted by SK", the page's own words, as at the voice). (My reading at 17:07 that it was "not accepted" was wrong: I looked at the plan's acceptances, which are empty, not the treatment's lines.) Its contents:
- **Direction:** the cavities are the point; a documentary explainer told from the site; real footage of masons carries the film; what a camera could have filmed with more time becomes a realistic AI scene (muted, true to life, never the client's own site); what is invisible to a camera (the cavity, heat, load, the saving, strength by storey, the sill) becomes **one drawn cutaway of a rat-trap bond wall that returns and develops across the film**, with the script's figures drawn exactly.
- **12 gaps, 186 s:** video 7 gaps (96.1 s), drawn 5 (76.5 s), a still 5.6 s, a graphic sequence 7.7 s; 20 pictures; nothing held frozen; **estimate ₹935.65**.

**The map (waiting for SK's yes).** Words: the treatment part (832) by paragraph and step 1 (43). Refusals: the server's `treatment` (14) and its line-by-line accept (I read `visuals_stage.treatment`).

| # | Sub-step | Words | Server refusals | VW-12 |
|---|---|---|---|---|
| 9.2.1 | The Direction first (a few lines: the viewer's understanding, the viewpoint, the approach, the roles of footage, stills, scenes and graphics) | 203 | 2 (missing; over 2,000 characters) | written |
| 9.2.2 | Planning the gaps as one progression: graphic or scene by a test, one visual language, variety, the team's intended pictures as a requirement, the opening gap (C4), the look beside no footage | 329 | 0 (some warned at the plan) | one recurring cutaway |
| 9.2.3 | One line per gap (picture, routes, seconds and segments, picture count, what each graphic shows, frozen seconds, shots) and the totals with the cost estimate | 134 | 12 | 12 lines; ₹935.65 |
| 9.2.4 | The draft sent; each line accepted or sent back on the page (C6); recorded when all are accepted | 164 + 43 | (line refusals) | all accepted, 16:42 |
| 9.2.5 | Settled before any plan; a change of direction revises everything it touches | (in 9.2.4) | the plan is checked against it | – |

Total: 875 words, about 14 refusals. Free (no picture is made).

### 9.2.1 — The Direction (reviewed 30 Oct 2026)

**What happened on VW-12 (I read it whole):** 175 words (1,017 characters, under the 2,000 limit). It says what the viewer should understand (the cavities are the point: fewer bricks and mortar, cooler, strong enough for three storeys) and see (the careful work); the viewpoint (a documentary explainer told from the site); the approach (real footage carries the film; what a camera could have filmed becomes a realistic AI scene, muted, natural daylight, a red-brick site in Tamil Nadu, never the client's own site; what is invisible becomes one drawn cutaway that returns and develops, with the script's figures drawn exactly) and why. Accepted on the page.

**Findings (I read the part's first paragraph, 203 words, and the server's two checks)**
- Works: the Direction (design/124 Change 3) is specific and becomes the rule the plan is checked against; it follows the brief (calm documentary, the mason's craft) and the claims (figures drawn exactly).
- Small gap, not proposed: the rule asks for the roles of "footage, stills, generated scenes and graphics"; stills are not named, though the treatment uses one 5.6 s still (scene 3's three-storey building). Harmless: the still is in its gap's line, accepted.
- Nothing paid; no keys; nothing parallel; one decision; no block; no helper; no older way; no label; nothing written twice that disagrees. Fingerprint: the treatment's direction opens the plan's foundation word for word; changing the rule's wording does not change a recorded direction. **Nothing to change.**

| Decided | Parked | Open |
|---|---|---|
| 9.2.1: no change | – | – |

### 9.2.2 — Planning the gaps as one progression (reviewed 30 Oct 2026)

**What happened on VW-12 (I read every gap's line):**
- **The opening gap (C4) works:** the film opens on a gap, and its line is "a wide view of a busy Indian housing site with masons laying a conventional brick wall…, then a family looking at the rising houses": the subject at work, wide first.
- **Graphic or scene by the test:** drawn where a camera cannot see (the cavity, heat, load, strength by storey, the sill course); AI scenes for kilns, plinth, guide strings, pointing, curing, families at home. No numbers invented ("no numbers, as the script gives none" on the load drawing).
- **The team's intended pictures:** every gap cites them ("Follows 'cleaning and wetting the plinth'"); the departures are named with a reason ("as a drawn cutaway rather than 3D"; "the engineer inspecting is folded into the testing scene"; "the drone and finished houses come from the real footage around it").
- **One visual language:** one drawn cutaway returning in gaps 2-B2, 3-B1, 3-B2, 7-B1 and 9-B1.

**Findings (I read the part's second paragraph, 329 words, the treatment check and the plan's graphics rule)**
- ⚠ **A plan rule the treatment does not know (points 3, 13 and 19):** the plan check warns when graphics run more than **8 s** without a camera picture ("break it with a camera shot"; over 12 s "give the reason in the treatment"), the length SK kept on 29 Oct (design/124 decision b). The treatment already states each shot's route and seconds, yet neither the treatment's text nor its check mentions the limit, so the operator accepted four runs over it: **gap 5-B1's strength chart, 23.9 s** (over 12 s, with no reason in the treatment), 2-B2's cutaway 11.8 s, 3-B2's load drawing 10.8 s, 3-B1's heat drawing 9.1 s. The plan will warn on all four; following the warning changes shots the operator has already accepted.
- To watch (parked): the strength chart is drawn (the cutaway's language) while the resource icons of gap 4-B1 are an AI graphic sequence (a different maker); whether they read as one language shows at the pictures.
- Nothing paid; no keys; nothing parallel; no helper; no older way; no label; not part of a shot's fingerprint (the treatment is checked, not fingerprinted).

**Proposed (waiting for SK)**
- **TR1 — The treatment warns on a graphics run over 8 s, as the plan does:** the treatment check reads each gap's `shots` (route and seconds) and gives the plan's own warning ("… s of graphics in a row: above 8 s, break it with a camera shot; above 12 s, give the reason in the treatment"), shown with the draft on the page before the operator accepts. No instruction text added (the warning says what to do). Hurts: every film with diagrams or charts (VW-12: 4 of 5 drawn gaps). Work: the treatment check reuses the plan's rule (one server function) and a test. Breaks: nothing stored; a treatment already accepted is not re-checked. Undo: remove the call. Operator: sees the warning on the line before accepting. Success: VW-12's treatment re-checked gives the four warnings; a treatment whose drawn shots are each 8 s or less gives none. **Older way:** retired in this release (the limit first met at the plan).

| Decided | Parked | Open |
|---|---|---|
| TR1 agreed (SK, 30 Oct 2026: "Yes, approve TR1") | drawn cutaway beside an AI graphic sequence (gap 4-B1): one language? at the pictures | – |

**For the builder (TR1):** `server/app/visuals_stage.treatment`: from each entry's `shots` (route, seconds), the runs of graphic routes (drawn, graphic_sequence, a still that is a graphic) give `visual_contract._graphics_run`'s warning; returned with the draft and shown on the line on the page. Test: VW-12's treatment gives four warnings (23.9, 11.8, 10.8, 9.1 s); drawn shots of 8 s or less give none.

### 9.2.3 — One line per gap, the totals and the cost estimate (reviewed 30 Oct 2026)

**What happened on VW-12 (read in the treatment):** 12 lines, every field present; pictures counted as the rule says (one start picture per video segment: gap 1 two segments, two pictures; gap 8 three segments, three; gap 4 two videos and a three-state graphic, five); what each graphic shows listed (`depicts`); nothing held frozen. Totals: video 96.14 s, drawn 76.52 s (free: rendered by the server), still 5.56 s, graphic sequence 7.7 s; 20 pictures; **estimate ₹935.65** (20 × ₹4 + 96.14 s × ₹8.90). The page shows "spend ₹0 of ₹5,000" (SK's screenshot).

**Findings (I read the part's third paragraph, 134 words, the treatment check, `prices`, `image_cost_inr`, `visuals_spend` and every place an estimate is made)**
- Works: the 12 refusals (a gap missing or twice, an unknown route, a picture line missing, seconds, a count that is not a whole number, frozen seconds…).
- ⚠ **The estimate prices every picture at GPT Image's figure on a Nano Banana film (point 10):** every estimate uses one flat picture price, ₹4 (the treatment's total, the plan check's "cost against the cap", the budget's "still needs", a fix's "₹4", "make a new start (₹4)"). The spend already counts a Nano Banana picture at its own price ($0.134, about ₹11.8 at ₹88, plus a little per input picture: `image_cost_inr`), so on a Nano Banana film the estimate says one thing and the spend another. VW-12: pictures ₹80 estimated against about ₹236; the treatment's total about **₹1,090, not ₹936**. The live server sets no price of its own (I read its settings: only the Gemini model line).
- Noted, not proposed now: the estimate counts the pictures for the shots only; the reference pictures (one sheet per thing: VW-12's page lists 38 things), the style sheet and any fixes come later and are not in it. Shown at the plan, which knows the things.
- Nothing else: no keys; nothing parallel; no block; no helper; no older way; no label; not part of a shot's fingerprint.

**Proposed (waiting for SK)**
- **TR2 — Every estimate uses the film's own picture price:** one price per film: Nano Banana at its configured dollar price (and the 4K price when asked) times the rupee rate; GPT Image at the configured ₹ figure, as today. Used by the treatment's estimate, the plan's cost line, the budget's "still needs", the cost said for a fix and for a new start. Hurts: every Nano Banana film (VW-12 now; half the team's films). Work: one price function and its callers (one server file) and tests. Breaks: nothing stored; recorded estimates keep their figure, new ones change. Undo: the flat price. Operator: sees a truer figure before accepting. Success: VW-12's treatment re-estimated gives about ₹1,092 (20 × ₹11.79 + 96.14 × ₹8.90); a GPT Image film's estimate unchanged. **Older way:** retired in this release (one flat picture price for both picture AIs).

| Decided | Parked | Open |
|---|---|---|
| TR2 agreed (SK, 31 Oct 2026: "Yes, approve TR2") | reference pictures not in the treatment's estimate: at the plan | – |

**For the builder (TR2):** `server/app/visuals_stage.py`: one `image_price_inr(run, tier=None)` (gemini: `GEMINI_IMAGE_USD` or `_4K` × `VISUALS_USD_INR`; openai: `VISUALS_PRICE_IMAGE_INR`), used by `treatment`, `check`, `budget`, `check_cap`'s per-image amounts, the fix line and the "make a new start" choice. Tests: VW-12's totals on a gemini run give about ₹1,092; the same on an openai run ₹935.65.

### 9.2.4 — Accepting each line on the page (reviewed 31 Oct 2026)
**What happened on VW-12:** the draft was sent and every line, the Direction and the 12 gaps, was accepted on the page, each recorded with the page's own words "accepted by SK" (the operators sign in with SK's account, as noted at 0.2 and 4.7); no line sent back. Works as built (design/124 Change 6). TR1 adds the 8 s warning to the lines before they are accepted. **Nothing else to change.**

### 9.2.5 — Settled before the plan (reviewed 31 Oct 2026)
The plan was written after the treatment was recorded, and the server checks the plan's routes against it (VW-12's run is now at the picture search, so its plan passed). Nothing to discuss.

### Phase 2 closing table (31 Oct 2026)
| Decided | Parked | Open |
|---|---|---|
| TR1 (the 8 s graphics warning at the treatment), TR2 (estimates at the film's own picture price) | the drawn cutaway beside an AI graphic sequence: at the pictures; reference pictures in the estimate: at the plan | – |

**SK, 31 Oct 2026:** "Covered all the points that are mentioned" (U1–U7 as proposed, U5 at 12 words, U6 in the picture's panel). Phase 3 (the detailed plan) next: VW-12's plan was proposed at 17:13 on 30 Oct (stored, 276 KB) and its run is now at the picture search; reading it needs the VM sign-in (gcloud), expired on 31 Oct.

## Issues reported by the users (SK's screenshots, 30 Oct 2026)

Checked in the live code (main d1335eb; pages `templates/review.html` and `templates/visuals.html`) and VW-12's stored session. Nothing built.

| # | Page | What the users saw | What I found | Status |
|---|---|---|---|---|
| U1 | Options review page (design/127) | The film highlights the shot playing on the right, but the list does not scroll to it; the highlighted row is off screen | I read it: on every tick of the film the page moves the highlight (`cur`) but never scrolls; it scrolls only when the film stops for an answer. After the answers close (VW-12: "answers closed: the master film is built") it never scrolls | **Not done.** Proposed fix: when the highlight moves, scroll that row into view in the list (one line, `scrollIntoView({block:'nearest'})` beside the highlight), not while the operator is typing a note |
| U2 | Reference pictures, the picture opened beside the list | No way to close the opened picture | A close button (×, and Esc) exists (design/99 C1), but it sits at the top of the panel's own scrolling area: when the panel is scrolled down to the note box, as in the screenshots, the × scrolls out of sight; the panel also scrolls sideways (the scrollbar at its bottom), which can push the × off the right edge | **Built, not usable when scrolled.** Proposed fix: keep the × fixed at the top of the panel (sticky, like the Approve and Reject bar at its bottom) and stop the sideways scroll |
| U3 | Reference pictures, a note on a ticked picture | Earlier, the operator's notes were not saved and not carried to the later steps | design/121 Change 4 is **built and live** (I read it): every note on a picture is added to the reference sheet's request ("The operator's note on Image k: …") and becomes a must point of the picture check; a note changed after the sheet marks it "sources changed". Saving: ticks and their notes stay on the page until the operator saves them (per thing, or Done for the whole pass), shown as "ticked · not saved", with a warning when leaving the step or the page. On VW-12 (read at about 17:30): no web picture saved yet, so **no note saved yet**; the cement-bag note in the screenshot is still "ticked · not saved" | **Done in code; not yet seen on VW-12.** To check after the operator's Done: the notes are on the saved pictures and in the sheet's request |
| U4 | Reference pictures, a Google picture opened beside the list | A footage picture opens the zoom view (− + Close), a Google search picture does not | I read it: the zoom view opens only from a picture already saved for the run (footage frames, saved web pictures, sheets: `data-view` on `big()`); a search result shown in the panel has no `data-view`, so a click does nothing, although the panel's style shows the zoom cursor on every picture (the "+" cursor in the screenshot) | **Not done.** Proposed fix: a search result opens the same zoom view, its Previous / Next moving through that search's results (the panel already has them); no change to saving |

**SK's added requirements (31 Oct 2026), checked in the live code (`templates/visuals.html`, `visuals_stage.py`):**

| # | SK's words (short) | What I found | Status |
|---|---|---|---|
| U3 (again) | "I add a note but there is no way to save this note with the selected image" | A ticked web picture and its note are held on the page until **Save N pictures** (per thing, in the bar at the bottom) or **Done** (the whole pass); the panel itself has no Save, and the note box says nothing about saving. Once a picture is saved, its note has its own "Save the note" (seen on the coconut broom in the screenshot) | **Not done as asked.** Proposed: a **Save** button under the note in the panel, saving that picture with its note at once (the existing per-thing save, for that one picture); the note box says "saved" after it |
| U4 (again) | "I need to be able to zoom in for reference images … only the web search references I'm not able to zoom in on" | As U4 above | **Not done** (U4) |
| U5 | "a restriction in the search string … about six or seven words … whether that is a limitation of the API" | **Our own rule, not the API's:** the server refuses fewer than 2 or more than 6 words ("Keywords are two to six words: the thing and its place or trade… Google Images is not Google search", `visuals_stage.search`), and the box says "two to six words". Google Images through the search service takes longer queries | **Not done.** Proposed: allow up to 12 words (the stock site's name stays outside the count, as today); the box's hint and the instructions' "two to six" changed with it. **Decided (SK, 31 Oct 2026: "Yes, 12 words"): 2 to 12 words** |
| U6 | "if web search is not bringing results … earlier we had an option to upload a user-given reference image or an image link" | It exists: **"Add your own picture"**, a file or an https link, saved and approved for that thing (design/110, live). But it is shown only on a thing's own view (after the round), not in the **round view** the screenshots show (`renderRound` has no such box), which is where a search comes back empty | **Partly done.** Proposed: the same box under each thing's search in the round view, and shown first when a search finds nothing. **SK, 31 Oct 2026:** the upload and link option appears in the same place as the selected picture (the panel on the right where a picture opens), for that thing |
| U7 | "some image requirements I am not able to make out where exactly that will be useful … mention the narration line or the scene description" | A thing's card shows its id, name and kind only (for example "clay_pan · Iron pan of wet clay · object"); the page already holds the plan's shots that show each thing, with their words | **Not done.** Proposed: under each thing's name, "used in": each shot that shows it (gap, shot) with the narration words under that shot and its one-line picture, so the operator can judge and refine the search |

### Phase 3 — The detailed plan (resumed 31 Oct 2026, with the review prompt vw2-notes/124-c4-review-prompt.md, unchanged since 30 Oct 09:27)

**Where VW-12 is in the visuals stage (read on the server, 31 Oct afternoon):** the plan proposed at 17:13 IST on 30 Oct (version 1, the only one) and **all 12 gaps accepted**; the picture search (phase 4) **complete** (108 searches; 27 web pictures and 6 footage frames approved, 6 frames rejected); two size corrections sent (brick, mortar: defect 37) and not yet folded in; **no picture made yet** (no paid job). So phases 3 and 4 are done and reviewable; phase 5 (sheets) has not produced anything.

**VW-12's plan (I read the stored copy):** 38 elements (15 objects, 8 places, 7 people, 5 techniques, 2 materials, 1 process), 23 scenes, **25 shots** (16 AI video, 7 drawn, 1 still, 1 graphic sequence), 2 material specs and 7 drawing specs, no choices; 276 KB; 11 warnings at proposal (cut_off_pause 5, spec_unresearched 2, ai_run 2, life_missing 1, still_long 1). **No graphics-run warning on any drawn shot**, which confirms the builder's finding for TR1: the plan's 8 s rule does not count drawn shots.

**The map (waiting for SK's yes).** Words: the live plan part (3,153) by paragraph and step 2 (35). Server checks: the plan check (`visual_contract.validate_plan`, about 167 refuse or warn lines; counted by sub-step when reviewed).

| # | Sub-step | Words | VW-12 |
|---|---|---|---|
| 9.3.1 | Order of work: plan-base (foundation, elements, style, sequence), helpers write the gaps at once (`vw-plan-gaps`), plan-join, check until valid, warning answers, the review before proposing, propose, accept per gap, revisions | 354 + 35 | proposed 17:13, 12 accepted |
| 9.3.2 | The foundation: world, exclusions, specifications, constraints, appearance; requirement / Proposed / unknown | 292 | – |
| 9.3.3 | Meaning: claims, descriptors, evidence, visual facts, messages | 196 | – |
| 9.3.4 | Elements: exact or representative, footage frames for the client's own, techniques, sizes and material specs, people, a real speaker | 391 | 38 elements |
| 9.3.5 | Scenes and life: activity level, background people and crowds, holds, ambient line, light and air, props, signs of use | 447 | 23 scenes |
| 9.3.6 | Positions, states and beats: landmarks, start and end states, beats, fixed landmarks, gaze | 339 | – |
| 9.3.7 | Timing and movement: cuts in pauses, shot lengths, AI runs, footage shots, motion of stills, sizes and camera reasons, crops, transitions, no picture twice | 534 | 25 shots |
| 9.3.8 | Graphics: builds, drawn shots, labels, claims, one graphic style | 283 | 7 drawn, 1 sequence |
| 9.3.9 | Drawing specs: research order, status, illustrative, the operator's approval table and corrections | 313 | 9 specs; 2 corrections |

Total: 3,188 words. Free (no picture is made).

### 9.3.1 — Order of work (reviewed 31 Oct 2026; SK repeated the map's question, taken as the yes)

**What happened on VW-12 (read in the stored plan and the run's session):** treatment recorded 16:42, plan proposed 17:13 (31 minutes); one version; every gap accepted with "Yes Approved" (the operator's words); 11 warnings at proposal, **15 warning answers**, each in its own box, never in the picture's purpose (design/124 Change 7 at work); the sequence overview says what each gap adds ("Gap 3 introduces the drawn cutaway… Gap 4 develops it"); no open question. Whether the `vw-plan-gaps` helpers wrote the gaps is not recorded on the server (the plan files stay on the laptop).

**Findings (I read the plan part's first paragraph, 354 words, step 2, the plan's warnings and their answers)**
- Works: one pass, checked, answered, accepted gap by gap.
- ⚠ **The treatment fixes lengths the plan then warns about, so the warnings are answered away (points 3 and 13, the same root as TR1):** the plan warns on AI video running back to back over 12 s (`ai_run`: gap 5-B1 13.9 s, gap 8-B1 18.8 s) and a still over 4 s (`still_long`: 3-B2's 5.6 s). Each answer says, in effect, "the accepted treatment set this length" ("The accepted treatment makes this gap three AI video shots (6.6, 5.04 and 7.2 s)…"). The treatment's check knows neither rule, so the operator accepted the lengths without the warning, and the plan's warning came too late to act on. The 12 s run rule is SK's decision (d) of 29 Oct ("AI video is broken up… the run rule stays").
- The `cut_off_pause` answers ("the narration has no longer pause here; the cut falls at the end of the sentence") are real answers: fine.
- Nothing paid; no keys; helpers: not visible; no older way; no label.

**Proposed (waiting for SK)**
- **TR3 — The treatment gives the plan's two other length warnings too:** with TR1's graphics run, the treatment check reads each gap's `shots` (route and seconds) and gives the plan's own `ai_run` warning (AI video back to back over 12 s in a gap) and `still_long` warning (a still over 4 s), shown on the line before the operator accepts. No instruction text added. Hurts: every film with long AI stretches (VW-12: 2 gaps, 1 still). Work: the treatment check reuses the plan's two rules (one server function) and a test; built into the waiting design/126 build with TR1. Breaks: nothing stored. Undo: remove the calls. Operator: sees the warning before accepting the length. Success: VW-12's treatment re-checked gives the two AI-run warnings and the long still. **Older way:** retired in this release (the limits first met at the plan).

| Decided | Parked | Open |
|---|---|---|
| TR3 agreed (SK, 31 Oct 2026: "Yes, approve TR3") | whether the plan helpers ran (not recorded on the server) | – |

**For the builder (TR3):** with TR1 in `visuals_stage.treatment`: from each entry's `shots`, back-to-back `video` shots over `AI_RUN_S` (12 s) give `visual_contract`'s `ai_run` warning, a `still` shot over the plan's still limit (4 s) its `still_long` warning; returned with the draft and shown on the line. Test: VW-12's treatment gives the two AI-run warnings and the long still.

### 9.3.2 — The foundation (reviewed 31 Oct 2026)

**What happened on VW-12 (I read the plan's foundation whole):** six world rules, three exclusions, two specifications, one production and one editing constraint, the appearance, the graphic style, and the treatment opening word for word with the Direction. Every rule names its source: the client card (Kanyakumari, Tamil Nadu), clip findings by clip number (masons in beige or cream collared shirts, dark trousers, sandals: C0088, C0097, C0120…; the site's tools: trowel, tasla, straightedge, plumb bob, coconut-midrib broom), the brief (PPE flags waived, Tamil speech), the claims ("only 25 percent and 20, 35 and 75 kg/cm²; the comparable-strength graphic carries no numbers"). The editing constraint even says what the two rejected shots showed (C0089 clearing the surface, C0100 finishing joints): written by hand, what MA1 will give the stage by itself. Exclusions are real consequences of the Direction (no client signboards or campus; no bad practice shown as right). No invented region or dress.

**Findings (I read the foundation paragraph, 292 words, and the plan check's proportion rule)**
- Works: a casting and production-design brief another director could use.
- ⚠ **An example in the instructions became a rule of the film (point 7, prompts that write prompts; point 20):** the world rule W_bricks says bricks are "about 3 : 1.5 : 1 in length, width and height", marked "Proposed from the usual Indian modular brick". That figure is the instructions' own example ("a spec of a real object its proportions (a brick about 3 : 1.5 : 1 …)"; the server's warning repeats it: "for example a brick about 3 : 1.5 : 1"). The operator's correction says **190 × 90 × 90 mm** (the Indian modular brick, about 2.1 : 1 : 1). Every picture of a brick would follow the example, not the brick.
- **A consequence for VW-12's correction (defect 37):** folding the brick size into the element's material spec alone leaves W_bricks saying 3 : 1.5 : 1; correcting W_bricks too changes the foundation, which **un-accepts all 12 gaps** (a gap's acceptance covers the foundation; only a material spec is left out). The operator then accepts them again (one "accept all"). Defect 37's note says "accepted gaps stay accepted", which is true only for the spec.
- Nothing paid; no keys; no block; no helper; no older way; no label.

**Proposed (waiting for SK)**
- **PL1 — No brick figure as the example:** the plan part's "(a brick about 3 : 1.5 : 1; a drawing spec is warned without them, a material spec refused)" becomes "(a drawing spec is warned without them, a material spec refused)", and the server's warning drops "for example a brick about 3 : 1.5 : 1,". Shorter. Hurts: every film with bricks or blocks (the proportion is copied). Work: one replacement in v3 (with the split check), one in the server's message, a test. Breaks: nothing stored; VW-12's plan keeps its rule until corrected. Undo: the old text. Success: no brick figure in the plan part or the server's warnings. **Older way:** retired in this release.
- **For VW-12 now (no build):** when the brick correction is folded in, W_bricks is corrected to 190 × 90 × 90 mm too, and the operator accepts the 12 gaps again; I add this to defect 37's note on SK's yes.

| Decided | Parked | Open |
|---|---|---|
| PL1 agreed (SK, 31 Oct 2026: "remove the brick example") | – | the note for VW-12: replaced by F37b below |

**For the builder (PL1):** v3 plan part: "(a brick about 3 : 1.5 : 1; a drawing spec is warned without them, a material spec refused)" → "(a drawing spec is warned without them, a material spec refused)" (a replacement script hooked into `c1_split_v3.py --check`); `visual_contract.py` line ~738: "for example a brick about 3 : 1.5 : 1, " removed. Test: no "3 : 1.5 : 1" in v3 or the server.

#### F37b — A proper way to resubmit a revised spec (SK, 31 Oct 2026: "need a proper fix"; requirements, waiting for SK)
**Today:** after an operator's correction, the only way to put a revised spec in is the whole plan: download it (`vw visuals plan`, defect 37), edit the JSON by hand, check, propose again. The operator's assistant had already written the revised specs as files (`out/spec-brick.json`, `out/spec-mortar.json`) and found no command that takes them. Hand-editing a 276 KB plan is where mistakes come from.
**Proposed:**
1. `vw visuals spec --element E --file out/spec-E.json` (a material spec) and `vw visuals spec --shot S --file out/spec-S.json` (a drawing spec): one server step that checks the file against the spec form, puts it in place of that element's or shot's spec as a new plan version, and changes nothing else. Accepted gaps stay accepted (a spec is not part of a gap's acceptance, design/124 C2 fix 6); the correction stops waiting (the spec changed); the operator then approves the table as today (page or `vw visuals spec --quote`). The same server step serves the page later (one flow, two front ends).
2. The plan part's correction sentence names this command instead of the plan download (same length or shorter).
3. One rule, said where the foundation is described: a material's sizes and proportions live only in its spec, never in the foundation (so a correction is made once). Word count kept by trimming the same paragraph.
**Edge cases:** a file that fails the spec form is refused by name, nothing changed; a shot or element without a spec refused; a spec for an element not in the plan refused; a spec whose numbers are still unknown keeps its research warnings; two corrections in a row each replace the last.
**For VW-12:** the foundation's W_bricks still says 3 : 1.5 : 1 (the example, PL1). With F37b the brick spec (190 × 90 × 90 mm) is approved and pasted into every brick prompt by the server (design/111 F10); W_bricks is corrected once with the plan download when convenient (that one change makes the 12 gaps need accepting again).
**Older way:** the hand-edited whole plan for a spec correction: retired for specs in this release (`vw visuals plan` stays for other revisions).

#### Defect 40 (VW-12, 17:46): measuring fails; frames refused (read on the server and in the code)
1. **The measure call fails every time ("Provider did not complete with STOP").** `visuals_stage.measure` asks Gemini 3.8 Flash for at most 4,096 tokens and sets no thinking level, so the model's own thinking (which counts against that limit) uses it up and the answer is cut off; the transport refuses a cut-off answer. The checks of pictures and takes set `thinkingLevel: LOW` with their limits; four calls do not: **measure (4,096), the web figure research (512), the not-this list (1,024) and the start/end pair check (4,096)**, so each is likely to fail the same way the first time it is used. (Assumed from the code and the error, not confirmed with a live call: the cut-off reason is not in the message.)
2. **"Not footage frames":** both refused requests named a frame the operator **rejected** in the picture round (84c8… for the trowel; 6d02… with the approved 73a5… for the wall). The refusal is right, but its words ("approved footage frames only: name frames taken from the clips") do not say which frame or why, and the status lists rejected frames beside approved ones.
3. **The corrections and the measured sizes:** measured sizes go into the elements' `size` and the corrections into their material specs; both are left out of a gap's acceptance, so `vw visuals plan`, edit, `propose` keeps the 12 gaps accepted (only a change to the foundation, such as W_bricks, un-accepts them). So the operator's own route works now, and covers sizes, which F37b (specs only) would not. **Recommended: drop F37b; keep the plan route.**

**Proposed fix D40:** measure gets room to answer (`maxOutputTokens` 32,768, as the fix call has) ; the figure research, not-this and pair check get `thinkingLevel: LOW` and 8,192 like the other checks; a measure naming a frame that is not approved says which and why ("84c8… was rejected in the picture round: measure an approved frame of trowel: …", listing the approved ones). With PL1 in the same release. Tests: each call's settings; the refusal names the frame and the approved ones.

## Why VW-12 hits one defect after another (defects 35–38, 31 Oct 2026)

Read in the code, the live server's log and the defects table.

**Defect 38's cause:** for a reference sheet (and a component), the server adds its own lines to the prompt (design/119 rule 2, 28 Oct; design/117 P1) *before* it keeps "the writer's words" for the answer check (`visuals_stage.generate_image`: `sheet_block` and the component block are composed, then `writer_prompt = body['prompt']`). The check then compares the answer's prompt with a prompt the server has already lengthened, so **every sheet sent with its answer form is refused**, however exactly the prompt matches. Present since 28 Oct; no film reached a sheet since then until VW-12. Second fault in the same defect: `image --file` splits `parents` on commas only, so a parent with a crop (`id@left,top,width,height`) breaks into pieces that are not references ("Parents must be approved references"); the single command parses crops (design/119 rule 1), the file path never did.

**Why it keeps happening (the pattern):**
1. **The later visuals steps had not run on a real film since many changes.** Between 28 and 30 Oct the picture steps changed several times (design/117, 119, 120, 121, 124, 125); every film was closed on 30 Oct; VW-12 is the first to reach the sheets. Each new step it reaches is the first real use of that code since those changes, so faults that were always there come out one at a time.
2. **The tests are pieces, not the whole path.** They load the tool as a module and stub the server, so they could not see a helper missing when `vw` runs as a script (35), a request missing its id (35), or a prompt changed before its check (38): each piece passed alone. The database tests that run the server end to end (Docker) are not run on this PC.
3. **Two copies of each command in the tool.** A file of rows (`--file`) and a single command build the same request separately; the file path lacked the request id (35) and the crop parsing (38).
4. **Laptops behind on the tool** (36), now stopped by the server's minimum version (G2).

**Proposed:** fix 38 (keep the writer's words before the server's lines; the file path parses crops like the single command, through the same function); then, before the operator reaches them, a read-only sweep of every remaining visuals command (sheet, golden, state, component, keyframe, take, draw, record) for these same three kinds of fault, and one test per command that runs the request through the server's real request model and checks.

### The sweep of the remaining visuals commands (31 Oct 2026; read-only, a helper; findings 1, 2, 3 and 6 re-checked by me in the code)

| # | Command | What breaks | Smallest fix |
|---|---|---|---|
| W1 | any command whose answer has no message (prepare-take, review, asset, generator, select, accept) | **the tool's summary line says "refused (no reason given)" although it succeeded** (exit 0): introduced by defect 35's `why()` in `emit` (my fault) | `emit` uses `why()` only when the exit code is not 0 |
| W2 | `review` without `--notes` or `--quote` | always refused (the tool sends None, the server wants text) although the reason is optional (design/99 C3) | send `''` |
| W3 | `take --shots all`, `take --shot <drawn>` | a drawn shot counts as "prepared" and goes to the take path; refused with the bare message `'provider'` | take only video shots; the server refuses a drawn shot by name ("rendered with `vw visuals draw`") |
| W4 | `fix` on an isolated picture (a golden candidate), a sheet, a style, a component | refused ("Parents must be approved references"): only keyframes and states may be fixed from a candidate; a component's fix puts the style picture first while the fix prompt says Image 1 is the picture to fix | allow the picture being fixed as a candidate parent for any kind; no style prepend on a fix |
| W5 | `fix` of any picture whose answer has exact text (labels, titles) | refused ("The exact text … is not in the prompt"): the fix prompt lacks the answer's exact texts | check a fix's answer without its exact texts (the server adds them after the check) |
| W6 | a drawn shot sent to prepare-take, still or sequence | told to use `vw visuals still` ("takes a still, not a still") | name `vw visuals draw --shot S` for a drawn shot |
| W7 | `font --file`, `scene --file` | the file is looked for in the folder the tool started in, not the run folder (every other `--file` uses the run folder), so `--file work/scene-S-fixed.svg` is refused | read it from the run folder |
| W8 | `spec --element E` (a material spec) | prints "Drawing spec of None approved" | print the server's `next` line |
| W9 | `bind --file`, `still --file` | rows built differently from the single command: bind's `E=R1,R2` strings refused; still drops `move`, `reuse`, `considered`, `crop` | the rows go through the same parsing as the single command |
| W10 | `select` without `--gap`/`--job`, `fetch` without `--ref`/`--job` | print nothing and end "ok" | one refusal line naming the flags |
| W11 | `prepare-take --seconds 5.5`, `clip --at 1:20`, a bad `--crop`, `asset` without `--file` | Python crash instead of a refusal | a refusal naming the expected form |
| W12 | the line after approving a start whose end must be exact | names `vw visuals image --kind keyframe --role end …` without `--element`, which is required | add `--element <id>` |
| W13 (minor) | `image` without `--kind`; status with only a drawn job open | default name "None-E"; status line starts " open;" | `kind or 'keyframe'`; count drawn jobs |

Checked and found fine by the helper: every field the single commands send matches the server's models; every write now carries its request id; no other value is rewritten before its check; every command and flag the instructions name exists; refusals reach the operator with text. Not verified: nothing was run; the page's "Try a fix" button.

## Blocks found (point 13), across all stages
| # | Where | Decision or refusal | Recommendation | SK |
|---|---|---|---|---|
| 1 | 0.1 | The picture AI never changes on a film (SK, 28 Oct, design/120) | keep | – |

## Older ways found (point 15), across all stages
| # | Where | Older way | Newer way | Recommendation | SK |
|---|---|---|---|---|---|
| 1 | 0.1 | A film with no picture AI silently gets GPT Image (server default; visuals stage) | the picture AI chosen at the start (28 Oct) | retire by refusal (ST1) | agreed |
| 2 | 5.1 | The footage guessed and confirmed at the media step (design/77 L42, 22 Oct): prepare's guess line, `media record --camera/--support/--look/--footage-note`, the empty `footage_character` field | the footage measured at visuals (design/88, 25 Oct) | retire by refusal (ME1) | agreed |
| 3 | 7.2 | One chapter per scene (P7, design/125, 30 Oct) | a scene lists every chapter; per-step answers by shot (design/127) | retire (OP2) | agreed |

## Parking list
| # | From | Item | Where it goes |
|---|---|---|---|
| 1 | 2.4 | VW-12 has 15 chapters on 9 paragraphs; with P7 (one chapter per scene) the options step may cut about 15 scenes, some of one sentence (5–8 s), each with a slide, an answer and a helper | options 7.2 on VW-12: count the scenes and the shortest | **seen: 9 scenes**; looked at in 7.2 |
| 2 | 3.3 | The brick-strength table (20 / 35 / 75 kg/cm²), which a graphic will draw, was not checked at the script | visuals: check it is researched before the graphic is made |
| 3 | 6.2 | The plain mode found six fewer grade-B pieces on short clips | options: not checked scene by scene; scenes 3 and 4 gained footage over VW-11 |
| 4 | 7.6 | The second look leaves no mark on the server: whether it ran and what it fixed cannot be read afterwards | a later build, if SK wants it |
