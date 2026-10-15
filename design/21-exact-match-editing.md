# 21 — Exact-match editing: real footage only where it shows what is said (requirement, awaiting SK's approval)

Date 15 Oct 2026. Raised by SK after watching the VW-2 review film (options v1, 11 options over 9 scenes).

## What went wrong in VW-2 options v1
- Every sentence was filled with whatever footage was available, even when it only loosely related to the words.
- Different parts of one source clip were used in several places.
- Abstract statements (savings of building material, cost, thermal comfort) were covered with unrelated site footage.

Cause: the options rules required every scene to be fully covered by footage or declared a gap as a whole. Nothing asked for an exact match, and nothing allowed a gap inside a scene.

## Requirement (restated)
1. **Exact matches first.** Real footage goes only where it shows exactly what is being said at that moment: the same action, on the same object, done the same way. A generic or merely related shot is not a match.
2. **Part of a sentence can match.** If footage matches one part of a sentence, use it for that part only, and leave the rest blank.
3. **Blanks are slots for AI-generated video.** They are filled later at the visuals stage. Abstract ideas are blanks by default.
4. **Each source clip is used once.** Reusing a different part of a clip already used is a last resort, and must say why nothing else works.
5. **Footage may go unused.** Quality of match beats coverage.
6. **Blank lengths.**
   - Minimum about 3 s, and 3 s only when an AI shot really adds something there.
   - Maximum 30 s per AI slot. A longer blank is split into several slots of up to 30 s each, in any mix, for example 8 s then 30 s.
7. **Order of work.** First place the exact matches. Then look at each blank: a B-roll that genuinely helps understanding, or AI.

## Unstated but expected requirements
- Each exact match cites the clip-log evidence for it, so the operator can see why it counts as exact.
- The coverage report shows, per scene, how many seconds are exact footage and how many are AI slots.
- Each AI slot carries what it must show: the words it sits under and the intent. The visuals stage then starts from that.
- Client safety rules still apply. A perfect match that is not client-safe (for example, it has copyrighted music) cannot be used.
- Narration timing is unchanged: blanks are picture only, and the narration keeps running.
- The approved pauses still apply. A pause after a step is best covered by the real footage of that step finishing.

## Edge cases (my proposed handling; please confirm or change)
| # | Case | Proposed handling |
|---|---|---|
| E1 | A blank shorter than 3 s between two exact shots | Hold the neighbouring exact shot longer if its usable window allows. If not, extend the blank to 3 s by trimming the weaker neighbour. If neither works, flag it for your decision. Never a sub-3 s AI slot. |
| E2 | Footage looks right in the log, but the specific method is unclear (for example, bricks laid but not clearly on edge, rat-trap style) | Not exact. Leave an AI slot, and list the clip as a "possible match, check by eye" for you to promote. |
| E3 | Exact match but poor quality (shaky, soft, grade C) | Use it only if the action is still readable. Otherwise an AI slot, with the reason given. |
| E4 | Two takes of the same action | Use the best one once; the other goes unused. |
| E5 | Reuse across PRIMARY and SECONDARY options of the same scene | Allowed, because only one of the two is kept. Uniqueness applies to the kept film. |
| E6 | One action spans two sentences | One continuous shot may run across the sentence boundary. It counts as one use. |
| E7 | A blank longer than 30 s | Split it at a sentence boundary nearest the 30 s mark. No slot over 30 s. |
| E8 | A whole scene with no exact match (VW-2 scene 8, pointing and curing; scene 4, environmental benefits) | The whole scene becomes AI slots, split at 30 s. |
| E9 | The speaker says the sentence on camera | Use the speaker's video only if the client policy allows showing the speaker (it does not for VK Nardep). Otherwise it is not a match. |
| E10 | The footage exists but its action is longer than the words | Use it, and let the action finish into the following pause where one was approved. Do not cut the action short to fit. |
| E11 | Last-resort reuse of a clip | Allowed only with a written reason why neither another clip nor an AI shot works. Shown on the slate as a warning. |
| E12 | A large share of the film becomes AI | Expected for explainer scripts. The report states the share so the AI generation effort is visible before the visuals stage. |

## Failure modes
- Matches are judged from the clip logs (text), not by watching. A log can overstate. E2 keeps uncertain ones out, and the review film is still watched by you.
- Too strict a match leaves very little real footage. You see the exact and AI seconds per scene before the review film is rendered, and can relax a scene.
- An AI slot shorter than the shot it needs to show (for example, a complex process in 3 s). The slot states its intent, and the visuals stage can ask for more length within the same pause rules.

## Questions for SK
1. In step 7 above, should a related B-roll be offered beside the AI option for each blank, or should blanks default to AI unless the B-roll is clearly better?
2. The finished rat-trap bond video: yes, please share it. I would measure how many seconds are real versus AI, the slot lengths, and how clips were used. Then I would set the defaults to match. The measuring is local and uses no paid AI.

## Build impact (after approval; tests first)
- The options rules gain blanks inside a scene (AI slots of 3–30 s), an exact-match evidence field per shot, and a refusal for reusing a clip without a reason.
- The coverage report shows exact versus AI seconds per scene.
- The visuals stage takes the AI slots, each with its words and intent.
- The options prompt is rewritten around exact matches first.
- VW-2 options v1 is replaced. The scenes and pauses you approved stay.
