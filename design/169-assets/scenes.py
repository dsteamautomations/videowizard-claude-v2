"""Four VW-12 scenes drawn to design/161's rules (fixed world, facing, contact, every second filled, a closing margin, no counts), 24 fps.
k1 kiln (5 s, slow pan left)   p1 plinth sweep and wet (8 s, static)   s1 string pulled taut (4 s, static)   j1 pointing a joint (7 s, static)
usage: scenes.py OUTDIR [names]  -> <name>.mp4, <name>-sheet.png, <name>-marks.json"""
import json, math, os, subprocess, sys
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'mason-test'))
import draw as D
from draw import HORIZON, WW, WH, W, H, SKIN, HAIR, lerp, ramp, clamp, ease, cam

FPS = 24
SAND, SAND_D, STONE, STONE_WET, SKY = '#cdb98f', '#b9a379', '#9d9a92', '#6f6c66', '#cfe6f5'
BRICK, BRICK_D, MORTAR, STEEL, WOOD, CLAY, GREEN_BRICK = '#b4472f', '#8e3522', '#8d8d86', '#b9bcc0', '#8b6a3e', '#9a4a2e', '#8d6a4a'
SHIRT_M, TROUSER_M, SHIRT_H, TROUSER_H, SHIRT_K, LUNGI_K = '#d9c9a3', '#3b3b3b', '#f2efe8', '#8a8a8a', '#2f4a7a', '#4a6b3a'


def person(d, x, base, s, facing, shirt, trouser, bend=0.0, squat=0.0, head_down=0.0, sleeves=True, walk=None):
    """A side-on figure facing right (1) or left (-1): legs, trousers, shirt, head with a nose and an eye on the facing side.
    bend tips the torso forward over the hip; squat lowers the hip. Returns (hip point, shoulder point)."""
    f = facing
    hip_y = base - lerp(300, 170, squat) * s
    if walk is not None:   # two legs swinging in opposite phase
        for sign in (1, -1):
            fx = x + f * 10 * s + sign * walk * 60 * s
            d.line([x, hip_y, fx, base], fill=trouser, width=int(32 * s)); d.ellipse([fx - 26 * s, base - 10 * s, fx + 26 * s, base + 8 * s], fill='#3a2a1a')
    else:
        knee = (x + f * lerp(5, 70, squat) * s, base - lerp(150, 90, squat) * s)
        d.line([x, hip_y, knee[0], knee[1]], fill=trouser, width=int(34 * s)); d.line([knee[0], knee[1], x + f * 10 * s, base], fill=trouser, width=int(30 * s))
        d.ellipse([x + f * 10 * s - 26 * s, base - 10 * s, x + f * 10 * s + 26 * s, base + 8 * s], fill='#3a2a1a')
    d.rectangle([x - 45 * s, hip_y - 10 * s, x + 45 * s, hip_y + lerp(150, 90, squat) * s - 60 * s], fill=trouser)
    # torso, tipped forward by `bend` towards the facing side
    tx = x + f * bend * 90 * s; ty = hip_y - 180 * s + bend * 50 * s
    d.line([x, hip_y, tx, ty], fill=shirt, width=int(96 * s))
    shoulder = (tx + f * 10 * s, ty + 10 * s)
    hx = tx + f * head_down * 30 * s; hy = ty - 70 * s + head_down * 40 * s
    d.ellipse([hx - 44 * s, hy - 50 * s, hx + 44 * s, hy + 50 * s], fill=SKIN)
    d.pieslice([hx - 46 * s, hy - 56 * s, hx + 46 * s, hy + 40 * s], 180, 360, fill=HAIR)
    d.polygon([(hx + f * 40 * s, hy - 6 * s), (hx + f * 60 * s, hy + 8 * s), (hx + f * 40 * s, hy + 18 * s)], fill=SKIN)   # nose
    d.ellipse([hx + f * 20 * s - 6 * s, hy - 14 * s, hx + f * 20 * s + 6 * s, hy - 2 * s], fill=HAIR)                      # eye
    return (x, hip_y), shoulder


def arm(d, shoulder, hand, s, shirt, sleeves=True):
    mid = ((shoulder[0] + hand[0]) / 2, (shoulder[1] + hand[1]) / 2 + 20 * s)
    d.line([shoulder[0], shoulder[1], mid[0], mid[1]], fill=shirt if sleeves else SKIN, width=int(30 * s))
    d.line([mid[0], mid[1], hand[0], hand[1]], fill=SKIN, width=int(26 * s))
    d.ellipse([hand[0] - 16 * s, hand[1] - 16 * s, hand[0] + 16 * s, hand[1] + 16 * s], fill=SKIN)


def tree(d, x, base, s):
    d.rectangle([x - 18 * s, base - 260 * s, x + 18 * s, base], fill='#5a4030')
    for cx, cy, r in ((x, base - 300 * s, 110 * s), (x - 90 * s, base - 250 * s, 80 * s), (x + 90 * s, base - 250 * s, 80 * s)):
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill='#4f7a3a')


# ---------------- k1: the kiln worker carries a pan of wet clay along the green-brick stacks, the kiln smoking behind; slow pan left; 5 s ----------------
def k1(t):
    im = Image.new('RGB', (WW, WH)); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, WW, HORIZON], fill=SKY); d.rectangle([0, HORIZON, WW, WH], fill='#b98a60')
    for px in (200, 700, 1500, 2300):   # coconut palms on the horizon
        d.line([px, HORIZON, px + 20, HORIZON - 160], fill='#6b5236', width=10)
        for a in (-150, -110, -70, -30, 10):
            r = math.radians(a); d.line([px + 20, HORIZON - 160, px + 20 + math.cos(r) * 70, HORIZON - 160 + math.sin(r) * 40 + 30], fill='#3f7a30', width=8)
    # the clamp kiln, back right: a long mud-plastered mound with blackened sides and smoke drifting right
    d.polygon([(1700, HORIZON + 60), (1850, HORIZON - 140), (2450, HORIZON - 140), (2560, HORIZON + 60)], fill='#7a5a3a')
    d.rectangle([1700, HORIZON - 20, 2560, HORIZON + 60], fill='#3b3029')
    for i in range(6):
        px = 1950 + i * 90 + (t * 40 + i * 70) % 300 * 0.3; py = HORIZON - 160 - (t * 60 + i * 90) % 400
        r = 40 + ((t * 60 + i * 90) % 400) * 0.15
        d.ellipse([px - r, py - r * 0.6, px + r, py + r * 0.6], fill='#d9d6d0')
    # rows of unfired green bricks in open lattice stacks, mid-ground left
    for row in range(3):
        for i in range(7):
            x0 = 120 + i * 190 + row * 60; y0 = HORIZON + 40 + row * 70
            for c in range(4):
                d.rectangle([x0, y0 - c * 26, x0 + 140, y0 - c * 26 + 20], fill=GREEN_BRICK, outline='#6e5238')
                d.rectangle([x0 + 20, y0 - c * 26 + 4, x0 + 120, y0 - c * 26 + 16], fill='#a07a58')   # the open lattice
    # the clay heap, right foreground, with pan marks
    d.ellipse([1900, HORIZON + 380, 2500, HORIZON + 560], fill=CLAY)
    for i in range(4):
        d.ellipse([2000 + i * 110, HORIZON + 440, 2060 + i * 110, HORIZON + 470], fill='#7a3a22')
    # the worker walks right to left across the lower middle third, the pan of clay on his head, steadied by one hand
    k = ease(t / 5.0)
    wx = lerp(2050, 1150, k); base = HORIZON + 420
    step = (math.sin(t * 7) * 18)
    sc = 0.95
    hip, sh = person(d, wx, base, sc, -1, SHIRT_K, LUNGI_K, walk=math.sin(t * 7))
    head = (wx - 30 * sc, hip[1] - 180 * sc - 70 * sc)
    d.ellipse([head[0] - 70 * sc, head[1] - 150 * sc, head[0] + 70 * sc, head[1] - 90 * sc], fill=CLAY)          # heaped wet clay
    d.rectangle([head[0] - 95 * sc, head[1] - 100 * sc, head[0] + 95 * sc, head[1] - 60 * sc], fill='#3a3a3a')   # the shallow iron pan, side on
    d.ellipse([head[0] - 95 * sc, head[1] - 112 * sc, head[0] + 95 * sc, head[1] - 88 * sc], fill='#555')
    arm(d, sh, (head[0] + 60 * sc, head[1] - 80 * sc), sc, SHIRT_K)                             # one hand steadying the pan
    arm(d, sh, (wx + 10 * sc + step, hip[1] + 20 * sc), sc, SHIRT_K)                            # the other arm swinging
    # camera: wide, slightly high, a slow pan left following him; the kiln stays in frame
    cx = lerp(900, 560, k); return cam(im, cx, 80, 1700)


# ---------------- p1: the helper sweeps the plinth top clean, lays the broom down, lifts the bucket, flicks water; the stone darkens; 8 s ----------------
def plinth(d, wet_to):
    """The plinth top running from bottom centre to upper left, cement-finished; wet (dark) from the near end up to `wet_to` (0..1)."""
    top = [(1500, HORIZON + 520), (1100, HORIZON + 520), (300, HORIZON + 160), (600, HORIZON + 160)]
    d.polygon(top, fill=STONE)
    d.polygon([(1500, HORIZON + 520), (1500, HORIZON + 620), (1100, HORIZON + 620), (1100, HORIZON + 520)], fill='#7d7a73')
    d.polygon([(1100, HORIZON + 520), (1100, HORIZON + 620), (300, HORIZON + 260), (300, HORIZON + 160)], fill='#85827b')
    if wet_to > 0:
        k = wet_to
        d.polygon([(1500, HORIZON + 520), (1100, HORIZON + 520), (lerp(1100, 300, k), lerp(HORIZON + 520, HORIZON + 160, k)), (lerp(1500, 600, k), lerp(HORIZON + 520, HORIZON + 160, k))], fill=STONE_WET)


def p1(t):
    im = Image.new('RGB', (WW, WH)); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, WW, HORIZON], fill=SKY); d.rectangle([0, HORIZON, WW, WH], fill=SAND)
    tree(d, 500, HORIZON + 80, 1.2)
    for i in range(3):   # the wire-cut brick stack, background left
        for c in range(4):
            d.rectangle([250 + i * 120, HORIZON + 40 - c * 36, 360 + i * 120, HORIZON + 70 - c * 36], fill=BRICK, outline=BRICK_D)
    sweep = ramp(t, 0.0, 3.8); laydown = ramp(t, 3.8, 4.6); lift = ramp(t, 4.6, 5.4); flick = ramp(t, 5.6, 7.4)
    plinth(d, wet_to=0.55 * flick)
    # sand and leaves on the far part before sweeping (drawn as flecks that vanish as the sweep passes)
    for i in range(14):
        fx = 600 + i * 60; fy = HORIZON + 480 - i * 24
        if (i / 14) > 0.55 * sweep:
            d.ellipse([fx, fy, fx + 14, fy + 8], fill=SAND_D)
    # the helper on the sand along the plinth's right side, bent over it, facing the plinth (left), stepping along it as he sweeps
    hx = lerp(1700, 1500, sweep); base = HORIZON + 640
    bend = 0.8 if t < 4.6 else lerp(0.8, 0.2, lift)
    hip, sh = person(d, hx, base, 1.25, -1, SHIRT_H, TROUSER_H, bend=bend, head_down=0.7 if t < 4.6 else 0.3)
    # the broom: in his hand sweeping, then laid on the sand
    stroke = math.sin(t * 6) * 60
    if t < 3.8:
        hand = (hx - 260 + stroke, HORIZON + 470 - (hx - 1500) * 0.3)
        arm(d, sh, hand, 1.25, SHIRT_H)
        d.line([hand[0], hand[1], hand[0] - 160, hand[1] + 60], fill=WOOD, width=14)
        for a in range(-40, 41, 10):
            d.line([hand[0] - 160, hand[1] + 60, hand[0] - 260 + a, hand[1] + 120], fill='#7a5a30', width=4)
        if stroke < -20:   # dust and sand going over the far edge
            d.ellipse([hand[0] - 320, hand[1] + 100, hand[0] - 280, hand[1] + 125], fill='#e0d4b0')
    else:
        # the broom on the sand to his right (frame right of him), laid during 3.8–4.6
        bx = hx + 120; by = HORIZON + 620 - 200 * (1 - laydown)
        d.line([bx, by, bx + 180, by + 20], fill=WOOD, width=14)
        for a in range(-40, 41, 10):
            d.line([bx + 180, by + 20, bx + 290 + a, by + 40], fill='#7a5a30', width=4)
    # the bucket: on the plinth top ahead of him, then lifted in his hand, then tilted to flick water
    if t < 4.6:
        bx, by = 1000, HORIZON + 470
        d.polygon([(bx - 60, by - 100), (bx + 60, by - 100), (bx + 50, by), (bx - 50, by)], fill='#6f6f6f'); d.ellipse([bx - 60, by - 112, bx + 60, by - 88], fill='#4a6a8a')
        if t >= 3.8:
            arm(d, sh, (bx + 10, by - 110), 1.25, SHIRT_H)
    else:
        bx = hx - 120; by = lerp(HORIZON + 470, HORIZON + 400, lift)
        arm(d, sh, (bx, by - 110), 1.25, SHIRT_H)
        d.polygon([(bx - 60, by - 100), (bx + 60, by - 100), (bx + 50, by), (bx - 50, by)], fill='#6f6f6f'); d.ellipse([bx - 60, by - 112, bx + 60, by - 88], fill='#4a6a8a')
        if 5.6 <= t < 7.6:   # the free hand dips and flicks water across the swept stone
            ph = ((t - 5.6) * 1.5) % 1.0
            hand = (bx - 40 - ph * 260, by - 120 + math.sin(ph * math.pi) * -80)
            arm(d, sh, hand, 1.25, SHIRT_H)
            for i in range(6):
                d.ellipse([hand[0] - 120 - i * 25, hand[1] + 40 + i * 12, hand[0] - 110 - i * 25, hand[1] + 50 + i * 12], fill='#5b86b0')
        else:
            arm(d, sh, (hx - 60, hip[1] + 40), 1.25, SHIRT_H)
    return cam(im, 150, 60, 1750)   # static, low eye level, looking along the plinth; the helper full figure at frame right of centre


# ---------------- s1: the mason crouches at the near peg and pulls the slack string taut, winding it twice round the peg; 4 s ----------------
def s1(t):
    im = Image.new('RGB', (WW, WH)); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, WW, HORIZON], fill=SKY); d.rectangle([0, HORIZON, WW, WH], fill=SAND)
    tree(d, 500, HORIZON + 60, 1.1)
    # the damp plinth running away from camera to the far peg, upper centre; the broom on the sand
    d.polygon([(1800, HORIZON + 640), (1300, HORIZON + 640), (1150, HORIZON + 120), (1300, HORIZON + 120)], fill=STONE_WET)
    d.polygon([(1300, HORIZON + 640), (1150, HORIZON + 120), (1120, HORIZON + 140), (1250, HORIZON + 700)], fill='#7d7a73')
    d.line([400, HORIZON + 600, 700, HORIZON + 560], fill=WOOD, width=12)
    for a in range(-30, 31, 10): d.line([700, HORIZON + 560, 790 + a, HORIZON + 540], fill='#7a5a30', width=4)
    far_peg = (1210, HORIZON + 110); near_peg = (1700, HORIZON + 560)
    d.rectangle([far_peg[0] - 10, far_peg[1] - 50, far_peg[0] + 10, far_peg[1] + 10], fill=WOOD)
    d.rectangle([near_peg[0] - 24, near_peg[1] - 130, near_peg[0] + 24, near_peg[1] + 20], fill=WOOD)
    taut = ramp(t, 0.3, 1.9); wind = ramp(t, 1.9, 3.2)
    # the mason crouches behind the near peg, three-quarter back, facing along the plinth to the far peg
    mx = 2000; hip, sh = person(d, mx, HORIZON + 660, 1.3, -1, SHIRT_M, TROUSER_M, squat=1.0, head_down=0.3)
    hands = (lerp(near_peg[0] + 120, near_peg[0] + 10, taut), lerp(near_peg[1] - 40, near_peg[1] - 120, taut))
    arm(d, sh, hands, 1.3, SHIRT_M); arm(d, sh, (hands[0] + 30, hands[1] + 20), 1.3, SHIRT_M)
    # the string: slack on the sand (a curve), drawn tight to a straight line just above the plinth's outer top edge, then wound twice on the peg
    sag = (1 - taut) * 160
    mid = ((far_peg[0] + hands[0]) / 2, (far_peg[1] - 45 + hands[1]) / 2 + sag)
    pts = [(lerp(far_peg[0], hands[0], u), (1 - u) ** 2 * (far_peg[1] - 45) + 2 * (1 - u) * u * mid[1] + u * u * hands[1]) for u in [i / 30 for i in range(31)]]
    d.line(pts, fill='#f4f1e8', width=5)
    if wind > 0:
        for w in range(int(wind * 2) + 1):
            d.ellipse([near_peg[0] - 28, near_peg[1] - 125 + w * 16, near_peg[0] + 28, near_peg[1] - 110 + w * 16], outline='#f4f1e8', width=4)
    return cam(im, 650, 470, 1700)   # low, looking along the line from behind the near peg


# ---------------- j1: the mason takes mortar from the pan, presses it into the raked joint, strikes it flush; 7 s ----------------
def j1(t):
    im = Image.new('RGB', (WW, WH)); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, WW, HORIZON], fill=SKY); d.rectangle([0, HORIZON, WW, WH], fill=SAND)
    tree(d, 300, HORIZON + 60, 1.3)
    # the exposed wall face receding across the right two thirds: bricks on edge, lower joints pointed flush, the chest-height course raked
    wall_top = HORIZON - 200
    d.polygon([(900, HORIZON + 500), (2560, HORIZON + 700), (2560, wall_top - 120), (900, wall_top)], fill=MORTAR)
    for c in range(8):
        for i in range(12):
            x0 = 920 + i * 140; y0 = wall_top + 20 + c * 85 + (x0 - 900) * 0.12 + (c % 2) * 35
            d.polygon([(x0, y0), (x0 + 120, y0 + 14), (x0 + 120, y0 + 70), (x0, y0 + 56)], fill=BRICK, outline=BRICK_D)
    # the window opening further along, soft in the right background
    d.rectangle([2150, wall_top + 60, 2400, wall_top + 300], fill='#5a5a5a')
    # the raked joint at chest height, frame centre, waiting: a dark groove; it fills with grey mortar as he works
    fill_amt = ramp(t, 1.6, 3.6); strike = ramp(t, 4.0, 5.8)
    jx0, jy0 = 1500, wall_top + 20 + 4 * 85 + 600 * 0.12 + 70
    d.line([jx0, jy0, jx0 + 240, jy0 + 30], fill='#3a2a22', width=10)
    if fill_amt > 0:
        d.line([jx0, jy0, lerp(jx0, jx0 + 240, fill_amt), lerp(jy0, jy0 + 30, fill_amt)], fill='#a7a7a0' if strike < 1 else MORTAR, width=14 if strike < 0.5 else 10)
    # the brick stack with the iron mortar pan at his left (frame left of him), waist height
    for c in range(4):
        d.rectangle([700, HORIZON + 300 - c * 36, 860, HORIZON + 330 - c * 36], fill=BRICK, outline=BRICK_D)
    pan = (780, HORIZON + 160); d.ellipse([pan[0] - 90, pan[1] - 30, pan[0] + 90, pan[1] + 30], fill='#2b2b2b'); d.ellipse([pan[0] - 70, pan[1] - 40, pan[0] + 70, pan[1] + 10], fill=MORTAR)
    # the mason: three-quarter profile from his right, waist up, facing the wall (right), left hand on the wall top
    mx = 1150; hip, sh = person(d, mx, HORIZON + 700, 1.6, 1, SHIRT_M, TROUSER_M, bend=0.25, head_down=0.4)
    arm(d, sh, (1380, wall_top + 80), 1.6, SHIRT_M)   # left hand resting on the wall top
    # the right hand with the pointing trowel: from the pan to the joint, pressing, then drawing along it
    if t < 1.6:
        k = ease(t / 1.6); hand = (lerp(pan[0] + 40, jx0 + 20, k), lerp(pan[1] - 40, jy0 - 10, k))
    elif t < 3.6:
        hand = (lerp(jx0 + 20, jx0 + 240, fill_amt), lerp(jy0 - 10, jy0 + 20, fill_amt))
    elif t < 4.0:
        hand = (jx0 + 240, jy0 + 20)
    elif t < 5.8:
        hand = (lerp(jx0 + 240, jx0, strike), lerp(jy0 + 20, jy0 - 10, strike))
    else:
        hand = (jx0 - 20, jy0 - 60)   # the trowel lifted off the finished joint: the closing margin
    arm(d, sh, hand, 1.6, SHIRT_M)
    d.line([hand[0], hand[1], hand[0] + 40, hand[1] + 10], fill=WOOD, width=16)                       # the handle
    d.polygon([(hand[0] + 40, hand[1] - 4), (hand[0] + 40, hand[1] + 24), (hand[0] + 120, hand[1] + 14)], fill=STEEL)   # the narrow blade, its edge in the joint
    if t < 1.6:
        d.ellipse([hand[0] + 60, hand[1] - 10, hand[0] + 110, hand[1] + 20], fill=MORTAR)                 # mortar on the blade
    return cam(im, 420, 0, 1700)   # eye level, slightly behind his right shoulder, looking along the wall face; static


SCENES = {'k1': (k1, 5.0), 'p1': (p1, 8.0), 's1': (s1, 4.0), 'j1': (j1, 7.0)}
MARKS = {'k1': [{'at_s': 0.0, 'label': 'he walks beside the stacks with the pan on his head; the camera pans left with him'}, {'at_s': 5.0, 'label': 'end'}],
         'p1': [{'at_s': 0.0, 'label': 'sweeps the plinth top in short strokes, stepping along it'}, {'at_s': 3.8, 'label': 'lays the broom on the sand'}, {'at_s': 4.6, 'label': 'lifts the bucket off the plinth top'}, {'at_s': 5.6, 'label': 'flicks water by hand across the swept stone, which darkens'}, {'at_s': 7.6, 'label': 'stands with the bucket, the stone wet'}, {'at_s': 8.0, 'label': 'end'}],
         's1': [{'at_s': 0.3, 'label': 'pulls the slack string tight'}, {'at_s': 1.9, 'label': 'winds it twice round the near peg'}, {'at_s': 3.2, 'label': 'holds the taut string, sighting to the far peg'}, {'at_s': 4.0, 'label': 'end'}],
         'j1': [{'at_s': 0.0, 'label': 'brings mortar from the pan on the trowel to the raked joint'}, {'at_s': 1.6, 'label': 'presses the mortar into the joint along a hand-length'}, {'at_s': 4.0, 'label': 'draws the trowel back along the joint, striking it flush'}, {'at_s': 5.8, 'label': 'lifts the trowel off the finished joint'}, {'at_s': 7.0, 'label': 'end'}]}


def render(name, out):
    fn, dur = SCENES[name]
    fd = os.path.join(out, f'{name}-frames'); os.makedirs(fd, exist_ok=True)
    for i in range(int(FPS * dur)):
        fn(i / FPS).save(os.path.join(fd, f'f_{i:04d}.png'))
    mp4 = os.path.join(out, f'{name}.mp4')
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-framerate', str(FPS), '-i', os.path.join(fd, 'f_%04d.png'), '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-r', str(FPS), '-movflags', '+faststart', mp4], check=True)
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', mp4, '-vf', 'fps=2,scale=400:-1,tile=4x5', os.path.join(out, f'{name}-sheet.png')], check=True)
    json.dump(MARKS[name], open(os.path.join(out, f'{name}-marks.json'), 'w'), indent=1)
    print(name, 'done', int(FPS * dur), 'frames')


if __name__ == '__main__':
    out = sys.argv[1]
    for n in (sys.argv[2:] or SCENES):
        render(n, out)
