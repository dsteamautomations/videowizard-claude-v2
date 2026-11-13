# Stage review: VW-23, voice

13 Nov 2026. Read-only review. Nothing was changed. Uncommitted working note. This replaces the earlier part-review written while the stage was still open.

The stage is finished: a narration was made final at 08:19:16 UTC (13:49:16 IST).

Evidence: `vw2_log` (27 rows for the stage), the server's request lines 06:26 to 09:05 UTC, `vw2_jobs` (7 voice jobs, all ElevenLabs, all ready, 1 attempt each), `vw2_defects` (none), `server/procedures/v3.json` (the voice step and the direction prompt), `server/app/jobs.py`, `voices.py`, `voice_direction.py`, `narration_pieces.py`, `worker.py`, `web.py`, `templates/voices2.html`, two screenshots and Deepa's account of what the operator did.

## Timeline

| UTC | IST | What the server saw | Answer |
|---|---|---|---|
| 06:26:26 | 11:56:26 | voice instruction fetched, favourites read; fetched again at 06:26:36 | 200 |
| 06:35:02 | 12:05:02 | direction recorded: "Best fit, passage 1" | 200 |
| 06:36:13 to 06:36:30 | 12:06 | voices page sent to sign-in, signed in | 303, 200 |
| 06:37:42 to 06:37:50 | 12:07 | six name searches | 200 |
| 06:38:57 | 12:08:57 | tryout: Reyaansh - Interactive Tutor; audition ready 06:39:09 | 200 |
| 06:47:57 | 12:17:57 | narrate; ready 06:49:06 (304.2 s of audio, 74 s to make) | 200 |
| 06:54:04 | 12:24:04 | narration played | |
| 07:01:14, 07:01:16, 07:01:20 | 12:31 | narrate again, three clicks | 200, **409 JOB_OPEN**, 200 |
| 07:04:50 | 12:34:50 | pronunciations recorded: "Yes" (version 1) | 201 |
| 07:04:50 to 08:05:14 | 12:34 to 13:35 | no call (the fault was being discussed with the builder) | |
| 08:05:14 | 13:35:14 | third narration played | |
| 08:06:11 to 08:08:26 | 13:36 to 13:38 | back to Browse; ten searches with filters (story use, Indian accent, English) | 200 |
| 08:08:47 | 13:38:47 | tryout: UD - Narrator; audition ready 08:09:00, with the pronunciation list | 200 |
| 08:09:40 | 13:39:40 | narrate; ready 08:10:42 (299.4 s, 65 s to make), with the pronunciation list | 200 |
| 08:14:37 | 13:44:37 | narration played | |
| **08:19:16** | **13:49:16** | **narration made final (UD - Narrator)** | 200 |
| 08:20:02 | 13:50:02 | next step read; media begins | 200 |
| 08:40:18 | 14:10:18 | voices page opened from a second computer | 200 |
| 08:46:29 | 14:16:29 | the final narration played there | |
| 08:48:06 | 14:18:06 | narrate again there, with the tag [proudly] on one sentence; ready 08:49:20 (303.9 s) | 200 |

## A. Restrictions someone set

1. **One open narration per voice.** `jobs.py:73`: "Finish or recover the open narration in this voice before starting another." Fired once, 07:01:16 UTC (12:31:16 IST), 409. Stopped one repeat click. Holds.
2. **A stored recording is reused when the request is the same.** `narration_pieces.py:67` identifies a recording by voice, model, settings, format and text; `worker.py:75` returns the stored audio. It fired twice at 07:01 UTC: both accepted "narrate again" clicks returned the first recording (same provider request id `4ebATrgtTv0XE7h4QBYP`). The reason holds (never pay twice). Two faults come from it: the pronunciation list is not part of the identity, and the page does not say a recording was reused.
3. **A tag equal to the one in force is not sent.** `voice_direction.py:102` (design/125 V1). The film's register is [measured]. A sentence tagged "measured" changes nothing. Reason holds for the provider; the page does not warn.
4. **A tag must be in square brackets.** `voice_direction.py:13`, message "a tag is a short direction in square brackets, like [measured]". Not seen firing on the server. The page says nothing about brackets before the click.
5. **Direction and test passage come first.** Step 2: "First, before any voice is discussed". Up to 8 min 26 s. "Best fit, passage 1", the same as VW-21 and VW-22. Only slowed this stage.
6. **The pronunciation list has no place in the served steps.** The six voice steps do not mention it. It was read at 06:35:12 and recorded at 07:04:50, after the first narration. In VW-22 it was recorded before narrating. Once recorded, every new audition and narration carried it (`jobs.py:74`; the 08:08 and 08:09 jobs show version 1).
7. **The voices page needs its own sign-in.** 06:36:13 UTC, 17 seconds.
8. **"The accepted narration is never re-recorded."** In the prompt only. The page allowed a new paid narration at 08:48 UTC, 29 minutes after the final click, while analysis was running. The server did not refuse it.
9. **Eleven v4, stability 0.5, similarity 0.75; at most six tryouts and three narrations.** Used as written. Two voices were narrated. No limit reached.
10. **Two record attempts** (`"cap": 2`). One used.

## B. Words in the prompt that restrict

1. **The kind of film is worked out again.** "The kind of film, which you state in one line before anything else … never assumed." The run holds the confirmed category. Looser: "The kind of film is the run's category."
2. **"three test passages of 50 to 100 words".** Passage 1 chosen three runs in a row. Looser: one recommended, two more on request.
3. **"ask one question: which list … and which test passage".** Always the full choice. Looser: a recommended answer to click.
4. **The tag box's hint "[softly]".** The prompt itself warns that volume-lowering tags "can make a deep or low voice breathy or husky" and belong only in the experimental list. The page's example is the tag the prompt advises against. Looser: use "[unhurried]" as the hint, or a list.
5. **"Never a pause tag", "Never an accent tag", "Never a reaction", "One tag per sentence at most".** Each has a stated reason. No change.
6. No example from an older film. The direction prompt names kinds of film from several categories.

## C. Steps that failed or were done again

1. **Narrate again, three clicks in ten seconds** (07:01 UTC, 12:31 IST). One refused, two accepted, both the same file. All reached the server. The operator reports typing "measured" in the tag box; the server received no tag on any click. Had "measured" arrived without brackets, the server would have refused it and made no row. Why the box arrived empty is not known. Label: the page (no check, no message) and our rule (reuse). No provider cost.
2. **The first voice's narration was not used.** 2,191 characters, made at 06:47 UTC. A word was mispronounced; the pronunciation list came 17 minutes later; a new take in that voice could not be had (C1, A2). The operator chose another voice. Label: our order (the list after the narration) and our fault (the list is not part of a recording's identity).
3. **A narration made after the final** (08:48 UTC, 14:18 IST), from a second computer, tag [proudly] on passage 10 sentence 1. A real provider call (`6fKO20Jsm4PyoDKsvnpP`), 2,196 characters. It is not the final; the final is still the 08:09 recording. Label: the page allows it; the operator's choice. It also shows the tag control works when a bracketed tag is sent: the text changed and a new recording was made.
4. **The voice instruction was fetched twice** (06:26:26, 06:26:36). Ten seconds. Label: the assistant, a guess.
5. **Page sign-in** (A7).

No failed or retried job. No defect.

## D. Getting the operator's input faster

| # | Question | Answered at | Wait | Mark |
|---|---|---|---|---|
| 1 | Which direction list and test passage? | 06:35:02 UTC (12:05:02 IST), "Best fit, passage 1" | up to 8 min 26 s | Same as VW-21 and VW-22. One click. |
| 2 | Which voice? (page) | first voice 06:47:57; second voice 08:09:40 UTC | 2 to 8 minutes of browsing each time | The client's last voice (Sid - Young Friendly Indian) was not chosen. Nothing to predict. |
| 3 | Approve the pronunciations? | 07:04:50 UTC (12:34:50 IST), "Yes" | asked only after the operator heard a wrong word | Must come before the first narration; club with question 1. |
| 4 | Which narration is final? | 08:19:16 UTC (13:49:16 IST), by a click | 4 min 39 s after starting to listen | Nothing to change. |

## E. Execution that can be better

1. **One hour lost to a fault.** 07:04:50 to 08:05:14 UTC: no call. The operator could not get a corrected narration in the chosen voice and stopped to ask. The stage took 1 h 53 min; without the fault, about 50 minutes.
2. **Paid work not used.** The first voice's audition and narration (264 + 2,191 characters), and the narration after the final (2,196 characters). The final cost 264 + 2,195. So about half of the characters paid for are not in the film.
3. **Five narration rows for two voices.** Three of them are one file.
4. **The cost record repeats.** Each reused job shows the full character count though the provider was not called.
5. **Time on the machine was small:** 17 to 26 s for an audition, 65 to 74 s for a narration.

## F. Known weak spots

1. Rounds to pass a check: none.
2. Refusals that are really questions: none.
3. Connection errors and timeouts: none in this stage. Every request reached the server.
4. Provider failures and retries: none. ElevenLabs, 7 jobs, 1 attempt each, 5 real calls.
5. Blank searches: none logged.
6. Next-step line against the plugin: none seen.
7. Output too big: not visible from the server.
8. Page and chat disagreeing: yes. The pronunciation list lives in the chat; the narration is made on the page; the page let the operator narrate before the list existed.
9. A fixed defect coming back: none.
10. Who the stage waited for: the fault for 60 minutes; the person for about 45; the assistant's direction step for up to 8; the machine for under 4.
11. Money on rejected work: 2,455 characters before the final (first voice) and 2,196 after it.
12. Answers identical to the previous run: "Best fit, passage 1" and "Yes" to the pronunciations.
13. An older way still in the text: the chat path is kept beside the page. Not checked against design/35.
14. A rule tied to one kind of film or an older model: none seen.
15. Too few log lines: no. 27 rows. But the log does not record the tag sent with "narrate again", which is what this stage turned on.

## The stage in one line

Voice: 06:26:26 to 08:19:16 UTC (11:56:26 to 13:49:16 IST), 1 h 53 min, about 54 server calls plus about 30 page polls, 1 refusal, 4 answers, 6 jobs to the final (4 real provider calls, about 4,900 characters), 1 more paid narration after the final.

## The three changes that would save the most

1. Ask for the pronunciation list before the first narration, and make the list part of what identifies a stored recording. This is what cost the hour and a wasted narration.
2. Make the tag control safe: a list of tags to pick, brackets added by the page, a check before sending, and a plain message when nothing would change or a stored recording is returned.
3. Offer "Best fit, passage 1" as one click, and close "narrate again" once a narration is final unless the operator reopens the stage.

## Could not see

- What was in the tag box at 07:01 UTC, and what the page showed after each click.
- Who used the second computer at 08:40 to 08:49 UTC and why a narration was made after the final.
- Whether the mispronounced word is right in the final narration.
- The assistant's messages and token cost.
- The price in rupees: the cost record holds characters, not money.

## Outside this stage, seen in the same window

At 08:38:46 to 08:39:31 UTC (14:08 to 14:09 IST) the server logged a database statement timeout (`QueryCanceled`) once, and the workers logged "worker error (QueryCanceled); retrying" seven times. This is in the analysis stage. Analysis went on recording clips afterwards. It belongs to the analysis review.
