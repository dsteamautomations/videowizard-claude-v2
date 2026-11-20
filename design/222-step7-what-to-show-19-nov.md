# Step 7, AI video: what to show and what to ask

19 Nov 2026. A study and a trial only.
Note of the same evening: SK answered the twelve decisions. Three change what this file describes: "Make another" is on the page (D4), Claude checks each take from frames in place of Gemini (D5), a recorded answer is shown without buttons (D8). The current statement is `222-step7-build-requirements-19-nov.md`, revision 2, sections 7 to 10.
 Nothing in the application, the database or the repository was changed.
Read at commit e86344d (live server 0.117.0 plus a hotfix).
Trial page (private): see the link in `222-step7-build-requirements-19-nov.md`, section 1.

## 1. Two findings before anything else

1. **No film has made an AI video take the new way inside the application.** The new way (a guide drawn by Blender, a still, the take as an edit of the guide; live since 12 Nov) has no take in the database. VW-21 has one shot with a guide (10 guide jobs, no still, no take). VW-22, VW-23 and VW-24 have none. The only films with takes are VW-6 (14 takes, 22 Oct) and VW-12 (17 takes on 16 shots, 31 Oct and 1 Nov), both made the older way (a start picture and words, Gemini Omni 1.1).
   So the trial uses **VW-12**: it has the most takes, one shot made twice (the first take rejected by SK, then made again), and a real check of every take. What the trial cannot show with real data: the eight-line scorecard of a guide take, a clip the server set aside ("the guide came back unedited"), the still on the guide's red outlines.
2. **The older "start image" question can no longer be asked on a new film.** `visuals_stage.waiting` still lists a start picture, or a start and end picture, of an AI video shot as a "picture to answer" (line 2762). But `guide.older_start_picture_retired` refuses every such picture for an AI video shot, and a take prompt that names an end picture is refused (`guide.NEVER`). The branch is dead for films started after 12 Nov. A shot with a start and end image therefore does not exist in step 7 today.

## 2. Who does what

- **Claude helper (on the laptop)** writes the scene description of plain boxes for each shot, and later the words of the still and of the take. Free.
- **Server, no AI** refuses a scene that cannot work, draws the shot (through the camera and from above), renders the check frames and the guide video in Blender, makes the overlay (the still under the guide's red outlines), and runs three measured checks on a returned clip. Free.
- **A second, fresh Claude helper** looks at the guide's check frames and passes or fails them. After two failed rounds the assistant shows the operator what is still open.
- **GPT image** makes the still from the guide's first frame. Paid.
- **Gemini Omni 1.2** makes the take: an edit of the guide video, with the still as its first frame. Paid, by the second.
- **Gemini 3.8 Flash** watches the finished take against fixed lines. It marks problems; it never blocks.
- **Operator** approves the shot's drawing, approves the still on the overlay, gives the word to make the take, and selects or rejects the take. Approval of the film belongs to SK.

## 3. Everything the operator decides or sees in step 7 today, in order

All of it is in the chat today, one item at a time. "Early (chat)" and "Full review (page)" follow SK's rule of 19 Nov: what arrives one by one, and what must be decided before money is spent, is a chat card; the finished takes are judged on the page, all together, once all are made.

| # | The thing | Who makes it | Who checks it | What the operator does today | Where it belongs | Facts needed to answer, nothing more |
|---|---|---|---|---|---|---|
| 1 | The layout drawing of the shot (two drawings: through the camera, from above) | Server, from the helper's scene. Free. | Server (refusals before it is drawn) | Yes, or Correct it with words (`chat_flow._drawing_items`, "Step 7, AI video: the layout drawing of the shot") | **Early (chat card).** It comes shot by shot and the still is not made before the Yes. | The two drawings; how to read a person (chest, back, working arm); what was changed from the plan. |
| 2 | The guide's check frames | Server (Blender). Free. | A fresh Claude helper | Nothing, unless two rounds fail: then the assistant says what is still open | **Not shown.** The operator is not asked what needs no answer. After two failed rounds: one chat message. | (none) |
| 3 | The still on the overlay | GPT image. Paid. | Nobody but the operator. No model looks at it. | Approve or Reject with words (`_guide_items`, "Step 7, AI video: the still") | **Early (chat card)**, SK 19 Nov: the still decides what the take will be. | The overlay and the still; one sentence: does every person and thing sit on the red outlines. |
| 4 | The word to make the take ("Shoot") | The assistant writes the take's words; the server refuses words that failed in tests | Server | Shoot, or Not yet with words (`_guide_items`, "Step 7, AI video: the take"). The card says the length and the cost. | **Early (chat card)**, SK 19 Nov: a take costs money. | The guide video, the overlay, the length, the warnings that matter before paying. Whether the cost is said: SK's decision. |
| 5 | A clip that came back unusable (the guide unedited, the wrong length, or the first frame off the still) | Gemini Omni | Server, three measured checks (`guide_worker.take_checks`, `blocked`) | "Send the same request once more?" with its cost (`_guide_items`, `again`) | **Early (chat card).** It is a question about money, and nothing is there to judge. | Why it cannot be used, in one line. |
| 6 | The take, to select or reject | Gemini Omni 1.2. Paid. | Gemini 3.8 Flash, and the server's measured lines (the scorecard) | Select or Reject (`_waiting_items`, kind "take to select"). Reject needs words. Select needs a reason when a line failed, when the take was not read, or when it is shorter than its place. | **Full review (page)**, all takes together when all are made. | The take playing; where it sits in the film and the words under it; what comes before and after it; the check as one line with its faults in full. |
| 7 | Why a rejected take was wrong (the still, the guide, the words, or the model's limit) | The assistant, with the operator's words | Server (a wording cause is refused when the first frame failed) | Nothing on a screen: the assistant records it (`vw guide cause`) before another take may be paid for | **Chat.** It follows a rejection made on the page and leads to a new Shoot card (item 4). | The operator's rejection words. |
| 8 | After two rejected takes from one camera: cut the shot, another angle, or leave it out | The assistant proposes | Server (refuses a third try) | Chooses, in the chat | **Chat.** It changes the plan. | The three ways, plainly. |
| 9 | "Record this gap into the film?" | Server | Server | Record it, or Not yet (`_record_items`) | **Chat**, unchanged. It is after step 7 and covers every kind of shot. | (unchanged) |

Not operator's things, and not shown: the scene description, the guide video's render, the generator (Gemini Omni only; no choice is offered), the take's request file.

## 4. The take on the page (item 6), in detail

### What is in view (redone on 19 Nov evening, after SK found the first trial too cluttered)
The current statement is section 1a of `222-step7-build-requirements-19-nov.md`. In short: in view are only the shot's name and the words under it, the take large, the check as one short line ("Check passed", or the first fault), the buttons Select, Make another, Reject, and two links. Two takes are two tabs. The film order ("See it in the film") and everything else ("Details") open over the page on one click. The left list is a name and a dot. The check is Claude's, from frames, with one line measured by the server ("one continuous shot").

What follows in this section is the first trial's layout, kept for the record.

### What was in view in the first trial
- **Left list:** the shots whose take needs an answer, numbered, in film order, each with its film time and "1 take" or "2 takes". Under it **"Answered earlier"**: every take already answered, with its decision; a click opens it again with the take, the check and the recorded answer (SK asked twice that recorded answers stay visible). Then "Could not be made", when there is one.
- **Middle, left:** the take playing, large, with no sound, on a loop. Under it one line: how long the take is and how long its place in the film is. Under that, **the film order**: what comes before, this take, what comes after. A click on "before" or "after" puts it beside the take, only to compare; it has no answer buttons.
- **Middle, right:** where the shot sits in the film and the words under it; the check as one coloured line; the question; the buttons. Details are folded below.
- **Bottom bar:** one count, "N of M answered".
- **End card:** what will happen for each take, before the operator says done in the chat.

### The answers
- **Select: use it in the film.** One click when the check found nothing wrong. When a line of the check failed, or the take was not checked, or the take is shorter than its place: the page asks once, "Why is it right for the film all the same?", and the reason is kept with the film (the server requires it today, `select_take`).
- **Reject**, with the operator's words (the server requires them). The failed lines of the check are put in the box to edit. What happens next is said on the button's line: "Claude says what caused it and asks you in the chat before another take is made." The money decision stays in the chat (item 4).

### Where a second take, or a rejected take, sits
- Today the server makes a second take only after the first is rejected (`guide.shoot` refuses while a take waits for its answer). So two takes of one shot are always: an earlier one, rejected with the operator's words, and the new one.
- On the page the shot is **one line**, marked "2 takes". The new take is the one to answer. The rejected take is one click away in the same row as the film order ("Take 1, rejected") and opens **beside** the new take, with the words it was rejected with; "Play both from the start" starts them together.
- The trial also offers **"Use take 1 after all"**, with a reason: the remake is sometimes worse than what was rejected, and both are paid for. This is a decision for SK (the server allows it today through `select_take` with notes).
- A take answered in an earlier visit is under "Answered earlier" and can be opened again. Changing a recorded answer there is a decision for SK (the trial shows it, with its buttons, to make the question concrete).

### What the check of a take says, and how it is shown
- **Today, for a guide take**, the record (`session.take_checks[job]`) holds: three measured lines (real footage, as long as the guide, the first frame matches the still), the reading of Gemini 3.8 Flash on five lines (people, the action, objects, bodies and contact, the place and the light), and a **scorecard** of eight lines, each Pass, Fail or Not sure, with "one thing to watch and the second it happens". The eighth line, "the join", is always "Not sure: judged in the film, between its neighbours; no tool sees it".
- **In the chat today** it is shown as up to eight short lines ("people: Pass", "the action: Fail (…)") and a "Look at: … at 3 s" line.
- **On the page** it is one coloured line, as on step 6:
  - green: "The check found nothing wrong."
  - amber: "The check found 2 problems:" with the first problem in full and "See all 2"; each problem has "Go to 5 s", which moves the player to the second the problem was seen;
  - grey: "Not checked: … Judge it by eye." when the reading did not run.
  - Under it, who checked: "Gemini 3.8 Flash watched the take against its list of 13 lines."
  - The lines it passed are folded under Details. "Not sure" lines are not faults: they are listed with the passed lines, marked "not sure". "The join" is not a line of the check at all: the film order under the player is how the operator judges the join.
- **In the trial** the check is VW-12's real one: Gemini 3.8 Flash on 10 to 14 lines of that week (planned end, tool kept, person kept, appear or vanish, …). 9 of the 17 takes have at least one failed line. SK selected all 16 shots on 1 Nov; the list of failed lines was not in front of him then.

### What is deliberately not in view
- The cost of the take (pending SK's decision; see the requirements, decision D1).
- The start picture or still, the take's words, the model: folded under Details.
- The frame sheet (4 frames a second) and the "first frame and still" pair the server makes today: not on the page. The player shows the take; "Go to 5 s" does what the sheet was for. The pair is only useful when the first-frame line fails, and then the clip is set aside before it is a take.

## 5. The state before all takes are made

The page is closed, as step 6 is: one card, "Nothing to answer yet", with the line of counts ("AI video: 11 made and checked, 4 being made, 1 being redone.") and one sentence: the page opens when every take is made; until then the stills and the words to make the takes are asked in the chat, one card each. The same line of counts is what the assistant says in the chat.

## 6. Differences between the code and what the operator should see (found, not fixed)

1. `visuals_stage.waiting` hands out a ready AI video take at once, one by one, while other takes are still being made. Only drawn graphics are held for the page (`gate`, line 2813).
2. An AI video shot usually has **no title** in the plan (13 of the 16 in VW-12): the chat item is headed with its id ("BEAT_04-B1_sh3: is this take right for the film?"). The trial names such a shot by its gap's title and its number in the gap.
3. "Your footage before and after" (`pictures.footage`) is a footage picture of the clip before and after the **gap**, the same for every shot of the gap, and only where the session holds an approved footage picture of that clip (VW-12: 2 clips). For a take, what matters is what sits directly before and after the **shot**: often another made shot of the same gap.
4. The chat shows the scorecard's "Not sure" lines beside the failed ones with the same weight; "the join" is always among them.
5. The rejection of a take and its cause are two separate steps (`review_take`, then `vw guide cause`); between them nothing tells the operator what happens.
6. `waiting` line 2762 (start image, start and end) is dead for new films (finding 2 above).
7. The older server page (`templates/visuals.html`) still carries takes and the guide view in its data (`visuals_stage.py:1242`); the operator's flow no longer goes there.

## 7. Patterns taken from Mobbin

Searched 19 Nov (web screens): a video review screen with approve and request changes; two versions of a video side by side; AI video results.

1. **One item, the media large, the decision in a side panel, arrows to the next** ([ClassDojo, "Needs review"](https://mobbin.com/screens/8767e826-c7af-478c-a797-8a02b71f4006), [Pitch, "Review recording"](https://mobbin.com/screens/731aa600-a88e-42ad-8fb1-d2d416297f35)).
   Taken because it is already the frame of steps 5 and 6: the take large on the left, "Approve item?" with two buttons on the right, one count ("2 / 29"). Nothing new to learn for the operator.
2. **Two versions side by side under one question** ([Grok, "Which video do you prefer to keep?"](https://mobbin.com/screens/6b38ce14-aed3-41a1-92a0-3e596b671be5), [Frame.io, compare view](https://mobbin.com/screens/47e3ef66-fad0-4e83-95b6-5f4653967a80)).
   Taken for a shot with a rejected take and its remake: both play at the same size, started together, each named under its picture. Not taken: Frame.io's long list of file facts beside it.
3. **A rejection that starts from the known faults** ([Runway, "What can we do better?"](https://mobbin.com/screens/aa016d55-74f1-47fb-8918-2ccb33a6c9b3)).
   Taken in this form: the words box of Reject opens with the check's failed lines already in it, to edit or replace. Not taken: a fixed list of tick boxes; the operator's own words are what the next take is written from.
4. **A comment tied to a second of the video** ([ClickUp Clips](https://mobbin.com/screens/bd3d21a9-6275-4865-957b-47af724b5c82), [Dialpad](https://mobbin.com/screens/fe2d0ad3-499b-4fa3-9792-4b655aee7490)).
   Taken as "Go to 5 s" on each fault of the check: the check already records the second it decided on; the link moves the player there. It replaces the frame sheet.

Looked at and not taken: a grid of all results at once (Leonardo, Luma, Magnific): good for picking among many variations of one prompt, but here each shot has one take to judge against its place in the film.
