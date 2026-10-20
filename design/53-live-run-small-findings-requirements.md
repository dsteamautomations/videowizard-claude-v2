# 53 — Live-run findings L1, L2, L3, L4 and L7 from design/49 (SK, 20 Oct 2026: "do everything not withdrawn"; built and deployed the same day: server 0.17.0, plugin 0.16.0)

Small changes to the intake and the brief found during the VW-4 live run (design/49), plus the format decision (L7, design/49 after SK's genre question). L5 and L6 were withdrawn; L8 and L9 are design/50.

| # | What changes | Where |
|---|---|---|
| L1 | `vw stage intake preview`: applies the removals in out/intake.json to the extracted text and writes `work/intake-preview.txt`, the script as it will be kept; prints the kept and removed counts and the path. The intake step tells the assistant to run it before asking, so the operator can read the kept text ("does it read as complete narration?"), not only the removed lines. Refused without out/intake.json or without a prepare. | plugin `stages_text.intake_preview`, `vw.py` cmd_stage (`preview` step), v2.json intake step 4 |
| L2 | The document's own timing lines, removed at intake as kind `timing`, are kept in the intake summary as `timing_lines` (the texts). The brief prepare shows them under `{document_timing}` in the prompt and in `inputs`, as a hint for the target length; the rule stays: a target length only if the operator gives one, so the assistant mentions the document's figure and asks. | plugin `intake_record` summary, `brief_prepare`, v2.json brief prompt |
| L3 | The brief prompt loses the two sentences that only forbid v1 behaviours ("Do not add coverage, feasibility or production-readiness work; those belong to later stages. Do not recreate ten mandatory fields, per-field forms, quality-score thresholds or a compulsory question count."). | v2.json brief prompt |
| L4 | The brief prompt and step say what chapters are: what the footage will show, the steps of the activity or the places and things the camera sees, in film order; they tag every clip at analysis and map scenes at options, so a chapter is never an argument of the script. | v2.json brief prompt and step 3 |
| L7 | `production.format`: `{frame: "16:9"|"9:16"|"1:1"|"4:5", destinations: [..], watched_muted: bool}`, optional, defaults 16:9, [], false; validated at brief record. Asked with the other production values ("where it plays and the frame shape; 16:9 unless they say"). Reaches: the options package `project` (with the other production values, already); visuals `prepare_take`, whose default aspect ratio becomes the brief's frame (a body value still wins); the delivery checklist, one line: "Deliver page: frame 9:16 for Instagram, TikTok; watched muted: burn the subtitles in" (16:9 and no destinations: "frame 16:9; destinations not given"). No vertical render path (design/51 B, later). | plugin `production_inputs`, v2.json brief prompt and step, server `visuals_stage.default_aspect`, `delivery.checklist_of` |

## Unstated but expected
- A brief recorded before L7 has no `format`; readers default to 16:9 and "not given".
- The preview file is a working file (work/), deleted at close like the rest of work/.
- The timing lines are the document's words, never parsed into seconds by the tool.

## Edge cases
| Case | Expected |
|---|---|
| preview before prepare | refused |
| preview with no removals | the whole text, counts 0 removed |
| intake with no timing lines | `timing_lines: []`; the brief prompt says "none" |
| `format.frame: "21:9"` | refused at record |
| `format` absent | defaults; `defaults_applied` lists `format` |
| a take prepared with `--aspect 9:16` on a 16:9 brief | the body value wins |

## Tests (written first)
plugin: test_intake (preview writes the kept text, refuses before prepare; timing lines in the summary), test_brief (prompt shows the document timing and the chapter sentence, lacks the v1 sentences; `format` validation and defaults). server unit: `default_aspect`, the checklist's Deliver line.

## Not covered
server/tests (Docker).
