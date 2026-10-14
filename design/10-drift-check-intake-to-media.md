# 10 — Drift check: v1 flow vs v2 build, intake → media

Date: 14 Oct 2026. Question from the owner: "is there any other change to the flow besides start/title/client?"
Method: v1's published procedures (`defs/intake-0.4.0`, `brief-0.4.0`, `script-0.5.0`, `voice-0.5.7` + prompt v2.7, `media-0.7.0`) and backend checks (`workflow.py`, `stages.py`, `voice.py`) compared with v2's stage table (`server/procedures/v1.json`), plugin scripts (`stages_text.py`, `stages_av.py`, `vw.py`) and `commands/vw.md`.

Origin column: **decided** = in design/02 §1 or an agreed DROP (design/05); **mine** = I changed it without asking; **same** = v1 behaviour kept.

## 1. Start (fixed today)

| v1 | v2 before today | v2 now | Origin |
|---|---|---|---|
| Run created from the script; client mandatory, resolved against the shared Active clients directory; title chosen at intake from ≤3 suggestions or typed by the user | `vw start --title` required, client free text | client mandatory and resolved (`vw clients`, `CLIENT_UNKNOWN` with candidates); no title at start; `vw stage intake record --title` sets the chosen title | mine → restored |

## 2. Intake

| Aspect | v1 | v2 | Origin |
|---|---|---|---|
| Source input | pasted text or TXT/MD/Fountain/DOCX/PDF via connector or browser upload | file in `runs/<code>/in/` (same formats); pasted text not documented | mine (gap: say "write pasted text to in/source.txt") |
| Cleanup | model returns line numbers to remove; backend removes exactly; never retypes | same | same |
| Titles | ≤3 suggestions, user picks or types own | same (since today) | same |
| User edits to the script at acceptance | `accept_intake` carried the exact accepted script, so the user could hand-edit wording at intake ("user-authorized preparation") | only removals at intake; wording edits happen at the script stage | mine, minor. Script stage covers it; v1's prompt also said wording edits belong there |
| Prompt | VW-SCRIPT-INTAKE 1.2.1 | ported verbatim | same |
| Readable-copy gate (PDF OCR) | yes | yes (`needs_readable_copy`) | same |
| Attempts | unbounded | cap 3 → operator decision | decided (rule 4) |

## 3. Brief

| Aspect | v1 | v2 | Origin |
|---|---|---|---|
| Five fields + constraints, reasons | yes | yes | same |
| Questions with `required` flag; **accept refused until required questions are answered**; answers stored verbatim per question id, never prefilled | enforced by the server (`stages.py:117`) | the proposal shape has `questions`, but record ignores them: no answers map, no required-question check | **mine — real drift**. Fix: `questions[].required` must have an operator answer in `answers{}` before record; store answers verbatim |
| Save partial supplied input before acceptance (`save_brief`) | yes | no separate save; the proposal file is edited and re-recorded | mine, acceptable (file is the draft) |
| Prompt | VW-BRIEF 2.0 | ported verbatim | same |

## 4. Script

| Aspect | v1 | v2 | Origin |
|---|---|---|---|
| Complete `spoken_text`, notes, assessment, changes | yes | yes | same |
| Changes shape | `before / after / reason` (exact excerpts) | output shape says `what / why`; prompt says before/after/reason | **mine — mismatch**. Fix: shape = `before, after, reason` |
| Acceptance binds intake digest + brief digest | yes | yes (`source_intake`, `source_brief`) | same |
| Passages / content digest for voice | yes | yes (`reference-paragraphs-v1`) | same |

## 5. Voice

| Aspect | v1 | v2 | Origin |
|---|---|---|---|
| Published voice prompt (VW-VOICE 2.7: recommend qualities from the Brief, do not infer accent/gender from client name, filters are discovery not approval, library voices, no name-only matching, max six auditions per paid batch) | yes | **no prompt in the stage table**; only one paragraph in `commands/vw.md` | **mine — drift**. Fix: port voice-2.7.md as the voice stage prompt (strip the browser/connector sentences) |
| Discovery: account/library catalog with filters, previews, add library voice | yes | yes (`vw voice catalog/preview/add-library`) | same |
| Saved voice plan (shortlist ids, filters, per-voice notes, excerpt, model, settings) before auditions | yes (`save_voice_plan`) | no persisted plan; the agent passes voices/excerpt on the command line | mine. Low impact: the run folder keeps the conversation; but the shortlist and notes are not on the run record |
| Audition excerpt must be one contiguous passage of the accepted script | server-checked | only length ≤ 3000 checked | **mine**. Fix: check excerpt is contiguous in `spoken_text` |
| Auditions per batch ≤ 6 | server-checked | not checked | mine. Fix: cap at 6 per `vw voice audition` |
| Explicit `choose_voice` before narration | yes | choice is implicit in `vw voice narrate --voice` | mine. Keep (one step fewer; the narration record names the voice) |
| Narration bound to the accepted script digest; one open job at a time; recover/resolve; no automatic uncertain retry | yes | yes | same |
| Paid authorization flag | agent-set `paid_authorized` | information only | decided (9) |
| Listening | authenticated browser player on `/runs/{id}/voice` | `vw voice fetch` downloads to `out/`; operator opens the file; no web player | mine. Acceptable for the walkthrough; a web player is a later nicety |
| Effects / voice lab | existed, never used | dropped | decided (F-13, F-14 DROP) |
| Default model | Eleven v4 | Eleven v4 | same |

## 6. Media

| Aspect | v1 | v2 | Origin |
|---|---|---|---|
| Upload via browser library; up to 50 videos; shared client library reused across runs | yes | clips in `in/`, one signed PUT + receipt, ≤ 200 MB each; per run only | decided (F-16 DROP, upload protocol collapse) |
| Media prompt (operator rules: preserve names, immutable bytes, no analysis claims, source-audio policy asked once) | yes | **no prompt / steps in the stage table**; rules partly in `vw.md` | mine. Fix: port the media prompt into the stage table |
| Dedupe identical originals | yes | yes | same |
| Analysis starts only as an explicit step | yes | yes (`vw analysis start`) | same |

## 7. Cross-cutting (all decided, listed for completeness)

Revision/`expected_revision` → server-owned order (`GET next`); per-stage prose release names → one pinned procedure version per run; browser acceptance → chat quote; chunked uploads → sign + PUT + receipt; `paid_authorized` → information; unbounded repeats → attempt caps.

## 8. What I will fix before you test (small, no new design)

1. Brief: required questions need operator answers; answers stored verbatim.
2. Script: changes shape `before/after/reason`.
3. Voice: port VW-VOICE 2.7 as the stage prompt; contiguous-excerpt check; ≤ 6 auditions per batch.
4. Media: port the media prompt as the stage prompt.
5. Intake docs: pasted text goes to `in/source.txt`.

Left as is (named above): no persisted voice plan, implicit choose_voice, file-based listening, intake wording edits deferred to the script stage.
