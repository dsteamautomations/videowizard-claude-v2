# The reference screens on the artifact page: the plan, one screen at a time

16 Nov 2026. A plan for SK's approval. **Nothing is built.**

**Asked by SK:** "The next set of work is to make Claude Artifacts for References Screen … Think about showing thumbnails so that the page loads fast. But users should be able to see the image in zoom also. Identify the screens one at a time. And show me the plan for each step."

Builds on this morning's analysis (`reference-steps-on-the-artifact-page-analysis.md`) and on the three views already on the page: the treatment, the plan, and the drawings and materials (text only).

**One thing I take as decided by this request:** footage frames and reference pictures, people included, will be stored in the page's own storage on claude.ai, under the operator's Claude account. That was the open question from this morning. If that is not what you mean, say so before the build.

---

## Part A. How pictures get onto the page

Everything else depends on this, so it comes first.

### The two pictures of every picture

| | Thumbnail | Zoom picture |
|---|---|---|
| Purpose | The page loads fast and the operator sees every item at a glance | The operator checks the detail before deciding |
| Size | About 360 px wide, a small JPEG, about 15 to 25 KB (estimate) | About 1,600 px on the long side, a JPEG, about 150 to 250 KB (estimate) |
| When it loads | With the block, as it scrolls into view | Only when the operator clicks the thumbnail |
| Where the operator sees it | In the block, in a row | Over the page, full width, with next and previous inside the same item, and Esc or a click to close |

So the page never loads a full picture the operator did not ask for.

### Two ways to store them, and the one test that chooses

The page can hold pictures in two places. Each has a limit that matters.

| | 1. In the page's database | 2. In the page's file store |
|---|---|---|
| How | The tool writes each picture as a small file; the assistant sends the files in batches, as it sends a round today | The assistant uploads the picture files; the page shows them by their link |
| Limit | One item at most 256 KB; one batch at most 1 MB | 25 files per upload, each up to 15 MB |
| Good for | Thumbnails: about 40 per batch | Zoom pictures: full quality, 25 per upload |
| Weak point | Zoom pictures: only about 4 per batch, so a film with 140 pictures needs about 35 batches | Each uploaded file gets an id that must be matched back to its picture. A wrong match shows the wrong picture on a line |
| Change to the page | None | The page declares one more ability, so each run's page is published once more |

**Proposed:** thumbnails in the database (fast, no matching), zoom pictures in the file store (full quality, few uploads).

**The matching risk, and how it is removed:** every picture file is named by its own code, and the picture's code is drawn in small letters in a corner of the thumbnail and of the zoom picture. The tool reads the upload's answer from a file and matches by file name, never by order. And the page shows the code beside each picture, so a mismatch would be visible to anyone.

### Step 0: a short test before anything is built

On this PC, on a trial page, with pictures from a closed film. No product code.

| What is tried | What it settles |
|---|---|
| 40 thumbnails written to the database in one batch, shown on the page | Do embedded pictures show at all; how long a batch takes; does it ask for permission |
| 25 zoom pictures uploaded in one call, shown on click | Does the upload answer name each file, so matching by name works; how long; permission |
| The same page opened on a phone and a laptop | Load time; the zoom view |
| One zoom picture written to the database instead | The fallback, if the file store cannot be used |

**If the file store cannot be matched safely,** the fallback is zoom pictures in the database at about 1,100 px (about 7 per batch). It is slower to fill but needs no matching.

I report the measured figures and you decide the method. This is half a day at most.

---

## Part B. The screens, in the order the film reaches them

| # | Screen (your guide's step) | Pictures | Paid answers | Notes |
|---|---|---|---|---|
| 1 | Reference drawings (step 3) | The drawing sheets of each thing | None | First and smallest. Proves the picture method on drawings, where readable labels matter |
| 2 | References, part 1 (step 4) | Up to 4 footage frames per thing | "Make a set" is paid | One visit for every thing, then the sets are made |
| 3 | References, part 2 (step 5) | The 3 pictures of each set | "No" and "Correct it" are paid | One visit per cycle |
| 4 | Pictures, sizes and drawn graphics (step 6) | Each still, each diagram and its steps | Making a still again is paid | Several kinds of item; planned after 1 to 3 are proven |
| 5 | AI video shots (step 7) | The layout drawing, the starting still, then a video | The take is paid | Needs video on the page; planned last |

Each screen gets its own short requirement, its own tests and its own release. I move to the next only after you have seen the one before on a real film.

---

## Part C. Screen 1 in full: the reference drawings

### What it is today

For a thing whose shape matters (a building element, a machine part, a product), a helper makes a set of simple labelled drawings. The operator is asked in the chat, one thing at a time: "is the shape and arrangement right?" They are shown the labelled sheets, the facts with their sources and the sizes that are assumed. The answers are **Yes** and **Correct it** (with their words). It is free. A corrected drawing is redrawn and asked again. The reference round cannot begin while a drawing is open.

### Requirement

The operator sees every thing's drawing set on the artifact page, in one visit: small pictures in a row, any of them opened large with one click. They answer Yes or Correct it on each thing, say "done" in the chat, and every answer is recorded in one call, through the same function as today.

### What one block shows

- The thing's name, and how many sheets its set has.
- The sheets as thumbnails in a row, each with its label (front, side, from above, a section).
- A click on a thumbnail opens it large; next and previous move through that thing's sheets.
- The facts, each with where it came from, in plain words.
- The sizes that are **assumed**, as one clear line, so the operator knows what is a guess.
- Two buttons: **Yes, the shape is right** and **Correct it** (their words, with the counter).
- An approved set stays on the page, folded, with its thumbnails.

### Expected though not said

- The page step comes straight after the drawings and materials, and before the references.
- A thing with no drawing set does not appear.
- A set sent back shows "With the assistant" and the operator's words; when it is redrawn, it returns as a new block with the new sheets.
- An answer given to an older set is ignored, by name (the set's fingerprint is in the answer).
- Each answer is one line in the run's log, by the operator, with their words.
- The chat stays as the way back where the page cannot be shown.
- Pictures stored on the page are only those of this step, at the two sizes above.
- Nothing here is tied to one kind of film.

### Edge cases

| Case | Handling |
|---|---|
| No drawing set waits | The step is skipped; the page goes on to the references |
| A set with one sheet | One thumbnail; the zoom view has no next or previous |
| A set with many sheets (8 or more) | The row wraps; all are shown |
| A thumbnail has not arrived yet | A grey box with the sheet's label, and "loading"; the buttons work only when every sheet of that thing has shown |
| A zoom picture is missing or fails to load | The zoom view says so and shows the thumbnail enlarged; the operator can still answer, and the assistant is told which picture failed |
| "Done" with nothing answered | Nothing is recorded; the assistant says so |
| "Done" with some unanswered | The answered ones are recorded; the rest stay open |
| "Correct it" with no words | Refused on that line |
| The set was redrawn while the page was open | The answer is stale and ignored; the new set is asked |
| A film with many things (30 or more) | Thumbnails load as blocks come into view; the round's text stays under the page's size limit, with later blocks held for the next "done" as the plan does |
| A very large or oddly shaped sheet | Shrunk to fit both sizes; never cropped |
| The run is taken over on another machine | A new page is published and filled again from the server, pictures included |

### Failure modes

| Failure | Handling |
|---|---|
| No artifact tools, or publishing fails | The chat, as today; the assistant says once that the page is not available |
| Writing the thumbnails fails | One retry, then the chat for this step |
| Uploading the zoom pictures fails | The page works with thumbnails only and says zoom is not available; the assistant offers to show a picture in the chat |
| A picture file cannot be matched to its code | It is not shown as that picture; the block says the picture is missing. Never a guess |
| The picture cannot be downloaded from the server to the laptop | The assistant is told which; the step is not started half filled |

### What is built

| Piece | Where |
|---|---|
| The step's blocks as data, from the function the chat uses | The server's page code |
| The two sizes of each picture, made on the server and served to the tool | The server (it already makes a small version for its own page) |
| The tool writes the picture files, prints the batches and the upload list, and reads the upload's answer | The plugin's tool |
| The page: thumbnails, lazy loading, the zoom view | The page file |
| The guard allows the batch of picture files and the upload, only from the run folder to the run's page | The plugin's guard |
| The assistant's instructions for the step | The instructions, by a wording script |

### Tests first

- Server: the blocks for a waiting set, an approved one, one sent back; a stale answer; a refusal kept on its line; many things under the size limit; both picture sizes within their limits; a picture that cannot be made.
- Plugin: the tool writes one file per picture named by its code; the batches stay under the limits; the upload answer is matched by name, and a missing or doubled name is refused; the guard allows these writes from the run folder and nothing else.
- The page, on a local copy: the row, lazy loading, the zoom view with next, previous and close, a missing picture, phone width.

### Not covered in screen 1

- The references (screens 2 and 3), the stills and graphics (4), and video (5).
- The operator adding their own picture on the page: it stays a chat command.
- Editing a drawing on the page.

---

## Part D. Screens 2 to 5 in outline

Each gets a full plan like Part C when its turn comes. The points that are already clear:

**Screen 2, References part 1.** Every person, object and place in one visit. A thing the footage shows: its frames as thumbnails; "Use this" or "Leave it out". A thing the footage does not show: "Make a set (paid, about ₹35)" or "Leave it out". The top of the page gives the total: "7 sets, about ₹250, of the ₹3,754 limit". A person's block also carries the permission line for their own photo. After "done" the sets are made; the page shows each as "being made".

**Screen 3, References part 2.** Each set's 3 pictures as thumbnails, lettered. A person: Yes, No, Correct it. A thing: Use A, Use B, Use C, None of these, Correct it. "No", "None of these" and "Correct it" say they are paid. A set made again returns as a new block; approved ones stay recorded.

**Screen 4, Pictures, sizes and drawn graphics.** The items differ (a still, a diagram's steps, a reused picture, an open question), so the block has a few shapes. Diagram steps are shown in their order, each large on click.

**Screen 5, AI video shots.** The layout drawing and the starting still fit the picture method. The take is a video and must go in the file store; the page plays it in the block. The paid word to shoot stays explicit, with the cost on the button.

**Two decisions that come up at screen 2, not now:**
1. Is a click on a paid button, plus "done", enough for a spend, with the price shown on the button? (Today the chat rule is "inform, do not ask".)
2. Should step 1 offer one button, "Use every proposal as it is", so that step is one click?

---

## Order of work

1. **Step 0:** the picture test, then your choice of method.
2. **Screen 1:** reference drawings. Build, critic's check with critical findings first, release, your team's use on a film.
3. **Screens 2 and 3** together (they are one round in two parts).
4. **Screen 4**, then **screen 5**.

## Not covered by this plan

- The stages outside the visuals stage.
- The readable record of accepted lines for the treatment and the plan (offered earlier, not yet answered).
