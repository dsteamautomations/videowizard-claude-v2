# design/141: Revathi's VW-16 feedback checked against the code, combined with SK's design/140 answers (2 Nov 2026, for discussion before the build)

Sources: `vw16-feedback-for-builder.md` (Revathi, 8 points) and SK's answers in `design/140-vw16-options-review.md` section 5. Where points 5 and 6 correct point 3, they win (they were checked in the code). The builder checked them again on main: both are right.

## 1. Each point: done, planned, or new

| Point | What it asks | Status | Where |
| --- | --- | --- | --- |
| 1 | The scenes file shape in `shapes.json`, with where pauses go | **Planned** | design/140 Q9 (b) |
| 2 | One permanent decision log the server writes for every stage of every run | **New** (the largest item) | below, section 2 |
| 2 (options) | A blank lists the clips considered and why each was turned down; a shot with alternatives says why it won; why the sub-clips that are not eligible were ruled out | **New** | below, section 2 |
| 3a | A closing scene and the chapter rule | **Corrected by point 5**, planned | design/140 Q6: the server message is reworded; a closing may leave the chapter empty (already allowed) |
| 3b | "Carries over" matching | **Corrected by point 6**, planned and extended | design/140 Q1 (by meaning) plus point 6: spaces, underscores and hyphens count as the same, and the instructions say it is compared with the clip's landmark labels |
| 3c | The frame base (50 fps clip frames, 25 fps timeline) not stated | **New** | every frame number in the package says its base, or gives seconds beside it |
| 3d | Three timing rules with no common solution, so one was dropped everywhere | **Partly planned** | design/140 Q2 (a dropped marker needs a reason) and Q3 (a cut may end before a camera move). Still open: which rule wins when the three cannot all be met (question 2 below) |
| 3e | The for-information flags counted but not listed | **Corrected by point 6**, new (small) | `vw options check` says "the full list is in `vw options status`" |
| 3f | The second look's output cannot be read | **Planned** | design/140 Q9 (a) |
| 3g | A B-roll shot named by a step needs its own "why" | **New** (wording) | the options instruction says it, as the server already refuses without it |
| 4 | A chapter that comes only from the client's picture notes is dropped | **New** | below, section 3 |
| 5 | The closing-scene correction | **Planned** | design/140 Q6 |
| 6 | Carries-over matching and the flag list corrections | **Planned** (see 3b, 3e) | design/140 Q1, plus 3b and 3e above |
| 7 | A scene may name every chapter it covers | **Planned** | design/140 Q8 |
| 8 | The second look sees only the edges of each logged piece | **Planned, and extended** | design/140 Q5 gives stills across the shot. Point 8 adds: stills from the shot as cut (not the logged piece), taken again when the cut points change, and for a shot under a state or a claim ("undisturbed", "without") the whole moving shot or enough stills to see all of it |

Nothing in the design/139 build covers these points. design/139 changed the blank rules (no 3-second minimum, no 12-second warning, no 4-second hold), so the VW-16 notes about those rules no longer apply after its deploy.

**A correction to design/140:** B1 said the carry-over check matched "one word at a time". In fact it accepts a match when either text contains the other, ignoring case (point 6). "steel bars" failed only because the label has an underscore. "rebar" against `reinforcement_steel_bars` still fails, so SK's Q1 answer (by meaning as well as by word) is still needed.

## 2. Point 2: the server's decision log (new; proposal)

- **One log per run, kept with the run**, readable as one story and downloadable from the run's page.
- **Written by the server** at every decision it takes, in every stage:
  - a refusal or a flag, with the rule's name and what was seen;
  - an eligibility or crop verdict;
  - a retry, a recovery, an exclusion or an override, with who did it and their words;
  - each approval, with the operator's words.
- **Written by the assistant through the tool** for its own judgement calls: `vw log --stage <stage> --about <clip or shot> --rule <name or "no rule"> "<what and why>"`. Each instruction names the moments to log: every choice between clips, every blank, every workaround.
- **At the options step, carried by the cut itself**, so it cannot be left out:
  - each blank lists the clips considered, each with its reason from a fixed list (wrong action, wrong object, already used, a number or claim that needs a graphic, too short, unusable crop, other with words);
  - each shot with alternatives says why it was preferred.
  - The check refuses a blank without its list. A blank no clip could fill says "no clip shows this", with the coverage figures.
- **The package says which sub-clips were ruled out** (the 13 of 98 on VW-16) and why, from the analysis verdicts.
- The hand-kept log in the operator folder stays until this is live, then is retired (design/35).

## 3. Point 4: the client's picture notes (new; proposal)

- **At intake**, the picture notes ("Visuals" lines) are kept with the sentences they sit under, instead of being removed with the other non-spoken lines.
- **At the scenes step**, a chapter that no scene covers is shown to the operator: "this topic is in the client's picture notes but no scene carries it". The operator places it under a scene or drops it, with their words.
- **At the visuals stage**, a scene's picture notes are offered for that scene's blanks.
- **Nothing is dropped silently.** A dropped note is listed with the operator's reason.

## 4. Open questions for SK (one at a time in chat)

1. Point 2: is the log above the right scope (server events, the assistant's entries through `vw log`, and the cut carrying its own reasons)?
2. Point 3d: when the whole action, starting before the word and landing the action on its word cannot all be met, which wins?
3. Point 4: are picture notes kept from intake and offered at the scenes and visuals steps?
4. Point 8: for a shot under a state or a claim, send the moving shot, or more stills?

## 5. What will change, in plain words (the list Revathi asked for, to be confirmed after the questions)

1. Every run gets one decision log on the server, covering every stage: what was decided, by which rule (or "no rule"), and why.
2. In the first cut, each empty slot lists the clips that were looked at and why each did not fit; each chosen clip with a backup says why it won.
3. The first cut's package says which clips were ruled out by the analysis, and why.
4. "Stays visible" is matched by meaning as well as by word, and spaces, underscores and hyphens count as the same.
5. Each shot names the word it shows and its action word, or says why it cannot.
6. A shot may end before a camera move once the action is complete, and the analysis reports camera moves apart from the action.
7. The "colour changes" flag uses colours the server measures, so footage from one place on one day is one group.
8. The "natural cut point" flag fires only when a natural cut point was there and was not used.
9. The second look sees stills from the shot as it is cut, across the whole shot, and sees it again when the cut changes.
10. The second-look helper knows the server's note kinds and timing rules.
11. A scene may name every chapter it covers. A paragraph is split only where its second chapter runs two sentences or more, and the operator is told why.
12. The server's chapter message says what it checks: a closing may have no chapter.
13. Every frame number in the package says whether it counts the clip's frames or the film's, or gives seconds.
14. The check points to the full list of information flags, and long commands write their output into the run folder.
15. The scenes file's shape is in the package.
16. The client's picture notes are kept from intake, and a topic no scene carries is shown to the operator.
17. The instructions say that a B-roll shot named by a step needs its own "why", and the analysis step does not ask questions.

## 6. SK's answers

- **Q1 (point 2), 2 Nov:** **All three sources, and for every stage of the pipeline.** Server events, the assistant's entries through `vw log`, and the reasons the cut must carry. The log covers every stage, not only analysis and options: the treatment, the plan, the visuals, the pictures and takes, assembly and delivery included. Kept on the server with the run.
