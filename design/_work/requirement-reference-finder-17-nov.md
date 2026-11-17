# Requirement: Claude finds the footage pictures, with helper threads

17 Nov 2026. For SK's approval. **Nothing is built.**

## SK's idea, restated

> "Claude can make use of a Gemini description, which extends to a time-based thing, and it can predict which of the frames will contain the image that it is looking for. Then it can round up certain frames and start looking for the best one and finally settle down on where the reference image looks its best. The search, when done across multiple places, can result in multiple reference images at different angles."
>
> "This … taking time can be overcome by assigning multiple subthreads, where each thread will start looking for a specific object."

In my words:

1. **Predict.** For each thing in the plan, Claude reads Gemini's timed description of the footage and names the moments most likely to show it well.
2. **Round up.** It takes a few trial frames at those moments.
3. **Look.** It looks at them and keeps the best one for each view.
4. **Several views.** Because it searches several clips, a thing can end with two or three pictures from different angles.
5. **Fast.** Several helper threads work at the same time, each on its own things.

## Is it possible on every operator's machine? Yes

The plugin already ships eight helper threads (for drawings, plan gaps, the guide and motion checks) and the team's machines run them today. The guard allows the plugin's own helpers and blocks all others. So this needs one new helper of the same kind, not a new ability.

## What changes, by actor

| Job | Today | After |
|---|---|---|
| Hand over the timed description | Server drops the sub-clips | Server gives a digest of every clip: what happens in each part, shot size, angle, best frame, usable window, defects, and each object's first and last second |
| Predict where a thing shows | Server, word match | Claude helper reads the digest |
| Take trial frames | Not possible | Server cuts a trial frame on request. It is free and is **not** yet a reference |
| Look and choose | Nobody | Claude helper looks, keeps the best per view, and writes one line of what it saw |
| Record the choice | Claude, unseen | Claude; the server refuses a footage picture that has no recorded look |
| Say "not in the footage" | Server, when nothing was grabbed | Claude helper, with what it searched and the closest it found |
| Approve | Operator, one yes for all frames | Operator, each picture on its own (unchanged actor) |

## Expected though not said

- The views come from the plan (for the pan: "side" and "tipped, pouring"). Where the plan names none: the thing whole and at rest, and one view in use.
- A frame is a good reference when the thing is whole, unobstructed, large enough, sharp, and its shape and size can be read. This rule is written once and given to every helper.
- Clips left out of the edit are searched too.
- A thing that is only ever small in the frame is kept, with a note that it is small. Cropping is a later step.
- The page shows each picture with its view and the helper's one line, and "not found" with the closest picture, so the operator can say "that is it".
- Nothing here is tied to one kind of film.
- The chat way back shows the same pictures and lines.
- People: unchanged. A person's sheet is still made from words, or from their photo with recorded permission.

## Limits (to keep it fast and bounded)

| Limit | Proposed |
|---|---|
| Things per helper | About 5, grouped by kind |
| Helpers at one time | Up to 6 |
| Trial frames per thing | Up to 8 |
| Pictures kept per thing | Up to 3, one per view |
| Size of a trial frame on the laptop | Small (about 640 px), enough to judge |

On VW-24 that is about 10 helpers for 50 things. I expect minutes, not tens of minutes; the trial will give the real figure.

## Edge cases

| Case | Handling |
|---|---|
| The thing is not in the footage | "Not found", with the clips searched and the closest picture, if any |
| The analysis has no entry for a clip | The clip is named as not searched; never "no picture" |
| Two views can only be found in one clip | Two frames of the same clip at different seconds are allowed |
| Two trial frames are nearly the same picture | One is kept (the server already compares pictures) |
| The same frame is the best for two things | Allowed; each thing records its own look |
| The best frame is blurred or half covered everywhere | Kept as "weak", shown as weak; the operator may still use it or ask for a set made from it |
| Very long footage (300 clips or more) | The digest is split by clip group; a helper reads only the groups that mention its things |
| Very few things (1 to 5) | No helper; Claude does it itself |
| A film with no footage | The step is skipped, as today |
| A helper is stopped or fails | Its things are searched by Claude itself, or shown as "not searched" |
| The run is taken over on another machine | The recorded looks and chosen frames are on the server; nothing is redone |
| The plan changes after the search | Only the changed things are searched again |
| The operator rejects a picture | Claude offers the next best it had seen, without a new search |
| A real person is in the chosen frame of a thing (hands holding the pan) | Allowed for a thing, as today; a person's own reference follows the people rule |

## Failure modes

| Failure | Handling |
|---|---|
| A trial frame cannot be cut | That moment is skipped and named; the others go on |
| The server is slow or refuses under load | Trial frames are limited per run at one time; a helper waits and retries once |
| Helpers cannot be started on a machine | Claude searches thing by thing itself; slower, same result |
| A helper reports a picture it did not look at | The server records a look only with the trial frame's own id, so a look cannot be claimed for a frame never fetched |
| The digest is missing (old run) | The older way is used and the operator is told the search was by words only |

## The older way

The word match (`vw visuals elements`) is **kept as the way back** for a run with no digest, and is listed in the decision log. It is no longer what the assistant is told to use.

## Tests first

- Server: the digest holds the sub-clip fields for a clip with and without sub-clips; a trial frame is cut, is not a reference and is not shown to the operator; a footage picture without a recorded look is refused by name; a look for an unknown trial frame is refused; limits per thing and per run hold; an old run without a digest falls back.
- Plugin: the tool writes the digest in groups; trial frames land in the run folder at the small size; the guard allows the new helper and its calls and nothing else; with no helper available the same commands work one by one.
- Instructions: the frame rule and the "not found" wording, pinned by test; the old sentence retired by name.
- A trial on VW-24 before the build is released (see below).

## The trial I propose first

Before any product code, on this PC, on VW-24's footage, without touching the run:

1. Build the digest from VW-24's stored analysis.
2. Run the helper's method on ten things, including the pan, the stone heap, the trowel, the bricks and the bucket.
3. Report: how many good pictures and views it finds, how long it takes, and how many of the 41 paid sets it would have made unnecessary.

This costs nothing on the picture models and shows the result before you decide.

## Not covered

- Claude's look at the **made sets** (all three pictures, against the film and the plan). Same idea, a second requirement.
- Making a set **from** the chosen footage pictures. That is a change to how sets are requested.
- Cropping a small thing out of a frame.
- The other gaps of the revised analysis.
