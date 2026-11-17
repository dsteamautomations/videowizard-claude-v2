# design/212: the References step 1 screen in its new layout

**Status:** built on 17 Nov 2026, server 0.109.0, plugin 0.93.0 (the plugin minimum is raised to 0.93.0: every laptop updates); **not deployed**, not pushed.

**Why:** SK tested the rebuilt References step (design/211) on the first real film, VW-24, on 17 Nov 2026. His findings are in `design/_work/vw24-test-notes-17-nov.md` (1 to 14). A trial page with VW-24's real data was corrected with him over five rounds and approved; it is kept beside the repository, in `ux1-mockup/vw24-step1-v2/` (`references-redesign-trial.html`, with its screenshots in `shots/`). This change builds that layout into the real page and the server. It covers findings 1, 3, 4, 5, 8, 9, 10, 11, 12, 13 and 14. Findings 2, 6 and 7 are not in it.

## 1. SK's words, and what each led to

| # | SK said (17 Nov 2026) | Built |
|---|---|---|
| 3 | The screen is cluttered: the pictures with the grey "Claude saw" text fill the view, the question and its buttons are out of sight; two rows of number circles waste the top. "It need not be mobile-friendly." | Step 1 has its own layout, for a desktop, full width: a slim top bar, the list of things on the left, one thing at a time on the right, the buttons directly under the pictures. What Claude saw is behind an "i" on each picture. |
| 4 | "Have a set made (paid, about ₹35)" does not say whether a click starts the paid work at once; buttons are overloaded. | Short plain buttons: Approve, Make a set, Minor corrections, Upload my own, Leave out. Under them: "Nothing is made until you say done in the chat." |
| 5 | No clear way to choose one, two or all three pictures; no simple way to say "this one, with a small change". | A "Keep" tick on each picture. "Minor corrections" opens a words box. "Upload my own" is its own button. |
| 8 | "Make as Sets": one word for every kind of thing, people included. | The suggestion reads "Make a set", "Use footage" or "Leave out". "How this works" ends with what a set is. |
| 9 | Keep the bulk approval, but have a button to show the details. | "Show the N" beside "Accept all N" opens the routine things in the main panel, each with its footage pictures, the suggestion, the reason and "Open". |
| 10 | "remove all the places where the cost is mentioned. I give my approval not to show the cost anywhere on this page." | No cost at steps 1 and 2 of a v2 round, on the page or in the chat (section 5). |
| 11 | A person the footage does not show: "the user should not have any action at all"; "you are given the same buttons for all types of questions". | The buttons follow the case of the thing, and the server sends the case (section 3). Such a person is not asked (section 4). |
| 12 | "Minor corrections" on a thing with no picture: is it required, or is making a set sufficient? | "Minor corrections" only where footage pictures exist. With no picture: a small optional link, "Add words for the picture". The suggested answer is the first button. |
| 13 | Group those with a picture at the top and those without below. | Five groups, in this order (section 2). "Next" follows the same order. |
| 14 | In a narrow window the thing's name was cut to one letter. | The name keeps its room; the chips and the arrows wrap under it. Checked at 1000 px. |
| 1 | The table "Facts, and where each came from" gives its columns poor widths. | FACT narrow, a short label (24 characters or fewer) not broken; VALUE the widest; FROM wraps. The sizes table of a drawing's or a material's line got the same for its FROM column. The plan's shots table is as it was (its two narrow columns are numbers). |

## 2. What is built

One flow, two front ends: the group, the order, the case, the buttons, the auto-answer and every sentence are built in `chat_flow._round_v2`, which the page (`page_flow._refs_lines`) and the chat (`vw visuals next`) both read. The page file only draws.

**The round.** For step 1 of a v2 round (`session['round']['v'] == 2`) the page's answer carries `layout: {kind: 'things', made, help, stopped?}`; `vw visuals page` writes it into the round file; `plugin/pages/decisions.html` draws the new layout when it is there. Every other step, and a round without `v`, has no `layout` and is drawn as before.

**The five groups** (`chat_flow.STEP1_GROUPS`), in this order; the things are sent in it, the plan's order inside a group:

1. "Routine: accept together": the things that are not doubtful (the doubt rule is design/211's, unchanged).
2. "With footage pictures": doubtful, with a footage picture or a "closest found" picture.
3. "No picture: a set is suggested".
4. "No picture: suggested to leave out" (the proposal is `leave` or `no_set`).
5. "No action needed": a person the footage does not show.

On VW-24's round as the live release posted it: 6, 25, 3, 11 and 4, as on the trial page.

**A thing's line** gains: `group`, `case`, `name`, `kind`, `desc`, `used` (the full sentence on the shots), `shots` (the same in a few words, for a chip), `search` (`{text, why}` where it has no footage picture), `tick` (what a click is told when it needs a picture kept and none is), and `rec.choice` (the suggested button). Its `buttons` are the case's. It no longer carries `text` on the page (the chat says the parts as one text), the comment box, or a button under each picture.

**"Accept Claude's proposals for the N routine things"** (`refs:proposals`) gains `head`, `show` ("Show the N") and `covers` (the keys of the routine things). Its button reads "Accept all N". A thing the operator answered alone keeps their answer (`chat_flow.round_accept`, as before).

**The page.** The top bar: the step, "N of M answered" with a thin bar, "How this works", "Keys", the auto-advance tick, "Next to answer". The list: the filters All, To answer, Answered; the groups, which fold. The thing: its name, its kind, the shots chip (a click gives the full sentence), Previous and Next with "i of n", the description on one line, "Claude suggests: … Why?", the pictures in one row, each with "Keep", a small "Weak" mark and an "i"; a click on a picture opens the page's own large view (from the file store, design/210); the buttons under the pictures, the suggested one first and marked; a refused click said inline; "Your answer" with Undo; "Details" folded. Keys: the arrows or J and K, 1 2 3 for the ticks, A, S, C, U, L, Esc. The pictures, the large view, the own-picture upload and the answers use the page's existing code; the buttons of a thing with pictures work only when every picture has shown, as on every line. On a screen wider than 1700 px the row shows the large pictures.

## 3. The four cases, and what each button records

The stored round is not changed. A step-1 answer is still kept as `approve`, `clean` or `ignore` with `words` and `pics` (design/211 section 3.4). The buttons send what the operator means (`use`, `set`, `fix`, `ignore`); the server finds the stored choice.

| Case | When | Buttons |
|---|---|---|
| `footage` | it has footage pictures | Approve · Make a set · Minor corrections · Upload my own · Leave out |
| `closest` | only a "closest found" picture | Approve (refused until the picture is ticked) · Make a set · Upload my own · Leave out |
| `none` | no picture, a thing | Make a set · Upload my own · Leave out, and the link "Add words for the picture" |
| `auto` | a person the footage does not show, a set proposed | no answer needed; "Add words for the picture" and "Upload my own" only |

A person, and a thing with approved drawings, has no "Approve": a set is always made of it, so "Make a set" is its answer with footage too. A person shown in a made picture has no "Leave out" (design/211 decision 16).

| Button | Sends | Stored as |
|---|---|---|
| Approve | `use`, with the ticks | `approve`, where that takes the ticked footage pictures as the reference. A ticked closest picture is `pics: {id: 'use'}` ("that is it"). What a tick means: section 3a. |
| Make a set | `set`, with the ticks | `clean` where the thing can be taken from footage (from its ticked pictures); else `approve`, where that has a set made: from the ticked pictures, or from the description where none is ticked. |
| Minor corrections | `fix`, with the ticks and the operator's words (required) | as Make a set, with `words`: they reach the request as the operator's words. |
| Add words for the picture | `fix` with words | as Make a set, with `words`. |
| Upload my own | `own` | the existing own-picture path (design/210); for a person, their words of permission first. |
| Leave out | `ignore` | `ignore`. The page first shows which shots lose the thing, with "Leave it out" and "Cancel". |

Refusals, by the server, kept on the thing: Approve, Make a set or Minor corrections with no picture kept where one is needed ("Tick at least one picture first.", "…: the set is made from it.", "Tick the picture first, if that is it."); Minor corrections with no words ("Write what should change first."). The page says the same sentence at the click, before anything is written. The refusals of design/211 stand (a picture not on the line; the limit at "done").

An answer of the page as it was before this change (an answer document with `approve`, `clean` or `ignore`, as the 0.92.0 page wrote it) is still taken, through `page_record`, with the label it had then; it knew no ticks, so every picture it did not mark "not" is used.

## 3a. What a tick means (the review of 17 Nov 2026)

In plain words: **a ticked picture is used; an unticked picture is not used.** Nothing more happens to a picture that was never ticked.

- **Which pictures start ticked** follows Claude's proposal for the thing, not the "Weak" mark (the mark stays on the picture). The server sends it (`on` on each picture), so the chat, which has no ticks, uses the same pictures.
  - "Use footage", and a set that can only come from the footage pictures: every picture starts ticked, weak or not.
  - A set proposed for a person, or for a thing with approved drawings (a set is made of these with or without footage): the pictures that are not weak start ticked. With only weak pictures none is ticked, and the set is made from the description.
  - "Leave out": none.
  - A "closest found" picture: not ticked; a tick says "that is it". Once the operator has taken it, it is theirs and starts ticked.
- **A picture that started unticked and is left so** is simply not used: no "not this picture", no search for the next best, and the thing keeps its pictures on its line. At "done" the server sets those pictures aside (`chat_flow.round_close`), so the set is made from the ticked ones only.
- **A picture the operator ticks themselves** is used (`pics: {id: 'on'}`).
- **A picture the operator unticks themselves** (it started ticked) is "not this picture" (`pics: {id: 'not'}`), as before: it is rejected with their word and the next best may come in its place.
- **With no picture ticked**, "Make a set" means from the description, for a person and for a thing with approved drawings. For any other thing with footage pictures the click is refused: "Tick at least one picture first: the set is made from it."
- **The answer says what will happen**, before "done": "Make a set from the 2 ticked pictures.", "Make a set from the description; the footage pictures are not used.", "Approve: the 2 ticked pictures are the reference.", and the same for corrections. An answer kept from an earlier visit says it too.
- **When "not this picture" brings a picture the operator has not seen**, their answer and their typed words are kept and wait: the thing stays to answer with the note "A new picture was found for this thing. Look at it, then confirm or change your answer." and a "Confirm my answer" button. The new picture starts ticked only if the proposal would use it. **Once per thing:** if another picture comes after the operator has confirmed, it is left unticked (not used) and the answer stands.

The stored round keeps its shape: the kept answer's `pics` map now also holds `'off'` for a picture that is not used; the taken closest pictures are remembered in `session['refs_taken']`; an answer that waits for a look is `chat_round[eid]` with `confirm`.

## 4. A person the footage does not show

A person with no footage picture and no closest picture, for whom a set is proposed, is not asked. The line says: "Not in your footage. A set will be made from the description when you say done in the chat. No answer is needed; you may add words or your own photo." It counts as answered from the start. At "done" the server answers for it (`chat_flow._auto_held`, read by `round_close`, which both front ends pass through): a set is made. Nothing is stored for it before that. The chat does not ask it; its first question of the step says once how many people get a set without being asked, with their names. Words or an own photo given on the line replace the server's answer.

## 5. No cost at the references

For a v2 round at steps 1 and 2: no price on a button, no money in the summary, the note or any line, on the page and in the chat. The words were taken out at their source (`chat_flow.WORDS`: `paid`, `free`, `accept_first`, `goes_after`, `money`, `money_spent` are gone; the labels and questions that said "(paid)" no longer do). The server still enforces the limit and records every spend as before. Where "done" is refused because the answers ask for more than the limit allows, the existing refusal says so with its figures; the page shows it above the list (`layout.stopped`).

This replaces two earlier decisions: design/210's default that a paid button shows its price, and design/211 decision 11 and 18 (step 1 shows what the sets may cost and what the plan's shots still need, as a warning). SK, 17 Nov 2026: "I give my approval not to show the cost anywhere on this page."

## 6. The words

- "set" for every kind of thing; no "clean set", no "Have a set made", no "character sheet" in a sentence the operator reads at step 1.
- A shot is named by its number in its gap and the gap's number in the film's order: "shot 2 of gap 11". Before: "shot 2 of gap BEAT_11-B1", the gap's code name. The plan gives a gap an id and, sometimes, a title; the number is the plainest form that is always there and matches the order of the plan's page.
- "Your footage was not searched for it: No clip could show her: …" is now "Not in your footage.", with the reason behind a small "why". A thing searched and not found reads the same, with "Searched: N clips (…)" behind "why".
- "Claude suggests", on the page and in the chat (before: "Claude proposes").
- The instructions say the new way: `scripts/d212_wording_v3.py`, registered in `scripts/c1_split_v3.py` after design/211's four scripts; five sentences of the picture search and one of `plugin/commands/vw.md`; six older sentences are in `server/retired-sentences.json`. The visuals stage has 134 more words (14,927).

## 7. Decisions taken by default (SK can change any)

1. **For a set proposed for a person or a thing with approved drawings, "the proposal uses the picture" is read from the weak mark**: the round's row has no field that says whether Claude means the footage or the description. A field on the row would say it exactly (section 3a).
2. **One look per thing at a picture that came in place of a rejected one**; a later one is left unticked (section 3a).
3. **"Minor corrections" is not offered on a "closest found" picture**, as the requirement lists the cases. The trial page offered it there.
4. **A real, named person with no photo, not in the footage, is under "No action needed" too.** The warning that the set is made from the description alone is in "Details".
5. **A proposal that cannot be carried out as said** (use the footage, where a set must be made) reads "Make a set", which is what the thing's button does. The line is not routine, as before.
6. **"No set needed" reads "Leave out"**: one button word. The reason says why.
7. **The limit as a cause that stands** (`visuals_stage.set_cause`, kind `cap`) is no longer a warning on a step-1 line: it is said when "done" is refused. A set that was not made at step 2 because of the limit still says so on its line: that is a refusal.
8. **The answer said back on the page** ("Your answer: …", "Kept from before: …", "Decided: …"), the words of the panels ("What should change?", "Leave it out", "Cancel") and the keys are the page's own fixed words, as the trial had them.
9. **The trial's "Clear my answers" and its "Money" chip are not built**: the first was a trial tool, the second is the cost.

## 8. Older ways (rows 113 to 118 of `design/35-decision-log.md`)

A paid button shows its price and the summary gives the money; "Doubtful: answer these yourself" and the groups by kind at step 1; the same long buttons for every thing, a button under each picture and a comment box; a person not in the footage asked like every thing; a shot named by its gap's code name; the search sentences. Each is retired for a v2 round at release; a round without `v` keeps what it had.

## 9. Not built

- **Finding 2**: the helpers' usage (model, effort, the clips each helper is given, trial frames on one sheet).
- **Findings 6 and 7**: why the doubt rule marks so many things; how the set estimate is counted. The doubt rule is unchanged, so on VW-24 only 6 things are routine.
- **The step-2 screen** (judging the made sets) keeps its layout. Only its cost words went and its words follow section 6 ("Make a set", "Leave out", "Claude suggests", the shot names).
- **One "leave all N out" action** for the group suggested to leave out.
- **The "what next" sentences to the assistant after "done"** (`ref_sets.GO1_MAKING`, `ALL_MAKING`, `REWRITE_MAKING`) and the tool's own lines for `round --verdicts`, `--rest`, `--make` still give the amount. They are for the assistant, after the operator's "done"; whether the assistant should still tell the operator the amount then is SK's to decide.
- **A film whose only things need no answer**, in the chat: the chat has no question to hang "done" on. On the page "done" records it.
- A phone layout for step 1.

## 10. Tests

- `server/unit/test_design212_layout_pure.py` (27): the five groups and their order on the fixture and on VW-24's shapes (`server/unit/vw24_step1_shapes.json`: the 49 things of VW-24's live round, shape only); the four cases and their buttons; the person not in the footage, page and chat; no cost in any built line, summary, note, button or chat sentence at five states of a v2 round, while a refusal after "done" names the limit; what each button stores, with the ticks and the required words; "Show the N"; accept-all keeps a personal answer; no code name; 60 things in one document; an older round has none of this.
- `server/unit/test_design212_browser_pure.py` (7 tests, 10 runs, 100 assertions, headless Chromium): 1366×768 and 1920×1080, light and dark, then the list, the keys, the refusal, 1000 px, "all answered" and the facts table.
- `plugin/tests/test_design212_page.py` (3): the round file carries `layout`; the new choices travel with their ticks.
- Tests of design/211 whose pinned text changed are listed in the commit message.

## 11. Not verified

- Not deployed; no claude.ai page was published: the page file was drawn in a local headless browser with a stand-in for the page's database and file store.
- VW-24's own session was not read (no database, no VM): the proof on VW-24 uses the shapes of its 49 lines as the live server gave them, in a film built from the shared fixture. Its words and pictures were seen on the trial page only.
- No real model call, no HTTP call, no database test (`server/tests`).
- The large pictures in the row at 1920 px: the stand-in file store gives no link, so the tests show the small picture there.
- How the page reads with 49 things and their real pictures loading from a real page database.
- The old browser test of step 1 of a v2 round (30 checks of the layout that is gone) was removed, not rewritten for a phone: step 1 has no phone layout now.
