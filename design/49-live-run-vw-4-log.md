# 49 — Live run VW-4 (VK Nardep, 18 Oct 2026): timings, observations, candidate changes

SK drives the operator's assistant in the operator folder; the builder watches the child's transcript, the server's records and the run folder, and logs here. Times are UTC from the transcript; "child" is the assistant's own time between the tool call and its message; SK's gaps are left out. Server 0.15.0, plugin 0.14.0.

## Timings

| Stage | Step | Server | Child | Notes |
|---|---|---|---|---|
| start | `vw start` (directory check, run created, client history) | 4 s | — | first try refused: "VK nrdep" matches nothing; `vw clients --search VK` found one; SK confirmed |
| intake | prepare (extract, number) | 1 s | — | 131 lines |
| intake | proposal written and presented | — | 52 s | 79 removals, 34 narration paragraphs kept |
| intake | record | 4 s | — | source.txt 4,787 bytes to storage |
| brief | prepare | 1 s | — | last brief (VW-3) and no client rules |
| brief | proposal written and presented | — | 48 s | five decisions, four production questions, nine chapters |

## Observations

- 13:16:36 the child's first act was a shell `ls` of the runs folder; the guard refused it and logged it (into VW-3's guard log, the active run at that moment). First live block of the hook.
- The pasted script was saved by the child with Write into `in/source.txt` (inside the run folder, allowed). No `--script` path, so no "allowed" line in the guard log for it.
- Intake: removals are all scaffolding (title, durations, scene headings, labels, visual notes); nothing spoken touched; blank lines kept. The child summarised the 41 visual notes with examples instead of listing each (the step says each); harmless here.
- Intake titles: the recommended title repeats the document's own title and drops the deliverable, against the prompt's "subject and deliverable" rule. SK chose it.
- Brief: grounded decisions, audience labelled a recommendation, no call to action added, the four production values offered as last time's answers and asked once. The chapters proposed are the nine narrative scenes; VW-3 used nine construction steps. Chapters tag every clip at analysis and map scenes at options, so they must be things the camera can see.
- The document's "Suggested Duration: 5–6 Minutes" was removed at intake as timing and the brief cannot see it; target length falls back to the narration (about 800 words, so near 5–6 min anyway).

## Candidate changes (not built; batched at stage boundaries or after the run)

| # | Candidate | Why | Size |
|---|---|---|---|
| L1 | Intake preview: a `vw stage intake preview` that applies out/intake.json and writes `work/intake-preview.txt` (the kept lines) for SK to read before approving | the cleaned script is only written at record; the check SK needs is "does the kept text read as complete narration" | small, plugin only |
| L2 | Intake carries removed `timing` lines (the document's stated duration) into the brief prepare output as a hint for target length | the document's duration is lost today | small, server + plugin |
| L3 | Brief prompt: trim the sentences that only forbid v1 behaviours ("do not recreate ten mandatory fields…") | dead text; attention cost | text only |
| L4 | Brief step: say that chapters are what the footage shows (process steps), not the script's outline | the child proposed narrative scenes on a repeat client whose last brief used construction steps | text only |
| ~~L5~~ | Withdrawn by SK: the film runs as long as the script; no hard target. (Was: target length reaches the script stage: `script_prepare` passes `target_runtime_s` and the script prompt fits the words to it (about 2.5 words a second) | today the target reaches analysis and the options check but never the wording pass, so a short-form target cannot shorten the narration | small, plugin + prompt |
| ~~L6~~ | Withdrawn: the script stage is a wording pass that fixes brief misfits, not a rewrite; the opening picture is decided at options and visuals, where tone already reaches. (Was: a sixth brief decision, `opening`: what the first line and the first picture do, with a reason; read by script (first sentence), options (first scene) and visuals | the brief decides the ending but not the opening; a social or promotional video is lost without a hook in its first seconds | small, prompt + shape + validator |
| L7 | Format and destination on the brief's production block (frame shape 16:9 / 9:16 / 1:1, where it plays, watched muted or not), passed to visuals (aspect of generated takes), options (which sub-clips survive the crop) and the delivery checklist (the editor reframes in Resolve) | nothing downstream can make a vertical film today; the intent must at least reach the stages that choose pictures | medium; a vertical render path is separate and larger |
| L8 | Specified in design/50 (SK, 18 Oct: all identified fields; chat > script > directory; warn on every difference; absence never fails). A client card from the directory at the brief: industry, description, USP, services, target audience, website and YouTube, location, competitors, past learnings, CTA instructions, brand guidelines; shown under "WHAT THE DIRECTORY SAYS ABOUT THIS CLIENT" as unverified context for the recommendations, never as answers. The delivery checklist gains logo, palette and website lines when the directory has them | v2 takes only id, name and status from the directory today; VK Nardep's directory audience ("youth, volunteers, rural communities…") would have informed the brief's audience recommendation; 54 of 139 Active clients carry an audience, 50–60 a description, USP and industry; CTA instructions, brand guidelines and logo are filled for almost none yet | small–medium, server (directory select, brief prepare, delivery checklist) + prompt |
| L9 | Logo: never placed by the tool. If a client's logo is ever wanted in the bundle, it travels as a file in Graphics/ with the placement words on the checklist; the editor places and sizes it in Resolve | SK's rule: nothing the editor cannot resize | checklist only, later |

## Confirmed in the workflow (SK's question on action without voice)
Pauses (design/19): at options, before any option, the child proposes scenes and pauses; a pause sits after a sentence-ending word (or after the last word), states the total silence wanted, at most 4 s, with a reason ("a step of an activity should finish on screen before the next is spoken"); the recording's own gap counts toward it; the narration is cut only in the silence after a sentence, never inside a word; the picture runs on under the silence; subtitles shift by the approved pauses; the assembly render inserts the silence. Approved with one quote (`vw options scenes`). No pause before the first word.
