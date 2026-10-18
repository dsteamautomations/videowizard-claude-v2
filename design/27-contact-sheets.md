# 27 — Contact sheets: let the assistant see the film as still frames (closed 18 Oct 2026: dropped by SK in the stage 10 review, design/45 10.8; never built)

Date 16 Oct 2026. Agreed in principle by SK on 16 Oct; takes effect from the next run, not VW-2.

## Requirement
A new free command, `vw sheet`, turns a film in the run folder into contact sheets: images of frames laid out in a grid, each labelled with its time. The assistant can read images, so it can then see the film as stills. It is used for:
1. **The first cut, before planning the blanks.** One frame every 2 seconds, plus, for every blank, the last real frame before it and the first real frame after it, labelled with the blank's id. The assistant plans each blank looking at its neighbours: light, colour, place, people.
2. **Each generated take, before the operator sees it.** One frame per second (takes are 3 to 10 seconds). The assistant checks for obvious faults such as garbled writing, the wrong setting, deformed hands or logos, and tells the operator what it saw.

## Unstated but expected requirements
- Free: local FFmpeg only, no upload, no paid AI.
- Works on any film inside the run folder; output goes to `work/sheets/`. The workspace guard already limits files to the run folder.
- Each sheet is at most 6 × 5 frames and about 1,920 pixels wide, so the assistant can read it whole.
- Labels show film time (mm:ss.f) and, for blank edges, "before BEAT_04-B1" or "after BEAT_04-B1".
- Blank positions come from the downloaded visuals package (`work/visuals-package.json`), so no server call is needed.
- The command prints the list of sheet paths and what each covers.
- Re-running replaces earlier sheets of the same film.

## Edge cases
| Case | Handling |
|---|---|
| File missing or not a video | Refused with a clear message naming the file |
| FFmpeg not installed | Refused: "install FFmpeg" (the plugin already depends on it for media) |
| Long film (a 6-minute first cut at 2 s is 180 frames) | Split into several sheets of 30; refuse beyond 12 sheets and suggest a larger interval |
| Very short take (under 1 second) | At least one frame |
| A blank at the very start or end of the film | Only the side that exists is shown |
| Two blanks next to each other | Their shared edge is a blank card, so it is labelled as such and not treated as real footage |
| Frame time past the end of the file | Clamped to the last frame |
| No visuals package downloaded yet | The blank-edge frames are skipped with a note; the regular frames still work |

## Failure modes
- **Stills hide motion faults** such as jitter, morphing or flicker. Sheets catch look, continuity and text errors only. The operator still watches every take, and the stage still requires their yes.
- **The assistant over-trusts a sheet.** Its instructions say what a sheet can and cannot show.

## Takes effect from the next run
The command ships in the plugin now but is not mentioned to VW-2's assistant. The instructions telling the assistant to use it are added to the procedure once VW-2 has left the visuals stage, so VW-2 is not changed mid-stage.

## Tests (written first, after approval)
One test per edge case above; tiles per sheet and sheet count; labels and blank-edge frames placed at the right times; a check that the sheet image is readable size.

## Not covered
Motion faults and sound: a still cannot show them. A paid video check (Gemini can watch video) is possible later if stills prove not enough.
