# 50 — The client card: what the directory knows about a client, carried through the run (specified 18 Oct 2026 during the VW-4 live run; built 20 Oct 2026 on SK's "do everything not withdrawn"; the reverse and symbol-only logos join `LOGO_FIELDS` when the directory gains their columns)

SK's instruction (18 Oct 2026, verbatim essentials): take up all the identified fields; the directory is being filled over time (logo, reverse logo and symbol-only logo are coming); identify where each value is got, where in the whole flow it can be used and passed; a missing value is never a failure; precedence is **what the operator says in chat > what the script says > what the directory says**, because a one-off film may go against the recorded audience; the assistant does what the operator wants and **always warns that it differs from the directory**. Nothing in the flow changes until this note is approved and built.

## A. Where the values come from
The shared directory (the v1 project's `clients` table, reached as today through `SHARED_SUPABASE_URL`, `auth.client_directory()`), one row per client. v2 reads three columns today: `client_id`, `client_name`, `status`. The card reads the row once, at `vw start`, for the chosen client.

Fill rates on 18 Oct 2026 across 139 Active clients: audience 54, description 53, USP 50, industry 60, location 47, website 117, YouTube 34, services 138, palette 137 (mostly empty lists), past learnings 139 (mostly empty lists), logo 2, CTA instructions 0, brand guidelines 0. VK Nardep has audience, description, USP, industry, location, services, website and YouTube; no logo, empty palette, empty learnings.

## B. The card
One JSON object, `client_card`, built by a new `auth.client_card(client_id)` from these columns. Every key is optional; a null, empty string or empty list is left out; texts are cut at 600 characters with "…", lists at 12 items; a jsonb field whose shape is unknown (brand guidelines, CTA instructions, past learnings, services) is carried as compact JSON text. The read never raises: any failure gives `{}` and a `card_error` string for the log.

| Group | Columns | Carried as |
|---|---|---|
| identity | `client_name`, `company_legal_name`, `dba_names` | names |
| what they are | `industry`, `business_model`, `client_description`, `services_products`, `usp`, `competitive_positioning`, `core_values`, `founding_story`, `notes` | profile |
| who they talk to | `target_audience`, `client_persona`, `geographic_markets_served` | audience |
| where they are | `client_location`, `country_addresses` (countries only), `time_zone` | place |
| how to reach them | `website_url`, `secondary_domains`, `phone_number`, `email_address`, `map_url`, `instagram_url`, `linkedin_url`, `facebook_url`, `twitter_x_url`, `youtube_url`, `pinterest_url`, `tiktok_url`, `social_sharing_platforms` | contact and destinations |
| what they ask for | `client_cta_instructions` | cta |
| how they look | `client_logo_url` (and the reverse-logo and symbol-only columns when they exist; names to confirm), `color_palette`, `typography_fonts`, `client_brand_guidelines`, `trademark_patterns` | brand |
| who they are not | `competitors` | competitors |
| what was learned | `client_past_learnings` | learnings |

Not taken (no use in a film, or private): `gst_number`, `billing_contact`, `monthly_budget`, `billing_cycle`, `contract_start`, `contract_end`, `onboarding_date`, `account_manager`, `client_contacts`, `primary_contact`, `business_hours`, `tech_stack`, `ssl_status`, `utm_naming_conventions`, `auto_extracted_keywords`, `bucket_id`, `tags`, `status_history`, `geo_coordinates`, `field_values`.

## C. Where it travels
The same road as the last brief and the client rules (design/37 2.2, 2.3): `POST /api/runs` answers `client_card`; `vw start` keeps it in `runs/<code>/manifest.json`; the stage prepares print it; the brief record writes the card it showed into the brief output's `summary.client_card` (the plugin builds the summary, the server stores it in `vw2_stage_outputs.summary`, no migration); every later stage reads the card from the brief output, so one run has one card. Delivery re-reads the brand group live, because logos and palettes are being filled now and may arrive after the brief.

## D. Where each group is used, stage by stage

| Stage | What the card does there | Who reads it |
|---|---|---|
| start | `resolve_client` also matches `dba_names` and `company_legal_name` (exact, case-insensitive), so an alternative name resolves; the start line says how much the directory holds: "directory: 9 fields on this client" or "directory: name only" | server |
| intake | nothing new (titles never carry the client's name) | — |
| brief | the prompt gains a section **WHAT THE DIRECTORY SAYS ABOUT THIS CLIENT** (`{client_card}`) after the last brief: profile, audience, place, contact, cta, brand, competitors, learnings, each on its own line, "the directory has nothing on this client beyond its name" when empty. The rule, in the prompt and in the step: the directory's words are context for the recommendations, never answers; the operator's words come first, the script second, the directory last; when the operator's answer or the script goes against the directory, say so in chat ("This differs from the directory, which says …") and record it. Uses: audience → the audience recommendation names the directory's audience and the script's evidence side by side; description, USP, positioning, values → purpose and message context; cta → the ending recommendation when the ending wants an action; brand guidelines, trademark patterns, competitors → recommended brand and safety rules ("no competitor logos: X, Y"); location → a field-language hint only ("Tamil Nadu: Tamil likely; ask"); learnings → shown with the tool's own learned rules under "confirm, drop or add"; destinations (YouTube, Instagram) → a note for delivery, not a decision (design/49 L7) | plugin prompt, child |
| brief record | `out/brief.json` may carry `directory_differences: [{field, directory_says, chosen, decided_by: "operator"|"script", operator_words}]`; absent is fine; stored in the summary with the card | plugin validator, server |
| script | the prepare prints cta, contact and trademark patterns; the prompt allows CTA words only when the accepted ending asks for them, taken from the card and marked as the directory's, and uses trademark patterns for how the name is written and spoken; no other claim from the card enters the script (the prompt's "do not invent facts" stands) | plugin prompt, child |
| voice | nothing | — |
| media | nothing | — |
| analysis | `project_config` gains `client_profile` (industry, description, services, competitors, trademark patterns): competitors make pillar 7's competitor-brand risk flag concrete; trademark patterns help the on-screen text reading | server, model |
| options, master, first cut | nothing beyond the brief's rules (already carried) | — |
| visuals | the prepare passes the brand group with the brief: palette and guidelines shape generated pictures, competitors are never shown, no logo is ever generated; a real logo for a reference element comes from `vw brand fetch` (new: the server fetches the directory's logo files and the plugin saves them to `runs/<code>/in/brand/`), then `vw visuals supply --element E --file in/brand/<name>` as today | server, plugin, child |
| assembly | nothing: the film never carries a logo | — |
| delivery | the bundle gains `Graphics/` with the logo files the server fetches live (logo, reverse, symbol; skipped when absent or unreachable, with a line in the summary); the checklist gains Brand lines: logo files and the placement words from the brand guidelines or CTA instructions, palette, fonts, website and contact for the end card, destinations with their frame shapes (YouTube 16:9; Instagram, TikTok vertical or square); OPEN-EDIT gains a "Brand" section and lists the recorded `directory_differences` so the editor knows where the film departs from the directory. The editor places and sizes everything in Resolve (design/49 L9) | server |
| web pages | the run page shows the card's presence ("directory: 9 fields"), not the values | server |

## E. Precedence and the warning, exactly
1. The operator's words in chat decide. The assistant never substitutes a directory value for an answer, a decision or a constraint.
2. The script decides where the operator has not spoken: an audience, a message or an ending the script evidently addresses stands over the directory's.
3. The directory fills in only where neither has spoken, and then as a recommendation the operator approves.
4. Whenever 1 or 2 overrides 3, the assistant says in the same message: "This differs from the directory, which says: <value>. Going with your words / the script." and records the difference. The warning never blocks and is never repeated for the same field in later stages.

## F. Unstated but expected
- A directory outage after start changes nothing: the card lives in the manifest and the brief output.
- A client with an empty row gets a one-line card; every prompt section reads naturally with it.
- Long free text from the directory is cut, not summarised; the child reads what it sees.
- The logo variants' column names are confirmed when the directory gains them; until then only `client_logo_url` is read.
- Nothing from the card is ever written back to the directory.
- The analysis model sees competitors and trademark patterns as plain strings; a company name in a competitor list is not a secret.

## G. Edge cases
| Case | Expected |
|---|---|
| directory row has only the name | card `{}`; brief says the directory has nothing beyond the name; no warning possible |
| audience in the directory differs from the script's evident audience, operator silent | the brief recommends the script's, names the directory's, warns once |
| operator answers "audience: donors" against both | the answer stands; warning names the directory's and the script's |
| CTA instructions present, accepted ending has no action | the script adds no CTA; the checklist still lists the end-card details |
| logo URL unreachable at delivery | bundle without Graphics/, a line in the summary; checklist says "logo: not fetched (URL unreachable), take it from the directory" |
| `dba_names` matches, `client_name` does not | resolves to that client |
| two clients share a dba name | refused with candidates, as today |
| directory read fails at start | start succeeds, card `{}`, `card_error` in the start line |

## H. Tests (written first, when built)
Layer one, plugin: `brief_prepare` prints the section and the rule with a full card, a partial card and none; `brief_record` accepts with and without `directory_differences` and refuses a malformed list; the manifest keeps the card; the script prepare prints cta and trademark patterns only when present. Layer one, server unit: `card_of(row)` (truncation, empty values dropped, jsonb as text); `resolve_client` on dba and legal names; `checklist_of` Brand lines with and without the brand group; the analysis `project_config` with and without `client_profile`. Layer two (Docker): `POST /api/runs` answers `client_card` with the directory faked; the bundle fetches Graphics/ from a faked URL and survives a failed fetch.

## I. Not covered
- The real directory's jsonb shapes for brand guidelines and CTA instructions (none filled yet); the first filled row is the test.
- Resolve placement of the logo: the editor's, by SK's rule.

## J. Deploy order (when built)
Server, then plugin, then design/35 row; the operator restarts Claude Code.

## K. Estimate
Directory read, card, start and brief: half a day. Script, analysis, visuals passes: half a day. Delivery Graphics/ and checklist, `vw brand fetch`: half a day. Tests throughout.
