# Codex review prompt for VideoWizard v2: the process

Built on 2 Nov 2026 from SK's self-review prompt (`124-c4-review-prompt.md`, revised twice: design/124-c5, then SK's additions of 30 Oct). Second round, 2 Nov (SK: "a focused review on the process"): only the checks on the film-making process are kept; the code-hygiene checks are removed (see the end of this file).

Paste everything between the lines into Codex, at the root of the `videowizard-v2` repository.

---

```
You are reviewing the FILM-MAKING PROCESS of one small product, by reading its instructions, its server steps and its decision notes. Your job is to find where the process loses quality, time or money, and report it. You change nothing.

WHAT THIS PRODUCT IS (so you size your advice to it)
- VideoWizard v2 turns a script and raw footage into a finished explainer film, stage by stage: the brief, the script, the voice, the media, the footage analysis, the options (the first cut), the master, the visuals (treatment, plan, reference pictures, shot pictures, video takes, record), then assembly. A handful of operators in one company use it.
- At each step the operator's AI (Claude Code) follows instructions and runs the `vw` tool; the server checks what it sends, calls AI providers for pictures, videos and checks, and says what comes next; the operator approves or rejects on two web pages.
- Where the process lives:
  - server/procedures/v3.json : the instructions the operator's AI reads, one part per step.
  - server/library/ (read by server/app/library.py) : the prompt-writing guides those steps read.
  - server/app/visuals_stage.py, server/app/visual_contract.py, server/app/stage2/, server/app/core.py : the server steps, their checks, their "what next" messages, and the text the server adds to AI requests.
  - server/app/video_providers.py : the text sent to the video model.
  - plugin/scripts/vw.py : the commands the operator's AI runs.
  - design/ : the decisions. Read CLAUDE.md, design/35-decision-log.md, design/126-flow-review-vw12.md and design/129-pending-requirements-1-nov.md first. Do not raise anything they already decided or parked.

HARD LIMITS (breaking any of these wastes the review)
1. Read only. Do not edit, create, move or delete any file except your one report file (see OUTPUT). Do not commit. Do not run any program or test: this is a reading review.
2. No network. Do not open server/.env or any file with keys.
3. Stay on the process. NOT WANTED, never a finding: code structure, style, naming, tests, typing, linting, refactors, dependencies, performance tuning, request formats, file size limits, web page wiring, deployment, versions, security hardening, authentication, secrets, rate limiting, logging, monitoring, CI/CD, containers, scaling, compliance, or more abstraction. The owner wants the cheapest control that works and no enterprise guardrails.
   The one exception: a concrete bug that loses an operator's approved work or leaks a key into a message. Report it in one line, with the file and line.
4. Every finding needs evidence: the file and line (or the instruction part and its words), and the film situation in which it goes wrong. No "could potentially", no "consider". Say "read" for what you traced in the text and the code.
5. Every fix is the smallest one: a shorter or clearer instruction, one server message changed, one check moved, a step removed. Any rewording shows the word count before and after; the text must get shorter or stay the same. No new step, tool or service unless nothing else works.
6. Do not add checks for rare edge cases. Better means simpler, or fewer steps.
7. Do the tasks below in order. When a task finds nothing, write "nothing found" in one line. Stop after the last task.

THE TASKS
P1. The map. From v3.json and the server steps, list every stage and its steps in order. For each step: who acts (the operator's AI, the server, an AI provider, the operator), what it receives, what it hands to the next step, and the server check that guards it. One table, one line per step. This is your base for the other tasks; keep it short.
P2. Handoffs. Find what one step produces that a later step needs but never receives, receives under another name or in another form, or has to work out again. Find steps that redo work an earlier step already did.
P3. Instructions against the server. Find where v3.json tells the AI one thing and the server checks, adds or says another, including the server's "what next" messages and the lines it adds to picture and video requests. Find topics written twice (in v3.json, or in v3.json and a guide) that say different things, and say which copy the server enforces. Find rules about features that no longer exist, change-history labels left inside text the AI reads (for example "design/91 N3" inside an instruction), and long instructions for something the server already refuses in one line.
P4. Prompts that write prompts. Where a step's instructions make the AI write a prompt for another AI (a picture, a video, a check), or the server builds one, find text that is unclear, contradicts itself, or contradicts the plan data it comes from. Quote the lines that disagree and show the fixed wording.
P5. Too much input. For each AI step, what goes into one request (instructions, guide files, past results)? Name the requests that load a whole guide when the step uses one part, or load many separate things together, with their sizes in words.
P6. Too many decisions at once. Name the places where one AI answer must get many choices right together (for example every shot of a plan, or every scene of a cut), with the count. Say whether a second pass by unit (one shot, one scene) exists, and where one is worth adding.
P7. Blocks. List the decisions and server refusals that stop the operator or the AI from a choice that would make a better film (not the ones that protect approved work or money). For each: the message, where it is, what it takes away, and keep, loosen or remove.
P8. Dead ends and loops. Find steps where:
  - a refusal does not say what to do next, or names a command that no longer exists;
  - the AI must remember a rule the server neither enforces nor tells it at that moment;
  - a small correction forces approved work to be done or approved again (for example a change that un-accepts every gap);
  - the server changes the operator's text before it checks it, so the check cannot pass;
  - an AI provider call's answer limit or expected answer shape makes the step fail on a normal film.
P9. Old and new ways side by side. Find steps that can still be done an older way beside the newer one: code or text kept "for old films", "for one release", or for one named run (VW-11, VW-12), and old names that still work. design/35 lists the ones already decided: report only ones it does not list.
P10. Cost and time. For each step that calls an AI provider: how many calls a typical film makes (from the code's counts and the prices in server/app/config.py), and where calls that could run at the same time run one after another. Name the three steps that cost the most and the three that take the longest.

OUTPUT
Write one file, codex-review/process-findings.md, and nothing else. It holds:
1. A summary for the owner, who is not technical: at most 10 lines of plain English. What is most likely to hurt a film next, and what to fix first. No code words; if one cannot be avoided, explain it.
2. The map from P1.
3. One table of findings, most harmful first, at most 30 rows. Columns: # | task (P2..P10) | stage and step | what goes wrong, in plain words | evidence (file:line or instruction part and words) | when it happens (the film situation) | smallest fix | effort (S under 1 hour, M a day, L more) | confidence (high or medium; leave out anything low).
4. One line per task that found nothing.
5. What you assumed without checking, as a short list.
Do not add a roadmap, a score, an architecture diagram or general advice.
```

---

## Second round (2 Nov): what was removed, and why

| Removed check | Why it is out of scope for the reviewing agent |
|---|---|
| The whole-path contract (request fields, request ids) | a code check, not the process |
| Tests that check pieces, not paths | about the test suite, not the process |
| Size limits and assumed fields | a code check; the one that stops a step on a normal film stays, inside P8 |
| Errors the operator sees, in general | kept only where the process dead-ends (P8) |
| Web page wiring and Jinja traps | the pages' code, not the process |
| Dead and diverging code | code hygiene |
| Versions and deploy | operations, not the process |
| Running the test suites | a reading review needs none; it costs time and tokens |

**Added in this round:** P1 (the map of the whole process, the base for the rest), P2 (handoffs between steps) and P8 (dead ends and loops), all on the process. The self-review's cost and time point (10) is P10.

**Still left out on purpose:** following a live run and judging film quality. The reviewing agent can't see the live data or ask SK questions, so that stays with our own review.
