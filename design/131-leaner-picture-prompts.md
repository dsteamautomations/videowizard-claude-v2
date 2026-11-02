# design/131: leaner picture prompts

2 Nov 2026. Status: **ON HOLD (SK, 2 Nov 2026): needs more time to address the issues. Nothing is built.** SK set aside the prompt-test results as a basis for prompt changes (C1 to C5) until more image tests are run (quality `medium`, 2048x1152, more photo prompts).

**Evidence:** `prompt-test/report.html` (11 real prompts from VW-6, VW-9 and VW-12 against one change at a time, judged blind), `image-edit-test/results.html` (the edit loop) and `diagram-compare/compare.html` (HyperFrames against GPT Image). Every run used the live GPT Image 2.5 setup, apart from VideoWizard.

**Older way:** today's prompt rules (section 2, "today") stay in force until this is built. The older library snapshot stays for sessions already pinned to it (section 3).

## 1. The request, restated

Make the picture prompts the operator's Claude writes shorter and plainer: every must-have stated plainly, nothing else. Remove the rules that add length without helping, and fix the rules that contradict each other.

The tests found, on 7 photos and scenes:
- **Short wins more often.** A short prompt with every must-have came first 4 times. Today's long prompt came first 3 times and last 3 times, called "a polished render" each time.
- **Where the long prompt won,** it was holding a must-have the short one dropped (the trowel hand, the lorry's place in the frame, the dust on the plinth).
- **Restating a reference picture added nothing:** every version kept the same man.
- **On both diagrams, stating the construction facts won.** Diagrams with words now go to HyperFrames on motion films (design/130 §12), so that lesson applies to scene prompts and to the HyperFrames brief.

## 2. The changes

Library paths are under `server/library/vwlib-2026-10-29-3d60877d3d23/library/`. Library changes go into a new snapshot folder made in the builder thread, as before (design/89 batch 4).

| # | Today | After | Where |
|---|---|---|---|
| C1 | The prompt follows a house shape (Asset, Scene, Subject, Details, Exact text, Constraints, the standing line), filled by quotas | **The must lines are the spine.** One asset line (what picture, its framing), then one plain sentence for each `must` line of the checklist, then the exact text and the constraints. No section labels required. A `should` line goes in only when the picture needs it. | RULEBOOK §1, §9; FACT-SHEET B1; answer-form.videowizard.md (example); procedure v3 "later" §5-6 |
| C2 | "Five to twelve named objects and surfaces … two to four light and material facts" | **Removed.** Name what the shot must show and what must not appear; no counts. | RULEBOOK:56 (second half); 00-method/craft.md:217; FACT-SHEET:135 |
| C3 | The de-slop block on every real-looking picture: "three or more located imperfections", "low micro-contrast, no added sharpening", the glow ban, each deviation named twice for people | **One look line, at most** ("a frame from handheld phone footage, flat natural colour"). de-slop.md stays in the library as reference and is no longer opened by default. The server's light line keeps the footage's light facts and drops its duplicate glow sentence. | RULEBOOK:66; VW-MAP opened files; visuals_stage.real_light_line:994 |
| C4 | Scene prompts carry no subject facts | **The subject's facts go in.** The preparation packet carries the matching subject rules (design/130 `server/subject_rules`, the same `_subjects_of` match). The procedure says: a picture that shows the subject states the facts it shows (a rat-trap wall is bricks on edge with headers). | visuals_stage packet / prepare; procedure v3 §5-6 |
| C5 | Prompts with a reference picture often re-describe the whole reference after "Image 1" | **Do not restate it.** The Image 1 line, then only what changes, plus the small details that must survive and are hard to see (dust, a wrist thread). RULEBOOK:41 already says this; the golden-picture example and the procedure's §9 wording follow it. | answer-form example; procedure v3 §9 |
| C6 | The answer declares a six-check `lint` copied from an advertising tool, never checked by the server; the job opens deterministic-checks.md and its phrase tables | **The `lint` field is retired and the tables are no longer opened.** The server ignores `lint` in this release and refuses it by name in the next (old ways). | answer-form.videowizard.md:24, 51; VW-MAP:11; library.check_answer |
| C7 | The standing line "Render only explicitly requested image text…" is in every prompt (and nine library files); the server also appends its own text block and checks text on every picture | **The text rule is said once, by the server.** With exact text: its existing block ("Render exactly this text…, nothing else"). With none: one line it appends ("No text, letters, numbers or logos anywhere"). The writer no longer adds the standing line. | RULEBOOK:24 and its copies; visuals_stage:1136; the request builder |
| C8 | Contradictions: craft.md recommends "hyper-realistic" and `8K_UHD` (banned at RULEBOOK:56); diagram-in-states suggests "centre" (the lint refuses it) and labels in quotes in keep lists (the quote check refuses them); the measured-distance rule forces words like "three paces" | **Resolved:** the banned words are removed from craft.md's example; diagram-in-states follows the lint. The distance rule accepts a relation to a named landmark ("beside the plinth", "behind the stack") without a number, and still refuses "centre" or "middle" alone. | craft.md:83-85, 113; diagram-in-states.md:27, 72; library.py:223-227 |
| C9 | The fix prompt keeps "everything else, the framing, the light"; the answer's `keep_list` is written but never read | **The fix prompt names what to keep** from the picture's `keep_list` when it has one; the generic line stays only when it has none. | image_check.fix_body:470-475 |

**Looked at and not changed:**
- **The rewriting route:** gpt-5.5 rewriting a short prompt came second both times. It isn't adopted; prompts stay on the Images API.
- **Quality:** stays `high` (VW-MAP, SK's decision). `xhigh` gained nothing in the test. `medium` was not tested.

## 3. Requirements check

**Unstated but expected**
- Every server check of a prompt still holds: exact text present and placed, no logo, no model name or size, the Image k role lines, at least one `must` line.
- The same rules serve Gemini runs; nothing here is specific to GPT Image.
- A session records its library version. A run already pinned to the 29 Oct snapshot keeps it; new sessions take the new snapshot.
- The procedure's word budget for the visuals stage goes down or stays the same (`test_design125_stage7_c_pure.py`).
- Wording changes to v3 go through a `scripts/d131_wording_v3.py` chained into `c1_split_v3.py --check`.

**Edge cases**
- **A shot whose checklist has many must lines** (the mason sheet): the prompt is long because the facts are many. That is fine; only filler goes.
- **A picture with no exact text:** the server's one no-text line. With exact text in two scripts (English, Hindi): the server's block, letter for letter, as today.
- **A fix of a picture with no `keep_list`:** today's generic keep line.
- **A film with no subject rules file:** no subject facts are added, and nothing fails.
- **A scene that shows no part of the subject** (a road, a lab): no subject facts are needed. The rule applies only where the picture shows the subject.
- **An older answer file that still carries `lint`:** accepted and ignored in this release.
- **A writer who still adds the standing line:** harmless. The server does not refuse it.

**Failure modes**
- **A short prompt drops a must-have:** C1 makes the must lines the spine, so a must cannot be dropped without the writer leaving a checklist line out. The picture check reads the same lines, and a fix names what to keep (C9).
- **The look drifts back to a render:** the one look line (C3) is available. The test split 2 to 2 on it, so it stays optional.
- **A subject fact is wrong:** subject rules are edited with `vw motion rule` (design/130), with the operator's words.

## 4. Tests

**Unit tests, written first:**
- The library snapshot manifest.
- `check_answer` ignores `lint`.
- `check_prompt` accepts "beside the plinth" and still refuses "in the centre".
- The request builder adds the no-text line once and never doubles it.
- `fix_body` names the `keep_list`.
- The packet carries the matching subject rules.
- The procedure: the split check and the budget.

**Acceptance on real pictures:** a fresh writer helper, following only the new rules, rewrites the seven photo prompts of the test (kiln yard, mason, family, lorry, lab, home, plinth). Each pair is generated and judged blind against today's prompt. The change is accepted when the new prompt ranks equal or better on at least 5 of 7, and drops no must line.

## 5. Older ways

| Older way | What happens |
|---|---|
| The house shape with quotas (C1, C2) and the de-slop block (C3) | Retired in the new snapshot. Runs pinned to the 29 Oct snapshot keep them until those runs close. |
| The `lint` field (C6) | Ignored in this release. Refused by name in the next ("lint is retired: the server checks the prompt itself"). |
| The writer's standing line (C7) | No longer required. Accepted if present; its removal from the library templates is the retirement. |

## 6. Not covered

- Start and end keyframe pairs were not part of the test; C5 applies to them by the same reasoning, unmeasured.
- Quality `medium` for photos: a separate test if SK wants it.
- The server-appended blocks (sizes, heights, signs of use, the composed lines of design/110-124) are unchanged. They were not varied in the test.
- One run per prompt in the test: a clear direction, not a measurement. The acceptance step above is the measurement.
