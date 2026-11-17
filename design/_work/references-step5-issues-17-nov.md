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
