# VW-23: the treatment, dissected

15 Nov 2026. Read-only study by Claude. Nothing was changed on the run, the server or the database. Uncommitted working note.

This note follows one treatment from what went in to what came out. The earlier note `how-the-treatment-is-made-VW-23.md` lists the rules in full; this one shows the real inputs and the real output.

## 0. What was read, and how

| What | How Claude got it |
|---|---|
| The package the assistant was given (`package.json`, 519,888 bytes: the same size the server logged at prepare) | Copied from the server's storage with a small read-only script run on the VM |
| The run's visuals session (`session.json`): the recorded treatment with every field, the first cut's footage list | Same |
| Both drafts' answers and both cards | `vw2_receipts` in the database |
| The rules and the checks | The deployed commit `4d7f72d` (server 0.98.2) |
| All 94 clip entries of the package | Read in full as a list of what each clip shows |

Not read: the assistant's chat on Uma's laptop. So "why" is taken from the reasons the assistant wrote into the treatment itself, not from its thinking.

## 1. The film in numbers

```
The whole film: 299.4 s
|-- footage already placed by the first cut     84.7 s   28 %
|-- 18 gaps for the visuals stage              214.7 s   72 %
      |-- stills (28 pictures)                 101.2 s   34 % of the film
      |-- drawn graphics                        76.1 s   25 %
      |-- footage the treatment added           23.8 s    8 %
      |-- AI video (2 shots)                    13.5 s    5 %
```

- 94 clips were analysed. The first cut uses 23 of them (and one library clip). 71 clips are not in the film.
- The first 132 seconds of the film have 11.5 s of placed footage. The building work (seconds 143 to 199) is almost all footage. The start and the end are almost all gaps.

**First finding.** Before any treatment rule applied, 72 % of the film arrived as a gap. That was decided at the options and master stages, not here.

## 2. The flow

```
 OPTIONS + MASTER stages            PREPARE (server)                 ASSISTANT                    SERVER                OPERATOR
 ------------------------           ----------------                 ---------                    ------                --------
 leave 18 blanks, each with   -->   one package:              -->    reads the files,      -->    checks the form, -->  card:
 an "intent" line                   9 inputs (section 3)             writes the direction         adds seconds and      Accept /
                                                                     and 18 lines                 cost, warns           Change this
                                                                     (picks every route)
```

The server never picks a picture. Every "still", "drawn", "footage" and "video" below was chosen by the assistant.

## 3. The inputs, one by one

### 3.1 The gaps (18)

- **From:** the first cut. Each blank carries the "intent" the options stage wrote for it, then the narration under it (`stage2/stage.py`: `"{intent} | narration: {words}"`).
- **What the assistant gets per gap:** start and end frame, the intent line, the sentences and every word with its time, the sentence before and after.
- **How it steered:** strongly. The intent often names the form already.

| Gap | Seconds | The intent it arrived with (shortened) |
|---|---|---|
| BEAT_01-B1 | 30.08 | Urban construction and housing growth; conventional concrete roofs being cast; then the turn to a filler slab |
| BEAT_02-B1 | 13.60 | "Animated cross-section of a conventional reinforced concrete slab: compression zone above, tension zone below" |
| BEAT_03-B1 | 7.42 | "Animation: the non-structural concrete … taken out of the cross-section and replaced by lightweight filler units" |
| BEAT_03-B2 | 2.34 | Hollow clay blocks and lightweight bricks as filler units |
| BEAT_03-B3 | 6.54 | The result: a finished, strong and durable filler slab roof |
| BEAT_04-B1 | 25.50 | The benefits: less concrete, cement, steel "(graphic)"; a lighter roof on a multi-storeyed building; an exposed tile ceiling |
| BEAT_04-B2 | 14.62 | Cooler rooms "(thermal comparison)"; then local masons and local materials at work |
| BEAT_05-B1 | 8.30 | The materials laid out: cement bags, steel bars and coarse sand |
| BEAT_05-B2 | 4.78 | Binding wire, clean water, then Mangalore tiles and hollow clay blocks |
| BEAT_05-B3 | 5.60 | The filler options side by side |
| BEAT_06-B1 | 7.32 | Supports under the shuttering; a thin layer of oil brushed on |
| BEAT_10-B1 | 5.32 | Less concrete, the same strength: the slab section showing concrete only where it carries load |
| BEAT_11-B1 | 11.68 | The fresh slab left to set, nobody on it; water curing, the slab kept wet |
| BEAT_12-B1 | 9.12 | The shuttering comes away and reveals the ceiling pattern |
| BEAT_13-B1 | 28.30 | Less cement and steel, lower carbon "(graphic)"; cooler rooms; eco-friendly homes |
| BEAT_14-B1 | 4.08 | Place the Center at Kanyakumari: "its name board or entrance, or a simple map" |
| BEAT_14-B2 | 7.18 | More of the Center's buildings, then inside one |
| BEAT_15-B1 | 22.88 | Finished filler slab buildings, people living beneath them; close on the client's mark |

### 3.2 The brief

- **From:** the brief stage (13 Nov).
- **What it says:** purpose (understand what a filler slab is, why it saves cement and steel, how it is built); audience (home builders, masons, site engineers, architects, students); tone ("Calm, clear and instructive, like a knowledgeable engineer explaining to an interested visitor"); ending (awareness, no sales call); 14 process stages; destinations website and YouTube; not watched muted.
- **Rules in force:** none from the client. 15 safety words are waived (helmet, glove, footwear and so on).
- **How it steered:** the direction's "a calm engineer walking a visitor through the idea" is the brief's tone almost word for word.
- **What it does not say:** nothing about moving pictures against stills, nothing about how much may be generated.

### 3.3 The team's intended visuals

- **From:** the script's visual notes, kept at intake. 11 scenes, 3 to 5 lines each.
- **Examples:** "Aerial shots of urban construction sites", "Animated cross-section of a conventional RCC slab", "Thermal imaging demonstrating cooler indoor temperatures", "Rural masons undergoing training", "Families living beneath filler slab roofs", "Sunset over sustainable housing", "Logo of Vivekananda Kendra – NARDEP".
- **How it steered:** the rule is "a stated requirement with its source … say in the treatment why you depart from one". Every treatment line has a note saying followed or departed (section 5).

### 3.4 The script's claims

- 4 claims, all "checked: false": the tension zone does little work; less cement, steel and aggregates; air pockets keep rooms cooler; water curing for at least two weeks.
- **How it steered:** the direction says "Claims with no figure in the narration are shown as plain comparisons without numbers". Every graphic line says "no figures" or "without temperatures".

### 3.5 The clip evidence ("world")

- **From:** each kept clip's analysis log. 94 entries, 332,281 characters: two thirds of the package.
- **What each entry holds:** the things in the clip (name, a sentence, first and last second seen, what is uncertain), a list of landmarks, a list of doubts.
- **What it does not hold:** what happens in the clip, which stretch is good, how long it is, whether it is already in the film.
- **What the 94 clips show:** almost all are the demonstration bed at the Center: the steel grid, cover blocks, tiles, coconut shells, clay dishes, hands placing them, concrete poured and levelled. Also: mixing by hand (C0016 to C0018, C0081, C0082), aggregate heaps and a concrete mixer (C0021, C0022, C0023), cutting and measuring steel bars (C0009 to C0015, C0019, C0024 to C0027), tying bars (C0028 to C0031), the finished demo slab (C0097, C0099 to C0102), a mason with a Mangalore tile (C0058 to C0060), six clips of a man speaking to camera.
- **How it steered:** the treatment named five clips (C0079, C0016, C0060, C0075, C0135). C0135 is the client's library clip, not one of the 94.

### 3.6 The footage line

- "Your footage: cinema camera, mixed support (58 tripod, 23 handheld, 12 gimbal), natural look (measured from the clips)". Per clip: Sony FX30, standard contrast.
- **How it steered:** the direction sets the made pictures "in the overcast daylight and red-earth, terracotta and grey-concrete palette of the footage".

### 3.7 The video generator list

- One entry: "Gemini Omni · Direct Google", model `gemini-omni-1.1-flash`, 3 to 10 seconds.
- **Mismatch:** the prompt says "A take is 3 to 15 seconds". The package says at most 10. Not read here which one the take uses.

### 3.8 The rules

- The common prompt (10,565 characters), five parts (55,611), eight step lines. The treatment part is 5,342 characters.
- Also sent, not for this step: the plan schema (28,233 characters).

### 3.9 What the assistant was not given

- The list of which clip plays where in the first cut. The server has it (25 entries) and keeps it in the session; the package does not carry it. The assistant can only know it from files the master stage left in the run folder.
- The film's category and motion style (they are on the run, not in the package).
- Prices. It sees them only in the server's answer after sending.

## 4. Who decided what

| Decision | Who | From what |
|---|---|---|
| Which parts of the film are gaps | Options and master stages | Before this step |
| What each gap should show (the intent) | Options stage | Before this step |
| The direction | Assistant | Brief, intents, the treatment rules |
| The picture of each gap | Assistant | The intent, the team's note, the rules |
| Still, drawn, footage or AI video | Assistant | The rules (section 6) |
| Seconds per shot inside a gap | Assistant | The gap's length; then the server's warnings |
| Is the form valid | Server | Fixed checks |
| Totals, cost, warnings | Server | Arithmetic |
| Accept or change | Operator | The card |

## 5. Gap by gap: what went in, what came out, and the reason written

"Reason" is the assistant's own note in the treatment (its `intended_visuals` field). The operator's card did not show this field.

| Gap | Came out as | The assistant's written reason |
|---|---|---|
| BEAT_01-B1 30.08 s | still 4.0, still 3.5, still 2.7, drawn 8.0, footage 4.0 (C0079), still 4.0, still 3.9 | "Departed from: aerial shots of urban sites and rising skylines, **which AI video cannot yet make** and which no footage shows." |
| BEAT_02-B1 13.6 s | drawn | "Followed: animated cross-section of a conventional RCC slab" |
| BEAT_03-B1 7.42 s | drawn | "Followed: animation showing concrete being replaced with filler materials." |
| BEAT_03-B2 2.34 s | still | "the narration names materials the footage does not show." |
| BEAT_03-B3 6.54 s | still | "Followed: completed filler slab roof." |
| BEAT_04-B1 25.5 s | drawn 8.0, footage 3.9 (C0016), drawn 7.1, still 3.3, still 3.2 | "The split screen becomes a side-by-side drawing." |
| BEAT_04-B2 14.62 s | drawn 5.1, still 3.2, still 3.2, footage 3.1 (C0060) | "Departed from: thermal imaging, which cannot be shown truthfully without a measurement; a drawing shows the idea." |
| BEAT_05-B1 8.3 s | still | "Followed: close shots of cement, sand and steel bars." |
| BEAT_05-B2 4.78 s | still | "Followed: stacks of Mangalore tiles and hollow clay blocks." |
| BEAT_05-B3 5.6 s | footage (C0075) | "the footage has the filler options laid side by side." |
| BEAT_06-B1 7.32 s | still 1.7, **AI video 5.6** (a hand brushing oil) | "Followed: installation of shuttering and application of oil" |
| BEAT_10-B1 5.32 s | drawn | "the claim is carried by the recurring drawing." |
| BEAT_11-B1 11.68 s | still 3.8, **AI video 7.9** (a worker pouring water) | "Followed: water ponding on the slab and workers curing the roof." |
| BEAT_12-B1 9.12 s | still 3.1, still 3.0, still 3.0 | "Followed: revealing the exposed tile ceiling." |
| BEAT_13-B1 28.3 s | still 3.2, still 3.1, drawn 7.0, still 3.0, drawn 3.6, still 2.8, still 2.8, still 2.8 | "Families are shown at a distance in a still, **since people speaking or moving in a group are not available as AI video.**" |
| BEAT_14-B1 4.08 s | drawn (a map) | "the Center is placed for the viewer; its exterior follows as footage." |
| BEAT_14-B2 7.18 s | footage (C0135, client's library) | "from the client's own footage." |
| BEAT_15-B1 22.88 s | still 4.0, still 4.0, still 4.0, still 4.0, drawn 6.9 (closing card) | "Departed from: sunset over sustainable housing; the film keeps the footage's daylight." |

The 28 stills by length: one of 8.3 s, one of 6.5 s, one of 4.8 s, six of exactly 4.0 s, nineteen under 4 s.

## 6. The rules that did the deciding

Short form. Full quotes are in the earlier note.

| # | Rule (served text) | Where it shows in VW-23 |
|---|---|---|
| R1 | AI video is "one action per shot, of three kinds: a walker; one action, close; a transfer, close". Anything else "is not yet available as AI video: make it footage, a still or a drawn shot" | The assistant cites it twice in its reasons (BEAT_01, BEAT_13). The only two video shots are "one action, close". |
| R2 | "at most four people, nobody crossing, hand work close and in the right hand" | Masons casting a roof, a family on a veranda: stills. |
| R3 | "Use a scene (footage, or AI video or still …)": no order between video and still | Every scene that R1 allowed as video but did not need it stayed a still. |
| R4 | "There is no quota of AI video, footage or graphics" | 5 % AI video raised no flag. |
| R5 | Draw "when the meaning is invisible to a camera or must be read precisely" | Six gaps drawn; all match an intent that already said "animated", "graphic" or "cross-section". |
| R6 | "one recurring diagram that develops across the film" | The slab cross-section returns in six gaps. The direction says so. |
| R7 | The team's visuals are "a stated requirement … say why you depart" | A followed/departed note on every line. |
| R8 | A realistic representative scene is allowed if "it does not pretend to be the client's own site" | The direction: "they never pretend to be the client's own buildings." |
| R9 | "muted and true to life by default" | The direction repeats these words. |
| R10 | "Footage first." and a clip "named at one gap only" | Five clips named, each once. See 8.4. |
| R11 | A still over 4 s is warned (only inside a gap with several shots) | Section 7. |
| R12 | Over 8 s of graphics in a row is warned | Section 7. |

## 7. The two drafts: what the server's warnings changed

The operator saw only the second draft.

| | First draft, 15:13:05 UTC | Second draft, 15:13:41 UTC |
|---|---|---|
| Pictures to make | 18 | 30 |
| Estimate | ₹196.6 | ₹244.6 |
| Stills | 103.96 s | 101.24 s |
| Drawn | 84.4 s | 76.1 s |
| Footage | 12.78 s | 23.8 s |
| AI video | 13.52 s | 13.52 s |
| Warnings | 13 | 0 |

What each warning turned into:

| Gap | Warning | The change |
|---|---|---|
| BEAT_01-B1 | stills of 10.2 s and 10.1 s; 9.8 s of graphics | 3 shots became 7: five stills, the drawing cut to 8.0 s, one footage shot added |
| BEAT_04-B1 | 19.0 s of graphics in a row; a still of 6.5 s | footage (C0016) put between the two drawings; the still split in two |
| BEAT_04-B2 | a still of 9.5 s | two stills of 3.2 s and footage (C0060) |
| BEAT_12-B1 | stills of 4.5 s and 4.6 s | three stills of about 3 s |
| BEAT_13-B1 | 13.6 s of graphics in a row; stills of 6.3 s and 8.4 s | 4 shots became 8: six stills, two drawings apart |
| BEAT_15-B1 | two stills of 8.2 s | four stills of exactly 4.0 s |

- The warnings added 11 s of footage in three gaps. That is the good effect.
- They added 12 stills. No still became an AI video. The AI video seconds did not move.
- All of this took 36 seconds and was never shown to the operator.

## 8. Findings

### 8.1 Most of the result was fixed before the treatment

- 72 % of the film came in as gaps, with an intent line each.
- Six intents already said "animated", "graphic", "cross-section" or "map". All six became drawn.
- The treatment's freedom was mainly in the other twelve gaps.

### 8.2 The AI video rule is the stated reason for the stills

- The assistant wrote it down: "which AI video cannot yet make"; "people speaking or moving in a group are not available as AI video".
- Under R1 and R2, VW-23 had few shots that qualify. It found two.
- Scenes that are one action, close, and still became stills: stacking tiles (BEAT_04-B2), a helper carrying shells (BEAT_04-B2). Nothing in the rules asked for them to move (R3).

### 8.3 The long stills come from a hole in the check

- The 4 s warning reads only gaps that list several shots.
- A gap made of one still is not looked at: BEAT_05-B1 (8.3 s), BEAT_03-B3 (6.54 s), BEAT_05-B2 (4.78 s).
- Those are the stills you later asked to change. At the plan card (16:15 UTC, 14 Nov) BEAT_03-B3 got "Make it as a AI video" and BEAT_05-B1 "Change this as AI video".

### 8.4 "Footage first" had little to work with

- 71 analysed clips are not in the film. The treatment used four of them.
- The clip list names things, not actions or good stretches. The assistant cannot tell from it whether a clip is usable for a gap.
- Stills were planned for things the clip list also names: a concrete mixer and aggregate heaps (C0022, C0021), steel bars being cut and measured (C0009 to C0015), concrete being poured (C0084), the finished demo slab (C0097 to C0102), water poured from a mug (C0081). Whether those shots would fit is not checked here; the point is that the assistant had no way to check either.
- The package does not say which clips the first cut already uses.

### 8.5 The warning's own words choose stills

- "fill the stretch with several different stills or a moving shot". Stills come first, and they are the quick fix.

### 8.6 Six stills are exactly 4.0 s

- The limit became the target. BEAT_15-B1 ends the film on four stills of 4.0 s each.

### 8.7 The card hides the reason and the mix

- Not on the card: the assistant's followed/departed note, the words under the gap, the seconds of each shot, the film's totals by type.
- So "which AI video cannot yet make" was never in front of the operator.

### 8.8 Two inputs disagree

- The prompt: a take is 3 to 15 seconds. The package's generator list: 3 to 10 seconds, model `gemini-omni-1.1-flash`.

## 9. Could not see

- The assistant's thinking and which files it opened (1 min 45 s between the package and the first draft).
- The first draft's full text (only its totals, warnings and the "what changed" lines on the card).
- Whether any unused clip is really usable for a gap. That needs the clips' own logs, which belong to the analysis stage.
- Why the options and master stages left 72 % of the film blank. That is their study, not this one.
- The exact prices in the server's settings.
