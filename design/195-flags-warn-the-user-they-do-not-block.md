# design/195: a flag warns the user, it does not block the piece

14 Nov 2026. From SK's review of the 52 flagged pieces of VW-23 (pictures in `model-test/vw23-compare/flags-review`). Not built. Waiting for SK's approval of this list.

## 1. The requirement, as I understand it

1. **A flag is a label, not a reason to remove a piece.** Licence plates, logos, labels, signboards, phones, background clutter, rubble, bottles, loose bars, a crew bag, a foreground object: all of these stay in the choice. A film on river pollution would lose every shot otherwise.
2. **The user decides.** A flagged piece may be offered as the second choice, or as the first choice when it is the only good piece for a sentence. The user is told plainly what the flag is, and can pick the other piece.
3. **Only truly useless footage is removed before the user sees it:** an empty frame, an unusable whip pan, footage that cannot be watched.
4. **A person talking to the camera or looking at the lens is not removed at once.** First try to hold the shot tight on the action so the person's face is out. Remove the piece only when that cannot be done (the person already fills the frame and is talking).
5. **Bad seconds are cut out, not the whole piece.** When someone walks in, or the person starts talking, those seconds are left out and the rest is still offered.
6. **Unprofessional moments (laughing at the camera, a fumbled banner) are flagged** and left to the user.
7. **A foreground object during a slow reveal is a camera technique,** not a fault.
8. **Unchanged:** no repeats, no reuse without a note, small pieces, shot sizes, the match rules of design/193.

My reading of one unclear point: you said laughter at the camera "can be removed" and later "can go in as a flag". I take the second: it is flagged and tried tight; it is removed only if it cannot be held tight on the action.

## 2. Where the removal happens today (three places)

| # | Place | Today | VW-23, 14 Nov |
|---|---|---|---|
| A | Gemini's grade | Grades a piece "reject" when a person looks at the lens or talks, before any tight crop is tried | 26 pieces graded reject; about 23 of them mention the camera, the lens or talking |
| B | Server, eligibility | Removes a piece Gemini marks "not safe for the client" | 7 pieces (3 with no other reason: clip C0059, licence plate and yard clutter) |
| C | Server's check of the cut | Refuses any shot that uses a piece with a flag | 38 pieces, 202 seconds |

## 3. The exact changes

| # | Change | File | Needs the clips studied again? |
|---|---|---|---|
| 1 | The check stops refusing a piece for a flag or for "not safe". It still refuses a piece removed for a reject grade or a failed crop. | `server/app/stage2/validator.py` | No |
| 2 | "Not safe for the client" no longer removes a piece. It becomes a stronger warning on the piece. | `server/app/clip_log/solver.py` | No (the free re-check does it) |
| 3 | Every shot and every alternative on the review page and in the chat shows its flags in plain words: "Has: licence plate in the background". The server writes this, so it does not depend on the assistant remembering. | `server/app/stage2/slides.py`, `templates/review.html` | No |
| 4 | The assistant's rule for choosing: a flagged piece may be used. Between two pieces that fit equally, the one without a flag goes first and the flagged one is its alternative. A flagged piece goes first when it is the only good fit. | options instructions in `server/procedures/v3.json`, `plugin/agents/vw-scene-review.md` | No |
| 5 | Gemini's instructions: grade "reject" only for an empty frame, an unusable camera move, or footage that cannot be watched. A person talking or looking at the lens is never a reason by itself: mark the boxes so the server can try the tight crop. Cut pieces around the bad seconds. Laughter, a fumble, clutter, plates, logos, labels, a foreground object in a reveal: flags only, and they do not lower the grade. | `server/app/clip_log/prompt.py` | **Yes** |
| 6 | The tight crop itself is not changed: the server already tries it and removes a piece only when the crop cannot hide the speaker. Change 5 lets pieces reach it. | none | |

## 4. Expected but unstated

- The warning also shows on a flagged piece that is an alternative, not only on the first choice.
- The flag words come from Gemini in its own spelling (`background_motorcycle_license_plate_unreadable`); they are shown with the underscores turned into spaces, not rewritten.
- The second look (the scene review) does not reject a shot for its flag alone.
- The waiver command (`vw analysis policy --waive`) stays; a waived flag is simply not shown.
- All categories: nothing here is specific to documentaries.

## 5. Edge cases and how each is handled

| Case | Handling |
|---|---|
| A piece with a flag and a reject grade | Still removed (the grade removes it, not the flag) |
| A piece Gemini marks not safe, good grade | Offered, with the stronger warning |
| A brief that records brand or safety rules | Same: warned, not removed; the user decides. (Today no run has such rules.) |
| A piece with many flags | All shown, in one line |
| No unflagged piece fits a sentence | The flagged piece is the first choice, with its warning |
| Person talking, crop cannot hide them | Removed, as today |
| Films analysed before this change | Changes 1 to 4 apply at once. Change 5 applies only to clips studied after the deploy. |
| The user rejects a flagged shot | Its alternative opens, as today |
| An older tool on a laptop | No new command; the plugin minimum does not change for this |

## 6. Failure modes

| Failure | Handling |
|---|---|
| Gemini still grades talking pieces "reject" after the new wording | Measured on VW-23's rerun (count of reject grades before and after); reported, not hidden |
| More pieces mean the assistant's list grows | design/193's list rule holds (exact fits in full, the rest in short rows); I report the size |
| A real problem piece reaches a film | The user sees the warning on the shot and decides; this is the intent |

## 7. Tests (light, as for design/193)

Unit tests only: a flagged piece passes the check; a reject-grade piece is still refused; "not safe" no longer removes; the review slide carries the flags; the new phrases are in Gemini's instructions and the assistant's. The full unit suite is run before the commit. No live model test: VW-23's rerun is the test.

## 8. Deploy and VW-23

- **Built on what is live (0.98.0), released alone as 0.98.1.** The intake-to-voice fixes already on `main` stay out of this deploy, so nothing else changes for the films in progress. They join at the later deploy with the image workflow.
- The server and workers restart (a few minutes; a running job is waited for).
- **VW-23:** the 14 Nov cut is first kept aside on the server (as the 13 Nov cut was), then the operator redoes the analysis and the options. Cost about 29 US dollars and about one hour for the analysis, on the 14 Nov figures.
- Then the same comparison as `design/_work/vw23-comparison.md`, three cuts side by side.

## 9. The older way

Retired with this change: "a piece that carries a risk flag cannot be used" and "a piece marked not safe for the client is removed". Row to be added to `design/35`.

## 10. Not covered

- The slow analysis start and the silent requests (still on the fixes list).
- No change to how many alternatives a shot may carry.
- No new page; the warning is one line on the existing shot card.
- The database tests (Docker is not running on this PC).
