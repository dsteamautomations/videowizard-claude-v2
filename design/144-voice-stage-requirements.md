# design/144: voice stage, Indian-word pronunciation and the direction feedback from VW-16 (2 Nov 2026, requirements for SK's approval)

Sources:
- SK's pronunciation request (design/143, with the dry run on VW-16's script);
- the operator's VW-16 voice-direction feedback (2 Nov).

Nothing is built. Every change works for any film, category and narration language.

**What ElevenLabs offers (checked 2 Nov 2026 against their current documentation).** Eleven v4 takes pronunciation dictionaries, up to three per request. A dictionary holds rules of two kinds:
- **alias** rules, a respelling: "Mangalore" is read as "MUNG-guh-lore";
- **phoneme** rules, exact sounds in IPA.

v4 also reads inline IPA. Older ElevenLabs pages still say phoneme rules work only on Flash v2, so a short paid listening test settles it before the build (question 1).

Sources:
- [Using pronunciation dictionaries](https://elevenlabs.io/docs/eleven-api/guides/how-to/text-to-speech/pronunciation-dictionaries)
- [Pronunciation dictionary guide](https://elevenlabs.io/blog/pronunciation-dictionary-guide)

---

## V1. A pronunciation step before the full narration (SK, design/143)

**Requirement**
1. **When.** After the operator has chosen the voices to narrate (the voices page's Try step, or the chat's auditions) and before the first full narration, the assistant reads the accepted script and lists every word a voice may say wrongly:
   - abbreviations;
   - names of people, places and organisations;
   - words tied to one region;
   - local words written in the script's letters.
   Each comes with how it is said (a respelling, and IPA).
2. **One message, one answer.** The operator sees the list and one question: "Reply yes to go ahead, or tell me any other words to add (and how they are said, if you know); I'll include them and start the narration." Their reply both accepts the list and adds to it. There is no form on the page and no second question.
3. **Recorded on the server with their words:** `vw voice pronounce --file out/pronunciations.json --quote "<their words>"`. The file holds `[{word, say_as, ipa, kind}]`.
4. **The server keeps one ElevenLabs pronunciation dictionary per run**, built from the list. It is replaced whenever the list changes. **The rule per word follows SK's choice (2 Nov, after the listening test):**
   - names, places and local words get an IPA (phoneme) rule, the exact sounds;
   - abbreviations and acronyms get a respelling (alias) rule: "NAR-dep" when said as a word, "N A R D E P" when spelt out.
   - ElevenLabs applies one rule per word, the first that matches, so longer words are listed first.
   - The list carries both forms for every word, so a word may switch kind if the operator says it still sounds wrong.
5. **Every narration made after that carries the dictionary**, on the page and in chat (one flow, two front ends: in `voices.narrate`). So do re-narrations and auditions made after the list.
6. **On the page,** the Narrations step shows the list ("5 words said as recorded"). Each narration says whether it used the list, and which version.
7. **Kept for the client's next film:** the list is offered as the starting point (like the last brief), and the operator confirms it in the same one message.

**Unstated but expected**
- When nothing is found, the message says so and still invites additions, in one message.
- Narration in another language (Hindi, Tamil): the step looks for words that are not in the narration's language, plus abbreviations and names. The rules are the same.
- A long list (twenty words or more) is grouped by kind, still in one message.

**Edge cases**

| Case | Handling |
| --- | --- |
| The operator adds a word without saying how it sounds | the assistant proposes the sound; the reply already counts as approval, and the operator hears it in the narration |
| A word that appears inside another word ("Kendra" inside "Kendrapara") | rules match whole words only; the dictionary is checked from the start and only the first match applies, so the longer word is listed first |
| A wrong sound heard in a narration | the operator says so in chat; the list is corrected, recorded with their words, and the next narration uses it |
| ElevenLabs refuses to create the dictionary | the narration is refused with ElevenLabs' reason, never made silently without the list |
| A narration made before the list changed | marked on the page: "made before the pronunciations changed" |
| A word the voice already says right | the assistant leaves it out; the operator can add it |

**Tests**
1. The record keeps the list with the words.
2. A narration request carries the dictionary; one before the list carries none.
3. A changed list makes a new dictionary and marks the older narrations.
4. Refused without the operator's words.
5. A refused dictionary refuses the narration.
6. The client's last list is offered on the next film.
7. Wording test: one message, one question.

---

## V2. Direction tags that make a deep voice breathy (operator, VW-16)

**What happened.** On a deep voice (Reyaansh, Eleven v4), the tags `[quietly proud]` and `[softly]` made two sentences husky across several narrations. Re-recording the direction with `[confident]` and `[warm]` fixed it. The direction instruction offers exactly these tags: its vocabulary lists `[quietly proud]`, `[softly]` and `[lower, thoughtful]`.

**Requirement:** the direction instruction (`v3.json`, voice stage, `direction_prompt`) says:
- Tags that lower the volume (softly, quietly, lower, whispered) can make a deep or low voice breathy or husky.
- For a deep voice, use attitude and pace instead (confident, warm, thoughtful, unhurried, measured).
- Volume-lowering tags belong only in the experimental list, with that note shown to the operator.
- `[quietly proud]`, `[softly]` and `[lower, thoughtful]` leave the best-fit vocabulary.

The old wording goes on the retired list.

**Test:** a wording test.

---

## V3. Which direction a narration used (operator, VW-16)

**Today.** The page already marks a narration "made before the direction changed", but not which direction it used, so the difference was not obvious.

**Requirement**
- Each recorded direction gets a number: direction 1, 2, 3.
- Each narration row says "direction 2" (and "made before the direction changed" when it is older).
- The chat tool's narration answer names the direction number too.

**Test:** the number is kept and shown.

---

## V4. The sentence-tweak control, findable from chat (operator, VW-16)

**Today.** The control is a "⋯" on each narration row, and nothing in the chat tool says where it is.

**Requirement**
- The control reads **"Change a sentence's tag"**.
- The tool's narration answer ends with: "To change one sentence's tag for this voice: voices page, Narrations step, the narration's row, 'Change a sentence's tag' (or `vw voice tweak --voice ID --file …`)."

**Test:** the answer carries the line; the page label (a syntax check of the page script).

---

## Questions for SK (one at a time in chat)

1. ~~Respelling or IPA?~~ **Answered (SK, 2 Nov): the combination**: IPA for names, places and local words; a respelling for abbreviations. The listening test (design/143) showed Eleven v4 takes both dictionary kinds; the server key now has the dictionary permission.
2. ~~Keep the list per client?~~ **Answered (SK, 2 Nov): yes, offer it.** The client's next film starts from the last list; the assistant adds the new script's words, in the same one message.

All questions answered; the requirements wait for SK's approval before any code.

## Older ways (design/35)
- A narration without a pronunciation list: films narrated before this keep theirs.
- `[softly]`-style tags in the best-fit list: retired.

## Not covered
- Words the narration voice says wrongly that the assistant did not spot and the operator did not add (heard only in the narration).
- How well each IPA spelling is spoken depends on ElevenLabs; the listening test checks five words, not every language.

## Build record (2 Nov 2026, after SK's "Approve, start build")

Built, tested and pushed (commit 6d27ee2); **not deployed**. Server 0.85.0, plugin 0.71.0; the minimum plugin version stays 0.70.0 unless SK raises it.

- **V1, the pronunciation list:**
  - `voices.set_pronunciations` builds the ElevenLabs dictionary from the list (IPA for names, places and local words; a respelling for abbreviations; longer words first) and saves `<run>/voice/pronunciations.json` with its version and SK's words.
  - Narrations made before a change are marked.
  - `jobs.submit_voice` puts the dictionary on every narration and audition made after the list, on both front ends, and `elevenlabs.synthesize` sends it as `pronunciation_dictionary_locators`.
  - The API is `GET/POST /api/runs/{run}/voice/pronunciations`; the GET also returns the client's last list. The tool command is `vw voice pronounce`.
  - The voices page shows the list on the Narrations step.
  - The one-message wording is in `plugin/commands/vw.md`.
- **V2:** `scripts/d144_wording_v3.py` takes the volume-lowering tags out of the direction vocabulary and adds the deep-voice warning. The old line is on the retired list.
- **V3:** each recorded direction has a number. Each narration row shows "direction N" and "pronunciations N", and is marked when it was made before the pronunciations changed. The chat narration answer gives the direction number.
- **V4:** the page control reads "Change a sentence's tag", and the chat narration answer carries the hint.

**Tests:**
- Server: 1106 passed.
- Plugin: 406 passed, with the 4 known failures.
- The voices page script was checked for syntax in a browser.

**Not covered:**
- A real narration with the dictionary through the worker; the listening test covered the ElevenLabs side.
- The page seen live.
- VW-16's voice stage is already recorded, so the new step applies to it only if its voice is revised. New films get it at their voice stage.
