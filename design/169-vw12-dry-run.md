# 169 — Dry run of the agreed process on four VW-12 scenes (5 Nov 2026)

SK's two conditions before build step one: (1) the requirements note read word by word, corrected, and made unambiguous (done: design/161 rewritten whole, commit 2b055a8); (2) four scenes from a real film taken through the agreed process by hand, without building it, to see whether the glaring failures are avoided. This note is (2).

## The film and the scenes

VW-12 (rat-trap bond masonry, 296 s, procedure version 3; its plan version 9 from storage, `visuals/plan-v9.json`). Four single-shot scenes on the `video` route, chosen for the failure types met in the test round: a person carrying a container, a tool acting on a surface with a visible result, a thing changing state (slack to taut), hands at a joint.

| Scene (plan id) | Gap | Seconds (plan → cartoon) | What the plan asks |
|---|---|---|---|
| **k1** BEAT_04-B1_sc1 | Where bricks come from | 4.2 → 5 | the kiln worker carries a pan of wet clay on his head from the clay heap along the green-brick stacks; a clamp kiln smokes behind; a slow pan left follows him |
| **p1** g08-s1 | Preparing the plinth | 7.8 → 8 | the helper sweeps the plinth top with a coconut-midrib broom, lays it down, lifts the bucket, flicks water across the swept stone, which darkens |
| **s1** g09-s1 | Guide strings | 3.5 → 4 | the mason crouching at the near peg pulls the slack string taut and winds it twice round the peg; it runs straight to the far peg |
| **j1** BEAT_08-B1-SC1 | Pointing and curing | 6.6 → 7 | the mason takes mortar from the pan on the pointing trowel, presses it into the raked joint, strikes it flush |

## The process as run by hand (design/161 §7, steps 2–5)

1. **References**: six pictures from the run's image model (`gemini-nano-banana-2.1`, the server's own call): the mason, the helper and the kiln worker full length from the plan's element descriptions and the scenes' outfits; still lifes of the broom and bucket, the peg and string, the trowel and mortar pan (`169-assets/ref-*.txt`, `refs-sheet.png`). No round, no operator approval: a shortcut of the dry run only.
2. **Animatic**: each scene drawn from the plan's layout, landmarks, facing, beats and camera by the rules of design/161 §5 (`169-assets/scenes.py`): one fixed world; the person's nose, eye and feet on the facing side; the broom on the stone, the trowel's edge in the joint, the string tied to the far peg; every second with a drawn action and a closing margin; no counts anywhere; 24 fps. Key stills read before anything was sent: two scenes needed a second pass (the string scene's crop showed sky; the kiln worker was too large for a wide shot and had no walking legs). Action marks written beside each (`*-marks.json`).
3. **Take text**: written as the server will write it, from the marks (§6): the guide sentence; the photographs named; the place from the scene's layout and light; the person's look; the fixed positions and facing; each beat with its seconds; "the camera does not move" or the one slow pan; no counts, no equipment, nothing not in the shot (`169-assets/prompt-*.txt`).
4. **Take**: the cartoon video + only the photographs of what is in the shot + the take text, to Omni through the same endpoint the server uses. One run each: 61, 85, 61 and 84 s.

## Results (`169-assets/review-*.png`: every half second at 480 px, the cartoon above the output)

| | k1 kiln | p1 plinth | s1 string | j1 pointing |
|---|---|---|---|---|
| Length, cuts | 5.03 s, none | 8.04 s, none | 4.03 s, none | 7.04 s, none |
| Staging | the kiln mound smoking at back right, the lattice stacks left, the clay heap in the foreground, palms on the horizon; **the camera pans left with him** | the plinth top running diagonally away, the bucket on it ahead of him, the brick stack and neem soft at left | the near peg at frame right, the far peg up the plinth, the broom on the sand at left, the neem | the wall receding right, the stack with the mortar pan at his left, the window soft behind |
| Facing | right side to the camera, walking right to left | left profile, bent over the plinth | back three-quarter, right shoulder nearest, sighting along the line | three-quarter from his right, facing the joint |
| The action, in order and on time | he walks the whole shot with the pan on his head, one hand steadying it | sweeps 0–3.8 with sand going over the edge; lays the broom; lifts the bucket; **flicks water, the drops visible in the air**; stands with the bucket | the string lies slack, lifts, runs taut to the far peg; the hands wind it on the peg; he sights along it | mortar from the pan to the joint; pressed along it; drawn back; the trowel lifted off |
| The state change | the pan stays on his head throughout | the near stretch of the top darkens | slack → taut, and stays taut | the joint filled and struck (hard to read at 480 px; the trowel's path is right) |
| Identity | the kiln worker from his photograph | the helper from his, the broom and bucket from theirs | the mason from his, the peg and string from theirs | the mason from his, the trowel and pan from theirs |
| Invented action, leaked marks, extra people | none | none | none | none |
| Deviations | a second worker at the far stacks (allowed by the scene's ambient) | the plinth reads as a long stone bench, fine | none seen | the bricks on edge are not legible at this size; SK to judge |

## Verdict

The glaring failures of the test round do not appear in these four: nothing changes sides, no one turns to face the camera, no tool acts on the wrong place, no container empties or fills by itself, no cut is invented, no count drifts because no count was asked. Each scene was designed so that the one state change is seen (G3), drawn with its contact (G1), filled to its last second (G4), and described without numbers (G2). The process as agreed in design/161 held on real plan text.

Two notes for the build, not failures:
- The four are single-shot scenes with no `one_take` flag; the flag's multi-angle path was proved on the mason scene (design/157, 160), not here.
- The references here were made straight from the element descriptions; in the flow they come from the round and the sets, which carry more (the footage frames, the operator's picks).

SK closes the testing as closed-ended on this; build step one (D14 (i): the `one_take` flag and the timecoded take text) starts with its tests.

## Not covered

- One run per scene; judged on half-second sheets at 480 px; SK has all four videos.
- The scenes were not placed between the film's real footage.
