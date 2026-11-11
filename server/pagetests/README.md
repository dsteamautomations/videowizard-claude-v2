# Browser tests of the visuals page

These tests open the real page `server/app/templates/visuals.html` in a real browser (Chromium, driven by Playwright) on this PC.
No server, no worker, no database and no network are used: the page's data and the server's answers come from files in this folder.

This is the harness and "layer 2" of the approved plan (`videobuilder-v4/phase2/ui/requirements-and-test-plan.md`, section 7):
every screen state is opened and checked. The tests state what the approved requirements say must be true, so they fail where
today's page is wrong. Nothing here changes the application.

## Run it

From `server/`, with the test environment that already holds pytest, Jinja2, Pillow and Playwright (`%TEMP%\vw2venv`):

```
"$TEMP/vw2venv/Scripts/python.exe" -m pytest pagetests -q --tb=line
```

That one command runs everything against the page in the working tree, with the states in `data/main`. It ends with totals
(states rendered, script errors, blank tabs, count mismatches, Next waiting, dead links, broken pictures, layout) and writes:

- `out/results-<label>.json`: every test with its result and its message;
- `out/screens/<label>--<state>.png`: a screenshot of every state at 1920x1080, for a person to look at.

`out/` is not committed.

### The live version of the page

```
VW_PAGE_REV=ed8dcb9 VW_PAGE_DATA=live "$TEMP/vw2venv/Scripts/python.exe" -m pytest pagetests -q --tb=line
```

| Variable | Meaning | Default |
|---|---|---|
| `VW_PAGE_REV` | a git revision; `visuals.html`, `base.html` and `style.css` are read from it | the working tree |
| `VW_PAGE_TEMPLATE` | a path to a `visuals.html` to test instead | none |
| `VW_PAGE_DATA` | the folder under `data/` holding the states | `main` |

One state or one check: `-k refs-step2-all-sets-back`, `-k test_counts_agree`.

## What is checked on every state (`test_states.py`)

| Test | What must be true | From |
|---|---|---|
| `test_loads_without_script_or_console_errors` | every tab draws with no script error, no console error, no failed request; saves the screenshot | failure modes, section 6 |
| `test_nothing_is_blank` | no empty tab; the state's own tab shows cards or a line saying what comes next; no "undefined" or "NaN" on screen | E1 |
| `test_counts_agree` | the header's number equals the tabs' numbers added up; on each tab the tab's number, the number of cards with the waiting mark and "Waiting for me (N)" are the same | R6 |
| `test_next_waiting_lands_on_something_actionable` | each press of Next waiting opens or outlines something with a live control in it, and never prints a red line | R9 |
| `test_every_inside_link_opens_something` | every link in the data's waiting list and every hash link on the page opens its tab and its item, with no red line | R10 |
| `test_every_picture_loads_or_shows_a_placeholder` | no broken picture on any tab | E16 |
| `test_layout_holds` (1920x1080 and 1366x768) | no sideways scrollbar; no control outside the window | section 4 |

## The harness (`conftest.py`)

`open_page(state_name, size='1920x1080', tab=None, answers=None)` renders the template with Jinja2 as the server does
(`run`, `user`, `version`), opens it at `http://vw.test/runs/<code>/visuals` in a fresh browser context (empty `localStorage`),
answers every request from memory and returns a `PageUnderTest` on the state's own tab:

| Request | Answer |
|---|---|
| the page | the rendered template |
| `GET …/visuals/data` | the state's payload |
| `POST …/visuals/act` | recorded in `posts`; answered with the canned answer of that action (`ANSWERS`, or `answers={action: (status, body)}` from the test) plus the payload as `view`; a status of 400 or more is sent without `view`, as a refusal |
| `/static/style.css` | the real stylesheet |
| pictures (`/thumb/`, `/file/`, and pictures on outside sites) | a small grey PNG made in memory; a 404 when the state says `"pictures": "missing"` |
| anything else | 404, and listed in `unstubbed` (a test fails on it) |

`PageUnderTest` gives: `click(selector)`, `click_text(text)`, `click_role(role, name)`, `open_tab(tab)`, `go_hash(hash)`,
`header_count()`, `tab_counts()`, `active_tab()`, `cards()` (each with `unit`, `title`, `badge`, `waiting`, `selected`),
`waiting_chip()`, `bar()` and `red_line()` (the message bar), `section_text()`, `links()`, `screenshot(name)`, and the lists
`posts`, `js_errors`, `console_errors`, `failed_requests`, `unstubbed`. `page` is the Playwright page for anything else.

## The states (`data/<name>/<state>.json`)

Each file holds `state`, `tab` (the tab the state belongs to), `source`, `pictures` (`ok` or `missing`), `note`, and `payload`:
exactly what `GET /runs/<code>/visuals/data` returns.

All states are **generated**, none is hand-made: `build_states.py` assembles a visuals session in memory with the unit tests' own
fakes (`FakeStore`, `FakeConn`, `doc_with`, `session`, `plan_doc`) and the server's own functions (`treatment`, `round_start`,
`round_done`, `round_sets`, `round_picks`, `search`, `approve_spec`, `approve_reference`, `still_from_reference`, `revise_gap`,
`add_asset`), then calls the real `visuals_stage.page_view`. Three things are set by hand, in the way the unit tests set them,
because the real writer needs a provider or the database:

- what a worker writes: a set's pictures coming back, a picture's check, the rows of the jobs table for takes and spend;
- `recorded_gaps` in `record-recorded` (`record_gaps` writes the run's outputs to the database);
- the small `run` block (`code`, `title`, `status`, `stage`, `open_defects`), which `web.py` reads through `core.next_for`.

`page_view` reads three things from the database connection, all from `vw2_jobs`: the take jobs, the spend, and the job of a
picture still "generating". `FakeConn` answers all three; `build_states.py` adds one answer for `vw2_files` (read by `add_asset`).

`data/main` is built with the server code of the working tree; `data/live` with the server code of `ed8dcb9` (the live version).
The two differ where the server differs: on live the waiting list holds one item per set, a footage-backed element still gets an
AI set, and a round whose sets were all refused goes back to step 1.

### Refresh the data

```
"$TEMP/vw2venv/Scripts/python.exe" pagetests/build_states.py
"$TEMP/vw2venv/Scripts/python.exe" pagetests/build_states.py --rev ed8dcb9 --name live
```

Run the first after any change to `visuals_stage.py`. The files carry the time they were made (the treatment's `at`), so a rebuild
always shows a small diff. A state the server code cannot make is printed as `NOT MADE` with the reason and no file is written.

### Add a state

In `build_states.py` add a function under `@state('<name>', '<tab>')` that returns `(store, conn, run)`: start from `film()`,
`step1()`, `step2()` or `complete()` and move the session on with the server's functions. Options of `@state`: `pictures='missing'`
(pictures answer 404), `run={...}` (fields of the `run` block), `repair=False` (the run lock was not free), `note='...'`. Rebuild;
every test in `test_states.py` runs on the new state without further work. If a state cannot be generated, write its payload by
hand using only fields a generated one has, name the file `handmade-<name>.json`, and list it here.

## Not covered here

- Layer 1 (one test per control) and layer 3 (the journeys, R1 to R24, E1 to E20 one by one): the next steps of the plan.
- Real data of VW-19 and VW-18: the states are made from the unit tests' small film (four elements; 58 in the large round).
- Video playback: a take's file is answered with an empty body.
- Browsers other than Chromium; widths other than 1920 and 1366.
