# 156 — The animatic gate test: results (5 Nov 2026)

The test design/155 phase 0 asked for, run on the VM with the key there, from a standalone script (`156-assets/omni_test.py`), nothing deployed. Inputs: SK's Part 1 cartoon from the "Evening at the park" thread (10 s, 1280×720, 15 fps) and its two reference stills of the couple (640×360), standing in for a person's set. Model `gemini-omni-1.1-flash`, the same as every take today, through the same interactions endpoint. Six paid runs, three methods, two runs each (thread finding F6: run twice before judging).

| Method | What went in | Prompt |
|---|---|---|
| **A** cartoon edited | the cartoon as the input video (Files API upload) + the two stills + an edit prompt ("keep every shot, cut, angle, timing and position; change only the look") | `156-assets/prompt-A-edit.txt` |
| **B** ten frames (SK's idea) | one cartoon frame per second (10 pictures) + the two stills + a timecoded shot list | `156-assets/prompt-B-frames.txt` |
| **D** today's method (baseline) | the cartoon's first frame as the start image + the two stills + the same timecoded shot list | `156-assets/prompt-D-baseline.txt` |

No run sent the single-shot sentence our server adds today. The task was left for the model to infer in every run (A was treated as an edit, as expected).

## Results

Measured with ffprobe and ffmpeg's scene-change score; judged by eye on the key-moment sheets (`156-assets/round1-key-moments.png`, `round2-key-moments.png`; cartoon on top, the three outputs below, at 1.3, 3.3, 5.6, 7.2, 8.4 and 9.8 s). The cartoon cuts at 2.5, 4.0 and 6.5 s.

| | A1 | A2 | B1 | B2 | D1 | D2 |
|---|---|---|---|---|---|---|
| Accepted | yes | yes | yes (12 pictures) | yes | yes | yes |
| Length, size, audio | 10.03 s, 720p, 24 fps, audio | same | same | same | same | same |
| Cuts found (s) | 3.08, 4.17 | 2.88, 3.92, 7.75 | 2.46, 4.0, 6.46 | 2.46, 4.0 | 2.5, 4.0, 6.38 | 2.42, 4.0 |
| Cut timing against the cartoon | off by 0.2–0.6 s; the last cut missing or late | off by 0.1–1.3 s | within 0.05 s | within 0.05 s (the last is a push-in, not a cut) | within 0.1 s | within 0.1 s |
| Shot 1 framing | truly wide, the couple small, as the cartoon | medium-wide | medium-wide | medium-wide | medium-wide | medium-wide |
| Shot 1 sip, right hand, left hand empty | sip too small to judge | yes | yes | yes | yes | yes |
| Shot 2 tumblers (must be two) | **one** (his into a bowl) | **one** | **three** | two | two | two |
| Shot 3 yawn, both arms up | half up | half up | fully up | fully up | hands on head | fully up |
| Shot 4 push-in to both faces | yes, tightest | yes | yes | yes | yes | yes |
| Shot 4 his head turns away | partly | yes | yes | yes | partly | partly |
| Shot 4 her look at him | yes | yes | yes | yes | yes | yes |
| Couple matches the two stills | yes | yes | yes | yes | yes | yes |
| Cartoon look leaked | no | no | no | no | no | no |
| Wall time | 83 s | 84 s | 76 s | 77 s | 52 s | 51 s |
| Input tokens (cost on top of the take) | 60,395 (video 57,920 ≈ ₹8) | same | 13,729 (≈ ₹2) | same | 3,752 | same |
| Output tokens | 57,920 (≈ ₹90, as every take) | same | same | same | same | same |

## What the six runs say

1. **Pictures beside a video are accepted, and identity holds on every path.** Risk 1 of design/155 is cleared. Two stills were enough for the same couple in all six runs.
2. **The edited cartoon (A) follows the cartoon's framing best but its timing is the loosest.** Both A runs drift the cuts by half a second or more and both lose a tumbler in the close-up. Risk 2 of design/155 (the edit does not promise timing) is real. A is not the path.
3. **The ten frames (B, SK's idea) give exact cuts and the truest body actions.** Both B runs cut within 0.05 s of the cartoon and show the full yawn and the head turn. B1 made three tumblers (the thread's F4 again: the cartoon's bowl sits against her hand, design/154 §7); B2 made two. B needs no Files API, no 10-second edit limit, and sends 13,000 input tokens instead of 60,000. The 12-picture call was accepted, so the "10 images per call" row of our fact sheet is not a hard limit at this count.
4. **Today's method with a timecoded shot list (D) is a strong baseline.** Both D runs cut on the second and keep two tumblers; the head turn is weaker. This is the honest surprise: **the cuts come from the timecoded text, not from the cartoon.** Multi-angle inside one take works today the moment the single-shot sentence is dropped and the shot list carries seconds (design/128's timeline already does). What the cartoon adds on top is the body positions, the framing and the actions: the full arms-up, the whole head turning, the push-in ending tight.
5. **Time:** 50–85 s a run, all paths. Nothing waits on the cartoon at this step.

## What this changes in design/155

- **Phase 0, the path:** not the edit. The animatic is still drawn, but what goes to Omni is **its frames**, one per second (or one per shot change plus one per second inside a shot), with the sets and the timecoded shot list. The server already sends pictures with a take; the change is the number of pictures and the text, not the Files API.
- **Phase 2, multi-angle:** available now for any scene, with or without a cartoon: the `one_take` scene flag drops the single-shot sentence and writes the scene's shots as a timecoded list. The cartoon frames are the next step, for position and action fidelity.
- **Phase 3, the cartoon:** unchanged in what it is; its output for the take is frames, not a video. The empty-hand rule (nothing touching a hand that should be empty) is now proven to matter on this path too (B1's three tumblers).
- **Phase 5, the take:** no video input needed. Drop the single-shot sentence on `one_take`; the camera line becomes "as the storyboard shows"; the drift check off.
- **Estimate:** the Files API day goes; the rest stands. 11–14 days after SK's go.

## Not covered

- One scene, one cartoon, two runs per method: enough to choose a path, not to set a success rate.
- The stills were 640×360 thread outputs, not a set from our round.
- No dialogue, no scene longer than 10 s, no documentary footage on either side of the clip.
- The outputs are in the scratchpad and were sent to SK; they are not in the repository.
