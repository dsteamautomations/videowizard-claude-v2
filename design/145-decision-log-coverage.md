# design/145: the decision log covers the pages, the background work and the visuals plan (3 Nov 2026; SK: "yes go ahead, and ask for my approval during deployment")

From VW-18's live log (the first run on design/142's log): the chat tool's steps, refusals and the analysis were logged, but four gaps showed. **Server only: no plugin update** (SK asked).

## Requirements

**L1. Page actions.** Every button on the voices, visuals and review pages (`/runs/<code>/voices2/act`, `/visuals/act`, `/review/act`) is one entry:
- the page and the action;
- what it was about (picture, shot, slide, voice, job);
- the operator's words when there are any;
- the server's answer, or its refusal.

This is the same middleware as design/142 R1, with the run found by its code. It also gives the **master stage its log**: every answer on the review page (keep, reject or trim, with its note) is an entry, beside `vw master decide` from chat.

**L2. Background results.** When a job ends (a narration, an audition, a picture, a take, a render, a check), `jobs.finish` writes one entry:
- the job's kind and name, and its outcome (ready, failed, rejected);
- the error, if any;
- the facts the result carries: the check's verdict on a picture and the marks Gemini found on a take, when present.

A retry in progress is not an entry. A clip that the analysis kept stays logged at record, with its details (design/142); an analysis failure is now logged too.

**L3. The visuals plan's reasons.** When the plan is proposed, each gap is one entry: the choice taken (when the gap offers choices), and each shot with its route (footage, still, AI video, drawn, sequence) and its stated purpose. It is copied from the plan, as design/142 R2 copies the first cut's reasons. Nothing new is required of the plan, so no wording or plugin change is needed.

**L4. Noise and names.**
- The file upload steps (sign and receipt per file: 104 entries on VW-18) are no longer entries. The media record says what was uploaded.
- A step outside a stage (a defect filed, a job claimed) is logged under "run", not as a stage called "defects" or "claim".

## Edge cases

| Case | Handling |
| --- | --- |
| A page action refused (409, 422) | logged as a refusal with its message, like the chat tool's |
| A page post with no recognised run code | not logged (no run to attach it to) |
| A job ending twice (a recovered job) | each ending is an entry; that is what happened |
| The log write fails | the step still succeeds; the server's journal notes it (design/142) |
| A plan with hundreds of shots | one entry per gap, so the log stays readable |

## Tests

1. A page action becomes an entry with its run, its stage and the operator's words.
2. A refused page action is logged as a refusal.
3. A file sign or receipt is not logged.
4. "defects" and "claim" are logged as "run".
5. `jobs.finish` logs a final outcome and skips a retry.
6. A proposed plan writes one entry per gap, with its routes and purposes.

## Not covered
- **Why the operator chose** on a page beyond the note they typed. A click carries no reason unless they gave one.
- Claude's own judgement entries (`vw log`): whether the assistant writes them is checked on VW-18's first cut, not by code.
