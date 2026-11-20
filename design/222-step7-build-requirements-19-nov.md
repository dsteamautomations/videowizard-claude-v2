# Step 7 (AI video) on the decisions page: requirements for SK's approval

Revision 3, 19 Nov 2026 (evening): the frames test is done and SK kept Claude's check ("the claude checks can be retained"); SK found the trial page too cluttered and the trial is redone with less in view (section 1a). Before that, revision 2: revised for SK's answers to the twelve decisions (relayed from the builder thread; a relay of his click answers, not yet his word to build).
Nothing is built. No code is written before SK approves this list.
Read at commit e86344d. The study is in `222-step7-what-to-show-19-nov.md` (same folder).

**What changed in revision 2:** section 7 (the answers), new section 8 ("Make another" on the page), new section 9 (Claude checks each take from frames), new section 10 (where the answers conflict with other rules of SK), more edge cases (E21 to E32), more failure modes (F8 to F13), more tests, a larger size. The trial page is updated at the same link.

## 1. The trial

- **Trial page (private):** https://claude.ai/artifact/B6e5hA4viXjGKB7684rjqn (version 2)
- **Data:** the 17 real takes of VW-12 (16 AI video shots, 31 Oct and 1 Nov 2026), each with its real check by Gemini 3.8 Flash, the real words under it, the real film times, and what really sits before and after it in the film. The videos are reduced copies (768 px wide, 0.1 to 0.5 MB each; 8.1 MB in all with the pictures).
- **Why VW-12 and not VW-21, VW-22 or VW-23:** those three have no AI video take in the database. No film has yet made a take the new way (guide, still, edit of the guide) inside the application. VW-12's takes were made the older way (a start picture and words). The screen is the same for both.
- **What the trial shows:**
  1. a shot with one take to select, its check passed ("Cool home, fewer bricks, shot 2");
  2. a shot with two takes side by side: the first rejected by SK on 31 Oct, the second made on 1 Nov, with "Play both from the start" ("Housing construction at work, shot 1"); "Use take 1 after all" asks once (D7); no "Make another" there, with the sentence why (two takes were made from this camera);
  3. takes whose check did not pass, with the check's lines in full and "Go to 5 s"; selecting one asks for a typed reason (D6);
  4. **"Make another"** (D4): a words box, "What should change in the next take?", with the check's faults in it, and the sentence "A new take is paid. Its price is said in the chat when you say done; nothing is ordered before that."
  5. takes answered earlier, still in the list with their decision, opening again with the take and the check, no buttons, "To change this answer, say so in the chat." (D8);
  6. what comes before and after the take in the film, shown only to compare;
  7. the end card, with how many new takes are ordered;
  8. the state before all takes are made ("Trial views", top right).
- **Fit, checked with Playwright on the real videos:** page areas 1536 x 510 and 1900 x 830; 14 views at each size; no scroll of the page or of the main area, the player, the question and every button in view, no horizontal scroll, no console error; the player is 230 px high at 510 and 550 px at 830. Screenshots: `shots\` (29 files). At 510 px, a long check or an open words box scrolls inside the answer column only.
- **What in the trial is not real:** the check lines are Gemini's of 1 Nov, not Claude's from frames (D5): no such check exists yet. The counts in the "nothing to answer yet" line are an example. Three shots are shown as "answered earlier" by my choice (their decisions are SK's real ones). 13 of the 16 shots have no title in the plan, so the trial names them by their gap's title and number.

## 1a. What is in view and what is on demand (the redone trial; the build follows it)

SK, 19 Nov: "the page need not show everything to the user for recording their decision … too cluttered". Agreed with SK ("Yes, redo the trial"):

**Always in view**
- The take, large, playing.
- One line: the shot's name, and under it **the words spoken during the shot, in time** (section 1b): the word being spoken is marked as the take plays. No sound is played.
- The check as ONE short line. Passed: "Check passed". Failed: "Check:" and the first fault in one sentence, with "Go to N s", and "See all N" only when there are more. Not checked: "Not checked. Judge it by eye."
- The buttons: Select, Make another, Reject.
- Two links: "See it in the film", "Details".

**Shown only when it applies**
- Two takes of one shot: two tabs above the player ("Take 1, rejected", "Take 2"); no tabs for one take. The rejected take's tab shows that take, its check, the words it was rejected with, and one button, "Use take 1 after all". (This replaces "two side by side" of D2: one take is in view at a time, at full size.)
- The take is shorter than its place in the film: one line saying so. Nothing when it fits.
- Why no further take can be made: said in the box that opens on Reject; "Make another" is simply absent there.
- The operator's answer, with Undo, once given.

**Behind one click**
- "See it in the film": what comes before, this take, what comes after, as pictures over the page, with "Shown to compare. Nothing here needs an answer." No answer button is in that view.
- "Details": one link, one sheet over the page: the check (every fault with "Go to N s", who checked and against how many lines, "Not judged: how things move between the frames. Play the take.", the lines that passed); where the shot sits in the film and the gap's name; the take's length against its place; the picture the take started from; how the take was asked for; how it was made.

**The left list:** the shot's name and a dot for its state (a number while open; a tick, a cross, a turn-arrow or an exclamation mark once answered; the state in words is the dot's tooltip and its spoken label). No film time, no take count. "Answered earlier" stays as a group.

**Where "Not judged: how things move between the frames" sits:** behind Details, not in view. Why: it is the same sentence on every take, so in view it would be read once and then ignored, and SK asked for less; the limit is said once, in "How this works", and on every take's Details.

**What could not be hidden, and why:** the first fault of a failed check (D6: selecting against it needs a typed reason, so the operator must see it before clicking); the tabs for two takes (the operator must know a second take exists); the answer given (it must be seen to be undone).

**Kept from SK's earlier rules:** recorded answers stay visible with their decision; every fault can be read in full, one click away; no amount of money on the page; one count; the end card; the page closed with the line of counts until every take is made and checked.

**Room for the take now** (measured with Playwright on the real takes): at 1536 x 510 the picture is 590 x 332 px (before the redo: 409 x 230), in a box of 780 x 332, so about 95 px stay empty on each side of the picture and none above or below; with two tabs it is 528 x 297. At 1900 x 830 the picture is 983 x 553 px (before: 856 wide in a row 550 high, about 856 x 482), with about 50 px empty above and below. The answer column has 332 px of height at 510 and its content needs under 120 px in the common case; only an open words box for "Make another" (413 px) scrolls inside that column.

Screenshots of the redone trial: `shots\v3-1536x510-*.png` and `shots\v3-1900x830-*.png` (14 views at each size, one more in dark).

## 1b. The words in time (SK, 19 Nov: "If we can show the narration or the exact lines that get spoken during this the user can judge better"; "Words only, no sound")

**What it is.** Where the plain line of words sat, the same line is now a caption: the words spoken during this shot, with the word being spoken marked as the take plays. It follows the player's time, also when the operator drags the player or uses "Go to N s". No narration sound is played and nothing is laid under the take. It replaces the plain line; it adds no box.

**Where the times come from.** `visuals_stage.gap_timing` (called by `ensure_timing`) gives, for each gap, `session['source']['gaps'][gap]['timing']['words']`: every word of the narration with its start and end in film frames (from the narration's own timing, `voice_timing.timing_evidence`: the voice provider's character times). A shot's words are those whose start falls inside the shot's frames, and a word's second is `(start_frame - shot.start_frame) / fps`. This is exactly what `motion_brief` prints for a drawn graphic ("Each word's start, seconds from the shot's start"); it does not depend on the kind of shot, so it is the same for an AI video shot. The page's line would carry `[{text, start_s, end_s}]` for the shot.

**A take longer than its place in the film.** A guide take is a little longer than its place, and the place sits in the middle of the take (`take_in_point`: `in_s = (take length - place length) / 2`, kept on the selection). The words are marked against the place, not the take's start: a word's time in the player is `in_s + its second from the shot's start`. Before `in_s` and after the place's end no word is marked. The page's line carries the same `in_s` the film will use, so what the operator sees is what the film will play. (In the trial `in_s` is 0: VW-12's takes are of the older way, which starts the place at the take's first frame.)

**A shot whose words start or end mid-sentence.** Recommendation, and what the trial shows: the shot's own words in full colour, and the rest of the sentence before and after them in grey, cut to about 60 characters a side with "…". The grey words are never marked. Reason: half a sentence is hard to judge a picture against ("are fixed to maintain straight and uniform walls."), and the grey part costs no extra line. The build takes the grey part from the timing's sentences (`timing.sentences`, `before`, `after`), so a sentence that begins before the gap is shown too (the trial only has the words inside each gap).

**A shot with no words.** Nothing is shown: no line, no empty space.

**Long lines.** At most two lines of text; the line never makes the main area scroll. If a shot's own words need more than two lines, the grey part is dropped first; if they still do, the two lines show the part of the words around the word being spoken. On VW-12 every shot's caption is one line at 1536 x 510 and at 1900 x 830.

**Another script (Tamil, Hindi, any).** A word is one unit, exactly as the server gives it (text split at spaces by `timing_evidence`); the page marks whole words and never splits a word into letters, so combining marks stay with their letters. The line breaks between words only.

**No word times** (a film whose narration has no timing, or a gap narrated before timing existed): the words are shown as a plain line, unmarked, as before.

**Verified on the trial** (VW-12's real word times, read from the film's session): for all 16 shots the timed words are exactly the plan's narration of the shot; the first word starts between 0.00 and 0.16 s and the last ends inside the shot's place. In the browser: dragging the player to 2.0 s marks "continues", to 0.1 s marks "As", to 5.9 s (past the place) marks nothing; while playing, the mark moves word by word.

## 2. The requirement, restated

Step 7 has no page today: every AI video decision is a single chat question, and a ready take is asked the moment it arrives. VW-24 has 19 AI video shots.

Build this:
1. **The finished takes are judged on the decisions page, all together, once every take of the film is made and checked.** One screen in the frame of steps 5 and 6: the list of what needs an answer, one shot at a time, the take large, the check as one line, the question, the buttons, one count, an end card. Nothing is recorded or ordered before the operator says done in the chat.
2. **Three answers to a take:** Select; Make another, with the operator's words (it orders one more take); Reject (no new take).
3. **Claude checks each take**, from frames the server takes from it; the Gemini 3.8 Flash check of a take is retired.
4. **What must be decided before the first take of a shot is paid for stays in the chat, one card each:** the shot's layout drawing, the still, the word to make the take, and "send the same request once more" for a clip that came back unusable.
5. **While takes are being made or checked, the page is closed** and the chat says one short line of counts.
6. **A recorded answer stays visible** on the page with its decision and can be opened again; it is changed in the chat.

## 3. What moves to the page and what stays in the chat

| Today (all in the chat) | After the build |
|---|---|
| The layout drawing of the shot: Yes / Correct it | **Chat card**, unchanged (D11) |
| The still on the overlay: Approve / Reject | **Chat card**, unchanged (SK, 19 Nov) |
| The word to make the first take: Shoot / Not yet, with the price | **Chat card**, unchanged (SK, 19 Nov) |
| A clip that came back unusable: Send it again / Not yet | **Chat card**, unchanged |
| The take: Select / Reject, asked as each take arrives | **Page**, when all takes are made and checked |
| The word to make a second take | **Page**: "Make another" (D4). No second Shoot card. |
| The scorecard of Gemini, as up to eight text lines | **Page**: Claude's check as one coloured line, the faults in full, "Go to N s" |
| "Take · shot" progress, one item at a time | **Chat**: one line of counts; nothing asked with it (D10) |
| Why a rejected take was wrong (the cause) | **The assistant**, from the words given on the page; said in the chat in one line, not asked |
| A new still when the still was the cause | **Chat card** (the still's approval, as for any still) |
| Cut the shot, another angle, or leave it out | **Chat**, unchanged |
| "Record this gap into the film?" | **Chat**, unchanged |

## 4. Unstated but expected requirements

1. One flow, two front ends: the page's answers call the server functions the chat calls (`review_take`, `select_take`, `guide.set_cause`, `guide.shoot`); where the page cannot be shown, the chat can ask the same line with the same words.
2. Every word on the screen comes from the server (`layout.words`); the chat says the same words. No amount of money in any of them (D1).
3. The page opens only when every AI video shot of the accepted plan has a take that is made and checked (or offered as not checked after the time limit), or is one that could not be made. A shot waiting for a chat card keeps the page closed, and the line of counts says how many wait for the operator in the chat.
4. Order of the list: film order.
5. A shot is one line, however many takes it has. The newest take is the one to answer. Two takes are shown side by side (D2); further earlier takes are one click away.
6. A shot's name is never an id. The plan check asks for a title on every AI video shot; where one is missing, the name is the gap's title and the shot's number in it.
7. "Before" and "after" mean what sits directly before and after the **shot** in the film: the neighbouring shot's own picture inside the gap; the footage at the gap's edges. Never with answer buttons. Where the film holds no picture of it, nothing is shown.
8. A take selected against a failed check carries the operator's typed reason (D6) and is marked "Against the check" in the list and on the end card.
9. The take plays with no sound, on a loop. The copy on the page is a reduced copy; the film uses the original.
10. The page's limits as on step 6: a round is one document of at most 200,000 bytes; details are dropped from the last lines first, a line is never cut.
11. All categories of video: no word on the screen is about documentaries.
12. Desktop only; fit at 1536 x 510 and 1900 x 830 with no scroll of the main area, checked with real takes before any deploy.
13. The decision log gets one entry per answer given on the page, and one per take ordered from the page with its price.
14. The old ways are named (the Old ways rule): the take asked in the chat as it arrives; the Shoot card for a second take; Gemini 3.8 Flash watching a take; the start-picture question of an AI video shot (dead since 12 Nov). Each is retired, refused by name where it can still be called.
15. A take is never offered before its check is recorded or its time limit has passed (today it can be: section 9.8).

## 5. Edge cases and how each is handled

| # | Case | Handling |
|---|---|---|
| E1 | A take could not be made (the provider failed, refused the request, or the answer never came) | The shot is listed apart, "Could not be made", with one sentence; it never keeps the page closed; the assistant says in the chat what happens to it. |
| E2 | A clip came back unusable (the guide unedited, wrong length, first frame off the still) | It is not a take and is never on the page or given to Claude's check. The chat card "Send the same request once more?" stays. Until answered, the shot counts as "waits for you in the chat". |
| E3 | A take too large for the page | The page copy is made as step 6 makes it (ffmpeg, 960 px wide, no sound). A 10 s take is under 1 MB that way; the limit is 15 MB a file. If a copy cannot be made: the frame sheet takes its place with one sentence. |
| E4 | No take yet | The page is closed: "Nothing to answer yet" and the line of counts. |
| E5 | Many takes arriving | Nothing is put on the page one by one. The chat says the line of counts when it changes; nothing is asked with it. |
| E6 | The operator answers while more arrive | Cannot happen: the page is closed until all are made and checked. |
| E7 | A new take ordered from the page | The page closes when the operator says done. When the new take is made and checked, the page opens again: only that shot needs an answer; the others are under "Answered earlier". The rejected take is beside the new one, with the operator's words. |
| E8 | Two takes were made from one camera | No "Make another" on that shot; one sentence says why. Reject leads to the chat: cut the shot, another angle, or leave it out. |
| E9 | A shot with a start and end image | Does not exist on a film started after 12 Nov. The dead branch is removed. |
| E10 | A take whose check never came | 30 minutes after Claude was first asked (as step 6), the take is offered as "Not checked: Claude's check did not come within 30 minutes. Judge it by eye." Selecting it needs the typed reason (D6). |
| E11 | Claude could not open the frames of a take | The same grey line, with the reason in one sentence. |
| E12 | The cost limit is reached | No still or take is made. The shot counts as "waits in the chat"; the assistant says the spend and that only the owner can change the limit. The page stays closed (D9). |
| E13 | A film with no AI video | Step 7 has no page and no line of counts. |
| E14 | A film with only AI video | The page goes from the references straight to "AI video". |
| E15 | A take shorter than its place in the film | Said in the line under the player and selecting it needs the typed reason. |
| E16 | The plan changed after a take was made | The take cannot be selected. It is counted as "must be made again" and is not on the page. |
| E17 | The same answer sent twice, or two windows | The second answer finds the line no longer waiting and is ignored with one sentence. A take is ordered once: the server refuses a second order while a take of the shot is open. |
| E18 | An open question on the shot | Its take is not offered; the question is asked in the chat first. |
| E19 | A shot cut out by a plan revision | Its takes leave the list and "Answered earlier". |
| E20 | 30 or more AI video shots | The list scrolls on its own; the round's size limit drops details from the last lines first. |
| | **Added by "Make another" (D4)** | |
| E21 | The assistant reads the words and the cause is **the words of the take** | The take's words change in that one thing and the take is ordered. No card. One chat line says the shot, the length and the price. |
| E22 | The cause is **the still** | A new still is made (paid) and its approval card comes in the chat, as for any still. After the Yes, the take is ordered without a second Shoot card. If the operator rejects the new still, nothing more is ordered until a still is approved. |
| E23 | The cause is **the layout** (a reach, a path, a speed) | The scene changes (free), its drawing is approved again in the chat, its still is made again and approved in the chat, then the take is ordered. Three cards before the take; the chat says so at once. |
| E24 | The cause is **none of these** (the model's limit) | No take is ordered: a second take from the same request would repeat the fault, and the server refuses it. The chat says so and asks: cut the shot, another angle, or leave it out. |
| E25 | The operator's words name nothing that can change ("make it better") | The assistant asks once in the chat what should change. Nothing is ordered before the answer. |
| E26 | The take's first frame did not match the still | The server refuses a cause in the words (today's rule): the cause is the still or the layout (E22, E23). |
| E27 | Several takes ordered in one visit and the cost limit allows only some | They are ordered in film order while the limit allows. The chat names the ones not ordered and the spend. |
| E28 | "Make another" clicked, then Undo before done | Nothing was ordered: the page orders nothing before done. |
| E29 | "Make another" on a take answered earlier | Not offered (D8). |
| E30 | The new take must wait for cards (E22, E23) and the operator leaves | The page stays closed; the line of counts says "1 waits for you in the chat". |
| | **Added by Claude's check (D5)** | |
| | **Added by the words in time** | |
| E33 | The take is longer than its place | The words are marked from `in_s`, the second the place starts in the take; nothing is marked before it or after the place's end. |
| E34 | The shot's words start or end mid-sentence | The rest of the sentence in grey, never marked, cut to about 60 characters a side. |
| E35 | A shot with no words, or a film with no word times | No line; or the plain unmarked line when there are words but no times. |
| E36 | The words need more than two lines | The grey part is dropped first; then the two lines follow the word being spoken. |
| E37 | A film in another script | Marked by word, never by letter. |
| E38 | The operator moves the in point of a take later (in the chat) | The page's next round carries the new `in_s`; the mark follows it. |
| | **Added by Claude's check (D5), continued** | |
| E31 | 19 takes become ready within minutes | Helpers check them, several at once, about three takes each; the assistant starts them when the tool says takes wait for a check. |
| E32 | A take is remade while its check is being written | The check names the take by its content; a check of an older take is refused by name and the new take is listed again. |

## 6. Failure modes and their handling

| # | What fails | What the operator sees | What the system does |
|---|---|---|---|
| F1 | The video does not play in the page | The frame sheet with one sentence | As step 6. |
| F2 | A picture beside the take is missing | The buttons stay off; one sentence names the picture | This line is answered in the chat. |
| F3 | The server refuses an answer after "done" (the plan changed, a question opened) | The refusal in the server's sentence on that shot's line | As steps 5 and 6. |
| F4 | "Done" is said with answers missing | "N answers still needed" | The given answers are recorded; nothing for the missing ones. |
| F5 | The connection drops while answering | Answers already written stay; the page says it could not save | The page's own store. |
| F6 | The page copy of a video cannot be made | The frame sheet | Tried again on the next call. |
| F7 | A take is selected but its recording fails later | Said in the chat at the recording step | Unchanged. |
| F8 | The order of a new take is refused after done (cost limit, a take already open, the plan changed) | One chat line: which shot, why, what happens now | The rejection stays recorded; nothing is ordered; the shot is counted as "waits in the chat". |
| F9 | The ordered take fails at the provider | The shot under "Could not be made" when the page next opens, and one chat line | No automatic second order: money is spent only on the operator's word. |
| F10 | The ordered take comes back unusable (the guide unedited) | The chat card "Send the same request once more?" | As today (E2). |
| F11 | The frames of a take cannot be made by the server | The take is offered as "Not checked: its frames could not be made." | The take is not held back. |
| F12 | A helper stops midway through its takes | Nothing; the unchecked takes are listed again | They stay due; after 30 minutes they are offered as not checked. |
| F13 | Claude's check sends a line with no answer, or for an older take | Nothing | The server refuses that take's row by name; the others are recorded (as step 6). |

## 7. SK's answers (19 Nov, relayed)

| # | Decision | SK's answer | Against my recommendation? |
|---|---|---|---|
| D1 | Cost at step 7 | Not on the page | no |
| D2 | Takes side by side | Two; then, with the redone trial (section 1a): two tabs, one take in view at a time | no |
| D3 | Rejecting needs a reason | Yes | no |
| D4 | "Make another" | **On the page too** | yes: section 8 |
| D5 | The take check | **Claude checks, as in steps 5 and 6** | yes: section 9 |
| D6 | Selecting against a failed check | **A typed reason** | yes: today's server rule stays; the trial shows it |
| D7 | An earlier rejected take | Yes, asked once | no |
| D8 | A recorded answer | Shown, changed in the chat | no |
| D9 | The page opens | When every take is made and checked | no |
| D10 | Finished takes one by one in the chat | No, the line of counts only | no |
| D11 | The layout drawing card | Keep it now, change later | no |
| D12 | Names | "AI video" and "take" | no |

## 8. "Make another" on the page (D4)

### What it is
"Make another" is two things in one click: the rejection of this take, and **the operator's word to pay for one more take of this shot**. It takes the place of the second Shoot card.

### What it asks
One box: **"What should change in the next take?"** It opens with the failed lines of the check in it, to edit or replace. The words are required. They are used three times: as the rejection's reason, as what the assistant names the cause from, and as what the next take is made from.

### What it orders, and when
Nothing is ordered on the click. On "done" in the chat, for each such answer, in film order:
1. The rejection is recorded with the words (`review_take`).
2. The assistant names the cause from the words and the check, in the server's order: the first frame against the still, then the layout, only then the take's words; else the model's limit (`guide.set_cause`). One chat line says it; nothing is asked.
3. The one thing changes: the take's words (E21), the still (E22) or the layout (E23).
4. The take is ordered with the operator's click as its word (`guide.shoot`, quote "Make another", with their words). No Shoot card.
The rule "the same request is never sent twice" stays: something must have changed, or no take is ordered (E24, E25).

### Where the price is said
Not on the page (D1). The page says: "A new take is paid. Its price is said in the chat when you say done; nothing is ordered before that." The end card says how many new takes are ordered. In the chat, after done, **one line, said and not asked**: "2 new takes are ordered: 13 s, about ₹N." The operator already saw the price of a take of this shot on its first Shoot card; a second take of the same shot has the same length and price.
- **D4a, answered by SK on 19 Nov (relayed): "Said, not asked".** After done the chat says one line with the number of new takes, their length and the amount; there is no second question. The click on the page is the word.

### When no further take is allowed
- Two takes were made from this camera: the button is not on the line; one sentence says why (the trial shows it on the first shot). Reject leads to the chat: cut the shot, another angle, or leave it out.
- The cost limit would be passed: the button is not on the line; one sentence: "The cost limit of this film is reached. Only the owner can change it." (no amounts).
- The last take's cause was the model's limit: no button.

### The third answer, Reject
Reject stays for "this take is wrong and I do not want another now" (the shot may be cut or changed). It orders nothing; the assistant asks in the chat what happens to the shot.

## 9. Claude checks each take (D5)

Claude cannot play a video. It judges **frames taken from the take**. This section says exactly which, what is asked, and what cannot be judged.

### 9.1 Who takes the frames
The server, when the take is stored and has passed its three measured checks (as it makes a drawn graphic's frames today). Free. Stored beside the take:
- **every half second** of the take, the first frame and the last frame, each at 960 px wide (a 6 s take: 13 frames; a 10 s take: 21). The half second stays (the test of 19 Nov: no fault was missed for want of more frames);
- **one sheet at 4 frames a second**, small pictures in order with the time under each (the server makes this sheet today). **Required:** a take whose sheet could not be made is offered as not checked. In the test the helpers placed every fault that fell between two half-second frames with this sheet;
- to compare with: **the approved still** (what the first frame must be) and **the guide's three check frames** (first, middle, last: where each person and thing should be).
The planned action's own seconds are in the take's words ("ONE action only", a second on every move); the frames nearest those seconds are marked in the list Claude gets.

### 9.2 Who looks
A Claude helper, as `vw-picture-look` does in step 6: several helpers at once, about three takes each (a take is 15 to 25 pictures). The assistant starts them when the tool says takes wait for a check (`vw visuals takes --looks`, beside `vw visuals pictures --looks`). The helper never selects or rejects a take.

### 9.3 What Claude is asked, line by line
Each line gets pass or fail, one plain sentence of what was seen on a fail, and the second of the frame that shows it (so "Go to N s" works on the page).

| The scorecard today | After the build | Judged from |
|---|---|---|
| 1. Real footage and length | **Unchanged: measured by the server.** A failure sets the clip aside. | the file |
| 2. First frame | **Unchanged: measured by the server.** A failure sets the clip aside. | the file and the still |
| (new) One continuous shot | **Measured by the server**, from the file: a sudden change between two neighbouring frames (a jump to another view). It marks the take's line as failed; the take is not set aside. On VW-12's 17 takes this measure (ffmpeg's scene score above 0.25) marks exactly the three takes with a jump, at 1.1 s, 1.5 s and 4.0 s, and no other. | the file |
| 3. People | **Claude.** The same people in every frame as in the first: nobody added, missing, doubled or changed; faces and clothes the same in the first and last frame. | all frames |
| 4. The action | **Claude.** The one action asked for is seen to start, go on and end in the frames at its seconds, in that order, and nothing else is done; any lettering reads the same at the end as at the start. | the marked frames, the take's words |
| 5. Objects | **Claude.** Every object of the first frame is in the last unless a hand is seen moving it; counted things keep their count; none changes shape, size or kind. A thing present in one frame and gone in the next with no hand near it fails. | all frames, the sheet |
| 6. Bodies and contact | **Claude.** In each frame: hands grip what they hold, nothing passes through anything, no extra limb or finger, feet on the ground. | all frames |
| 7. The place and the light | **Claude.** The place, its fixed things and the light's direction and brightness are the same in the first, middle and last frames. | three frames |
| 8. The join ("Not sure", always) | **Removed from the check.** The page's film-order row is how the operator judges the join. | (none) |
| (the camera's drift, measured) | **Unchanged: measured by the server**, shown as measured advice, not as Claude's line. | the file |

### 9.3a Two rules that cut the noise (from the test)
- **What the start picture (the approved still) already shows is not a fault of the take.** A line is judged against the still where the plan's words and the still differ (two of the test's light lines were faults of the start picture, not of the take).
- **Nothing that only motion can show is asked of frames.** "The surroundings move" (leaves, dust) is not a line of Claude's check; the five lines of a guide take do not have it.

### 9.4 What cannot be judged from frames, and how it is said
- how things move between two frames: speed, slow motion, a jerk, a jump;
- a fault shorter than half a second (a hand through an object for a few frames, a flicker);
- **how** a thing went: Claude sees "the broom is in his hand at 3.0 s and gone at 3.5 s, no hand near it", not the vanishing itself;
- whether the action runs in real time;
- sound (a take has none in the film today).
Where it is said (the redone trial, section 1a): in view the check is one short line, "Check passed" or the first fault. In Details, on every take: who checked ("Claude looked at 13 frames of this take (one every half second, the first and the last), the sheet at four a second and the start picture, against 12 lines. The server measured one more: one continuous shot.") and **"Not judged: how things move between the frames. Play the take."** The same limit is said once in "How this works".

### 9.5 The time limit
30 minutes from when Claude was first asked to check the take (the rule and the number of step 6). Then the take is offered as "Not checked: Claude's check did not come within 30 minutes. Judge it by eye.", and the page may open. A check that arrives before the operator's answer replaces "not checked".

### 9.6 What happens to the Gemini check
`image_check.run_take_check`'s reading by Gemini 3.8 Flash is no longer run for a take. The record a take carries (`session.take_checks`) keeps its shape: the server's measured lines, then Claude's five lines in place of Gemini's five, so `select_take`'s rule (a failed line needs the typed reason) reads it unchanged. Retired by name in design/35.

### 9.7 My honest view of what is lost, and the cheap test
- **Lost:** everything in 9.4. Gemini watches the whole clip; Claude sees two pictures a second. Faults of motion and faults shorter than half a second will be passed.
- **Probably kept:** most of what the check actually found on VW-12. Of its 19 failed lines on 17 takes, most are visible in still frames: the planned end not reached (the last frame), a man where the plan asks for a woman (any frame), a pan on the head instead of in the hand (the last frame), the camera tracking away (the server's own measurement), a broom gone between two seconds (two frames). The one I expect frames to miss or blur: "the tractor's parts distort as they near the camera".
- **Gained:** the same kind of check as steps 5 and 6, in words the operator can send back; no Gemini key to fail (defects 43 to 45 stalled two films); the check can read the approved still and the layout beside the frames.
- **Not known for either:** how often the faults are right. SK selected all 16 shots of VW-12 with 9 takes marked.
- **The cheap test, before the build is released (no money, about an hour):** take the 17 takes of VW-12; make the frames as 9.1 says; a helper that has not seen Gemini's results judges each take against the same lines Gemini had that day; then compare, line by line: (a) of Gemini's 19 failed lines, how many Claude also fails; (b) what Claude fails that Gemini passed; (c) for the one take SK rejected (shot 1, take 1, which Gemini passed on every line), whether Claude finds a fault. SK looks at the disagreements only (I expect 10 to 20 lines) on one page. If Claude misses more than a few of (a), the half second becomes a quarter second, or the server adds one measured line for a sudden change between neighbouring frames. Limit of this test: VW-12's takes are of the older way; the five lines of a guide take get their first real test on the first new film.

### 9.7a The test's result (19 Nov) and SK's decision
The test was run on VW-12's 17 takes: `222-step7-take-check-test-result-19-nov.md`, page https://claude.ai/artifact/WaL36EQAXtzNPrVE5JXxft. 197 lines: 150 both passed, 8 both failed, 6 only Gemini failed, 33 only Claude failed; Claude found a jump to another view in three takes that Gemini passed (one is the take SK rejected); Claude missed three things Gemini saw. SK, having seen the page: "the claude checks can be retained." So: the half second, the sheet at four a second required, the measured line "one continuous shot", and the two rules of 9.3a.
Also to fix in the build (found by reading, never run): `guide_worker.take_checks` reads the frame rate with `float()` on the text "24/1"; it must be read as a fraction, or the sheet is never made for a guide take.

### 9.8 The gap: a take shown before its check is stored
Found in the code: the take's job is marked ready first, and its check is written about a minute later (`visual_workers.tick`: `jobs.finish`, then `check_take`). In between, `waiting` already hands the take out, with no check lines. With this build the gap closes by rule 15 of section 4: a take is offered only when Claude's check of its content is recorded, or 30 minutes after Claude was asked; and the page opens only when that holds for every take.

## 10. Where SK's answers conflict with another rule of his

Said plainly; each needs one word from SK.

1. **D4 against his decision of 19 Nov ("the word to shoot stays in the chat, because a take costs money") and against D1 (no cost on the page).** With D4, the word for a second take is given on the page, where no amount is shown. Section 8 resolves it this way: the page says the take is paid, the amount is said in the chat right after done, and the first take of every shot keeps its Shoot card with the price. SK settled it with D4a: said, not asked.
2. **D4 against the cause rule (SK, 10 Nov: "fix once": name the cause, the still, the layout or the words, before another take).** The page cannot ask the cause. Section 8 keeps the rule: the assistant names the cause from the operator's words before anything is ordered. Consequence SK should know: "Make another" does not always make a take at once. When the cause is the still or the layout, one to three chat cards come first (E22, E23); when it is the model's limit, no take is made (E24).
3. **D6 against his standing rule "approving against a failed check asks once".** D6 (a typed reason) is the newer answer and is built for takes. Step 6 then has both: a still against Claude's check asks once; a drawn graphic and a take need a typed reason. If SK wants one rule everywhere, that is a change to step 6, outside this build.
4. **D5 with D9: the page waits for Claude's check of every take.** No conflict of rules, but a cost in time: the page opens some minutes later than the last take is made (helpers checking 19 takes), at most 30 minutes if a check never comes.
5. **D5 against "one flow, two front ends" for the helper:** none; the check is a server record whichever front end shows it.
6. **D10 with D4:** a bad take is found only when the page opens, and its remake closes the page again. Each round of "Make another" is one more visit to the page. SK chose this knowingly; noted so it is not a surprise on VW-24.

## 11. Tests

Written first, from the approved list. Database-free where possible (`server/unit`), plus the page tests with a browser (`server/pagetests`).

Server, the page and the gate:
1. 3 AI video shots, 2 takes checked and 1 being made: the page is closed, the answer is the line of counts, `waiting` hands out no take.
2. All 3 made and checked: the page is open with 3 lines in film order; each with its video, its check, its where and words, its buttons.
3. A take made but not yet checked: not offered (the gap of 9.8); offered 30 minutes after Claude was asked, as "not checked".
4. A clip set aside: not a line, not given to the check; the page stays closed; the chat item "Send it again" exists.
5. A shot with a rejected take and a new one: one line, "2 takes", the earlier take with the rejection words, no "Make another".
6. Select: the same function as the chat; against a failed line, a not-checked take or a short take, the typed reason is required and recorded.
7. Reject needs words; nothing is ordered; the next chat item asks what happens to the shot.
8. Use the earlier take after all: asked once when its check passed; the typed reason when it failed.
9. A take that could not be made: listed apart; the page opens without it.
10. A stale answer is ignored. A film with no AI video: no step. A film with only AI video: from the references to step 7.
11. A shot with no title: the gap's title and number. Before and after: the neighbouring shot; the footage at the gap's edge; nothing when no picture.
12. The round's size: 30 lines under 200,000 bytes. The words: every label in `layout.words`; no amount of money in any.
13. Steps 5 and 6 are unchanged: their fixtures give the same rounds.

Server, "Make another":
14. The answer needs words; nothing is ordered before "done".
15. Cause in the words: the words change, one take is queued, the chat line names shot, seconds and price; the quote of the order is the operator's.
16. Cause the still: a still is queued, no take; after the still's approval the take is queued with no Shoot item.
17. Cause the layout: the drawing item, then the still item, then the take.
18. Cause the model: no take; the chat asks cut, angle or leave out.
19. The first frame failed: a cause in the words is refused.
20. Two takes from the camera, or the cost limit would be passed: the line has no "Make another" and has its sentence.
21. Three orders and a limit that allows two: two queued in film order, the third named with the spend.
22. "Done" sent twice: one take queued.
23. The Shoot item for a second take no longer exists; the first take's Shoot item is unchanged.

Server, Claude's check:
24. The frames: every half second plus first and last, the 4-a-second sheet; a 6.04 s take gives 13 frames.
25. The list of takes due: content mark, frames, still, guide frames, the five lines; a blocked clip is never listed.
26. A look recorded: five lines with pass and, on a fail, a sentence and a second; a missing line, an unknown line or an older take is refused by name, the others recorded.
27. The record keeps the scorecard's shape: `select_take` requires the reason on Claude's failed line.
28. The check line's words: pass says the number of frames; the "not judged" sentence is on every take.
29. Gemini is not called for a take (the transport is never used).
28a. The words in time: a shot's line carries its words with seconds from the shot's start, equal to what `motion_brief` gives for the same frames; the take's `in_s`; a shot with no words carries none; a word is never split.
29a. One continuous shot: a file with a jump fails the measured line with its second; a file with a fast pan does not; the take is still offered.
29b. The sheet at four a second could not be made: the take is offered as not checked.
29c. A fault the still already shows is not asked: the helper's instructions and the list carry the still as what the take is judged against.
29d. The frame rate "24/1" is read as 24.
30. The retired ways are refused by name.

Page (Playwright, with real takes, at 1536 x 510 and 1900 x 830): the fourteen views of the redone trial's fit check on the real page file (two tabs, Reject saying why no further take, the typed reason, "See it in the film", "Details", every fault one click away, "Make another", an answer reopened, the end card, the closed state); in view on a line are only the name, the words, the take, the check line, the buttons and the two links; the words in time: dragging the player marks the word of that second, past the place nothing is marked, the line is at most two lines, on a server that answers byte ranges (a plain test server cannot seek in a video); the video plays; "Go to N s" moves the player; the keys; the answered lines stay; the end card counts the new takes; the closed state.

Before release: the cheap test of 9.7 on VW-12, and one full run on the test film (VW-24, 19 AI video shots).

## 12. Not covered, and not verified

Not covered by this build (deliberately):
- The chat cards (drawing, still, first Shoot): unchanged. All shot drawings on one page visit (D11): later.
- One rule everywhere for "against the check" (section 10, point 3): a change to step 6.
- Sound; trimming a take or choosing where it starts in its place; the recording step and after.
- A measured line for sudden change between frames: only if the test of 9.7 shows the need.
- Phones.

Not verified:
- **No take made the new way exists.** The scorecard, the set-aside clip and the overlay were read in the code only.
- **Claude's check from frames has never been run on a take.** Section 9 is a specification; 9.7's test is how it gets verified. How long helpers take on 19 takes is an estimate.
- Whether the videos play inside the published trial for SK: checked locally with a browser, not on claude.ai.
- The size of a page copy at 960 px for a guide take: estimated from VW-12's takes at 768 px.
- The trial page is my own code in the look of step 6, not the real page file; the build's fit must be checked again on the real file.

## 13. What the build would touch, and its size

No code is written here. Estimates are lines changed or added. Revision 1 was about 650 lines of product code and text and 450 of tests; D4 and D5 add about 400 and 350.

| Where | What | Size |
|---|---|---|
| `server/app/pictures.py` | The line of a take: video, earlier takes, before and after, the check as one line with seconds, three answers and their sentences; the words; each shot's state and the line of counts | about 200 |
| `server/app/takes_look.py` (new, beside `pictures.py`'s look functions) | Which takes are due for Claude's check, the lines, the list for the helper, recording a look, the time limit | about 180 |
| `server/app/guide_worker.py`, `visual_workers.py`, `image_check.py` | The frames every half second stored with the take; Gemini's reading no longer called for a take; the scorecard built from Claude's lines | about 80 |
| `server/app/visuals_stage.py` | `waiting`: a take is held until all are made and checked; the dead start-picture branch removed; `select_take` for an earlier take | about 50 |
| `server/app/guide.py` | An order from the page: the cause, the one change, `shoot` with the page's word; the refusals as sentences for the line | about 70 |
| `server/app/chat_flow.py` | The take item carries its page line; the second Shoot item removed; the chat lines after done (cause, price); the header comment | about 70 |
| `server/app/page_flow.py`, the API routes | The step after `pictures`; the round of step 7 open and closed; its answers; more than one video on a line; two routes for the looks | about 130 |
| `plugin/pages/decisions.html` | `layout.kind = "takes"` in the frame of step 6: two players, "Go to N s", the film-order row, "Answered earlier", "Make another" | about 220 |
| `plugin/scripts/vw.py` | `vw visuals takes --looks`: fetch the frames into the run folder, send the looks | about 80 |
| `plugin/agents/vw-take-look.md` (new) | The helper's instructions | about 40 |
| Served text (`server/procedures/v3.json`), `plugin/skills/guide/SKILL.md`, `plugin/commands/vw.md` | The new order; who checks; "Make another" | about 60 |
| `design/35` (old ways), a design note, the versions, the plugin minimum | | about 70 |
| Tests: `server/unit` (two files, one fixture round), `server/pagetests` | Section 11 | about 800 |

The test's result adds the measured line and the two rules (about 40 lines and 4 tests); the redone page is about the same size in the page file (no film-order row and no rows of details, but two sheets over the page). The words in time add about 15 lines on the server (the shot's words and `in_s` on the line), about 30 in the page file and 3 tests. In all about 1,135 lines of product code and text and 860 of tests. One deploy of the server and one publish of the plugin; laptops update. Who does what: the builder thread builds and deploys on SK's word; SK approves this list, the trial and the release.
