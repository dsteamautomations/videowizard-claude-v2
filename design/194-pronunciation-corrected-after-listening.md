# 194 — Pronunciation, corrected after listening (design and requirements)

14 Nov 2026. Source: `design/_work/stage-fixes-VW-23.md`, voice rows 8, 10 and 16 to 19, with the eight points a to h (all decided by Deepa, 13 Nov).
Nothing here is built. This document and the mock-up are shown first, as row 18 asks. Mock-up: `design/194-assets/pronunciation-mockup.html`.

## 1. What the operator does (the control)

On the voices page, Narrations step, each narration's row has two named buttons in place of today's "Change a sentence's tag":

- **A word sounds wrong** (new)
- **A sentence's tone or pace** (today's tag control, renamed; row 10)

"A word sounds wrong" opens one panel that slides in from the right side of the page (SK, 14 Nov: a floating side panel, not a section inside the page). It takes about a third to half of the screen; the narrations and their play buttons stay visible and usable on the left, so the operator can play the narration again while correcting. It closes with its × or the Escape key; nothing typed is lost by closing. On a narrow screen it takes the full width. Inside, the parts stack from top to bottom:

| Part | What it does | Row or point |
|---|---|---|
| The script, at the top | The accepted script as text. Click a word (drag across two or three for a name of several words). The word is marked in every place it appears. | 16a, c |
| This word, under it | The word, how many places it appears, one box "How should it sound?" for a plain respelling such as "Man-ga-loor", the number of tries so far. | 16b, d, f |
| Hear it in its sentence | The first sentence that holds the word is read in the voice of that narration, with the respelling. A small paid request. | 16c, a |
| The word alone | A second button; the page says a word alone can sound different. | a |
| Pronunciation final for this word | Enabled after the word was heard at least once. | 16e |
| Corrected words, below | Every corrected word: the word, how it sounds, places, tries, its state, "play the last try", change, remove. | 16f |
| Narrate again with the final words | At the foot of the page, visible whether the panel is open or closed. Enabled when at least one final word is not in that voice's latest narration. The whole script, once. | 16g, b |

States a word can show: **still trying** (not used in any narration), **final**, **from this client's last film** (applied without a question, removable; point e), and beside any of them **not yet heard in this voice** (point g).

Patterns taken from Mobbin (looked at on 14 Nov):
- The rule row "word, sounds like, play, with the voice named beside it": [ElevenLabs, pronunciation dictionaries](https://mobbin.com/screens/95a24479-ff15-4d56-8d4f-6826d4efb5cc?utm_source=claude&utm_medium=ai-assistant&utm_source_platform=mcp).
- Pick the word in the text itself, and "one correction for every place": [Descript, Correct and Correct all](https://mobbin.com/screens/67f0fc60-97f2-4114-9586-c18c9068824a?utm_source=claude&utm_medium=ai-assistant&utm_source_platform=mcp).
- The script as plain readable text with marked parts: [Hume AI](https://mobbin.com/screens/d5a42861-7fc5-463a-9f70-4c0f92aba0b6?utm_source=claude&utm_medium=ai-assistant&utm_source_platform=mcp).
- A list of names with their state and an edit on each row: [Profound, name matching](https://mobbin.com/screens/1fb56316-4944-4302-b040-9d791eb7ac71?utm_source=claude&utm_medium=ai-assistant&utm_source_platform=mcp).
- Remembered words that can be removed one by one: [Voicenotes, names to remember](https://mobbin.com/screens/90a2768c-da52-4584-9c25-0f76abe574d3?utm_source=claude&utm_medium=ai-assistant&utm_source_platform=mcp).

What was deliberately not taken: a separate dictionary screen away from the script, and a dialog in the middle of the screen (ElevenLabs, Grammarly). The operator finds the word while listening, so the panel sits beside the narrations and never covers their play buttons.

## 2. What changes underneath

| # | Change | Where |
|---|---|---|
| 1 | **Row 8.** The pronunciation list becomes part of what identifies a stored recording. A changed list gives a new recording; an unchanged list still reuses the store. A recording stored before this change (no list) keeps its identity, so nothing already paid for is paid again. | `narration_pieces.piece_identity` |
| 2 | One list of words per run, each word with its state (trying, final), its tries and the voices it was heard in. Only final words are in the dictionary a narration uses. The list's version rises when the final words change. | `voices.py` (the run's `pronunciations.json`) |
| 3 | **Hear it.** One server function: the sentence (or the word alone) is read in the given voice with the respelling in place of the word. It is a small paid job like a tryout; its audio is kept so "play the last try" costs nothing. | `voices.py`, `jobs.submit_voice` |
| 4 | **Final / change / remove** a word: one server function each, used by the page and by the chat. | `voices.py`, `web.py`, `main.py` |
| 5 | **Point e.** At a run's first narration, when the run has no list yet, the final words of the client's last film are copied in (state "from this client's last film") and used without a question. The page lists them; each can be removed. | `voices.narrate`, `last_client_list` |
| 6 | **Row 17.** The pronunciation question before the first narration is removed from the assistant's instructions. | `plugin/commands/vw.md` |
| 7 | **Chat front end** (one flow, two front ends): `vw voice pronounce` gains `--word`, `--say`, `--hear --voice ID`, `--final`, `--remove`; with no flags it shows the list. | `plugin/scripts/vw.py` |
| 8 | **Point h.** After the final narration is chosen, hearing, changing and narrating are refused until the voice stage is reopened (the check built for row 13). | `voices.refuse_after_final` |
| 9 | The voices page's "final" mark follows the stage: after a reopen it no longer shows the old final. | `web._voices2_state` |

How a try is made (a choice to confirm): for a try, the respelling is written into the sentence in place of the word and that text is sent. No dictionary is created per try, so tries leave nothing behind on the ElevenLabs account. The full narration keeps using a dictionary (as today), because its timing must match the accepted words. A respelling rule in a dictionary does the same replacement, so the try and the narration should sound alike; this is not tested yet, and the operator hears the result either way.

## 3. Unstated but expected

1. The same server functions serve the page and `vw` (working rule).
2. The accepted script is never changed; a respelling is only how a word is said.
3. Words still being tried never reach a narration.
4. Every paid step says so before the click, with its size (one sentence; the whole script).
5. The log gets one line per try (word, respelling, voice), per final, per removal.
6. Each change states its older way (section 6) and gets a row in `design/35-decision-log.md`.
7. Examples in texts and messages suit every category of video.
8. `plugin/` stays Python 3.9 compatible; files keep their line endings.
9. The typed respelling is shown as text only, never as page code.

## 4. Edge cases

| # | Case | Handling |
|---|---|---|
| 1 | The word appears several times | One correction; every place uses it. The sentence heard is the first one that holds it. (point c) |
| 2 | The same word in two spellings or capitals ("Kendra", "KENDRA") | Each spelling is its own entry; the page shows the places of each. |
| 3 | A name of several words | Picked by dragging; kept as one entry; it must be next to each other in the script. |
| 4 | A word that is part of a longer corrected name | The longer entry is applied first (as today's rule: longer words first). |
| 5 | The word typed in the chat is not in the script | Refused: "that word is not in the script". |
| 6 | Empty respelling, or the respelling equals the word | Refused before any paid request. |
| 7 | The same respelling heard again | The kept audio is played; no new request. A changed respelling is a new try. |
| 8 | Hearing a word in a voice with no narration yet | Allowed for any voice tried or narrated in this run. |
| 9 | A final word changed again | It goes back to "still trying"; narrations keep the last final version until it is final again. |
| 10 | A second voice after corrections in the first | The final words apply; each shows "not yet heard in this voice" until heard there. (point g) |
| 11 | Narrate again with no change in the final words | Refused as "nothing changed" (voice row 1). |
| 12 | Final words changed, narration asked | Allowed; a new recording (row 8). Older narrations show "made before the pronunciations changed", as today. |
| 13 | A long script in pieces | Every piece is recorded again when the list changes; one more paid narration. (point b) |
| 14 | A client's remembered word that is not in this script | Listed as "not in this script"; it costs nothing and can be removed. |
| 15 | Removing a client's remembered word | Removed for this film only; the client's earlier films are not touched. |
| 16 | The client's last film has no list | Nothing is copied; no question. |
| 17 | After the final narration | Everything in the panel is refused with "reopen the voice stage first". (point h) |
| 18 | Two computers on the same run | The run's lock makes one change at a time; the page reloads the list after each action. |
| 19 | IPA | Still accepted from the chat (`--ipa`); never asked for. (point d) |
| 20 | No direction recorded, or direction "none" | The try reads the plain sentence; with a direction, the sentence carries its tag. |
| 21 | A run with a list made the old way (design/144) | Its words count as final; nothing is lost. |

## 5. Failure modes

| # | Failure | Handling |
|---|---|---|
| 1 | ElevenLabs refuses or fails a try | A try refused before it is sent changes nothing and is not counted. A try that fails after it was sent shows "failed" with the reason and stays counted. |
| 2 | The dictionary cannot be made when a word is made final (key without the permission, provider down) | The word stays "still trying"; the message says why; narrations keep the earlier list. |
| 3 | The voice does not obey the respelling | The operator hears it and types another; no limit, the tries are counted. If no respelling works, the word can be removed and the script changed at the script stage. |
| 4 | The try sounded right but the narration sounds different | Possible (section 2, last paragraph). The operator corrects again and narrates again; each narration is kept. |
| 5 | A try's audio is missing from storage | "Play the last try" says so and offers to hear it again (a new paid try). |
| 6 | The copy of the client's words fails at the first narration | The narration goes ahead without them and the page says the client's words could not be read. |

## 6. Older ways

| What | After this change |
|---|---|
| The word list written by the assistant before the first narration, one question, `vw voice pronounce --file --quote` | Retired: the question is removed; `--file` is refused by name with the new way. A list recorded this way on an open film stays in force. |
| A stored recording identified without its pronunciation list | Retired (row 8). |
| "Change a sentence's tag" as the only control on a narration | Kept, renamed "A sentence's tone or pace". |
| The client's last list offered to the assistant "to start from" | Retired: the final words are applied at the first narration and shown on the page. |

## 7. Tests (unit tests, written first)

Stored-recording identity with and without a list; the list's states and versions; a try's text with the respelling in place (first sentence, word alone, several words, with a tag); refusals (not in the script, empty, after the final); the kept audio for a repeated try; the client's words copied once; the chat flags; the page's data and the panel's code; the removed question in the instruction text.

## 8. Built, 14 Nov 2026 (SK: "Approved, build it")

Everything in sections 1 and 2 is built on branch `worktree-stage-fixes-vw23`. Not merged, not deployed.

**Tests (run by Claude on this computer, Python 3.12; unit tests only, by SK's word).** New: 35 tests in `unit-local/test_d194.py` (not in git), all pass, with the 87 of design/192: 122 pass. Existing `server/unit` and `plugin/tests`: the same failures as before this build (the 4 and 7 that failed before any of this work, and 2 in the analysis tests that came with `main`'s design/193). Two existing tests were changed because they pin what is retired: the old `--file` list (`plugin/tests/test_design142.py`) and the old control's name (`server/unit/test_design144_voice_pure.py`). The page was tried in a browser on a local copy with a stand-in server (no network, no sound): open the panel, pick a word, the empty-box refusal, hear, final, narrate again, remove, Escape.

**Review for effects on existing flows.** Found and fixed: a word's try would have been counted as an audition of the voice in the usage lists; it would have been read as the voice's latest tryout on the Try step and for the narration's settings. Remaining, by design:
- A narration job that carries a pronunciation list and is waiting to be stored at the moment of the deploy would not find its stored pieces (their identity now includes the list). Deploy when no voice job is open.
- A film of a client whose earlier film has a pronunciation list gets those words at its next first narration without a question (point e), also films already open at the deploy.
- `GET …/voice/pronunciations` answers the words with their states; `client_last` is gone. `POST …/voice/pronunciations` answers `RETIRED`.
- A try is counted when it is submitted; a try the provider fails afterwards stays counted and shows "failed".

**Not covered.** `server/tests` (Docker) not run; `test_voice_media.py` and any test that posts the old list will need new expectations. Nothing was tried with a real voice or on the live page. Python 3.9 is not installed here. Dragging to pick several words was tried only as code, not by hand. A name of several words is not marked in the script after it is picked (only single words are).

## 9. Not covered by this design

- Whether Eleven v4 obeys a plain respelling for every word, and whether a try and a full narration sound alike: only a paid test on a real voice shows it.
- Splicing a corrected sentence into an old recording (decided against: point b).
- A shared dictionary across clients.
