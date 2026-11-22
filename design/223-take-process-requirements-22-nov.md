# design/223: the new take process — requirements (for SK's approval)

22 Nov 2026. Branch `take-process`, worktree `vw2-take-process`. **No code is written yet.** This note is step 1: SK approves, adds or strikes; then tests, then the change.

Source: SK's approved brief `vw2-archive/2026-11-21/omni-edit-trial/process-change-prompt.md`, with `learnings.md` and the trial scripts beside it (`batch9/oe_edit.py`, `batch4/oe_ref3.py`).

Words used here:
- **first take**: the one video made from the layout video, the approved still and the take words.
- **version**: any later video of the same shot: an edit, a remake, or the 720p copy.
- **correction**: the operator's words about one video, and the one version made from them.

---

## 1. The requirement, restated

| # | Requirement |
|---|---|
| R1 | Each AI video shot gets one first take, made as today, **once**, at **360p**. |
| R2 | Nobody checks it. Claude does not look at its frames to judge it, no helper does, and nothing makes it again on its own. It goes to the operator as it is. |
| R3 | A call that fails at the provider is reported with the provider's own status and message. |
| R4 | The operator watches each take and either **accepts** it or **says what is wrong**, in plain words, shot by shot. They are never asked for seconds, a cause or a route. |
| R5 | The answers for all shots are collected. Nothing is sent until the operator says done; then all go in one run. |
| R6 | For each correction the assistant chooses the route, from the operator's words and the take's frames: things in the take to correct, add or remove → **edit** the whole take; the first seconds usable and what happens after must change → **remake by reference**. Added with A1: nothing of the take usable → **make the first take again**. |
| R7 | The rule for that choice is written in **one place**. Every correction records which route was taken and why. |
| R8 | **Edit:** the whole video, uncut, and words. No pictures. The words: "Edit the video. Make only these changes:", each change as one exact line, then "Keep everything else exactly the same:" with what must stay. Same length as the take. |
| R9 | **Remake by reference:** a clip from the start of the video to just before the fault, 3 seconds at most; up to 6 approved pictures; a short prompt in the brief's order (what the shot is for, what stays, what happens, the result at the end). Task `reference_to_video`. Same length as the take. No blanks. |
| R10 | Both routes: `gemini-omni-1.2-flash`, 16:9, **720p**. The size is one setting (1080p later, on SK's word). |
| R11 | When our own words asked for the fault (the still's words or the take words), the stored words are corrected too. |
| R12 | A shot accepted as it is still gets its 720p video: the whole 360p take sent as an **edit** that asks for the same video again. This choice sits in one place, easy to change. |
| R13 | The operator sees the original and the new video side by side, with "play both together", and the new video beside its neighbouring shots. They accept, or give another correction. **No limit on rounds.** |
| R14 | When every shot has an accepted video, the film moves to the next stage. |
| R15 | Only the takes change. Layouts, stills and every other step, with their checks, stay exactly as they are. |

---

## 2. Unstated but expected

| # | Expected | How |
|---|---|---|
| U1 | Every paid call is made on the operator's word. | "Accept" is their word for the 720p copy. Their words of what is wrong are their word for one correction. No amount is on the page (as today); after done, the chat says one line: how many videos are ordered, the seconds, the amount. Said, not asked (as today's "Make another"). |
| U2 | The film's cost limit is checked before every call. | The same check as today, call by call. |
| U3 | The film only ever takes a 720p video. | A 360p take is never placed in the film, the editor's package or the assembly. "Accept" on a 360p take records the acceptance and orders the copy; the shot is finished when a 720p video is accepted. |
| U4 | The 720p copy is shown too. | It is a new video and may differ (not tested). The operator sees it beside the 360p take and accepts it, or says what is wrong. |
| U5 | Which video a correction starts from. | The newest video of the shot. When the operator's words say the earlier one was better, the earlier one. Recorded. |
| U6 | An earlier video can still be taken. | Any earlier 720p video of the shot can be accepted after all (today's "Use take n after all", kept). |
| U7 | Everything is recorded, for SK's later look at the split. | For each correction: the operator's words, the video it started from, the route and the assistant's one-sentence reason, the change lines or the prompt, the second of the cut, the pictures, the size, the model, the job, what came back, and the operator's answer to it. In the record of generations and the run's log. |
| U8 | The page opens when it is complete (SK, 19 Nov). | It opens when every first take is made or has failed. After a run of corrections it opens again when every video of that run is back or has failed. Until then the chat says the line of counts. |
| U9 | One flow, two front ends. | The page's answers and the chat's go through the same server functions. The route, the clip, the pictures and the final words are built and checked on the server. |
| U10 | The frames are still made. | The server keeps making the frames of every video (one every half second, and the sheet). The assistant uses them only to choose the route and to place the cut. They are not a check and the operator is shown no verdict from them. |
| U11 | The server holds the prompt's shape. | Edit: the fixed opening and "keep" lines are the server's; it refuses an edit with a picture or with no change line. Remake: it refuses more than 6 pictures, a picture that is not approved, a clip over 3 s, and a prompt with a second for every move or with box and layout words. |
| U12 | The clip and the pictures are prepared by the server. | The clip is cut by the server from second 0 to the cut. Pictures are made smaller (longest side 1,536) and may be cropped close to the object, with the crop the stills already use. |
| U13 | One key for one call. | The upload, the send and every later ask of the same call use the same Gemini key (as the 21 Nov hotfix does for takes). |
| U14 | Length and place in the film. | A version is asked at the same whole seconds as its take (3 to 15). Where it starts in its slot follows today's rule for a take. |
| U15 | Settings, each in one place. | First take size (360p); correction size (720p); clip at most 3 s; pictures at most 6; the model; the way a 720p copy is made (R12). |
| U16 | Videos made before this change keep working. | A first take that is already 720p (VW-24's) is shown with no check; accepted, it is final: no copy is ordered. A correction of it follows the new routes. |
| U17 | The estimate follows the new count of calls. | The plan's estimate counts, for every AI video shot, the first take and its 720p video, and keeps today's allowance (30 %) for corrections until real figures exist. The figures depend on SK's answer to the open point. |
| U18 | The words are generic. | No rule names this film, a mason or a roof. They hold for every category of video. |
| U19 | Old ways are refused by name. | See section 5. The skill, the helper list, the guard and the plugin's lowest version are updated with it. |
| U20 | Nothing new is checked or asked elsewhere. | Layout checks, still checks, the word to make the first take: untouched. |

---

## 3. Edge cases

| # | Case | What happens |
|---|---|---|
| E1 | A shot has both kinds of fault. | Two calls in a row: the edit first, then the remake from the edited video. The second is not sent when the first fails. The operator sees the original and the final video; the in-between video is kept in the record. Both calls are in the price line. **Not tested.** |
| E2 | The correction adds a thing the film has no picture of. | It goes in words only. No new picture is made. |
| E3 | More than 2 people, or more than 6 pictures wanted. | 6 at most. Order: the people who act in the changed part first; with more than 2 people, fewer pictures each (full length before face before hand); then things that must appear and are not in the clip; then other things. What is left out goes in the words. The record says what was left out. |
| E4 | A picture shows the action being removed, or other people and things. | Not sent, or cropped close to the object. The assistant decides; the rule is in its instructions. |
| E5 | The fault starts in the first second (no usable start). | Not a remake case: see E7. The shortest clip is 1 second (the shortest the trial proved). |
| E6 | A take shorter than 3 s or longer than 15 s. | Cannot be made today: a take is a whole number of 3 to 15 seconds. The clip is always shorter than the video (at most 3 s, and at least 1 s is left to be made new). A video outside 3 to 15 s is refused by name. |
| E7 | Neither route fits: nothing of the take is usable, or the operator's words are about the still, the layout or the camera, or they want the shot cut or left out. | Nothing usable: the **third route**, make the first take again (A1). Words about the still, the layout or the camera, or a shot to cut or leave out: the assistant says so plainly and pays for no version; today's ways remain for these (the scene's and the still's own steps, unchanged, or a plan revision). |
| E8 | The operator's words are too vague to act on ("not good"). | The assistant asks them once what should be different. Nothing is sent until then. |
| E9 | The provider refuses a call, or ends it as failed (`RESOURCE_EXHAUSTED`). | Its status and message are kept and shown (never a key). The same request can be sent again **once**, on the operator's word. A second failure stops there; the shot is listed as "could not be made" and the operator decides. A failed call is not counted as spent. |
| E10 | It is unknown whether the provider accepted a call (the line dropped at the send). | Never sent again by itself (today's rule): it is recovered or resolved first, so nothing is charged twice. |
| E11 | One shot of a run fails, the others succeed. | The others are shown as usual. The failed one is listed apart with the provider's message and the "send again" of E9. |
| E12 | The cost limit is reached in the middle of a run. | The calls already sent stay. The rest are not sent; their answers are kept. The chat says the spend and which shots wait. Only the owner changes the limit; after that the waiting ones go without being answered again. |
| E13 | The operator corrects a shot that was already accepted. | Before done: the answer is simply changed. After done, while the film is still in this step: the acceptance is taken back and the correction starts from the accepted video. While a video of the shot is being made: refused until it is back. |
| E14 | A remake's first frame is not the approved still. | The server does not measure a remake against the still. The operator judges the join where the new video is shown beside its neighbouring shots. |
| E15 | The new video is worse than the one before. | The operator says so. The next correction starts from the earlier video (U5), or the earlier 720p video is accepted (U6). |
| E16 | The same correction is sent twice (two clicks, the page and the chat together, done said twice). | The same request (same video, same words, same pictures, same size) is made once. |
| E17 | The plan changes while versions are being made. | As today: a video made for an earlier plan cannot be accepted; the page says so. |
| E18 | Our own words asked for the fault (R11). | The assistant is shown the still's words and the take words with every correction. When they asked for the fault, it sends the corrected take words with the correction; the server stores them and the record says "asked by our words", with a note of what the still's words or the plan's line asked for. The approved still is not made again and the plan is not changed (A2). |
| E19 | A correction with many changes in one edit. | Sent as numbered lines in one call. **Not tested** beyond two lines. |
| E20 | The first take came back as the layout video itself, or at the wrong length. | It is shown like any take (A1). The operator says what they see; the assistant makes the first take again (the third route). The same request may be sent again for this; each sending is on the operator's words. |
| E21 | A shot has no approved picture of anyone in it. | The remake goes with the clip and the words alone. |
| E22 | The worker restarts in the middle of a call. | Versions run through the same job steps as takes: sent once, asked again later, never sent twice. |
| E23 | The key's daily allowance. | Each shot now needs at least two calls (first take, 720p video). The trial saw one key refuse after about 22 video calls in a day. The pool's next key is used when there is one (today's rule); else E9. |

---

## 4. Failure modes

| # | Failure | Handling |
|---|---|---|
| F1 | The provider does not accept `360p` for the first take. | The refusal is shown with its message. Nothing falls back to 720p by itself. (Not proven: no 360p call was made in the trial. I read the provider's documents before building; no paid call without SK's word.) |
| F2 | The upload of the video or the clip fails. | Nothing was charged; said so; can be sent again. |
| F3 | The clip cannot be cut (ffmpeg fails). | No call is made; the fault is said with the shot's name. |
| F4 | A picture cannot be read or shrunk. | No call is made; the picture is named. |
| F5 | The assistant places the cut too late and the clip shows the fault. | The model copies it; the operator sees it side by side and says so; the next round cuts earlier. The instruction says: in doubt, cut earlier. The second of the cut is in the record, never asked of the operator. |
| F6 | The assistant chooses the wrong route. | The operator sees the result and says so; the next round may take the other route. Both are in the record: this is the data for SK's look at the split. |
| F7 | The version comes back at another length. | Shown as a plain fact on the video ("8.0 s; its place needs 5.0 s"). Not set aside. A video shorter than its place is marked as short when it is accepted, as today. |
| F8 | The 720p copy differs from the 360p take. | The operator sees both and decides (U4). |
| F9 | The cost limit refuses a call. | E12. |
| F10 | The stored output cannot be saved after the provider made it. | Today's "being stored" recovery, unchanged: the same output is fetched again, nothing is made again. |
| F11 | Two keys: the sending key is cooled or gone before the video is read. | Today's hotfix rule: each other key is tried once for reading (free). |
| F12 | The run of corrections is long and the operator closes the chat. | Jobs run on the server; the line of counts and the page are there when they come back. |

---

## 5. Old ways

Each row becomes a row of `design/35` when it is built. A retired way is refused by name.

| # | Older way | Where | Now |
|---|---|---|---|
| O1 | The first take is made at 720p. | `video_generators.GUIDE` | **Retired.** 360p, as one setting. |
| O2 | Claude checks each take from frames before the operator sees it (five lines, pass or fail, "na"). | `takes.look_lines`, `due`, `asked`, `listed`, `record`, `looked`; `vw visuals pictures --looks` rows of kind `take`; `how_take` | **Retired.** A look sent for a take is refused by name. |
| O3 | The `vw-take-look` helpers, about three takes each. | `plugin/agents/vw-take-look.md`, the guard's list, `takes.starts` ("the checkers of the takes") | **Retired.** The file is removed. |
| O4 | A take is offered only with its check, or 30 minutes after Claude was asked. The page opens when every take is "made and checked". The state "being checked by Claude". | `takes.offered`, `LOOK_MINUTES`, `STATE`, `complete` | **Retired.** A take is offered as soon as it is made (U8). |
| O5 | The check line on the take ("Check passed", "Check:", "Go to 5 s"), "Against the check", the scorecard, the note asked when a take is selected against its check. | `takes.check_view`, `item_id`, `guide_worker.scorecard`, `visuals_stage.take_held`, `select_take` (guide part) | **Retired.** |
| O6 | "Make another" with the operator's words, then the assistant names a cause (`still`, `guide`, `words`, `model`), changes one thing and shoots the whole take again. | `takes.answer` (`again`), `again_due`, `guide.set_cause`, `CAUSES`, `vw guide cause`, the skill's "When a take is wrong" | **Retired.** The operator's words make a correction; the assistant chooses edit or remake. `vw guide cause` is refused by name. |
| O7 | At most two takes from one camera; "a third try is not made" (the ladder). | `guide.LADDER`, `takes._can_again`, `no_more` | **Retired.** No limit on rounds; the cost limit is the only stop. |
| O8 | "Reject" as a button (no new take; the assistant asks: cut, another angle, leave out). | `takes.answer` (`reject`), `rejected_due` | **Button retired; the way out is kept** (E7): when the operator's words mean the shot itself must change, the assistant does what it does today. |
| O9 | An accepted take goes into the film at once. | `takes.answer` (`select`), `visuals_stage.select_take` | **Replaced.** A 360p take is accepted and its 720p copy ordered; the film takes the accepted 720p video. A first take already at 720p is accepted as before (U16). |
| O10 | "The same request is never sent twice." | `guide.same_of`, `guide.shoot` | **Kept** for the first take, except the third route (E20). For a version: the same request is made once (E16), sent again once after a provider failure (E9). |
| O11 | A failed call shows our own sentence; the provider's message is dropped. | `video_providers.Provider.request`, `visual_workers.process_take` | **Retired.** The provider's status and message are kept and shown. |
| O12 | The server sets a first take aside when it is the layout video unedited, the wrong length, or its first frame is over 30 % off the still; the chat asks "Send it again?". | `guide_worker.blocked_by`, `take_checks`, `chat_flow` (the "Send it again" card) | **Retired** (A1, SK 22 Nov 2026), with "one continuous shot" (`guide_worker.jumps`, `continuous_line`) and the drift line (`image_check.take_drift`): nothing is measured on a take, nothing is set aside, the "Send it again" card is gone. A wholly unusable take is made again by the third route. |
| O13 | "Use take n after all." | `takes.answer` (`old:n`) | **Kept** (U6). |
| O14 | One price a second at every size. | `visuals_stage.prices`, `VISUALS_PRICE_VIDEO_INR_PER_S` | **Retired** (SK, 22 Nov 2026: "the price by size"): one price a second for each size (section 7). |
| O15 | The estimate counts one take a shot; a 30 % allowance for takes made again is shown beside it. | `visuals_stage.plan_estimate`, `RERUN_SHARE` | **Replaced** (U17). |
| O16 | The take words carry a second for every move ("ONE action only"). | `guide.set_prompt`, the skill's "The take's words" | **Kept.** The brief makes the first take as today. The trial says long words stiffen movement; SK decides that apart. |

---

## 6. My readings that SK may strike

| # | Reading |
|---|---|
| A1 | **Decided (SK, 22 Nov 2026: "ok done").** The server measures nothing on a take any more: "real footage", "as long as the guide", "first frame matches the still" and "one continuous shot" are all removed, and no video is ever set aside. Every first take goes to the operator. When nothing of a take can be used, the assistant takes a **third route: make the first take again** (the same layout video and still; the take words corrected when they asked for the fault), at 360p, on the operator's words, named in the price line and recorded like the other routes. The page's line of the video's length beside its place's length stays. (My first reading was to keep the three; SK's concern was what the operator does with a wrong video: they say what they see, as for any take.) |
| A2 | **Approved (SK, 22 Nov 2026).** "Correct the plan's words too" (R11): the shot's stored **take words are corrected**. The still's words and the plan's line get a **note only**: the still is not made again and the plan is not changed (a changed plan makes every video of the film "made for an earlier plan", which cannot be accepted). The still's words and the plan's line are in no call to the video model, so they cannot bring the fault back. **The still picture can:** the first take again sends the approved still. So: the first take is made again only when the still and the layout are right; when the still shows the fault and the rest is fine, the route is edit (it sends no still); when nothing is usable and the still shows the fault, the still is repaired first by its own step, as today, then the first take is made again, and the assistant says so to the operator. |
| A3 | **Decided (SK, 22 Nov 2026: "pictures").** "Beside its neighbouring shots" is today's "See it in the film": the shot before and the shot after as pictures, with the new video. One correction: the shot before is shown by its **last** picture (the one the cut leaves from), not its first as today (`takes._beside`). Playing the three in a row is not built; it can be added if a real run shows the pictures are not enough. |
| A4 | **Decided (SK, 22 Nov 2026: "the operator sees it").** A 720p copy is accepted by the operator like any version (U4): the 360p take and the copy side by side, "play both together"; it does not go into the film unseen. Claude compares nothing and says nothing about whether the two are the same. Kept as one easy change, should SK later want the copy to go in unseen. The size stays 720p (the brief); 1080p on SK's word. |
| A5 | **Decided (SK, 22 Nov 2026: "No, both in a row").** For both kinds of fault: the edit first, then the remake from the edited video, one after the other with no stop (E1). The operator sees the video they answered and the final one; the in-between video is kept in the record. The remake is not sent when the edit fails at the provider. Known cost of this choice: nobody judges the edited video in between, so a failed edit is copied by the remake and that call is spent. (I had recommended showing the in-between first; SK chose in a row.) Not tested. |

---

## 7. The open point (the brief's)

**Answered (SK, 22 Nov 2026: "the price by size").** The price is one figure a second for each size, each a setting: 720p stays ₹8.9; 360p starts at a third of it (₹2.97) and is corrected from the provider's own token count of the first real 360p take. The cost limit, the price line in the chat and the plan's estimate all use the price of the size that is made. Row O14 is **retired**.

**Should the price follow the size?** Today the application counts ₹8.9 for every second of video, whatever the size. With the new process every shot has a 360p take and at least one 720p video. For a 5-second shot accepted as it is:

| | 360p take | 720p copy | Counted for the shot |
|---|---|---|---|
| One price (today) | ₹44.5 | ₹44.5 | ₹89 |
| Price by size (360p at about a third) | about ₹15 | ₹44.5 | about ₹59 |

The film's cost limit is checked against the counted figure, so with one price a film reaches its limit sooner than its real cost.

One more fact, not a second question: an edit also sends the whole video **in**, and the provider counts those tokens (the trial's 5-second edit: 28,960 in, 28,960 out). The application counts only the seconds made. I leave that as it is unless SK says otherwise.

---

## 9. As built (22 Nov 2026, after SK's "Approved, start")

Tests first, then the change. Server 0.122.0, plugin 0.106.0 (the lowest plugin the server takes). Not deployed.

| Where | What |
|---|---|
| `server/app/corrections.py` (new) | The versions of a take: the one rule for the route (`RULE`), the settings (720p, clip 1 to 3 s, 6 pictures, the copy's way), the words sent (edit, remake, copy), what is refused before anything is paid, the cost limit's wait, the chain for both faults, "send again" once, the list for the assistant, the one line after done. |
| `server/app/takes.py` | Each shot's state with no check; the page's line (Accept, Say what is wrong, the version beside the video it was made from, a failed new video with "Send it again"); the answers. |
| `server/app/guide.py` | The first take at 360p; `again` once after a provider failure; `same` for the third route; the cause, the ladder and "Make another" removed and refused by name. |
| `server/app/video_providers.py`, `visual_workers.py`, `guide_worker.py` | The edit and remake requests; the provider's message kept; after a take only its frames are kept (nothing measured), and the remake of both is sent when the edit is back. |
| `server/app/visuals_stage.py`, `config.py`, `video_generators.py` | The price by size, the spend and the estimate; only a 720p video goes in the film; the newest video of a shot is the one to answer; the videos that waited go when the owner sets another limit. |
| `server/app/pictures.py`, `chat_flow.py`, `page_flow.py`, `main.py` | A take is not in Claude's looks; the Shoot card once; the next-step lines; the two new server calls. |
| `server/procedures/v3.json`, `scripts/d223_wording.py` | The assistant's served text for the visuals stage says the new process (7 sentences replaced; the text is shorter than before). |
| `plugin/` | `vw guide corrections`, `vw guide correct` (`--file`, `--withdraw`, `--reopen`); the guide skill's "When a take is wrong"; the `vw-take-look` helper removed; the page draws the two videos side by side with "Play both together". |
| `design/35-decision-log.md` | Rows 316 to 333: every older way, retired or kept. |

**Test results (22 Nov 2026, on the builder PC):**

| Suite | Result |
|---|---|
| `server/unit`, the whole database-free suite, with the page tests in a headless browser | 3,395 passed, 10 skipped, 0 failed |
| of these, new for design/223 | 64 (the process), 6 (the page's own route with a real stored film), 6 (the page in the browser) |
| `server/pagetests` (the page's controls) | 765 passed |
| `plugin/tests` | 695 passed, 3 failed: the three that fail on this Windows PC before the change too (section 10) |
| Before the change, for comparison | `server/unit` without the browser: 3,103 passed, 34 skipped |

The older tests of the retired ways were removed with the code they tested (about 100 of them: the take check, the scorecard, "Make another" and the cause, the two-take limit, the set-aside and its release script).

Two things found by the tests while building, both corrected: after a new video came back the page had no line for it (the oldest take of the shot was offered, not the newest); the tool asked a wrong address for the list of corrections.

One addition to the note: a take made for an earlier plan cannot be accepted, but the operator can say what should change (a version stands on today's plan).

## 10. Not covered

- **Calls to Google:** none while building; seven after it, on SK's word (section 11): a first take at 360p, the 720p copy and the edit and reference requests all work. Still not proven: whether a copy made from a 360p take is good enough for the film (one shot, SK's judgement); a remake by reference from a 360p take with pictures; the exact shape of a failed call's message (read from its `error` field, as Gemini gives it elsewhere).
- **The database-backed tests** (`server/tests`, Docker) were not run. The worker's step after a take (frames stored, the remake of both queued under the run's lock) is tested through its parts, not against a database.
- **A remake's pictures through the film's own rules for a person's picture:** the flow is tested with the picture step stood in; the shrink to 1,536 px is tested alone.
- **VW-24 as it stands on the live server:** not touched and not read. A shot of it with "Make another" pending or a rejected take will show its newest video to the operator again; this was not tried on its real data.
- **The page:** tested in a headless browser with stand-in data and a stand-in video, at two sizes; not on a real artifact page with real takes. The 33 older page tests of step 7 still draw a round in the older shape (the page keeps drawing it).
- **The chat without the page:** the answers go through the same function, which is tested; the chat's own item text was not read by a person.
- **The 360p price** is a third by rule (₹2.97), not measured.
- Three plugin tests fail on this Windows PC before and after this change (line endings, a Mac path): `test_intake` (2) and `test_start_defect_paths` (1).

## 11. SK's test of the 720p copy (22 Nov 2026, after the build)

Five paid calls, on SK's word, by Claude's scripts outside the application, on the local test key; the requests were built by the application's new code. The server and VW-24 were not touched. Evidence and the full results: `vw2-archive/2026-11-22/upscale-test/results.md` and `batch2/results.md`.

The input each time: a true 720p take of the trial made smaller to 360p (no take made at 360p by the model exists yet).

| Call | Words | Result |
|---|---|---|
| Edit, hand-over take | "Do not change anything: this is only an increase of the picture size" | The same video frame for frame (0.98), but only as detailed as the 360p picture made bigger (32; the true 720p take 94). |
| Reference mode, first 3 s | the same idea | More detail (58), but the movement is acted again: not the same video (0.84). |
| Edit, hand-over, brick close-up, mason with wire | "the picture becomes true 720p footage with sharp, fine detail ... do not simply enlarge it", then "keep everything else exactly the same, frame for frame" | The same video frame for frame (0.94 to 0.96) with the detail of a true 720p take (91, 77, 158 against 89, 44, 173). |

What follows from it:

- **The 720p copy stays an edit (R12), with the second wording.** The words the build first had ("make no change: give the same video again") were of the first kind and would have given a soft picture; they were replaced before any deploy (`corrections.copy_text`, design/35 row 324). The two sizes in the words come from the settings.
- The detail is drawn by the model, not taken from an original: the operator still sees the copy beside the take before it goes in the film (A4).
- A 360p video is accepted as the input of a 720p edit and of a reference call, and is counted at a third of the 720p tokens (1,931 a second against 5,792): this supports the 360p price.
- The application's edit and remake requests work against Google as built.

Not proven by it: a take made at 360p by the model; a face large in the frame; more than one try of each.

### A first take asked at 360p, and its copy (the same day, two more calls)

Evidence and results: `vw2-archive/2026-11-22/first-take-360/results.md`. The material was the layout test of 20 Nov (a nurse walks to a door, 6 s), all on the builder PC; both requests were built by the application's code, the copy with the application's own words.

- **Google makes a first take at 360p** (640 x 360, 6 s, real footage of the layout).
- **A 360p second is exactly a third of a 720p second** in tokens (1,931 against 5,792): the 360p price of ₹2.97 stands.
- **The copy is the same video** (0.99 frame by frame) and sharper than its take (fine detail 10 to 26), **but less detailed than a take made at 720p** from the same request on 20 Nov (50; another take, so a loose comparison; the scene is mostly plain walls). On the model's own 360p picture the copy gained less than on the 720p takes made smaller. One shot, one try: SK judges on the videos whether it is enough.
- Seen in passing: the layout video is sent in at 720p and counted at three times the tokens of the 360p take it makes. The application does not count what is sent in; sending it in smaller is not tested.

## 8. Not in this change

- No deploy, no restart, nothing on the VM, nothing of VW-24's live run.
- (The 360p size of a first take and the 720p copy were tested after the build: section 11.)
- Shorter take words for the first take (O16).
- 1080p.
- SK's other way for the 720p copy (the first seconds as a reference): only the place to switch it is built.
- Changing an accepted video after the film has left this step.
