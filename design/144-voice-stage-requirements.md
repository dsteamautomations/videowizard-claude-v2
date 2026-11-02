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
4. **The server keeps one ElevenLabs pronunciation dictionary per run**, built from the list. It is replaced whenever the list changes.
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

1. Run the short paid listening test first (the five VW-16 words read by the chosen voice: as written, respelled, and in IPA), to choose respelling or IPA?
2. Keep the list per client for later films?

## Older ways (design/35)
- A narration without a pronunciation list: films narrated before this keep theirs.
- `[softly]`-style tags in the best-fit list: retired.

## Not covered
- Words the narration voice says wrongly that the assistant did not spot and the operator did not add (heard only in the narration).
- How well each IPA spelling is spoken depends on ElevenLabs; the listening test checks five words, not every language.
