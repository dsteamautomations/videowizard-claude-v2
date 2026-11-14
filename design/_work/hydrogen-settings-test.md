# Gemini 4 Hydrogen, look-again way: cheaper settings, cache and batch

14 Nov 2026. Run by Claude's scripts outside the application (`model-test/settings_vw19_hydrogen.py`, `looks_vw19_hydrogen.py`, `batch_vw19_hydrogen.py`). Nothing in the application was changed. 29 requests, 4.59 US dollars.

Two clips of VW-19, the application's own request, the look-again way:
- **C0113** (13.0 s): one mason leaves with a mortar pan, a second sweeps the wall with a broom.
- **C0032** (3.8 s): a brick vault ceiling seen from below. Deepa's verdict (14 Nov): the dark thing in the foreground is a ceiling fan.

The findings below are the model's own statements. **None is judged except the fan. Deepa judges the rest.**

## Table 1: cost, time and looks for each setting

**C0113 (13.0 s)**

| Thinking | Picture quality | Cost | Time | Looks | Pieces |
|---|---|---|---|---|---|
| High | High | 0.33 USD | 135 s | 5 | 4 |
| High | Medium | 0.23 | 105 s | 4 | 5 |
| High | Low | 0.19 | 83 s | 4 | 3 |
| Medium | High | 0.12 | 45 s | 2 | 2 |
| Medium | Medium | 0.13 | 53 s | 2 | 3 |
| Medium | Low | 0.15 | 56 s | 3 | 3 |
| Low | High | 0.08 | 33 s | 2 | 1 |
| Low | Medium | 0.08 | 47 s | 2 | 2 |
| Low | Low | 0.08 | 31 s | 2 | 2 |

**C0032 (3.8 s)**

| Thinking | Picture quality | Cost | Time | Looks | Says "fan"? |
|---|---|---|---|---|---|
| High | High | 0.18 USD | 72 s | 3 | Yes |
| High | Medium | 0.15 | 62 s | 3 | Yes |
| High | Low | 0.19 | 80 s | 3 | Yes |
| Medium | High | 0.09 | 35 s | 2 | Not sure ("blade or post") |
| Medium | Medium | 0.07 | 34 s | 2 | No ("post") |
| Medium | Low | 0.09 | 40 s | 2 | Yes |
| Low | High | 0.07 | 24 s | 1 | No ("post") |
| Low | Medium | 0.06 | 33 s | 1 | No ("post") |
| Low | Low | 0.06 | 22 s | 1 | Yes |

For comparison, the plain way at high thinking and high quality cost 0.14 USD on C0113 and 0.08 on C0032 (and said "wooden batten" for the fan).

## Table 2: what a "look" is, one by one

Recorded by sending the same request straight to Google and keeping the model's own short notes between its looks. What a look asked for (which seconds, how many frames a second) is not given out by Google; only that a look happened. The notes say it in the model's words.

**C0113, thinking high (5 looks, 150 s, 0.35 USD)**

| Look | What it was for, in the model's notes | What it noted afterwards |
|---|---|---|
| 1 and 2 | Load the clip: once for the frames and sound, once for the speech-to-text | The speech in the first four seconds is Tamil; the automatic transcript is a mishearing |
| 3 and 4 | Look again at 1.0 to 1.6 s and at 12.0 to 13.0 s, the second at 10 frames a second, "to inspect the tail end" | Between 2.0 and 3.7 s someone clearly speaks; it wrote down the Tamil words (sweep the top and the side) |
| 5 | Look again at 12.7 to 12.9 s | A slight shift of the camera at the very end; it checks whether the camera is steady from 1.3 to 12.7 s |

**C0113, thinking medium (3 looks, 62 s, 0.16 USD)**

| Look | What it was for | What it noted afterwards |
|---|---|---|
| 1 and 2 | Load the clip: frames and sound, and the speech-to-text | Bricks on edge, a mortar pan; the worker on the right sweeps with a twig broom; the left worker leaves at about 1 s |
| 3 | Look again at the first second and a half, frame by frame | The left worker's hand leaves the frame at 1.2 s and is gone by 1.4 s; it cuts the clip into two pieces there |

**C0113, thinking low (2 looks, 36 s, 0.07 USD)**

| Look | What it was for | What it noted afterwards |
|---|---|---|
| 1 and 2 | Load the clip: frames and sound, and the speech-to-text | A person reaches for a mortar pan; a second steps in with a broom; Tamil speech at 2 to 4 s; the camera does not move |
| none further | | It did not look again |

**C0032, thinking high (3 looks, 58 s, 0.16 USD)**

| Look | What it was for | What it noted afterwards |
|---|---|---|
| 1 and 2 | Load the clip: frames and sound, and the speech-to-text | The transcript says "I don't know"; it doubts it |
| 3 | Listen again and look at the end, at 3.7 s | No speech, only room noise; then it names the lattice openings, the grey conduit and the still ceiling fan |

**C0032, thinking medium and low (2 looks each)**

| Look | What it was for | What it noted afterwards |
|---|---|---|
| 1 and 2 | Load the clip only | A brick vault, a white curved wall, a grey conduit, "a dark post or blade" (medium) or "a wooden post" (low) |
| none further | | It did not look again |

**The pattern:** the first two looks are always the same: loading the clip and its speech-to-text. A real second look starts at look 3. At low thinking there is none. At medium there is at most one. At high there are one to three.

## Table 3: what each thinking level found, C0113 (for Deepa to judge)

Picture quality high in every row.

| Point | Thinking high | Thinking medium | Thinking low |
|---|---|---|---|
| Pieces | 4: 0 to 1.3 s, 1.3 to 2.9 s, 2.9 to 4.5 s, 5.0 to 12.7 s | 2: 0 to 1.5 s, 1.5 to 12.9 s | 1: 1.5 to 13.0 s |
| The first second and a half | Its own piece, grade C | Its own piece, grade C | Left out of the answer |
| The sweeping of the front face, then the top | Two separate pieces | Inside the one long piece | Inside the one long piece |
| The broom | "Coconut broom" | "Straw broom" | "Broom" |
| The trowel | Named | Named | Not named |
| The stack of bricks behind | Named | Named | Not named |
| The off-camera Tamil instruction | Written down and translated | Noted | Noted as partly heard |
| The slight camera shift at the very end | Noticed, and the last piece ends at 12.7 s | Not mentioned | Not mentioned |

Questions for Deepa:
1. Is the first second and a half (the first mason leaving with the pan) worth having as its own piece?
2. Are the sweeping of the front face (about 1.3 to 2.9 s) and of the top (about 2.9 to 4.5 s) really two different actions an editor would want apart?
3. Is there a slight camera shift in the last quarter second?
4. Is the broom a coconut-stick broom?

## Table 4: the same setting twice does not give the same answer

C0113 was sent four times at thinking high and picture quality high.

| Run | Pieces | Things named | Motorbike in the background? |
|---|---|---|---|
| 13 Nov, the main test | 4 | 11 | Yes |
| 14 Nov, settings run | 4 | 7 | No |
| 14 Nov, the looks record | 3 | 9 | No |
| 14 Nov, instruction placed before the video | 3 | 10 | Yes |

So a difference between two settings on one run can be chance. The fan on C0032 is the steadier evidence: 6 of 6 runs at high thinking said "fan"; 2 of 4 at medium (one more unsure); 1 of 4 at low.

## Table 5: the cache and the batch

| Trial | Result |
|---|---|
| Instruction placed before the video | No cached tokens reported on either clip. No saving. |
| Instruction rewritten so that 95 % of it is the same for every clip, the clip's own values last, video last | No cached tokens reported on three requests in a row (two clips, then the first again). No saving. |
| The request as it is | Three of the 18 runs did report cached tokens (about 7,800 each), all at low picture quality. It happens by itself, sometimes; we did not cause it. |
| Batch, look-again way | The job was accepted, then the request inside it failed: "Request contains an invalid argument." |
| Batch, plain way | Sent to tell whether the look-again way is what the batch refuses. Result pending. |
| Batch output limit | A batch refuses more than 32,768 output tokens; our request asks for 65,536. |

- **Caching:** reordering the request does not make the automatic cache catch our instruction. Even if it did, the instruction is about 5 % of the cost.
- **Batch:** the half price is not available for the look-again way as we send it. Whether it is available for the plain way is pending.

## What this says about cost

| Choice | Cost against today's (high, high) | What is given up, as far as seen |
|---|---|---|
| Thinking medium | About 40 % | Fewer pieces (2 or 3 against 4); the fan found in about half the runs |
| Thinking low | About 25 % | No second look at all; one or two pieces; the fan mostly missed. This is the plain way with a transcript, at a similar price. |
| Picture quality medium, thinking high | About 70 to 80 % | Nothing seen on these two clips: 5 pieces on C0113, the fan found |
| Picture quality low, thinking high | About 55 to 100 % (it varied) | Nothing seen on these two clips, and no steady saving |

**Reading:** the look-again way earns its price only at high thinking. Below that it stops looking again. The one setting that saved money without a visible loss here is picture quality medium with thinking high. That rests on two clips and one run each.

## Not known

- Whether the extra pieces and details at high thinking are right. Table 3's questions are for Deepa.
- Whether picture quality medium loses small things (text on screen, a fine detail) on other clips. Neither test clip has any.
- The cost figures do not take off the discount for the cached tokens in three runs.
- Longer clips: both test clips are 13 seconds or less.
