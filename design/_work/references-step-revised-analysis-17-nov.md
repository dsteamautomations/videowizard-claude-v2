# The References step: revised analysis

17 Nov 2026. For SK. **Nothing is built or changed.** VW-24 was only read.

This replaces yesterday's note (`references-step-review-vw24-17-nov.md`), which answered only the two questions asked. This one covers the whole step, from the first footage picture to the approved set, and asks of every job in it: is the right actor doing it?

## 1. The verdict in five lines

1. **The film's own footage is hardly used.** 111 of VW-24's 114 set pictures were made with no picture from the film as input. They were made from web photographs and a few words.
2. **Nobody with eyes judges anything before the operator.** A checking model exists, but its result is broken, partial, and hidden from the page.
3. **One mould is used for every kind of thing.** A person, a tool, a street and a way of working all get the same three views and the same rules, and the rules contradict the request.
4. **Every thing is decided alone.** 49 questions with nothing to decide by; 41 sets made apart from each other, which then disagree with each other.
5. **Of 59 judgements in this step, 31 are made by the wrong actor.** Most are the server deciding by a word list or a fixed rule where a model should look or read.

## 2. What was checked, and how

| Checked | How |
|---|---|
| Every function and instruction of the step | Three reviewers, each claim with file and line. I re-checked the four claims that matter most in the code myself |
| VW-24's plan, its 10 footage pictures, the 49 lines the operator answers | A read-only script on the server |
| VW-24's 38 made sets: the full request sent for each, what went in, what the checking model said | The same |
| The pictures | I looked at the two footage pictures SK named, and at 20 of the 38 sets (60 pictures) |

## 3. VW-24 in numbers

| | |
|---|---|
| Things in the plan | 50 |
| Things with a footage picture | 8 |
| Questions to the operator at step 1 | 49 |
| Sets ordered at "Done" | 40 (38 made, 2 failed) |
| Pictures made | 114 |
| Pictures made with a picture from the film as input | 3 (one set, the roof tile) |
| Cost of the 38 sets made | about ₹1,345 |
| Left of the ₹3,754 limit for every remake, still and video | about ₹2,400 |

## 4. The five root problems, with the evidence

### A. The film's own footage is not the source

- **Where a thing is seen** is decided by a word match, and the second given is "first seen" (yesterday's finding). 38 of 43 hints said 0.0 seconds.
- **The sets ignore the footage.** The request tells the image model to "search Google Images for real photographs" and says "the photographs win". No frame of the film is sent, except where drawings exist.
- **So the sets contradict the film.** The footage shows a trowel with a red handle and white plastic buckets. The sets show a trowel with a wooden handle and a galvanised bucket. A shot made from these references will not match the real clips beside it.
- **A bad footage picture becomes the reference with no second chance.** When the operator says yes to a footage picture, no set is made and the first frame becomes the thing's picture. For the pan, that is the frame where concrete covers it. The operator has no answer that says "make a clean set from this frame".
- **The analysis is stripped before this step.** The best frame, the shot size, the angle and what happens in each part of a clip are dropped (yesterday's finding).

### B. Nobody with eyes judges before the operator

- **Nobody looks at a footage picture** before the operator (yesterday's finding).
- **A checking model does look at each set, but:**
  - it looks at picture 1 of 3 only; the operator may choose picture 2 or 3;
  - one of its checks is broken: the size check compares two different kinds of value and fails **every** picture, so every set on VW-24 reads as "failed" and the word means nothing;
  - real failures were found and nothing happened. The support post set mixes a steel prop and a wooden post in one picture (the request forbids exactly this). The tile set fails 14 facts of its approved drawing. Both went to the operator like any other set;
  - **the page shows none of it.** Not the check, not the image model's own notes on what it found and what it changed.
- **The assistant is told not to study the pictures itself.**
- **The check never compares a set with the film:** not with the footage picture, not with the plan's description.

### C. One mould for every kind of thing

- **The same three views for every thing:** whole, three-quarter, close-up. The views the plan asks for are ignored. The mason's "right hand and forearm", the tile's "underside" and the pan "tipped, pouring" were never asked for.
- **Pictures 1 and 2 are nearly the same picture** for most things (brick, bucket, cement bag, stone heap, street, window shutter). The operator pays for three and gets about one and a half.
- **The rules contradict the request.**
  - A way of working (oiling a board, laying a brick) needs hands. The rules say "no person, no hands", and the check then fails the picture for showing hands.
  - A place (a street, a lane) is told "the subject fills the frame, the setting is only a soft hint". A street is its setting.
  - One set asks for evening light; the fixed text adds "natural daylight".
- **Every thing is put in the film's first place.** The first scene's "sandy unpaved street" is pasted into all 40 requests. So the fan regulator is on an outside wall beside a street, and the bucket and cement bags stand in the road. VW-24 has 9 places.
- **A person's second picture, "a working pose of their trade",** is asked of an eight-year-old girl and a house owner, and the later step forbids using it.
- **The fixed text is written for building-site documentaries** ("one way of working", "on one real site"). An advertisement or a product film would get the same sentences.

### D. Every thing is decided alone

- **49 questions with nothing to decide by.** A line shows a name and a fixed sentence; 33 lines carry the same sentence. No description, no reason, no count of shots that use the thing, no recommendation. The assistant already had a proposal (48 yes, 1 leave out) and it is not shown.
- **Things that do not deserve a paid set get one.** Clean water, a cotton curtain, a fan regulator, a coil of wire: ₹35 each. Oiling is four sets (the oil, the brush, the tin, the act).
- **The same thing is paid for more than once, and the copies disagree.** The "materials on the site floor" set draws its own stone heap, cement bags and bucket; each of those also has its own set, and they look different. The ceiling set shows flat square panels; the roof tile set shows ribbed tiles. They are the same tiles.
- **Places are made apart.** The roof deck, the room below, the house and the street are one building in the film and four unrelated buildings in the sets.
- **All 40 sets are ordered in one go.** There is no trial of two or three first. A fault in the fixed text repeats 40 times before one picture is seen, and it cannot be undone.
- **No approved reference is tied to the shots that use it.** A later picture must have the reference of its own thing only. A shot with the mason, the pan and the tile is not refused when two of the three references are missing.
- **Sets of places and of ways of working have no stated use later.** The later step names people and props as inputs. About ₹490 of VW-24's sets are for 9 places and 5 ways of working. That they go unused is an inference: no rule was found that uses them.

### E. Words and money that are not true

- **"Your footage has no picture of it"** means only "none was grabbed" (yesterday's finding).
- **The comment box at step 1 does nothing.** The words go to the log and never reach the picture.
- **"OpenAI rejected the request"** is shown for the two failed sets. The model was Gemini.
- **A set with one or two pictures is called "three pictures".**
- **"No" makes the set again with the same request.** Corrections pile up and cannot be taken back; there is no limit on remakes.
- **"Leave it out" does not say what happens** to the shots that need the thing. It is offered for people, although "a set is made for every person".
- **A round file sent a second time can spend without the operator.** A thing the operator left out is switched back on and its set is ordered at once.
- **One limit covers everything.** On VW-24 the sets took ₹1,345 of the ₹3,754 limit, over a third, before one still or one video was made. Step 1 does not show what the shots still need.

## 5. Wrong actor: the cases that matter

59 judgements were listed. **31 wrong actor, 22 right, 6 unclear.** The full table is in `refs-review/B-wrong-actor.md`.

| # | The job | Who does it today | Who should |
|---|---|---|---|
| 1 | Where the footage shows a thing, and at which second | Server: word match | A model reading the analysis; then a model looking at the frame |
| 2 | Is this frame a good reference? | Nobody | A model with eyes |
| 3 | Is this set right: against the film, the plan and the drawing? | A model, on picture 1 only, never blocking; hidden | A model on all three, shown to the operator, stopping a clear failure |
| 4 | Which views a thing needs | Server: a fixed list of three | The plan (it already says) |
| 5 | Does this thing need a set at all? Which picture is its reference? | Server: "has a frame, so no set; the first frame wins" | A model's recommendation, the operator's choice |
| 6 | The request for each kind of thing | Server: one fixed text for all | A text per kind, written from the plan's fields |
| 7 | The exact words of each request | The assistant retypes them from the plan | Server places the plan's words; the assistant adds only what is new |
| 8 | 49 routine yes or no answers | The operator, with no advice | A model proposes with a reason; the operator confirms the list and looks only at the doubtful ones |
| 9 | What a "Correct it" means for the request | Server: pastes the words on the end | A model rewrites the request |
| 10 | Which people look alike | Server: a word list (reads any number from 40 to 49 as an age) | A model |
| 11 | "This will spend money" on a second send | Server decides alone | The operator |
| 12 | What "Leave it out" costs the film | Nobody says | Server knows the shots: it should say |

**Right today, to keep:** prices, the limit, counts and state with the server; the spend at "Done", a real person's likeness, the drawing approval and the choice of picture with the operator.

## 6. Every gap, in one list

Size: S small, M medium, L large. "Y" marks yesterday's findings.

| # | Gap | Root | Size |
|---|---|---|---|
| 1 | A model looks at every footage picture first (Y) | B | S |
| 2 | The analysis sub-clips are passed on (Y) | A | M |
| 3 | A model's reading replaces the word match (Y) | A | M |
| 4 | One frame per view the plan asks for; each answered; all used (Y) | A, C | M |
| 5 | A frame rule that says what a reference is (Y) | A | S |
| 6 | "No picture" tells the truth and shows the closest (Y) | E | S |
| 7 | The set is made **from the footage picture** when one exists, even a weak one | A | M |
| 8 | An answer "make a clean set from this frame" | A | S |
| 9 | The size check is repaired | B | S |
| 10 | All three pictures are checked, against the footage, the plan and the drawing | B | M |
| 11 | A clear failure is made again once before the operator sees it | B | M |
| 12 | The page shows the check and the image model's notes | B | S |
| 13 | The plan's views drive the three pictures; no near-duplicates | C | M |
| 14 | A request per kind: person, thing, material, place, way of working | C | M |
| 15 | Each thing is placed where the film uses it, not in the first scene | C | S |
| 16 | The fixed text is made generic for every category of film | C | M |
| 17 | A person's pictures follow the plan; relative heights fixed across the family | C | M |
| 18 | Each line shows why the thing matters: its description, its shots, a recommendation | D | M |
| 19 | Grouping, folding, and "accept the proposals" for the routine ones | D | M |
| 20 | A rule for which things deserve a set, by their use in the film | D | M |
| 21 | Related things are made together or from each other (the yard and its heaps; the ceiling and its tile; one building) | D | L |
| 22 | A trial of two or three sets before the rest | D | S |
| 23 | Approved references are tied to every shot that names the thing | D | M |
| 24 | A stated use for sets of places and ways of working, or none are made | D | L |
| 25 | The step-1 comment reaches the picture, or the box is removed | E | S |
| 26 | The failure text names the right cause | E | S |
| 27 | A partial set is shown as it is | E | S |
| 28 | "No" and "Correct it": the request is rewritten; a limit on remakes | E | M |
| 29 | "Leave it out" says what it costs the film | E | S |
| 30 | A second send never spends without the operator | E | S |
| 31 | Step 1 shows the money the shots still need | E | S |
| 32 | A plan changed after the sets marks the sets that are now old | A | M |
| 33 | The page and the chat use the same words | E | S |

**How I would group the work** (an opinion, not a plan):

- **Stop the waste first (small):** 1, 5, 6, 9, 12, 15, 22, 25, 26, 30. Mostly sentences, one repair and one extra look.
- **Use the film (medium):** 2, 3, 4, 7, 8, 10, 11, 13.
- **Decide well (medium):** 14, 18, 19, 20, 23, 28, 29, 31.
- **Think again (large):** 21, 24. These ask what a reference is for, and are worth a talk before any build.

## 7. Not checked

- I looked at 20 of the 38 sets. The other 18 were read through their requests and check results only.
- "Sets of places and ways of working go unused" is an inference.
- Symptoms marked as inference by the reviewers (corrections piling up, the age word list) were not seen on a film.
- The chat way back was read only where it shares code with the page.
- No model's look was tried on VW-24's frames; that it would refuse the two bad ones is my expectation.

## 8. The detail

| File | What it holds |
|---|---|
| `refs-review/A-step-gaps.md` | 21 gaps of the step, each with the code line or VW-24 evidence |
| `refs-review/B-wrong-actor.md` | All 59 judgements: who does each, who should |
| `refs-review/C-carry-over.md` | 70 outputs of the treatment and plan steps: used here or not |
| `mistakes-and-learnings-treatment-plan-17-nov.md` | The mistakes and learnings of the two earlier steps, and their effect here |
