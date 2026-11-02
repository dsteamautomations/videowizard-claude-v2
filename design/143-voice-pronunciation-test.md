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
