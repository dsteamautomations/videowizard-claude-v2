# Gemini Omni 1.1 Flash: how it reads words

How the video model reads a motion brief, for whoever writes one. The server picks the model, the resolution and the wait, and writes the picture tags, the camera line, the single-scene line, the length, the beat timeline and the end state around your brief (`playbooks/video-clip.md`). The facts below come from Google's own pages, read on 19 Oct 2026.

## General: every category

### What reaches the model

- Two frames only: 16:9 and 9:16. A start image is made at one of them.
- Write the brief in English; Google says other languages have not been evaluated.
- Uploaded pictures of certain recognisable people are refused; VideoWizard never sends a person's picture.
- A blocked prompt is rewritten, never sent again unchanged.
- Every clip carries Google's invisible watermark (SynthID); see compliance C16.
- There is no negative-prompt field. Negatives go in the brief, short and specific ("no hands").

### How it reads a brief

- Omni needs less spelling-out than older video models; Google says it does not have to be as prescriptive.
- The start image already holds who, where, the look and any text. Write only what moves: the subject's one action with one physical detail, then one or two movements in the surroundings. Do not retell the picture.
- Vague briefs ("make it move") give weaker clips than specific descriptions of the subject's motion and the effects around it.
- Lead with the subject and the action; describe what is seen, not what it means.
- Left alone, Omni makes a few different shots. The server's single-scene line holds it; do not add another.

### Timing inside the take

An action may be timed in plain words ("after about three seconds she sets the cup down"); Google says no special syntax is needed. No cuts, no timecode windows, no frame counts.

### Text in the take

Text already in the start image stays as it is; never ask the take to add, change or animate words. Google's model card says perfectly accurate text remains a challenge: check every character survived the motion.

### With an end image

Describe the action that carries the start into the end. The camera does not move between them; the server adds the frame lines.

### Known limits, and the fix

| Habit | Fix |
| --- | --- |
| Complex motion breaks (named as a challenge in the model card) | One action per take |
| The subject or the label drifts | Compare with the approved start image; make the take again from it |
| Text in frame is misspelled | Check every character; never rely on a take for a logo or legal text |

## For advertisement-product

- Google names bringing product shots to life as a use. The product's shape and label must survive the motion: read the label in the last frame.

## Not available yet

VideoWizard makes silent, steady, single-shot takes at final quality today. Filed for categories that may want more:

- **Sound (advertisement-product, social-ugc, narrative-story):** Omni makes an audio track by default. Music is described by its kind; a spoken line names the speaker and gives the line; a sound can be tied to an action. Voice editing is not supported: dialogue cannot be added to footage of someone already speaking.
- **Editing a clip:** simple prompts work best; long ones cause changes nobody asked for. One change per turn, closed with "keep everything else the same". Compare every edit with the approved clip, not the previous edit.
- **Extending a clip (narrative-story):** "the scene continues" or "extend this video"; one beat per extension; up to 40 s in all, each extension reading the last 10 s. Google edits some final frames to blend the join, so keep the approved clip as its own version.
- **Timed cuts and windows (narrative-story, social-ugc):** natural-language cuts ("every 2 s cut to a new frame") and timecode windows both work.
- **Words animated on screen (social-ugc):** one word at a time, each for about a second, works.
- **Loops (social-ugc):** the same picture as start and end gives a loop.
- **Phone, webcam or film-camera looks (social-ugc):** Google lists them as camera words.
- **Picture and clip references:** reference pictures, and up to three reference clips of up to 3 s each, guide a person or object without being the first frame.
- **Drafts at lower resolution:** Google suggests 3 or 4 low-resolution drafts varying one thing, then a final run; the final is a new generation, so compare again.
