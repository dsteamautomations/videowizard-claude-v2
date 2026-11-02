# Answers, old guidebooks

## 1. Start image, shot BEAT_01-B1-S1

### prompt

```text
Asset: start image of a video shot, a wide documentary frame that the camera will drift slowly right from. Mode: generate. No reference image is used; everything is described here.
Layout: the near house fills the left half of the frame, with a clear strip of sand left of its bamboo scaffold poles so the drift right never cuts the mason. The street recedes from the brick stack past the near house to three far houses at the upper right; the horizon sits in the upper third. Camera feel: slightly high, about 2 m up, from across the street, 35mm feel, deep focus from the near wall to the far houses.
Scene: a new sandy street of half-built single-storey brick houses in rural Tamil Nadu, under neem and coconut trees. Mid-morning sun high to one side of the street, warm white and hard on the brick walls and sand, soft shade under the neem trees; clean air, a little dust lifting near the brick stack.
Near house: front wall of red-orange burnt clay bricks laid flat and solid in English bond, full grey mortar joints, raised to a standing man's chest, a door opening halfway along it, two bamboo scaffold poles leaning at its left corner. On the wall top, at the mason's right, a shallow round iron mortar pan of wet grey mortar.
Mason: Indian man in his forties, slim, dark hair grey at the temples, thin moustache, beige short-sleeved collared cotton shirt with a pen in the pocket, charcoal trousers, open rubber sandals. He stands inside the house behind the right half of the front wall, seen from the waist up, facing the camera, bent slightly forward, head bowed to the wall top. His left hand holds one brick flat a hand's width above a fresh mortar bed at the end of the top course; his right hand holds a pointed steel trowel with a wooden handle.
Helper: Indian man in his fifties, grey hair, white long-sleeved cotton shirt rolled to the elbow, grey trousers, sandals. In profile, his right side to the camera, he walks left along the street, three metres from the near house, halfway to the brick stack, four bricks held flat against his chest.
Background: a waist-high brick stack on the sand six metres right of the near house, broken brick bats at its foot; beside it on the street side, eight plain grey cement bags on a wooden pallet, one torn open with spilt dust. The three far houses: one at plinth height, one at window height with bamboo poles, one nearly at roof height, all of flat solid brickwork. Four workers there: cream shirt carrying bricks in a head pan, white shirt mixing mortar with a spade, light-check shirt laying bricks on a far wall, beige shirt walking with a bucket. All in dark trousers and sandals.
Real photograph: muted true-to-life colour, standard contrast, no added sharpening. Mortar droppings along the near wall top, chipped edges and mixed tones on the stacked bricks, footprints and wheelbarrow tracks in the sand.
Constraints: every wall is bricks laid flat, no cavities, no rat-trap pattern; no helmets or safety vests; no lettering on bags, walls or anywhere; no extra people; no HDR, glow or glossy finish.
Render only explicitly requested image text. Do not add unrelated logos, signatures or captions.
```

### checklist

| check | pass_when | weight |
| --- | --- | --- |
| Brick laying on every wall | All walls, near and far, show bricks laid flat in solid courses; no cavities or rat-trap pattern anywhere | must |
| The mason's start state | Behind the right half of the near wall, facing camera with head bowed, one brick held flat a hand's width above the end of the top course, trowel in the other hand | must |
| The mortar pan | A round iron pan of grey mortar on the wall top at the mason's right | must |
| The helper's start state | On the street about three metres right of the near house, in profile, carrying exactly four bricks against his chest, walking toward the house | must |
| Room for the drift right | Clear sand left of the scaffold poles; the mason not touching the left edge | must |
| Far houses and workers | Three far houses at three different heights; four workers at four different tasks | must |
| No text anywhere | Cement bags plain, no signboards, no captions, no watermarks | must |
| Dress | Light collared cotton shirts, dark trousers, sandals; no helmets or vests | must |
| Light | Hard mid-morning sun on brick and sand, soft shade under the trees, muted natural colour | should |
| Photographic look | Reads as documentary footage: no glow, no glossy finish, mortar droppings and tracks visible | should |

### exact_text

none (`[]`)

---

## 2. Still picture, shot BEAT_03-B2_sh2

### prompt

```text
Asset: a photographic still for a documentary, held on screen with a slow 5 percent push-in toward the brick face of the first floor, so the brickwork must stay crisp in detail there and keep a margin of sky and trees around the building.
Layout: the whole building framed between two neem trees standing at the left and right edges of the frame, a strip of sky above the roof terrace, the low compound wall and its iron gate along the bottom. Camera feel: eye level, about 1.6 m, from the far side of the street, 35mm feel, verticals straight, deep focus across the whole building.
Subject: a finished, lived-in three-storey house of exposed, unplastered red-orange burnt clay brick in a tree-lined street in rural Tamil Nadu. Exactly three floors of windows counted from the ground: ground floor, first floor, second floor. Above the second floor only the low parapet of the flat roof terrace and one black water tank; no fourth row of windows.
Brickwork: rat-trap bond over the whole front. Bricks stand on edge; each course shows long stretcher faces alternating with square header ends, each header sitting over a stretcher of the course below, all in thin grey cement-sand mortar joints about one tenth of a brick's height. No plaster, no paint.
Life: balconies on the first and second floors with potted plants and washing on the rails; clothes drying on a line on the roof terrace; a two-wheeler parked just inside the iron gate; a bicycle leaning by the gate; a worn path from the gate to the front door.
Light: warm late-morning sun from the upper left, hard, raking across the brick face so each joint casts a fine shadow; soft shade under the neem trees; natural, muted, true-to-life colour.
Capture: a real photograph from a mirrorless camera, natural light, no flash, no retouch, fine sensor noise, low micro-contrast, no added sharpening, muted saturation. Imperfections: dark rain streaks under the window sills, one chipped brick at the gate pillar's top corner, dust on the two-wheeler's mudguard, the washing line sagging toward the tank.
Constraints: no fourth floor; no plaster or render on the front; no people; no signboard, house name, number or lettering anywhere; no HDR, bloom, glossy surfaces or perfectly even sky.
Render only explicitly requested image text. Do not add unrelated logos, signatures or captions.
```

### checklist

| check | pass_when | weight |
| --- | --- | --- |
| Floor count | Exactly three floors of windows above ground; the terrace parapet and tank do not read as a fourth floor | must |
| Bond on the front | Bricks on edge in rat-trap bond (stretchers alternating with header ends) across the visible front, grey joints | must |
| No plaster | The front is bare brick throughout | must |
| No text | No signboard, house name, number or lettering anywhere | must |
| Whole building in frame | Roof terrace to front gate visible, neem trees at both edges, sky above, verticals straight | must |
| Room for the push-in | Margin around the building; first-floor brickwork sharp enough to hold a 5 percent push | must |
| Lived-in signs | Balcony plants and washing, roof-terrace clothes line, two-wheeler inside gate, bicycle by gate | should |
| Light | Hard warm sun from the upper left on the brick face, soft shade under the trees | should |
| Photographic look | No glow or gloss; at least the named imperfections visible | should |

### exact_text

none (`[]`)

---

## 3. Motion brief, take of shot BEAT_01-B1-S1

```text
The mason lowers the brick in his left hand flat onto the mortar bed at the end of the top course and taps it level twice with the trowel handle; a little mortar squeezes from the joint and his left hand comes to rest on the new brick. Then his right hand takes the trowel to the iron pan on the wall top, scoops mortar and spreads a fresh grey strip along the course beyond the new brick, ending with the trowel held just above it; his head stays bowed to the wall top throughout. At the same time the helper walks left along the sandy street, about three metres, carrying the four bricks against his chest, stops outside the right end of the front wall beside the mason, leans in and sets the four bricks flat in a stack on the wall top to the mason's left, then straightens with his hands empty at his sides and turns his head toward the mason. Down the street the four workers keep at their tasks: the head pan carried, mortar turned with the spade, a brick laid on a far wall, the bucket carried. A little dust lifts near the brick stack. Every brick stays laid flat.
```
