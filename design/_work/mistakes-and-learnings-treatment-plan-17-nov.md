# The mistakes and learnings of the Treatment and Plan steps, checked against the References step

17 Nov 2026. For SK.

**What this is.** Over 14 to 17 Nov the Treatment and Plan steps were reviewed line by line and changed heavily. This document lists every mistake found in those two steps and every learning stated, and then checks each one against the References step (the footage pictures, the paid reference sets, and the page where the operator judges them). **What was read:** design notes 151, 188, 190, 191, 195, 200 and 202 to 210; SK's review points and the answers; the critic reviews after each build; the commit messages since 14 Nov; the code and the instructions the References step runs; and VW-24's own files: the 49 lines of step 1 as the operator saw them, the plan's 50 things, and all 38 reference sets that were made (114 pictures, each with the full text sent to the picture model, the model's notes and the check result). I opened the four contact sheets and looked at every set. **Nothing is built or changed.** No code was touched; nothing was run on the server or the database.

Yesterday's review of the footage pictures (`references-step-review-vw24-17-nov.md`) is taken as known and is not repeated.

---

## Summary

| | Count |
|---|---|
| Mistakes and learnings of the Treatment and Plan steps | 56 |
| Present in the References step today | **41** |
| Not present | 11 |
| Not checked | 4 |
| Data and rules of the two steps that the References step uses in full / in part / not at all (Part 3) | 21 / 19 / 20 |

The References step went onto the page on 16 Nov as it stood. It did not get the review the two earlier steps got. On VW-24 the result is 38 paid sets (about ₹1,345), of which 21 fail a real check of the program's own second look, and the operator is shown none of it.

### The ten that matter most for the References step

| # | The mistake | Where it showed in the Treatment or Plan | Where it shows in References, on VW-24 | Impact |
|---|---|---|---|---|
| 1 | Faults that the program could catch reach the operator, and a flag is not shown (items 14, 55) | The three framing warnings (SK, D7); "a flag warns the user" (design/195) | The second look runs on picture 1 of each set only. 21 of 38 sets fail a real "must" line. None stops the set and none is on the page. Every set also carries a false "size" failure, so all 38 read as failed. | The operator is the first and only checker of 114 pictures, and the program's own findings are thrown away. |
| 2 | Words that must be exact are retyped by the assistant, not placed by the program (item 46) | The Direction copied by hand into the plan and refused | A thing's description, views and place are retyped. Every thing got the place of the film's first scene: a fan regulator on an outside wall, a bucket and cement bags in the street. | Pictures that do not match what was approved on the plan page. |
| 3 | The instructions and the program disagree (item 44) | "Not to scale" told by the instructions and refused by the program | A technique must show the work. The instruction says "nobody in it" and the check demands "no person, no hands". Three of five technique sets fail that check; the picture model's own note says the rule cannot be kept. | Either the set fails its own check or it does not show the technique. |
| 4 | The same fact is asked more than once (item 5) | A size shown in several drawings (design/209) | The same thing is in several paid sets, and they disagree. The yard of materials has its own stone heap, bags and bucket, different from their three sets. Four sets show the ceiling four ways. | Money for each, a judgement for each, and no single truth for the shots to follow. |
| 5 | An outside source wins over the film's own choice, and the note that says so is hidden (items 10, 49) | The script's notes followed over the narration (the kiln) | The picture model changed the request in at least two sets and said so in its notes: two switches added to the fan regulator; the heaps and bags moved off the roof deck. The page shows no notes. | The operator is not told that what they approved in words was set aside. |
| 6 | The assistant decides alone (item 12) | 14 treatment warnings cleared before the operator saw them | The assistant chose 41 things for a paid set and wrote each request. The operator never sees a request. The trowel and the bucket are in the footage, and their sets were made from invented descriptions. | The operator pays without seeing what was ordered; the film's own things are replaced by made-up ones. |
| 7 | A figure is guessed where it is not known (item 18) | Still seconds guessed (design/202 review) | All 24 sizes are "unknown" in the plan. No request carries a size from the plan; several carry sizes in the assistant's own words. The pan's reference is the frame where concrete covers it. | Sizes nobody approved are fixed into the references. |
| 8 | Rules that fit one kind of film or one kind of thing (items 38, 39, 40) | Building-site wording; "three to five beats"; water asked for its unit size | Every person is asked for "a working pose of their trade": the daughter sweeps with a broom. Pictures 1 and 2 of most thing sets are nearly the same picture. Eight of nine place sets fail "the subject fills the frame". | A third of the money buys a duplicate; people are given jobs the film never gave them. |
| 9 | What the operator is shown (items 1, 2, 3, 9) | No reasons; the world never shown; labels repeated; "changed" not explained | 49 flat lines, 33 with the same sentence; no description, no reason, no grouping; a set made again shows neither the operator's words nor the earlier set. | The operator cannot judge "leave it out" or "is this right" from the page. |
| 10 | Cost shown in part, and faults found after the money is spent (items 29, 30, 31) | One limit for all films; a shot accepted at the plan and thrown out later | The page shows the sets against the limit but not what the shots still need. Nothing free stands between the assistant's requests and the paid sets. "No" with no words pays for the same request again. | The limit is met in the middle of the film; second sets are paid for without a change. |

---

## Part 1. The mistakes and learnings of the Treatment and Plan steps

Who found it: **SK**; **critic** (a reviewer who had not written the code); **operator** (seen on a film by the team); **builder** (found while building or reading).

### Theme 1. What the operator is shown

| # | The mistake or learning | Found by, and where it is written | How it was fixed |
|---|---|---|---|
| 1 | A line said what would be shown, not why. | SK, on VW-24. design/202 section 1 | Each shot carries two reasons. The plan page shows them again under each gap. |
| 2 | The operator never saw the world of the film whole. | SK. Review point 1 (`requirement-visuals-rules-review-16-nov.md`) | "The world of this film" is the first block of the plan page. |
| 3 | The same label was repeated on every row; nothing was grouped. | SK, 16 Nov. Plugin 0.89.2 | One heading per kind; each group folds. |
| 4 | A stored record was printed field by field, nine times. | SK and the operator, VW-24. design/209 | Plain words; the working notes are not shown. |
| 5 | The same fact was asked more than once (37 size lines, 7 of them in more than one drawing). | SK, VW-24. design/209 | Each size is asked once; later lines say "already confirmed". |
| 6 | The Direction was asked as "Do you accept this line?", so it was not seen as a step. | SK, VW-23 and VW-24. design/202 section 1 | Asked by name, with what it is and what a yes means. |
| 7 | The operator's plain warning lines were not on the plan page. | critic, after design/207 | "Read before you answer" above each gap. |
| 8 | An earlier text was shown cut at 400 characters. | SK, on the page. design/205 point 1 | Shown whole. |
| 9 | "Changed since you last saw it" confused the operator. A change they ask for must come back marked, with before and after. | SK, VW-24. design/202 section 3.3; plugin 0.89.1 | "Changed as you asked", against what the operator last saw; the list folds. |
| 10 | Notes that matter to the decision were hidden, and notes that do not were shown. | builder. design/209 | The assistant's working notes were taken off the page. |
| 11 | A recorded line lost its content; the operator could not read back what they approved. | SK and builder. design/209 | Approved drawings and materials stay on the page, folded. |

### Theme 2. Who decides

| # | The mistake or learning | Found by, and where it is written | How it was fixed |
|---|---|---|---|
| 12 | The assistant took decisions of taste alone: on VW-24 it rewrote the treatment to clear 14 warnings before the operator saw anything. | builder, for SK. `decisions-taken-by-the-system-16-nov.md` | Proposed, not built: the first draft is shown; a "Decided for you" list. |
| 13 | The operator was asked things that need no answer from them (a footage reuse). | SK, decision D2. Review point 9 | The question was removed; the reason is kept on record. |
| 14 | Faults the writer could prevent reached the operator (the three framing warnings). | SK, decision D7. Review point 11 | Written as instructions; the warnings go to the assistant only. |
| 15 | The builder assumed a limit that was not there ("the guide cannot move a thing"). | SK, decision D5 | A thing travels on a timed path. |
| 16 | The builder took decisions by default and they went live. | builder, stated in design/202 and design/210 | Each was written down for SK. |

### Theme 3. Whether the sentences are true

| # | The mistake or learning | Found by, and where it is written | How it was fixed |
|---|---|---|---|
| 17 | Texts said what the program does not do: a warning that never fires; a refusal placed at the wrong step. | SK's review, then builder. "Three corrections to the guide" | The dead warning was deleted; the guide corrected. |
| 18 | A figure was guessed where it should have been marked "not known". | critic. design/202 review, fault 1 | Counted shot by shot; what cannot be told is kept apart. |
| 19 | The log said nothing of what a draft returned or what the page recorded. | builder. Stage review of VW-24's treatment | Each page answer is a log line with the operator's words. |

### Theme 4. Questions asked again, answers lost

| # | The mistake or learning | Found by, and where it is written | How it was fixed |
|---|---|---|---|
| 20 | One changed word made every gap be asked again; an answer went back to "to accept" without notice. | SK, VW-22 and VW-21. design/191 | One question for a shared change; "what changed" on each gap. |
| 21 | The operator was sent several rounds of answers. | SK. design/206, first point | One visit and one "done" for the whole plan. |
| 22 | The check told one fault at a time, so a plan needed four rounds. | SK. Review point 2 | Every fault in one answer. |
| 23 | A yes was recorded although it rested on something corrected in the same visit. | critic. design/209 | Corrections are recorded first; such a yes is asked again. |
| 24 | An answer given to an older text stayed shown after the text changed. | builder, on the trial page. design/202 | Each answer names its item; a stale one is ignored. |
| 25 | A yes the program refused was left with the operator, though the fault was the assistant's to fix. | critic. design/209 | The assistant is told it is its own to fix. |
| 26 | A step did not end after its last answer. | critic. design/210 | The round is completed by the program's own test. |
| 27 | A paid remake ignored the words the operator typed. | critic. design/210 | "No" with words is made again with them. |
| 28 | After a page step, the "what next" sentences still sent the assistant to the chat (13 faults). | builder, after the deploy | One function for "what next"; live as 0.107.1. |

### Theme 5. Cost

| # | The mistake or learning | Found by, and where it is written | How it was fixed |
|---|---|---|---|
| 29 | One cost limit for every film, and no cost on the plan page. | SK. Review point 16b | A limit by length; the estimate against it on the plan page. |
| 30 | A fault was found late, after money was spent. Free checks come before paid steps. | SK's review; design/200 | The plan check warns earlier; drawings are approved before any paid picture. |
| 31 | The same thing must not be charged twice. | SK. design/208 | An earlier try of the same spelling is replayed, not charged. |
| 32 | A storage hiccup could rewrite a running film's cost limit. | critic. design/207 | The limit is decided from the film's own record. |
| 33 | The plan's estimate left out the reference sets. | builder. design/209 | "Up to ₹Y for N reference sets." |

### Theme 6. Real people

| # | The mistake or learning | Found by, and where it is written | How it was fixed |
|---|---|---|---|
| 34 | A real person's picture could reach the picture model with no recorded permission, by a side door. | critic. design/207 | One test for every door. |
| 35 | A photo given after the reference step was complete led nowhere. | critic. design/207 | A complete round opens again for that person. |
| 36 | "A real, named person is shown as a made-up stand-in" was told in one place only. | builder. design/207, known limits | Told on the plan page. |
| 37 | Client material, people included, is stored on claude.ai under the operator's account. The question was raised and not answered. | builder. design/204; the reference-steps analysis, question 1 | Not settled: taken as decided by the request. |

### Theme 7. Rules for every kind of film

| # | The mistake or learning | Found by, and where it is written | How it was fixed |
|---|---|---|---|
| 38 | Building-site wording stood in general rules and messages. | SK. Review point 14; design/202 | Nine instruction sentences and six messages reworded. |
| 39 | A fixed count stood where a test was meant ("three to five beats"; "a still always moves"). | SK. design/205 | The sentence gives the test and leaves the count open. |
| 40 | One rule was applied to kinds it does not fit: water was asked for its unit size. | SK. Review point 5 | Unit sizes only for a material laid in units. |
| 41 | A word match fired on the wrong thing ("big savings" as a size claim). | SK's review. Points 6 and 8 | The circling test was removed. |
| 42 | A rule written for an older model was still in force. | builder. Stage review of VW-24's treatment | Refusals became warnings. |
| 43 | A default that suits documentaries stood in the general text. | builder. Same stage review | Not changed yet. |

### Theme 8. The instructions against the program

| # | The mistake or learning | Found by, and where it is written | How it was fixed |
|---|---|---|---|
| 44 | The instructions told the assistant one thing and the program refused it. | critic, design/207; SK, review point 14 | The sentences were brought in line. |
| 45 | A helper's brief was left behind when the rules changed, and a shot was never drawn. | critic. design/207 | The brief was updated. |
| 46 | Words that must be exact were retyped by the assistant. Learning: the program places what must be exact. | SK's review. Point 14 | The program places the Direction in the plan. |
| 47 | A behaviour lived only in an instruction. Rule: the program holds it, for the chat and the page alike. | SK, 20 Oct. The repository's working rules | A standing rule. |
| 48 | The writer had no checklist for the part it writes alone, and that part caused the faults. | SK's review. Point 2 | A checklist for the assistant; shot sizes added to the helper's. |
| 49 | An outside source was followed over the film's own choice (the script's notes: the kiln). | SK, VW-24. design/202 | The script's notes are no longer handed over. |

### Theme 9. How the work is built and reviewed

| # | The mistake or learning | Found by, and where it is written | How it was fixed |
|---|---|---|---|
| 50 | Learning: after a build by helpers working apart, run three reviews before a deploy: instructions against the program, the requirement against what was built, and defects. | SK asked for it; 22 faults found. design/207 | Done for design/207. |
| 51 | Nothing was run on a real film; causes were read from the code. | builder, stated in each note | Said in each note. |
| 52 | A film in progress at a release meets the new rules half way. | builder. design/202, design/207 | Accepted for test films. |
| 53 | Learning: every change says what happens to the older way. | SK, 30 Oct | Rows 72 to 102 of the decision log. |
| 54 | Learning: the load on the assistant (a card retyped character for character). | SK and builder. design/202 section 6 | The page takes data; the assistant sends a file. |
| 55 | Learning: a flag warns the user; it does not block. | SK, 14 Nov. design/195 | Applied to the treatment's missing reasons. |
| 56 | The tool's own rewrite was taken for a hand edit, and a correction could be dropped. | operator, VW-24. design/209 | A fingerprint, not a file time. |

---

## Part 2. Is it in the References step?

Short names used in the evidence column only:

| Short | File |
|---|---|
| VS | `server/app/visuals_stage.py` |
| PF | `server/app/page_flow.py` |
| CF | `server/app/chat_flow.py` |
| DH | `plugin/pages/decisions.html` |
| IC | `server/app/image_check.py` |
| INS | the assistant's instructions, visuals stage, part "picture-search" (`server/procedures/v3.json`) |
| EV | `ux1-mockup/vw24-part1/evidence.json` (the plan's things and the assistant's requests) |
| RD | `ux1-mockup/vw24-part1/round.json` (the 49 lines of step 1) |
| SETS | `ux1-mockup/vw24-sets/sets.json` and the contact sheets `sheet1.jpg` to `sheet4.jpg` |

A "request" below means the full text sent to the picture model for one set. A "must line" is a line of the program's own second look that the picture has to pass.

### Theme 1. What the operator is shown

| # | In References? | Evidence | Impact on the operator or the film |
|---|---|---|---|
| 1 | **YES** | A reference line is a title, one fixed sentence, pictures and buttons (PF:482-485). RD: 33 of 49 lines read the same, word for word. | The operator cannot tell why a thing is in the film or which shots use it, so cannot judge "Leave it out". |
| 2 | **YES** | The references page has no world block and no description of any thing (PF:534-581). | The operator judges "the neighbour" without the words that say who she is. |
| 3 | **YES** | RD is 49 flat lines: people, materials, objects, places, techniques, with no heading. The page has no grouping for them. | A long scroll; nothing can be folded once read. |
| 4 | **NO** | The page lines are plain sentences (PF:475-480, 509-519). | None. |
| 5 | **YES** | The same thing is in several paid sets, and they differ (SETS, by looking). The yard of materials shows a small dark bucket, tan printed bags and a small stone heap; the bucket set is galvanised steel, the bag set is plain grey, the stone-heap set is a large heap. The oil tin is oval in its own set, round and printed in the oil set, square in the technique set. The ceiling is flat square panels in the ceiling-finish set and the room set, flat oblong tiles in the shuttering set, and ribbed tiles in the tile set. | About ₹35 and one judgement for each; the shots then have several different "truths" to follow. |
| 6 | **NO** | Each line names its thing, asks one question, and says what a yes does and costs (PF:475-482). | None. |
| 7 | **YES** | A reference line cannot carry a "read before you answer" line (PF:482, 508). | Three facts are missing where they matter: a real person with no photo yet; the client's own thing; a size not known. |
| 8 | **NO** | Nothing on a line is cut. Only the first four footage pictures show (PF:474); VW-24 has at most two. | None. |
| 9 | **YES** | A set made again after "Correct it" comes back with no mark, without the operator's words and without the earlier set (PF:508-513). | With several corrected sets in one visit, the operator must remember what they asked of each. |
| 10 | **YES** | Each set comes back with the picture model's notes: what it chose, what it changed in the request, its sources. 111 of 114 pictures carry notes; 20 sets have a part on what was changed (SETS). The page shows none (PF:489-531). Two examples: the fan regulator, "I included two standard toggle switches on the same plate"; the roof deck, the heaps and bags "are staged on the unpaved ground" and not on the deck as asked. Sources were recorded for 30 of 114 pictures only. | The operator is not told when the model set aside what the plan asked for. |
| 11 | **YES** | An approved set keeps its pictures (PF:523-530). A thing settled from its footage picture is left out of the sets page (PF:501). VW-24 has seven such things (SETS, `golden`). | After step 1 the operator cannot look back at the footage pictures they approved. The pan is one of them: its reference is the frame where concrete covers it. |

### Theme 2. Who decides

| # | In References? | Evidence | Impact on the operator or the film |
|---|---|---|---|
| 12 | **YES** | The assistant alone decides which things get a footage picture and what each paid set is asked to show. The page holds no request (PF:482). 111 of 114 pictures were made with no picture given to the model; only the tile had a footage picture and two drawings (SETS, `cost.inputs`). The trowel and the buckets are in the footage (EV: "a reddish-brown handle"; "two white cylindrical plastic buckets"); their sets show a wooden-handled trowel and a galvanised bucket, as the assistant wrote them. | The operator pays for sets without seeing what was ordered. The film's own things are replaced by invented ones that will not match the footage beside them. |
| 13 | **YES** | SK decided every named person gets a sheet. The page still asks for each of the 7 people, "Have a reference set made (paid)?" (RD lines 1 to 7; CF:397). A set held by a cause only the assistant can settle is shown to the operator with "Make it" and "Leave it out" (CF:446; PF:514-519). | Seven answers that are not choices; and a question the operator cannot answer. |
| 14 | **YES** | The second look runs on picture 1 of each set only: 38 checks for 114 pictures (SETS). 21 of the 38 fail a real must line. Examples: the prop set mixes a steel prop and a wooden post and fails "one way only"; the tile set fails 13 facts of its approved drawing; the house, the roof deck and the oil set fail "no text"; two people fail "plain ground". No failure stops a set, and the page shows no check (PF:489-531). | The operator is the first and only checker. Pictures 2 and 3 are never checked by anyone but them. |
| 15 | **YES** | "Three pictures per thing: the whole, a three-quarter view, a close-up" is the builder's own assumption (design/151 section 13: "Assumption"). On VW-24, pictures 1 and 2 are nearly the same picture for the brick, bucket, cement bag, stone heap, trowel, wire coil, oil tin, curtain, window shutter, street and lane (SETS, by looking). | About a third of the money buys a second copy of picture 1. The views the plan asked for (the mason's "right hand and forearm", the tile-maker's "hands") were not made. |
| 16 | **YES** | Three defaults stand without SK's word: a click on a priced button plus "done" is the spend; no "accept everything"; and footage pictures, people included, are stored on the claude.ai page (`reference-screens-on-the-page-plan.md`: "One thing I take as decided by this request"). | SK has not ruled on them. |

### Theme 3. Whether the sentences are true

| # | In References? | Evidence | Impact on the operator or the film |
|---|---|---|---|
| 17 | **YES** | Five untrue statements. (a) Every set's picture 1 carries a failed must line "size" that is false: the program compares "2752x1536" with a record of the shape and quality asked for, which can never match (IC:318-320; SETS). So all 38 sets read as failed. (b) The two sets that failed say "OpenAI rejected the request"; the model was Gemini (SETS, `jobs`). (c) "Your footage has no picture of it" means only that none was taken (yesterday's review). (d) The comment box says "where a set is corrected, it says what to correct" (DH:400); at step 1 the comment does nothing (item 27). (e) A set with drawings is told the drawings "were made from this thing's real sizes" (VS:1967), also when sizes were assumed. | A false alarm on every set hides the 21 real ones. A wrong name in an error sends the builder to the wrong place. |
| 18 | **YES** | All 24 sizes of VW-24's things are "unknown" in the plan (EV). No request carries a size line from the plan: 0 of 116 (SETS). The requests carry sizes in the assistant's words instead: "about a hand wide", "knee-high", "five across and four deep", "a finger deep" (EV). The first footage picture of a thing is taken as its reference without a choice (VS:3218); for the pan that is the pouring frame (SETS, `golden`). | Sizes nobody approved are fixed into the pictures every shot starts from. |
| 19 | **NO** | Every answer of the round is logged, and the record says what was recorded, kept, stale and refused (PF:828, 872, 918). | None. |

### Theme 4. Questions asked again, answers lost

| # | In References? | Evidence | Impact on the operator or the film |
|---|---|---|---|
| 20 | **YES** | A kept step-1 answer is dropped without a word when that thing's footage pictures change (CF:312-314). A set is marked "made before a change" only for a changed material spec or photo (VS:3490-3509): a person re-described in the plan keeps the old sheet, unmarked. A thing the plan no longer names drops out silently (CF:380). | The operator answers a thing twice without knowing why; an out-of-date sheet stays in use. |
| 21 | **YES** | By design, each "No" or "Correct it" is one more round. With 21 of 38 sets failing a real check, and the plan's views and places not carried, many will come back (INFERENCE: the operator had not yet judged the sets when the files were taken). A long list is also cut and the rest shown after the next "done" (PF:549-561). | More visits and more paid sets. |
| 22 | **YES** | The posting of the round stops at the first faulty row (VS:3178-3196). People who read alike are refused one pair at a time (VS:2015). | A slower start; the operator waits. |
| 23 | **NOT CHECKED** | A like case exists: a technique's set approved in the same visit in which its tool's set is rejected. I did not trace what the shots then use. | |
| 24 | **NO** | A set made again has a new name in its item (CF:442); step 1 is guarded by the stamp of the footage pictures (CF:314). | None. |
| 25 | **YES** | For any refusal on a reference line the assistant is told only "tell the operator and give them the link again" (PF:413). | The operator is handed faults that are the assistant's to fix. |
| 26 | **YES** | Written in design/210 itself: "a round element the plan no longer names still holds step 2 open". Not fixed. Not seen on VW-24. | The step may not end. |
| 27 | **YES** | Fixed at step 2 only. A comment typed at step 1 is logged and goes no further (CF:399-405). | "The handle is red", typed at step 1, is not in the set; a second set is paid for. |
| 28 | **NO** | The sentences after each reference step name the page or the wait (PF:400-413, 901-917). | None. |

### Theme 5. Cost

| # | In References? | Evidence | Impact on the operator or the film |
|---|---|---|---|
| 29 | **YES** | The page shows the sets, the limit and the spend (PF:570), not what the plan's shots still need. Step 1 closes if the sets alone fit (PF:598). VW-24: ₹1,345 spent on 38 sets, of a ₹3,754 limit. | Over a third of the limit went on references before one still or take was made; about ₹2,400 is left. INFERENCE: the film meets its limit later; the shots' estimate was not in the files read. |
| 30 | **YES** | Nothing free stands between the assistant's requests and the paid sets. The program tests only that a request is not empty and has no "how to" words (VS:2029-2032, 3191-3192). 38 sets were paid for; the second look then found real faults in 21 (SETS). | Faults a free look at the request would have caught (the wrong place, a mix of two things in one set) are found after payment. |
| 31 | **YES** | "No" or "None of these" with no words makes the set again from the very same request (VS:3375-3381). See also item 5. | ₹35 for a second throw of the same dice. |
| 32 | **NO** | The round only reads the limit (VS:730; PF:420-423). | None. |
| 33 | **NO** | The count on the references page comes from the lines themselves (PF:486). | None. |

### Theme 6. Real people

| # | In References? | Evidence | Impact on the operator or the film |
|---|---|---|---|
| 34 | **NO** | A person's set takes a photo only with the recorded permission (VS:3744, 2507-2515); the page asks for the permission words first (PF:619; DH:303). On VW-24 all 21 pictures of the 7 people were made from words, with no picture given (SETS). | None. |
| 35 | **NO** | Read at VS:3512-3538. | None. |
| 36 | **YES** | The references page does not repeat it; every person gets the same sentence (PF:476). | This is the page where the operator can add the photo. |
| 37 | **YES** | Every footage picture on a reference line is sent to the page's store, a person's too (PF:474-483). The permission that is recorded is for making AI pictures, not for this. VW-24's 7 people have no footage picture, so it has not happened on this film. | SK has not ruled on it. |

### Theme 7. Rules for every kind of film

| # | In References? | Evidence | Impact on the operator or the film |
|---|---|---|---|
| 38 | **YES** | "On one real site" is in all 95 requests for a thing; "a working pose of their trade" is in all 21 for a person (SETS; VS:1958, 1960, 1973). The pictures show it: the daughter sweeps the ground with a broom, the mother winnows grain, the neighbour carries a pot, the home owner holds rolled papers (SETS, by looking). | People are given work the film never gave them. A film that is not about a site gets site wording in every request. |
| 39 | **YES** | Three pictures of fixed kinds for every thing (VS:1976-1984). See item 15 for the near-duplicates. | A fixed count where the plan's views should decide. |
| 40 | **YES** | One set of rules for every kind that is not a person. A place is told "the subject fills the frame; the setting is only a soft hint" (VS:1986); 8 of 9 place sets fail that line, because for a place the setting is the subject (SETS). A technique is told "no person, no hands" (VS:1988); see item 44. Every thing is told it stands in the place of the film's first scene (VS:2019-2021): the same street is in all 95 requests (SETS). | Checks that fail for the wrong reason; indoor things pictured on a street. |
| 41 | **YES** | Footage is matched to things by shared words (yesterday's review). "People who read alike" is a word match too (VS:1994-2003): the word "white" anywhere counts as grey hair. The refusal of "how" in a request is three fixed phrases (VS:1972). | False matches and false refusals. |
| 42 | **NOT CHECKED** | The fixed opening of a request and "one picture per turn" were written on 4 Nov for one model. Whether today's model still needs them was not tested. The near-duplicates of item 15 suggest the per-turn way does not give three different views. | |
| 43 | **YES** | Every thing is told "natural daylight as in that place, natural colours, no filters, no stylisation" (VS:1965), whatever the film's kind. The kind of film is not in the request at all. | INFERENCE: a night film, a studio product film or a stylised film gets daylight photographs as its references. |

### Theme 8. The instructions against the program

| # | In References? | Evidence | Impact on the operator or the film |
|---|---|---|---|
| 44 | **YES** | The plan tells the assistant to list each way of working as a "technique". INS says a thing's request has "nobody in it, never how the work is done". The check demands "no person, no hands" (VS:1988). On VW-24, three of the five technique sets that were made (laying a brick, curing, oiling) show hands or a whole man and fail "no person" (SETS). The picture model wrote, for the curing set, that it kept an arm in the picture to avoid "a bucket magically flying or tipping by itself". | A technique cannot be shown under these rules. The set either fails its check or shows a tool lying still. |
| 45 | **YES** | INS was updated for people. It names no views, no world rules, no signs of use, no sizes, and still says "a frame of each". No helper exists for the references; the assistant writes all requests alone. | The assistant writes each request from memory. |
| 46 | **YES** | A thing's description is retyped by the assistant and sent as written (VS:3287). EV: the plan asks for the pan "side" and "tipped, pouring"; the retyped request asks for "from the side and from above". The place is not taken from the thing's own scenes: the fan regulator is on an outside wall with the street behind it; the bucket, the bags, the brick and the wire coil lie in the street (SETS, by looking). | The pictures do not match what was approved on the plan page. |
| 47 | **YES** | "The sharpest frame, the subject large and evenly lit" and "what the picture must represent, its frame, nobody in it" are only sentences in INS. The program holds neither. | Nothing enforces them. |
| 48 | **YES** | The assistant writes 49 requests alone, with no checklist. The program's only tests are "not empty" and three phrases (VS:2029-2032). | The same cause as the plan's four rounds, without the plan's check behind it. |
| 49 | **YES** | Every thing's request says "if anything I ask for contradicts what the real photographs show, the photographs win" (VS:1955). On VW-24 the model used this: two switches were added to the fan regulator; the heaps and bags were moved off the roof deck (SETS, `notes`). The page does not show the notes (item 10). | What the operator approved in words can be set aside by web photographs without their knowing. |

### Theme 9. How the work is built and reviewed

| # | In References? | Evidence | Impact on the operator or the film |
|---|---|---|---|
| 50 | **YES** | design/210 records one critic limited to critical faults, and a wording review after the deploy. No review of "the plan's content against what the round uses" is recorded. | The faults in this document reached a real film. |
| 51 | **YES** | design/210 "Not verified": the page with a real film. The false "size" failure (item 17) is on every set of the first real film that made sets. | A fault any one real set shows was not seen before release. |
| 52 | **NOT CHECKED** | Whether any of VW-24's requests were written under older instructions. | |
| 53 | **YES** | The older reference way was retired for new films on 4 Nov. With it went the only reader of the plan's "views" (VS:2166, 2179, 2187 are all in the older way). The plan still demands the views; nothing new reads them. INFERENCE: this is how the views were lost. | See item 15. |
| 54 | **NOT CHECKED** | The assistant types 49 requests and sends the pictures in batches of calls. Time and permission prompts on an operator's machine are not known. | |
| 55 | **YES** | The flags here neither block nor warn. The second look's failures are stored with each picture and shown nowhere on the page (PF:489-531). The one failure that is on every set is false (item 17). | The learning was "warn the user". The user is not warned. |
| 56 | **NO** | A round posted again after step 1 merges and never wipes the sets (VS:3223-3261). | None. |

### Counts

| In References? | Items | How many |
|---|---|---|
| YES | 1, 2, 3, 5, 7, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 20, 21, 22, 25, 26, 27, 29, 30, 31, 36, 37, 38, 39, 40, 41, 43, 44, 45, 46, 47, 48, 49, 50, 51, 53, 55 | 41 |
| NO | 4, 6, 8, 19, 24, 28, 32, 33, 34, 35, 56 | 11 |
| NOT CHECKED | 23, 42, 52, 54 | 4 |

---

## Part 3. What the two earlier steps produce that the References step does not use, in short

The full table, with 70 items and the proof for each, is `refs-review/C-carry-over.md`. Below are only the items the References step uses in part or not at all.

### Not used at all

| Item | What the References step should do with it | Effect today |
|---|---|---|
| The views the plan asks for | They name the pictures of the set and the footage frames to take | The three pictures are fixed. 14 VW-24 things ask for views that were not made. |
| Why and where a thing is used: the two reasons of each shot; the shots and how close they are | One line under each thing on the page; the closest shot decides the pictures | The operator cannot judge "leave it out"; references are made at distances the film may not use. |
| The world block on the page, grouped and folding | Group the things by kind; keep the world block at the top | 49 flat lines. |
| The world rules (place, period, people, work, clothes, tools) and "not shown" | The rules that bind a place or a person go into its request | Absent from every request. |
| Everyday things; fixed things belong to the place | A place's request names its fixed things | Each picture of a place may put them elsewhere. INFERENCE. |
| Signs of use of a place; "shown clean" | A place's reference shows the place in use | Added only to shot pictures. Nine VW-24 places carry them. |
| Confirmed facts about how a thing looks | Sent with the request as "what must be true" | The set is made from web photographs alone. |
| "Changed as you asked", with before and after | Shown on a set made again | Not shown. |
| "Read before you answer" lines | One or two plain lines on a thing | Not possible on a reference line. |
| Rules filed by kind of film | The kind of film is passed; the fixed wording is general | Building-site wording in every request. |
| The Direction, and the brief's purpose, audience and tone | One line at the top of the page for the operator | Not on the page. Low effect. |

### Used in part

| Item | What the References step should do with it | Effect today |
|---|---|---|
| A thing's description and requirements | The program places them in the request, as it does for a person, and shows them on the page | Retyped by the assistant for every thing. |
| The place of each scene | Use the place of the scenes the thing is in | Every request carries the first scene's street. Seen in the pictures. |
| Sizes with their status | Show them on the page; a size in a request comes from the plan | No plan size reached any request; loose sizes in the assistant's words did. |
| A material's amount or coverage | With the description | Written by the assistant ("a finger deep"). |
| A real, named person | Said on that person's line | The same sentence for every person. |
| The client's own thing, or a typical one | Said on the line; no paid set offered as the plain default for the client's own thing | Not shown. |
| Clothes per scene; clothes change with time | The sheet shows the outfit of the most scenes and names the others | All outfits in one line, with no rule. |
| Which things a made picture shows | Ask and pay only for those | Tested for people only. |
| Right-handed work | Added to a person's working pose and a technique's set | Only if the assistant wrote it. |
| The plan's estimate against the limit | Three figures together: spent, these sets, what the shots still need | Only the sets and the spend are shown. |
| The warnings raised at the plan | Repeat the ones that matter here | People who read alike: yes. The others: no. |
| Every fault in one answer | The round's own check lists every faulty row | Stops at the first. |
| Assumed sizes in a drawing | Sent as "about", or left out of "what must be true" | Sent under "real sizes". The tile set fails 13 drawn facts. |
| A plan changed after the sets were made | Mark a set whose plan fields changed | Marked only for a spec or a photo. |
| One visit per step | Say when a kept answer was dropped | Dropped silently when the footage pictures change. |
| The operator's words in the log | A step-1 comment goes into the set's request | Logged only. |
| A recorded line keeps its content | Show the things settled from footage too | Left out of the sets page. |
| The instructions brought in line | Say what a request takes from the plan, or let the program place it | Updated for people only. |

---

## Not checked

- Items 23, 42, 52 and 54 of Part 2.
- The operator had not yet judged the sets when the files were taken, so how many come back for a second round is not known.
- I looked at the pictures at contact-sheet size. Small faults (a wrong hand, lettering on a bag) cannot be told at that size and are not claimed.
- Whether the people's faces and builds match their written descriptions was not compared line by line.
- The step-1 page read here is a trial copy, built to show the screen as it would look before any set was ordered. Its "up to 41 sets, about ₹1,450" is that screen's estimate, not a second payment. The real spend is ₹1,345 for the 38 sets made.
- The shots' estimate for VW-24 was not in the files read.
- The chat way back was read only where it shares code with the page.
- No set was made or remade for this study; nothing was tried against the picture model.
