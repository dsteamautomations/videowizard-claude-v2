# 51 — The Voices page, the voice questions, and Eleven v4 delivery direction (specified 18 Oct 2026 during the VW-4 live run; NOT approved for building; nothing executed)

SK's instructions (18 Oct 2026): the full-page option; check the account's voice limits through the API; read what Eleven v4 can do (emotion on a word or a phrase) and plan a step where, after the voice is chosen, the assistant proposes the emotions it intends to add, the operator agrees, and the narration is made with them. Supersedes design/49 V1, V2 and V5; V3 and V4 stay as small fixes.

## A. What is confirmed from the provider's documentation (read 18 Oct 2026)
- **How we connect.** The server talks to ElevenLabs over its HTTP API with the key held in `server/.env` on the VM (`elevenlabs.py`, httpx). No MCP. Everything below is reachable the same way.
- **Audio tags.** Delivery is directed with tags in square brackets inside the text: `[whispering]`, `[softly]`, `[measured]`, `[thoughtful]`, `[slowly]`, `[sighs]`, `[pause]`, `[long pause]`, and any natural-language description such as `[lower, thoughtful]` or `[gradually building energy]`; there is no fixed list. Rules from the provider: put the tag **before the words it affects**; a tag applies to a word, a phrase or a whole line and **carries forward across the line until the next tag**; one tag per clause; combine cues with commas inside one bracket (`[whispering, playful]`), never contrasting cues on the same words; parentheses or braces may be read aloud, only square brackets are tags. Tags work on `eleven_v4`, `eleven_v4_turbo` and `eleven_v3`, through the API and the app. Punctuation also directs: ellipses slow, dashes cut off, capitals and exclamation marks add intensity.
- **What v4 does not have.** No SSML, no `<break>` tags, no speed or style sliders: stability and similarity only (lower stability, more expressive). Pacing is directed with tags (`[slowly]`, `[rushed]`).
- **Caveats stated by the provider.** Tags are "not perfect yet"; how reliably a voice follows them varies by voice (tags that fit the voice's training work better); accent tags are experimental; test with the chosen voice before production; generate more than once when consistency matters; remove leftover direction in post.
- **Limits.** 10,000 characters per request on v4 (our pieces split already respects the model's limit); 90+ languages.
- **Timestamps.** The narration already runs on `eleven_v4` through the with-timestamps endpoint (VW-3 was narrated on v4 with timing), so character alignment is available. **Not documented anywhere: whether the bracketed tag characters appear in the alignment arrays.** This decides the integration (section E) and is verified by one small paid request before building, never assumed.
- **Account limits.** Custom voice slots per plan: Free 3, Starter 10, Creator 30, Pro 160, Scale and Business 660. **Voices saved from the Voice Library do not use custom slots.** Adding and editing voices draws on a monthly operations quota (Free 55, Starter 65, Creator 95, Pro 290, Scale 1040). The subscription endpoint answers `voice_limit`, `voice_slots_used`, `voice_add_edit_counter`, `max_voice_add_edits`, `character_limit` and `character_count`. SK counts 54 custom voices today, so the plan is at least Pro. The tool can add a library voice (`vw voice add-library`); it cannot remove one.

## B. The Voices page (the full option)
A page on the server's site, signed in as today, opened for a run: `/runs/<code>/voices`.

| Part | What |
|---|---|
| Account line | the plan's slots used and free, the month's add/edit operations used, the characters used this period (from the subscription endpoint; read live, cached a minute) |
| Filters | language, accent, gender, age, use case, search text, scope (library by default, account, both); a page of 20 at a time with "more"; the filters the assistant recommended in chat are passed in the link and pre-set |
| Rows | name, labels (accent, gender, age, use case, descriptive), the description cut to two lines, **play** (the provider's own preview sample, streamed from its public link; nothing stored on our side), "on the account" mark, shortlist checkbox |
| Shortlist | up to six voices; a library voice is added to the account when auditioned (no custom slot used; one add operation each); a "release" action removes a library voice from the account again (new provider call; never a custom voice) |
| Audition | one button, paid: the run's audition excerpt (the assistant's chosen passage from chat when there is one, else the server's default: the first passage of 45 to 70 words) in every shortlisted voice, on Eleven v4 at 0.5 / 0.75; the same job path as `vw voice audition`; results appear on the page with a player each, streamed from the run's storage; the characters each audition costs are shown before the click |
| Choose | "Choose this voice" on a row or an audition result; recorded on the run as `voice/choice.json` in storage: voice id, name, model, settings, by (the signed-in operator), at, and which auditions had been heard on the page; one choice at a time, a new choice replaces it |
| Hand-back | the assistant sees the choice at its next call (`vw stage voice prepare`, `vw voice jobs`, `vw next` answer `voice_choice`), says "you chose <name> on the voices page at <time>", and continues: the delivery direction step (section D), then narration |

Nothing is downloaded or kept on our server for browsing: the provider hosts a preview sample for every voice and serves it from a public link, and new voices appear as the provider adds them. What we keep are the run's own auditions and narrations, as today.

## C. The chat path (when the operator does not open the page)
On "compare", the assistant asks **one question per message**, recommendation first with its reason from the brief (tone, audience, message), and waits: gender; age group; accent (language and accent are different things; never inferred from the client's name); register (warm, authoritative, conversational, measured). Then it repeats the four values and asks for a yes. Then one `vw voice catalog` call, library scope, with exactly those filters; the answer is compact (id, name, accent, gender, age, use case, descriptive, description cut at 160 characters, preview link, on-account mark; one line per voice on the tool's summary; 20 per page). The assistant offers the page link with the filters pre-set, or continues in chat: preview links, shortlist, audition, as today.

## D. Delivery direction: the new step after the voice is chosen
Between the choice and the narration, the assistant proposes how the script should be delivered, the operator agrees, and the narration is generated with those directions.

| Piece | What |
|---|---|
| Vocabulary | for narration, a short set of register and pacing tags: `[measured]`, `[warm]`, `[thoughtful]`, `[confident]`, `[softly]`, `[slowly]`, `[gradually building energy]`, `[emphatic]`, and free descriptions in the same spirit; **no reactions** (`[laughs]`, `[sighs]`, `[gasps]`) and **no `[pause]` tags**: pauses stay with the tool's own silence insertion (design/19), which is exact and already approved with the scenes; a provider pause of unknown length would fight it |
| Grain | one tag per sentence at most, placed before the sentence's first word; a phrase inside a sentence may get its own tag when the delivery changes mid-sentence (the provider's rule: tag before the clause, another after it); a word alone is possible but discouraged for narration |
| Proposal | `out/voice.json` gains `delivery`: `[{sentence: n, after_word_id (or first_word_id), tag, reason}]`, with the register of the whole film stated once at the top; the assistant presents it as a list: the sentence's first words, the tag, the reason, and asks once: approve, change, or none |
| Direction audition | before the full narration, one paid audition of one passage **with its tags** in the chosen voice, played from the page or fetched; the operator hears whether the voice follows them (the provider says this varies by voice); on their yes the narration runs; a tag read aloud or ignored is dropped or changed here, not after a full narration |
| Record | the approved directions are recorded with the operator's quote in the voice output's summary and in the narration job's snapshot (`delivery`), so the narration is reproducible |
| Narration | the server builds the provider text from the accepted script with the tags inserted; the pieces split (design/40) keeps every tag with its sentence; nothing else changes in the request |

## E. The timing contract: what must stay true
Every later stage trusts `timing.json`, built from the provider's character alignment and checked against the accepted script character for character (`script_characters_match`). Tags add characters to the request text. Two cases, settled by the verification request in A:
- **The alignment includes the tag characters.** The server removes the tag spans from the three alignment arrays (characters and the two time arrays) before building the timing, then checks the remainder against the accepted script as today. The tag's characters carry no speech; their start and end times are dropped with them.
- **The alignment excludes them.** The check passes as today; nothing to strip.
**SK's decision (20 Oct 2026, side thread): strip always.** The server removes every tag span from the provider text's alignment whether or not the provider timed its characters (a tag span absent from the arrays is simply not there to remove), so tags never reach the timing file, the transcript, the subtitles or any later stage; only the spoken characters and their true times remain, and the total length stays the real audio length. The verification request in A then only tells us which branch runs; it no longer changes the design. In both cases `source_script`, `text_sha256` (of the accepted script) and the word ids are unchanged, so scenes, pauses, subtitles and the assembly see exactly the narration they see today. The provider text with tags is kept in the snapshot for the record.

## F. Unstated but expected
- Choosing on the page is the operator's choice; the paid narration is announced, not asked (the existing rule for paid steps). Whether the page choice also stands for the quote at `vw stage voice record` is SK's decision (open question 2 below); the recommendation is that record still takes the operator's words after they listened to the full narration, as today.
- A library voice added for an audition stays on the account until released; releasing never touches a custom voice.
- The page never generates anything without a click on a button that names the cost.
- The direction audition is the only new paid step; the full narration is paid as today.
- A run narrated without directions (the operator says "none") is exactly today's narration.

## G. Edge cases
| Case | Expected |
|---|---|
| the page's choice and a voice named in chat differ | the later one wins; the assistant says which it is using and when each was made |
| shortlist of seven | refused at six |
| audition on a library voice when the month's add quota is spent | the provider refuses; the page shows the refusal and the quota line; the operator picks an account voice or waits |
| the voice follows no tag in the direction audition | the operator hears it; the assistant proposes "none" or another voice; no claim of having heard |
| a tag read aloud | the operator hears it in the direction audition; the tag is dropped |
| tags in the alignment, stripping leaves a mismatch | the narration is refused with "narrate again", as any mismatch is today; the snapshot shows the tagged text |
| the operator asks for `[pause]` | the assistant explains pauses are set with the scenes at options and offers to note the wish there |
| a tag inside a piece boundary | pieces split at paragraph and sentence ends; a tag before a sentence stays with it |

## H. Open questions for SK
1. Does the choice on the page also stand as the approval at `vw stage voice record`, or does record still take your words after the full narration (recommended)?
2. Keep a "release from account" action on the page (recommended: yes, for library voices only)?
3. The chat questions, one per message: gender, age, accent, register. Anything else asked every time?
4. The direction vocabulary: register and pacing only, no reactions, no provider pauses (recommended). Agree?
5. Settled 20 Oct 2026: tags are always stripped from the alignment (section E); the twenty-character call stays as a check of which branch runs, made when building starts.

## I. Tests (written first, when built)
Layer one, server unit: compact catalog rows; `strip_tags(alignment, text)` on both alignment cases with fixtures; the delivery list validator (one tag per sentence, vocabulary, no pauses, ids exist); provider text built from script plus directions, pieces keep tags with sentences; choice record shape. Layer one, plugin: the voice prepare prints the page choice and the direction step; `out/voice.json` with and without `delivery`; the one-question-per-message steps in the procedure text. Layer two (Docker): the page's endpoints (catalog proxy, shortlist, audition submit, choice) with the provider faked; `next` carries `voice_choice`.

## J. Not covered
- The provider's alignment with tags until the verification request runs.
- How well any given voice follows tags: the direction audition is the test, every time.
- The desktop app's handling of a sent mp3 (inline player or download card); the page is the sure way to listen.

## K. Estimate
Page (catalog proxy, previews, shortlist, audition, choice, account line): two days. Chat path and compact catalog: half a day. Delivery direction (proposal, validator, direction audition, provider text, alignment stripping, record): one and a half days. Tests throughout; a VM check of the alignment first.

## L. Relayed from SK's side thread (20 Oct 2026, by another session; SK to confirm here before building)
Question 1 is answered with a third flow, which replaces "choose on the page" in B and the record wording in F when confirmed:
1. On the page SK listens to samples and auditions and picks a voice. The pick is provisional.
2. Before the first full narration the assistant shows the delivery direction list once (the film's register, then at most one tag per sentence with its reason); SK approves, changes or says none. **The tags belong to the script, not the voice**: decided once, kept with the script, reused for every voice tried.
3. A page button "Full narration with this voice" (cost shown, whole script, paid). Before it runs the direction list is shown again, pre-filled; a tweak made here stays with that voice's narration, the base list stays with the script.
4. SK listens to the full narration on the page.
5. Not right: pick another voice, press the same button; the tags come along, only the voice changes. Every narration is kept, named by its voice, so SK can go back to an earlier one. If the base list changes after narrations exist, the page says which narrations were made without the change.
6. Right: "Make this the final narration", with SK's words: that click is the record. Nothing before it is final.
Agreed in principle: an optional cheaper button, one passage with tags in the new voice before the full narration (offered, not forced).
Questions 2 to 5 remain open.

## M. Relayed from SK's side thread on the Voices page (20 Oct 2026, by another session; SK: "happy with everything proposed except the last question"; to confirm here before building)
Two additions to section B, accepted in the side thread:
1. **A voice register** on the server, one small table: voice id, name, source (custom, or library with the owner id and original voice id), favourite mark, note, who marked and when. Rules: Release refuses a favourite ("favourite since <date>, by <name>; unmark it first"); unmarking is a separate, logged click; the tool never deletes custom voices (Release is for library copies only); a favourite library voice missing from the account shows "missing from the account" with one click to save it again from the stored library identity; a voice withdrawn from the library itself is unrecoverable and the page says so. Favourites come first on the page with a star; in the chat path the assistant proposes favourites after the client's last voice and before the catalogue.
2. **A usage directory** built from existing records (accepted voice outputs, audition and narration jobs): per voice, narrated in (run code, title, client, date), auditioned in, counts, last used. Shown as a Voices directory page (the page opened without a run), on each run's page (its narrator), and as `vw voice history`, so the assistant can say where a voice was used when proposing it.
No history from earlier runs: both start with the first run after the change is deployed. Standing rule (memory: trial-runs-are-disposable): existing runs are disposable trials; no design or code for old runs or old flows.
