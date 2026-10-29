# 124 — C4: the review prompt for the later phases

SK's review prompt of 29 Oct 2026, revised after reviewing the first four phases (design/121, design/124). Paste everything between the lines into a new conversation, naming the phase to review. The later phases are: **5 Reference sheets and golden pictures**, **6 Shot pictures** (start images, stills, graphic states, drawn scenes), **7 Videos** (takes), **8 Review and record**.

---

```
Today, you and I are going to review one phase of the Visuals stage in this project, one step at a time.
The phase: <NAME THE PHASE, e.g. "5 Reference sheets and golden pictures">.

ABOUT ME
- I am a non-technical person. I can only understand a functional description in very simple English: what something does and why it happens.
- Avoid code, file names, and jargon. If a technical word cannot be avoided, explain it in plain words.
- Whenever you mention a label like F14 or F15, always explain what it is.
- Keep explaining this way in every reply, so I don't have to ask you again or repeat this.
- Ask me one question at a time, with your recommendation first.

WHEN YOU ARE NOT SURE
- If you are not sure about anything, always ask me. Don't worry about disturbing me, even if you have to ask again and again.
- Never tell me something is checked unless you checked it in the code or ran it. Say "I read it" or "I tested it", and which.

WHAT YOU READ FIRST (silently)
- design/124 (the review so far, every decision and the tidy-up plan), design/124-a0-rule-list.csv (every rule, by phase), design/124-a3-disagreements.md, design/124-a4-server-voices.md, design/124-a4-guide-voices.md, design/124-b-film-types.md.
- The instructions' part for this phase (version 3: the part named for this phase, or the "later" part until it is split), the server code that checks it, the lines the server adds to its requests, and the prompt-writing guide files this phase's step reads.
- Do not raise again what is already decided there.

HOW WE WORK
- We go one step at a time inside the phase. I will ask questions as we go.
- For each step, tell me:
  1. What happens
  2. Why it happens
  3. What it connects to
  4. Anything that has gone wrong
  5. Anything that can be done better (see "What better means" below)
  6. Too many rules: check whether the instructions at this step are over-constrained: so many rules that the AI's actual behaviour changes, or a rule that works for one thing and spoils another. If a rule needs to be added, do not add it in a way that hurts another situation; explain where it applies and how the AI should behave there.
  7. Prompts that create prompts: some steps contain instructions that create another prompt for an AI (a picture request, a video request, a check). Check whether those instructions are very clear and whether they contradict themselves. If you find a problem, explain it in plain words and suggest a fix.
  8. API keys: wherever a key can make several calls at the same time, check that it does. If more keys are needed to rotate between, tell me and ask me for them.
  9. Parallel work: if something in the process can be done in parallel (calls or several AI helpers at once), check that it is.
  For points 8 and 9, tell me about the possibility and propose the change. Make the change only after I say yes.

ALSO BRING UP, UNASKED, FOR THIS PHASE (the tidy-up checks)
  10. Change-history labels still inside text the AI reads (instructions, server messages, added lines).
  11. Topics written twice (in the instructions, or in the instructions and the prompt guide), and especially copies that say different things. For each disagreement say which copy the server actually follows.
  12. Out-of-date rules: rules about features that changed (for example: four ways to make a picture; start and end pictures for every video; "refused from the next release"; models no longer used; the spending limit once design/122 is built).
  13. The other voices: the server's "what next" messages, the lines it adds to picture and video requests, the picture check's fixed lines, and the prompt guide — anywhere they disagree with the instructions or with my decisions.
  14. Rules that misfire for one of these film types: opens on footage / opens on a gap; human story / technical record; no footage at all; a very short gap (about 3 s) / a long gap (30 s or more); no people / a person speaking to camera; a busy scene / a quiet one.
  15. Rules the server already refuses or warns on, which the instructions can say in one line.
  16. Anything in this phase's step that is part of each shot's fingerprint (changing it marks prepared work stale): say so before proposing a change.

THE FLOWCHART
- Draw the flowchart with me as we go. It shows what is connected to what, and where something has gone wrong.
- The flowchart is for you as well as for me. Use it to step back and see what could have been connected and what is not yet connected. If you spot something, tell me in plain words, even if it relates to an earlier phase.

WHAT "BETTER" MEANS
- Better means not complicating things.
- Do not add or redo checks for rare edge cases.
- If there is a clever way to do something in simple steps, or in fewer steps, move toward that.

RECORDING
- Keep a running document of every change I agree, as design/<next number>-visuals-review-<phase>.md, with what changes, why, and a short "for the builder" part. Nothing is built until I say so. When we build: tests first, a trace of old and new wording with an independent check, and no number or condition lost.

BEFORE EVERY REPLY, CHECK YOURSELF
- Is this in simple English?
- Is it written for me, a non-technical person?
- Am I going one step at a time?
- Did I ask only one question?
If any answer is no, rewrite the reply before sending it.
```

---

What changed from the original prompt, and why:
- **Names the phase and what to read first,** so a new conversation starts from the decisions already made instead of re-raising them.
- **Items 10–16** are the tidy-up checks that took Phases A and B to find (labels, copies that disagree, out-of-date rules, the other voices, film types, one-line server rules, the shot fingerprint), so each later phase finds them in its own review.
- **"Checked" means checked:** two findings in this review were wrong because a helper's reading was trusted (the cap; one change per edit).
- **One question at a time, recommendation first;** and the recording and building rules that worked here.
