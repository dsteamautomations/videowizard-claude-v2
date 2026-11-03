# design/147: the brand-generic library, build list (3 Nov 2026, for SK's approval; SK: "We need to build this and dont deploy until i confirm")

Sources: design/140 part 1 (the requirement), part 2 (the hidden requirements and SK's eight answers of 3 Nov). Video only (Q1). Server, plugin and instructions. **Not deployed until SK confirms.**

## What will change, in plain words

1. **A library table per client** (`vw2_library`, migration 013). One row per file per client: its name, Gemini's short description (the descriptive name, the overview, the summary-card lines, the names it saw), whether it is marked brand-generic, the films it came with, where its media and its full Gemini log are kept, its frame fingerprints, and who marked it with their words. Keyed by the client, never by who made the film (part 2, B1 to B8).

2. **The marking question, between the study and the first cut** (A1 to A7). After every clip is studied, Claude reads each clip's short description (never the full log), shortlists the ones that would read true in any film of this client (premises, products, logo shots, staff at work, establishing shots; never a dated event, a named person speaking about this topic, a one-off site state), and asks with the question tool: which to mark, "Other" for files it did not suggest, "none" allowed. The answer is recorded with the operator's words (`vw library mark --generic <names> --quote`). Every studied clip of the batch is stored, generic or not (B4); an excluded clip with a description may be marked (Q5). The first cut's prepare is refused on a new film until the answer is recorded; films started before this release skip it (old ways). Unmark and re-mark: `vw library unmark --clip <name> --quote`, by any team member on that client (Q8); a film that already placed the clip keeps it.

3. **A repeated clip is caught before the paid study** (Q2, C1 to C4).
   - At media prepare, the batch's file fingerprints are checked against the client's library: an exact repeat is listed with the film it came with.
   - At analysis start, before any paid request, the server takes frame fingerprints of each new clip (the look-alike tool already in the code) and lists near repeats against the library.
   - The operator decides once for the list: analyse them anyway, or skip them. A skipped clip is left out of this film's batch and is offered from the library in the library round instead. Nothing is dropped silently.

4. **The library round, after the second look** (Q3, Q4, Q6; D1 to E10). `vw options library` gives Claude the client's generic clips that this film can use: each re-checked for eligibility and crops under this film's own rules and shape (the solver, no paid call), the batch's own files left out. Claude matches them to the remaining blanks from the description and free stills, and proposes:
   - a gap proposal: a shot marked `library` (Keep takes it, Reject leaves the blank);
   - a swap: the library clip as the shot, the current clip as its alternative, with a stated reason (Reject brings the current clip back).
   Proposals carry `match: library` with the description as evidence; the first cut's check accepts them; the review page shows "library · from VW-12". A proposal the operator rejected is not offered again on that film. Every server rule applies unchanged (each clip once, no B-roll into a claim, sizes, lighting, screen direction, usable window).

5. **Library clips play and ship like any clip** (E8, E10). The seven places that read a clip from the film's own folder read a library clip from its source film's folder instead; the file route lets a film of the same client fetch it; the editor's package lists library originals with their source film.

6. **The instructions** (the options steps in version 3, the analysis step, `vw.md`) say when to ask, how to shortlist, and how the library round is run.

## Edge cases and failure modes
As listed in design/140 part 2 (sections 3 to 8), with these settled by the answers: duplicates before the study; excluded-but-studied clips may be marked; the library starts empty (Q7); matching is free (Q4).

Added here:
- **A client's first film** has no library: the marking question still runs; the duplicate check and the library round say "no library yet" in one line and pass.
- **The library read fails at options:** the first cut carries on with the film's own clips and says the library round could not run; it never blocks the film.
- **A library clip whose media is gone** (a deleted run): marked missing, never proposed.
- **A run with no client:** nothing stored; the question is skipped with one line.

## Tests (first, per step)
1. The table and the mark/unmark step: stored with the words; unmark reversible; a film that placed the clip keeps it; no client → skipped.
2. The gate: a new film's options prepare refused until marked; an older film passes.
3. Exact repeat at media prepare; near repeat at analysis start; the one answer (keep or skip); a skipped clip excluded and later offered.
4. The library round: eligibility re-solved under the new film's policy and shape; the batch's own sha left out; a rejected proposal not offered again; `match: library` accepted by the check; the slides say the source film.
5. Media readers take a library key; the file route allows a same-client key and refuses another client's.
6. Wording tests.

## Older ways (design/35)
- Films started before this release (film NULL): no marking question, no library round, no duplicate check; they can be backfilled later as a task (Q7).

## Not covered
- Images (a later change on the same library).
- A page for the marking question (the chat question tool is the UI, as part 1 says).
- How long a closed client's library is kept.
- The paid re-study of library clips (Q4 chose free matching).

## Order of work
1. The table, the mark and unmark steps, the gate, `vw library`.
2. The duplicate checks at media prepare and analysis start.
3. Library clips readable from their source film (readers, file route, delivery).
4. The library round: candidates, the package rows, proposals, the check, the slides and page.
5. Instructions, tests across, versions (server 0.87.0, plugin 0.73.0), commit. No deploy.
