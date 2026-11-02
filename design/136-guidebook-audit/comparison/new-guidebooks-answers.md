# Answers: three shots, rat-trap bond film

Guidebooks read: new/always (all four), then new/start, new/still-scene or new/take per job. Nothing else opened.

## 1. Start image, BEAT_01-B1-S1

Files opened: always/RULEBOOK.md, always/answer-form.videowizard.md, always/deterministic-checks.md, always/VW-MAP.md, start/video-frame.md, start/FACT-SHEET.md, start/consistent-character-frames.md, start/gap-fill.md.

**prompt**

```
Scene: a real frame grabbed from steady documentary footage of a new sandy street of half-built single-storey brick houses in rural Tamil Nadu, South India, mid-morning. Seen from across the street, about 2 m up and slightly high, a 35 mm feel, deep focus from the near wall to the far houses.

Layout: the near house fills the left half of the frame. Its front wall of solid brickwork stands chest-high to a standing man, a door opening midway along it, two bamboo scaffold poles leaning at its left corner. The mason stands behind the wall's right half, seen from the waist up above it. About three metres right of the wall's right end, on the street, the helper walks toward the wall. About six metres along the street from the near house, at the right edge, a waist-high stack of red bricks with broken bats at its foot, and beside it on the street side eight plain grey cement bags on a wooden pallet, one torn open with spilt dust. The street recedes to three more half-built houses at the upper right; the horizon sits in the upper third. Keep open sandy street along the right side of the frame for a slow sideways move to the right.

Subject: the mason, the instant before he lays a brick. An Indian man in his forties, slim, dark hair with grey at the temples, a thin moustache, a beige short-sleeved collared cotton shirt with a pen in the pocket, charcoal trousers. He bends slightly forward over the wall, head bowed to the top course. His left hand holds one red brick flat a hand's width above a fresh grey mortar bed at the end of the top course; his right hand holds a pointed steel trowel with a wooden handle just above the wall top. A shallow round iron pan of wet grey mortar rests on the wall top at his right.

Helper: an Indian man in his fifties, grey hair, a white long-sleeved cotton shirt rolled to the elbow, grey trousers, open sandals; in profile, right side to camera, walking left, both forearms holding a stack of four red bricks against his chest, head turned toward the near house.

Background: three far houses at different stages, one at plinth height, one at window height with bamboo scaffold poles, one nearly at roof height, under neem and coconut trees. Four workers there, each at a different task: a cream shirt carrying bricks in a head pan, a white shirt mixing mortar with a spade, a light-check shirt laying bricks on a far wall, a beige shirt walking with a bucket; dark trousers, open sandals.

Details: every wall is conventional solid brickwork: red-orange country-burnt clay bricks with chipped edges and mixed tones, laid flat on their widest face in English bond, full grey mortar joints. Mortar droppings along the wall top; footprints and wheelbarrow tracks in the sand. Hard mid-morning sun high from the left of the frame, short sharp shadows on the walls and sand, soft shade under the neem trees, a little dust lifting near the brick stack. Palette: red-orange brick, grey mortar, beige and white cotton, dark trousers, green foliage, pale sand; muted, natural, standard contrast. The mason's face is lined, skin uneven with sweat at the temples; the helper's shirt is creased at the elbows.

Constraints: no bricks on edge, no cavities, no rat-trap pattern in any wall; the brick is not yet laid; one brick in the mason's hand. No helmets or safety vests. No signboards, no print on the bags. Low micro-contrast, no added sharpening, no HDR, no bloom, no glossy skin. Render only explicitly requested image text. Do not add unrelated logos, signatures or captions.
```

**exact_text**: none (`[]`).

**checklist, must lines**

| check | pass_when |
|---|---|
| Wall bond, every house | All bricks laid flat in solid walls; no bricks on edge, no cavities anywhere |
| Mason's action state | One brick held flat a hand's width above the mortar bed, not yet laid; trowel in right hand |
| Helper | In profile on the street right of the wall, four bricks against his chest |
| People's description | Mason: forties, grey temples, thin moustache, beige shirt, charcoal trousers. Helper: fifties, grey hair, white rolled-sleeve shirt, grey trousers; no helmets or vests |
| Room for the move | Open street along the right side; the stacks are not at an edge that a drift right would lose first |
| Light and palette | Hard sun from one side, soft shade under neem; muted natural colour, matches the film's look |
| Text | No captions, signs, logos or print on the bags |

## 2. Still picture, BEAT_03-B2_sh2

Files opened: always/ (all four), still-scene/video-frame.md, still-scene/FACT-SHEET.md, still-scene/de-slop.md, still-scene/gap-fill.md.

**prompt**

```
Scene: a frame from steady documentary footage of a tree-lined residential street in peri-urban Tamil Nadu, South India, late morning. Seen from the far side of the street at eye level, about 1.6 m up, a 35 mm feel, verticals straight, deep focus across the whole building.

Layout: the building's front fills the frame between two neem trees, one at each side edge, each framing about one window-width of foliage. A strip of pale sky about half a storey high sits above the roof terrace parapet. The low brick compound wall and gate run across the lower part, with a band of sandy street below them in the foreground. Keep about one window-width of margin around the building on every side for a slow push-in toward the middle floor's brickwork.

Subject: a finished, lived-in building of exactly three floors above ground, unplastered, its whole front in exposed rat-trap bond: red-orange burnt clay bricks laid on edge, two faces of bricks with headers across, thin grey cement mortar joints struck flush. Windows on all three floors; balconies on the second and third floors with potted plants and washing on the railings. Above the third floor, a flat roof terrace with a low brick parapet, a black water tank and clothes drying on a line, reading clearly as a terrace, not a fourth floor.

Foreground: a low brick compound wall with a plain iron gate, a two-wheeler parked just inside, a bicycle leaning by the gate, a worn path from the gate to the door.

Details: warm late-morning sun from the upper left, hard, raking across the brick face so each brick and joint casts a small shadow; soft shade under the neem trees. Country-burnt bricks with chipped edges and mixed red-orange tones; dark weather stains below the window sills; dust along the parapet. Palette: red-orange brick, grey mortar, green neem, pale sky, sand; muted, natural, standard contrast.

MEDIUM: a frame from tripod documentary video, fine sensor noise, mild compression, low micro-contrast, no added sharpening.
BUILDING: three floors only; no plaster, no paint, no open cavities showing on the face.
Constraints: no signboards, house names or lettering; no HDR, bloom, glossy surfaces or saturated sky. Render only explicitly requested image text. Do not add unrelated logos, signatures or captions.
```

**exact_text**: none (`[]`).

**checklist, must lines**

| check | pass_when |
|---|---|
| Floor count | Exactly three floors above ground; terrace with parapet and tank does not read as a fourth |
| Bond | Exposed face in rat-trap bond, bricks on edge with headers, grey joints; no plaster or paint |
| Whole building in frame | Roof terrace to front gate visible, neem trees at both edges, sky above |
| Room for the push-in | Margin of about a window-width around the building |
| Light and palette | Hard sun from upper left on the brick face, muted natural colour matching the footage |
| Text | No signboard, house name, lettering, logo or caption anywhere |
| Real-photograph look | Fine noise, no glossy sheen, no HDR or bloom |

## 3. Motion brief, take of BEAT_01-B1-S1

Files opened: always/ (all four), take/video-clip.md, take/FACT-SHEET.md, take/camera-lighting-vocabulary.md, take/gap-fill.md (still-to-motion-pipeline.md read but not used: this is not a styled still).

```
The mason lowers the brick flat onto the mortar bed at the end of the top course and taps it level twice with the trowel handle, a little grey mortar squeezing from the joint. He then scoops mortar from the iron pan at his right and spreads a fresh strip along the course beyond the new brick. The helper walks left along the sandy street to the wall's right end and sets his four bricks down flat on the wall top to the mason's left, his hands then empty. At the far houses the workers keep at their tasks; a little dust lifts near the brick stack. Every brick stays laid flat; both men's faces and clothes, the far houses, the cement bags and the street stay as in the start image.
```
