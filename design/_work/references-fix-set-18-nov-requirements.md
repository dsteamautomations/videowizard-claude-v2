# References steps 4 and 5: the fix set of 18 Nov, requirements

For SK's approval. **Nothing is built.** Sources: SK's seven approved changes, the dry run on VW-24 (18 of 18 waiting sets, read only), and the review round (`references-review-round-18-nov.md`). Would ship as one release (server and plugin), one deploy on SK's word.

## Part 1. Old rules that must not touch a server-written set request

The server writes the request of a set from the plan's own words. Rules made for requests the assistant writes still read it. Found by the review; two were proven by running the rule on sample words.

| # | Rule | What it refuses today | Change |
|---|---|---|---|
| R1 | The prompt library's wording rules | A plan description with "brand logo printed on the front", "600 x 600 mm tile", "flare", "Omni van" | For a set, the rules read only the words Claude or the operator added, never the plan's words |
| R2 | The quoted-words rule | `4" pipe`, `6' ladder`, `printed "OPC 53 Grade"`: inch and foot marks and printed names read as "words to show" | Not applied to a set |
| R3 | "The plan cites the footage" | A set of a thing whose size source says footage, with no kept footage picture | Not applied to a set |
| R4 | "Measure it first" (SK approved) | The cement bag on VW-24 | Not applied to a set; the same rule's second copy, which drives the "Make it" button and the step-4 warning, changes with it |
| R5 | The "Not this" list | Not a refusal: the operator's correction words are appended to the next request as things to avoid | Not appended to a set; the server's own request already carries the correction |

Kept as they are: the cost limit, three makes per set, the limit on input pictures, no web picture of a person, an animal gets no set.

To watch, not changed: two people whose descriptions carry no distinguishing words are refused a set ("distinct people"). This is a right refusal; the page must say it plainly.

## Part 2. SK's seven changes, as they should be built after the review

| # | Change | As approved | What the review changes |
|---|---|---|---|
| 1 | "Leave out" | Rename to "No reference needed", name what the shots lose, hint beside "Make a set" | The button does three jobs, so three labels: **"No reference needed"** at step 4; **"Do not make this set"** on a set waiting at step 5; **"Go on without a reference"** on a set that failed or reached three makes. Each with the line naming the shots made without a reference |
| 2 | Cement bag's rule | Off for sets | R3 and R4 above |
| 3 | What the model searched | Record web and image search; show "searched: yes or no" | Three states: **searched** (with the pages), **did not search**, **not asked** (a person's set). The Gemini field for image search is not verified: if the model reports only "search was used" with no page, the page says "searched" without a list |
| 4 | "Muted and true to life by default" | Default look from category and Direction | Also remove the fixed "no stylisation" line of the set request for films whose look is stylised; the film's category is stored and not yet used in the request |
| 5 | A correction's words | Add to the thing's description | **Not into the plan's description.** That would cancel the acceptance of every gap using the thing, mark the set "plan changed", and be overwritten at the next plan revision. Instead: kept per thing in the film's record as "the operator's corrections", carried by the server into every later request of that thing (stills, start pictures), shown on the thing's line |
| 6 | "Drawings" used twice | Rename the sizes list "Sizes and materials" | The same step also holds the drawing specs of drawn graphics. Name the step **"Sizes, materials and graphic specs"**, and keep "drawings" only for step 3 |
| 7 | How many are made first | Tell the operator in the chat and on the page | Said by the server in the chat when step 4 is recorded and again at "Make them": "The first 3 sets are made to check the method. After you judge them, the other N are made in one go. A set you ask to change is made again, at most 3 times." With 3 sets or fewer: "All N sets are made now." |

## Part 3. Other findings of the review, proposed for the same set

| # | Finding | Change |
|---|---|---|
| W1 | "Minor corrections" at step 4 makes a new set, and its panel button says "Send corrections" | Button: "Make a set with these words" |
| W2 | The chat explains "Approve" as "It is right; go on" | "Use this as the reference" |
| W3 | Amounts are still named: three assistant-facing sentences, one server line, and the page when "done" passes the limit | No amount on these steps, as SK ruled; the limit is said without a figure |
| W4 | "free" and "(paid)" in the instruction text and the command file (the source of finding 15: "free" in 11 of Claude's reasons) | Removed from the references part |
| W5 | The instruction text says an unticked picture is "not this picture"; live it is only "not used" | Text corrected |
| W6 | The order of authority (footage, drawing, plan's words, operator's words) is written three different ways | One wording, the code's |
| W7 | The operator's rules file does not list the two reference helpers among the allowed helpers | Added |
| W8 | Documentary-only text: references must be photographs; an object may show only a hand (a worn product cannot be shown in use) | Filed under the documentary category; the general rule allows the product in use |

## Unstated but expected

- VW-24 keeps working: its made sets, answers and kept pictures are untouched. The new words appear on its page after the deploy; the cement bag's set becomes makeable.
- A round posted before this release behaves as before, except words (old-ways rule: each older way is named as retired or kept until, in design/35).
- Every changed sentence goes through the wording scripts; retired sentences are refused by name.
- The page and the chat say the same words (one flow, two front ends): the server sends labels; the page stops hard-coding them (seven places today).
- Rules stay generic or are filed by category.

## Edge cases

- A set with only the plan's words (no added words): R1 has nothing to read; passes.
- The operator's added words break a library rule (a brand name, a model word): refused, and the page names the word, since the operator can fix that.
- Two corrections of one thing that contradict: both are kept in order; the later one is marked as the one in force.
- A correction about one view only ("the side view is too dark"): kept on the set, not carried to later pictures. The operator ticks "applies to every picture of this thing" (off by default).
- The plan is revised after a correction: the correction stays with the thing by its id; a thing removed from the plan takes its corrections with it.
- A film with 0 sets: no "first 3" sentence. With 1 to 3: "All N sets are made now."
- A first set that cannot be made: replaced by the next (live since 0.110.0); the sentence still says 3.
- "Go on without a reference" on a person shown in a made shot: refused as today (a person always gets a set).
- Search not asked (person), asked but unused, used with no page list: each has its own words.
- An older-round set (no `v`): none of Part 1 applies; it keeps the older rules.

## Failure modes

| Failure | Handling |
|---|---|
| A plan word that was refused before now reaches the picture model and the model refuses it | The set shows "could not be made" with the provider's reason behind "why"; the operator adds words, uploads, or goes on without |
| The search record is missing in Gemini's answer | "Searched: not known"; never guessed |
| A correction cannot be stored (the run is locked or a defect is open) | The answer is refused with the reason; nothing half-stored |
| The page is an older copy (plugin not updated) | Labels come from the server, so the words are right; the plugin minimum is raised so an old page cannot send an old answer shape |

## Tests

Area tests while building (each R-rule with the review's sample words, each label per case, the corrections carry-over, the three "searched" states, the chat sentence per count). One full suite run by me before the deploy. A short critic. A dry run of VW-24's 18 waiting sets again, read only, expecting 18 of 18.

## Not covered

- Whether the picture model truly uses the search, and the exact field for image search: seen only on the first real set after the deploy.
- Change 4 changes instruction text for the treatment; its effect is seen only on the next film's treatment.
- "Distinct people" wording on the page: listed to watch, not changed.
- The lighter footage search (finding 2) and the "doubtful" rule (finding 6): separate work.
- Screens for steps 6 and 7.
