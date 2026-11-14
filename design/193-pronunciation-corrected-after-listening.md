# 193 — Pronunciation, corrected after listening (design and requirements)

14 Nov 2026. Source: `design/_work/stage-fixes-VW-23.md`, voice rows 8, 10 and 16 to 19, with the eight points a to h (all decided by Deepa, 13 Nov).
Nothing here is built. This document and the mock-up are shown first, as row 18 asks. Mock-up: `design/193-assets/pronunciation-mockup.html`.

## 1. What the operator does (the control)

On the voices page, Narrations step, each narration's row has two named buttons in place of today's "Change a sentence's tag":

- **A word sounds wrong** (new)
- **A sentence's tone or pace** (today's tag control, renamed; row 10)

"A word sounds wrong" opens one panel under the narrations:

| Part | What it does | Row or point |
|---|---|---|
| The script, left | The accepted script as text. Click a word (drag across two or three for a name of several words). The word is marked in every place it appears. | 16a, c |
| This word, right | The word, how many places it appears, one box "How should it sound?" for a plain respelling such as "Man-ga-loor", the number of tries so far. | 16b, d, f |
| Hear it in its sentence | The first sentence that holds the word is read in the voice of that narration, with the respelling. A small paid request. | 16c, a |
| The word alone | A second button; the page says a word alone can sound different. | a |
| Pronunciation final for this word | Enabled after the word was heard at least once. | 16e |
| Corrected words, below | Every corrected word: the word, how it sounds, places, tries, its state, "play the last try", change, remove. | 16f |
| Narrate again with the final words | At the foot. Enabled when at least one final word is not in that voice's latest narration. The whole script, once. | 16g, b |

States a word can show: **still trying** (not used in any narration), **final**, **from this client's last film** (applied without a question, removable; point e), and beside any of them **not yet heard in this voice** (point g).

Patterns taken from Mobbin (looked at on 14 Nov):
- The rule row "word, sounds like, play, with the voice named beside it": [ElevenLabs, pronunciation dictionaries](https://mobbin.com/screens/95a24479-ff15-4d56-8d4f-6826d4efb5cc?utm_source=claude&utm_medium=ai-assistant&utm_source_platform=mcp).
- Pick the word in the text itself, and "one correction for every place": [Descript, Correct and Correct all](https://mobbin.com/screens/67f0fc60-97f2-4114-9586-c18c9068824a?utm_source=claude&utm_medium=ai-assistant&utm_source_platform=mcp).
- The script as plain readable text with marked parts: [Hume AI](https://mobbin.com/screens/d5a42861-7fc5-463a-9f70-4c0f92aba0b6?utm_source=claude&utm_medium=ai-assistant&utm_source_platform=mcp).
- A list of names with their state and an edit on each row: [Profound, name matching](https://mobbin.com/screens/1fb56316-4944-4302-b040-9d791eb7ac71?utm_source=claude&utm_medium=ai-assistant&utm_source_platform=mcp).
- Remembered words that can be removed one by one: [Voicenotes, names to remember](https://mobbin.com/screens/90a2768c-da52-4584-9c25-0f76abe574d3?utm_source=claude&utm_medium=ai-assistant&utm_source_platform=mcp).

What was deliberately not taken: a separate dictionary screen away from the script (ElevenLabs, Grammarly). The operator finds the word while listening, so the control stays beside the narrations.

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
| 1 | ElevenLabs refuses or fails a try | The try shows "failed" with the reason; the tries count is not raised; nothing changes in the list. |
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

## 8. Not covered by this design

- Whether Eleven v4 obeys a plain respelling for every word, and whether a try and a full narration sound alike: only a paid test on a real voice shows it.
- Splicing a corrected sentence into an old recording (decided against: point b).
- A shared dictionary across clients.
