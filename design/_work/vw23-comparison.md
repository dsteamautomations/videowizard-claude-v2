# VW-23: the cut of 13 Nov against the cut of 14 Nov

14 Nov 2026. Both cuts read from the server (read only), with the operator's keep and reject answers from the run's log. Worked out by Claude's script (`model-test/vw23-compare/compare_vw23.py`); no model was called.

| | The cut of 13 Nov | The cut of 14 Nov |
|---|---|---|
| Who watched the clips | Gemini 3.8 Flash; fit by paragraph | Gemini 4 Hydrogen, the look-again way for every clip; fit by sentence |
| Who chose the clips | Claude, the operator's assistant, under the application's full rules, with the server's check and the second look | The same |
| Scenes, narration, film length | 15 scenes, 42 sentences, 299.4 s | The same |

## In short

- **The new cut has less real footage, not more:** 77.4 seconds against 95.0.
- **What it placed was right more often:** 2 of 23 footage shots rejected, against 5 of 29.
- **It lost four shots the operator had kept, and gained none.** Two were lost to stricter matching, two because Gemini 4 Hydrogen flags small background things as risks and the server then refuses the piece.
- **Three of the four direct shots the operator rejected on 13 Nov were right first time on 14 Nov.**
- So the change made the cut more careful and less full. On the first two of Deepa's three points it is not a win.

## 1. More real footage?

| | 13 Nov | 14 Nov |
|---|---|---|
| Real footage | 95.0 s (31.7 %) | 77.4 s (25.8 %) |
| Left blank for AI video or graphics | 204.4 s | 222.0 s |
| Footage shots | 29 | 23 |
| Footage the operator kept as placed | 75.4 s | 69.1 s |
| Footage kept, counting a kept alternative | 89.2 s | 71.8 s |

Per scene, seconds of real footage (scenes with none in both cuts are left out):

| Scene | 13 Nov | 14 Nov |
|---|---|---|
| 2 | 4.0 | 0.0 |
| 3 | 5.9 | 5.2 |
| 5 | 14.3 | 12.7 |
| 7 | 17.6 | 17.6 |
| 8 | 20.3 | 20.3 |
| 9 | 6.2 | 6.2 |
| 10 | 11.4 | 11.4 |
| 12 | 3.8 | 0.0 |
| 14 | 11.6 | 4.0 |

## 2. Small pieces found?

| | 13 Nov | 14 Nov |
|---|---|---|
| Pieces the clip study offered | 204 | 299 |
| Shots under 3 seconds | 10 | 9 |
| Shots cut from inside a longer piece | 8 | 5 |
| Different clips used | 29 | 22 |
| Clips used only in this cut | 14 | 7 |
| Clips used in both cuts | 15 | 15 |

Gemini 4 Hydrogen cut the footage into more pieces (299 against 204), but the cut did not use more of them.

## 4. Kept by the operator

| | 13 Nov | 14 Nov |
|---|---|---|
| Footage shots kept | 24 of 29 | 21 of 23 |
| Rejected | 5 | 2 |
| Rejected, then its alternative kept | 4 | 1 |

## 5. Gained and lost, sentence by sentence

| | Sentences |
|---|---|
| Footage in both cuts | 13 |
| Blank in both | 25 |
| Footage gained by the new cut | 0 |
| Footage lost by the new cut | 4 |
| The same clips in both | 4 |

The four sentences that lost footage. In every one the operator had kept the old shot.

| Sentence | Old shot (kept) | Why the new cut has a blank |
|---|---|---|
| The concept behind a filler slab is simple yet ingenious. | C0079, 0.0 to 3.98 s, placed as B-roll | No piece is offered for this scene any more: the line names nothing a clip shows, and the looser B-roll the old cut used is no longer fitted to it. |
| The result is a strong and durable roof that uses fewer resources without compromising performa | C0080, 1.4 to 4.56 s, placed as a direct match | The assistant now treats the sentence as a strength claim that no piece shows. |
| Once adequate strength is achieved, the shuttering is removed, revealing the beautiful exposed  | C0104, 30.6 to 34.4 s, placed as a direct match | The piece is refused: Gemini 4 Hydrogen flagged "background banner signage" on this clip. |
| A successful demonstration of this technology can be seen at the Technology Resource Center of  | C0050, 40.7 to 44.3 s, placed as a direct match | The piece is refused: Gemini 4 Hydrogen flagged "a crew bag in the background"; the other candidate was the wrong object. |

## 6. Honest labels

| | 13 Nov | 14 Nov |
|---|---|---|
| Placed as a direct match | 25 | 20 |
| Placed as B-roll | 2 | 2 |
| From the client's library | 2 | 1 |

Of the new cut's 20 direct shots, Gemini marked 4 as showing the sentence exactly and 16 as showing part of it. None was only "related": the new rule held.

## 7. Repeats

- 13 Nov: no clip used twice. 14 Nov: one clip used twice (C0091), under two neighbouring sentences of one scene.
- Two neighbouring shots of the same subject: for the team's eye, in the list at the end.

## 8. Effort

| | 13 Nov | 14 Nov |
|---|---|---|
| Refusals of the cut by the server's check | 9 | 3 |
| Analysis time | 51 minutes | 60 minutes, of which about 40 were waiting on two clips that stopped without an answer |
| Analysis cost | not worked out | 28.62 US dollars |

## What caused the loss of footage

| Cause | Evidence |
|---|---|
| **Small background things flagged as risks** | Gemini 4 Hydrogen put a risk flag on 52 pieces; Flash on 17. Its flags are things like "background motorcycle licence plate, unreadable", "minor background clutter", "commercial paint bucket label", "background banner signage", "personal item on prop". The server refuses any piece that carries a flag, even when the model itself marks the piece safe for the client. Clips with at least one usable piece fell from 95 to 89 of 106. Four clips the old cut used (C0081, C0084, C0101, C0104) are refused in the new list for this reason alone. |
| **Stricter matching** | The fit is now by sentence, and a piece only related to a sentence cannot be a direct match. Looser B-roll under an opening line, and a shot under a strength claim, are no longer offered. |

## 3. Order and choice within a sentence: for the team's eye

Every sentence where the two cuts chose differently, shots in play order. "Operator" is the answer on the review page; "Gemini" is its mark for that piece under that sentence.

**Filler slab technology utilizes this principle by replacing the non-structural concrete with lightweight filler materials such as Mangalore tiles, country tiles, hollow clay blocks, lightweight bricks, or other locally available materials.**

| Cut | Shot | Clip and seconds | Size | Placed as | Operator | Gemini |
|---|---|---|---|---|---|---|
| 13 Nov | 3.2 | C0069, 0.0 to 2.7 s | MWS | direct | Reject (its alternative kept) |  |
| 13 Nov | 3.4 | C0080, 1.4 to 4.56 s | MS | direct | Keep |  |
| 14 Nov | 3.2 | C0069, 0.3 to 3.0 s | MWS | direct | Keep | PARTLY |
| 14 Nov | 3.4 | C0072, 0.2 to 2.68 s | MCU | direct | Keep | PARTLY |

**These include cement, reinforcement steel, coarse sand, crushed stone aggregates, binding wire, clean water, and suitable filler materials such as Mangalore tiles, hollow clay blocks or even coconut shells.**

| Cut | Shot | Clip and seconds | Size | Placed as | Operator | Gemini |
|---|---|---|---|---|---|---|
| 13 Nov | 5.2 | C0009, 6.1 to 8.6 s | MS | direct | Keep |  |
| 13 Nov | 5.3 | C0023, 11.1 to 13.0 s | CU | direct | Keep |  |
| 13 Nov | 5.5 | C0060, 4.3 to 6.7 s | CU | direct | Keep |  |
| 13 Nov | 5.6 | C0072, 0.6 to 2.28 s | MCU | direct | Keep |  |
| 14 Nov | 5.2 | C0023, 8.16 to 11.02 s | CU | direct | Keep | PARTLY |
| 14 Nov | 5.4 | C0060, 1.8 to 4.0 s | CU | direct | Keep | PARTLY |
| 14 Nov | 5.5 | C0070, 0.0 to 2.06 s | MCU | direct | Keep | PARTLY |

**Once the reinforcement is in place, the filler materials are carefully positioned between the steel bars.**

| Cut | Shot | Clip and seconds | Size | Placed as | Operator | Gemini |
|---|---|---|---|---|---|---|
| 13 Nov | 8.1 | C0063, 1.4 to 4.02 s | MCU | direct | Keep |  |
| 13 Nov | 8.2 | C0057, 1.9 to 5.3 s | CU | direct | Reject (its alternative kept) |  |
| 14 Nov | 8.1 | C0063, 2.0 to 4.62 s | CU | direct | Keep | EXACT |
| 14 Nov | 8.2 | C0044, 4.3 to 7.7 s | MWS | direct | Keep | EXACT |

**The tiles or blocks are arranged in straight rows with uniform spacing, creating the distinctive pattern that will later become visible on the ceiling.**

| Cut | Shot | Clip and seconds | Size | Placed as | Operator | Gemini |
|---|---|---|---|---|---|---|
| 13 Nov | 8.3 | C0044, 8.8 to 13.36 s | MS | direct | Keep |  |
| 13 Nov | 8.4 | C0067, 0.0 to 4.56 s | WS | direct | Reject (its alternative kept) |  |
| 14 Nov | 8.3 | C0055, 19.6 to 24.16 s | CU | direct | Keep | PARTLY |
| 14 Nov | 8.4 | C0074, 0.0 to 4.6 s | MWS | direct | Keep | PARTLY |

**Continuous monitoring ensures proper alignment and an aesthetically pleasing finish.**

| Cut | Shot | Clip and seconds | Size | Placed as | Operator | Gemini |
|---|---|---|---|---|---|---|
| 13 Nov | 8.5 | C0064, 0.9 to 3.06 s | MCU | direct | Keep |  |
| 13 Nov | 8.6 | C0065, 1.4 to 4.38 s | MWS | direct | Keep |  |
| 14 Nov | 8.5 | C0065, 0.5 to 5.6 s | MS | b_roll | Keep | RELATED |

**Concrete is prepared using the prescribed mix and poured around the reinforcement and filler materials.**

| Cut | Shot | Clip and seconds | Size | Placed as | Operator | Gemini |
|---|---|---|---|---|---|---|
| 13 Nov | 9.1 | C0081, 29.9 to 33.06 s | MS | direct | Reject (its alternative kept) |  |
| 13 Nov | 9.2 | C0084, 2.48 to 5.52 s | MWS | direct | Keep |  |
| 14 Nov | 9.1 | C0018, 2.3 to 5.0 s | CU | direct | Reject (its alternative kept) | PARTLY |
| 14 Nov | 9.2 | C0088, 4.1 to 7.6 s | MS | direct | Keep | PARTLY |

**Care is taken to ensure that all gaps are completely filled and properly compacted.**

| Cut | Shot | Clip and seconds | Size | Placed as | Operator | Gemini |
|---|---|---|---|---|---|---|
| 13 Nov | 10.1 | C0093, 0.3 to 3.02 s | CU | direct | Keep |  |
| 13 Nov | 10.2 | C0090, 0.8 to 3.14 s | MS | direct | Keep |  |
| 14 Nov | 10.1 | C0089, 1.9 to 4.62 s | MWS | direct | Keep | EXACT |
| 14 Nov | 10.2 | C0091, 0.8 to 3.14 s | CU | direct | Keep | PARTLY |

**The casting is carried out systematically so that the slab remains uniform and structurally sound.**

| Cut | Shot | Clip and seconds | Size | Placed as | Operator | Gemini |
|---|---|---|---|---|---|---|
| 13 Nov | 10.3 | C0095, 1.5 to 4.5 s | CU | direct | Keep |  |
| 13 Nov | 10.4 | C0101, 0.0 to 3.38 s | MWS | direct | Keep |  |
| 14 Nov | 10.3 | C0090, 0.4 to 3.4 s | MS | direct | Keep | PARTLY |
| 14 Nov | 10.4 | C0091, 5.8 to 9.18 s | CU | direct | Keep | PARTLY |

**The buildings here showcase how traditional wisdom and scientific understanding can come together to create affordable, durable, and environmentally responsible construction solutions.**

| Cut | Shot | Clip and seconds | Size | Placed as | Operator | Gemini |
|---|---|---|---|---|---|---|
| 13 Nov | 14.3 | C0134, 0.0 to 4.0 s | WS | library | Keep |  |
| 13 Nov | 14.4 | C0136, 1.6 to 5.6 s | MWS | library | Keep |  |
| 14 Nov | 14.2 | C0134, 0.0 to 4.0 s | WS | library | Keep |  |

## Not known

- Whether the four lost shots were good film. The operator kept them on 13 Nov; nobody has judged whether the blank is the better choice.
- Order within a sentence (area 3): listed above, not judged.
- One film, one operator, one pass.
