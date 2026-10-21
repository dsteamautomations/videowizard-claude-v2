# design/63 — Two rules after the operator has seen both cuts

Status: proposed, 21 Oct 2026. SK holds the review page design as built (design/62): both cuts of a scene stay fully visible and comparable; nothing is folded away. Only what happens after the choice changes.

## Rule 1 — keeping both cuts of a scene is said at once, not at the build

**Today** keeping #1 and its backup #2 is accepted silently; `vw master build` refuses later with "both options kept; keep one", a round after the answers.

**Change.** The slide rows (`stage2._slide_rows`, served to the page and to `vw master slides`) carry `conflict` on a scene or backup slide that is kept while the other cut of the same scene (same `beat_id`) is also kept: `"#2 is also kept: reject it or this one"`. The page shows it in red under the row's answer and counts such scenes in the top line ("2 scenes with both cuts kept"); the `vw master slides` line adds "both cuts kept: scene 2 (#1, #2)". The `decide` reply carries the same `conflict` so the page can say it the moment the second Keep is clicked. The build keeps its refusal as the backstop.

## Rule 2 — slides inside a rejected cut need no answer

**Today** the build demands an answer for every numbered slide, including the decision slides inside a cut the operator rejected, whose answers cannot change anything (the build skips a rejected cut).

**Change.** A decision slide whose cut is REJECTed is `needs_answer: false` with `why: "inside rejected #2"`: the page greys the row and shows no buttons, the counter and the waiting list leave it out, and `build_master` no longer lists it as missing. The rule is computed from the current decisions, so un-rejecting the cut brings its questions back. An answer already given inside a rejected cut is kept and ignored. One helper, `stage2.needs_answer(slide, decisions_by_option)`, used by the rows and by the build, so the page, the chat and the build agree.

Not changed: the film, the slide order, the two cuts shown in full, the buttons, KEEP_WITH_EDIT, the chat interim.

## Addendum — why the page felt slow, and what changes (SK, 21 Oct)

Measured in the code, not yet on the wire (the browser pane had lost its sign-in): every load of the page's data did four storage round trips to Supabase from the VM (the session, the version document, a write of the session back, the render plan) plus the next-stage queries, and every button click did a decide (session read and write) **and then** a full reload. That is six storage round trips per click, each a few hundred milliseconds. Changes: the view reads the session once, loads the version document only when the version carries no slides (every version since design/21 carries them), writes nothing, and keeps a rendered version's slide cues in memory; the act reply carries the fresh view, so a click is one request. The video gets its own compositing layer (`will-change: transform`), the usual fix for sluggish scrolling beside a sticky video. Expected: a load at one storage read, a click at one read and one write.

## Tests first

`server/unit/test_review_page.py`: a load reads the session once, writes nothing and skips the document, the second load reuses the cues; both cuts kept → both head rows carry `conflict` naming the other, progress unchanged; one rejected → its inner decision rows `needs_answer` false with `why`, left out of `of` and `waiting`; un-rejected → they count again; `missing_answers` for the build ignores slides inside a rejected cut and still names the rest; the template renders `conflict` and `why`. plugin: the slides line names the scenes with both cuts kept.

## Not covered

server/tests (Docker); the first live use is the new run's master stage.

## Versions

Server 0.21.2 → 0.21.3; plugin 0.20.0 → 0.20.1 (the slides line). Both deploys; the workers restart; the operator restarts Claude Code once.
