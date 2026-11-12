# design/185: a page that shows the master film

SK, 12 Nov 2026, during the first user run (VW-21): "create a page to show the master.mp4 … just a page to view, no buttons required".

## Requirement

`/runs/<code>/master` plays the run's current master film in the browser. View only. The approval stays in chat (`vw master record`, the words "watched and listened", design/44).

## What is built

- `stage2.master_state` (pure) and `master_view` in `server/app/stage2/stage.py`; the route in `server/app/web.py`; `server/app/templates/master.html` (no script, no button).
- The film is served by the existing `/runs/<code>/film/…` route.
- Links: the run page ("Master film"), and `vw master status` prints the link when the film is ready.

## Cases

| Case | The page says |
|---|---|
| No master built, or a change to the options dropped it | No master film yet |
| Built, not rendered (or the render is of an older build) | Built but not rendered yet |
| Render queued or running | Being rendered; reloads every 15 s |
| Render failed | The job's error |
| File not in storage | Not in storage; render again |
| Ready | The player, version, length, loudness, approved or not |
| Not signed in | Sign-in, then back |
| Unknown code or no access | As every run page (`_run_by_code`) |
| Run closed or master recorded | Still plays |

## Old way

`vw master fetch` (the film downloaded to the laptop) is kept; the page is an addition.

## Tests

`server/unit/test_design185_master_page_pure.py`. **Not run yet (SK, 12 Nov: hold the testing for later).** Still to do: run it with the unit suite, a plugin test for the printed link, a page test in `server/pagetests`, one look in a browser.

## Not covered

- Approving on the page (SK: no buttons).
- A previous master while a new one renders: a new build drops the old render record.
- The final film after the visuals step.
