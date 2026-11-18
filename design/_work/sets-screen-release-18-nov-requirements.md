# The sets screen and the VW-24 corrections: one release, requirements

For SK's approval, 18 Nov 2026. **Nothing is built.** One build, one deploy on SK's word (server and plugin). The screen is the trial SK corrected: https://claude.ai/artifact/Q41ji68skU4VR2ygSgSaBC (version 5).

## Part A. The step-5 screen, as on the trial

| # | Change |
|---|---|
| A1 | One large picture of the set; the small pictures in a row below it. The answer sits beside the picture. |
| A2 | The large picture is always a picture of the set. A footage picture never replaces it: a click on one shows it beside the set's picture ("The set: picture A" next to "Your footage, to compare: the whole place"). |
| A3 | One answer for the whole set: the heading "Your answer for the whole set (pictures A, B and C)", the line "One answer covers all 3 pictures", and the buttons "Approve all 3", "Make all 3 again", "Minor corrections". A set of one picture says "Approve", "Make again". |
| A4 | What belongs to one picture (the check's faults for it) sits under that picture. The answer column speaks only of the set. |
| A5 | Claude's recommendation as one coloured line with the first sentence of its reason; "more" opens the rest. |
| A6 | Approving against a "make again" recommendation asks once: "Claude's check found N faults in this set. Approve it all the same?" The list marks the row "Against advice". |
| A7 | The main picture is A; "Make B the main picture" is a link under picture B, for a thing. A person is always A. |
| A8 | "Use my own picture instead" is a link under the buttons. |
| A9 | Details as folded rows in the answer column: the check's faults, description, shots, what Claude saw, what the picture model did and searched, the operator's corrections. |
| A10 | The left list holds only what needs an answer, numbered; a tick when answered. "The other N sets" is the last row of the same list. "Settled earlier" is one folded row. |
| A11 | One count, in the bottom bar: "1 of 4 answered. When all are answered, say done in the chat. Nothing is made before that." |
| A12 | "The other N sets": the buttons "Make the other N" and "Make only some of them" (the table of what the shots lose). One label everywhere. |
| A13 | The end card lists what will happen, thing by thing, before the operator says done. |
| A14 | Type: Inter 14 px for text, Space Grotesk 20 px for the thing's name. Desktop only. |
| A15 | Gone from the screen: the filter chips, the "4 of 34" counter, Auto-advance, "Next to judge", "Keys", the box for the waiting sets, the radio under every picture. The arrow keys and Escape stay. |

## Part B. Corrections from the VW-24 screenshots

| # | Finding | Change |
|---|---|---|
| B1 | The chat said "four lines to answer and all 44 pictures"; the operator did not know what to do. | The server writes the chat message; Claude posts it unchanged: "3 things need your answer: the mason, the roof deck, the family room. Then choose whether the other 17 sets are made. Then say done here." No picture counts, no "lines". |
| B2 | Two to three minutes of silence before the page (finding 16). | The server gives the sentence Claude says before it starts: "Preparing N pictures for the page, about M minutes." |
| B3 | The family room still shows the old technical refusal. | A set held back by a rule that no longer applies shows the server's plain sentence and "Make it". |
| B4 | The roof deck shows clay pans, not the film's Mangalore tiles (finding 18). "Make again" would repeat it. | A place's request names the film's own things that stand in it and gives their approved references as input pictures. The things are made before the place: the first go and "Make the other N" order things before places. Approved in the judgement of 17 Nov. |
| B5 | Two people who read alike are refused a set in a technical sentence (finding 24). | Plain words on the page: "These two people read alike: add what tells them apart." |
| B6 | Two assistant-facing sentences and older-round labels still say "left out"; the command line cannot tick "every picture" (finding 23). | Reworded; the flag added. |

## Unstated but expected

- VW-24 keeps its made sets, its recorded checks and its answers. The new screen appears after the operator updates the plugin and the page is published again.
- Step 4's screen is not changed in this release.
- Every label comes from the server; the page and the chat say the same words.
- Older rounds (before the rebuild) keep their older screen.
- No amount of money anywhere, as before.

## Edge cases

- A set of one picture (a place, from rounds posted since 0.110.0): no "all 3", no main-picture link, no row heading "answered together".
- A set with no footage picture (a person, a thing not in the footage): no footage row, no compare.
- A set with more footage pictures than set pictures, or fewer: the compare shows the footage picture the operator clicked; by default the one with the same position, else the last.
- A picture that could not be opened by Claude ("not checked"): under the picture, "Claude could not check this picture", never "no fault found".
- Claude's recommendation is "not sure": the neutral colour, no button marked "Suggested", no against-advice question.
- The operator approves against advice, then undoes: the mark goes.
- B4: a place whose things are not made yet, or were answered "No reference needed": the request names them in words only. A place with more input pictures than the model takes: the film's things in order of how many of the place's shots show them, the rest in words.
- B4 on VW-24: the roof deck's "Make all 3 again" uses the tile's reference only after the tile's set is approved; before that the page says "This place shows the Mangalore tile, whose set is not approved yet: answer that first, or it is made from words."
- B1 with nothing to answer, or only the "other sets" question: the sentence names what there is.
- A narrow window: the answer column drops under the picture; nothing overlaps.

## Failure modes

| Failure | Handling |
|---|---|
| The large pictures did not upload | The small picture is shown enlarged, with "The large picture is not available." |
| The page is an older copy | The plugin minimum is raised; the server refuses the old page's answers with "Publish the page again." |
| B4 makes a request the picture model refuses (too many inputs) | The limit is kept by the server before the call; never a provider error. |
| An answer cannot be recorded | Refused with the reason; the page keeps the operator's answer on screen. |

## Tests

Area tests while building: the page tests in the browser for A1 to A15 with VW-24's round as fixture; the server sentences B1 to B3 and B5; B4's request, order and limits. One full suite run by me before the deploy. A short critic. A read-only dry run of VW-24's waiting sets and of the roof deck's new request.

## Not covered

- Step 4's screen in the same style: a later release.
- A correction into AI-video takes and drawn graphics (finding 21); a drawing set asking for a photograph (finding 22).
- Whether the picture model follows the tile's reference inside a place: seen only on the first real set.
- Mobile.
