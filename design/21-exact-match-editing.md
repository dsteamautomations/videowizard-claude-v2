# 21 — Exact-match editing: real footage only where it shows what is said

Date 15 Oct 2026. Raised by SK after watching the VW-2 review film (options v1, 11 options over 9 scenes). Revision 3 includes SK's corrections and SK's answers after the VK02 reference analysis (design/22). Awaiting SK's final yes.

## What went wrong in VW-2 options v1
- Every sentence was filled with whatever footage was available, even when it only loosely related to the words.
- Different parts of one source clip were used in several places.
- Abstract statements (savings of building material, cost, thermal comfort) were covered with unrelated site footage.

Cause: the options rules required every scene to be fully covered by footage or declared a gap as a whole. Nothing asked for an exact match, and nothing allowed a gap inside a scene.

## Requirement
1. **Exact matches first.** Real footage goes only where it shows exactly what is being said at that moment: the same action, on the same object, done the same way. A generic or merely related shot is not a match.
2. **Part of a sentence can match.** If footage matches one part of a sentence, use it for that part only, and leave the rest blank.
3. **Blanks are filled with AI-generated video.** They are filled later at the visuals stage. Abstract ideas are blanks by default.
4. **No obligation to use the footage.** Unused clips are fine; quality of match beats coverage.
5. **Blank lengths.** A blank is at least 3 s. Anything from 3 s upward can be AI-generated, with no upper limit. Today's AI tools make at most 30 s per shot, so the visuals stage makes a long blank as a series of shots of up to 30 s each. Example: a 5-minute film with 30 s of usable footage has 4 min 30 s of AI video, made as a series of shots.
6. **B-roll.** After the exact matches are placed, a clip from the footage may be suggested for a blank when it is a good choice for that blank: it helps understanding and is a good candidate against an AI shot. Otherwise the blank is left for AI. B-roll suggestions are always presented as a choice (rule 8).
7. **Reuse is a choice, never automatic.** Using a clip a second time is allowed only when nothing else works. This includes using different parts of the same clip, for example the first 5 s near the start of the film and the last 5 s near the end: the viewer sees almost the same thing twice. Every such reuse is presented as a choice (rule 8), never placed silently.
8. **Decision slides.** Anything that needs the operator's opinion is not played back to back with the confirmed shots. A decision slide is placed before it, stating the question. Decision slides are used for:
   - a B-roll suggestion for a blank (rule 6);
   - a reuse of a clip or part of a clip (rule 7);
   - a "possible match, check by eye" (E2);
   - an exact match logged as poor quality (E3);
   - a join of shots across a sentence boundary that may not read as one action (E6);
   - any other placement the assistant is not sure of.
   The operator answers each decision keep or drop. A dropped placement becomes a blank (AI) if it is 3 s or more; otherwise the neighbouring shots extend, or it is flagged (E1).
9. **Speaker on camera follows the client's policy.** Where the client allows showing the speaker, the speaker saying the line is an exact match. VK Nardep does not allow it.
10. **A large AI share is fine.**
11. **Real shots are cut to meaning, not stretched.** Several short real shots may be combined; 2 to 3.5 s per shot is normal, as in VK02. A shot is never held longer just because the footage exists. Proposed check: a real shot over 4 s raises a flag asking whether its length earns its place (a flag, not a refusal).
12. **What counts as a match.** The footage conveys what the script says, directly, or indirectly so the viewer can relate it to the words, and it contains nothing wrong. Directly matching footage is placed as a confirmed shot. Indirect footage (B-roll), including for abstract lines, is used only when it is clearly relevant, and always behind a decision slide.
13. **Scope of this stage.** The finished film combines three things made separately: real clips, AI videos, and animations or edits. This stage only decides which real clips to use, in what combination, and where. Everything else stays a black slide, which later stages fill with AI video or animation.
14. **Finishing is out of scope.** Titles, subtitles, mascot, logos, frames, infographics and end cards are done separately and are not planned here.

## Slide format (proposed 15 Oct; awaiting SK's yes)
Every slide carries one running number; the operator answers by number. The words "option" and "beat" are not used on slides.
```
#05 · Scene 5: Quality materials · 57.2 s · 7 shots
Clips: brick stacking close-up (2.5 s) + ... (readable clip names, wrapped)
#06 · Scene 5: Quality materials · BACKUP for #05 · 57.2 s · 6 shots
#12 · DECISION · Scene 6 · B-roll suggested instead of AI: keep or drop?
#13 · BLANK · Scene 6 · 12.4 s · for AI video or animation
```
Internal clip codes stay in the plan files only.

## Unstated but expected requirements
- Each exact match cites the clip-log evidence for it, so the operator can see why it counts as exact.
- The coverage report shows, per scene, how many seconds are exact footage, how many are AI, and how many decisions are waiting.
- Each AI blank carries what it must show: the words it sits under and the intent. The visuals stage then starts from that.
- Client safety rules still apply. A perfect match that is not client-safe (for example, copyrighted music) cannot be used.
- Narration timing is unchanged: blanks are picture only, and the narration keeps running. The approved pauses still apply.
- Decision slides appear in the review film only. The master and the final film contain the kept shots and blanks, never the slides.

## Edge cases (agreed 15 Oct unless marked)
| # | Case | Handling |
|---|---|---|
| E1 | A blank shorter than 3 s between two exact shots | Hold a neighbouring exact shot longer if its usable window allows. Otherwise flag it for the operator's decision. Never an AI shot under 3 s. |
| E2 | Footage looks right in the log, but the specific method is unclear (for example, bricks laid but not clearly on edge) | Not exact. Leave a blank, and offer the clip behind a decision slide as "possible match, check by eye". |
| E3 | The log says the clip matches but also marks it as poor quality (shaky, soft, grade C) | Not used as an exact match. Offered behind a decision slide so the operator can judge it by eye. The assistant reads logs only, so it cannot confirm quality itself. |
| E4 | Two takes of the same action | Only one may be in the final film. The other take can be the backup option for that scene (see "Takes and options" below). |
| E5 | The first and backup option of one scene | They may use the same clip or different takes. Only one option is kept, so the film never shows both. |
| E6 | One action across two sentences | Allowed: one shot, or several shots from different clips, may run across the sentence boundary. If the join may not read as one action, a decision slide asks the operator. |
| E7 | A long blank | No upper limit. The visuals stage splits it into AI shots of up to 30 s, at sentence boundaries where possible. |
| E8 | A whole scene with no exact match (VW-2 scene 8, pointing and curing; scene 4, environmental benefits) | The whole scene is a blank for AI. |
| E9 | The speaker says the sentence on camera | Exact match only where the client allows showing the speaker. |
| E10 | The footage shows an action longer than the words | Use only the part that carries the meaning (rule 11). Where the action must be seen to finish, let it run into a following approved pause. |
| E11 | Reuse of a clip, including another part of the same clip | Behind a decision slide with the reason no other clip or AI shot works. |
| E12 | A large share of the film is AI | Allowed. The report states the share before the visuals stage. |

## Takes and options (answer to SK's question)
- **Two takes** are two recordings of the same action. Rule: the finished film shows the action once.
- **First and backup options** are two alternative edits of one scene. The operator keeps one at the master step; the other is discarded.
- So they fit together: the natural backup option is the same scene cut with the other take. The operator compares take A (option 1) with take B (option 2) and keeps one. The film still shows the action once.

## Failure modes
- Matches are judged from the clip logs (text), not by watching. A log can overstate. E2 and E3 put doubtful clips behind decision slides, and the operator watches the review film.
- Too strict a match leaves very little real footage. The coverage report shows exact and AI seconds per scene before the review film is rendered.
- Too many decision slides make the review long. Each slide is short (3 s), and only real doubts get one.

## Next
- SK's final yes on this revision, including the slide format.
- Then tests first and the build: blanks inside a scene, match evidence per shot, numbered slides (confirmed, backup, decision, blank), keep/drop decisions, the reuse rule, the long-real-shot flag, the coverage report (real seconds, blank seconds, decisions per scene), blanks handed to the visuals stage, and a rewritten options prompt. VW-2 options v1 is replaced; the approved scenes and pauses stay.
