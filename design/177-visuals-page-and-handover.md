# design/177: the visuals page's one change, the hand-over with nothing redone, and both reaching the chat tool (11 Nov 2026)

One release, `release-next`: `main` plus the branches `handover-no-redo` and `ui-visuals-page`, plus the chat-tool commands for the page's new actions. Server 0.91.0, plugin 0.77.0; the minimum plugin version stays 0.70.0, so an older plugin keeps working (it only lacks the new commands). Built, not deployed: deploys are on hold without SK's yes.

## Why
- **The page.** SK walked the reference round on the visuals page on 11 Nov and reported U1 to U16 (counts that disagree, a waiting mark that does not say what waits, a tool command printed on a card, "No" as the way to get a set made, Done hit by accident, answers lost on a tab switch); reading the code found X1 to X7. A follow-up gave ten fixes, and round 3 added U17 (a verdict on one picture changed both ways), U18 (the pressed button shows it is working), U19 (the operator's own picture on a set's card) and U14 again. Requirements: `videobuilder-v4/phase2/ui/requirements-and-test-plan.md` (R1 to R24, E1 to E20); what was built: `videobuilder-v4/phase2/ui/build-report.md`.
- **The hand-over.** SK, 11 Nov: the DaVinci step is done on another PC, and taking a run over there must redo nothing; the next step offered is moving the files to DaVinci. Requirements: `videobuilder-v4/phase2/handover/requirements.md` (H1 to H7).
- **One flow, two front ends.** The page's new server functions could be reached only by the page's route. This note's own change gives each its API route and its `vw` command.

## The server functions (all in `server/app/visuals_stage.py`), their page action and their chat command
| Function | Page action (`/runs/{code}/visuals/act`) | API route under `/api/runs/{run}/visuals` | Chat command |
|---|---|---|---|
| `set_answer`: one answer of step 2 stored, not recorded until Done | `set_answer` | `POST /round/answer` | `vw visuals round --answer <element> --verdict yes\|no\|correct [--golden <picture>] [--words "…"]` |
| `set_make`: one set that was not made is made now (paid); refused while its cause stands | `set_make` | `POST /round/make` | `vw visuals round --make <element>` |
| `set_aside`: a never-made set set aside, or brought back while the round is open | `set_aside` | `POST /round/aside` | `vw visuals round --aside <element> [--words "…"]`, `vw visuals round --back <element>` |
| `reapprove_reference`: a rejected picture approved after all, until a later step used it (`verdict_lock` says why not) | `reapprove` | `POST /references/{ref}/reapprove` | `vw visuals approve --ref R --again [--sha S] [--quote "…"]` (the hash is read from the film when not given) |
| `supply_own`: the operator's own picture, stored approved; on a kept film never a person's photo; at most 15 MB; a picture | `supply` | `POST /own` | `vw visuals own --element E --file F` or `--url https://…` `[--name N]` |
| `round_sets` (changed): returns `held`, the answers whose remake the spend cap holds; a stored whole answer stands where the file names none | `round-sets` (partial) | `POST /round/sets`, as before | `vw visuals round --sets <file>` now prints `held` |
| `reject_reference` (changed): refuses a picture a later step used | `reject` | as before | `vw visuals reject`, as before; it prints the refusal |

Every new route goes through `_visuals_call` like its neighbours: sign-in, the run's lock, the visuals stage, one receipt per request.

**The hand-over (H1 to H7):** `core.next_for` reports what is done inside assembly and delivery (`stage3`, with the one next thing to do); `vw pull` prints it and says whether DaVinci Resolve is on this computer; a repeated `assembly` command builds nothing when its work is current; the DaVinci ledger routes (`delivery_reserve`, `delivery_mark`) accept the assembly stage.

**An unexpected error (this note).** `visuals_stage.guarded` wraps every visuals API route. A refusal written for the operator (a `ValueError` from `need`) arrives as written, 422. A missing key, a wrong type or a division by zero now goes to the server log (`vw2.visuals`, with its trace) and reaches the chat tool as the page's sentence, 500: "That could not be done; nothing was changed. The builder has been told what failed." The sentence lives once, in `errors.UNEXPECTED`; `web.PAGE_FAILED` is the same object.

## Tests, and how to run them
- Page suite, `server/pagetests` (715 tests; real Chromium on the page's template, no server, no database, no network; about 15 minutes): from `server/`, `"$TEMP/vw2venv/Scripts/python.exe" -m pytest pagetests -q --tb=line`. Its README and CONTRACT say what each layer proves; `walk.py` serves the page by hand with the real functions behind the buttons.
- Unit suite, `server/unit`: `pytest unit -q`. New here: `test_release_chat_routes_pure.py` (7: each new route and its guard, read from `main.py`; the plain sentence). From the branches: `test_ui_visuals_actions_pure.py`, `test_handover_no_redo_pure.py`.
- Plugin, `plugin/tests`: `pytest tests -q`. New here: `test_visuals_page_actions_cli.py` (22: the request each flag sends, the line it prints, the refusal it relays). From the hand-over: `test_pull_handover.py`.

## Older ways (design/35, rows 25 to 33)
Retired in this release, each refused or gone by name:
- A repeated `assembly` command redoing finished work; the DaVinci open and confirm refused until the delivery stage.
- On the page: the per-picture Approve / Reject / Try a fix on a picture of a set while its round is open; "No" as the page's way to get a never-made set made; a tool command or a picture id in a message; the unlabelled golden tick; Done locked until every card is answered, and one-click Done at step 2; Done disabled at the spend cap; read-only on `busy`; the waiting labels "Reference round · step 2: judge every set", "Material specs · N to approve", "Drawing specs · N to approve"; a refusal said in the top bar only; a tab switch keeping the open picture and the old address.
- Rejecting an approved picture that a later step used (page and chat tool alike).
- A bare key name or an exception's text as a refusal of a visuals route.

Kept, with the reason:
- `approve_reference` still refuses a rejected picture (design/74 L7); `reapprove_reference` is the one way back.
- `vw visuals supply` (a candidate, approved with its hash): the procedures name it; `vw visuals own` is the page's way.
- "No" or "Correct it" in `round --sets` on a never-made set still makes it, for the chat tool.
- The older film's own-picture box and search-era answers, until the last film without `kept` closes.

## Not covered
- No database test: Docker was not running on the builder PC, so `server/tests` did not run and none was added for the five routes. They are checked by reading `main.py` and by the functions' unit tests; no request went through FastAPI.
- The procedure texts in `server/procedures/v3.json` do not name the new commands; only the "Visuals" paragraph of `plugin/commands/vw.md` does.
- A real picture near 15 MB through `POST /own` (about 20 MB as JSON); the size the live server's front accepts was not checked.
- `verdict_lock` is not printed by `vw visuals status`; the chat tool learns of a lock from the refusal.
- `set_answer` with no verdict (a starting picture alone) is the page's; the chat command asks for the verdict.
- People: `OWN_PICTURE_FOR_PEOPLE` stays false; the question is SK's.
- A run taken over in the middle of the visuals stage or earlier; pages for assembly and delivery (hand-over requirements, section 8).
- E19 (a run another operator's machine holds) on the page; browsers other than Chromium.
- Nothing ran against the live server; nothing is deployed.
