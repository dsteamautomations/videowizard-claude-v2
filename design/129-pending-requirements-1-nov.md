# Pending and parked requirements, 1 Nov 2026

From the VW-12 review (design/126) and this session's defect work, 30 Oct – 1 Nov. Live today: server 0.77.9, plugin 0.64.4, main 1a417ab.
Everything deployed since 30 Oct is **not** listed: defects 35, 37, 38, 40, 41, 42, G2, the sweep W1–W13, design/128.

Mark the **SK** column (go / hold / drop) for each record you want taken up.

## A. Deployed 1 Nov 2026 (main 221b0bb: server 0.78.0, plugin 0.65.0, minimum tool 0.65.0), with TR1b and TR3

The branch was brought up to date with main, TR1b and TR3 were added, and main was fast-forwarded to it. Not verified: U1–U7 clicked in a browser (the live page data could not be read here; the scripts parse and the page loads without errors), and the Docker suite.

Agreed on 30–31 Oct, built by three builders, never deployed. The branch was cut **before** every hotfix, so it must first be brought up to date with main (35–42, W1–W13, design/128) and tested again. Deploying it changes both the server and the plugin, so every laptop has to update its plugin.

| # | Change | SK |
|---|---|---|
| ST1 | A film with no picture AI is refused (no silent GPT Image) | |
| ST2 | "(as in v1: …)" removed from the start paragraph | |
| IN1 | Intake wording (design/126 1.x) | |
| BR1–BR3 | Brief prompt trimmed 1,060 → 973 words; "recommendation" stated in the reason | |
| SC1–SC5 | Script stage wording; the "defer" paragraph in plain words; the script answer shape | |
| ME1 | The footage guess at media retired (measured at visuals instead) | |
| AN1 | Analysis starts without asking again | |
| OP1–OP4 | Options: related pieces on one line; a scene lists every chapter (P7 retired); chapter warning for information; dashes and quotes on the cards | |
| MA1 | A rejected shot's gap says what was turned down and why | |
| VI1 | The chat tool's message points to the part's reading list | |
| TR1 | Treatment warns on a graphics run over 8 s | |
| TR2 | Every estimate uses the film's own picture price | |
| U1–U7 | Users' page issues: the list scrolls to the playing shot; the × always visible; a note saved with its picture; zoom; search up to 12 words; upload when search finds nothing (in the picture's panel); where a picture is used | |

**TR1's open question, decided (SK, 1 Nov: "Yes, count drawn"):** the plan's 8 s graphics run counts drawn shots too (TR1b, not built yet; VW-12 keeps today's rule). The plan never warned on VW-12's four drawn runs because the rule left drawn out.

## B. Agreed, not built

| # | Change | Work | SK |
|---|---|---|---|
| TR1b | The plan's graphics run counts drawn shots (approved 1 Nov); VW-12 keeps today's rule | `visual_contract.py`, one test; build with TR1 on the branch | go (1 Nov) |
| TR3 | The treatment gives the plan's two other length warnings: AI video back to back over 12 s, and a still over 4 s | server, one test (VW-12's treatment gives 2 + 1) | |
| PL1 | No brick figure ("3 : 1.5 : 1") as the example, in the plan instructions or the server's warning | one wording change in v3, one in `visual_contract.py`, one test | |

## C. Proposed, waiting for your decision

| # | Proposal | My recommendation | SK |
|---|---|---|---|
| F37b | `vw visuals spec --file`: put a revised spec in without editing the whole plan by hand | **Drop.** The plan download route (defect 37) already keeps accepted gaps accepted, and it also covers sizes, which F37b would not | |
| D39 | The tool's first file download retries like the other requests, and treats a network timeout as "run it again", not a defect | Take up. Small change, and it stops defects being filed for a bad connection (39 was one) | |
| G1 | The plugin's guard steps aside by itself outside the operator folder, so nobody needs the desktop "Vw off" switch (which is not working for the users) | Take up. A few lines; removes the workaround | |
| P4 | The second look (7.6) leaves a mark on the server, so you can see whether it ran and what it fixed | Hold until a film shows the need | |
| S1 | New finding: after a server wording deploy, the operator's instruction files stay old until `vw visuals prepare` is run again | Not written up yet; I would propose the smallest fix if you want it | |

## D. Old ways due for retirement (design/35)

| Row | Older way | When | SK |
|---|---|---|---|
| 9, 10 | VW-11's old slide rows and declared gaps | **due at the next release** (VW-11 closed 30 Oct) | |
| 13 | The empty `footage_character` field | next release that touches media (ME1 covers it) | |
| 15 | Docker tests that still use the retired planning stage | the next build with Docker running | |
| 17 | The take prompt without a timeline, kept for VW-12 | when VW-12 closes | |

## E. Watch items (no build)

- Drawn cutaway beside an AI graphic sequence (gap 4-B1): do they read as one style? Seen at the pictures.
- Reference pictures are not in the treatment's estimate (TR2): seen at the plan.
- Whether the plan helpers and the second-look helpers ran on VW-12: not recorded on the server.
- The first new run after design/128: are the plan's beats fine enough for the timeline to help?

## F. The review itself

Paused at visuals Phase 3, item 9.3.4 (the items). Phase 4 (pictures, takes, drawing) not reviewed yet.

## G. New requirement UX1: the visuals page as slides (SK, 1 Nov 2026; built on branch `ux1`, server 0.78.1, not deployed)

**Build, 1 Nov:** the page keeps every step view and adds the rail (cards per step, with an "All" card for the whole step as before), the stage that shows the chosen card, version tabs in the panel (pictures and takes), the coloured message bar with History, the rail width (200-360 px, remembered) and the up and down arrow keys. Tests: `server/unit/test_ux1_page_pure.py` (every action, id and data attribute of the old page; every request body; the new pieces), 958 server tests pass. Browser check on test data: the old and new pages clicked side by side sent the same 17 requests (approve, reject, reject-take, reject-take-why, select-take, t-accept, t-back, treatment); the other actions are checked by their request text only (test 5). Not checked: VW-12's real data (reading it from the VM was blocked), References with a live search round, the Docker suite.

Source: SK's note and a screenshot of `/runs/VW-12/visuals#takes/…`. In the screenshot, the graphic style card fills the left column and leaves empty space beside its picture. The take's player sits alone on the right. The whole page scrolls.

### Requirement

Redesign how the visuals page (`server/app/templates/visuals.html`, six tabs: Treatment, Plan, References, Pictures, Takes, Record) is laid out, **without removing or changing any function it has today**. The model is PowerPoint:
- **Left rail ("slides"):** one card for each thing to look at in the current tab, in film order. It scrolls on its own.
- **Right stage:** the selected card's content in full, laid out to be read at once, with its decisions. Clicking a card replaces the stage.
- **No whole-page scroll.** The top bar (tabs, spend, "N waiting", Next waiting) and the message bar stay fixed. Only the rail scrolls, and the stage scrolls only if its content is longer than the screen.
- **Versions:** when a picture or take is fixed or made again, the newest version is in front. Older versions sit in tabs named so that new and old are obvious, each with its rejection reason.
- **Messages:** what the page is doing and what the user must do, in colour, in one place that is always in sight.

### What each tab's rail and stage show

| Tab | Rail cards | Stage for the selected card |
|---|---|---|
| Treatment | Direction, then one card per gap line | the line in full, its shots (route, seconds), its warnings (TR1/TR3), Accept / send back |
| Plan | Foundation, graphic style, then one card per gap | the gap's shots with their warnings and answers, Accept |
| References | Graphic style, then one card per element (badge: needs a picture / pictures to approve / sheet to approve / sheet approved) | the element's search round (the web results grid, ticks, notes, Save), its own upload, frames from the footage, the sheet beside its sources |
| Pictures | Graphic style, then gaps → shots (thumbnail, route, seconds, state) | the shot's picture(s) large: start and end pair, the states of a sequence, a still. Beside them: the check, the fix (with price), the note, Approve / Reject / Use for the shot / Remove, and where in the film the picture is used |
| Takes | gaps → shots (thumbnail of the newest take, state) | the player (or the drawn shot's frame sheet), the take check, the checklist, Select / Reject with a reason, Download |
| Record | one card per gap (recorded or not) | what the gap holds and what is still missing, Record |

### The rail
- **Width:** 260 px by default, so a 16:9 thumbnail of about 228 × 128 px plus two lines of text fits. The user can drag it between 200 and 360 px; the page remembers the width on that computer only. **Desktop only (SK, 1 Nov 2026):** built for 1366 × 768 and larger; no phone or tablet layout.
- **Each card shows:**
  - a thumbnail;
  - a short title, such as `03-B2 · sh2 · Still · 5.6 s`;
  - one coloured state badge;
  - a dot when it waits for the user;
  - a spinner while something runs on it.
- **Grouping:** cards are grouped under their gap, and a gap's group can be collapsed.
- **At the top of the rail:** chips for All / a gap / **Waiting for me**.
- **Keyboard:** ↑ and ↓ move between cards, as in PowerPoint.

### The stage
- **Wide screens:** two columns. The picture or player takes about 60 % of the width. The facts, check and decisions go in the other column. The decision buttons stay pinned at the bottom of that column.
- **A desktop window narrower than 1280 px:** the stage goes to one column, picture first; the rail keeps its width.
- **Nothing hidden:** every state an item can pass through is shown on the stage and on its card: queued, generating, checking, fix queued, failed (with the reason), waiting for storage, ready, approved and placed, rejected, recorded.

### Versions (pictures and takes)
- **Tabs above the picture:** "Version 3 · new" (in front), "Version 2 · rejected", "Version 1 · fixed into version 3". A fix is named "fix of version 1".
- **On an old version's tab:** the rejection reason and the user's words, in red.
- **Takes** work the same way: "Take 2 · new", "Take 1 · rejected: …".
- **Order:** versions are numbered by the time each was made, from what the page already receives (`fix_of`, `parents`, `status`, `rejection`, `reviews`). No server change.

### Messages
- **One fixed message bar under the top bar,** replacing the line at the foot. Its colours:
  - **blue**, with a spinner: working ("Generating 3 pictures…");
  - **green:** done;
  - **red:** refused or failed, with the server's own reason;
  - **amber:** waiting for you ("2 pictures wait for your verdict: Next waiting").
- **History:** the last 5 messages can be opened from the bar.
- **On the stage:** a red refusal also stays on the stage of the item it concerns until the next action on that item.

### Unstated but expected
- Every link that works today keeps working, such as `#takes/<shot>/<job>`. Selecting a card updates the address, so a link opens on that card.
- The page refreshes itself every few seconds, as today. A refresh never loses the selected card, the rail's scroll position, ticked web pictures or a note being typed (today's `unsavedTicks` protection).
- The zoom viewer, the search round's Save and Done bar, "Add your own picture", "Try a fix (₹…)" and the reason chips all stay. They only move.
- Dark theme as today. Readable at 1366 × 768, the operators' laptops.
- **One flow, two front ends:** no new step, so the chat tool (`vw`) does not change.

### Edge cases and how each is handled

| Case | Handling |
|---|---|
| A tab with nothing yet (no plan, no takes) | the stage says what comes next and which command or button starts it; the rail shows one card "Nothing yet" |
| The selected item disappears after a refresh (deleted, regenerated) | select its newest version, or else the next card waiting; the message bar says so |
| 100+ pictures in References | thumbnails load as they scroll into view (lazy), and the rail stays fast |
| A long title or element name | cut with "…"; the full text appears on hover and on the stage |
| A picture or video that fails to load | the card shows "picture not available" and the stage offers the link; nothing breaks |
| A graphic sequence (2–4 states) or a start/end pair | side by side on the stage, as today, each with its own version tabs |
| A take still being generated or waiting for storage | the card has a spinner; the stage shows the state and the time it was asked for |
| Two people on the same run | each sees the other's decisions at the next refresh; a refused action says why |
| The refresh fails (network) | amber: "not refreshed since 14:59; retrying"; the decisions already on screen stay |
| An action refused by the server | red on the bar and on the item's stage, with the server's words |
| A desktop window narrower than 1280 px | the stage is one column; the rail keeps its width (no phone or tablet layout, SK 1 Nov) |

### Everything that works today keeps working (SK, 1 Nov 2026)
- **Only the layout changes.** The server routes, the requests the page sends, the data it reads and the refresh stay exactly as they are. No server code changes and no plugin change.
- **The working code is reused, not rewritten.** Today's pieces that build each picture, take, check, checklist, reason box, fix button, search round and viewer (`panel`, `checklist`, `takeCheck`, `reasonBox`, `fixBtn`, `renderRound`, `openViewer` and the rest) are placed on the rail and the stage. They are not written again.
- **An inventory before the build:** every control, action, keyboard key, address (`#tab/…`) and automatic behaviour of today's page (refresh, unsaved-tick protection, Next waiting, zoom), listed in a checklist. Each line is ticked after the build with where it now lives.
- **Same click, same request:** for every action, the request today's page sends and the request the new page sends are recorded in the browser check and must be identical.
- If anything cannot be kept as it is, it is raised with SK before the build, never dropped quietly.

### Failure modes
The page only shows what the server sends, and every decision still goes through the same server routes. So a layout fault can hide or misplace something, but it cannot change data. Tests 1 and 5 guard against that.

### Tests first
1. **Every control that exists today exists after the change:** a pure test lists every `data-a` action, every button and input id, and every address form in today's `visuals.html`, and checks each one is still present.
2. **The version order:** from a set of references with `fix_of`, rejections and times, the page's version function gives "Version 3 · new / 2 · rejected / 1 · fixed into 3". The same for takes.
3. **The rail cards:** for VW-12's data, the cards per tab and their badges, including **Waiting for me**.
4. **A browser check on a local copy of the page** with VW-12's data (the method in memory "VW2 page browser check"):
   - at 1920 × 1080, 1366 × 768 (desktop only);
   - each tab opened;
   - every action button clicked once against a stub;
   - refresh with a ticked picture and a typed note: nothing lost;
   - screenshots for SK.
5. **Same click, same request:** the old and new pages are opened side by side on the same data with a stub server. Every action is clicked on both, and the route and body each one sends must be identical. Any difference fails the test.
6. **The existing tests that read `visuals.html`** (server/unit, for example design/100, 101, 103 and defects 28–30) still pass unchanged.

### Order and lane
- **It goes after the `design126-build` branch.** U1–U7 on that branch change this same page (close button, saving notes, upload in the panel, search length), so UX1 is built on top of it, not beside it.
- **Server deploy only:** the page is served by the server, and the plugin does not change.
- **Mockup approved (SK, 1 Nov 2026: "Layout approved"):** `../ux1-mockup/index.html` (Pictures and Takes with VW-12's real pictures and takes; kept out of git, it holds the client's pictures). The build follows it for all six tabs.

### Old way (design/35)
The scrolling visuals page is **retired at the UX1 deploy**, with no switch back. The same functions stay on the new layout, so nothing is lost.

### Not covered
- The other pages (`run.html`, `review.html`, voices): out of scope unless SK asks.
- Drag to reorder cards: the film order is fixed by the plan.

## H. SK's decisions, 1 Nov 2026

| # | Decision |
|---|---|
| F37b | **Drop** (the plan download covers specs and sizes) |
| D39 | **Build**: the first file download retries; a network timeout says "run it again", not a defect |
| G1 | **Build**: the plugin's guard acts only in the operator folder |
| P4 | explained to SK; decision pending |
| S1 | **Wait** for SK's tech person |
| Old ways 9, 10 (VW-11's slide rows and declared gaps) | **Retire** in the next release |
| VW-12 review | **Stopped**: VW-12 is a trial run, not completed; SK deletes it soon. Then rows 17 and 18 (`OLD_PROMPT_RUNS`, `OLD_PLAN_RULE_RUNS`) are emptied. |

D39, G1 and the retirement of rows 9 and 10 go in one release (server and plugin), so the laptops update once. Requirements note first, for SK's approval.

## I. The release after UX1: P4, D39, G1, old ways 9 and 10 (SK, 1 Nov 2026: "build the second record. go ahead with all other approvals")

### P4 — the second look leaves a record
**Requirement:** when `vw options join-second-look` succeeds, the tool writes a short record into out/options.json: when, how many scenes, which scenes changed and which stayed (with the helper's reason), the scenes with no fix file, each fix (scene, option, the helper's reason), and a fingerprint of the options as joined. `vw options propose` carries it to the server, which keeps it with that version (never in the cut's own fingerprint). The review page's top line says "Second look: ran 1 Nov 12:20 · 9 scenes · 4 changed …", or "Second look: not recorded for this version", or adds "the cut was changed after the second look" when the options proposed differ from the ones joined.
**Edge cases:** a version proposed without a join → "not recorded"; a join refused → no record (the file is untouched); a second join → the latest record replaces the earlier one; the operator edits options.json after the join → "changed after the second look"; a malformed or oversized record → kept as far as it is readable, lists capped, never a refusal of the cut; an older tool sends none → "not recorded".
**Older way:** a second look with no record: retired at this release (an older tool is refused by the minimum version).

### D39 — a dropped connection during a download is "run it again", not a defect
**Requirement:** the tool's first request of a file download (the server's link to the file) is retried like the storage part (5, 15, 30 s). When the network still fails, the tool says the operator's network dropped and to run the same command again, with action `unreachable`, not `tell_builder`. A server answer that is an error (HTTP status) still goes to the builder.
**Edge cases:** the link request times out once then works → the download continues; the storage part fails after its retries → "run it again"; a fingerprint mismatch twice → still named for the builder.
**Older way:** a crash ("unexpected failure") on a dropped connection: retired.

### G1 — the guard acts only in the operator folder
**Requirement:** the plugin's two hooks (the guard and the reminder) act only in a folder whose Claude settings (`.claude/settings.json` or `settings.local.json`, in the folder or a folder above it) name `VW2_SERVER_URL`, which only the operator folder does. Everywhere else they step aside, so the desktop app switching the plugin on everywhere no longer blocks other work.
**Edge cases:** the operator opens Claude in a sub-folder of the operator folder → still guarded; a settings file that is not valid JSON → read as text for the name; the builder checkout → steps aside, as today.
**Older way:** the desktop app's "Vw off" switch as the only way out: no longer needed (kept harmless).

### Old ways 9 and 10 — VW-11's leftovers
Both are already refused by name since the design/127 build (a cut in the old form, design/35 row 12; a declared gap, at propose). What is left: the version record still copies a declared-gap list, always empty since then. It is removed; rows 9 and 10 are marked retired.

### Lane and versions
Regular. Server 0.78.2, plugin 0.65.1, minimum tool 0.65.1 (the guard fix and the record reach every laptop with one update). Tests first, in server/unit and plugin/tests.

### Not covered
- The second look's quality: the record says what the helpers changed, not whether the changes were right.
- The Docker suite.

## G. Parked, added 2 Nov 2026

| # | Item | Waiting for | SK |
|---|---|---|---|
| PK1 | **Deploy of design/137 + design/139** (server 0.83.0, plugin 0.69.0, main db565b9): built, tested and pushed; deploy held | SK's go ("Not yet", 2 Nov) | parked |
| PK2 | The minimum plugin version at that deploy: it stays 0.66.0 (films already running work with any plugin), or is raised to 0.69.0 (every laptop updates first; a new film needs 0.69.0 for `vw category` and `vw shape`) | decided at PK1 | |
| PK3 | A short vertical test film before a client's: the cut, the editor's package and HyperFrames have never made one | after PK1 | |
| PK4 | The voices page sliders seen working with live data (only checked for syntax so far) | after PK1 | |
| PK5 | A font for Tamil and Hindi labels in drawings (Noto Sans's file does not draw them) | a film that needs it | |
| PK6 | One shot-guidance line still names construction traces ("mortar droppings", `visuals_stage.shot_guidance`, B8): make it generic | the next clean-up | |
| PK7 | Vertical short videos cut from a horizontal film (design/138 A1) | a future update | |
| PK8 | Square and 4:5 shapes (design/138 A3) | a future update | |
| PK9 | The deploy script's restart order (the server stays down while the workers drain; the 2 Nov outage) | SK ("Not now", 2 Nov) | |
| PK10 | Empty OLD_PROMPT_RUNS and OLD_PLAN_RULE_RUNS once VW-12 is deleted | VW-12 deleted | |
| PK11 | Review of Codex's round 2 findings (codex-review/process-findings.md, committed 21713c2) | SK's time | |
