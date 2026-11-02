# The builder's response to the process review (2 Nov 2026)

To the reviewer of `codex-review/process-findings.md`. The owner (SK) and the builder checked each finding in the code before deciding. This file says what was decided and why, what your reading could not see, and what to look for next. Please use it for a second round: find more issues of the same kinds, and leave alone what is decided here. The scope and limits of `design/133-codex-process-review-prompt.md` still apply.

Facts you could not see, which apply throughout:
- **Live state (2 Nov 2026):** server 0.80.0, plugin 0.67.0. HyperFrames (the motion drawing route) has been the default for new films since 1 Nov; SVG remains only on films started with `--drawn svg`. The second look now leaves a record on the server (design/129 P4, live since 1 Nov).
- **VW-12** (the trial film about rat-trap bond walls, started 30 Oct) is a trial run. It will be deleted and never completed. Exceptions kept only for it (`OLD_PROMPT_RUNS`, `OLD_PLAN_RULE_RUNS`) are emptied when it is deleted.
- **design/131** (leaner picture prompts) is on hold until more image tests. Finding 15 is the one exception; see below.
- **Tests run outside the code** that you could not see are listed under the findings they affect, for example the G07-S4-SH1 timing test of 1 Nov.
- **Our own review** (design/126) covered every stage up to the first cut, then the visuals stage up to the detailed plan. It stopped before the reference pictures, shot pictures, takes and drawn shots. Most of your findings are in that unreviewed part, which is why our review did not catch them.

## The decisions

### 1. Tool sentences that contradict the plan
- **What it is:** the server adds one fixed sentence per held tool. "{holder} holds nothing else" excludes a second tool held by the same person, and "fully inside the frame" contradicts a tool that the plan carries out of frame.
- **Decision:** yes, in part. Drop "holds nothing else" (the inventory line already lists everything allowed). Keep "fully inside the frame" except for a prop whose end is `carried_out`.
- **Why, and what you could not see:** you also proposed deleting the motion text's "each stays where it is, in plain view". **Rejected.** That end-state line comes from design/128, built after a real test on 1 Nov (shot G07-S4-SH1, a brick crushed in a testing machine). Without an end-state line the broken brick vanished; with it, both tries passed. The tests that prove a sentence earns its place are in the design notes and test folders, not in the code.

### 2. The golden picture never reaches the drawn-shot brief
- **What it is:** golden pictures are stored as kind `isolated` and recorded in `session['golden']`, while the brief selects kind `golden`, which no picture has.
- **Decision:** yes. Select by the golden record.
- **What you missed:** a golden picture is photographic and drawn shots are flat diagrams. The brief's "flat, clean, technical" must stay, so the picture guides shape and proportion and is not pasted into the drawing.

### 3. One cached film light in every picture
- **What it is:** `real_light_line` is measured once from the first six approved frames of any scenes, then added to every picture. It contradicts a scene's own light; VW-12 has outdoor site footage and an indoor laboratory shot.
- **Decision:** yes, changed. When the shot's scene has its own light, leave out the measured brightness and colour words.
- **What you missed:** keep "no studio light, no glow, no added saturation". That clause protects every picture from the glossy AI look, and dropping the whole paragraph would lose it.

### 4. The second-look helper strips B-roll
- **What it is:** the helper's rule 1, "related is not enough", has no exception for B-roll, which the options instructions allow under words without a specific claim.
- **Decision:** yes, with your wording (24 → 22 words).
- **What you could not see:** whether it happened on a real film. The second look left no record until 1 Nov; the new record will show it on the next film.

### 5. Old drawing snapshots remain after a correction
- **Decision:** yes. Clear the shot's snapshots when its uploaded project changes.
- **Added:** this matters because a false failure uses one of the two redo rounds, and after the second round a good drawing is "held" for the operator.

### 6. "Approve all specs" skips the not-this list
- **Decision:** yes. The bulk approval builds each material spec's not-this list, like the single approval (a failed model call still approves).
- **What you missed:** on the Pictures page, "Approve all specs" sits under a table of drawing specs only, but the same call also approves every waiting material spec. The operator approves real sizes that page does not show. Fix: list the material specs in that table too. Look for more approve-all or batch paths that approve more than they display.

### 7. The end check's "no one looks at the lens"
- **Decision:** yes, changed. Add the phrase only when no person's gaze target is the camera.
- **What you missed:** you proposed deleting it outright. It protects almost every shot, because AI people stare into the lens by accident and it reads as posed in a documentary.

### 8. The shot's progression sent as exact text to render
- **Decision:** yes. `copy: none` unless approved lettering exists; graphic states keep their labels.
- **Added:** if the writer copies that `copy` into `exact_text`, the server's exact-text rules force the sentence into the picture and its check. Your finding is more harmful than its row suggests.

### 9. Two sentences ask for an end picture with every start
- **Decision:** yes, with your wording.
- **Why our review missed it:** see the facts at the top. Also, when start-only became the default, only the places found at the time were updated; nobody searched the whole text for the old rule.
- **Added (SK):** a retired-sentences list, and a test that fails while a retired sentence is still in v3.json or the library. Every change that replaces a rule adds its old wording to the list.

### 10. The common part still describes the old drawing route
- **Decision:** yes. Rewrite the spots shorter, and put the old wording on the retired-sentences list.
- **What you missed:** a third spot. The "AI still" bullet still allows "a diagram or labelled picture without figures", which motion films refuse.

### 11. Scene helpers cannot see clips used by other scenes
- **Decision:** yes. Each scene file lists the parts of clips used in other scenes.
- **What you missed:** the reuse rule itself must not change. SK asked about it, and the fix keeps it exactly: the same part never; another part of a clip used in another scene only with a note of kind `reuse`, answered by the operator; a later, non-overlapping part in the same scene allowed (never side by side at one size). The helper's text must say exactly what the server's `validator.py` enforces, no more and no less.

### 12. The cost preview prices placed seconds
- **Decision:** yes.
- **What you missed:** the treatment's estimate has the same fault. Both must use the take's rounding: whole seconds, rounded up, at least the generator's minimum.

### 13. The drawing checker is forbidden to read last-upload.json
- **Decision:** yes, with your wording.
- **Added:** a wrong or missing fingerprint makes the server refuse the verdict, and the shot stalls.

### 14. The tool's reply after the motion brief skips the rules helper
- **Decision:** yes, with your wording. The operator's tick of open facts stays in the instructions.

### 15. Whole guidebooks loaded for one section
- **Decision:** yes, now (SK).
- **Why:** the builder first proposed parking it with design/131, on hold until image tests. SK decided it is the first step to improvement, because the AI reading only the relevant sections focuses better.
- **How:** the method goes to SK before anything is built. Sections are pulled by their heading when the step's files are packed; nothing is split into new files; a test per step proves each section is present.

### 16, 17 and 18
Not yet decided at the time of writing: drawn-brief scope, the older delivery rebuild command, and the "(design/130)" label in a refusal.

## What to look for in a second round

Each pattern below is behind at least one confirmed finding. Search the whole of v3.json, server/library, plugin/agents, plugin/scripts/vw.py and the server's message and added-line code for more of each.

1. **A rule replaced in one place and not in the others** (9, 10). For every "only when", "by default" or "no longer" in v3.json, search for older unconditional wording elsewhere: v3.json, the library guides, agent files and server messages.
2. **Fixed lines the server adds that contradict a plan value allowed later** (1, 7). For each enum or option in `visual_contract.py`'s plan model (gaze targets, prop ends, camera moves, motion `none`), check every fixed sentence or must line the server adds for it.
3. **Wiring by a name that never exists** (2). Kinds, roles, statuses and keys compared as literals that nothing writes.
4. **A value computed once per film, used per shot** (3).
5. **Two paths for one action that behave differently** (6). Single and bulk, chat and page, `--file` and the single command, approve and approve-all. Also anything that approves what the screen does not show.
6. **A helper given part of the film but held to a film-wide rule** (11), and a helper told not to read a file it needs (13).
7. **"Next" messages that point at the wrong step or a retired command** (14, 17).
8. **Estimates that use different arithmetic from the order that spends the money** (12).
9. **Text meant for the AI that ends up drawn in a picture** (8): any field fed into `copy`, `exact_text` or the picture checklist.

Keep to the limits of design/133: reading only, the smallest fix, wordings never longer, no enterprise or code-hygiene findings. Leave out anything already decided here or in design/35, design/129 and design/134.
