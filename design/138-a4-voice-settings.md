# design/138 A4: what the voices page could offer, what each choice does, and the work (2 Nov 2026, for SK)

SK asked: which values could be shown, what happens when the operator changes each one, can the operator hear the change, and how big is the change to build.

## What the system can use today (read in `server/app/elevenlabs.py`)

The server already accepts a voice model and its settings on every audition and narration, and checks them. The chat tool can send them; the voices page never does, so it always gets the default.

| Model | Settings it takes | Today's default |
| --- | --- | --- |
| Eleven v4 (the default) | stability, similarity | 0.5, 0.75 |
| Eleven Multilingual v2 | stability, similarity, style, speed, speaker boost | 0.5, 0.75, 0, 1.0, on |
| Eleven v3 | stability only, and only 0, 0.5 or 1 | 0.5 |

## What each setting does to the voice

| Setting | Range | Lower | Higher | When to change it |
| --- | --- | --- | --- | --- |
| Model | v4, Multilingual v2, v3 | | | v4: natural English narration. Multilingual v2: steadier for Indian languages and mixed-language scripts; the only one with speed. v3: the most expressive, follows emotion tags; less predictable. |
| Stability | 0 to 1 | more expressive and varied from line to line; can wander or over-act | flatter, steadier, the same delivery every take; can sound monotone | lower for a story or an advertisement, higher for a training or a technical film |
| Similarity | 0 to 1 | freer, can drift from the chosen voice | closer to the original voice; at the top it can copy recording noise | rarely; keep around 0.75 |
| Style (v2 only) | 0 to 1 | neutral | exaggerates the voice's own style; slower to make, can sound affected | an advertisement or a character voice |
| Speed (v2 only) | 0.7 to 1.2 | slower | faster | to fit a narration into its time, or a calm training film |
| Speaker boost (v2 only) | on or off | | on: a little clearer, closer to the voice | leave on |

## Can the operator hear a change?

Yes, but only by making a new audition: a setting changes nothing until the passage is read again. Each audition is one paid request (a few seconds of the test passage, a small share of the account's monthly characters) and takes about 10 to 20 seconds. The page already plays auditions side by side, so the operator would compare the same passage read with the old and the new settings.

## A problem found while looking (a fault, whatever is decided)

The page makes the **narration** with the default settings, even when the audition the operator chose was made with different ones in chat. So the full narration can sound different from the audition that was approved. Whatever is decided for A4, the narration should use the settings of the chosen audition.

## The work, by option

| Option | What the operator sees | Work |
| --- | --- | --- |
| **Show and allow change** | the model and each of its settings, with the effect line above under each; "Try again with these settings" re-reads the passage; the chosen audition's settings carry into the narration | the page: a model choice, sliders per model, the descriptions, passing them on the audition and narration calls; the server accepts them already. About a day, with tests; no change to the chat tool |
| **Show only** | the model and settings used for each audition, as a line under it; the narration uses the chosen audition's settings | the page: one line per audition; about half a day |
| **Leave as it is** | nothing | only the narration fault above should still be fixed (an hour) |

Recommended: **show and allow change, with three presets above the sliders** (steady narration; expressive story or advertisement; calm and slower training, which picks Multilingual v2 for its speed) so most operators choose a preset and hear it, and only a skilled operator touches the sliders.
