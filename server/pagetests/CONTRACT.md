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
| `set_aside` | `{action: 'set_aside', element_id, words}` to set aside; `{action: 'set_aside', element_id, back: true}` to bring back | a press of "Set aside" on a set that was never made (the words at the foot go with it, optional); a press of "Bring back" | follow-up fix 3 |
| `reapprove` | `{action: 'reapprove', reference_id, sha256}` | a press of Approve on a rejected picture ("Use this picture" on an ignored footage picture, "Use it again" on a removed picture of the operator's own); the server function is `visuals_stage.reapprove_reference` | U17 |
| `supply` (an action of before, now also on a card) | `{action: 'supply', element_id, name, content_base64}` for a file, `{action: 'supply', element_id, url}` for a link | a press of "Upload my own picture" on the card of a thing or a place, at step 1 and at step 2 | U19 |

- `verdict`: `'yes'`, `'no'`, `'correct'`, or `null` while only the starting picture is chosen.
- `golden`: the picture's id, or `null` (a person's set, a No, nothing chosen yet). Never an empty string. Since U19 it may be the id of the operator's own picture of the same element (an approved `supplied` reference); the server refuses another element's picture and, for a person, an uploaded photo.
- `words`: the text of the card's words box (`''` when empty).
- Done (`round-sets`) keeps its body of today.

## 2. Fields added to the page's data (`GET …/visuals/data`)

| Field | Meaning | Requirement |
|---|---|---|
| `round.elements[<id>].answer` | `{verdict, golden, words}`: the stored answer of step 2, not yet recorded by Done; absent or `null` when none | R13, R14, E3, E5, E10 |
| `round.elements[<id>].aside` | `{by, at, words}` on an element set aside at step 2 (its `ignored` is `true`, as after Ignore at step 1); absent otherwise | follow-up fix 3 |
| `gaps[].shots[].asset.by` | the name of the person who supplied the file (a supplied movie or still) | R21 |
| `gaps[].shots[].asset.quote` | the operator's words given with the supplied file | R21 |
| `gaps[].shots[].asset.duration_s` | the length of a supplied movie, in seconds | E17 |
| `references[].locked` | one plain line saying why the verdict on this picture can no longer be changed (a later step used it), or `null`; set only on an approved or a rejected picture (`visuals_stage.verdict_lock`) | U17 |

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
| Set aside a set that was never made | `button[data-a="set-aside"][data-el="<element>"]`, beside "Make it now" (or alone where the page cannot settle the cause: a size not measured, a spec under revision); never on a set that was made | `Set aside` | follow-up fixes 3, 4 |
| Bring back an element set aside | `button[data-a="set-back"][data-el="<element>"]` on its card, while the round is open | `Bring back` | follow-up fix 3 |
| The confirmation of Done at step 1 (a kept film) | `#done-confirm`, shown by the first press of `button[data-a="round-done"]`; Back and Finish stay in `#action` | `N footage picture(s) used · N ignored · N set(s) will be made (paid, about ₹N) · N will not be made`, then who is not made and why | follow-up fix 8 |
| Retry a failed save of one answer | `button[data-a="set-answer-retry"][data-el="<element>"]` | `Try again` | E9 |
| The verdict on one picture, both ways (a footage picture at step 1, a picture on Pictures or Takes, a saved picture of an older film, the style sheet, the operator's own picture) | a candidate: `button[data-a="approve"]` and `button[data-a="reject"]`; an approved one: `button[data-a="reject"]`; a rejected one: `button[data-a="reapprove"][data-ref="<picture>"][data-sha]` | `Approve` / `Reject`; on a footage picture `Use this picture` / `Ignore`; on an own picture `Use it again` / `Remove` | U17 |
| A picture whose verdict can no longer be changed | `[data-locked="<picture>"]` (class `lockd`) in place of the buttons | the server's `locked` line, for example `Step 1 of the reference round is done with this picture used; it can no longer be changed here.` | U17 |
| A take, both ways | a rejected take offers `button[data-a="select-take"]`, a selected one `button[data-a="reject-take"]`; once its gap is recorded neither | `The gap is recorded; this take can no longer be changed here.` | U17 |
| Upload the operator's own picture, on the card of a thing or a place (step 1; step 2 on a set that was made and is not yet approved) | `[data-own="<element>"]` holding `input[type=file][id="up-<element>"]` (PNG, JPEG, WebP), `input[id="url-<element>"]` and `button[data-a="supply"][data-el="<element>"]` | `Upload my own picture` | U19 |
| No upload for a person | `[data-own-no="<element>"]` on the person's card; no file box | `A person's reference is made from the description; an uploaded photo is not used for people.` | U19 |
| A picture of the operator's own on its card | `.pic[data-own-pic="<element>"][data-item="<picture>"]`; at step 2 it carries `[data-golden="<element>:<picture>"]` like a picture of the set | `your picture` | U19 |
| The button whose request is running | the button is `disabled` and has class `busy` (it shows ` …` after its text) | | U18 |
| A refusal or a failure, beside the button pressed | `.near` (class `err` for a refusal, `net` for a failed connection), placed right after the button's own row, inside its card, the right panel or the foot; it stays until the next action or a redraw of the card | the same text as the bar `#fmsg` | U18 |

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
| The run's lock was held at this read (`busy: true`) | the header says, not in red, `the server is busy; the page reads again shortly`; no control is switched off and nothing says read-only. **E19 (a run another operator's machine holds) is not covered**: the data does not carry who holds the run | follow-up fix 1 (was E19) |
| A run with an open defect | the header's line of today; every `button[data-a]` is disabled | E20 |
| The spend cap reached | the header says `spend cap reached` with the spend; `Make it now` is disabled. Done stays usable: its confirmation says `The N set(s) to be made again will not be made: the spend cap of ₹X is reached … answered and waiting`, and Finish records the Yes answers | E15, follow-up fix 2 |
| An element set aside at step 2 | its card and its left-list card say `set aside`; no `.wdot` | follow-up fix 3 |
| An element, wherever the operator reads it (the foot line, `#notmade`, the confirmations, a refusal, the waiting list, a card heading) | its name; the id only as small secondary text on a card heading and under the left-list title | follow-up fix 5 |
| The green line after Done at step 2 | `Recorded: N approved`, then `· N being made again` only when above zero, then `The round is complete.` when it is | follow-up fix 6 |
| An unexpected failure of an action | the bar says `That could not be done; nothing was changed. The builder has been told what failed.`; never a key name or an exception's text | follow-up fix 9 |
| A picture whose file is missing | the picture is replaced by an element with class `ph` that says `picture not available` | E16 |
| A lapsed sign-in | the page goes to `/login?next=<the page's path and its #link>` | E10 |
| A script error | the bar turns red and says `the page hit an error; reload` | failure modes |
| An ignored footage picture at step 1 | it stays on its card, dimmed, marked `rejected`, with `Use this picture` | U17 |
| A file the page can tell is wrong, before anything is sent | `That file is larger than 15 MB: choose a smaller picture.`; `That file is not a PNG, JPEG or WebP picture: choose another.`; `Choose a file or paste an https link first.` | U19 |
| A tab switch | the right panel closes unless the new tab has its own selected card with a picture or a take; the address is `#<tab>` or `#<tab>/<card>` of the tab shown | U14 |
