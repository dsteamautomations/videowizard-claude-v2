# The references step, reviewed on VW-24

17 Nov 2026. An opinion for SK, with the evidence. **Nothing is built or changed.** VW-24 was only read.

SK's two observations, from the operator's side of VW-24:

1. The pan was shown half filled with concrete, so its size and shape could not be seen. Could two frames be shown, from different views?
2. For the gravel stone, a picture of something else was shown. Is the analysis made by Gemini not being used, with a simpler program inferring the objects instead?

**Short answer: both observations are right, and the second is the cause of most of what is wrong in this step.**

---

## 1. What I checked

| Checked | How |
|---|---|
| The code and the instructions for choosing a footage picture | Read by a helper, each claim with its file and line |
| VW-24's 50 planned things, its 10 footage pictures, and what the analysis says about its 94 clips | A read-only script on the server |
| The two pictures SK named | I looked at them myself |

## 2. What happens today

1. The plan lists the things the film needs (VW-24: 50 people, objects, materials, places and techniques).
2. A small program on the server compares **words**: the thing's name against the names and descriptions of the objects Gemini listed for each clip. Two shared words is a match.
3. The program gives the assistant one line per thing: "seen in clip X at N seconds". N is the moment the object is **first seen** in the clip.
4. The assistant picks a clip and a second, and the server cuts that frame.
5. **Nobody looks at the frame.** No model, and not the assistant. The operator is the first to see it.
6. Where the assistant grabbed nothing, the page says "your footage has no picture of it" and offers a paid set.

## 3. What VW-24 shows

**The word program is mostly noise.**

| The thing in the plan | What the word program matched |
|---|---|
| Clean water | Concrete cover blocks |
| Wide flat brush | Steel reinforcement rods |
| Spirit level | Steel reinforcement bars |
| Cement bag | A stack of roof tiles |
| Heap of crushed stone | A pile of wet concrete (a tie with the real stone heap; the tie was broken by the clip's name) |
| Street of houses | "Bright yellow out-of-focus object" |

- 43 of the 50 things got a "match". Most are of this kind.
- The time given was 0.0 seconds for almost every match, so it says nothing about the best moment.

**The assistant, with a poor hint, grabbed little.**

- Footage pictures were taken for only 8 of the 50 things (10 frames).
- 41 things went to a paid set, about ₹1,450.

**Things the footage does show, by Gemini's own list, that got no footage picture:**

| Thing | What Gemini recorded |
|---|---|
| Mason's trowel | Named in three clips, with its handle colour and the hand that holds it |
| Red clay brick | "Rectangular red clay bricks laid flat along the right border" |
| Heap of crushed stone | Two clips: "Large heap of dark grey crushed stone aggregate on the ground" |
| Concrete mix pile, sand bed, buckets | Each named and described |

For these the operator was told "your footage has no picture of it". That sentence is not true: it means only that the assistant did not grab one.

**The two pictures SK named. I looked at both.**

- **The pan.** The frame is from the moment of pouring. Concrete covers the pan; its rim, depth and size cannot be read. The assistant chose this moment on purpose (it named the frame "metal-pan-tipping"). The plan had asked for two views of the pan, "side" and "tipped, pouring". Only one was taken, and the side view, which shows the shape, was not.
- **The stone heap.** The frame shows two workers bending in a yard in front of a building. A little gravel is at the bottom edge. It was cut at 0.7 seconds of a clip that Gemini describes by its building, not by a stone heap. Gemini had named two other clips that show the heap clearly. The operator rejected it, rightly.

Either picture would have failed a two-second look by a model.

## 4. Is Gemini's analysis being used? No, only a thin slice of it

| What the analysis holds for every clip | Reaches this step? |
|---|---|
| The list of objects with a description, first and last second seen | Yes, but read only by the word program |
| The clip cut into sub-clips, each with what happens in it | **No. Dropped when the visuals package is built** |
| The best frame of each sub-clip (`hero_frame_s`) | **No** |
| Shot size and camera angle of each sub-clip (close, wide, from above) | **No** |
| The usable window, the quality grade, defects with their times | **No** |
| What state things are in at the end (`outcome_state`) | **No** |

So the analysis already knows where the close shots are, which second is the cleanest, and when the pan is being carried and when it is being tipped. None of that is passed on. The instruction to the assistant says "search the clip analyses first", but the package it is given does not contain them, and no command in this stage fetches them.

## 5. Are the two earlier steps passed on in full? No

The treatment and the plan were improved in the last days (designs 202 to 207). What this step does with their output:

| Produced earlier | Used when footage pictures are chosen? |
|---|---|
| The thing's name and requirements | Yes (by the word program) |
| The views the plan asks for (`required_views`, e.g. pan: side; tipped, pouring) | **No** |
| The thing's description, identity and signs of use | **No** |
| Its sizes and its material | **No** |
| Which shots use the thing, and how close those shots are | **No** |
| The Direction of the film (from the treatment) | **No** |
| Where the first cut already uses each clip | **No** |

The plan's views are also not used when a paid set is made: the set uses fixed views.

## 6. SK's question 1: two frames at a time

Yes, and the page can already show up to four per thing. Two things stand in the way of it being useful:

- The instruction says "a frame of each", so the assistant takes one.
- **Only the first frame is ever used.** One "yes" approves all the frames of a thing together, the first becomes the thing's picture, and when a set is made only the first is given to the image model. A second angle would be shown to the operator and then thrown away.

So the answer is: take one frame per view the plan asks for (two or three), let the operator say yes or no to each, and give all the approved ones to the image model.

## 7. What is missing in this step, in order of value

| # | Missing | What it would do |
|---|---|---|
| 1 | **A model looks at every frame before the operator.** It is asked: is the thing whole, unobstructed, large, sharp, its shape and size readable? | The pan and the stone heap would both have been refused and replaced. This is the largest gain for the least work |
| 2 | **The sub-clips of the analysis are passed on:** what happens, shot size, angle, best frame, usable window | The assistant can choose "the close shot where the pan is carried empty", not "second 0" |
| 3 | **The word program is replaced by a model's reading** of the plan's things against the analysis, once per film: for each thing, the clips that show it, the best second for each view, and why | Ends "clean water = cover blocks". Finds the trowel, the bricks, the stone heap |
| 4 | **One frame per view the plan asks for,** each answered on its own, all approved ones given to the image model | SK's question 1 |
| 5 | **A frame rule that says what a reference is:** the thing alone or clearly apart, whole, empty or clean, at rest, and one view in use | Today the rule says only "sharpest, large, evenly lit" |
| 6 | **"No picture of it" says the truth:** "none was found; the closest the analysis has is …", with that picture shown | The operator can say "that is it" and save a paid set |
| 7 | **A crop:** when the thing is small in the frame, the reference is the cropped region | Many objects are only ever seen small |
| 8 | **The plan's views drive the paid set too** | The set shows the angles the film needs |

Items 1, 5 and 6 are small. Items 2 to 4 are one piece of work and belong together. Item 7 can wait.

**The money side.** VW-24 was about to pay for 41 sets. A fair guess from Gemini's list is that 8 to 12 of them are for things the footage shows well enough. That is ₹300 to ₹400 on this film, and, more important, a reference from the real footage matches the film better than a generated one.

## 8. Not checked

- I looked at two of the ten frames, the two SK named. The other eight were approved by the operator.
- "8 to 12 sets saved" is my estimate from the object names, not a count made by looking at the clips.
- I did not test a model's look on these frames. I expect it to refuse both, but that is not proven until tried.
