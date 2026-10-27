# design/108 — Pictures, takes and downloads, faster

27 Oct 2026. SK, on VW-7's References step: the picture takes a long time to load. Also: give the videos the same treatment, and make downloads to the operator's PC as fast as they can be. **Nothing is built until SK approves this note.**

## 1. What happens today, measured on VW-7

**Pictures.** Only the visuals page shows pictures (the review page shows the film; the voices page plays audio).
- Every `<img>` points at `/runs/VW-7/file/{key}`. For each one the server checks the sign-in, reads the run, asks storage whether the file exists (88 ms) and signs a link (65 ms), then answers a redirect. The browser follows it and downloads the **full PNG**.
- The full pictures are big: VW-7 holds 159 pictures, 339 MB; a keyframe is 2.5 MB on average, a sheet 2.4 MB. A References element shows 5 to 15 of them; the Pictures step shows dozens.
- **Nothing is cached.** The signed link is different every time, so the browser can't reuse what it fetched. The page refreshes its data every 60 s and redraws the step, and every redraw downloads every picture on screen again.
- There is no small copy of any picture in v2. The lean-image fix SK remembers isn't in this code.

So a screen with 12 pictures moves about 30 MB, again each minute. That's the slowness.

**Takes (videos).** Already in good shape: the takes have `faststart` (checked on a live take), the players load only the metadata until play, and the signed link supports byte ranges, so a take plays before it's fully downloaded. The one gap is the same as for pictures: nothing is cached, so a replay after a redraw fetches the take again. The approved film on the review page is the same: faststart, ranges, no cache.

**Downloads to the operator's PC** (`vw fetch`, `vw visuals fetch`, `vw pull`'s bundle, the delivery):
- one request per file, the **whole file read into memory** before it's written to disk (a 1 GB original sits in RAM);
- one stream per file, no resume: a failure restarts the file from zero;
- the bundle takes three files at a time;
- a file already on disk is downloaded again on a re-run.

## 2. What changes

### Pictures

| # | Change | Where |
|---|---|---|
| I1 | **A small copy of every picture, made once.** A new route `/runs/{code}/thumb/{key}` serves a JPEG 768 px wide (about 60–90 KB instead of 2.5 MB). On the first request it's made from the full picture and stored beside it (`{key}.thumb.jpg`); after that it's served from storage. Old pictures need no backfill: each gets its small copy the first time someone looks. | `web.py`, `storage` |
| I2 | **Served with a cache.** The small copy comes straight from the server with `Cache-Control: private, max-age=86400` and an ETag (pictures never change under a key; a new picture is a new key). The browser keeps it for a day, across redraws and reloads. | `web.py` |
| I3 | **The page uses the small copy everywhere except the zoom viewer.** Grid cards, strips, the panel's picture and the round use `/thumb/`; the viewer (click to zoom) keeps the full picture. Grid pictures load lazily (`loading="lazy"`, `decoding="async"`), so an element with 40 pictures fetches only those in view. | `visuals.html` |
| I4 | **Full pictures and takes stop being re-fetched.** The redirect route sends `Cache-Control: private, max-age=3000` (under the signed link's hour), so a full picture or a take fetched once is reused on the next redraw. | `web.py` |

Expected: a References screen goes from about 30 MB to under 1 MB on the first load, and to nothing on the minute's redraw.

### Takes and the film

- **V1:** I4 above covers them: a take or the film plays from the browser's cache after the first play.
- **Left out on purpose:** a poster frame for each take (one ffmpeg call per take when it's stored). The players already show the first frame as soon as the metadata arrives, and takes are 4 MB, so a poster would save well under a second. Say so if you want it anyway.

### Downloads

| # | Change | Where |
|---|---|---|
| D1 | **Stream to disk.** Files are written in 1 MB pieces to `name.part`, then renamed when complete and verified. No file sits in memory. | `vw.py` `_download` |
| D2 | **Skip what's already there.** A file on disk whose size and sha256 match the manifest is not downloaded again. On a re-run only what's missing or wrong moves. | `vw.py` `_download`, `download_bundle` |
| D3 | **Parts in parallel, as IDM does.** For a file over 16 MB, the plugin follows the redirect once, then asks the storage link for 4 byte ranges at the same time and writes each into its place in the file. A failed part is re-fetched alone with the usual 5/15/30 s waits. | `vw.py` |
| D4 | **Verified.** After D3 the whole file's sha256 is checked against the manifest (the receipt files already carry it); a mismatch names the file and re-downloads it. | `vw.py` |

Expected: D1 and D2 are certain gains (no RAM use; re-runs move only what's missing). D3 helps when one stream is the limit, which it often is on a fast office line (2–3× on a 50 Mbit/s line); on a slow home line the line itself is the limit and D3 changes little, as the upload review found.

## 3. What is not changed

- Full pictures and takes still come from storage through a signed link; only the small copies are served by the server.
- Nothing about how pictures and takes are made or checked.
- The server's upload path and receipts.

## 4. Tests first

- **I1:** the thumb route makes a JPEG at most 768 px wide from a 1536×864 PNG, stores it beside the picture, serves the stored one next time, and answers 404 for a key outside the run.
- **I2:** the response carries `Cache-Control` and an ETag; a request with the matching `If-None-Match` gets 304.
- **I3:** the page's cards, strips, panel and round use `/thumb/`; the viewer uses `/file/`; grid images carry `loading="lazy"`.
- **I4:** the redirect carries `Cache-Control: private, max-age=3000`.
- **D1–D4** (plugin, with a fake server): a 40 MB file is fetched in 4 ranges and verified; a wrong sha256 re-downloads; a file already on disk with the right hash is skipped; a part failure retries once and then succeeds; a 5 MB file still comes in one request.
- **Browser:** on a local copy with VW-7's data, the References step requests `/thumb/` links and the viewer `/file/`.

## 5. Not covered

- The real timings on Revathi's and SK's lines (the first use shows them).
- `server/tests` (Docker).

## 6. Release

Server 0.54.0, plugin 0.48.0. Not committed or deployed until SK says so.

## As built (27 Oct 2026)

Server 0.54.0, plugin 0.48.0. Not committed or deployed.

- **I1, I2:** `web.thumb_bytes` and `web.thumb_response`, route `/runs/{code}/thumb/{key}`. A JPEG at most 768 px wide (a 1536×864 PNG of 2.5 MB becomes about 60 KB), made once, stored as `{key}.thumb.jpg`, served with `Cache-Control: private, max-age=86400` and an ETag; 304 when the browser has it. A key that is not a picture (a take) gets the usual redirect.
- **I3:** `thumbOf()` in the page: every card, strip, round frame, sequence state, placed asset and the panel use the small copy; the zoom viewer keeps the full file. Grid pictures carry `loading="lazy" decoding="async"`.
- **I4:** `files.file_redirect` sends every file redirect (the plugin's route and the page's audio, film and file routes) with `Cache-Control: private, max-age=3000`.
- **D1–D4:** `_download(m, key, rel, expect=None)`: skipped when the file is on disk with the manifest's size and sha256; otherwise one redirect, then `_fetch_to` streams the storage link into `name.part` in 1 MB pieces, in 4 ranged parts at once when the manifest's size is 16 MB or more, each part with the 5/15/30 s retries; the fingerprint is checked, a mismatch downloads once more and then names the file; the bundle passes each file's manifest row. A server answer served directly (200) is kept as before.
- **Checks:**
  - `server/unit`: 470 passed, 4 of them new in `test_design108_pure.py`.
  - `plugin/tests`: 278 passed, 6 of them new in `test_download.py`, with the 3 known Windows-only failures. Two delivery tests' stubs take the new `expect` argument.
  - Browser, on a local copy with VW-7's page data: References 12 of 12 pictures by `/thumb/` (the other 9 are Google's own thumbnails), the panel by `/thumb/`, the viewer by `/file/`, Pictures 66 of 66, Takes 49 of 49, every grid picture lazy, no script error.
- **Not covered:** real timings on the operators' lines; the first live request of each old picture makes its small copy (about half a second each, once).
