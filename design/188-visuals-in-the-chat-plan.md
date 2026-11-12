# 188 — The visuals stage in the operator chat: the plan

12 Nov 2026. For SK's approval. A plan, not yet a requirement list; no code. It answers the handover note `HANDOVER-visuals-in-operator-chat-2026-11-12.md` and SK's three additions of the same day.

## 1. What SK asked, restated

1. **Every visuals decision is taken in the chat.** Pictures and videos are shown inside the Claude window. The user answers with buttons ("A, B or C"; "Yes, No, Correct").
2. **One thing at a time.** One treatment line, one plan gap, one reference picture, one take. Never a list to work through.
3. **No approval can be missed.** The gates are real, not an instruction the assistant might forget.
4. **Only the question.** The chat does not tell the user what it did or how. It posts the question, as the brief, the script and the voice steps do today.
5. **The user is told when to wait.** When several helpers work at once, the chat says so up front, and says what is happening where ("gap 1 has its stills, gap 2 is searching"), so nobody wonders whether to wait.
6. **Users cannot open the visuals page** (the one with the tabs).
7. Fully implemented and tested; more work is accepted.

Two points of the handover note are changed by this: its three-bullet opening note per step is dropped (point 4), and the page is not kept as the user's fallback (point 6).

## 2. Due diligence: can the chat do it?

Read in the code on `main` (b29aa34 and later). Each row says what exists and what does not.

| Need | What exists today | What is missing |
|---|---|---|
| Show a picture in the chat | The tool downloads any reference or take into the run folder (`vw visuals fetch`). The plugin's guard already lets the assistant show a file of the run folder to the user (`SendUserFile`, design/49) | Nothing in the instructions tells it to. Not yet seen working on the Mac in an operator session |
| Buttons | The guard already allows the question tool (`AskUserQuestion`): 2 to 4 buttons plus a free-text answer. The Mac screenshots of VW-21 show such buttons today | The buttons and their meaning are invented by the assistant each time. They must come from the server, so every user sees the same |
| A video in the chat | The same file route. The four research videos reached SK in this app as file cards today | **Not proven:** whether a take plays inline in the chat on the Mac, or opens in the Mac's own player. One test settles it; either way the user sees the take without the page |
| A set of pictures (A, B, C) | The server judges a set together (design/151) | One combined picture with a letter on each candidate, made by the server |
| The approval is the user's words | Every decision command already stores the user's reply as `--quote` | Nothing |
| The gates | Every later step is refused by the server until the earlier one is approved (about 75 routes) | **Nothing hands out the single next decision.** The server lists everything that waits, and the assistant picks |
| Telling the user to wait | Nothing | A status the server gives: what is being made, for which gap, and whether the user's answer is needed now |
| Closing the page to users | The page is one route with a sign-in | A rule on who may open it |

So the mechanics are there. What is missing is the conductor: one server function that says "this is the next decision, show this, offer these buttons", and refuses everything else.

## 3. How it will work

### The conductor: `vw visuals next`

The server answers with exactly one item:

- where it is ("Reference 7 of 23");
- the question, in fixed plain words, the same for every user;
- what to show: the files to download and show, or the text of the line;
- the buttons, at most four (for example "Use A", "Use B", "Use C", "None of these"), each with what it records;
- or, when nothing waits for the user: what is being made and that no answer is needed.

The assistant shows the files, asks the question with those buttons, and sends the answer back (`vw visuals answer --item … --choice … --quote "<their words>"`). The server maps the answer onto the decision functions that exist today; no approval logic is rewritten.

**The gate:** the server refuses an answer to any item other than the one it handed out, and refuses to hand out the next while one is open. That makes "one at a time" and "none missed" a property of the server.

### Only the question

The item carries the question and nothing else. The instructions tell the assistant to post it as it comes: no account of what it did, no summary of the step.

### Waiting, said clearly

- Before helpers start, one fixed sentence from the server, with the numbers filled in: "Five helpers are now working on the five gaps. This takes about N minutes. You do not need to do anything; I will ask you when the first one is ready."
- Each time something finishes, one line from the server: what is ready, what is still being made, for which gap ("Gap 1: its stills are ready. Gap 2: searching for pictures. Gaps 3 to 5: waiting").
- Every such line ends with one of two fixed phrases: "Nothing is needed from you now" or "Your answer is needed".

### The page

Closed to users: its address answers "Visuals decisions are taken in the chat" for anyone but the administrator. SK and the builder keep it to look at a run. Every message in the tool that sends the user to the page (31 today) is rewritten. This happens with the last release below, not before: until every step works in the chat, closing the page would strand a user.

## 4. The steps, in the order they are built

| Release | Steps moved to the chat | What "one at a time" means there |
|---|---|---|
| **A** (text only) | The conductor itself. The treatment. The plan | One treatment line. One gap of the plan |
| **B** (pictures) | Reference pictures, reference sets, the style sheet, character and prop sheets, generated stills, graphics, drawing specs | One picture, with Yes / No / Correct. One set as one lettered picture, with A / B / C / None. One spec |
| **C** (video) | Takes of drawn shots. For an AI video shot: the still on its overlay, the word to shoot, the take with its scorecard. The finish on a drawing (take it away). Recording the gaps. The page closed to users | One take: Select / Reject. One still: Approve / Reject / Repair |

Each release has its own requirement list for SK's approval before its code, with its edge cases and tests. Each is one deployment on SK's yes, and each raises the minimum plugin, so laptops update three times.

## 5. Decisions already taken from SK's words

- **"Approve all" is refused in words.** One at a time is the core rule.
- **A set is one thing.** Its candidates are shown together in one lettered picture and answered with one button. The elements are still answered one by one.
- **A long round is accepted.** A reference round can hold dozens of elements (58 in one test). One at a time means that many questions.
- **A free-text answer is always possible** beside the buttons, for "correct this: …".

## 6. How it is tested

1. **Unit tests** for each release: the order of items, the count, the refusal of an out-of-turn answer, each button's mapping to its decision, a run resumed on another computer, a changed item returning, the waiting lines.
2. **The plugin's guard tests**: showing a run file passes, anything outside the run folder is refused, as today.
3. **One real film through the chat on the Mac**, start to end of the visuals stage, with the transcript kept as proof. This is the only test of what the user actually sees (a picture inline, a video playing, the buttons). It cannot be done on this PC: the plugin is not installed here.
4. **A first small test before release A is even built**: on the Mac, one picture and one take shown in an operator chat by hand, to settle the two unproven points of section 2.

## 7. Older ways

- The visuals page as the place where the user decides: retired for users when release C is live; kept for the administrator.
- The tool's page-first messages: replaced release by release.
- The assistant choosing the order of what waits: retired with release A.

## 8. What this does to VW-21

VW-21 is already deep in the visuals stage on the page. It finishes there. The chat flow is tested on a fresh film, so the two do not disturb each other.

## 9. Not covered, and risks

- **Size.** The handover's estimate was 600 to 900 lines. With the picture sheet for sets, the waiting status, the rewritten messages, the page rule and the tests, I expect two to three times that. No time is promised.
- **A video inline on the Mac** is not proven (section 2). If a take only opens in the Mac's player, the flow still works, one click longer.
- **Cost in the assistant's reading.** The assistant should show a picture without studying it itself, unless a step needs its eye. The instructions will say so; the saving is not measured.
- **Other stages** (options, master, voices) keep their pages.
- **Several users on one run** answering at once: the server's "one open item" rule decides who is first; the second is told the item is taken. Not designed further.
- The two local fixes from VW-21 (the guide's jobs shown as takes; the checker and the camera drift) are separate and go with the next deployment.

## Built (12 Nov 2026, on SK's word: staged build, one quick review round, no unit tests, no staged deployments; not committed, not deployed)

SK's decisions after the plan: build A, then pictures, then video, in one go; no unit tests and no deployment per stage; a new user run (VW-22) tests it; VW-21 goes its own way. On showing a set, SK asked for my own view: a thing's set is shown as one side-by-side picture with a letter on each candidate **and** each candidate at full size, with buttons "Use A", "Use B", "Use C", "None of these"; a person's set (pictures that belong together) is answered Yes / No / Correct it; free text is always possible.

- `server/app/chat_flow.py`: `next_item` (one decision, or what is being made), `answer` (refuses any item but the one handed out), and one builder of items per step: the treatment (a line), the plan (a gap, or an offered choice), the reference round (an element at step 1, then a set, a set to make), every other thing `waiting()` lists (a question, a picture or sheet, a graphic's steps, a drawing or material spec, a reuse, a take or drawing, with "Take the effect away" where it has a finish), an AI video shot's still on its overlay and its word to shoot, and a gap ready to record. Each answer calls the same server function as the page's button. `sheet_of` makes the lettered picture of a set.
- Routes `POST /visuals/chat/next` and `/visuals/chat/answer`; the tool's `vw visuals next` (it also saves the files to show under `work/chat/` in the run folder) and `vw visuals decide --item --choice --quote --notes`.
- The assistant's instructions: a new section E in the common part (decisions one at a time in the chat, only the question, the fixed sentences about waiting), the treatment and plan passages, and the page taken out of the later steps (`scripts/d188_wording_v3.py`, chained in `c1_split_v3.py`; 10,613 words before, 10,886 after). `plugin/commands/vw.md` and the tool's own messages no longer give a page link for this stage.
- The visuals page answers "the decisions are taken in the chat" to anyone but the administrator.

**The review round** (Claude, by running the new module against a stand-in film, not a test file): the treatment walked line by line to its record; an out-of-turn answer refused by name; "Change this" refused without the operator's words; a sent-back line reported as "with the assistant"; the lettered set picture made and looked at. Everything compiles and the server and the tool load.

**Not verified (no unit tests, by SK's word; VW-22 is the test):**
- The plan, the reference round, the pictures, the specs, the stills, the takes, the word to shoot and the record were written from the page's own action table and **never run**, not even against a stand-in. A wrong field name there shows only in the real run.
- A picture or a take actually appearing in the operator's chat on the Mac, and the buttons as the user sees them.
- An older (not "kept") reference round has no items: its film cannot use the chat for references.
- A set of more than three candidates: buttons for the first three; the others by typed letter.
- Six page mentions remain in the instructions (plan: 3, preparation, picture-search, later: 1 each), none telling the operator to decide there; section E forbids the page.
- The existing unit suites were not run after this change; some of their tests pin the old messages and will fail until updated.
- The waiting lines name a shot by its id, not yet by its gap.

## Deployed

12 Nov 2026, on SK's "fine, let's deploy" (he dropped VW-21 as it stands, so no gating by instruction version was built): main bb4bb93 live as server 0.96.0, plugin 0.82.0 (minimum 0.82.0), with design/187 and the guide checker's drift line. Server and workers restarted with no job running; the chat route answers. Unit suites not run (SK's word). First real use: VW-22.
