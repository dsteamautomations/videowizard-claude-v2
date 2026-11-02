# Killing the "AI look"

For any still that must pass as a real, unretouched photograph or frame: a portrait, reportage, a product in a hand, a phone snapshot, a casting shot. Also read it when a result "looks AI", "too glossy" or "not like the footage". Do not use it for illustration, 3D, poster graphics or stylised art; there the polish is the point.

## General: every category

Both picture models lean hard toward an idealised image. Left alone they beautify: skin loses pores, faces gain symmetry, clothes lose creases, backgrounds gain saturation. Anything in the footage or brief that differs from that ideal is quietly dropped unless you push it.

### 1. The default prior: where beautification starts

Check every row before writing. Where the brief or footage differs from the middle column, push the difference (step 2).

| Axis | What the model reaches for | What a real person or place usually has |
| --- | --- | --- |
| Eyes | large, round, wide-open, symmetric | narrow, hooded, monolid, one eye smaller |
| Face | narrow jaw, doll proportions, mirror symmetry | long or flat midface, visible asymmetry |
| Skin | poreless, glowing, even tone | pores, fine hair, redness, uneven tone |
| Body | idealised silhouette | flat, square, heavy, or simply ordinary |
| Clothing | tighter, newer, more skin | the exact coverage and wear shown |
| Hair | full, glossy, every strand placed | flatter, clumped, flyaways, dull ends |
| Stance | model pose, chin up | the awkward real stance |
| Casting | idol or influencer look | an ordinary person |
| Background | saturated, tidy, gradient | muted, cluttered, one named colour |
| Extras | adds earrings, props, signs, text | absent |

Steer toward the footage, not toward plainness. If the subject really is glamorous, describe that faithfully; the capture rules (steps 3 to 5) still apply.

### 2. State every difference in two places

A difference stated once, in passing, loses to the prior. State it twice:

1. **In the description**, measurably: "narrow eyes with a low single lid crease, iris about 60 % covered", not "unusual eyes".
2. **In the constraints**, one short line per axis, labelled: `EYES:`, `SKIN:`, `BODY:`, `HAIR:`, `MEDIUM:`. Where the picture model's prompt has no constraints part, fold the same lines into one short closing sentence.

This is the one place where naming the unwanted version is right; everywhere else describe what is there.

### 3. A capture path instead of adjectives

Do not ask for "realistic". Name the device and the path the file took; that carries the texture.

| Medium | What to state | Residue to ask for |
| --- | --- | --- |
| Video frame grab | grabbed from handheld footage, not a photo | soft detail, mild compression blocking, slight motion smear |
| Film scan | 35 mm colour negative, lab scan | visible grain, halation around highlights, soft blacks |
| Phone photo | phone camera, auto HDR off | smeared shadow noise, faint edge halo, slightly flat tone |
| Mirrorless or DSLR still | natural light, no flash, no retouch | fine sensor noise, natural falloff, unpolished skin |

State the medium as a fact of the picture, never as a render style: "a real phone photo", not "photorealistic render in phone style". Words such as "8K", "ultra-detailed", "masterpiece", "sharp focus" and "crisp" push the prior harder; leave them out (the vague-word table in `agency/deterministic-checks.md`).

### 4. Imperfections, and where they sit

An imperfection without a place is ignored or sprayed everywhere. Name the place:

- skin: "pores across the nose and cheeks, redness at the nostril wings, one mole below the left jaw"
- hair: "two flyaways above the crown, ends clumped on the right shoulder"
- fabric: "creases at the elbow bend, collar sitting slightly askew on the left"
- surroundings: "scuffed skirting board behind the subject, uneven paint on the wall"
- optics: "one blown highlight on the forehead, slight motion blur on the near hand"

Match the footage, but never set the count to zero.

### 5. Sharpness and grading

- Ask for no added sharpening and low micro-contrast.
- Grading: flat or natural, muted to moderate saturation, low contrast, unless the footage clearly shows otherwise.
- In the constraints, ban the glow family: HDR, bloom, high clarity, luminous or radiant skin, glossy hair highlights, a perfectly even background.

### 6. Self-check before sending

- Every axis from step 1 that differs appears both in the description and in the constraints.
- No booster word survives.
- A capture path from step 3 is named, as a fact, not a style.
- At least three located imperfections, each with a place.
- Sharpness and grading lines are present.
- Anything the model likes to add but the brief does not contain (glasses, earrings, a second person, signs, captions) is named as absent, briefly.
- Nothing in the constraints contradicts the description (asking for grain while banning grain).

### 7. When the result still misses

Treat every mismatch as a fact that was under-specified, not as a bad roll. Split the description into finer facts, sharpen its constraint line, and make it again: one change per attempt. Re-running an unchanged prompt returns the prior.

## For documentary-explainer and training-education

- A still that sits next to real footage takes the frame-grab capture path, so it matches the clips around it.

## For social-ugc

- The phone-photo capture path: eye-level, auto HDR off, the room's own light.

## For advertisement-product

- A product in a real hand: the hand gets the same located imperfections as any skin; the product itself stays clean and exact (its traits from the approved sheet).
