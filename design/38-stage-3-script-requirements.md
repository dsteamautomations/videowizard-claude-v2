# 38 — Stage 3 (script) improvements: requirements (approved by SK 18 Oct 2026, implemented the same day)

Source: the stage 3 review run with the stage review prompt on 18 Oct 2026 and SK's decisions on its 6 findings. Five go ahead (3.1–3.5); 3.6 confirmed the stage's constants and carried "split beats at sentence boundaries when a paragraph runs long" to the stage 6 review. Nothing here makes a paid call. VW-3 is past the script and is not affected; every change is backward compatible with the 0.3.0 plugin and the 0.4.0 server.

## Decisions carried from the review
- The record **rebuilds the spoken text from the cleaned script plus the accepted changes** and refuses a text that differs (3.1).
- Every change carries the **operator's decision**: accepted, rejected or reworded with the operator's wording; rejected changes stay in the file as history (3.2).
- Script prompt: minimal cut of the v1 machinery plus two sentences (3.3); the stage receives the brief's answers, the narration language, the rules and the chapters (3.4).
- When the assessment names a figure the message rests on, the assistant **proposes** a web search under the warning; it never searches on its own (3.5).

## A. Plugin changes (`plugin/`)

| # | What changes | Why | Where |
|---|---|---|---|
| 3.1 | `script_record` rebuilds the text: start from the cleaned script (`cleaned_script`, already digest-checked); apply every change whose decision is accepted or reworded, in file order: a non-empty `before` must occur **exactly once** in the working text (none → "before not found: quote it exactly"; more than once → "quote more words so it occurs once") and is replaced by `after` (reworded: by `operator_wording`); an empty `after` is a deletion; an empty `before` is an insertion, applied as: `after` must occur exactly once in the submitted spoken_text and is removed from a copy of it for the comparison. Then compare the rebuilt text with the submitted text (insertions removed), whitespace collapsed, exactly otherwise; on a mismatch refuse with the first differing sentence (split on `. ! ?` followed by space or end) of each side. Zero accepted changes: the submitted text must equal the cleaned script. | The stage's two firmest rules become a refusal. | stages_text.py `script_record`, new helpers `apply_changes`, `first_difference` |
| 3.2 | Each change requires `decision` ∈ {accepted, rejected, reworded}; reworded requires a non-empty `operator_wording`; a missing or unknown decision is refused ("every change needs the operator's decision before record"). Rejected changes stay in out/script.json and are not applied. Summary gains `changes_proposed`, `changes_accepted` (accepted + reworded), `changes_rejected`; the existing `changes` count becomes `changes_accepted`'s value. | The proposal and the operator's choice per item are the record. | stages_text.py |
| 3.4 | `script_prepare` adds to `inputs`: `answers` (the brief's answers map), `narration_language`, `brand_and_safety_rules`, `chapters` (the brief's `process_stages`), read from the brief output's summary. | The wording pass sees the whole brief. | stages_text.py |
| — | `plugin.json` 0.3.0 → 0.4.0. | | .claude-plugin/plugin.json |

## B. Server changes (`server/`)

| # | What changes | Why | Where |
|---|---|---|---|
| 3.3 | Script prompt, minimal edit: remove the paragraph "Submit propose_script … needs no second chat approval."; remove "Fetch context after saving and compare the persisted text, notes and source linkage." and "Use the current expected run revision and one stable request ID … never replacement projects."; remove "Do not substitute old prompts or a paid model. After acceptance report the saved run and fetch its published Voice context when the employee wants to continue."; "The backend preserves the submitted text, but the operator must compare it against the source and expose every substantive edit." → "The record step rebuilds the text from the cleaned script plus the accepted changes and refuses anything else, so every edit must be a listed change with an exact `before` that occurs once."; "employee" → "operator" (six places); add after the before/after review sentence: "After the operator decides, each change carries `decision`: accepted, rejected, or reworded with `operator_wording`; rejected changes stay in the file and are not applied."; first paragraph lists the new inputs: "the operator's answers at the brief, the narration language, the brand and safety rules and the chapters of the film". | Stale v1 mechanics; a home for 3.1, 3.2 and 3.4. | procedures/v2.json script `prompt` |
| 3.2, 3.5 | Script steps: step 2 adds "`changes` each with before, after, reason; after the operator decides, add `decision` (accepted \| rejected \| reworded, with `operator_wording`)"; step 3 adds "When the assessment names a figure or claim that the message rests on, propose a web search: say 'I am deviating from the usual procedure. I want to check X in the script, because the message rests on it. A different figure may change the wording.' Search only after the operator says yes; show what you found; any change is a normal before/after the operator decides."; step 4 adds "The record step rebuilds the text from the cleaned script plus the accepted changes and refuses a text that differs." | Decisions and the web rule where the assistant reads them. | procedures/v2.json script `steps`, `output_shape` (`decision`, `operator_wording` on a change) |
| — | `SERVER_VERSION` 0.4.0 → 0.5.0. | | config.py |

## C. Unstated but expected
- The comparison ignores whitespace only. A punctuation change is a change and must be listed; the prompt already says "keep unchanged text exact".
- A change that spans a paragraph break is allowed (the prompt says changes can cross physical lines); the rebuilt text keeps the break unless the change removes it.
- An old proposal without `decision` fields (written by a 0.3.0 plugin's assistant before the deploy) is refused with the message above; the assistant adds the decisions and records again. No run is at the script stage today.
- The insertion rule (empty `before`) cannot place the text; it only proves the inserted wording is present once. An assistant that wants a precise placement lists the change with a short `before` anchor and the anchor plus new words as `after`; the prompt sentence says so.
- The passages and beats are computed from the rebuilt text as today; ids unchanged.

## D. Edge cases
| Case | Expected |
|---|---|
| zero changes, text equals the source up to whitespace | recorded |
| zero changes, one word differs | refused; message names the differing sentence on both sides |
| accepted change, text matches source + change | recorded; `changes_accepted` 1 |
| accepted change, text also carries an unlisted rewording | refused with the differing sentence |
| rejected change still present in the text | refused (the rebuilt text lacks it) |
| reworded change: `operator_wording` present in the text, `after` absent | recorded |
| `before` occurs twice in the source | refused: "quote more words so it occurs once" |
| `before` not found | refused: "before not found: quote it exactly" |
| deletion (`after` empty) and the text omits the sentence | recorded |
| insertion (`before` empty) and the text contains `after` once | recorded |
| change without `decision` | refused |
| prepare: brief with answers, Tamil narration, rules and chapters | all four in `inputs` |
| assessment names a figure the message rests on | the assistant proposes the search with the warning (instruction; verified by reading, not by test) |

## E. Tests (written first)
Layer one, `plugin/tests/test_script.py` (new, runs on this Mac): every row of §D for `apply_changes` and `script_record`, `first_difference` on two sentences, the prepare inputs, and the prompt and steps clean of `propose_script`, `save_script`, `accept_script`, "employee", "backend", "browser" and carrying "rebuilds the text" and "I am deviating". `test_brief_script_binding.py`: the script record case gains `decision` and an equal text.
Layer two, `server/tests` (Docker): T7's script proposal becomes the cleaned source with zero changes, then after `revise` a second record with one accepted change (`before: "pressed, not fired"`, `after: "pressed rather than fired"`) and a text that matches, asserting `changes_accepted` 1 and the beats unchanged; T4's blank text still refused; T5 unchanged ("Just narration." equals its source); test_planning and test_voice_media: their `in/source.txt` becomes the two-paragraph text they later record ("Earth blocks are pressed.\n\nNot fired.\n"), so the script equals the source with zero changes.

## F. Not covered
- server/tests cannot run on this Mac; compile-check only until a Docker machine runs them.
- The proposal of a web search for a figure (3.5) is the model's behaviour; the steps are verified, the behaviour is not.
- Beat granularity for one-paragraph scripts is not in this batch; it is reviewed at stage 6.

## G. Deploy order
1. Server (`deploy-server.sh`, workers restart): tell SK first.
2. Plugin (`deploy-plugin.sh`); the operator restarts Claude Code.
3. design/35: a row for the stage 3 decisions.

## H. Estimate
Plugin A with tests: about half a day. Server B: an hour. Deploys: an hour.
