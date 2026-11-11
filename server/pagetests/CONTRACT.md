# The names the layer 3 tests expect

The approved requirements (`videobuilder-v4/phase2/ui/requirements-and-test-plan.md`) say what the operator sees. Where a requirement
needs something the page or the server does not have yet, the tests had to choose a name for it. Every such name is here. The page and
the two new server actions are to be built to these names; change a name here and in the tests together.

Everything else the tests use is what `visuals.html` has today (`data-a="<action>"` on buttons, `data-unit` on a centre card,
`data-unit-card` on a left-list card, `input[name="v-<element>"]`, `textarea#w-<element>`, `#panel`, `#fmsg`, `#action`, `#words`).

## 1. Two new server actions (`POST /runs/<code>/visuals/act`)

| Action | Body | When the page sends it | Requirement |
|---|---|---|---|
| `set_answer` | `{action: 'set_answer', element_id, verdict, golden, words}` | at every change of a card's answer at step 2: the starting picture chosen or changed, Yes / No / Correct it chosen, the words box left after typing. It always carries the card's whole answer | R13 |
| `set_make` | `{action: 'set_make', element_id}` | a press of "Make it now" | R17 |

- `verdict`: `'yes'`, `'no'`, `'correct'`, or `null` while only the starting picture is chosen.
- `golden`: the picture's id, or `null` (a person's set, a No, nothing chosen yet). Never an empty string.
- `words`: the text of the card's words box (`''` when empty).
- Done (`round-sets`) keeps its body of today.

## 2. Fields added to the page's data (`GET …/visuals/data`)

| Field | Meaning | Requirement |
|---|---|---|
| `round.elements[<id>].answer` | `{verdict, golden, words}`: the stored answer of step 2, not yet recorded by Done; absent or `null` when none | R13, R14, E3, E5, E10 |
| `gaps[].shots[].asset.by` | the name of the person who supplied the file (a supplied movie or still) | R21 |
| `gaps[].shots[].asset.quote` | the operator's words given with the supplied file | R21 |
| `gaps[].shots[].asset.duration_s` | the length of a supplied movie, in seconds | E17 |

## 3. Controls

| What | Selector | Visible text | Requirement |
|---|---|---|---|
| Choose the starting picture, on each picture of a thing's or place's set | the existing `[data-golden="<element>:<picture>"]` | `Use this as the starting picture`; the chosen one carries `aria-pressed="true"` | R2 |
| A person's set | the card `[data-unit="<element>"]` | contains `the full-length front picture is taken automatically` | R2 |
| A footage picture at step 1 | inside the card `[data-unit="<element>"]`, one pair per picture | `Use this picture` and `Ignore` | R3 |
| Make a set that was not made | `button[data-a="set-make"][data-el="<element>"]` | `Make it now` | R17, R18, E14, E15 |
| Material spec while a round is open | `#card-mspec-<element>` (the id of today's box) inside the card `[data-unit="<element>"]`, with today's `button[data-a="approve-spec"][data-shot="element:<element>"]` and `button[data-a="correct-spec"]` | | R11 |
| What will not be made, before Done at step 1 | `#notmade`, one line per element `[data-notmade="<element>"]` holding the reason and the control that settles it | begins `N will not be made` | R12 |
| The confirmation of Done at step 2 | `#done-confirm`, shown by the first press of `button[data-a="round-sets"]`, which sends nothing; inside it Finish is `button[data-a="round-sets"]` and Back is `button[data-a="round-picks-back"]` (the names step 1 uses today) | `N approved · N made again (paid) · N unanswered` | R15, E6, E7 |
| Retry a failed save of one answer | `button[data-a="set-answer-retry"][data-el="<element>"]` | `Try again` | E9 |

## 4. Texts and marks

| Where | Text or mark | Requirement |
|---|---|---|
| Waiting list links, tab and left-list card of a waiting thing | one of `picture to answer`, `set to judge`, `material spec to approve`, `drawing spec to approve` (a card may say the short `spec to approve`) | R7, R8 |
| The waiting mark on a left-list card | the existing `.wdot`; a click on it opens the thing that waits | R8 |
| Left-list card of an answered set, until Done | `Yes`, `No` or `Correct it`, then `not recorded yet`; no `.wdot`; its thumbnail is the chosen starting picture | R14 |
| A picture thumbnail (`.pic`) in the reference views | one of `approved`, `rejected`, `not answered` | R20 |
| An element's card | a one-line summary such as `2 approved, 1 rejected` | R20 |
| An element set to Ignore | its left-list card says `ignored` and carries no `.wdot` | E13 |
| A set approved in an earlier pass, on a later pass | the card says `approved` and has no Yes / No / Correct it | R16 |
| A set not made whose cause is settled | the card says `spec approved` (never the old reason) and offers `Make it now` | R18 |
| A set whose spec changed after it was made | the card says `the spec changed` and offers `Make it now` | E14 |
| A stored answer whose set was made again | `made again since; judge the new set` | failure modes |
| A card with an answer that is missing something | `choose the starting picture` (Yes on a thing with none), `say what to correct` (Correct it with no words) | E6 |
| A card whose answer could not be stored | `not saved, try again` | E9 |
| The card a refused or failed Done names | `not recorded` | R24, E8 |
| The message bar `#fmsg` | class `err` for a refusal by the server; class `net` for a failed connection | R24 |
| A shot filled with a supplied file, on Takes | the card's turn line has class `ok` and says `Supplied by <name>`, with the words; a still or a file shorter than its slot adds `assembly holds the last frame`; the left-list badge is `done` | R21, E17 |
| A run that cannot be written (`busy: true`) | the header says `read-only`; every `button[data-a]` and the Done button are disabled | E19 |
| A run with an open defect | the header's line of today; every `button[data-a]` is disabled | E20 |
| The spend cap reached | the header says `spend cap reached` with the spend; `Make it now` and Done are disabled | E15 |
| A picture whose file is missing | the picture is replaced by an element with class `ph` that says `picture not available` | E16 |
| A lapsed sign-in | the page goes to `/login?next=<the page's path and its #link>` | E10 |
| A script error | the bar turns red and says `the page hit an error; reload` | failure modes |
