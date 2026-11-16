# design/208: a page of its own for "A word sounds wrong"

16 Nov 2026. Requirements only. Nothing is built. Waiting for SK's approval.

The number 208 is the next free one on `main` today; the master thread may change it at merge.

Asked by SK on 16 Nov, from screenshots of the voices page on VW-23:
- "The button clicks are not very clear … they have to put in the spelling and submit it at one time. After submitting, there should be a different button to play it."
- "I think it's better that we just display it as a single word so that we can save some cost on it."
- "look at the two parallel scroll bars, which is again a difficult thing for the users … this is too cluttery."
- "we can take the user to a new page itself, let them finish the pronunciation, and then come back."
- "if they want to first listen to or re-listen to the incorrect method in the script and then they have to correct it."
- "Yes keep the sentence try as that small link." "Hear it now: agreed." "every paid button in this page alone" (the Are-you-sure popup).

## A. What changes

1. **A separate page.** "A word sounds wrong" on a narration's row opens a page for that narration. "Back to the narrations" returns. The side panel is retired.
2. **Two columns, one scroll bar.** Left: the script, the only part that scrolls. Right: the word card, fixed. "Corrected words (n)" is one folded line under the card.
3. **Hear it now (free).** Plays the word as it sounds in this narration, from about 1 s before it to 1 s after. Uses the narration's stored word times. No request to the voice provider.
4. **Three clear steps on the card.**
   - Step 1: type how it should sound.
   - Step 2: "Make the sound · paid, about N characters". The word alone is the standard try. Under it a small link: "Hear it inside its sentence instead (about N characters)".
   - Step 3: listen. Each try is a line with its spelling and its own Play. Playing is free.
   - Then: "Use '<spelling>' as final".
5. **Are you sure, on every paid button of this page, and on this page only.** The two paid buttons are "Make the sound" and the sentence link. The popup says what is sent and what it costs: "Make the sound for 'SHUT-er-ing'? Paid: about 20 characters." with "Yes, make it" and "Cancel".
6. **The cost is on the button before the click**, and no spelling is charged twice: a spelling already tried for this word and voice shows "Already made, press Play".

## B. Expected though not said

1. Every try and every final word is saved on the server as today, so a refresh, the Back button or a closed tab loses nothing.
2. The page uses the server functions that exist (`try_word`, `finalise_word`, `remove_word`, `words_view`). `vw voice pronounce` in the chat tool is unchanged.
3. One new server function gives the places and times of a word in a narration, read from the narration's `timing.json`. The page calls it for "Hear it now".
4. The link the tool prints still signs the browser in; a session that ran out goes to sign-in and comes back to this page.
5. When any final word changed, the narrations page shows "Narrate again with the final words" highlighted, as today. That button stays on the narrations page, so it gets no popup from this change.
6. Clicking a word in the script selects it, highlights it and fills the card. A word with a final spelling stays underlined.
7. The header says which voice and which narration (number and time made) the page is for.
8. While a try is being made, its line says "Being made, about half a minute" and Play is grey; the page checks by itself and lights Play when it is ready.
9. No popup on leaving the page. SK chose the popup for paid buttons only.

## C. Edge cases

| # | Case | What happens |
|---|---|---|
| 1 | No word picked yet | The card shows one line: "Click a word in the script, or select several words for a name." No buttons. |
| 2 | The spelling box is empty | Step 2 is refused beside the box: "Type how it should sound first." No popup, nothing sent. |
| 3 | The same spelling was tried before (same word, same voice, same kind of try) | No popup and no request: "Already made, press Play". |
| 4 | The spelling is changed after a try | The earlier try keeps its own spelling on its line. The final button names the spelling in the box. |
| 5 | Cancel on the popup | Nothing is sent, nothing is charged, the box keeps its text. |
| 6 | A double click on "Yes, make it" | One request. The button is off until the answer comes. |
| 7 | Two tries being made at once | Each has its own line and its own state. |
| 8 | The page is refreshed while a try is being made | The line is back with "Being made"; it finishes as before. |
| 9 | A try fails at the provider | The line says "This try failed" with the reason and "Try again" (which asks again with the popup). |
| 10 | The word is in several places | "Hear it now" shows "place 1 of 2" with arrows; the script scrolls to the place. The sentence link uses the place shown. |
| 11 | A name of several words, selected with the mouse | Treated as one word everywhere, as today. "Hear it now" plays from the first word to the last. |
| 12 | The word is first or last in the script | The lead-in or the tail stops at the start or the end of the recording. |
| 13 | The narration has no word times (an older one, or one recovered without them) | "Hear it now" is not shown. One line: "Not available for this narration: use its player on the narrations page." Everything else works. |
| 14 | The narration was made before the final words changed | "Hear it now" says under it: "As narrated on <date, time>, before the final words". |
| 15 | The audio file does not load | A line beside the button: "The recording could not be played. Try again." |
| 16 | The page is opened without a narration, or with one that is gone | It goes back to the narrations page with a line saying why. |
| 17 | The voice stage is already final | The page opens for reading and listening; the paid buttons and "final" are refused with today's message. |
| 18 | The word has punctuation or a capital beside it ("Kendra," "kendra") | Matched as today's word pattern does; the card shows the word without the punctuation. |
| 19 | A very long script | Only the script column scrolls. Opening a word from "Corrected words" scrolls the script to it. |
| 20 | A narrow window (under about 900 px) | The columns stack and the page scrolls as one; the script is not in a box of its own. Still one scroll bar. |
| 21 | Two people, or two tabs, on the same run | The lists come from the server; a refresh shows the other's tries and finals. |
| 22 | The operator makes a word final without any try | Allowed or not exactly as today; this change does not alter it. |
| 23 | The cost on the button | Counted from the text that will be sent: the spelling for the word alone, the sentence with the spelling for the sentence try. |
| 24 | Removing a final word | In "Corrected words", as today. Not paid, so no popup. |

## D. Failure modes

| What fails | How it is handled |
|---|---|
| The server cannot be reached on a paid click | A line on the card: "Not sent. Nothing was charged. Try again." The box keeps its text. |
| The provider refuses or times out | Case 9. The server's job record says whether anything was charged; the line repeats it. |
| The word times are slightly off | The 1 s before and after covers it. If the word is still cut, the arrows and the main player remain. |
| The session ran out | Sign-in, then back to this page with the same narration and word. |
| The page's own check for a finished try stops | "Refresh" on the line; the try is on the server either way. |

## E. Older ways

| Older way | From this change |
|---|---|
| The side panel that slides in from the right on the voices page (design/194) | Retired. The button on the row opens the page instead. |
| "Hear it in its sentence" and "The word alone" as two equal buttons that both send and play | Retired. One paid button (the word alone), the sentence as a small link, Play apart. |
| A green line after the click saying what was charged | Retired. The cost is on the button and in the popup before the click. |

A row for `design/35-decision-log.md` and three old-ways rows are added with the build.

## F. Tests (written first)

Unit tests only, kept in `unit-local/` as for design/192 and 194, unless SK says otherwise.

1. Server: the places and times of a word in a narration: one place, several places, a name of several words, first and last word, punctuation and capitals, a narration without times.
2. Server: a spelling already tried is found and no new job is made; a new spelling makes one job; the kind of try (alone, sentence) is part of the match.
3. Server: the page opens for a narration; without one, or with a missing one, it sends back; with the stage final it is read-only.
4. Page (local copy with a stand-in server, in the built-in browser): the popup on both paid buttons, Cancel sends nothing, one request on a double click, "Already made", the try lines and their Play, "Hear it now" with the arrows, one scroll bar at 1280 px and at 800 px.
5. The existing `server/unit` and `plugin/tests` are run again; any test that pins the side panel is changed with the change.

## H. Built (16 Nov, on SK's "Approved, build it")

On the branch `worktree-stage-fixes-vw23`, with `main` (a1f4ec3) brought in first. Not pushed, not merged, not deployed. No version number was changed.

| Where | What |
|---|---|
| `server/app/templates/voice_words.html` (new) | The page: two columns, the script the only scrolling part, the card with "Hear it now", the three steps, the question before every paid request, "Corrected words" folded. |
| `server/app/web.py` | The page at `/runs/<code>/voices2/words/<job>` and its data at `…/data`; the free action `word-cost`; `word-final` takes the spelling chosen. |
| `server/app/voices.py` | `token_times` (the time of every word in a narration), `try_preview` (the cost and "made before"), `_kept_try` (any earlier try of the same spelling, not only the last), `finalise_word(…, say_as)`. |
| `server/app/templates/voices2.html` | The side panel is removed; the row's button opens the page (only on a narration that is ready). |
| `design/35-decision-log.md` | Decision row 121; old-ways rows 91 to 96 (renumbered at the merge, after design/207's rows 81 to 90). |

Three things differ from the list above, each on purpose:

1. **"Use … as final" is on each try's line**, not one button for the spelling in the box. A word is made final only as a spelling that was heard, and it is always clear which one.
2. **The narration is in the page's address** (`…/words/<job>`), not after a question mark, so a sign-in comes back to the same narration.
3. **A narration that is gone (case 16)** shows a line on this page with "Back to the narrations", instead of sending the browser back by itself.

Tests, run by Claude on this PC with Python 3.12:

- New: 20 tests in `unit-local/test_d208.py` (not in git, by SK's earlier word). All of `unit-local`: 146 pass.
- `server/unit`: 1,834 pass, 1 skipped, none fail.
- `plugin/tests`: 501 pass, 7 fail, the same 7 Windows-only ones as before this work (line ends, Mac paths, page links); the plugin was not touched.
- One local test that pinned the side panel was changed (`unit-local/test_d194.py`).
- The page was tried in the built-in browser on a local copy with a stand-in server (`unit-local/make_word_page_harness.py`): picking a word, "Hear it now" (starts 1 s before the word), the arrows, the empty box refused, the question and Cancel, one request on a double click, "Being made" then Play, "Already made", the sentence link, final on a chosen try, remove, one scroll bar at 1280 px and at 800 px.

## I. Second part: from the corrected word to the narration made again (built 16 Nov, on SK's "Yes, build A to K")

SK, 16 Nov: "I somehow feel there is a gap in the flow … simulate a real user." The walk-through found six gaps (A to E below answer them); a critic's pass on that proposal found six more (F to K).

| # | Change | The gap it closes |
|---|---|---|
| A | On the word page, when approved words are not in this narration: a bar "n corrected words are not in this narration yet" with "Narrate again with these words (paid, the whole script)", asked with the Are-you-sure question; then back to Narrations. | The word page never offered the next step. |
| B | The same button on the narration's own row, for that row's voice. The one in the bottom bar is removed. | The button was hidden when the bar was minimised; it could name another voice; two buttons for one action. |
| C | When the new narration is ready, its row shows "Check the corrected words": the word page listing each corrected word with "Hear it now" from the new narration, free. A word still wrong is corrected again from there. | No quick way to verify; the operator would listen to the whole narration again. |
| D | On the page a word is "approved" ("Approve this spelling", "Approved words"). "Final" is said of a narration only. The server's next-step line says "approved words" too. The tool's flag `--final` keeps its name. | Two different things were both called final. |
| E | One line on the word page: "Correct every word first, then narrate once. Each narration reads the whole script and is charged in full." | No advice on cost. |
| F | The same word with a capital (at the start of a sentence) is corrected with it. The card says so: "also 'Shuttering', 1 place". | The rule sent to the voice matches the word exactly as written, so a capitalised place stayed wrong and was not counted. To be confirmed with a real voice. |
| G | The Are-you-sure question for a narration names what is left out: "1 word is still being tried and will not be in it: Kendra." | A word tried but not approved is silently absent from the narration. |
| H | While a narration is being made, the word page says: "A narration is being made with the words approved so far. A word approved now will not be in it." | A word approved in those minutes makes the new narration out of date the moment it arrives. |
| I | "Not in this narration yet" is decided by the approved words themselves, not by a counter. Approving a word and removing it again leaves the narration up to date. | A paid narration could be offered, and made, that would sound exactly the same. |
| J | On Narrations, a narration made before the approved words is marked "older: without the corrected words", and picking it as the final narration asks once: "This narration does not have the corrected words. Make it final anyway?" | After a fix there are two rows of the same voice; the wrong one could be made final. |
| K | The card says an approved word is remembered for this client's next films, and can be removed there. | Approving has an effect beyond this film that the page did not say. |

Looked at and left as they are:

- Two ways of asking "are you sure" (the popup on the word page, the two-click Confirm on Narrations). SK asked for the popup on the word page alone.
- Other forms of a word (a plural, a possessive) are separate words; the operator corrects each.
- Narrations in several voices: each row has its own button and each is charged in full; the question says so.

Built as listed, with these points worth knowing:

- **I** is done with a digest of the rules sent to the voice, kept on the list and on each narration. The same approved words get the dictionary they had before, so a narration asked again with nothing changed is refused as the same recording and nothing is charged. A narration or a list made before this change has no digest and is judged by the counter, as before.
- **F**: the other-case form gets a rule only when the script has it and it is not corrected on its own. On the page the two forms count as one word.
- **A**: when a newer narration of the voice already has the words, the bar points to it instead of offering a paid narration.
- **J** uses the browser's own yes/no box. **B** keeps the two-click Confirm that the page's other narration buttons use.
- **D**: the instruction text and `vw.md` still say "final" for a word; only the pages and the server's next-step line changed. The assistant may therefore say "final word" in the chat.

Where: `server/app/voices.py` (`narration_behind`, `words_digest`, `other_form`, `_rebuild`, `voice_do_next`), `server/app/jobs.py` (`same_recording`, the narration's digest), `server/app/web.py` (each narration's `behind`, the word page's `making` and `newer`), `templates/voice_words.html`, `templates/voices2.html`. Decision row 122; old-ways rows 84 to 86.

Tests, run by Claude on this PC with Python 3.12: 11 new tests in `unit-local/test_d208b.py`; all of `unit-local` 157 pass; `server/unit` 1,834 pass, none fail (one test changed: it pinned the retired wording "made before the pronunciations changed"); the plugin was not touched. Both pages were tried in the built-in browser on local copies with a stand-in server: the bar and its question (Cancel sends nothing, yes sends once, the word still being tried is named), "approved" on the try and in the list, the capitalised form counted and highlighted, the list's play buttons, one scroll bar at 1280 px; on Narrations the row's button with its note, the older mark, "Check the corrected words" on the new row, and the yes/no box before an older narration is made final.

Cannot be settled without a real voice (to try on the first film after deploy): whether the narration says an approved word as its try sounded; whether "Hear it now" finds the word in a narration made with approved words; item F.

## J. Third part: help with the spelling, and words checked before the first narration (built 16 Nov, on SK's "yes for all 4 … you can start building it")

SK asked what Alias, IPA and CMU are in the ElevenLabs application, which spelling the team should use, and whether the Google "sounds like" box could help. The application sends Alias rules only: the voice reads the spelling typed. So the spelling needs no standard; it needs to sound right in our voice.

| # | What | How it works |
|---|---|---|
| J1 | "Look it up on Google" on the word card | A link. The operator's own browser opens Google with "how to pronounce <word> in english" in a new tab. The application sends nothing and fetches nothing: Google's box cannot be shown inside our page. |
| J2 | One line on how to write a spelling | "Write it as it sounds: syllables with hyphens, the stressed one in capitals. Google shows vi · vay · **kaa** · nuhnd: type vi-vay-KAA-nuhnd." |
| J3 | Words checked before the first narration | On the Try step, under the tryouts: "Check words first", one link per voice with a ready tryout. It opens the word page for that voice (`/runs/<code>/voices2/words/v-<voice id>`). There a word is heard as the script has it ("Hear it as written", paid, the word's letters plus one), then corrected and approved as usual. The first full narration already has the approved words. |
| J4 | "Suggest spellings (free)" on the word card | Up to three spellings in the house style for the picked word, from one small text request to the server's Gemini pool. A click puts one in the box; nothing is sent to the voice until "Make the sound". They are marked as guesses. |

Edge cases and how each is handled:

| Case | What happens |
|---|---|
| The page is opened for a voice that was not tried | Refused with a line; "Back to the voices page". |
| "Hear it as written" asked twice | The second time plays the one kept; nothing is sent. |
| "Hear it as written" and then nothing else | No entry in the word list, no try counted, nothing to approve: it is listening, not a correction. |
| A word refused (not in the script, an empty spelling) | Nothing is written and nothing is sent. |
| A word list begun before the first narration | It starts from the client's remembered words, as the first narration would have started it, so they are not lost. |
| A narration without word times, opened from its row | "Hear it as written" is offered there too, beside the line that "Hear it now" is not available. |
| Suggestions: no key, the provider down, or nothing usable back | One line: "No suggestion could be made now. Type your own spelling, or look the word up." Everything else works. |
| Suggestions with phonetic symbols, the word itself, a repeat, or over 60 letters | Dropped. Only letters, hyphens, spaces and apostrophes are kept. |
| The operator picks another word while suggestions are being made | The answer is kept for its own word and shown when that word is picked again. |
| The voice stage is final | The page reads and plays; every paid button and "Suggest" is off. |

Where: `server/app/spelling_hints.py` (new), `server/app/voices.py` (`try_word` and `try_preview` with `as_written`, `suggest_spellings`, `sentence_of`), `server/app/web.py` (the action `word-suggest`, the page for `v-<voice id>`), `templates/voice_words.html`, `templates/voices2.html`. Decision row 123; old-ways rows 97 and 98. Server only; no plugin change, no migration, no instruction text change.

Tests, run by Claude on this PC with Python 3.12: 12 new tests in `unit-local/test_d208c.py`; all of `unit-local` 169 pass; `server/unit` 1,864 pass, 1 skipped, none fail. Tried in the built-in browser on local copies with a stand-in server: the page before a first narration (its header, bar and back link), "Hear it as written" with its question and its line in the tries, no approve on it, the Google link's address, the suggestions filling the box, the failure line, and "Check words first" on the Try step.

Not covered in this part:

- The suggestion request has not been sent to the real model: the model's name is the one the picture check uses (`gemini-3.8-flash`), and what it returns for Indian names is unknown until tried.
- A voice the operator "already knows" and narrates without a tryout has no "Check words first" link; it needs one tryout first.
- The chat tool has neither the suggestions nor "as written". The assistant still proposes no spelling in the chat.
- Whether a word heard alone, as written, sounds as it does inside the narration.

## G. Not covered

- The search for an earlier try (`_kept_try`) and the page's data query are SQL that only a real database runs; the unit tests use a stand-in.
- "Hear it now" was not heard with a real recording: the seek and the stop are checked with a stand-in player only.

- `server/tests` (the Docker ones) are not run.
- Nothing is tried on the live server or with a real voice before SK's deploy.
- Whether a word alone sounds the same as inside its sentence. The sentence link and the full narration remain the checks.
- The chat tool gets no "Hear it now": it cannot play sound. It keeps `vw voice pronounce`.
- The popup is not added to any other page.
