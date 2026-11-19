# design/222: the contract of the AI video screen (step 7) and of Claude's check of a take

19 Nov 2026. The fixture of this contract is `server/unit/d222_takes_round.json`: one round in exactly this shape, built by the server's own functions. Where this text and the fixture disagree, the fixture wins. The page builds against the fixture; the server's tests hold a built line to the fixture's fields.

## 1. What is reused, what is new

Reused unchanged from design/217: the round document, the answers (`rounds/<round>/answers/<line>`: `{key, item, choice, notes, at}`), the small and large pictures (`pics`, `zoom`), the video page copy under a code in `zoom` only, `ROUND_BYTES`, `page_refused`, `vw visuals page --record`, the screen's frame (the list, one count, the end card, help, keys, Undo), the looks routes and `vw visuals pictures --looks`.

New: the layout `layout.kind = "takes"`, its line kind `take`, its words `layout.words.takes`; rows of kind `take` in the looks list; the closed round of step 7.

## 2. The round

`step` is `"AI video"`. Open: `open`, `lines`, `say`, `summary`, `note`, `layout = {kind: "takes", help: [str], coming: [row], words}`. Closed (a take is being made or checked): `open: false`, `closed: true`, `lines: []`, `say` and `then` the line of counts, `note` "The page opens when every take is made and checked.", no `layout`; the assistant publishes nothing.

`layout.words.takes` (the page holds no words): `todo`, `answered_head`, `coming`, `nothing`, `state_open`, `against`, `done {select, reject, again}`, `check_pass`, `more` ("See all {n}"), `seek` ("Go to {s} s"), `words_label`, `film`, `film_head`, `before`, `after`, `this_take`, `compare_only`, `details`, `d_check`, `d_passed` ("The {n} lines it passed"), `d_still`, `undo`, `cancel`, `close`, `change_in_chat`, `loading`, `missing`, `video_bad`, `left_one`, `left_many` ("{n}"), `left_note`, `end_head`, `end_note`, `end_foot`, `end_again` ("{n}"), `end_reject` (the end card's line when a take is rejected with no new one ordered), `foot` ("{n} of {m} answered."), `foot_wait`, `foot_done`, `help`, `keys`. The only substitutions the page makes: `{n}`, `{m}`, `{s}` in these words and `{words}` in a button's `say`. No amount of money anywhere.

`layout.coming[]`: `{name, kind_words, state: "failed", note}` for a take that could not be made.

## 3. A line (kind `take`): one AI video shot

| Field | Meaning |
|---|---|
| `line`, `key`, `item`, `state` | `l01`…; `pic:take:<job>:<mark>` (open; the mark is of the take's check as shown: an answer given to an older view of the check is stale) or `pic:take-done:<shot>` (recorded); the chat item's id; `open` or `recorded` |
| `kind`, `name`, `kind_words`, `ask` | `take`; the shot's title, else its gap's title and its number in the gap (never an id) |
| `where`, `film_at`, `words` | "In the film at 0:00.0 to 0:05.2 (5.2 s) · <gap>"; the shot's start; the narration as a plain line (shown only when `caption` is null) |
| `caption` | `{pre, post, words: [{t, s, e}]}` or null: the words spoken during the shot with their start and end in seconds from the shot's start; `pre` and `post` are the rest of the sentence, shown in grey and never marked |
| `takes` | every take of the shot, oldest first; the last is the one to answer (3.1) |
| `pics` | `{code, label, role}`: `before` / `after` (what sits directly before and after the shot, only to compare), `frame` with `take: n` (the take's first frame), `sheet` with `take: n` (its frames at four a second: shown in the player's place, with `video.none`, when the take's video cannot be shown), `still` (the picture the take started from) |
| `buttons` | the answers, each with `take: n`, the tab it belongs to (3.2); empty on a recorded line |
| `answer` | on a recorded line only: `{say, against, act}` |
| `details` | `[]` (a take's details are on the take) |
| `refused` | optional: the server's refusal of the last answer |

### 3.1 A take

`n`, `job`, `label` ("Take 2"), `tab` ("Take 1, rejected" / "Take 2"), `video {code, label, none}`, `secs`, `in_s` (the second of the take at which its place in the film starts: a word's time in the player is `in_s + s`), `short` ("" or "The take is 4.0 s; its place in the film is 5.2 s."), `rejected` ("" or "Rejected. You said: …"), `details [[head, [str]]]`, and `check`:

| Field | Meaning |
|---|---|
| `state` | `pass`, `fail` or `not_checked` |
| `head` | "Check passed" / "Check:" / "Not checked: …" |
| `faults` | `[{text, at_s}]`: the server's measured lines first ("One continuous shot: … Measured by the server."), then Claude's, each with the second it was seen (or null) |
| `by` | who checked, and against how many lines ("" when not checked) |
| `not_judged` | "Not judged: how things move between the frames. Play the take." |
| `passed` | the lines that passed |

### 3.2 A button

`label`, `choice` (`select`, `again`, `reject`, `old:<n>`), `act` (`select`, `again`, `reject`), `take`, `needs_words`, `hint`, `go`, `prefill`, `need`, `note` (a small line inside the open box: that a new take is paid; why no further take can be made), `say` (with `{words}`; shown with the answer and Undo), `end` (the short row of the end card, with `{words}`), and `sure {ask, go, back}` on "Use take n after all" when that take's check passed. "Make another" is absent when two takes were made from the camera or the cost limit would be passed.

### 3.3 What each choice calls (`takes.answer`, through the chat item's run function)

| Choice | Server |
|---|---|
| `select` | `review_take(accepted)` then `select_take` when nothing holds the take; else `select_take` with the operator's reason as notes |
| `reject` | `review_take(rejected, words)`; nothing is ordered |
| `again` | `review_take(rejected, words)`, then the word for one more take is kept on the shot (`guides[shot].again`); `guide.shoot` uses it once |
| `old:<n>` | the newer take is rejected ("the earlier take was used instead, at the operator's word"), then take n is accepted and selected (with the reason when its check did not pass) |

After `--record`, `tell` is the one line "N new take(s) … ordered: S s, about ₹M." and `then` says to say it as it is and ask nothing, then what the assistant does for each order.

## 4. Claude's check of a take

`GET /api/runs/{run_id}/visuals/pictures/looks` also lists the takes due, as rows of kind `take`: `{ref: <job>, sha10, kind: "take", name, shot_id, key: <the sheet at four a second>, inputs: [{ref, role: "frame", at_s, key} …, {ref, role: "still", key}], request, seconds, lines}`, with `how_take` beside `how`. `POST` the same route records a take's row like a picture's: one answer per line `{id, pass, seen, at_s}`, or `not_checked`. The refusals are the pictures' (a skipped line, an unknown line, a fail with no words) and "…: it is not a take waiting for its check now …".

Stored on the take's check record (`session.take_checks[job]`): `look {who, at, sha256, lines | not_checked}`, `asked_at`, and the `scorecard` rebuilt from the measured lines and the look. A take is offered with its look, or 30 minutes after Claude was first asked (as not checked), or at once when its frames could not be made; never before the worker has written its record (then 30 minutes after the take was made).

The worker stores with a take made from a guide: `frames [{at_s, key}]` (one every half second, the first and the last, 960 px wide), `sheet_key` (four frames a second), `code_lines` with "one continuous shot".
