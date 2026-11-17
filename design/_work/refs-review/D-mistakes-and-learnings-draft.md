# D. Mistakes and learnings of the Treatment and Plan steps (14 to 17 Nov), each checked against the References step

17 Nov 2026. **Draft.** Read-only study for SK. No code was changed. Nothing was run on the server, the VM or the database.

SK's question 2: which mistakes found in the Treatment and Plan steps, and which learnings, could be repeated in the References step?

**Short answer: most of them are.** Of 56 mistakes and learnings, 40 are present in the References step today, 12 are not, and 4 I could not check. The step was put on the page on 16 Nov (design/210) as it stood. It did not get the line-by-line review that the Treatment and the Plan got.

## How to read this file

- **The References step** means: the footage pictures (step 1), the paid sets, the judging of the sets (step 2), and the page that shows them.
- Each item says: the mistake or learning; who found it and where it is written; how it was fixed; then **"In References?"**: YES, NO or NOT CHECKED, with the proof and the effect.
- **FACT** means read in the code or in VW-24's files. **INFERENCE** means reasoned from the code, not seen on a run.
- Yesterday's review (`design/_work/references-step-review-vw24-17-nov.md`) is taken as known. Where an item rests on it, the item says "yesterday's review" and adds only what is new.

Short names for files (the same as in file C):

| Short | File |
|---|---|
| VS | `server/app/visuals_stage.py` |
| VC | `server/app/visual_contract.py` |
| PF | `server/app/page_flow.py` |
| CF | `server/app/chat_flow.py` |
| DH | `plugin/pages/decisions.html` |
| INS | `server/procedures/v3.json`, visuals stage, part "picture-search" |
| EV | `ux1-mockup/vw24-part1/evidence.json` (VW-24: plan elements, frames, set prompts) |
| RD | `ux1-mockup/vw24-part1/round.json` (VW-24: the 49 lines of step 1) |
| REQ | `design/_work/requirement-visuals-rules-review-16-nov.md` (SK's review points) |
| SYS | `design/_work/decisions-taken-by-the-system-16-nov.md` |
| SR24 | `design/_work/stage-review-VW-24-treatment.md` (in git, commit c8a8e3b) |

Who found it: **SK**; **critic** (a reviewer who had not written the code, run after a build); **operator** (seen on a film by the team); **builder** (found while building or reading).

---

## Theme 1. What the operator is shown

| # | Mistake or learning | Found by, and where | How it was fixed | In References? | Proof and effect there |
|---|---|---|---|---|---|
| 1 | A line said what would be shown, not why. | SK, on VW-24. design/202 section 1 | Each shot carries two reasons, shown on the line. The plan page shows them again under each gap (PF:220). | **YES** | FACT: a reference line is a title, one fixed sentence, pictures and buttons (PF:482-485). It does not say why the thing is in the film or which shots use it. RD: 33 of 49 lines read the same, word for word. Effect: the operator cannot judge "Leave it out", or which angle matters. |
| 2 | The operator never saw the world of the film whole. | SK. REQ point 1 | "The world of this film" is the first block of the plan page (PF:197-202). | **YES** | FACT: the references page has no world block and shows no description of any thing (PF:534-581). Effect: the operator judges a picture of "the neighbour" without the words that say who she is. |
| 3 | The same label was repeated on every row; nothing was grouped. | SK, 16 Nov. Commit cd1fde1 (plugin 0.89.2) | One heading per kind, each group folding (DH:323-335). | **YES** | FACT: RD is 49 flat lines: people, materials, objects, places and techniques with no heading. The page code has no grouping for these lines. Effect: a long scroll; easy to lose one's place; nothing can be folded away once read. |
| 4 | A stored record was printed field by field, nine times ("serious UI UX issue"). | SK and the operator, VW-24. design/209 | Plain words; the working notes are not shown. | **NO** | FACT: the page lines are plain sentences (PF:475-480, 509-519). No raw record is printed. The chat way back was not read line by line. |
| 5 | The same fact was asked more than once (37 size lines, 7 of them in more than one drawing). | SK, VW-24. design/209 | Each size is asked once; later lines say "already confirmed". | **YES** | FACT (EV): the same thing is pictured in several paid sets. The pan is in three: the pan, wet concrete "in a pan", and "pouring concrete from a pan". The brush, the oil and the tin are spread over four. The yard of materials lists six things that each have a set of their own. Effect: about ₹35 for each, a separate judgement for each, and two sets may show the same tool differently. |
| 6 | The Direction was asked as "Do you accept this line?", so it was not seen as a step. | SK, VW-23 and VW-24. design/202 section 1 | Asked by name, with what it is and what a yes means. | **NO** | FACT: each line names its thing and its kind, asks one question, and says what a yes does and what it costs (PF:475-482). |
| 7 | The operator's plain warning lines were not on the plan page. | critic, after design/207. design/207 "The critic's review" | "Read before you answer" above each gap (PF:222; DH:368). | **YES** | FACT: a reference line cannot carry such a line (no `warnings` at PF:482 or PF:508). Three would matter: "a real, named person with no photo yet", "the client's own thing", "its size is not known". |
| 8 | An earlier text was shown cut at 400 characters. | SK, on the page. design/205 point 1 | Shown whole. | **NO** | FACT: nothing on a reference line is cut. Only the first four footage pictures of a thing are shown (PF:474), and VW-24 has at most two. |
| 9 | "Changed since you last saw it" confused the operator: it showed raw data and compared with a draft they had never seen. A change they ask for must come back marked, with before and after. | SK, VW-24 redo. design/202 section 3.3 and review fault 2; commit 2a23def | "Changed as you asked", against what the operator last saw; the list folded. | **YES** | FACT: the opposite fault. A set made again after "Correct it" comes back with no mark, without the operator's words and without the earlier set (PF:508-513). Effect: with several corrected sets in one visit, the operator must remember what they asked of each. |
| 10 | Notes that matter to the decision were hidden, while notes that do not were shown. | builder. design/209 ("the assistant's notes on what it tried are not shown") | The working notes were taken off the page. | **YES** | FACT: each set comes back with the picture model's own notes: the method it chose, what the web photographs contradicted in our request, and its sources (VS:1963-1964; kept on the picture, VS:1203). The new page shows none of them (PF:489-531). The older server page showed them folded (design/151 section 12). Effect: the operator is not told when the model set aside something the plan asked for. |
| 11 | A recorded line lost its content; the operator could not read back what they approved. | SK and builder. design/209 ("An approved line stays on the page with its content, folded") | Approved drawings and materials stay, folded. | **YES** | FACT: an approved set keeps its pictures (PF:523-530). But a thing settled at step 1 from its footage picture is left out of the sets page altogether (PF:501). Effect: after step 1 the operator cannot look back at the footage pictures they approved. |

## Theme 2. Who decides

| # | Mistake or learning | Found by, and where | How it was fixed | In References? | Proof and effect there |
|---|---|---|---|---|---|
| 12 | The assistant took decisions of taste alone. On VW-24 it rewrote the treatment to clear 14 warnings before the operator saw anything. | builder, for SK. SYS | Proposed, not built: the first draft is shown; a "Decided for you" list. | **YES** | FACT: the assistant alone decides which things get a footage picture, which second of the clip, and what each paid set is asked to show. The operator never sees the text a set is made from (PF:482 holds no prompt). Yesterday's review: 41 of 50 things went to a paid set by the assistant's choice. Effect: the operator says yes to 41 paid sets without seeing what was ordered. |
| 13 | The operator was asked things that need no answer from them (a footage reuse, D2). | SK. REQ point 9 | The question was removed; the reason is kept on record. | **YES** | FACT: SK decided that every named person gets a sheet (D3). The page still asks, for each of VW-24's 7 people, "Have a reference set made (paid)?" (RD lines 1 to 7; CF:397). FACT: a set that cannot be made yet for a cause only the assistant can settle (a size not measured) is shown to the operator with "Make it" and "Leave it out" (CF:446; PF:514-519). |
| 14 | Faults the writer could prevent reached the operator (the three framing warnings, D7). | SK. REQ point 11 | Written as instructions; the warnings go to the assistant only. | **YES** | Yesterday's review: nobody looks at a footage picture before the operator; the pan and the stone heap reached SK. New, FACT: the same holds for a set. Its check lines are written (VS:1985-1992) but their result is not on the page line (PF:508-513), so the operator is the first reader of every fault. |
| 15 | The builder assumed a limit that was not there ("the guide cannot move a thing"). SK corrected it: Blender can move anything. | SK. REQ, decision D5 | A thing travels on a timed path. | **YES** | FACT: "three pictures per thing: the whole, a three-quarter view, a close-up" is the builder's own assumption. design/151 section 13 says so: "Assumption: three per thing (SK took the count question off the table)". It was never checked against what a film needs. |
| 16 | The builder took decisions by default and they went live. | builder, stated in the notes. design/202 ("three departures"), design/210 ("Decisions taken by default") | Each was written down for SK. | **YES** | FACT: three defaults stand in the References step without SK's word: a click on a priced button plus "done" is the spend; no "accept everything"; and footage pictures, people included, are stored on the claude.ai page ("One thing I take as decided by this request", `reference-screens-on-the-page-plan.md`). |

## Theme 3. Whether the sentences are true

| # | Mistake or learning | Found by, and where | How it was fixed | In References? | Proof and effect there |
|---|---|---|---|---|---|
| 17 | Texts said what the program does not do: a warning that never fires; a refusal placed at the wrong step. | SK's review, then builder. REQ "Three corrections to the guide" | The dead warning was deleted; the guide corrected. | **YES** | Yesterday's review: "Your footage has no picture of it" means only that none was taken. New, all FACT: (a) "Three pictures of the same thing" is fixed text (PF:509), but a set may come back with fewer (design/151 section 13 point 3). (b) The comment box says "where a set is corrected, it says what to correct" (DH:400); at step 1 the comment does nothing (item 27). (c) In the chat, a person's footage question reads "Use these pictures to make the reference set?" (CF:391-392); without a recorded permission the pictures are not used. (d) A set with drawings is told "the drawings were made from this thing's real sizes" (VS:1967) even when sizes were assumed. |
| 18 | A figure was guessed where it should have been marked "not known". | critic. design/202 review fault 1 | Counted shot by shot; what cannot be told is kept apart, never guessed. | **YES** | FACT (EV): all 24 sizes of VW-24's things are `unknown` in the plan. The set prompts carry sizes all the same, in the assistant's words: "about a hand wide", "knee-high", "five across and four deep", "a finger deep". Nobody approved them. FACT: when a thing has several footage pictures, the first is taken as its reference without a choice (VS:3218). |
| 19 | The log said nothing of what a draft returned or what the page recorded. | builder. SR24, points C3, C5, F15 | Each page answer is a log line with the operator's words (design/205). | **NO** | FACT: every answer of the reference round is logged (PF:828, 872), and the record call says what was recorded, kept, stale and refused (PF:918). |

## Theme 4. Questions asked again, answers lost

| # | Mistake or learning | Found by, and where | How it was fixed | In References? | Proof and effect there |
|---|---|---|---|---|---|
| 20 | One changed word made every gap be asked again; an answer went back to "to accept" without notice. | SK, VW-22 and VW-21. design/191 | Two fingerprints; one question; "what changed". | **YES** | FACT: a kept step-1 answer is dropped without a word when that thing's footage pictures change (CF:312-314). FACT: a set is marked "made before a change" only for a changed material spec or photo (VS:3490-3509); a person re-described in the plan keeps the old sheet, unmarked. A thing the plan no longer names drops out silently (CF:380). |
| 21 | The operator was sent several rounds of answers. SK: "do not send several rounds back to the operator." | SK. design/206, first point | One visit and one "done" for the whole plan. | **YES** | By design, each "No" or "Correct it" is one more round. INFERENCE: because the plan's views and descriptions do not reach the set (file C, rows 19 to 21), more sets come back wrong, so more rounds. A long list is also cut, with the rest shown after the next "done" (PF:549-561). |
| 22 | The check told one fault at a time, so a plan needed four rounds. | SK. REQ point 2 | One fault per shot and the plan-wide faults in one answer. | **YES** | FACT: the posting of the round stops at the first faulty row (VS:3178-3196). People who read alike are refused one pair at a time (VS:2015), though the plan check now names all pairs. The making of the sets does collect every refusal (VS:3289-3308). Effect: slower start; not seen by the operator. |
| 23 | A yes was recorded although it rested on something corrected in the same visit. | critic. design/209, critical fault 2 | Corrections are recorded first; such a yes is asked again. | **NOT CHECKED** | A like case exists: a set of a technique approved in the same visit in which the set of its tool is rejected (item 5). I did not trace what the shots then use. |
| 24 | An answer given to an older text stayed shown after the text changed. | builder, on the trial page. design/202, trial page fault 1 | Each answer names its item; a stale one is ignored. | **NO** | FACT: a set made again has a new id in its item (CF:442), and step 1 is guarded by the stamp of the footage pictures (CF:314). |
| 25 | A yes the server refused was left with the operator, though the fault was the assistant's to fix. | critic. design/209, critical fault 3 | The assistant is told it is its own to fix. | **YES** | FACT: for any refusal on a reference line the assistant is told only "tell the operator and give them the link again" (PF:413). See also item 13, second fact. |
| 26 | A step did not end after its last answer. | critic. design/210, review fix 1 | The round is completed by the server's own test. | **YES** | FACT, written in design/210 itself: "a round element the plan no longer names still holds step 2 open". Not fixed. |
| 27 | A paid remake ignored the words the operator typed. | critic. design/210, review fix 2 | "No" with words is made again with them. | **YES** | FACT: fixed at step 2 only. A comment typed at step 1 is logged and goes no further (CF:399-405; design/210 "Not covered"). Effect: "the handle is red", typed at step 1, is not in the set; a second set is paid for. |
| 28 | After a page step, the "what next" sentences still sent the assistant to the chat (13 faults). | builder, after the deploy. Commit 9c9bb0c | One function for "what next"; live as 0.107.1. | **NO** | FACT: the sentences after each reference step now name the page or the wait (PF:400-413, 901-917). |

## Theme 5. Cost

| # | Mistake or learning | Found by, and where | How it was fixed | In References? | Proof and effect there |
|---|---|---|---|---|---|
| 29 | One cost limit for every film, and no cost shown on the plan page. | SK. REQ point 16b | A limit by length; the estimate against it on the plan page, the reference sets named (design/209). | **YES** | FACT: the references page shows the sets, the limit and the spend (PF:570), but not what the plan's shots still need. The close of step 1 tests only that the sets fit (PF:598). RD: ₹1,345 spent, ₹1,450 for 41 sets, limit ₹3,754. ₹959 is left for every still and take. INFERENCE: the film meets its limit later; VW-24's shot estimate was not in the files I read. |
| 30 | A fault was found late, after money was spent (a lorry accepted at the plan and thrown out at step 7). Free checks come before paid steps. | SK's review; design/200 | The plan check now warns; drawings are approved before any paid picture. | **YES** | FACT: nothing free stands between the assistant's 49 texts and 41 paid sets. The operator first sees how a set was framed after it is paid for. The server tests only that a text is not empty and has no "how to" words (VS:2029-2032, 3191-3192). |
| 31 | The same thing must not be charged twice ("Already made, press Play"). | SK. design/208, point A6 | An earlier try of the same spelling is replayed, not charged. | **YES** | FACT: "No" or "None of these" with no words makes the set again from the very same prompt (VS:3375-3381 adds words only when given). Effect: ₹35 for a second throw of the same dice. See also item 5. |
| 32 | A storage hiccup could rewrite a running film's cost limit. | critic. design/207, critical fault 1 | The limit is decided from the session; a set figure is left alone. | **NO** | FACT: the round only reads the limit (VS:730; PF:420-423). |
| 33 | The plan's estimate left out the reference sets. | builder. design/209 | "Up to ₹Y for N reference sets." | **NO** | FACT: the count on the references page comes from the lines themselves (PF:486), so it is exact there. |

## Theme 6. Real people

| # | Mistake or learning | Found by, and where | How it was fixed | In References? | Proof and effect there |
|---|---|---|---|---|---|
| 34 | A real person's picture could reach the picture AI with no recorded permission, by a side door. | critic. design/207, critical fault 4 | One test for every door (VS:2527). | **NO** | FACT: a person's set takes a photo only with the permission (VS:3744, 2507-2515); the page asks for the permission words first (PF:619; DH:303); a set made from a photo cannot be approved once the permission is gone (VS:3350). |
| 35 | A photo given after the reference step was complete led nowhere. | critic. design/207 | A complete round opens again for that person (VS:3520). | **NO** | FACT: read at VS:3512-3538. |
| 36 | "A real, named person is shown as a made-up stand-in" was told in one place only. | builder. design/207 "known limits" | Told on the plan page, when the assistant marked the person. | **YES** | FACT: the references page does not repeat it. Every person gets the same sentence (PF:476). This is the page where the operator can add the photo. |
| 37 | Client material, people included, is stored on claude.ai under the operator's account. The question was raised and not answered. | builder. design/204 section 8; `reference-steps-on-the-artifact-page-analysis.md`, question 1 | Not settled: taken as decided by the request. | **YES** | FACT: every footage picture on a reference line is sent to the page's store, a person's too (PF:474-483). The permission that is recorded is for making AI pictures, not for this. VW-24's 7 people have no footage picture, so it has not happened on this film. |

## Theme 7. Rules for every kind of film

| # | Mistake or learning | Found by, and where | How it was fixed | In References? | Proof and effect there |
|---|---|---|---|---|---|
| 38 | Building-site wording stood in general rules and messages. | SK. REQ point 14; design/202 | Nine instruction sentences and six messages reworded. | **YES** | FACT: every thing's set is told "on one real site" (VS:1958) and "on the same site" (VS:1960); its check says "could not stand on a real site" (VS:1987). Every person's set asks for "a working pose of their trade" (VS:1973, 1977). On VW-24 that is asked of the daughter, the mother and the neighbour. |
| 39 | A fixed count stood where a test was meant ("three to five beats"; "a still always moves"). | SK. design/205 points 2 and 3 | The sentence gives the test and leaves the count open. | **YES** | FACT: three pictures of fixed kinds for every thing (VS:1976-1984). Water, a curtain and a street each get "the whole", "a three-quarter view" and "a close-up of the part that shows how it is made or used". |
| 40 | One rule was applied to kinds it does not fit: water was asked for its unit size. SK: "the question was wrong, not the idea." | SK. REQ point 5 | Unit sizes only for a material laid in units. | **YES** | FACT: one set of rules for every kind that is not a person. A place is told "the subject fills the frame; the setting is only a soft hint" (VS:1986) and "the surroundings soft" (VS:1966); for a place, the setting is the subject. A technique is told "no person, no hands" (VS:1988); see item 44. |
| 41 | A word match fired on the wrong thing ("big savings" as a size claim; "a circle of bricks" as a circling camera). | SK's review. REQ points 6 and 8 | The circling test was removed; the size test stays a word match. | **YES** | Yesterday's review: footage is matched to things by shared words ("clean water" matched concrete blocks). New, FACT: "people who read alike" is a word match too (VS:1994-2003). The word "white" anywhere in a description counts as grey hair, and any number from 20 to 29 counts as an age in the twenties. The refusal of "how" in a subject block is three fixed phrases (VS:1972). |
| 42 | A rule written for an older model was still in force ("at most four people, nobody crossing"). | builder. SR24, B1 and F14 | Refusals became warnings (design/207). | **NOT CHECKED** | The fixed opening of a thing's set and the "one picture per turn" way were written on 4 Nov for one model (design/151 section 13). Whether today's model still needs them was not tested. |
| 43 | A default that suits documentaries stood in the general text ("muted and true to life"). | builder. SR24, B6 | Not changed yet. | **YES** | FACT: every thing's set is told "natural daylight as in that place, natural colours, no filters, no stylisation, no illustration" (VS:1965), whatever the film's category or look. The category is not in the prompt at all, although design/151 section 3.3 says the server adds it. INFERENCE: a night film, a studio product film or a stylised film gets daylight photographs as its references. |

## Theme 8. The instructions against the server

| # | Mistake or learning | Found by, and where | How it was fixed | In References? | Proof and effect there |
|---|---|---|---|---|---|
| 44 | The instructions told the assistant one thing and the server refused it ("not to scale"; "never on a page"). | critic, design/207 fault 3; SK, REQ point 14 | The sentences were brought in line. | **YES** | FACT: three texts disagree. The plan tells the assistant to file each way of working as a "technique" (VC:44). INS says a thing's text says "nobody in it, never how the work is done". The set's check demands "no person, no hands" (VS:1988). VW-24 has 7 techniques; two of their texts say "held in both hands" (EV: T_POUR, T_SCREED). Effect: either the set breaks its own check, or it shows a tool lying still, which is not the technique. |
| 45 | A helper's brief was left behind when the rules changed, and a shot was never drawn. | critic. design/207, critical fault 2 | The brief was updated. | **YES** | FACT: INS was updated for people (own likeness, a sheet for each, none for an animal). It was not updated for the plan's new content: it names no views, no world rules, no signs of use, no sizes. It still says "a frame of each". No helper exists for the references (the folder `plugin/agents` has none); the assistant writes the round alone. |
| 46 | Words that must be exact were retyped by the assistant, and the server refused the copy. Learning: the server places what must be exact. | SK's review. REQ point 14, "The Direction copied by hand" | The server places the Direction (VS:297-311). | **YES** | FACT: a thing's description, approved on the plan page, is retyped by the assistant into the round file and sent as written (VS:3287). EV: the plan asks for the pan "side" and "tipped, pouring"; the retyped text asks for "from the side and from above". |
| 47 | A behaviour lived only in an instruction. Rule: one flow, two front ends; the server holds it. | SK, 20 Oct. Repo `CLAUDE.md` | A standing rule. | **YES** | Yesterday's review: "the sharpest frame, the subject large and evenly lit" is only a sentence in INS. New, FACT: so is "what the picture must represent, its frame, nobody in it". The server does not hold either. |
| 48 | The writer had no checklist for the part it writes alone, and that part caused the faults. | SK's review. REQ point 2 | A checklist for the main assistant; shot sizes added to the helper's. | **YES** | FACT: the assistant writes 49 texts alone. There is no checklist. The server's only tests are "not empty" and three phrases (VS:2029-2032). |
| 49 | An outside source was followed over the film's own choice (the script's notes: the kiln). | SK, VW-24. design/202 | The script's notes are no longer handed over. | **YES** | FACT: a thing's set is told "if anything I ask for contradicts what the real photographs show, the photographs win" (VS:1955). Only approved drawings stand above the photographs (VS:1967). So what the operator approved in words on the plan page can be set aside by web photographs, and the note that says so is not shown (item 10). |

## Theme 9. How the work is built and reviewed

| # | Mistake or learning | Found by, and where | How it was fixed | In References? | Proof and effect there |
|---|---|---|---|---|---|
| 50 | Learning: after a build by helpers working apart, run three reviews before asking to deploy: instructions against the server, the requirement against what was built, and defects. | SK asked for it; 22 faults found. design/207; memory note `vw2-design207-visuals-rules` | Done for design/207. | **YES** | FACT: design/210 records one critic limited to critical faults, and a wording review after the deploy. No review of "the plan's content against what the round uses" is recorded. Files C and D are that review, done after the release. |
| 51 | Nothing was run on a real film; causes were read from the code, not from the run's log. | builder, stated. REQ "Not covered"; design/207 "Not verified" | Said in each note. | **YES** | FACT: design/210 "Not verified": the page with a real film; the upload; the time of a first visit. VW-24's sets were not yet made when EV was taken. No set made after design/207 has been looked at by anyone. |
| 52 | A film in progress at a release meets the new rules half way. | builder. design/202 "risks"; design/207 "Left open on purpose" | Accepted for test films. | **NOT CHECKED** | VW-24's round was posted under the new server. Whether any of its rows were written under older instructions was not checked. |
| 53 | Learning: every change says what happens to the older way. | SK, 30 Oct. Memory note `feedback-old-ways-rule` | Rows 72 to 102 in design/35. | **YES** | FACT: the older reference way (search, picks, one sheet) was retired for new films on 4 Nov. With it went the only reader of the plan's `required_views` (VS:2166, 2179, 2187 are all in the older way). The plan still demands the field; nothing new reads it. INFERENCE: this is how the views were lost. |
| 54 | Learning: the load on the assistant. The card had to be retyped character for character. | SK and builder. design/202 section 6 | The page takes data; the assistant sends a file. | **NOT CHECKED** | The round is sent as a file. But the assistant must still type 49 texts, and send the pictures in batches of calls (design/210). Time and permission prompts on an operator's machine are not known. |
| 55 | Learning: a flag warns the user; it does not block. | SK, 14 Nov. design/195 | Applied to the treatment's missing reasons. | **NO** | FACT: a set's check lines never block an approval (design/200 section 4, step 8). The two refusals in the round (people who read alike; a size to measure first) are SK's own rulings of 4 Nov (design/151, part 2 and Q6). |
| 56 | The tool's own rewrite was taken for a hand edit, and a correction could be dropped. | operator, VW-24. design/209 section 2 | A fingerprint, not a file time; a merge. | **NO** | FACT: a round posted again after step 1 merges and never wipes the sets (VS:3223-3261; fixed on 5 Nov). |

---

## Counts

| In References? | Items | How many |
|---|---|---|
| YES | 1, 2, 3, 5, 7, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 20, 21, 22, 25, 26, 27, 29, 30, 31, 36, 37, 38, 39, 40, 41, 43, 44, 45, 46, 47, 48, 49, 50, 51, 53 | 40 |
| NO | 4, 6, 8, 19, 24, 28, 32, 33, 34, 35, 55, 56 | 12 |
| NOT CHECKED | 23, 42, 52, 54 | 4 |

## The ten that matter most

1. **Item 12.** The operator pays for 41 sets without seeing what each was asked to show.
2. **Item 46.** A thing's approved description is retyped by the assistant; the pan's views were changed in the retyping.
3. **Item 44.** A technique must show hands at work, and its own check forbids hands.
4. **Item 5.** The same thing is paid for and judged in several sets.
5. **Item 18.** Sizes nobody approved go into the paid pictures, while the plan marks all 24 sizes "unknown".
6. **Items 1, 2, 3.** The page: no reason, no description, no grouping; 49 lines.
7. **Items 9 and 10.** A set made again shows neither the operator's words nor the model's own notes on what it changed.
8. **Item 29.** The references can take the money the shots need; the page shows only part of the sum.
9. **Items 38, 39, 40.** Building-site words, a fixed three pictures, and one rule for every kind of thing.
10. **Item 49.** Web photographs win over what the operator approved in words, and the page does not say when they did.

## What this draft still needs

- A look at real sets. VW-24's were not made when the evidence was taken, so every effect on a picture is an inference.
- The four NOT CHECKED items.
- SK's word on the three defaults of item 16 and on the storage question of item 37.
- The chat way back was read only where it shares code with the page.
