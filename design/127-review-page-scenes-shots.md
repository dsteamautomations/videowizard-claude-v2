# 127 — The review page and film by scene and shot (requirements, 30 Oct 2026)

Source: SK's design of 30 Oct 2026 (vw2-notes/review-page-scene-shot-proposal.md: scenes and shots, alternatives per shot, B-roll in two rounds, the words on screen, pausing). Read against the code: `stage2/slides.py`, `stage2/stage.py` (`needs_answer`, `decide`, `build_master`, `slide_cues`), `stage2/validator.py`, `stage2/render.py`, `templates/review.html`, `procedures/v3.json` (options and master), `plugin/scripts/vw.py`, `plugin/commands/vw.md`, `plugin/agents/vw-scene-review.md`. Server 0.77.0, plugin 0.64.0. Nothing is built until SK approves this list.

## 1. What changes (the requirement, restated)
1. **A scene is a header, not a question.** Its row and its film card list, one line each: "Scene 1", the title, "Total time: 25.9 s", "Shots: 3 (1 made with AI, 2 footage)". No buttons, except one case (6).
2. **Every shot is numbered in play order and has its own row:** Scene 1 · Shot 1, Shot 2…, AI shots included. The letters (1A, 1B) and the "#1 | …" one-line text go.
3. **A footage shot** (direct or B-roll) takes **Keep / Reject / Trim**. Reject turns its time into an AI stretch.
4. **An AI shot inside a scene** takes nothing.
5. **An alternative belongs to a shot:** "Scene 2 · Shot 1 · Alternative 1": another clip for the same words and the same length. It plays right after its shot, after its own card, with the same narration again. Keep on the shot switches its alternatives off; Reject on the shot opens them (Keep / Reject); at most one alternative kept; shot and alternatives all rejected → an AI stretch.
6. **A scene that is all AI** (one AI shot the scene's length) takes **Keep AI / Find footage** (today's Keep / Reject of such a scene).
7. **B-roll** is a footage shot labelled "B-roll" in dark red at two to three times the text size, on its row and in the film. It is no longer a separate question.
8. **The spoken words are always on screen:** a strip at the bottom of every footage shot (label and words); on an AI shot's card, the words are the main text (what it must show, one line under them).
9. **Cards only before a scene and before an alternative.** A question no longer gets a card of its own.
10. **One colour per scene,** the same on the page (the scene's rows) and on the film (a band on its card and its strip). An alternative: dashed border and its label, no colour of its own.
11. **The page pauses** the film at the end of a shot that still needs an answer and says "Answer to continue"; an answer or "Continue" plays on. AI shots never pause. A switch "Pause for answers" (on by default, remembered on that computer) turns it off. A switched-off alternative is skipped while playing.
12. **B-roll in two rounds (editor's instructions):** round 1, exact matches across the whole film; check; round 2, B-roll only into blanks, only from clips not used in round 1, the same subject or setting as the words, nothing contradicting them, and checked against the shot before and after (it must not contradict them and should support the idea); never into a blank whose words make a specific claim (a number, a comparison, a saving); a blank stays when no unused clip conveys the idea. "A large share of blanks is fine" becomes "a blank is fine when no unused clip conveys the idea".
13. **Older ways retired by refusal (the overhaul):** the whole-scene second choice (SECONDARY, "-2", "second choice", blue card and mark): "a second cut of a scene is retired; give an alternative for a shot"; scene Keep/Reject/Trim on a scene with footage: "decide its shots: Scene 1 · Shot 2 …"; the decision rows and KEEP/DROP: "answer the shot: KEEP, REJECT or TRIM"; KEEP_WITH_EDIT: "use TRIM on the shot"; the old slide labels (2A, 2-2): refused with the new labels listed; `b_roll` as a decision kind: "B-roll is a shot with match b_roll; it needs no question". Removed with them: scheme 2, `parts_decide`, `sure_shots`, `backup_for`, the blue background, the slate-head parsing ("#N | …"), the master build's swap to the other option, the old hints and the page's bottom help text, and the tests built on them.

## 2. Unstated but expected
- **The doubtful-shot question stays, as a note on the shot** (kinds check_by_eye, poor_quality, reuse, join, other): shown under the shot's row and in the strip; the answer is the shot's Keep / Reject. A kept reuse note approves the reuse (as today).
- **Labels the chat path uses:** `1` (scene, answerable only when all AI), `1.2` (scene 1, shot 2), `1.2a1` (its alternative 1). `vw master decide --slide 1.2 --action KEEP|REJECT|TRIM [--edit "in:+12,out:-6"]`; the page shows the words ("Scene 1 · Shot 2"), the chat may type the short label.
- **The first answer still approves the options** (unchanged).
- **The options file:** one option per scene (no rank, or PRIMARY only); a real shot may carry `alternatives`: [{sub_clip_id, source_in_frame, source_out_frame, match, evidence, crop?}]. Each alternative is checked like a shot (eligible, inside its window, its hold, its peak) and must be the same timeline length as its shot; its clip is used nowhere else in the cut.
- **A B-roll clip must not be a direct match anywhere in the cut** (enforces "B-roll after the actual ones" mechanically): refused by name.
- **The second look (O4–O6)** reads and writes the new shape: the scene file lists shots, alternatives and notes; the helper may add or change alternatives and B-roll for its scene.
- **The master build** keeps per shot: Keep → the shot; Reject → its kept alternative, else an AI stretch (intent: "in place of rejected Scene 1 · Shot 2: <its words>"); Trim → the shot trimmed. Adjacent AI stretches merge (as today).
- **The review film's cues** come from the render plan items (each carries its row label), not from parsing card text; the page gets start and end per row (for the highlight, the click-to-seek and the pause).
- **Wording:** options prompt rules 3, 4, 5, 7, 8, SCENES and SLIDES; the options and master steps; `vw.md`; the helper text; every server message naming slides; the page's help line. Word counts before and after; no number or condition lost; an independent check.
- **Versions:** server 0.77.0, plugin 0.64.0; design/35 row and old-ways list; design/49 line on deploy.

## 3. Edge cases
1. A scene with no footage → one AI shot; Keep AI / Find footage; the scene card shows "made with AI".
2. A scene of only footage, no AI → header plus shots; no AI line in its card.
3. A shot with two alternatives → Alternative 1 and 2, in order after the shot; keeping one rejects nothing else automatically, but a second Keep among them is refused ("keep only one of Shot 1, Alternative 1, Alternative 2").
4. An alternative of a different length → refused at check ("an alternative fills its shot's time exactly: N frames").
5. An alternative's clip used elsewhere in the cut, or the same part as its shot → refused.
6. An alternative on an AI shot → refused (an AI shot has no clip to replace).
7. Answering an alternative before its shot, or after the shot is kept → refused with the reason ("Shot 1 is kept: its alternatives are off"); changing the shot to Reject later re-opens them; a stale Keep on an alternative whose shot is now kept is ignored and shown as ignored.
8. Rejecting a short footage shot between two footage shots leaves an AI stretch under 3 s → the build refuses, naming it: "Rejecting Scene 1 · Shot 2 leaves 2.4 s of AI between two shots: keep it, trim a neighbour, or reject a neighbour too" (today's rule for a dropped piece, kept).
9. A trim that changes the scene's length → the build refuses as today ("trim one shot and extend another in the same scene").
10. Trim on an AI shot, an alternative or a scene header → refused.
11. The words of a shot: the narration words whose start falls inside the shot's time; none (a pause) → the strip shows the label only. Long words (a 6 s shot of about 17 words) → wrapped to at most two lines, smaller type before a third line is cut with "…".
12. Non-ASCII words (Tamil or Hindi films later, design/123): the cards today replace them with "?"; the strip uses the same font and limitation; recorded under "not covered" (design/123's work).
13. More than eight scenes → the colours repeat in order (8 colours); two neighbouring scenes never share one.
14. Many rows (a 40-shot film) → the page groups rows under their scene; the sticky film stays in view (as today).
15. Pausing: the user seeks backwards past a paused shot → it pauses again only if still unanswered; "Continue" without answering plays on and does not pause that shot again in that viewing; switch off → no pauses; a cue missing (old render) → no pause there.
16. The film was rendered before the answers changed (render is per version, not per answer) → the page reads answers live; nothing re-renders.
17. Two people answering on two screens → the last answer wins (as today); the page reloads after every click (as today).
18. Network failure on an answer → the page says so and keeps the film paused; nothing is recorded twice (one request at a time, as today).
19. VW-12 (at options today, answered on the old labels): see the question below.

## 4. Failure modes and how each is handled
- **An options file in the old shape** (SECONDARY, decisions with b_roll, KEEP_WITH_EDIT answers) → refused at check by name with the new way; nothing half-applied.
- **A stored version from before this release** (VW-12) → the page and `vw master decide` refuse to answer it ("this cut was proposed in the old form: the assistant proposes it again (`vw options propose`)"), so nobody answers old labels.
- **A render with a strip that fails to draw** (font, very long text) → the label alone is drawn; the render never fails for a caption (the corner label's rule today).
- **The pause logic fails in the browser** → the film plays through as today; answering is unaffected.
- **The build meets a kept shot and a kept alternative of the same shot** (answers changed out of order) → the shot's Keep wins; the alternative's answer is ignored and said so.

## 5. Not covered (planned)
- An unused alternative turning into B-roll live on the page (parked by SK).
- Non-Latin words on cards and strips (design/123).
- The visuals stage and later: unchanged; they receive AI stretches as gaps exactly as today.

## SK's decision (30 Oct 2026)
"Yes, re-propose": the list is approved; after the release VW-12's options are proposed again in the new form (its answers on the old labels are not carried over).

## The build (30 Oct 2026; committed, not deployed)
- **Server:** `stage2/slides.py` (rows by scene and shot, scheme 3, colours, words, cards capped at six lines of words), `stage2/stage.py` (needs-answer, refusals by name, KEEP/REJECT/TRIM, cues with start and end, the old form refused and shown on the page, the master built per shot; the swap to the other option removed), `stage2/validator.py` (one cut per scene, notes, alternatives checked like shots and of the same length on unused clips, B-roll never on a clip used as a direct match), `stage2/render.py` (the coloured card, the strip with the words and the dark red B-ROLL mark; the corner label, the blue card and the "#N |" head parsing removed), `stage2/render_jobs.py` (the master's AI card one line per item), `stage2/package.py` (the options shape), `main.py` (the answer passes through to be refused by name), `templates/review.html` (scene blocks, B-roll, dashed alternatives, Keep AI / Find footage, pause for answers with its switch, a switched-off alternative skipped), `procedures/v3.json` (options and master wording: `scripts/d127_wording_v3.py`, `scripts/d127_wording_v3_fixes.py`, trace `design/127-wording-trace.md`). Server 0.77.0.
- **Chat tool:** `vw.md`, the `vw-scene-review` helper, `vw.py` (labels, the second look carries alternatives' clips and no rank, `vw master slides`). Plugin 0.64.0.
- **A choice made inside SK's decisions (for SK to confirm):** keeping one alternative switches its sibling alternatives off (as keeping the shot does); changing that answer opens them again.
- **Independent check** (a helper that did not write the wording): no real loss; seven points of clarity, all applied in the fixes script (claims stay out of round 2, a rejected shot takes its kept alternative, "first answer", what an alternative is checked for, alternatives asked after the reject, a note's answer is the shot's own, a clip used twice among the build's refusals).

## Tests
- Server unit: 889 passed, 4 skipped (Chromium not installed); new: `server/unit/test_design127_review_pure.py` (34), the review page tests ported to the new rows (`test_review_page.py`); tests of the retired rows removed (design/125 O1–O3, O8 and the letter labels).
- Plugin: 349 passed; 3 failures known on Windows before this change (test_intake ×2, test_start_defect_paths).
- A real render on this PC (ffmpeg): the scene card, the AI card and the strip with B-ROLL drawn as designed; the review page copy in the in-app browser: the film pauses at the end of an unanswered shot, an answer plays on, a Reject opens the alternative, a kept shot's alternative is skipped.
- Docker tests (`server/tests`): stale before this change (design/35 Old ways 15: they still start runs without `--images` and declare gaps); 40 of the options, texts and plugin files fail for those reasons; not rewritten here.

## Not covered
- The Docker tests above (Old ways 15).
- A real review film from real footage and the live page: checked after the deploy on VW-12's new proposal.
- The desktop pause on a phone-size screen (desktop and laptop only, SK).
- Non-Latin words on cards and strips (design/123).
