# design/224: person A stops after the editor's package; the proof film waits for DaVinci

22 Nov 2026. **For SK's approval. No code is written until this list is approved.** Regular lane.

**Withdrawn by SK on 25 Nov 2026. Not built, and not to be built from this note.** It contradicts the hand-over flow SK set on 23 Nov 2026 (person A stops after the visuals, person B takes over on the computer with Resolve), which is live since server 0.123.0. The note is kept for the record only.

**Source:** SK, 22 Nov 2026, after VW-24's operator built the proof film on a Windows computer without Resolve: "The building of film should not happen here ... after this step, the packaging must happen, and the next flow should start in the machine which has Resolve." His choice the same day: "Stop after the package". Earlier words: 1 Nov ("drop this assembly step because it is redundant"), 2 Nov ("Editors package first then followed by assembly"), 11 Nov ("the DaVinci step on a different PC and the smallest step before that"). The whole history is in the workspace file `vw2-flow-after-visuals-22-nov.md`.

**Older way:** once the editor's package exists, the proof film may be prepared, built and rendered from any computer, before the timeline is in DaVinci (design/132, the hand-over of 11 Nov). On a computer without Resolve the tool says "What can be done here: the proof film". **Retired at the deploy for every open run.** VW-24 is the only open run.

## 1. The requirement, restated

Two people make a film. Person A works on any computer up to the end of the visuals and makes the editor's package. There A stops. Person B, on the computer with DaVinci Resolve, takes the run over, brings the package into DaVinci, and only then builds and reviews the proof film and answers the final questions.

## 2. The change

| # | Change | Where |
|---|---|---|
| S1 | **The gate.** The proof film (`assembly prepare`, `build` and `render`) is refused until the current package has been opened in DaVinci and reported. The refusal says: "The editor's package is ready. The proof film comes after the DaVinci step: on the computer with DaVinci Resolve, `vw pull <code>`, `vw delivery check`, `vw delivery download`, then `vw delivery open`." | `server/app/stage3/assembly.py`, one helper beside `package_first` |
| S2 | **The next step.** While the DaVinci step is open, the one next thing the server names for the stage is the DaVinci step, not the proof film. The tool then already prints, with no change to it: on a computer without Resolve "Nothing in this stage can be done here. Waiting for a computer with DaVinci: ..."; on a computer with Resolve "Next, the hand-over: ...". | `assembly.progress` |
| S3 | **The served instructions** say the same in one sentence: after the package this run continues on the computer with DaVinci Resolve; the proof film is made there, after the timeline is in DaVinci. | the assembly step of `server/procedures/v3.json`, by a wording script |

Why the gate is on the DaVinci step and not on "does this computer have Resolve": the server cannot see a computer. It can see that the timeline was opened in DaVinci, and only a computer with Resolve can do that. So the one rule stops person A and sets person B's order, for the chat tool and for any page, with no plugin change.

**No plugin release.** The tool's lines for both kinds of computer exist since 11 Nov; they follow the server's answer. The plugin minimum stays 0.106.0.

## 3. Unstated but expected

- Making the package on person A's computer works as today and is still enforced before everything else.
- Nothing is done again when person B takes the run over (the hand-over of 11 Nov stays as it is).
- A proof film already built or rendered before the DaVinci step is kept. After the DaVinci step it is offered for watching; it is not built again.
- Once the proof film is recorded, the rest is as today: the full package, DaVinci once more, the final questions.
- One person with Resolve on their own computer does all of it in the same order, with no extra step.
- All video categories; nothing here depends on the film's subject.

## 4. Edge cases

| # | Case | What happens |
|---|---|---|
| E1 | Person A asks for the proof film | Refused with the sentence of S1. Nothing is built, nothing is counted as a failed attempt of the operator |
| E2 | The run is at the proof film already when this is deployed (VW-24: built, the render failed) | The next render waits for the DaVinci step like any other. The build is kept |
| E3 | The DaVinci step was started and not finished (the import failed half way) | Refused, naming the computer that holds it and `vw delivery resolve --inspect` |
| E4 | A gap is recorded again after the DaVinci step | The package is made again (as today), which clears the DaVinci record: the DaVinci step is asked again before the proof film |
| E5 | Changes are asked at the proof film's review | The fills are changed and the film is built and rendered again with no new DaVinci step: the package did not change |
| E6 | Free Resolve instead of Studio | The operator imports the timeline by hand and `vw delivery confirm` reports it, as today. See "not covered" for its wording |
| E7 | Person B's computer loses Resolve, or the run is taken back to person A after the DaVinci step | The proof film is then allowed from that computer: it is a server job. The take-over still needs the operator's yes |
| E8 | An older tool on a laptop | The server's refusal and its next-step line are printed as they are; nothing in the older tool lets the proof film through |
| E9 | Two computers at once | As today: one holds the run, the other must take it over with the operator's yes |
| E10 | The proof film's own failure (a defect such as 60) | Unchanged: the defect holds the step; this gate adds nothing to it |

## 5. Failure modes

| Failure | Handling |
|---|---|
| DaVinci will not import (not running, scripting off) | The tool gives the three hand steps of the free route; `vw delivery confirm` reports it; the proof film is then allowed |
| No computer with Resolve is free | The run waits at the package. Nothing is lost; the package stays current |
| The server cannot read its stage record | The proof film is refused, never let through on a doubt |
| The builder must let one film through | No switch is built. The builder marks the DaVinci step by hand on the server, with SK's word |

## 6. Tests (written first)

`server/unit/test_design224_pure.py`:
- With a current package and no DaVinci report: `prepare`, `build` and `render` are refused with the sentence of S1.
- With the DaVinci step reported for this package: all three pass the gate.
- Reserved or dispatched, not reported: refused, naming the computer.
- A package made again clears the report: refused again.
- The next step the server names is the DaVinci step while it is open, and the proof film after it; the tool's two lines (with and without Resolve) read as in S2.
- After the proof film is recorded the gate is not asked.
- A proof film built before the DaVinci step is kept and offered after it.
- The served assembly step carries the new sentence and stays inside the stage's word limit.
- The older tests of the hand-over and of design/132 pass, changed only where they assert the older order.

## 7. Not covered, on purpose

- **Dropping the proof film altogether** (watch list C2). It stays, as person B's check.
- **The free route's words.** Its third step says to compare with `Approved-film.mp4`, which the early package does not hold. That text is in the plugin; changing it needs a plugin release. SK's Mac has Resolve Studio, which does not use those steps.
- A page for the assembly and delivery stages (there is none today).
- Who person A and person B are: the server does not know people, only that the DaVinci step is done.
- The database tests (`server/tests`) unless SK asks for them.

## 8. What I need from SK

Approval of this list, or changes. Then tests first, the change, one review round, and a deploy on your word.
