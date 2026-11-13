# Stage review: the prompt, and where else to look

13 Nov 2026. Uncommitted working note. Nothing here changes the application.

## 1. The prompt (paste to the builder after each stage)

Replace the two words in capitals. Everything else stays as it is.

```
Stage review. Run: RUN-CODE. Stage just finished: STAGE.

Review this one stage only, from the first server call of the stage to its
approval. You only read: no fix, no deploy, no change to a row or to the run.

Evidence to read, in this order:
1. vw2_log for this run and stage: every step, refusal, blank, choice,
   decision and result, with its rule and its time.
2. The server's request lines (journalctl -u vw2-server) for the same window:
   what was called, how many times, with which answer code, and the gaps
   between calls.
3. vw2_jobs for this run and stage: provider, status, attempt, error, cost,
   time from created to finished.
4. vw2_defects raised in the window.
5. For every refusal or repeat you found: the text that caused it. The check
   in server/app, the instruction the server served for the step, and the
   plugin's skill or operator-CLAUDE.md line. Quote the exact words.
6. The operator's stage note, if I paste one below.

Report these five lists. Each item: what happened, the time (UTC and IST),
how many times, the evidence, the cost in minutes or rupees where you can
measure it, and one proposed change.

A. Restrictions someone set. Every rule, gate, limit or fixed order that
   fired in this stage. For each: who set it and when (design note number or
   commit), whether its reason still holds today, and whether it helped or
   only slowed this stage. Include restrictions that did not refuse anything
   but shaped the work (a cap, a fixed count, a required field).

B. Words in a prompt that restrict. Any word or sentence in the instruction
   or prompt served for this stage that narrowed the result more than the
   rule needs: "never", "only", "must", "exactly", a fixed number, a named
   example from an older film, a category-specific word. Quote it, say what
   it stopped, and give the looser wording.

C. Steps that failed or were done again. Every refusal, rejected check,
   failed or retried job, and every call repeated with the same purpose.
   For each: the cause, and one label: our rule / our instruction was unclear
   / the assistant's mistake / a provider / the server / the operator's
   computer or connection / the operator changed their mind. Say whether the
   request reached the server. If a rule caused it, name the rule.

D. Getting the operator's input faster. List every question the operator
   was asked in this stage, in order, with the wait before each answer.
   Then mark each one: could be clubbed with another question; could be
   predicted from the brief, the client record or an earlier run; could be
   offered as ready answers to click or copy; could be dropped. Also list
   anything asked twice.

E. Execution that can be better. The slowest steps, waiting with nothing
   running, work done one after another that could run together, output too
   large to read, a next-step line that was wrong or unclear, money spent on
   work that was thrown away.

F. Known weak spots. Check each one for this stage and answer it in one
   line, "none seen" included:
   1. Rounds to pass a check: how many rejections before it passed, and
      what the assistant could have been told beforehand.
   2. Refusals that are really questions (an approval or a choice missing):
      could each have been asked earlier with a recommended answer?
   3. Connection errors and timeouts: did the request reach the server?
   4. Provider failures and retries: which provider, how many attempts.
   5. Blanks: parts of the film left without real footage ("blank" entries):
      how many, and whether unused footage existed for them.
   6. A next-step line naming a command or option the installed plugin
      does not have.
   7. Output too big for the assistant to read.
   8. The page and the chat disagreeing, or the same thing asked in both.
   9. A defect marked fixed that came back.
   10. Who the stage waited for: the person or the machine, in minutes.
   11. Money spent on work that was rejected or replaced.
   12. Answers identical to the previous run: candidates for a default.
   13. An older way kept in design/35 that is still in the served text.
   14. A rule tied to one kind of film or to an older model.
   15. Too few log lines to tell what happened in the stage.

End with:
- The stage in one line: start, end, minutes, server calls, refusals,
  questions asked, jobs run, cost.
- The three changes that would save the most, in order.
- "Could not see": what the server and database do not show for this stage.

Rules for the report: plain short sentences; state only what the evidence
shows and mark a guess as a guess; no item without a time or a quote; save
it as design/_work/stage-review-RUN-CODE-STAGE.md and give me the summary
in the chat. Do not start any fix. I decide after reading.
```

## 2. The operator's stage note (Uma pastes this to her assistant at the end of each stage)

The server sees only the calls that reach it. What happened inside the operator's chat is invisible to the builder, so this short note fills the gap.

```
Stage note for the builder. Stage just finished: STAGE. Do not call the
server for this. From this conversation only, list:
1. Every vw command you ran more than once, and why.
2. Every refusal or error you got, in the server's exact words.
3. Every question you asked me, in order, and whether my answer was
   something you could have guessed.
4. Anything in your instructions that stopped you doing what I wanted, with
   the exact words.
5. Anything you did that never reached the server: files rewritten, waits,
   connection errors.
Short lines, no opinions. Save it as out/stage-note-STAGE.md.
```

## 3. Other areas worth looking at

From the 50 defects raised so far and from VW-22's own log. Each is something the five lists above may miss unless it is looked for.

| # | Area | What the history shows |
|---|------|------------------------|
| 1 | Rounds to pass a check | VW-22 visuals: `visuals/check` rejected 6 times, the first with 27 things to fix. Options check and master build also refused once each. Defect 46: every key name tried was refused. The assistant learns the contract by being refused. |
| 2 | Order gates that are really questions | `SCENES_NOT_APPROVED`, `FILM_MOTION` (no motion style yet), `LIBRARY_REPEATS` (45 clips). Each refusal is a question that could have been asked earlier, with a recommended answer. |
| 3 | Connection and timeouts | Defects 18, 22, 23, 41, 50. Each cost two waits of three minutes and a defect. Defect 50 was the operator's own internet; the calls never arrived. |
| 4 | Provider failures and retries | Defects 16, 40, 42, 43, 44, 45, 48. Look at `attempt`, rejected and failed jobs per stage, and at which provider. |
| 5 | Blanks left without footage | VW-22 options: 14 "blank" entries. A blank is a part of the film left for AI video or graphics, not a failed search (corrected 13 Nov; I first misread it). Worth asking each time whether unused footage existed. |
| 6 | Next-step line against the installed plugin | Defects 24, 25, 32, 34. The server named a command or an image AI that the operator's plugin did not have. |
| 7 | Output too big for the assistant to read | Defects 17, 21. Check the size of what each step prints. |
| 8 | The page and the chat disagree | Defects 20, 28, 29, 30. The operator answered on the page and the answer did not reach the assistant. Now that visuals decisions are in the chat (design/188), check that nothing is still asked in both places. |
| 9 | A fix marked fixed that came back | Defects 25 and 36. After each deploy, re-run the exact failing step before closing the defect. |
| 10 | Who the stage waited for | In the request lines, the gap before an answer is the person; the gap after it is the machine. VW-22 visuals has run from 12 Nov 16:43 UTC to now; most of that is not server time. |
| 11 | Money spent on rejected work | `vw2_jobs.cost` for jobs that ended rejected or were replaced. 5 rejected jobs in the last three days. |
| 12 | Answers that are the same every run | VW-21 and VW-22 are the same owner, the same route, the same image AI. Any answer that was identical in both is a default waiting to be set. |
| 13 | Older ways still in the text | design/35 lists ways kept "until …". A kept older way that is still in the served instruction is a restriction nobody chose today. |
| 14 | Rules written for one kind of film or an older model | SK's rule of 2 Nov: generic, or filed by category, and written for today's models. Look for a brick, a mason or a documentary word in a rule that every film gets. |
| 15 | Stages with no trace | Brief, script and intake show 1 or 2 log lines and no questions. Either they are smooth or the log does not record what happened there. Worth one check. |

## 4. What the builder cannot see

- The operator's chat: retries, rewrites and waits that made no server call. The stage note in section 2 covers this.
- Why the operator took time to answer.
- Blender, HyperFrames or DaVinci work done on the operator's computer, except the calls it makes to the server.
