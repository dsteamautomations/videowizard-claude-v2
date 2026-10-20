# 52 — Voice stage: the Voices page, the voice register, the chat path, and delivery direction on Eleven v4 (requirements for SK's approval, 20 Oct 2026)

Consolidates design/51 (research and the trail of decisions, sections A to M) and SK's three side-thread decisions of 20 Oct 2026 into one buildable note. Where the side threads and the first draft differed, section N says what was chosen and why. Nothing here is built. The runs that exist today are disposable trials (memory: trial-runs-are-disposable): no section covers old runs or old flows.

## Decisions carried
1. The full Voices page, with the voice register (favourites) and the usage directory (design/51 B, M).
2. The pick on the page is provisional; the click "Make this the final narration", with SK's words, is the record; nothing before it is final (design/51 L).
3. Delivery tags belong to the script: decided once before the first full narration, reused for every voice; per-voice tweaks stay with that voice's narration (design/51 L).
4. Tag characters are always stripped from the alignment; the timeline is the real audio length; word ids, source_script and text_sha256 of the accepted script are unchanged (design/51 E).
5. The assistant proposes the tags from a procedure prompt of its own, from the script, the brief and the kind of film, as **two lists: best fit and experimental** (SK, 20 Oct); the vocabulary is register and pacing, no reactions, no provider pauses (design/51 D, H4).
6. The chat path asks one question per message: gender, age, accent, register, recommendation first with its reason (design/51 C, H3); favourites are proposed after the client's last voice and before the catalogue (design/51 M).
7. Release exists for library copies only, refuses a favourite, and custom voices are never deleted (design/51 M, H2).
8. An optional cheaper button: one passage with tags in a voice before its full narration (design/51 L).

## A. Server: the catalog and the account
| Piece | What |
|---|---|
| Compact catalog rows | `GET /api/voice/catalog` answers per voice: id, name, accent, gender, age, use case, descriptive, description cut at 160 characters, preview link, scope, on-account mark, favourite mark, usage counts; 20 per page; default scope `library` |
| Account | `GET /api/voice/account`: voice_limit, voice_slots_used, voice_add_edit_counter, max_voice_add_edits, character_count, character_limit (the provider's subscription endpoint, cached 60 s) |
| Release | `POST /api/voice/release {voice_id}`: removes a library copy from the account (provider delete on the account's copy); refused for a custom voice ("custom voices are never deleted here") and for a favourite ("favourite since <date>, by <name>; unmark it first") |
| Register | table `vw2_voices`: voice_id (pk), name, source (`custom`/`library`), public_owner_id, original_voice_id, favourite bool, favourite_by, favourite_at, note, updated_at. `POST /api/voice/favourite {voice_id, on, note}`: marking and unmarking are separate logged rows in `vw2_voice_events` (voice_id, event, by, at, note). A row is created the first time a voice is auditioned, narrated, favourited or released |
| Usage directory | `GET /api/voice/history[?voice_id]`: from `vw2_jobs` (audition, narration) and accepted voice outputs: per voice, narrated in (run code, title, client, date), auditioned in, counts, last used. Starts empty |
| Missing favourite | a favourite whose `source=library` is not on the account answers `missing: true`; `POST /api/voice/restore {voice_id}` saves it again from the stored library identity; a voice gone from the library answers "withdrawn from the library; unrecoverable" |

## B. Server: the run's voice work
| Piece | What |
|---|---|
| Run voice state | storage document `<run>/voice/page.json`: `shortlist` (≤6 voice ids), `excerpt` (the audition passage: the assistant's from chat, else the server's default, the first passage of 45–70 words), `pick` (provisional: voice id, name, by, at), `narrations` (one per full narration: job id, voice id, name, model, settings, direction digest, tweaks, by, at, heard), `final` (set by record) |
| Direction document | storage `<run>/voice/direction.json`: `{register, options: {best_fit: [...], experimental: [...]}, chosen: 'best_fit'|'experimental'|'none', base: [...], approved_by, at, quote, digest}`; each item `{passage_id, sentence, first_words, tag, reason}`; the sentence index counts sentences inside the passage with the script stage's splitter (`stages_text.sentences`) |
| Validator (`voice_direction.py`, pure) | one tag per sentence; every (passage_id, sentence) exists in the accepted script; tags are square-bracketed, ≤ 60 characters, from the register and pacing vocabulary or a free description with none of the reaction words (laugh, sigh, gasp, cry, cough, clears throat, giggle, chuckle) and no pause words (pause, silence, break, beat); the experimental list may use richer descriptions under the same rules; a register line is required |
| Provider text | `voice_direction.apply(text, base, tweaks)`: the accepted script with each tag inserted before its sentence's first character, plus the register tag before the first sentence; pieces (design/40) keep a tag with its sentence; the snapshot keeps `text_tagged`, `text` (accepted), `direction_digest`, `tweaks` |
| Alignment | `voice_direction.strip(alignment, text_tagged, tag_spans)`: every tag span (and one following space) removed from the three arrays whether or not the provider timed it; the remainder must equal the accepted script, else the job fails with "narrate again" as today; `timing_evidence` then runs unchanged |
| Full narration | `POST /api/runs/{id}/voice/narrate {voice_id, tweaks?}`: the same job as `vw voice narrate`, with the direction applied; every narration is kept and listed in `page.json.narrations`; a later change of the base list marks earlier narrations `made_before_direction_change` |
| Direction audition | `POST /api/runs/{id}/voice/direction-audition {voice_id, passage_id}`: one passage with its tags, an audition job (no timing), kept with the run's auditions |
| Final | `POST /api/runs/{id}/voice/final {narration_job_id, quote}`: records the voice stage output exactly as `vw stage voice record` does today (files: narration.mp3, timing.json, voice.json; summary with voice, model, settings, direction digest, tweaks, `accepted_quote` = SK's words from the page), sets `final`; `next` moves to media. The quote is required and non-empty |
| `next` | answers `voice_page: {pick, narrations: n, final: bool, direction: chosen}` while the run is at voice |

## C. The Voices page
`/runs/<code>/voices` (with a run) and `/voices` (the directory, without a run). Signed in as today.

| Part | What |
|---|---|
| Account line | slots used/free, add-edit operations used this month, characters used this period |
| Filters | language, accent, gender, age, use case, search, scope (library default, account, favourites); 20 rows and "more"; a link from chat pre-sets them |
| Rows | star for favourites (listed first), name, labels, description (two lines), **play** (the provider's preview sample, streamed from its public link, nothing stored), on-account mark, used-in summary (from the directory), shortlist checkbox, favourite toggle (with a note box), release (library copies only) |
| Shortlist and audition | up to six; "Audition the shortlist (N voices, ~M characters)": library voices are saved to the account first (no custom slot; one operation each); results appear with a player each (streamed from storage) |
| Pick | "Pick this voice" on a row or an audition: provisional, shown at the top |
| Direction | the approved base list (from chat, section D) shown read-only with its register, or "no direction yet: ask the assistant" when none; the experimental/best-fit choice shown |
| Full narration | "Full narration with <name> (~K characters)": opens the direction list pre-filled; SK may tweak a tag for this voice (the tweak stays with this narration); optional "Try one passage first (~k characters)" (the direction audition); then the narration runs; the result appears under Narrations with a player, named by voice, with its date and whether it was made before a later direction change |
| Final | on any kept narration: "Make this the final narration", a text box for SK's words (required), the click is the record; the page then shows the run at media |
| Directory page | every voice in the register and every voice used, with favourites first, usage, last used, missing-from-account marks with "save again"; the same filters |
| Run page | shows the run's narrator (final) or the provisional pick |

## D. The chat path and the assistant's steps (procedure text, v2.json voice stage)
1. `vw stage voice prepare`: prints the accepted script, the brief, the languages, the client's last voice, the favourites (with usage), the run's page state (`pick`, narrations, direction) and the prompts (voice and direction).
2. Repeat client: propose the last voice first ("same voice, or compare?"). Then favourites, with where each was used. Then the catalogue.
3. On "compare": **one question per message**, recommendation first with its reason from the brief: gender; age group; accent (never from the client's name); register. Repeat the four and ask for a yes. Then one `vw voice catalog` call with those filters (library scope); offer the page link with the filters pre-set, or continue in chat (preview links, `vw voice shortlist`, `vw voice audition`, as today).
4. **Direction, once per run, before the first full narration**: run `vw voice direct prepare` (prints the script with passage and sentence ids, the brief, the kind of film, the direction prompt); write `out/direction.json` with the register and the two lists; present both as lists (first words, tag, reason), with one line on what the experimental list does differently; ask: best fit, experimental, changes, or none. On the operator's words run `vw voice direct record --choice best_fit|experimental|none --quote "<their words>"`; corrections: edit the file and ask again.
5. Narration: on the page (section C) or in chat with `vw voice narrate --voice ID --note` (the direction applies the same way); `vw voice tweak --voice ID --file` for per-voice tweaks in chat.
6. The record: the page's final click, or in chat `vw stage voice record --job ID --quote` after the operator listened to that narration. Both record the same output.
7. Paid steps are information, not questions: say what is generated, the model, the settings and the character count, then proceed.
8. `vw voice history [--voice ID]` prints the usage directory line for a voice.

## E. The direction prompt (VW-DIRECTION v1, for the assistant only, carried in v2.json as the voice stage's second prompt)
```
VW-PROCEDURE — for the assistant only, never for the operator.

# VW-DIRECTION v1 — how the narration should be delivered

You are directing a narrator, not writing. The words are fixed: the accepted script below,
sentence by sentence, with passage and sentence ids. You never add, remove or change a word.
You add delivery tags in square brackets that Eleven v4 reads as direction, placed before the
sentence they govern. A tag carries forward until the next tag.

WHAT YOU READ FIRST
- The brief: purpose, audience, message, tone, ending. The tone is the register of the film;
  your direction makes it audible.
- The kind of film, which you state in one line before anything else: a documentary explainer,
  a promotional film, a social video, a testimonial, a training film, or another kind; from the
  brief and the script, never assumed. The kind sets the range: a documentary is measured and
  even; a promotional film builds and lands; a social video is quick and warm; a training film is
  clear and unhurried.
- The script: where it explains, where it argues, where it instructs, where it concludes.
- The chosen voice's labels when known (descriptive, use case): direct within the voice's character;
  a calm voice is not pushed to shout.

THE VOCABULARY
Register and pacing only. Register: [measured], [warm], [confident], [thoughtful], [earnest],
[reassuring], [matter-of-fact], [quietly proud], [emphatic], [softly], and free descriptions in the
same spirit ("[lower, thoughtful]", "[gradually building energy]", "[lighter, inviting]").
Pacing: [slowly], [unhurried], [brisk], [with weight on the figures], [lifting at the end].
Never a reaction ([laughs], [sighs], [gasps], [clears throat], [crying]) in a narration.
Never a pause tag ([pause], [long pause], [beat], [silence]): pauses are set exactly with the
scenes at the options stage; a provider pause would fight them.
Never an accent tag: accent is the voice's, chosen by the operator.
One tag per sentence at most; a tag only where the delivery changes. Most sentences carry no tag:
the register tag at the top governs them. A list of forty tags on forty sentences is wrong.

TWO LISTS
1. best_fit: the delivery the brief asks for, as a careful director would give it. Few tags:
   the register once, then a change only at the turns of the film (the opening claim, the first
   figure, the warning, the conclusion).
2. experimental: a second reading that is different, not strange. One idea, carried through:
   for example a quieter, more intimate register for an explainer; a brisker, lighter pace for
   a film that risks solemnity; weight on the numbers; a warmer close. Say in one line what the
   idea is and what it risks. Same vocabulary, same rules, never contrasting cues on one sentence.
   The experimental list is an offer the operator may refuse; it is not better by default.

WHAT YOU SAY TO THE OPERATOR
Present the kind of film in one line, the register of each list, then each list as rows:
the sentence's first four or five words, the tag, the reason in a short phrase. Then the one line
on the experimental idea. Ask: best fit, experimental, changes, or none. "None" is a valid
answer: the voice reads the script as it is. Never claim to have heard anything; only the
operator's listening establishes what a voice does with a tag.

Return only JSON:
{
  "kind_of_film": "one line",
  "register": {"best_fit": "[...]", "experimental": "[...]"},
  "options": {
    "best_fit": [{"passage_id": "P001", "sentence": 1, "first_words": "…", "tag": "[...]", "reason": "…"}],
    "experimental": [...]
  },
  "experimental_idea": "one line: the idea and what it risks"
}
```

## F. Unstated but expected
- A run narrated with "none" is exactly today's narration; the direction document records "none".
- The page never generates anything without a click on a button that names its cost; the assistant announces paid steps and proceeds.
- The provisional pick and a voice named in chat: the later wins; the assistant says which.
- Every narration is kept in storage under the run until close, like auditions; the final one is the stage output.
- The register and the directory start empty; the first run after deployment fills them.
- A tweak never changes the base list; changing the base list after narrations exist marks them, it does not delete them.
- The voice stage's attempt cap (2) counts failed records, not narrations.

## G. Edge cases
| Case | Expected |
|---|---|
| a tag on a sentence that does not exist | direction record refused, naming it |
| a reaction or pause word in a tag | refused, naming the word |
| 40 tags on 40 sentences | accepted by the validator but the prompt forbids it; the assistant is asked to redo when the operator objects |
| the provider leaves tag characters in the alignment | stripped; remainder equals the script |
| the provider drops them | nothing to strip; remainder equals the script |
| stripping leaves a mismatch | the job fails "narrate again"; the snapshot shows text_tagged |
| release on a favourite | refused with the favourite's date and name |
| release on a custom voice | refused |
| favourite library voice missing from the account | "missing"; one click restores from the stored identity |
| voice withdrawn from the library | "withdrawn; unrecoverable" |
| final click with an empty words box | refused |
| two full narrations with the same voice | both kept, numbered |
| base list changed after two narrations | both marked "made before the direction change" |
| the operator asks for a pause tag | the assistant explains pauses live with the scenes |

## H. Tests (written first)
Layer one, server unit (no database): compact rows; `voice_direction` validator (ids, vocabulary, reactions, pauses, one per sentence); `apply` (tags before sentences, pieces keep tags); `strip` for both alignment cases and the mismatch; the final-record summary shape; the directory aggregation from job rows (pure function over dicts). Layer one, plugin: `vw voice direct prepare/record`, `tweak`, `history`, `stage voice record --job`; the one-question steps and the direction prompt present in v2.json with the sentinel. Layer two (Docker): page endpoints with the provider faked (catalog, account, favourite, release rules, restore, shortlist, audition, narrate, direction-audition, final, `next.voice_page`).

## I. Not covered
- Which alignment branch the provider takes: checked with one ~20-character paid call from the VM when building starts (settled as a check, not a decision).
- How well any voice follows tags: the direction audition and the operator's listening, every time.
- The desktop app's inline playing of a sent mp3; the page is the way to listen.
- `server/tests` cannot run on this Mac.

## J. Versions and deploy order
Server minor bump; plugin minor bump. Migration: `vw2_voices`, `vw2_voice_events` (applied by hand in Supabase before the server deploy, as earlier tables were). Deploy order: server (workers restart; tell SK first), plugin (SK restarts Claude Code), design/35 row.

## K. Estimate
Server catalog, account, register, release, restore, directory: one day. Page: two days. Direction (prompt, validator, apply, strip, audition, narrate, final): one and a half days. Plugin and procedure text: half a day. Tests throughout. The scenario test with SK (VW-4 or the next run) after deployment.

## N. Reconciliation of the three side threads with the first draft
| Point | Draft (design/51) | Side threads | Chosen |
|---|---|---|---|
| What is the record | "choose" on the page, then the assistant narrates, record takes words after listening | L: the final-narration click with SK's words is the record | L; the page's click records with the words; chat keeps `vw stage voice record --job` for the same |
| When tags are decided | after the voice is chosen, per voice, with a direction audition | L: once, with the script; per-voice tweaks; the audition optional | L, plus the two-list proposal (SK, 20 Oct) |
| Vocabulary | register and pacing, no reactions, no pauses | H4 accepted ("happy with everything proposed") | kept, for both lists; the experimental list differs in idea, not in rules |
| Release | yes, library copies only | M: refuse a favourite; never custom voices | M |
| Chat questions | gender, age, accent, register | H3 accepted | kept; favourites proposed after the last voice (M) |
| Alignment | two branches | E: strip always | E |
| Old runs | edge cases for earlier runs | memory rule: disposable | removed |
Not quite clear from SK's words, decided here and open to correction: (a) "the tags belong to the script" is read as one base list per run, chosen from the two proposals, not two lists both kept; (b) the experimental list keeps the same vocabulary rules (no reactions, no pauses); "a little different, not too weird" is an idea carried through, not a looser rule; (c) the direction is proposed in chat (the assistant writes it), shown on the page read-only; tweaks are edited on the page before a narration.
