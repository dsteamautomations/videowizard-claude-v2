# 175 — SK's staging rules for right-handed action, for every prompt from now on (5 Nov 2026)

SK, 5 Nov night: "include this in all of our upcoming prompts and have this as an important note." Four rules, SK's wording condensed; the examples are his.

| # | Rule | The logic | How to write it | SK's example |
|---|---|---|---|---|
| 1 | **Right-facing geometry.** The object's handle, grip or opening faces the right of the frame or the right hand's approach path. | the model never has to rotate the object mid-air or warp the wrist | place the object on the right and orient its features to the right | "A coffee cup sits on the right side of the table with its handle pointing directly to the right. A person naturally reaches out with their right hand to lift it smoothly." |
| 2 | **Over-the-right-shoulder anchor.** The camera favours the right side of the body: over the right shoulder, or a right-profile angle. | hiding the left side keeps the model from choosing the wrong arm | use over-the-shoulder or right-profile shots so the right arm is the focus | "An over-the-shoulder camera angle looking past a person's right side. The camera tracks their right arm as it extends forward to cleanly pick up the object from the desk." |
| 3 | **A passive task for the left hand.** The left hand rests on a surface, sits in a pocket or holds a still background object. | it removes the two-handed grab and the wrong arm | state the left hand's resting place and that the left arm stays still | "A person with their left hand resting flat on the table uses their right hand to pick up the key. The left arm remains completely still." |
| 4 | **Left-to-right action flow.** The subject starts left or centre, the target sits on the right; describe the character, then the rightward movement, then the object on the far right. | the model plans frames in reading order | character first, the rightward move, the object last on the far right | "A person standing on the left side of the frame extends their right arm horizontally toward the right end of the screen, cleanly gripping the handle of a bucket positioned on the far right." |

**Where it binds:** every take text (Wan, Gemini Omni), every Blender brief (design/172: object placement and the camera), the plan's staging rules (design/161 §4) when the build comes. When a plan's fixed order conflicts (design/157: the pile stays on the mason's left), the plan's invariant stays and the *reached-for* object is placed on the actor's right so the right hand still moves rightward.

**First application:** the mason atom's prompt in Alibaba's formula, revised (design/174 §"Revised with the right-handed rules"), not run.
