# 55 — The Voices page rebuilt: live search of the provider's library, the ElevenLabs layout, four steps, no mirror (approved by SK 20 Oct 2026; built the same day at /runs/<code>/voices2; the mirror of design/54 removed)

Source: SK's review of `/runs/VW-6/voices2` on 20 Oct 2026: too many controls, cluttered, no clear start or next step, nothing like the ElevenLabs app, no name search, and an unacceptable wait ("refreshing the catalogue … three to four minutes"). SK's proposal: pull nothing in advance; start with the filters; on a filter change call the provider, 100 voices at a time, and show 20 a page. Checked against the provider's voice-library endpoint and the ElevenLabs screens on Mobbin ([explore](https://mobbin.com/screens/609210af-c2ba-4d78-8176-3b41197e5dc2), [filters](https://mobbin.com/screens/943ec027-0884-420a-b3a5-3563b697d97f), [sort](https://mobbin.com/screens/ba7e714b-73d8-4580-b94c-66b6c486e724), [my voices](https://mobbin.com/screens/88926855-ed44-4236-ae9a-7603f3095fa4)). Revises design/54 section A and step 1 of section C; steps 2 to 6 keep their behaviour and take the same restyle. One flow, two front ends (CLAUDE.md): every call below is a server function `vw` calls too.

## Decisions carried (SK, 20 Oct, after the review)
- Empty first: no voices are fetched until the operator sets a filter or searches, except when the assistant's link carries the recommended filters, in which case that search runs on open.
- Every table on every step has alternating row colours; the play control is a column of its own; one docked player at the foot plays one voice at a time.
- The steps are a sticky line at the top and the primary action sits in a sticky bar at the foot, so the next action is never out of view.
- Every step is clickable at any time: steps are views of the run's state; the gates are on the actions.
- Four steps, not six: Browse, Try, Narrations, Final (Choose becomes a checkbox on the tryout results; Download is a line on Final once the final exists).
- A voice the operator already knows (last time's narrator, a favourite, any voice in my voices) can be narrated directly without a tryout, within the cap of three.
- Clarity above all: every empty screen says what to do next in one line; every button says what it costs; every state has one obvious next action.

## Decisions carried from the first draft
1. No mirror. The catalogue is the provider's; the page asks it live, with the operator's filters, 100 voices a page, and shows 20 a page. The mirror table, its refresh button and the nightly refresh go.
2. The layout follows the ElevenLabs voice library: tabs, one search bar, a filters panel, a chips row, plain rows with a play icon, one sort menu, a pager.
3. One primary action on the step, pinned at the foot: the tryout. Everything else is a quiet control.
4. The steps are one thin line at the top; the direction and the account line collapse into one line with "show".

## A. What the provider's endpoint gives us (checked 20 Oct)
`GET /v1/shared-voices`: `page_size` up to 100, `page`, `search` (name and description), `gender`, `age`, `accent`, `language`, `locale`, `use_cases`, `category` (professional, famous, high_quality), `featured`, `sort` (`trending`, `created_date`, `usage_character_count_1y`, `cloned_by_count`); the answer carries `total_count`, `has_more` and per voice `is_added_by_user`, `preview_url`, `description`, `accent`, `gender`, `age`, `use_case`, `descriptive`, `language`, `category`, `cloned_by_count`, `usage_character_count_1y`, `public_owner_id`. My voices: `GET /v2/voices` (the account), with `search` and the same page size. So one call answers a filter change with everything a row needs; no second call for the sample link and no account walk for the "in my voices" mark.

## B. Server
| Piece | What |
|---|---|
| `voices.search(conn, provider, q)` | `q`: tab (`explore`/`mine`/`favourites`), search, language, accent, gender, age, use_case, category, sort (default `trending`), page (0-based, 100 a page). Explore → shared voices with the filters; mine → the account with `search`; favourites → the register's favourite ids resolved through the account (and the library by identity when missing). Each row is compacted (design/52 A) and joined with the register (favourite, note) and the usage directory (narrations, auditions, last used). Returns `{voices, total, has_more, page}`. The 100-row answer is cached in memory for two minutes per `q`, so paging through the 100 is instant and a repeated filter costs nothing. |
| `GET /api/voice/search?…` | the same, for the page (cookie) and for `vw voice catalog` (Bearer): the chat command becomes a thin client of it, one line per voice, 20 a page, `--page N`. |
| Removed | `vw2_voice_catalog` (migration 008 drops it), `refresh_catalog`, `refresh_if_due`, `mirror_rows`, `mirror_page`, `filter_rows`, the worker's refresh check, `POST /api/voice/refresh`, `/voices2/mirror`. `remember()` keeps recording the library identity of every voice a search lists (defect 16). |
| `voices.preview_link` | from the search answer's row (the page passes the link it already has); the provider lookup stays as the fallback for a voice id typed in chat. |
| Latency | one provider call per filter change, about one to two seconds; the page debounces typing by 400 ms and shows "searching…"; the first screen is trending voices in the brief's narration language, so it is never blank. |

## C. The page: four steps, one look

**Frame (every step).** A sticky line at the top: `Browse › Try › Narrations › Final`, the current step bold, each clickable; under it one line: "Direction: best fit, 5 of 34 sentences tagged · test passage 2 · last voice UD - Narrator · show". A sticky bar at the foot with, from left to right: the docked player (voice name, play/pause, progress), the selection tray for the step, and the one primary button with its cost. Tables everywhere, alternating row colours, the play control in its own column. When a step has nothing to show, its table is replaced by one sentence saying what to do and a link to the step where it is done.

| Step | What it shows | Primary action (footer) | Gate |
|---|---|---|---|
| 1 Browse | tabs Explore / My voices / Favourites; search bar; Filters panel; language, accent and use-case chips; 20 rows a page; columns: voice (initial, name, one-line description, "used: VW-5" or "in my voices"), language · accent, use case, ▶, + (to the tryout), ★ | "Try these N voices on passage 2 — paid, ~M characters" | the direction and the test passage recorded; at most six |
| 2 Try | the tryouts of this run as rows: voice, status, ▶ (the tagged passage), a checkbox "narrate the full script with this voice"; above them a short table **Known voices**: last time's narrator, favourites and voices in my voices with the same checkbox, so a known voice can be narrated without a tryout | "Narrate the full script with these N voices — paid, ~M characters, with the direction tags" | at most three ticked across both tables |
| 3 Narrations | every narration as a row: voice, version, made at, status, duration, ▶, "⋯" (tweak one sentence for this voice and narrate again; shows the base tag beside the tweak); "made before the direction changed" when so | "Make the ticked narration final" (one radio across the rows) with the words box in the footer | one ready narration ticked; the words box filled |
| 4 Final | the final narration as one row with ▶, by whom and when; download links for narration.mp3 and timing.json; "the run is at media" with the run page link | none (done) | a final exists; before that the step shows "No final yet. Pick one on Narrations." |

**Clarity rules.** The footer button is the only filled button on the page; every other control is quiet. A disabled button always carries the reason beside it ("needs the direction first", "tick one to three voices"). Costs are stated before the click. A refused action shows the server's sentence in the message line and nothing else changes. Playing a voice never changes a selection. The tray in the footer names the selected voices so the operator sees what the button will do.

## C1. Step 1 as the operator sees it

```
Browse › Try › Narrations › Final                                              VW-6 · Rat-Trap Bond Masonry v3
Direction: best fit, 5 of 34 sentences tagged · test passage 2 · last voice UD - Narrator · [show]

[ Explore ]  My voices   Favourites

🔍 Search library voices…                                            [ Filters ▾ ]   [ Trending ▾ ]
Language: English ▾   Accent: Indian ▾   ( Narration ) ( Educational ) ( Conversational ) ( Advertisement ) ( Characters ) ( Social media )

Results · 1–20 of 412                                                                     ‹ 1 2 3 … 21 ›
 S  Santhi Prakash - Warm Indian Narrator        English · Indian     Narration            ▶   +   ★
    Warm, clear, measured, crisp diction …       used: VW-5
 J  Jamil - Rich Audiobook Narrator              English · Indian     Narration            ▶   +   ☆
    Deep, impeccable diction, warm measured …    in my voices
 Y  Yash - Mystery Documentary Narrator          English · Indian     Narration            ▶   +   ☆
 …

──────────────────────────────────────────────────────────────────────────────────────────────────── (sticky)
▶ Santhi Prakash  ━━━━━━━━━●──────── 0:07 / 0:19   │  Tryout: Santhi, Jamil (2 of 6) · passage 2  │ [ Try these 2 voices — paid, ~340 chars ]
```
(the rows alternate in colour; the first open with no filters shows the tabs, the bar and the chips over one line: "Set a filter or search to see voices.")

| Element | Behaviour |
|---|---|
| Steps line | the four steps as text with the current one bold; each clickable at any time (a step with nothing yet says what to do and where) |
| Direction line | one line: the chosen list, the tag count, the test passage number, the last voice; "show" opens the directed script and the account figures |
| Tabs | Explore (the library), My voices (the account), Favourites (ours); the search bar and the chips apply to all three |
| Search bar | name or description; 400 ms debounce; Enter searches at once |
| Filters panel | a small panel like theirs: gender (male, female, neutral, any), age (young, middle aged, old, any), quality (high quality, any); a count badge on the button when any is set; "clear all" |
| Chips row | language and accent as dropdowns (the brief's narration language pre-selected; the assistant's recommendation pre-sets gender, age and accent through the link); use cases as toggles, one at a time |
| Sort | trending (default), latest, most used |
| Rows | zebra-striped; a coloured initial, name, one-line description; language · accent; use case; then the columns ▶ (sends the sample to the docked player; the playing row shows ⏸), + (adds to the tryout; turns into a tick), ★ (favourite); small text under the name when used before ("used: VW-5") or already in my voices |
| Pager | 20 rows a page; "1–20 of 412"; the next 100 fetched when the pager crosses a 100 boundary |
| Sticky footer | the docked player, the tryout tray (names, "n of 6", the passage) and the one button with its cost; disabled with the reason beside it when no passage is recorded; the seventh + is refused with a line |
| Save to my voices | not a separate button: the + adds the voice to the tryout and the tryout saves it to the account when it runs (defect 16); the row then shows "in my voices". A "save" item sits in the row's ⋯ menu for the operator who wants a voice saved without trying it |
| Nothing else | no count of the whole catalogue, no refresh, no wait message, no account line in the header |

Steps 2 to 4 are in the table of section C; their server functions are design/54's (tryout, narrate_many, tweaks, finalise), with one addition: `narrate_many` accepts voices that were not tried when they are in my voices (the gate is the cap of three and the recorded direction, not a tryout).

## D. Chat path
`vw voice catalog` calls the same search: `--search`, `--language`, `--accent`, `--gender`, `--age`, `--use-case`, `--sort`, `--page N`, `--tab mine|favourites`; prints 20 lines and "page 2 of 21: --page 2", and the page link with the same filters. `vw voice preview` unchanged.

## E. Unstated but expected
- A provider outage shows "the voice library did not answer; try again" on the page; nothing else breaks.
- The operator's filters live in the page's address, so a link from the assistant and a browser reload land on the same list.
- The register (favourites) and the usage directory are unchanged; the directory page `/voices` lists them as before.
- Trial runs are disposable: nothing migrates; the mirror table is dropped empty of any meaning.

## F. Edge cases
| Case | Expected |
|---|---|
| no filter, first open | trending voices in the narration language |
| search "santhi" | matches by name within the current tab |
| a filter with zero matches | "No voices match. Loosen a filter." with "clear all" |
| the seventh + | refused with a line; the tray stays at six |
| ▶ on a second row | the first stops |
| page 6 (rows 101–120) | the second 100 fetched, then shown |
| provider 429 or 5xx | the message line, the previous list stays |
| a favourite no longer in the account | shown in Favourites as "missing from my voices" with "save again" in its ⋯ menu |
| Narrations opened before any tryout | "No narration yet. Tick voices on Try and press Narrate." |
| a known voice narrated without a tryout | allowed; the row says "narrated without a tryout" |
| ▶ pressed while another voice plays | the docked player switches; the first row's ⏸ returns to ▶ |

## G. Tests (written first)
Server unit: `search` query building for each tab and filter (provider request params), the compact row join, the two-minute cache key, the 20-of-100 paging arithmetic; `vw voice catalog` line format and `--page`. Docker: the search endpoint with the provider faked (two pages, `is_added_by_user`), favourites tab, zero matches. Migration 008 drops the mirror.

## H. Not covered
server/tests on this Mac; the look is reviewed by SK on VW-6 at `/voices2` before it replaces `/voices`.

## I. Estimate
Server search and the chat catalog, half a day. The four-step page with the frame (sticky line and footer, docked player, zebra tables), one and a half days. Removal of the mirror, an hour. Tests throughout.
