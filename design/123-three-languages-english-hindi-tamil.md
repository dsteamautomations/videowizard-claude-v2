# 123 — One script, three narrations: English, Hindi, Tamil

Status: **plan with SK's six answers, 29 Oct 2026; waiting for the go-ahead to build. Nothing built.**

## The requirement, restated
The operator gives the script in English, as today, and picks one voice, as today. VideoWizard translates the script into **Hindi** and **Tamil** and narrates all three with **the same voice**. The film comes out in three languages.

## How it works today (read 29 Oct 2026)
- **Script stage:** the English script is approved word for word. Every later step checks against it.
- **Voice stage:** ElevenLabs narrates the script with the chosen voice. The model is `eleven_v4` by default; `eleven_v3` and `eleven_multilingual_v2` are also allowed. The narration comes back with a timestamp for **every character**, which becomes `timing.json`: every word with its start and end.
- **Everything after the voice is timed to that one narration.** That covers the scenes, the clip cuts, the blanks, the pictures' start on their words, the graphics' labels appearing on a word, the subtitles, and the length of the film.

Two facts that make this requirement possible without a new provider:
1. **ElevenLabs speaks Hindi and Tamil with the same voice.** Its multilingual models accept the same voice id, and the timestamps work for any script (Devanagari, Tamil), because they are per character and words are split on spaces.
2. **Translation needs no new paid service.** The server already has paid Gemini keys (Gemini 3.8 Flash for analysis). One translation of a 3-minute script costs a few rupees. Claude would also work. A dedicated service (Google Translate, DeepL) is weaker on tone and on keeping the script's structure, so it is not recommended.

## The main decision: one picture for three languages, or three films?
Hindi and Tamil are usually spoken **longer** than English for the same text, often 15–40 % longer for Tamil. The picture is timed to the English words. So the three narrations cannot simply be swapped.

**A. One film, three narrations (recommended).** The pictures are made once, timed to English as today. For Hindi and Tamil, each script paragraph's narration is fitted into that paragraph's time in the film:
- a little faster (ElevenLabs speed, up to about 10 %), and/or
- the picture holds a little longer at the end of the paragraph (the film becomes a few seconds longer in that language).

Pictures change at paragraph edges, so they stay right. Cuts **inside** a paragraph land on English words, so in Hindi or Tamil a picture may come a moment before or after its word. For most films this is acceptable.
- Cost: narration ×3, everything else ×1.

**B. Three separate films.** Each language gets its own timing, its own first cut and its own visuals.
- Every shot is exact in each language, but pictures, videos and approvals are three times over.
- Not recommended.

### How a longer Hindi or Tamil narration fits (SK's question, 29 Oct 2026)
Example: English 3:00 in six paragraphs of 30 s; Tamil comes to 3:10, so each paragraph is about 31.7 s. Fitting works **per paragraph**, in this order, stopping as soon as it fits:
1. **A translation written to length.** The translator is given each paragraph's English seconds and the language's usual speaking rate, and asked for the same meaning in about that length (shorter words, no padding). The server measures the narration; a paragraph more than 10 % over is translated again once, tighter. This usually removes most of the difference before anything is voiced twice.
2. **A little faster.** ElevenLabs' speed setting, at most 10 % (31.7 s → 30 s here). Beyond about 10 % it sounds rushed, so it stops there.
3. **The picture holds a little longer.** What is still over (for example 2 s) is added at the end of that paragraph: the last picture of the paragraph stays on screen 2 s longer (a still or a graphic simply holds; a video's last frame holds, or it is slowed slightly). That language's film is then a few seconds longer than the English one: 3:02 instead of 3:00. The English film is never changed.

So the 3:10 Tamil narration becomes, say, a 3:00–3:03 Tamil film with every paragraph's pictures still under their own words. The limit: within a paragraph, a picture timed to an English word may arrive a moment before or after the matching Tamil word.

A shorter narration (Hindi is sometimes shorter) is fitted the other way: a little slower (at most 10 %), then a short silence at the paragraph's end.

## On-screen words
Titles, labels in diagrams, and the exact text in pictures are in English today.
- **Keep them English in all three films (recommended for now).** No extra pictures; the narration and subtitles carry the language.
- **Or translate them:** every picture or graphic with words is made three times (drawn graphics re-render free; AI pictures with text are paid again and re-approved).

## The stages
1. **Start of the run:** a new choice, `languages` (`en` alone, or `en+hi+ta`), stored on the run like the image model.
2. **Script stage (English, unchanged).** After the English script is approved:
   - **Translation:** one paid Gemini call per language. It keeps every paragraph and its id, keeps the voice-direction tags as they are, and keeps the glossary words as told (below). The server checks that every paragraph came back and that no tag was lost or added.
   - **Glossary**, asked once per run: brand names, place names and technical terms ("rat-trap bond", a product name), with how each is said in Hindi and Tamil (kept in English, or transliterated).
   - **Approval of each translation by a person who reads it.** The operator may not read Tamil. *Decision:* who approves, and whether a page shows the English and the translation side by side, paragraph by paragraph.
3. **Voice stage:** the same voice, the same direction, narrates each language.
   - The model must support Hindi and Tamil; the server checks this from ElevenLabs' model list before narrating.
   - Each language gets its own audition sample first, because a voice that is good in English may carry an accent in Tamil. The operator approves each language's sample (or picks another voice for that language: *decision*).
   - Each language gets its own `timing.json` and narration file.
4. **Options to visuals:** unchanged, on the English narration.
5. **Fitting (new, after visuals):** for each language, each paragraph is fitted into its English time as in A above, and the film timing per language is written.
6. **Assembly and delivery:** three films (English, Hindi, Tamil), three subtitle files, and the editor's package with the three narration tracks.

## Edge cases and failure modes
- **A paragraph far longer in Tamil** (more than about 10 % faster can fit): the picture holds at the paragraph's end; the film is longer in Tamil. Above a limit (say 25 %), the server flags the paragraph so the translation can be made shorter.
- **The English script changes after translation:** the translations become stale and are redone; the old narrations are not reused.
- **A word that must not be translated** (a brand, a measurement unit): the glossary; the server checks that each glossary word appears as told.
- **Numbers and units:** the translation keeps the numerals and the units as in English, unless the glossary says otherwise.
- **Voice-direction tags** (pauses, emphasis): kept in place; the server refuses a translation that loses or adds one.
- **The voice cannot speak Tamil well:** caught at the audition, before the paid full narration.
- **Silence and pauses** inside a paragraph differ by language: fitting is per paragraph, so a different pause does not drift the film.
- **Subtitles:** made from each language's own timing, so they match what is heard.
- **Cost:** ElevenLabs bills per character; Hindi and Tamil text is often longer in characters, so the narration cost is about three to four times today's.
- **A run in English only:** unchanged.

## Not covered by this plan
- Languages other than Hindi and Tamil (the design allows them later; the plan names only these two).
- Translated on-screen text, unless SK decides otherwise.
- Lip-sync for people speaking to camera in the footage: their own voice and language stay as recorded.

## Open decisions for SK (one at a time)
1. ~~One film or three?~~ **Answered (SK, 29 Oct 2026): A, one film with three narrations**, fitted per paragraph (translate to length, at most 10 % faster or slower, then the picture holds or a short silence).
2. ~~On-screen words?~~ **Answered (SK, 29 Oct 2026): English in all three films**; narration and subtitles carry the language.
3. ~~Who approves the translations?~~ **Answered (SK, 29 Oct 2026): the operator, on a page that shows each English paragraph beside its Hindi and Tamil**, approving each language with one click (an edit per paragraph allowed; the server re-checks tags and glossary words after an edit). The chat path records the same approval with the operator's words (one flow, two front ends).
4. ~~Translation service?~~ **Answered (SK, 29 Oct 2026): Gemini**, through the server's existing key pool (design/114), one paid call per language, announced to the operator.
5. ~~Same voice always?~~ **Answered (SK, 29 Oct 2026): the same voice by default; when a language's test recording is poor, the operator may pick another voice for that language** (recorded per language with the operator's words; the other languages keep theirs).
6. ~~Every run or chosen?~~ **Answered (SK, 29 Oct 2026): chosen at the start of each run**, with the other first questions (design/122's material question first, then languages, then the image model, then the client): English only, or English + Hindi + Tamil; stored on the run, never changed.

**All six answered. The plan is ready for SK's go-ahead to build.**

## The start questions, as the operator reads them (SK, 29 Oct 2026: "picture AI" is too broad)
Asked in this order, one message each, before the run is created:
1. **What do you have from a real shoot?** Video and photos / Photos only (not available yet) / Nothing: the whole film is made by AI.
2. **Which languages should the film be narrated in?** English only / English, Hindi and Tamil.
3. **Which AI should draw the film's still images?** These are the pictures the AI makes: the reference picture of each person, object and place, the first and last frame of every AI video clip, and the still shots and diagrams. The same AI is used for the whole film and cannot be changed later. GPT Image (OpenAI) / Nano Banana (Google Gemini). *(AI video clips, the voice and translation are separate and not affected.)*
4. **Which client is this film for?**

The chat tool's refusal when the image choice is missing changes to the same wording as question 3 (it says "image model" today).
