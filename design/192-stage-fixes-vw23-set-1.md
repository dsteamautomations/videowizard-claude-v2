# 192 — VW-23 stage fixes, set 1: intake, brief, script, voice (requirements)

14 Nov 2026. Source: `design/_work/stage-fixes-VW-23.md`. This set holds only rows already approved by Deepa on 13 Nov:
intake 1 to 8, brief 1 to 5 and 7, script 1, voice 1, 2, 4 to 7 and 11. Nothing here is built until this list is approved.
The pronunciation set (voice 8, 16 to 19) is a separate list with a design first. Rows not yet approved are asked one at a time.

Built on branch `worktree-stage-fixes-vw23`. Not deployed, not merged. Instruction text changes are made in version 3 only
(`server/procedures/v3.json`, by one script `scripts/d192_wording_v3.py`); a film on version 2 keeps its text.

## A. What changes, row by row

### Intake

| Row | Change | Where |
|---|---|---|
| 1 | New first command `vw last`. It needs the sign-in, so a laptop that is not signed in is told to sign in before any question is asked. The instructions say: on "new video", run `vw last` first; on "resume", run `vw next` or `vw pull` first (they already need the sign-in). | `plugin/scripts/vw.py`, `plugin/commands/vw.md` |
| 3 | `vw last` also answers this operator's last run: client, picture AI, drawn route. The assistant offers "Same as last run: <client>, <picture AI>, <drawn route>" as the first answer to click; the other answer is "Different". The start command is unchanged (`vw start --client … --images … --drawn …`). | `vw.py`, `vw.md`; server: the run list also carries picture AI, drawn route and owner |
| 2 | One question with three parts, each with a recommended answer to click: the title, the approval of the cleaned script, the category. One record: `vw stage intake record --title … --category … --quote …`. The recommended category is the one this client's last film recorded, when there is one. | `vw.py`, v3 intake steps, `vw.md`; server: run creation also answers the client's last category |
| 4, 5, 6 | Intake text: examples from several kinds of film, no project named; the title rule says "name the subject and what the film is" with examples from three categories; "The document may be a bare script or a plan around one." | v3 intake prompt |
| 7 | The no-rewrite rule stated once, in plain case. Added: a line that looks mistyped is listed in `notes` with its line number; it is never changed. | v3 intake prompt |
| 8 | The log gets: one entry when a text stage is prepared (intake, brief, script); one entry for each question asked with the question tool in those stages, and one for its answer. The category is logged under intake. | `vw.py`, `plugin/hooks/guard.py` and a new hook after the question tool, `server/app/runlog.py`, `main.py` (two new entry kinds) |

### Brief

| Row | Change | Where |
|---|---|---|
| 1 | The brief prompt gets the film's category and a short block of defaults by category (ending, examples). | v3 brief prompt, `stages_text.brief_prepare`, `vw.py` |
| 3 | "Never add a sales call to action by default" becomes: the ending follows the category unless the operator says otherwise (advertisement: an action for the viewer is the default; documentary, training: no sales action by default; social and story: what the script ends on). | v3 brief prompt |
| 2 | When the client has a latest brief: its production values (brand and safety rules, speaker on camera, where it plays, watched muted, target length) are shown filled in, and the one approval question has the first answer "Same as last time, approved". That one answer covers the production values and the approval of the brief. | `brief_prepare` (a ready `same_as_last` block; where it plays added to what is read from the last brief), v3 brief steps |
| 4, 5 | Chapter examples: one process example and one non-process example. Brand and safety examples from more than one category. The same in the tool's refusal message that names a chapter example. | v3 brief prompt and steps, `stages_text.py` |
| 7 | Covered by intake row 8 (prepare, questions and answers of the brief are logged; "Same as last time, approved" is logged as the answer). | — |

### Script

| Row | Change | Where |
|---|---|---|
| 1 | The five parameters, as rules of the script step: (a) always propose a check for any number, quantity, duration, percentage or cost; (b) always for a safety or structural claim; (c) for a comparison or saving when a graphic will show it; (d) never for what the footage itself shows; (e) one question for all checks, the claims listed with a tick each. Every claim under (a) and (b) is listed in `claims`, checked or not. | v3 script prompt and steps |

### Voice

| Row | Change | Where |
|---|---|---|
| 1 | A narration asked again with nothing changed (same voice, model, settings, tags, text) is refused before any job row is made. The message says it would be the same recording as narration #n and names what to change for a new take: the settings, a sentence's tag, or (after the next set) a word's pronunciation. Same on the page and in the chat. | `server/app/jobs.py` (`submit_voice`), page message |
| 7 | A recording reused from the server's store is not counted as a new cost: the job's cost counts only the pieces this job paid for, and says how many were reused. | `server/app/worker.py` |
| 2, 6 | The direction step proposes one recommended test passage (two more only on request). The assistant asks one question whose first answer is "Best fit, passage 1"; the two lists are shown only on request. | v3 voice steps and direction prompt, `vw.py` messages |
| 5 | The kind of film is the run's category: given to the direction step, stated, never worked out again. The recorded direction keeps it. A film with no category recorded (started before categories) keeps today's way. | `vw.py` (`voice direct prepare`), `voices.record_direction`, v3 direction prompt |
| 4 | Every page link the tool gives the operator (voices, review) carries a one-use sign-in ticket made from the laptop's own sign-in, valid 10 minutes. Opening the link signs the browser in and lands on the page. A used or expired ticket falls back to the sign-in page as today. | `vw.py`, `server/app/web.py`, `auth.py`, `main.py` |
| 11 | The tag box: the page adds the square brackets itself, offers the allowed tags as a list to pick from (typing another is allowed), and checks the tag before sending with a plain message. The server adds the brackets too, so the chat command behaves the same. | `voices2.html`, `voice_direction.py`, `voices.set_tweaks`, page data |

## B. Unstated but expected

1. One flow, two front ends: voice 1, 7, 11 and the brackets live in the server functions the page and `vw` both call.
2. Every change states its older way (section E) and gets a row in `design/35-decision-log.md`.
3. All new text suits every category of video; no example names an earlier film.
4. `plugin/` stays Python 3.9 compatible; every file keeps its own line endings.
5. The new tool needs the new server and the new text needs the new tool (the brief prompt's category, `vw last`, the ticket). The plugin minimum version must be raised at the release; the version numbers are left to the master thread at merge.
6. A log entry never blocks or delays a question: the hook starts the log call and does not wait for it; a failure is silent.
7. Only the question's text and the chosen answer are logged (each cut at 300 characters), never a prompt or a file.
8. The sign-in ticket is never printed in the run log; the tool's guard log is unchanged.
9. Voice 4: the cause of the second sign-in in VW-23 is not known from the log (the browser session lasts 7 days; possible causes: the link opened in another browser or profile than the one used to connect, or the cookie was not sent). The ticket link removes the second sign-in in each of these cases; it is not a diagnosis.

## C. Edge cases

| # | Case | Handling |
|---|---|---|
| 1 | `vw last`, laptop not signed in | The usual "connect" answer: sign in first; nothing else is asked. |
| 2 | `vw last`, this operator has no earlier run, or the last run has no picture AI recorded | No "same as last run" answer is offered; the questions are asked as today. |
| 3 | The last run's client is no longer Active | `vw start` refuses as today (`CLIENT_UNKNOWN`); the assistant asks for the client. |
| 4 | An administrator's run list holds everyone's runs | "Last run" is the newest run this user owns. The team shares SK's sign-in during testing (intake row 9, closed 14 Nov), so today it is the last run under that sign-in, whoever operated it. |
| 5 | `--category` not a category | Refused before the intake is recorded; nothing is recorded. |
| 6 | `--category` given, intake record then refused (source changed, title missing) | The category stays recorded (it can be changed until the visuals stage starts); the message says the intake was not recorded. |
| 7 | `--category` left out | Intake is recorded as today; `vw category` stays for recording or changing it; the brief still waits for it. |
| 8 | Client with no earlier film | No recommended category from history; the assistant recommends from the script as today. |
| 9 | Brief on a film with no category (an older film) | The prompt says "not recorded"; the ending rule falls back to "no sales action unless the script or the operator asks". |
| 10 | Client has no latest brief | No "same as last time" block; the production values are asked in one message as today. |
| 11 | The last brief lacks a value (an older brief without "where it plays") | The block shows that value as "not asked last time" and the assistant asks only for it. |
| 12 | Operator answers "changes" instead of "Same as last time, approved" | The file is edited and the one question asked again, as today. |
| 13 | The chapters | Never taken from the last brief (existing rule, kept). |
| 14 | A script with no number, safety claim or comparison | Zero claims and no check question is a valid result. |
| 15 | A number spelled in words ("two weeks") | The rule names it: a number in digits or in words. No program check (see D4). |
| 16 | Narrate again, nothing changed, earlier narration ready | Refused, no job row; the refusal is in the run log. |
| 17 | Narrate again, nothing changed, earlier narration failed or set aside | Allowed (it is a retry, and stored pieces are reused without a second charge). |
| 18 | Narrate again, earlier one still running | Refused as today (`JOB_OPEN`). |
| 19 | Narrate again after a change of settings, tag, direction or script | Allowed; a new recording. |
| 20 | Narrate again after only the pronunciation list changed | Until the next set (voice row 8) the stored recording would still come back; in this set it is refused as "nothing changed" only if the list version is also the same; with a changed list it is allowed. Row 8 then makes it a new recording. |
| 21 | A long script in pieces, some pieces stored, some new | The cost counts only the new pieces; the result says how many were reused. |
| 22 | A stored piece made before this change (no record of which job paid) | Counted as reused when it existed before the job began. |
| 23 | Direction file with one passage | Accepted (the server already allows one to three). `--passage 1` is the default answer. |
| 24 | Operator asks for the lists or more passages | The assistant shows them; two more passages are added to the file and proposed. |
| 25 | Ticket link opened twice, or after 10 minutes | The sign-in page, as today; after signing in, the page opens. |
| 26 | Ticket cannot be made (server error) | The plain link is given; the page asks for the sign-in as today. |
| 27 | Ticket link opened in a browser already signed in as someone else | The browser is signed in as the laptop's user (the link's owner). |
| 28 | Tag typed with brackets, without, with spaces or capitals | Brackets added when missing; spaces trimmed; sent as typed otherwise. |
| 29 | Tag names a reaction, a pause or an accent, or is longer than 60 characters | The page says so before sending, in the server's words; nothing is narrated. |
| 30 | Empty tag box | Unchanged in this set (voice row 9 is not yet approved); with voice 1 built, the click is refused as "nothing changed" instead of returning the old recording. |
| 31 | A question asked in plain chat text, not with the question tool | Not logged. The steps say to use the question tool for the stage questions. |
| 32 | Question tool used outside intake, brief and script | Not logged by this change (those stages log their decisions already). |
| 33 | No active run when a question is asked (before `vw start`) | Nothing is logged; no error. |

## D. Failure modes

| # | Failure | Handling |
|---|---|---|
| 1 | The log call fails or the server is slow | The question is not delayed; the entry is lost; nothing is shown to the operator. |
| 2 | The category is recorded but the intake record fails in the network | The retry records the intake; the category is already there (recording it twice is harmless). |
| 3 | An old tool with the new server text | It would show the literal `{category}` line in the brief prompt. Prevented by raising the plugin minimum at the release (B5). |
| 4 | The assistant still skips a figure at the script stage | Not caught by a program: the rule is text only, by the standing preference for the cheapest control. Listed under "not covered". |
| 5 | The worker cannot tell whether a stored piece was paid by this job | It is counted as reused only when the piece's record names another job or predates this job; otherwise as paid (never under-reported as free by mistake on a fresh piece). |
| 6 | Ticket exchange fails halfway | No session is made; the sign-in page is shown. |

## E. Older ways

| What | State after this set |
|---|---|
| The category asked in its own turn after intake (`vw category`) | Kept for recording or changing the category later; no longer the default at intake. |
| Client, picture AI and drawn route asked on every start | Kept when the operator answers "Different" or has no earlier run. |
| The intake prompt's single-film examples, the fixed title example, the capitals | Retired. |
| "Never add a sales call to action by default" | Retired; the ending follows the category. Kept for a film with no category. |
| Production values asked in one message on every film | Kept for a client with no earlier brief; otherwise one approval with "Same as last time, approved". |
| One sentence deciding every claim check | Retired; the five parameters. |
| A repeated narration returning the stored recording as a new row | Retired; refused with what to change. |
| A reused recording showing its full character cost | Retired. |
| Three test passages and both lists always presented | Retired as the default; shown on request. |
| The kind of film worked out by the assistant at the direction step | Kept only for a film with no category. |
| The voices page asking for its own sign-in | Kept as the fallback (a used or expired ticket, a link typed by hand). |
| A tag accepted only with square brackets typed by the operator | Retired. |

## F. Tests (written first)

- `plugin/tests`: `vw last` (signed out, no earlier run, earlier run, administrator's list); intake record with `--category` (valid, invalid, left out); brief prepare with the category and the `same_as_last` block (no last brief, a value missing); the direction prepare carries the category; the page link carries a ticket and falls back; the hook logs a question and an answer and stays silent outside the text stages; the changed refusal text.
- `server/unit` (no database): the same-recording check; the cost of reused pieces; the tag with and without brackets; the suggested tag list passes the tag check; the log entry kinds; the category logged under intake; the wording script applied once and its anchors found once; no retired sentence left in the v3 text.
- `server/tests/check_*.py` (no database): the ticket exchange and the narrate refusal through the route functions with a stand-in store.
- `server/tests` proper needs Docker, which is not running on this computer; if it stays so, those are listed as not run.

## H. Built, 14 Nov 2026 (SK: "Approved. Go Ahead and build it. Perform only unit tests")

Every row of section A is built on branch `worktree-stage-fixes-vw23`. Not merged, not deployed.

**Tests (run by Claude on this computer, Python 3.12).** Unit tests only, by SK's word.
- New: 74 tests in `unit-local/` (kept out of git by SK's word; the folder is in `.gitignore`): 74 pass.
- Existing `server/unit`: 1494 pass, 4 fail, 4 skipped. The same 4 failed before the change (`test_design125_stage7_c_pure`, `test_design130_p1_pure`, `test_design151_refs_pure`, `test_g2_plugin_minimum_pure`).
- Existing `plugin/tests`: 469 pass, 7 fail. The same 7 failed before the change (Windows paths and line ends, and the visuals page link).
- Two existing tests were changed because they assert what this set retires: `server/unit/test_design126_wording_pure.py` (the capital-letter intake wording) and `plugin/tests/test_stage_calls.py` (the prepare now writes one log entry).

**Review for effects on existing flows (after the unit tests).** Three things were found and fixed:
1. Narrating several voices in one click: a refusal for one voice (nothing changed) would have undone the other voices' job rows while the page kept their entries. Now that voice is left out, the others are narrated, and the page says how many were left out.
2. The question hook would have started a second process before every tool call. It now runs inside the guard that already runs; only the answer side is its own hook, for the question tool alone.
3. A ticket link opened while the database is unreachable would have answered with an error page. It now falls back to the sign-in page.

Effects that remain, by design:
- The tool makes one more short server call at `vw next`, `vw stage voice prepare`, `vw voice direct record` and `vw voice catalog` (the ticket; it gives up after 10 seconds and gives the plain link) and at the prepare of intake, brief and script (the log entry; 5 seconds at most).
- The category is logged under intake also when it is changed later.
- The run list answers three more fields (owner, picture AI, drawn route).
- A changed pronunciation list still returns the stored recording until voice row 8 is built (next set); it is not refused as "nothing changed".

## I. Not covered

- `server/tests` (the database tests) were not run: Docker is not running here, and SK asked for unit tests only. `server/tests/test_voice_media.py` narrates the same voice several times and will need its expectations changed where nothing differs between two narrations.
- Nothing was tried on a real run, a real browser or an operator laptop: the ticket link in a browser, the voices page's tag list, the hook's log call from the operator folder (that the hook's process sees the server address and the sign-in is assumed, not seen).
- Python 3.9 is not installed on this computer; the plugin files were compiled with 3.12 and read for 3.9 syntax only.
- The claim-check rules, the one question at intake and "Best fit, passage 1" are instruction text; no program checks that the assistant follows them.
- A question asked as plain chat text is not logged.
- Version numbers and the plugin minimum are not changed; the release must raise the plugin minimum (an older tool does not know `--category`, `vw last`, and would show `{category}` in the brief text).
- Why the voices page asked for a second sign-in in VW-23 is still not known.

## G. Not in this set

Intake 9 (closed 14 Nov, no change: SK's sign-in is shared on purpose during testing); script 2 to 4; voice 3 (withdrawn), 8 to 10, 12 to 19. Brief 6 is "no change".
