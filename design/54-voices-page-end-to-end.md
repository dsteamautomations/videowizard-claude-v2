# 54 — The Voices page, end to end: the whole catalogue, live filtering, tryouts, up to three full narrations, final and download (approved by SK 20 Oct 2026; built the same day as /runs/<code>/voices2 beside the current page; switch on SK's word)

Source: SK, 20 Oct 2026, after resuming VW-6's voice stage: the page must give an experience close to the ElevenLabs app (filter the whole library and see the voices change as the filter changes, play samples, try a few, choose, hear the full script, finalise, download), the test lines must be proposed by the assistant and never asked from the operator, the delivery direction is proposed before the voice is chosen, and at most three voices get a full narration. Replaces design/52 B and C (the page and the chat path); design/52 D and E (direction, the timing contract) stand. One flow, two front ends (CLAUDE.md): every button below calls a server function the `vw` tool calls too.

## Decisions carried
1. The page is the only place the operator needs to be from the end of the script stage to the media stage; chat does the two things that need the model's judgement (direction, test passages) before the page, and `vw next` afterwards.
2. The full library is mirrored as metadata on the server and filtered in the browser as the filters change; samples play from the provider's links; nothing is stored for browsing.
3. Tryouts (auditions) carry the recorded direction tags; up to six voices per tryout; up to **three** voices get a full narration; per-voice tweaks and re-narrations are kept as versions; the final click with the operator's words is the record; the final narration and its timing can be downloaded from the page.

## A. The catalogue mirror
| Piece | What |
|---|---|
| Table `vw2_voice_catalog` | voice_id (pk), name, scope (`library`/`account`), public_owner_id, original_voice_id, language, accent, gender, age, use_case, descriptive, description (cut at 600), preview_url, category, verified_languages (text[]), on_account (bool), seen_at, refreshed_at. A row per voice the provider lists. |
| Refresh | `voices.refresh_catalog(conn, provider)`: walks the shared library (`/v1/shared-voices`, 100 a page, all pages) and the account (`/v2/voices`, 100 a page), upserts rows, marks rows not seen as `withdrawn_at`. Runs on the page's "Refresh catalogue" button (one click, the page shows "refreshing… N voices" and the finish time) and once a night from the worker loop (a `catalog_refresh` job). The first run after deploy fills the table. Register rows (favourites, design/52 M) stay in `vw2_voices`; the mirror is read-only data. |
| Read | `GET /api/voice/mirror` answers the compact rows (voice_id, name, accent, gender, age, use_case, descriptive, description cut at 160, on_account, favourite, narrations, auditions, last_used; no sample link) as one JSON, cached in memory on the server for five minutes; a few thousand rows is a few megabytes, loaded once by the page. |
| Sample | `GET /api/voice/preview/{id}` (exists): the page asks for the link when the play button is pressed; an expired provider link is refetched. No audio is stored. |
| Size | At 10,000 voices: about 1 KB a row, 10 MB in the table, 2–3 MB on the wire. Refresh: about 100 provider requests, under a minute. |

## B. Before the page: direction and test passages (chat, right after the script is recorded)
`vw voice direct prepare` and `record` (design/52 D) move to the start of the voice stage, before any voice is discussed, and gain the test passages:
- The direction prompt (VW-DIRECTION v1) adds one task: propose **three test passages** of 50 to 100 words from the accepted script, each one contiguous and starting at a sentence, each with one line on why it tests a voice (a figure to land, a turn of register, the close). `out/direction.json` gains `test_passages: [{passage_id, first_word_id, last_word_id, words, why}]`.
- The operator chooses the direction list (best fit, experimental, none) and the test passage (1, 2 or 3) in one answer; `vw voice direct record --choice … --passage N --quote "…"` records both. The server validates that the passage is contiguous script text.
- The assistant then prints the page link (`voice_page_url`) and says: everything else happens on the page; say "what is next" when a narration is final.
- Last voice and favourites are still named in that message as recommendations; the page shows them first.

**How the tags are shown (SK, 20 Oct: the tags were not visible in VW-6's flow; they must be).**
- In chat, when the direction is proposed: the kind of film in one line; then for each list its register tag and a table of every tagged sentence: the sentence's first words, the tag, the reason; then one line on the experimental idea and what it risks. Sentences without a tag are not listed (the register governs them); the count of tagged sentences out of the total is stated ("5 of 34 sentences carry a tag").
- Before recording: on request, `vw voice direct prepare --show` prints the whole script with the chosen list's tags inserted where the provider will read them, so the operator sees the directed text as one piece.
- On the page, at the top: the register, the count, and "show the directed script", which opens the full script with each tag shown in front of its sentence (read-only). The three test passages are shown the same way, the chosen one marked.
- At tryout: every audition reads the test passage **with its tags**, so what the operator hears is the directed delivery; the card says "with the direction tags".
- In panel 4: "tweak one sentence" opens the same sentence list for that voice; a tweaked sentence shows the base tag and the tweak side by side.
- The timing never carries the tags (design/52 E); the page's download gives the clean narration and timing.

## C. The page (`/runs/<code>/voices`)
**Layout (SK, 20 Oct): a wizard with a step bar.** One page; a header always visible (run, direction summary, chosen test passage, "show the directed script", the account line); a step bar with the six steps (1 Browse · 2 Try · 3 Choose · 4 Narrations · 5 Finalise · 6 Download), each showing its count (tried 2 of 6, chosen 1 of 3); one step's content visible at a time; every step is clickable at any time to go back or forward (no step is locked except Download before a final exists); a "next" button at the foot of each step; the current step is remembered on the server so reopening the page lands on it. Not tabs (tabs imply no order) and not a side rail (Browse needs the full width for the cards). Vanilla JavaScript (no framework), the existing stylesheet extended.

**My voices (SK, 20 Oct).** Two different marks on every card: "save to my voices" saves a library voice to the ElevenLabs account (the provider's My Voices; no custom slot used; one add operation) so it is ready and appears under the "in my voices" filter; the star marks a favourite in our own register (design/52 M), which also orders the cards. A voice is saved to my voices automatically when first tried; the button lets the operator save it without trying.

**Narrations carry the tags (SK, 20 Oct).** Every tryout reads the test passage with the direction's register and that passage's tags; every full narration reads the whole script with the chosen list's tags and that voice's tweaks. The card and the narration row say "with the direction tags". A narration without tags exists only when the recorded direction is "none". The run's state (`page.json`) and the jobs are polled every ten seconds while any job is open, so nothing needs a manual refresh.

```
+--------------------------------------------------------------------------------------------------+
| VW-6 · Rat-Trap Bond Masonry - Documentary Explainer v3 · voice stage                            |
| Direction: best fit, register [measured], 4 tags · Test passage 2 (71 words): "The greatest …"   |
| (ask the assistant to change these)                     Account: slots 54/160 · ops 12/290       |
+-----------------------+--------------------------------------------------------------------------+
| 1 BROWSE              |  cards (filtered live; favourites and last voice first)                   |
| language  [en      ]  |  +------------------------------+  +------------------------------+      |
| accent    [indian  ]  |  | ★ Santhi Prakash              |  | Jamil - Rich Audiobook        |      |
| gender    (•)M ( )F   |  | indian · male · middle_aged   |  | indian · male · middle_aged   |      |
| age       [middle ▼]  |  | narration · warm, clear …     |  | narration · deep, warm …      |      |
| use case  [any    ▼]  |  | ▶ sample   [ ] try   ☆ fav    |  | ▶ sample   [x] try   ☆ fav    |      |
| search    [measured]  |  | used: 1 narration (VW-5)      |  | on the account                |      |
| [ ] favourites only   |  +------------------------------+  +------------------------------+      |
| [ ] on the account    |  … 12 of 4,812 voices match                                              |
| Refresh catalogue     |                                                                          |
| (last: 20 Oct 06:00)  |                                                                          |
+-----------------------+--------------------------------------------------------------------------+
| 2 TRY (up to 6)       Santhi, Jamil, Yash, Sarang, Dev, UD - Narrator                             |
|   test passage 2 · with the direction tags · [Try these 6 voices — paid, ~3,600 characters]       |
|   results: Santhi ▶ ready · Jamil ▶ ready · Yash ◌ generating · … (polls itself)                  |
+--------------------------------------------------------------------------------------------------+
| 3 CHOOSE (up to 3)    [x] Santhi  [x] Jamil  [ ] Yash …                                           |
|   [Narrate the full script with these 2 voices — paid, ~9,600 characters]                        |
+--------------------------------------------------------------------------------------------------+
| 4 NARRATIONS          Santhi #1 ▶ 5:41 · made 06:52 · [tweak one sentence ▼] [narrate again]      |
|                       Jamil  #1 ▶ 5:38 · made 06:53 · [tweak one sentence ▼] [narrate again]      |
|                       (an earlier version stays listed; "made before the direction changed" when so)|
+--------------------------------------------------------------------------------------------------+
| 5 FINALISE            Santhi #1 · your words: [________________________] [Make this the final]    |
+--------------------------------------------------------------------------------------------------+
| 6 DOWNLOAD            final: Santhi #1 · narration.mp3 · timing.json                              |
+--------------------------------------------------------------------------------------------------+
```

| Panel | Behaviour | Server function (shared with `vw`) |
|---|---|---|
| 1 Browse | The mirror is loaded once; every filter change re-filters in the browser; cards show name, labels, the short description, usage, the favourite star, "in my voices" or "library"; ▶ fetches the sample link and plays; "try" adds the voice to step 2 (max six, the seventh is refused with a line); "save to my voices" saves a library voice to the account; last voice and favourites come first | `GET /api/voice/mirror`, `GET /api/voice/preview/{id}`, `POST /api/voice/favourite`, `POST /api/voice/library-add`, `POST /api/voice/refresh` |
| 2 Try | One button; the cost line says voices × passage characters; auditions carry the direction's register and the passage's tags (design/52 D direction audition, now the only audition); results appear per voice with a player as jobs finish | `POST /api/runs/{id}/voice/tryout {voice_ids}` → `voices.tryout` → `jobs.submit_voice` (saves library voices to the account itself) |
| 3 Choose | Tick up to three tried voices; one button narrates the whole script in each, direction applied; the fourth tick is refused with a line; progress per voice | `POST /api/runs/{id}/voice/narrate {voice_ids}` → `voices.narrate` once per voice |
| 4 Narrations | Every narration listed by voice and version with a player and duration; "tweak one sentence" opens the sentence list with a tag box for that voice only; "narrate again" makes a new version with the tweaks; a base-direction change after narrations marks the earlier ones | `POST /api/runs/{id}/voice/tweaks`, `…/voice/narrate` |
| 5 Finalise | On any ready narration: a words box (required) and the button; the click is the record; the page then says the run is at media and links the run page | `POST /api/runs/{id}/voice/final` → `voices.finalise` → `core.output` |
| 6 Download | After the final: the narration mp3 and timing.json by their storage links | `GET /runs/{code}/audio/{key}` (exists) |

Also on the page: the account line; a "withdrawn from the library" mark on a card whose voice the provider no longer lists; an error line for any refused action, in the server's words.

## D. The chat path, reduced
`vw voice direct prepare|record` (with the passage), `vw next` (prints `voice_page_url` and the page state), `vw voice history`. The audition and narration commands stay for the operator who prefers chat and call the same server functions (`vw voice tryout --voice …`, `vw voice narrate --voice …`, `vw stage voice record --job …`); the step text says the page is the default and chat is the fallback. `vw voice catalog` reads the mirror (one line per voice, the page link with the filters), no provider call.

## E. Rules kept
Provisional pick until the final click; tags belong to the script, tweaks to a voice; tags stripped from the timing (design/52 E); every narration kept; library voices saved to the account on first use (defect 16); paid buttons name their cost; nothing runs without a click; favourites and release rules (design/52 M); trial runs are disposable, so the mirror and the page start empty and nothing migrates from earlier runs.

## F. Unstated but expected
- A page open during a long narration keeps polling; closing and reopening it shows the same state (all state is on the server).
- The mirror can be a day old; the refresh button is for the operator who wants the latest; a voice withdrawn since the refresh fails at tryout with the provider's message and the card is marked.
- The chat path still works end to end for an operator with no browser.
- Three full narrations at once run on three workers; the page shows each as it finishes.

## G. Edge cases
| Case | Expected |
|---|---|
| seventh voice ticked for tryout | refused on the page with a line; nothing sent |
| fourth voice ticked for narration | refused likewise |
| tryout with no direction recorded | the button is disabled with "ask the assistant for the direction and test passage first" |
| a tried voice withdrawn from the library before narration | the narration refuses with the provider's message; the card is marked |
| the mirror empty (first deploy) | the page offers the refresh button and says why the grid is empty |
| refresh while one is running | refused; the running one's progress is shown |
| final click with an empty words box | refused |
| the operator narrates the same voice twice | versions #1 and #2, both kept |

## H. Tests (written first)
Server unit: mirror row from a provider voice (both shapes), the in-browser filter's server twin (`filter_rows`) for the fallback catalog, tryout and narration caps, the passage validator (contiguous, 50–100 words), `final_body` unchanged. Plugin: `direct record --passage`, the prompt asks for three passages, `vw voice catalog` reads the mirror, the steps text (page default, chat fallback). Docker: refresh with the provider faked (two pages), mirror endpoint, tryout → six jobs with tags, narrate three, final, download links.

## I. Not covered
server/tests on this Mac; the page's look is reviewed by SK on the live server with VW-6 before it replaces the current page (built as `/runs/<code>/voices2`, switched over on SK's word).

## J. Deploy order
Migration (the mirror table) applies at server start; server, then plugin; the first refresh from the page; SK reviews `/voices2` on VW-6; switch; design/35 row.

## K. Estimate
Mirror and refresh, half a day. The page, two days. Direction with test passages, chat path, half a day. Tests throughout.
