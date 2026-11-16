# design/210: pictures on the page; the reference drawings and the reference round

**Status:** built on 16 Nov 2026 (server 0.107.0, plugin 0.91.0, plugin minimum raised to 0.91.0: every laptop updates); **not deployed**; SK's deployment word awaited.

**Why:** SK, 16 Nov 2026: "The next set of work is to make Claude Artifacts for References Screen … Think about showing thumbnails so that the page loads fast. But users should be able to see the image in zoom also." After the picture test: "the screen looks good. but there are not buttons to accept, reject or add comments. In previous version we have options where the user can upload images when the reference image is incorrect and for some picture it shows 3 pictures and user has to select one."

The plan SK saw: `design/_work/reference-screens-on-the-page-plan.md`. Screens 4 (stills and graphics) and 5 (AI video) are not in this change.

## The picture test (step 0), run on a trial page

| Tried | Result |
|---|---|
| 40 small pictures written to the page's database in one batch | Worked, about 6 s; mean 12 KB each |
| 25 large pictures (1,600 px) uploaded to the page's file store in one call | Worked, about 25 s; mean 163 KB, largest 400 KB |
| The upload's answer | Names each file with its link, so the tool matches by file name |
| SK opened the page | Small pictures show; a click opens the large one at 1,600 px |
| A file fetched back from the file store | Saved under its id with its extension (checked after the build) |

## What is built

**Pictures, once, for every screen.** A page line names its pictures. The server makes two sizes of each (360 px and 1,600 px, never cropped) and keeps them. The tool sends only what was not sent before: the small ones as database documents in batches, the large ones as files to the page's file store, matched to their links by file name. The page shows a row of small pictures, loaded as the row nears the screen; a click opens the large one with next, previous and close. A line's buttons stay off until every one of its pictures has shown. With no large pictures the page still works and says so.

**Screen: Reference drawings.** Every thing's drawing set in one visit: its sheets as pictures, the facts and where each came from, one line for the sizes that are assumed. Yes, or Correct it with words.

**Screen: References (step 1).** Every person, object and place in one visit: its footage pictures, what a yes does, the price on every button that leads to a paid set, a comment box. Answers are kept until every thing is answered; then one record and the sets are made. The top line gives the bounds: things, sets, cost, limit, spent.

**Screen: References, the sets (step 2).** Each set's three pictures, lettered. A person: Yes, No, Correct it. A thing: choose A, B or C on the picture or by button, None of these, Correct it. A set not made: Make it or Leave it out, with the cause. Sets being made show as "Being made". Approved sets keep their pictures.

**The operator's own picture, on both screens.** "Use my own picture" on a thing's line: the file shows at once and is handed to VideoWizard at "done", through the same path as `vw visuals own`. For a person, the operator first writes that they have the person's permission; that is recorded through the same path as `vw visuals likeness`.

**The chat** stays as the way back and ends in the same state.

Where: `server/app/page_flow.py`, `server/app/chat_flow.py`, `plugin/scripts/vw.py`, `plugin/pages/decisions.html`, `plugin/hooks/guard.py`, `scripts/d210_wording_v3.py`, `scripts/d210b_wording_v3.py`. Old ways 101 and 102 are in `design/35-decision-log.md`.

## Review fixes (16 Nov 2026, same versions, not deployed)

1. **Step 2 always ends.** When the last answer is "Leave it out" or the operator's own picture, no set is left to judge: the round is completed by the server's own test (`round_sets`), in `chat_flow.flush_sets`, which the page and the chat both pass through. A round that stalled before is ended by the next `vw visuals page` or `vw visuals next`. "The answers kept wait" is said only when an answer is kept.
2. **A paid remake carries the words.** On the page, "No" or "None of these" given with words in the comment box makes the set again with those words, as "Correct it" does. The log keeps the button pressed and the words. In the chat nothing changes.
3. **Pictures sent again.** The page's database refuses a second write to a document that exists. `vw visuals page --pictures-again` offers every picture again under new document names (`<code>-1`, then `-2`), and the round names the document of each picture (`pic_docs`, `zoom_docs`); the page reads it from there. The instructions name the flag as the way out; "send it once more" is gone. The large pictures are uploaded again too.
4. **One instruction while own pictures are fetched.** The first `vw visuals page --record` then says only what to fetch; the server's next step and the new round come with the second one.
5. **The first visit.** The server makes the sizes of eight pictures at a time; the tool waits 300 s for the page calls and, when that is not enough, says to run `vw visuals page` again in a minute (the sizes already made are kept).

Not covered by these fixes: a round element the plan no longer names still holds step 2 open; a "None of these" with words that is kept while other sets are being made shows as "Kept: Correct it"; a page already published is not asked to be published again by this change alone, because the version did not change (the versions change at the release).

## Decisions taken by default (SK asked to start; say if either should change)

- A click on a button that shows its price, followed by "done", is the operator's word for that spend. The priced label is logged as their words.
- No "accept everything" button on step 1.

## Not verified

- The page on claude.ai with a real film, and the whole loop on an operator's machine. Both builders ran the page in a headless browser on local copies (34 and 49 checks).
- The page's own upload to its file store (`assets.upload`): run against a stand-in only.
- How long the first visit takes on a film with many pictures: both sizes are made at that moment, eight pictures at a time (not timed on the live server).
- The database tests were not run.

## Not covered

- Screens 4 and 5 (stills and graphics; AI video).
- Removing old pictures from the page's storage when a set is made again.
- The comment at step 1 is kept in the run's log; the round itself takes no per-thing words there.
