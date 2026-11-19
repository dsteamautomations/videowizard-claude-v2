# design/220: the sample sets are judged by Claude's check

SK, 19 Nov 2026, after the stage review of VW-24's References step 2 (`design/_work/stage-review-VW-24-step5-references-step2.md`). Built, not deployed. No version change in this commit.

## Why

- Since design/211 the first three sets are made first, "to check the method", and the others wait for the operator's "Make the other N".
- On VW-24 that cost one extra visit and held 17 sets for most of a day. It also did not do its job: one of the first sets failed Claude's check and the others were ordered anyway.
- Claude's check (design/214) now reads every set before the operator sees it. So the check can decide whether the others follow.

## The requirement (approved by SK)

The first three sets are made and checked by Claude. If all pass, the rest are ordered at once with no question. If one does not pass, the operator sees that set first with the check's words, and the rest wait for their answer.

- "Pass" means the check says "use". "Make again", "doubtful" and "not checked" all hold the rest.
- The operator still judges every set afterwards; nothing is approved for them.
- The chat and the page say the same new sentence about how many are made first.
- Three sets or fewer: all are made at once, as before.
- The older way (the operator's "Make the other N") stays as the path when a first set did not pass (design/35, row 174).

Edge cases:

| Case | What happens |
|---|---|
| A first set could not be made (provider failure or refusal) | The rest wait; the line of the other sets says which set could not be made; that set's own line gives the reason, as before |
| Claude's check never comes | Nothing is ordered; the rest wait |
| The limit has no room for all the rest | None is ordered; the line of the other sets says the limit sentence (no amount, as since design/213) |
| A place among the rest | It still waits for the sets of the things in it (design/216), also when the rule orders the rest |
| Things the operator set aside | Not ordered |
| The order fails part-way | A set not ordered keeps its reason on its own line ("Could not be made"); nothing is ordered twice (`go` is 2) |
| The looks are sent again | No second order |
| A first set made again later and passed | The rule does not come back: once the others were held, they are ordered on the operator's word only |

## What was built

- `ref_sets.rest_by_check(conn, store, user, run, outputs, out)`: called by the route `POST /visuals/round/looks` with the answer of `round_looks`. It acts only when the round is in its first go, sets still wait, and every made set has its look (state 2).
  - Every first set says "use": the others are ordered through `_order` (the same path as `round_rest`), `go` becomes 2, `rest_word` is `{by: 'rule', quote: REST_RULE}`, and one `decision` line by the server is written: "ordered by the rule, not by the operator: …". The answer carries `rest_ordered`, `errors`, `pass` and a `then` that starts with `REST_BY_RULE`.
  - Otherwise: the round keeps `rest_held` (`fault`, `unmade`, `unchecked` with the ids, or `limit`), and `then` starts with `REST_HELD`.
- `ref_sets.first_sets(session, rd)`: the sets of the first go as the check finds them.
- `chat_flow`: the line of the other sets (`sets:rest`) says why they wait (`rest_held_fault`, `rest_held_unmade`, `rest_held_unchecked`, or the limit sentence) in place of the general sentence; held by the check, it comes after the sets in the lines, so the set that did not pass is first (the sets were already sorted with "make again" and "doubtful" first).
- The sentences the operator reads:
  - `SAID_FIRST`: "The first 3 sets are made and checked first. When the check passes them all, the other N are made at once; when it does not, you see that set first and the others wait for your word. A set you ask to change is made again, at most 3 times."
  - `WORDS['goes']` and the page's help: "Up to 3 sets are made and checked first; when the check passes them all, the others are made at once, and when it does not, you see that set first and the others wait for your word. A set you ask to change is made again, at most 3 times."
- The served instruction (`scripts/d220_wording_v3.py`, +81 words): one sentence after "… when the others are ordered (`then`): pass it on as it is."
- Tests: `server/unit/test_design220_sample_by_check_pure.py`.

## Older ways

- The operator's "Make the other N": kept, as the path when a first set did not pass (design/35, row 174). No sentence of the instruction was replaced, so nothing was added to `server/retired-sentences.json`.

## Not covered

- One click to approve all the sets the check passed: a proposal of the stage review, not built.
- The assistant watching for finished sets while the page is open: a proposal, not built.
- Old runs: a round already past its first go is not touched; no migration.
- The plugin's command file still says "one click orders the other sets"; it stays true where they wait. The plugin was not changed.
- The page (`plugin/pages/decisions.html`) was not changed: it reads `why` and the order of the lines from the server. How the held line looks on the real page was not checked in a browser.
- A first set that is a place waiting for its things is not counted as a first set: the rule judges the method by the sets that were made.
- Not tried on the live server.
