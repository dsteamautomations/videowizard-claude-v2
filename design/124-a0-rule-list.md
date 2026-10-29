# 124 — Phase A0: the rule list (29 Oct 2026)

Every rule that steers the visuals stage, in one numbered list: `design/124-a0-rule-list.csv` (opens in Excel; one row per rule). **Nothing was changed**; this list is the safety net for phases A1–A4, B and C of design/124.

Built by five helpers working at the same time, one per place where rules live; each copied the old wording word for word and a script checked it (all rows found in their source; 38 rows from the server's code are text the code assembles from several pieces).

## Columns
`id` (R0001…), `source` (where it lives), `place` (section / step / file and line), `phase`, `topic`, `rule` (one plain line), `old_text` (the exact wording), `kind` (rule, number, command, flow), `checked` (for written rules: does the server also refuse, warn or write it), `labels` (change-history labels in it), `flag` (outdated?, contradicts?, duplicate?, misfires?, changes-with-design/122).

## How many rules, and where

| Where the rule lives | Rules | What it is |
|---|---|---|
| Main guide (the stage's instructions, sections 0–8) | 368 | read by the assistant |
| Step list (the stage's numbered steps) | 342 | read by the assistant |
| Server checks | 423 | code: 362 refuse, 61 warn |
| Prompt-writing guide (the library) | 883 | read by the assistant when it writes picture and video requests |
| Lines the server adds to requests and checklists | 234 | sent to the picture/video AI and the picture check |
| "What next" messages from the server and the chat tool | 103 | read by the assistant |
| **Total** | **2,353** | |

By phase: shot pictures 707 · plan 465 · videos 341 · common 254 · review and record 197 · reference sheet and golden picture 162 · picture search 114 · treatment 62 · preparation 21 · other 30.

Of the 581 rules in the stage's written instructions (guide + steps, kind rule or number): 176 are also refused by the server, 80 warned, 89 written by the server itself, 212 not checked, 24 unsure. So **345 written rules (about 6 in 10) are already enforced or written by the server**: candidates for one line each in Phase B.

## What the helpers flagged (for phases A1–A4)

| Flag | Rows | Goes to |
|---|---|---|
| change-history labels inside the wording | 441 rows | A1 |
| outdated? | 45 (18 of them "refused from the next release" warnings that never became refusals) | A2 |
| changes-with-design/122 (the ₹ spending limit; still live today, removed when design/122 is built) | 17 | with design/122 |
| contradicts? | 99 | A3 / A4 |
| duplicate? | 83 | A3 / Phase B |
| misfires? (written for one situation, applies to all) | 81 | Work item 7 / Phase B |

Flags are the helpers' first reading, to be confirmed one by one in each phase; they are not decisions.

## The most serious findings, in plain words

**Rules that clash with each other**
1. "Text is not a reason to choose or avoid a way of making a picture" — while the server refuses an AI graphic with exact sizes or numbers and makes the drawn diagram the rule for them.
2. "Write every label and number in the picture request exactly" — while another rule refuses quoted words in a picture request (labels go through the "exact text" box instead).
3. The picture check's fixed line "no readable text unless the request asked for exact text" — while every reference sheet is told to label its views: a labelled sheet can fail its own check.
4. The line "not on a plain background, not an object alone" is added to pictures that are meant to be the object alone on plain ground (golden pictures, reference pictures).
5. The golden picture: "a client's own object sends its footage frame here and never again" — while the server refuses a later picture of it without that frame.
6. The operator's yes to a web size figure: asked per drawing in one place, "one yes covers every drawing of the run" in another.

**The prompt-writing guide against the server**
7. The guide says to open a form file the server never sends (it sends the VideoWizard version of it).
8. The video guides ask for sound, dialogue, timed cuts and each model's own prompt shape; the server always builds one prompt shape and adds "no dialogue, no music, no captions".
9. A guide template writes the video model's name into the prompt; the server refuses model names in prompts.
10. One guide file recommends "8K", "hyper-realistic" and naming studios as styles; other guide files forbid exactly these.
11. Several guide files prescribe low-quality drafts; another guide file and the server say no low-size drafts (the server uses high quality).

**Out of date**
12. "Four ways make a picture" (there are five; drawn diagrams); "arrows that travel are not available in this release".
13. A start and an end picture for every video ("segments plus one", "three segments need four images"); since design/112 a video takes a start picture only, an end only where it must be exact. Also in the server's own next-step messages and one check that asks for notes about "the two pictures".
14. 18 warnings that say "refused from the next release" and never were; one of them can no longer fire because the same thing is already refused.
15. Messages still say "paid OpenAI image" though the picture AI is chosen per film (design/120).
16. The server's "what next" after preparation says "write the plan" while the instructions say "treatment first" (design/124 Change 1).

## How this list is used
- **A1–A4:** each phase filters this list by flag (labels, outdated, contradicts, other voices) and brings SK the rows that need a decision.
- **Phase B:** for each reviewed phase, the rows of that phase are the trace table's "old" column: every row must land in the new text or be removed with SK's yes.
- **Phase C:** the trial run and the new version are checked against it.
