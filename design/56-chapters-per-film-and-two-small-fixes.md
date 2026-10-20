# design/56 — Chapters belong to the film (L10), the refusal names its command (L11), the vw tool allowed without asking (L12)

Status: proposed, 20 Oct 2026. Batch point: VW-6 at the media stage (design/49). Nothing here touches VW-6's recorded brief; the checks apply from the next brief record.

## L10 — chapters are proposed from this script, never carried from the last brief

**What went wrong.** VW-4's brief named nine narrative chapters as identifiers (`Chapter_1_The_Need_For_Better_Building` …). At VW-5 and VW-6 the brief prepare showed them under "what this client said at their latest brief" as recommendations, the step asked "same as last time, or changes?", and the operator said yes. The film's chapters were copied from another film. On VW-5 SK corrected them by hand to construction steps.

**Why.** The production values that repeat per client (languages, speaker on camera, brand and safety rules) are rightly recommended from the last brief. Chapters are not a client value: they are what *this* footage will show, in film order (design/53 L4). Listing them with the others made them look like a setting to confirm.

**Change.**

1. `plugin/scripts/stages_text.py` `last_brief_text`: `process_stages` leaves the recommended list. The last brief's languages, speaker, rules and runtime still show. (Alternative not taken: show the last film's chapters "for style only"; it is the same temptation with a label.)
2. `server/procedures/v2.json`, brief step 2 and step 3: one sentence each. Step 2: chapters are this film's, from this script and what its footage will show, named plainly in a few words ("Mixing the mortar", "Pointing the joints"); they are never taken from a previous brief, and the "same as last time" question covers only the other production values. Step 3: present the chapters as a numbered list of plain names (unchanged) and add: a chapter name is words, not an identifier.
3. `production_inputs` (the plugin's brief record check, where the generic-names rule already lives) refuses identifier names with one message: a name containing `_`, a name starting with a numbering token (`Chapter 3`, `Stage_2`, `Scene 1`, `Part 4`, `3.`, `3)`), a name with no letter, or a duplicate. Message: `out/brief.json: production.process_stages are the plain names of what the footage shows ("Mixing the mortar"), in film order: no Chapter_N or Stage N prefixes, no underscores, no numbering, no duplicates.` The list is numbered when presented; the names carry no numbers.

**Downstream.** Analysis tags clips with these names and the options stage maps scenes to them by exact name; both take whatever names the brief recorded, so plain names change nothing there. VW-6's brief keeps its identifier names (trial runs are disposable; the check applies at record only).

**Tests first** (`plugin/tests/test_brief.py`): the prepare prompt shows the last brief without `process_stages` and still with the languages; `production_inputs` refuses `Chapter_1_Need`, `Stage 2 Mixing`, `3. Curing`, a duplicate, and accepts `['Mixing the mortar', 'Pointing the joints']`; the step text test (`test_brief` prompt/step assertions) checks the new sentence. The server has no brief validation (the brief has one front end, the chat), so nothing moves to the server.

**Not covered.** A live brief on the next run is the only check that the child follows the sentence; the refusal is the backstop.

## L11 — the refusal names the exact command

**Today.** `voices.ensure_on_account` refuses a voice the account does not hold and the register has no identity for: "…Run `vw voice catalog` with filters that list it…, or `vw voice add-library --owner <id> --voice <id>`." (wording from the defect 16 fix). Since that fix every voice the catalog or the page lists is remembered, so the refusal is now rare; when it fires the child still has to guess the filters.

**Change.** Neither front end sends a name with a narration request; the register row (`vw2_voices`) holds one when the voice was ever listed. `ensure_on_account` uses it: when the register knows the voice by name the message says `Run \`vw voice catalog --search "<name>"\` (the tool remembers the library voices it lists), then submit again`; when the register has never seen the id it says so: `the tool has never listed <id>: run \`vw voice catalog\` with filters that show it, or \`vw voice add-library --owner <id> --voice <id>\``. Nothing else changes.

**Tests first** (`server/unit/test_voices_pure.py`): the message names the search command when a name is given and the general wording when not.

**Not covered.** server/tests (Docker).

## L12 — the vw tool runs without the classifier's question (SK's side)

The desktop app's auto-mode classifier blocked `vw voice jobs --wait 180` and `vw voice jobs` on VW-6, and two voice-add commands before that. Every vw call is one command shape: `python "/Users/vasudha/.claude/plugins/cache/vw-local/vw/<version>/scripts/vw.py" …`. An allow rule in the operator folder's `.claude/settings.json` lets those through without a question. The exact line follows the syntax check (below); nothing in this repository changes for L12, and the operator restarts Claude Code once after the edit.

**The line** (operator folder, `.claude/settings.json`, next to `env` and `enabledPlugins`):

```json
"permissions": {
  "allow": [
    "Bash(python \"/Users/vasudha/.claude/plugins/cache/vw-local/vw/*/scripts/vw.py\" *)"
  ]
}
```

Why this shape (from the Claude Code permissions docs, checked 20 Oct): a `*` may stand anywhere in a Bash rule and matches the literal command text, so the version segment of the cache path (`0.18.0` today) survives plugin updates; the rule is pinned to the one script and does not allow `python` in general. Broad interpreter rules such as `Bash(python*)` are dropped on entering auto mode, so they are not an option. Quotes are literal: the rule matches the double-quoted form the plugin instructions prescribe and every one of the 20 vw calls in VW-6's transcript used. Allow rules resolve before the classifier. Two things the docs leave open, to be tested on the first vw call after the restart: whether the desktop app treats this path-pinned rule as "narrow" and keeps it in auto mode, and the folder's workspace-trust state (project allow rules apply only in a trusted folder).

## Versions and deploy

Plugin 0.18.0 → 0.19.0 (L10 code and tests), server 0.20.0 → 0.20.1 (L11; the procedure text is served by the server, so the step sentences need the server deploy too). Both deploy scripts; the workers restart; SK restarts the operator's Claude Code.
