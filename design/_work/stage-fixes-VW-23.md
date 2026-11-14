# VW-23: observations and fixes by stage

Fixes approved by Deepa on 13 Nov 2026 unless marked otherwise. None is built yet.

**Built 14 Nov 2026 (design/192), on branch `worktree-stage-fixes-vw23`, unit tests only, not merged, not deployed:** intake 1 to 8; brief 1 to 5 and 7; script 1; voice 1, 2, 4 to 7 and 11. The lines "None is built yet" below are older than this note. Still to do: script 2 to 4; voice 8 to 10 and 12 to 19.

## Intake

| # | Observation | Fix |
|---|---|---|
| 1 | The first call was refused (401) because the laptop was not signed in. 84 seconds lost before the run could start. | Check the sign-in as the very first thing when the user asks for a new video or to resume one. If not signed in, ask for the sign-in before anything else. |
| 2 | The category was asked in a separate turn after the script was recorded (38 seconds). The last six runs of this client gave the same answer. | Ask the title, the approval of the cleaned script and the category in one question, each with a recommended answer to click. |
| 3 | Client, picture AI and drawn route were the same in the last eight runs. | Offer "same as last run" as a ready answer at the start. |
| 4 | Every example in the intake prompt comes from one older film (compressed earth blocks). | Use examples from different kinds of film, with no project named. |
| 5 | The title example ("Compressed Earth Blocks - Documentary Explainer") was copied word for word in earlier titles. | Say "name the subject and what the film is" with no fixed example, or with examples from three categories. |
| 6 | "Clients rarely send a bare script. They send a plan…" assumes a documentary plan. | "The document may be a bare script or a plan around one." |
| 7 | The no-rewrite rule is written in capitals and repeated several times (an older-model habit). It also stops the assistant pointing out a mistyped line. | State the rule once in plain case. Add: list any line that looks mistyped in `notes`; do not change it. |
| 8 | Intake leaves one log line, and the category is logged under `brief`. | Log the prepare step and the questions of the text stages. Log the category under intake. |
| 9 | The run is recorded as SK's though it ran on Uma's laptop. Reviews cannot be split by operator. | No change (14 Nov): it was SK's sign-in. During testing the team uses SK's sign-in on purpose, so the fix is dropped. |

## Brief

Approved by Deepa on 13 Nov 2026. None is built yet.

| # | Observation | Fix |
|---|---|---|
| 1 | The brief waits for the category, but the brief prompt has no place for it. The answer is not used here. | Give the category to the brief prompt and let it set the defaults (ending, examples). |
| 2 | The production values (brand and safety rules, speaker on camera, where it plays) are "asked on every film". The operator answered "Yes, same; approved". | When the client has a latest brief, show its values filled in and ask one approval, with a button "Same as last time, approved". |
| 3 | "Never add a sales call to action by default" suits an explainer, not an advertisement. | The ending follows the film's category unless the operator says otherwise. |
| 4 | Chapter examples are all building work ("Mixing the mortar", "Pointing the joints", "laying the first course"). | One process example and one non-process example, or none named. |
| 5 | Brand and safety examples are site rules ("PPE required or not", "nothing staged"). | Add examples from another category. |
| 6 | Square and 4:5 are refused ("kept for a future update, SK, 2 Nov 2026"). Did not fire here; it will on a social clip. | No change: keep the refusal (Deepa, 13 Nov). |
| 7 | The brief leaves one log line. Six minutes pass with no server call, and the person's time cannot be split from the assistant's. | Log the questions and the "same as last time" answers of the brief. |

## Script

Row 1 approved by Deepa on 13 Nov 2026. Rows 2 to 4 proposed, awaiting Deepa's answers. None is built yet.

| # | Observation | Fix |
|---|---|---|
| 1 | One sentence decides every claim check ("a figure or claim that the message rests on"). The assistant listed four claims and proposed no search, calling them "qualitative"; one is a figure (two weeks of curing). | Five parameters: (a) always propose a check for any number, quantity, duration, percentage or cost; (b) always for a safety or structural claim; (c) for a comparison or saving when a graphic will show it; (d) never for what the footage itself shows; (e) one question for all checks, the claims listed with a tick each. |
| 2 | No rule covers how a line sounds when spoken. The one change made (a stray "the") was found by the assistant's own judgment. | Add to the script step: a line that will sound wrong when spoken (a slip, a tongue-twister, a sentence too long for one breath) is a useful change. **Approved by SK, 14 Nov ("Yes, add it"); built the same day (design/192).** |
| 3 | The script stage has no checking tool. The only method is the assistant's web search in the operator's chat, after a yes. Unchecked claims are stored "checked: false". | Decide whether the assistant's own search is enough or a search service is to be connected. **Decided by SK, 14 Nov: the assistant's own search is enough for now; no search service is connected. Nothing to build.** |
| 4 | The script leaves one log line. The proposed change, the decision and the claims are not in the log. A stage held for a discussion (1 h 48 min) looks the same as a stuck one. | Log the proposed changes, the decisions and the claims with checked or not. **Approved by SK, 14 Nov ("go ahead"); built the same day (design/192): one log line at the script record, written by the tool.** |

## Voice

Rows 1 to 7 approved by Deepa on 13 Nov 2026. Row 11 approved the same day. Rows 8 to 10 and 12 are faults found the same day, proposed. None is built yet. Rows 13 to 15 added at the final review, proposed. The stage was made final at 08:19 UTC.

| # | Observation | Fix |
|---|---|---|
| 1 | "Narrate again" was clicked three times in ten seconds. One was refused (JOB_OPEN); two were accepted and both returned the first recording unchanged, because the inputs were identical. | When nothing changed, the page says it is the same recording and names what to change for a new take. No new job row. |
| 2 | The direction and test passage step took up to 8 min 26 s. The answer "Best fit, passage 1" is the same in VW-21, VW-22 and VW-23. | Offer "Best fit, passage 1" as the recommended answer to click; show the lists only on request. |
| 3 | The pronunciations were approved ("Yes") after the narration was made. In VW-22 they were approved before. | **Replaced by rows 16 and 17 (Deepa, 13 Nov).** The first fix (ask for the pronunciations before the first narration) is withdrawn: a wrong pronunciation is only known after the narration is heard. |
| 4 | The voices page asked for a second sign-in (17 seconds). | One sign-in at the start covers the browser pages too. |
| 5 | The direction prompt works out the kind of film again ("never assumed"), though the run holds the confirmed category. | The kind of film is the run's category. |
| 6 | Three test passages are always proposed. Passage 1 was chosen three runs in a row. | One recommended passage; two more on request. |
| 7 | Three narration job rows hold the same file, and each shows the same character cost though the provider was called once. | Do not count a reused recording as a new cost. |
| 8 | Fault. A narration made again after the pronunciations change returns the old recording. The stored recording is found by voice, model, settings, format and text only (`narration_pieces.py:67`); the pronunciation list is not part of it, so the worker reuses the old audio (`worker.py:75`) and the provider is never asked with the new list. | Make the pronunciation list part of what identifies a stored recording, so a changed list gives a new recording. |
| 9 | "Change a sentence's tag" has a sentence list and an empty tag box; the grey "[softly]" in the box is only a hint. The operator reports typing "measured" in the box; the server received no tag on any of the three clicks, and why is not known. With the box empty the page sends "narrate again" with no change (`voices2.html:200`), the server treats it as no change (`web.py:647`) and returns the stored recording in seconds. The button still says "paid" and the page says "narration submitted; a few minutes". Rows #2 and #3 of VW-23 show the same 7 tags as #1. | With an empty tag box the page does not narrate; it says "type a tag first". When a recording is reused, the page says so and adds no row. **Approved by SK, 14 Nov ("Yes, do that"); built the same day (design/192): the page stops at an empty box; the reused recording is refused with no row by voice row 1.** |
| 10 | "Change a sentence" on the page changes only the delivery tag of a sentence (warm, measured …). It cannot change how a word is pronounced. The operator used it to fix a mispronounced word. | On the page, name the control for what it does, and put "a word sounds wrong" next to it, leading to the pronunciation list. **Approved by SK, 14 Nov ("Yes, with the next set"): both halves are built with the pronunciation set (rows 16 to 19), so the link has somewhere to lead. Not built yet.** |
| 11 | Approved by Deepa, 13 Nov. The tag box expects square brackets ("[measured]") and nothing on the page says so. A tag without brackets is refused by the server only after the click. | The page adds the brackets itself, offers the allowed tags as a list to pick from, and checks the tag before sending, with a plain message. |
| 12 | A tag equal to the one already in force is not sent to the narrator (`voice_direction.py:102`). This film's register is [measured], so choosing "measured" for a sentence changes nothing and the stored recording comes back. | The page says "this sentence is already read as [measured]; pick a different tag" and does not narrate. |
| 13 | A paid narration was made at 08:48 UTC, 29 minutes after the final click, from a second computer, while analysis was running. The prompt says "the accepted narration is never re-recorded"; the page does not stop it. It is not the final. | After the final click, "narrate again" is closed unless the operator reopens the voice stage. |
| 14 | The tag box's hint is "[softly]". The direction prompt warns that volume-lowering tags can make a deep voice breathy and keeps them for the experimental list. | Use a safe example as the hint, or the tag list of row 11. |
| 15 | The log does not record the tag sent with "narrate again", so what the page sent at 07:01 UTC cannot be known. About half of the characters paid for in this stage are not in the film (first voice 2,455; after the final 2,196; final 2,459). | Log the sentence and tag of every "narrate again", and whether the recording was new or reused. |

Row 8, what happened (13 Nov): the operator chose another voice (UD - Narrator) at 08:08 UTC. Its audition and narration carried the pronunciation list (version 1), and that narration was made final at 08:19 UTC. The stability and tag workarounds were not tried in the first voice.

### Pronunciation, corrected after listening (Deepa, 13 Nov, replaces row 3)

| # | Observation | Fix |
|---|---|---|
| 16 | A wrong pronunciation is found only when the operator listens to the full narration. Today the word list is made in the chat before that, by the assistant, and the voices page only shows it. On the page a sentence's delivery tag can be changed and tried; a word's sound cannot. | Decided by Deepa: on the voices page, at the narrations step and before the final narration, the operator corrects words. (a) Pick the word from the script shown on the page. (b) Type how it should sound. (c) Hear it in the voice already chosen. (d) Change it and hear it again, as often as needed. (e) Press "pronunciation final for this word". (f) Do the same for as many words as needed; the page lists every corrected word with its state. (g) Come back to the narrations and narrate again with all the final words. |
| 17 | The pronunciation question is asked before the narration, when nobody can know which words will come out wrong. | Decided by Deepa: remove the pronunciation step from before the narration, in the chat and on the page. |
| 18 | The voices page was built poorly from the operator's seat (Deepa). | Decided by Deepa: design this control properly before building it; look at mobbin.com for patterns. The same server step serves the chat, as the working rules require (one flow, two front ends). |
| 19 | Row 8 (a changed pronunciation list must give a new recording) is what makes rows 16 and 17 work: without it, every test and every new narration returns the stored recording. | Row 8 is built together with row 16, never after it. |

Points settled on rows 16 to 19: all eight approved by Deepa on 13 Nov 2026.

| # | Point | Decided |
|---|---|---|
| a | Is the word heard alone, or inside its sentence? | Inside its sentence, with the word alone as a second button. A word alone often sounds different from the same word in a sentence. |
| b | After the words are final, is the whole script narrated again, or only the sentences that changed? | The whole script, once, after all words are final. Splicing new sentences into an old recording risks a change of tone at the joins. One more paid narration. |
| c | The same word appears several times in the script. | One correction applies to every place the word appears. |
| d | What does the operator type? | A plain respelling, such as "Man-ga-loor". The phonetic alphabet (IPA) stays possible but is not asked for. Whether the voice model obeys a respelling for every word is not tested yet; the hear-it button shows it. |
| e | Are the final words remembered for the client? | Yes. On the next film of the same client they are applied to the first narration without a question, and listed on the page so the operator can remove one. |
| f | How many tries per word? | No hard limit; the page shows how many tries were made. Each try is a small paid request. |
| g | The operator narrates in a second voice after correcting words in the first. | The corrections apply to the second voice too, marked "not yet heard in this voice". |
| h | Corrections after the final narration is chosen. | Not allowed, as row 13 closes the stage; the operator reopens the voice stage first. |

## Analysis

Added by the builder thread, 13 Nov (from the server log; the run was not touched).

| # | What was seen | Fix |
|---|---|---|
| 1 | Not yet approved. `vw analysis start` timed out three times on 94 clips and the assistant reported "no clips queued". The first call was in fact accepted (08:31 UTC) and held the run locked for about eight minutes: before queuing the paid jobs the start checks every clip against the client's library for repeats and makes a frame fingerprint of each clip that is not the same file (`analysis_jobs.start` :122-124, `brandlib.repeats`, since design/147 L2). The assistant's call timed out on its side; each "try again" waited for the locked run and was cancelled by the database's time limit (08:34, 08:38). The jobs appeared at about 08:39 and the workers recovered by themselves. No clip was queued twice. That the fingerprint step took the eight minutes is read from the code and the timing; the log does not time that step. | Server: make the repeat check before the run is locked, so status calls and retries are not blocked. Tool: give the start call a long wait and, on a timeout, say "the server is still working on the start; check the status" instead of offering to try again. |

## Analysis and options

Decided or proposed on 13 Nov 2026 from the model test on clip C0120 (one clip, one run per model, judged by Deepa). None is built yet. Detail: design/_work/analysis-options-review.html, sections 9 to 11.

| # | Observation | Fix |
|---|---|---|
| 1 | On clip C0120 Gemini 4 Hydrogen was right on all four points Deepa checked (two bricks, four strikes, no quiet gap, the interviewer speaks); Gemini 3.8 Flash was right on two. Hydrogen took 177 s against 327 s, and left 5 of 35 uncertainty fields empty against 23 of 34. Cost today about 0.52 against 0.27 dollars; the same from January 2027. | Decided by Deepa: use Gemini 4 Hydrogen for the analysis. Needs SK's yes to deploy. |
| 2 | 54 of the 147 field names in the analysis answer are never named by any rule or check. Among them: the editor's notes for the clip, the speech transcript, why a piece was cut where it was, the hero frame. | Proposed: give the notes and reasoning to the placer, the transcript to the claim check, the hero frame as the piece's picture; drop the low-value fields after the test. |
| 3 | The earlier "truth" for the test clip, written by Claude from frames and sound levels, was wrong on three points. | Rule for every model test: the truth is written by a person who watches the clip. |
| 4 | Whether Gemini 4 alone can say which clip goes under which sentence is not known. | Test plan written (section 11), on VW-19, capped at 15 US dollars. Awaiting Deepa's go. |
| 5 | A pause may be at most 4 seconds today (`narration.py`, MAX_PAUSE_S). | Decided by Deepa, 13 Nov: up to 4 seconds is the usual pause; the longest allowed is 7 seconds. Shorter pauses stay allowed (her "minimum 4" was a slip, corrected the same day). |
| 6 | The library question has the same weakness as the placer's short list. Claude shortlists from each clip's name and ten-line card only ("never the full log"); the pieces' own descriptions and the spoken words are not shown. The whole clip is marked, never one piece of it, so a clip with one piece true in any film and one piece about this film only is all in or all out. When a library clip is offered to a later film, every allowed piece is offered with the clip's overview, not its own description, and with no script fit. Raised by Deepa, 13 Nov. | Approved by Deepa, 13 Nov: show each piece's own description at the library question; mark by piece, not by clip; give a library piece its own description when it is offered to a later film. |
| 7 | The placer's short list carries one line about the whole clip for every piece. Each piece's own description (`visual_action_observed`) and its "does not show" line (`beat_fit_limits`) are written by the model and not on the list. No full log was opened in VW-21, VW-22 or VW-23. | Approved by Deepa, 13 Nov: add each piece's own description and its "does not show" line to the short list. |
| 8 | The scenes file was refused in VW-21 and VW-23 for the same reason: the first word written as "1", not "W00001". The shape shown to the assistant has words in place of a real example. | Approved by Deepa, 13 Nov: one filled example with a real word number in the scenes shape. |
| 9 | Pauses are proposed with the scenes, before anything about the footage is read. None was proposed in the runs seen. | Approved by Deepa, 13 Nov: the server suggests pauses after the first choice of clips, where an action needs longer than its sentence; the operator approves them then. Needs a second approval of scenes and pauses and a step that re-times the cut. |
| 10 | Only one reason for a pause is allowed ("where a step of an activity should finish on screen"). | Approved by Deepa, 13 Nov: more reasons are allowed, such as a pause after a key number or before a new chapter. |
