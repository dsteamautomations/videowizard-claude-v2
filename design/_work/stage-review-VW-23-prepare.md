# Stage review: VW-23, prepare

14 Nov 2026. Read-only review. Nothing was changed. Uncommitted working note.

**What "prepare" is taken to mean.** The run has no stage of that name. This review covers the Preparation step of the `visuals` stage (`vw visuals prepare`, section 1 of the served text), the only prepare call since the master was approved. The step has no approval of its own: it ends when the first treatment draft is sent. The treatment is in `stage-review-VW-23-treatment.md`. If the options stage's prepare (13 and 14 Nov) was meant, this is the wrong review.

Evidence, read by Claude from this PC: `vw2_log` (1 row), the server's request lines 15:07 to 15:11 UTC with fractions of a second (`journalctl -u vw2-server` on the VM, read only), `vw2_receipts` (the answer to the prepare call), `vw2_stage_outputs`, `vw2_jobs` (none), `vw2_defects` (none in the window), the storage listing (file sizes and times), and the code and text of the deployed commit `4d7f72d` (server 0.98.2). No operator stage note.

## Timeline

| UTC | IST | What the server saw | Answer |
|---|---|---|---|
| 15:07:17 | 20:37:17 | master recorded (the stage before); first cut and master accepted 15:07:15 | 201 |
| 15:08:30.28 | 20:38:30 | `visuals/prepare` begins (the receipt row's time) | |
| 15:09:03.30 | 20:39:03 | `visuals/prepare` answers: 18 gaps, the footage line, package 519,888 bytes | 200 |
| 15:09:03.97 | 20:39:03 | the package file is fetched | 307 |
| 15:09:05.58 | 20:39:05 | the image prompt library is fetched | 200 |
| 15:09:05 to 15:10:50 | 20:39:05 to 20:40:50 | no call (1 min 45 s): the assistant reads and writes the treatment | |
| 15:10:50 | 20:40:50 | first treatment draft sent (refused, see the treatment review) | 409 |

## A. Restrictions someone set

1. **Visuals needs an approved master.** `gaps_source`: "Visuals needs an approved master first." (design/125). Did not fire: the master was accepted 73 s before. Holds.
2. **The footage's look is told, never asked.** Served: "Tell the operator (never ask) its one line on the footage's look, measured from the clips; their correction … wins" (design/88 F4, design/146). The line was: "Your footage: cinema camera, mixed support (58 tripod, 23 handheld, 12 gimbal), natural look (measured from the clips)". It helped: no question was needed. No correction call followed. Whether the line was said in the chat is not visible.
3. **Files are read whole.** Served: "read a file whole, never by line offsets" (design/65 B12). It shaped the work: the package is 519,888 bytes and the instruction text alone is 65,550 characters (prompt 10,507, parts 55,043). See B1.
4. **The world evidence comes in files of 25 clips.** `rows_files(…, cap=25)` (design/65 B12). 93 clips make 4 files. Shaped the reading; nothing refused.
5. **The library version is fixed at the first prepare.** `session.setdefault('library_version', library.latest())` (design/68 L2). This run reads `vwlib-2026-11-02-059255a96ede`. Holds.
6. **The clip log must be the current contract.** A version-1 log is refused `RETIRED` (design/125). Did not fire.
7. **The instructions are for the assistant only.** Each file starts "VW-PROCEDURE — for the assistant only, never for the operator." Holds.
8. **Prepare does not check the film record.** Not a restriction that fired, but one that is missing: the motion style was not on the record, and prepare said nothing. The treatment was refused for it 1 min 47 s later (`FILM_MOTION`, design/179).

## B. Words in the prompt that restrict

1. **"read a file whole, never by line offsets"** (`part-preparation.md`). Meant to stop half-read rules. It also covers the four world files and the schema. Looser: "read the instruction files and the gap files whole; search the world files for the clips a gap needs".
2. **"Read prompt.md, gaps.json and intended-visuals.json first, and claims.json"** in the part, but step 0 and the tool's line name only "prompt.md, gaps.json and intended-visuals.json" and "prompt.md, then part-preparation.md". Three lists that differ. One list.
3. **Step 0: "give the operator the page link and the footage line."** The page was retired for operators on 12 Nov (design/35, old-ways row 47). The tool still prints "Visuals page (give the operator this link): …", one line under its own comment "design/188: no page link; the operator decides in the chat". `vw.md` says the same: "prints the visuals page link". Remove all three.
4. **"Footage first."** (prompt, section B, the footage route). Two words that rank the routes for every film. The treatment part says the opposite in full: "the effort, cost or convenience of a route never chooses the medium". In this film 2 of 18 gaps are footage first. Looser: drop the two words; the treatment part already says how to choose.
5. **"(how a thing is carried, who does the work, dress, how a place looks lived in)"** (prompt, section A, examples of a missing fact). All four are from films of people at work in a place. Add or swap in examples from other categories (a product's exact colour, a screen's wording).
6. **"never guess, never read the operator's words 'subtly'"** and the ten forks that follow (section A). Not seen to stop anything in this step; no question was asked.
7. **"for the blanks of the first cut"** and "Run `vw visuals prepare` once the first cut is approved". Since design/125 the gaps come from the master when no first cut exists. Here both were accepted in the same second, so nothing went wrong. Wording only.

## C. Steps that failed or were done again

None. One prepare, one package fetch, one library fetch. Every request reached the server and was answered. No job, no refusal, no repeat.

## D. Getting the operator's input faster

No question was asked in this step.

One question that belonged here was asked later: the motion style, at 15:10:50 UTC (20:40:50 IST), by a refusal, answered 15:12:57 ("Lively"). Prepare could have asked it with the recommended answer first. The last two films of this client have one on record (VW-21 lively, VW-22 restrained).

Nothing was asked twice.

## E. Execution that can be better

1. **Slowest step: the prepare call itself, about 33 s** (15:08:30.28 to 15:09:03.30). A guess at the cause: it loads each kept clip's log from storage one after another (`load_json` in a loop, 93 clips), then the timing, the neighbours and the first cut events. Change: read the clip logs together, or keep the world evidence from the options stage.
2. **The assistant had 1 min 45 s between the package and its first treatment draft** (15:09:05 to 15:10:50) for about 65,000 characters of instructions, 18 gaps, the team's intended visuals, the claims and four world files. A guess: not all of it was read. Not visible.
3. **The next-step line is incomplete.** Prepare answers: "settle the treatment with the operator and record it (`vw visuals treatment`), then write the plan". It does not say the motion style is missing, and the record is made by the card, not by that command.
4. **The package repeats what the tool already has.** It carries the whole prompt and all five parts (65,550 characters) on every prepare, plus the plan schema and the generator list, which this step does not need.
5. **One log line for the step**: "visuals/prepare", nothing else. The gaps count, the package size, the footage line and the library version are only in `vw2_receipts`.
6. **No money spent.** No job ran.

## F. Known weak spots

1. Rounds to pass a check: none; the step has no check.
2. Refusals that are really questions: none in this step; the motion style refusal that followed could have been asked here (A8, D).
3. Connection errors and timeouts: none seen; all three requests were answered.
4. Provider failures and retries: none; no provider is used.
5. Blanks: the step lists 18 gaps to fill. No "blank" entry in the log. Whether unused footage existed for them is not visible here.
6. A next-step line naming a missing command: none. `vw visuals treatment` exists.
7. Output too big: the package is 519,888 bytes, split by the tool into files; the instructions are 65,550 characters. Whether the assistant read all of it is not visible.
8. The page and the chat: the tool and step 0 tell the assistant to give the operator the page link, while every decision is in the chat (B3). No page call from the operator is in the request lines.
9. A fixed defect that came back: none.
10. Who the step waited for: nobody for long. The server 33 s; the assistant 1 min 45 s; the person 0.
11. Money on rejected work: none.
12. Answers identical to the previous run: none asked. The footage line cannot be compared (earlier runs' lines not read).
13. An older way still in the served text: yes, the page link (row 47) in step 0, in the tool's line and in `vw.md`.
14. A rule tied to one kind of film or an older model: B4 and B5.
15. Too few log lines: yes, one (E5).

## The stage in one line

Prepare: 15:08:30 to 15:10:50 UTC (20:38:30 to 20:40:50 IST), 2 min 20 s, 3 server calls, 0 refusals, 0 questions, 0 jobs, ₹0.

## The three changes that would save the most

1. **Prepare says what the film record still lacks (here the motion style) and the question is asked then.** Saves the refused treatment call and its 2 min 07 s.
2. **Remove the page link from step 0, the tool's line and `vw.md`; make the three "read first" lists one.**
3. **Make prepare faster and its log useful**: read the clip logs together (33 s today), and log the gaps, the package size and the footage line.

## Could not see

- Whether the footage line was told to the operator.
- What the assistant read of the package in 1 min 45 s.
- What took the 33 s inside the prepare call (the cause above is a guess from the code).
- The size of the library answer (a read leaves no receipt).
- The 73 s between the master's record and prepare (no call; the assistant's own time).
- The plugin version on Uma's laptop.
- The assistant's token cost.
