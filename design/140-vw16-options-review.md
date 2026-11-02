# design/140: VW-16 analysis and options review, Codex's findings and the builder's (2 Nov 2026, for SK's Q&A)

VW-16 is at the options step: the first cut was proposed and rendered, and the operator is reviewing it on the review page. SK gave Codex and the builder the same two logs (`log-analysis.md`, `log-options.md`, written by the operator's assistant). The question: did something go wrong, is the decision-making flawed anywhere, and where could it fail on a future film?

VW-16 ran on the live build (0.82.1). Some of the rules below (the 3-second blank minimum, the 12-second blank warning, rule 11's 4-second hold) are already removed in the design/139 build, which is not deployed yet. They are marked where that matters.

## 1. Codex's four points, checked against the logs

| # | Codex said | Builder's reading | Verdict |
| --- | --- | --- | --- |
| C1 | C0073 was removed because its description said "reinforcement_steel_bars", not "rebar" | True (options log, entries 39 to 41). The fault is the server's carry-over check, not the assistant's judgement: it matches one word at a time against the clip's landmark words. "steel bars" did not match `reinforcement_steel_bars`, and "wet concrete" did not match `wet_concrete_slurry`. The assistant then chose the carry-over words to pass the check ("trying landmark words"), so the check stopped checking what the viewer still sees. | **Agree, and the root cause is a server rule** (see B1) |
| C2 | The action-word markers were all removed; the cut then passed, but passing proved nothing | True (entry 34: `action_word_id dropped everywhere`; four shots also left without an illustrating word). The server checks a marker only when it is present, so leaving it out makes the check pass. | **Agree** (see B2) |
| C3 | C0100's wide shot was first rejected (2.5 s slot, 3 s rule), then restored | True (entries 35 and 52). The rule was applied correctly; the first fix chose to swap the shot instead of moving the next cut by half a second, and the second look found the better answer. Minor. | Agree, minor |
| C4 | The second look caught a foot entering wet concrete under "allowed to set undisturbed" | True (entry 50). It also caught two more pictures that did not show what their descriptions said (B5). | Agree, and it is a pattern |

Codex left one question open: whether the reviewer's or the rule's trim was better at the action endings. The builder agrees it cannot be settled from the log (B3).

## 2. The builder's further findings

| # | Finding | Evidence | Why it matters on a future film |
| --- | --- | --- | --- |
| B1 | **The carry-over check matches words, not meaning.** A clip is marked as "not showing" a thing when its log uses another name for it. | entries 39 to 41 | Good shots are dropped for wording, and the assistant learns to write words that pass instead of words that describe. Every category has synonyms (a product's name against its type, for example). |
| B2 | **Leaving a marker out passes its check.** The action-word timing (B2) and the illustrated word (B1) are checked only when given. | entries 34, 41, 52 | The cut can pass while nothing was checked. The more conflicts the assistant meets, the more markers it drops. |
| B3 | **Two rules contradict each other at some shot ends.** The action peak the analysis logged sometimes ends in a camera move (a pan or a whip). The "keep the whole peak" rule then forces the move into the cut, and the reviewer's clean out breaks the rule. | entry 51, workarounds | The assistant swaps the shot for another, as here. If no other clip exists, it has to choose between a broken rule and a bad cut, with no rule to say which. |
| B4 | **Most "for information" flags are noise.** R10 (colour group changes) fired on 16 shots because the analysis gives every clip its own colour group, though the footage is one yard on one day. R1 ("not at a natural cut point") fired on 19 shots because rule B1 places cuts 6 to 12 frames before the word, which is a different point. | entry 56 | 51 flags that nobody needs to act on hide the one that matters, and they teach the assistant and the operator to ignore flags. |
| B5 | **The analysis described three pictures wrongly, and only the second look caught them.** C0087: "resting undisturbed", but a foot steps into the pour. C0086: "hollow clay blocks", but it shows paired tiles. C0074: "comparative layout of the named kinds", but none of the named kinds is in the picture. | entries 29, 50 | Round 1 places footage from the analysis text alone. The second look checks only a few still frames at each edge of a shot, so a fault in the middle of a shot (the foot) is caught only by luck. |
| B6 | **The scene's chapter: the instruction and the server disagree.** The instruction allows a scene with no chapter; the server requires one. The closing scene (summary and logo) was given "Finished homes and families" to pass. | entries 12, 16, 17 | A wrong chapter on a scene feeds the stage checks (N17) and the editor's notes. |
| B7 | **The second-look helper does not know all of the server's rules.** It used four note kinds the server refuses, and suggested two cut points that drop the action peak. | entries 51, 52, workarounds | Every helper finding has to be translated or undone by hand; a helper fix can be lost in that translation. |
| B8 | **Splitting a paragraph that covers two chapters has no rule.** Paragraphs 5 and 8 were split; paragraph 7 (pouring and compacting) was not. | entries 10, 11 | The same script could be cut differently on another day; the chapter checks (N17) then flag the merged chapter, as they did here (entry 56). |
| B9 | **The tool's own working is hidden from the assistant.** The output of long commands run in the background sits outside the run folder, which the guard blocks; the shape of `out/scenes.json` is not in the package (written by guess, fixed from the refusal); no clock time reaches the assistant. | entries 14, 48, 55; analysis log | Small each, but each one is a guess. |
| B10 | **The analysis step asked the operator two questions it should not ask.** In the earlier chat, the assistant asked "listen to the clips' audio? any clip to leave out?". The instruction says to start without asking (your B11 answer: keep). | analysis log, entries 7 and 8 | An extra question each film; harmless, but it shows the instruction was not followed. |
| B11 | **The safety flags were waived automatically.** Because the brief recorded no brand or safety rules, the server waived every protective-equipment flag (helmet, gloves, footwear, barefoot …) for the whole film. | analysis log, entry 11 | That is design/60's rule, and it is told, not asked. On a construction or factory film, "no rules" in the brief can let barefoot or unhelmeted workers on screen without anyone choosing that. Worth confirming as a decision. |

## 3. What worked

- The second look did its job: five scenes changed, including the foot in the concrete.
- Rejected checks were fixed and re-checked until valid, with the server's exact words in the log.
- One clip once, the risk flag on a licence plate (C0084), and the screen-direction rule were each applied and recorded.
- 300.7 s of film: 55.0 s real footage, 21.7 s B-roll, 224.0 s for the visuals stage. That share follows from what was filmed (no shuttering, bar placing, ceiling or campus footage), not from a fault.

## 4. Questions for SK (asked one at a time in chat)

1. B1: the carry-over check, by meaning or by word?
2. B2: a left-out marker: allowed, or refused without a reason?
3. B3: a peak that ends in a camera move: may the cut end before the move?
4. B4: the noisy flags R10 and R1: fix, or silence?
5. B5: footage placed from the analysis text: check by eye before placing, or rely on the second look?
6. B6: a scene with no chapter: allowed?
7. B7: the second-look helper given the server's rules?
8. B8: when to split a paragraph that covers two chapters?
9. B9: the tool's output and the scenes shape made visible?
10. B11: the protective-equipment waiver when the brief has no rules: keep, or ask?

B10 needs no decision: it is a wording reminder for the analysis step.

## 5. SK's answers

- **Q1 (B1), 2 Nov:** **Match by meaning as well as by word** (SK: "it should also refer by meaning"). A word match still passes as today; where the words differ, Claude judges whether the description shows the same thing under another name (rebar and reinforcement_steel_bars) and records its reason, and the shot is accepted. A shot is refused only when neither the words nor the meaning match.
- **Q2 (B2), 2 Nov:** **Required, or a reason.** Every real shot names both markers (the word it shows and the action word), or says why one cannot be met (for example: no action word in its sentence); the reason is shown to the operator on that shot.
