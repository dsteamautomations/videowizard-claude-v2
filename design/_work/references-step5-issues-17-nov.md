# References step 5 (judging the sets): the issues, from VW-24's first two sets

17 Nov 2026. For SK, to read beside the guide's step 5. **Nothing here is fixed unless it says so.** VW-24 was only read.

Evidence: the two sets the rebuilt step made on VW-24 (the mason, the roof deck), the request sent for each, what the program's check said, what Claude recorded as its look, the lines the live page gives, and the pictures themselves, which I looked at.

## The issues, most serious first

| # | The issue | The evidence on VW-24 | What it means | Direction |
|---|---|---|---|---|
| 1 | **The page and Claude were shown yesterday's pictures.** A picture is remembered by its file name alone in three places: the server's small and large copies, the files on the operator's laptop, and the pictures stored on the page. | After the rollback, today's sets were saved under the same names as the sets of 16 Nov. Claude's remarks ("the whole man crouching with bricks, tiles and a pan"; "an empty deck, half the panels dark") describe the old pictures exactly. Today's pictures show the mason's right hand and forearm, and a deck with the grid and the clay fillers laid. | Claude recommended remaking both sets for faults that are not in them. The operator would have judged pictures that no longer exist. | **Being fixed now:** a picture is its name and its content together. After the deploy the two looks are redone. |
| 2 | **A person's set is made from words only, even when the footage shows the person well.** | The mason's request went with no picture (`inputs 0`). Claude's own reason for him says: "The man who demonstrates in the footage matches the plan's description, with good frames of face, hand and full length." | The film's mason and the made mason are two different men. Every shot of him will show the made one beside real clips of the other. | Decide the rule. Today a real person's footage picture is used only as their own likeness, with permission. If the man in the footage is the film's mason and his permission is given, his pictures should go to the set. |
| 3 | **The plan and the footage disagree, and nobody is asked which wins.** | The plan describes the deck as the top of a house's roof, open to the sky. The footage shows a mock-up on the ground in a yard. The request says "the film's own picture is the truth", and the model's notes say it "omitted any ground-level dirt staging … instead elevating the structure". The check then failed it: "depicts an elevated rooftop rather than the ground-level mockup". | The set follows the plan; the check judges by the footage. Whatever is made, one of the two says it is wrong. | When Claude proposes a set for a thing whose footage and plan differ, say so on the line and ask once: follow the plan, or follow the footage. The check then judges by that answer. |
| 4 | **The check says a face is "real" on a face made from words.** | The mason, picture C: "a real face: The face intentionally depicts the same person from the provided Reference 1 frame." No reference frame was provided. | A false alarm on every person, which teaches the operator to ignore the check. | The "real face" line is asked only when a real person's photo was an input. |
| 5 | **The check compares pictures B and C with picture A as if they should be the same view.** | The roof deck: "Picture B: same as picture 1: the layout … is swapped in perspective", "Picture C: … differ from the structure established". B is meant to be the other side. | A different view is reported as a fault. | "Same thing as picture A" must mean the same object and layout seen from another side, not the same picture. Give the check each picture's view. |
| 6 | **The three pictures of a place are not one place.** | The roof deck: in A the clay fillers cover the left half; in B they cover the right half; C shows a different arrangement. | The reference is not one agreed layout, so later shots cannot follow it. | For a place, make A first and give A to the model when it makes B and C (today the three are made in one conversation, which did not hold the layout). |
| 7 | **The set shows the footage's method, not the film's.** | The roof deck set is laid with round clay domes, as in the footage mock-up. The film's roof uses pairs of Mangalore tiles (the plan, and the approved tile drawing). | The reference of the deck contradicts the reference of the tile. | The request for a place names the film's own things that stand in it and gives their references. This is the "related things" point left out of the rebuild. |
| 8 | **The image model's notes are shown raw.** | "### What this picture adds", "`image_0.png`", "**The Variant Chosen and Why**". | Unreadable for an operator, though they hold the most useful sentence on the page ("I omitted any ground-level dirt staging"). | Claude turns the notes into two plain lines: what the model chose, and what it set aside. |
| 9 | **The same notes are attached to all three pictures.** | Each picture of a set carries the full notes of the whole conversation, starting "Here is the first of the three pictures". | The operator cannot tell which remark belongs to which picture. | Split the notes by picture when they are stored. |
| 10 | **"Leave these 11 out" lists 30 shots in one sentence.** | The line's cost sentence runs to about 900 characters. | Nobody reads it; the choice is made blind. | In the trial page it is a table, one row per thing. |
| 11 | **The 17 waiting sets and the 14 settled things look like work.** | 35 lines, of which 3 need an answer. | The operator scrolls past 31 lines to find 3. | In the trial page they are folded groups with nothing to press. |
| 12 | **The page groups by "Doubtful: look at these first" again.** | Both made sets are in that group. | The same wording that was replaced on step 4. | In the trial page: "To judge", "Could not be made", "Waiting to be made", "Settled". |
| 13 | **A set that could not be made shows the technical reason in the open.** | The family room's line ends with the refusal sentence about "middle" and "landmark". | It reads like an error message. (The cause itself is fixed: defect 54.) | "This set could not be made", with the reason behind "why". |
| 14 | **One "first three" set was lost to a fault and not replaced.** | Three sets were ordered first; the family room was refused, so only two came back. | The trial of three became a trial of two. | When a first set cannot be made, order the next one in its place. |

## What worked

- The request is now written by the server from the plan, per kind of thing: the mason's has his description, clothes, and one line against every other person.
- The views followed the plan: the mason's second picture is "right hand and forearm", which the plan asked for. Yesterday it was a fixed "working pose".
- The roof deck's set was given three footage pictures as inputs. Yesterday no set but one got any.
- All three pictures of each set were checked. Yesterday only the first was.
- Claude looked at each set before the operator and recorded a recommendation with its reason. (It looked at the wrong pictures, which is issue 1; the step itself worked.)
- The operator answered all 49 things of step 4 on the new screen, and "done" recorded them.

## Not checked

- I looked at the six pictures of the two sets and the three footage pictures of the deck. No other set exists yet.
- Whether the mason in the footage has given permission is not something the system knows.
- The fix for issue 1 is being built; it is not deployed.

---

## The judgement: is each proposed correction the right one?

Added 17 Nov 2026, at SK's request ("act on my behalf and say whether those fixes will be appropriate"). **Nothing is built; this waits for SK's approval.**

I judged each correction against the rules SK has set over these weeks: a model reads and looks, the program enforces; the operator is not asked what needs no answer; a rule fits every category of film; a real person's likeness needs recorded permission; nothing already approved is quietly set aside; the smallest change that removes the cause.

| # | Issue | My first proposal | Verdict | The correction I now recommend |
|---|---|---|---|---|
| 1 | Yesterday's pictures were shown and looked at | A picture is its name and its content | **Right. Done and live** (0.109.2) | None further. |
| 2 | A person's set is made from words though the footage shows them | "Decide the rule" | **Not enough: it left the decision open.** | At step 4, a person the footage shows gets one question: "Is the person in these pictures the one the film means, and do you have their permission?" Yes: their footage pictures go into the set as their own likeness, with the permission recorded. No: a stand-in from the description, and the request says the stand-in must not resemble the person in the footage. This keeps your permission rule and ends the two-different-men problem. |
| 3 | The plan and the footage disagree, and nobody is asked which wins | Ask the operator once | **Wrong: one more question that needs no answer.** | Claude already knows the difference and says so in its reason ("the footage deck lies on the ground; the plan's deck is on a roof"). It should write one more line per thing: what to take from the footage (the materials and their look) and what from the plan (where it is). The server gives that same line to the request and to the check. The operator reads it behind "Why?" and corrects it with "Minor corrections" if it is wrong. |
| 4 | The check calls a face "real" on a face made from words | Ask the line only when a real photo was an input | **Right.** Small. | As proposed. |
| 5 | The check treats another view as a fault | Give the check each picture's view | **Right.** Small. | As proposed: "the same thing as picture A, seen as picture B's view asks". |
| 6 | The three pictures of a place are not one place | Make A first, then give A to the model for B and C | **Wrong tool. The right one is already approved.** | Your image workflow (design/200, Area A) names a "composition set" for exactly this: a site, a room, where things stand. The roof deck should have had one. The correction is that Claude proposes the kind of drawing for every thing, places included, with its reason, and the operator sees it at the Reference drawings step. Chaining A into B and C is not needed then. |
| 7 | The set shows the footage's method, not the film's | Name the film's own things in a place's request and give their references | **Right, and it belongs with 6.** | A place's composition drawing is built from the film's own things (the tile's approved drawing), and the things that stand in a place are made before the place. |
| 8 | The image model's notes are shown raw | Claude turns them into two plain lines | **Right.** It is a reading job, so it is Claude's. | Done at Claude's look, where it already reads them: what the model chose, and what it set aside. The raw notes stay in the record, not on the page. |
| 9 | The same notes sit on all three pictures | Split the notes by picture when stored | **Drop it.** | Splitting free text by a program is the kind of rule that fails. With 8, the raw notes are not shown, and Claude's own line per picture already exists. |
| 10 | "Leave out" lists 30 shots in one sentence | A table, one row per thing | **Right.** In the trial page. | As in the trial. |
| 11 | Waiting and settled things look like work | Folded groups with nothing to press | **Right.** In the trial page. | As in the trial. |
| 12 | "Doubtful: look at these first" is back | Plain group names | **Right.** In the trial page. | As in the trial. |
| 13 | A technical refusal is shown in the open | "This set could not be made", reason behind "why" | **Right.** In the trial page. | As in the trial. |
| 14 | A first set that fails is not replaced | Order the next one in its place | **Right, small, low value now.** | Do it with the others; the cause of this one failure is already fixed (defect 54). |
| 15 | Places and rooms get no drawing | (found after the note) | **Same correction as 6.** | See 6. |

### What changed in my own proposals

- **Three were wrong or incomplete** (2, 3, 6). In each I had reached for the nearest patch: a question, another question, a chaining trick. The better answers were already in your own decisions: the permission rule, "do not ask what needs no answer", and the composition drawing of design/200.
- **One should be dropped** (9).
- **The rest stand** as proposed.

### How I would group the work

| Group | Items | Size | Needs from SK |
|---|---|---|---|
| The screen | 10, 11, 12, 13, with the trial page's layout | Medium | Approval of the trial page |
| The check tells the truth | 4, 5 | Small | Nothing |
| The request and the check agree | 3, 8 | Small to medium | Nothing |
| Drawings for places | 6, 7, 15 | Medium | A yes that places and rooms may get a composition drawing, as design/200 says |
| A person from the footage | 2 | Medium | A yes to the one question at step 4, since it concerns a real person's likeness |
| Small | 14 | Small | Nothing |

### What I would not do now

- Make the three pictures by chaining one into the next. The composition drawing is the approved way.
- Add any question the operator must answer about plan against footage.
- Parse the image model's notes by program.

