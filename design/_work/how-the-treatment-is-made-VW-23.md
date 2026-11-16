# How the treatment is made, step by step (with VW-23 as the example)

15 Nov 2026. Read-only study by Claude. Nothing was changed. Uncommitted working note.

Read from: the deployed commit `4d7f72d` (server 0.98.2): `server/procedures/v3.json` (the text served), `server/app/visuals_stage.py`, `chat_flow.py`, `film.py`, `visual_contract.py`, `plugin/scripts/vw.py`, `plugin/commands/vw.md`; and for VW-23 the log, the request lines and the server's stored answers (`vw2_receipts`), which hold both treatment cards.

The plan is not in this note. It is the next one.

## 1. In short

The treatment is written by the assistant alone, in one pass, from files the server hands it. The server does not choose any picture. It gives the rules as text, checks the form of what comes back, adds up seconds and cost, and shows the operator each line on a card. The operator's part is Accept or Change this, line by line.

So what decides "still or AI video" is: (a) the words of the rules the assistant reads, and (b) the assistant's own judgement. No program weighs one route against another.

## 2. Who does what

| | The server | The assistant (in the operator's chat) | The operator |
|---|---|---|---|
| Start | Says the stage is visuals | Runs `vw visuals prepare` | Asks "what is next" |
| Prepare | Builds one package: gaps, timing, brief, script claims, team's intended visuals, clip evidence, the rules | Reads the files; says the footage line | Hears the footage line |
| Write | Nothing | Writes the direction and one line per gap into `out/visual-treatment.json` | Nothing |
| Send | Checks the form; adds totals, cost, warnings; keeps it as a draft | Sends; may rewrite and send again | Sees nothing yet |
| Decide | Builds the card | Shows the card as it is | Accept or Change this, per line |
| Record | Records when every line is accepted | Starts the plan | Done |

## 3. The steps, with the exact words

### Step 0. "What is next"

`vw next` answers with the stage and this line: "The operator's decisions of this stage are taken in the chat, one at a time: `vw visuals next`." In VW-23 the assistant went from the master's record straight to prepare; no `next` call is in the request lines.

### Step 1. `vw visuals prepare` (server, about 33 s in VW-23)

The server (`visuals_stage.prepare`) collects:

| Into the package | Where it comes from |
|---|---|
| The gaps: for each, start and end frame, the passage, the reason it is a gap | the approved first cut, else the master |
| Each gap's timing: the sentences and words under it with seconds, the sentence before and after | the options package |
| The brief and the client's rules in force | the brief stage |
| The team's intended visuals (the script's visual notes per scene) | the intake |
| The script's claims (figures, checked or not) | the script stage |
| Clip evidence: per clip, the things in it, what is uncertain, landmarks | each kept clip's analysis log |
| The footage line (camera, support, look) | measured from the clips |
| The rules: the common prompt and five parts | `v3.json` |
| The plan schema, the list of video generators | the code |

The tool then splits the package into files under `work/visuals/`: `prompt.md`, `part-preparation.md`, `part-treatment.md`, `part-plan.md`, `part-picture-search.md`, `part-later.md`, `gaps.json`, `intended-visuals.json`, `claims.json`, `brief.json`, `world-1.json` and on (25 clips each), `schema.json`, `generators.json`, `rest.json`.

Not in the package: the list of which clip plays where in the first cut. The assistant has that only from the files the master stage left in the run folder.

### Step 2. What the assistant is told to read

`part-preparation.md`: "Read prompt.md, gaps.json and intended-visuals.json first, and claims.json … the world files when you plan the scenes. Tell the operator (never ask) its one line on the footage's look … Then settle and record the treatment (section 2, part-treatment.md), before any plan or picture."

### Step 3. The rules for choosing each picture

These are all the rules the assistant has when it decides what each gap shows and how it is made. Quoted in the order they are served.

**From the common prompt, section B (the five routes):**

1. Footage: "a moving stretch of any clip (`vw visuals clip`, free), or a frame of a clip shown nowhere else in the film … **Footage first.**"
2. AI still: "a picture generated with the run's image model … a photograph-like scene or an illustration".
3. AI graphic sequence: "two to four generated stills that are states of one graphic".
4. Drawn diagram: "anything exact or labelled; drawn with HyperFrames by default".
5. AI video: "It is one action per shot, of three kinds: **a walker; one action, close; a transfer, close, ending before the set-down.** A take is 3 to 15 seconds … **Any other kind (a crowd, a vehicle, a run, a door, night, people speaking) is not yet available as AI video: make it footage, a still or a drawn shot.**"

**From `part-treatment.md` (section 2):**

6. The direction first: "a few lines (at most 2000 characters) on what the audience should understand or feel by the end, the storytelling viewpoint, the principal visual approach and why, and the roles of footage, stills, generated scenes and graphics".
7. "Choose the picture from the film's purpose, audience and script before you think about how it is made: the effort, cost or convenience of a route never chooses the medium."
8. "In a documentary or a client story, people, purposeful work and the material changing under their hands carry the film; a realistic representative scene is a legitimate picture when the footage lacks one, provided it does not pretend to be the client's own site, people or measured result."
9. "**There is no quota of AI video, footage or graphics**: a technical record may lean on graphics, a human story on scenes; say in the direction which the film is and why."
10. "Read the whole first cut … Plan the missing passages in film order as one progression".
11. When to draw: "Use a diagram, chart or illustrated graphic when the meaning is invisible to a camera or must be read precisely: the inside of something …; a flow, force, heat or load path; a number, comparison or proportion …; a sequence where the order matters; scale; or before and after."
12. When to use a scene: "**Use a scene (footage, or AI video or still of people and places)** for people, places, materials, textures, effort, feeling and results, anything a camera could have filmed with more time."
13. "Build the film's graphics as one visual language: one recurring diagram that develops across the film".
14. "Vary the pictures: mix the shots of a gap longer than one shot (footage, an AI scene, a labelled scene, a graphic); two graphics in a row only when each passes the test above".
15. "A footage clip, or a specific thing the footage shows …, is named at one gap only".
16. The team's intended visuals: "a stated requirement with its source: follow them where they fit the direction and the footage; say in the treatment why you depart from one."
17. The opening: "opens on the subject at work, framed wide enough to see where (the mason laying bricks on the half-built wall, the site around), never an empty view of the place; a close-up comes after a wider view."
18. The look of a gap with no footage beside it: "palette, contrast, saturation, **muted and true to life by default**, light".
19. AI video inside the treatment: "an AI video shot is one action, **at most four people, nobody crossing, hand work close and in the right hand, every transfer named and close; a picture that needs more is re-staged, or is footage, a still or a drawn shot**".

### Step 4. The form of one treatment line

One entry per gap in `out/visual-treatment.json`:

| Field | What it is |
|---|---|
| `gap_id` | the gap |
| the words under it; the team's intended visuals, cited or departed from with the reason | free text |
| `picture` | the picture in one line |
| `routes` | footage, still, graphic_sequence, video, drawn |
| `seconds` | the gap's total, one number |
| `images` | how many pictures are to be made (one still per AI video shot counts) |
| `depicts` | one line per graphic |
| `frozen_seconds` | seconds held with no movement, "usually 0" |
| `shots` | only for more than one route: each `route` and `seconds` |

### Step 5. What the server does when the draft arrives (`visuals_stage.treatment`)

**Refused** (the draft does not get in):

- no motion style on the film (`FILM_MOTION`);
- no direction, or over 2000 characters;
- an unknown gap, a gap twice, a gap missing;
- a route that is not one of the five; a shot using a route the entry does not name;
- no `picture`; `seconds` not above zero; `images` not a whole number; `frozen_seconds` out of range.

**Warned** (the draft gets in, the warning is returned to the assistant):

- a still of more than 4 s: "at most 4 s; fill the stretch with several different stills or a moving shot" (`STILL_MOVING_MAX_S = 4`, SK, 23 Oct);
- more than 8 s of drawn or sequence graphics in a row within one gap: "above 8 s, break it with a camera shot"; above 12 s, "give the reason in the treatment".

**Added up**: gaps, pictures, seconds per route, the frozen share against its 10 % limit, the estimate in rupees against the limit of ₹5,000, and an amount "kept aside for takes made again".

**Not checked at all**: whether the picture suits the words; whether a scene with action is a still or a video; how many stills the film has; the share of the film that is stills; the length of a still in a gap with one route (see 5.3).

### Step 6. What the operator is given

One card (two when there are more than 12 lines). The first entry is the direction, in full. Each gap entry shows: The picture, Made as, Length, Pictures to make, Shows (for graphics), Held still for, Why. Above them, one line: gaps, pictures, estimate, limit.

The card does **not** show: the seconds of each shot inside a gap (only the gap's total), the words spoken under the gap, the team's intended visual for it, the share of stills, video and graphics in the whole film, or which warnings the assistant cleared before the card.

### Step 7. The record

When every line is accepted the treatment is recorded. From then on the plan is checked against it: a plan whose routes depart from the treatment is refused.

## 4. VW-23: what the treatment held

The direction (accepted as written) says: real footage carries the work; "What a camera cannot see is drawn"; and what the shoot did not film "is shown as realistic representative scenes, muted and true to life". It does not say whether those scenes are stills or video.

| Gap | Made as | Length | Pictures |
|---|---|---|---|
| BEAT_01-B1 | still, still, still, drawn, footage, still, still | 30.08 s | 5 |
| BEAT_02-B1 | drawn | 13.6 s | 0 |
| BEAT_03-B1 | drawn | 7.42 s | 0 |
| BEAT_03-B2 | still | 2.34 s | 1 |
| BEAT_03-B3 | still | **6.54 s** | 1 |
| BEAT_04-B1 | drawn, footage, drawn, still, still | 25.5 s | 2 |
| BEAT_04-B2 | drawn, still, still, footage | 14.62 s | 2 |
| BEAT_05-B1 | still | **8.3 s** | 1 |
| BEAT_05-B2 | still | **4.78 s** | 1 |
| BEAT_05-B3 | footage | 5.6 s | 0 |
| BEAT_06-B1 | still, **AI video** (a hand brushing oil on a plank) | 7.32 s | 2 |
| BEAT_10-B1 | drawn | 5.32 s | 0 |
| BEAT_11-B1 | still, **AI video** (a worker pouring water on the slab) | 11.68 s | 2 |
| BEAT_12-B1 | still, still, still | 9.12 s | 3 |
| BEAT_13-B1 | still, still, drawn, still, drawn, still, still, still | 28.3 s | 6 |
| BEAT_14-B1 | drawn | 4.08 s | 0 |
| BEAT_14-B2 | footage | 7.18 s | 0 |
| BEAT_15-B1 | still, still, still, still, drawn | 22.88 s | 4 |

Totals from the server's answer: 214.7 s of gaps. Stills 101.2 s (47 %), drawn 76.1 s (35 %), footage 23.8 s (11 %), AI video 13.5 s (6 %). 28 stills, 2 AI video shots. Frozen share reported: 0.

Cost, worked out from the two drafts' estimates: a picture is ₹4; the two AI video takes are about ₹125 of the ₹244.6.

## 5. Why VW-23 has so few AI videos and so many long stills

Each cause is a rule or a missing rule. None is a fault of one line.

1. **AI video is allowed for three kinds of shot only.** Rule 5 and rule 19 above. "Masons on the deck, the mixer and the workers feeding it" (BEAT_01), "a mason stacking clay tiles … a helper carrying coconut shells" (BEAT_04-B2), "a family on its veranda" (BEAT_15) are several people or more than one action, so by the rule they become "footage, a still or a drawn shot". The two shots that did become video are exactly the allowed kind: one action, close (a hand brushing oil; a worker pouring water). The three kinds come from the video tests of 5 to 12 Nov (design/170 to 181).
2. **Nothing prefers movement.** Rule 12 puts "AI video or still" side by side for a scene. No sentence says a scene with people working should move, or that a still is for things that do not move. Rule 9 says there is no quota. So a still is always a correct answer.
3. **The warning for a long still asks for more stills.** Its words: "fill the stretch with several different stills or a moving shot". In VW-23 the first draft had 10 such warnings; the assistant cleared them in 36 s by splitting stills: 18 pictures became 30. No still became a video.
4. **The 4 s limit does not look at a gap with one route.** `treatment_length_warnings` reads only the `shots` list, and a gap with one route has none. So BEAT_05-B1 (8.3 s), BEAT_03-B3 (6.54 s) and BEAT_05-B2 (4.78 s) passed with no warning. This is a hole in the check, not a decision.
5. **A still with a slow camera move is not counted as frozen.** The frozen share counts only seconds declared "held still". VW-23 reports 0 with 47 % of the gap time in stills. The one number meant to warn about a static film does not see them.
6. **The card does not show the mix.** The operator accepts line by line and never sees "47 % stills, 6 % AI video", nor each still's seconds inside a mixed gap.
7. **Cost is not the cause in the rules** ("cost … never chooses the medium"), but the assistant sees the estimate: a still ₹4, a take about ₹60. Whether that swayed it is a guess.

## 6. Rules that look too strict, or made for one kind of film

For SK to decide. Each is quoted in section 3.

| # | Rule | Why it is on this list |
|---|---|---|
| 5, 19 | AI video: three kinds, at most four people, right hand | The main reason scenes became stills. Written from tests on one model in one week. |
| 12 | "AI video or still" with no order | Leaves movement to chance. |
| 9 | "There is no quota" | Right against padding; also removes any floor for moving pictures. |
| 1 | "Footage first." | Two words that rank the routes for every film; rule 7 says the opposite. |
| 8 | "In a documentary or a client story, people, purposeful work…" | A rule for one category inside the general text. |
| 17 | "the mason laying bricks on the half-built wall" | An example from a building film. |
| 18 | "muted and true to life by default" | VW-23's direction repeats it word for word. Wrong default for an advertisement or a product film. |
| 4 s | A still at most 4 s, one number for every film | And its fix-it words push to more stills. |
| 8 s / 12 s | Graphics in a row | An explainer may need a 13 s diagram (VW-23's BEAT_02-B1 is 13.6 s and was not warned, because it is one shot in a one-route gap). |
| 15 | A clip "named at one gap only" | May force a made picture where good footage exists. |
| 17 | "never an empty view of the place; a close-up comes after a wider view" | A fixed opening for every film. |

## 7. Could not see

- The treatment file itself and its "reasons" (only what the two cards show).
- The team's intended visuals for VW-23, and whether the treatment followed or departed from them.
- What the assistant read before writing (1 min 45 s between the package and the first draft).
- Why the assistant chose a still for each scene; the causes in section 5 are read from the rules, not from its reasoning.
- The exact prices in the server's settings (the ₹4 and ₹125 are worked out from the two estimates).
