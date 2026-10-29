# 124 — Visuals stage review, part 2: preparation, treatment and the detailed plan (started 29 Oct 2026)

A running list, like design/121 (which reviewed the steps from the Google picture search onwards). SK and the assistant review the three steps before the picture search one at a time; every change agreed is added here. **Nothing here is built yet.** Each change waits for SK's go-ahead before any code (requirements, then tests, then the change).

Written in plain English first; the last part of each change ("For the builder") says where it lands.

The order of the stage, for reference:

```
[First cut approved]
      ▼
1. Preparation      collects everything the assistant needs (gaps, timed narration, brief, team's notes,
      ▼             what the footage shows and how it looks, the instructions, the plan form)
2. Treatment        the approach gap by gap and the estimated cost → the operator approves
      ▼
3. Detailed plan    every scene, shot, thing, action and timing → checked, then accepted
      ▼
4. Picture search   (reviewed in design/121)
```

---

## Step 1 — Preparation (reviewed 29 Oct 2026)

### What it does
Right after the first cut is approved, the assistant runs the preparation. No picture is made and nothing is paid. It collects, once, what every later step reads: the gaps with their exact times; the narration under each gap, sentence by sentence and word by word, with the sentence before and after; the client's brief and its rules; the team's intended visuals per scene; what each clip of the footage shows (people, objects, places, the fixed features of each place); how the footage looks, measured from the clips (told to the operator in one line, corrected on the page if wrong); the stage's instructions and the blank form of the plan; the list of video AI tools and their lengths; the prompt-writing guide, per step. The assistant gets it as a set of files; the operator gets the visuals page link.

### Findings
- **Nothing paid, no keys, nothing to run in parallel** at this step.
- **Too many rules:** the assistant reads the whole stage's instructions here, one very long document for treatment, plan, pictures, videos and checks. Agreed as Change 2 below.

## Change 1 — One "what next" message after the preparation

### The problem today
When the preparation finishes, the assistant receives two "what next" messages that disagree:
- the stage's instructions: "settle the treatment with the operator first; nothing else before this: no plan, no picture";
- the server's reply: "write the detailed plan, then check it".

The server would refuse a plan without a treatment later, so nothing breaks, but the assistant may spend time writing a plan too early.

### What changes
The server's reply says the same as the instructions: settle the treatment with the operator first, then the plan.

### For the builder
- `visuals_stage.prepare`: its `next` line becomes "settle the treatment with the operator and record it (`vw visuals treatment`), then write the plan".
- Test: prepare's `next` names the treatment, not the plan.

---

## Change 2 — The instructions given one step at a time (agreed in principle, SK 29 Oct 2026)

### The problem today
At the preparation the assistant reads the whole stage's instructions at once: one very long document covering the treatment, the plan, the pictures, the videos and the checks. With that many rules in front of it, the assistant may forget or mix some of them, and a rule meant for one step can colour another.

### What changes
At each step the assistant gets only the part of the instructions for that step (the treatment part when it writes the treatment, the plan part when it writes the plan, and so on). The prompt-writing guide already works this way.

### Still to decide
How to split the document: settled **after the treatment and the plan steps are reviewed**, so the split follows what each step really needs. The rules that apply everywhere (stop and ask, never guess; plain language; the operator's words) stay in a short common part read once.

### For the builder (sketch, to be finalised)
- Procedure text (`procedures/v2.json`, visuals): the prompt split into a short common part and one part per step; `vw visuals prepare` writes them as separate files and names which one each step reads, like the library's `steps.json`.
- Check: no rule lost in the split (every sentence of today's text lands in exactly one part).

---

## Step 2 — Treatment (reviewed 29 Oct 2026; SK approved the findings below)

### What it does
The plan in big strokes, approved before any detail is written. The assistant reads the whole first cut and the team's notes, settles the direction with the operator in conversation, then writes one line per gap: the narration under it, the team's intended picture (followed or departed from, with the reason), the proposed picture in one sentence, how it is made (footage, AI still, AI graphic that builds, AI video, drawn diagram), its length, its pictures, how busy it is, and what each graphic shows; then the totals, the estimated cost and the frozen share against its 10 % limit. The operator sees it on the visuals page as a draft and approves it with their words. The detailed plan is refused when a gap's method departs from the treatment. No AI call and nothing paid at this step; nothing to run in parallel.

## Change 3 — A "Direction" box at the top of the treatment

### The problem today
The instructions ask for a directing brief (what the audience should understand or feel, the point of view, the approach and why), but it is written only later, inside the detailed plan. The operator approves the gap lines without seeing the overall direction written down.

### What changes
The treatment starts with a short Direction box, shown at the top of the page and approved with the gaps (it has its own accept or send back, Change 6). The detailed plan copies it into its foundation, unchanged unless the operator approves a new treatment.

**For films with no footage (design/122, when it is built):** the Direction box also holds the one look of the whole film (colours, contrast, light), approved once. Today a gap with no footage beside it gets its own look proposed; in a film with no footage that would be every gap, and the look could drift from gap to gap.

### For the builder
- `visuals_stage.treatment`: a `direction` field (a few lines) required; kept in the record; shown first on the page; `propose` checks `foundation.treatment` starts from it.
- Procedure text: the directing brief moves from "start the plan's foundation with it" to "write it first, in the treatment".

## Change 4 — The "strongest first picture" rule only when a gap opens the film

### The problem today
The rule "the first gap opens on the strongest picture of the film's subject, not a neutral establishing shot" fits a film that opens on a gap, and misfires when the film opens on real footage and the first gap sits in the middle.

### What changes
The rule applies only to a gap that starts the film.

### For the builder
- Procedure text (visuals steps, the treatment paragraph): "The gap that opens the film (if one does) opens on the strongest picture…".

## Change 5 — Five ways to make a picture, all named in one place

### The problem today
The instructions say "four routes make a picture"; the system has five. The fifth, the drawn diagram (for anything with exact sizes, counts or numbers), is described only deep in a later paragraph, so the treatment may plan a measured diagram as an AI graphic, and the detailed plan later refuses it. It also matters for design/121 change 2: during the picture search the assistant writes the drawn diagrams' instructions in advance, which only works when the treatment named them as drawn.

### What changes
The list of ways says five and names the drawn diagram with its one-line rule. In Change 2's split this list belongs to the short common part (the treatment and the plan both read it).

### For the builder
- Procedure text, section 1: the drawn route as the fifth, with "for exact sizes, counts, a sequence of courses, measured comparisons".

## Note D — The picture count for a video (no separate action, SK 29 Oct 2026)

The instructions still count "segments plus one" pictures for a video (a start and an end picture each); since design/112 a video takes a start picture only, and an end picture only where the final moment must be exact, so the count reads high. With design/122 no film has a spending limit, so the count can no longer block anything. The estimate is still shown on the treatment (design/122 keeps it), so it would read somewhat high; the wording is corrected when the treatment part is rewritten in Change 2's split, with no change of its own.

## Change 6 — Accept or send back each gap of the treatment, on the page

### The problem today
The page offers one Approve for the whole treatment. To change one gap while the others are fine, the operator has to say it in chat. (The detailed plan already works per gap.)

### What changes
- Every gap line of the treatment, and the Direction box, has its own **Accept** and **Send back** (with a short note of what to change).
- Accepted lines stay accepted. A line sent back goes to the assistant with the note; the assistant revises **only that line** and shows it again for its own accept.
- If the assistant's revision changes another line too (a shared method, the totals), that line goes back to "to accept" and is marked as changed.
- The treatment is recorded when the Direction and every gap are accepted; the detailed plan starts then, as today.
- The same in chat: the operator's words per gap (accept, or what to change).

### For the builder
- Server: the treatment draft keeps a state per gap (to accept, accepted, sent back with note) and per the direction; `treatment` records when all are accepted; a revised draft keeps the acceptance of lines whose text did not change (compared line by line).
- Page: per line Accept / Send back with a note box, like the plan step's Revise.
- Chat: `vw visuals treatment --accept G1,G2 --quote` and `--send-back G3 --notes "…"`.
- Tests: one gap sent back while the rest stay accepted; the record waits for every line; a revision that changes an accepted line returns it to "to accept".

SK agreed Changes 1–6 and Note D on 29 Oct 2026.

---

## Step 3 — The detailed plan (reviewed 29 Oct 2026)

### What it does
After the treatment, the assistant writes the full plan: the film's shared world (place, period, people, dress, materials, tools, light, colour, graphic style), every thing the film shows, every scene and shot (framing, camera, length, the words it sits under, where it cuts), every action second by second (where each person stands against a fixed part of the place, which way they face and look, what they hold, what changes from start to end, how long each action takes), the facts and sizes with their sources, and for graphics what they show, their labels and measurements. One shot has about 50 boxes, plus about 90 for its people and actions. The server's check refuses a plan for 86 reasons and warns for 40 kinds of doubt; the assistant fixes and resends until it passes, and every gap must use the methods the treatment approved. The operator accepts each gap on the page, or sends it back with Revise; accepted gaps stay accepted unless they changed. No AI call and nothing paid.

### Findings
- **The page already shows a readable shot list** (VW-7, BEAT_01): per shot its name, method, seconds, a sentence and what moves around it; the operator accepts per gap with their words. Kept (SK's choice, 29 Oct 2026); Change 7 makes what it shows match what will be made.
- **A clash in the instructions:** "each fact has one home; the purpose describes the picture" against "answer every warning in the shot's purpose". The purpose is the sentence the operator reads and is copied into the picture request, so warning notes leak into both. Change 7.
- **Technical warnings** ("cut_off_pause", "size_close_first") are to be shown to the operator as they are. Change 8.
- **Out of date:** 9 warnings still say "refused from the next release", long past (Phase A2).
- **Written twice:** many plan rules appear in the main guide and the step list in different words (where cuts fall, how stills move, how long graphics hold) (Phase B).
- **New rules mid-film force re-plans** (VW-7 re-planned more than once) (Phase C3, a new instruction version per film).
- **Parallel work (point 9):** the whole film's plan is written in one go, gap after gap; helpers could write gaps at the same time (proposed to SK; not agreed yet).

## Change 7 — The shot list shows what will be made (SK, 29 Oct 2026)

### What changes
1. **A box of its own for warning answers.** The assistant answers a warning there, not in the shot's purpose. The operator can see it on the page; it never goes into a picture request. The purpose stays a clean description of the picture.
2. **One line per shot written by the server from the plan's checked facts**, under the assistant's sentence: shot size, the narration words it sits under, who does what and how it ends, and any count. For example: "Wide · under 'homes going up' · the carter sets 6 bricks on the pan · ends at the stack".
3. Nothing else on the page changes: per-gap Accept and Revise stay as they are.

### For the builder
- Plan form (`visual_contract`): a `warning_answers` list per shot (kind and answer); the check counts a warning answered when its kind has an entry; the picture request's job form never reads it.
- `visuals_stage.page_view`: a `facts_line` per shot built from size, narration, the subjects' last beat (`done`, `result`) and the changed counts; the page shows it under the purpose.
- Procedure text: "answer every warning in the shot's purpose" becomes "answer every warning in its warning_answers entry".
- Tests: a warning answered in `warning_answers` is counted answered; the job form carries no warning answer; the facts line for a shot with a beat and a count.

## Change 8 — Warnings in plain words for the operator

### What changes
The operator sees a warning only when it changes what they will see, in one plain sentence (for example, "this cut falls in the middle of the sentence 'homes going up'"); purely technical ones stay between the assistant and the server.

### For the builder
- A plain sentence per warning kind that the operator sees (a short table beside the 40 kinds), and a list of the kinds kept from the operator; the page shows the plain sentence with the gap.

## Change 9 — The plan's gaps written in parallel (SK, 29 Oct 2026)

### The problem today
The assistant writes the whole film's plan in one go, gap after gap, in one very large form (about 140 boxes a shot with its people and actions). For a film of 15–20 gaps that is a long piece of work done one gap at a time.

### What changes
1. **The shared parts first, by the main assistant:** the film's world, the list of things, the graphic style, the sequence overview (what each gap adds to the film, from the approved treatment), and for each gap what comes before and after it (the neighbouring gaps' pictures and the people's last state).
2. **Helpers write gaps at the same time.** Several helper assistants, each given the shared parts and a few gaps, write those gaps' scenes, shots and actions. A helper that needs a thing not on the list adds it to a short "new things" list instead of inventing an identity.
3. **The main assistant joins them** into one plan (the new things merged once, duplicates removed) and sends it to the server's check, as today. The check sees the whole film, so rules across gaps (no picture shown twice, a person's state carried from one shot to the next, the frozen share) are still checked; the main assistant fixes what it names, or sends a gap back to its helper.
4. Same rules, same check, same operator approval per gap; nothing extra paid; faster for long films. A revision of one gap goes to one helper.

### For the builder
- Chat tool: `vw visuals plan-join --base out/plan-base.json --gaps out/plan-gaps/` writes `out/visual-plan.json` (the gaps in film order, the new things merged and de-duplicated by name) for `vw visuals check`.
- Procedure text (the plan step, in Change 2's split): the three steps above; helpers through the assistant's own agents, a few gaps each; each helper reads the shared parts and the package files, never another helper's gaps.
- Check: a joined plan with a thing added by two helpers keeps one; a join with a gap missing is refused by name.
- Not covered until a real film: how many helpers suit the operator's machine and account (start with three or four).

---

## The instruction tidy-up, in phases (agreed in outline, SK 29 Oct 2026; one phase at a time, on SK's word)

The assistant's instructions for the visuals stage (about 10,800 words), the prompt-writing guide, the messages the server and the chat tool send back, and the lines the server adds to picture requests all instruct the AI. They are fixed in phases, one at a time, each with its own go-ahead, so each has the context and room it needs. Nothing is changed until SK names the phase.

### Part A — Common problems, across the whole stage

| Phase | What | Why it is a problem | SK's part |
|---|---|---|---|
| **A0. The rule list** (do first; changes nothing) | Every rule as one numbered line: its exact old sentence, its place, whether the server already checks it, its phase | The safety net for every later phase: the trace table and the "nothing lost" check are built from it | none |
| **A1. Change-history labels** | Remove the 138 labels ("design/111 F14", "L42"…) from the text the AI reads; they stay in the design notes | Noise for the AI; mean nothing to it | none (mechanical) |
| **A2. Out-of-date rules** | Remove or correct rules for features that changed: the spending limit (design/122), the start-and-end picture count, "warned now, refused from the next release", the old cap of four pictures | The AI follows rules that are no longer true | confirm the list |
| **A3. Copies that disagree** | Every topic written in both lists where the two copies say different things (found so far: four or five ways to make a picture; the start-and-end picture count; the order of picture sources) | The AI has to guess which is right | decide each one |
| **A4. The other voices** | Make the server's and the chat tool's "what next" messages, the prompt-writing guide and the server's added lines say the same as the instructions; remove the rule about "which one wins when they disagree" once nothing disagrees | They contradict the instructions (Change 1 was one) | confirm the list |

### Progress

- **A0 done (29 Oct 2026):** `design/124-a0-rule-list.csv` (2,353 rules) and its summary `design/124-a0-rule-list.md`.
- **A1 done (29 Oct 2026), not deployed:** the instructions' change-history labels removed into a **new instruction version 3** (`server/procedures/v3.json`); version 2 is untouched, so films in progress keep their wording. Only the visuals stage differs between the two. 50 labelled brackets and 3 history notes ("SK, 28 Oct …", "the cap of four removed by SK …") removed; 11,302 words became 11,047; a script proved that no other word changed and no label is left; the ratio "3 : 1.5 : 1" and every number stay as they were. Server unit tests 705 passed. New films start on version 3 only when the default is switched (Phase C3). From now on, every instruction change of this tidy-up, and every procedure change of design/121 and design/124's Changes 1–9 when they are built, goes into version 3.
- Labels still inside the server's own refusal texts, added lines and messages (about 360 rows of the rule list): handled with A4 (the other voices), since they live in the code.
- **A2 proposed (29 Oct 2026), waiting for SK:** the out-of-date rules, checked against the code, in six groups (rule-list ids in brackets):

| Group | What is out of date | Proposed |
|---|---|---|
| **1. A start and an end picture for every video** | Since the start-only change a video takes a start picture only, and an end only where the final moment must be exact; still written as pairs in the instructions (R0073, R0325, R0329, R0383), the prompt guide (R1403), a server line (R2151), a message (R2320) and a refusal that asks for notes about "the two frames" (R1061) | Correct the wording everywhere to "start picture; an end picture only where it must be exact" |
| **2. Four ways to make a picture; "arrows that travel are not available"** | There are five ways (the drawn diagram), and a drawn diagram can move things along a path (R0031, R0043) | Correct (the same as Change 5) |
| **3. "Refused from the next release"** | 18 warnings promise to become refusals and never did (R0452, R0789, R0790, R0794, R0797, R0798, R0804, R0850, R0864, R0880, R0910, R1018, R1022, R1023, R1056, R1066, R1067, R1098); one of them can never fire, because the same thing is already refused (R1015) | Remove the promise and keep them as warnings; remove R1015's warning. Whether any should become a refusal is decided per rule in Phase B, not all at once |
| **4. The picture AI is chosen per film** | The prompt guide says "GPT Image for every picture, never Nano Banana" (R1150, R1554) and two messages say "paid OpenAI image" (R2315, R2317), though a film may use Nano Banana | Correct to "the film's picture AI (GPT Image or Nano Banana)" |
| **5. Small leftovers** | A pointer to the wrong section (R0048); an old alias "answers for one release" kept for weeks (R2160); a warn-only path for sessions begun before 23 Oct (R0884) | Fix the pointer; remove the alias; keep the old-session path until no film from before 23 Oct is open |
| **6. Facts in the prompt guide about video models** | Veo (not used), Kling 4.0 watch notes, the Higgsfield fixed lines listed differently from today's, a file named INDEX that VideoWizard replaced, a section that is not in the bundle (R1193, R1252, R1800, R1866, R1895, R1906, R1910) | Handle in A4 with the prompt guide (it is a separate snapshot; a corrected guide is a new snapshot, so films in progress keep theirs) |

Not in A2: the ₹ spending limit (17 rows): still live; it goes with design/122. R0626 (the "cap of four" note): already removed in A1.

- **A2 done for groups 1–5 (SK, 29 Oct 2026), not deployed:**
  - Instruction version 3: five routes, with the drawn diagram named beside the other four and its moving parts; a start image per video, an end image only where the final state must be exact (three places); "warned and refused from the next" became "warned"; the section pointer corrected.
  - Server: the "refused from the next release" promise removed from 15 warnings and reworded in 3 more (they stay warnings); the warning that could never fire removed (the same thing is refused earlier); the continuity refusal no longer speaks of "the two frames".
  - Chat tool: "paid OpenAI image" became the film's picture AI (2 messages); "compose the start and end images" became "the start image (and the end image only where the shot must end exactly)" (2 messages).
  - Tests: 7 assertions that expected the promise now expect it gone. Server unit 705 passed; plugin 320 passed, 3 known Windows-only failures.
  - **Held back (with Phase C3):** the packet's start instruction (R2151, "a cut starts a new pair with its own two images"), its old alias (R2160) and the video instruction's "the two images". These texts are part of each shot's fingerprint: changing them now would mark prepared takes stale in every film in progress. They change with the switch to version 3 for new films.
  - Group 4's prompt-guide rows (R1150, R1554) and group 1's (R1403) go with A4 (a new guide snapshot).

Where the corrections land: groups 1, 2 and 5 in instruction version 3 (the wording) and in the server code (the lines and messages); group 3 in the server code; group 4 in the messages now and in the prompt guide with A4.

### Part B — The four phases reviewed so far (SK, 29 Oct 2026)

Preparation, treatment, the detailed plan (reviewed next) and the picture search. For each of the four:

1. **Write each topic once** (merge the main guide and the step list for that phase's topics: the principle in the guide, the order of work in the steps).
2. **Shorten** the rules the server already checks to one line each, keeping every number and condition.
3. **Move command details out** where the tool already states them.
4. **Check the phase's rules against the film types** (Work item 7, for these four phases).
5. **That phase's own fixes** (preparation: Changes 1–2; treatment: Changes 3–6; the detailed plan: from its review; the picture search: done in design/121, its wording only).
6. **The safety checks**: trace table (old sentence → new sentence per rule), a second helper comparing them, a script checking every number and fixed phrase survived.

The later phases (reference sheet and golden picture, shot pictures, videos, review and record) are **not** tidied now: their problems come up when SK reviews each of them with the revised review prompt (C4), and are fixed then.

### Part C — Right after Part B

| Phase | What |
|---|---|
| **C1. Split by step** (Change 2) | A short common part plus one part per step. The four tidy phases go in tidy; the later phases go in as they are, to be tidied when reviewed |
| **C2. Trial run** | The assistant writes a treatment and a plan for a past film (VW-7) with the old and the new instructions; the server's checks run on both; compare. No pictures, nothing paid |
| **C3. A new version** | The tidy instructions go in as a new instruction version: films in progress keep the old one; going back is easy |
| **C4. The revised review prompt** | SK's review prompt (the one that opened this review: what happens, why, connections, what went wrong, better, too many rules, prompts that create prompts, API keys, parallel work, the flowchart), revised so that for each later phase it also brings up, unasked: change-history labels; topics written twice and copies that disagree; out-of-date rules; the other voices (server and chat-tool messages, the prompt-writing guide, the server's added lines) that disagree with the instructions; rules that misfire for one of the agreed film types; rules the server already checks that can be one line; and the phase's place in the split. SK reuses it for each later phase |

---

## Work item 7 — Check every rule against the kinds of film we make (agreed, SK 29 Oct 2026; not started)

### Why
Change 4 was found by chance, while reading the treatment section: a rule written for one situation that fires in all of them. The visuals stage has many more rules: about 10,800 words of written instructions (several hundred rules), about 86 automatic checks that refuse a plan and 38 that warn, and the prompt-writing guide. Others are likely to misfire the same way (rules that assume real footage, rules written for a documentary, rules for long gaps that misfire on a 3-second gap).

### How
1. **Agree the film types with SK first**, so every rule is tested against the same situations. Proposed list (SK to confirm or change):
   - a film that opens on real footage / a film that opens on a gap;
   - a human story (people at work) / a technical record (diagrams, sizes, numbers);
   - a film with no footage at all (design/122);
   - a very short gap (about 3 s) / a long gap (30 s or more);
   - a scene with no people / a person speaking to the camera;
   - a busy scene (a site with many workers) / a quiet one (an empty room, a product).
2. **List every rule** that decides what appears on screen and how, from the three places.
3. **Test each rule against each film type**: mark where it misfires, where it contradicts another rule, and where it is never needed.
4. **One table for SK**: each problem rule, the film type where it goes wrong, and a simple fix in plain words. Fixes then join this document as changes, after SK's yes.

### Parallel work (point 9)
Three helpers at the same time, one each for: the written instructions, the automatic plan checks, the prompt-writing guide. They read files only, change nothing and cost nothing beyond time; their findings come back here as one table.

### When
For the four phases reviewed so far, in Part B (item 4), before Change 2's split; for the later phases, as part of their review with the revised review prompt (C4).

---
