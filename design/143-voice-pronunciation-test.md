# design/143: Indian words in the narration, a dry run on VW-16's script (2 Nov 2026, for SK, before any requirement or code)

SK, 2 Nov 2026: after the operator chooses among the voices and before the full narration, the assistant finds every word that is not plain English (abbreviations, names of people and places, words tied to one region, local words written in English letters), converts each to how it should be said, and passes that to ElevenLabs. It tells the operator in **one** message, which they can accept as it is or answer with more words to add. They are never asked twice.

Test asked for: take a script already made and let the assistant find the words and propose them. Script used: VW-16 (filler slab roofs, Vivekananda Kendra NARDEP, Kanyakumari), 671 words, narration language `en`, read from the server.

## What the assistant found

| Word as written | Kind | How it should be said (spelt for an English voice) | IPA (the exact sounds) | Where |
| --- | --- | --- | --- | --- |
| Mangalore (tiles) | place, and a regional product named after it | **MUNG-guh-lore** | /ˈmʌŋɡəlɔːr/ | paragraphs 2 and 4 (twice) |
| Kanyakumari | place | **kun-yaa-KOO-muh-ree** | /kənjaːˈkuməɾi/ | the demonstration paragraph |
| Vivekananda | name of a person (the organisation is named after him) | **vi-vay-KAA-nun-duh** | /ʋiʋeːˈkaːnəndə/ | the demonstration paragraph |
| Kendra | Hindi word, part of the organisation's name | **KAYN-druh** | /ˈkeːndrə/ | the demonstration paragraph |
| NARDEP | abbreviation (Natural Resources Development Project) | **NAR-dep**, said as one word, *or* **N-A-R-D-E-P** letter by letter: the client decides | /ˈnɑːrdɛp/ | the demonstration paragraph |

**Left alone, on purpose:** English words with Indian or British spelling ("multi-storeyed", "levelling", "centre") are said the same either way. "Filler slab", "shuttering" and "country tiles" are building-trade English, and an English voice says them correctly.

## The one message the operator would see

> Before the full narration, I checked the script for words an English voice may say wrongly. I will have them said like this:
> - **Mangalore** (tiles): MUNG-guh-lore
> - **Kanyakumari**: kun-yaa-KOO-muh-ree
> - **Vivekananda**: vi-vay-KAA-nun-duh
> - **Kendra**: KAYN-druh
> - **NARDEP**: said as one word, NAR-dep (tell me if the client spells it out letter by letter)
>
> Reply **yes** to go ahead, or tell me any other words to add (and how they are said, if you know); I'll include them and start the narration.

One question, answered in one reply: a "yes" accepts all of them; any other words in the reply are added and the narration starts. The operator is never asked to confirm a list and then asked again for additions.

## What this dry run shows

1. **The finding works on this script.** Five words, all of the kinds SK named: places, a person's name, a local word and an abbreviation. Nothing English was flagged by mistake.
2. **One item needs the operator's knowledge, not a guess:** whether an abbreviation is said as a word or letter by letter. The message says the assistant's guess and invites the correction in the same reply.
3. **VW-16 is a light case.** A script in Tamil or Hindi, or one full of local names, would give many more words. The step has to stay one message even with twenty words, so the list is grouped by kind and shown compactly.

## Still to find out before the requirements

- **How ElevenLabs takes the pronunciation for Eleven v4.** It has two ways: a spelling replacement (the voice reads "MUNG-guh-lore" instead of "Mangalore"), which works with every model; and exact sounds (IPA), which only some models accept. Which one v4 honours must be checked against ElevenLabs' current documentation, then heard in a short paid test: the five words above, read by the chosen VW-16 voice with and without the change. That test is about a sentence each, a few rupees.
- **Where the list is kept:** with the run (and offered again to the client's next film, since place and organisation names repeat), so the narration, a re-narration and the next film all use it.

## Listening test (2 Nov 2026, SK: "Yes, run the test")

- **Voice:** VW-16's narration voice, Reyaansh (`emceOb89ymaMozXE8Kfw`), on Eleven v4 at 0.5 / 0.75.
- **Sentences:** two from the script.
  - s1, Mangalore: "Suitable filler materials include Mangalore tiles, hollow clay blocks or even coconut shells."
  - s2, Vivekananda, Kendra, NARDEP, Kanyakumari: the demonstration sentence.
- **Three readings of each:** as written; respelled in the text; IPA written inline between slashes. That makes six clips, about 900 characters.
- **The clips** are in `C:\Coworkspace\Review Videobuilder Tool\voice-test-143\`, kept outside the repository.

**Found:** the dictionary route could not be tried. The server's ElevenLabs key lacks the permission `pronunciation_dictionaries_write`, and ElevenLabs refused with that reason. So the test wrote the pronunciation into the text itself, which sounds the same as a dictionary rule but cannot be built that way: the respelling would then appear in the timing and the subtitles. Building the dictionary route needs that permission switched on for the key, in ElevenLabs' settings, by the account owner. The six clips differ, so the voice did read each version differently. Which sounds right is SK's call by ear.

## Listening test, the dictionary route (2 Nov 2026, after SK switched on the key's dictionary permission)

- **Dictionaries:** two, made on the account: `vw2-design143-test-alias` (respelling rules, id RMfngYLiyWMBQEZ7YYHa) and `vw2-design143-test-phoneme` (IPA rules, id DzEA0jdBZbrkB59kP9Up).
- **What was read:** the same two sentences as written, each with one dictionary, giving four more clips: `s1-dict-alias`, `s1-dict-phoneme`, `s2-dict-alias`, `s2-dict-phoneme`, in the same folder.
- **Result:** ElevenLabs took both dictionaries on Eleven v4 without refusal. All four clips differ from each other and from the plain readings, so the rules were applied. Which reading is right is SK's call by ear.
- **The two test dictionaries stay on the account.** They are small and named as tests. Remove them on request.
