# design/209: the drawings and the materials approved on the page; the join after a proposal

**Status:** built on 16 Nov 2026 (server 0.106.0, plugin 0.90.0, plugin minimum raised to 0.90.0: every laptop updates); **not deployed**; SK's deployment word awaited.

**Why:** SK, 16 Nov 2026, from VW-24 run live by the team. Two things:

1. The question "the parts and sizes of this drawing" printed the stored record field by field (`dimensions: measure: thickness, part: slab, status: unknown, tried: …`), nine times. On VW-24: 37 size lines, 22 different sizes, 7 shown in more than one drawing, 30 of 37 "unknown". SK: "These questions are poorly presented. Serious UI UX issue … it's now time we convert this into an artifact so that the user can clearly know what they are approving."
2. The operator's assistant corrected two clip names in the plan's shared part after the plan was accepted, and "the tool refused to join the plan again"; it asked the operator how to go on.

SK approved the plan for (1) and asked for it on the artifact page, and for (2) in the same deployment.

## 1. The drawings and the materials on the page

- After the plan is accepted, the page's step is **Drawings and materials**: every material and every drawing in one visit, materials first.
- Each is written in plain words: what it is drawn as and why; the words it carries when not to scale; its parts; how they sit; the sizes to confirm as a small table; one line for sizes already confirmed; one line for sizes not known. The assistant's notes on what it tried are not shown.
- **Each fact is asked once.** A size approved earlier in the film, or on an earlier line of the page, is listed as already confirmed. The same size with another value in two places is shown in full in both and marked.
- The question says what a yes means: "Are the parts and the known sizes right?", "Are the parts right?", "Are these facts right?".
- "Done" in the chat records every answer through the same functions as before (`approve_spec`, `correct_spec`). An approved line stays on the page with its content, folded.
- The chat is the way back where the page cannot be shown, with the same plain wording.
- The plan's estimate now also names the reference sets: "estimate ₹X for the shots, and up to ₹Y for N reference sets, of the ₹Z limit" (plan page and check).

Where: `server/app/chat_flow.py` (`_spec_parts`, `_spec_views`, `_spec_text`), `server/app/page_flow.py` (`_spec_page`, `_spec_lines`, `_spec_answer`), `server/app/visuals_stage.py` (`set_estimate`, two messages), `plugin/pages/decisions.html`, `plugin/scripts/vw.py`, `scripts/d209_wording_v3.py`, `plugin/commands/vw.md`.

## 2. The join after a proposal

**Cause.** The join refused to overwrite the joined plan when that file was newer than the gap files. The base file was not in the comparison, so a corrected shared part could never be joined; and the tool itself rewrites the plan file after a proposal, which was taken for a hand edit. The instructions also told the assistant both never to edit the joined plan and to fold a drawing correction into it, so a fresh join could silently drop a correction held only by the server.

**Rule now.** The base and the gap files are where every change is made, before a proposal and after one. A hand edit is the plan file differing from what the tool last wrote (a fingerprint in `out/.plan-join.json`), not a file time. After a proposal the join carries the files' changes onto the server's current plan and keeps what was corrected there; a part changed on both sides differently is refused by name with what to do. A run folder with a proposal and no record of its join (VW-24) is told the working way: get the server's plan, change it there, check, propose.

Where: `plugin/scripts/vw.py` (`plan_join`, `_merge3`, `_plan_written`), `plugin/agents/vw-plan-gaps.md`, the plan part of the instructions.

Old ways 99 and 100 are in `design/35-decision-log.md`.

## Not verified

- The page on claude.ai with a real film, and the whole loop on an operator's machine. The builder saw the page on a local copy in a headless browser with a round made by the server's own function.
- The join against the real server and a real plan: plugin unit tests only.
- The reference-set estimate against a real round's cost; it is an upper figure ("up to").
- The database tests were not run.

## Not covered

- The reference pictures, the stills and the takes are still asked in the chat (the reference steps wait on SK's answer about pictures on claude.ai).
- The assistant still writes its notes on what it tried in technical words; they are no longer shown to the operator.
- `vw visuals spec` stays for a correction said in the chat.

## The critic's check before the deploy

One read-only reviewer checked the merged change for faults that stop a run, lose the operator's work, or tell the assistant something the server refuses. The first join on a new film was read end to end and is sound. Three critical faults were confirmed and fixed, each with a test seen failing first:

1. **After a proposal the join refused any file change that added a field the server stores with an empty default** (a material spec, an outfit, a camera move: about 28 fields). It named a clash the server never made. Now a field the files add where the server holds only an empty default goes in; a field the server really changed is still named.
2. **A drawing was approved with a size the operator corrected in the same visit.** The drawing showed the size only as "Already confirmed"; the yes was recorded although the material it rested on was sent back. Now corrections are recorded first, and such a yes is not recorded: the drawing is asked again.
3. **A yes the server refuses for missing research left the line open and told the assistant only to send the link again.** Now the assistant is told the drawing is its own to fix: complete it in the plan, check, propose again.
