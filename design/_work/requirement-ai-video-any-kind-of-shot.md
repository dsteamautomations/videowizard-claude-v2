# Requirement list: any kind of shot may be an AI video; untried kinds warn, they do not refuse

**Status:** requirement list only, 16 Nov 2026. Nothing is built. Waiting for SK's approval or additions.

**Why:** SK, 16 Nov 2026. Today an AI video may be only one of three kinds, all with a person: a person walking; one action seen from close; a pour, a pick-up or a hand-over seen from close. A machine running with nobody in the frame, a product turning on a table, a vehicle, a crowd: all are sent to footage, a still or a drawn diagram. That does not fit a tool that makes every category of video.

## 1. The requirement, restated

1. **Any kind of shot may be planned as an AI video.** The list of three stops being the only door.
2. **The three proven kinds keep everything they have today**: their tested instructions, their checks, their default wording.
3. **Any other kind is allowed, with a warning to the operator** in plain words: "this kind of shot has not been tried here; the first take is a trial and may need a second." It is a warning, not a refusal (the rule of 14 Nov: flags warn, they do not block).
4. **A shot with no person is a normal shot.** A conveyor, a robot arm, a bottling line, a product, a landscape, weather, water, smoke.
5. **Only what has actually been seen to fail is named**, each with its reason and what to do instead. Nothing is refused for "no evidence".

## 2. What stops a shot today (four places), and what each becomes

| # | Where | Today | After |
|---|---|---|---|
| 1 | The assistant's instructions for the visuals stage | "It is one action per shot, of three kinds… Any other kind (a crowd, a vehicle, a run, a door, night, people speaking) is not yet available as AI video: make it footage, a still or a drawn shot." | Any kind may be an AI video. Three kinds are proven here and are named with what they are. For any other kind: describe plainly what moves, how far, how fast and in what order; expect a trial take. The known weak cases (row 4 below) are listed with their reasons |
| 2 | The plan check (`visual_contract.py`) | The shot's kind may be one of the three words or empty; any other word is refused | A fourth word, `other`, is accepted. A shot marked `other` adds one warning to the plan, told to the operator |
| 3 | The scene description check, when the guide is written (`guide_spec.py`) | Refused unless the kind is one of the three | `other` is accepted. The scene already allows an empty list of people and set pieces that turn; nothing else changes |
| 4 | Two limits in the plan check | More than four people: refused ("a crowd is not yet available"). A camera that circles a person: refused | Both become warnings with their reason. The register itself marks the four-people rule "contradicted" (crowds of six to nine people came out clean in 14 of 16 runs on the consultant's machine) |

The kinds named as "not yet available" today, and what the evidence says:

| Kind | Evidence in the register | After |
|---|---|---|
| A crowd crossing | 14 of 16 runs clean on the consultant's machine; walkers one to two seconds late | Allowed, warning: not tried here; timing may be late |
| A vehicle | Two clean runs of one car | Allowed, warning: not tried here |
| A door | Five of five clean when the path does not clash with the door; failed when it clashed | Allowed, warning: keep the person's path clear of the door's swing |
| A run or sprint | A pan that follows a sprinter failed two of two | Allowed with a fixed camera; warning names the failing case (a following pan) |
| Night | No run found | Allowed, warning: not tried here |
| People speaking | Out of scope by SK's narration-only decision; takes are made without sound | Allowed as a picture; warning: the take has no sound and lips will not match words |
| Four people crossing with paths that overlap | Copies of people in about seven of twelve runs | Allowed, warning names it: keep paths apart, or expect a retake |

## 3. Unstated but expected

- A plan already accepted with one of the three kinds stays valid, unchanged.
- The warning is told once per plan, listing the shots it covers, not once per shot.
- The treatment may now name "AI video" for a gap with no person; nothing at the treatment refuses it today, but the assistant's instructions steer away from it. That steer is removed.
- The operator still gives their word before any paid take; that is unchanged, so a trial take is never bought silently.
- The take's record keeps the kind (`other`) and the plain description, so later we can see which untried kinds worked.
- The rules that are about a person (one activity per person, the right hand, one thing changing) stay as they are and apply only when a person is in the shot.
- The length limits of a take (3 to 15 seconds) are the video model's limits and stay.
- The plain-language guide for the operator and the guide skill's text say the same as the instructions.

## 4. Edge cases

| Case | Handling |
|---|---|
| No kind given on an AI video shot | As today: taken at the plan; when the scene is written it must name a kind, and `other` is now a valid answer |
| A shot marked `other` that is really a walk | Taken. The helper loses the walk's tested instructions; the instructions say: use the proven kind when the shot is one |
| A shot marked `other` with no description of how the thing moves | Refused when the scene is written, as today for every kind (the description of the real process is already required) |
| No person and no moving set piece (nothing moves) | Warning: nothing moves in this shot; a still costs less |
| A person plus a machine | Allowed; one clean set of runs exists (a person and an animated object). No warning beyond `other` if it is not one of the three |
| More than four people | Warning, not refusal |
| A circling camera | Warning with the reason (the place can change between angles) |
| A plan with many `other` shots | One warning lists them; the cost line already shows the retake allowance |
| An unknown word for the kind | Refused, naming the four words |
| An older plugin | Works: the change is on the server and in served text. The guide skill's text is in the plugin, so the plugin version rises and laptops update at the next stable release |
| A film from before this change, mid-plan | Its plan is checked by the new rules on its next proposal; nothing accepted is reopened |

## 5. Failure modes

| Failure | Handling |
|---|---|
| A trial take of an untried kind comes out wrong | The existing path: fix once, then cut or change the shot, then hide the detail (SK, 10 Nov). The rejection's reason is recorded with the kind |
| The guide of boxes cannot express the shot (water, smoke, cloth) | The warning for `other` says so. The assistant may still plan it; the scene check reports what it cannot build, in plain words, and the shot is changed to a still or footage |
| The operator does not read the warning | The warning is shown again on the "ready to shoot" card, before the paid take |

## 6. Old way (for design/35)

- "An AI video shot is one of three kinds; any other is refused as not yet available." **Retired.** The three kinds remain as the proven ones.
- "More than four people near the camera is refused" and "a circling camera is refused." **Retired as refusals; kept as warnings.**
- "A kind opens after three passes here and SK's yes" (integration requirement E4). **Retired.** Replaced by: every kind is open; the record shows what worked.

## 7. Tests first (server, database-free)

- The plan check takes `other`; refuses an unknown word and names the four.
- A plan with an `other` shot carries one warning listing those shots; a plan without one carries none.
- Five people in an AI video shot: a warning, not a refusal. A circling camera: a warning, not a refusal.
- The scene check takes `other` with no people and a turning set piece; still refuses a missing description of the process.
- The scene check with nothing that moves: the "nothing moves" warning.
- The served text no longer says "not yet available"; it names the three proven kinds and the known weak cases. The word pin for the visuals stage is updated.
- The three proven kinds: every existing test passes unchanged.

## 8. Not covered

- **No trial has been run.** Whether a machine-only shot comes out well through the guide of boxes is unknown until the first take. This change only opens the door.
- **Whether the guide of boxes is the right route for shots with no person at all** (a landscape, water, a product on a table). A plain still turned into a clip with no guide may suit them better. That is a separate question and is not in this list.
- No counter of passes per kind, and no automatic "proven" status. If a kind proves itself, it is named as proven on SK's word.
- The warnings for the seven named cases come from the consultant's runs, not ours.
- Sound on takes and speaking people with matching lips: outside this change.

## Correction to an earlier statement

On 16 Nov I told SK the video model had changed on 14 Nov. That was wrong. The model that changed on 14 Nov is the one that watches the operator's footage. AI video takes are still made with the same model as when the three kinds were tested.
