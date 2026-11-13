# Analysis and options: how the heart of the process can be made better

13 Nov 2026. A proposal for SK and Deepa. Nothing here is built or tested. Uncommitted working note.

Read for this: the served analysis and options steps (`server/procedures/v3.json`), `server/app/analysis.py`, `clip_log/prompt.py` and `schema.py`, `stage2/package.py`, `narration.py`, design/11 to 15, 17, 19, 21, 43, 91, 140, the model test report (`model-test/REPORT.md` and round 1), and VW-23's jobs and log. Not read: the blueprint file itself, and most of the validator's code.

## 1. How it works today

1. **Gemini 3.8 Flash, one paid request per clip.** It sees one clip, the script as paragraphs (beats), and the brief. It writes a long log: sub-clips, what is seen, people and sound, camera, quality, and which paragraphs each sub-clip fits. VW-23: 94 clips, 51 minutes, 825,000 tokens in, 551,000 tokens out.
2. **The server, no AI.** Eligibility, crops, and a list of pieces per scene.
3. **Claude, from text only.** "You have NOT seen the footage." It decides which clip goes under which words, to the frame.
4. **Checks.** The server's rule check; a second look at still frames by a helper; the operator's keep, reject or trim on every footage shot.

## 2. Where it is weak, with the evidence

| # | Weakness | Evidence |
|---|---|---|
| W1 | **The placement is made blind.** Claude places footage from Gemini's words, then pictures are checked afterwards, a few stills at each edge of a shot. | design/140 B5: three clips described wrongly ("resting undisturbed" while a foot steps into the pour). The foot was caught "only by luck". |
| W2 | **The model that sees the video is asked the coarse question; the model that cannot see it answers the fine one.** Gemini matches to a paragraph. Claude matches to a sentence and a frame, from text. | `clip_log/prompt.py:48`; design/91 N17. |
| W3 | **The cheaper logger is weakest exactly where a blind placer needs it.** | `model-test/REPORT.md`: "Choose Argon if the log feeds an assembler that never sees the footage." Flash "left most uncertainty strings empty". Flash was chosen on cost, "a close call". |
| W4 | **Some server checks match words, not meaning, and a check passes when its marker is left out.** The assistant learns to write words that pass. | design/140 B1, B2. |
| W5 | **Most flags are noise.** | design/140 B4: 51 flags nobody needed to act on. Each clip gets its own colour group because Gemini sees one clip at a time. |
| W6 | **The assistant learns each file's shape by being refused.** | VW-21 and VW-23 got the identical refusal on the first word of scene 1. VW-23's options check was rejected three times. |
| W7 | **Pauses are decided before the footage is read.** | Options step 2: read the scenes and sentences "and nothing else yet". No pause was proposed in the runs seen. |
| W8 | **Gemini is paid to write things nobody reads.** | design/43 7.4: the reading copy drops `entities`, `sfx_cues` and `editorial_ideas` from every row. |
| W9 | **Nobody knows how good the placement is.** No score exists. The choice of placer rests on one test on one clip, judged by one of the two contestants, never repeated. | `model-test/obsolete-round1` report; design/12 C.4. |

## 3. What to change

The idea in one line: **let each model do what it is best at, let the placer see before it places, and measure the result against the operator's own answers.**

### A. Measure first (W9)

- The operator already answers KEEP, REJECT or TRIM on every footage shot. That is the truth.
- Keep a score per film: share of footage shots kept as placed, split by direct match and B-roll, and how many faults the second look found.
- Score the last films from their recorded answers. That is the baseline. Every change below is then judged by this number, not by opinion.
- Cost: small. No model call.

### B. Let the placer see before it places (W1)

- For every sub-clip the placer intends to use, give it a contact sheet: a strip of frames across the whole sub-clip, not only its edges. (Contact sheets exist in design/27; strips at 480 px was a lesson of the animatic round.)
- The placement rule becomes: no real shot is proposed that the placer has not looked at.
- The second look then checks the cut as a sequence (does shot 2 follow shot 1), which is what it is good for.
- Cost: image tokens for a few dozen candidates per film, not for all 94 clips.

### C. Ask the video model the fine question, after the scenes exist (W2, W3)

- Keep the first pass per clip as the cheap log.
- Add a second, small pass once the scenes are approved: for each sentence that has a candidate, send that sentence and the candidate sub-clip (as video) and ask three things. Does it show exactly this, yes or no. From which second to which. What does the sentence say that the clip does not show.
- This is the paid "inspect" of today, turned from an exception into the rule for every direct match. It catches the fault in the middle of a shot, which stills cannot.
- Calls: one per placed footage shot (tens), each on a short piece. This is the one place where the stronger Gemini model may be worth its price; test both.

### D. Make the first log shorter and sharper (W3, W8)

- Stop asking for the fields that are thrown away.
- Ask for the fit by sentence as well as by paragraph. Sentences are fixed at the script stage, so their ids are stable.
- Make "what this clip does not show" required and non-empty wherever a fit is claimed. The model test recommended exactly this for Flash.
- Expected: fewer output tokens per clip, so a faster and cheaper analysis.

### E. One look at the whole film (W5)

- After the per-clip logs, one request reads all the summary cards (and contact sheets) together and sets what only a film-wide view can: which clips are the same place and day (one colour group), which clips are takes of the same action and which take is best, which things have two names in the logs.
- This removes the colour-group noise and gives the word checks one vocabulary.

### F. Checks by meaning, and no silent passes (W4, W5)

- A check that compares words is replaced by the answer from C ("does it show this") or removed.
- A marker left out needs a stated reason (SK already decided this on 2 Nov: "Required, or a reason").
- Flags that never lead to an action are not shown.

### G. Pauses from the footage (W7)

- Move the pause proposal after round 1 of the placement.
- The server can suggest them by arithmetic: where a placed action needs longer than its sentence lasts, propose a pause of the difference, up to 4 seconds, with that as the reason.
- The operator approves them with the cut, not before it.

### H. Show the shape before the first try (W6)

- Each file the assistant must write comes with one filled example (a real scene, a real word id).
- Target: no refusal for a file's shape.

## 4. Order

1. **A**, the score. Without it nothing else can be judged.
2. **B** and **C** together on one finished film, as a test outside the application: same footage, same script, compare the score.
3. **D** and **H**: cheap, lower risk, save time on every film.
4. **G**, **E**, **F**.

## 5. What this does not claim

- That a newer model is the fix. The gains above come from who sees what and when, and from measuring. A stronger placer on the same blind text would still place blind.
- That Claude must be the placer. Test Claude and Gemini as placer on the same film, scored by the operator's answers. The earlier test was not fair and says so itself.
- Any number for the improvement. There is no baseline yet.
- That it suits every category as written. The examples are from documentaries; the rules above are generic, but they are untested on an advertisement or a social clip.
