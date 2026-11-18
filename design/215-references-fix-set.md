# design/215: References steps 4 and 5, the fix set of 18 Nov 2026

**Status:** built on 18 Nov 2026, server 0.112.0, plugin 0.96.0 (the plugin minimum is raised to 0.96.0: every laptop updates); **not deployed**, not pushed.

**From:** the requirement list SK approved (`design/_work/references-fix-set-18-nov-requirements.md`) and the review it rests on (`design/_work/references-review-round-18-nov.md`). The owner's rulings held: no amount is shown or named on the references steps; one word, "set"; the screens of steps 4 and 5 are desktop only; a rule is generic or filed under its category; text is written for today's picture models.

A round with `v == 2` is the rebuilt flow. A round without `v` keeps every older behaviour; only words that are not round-specific (the step's name) change for it.

## 1. What changed

### Part 1. Older rules no longer touch a server-written set request (a v2 round only)

| # | Rule | Now |
|---|---|---|
| R1 | The prompt library's wording rules | read only the words Claude (`row.prompt`) or the operator (the latest words in the request) added; a refusal names the word |
| R2 | The quoted-words rule | not applied to a set |
| R3 | "The plan cites the footage" | not applied to a set |
| R4 | "Measure it first" | not applied to a set; its second copy (`set_cause`) too, so "Make it" works and step 4 no longer warns or marks the thing doubtful for it |
| R5 | The "Not this" list | not appended to a set; the pictures of the shots keep it |

A refusal one of R3 or R4 stored on a row before the release reads "The rule that held this set back no longer applies to a set: it can be made now." Kept as they were: the film's limit, three makes, the input limits, no web picture of a person, an animal gets no set, "distinct people".

### Part 2. The seven changes

1. **"Leave out"** is three labels: "No reference needed" (step 4, and a thing back with the operator), "Do not make this set" / "Do not make these sets" (the waiting sets), "Go on without a reference" (a set that could not be made or was made three times). Each comes with the line naming the shots made without a reference. Beside "Make a set", only where a footage picture exists and may be used as it is: "Picture not good? Make a set instead."
2. **The cement bag's rule**: R3 and R4.
3. **What the picture model searched**: the worker reads Gemini's grounding record defensively and stores `searched` with the set: `yes`, `no`, `not asked`, `not known`. The line says: "The picture model searched the web: N pages." (with the list), "… It gave no list of pages.", "The picture model did not search the web." (for a set made from the film's picture: "It was asked to search only for what the film's picture does not show."), "No search was asked: a person's set …", "Searched: not known."
4. **The default look**: the treatment text says the default look follows the film's category and the Direction. In the set request, the documentary-only lines (photograph-like, natural colours and no stylisation, the film's look with its drawn sentences removed) are filed under `documentary-explainer`; the other categories read "Colour and finish follow the film's look given above."
5. **A correction's words**: kept per thing in the session, `thing_corrections: {element: [{words, at, by, set}]}`, never in the plan. Off by default: the operator ticks "This applies to every picture of this thing" (the chat: "Correct every picture of it", choice `correct_all`). The server carries them into every later request of the thing (a later set, a still, a start picture) with the operator's rank, in order, the later one winning, and the thing's line shows them. A thing the plan no longer names takes its corrections with it.
6. **The step's name**: "Sizes, materials and graphic specs"; "drawings" stays for step 3.
7. **How many are made first**: said by the server when step 4 is recorded and at "Make them", and in the page's help: "The first 3 sets are made to check the method. After you judge them, the other N are made in one go. A set you ask to change is made again, at most 3 times." Three or fewer: "All N sets are made now." (one: "The set is made now."); none: nothing.

### Part 3. The other findings

- W1: step 4's "Minor corrections" is "Make a set with words"; the words box's button is "Make a set with these words" (step 5: "Make it again with these words").
- W2: the chat says under "Approve": "Use this as the reference" (step 4: "Use the ticked footage pictures as the reference; nothing is made").
- W3: no amount in any sentence or answer of a v2 round (`cost_inr` is no longer sent there); the limit after "done" is the plain sentence.
- W4 to W6: the instruction text (`scripts/d215_wording_v3.py`): no "free" or "paid" in the references part, nor in a reason; an unticked picture is only not used; one order of authority, the program's.
- W7: `plugin/operator-CLAUDE.md` lists `vw-reference-finder` and `vw-set-look`.
- W8: an object in use: on a documentary-explainer film only the hand that holds it; in the other categories the person who wears, holds or uses it, as far as the use needs, the thing staying the subject (the request, the view, the check line, and what the looker is told).

### The page

`plugin/pages/decisions.html` renders what the server sends and holds none of the older words: `layout.words` (`leave`, `leave_set`, `set`, `fix`, `loss_head`, `done`, `wait_out`, `wait_made`, `corrections_head`, `searched_head`), a button's `go` (the words box's button), `note` (a hint beside it) and `all` (`{label, choice}`: the tick of a correction); a step-4 line's `corrections`. Step 5 shows the corrections and the search record in "Details", from the server's rows.

## 2. The older ways

Rows 130 to 142 of `design/35-decision-log.md`.

## 3. A round that is open at the release (VW-24)

Its made sets, answers and kept pictures are untouched. Its page and chat show the new words after the page is published again. The cement bag's stored refusal reads as retired, and "Make it" orders its set. Its made sets read "Searched: not known" (or "searched", with the pages, where pages were kept). The waiting sets are offered with "Make them" and "Do not make these sets".

## 4. Tests

`server/unit/test_design215_*.py` (rules, words, corrections, search, category, wording, browser), database-free; the pins of the older words moved in the tests of design/209 to 214.

## 5. Not covered

- Whether the picture model truly uses the search, and the field Gemini returns for image search: seen on the first real set after the deploy.
- The change of the treatment text (change 4) shows only on the next film's treatment; no film of another category has been run through the set request.
- An approved drawing set still asks for a photograph in every category (`DRAWN_LOOK_LINE`); a material keeps "no person" in every category.
- The operator's corrections are not carried into an AI-video take's prompt or a drawn graphic: stills, start pictures and sets only.
- "Distinct people" wording on the page; the lighter footage search; the "doubtful" rule; screens for steps 6 and 7.
- `server/pagetests/data` (the built page states) is not rebuilt; `server/tests` (with a database) were not run by the builder.
- The words of an older round's chat questions ("Leave it out") are kept as they were.
