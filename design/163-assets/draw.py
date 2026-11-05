"""The mason cartoon, 10 s at 15 fps, 1280x720, drawn with Pillow from a fixed world so the left-to-right order (helper, pile, mason, wall)
never flips between angles. usage: draw.py frames|keys [OUTDIR]"""
import math, os, random, sys
from PIL import Image, ImageDraw, ImageFont
FONT = lambda px: ImageFont.truetype('arialbd.ttf', px)


def label(d, x, y, text, px=44):
    """A word on the cartoon that names a thing: black on white, never meant for the film."""
    w = d.textlength(text, font=FONT(px))
    d.rectangle([x - 8, y - 4, x + w + 8, y + px + 4], fill='white', outline='black', width=3)
    d.text((x, y), text, font=FONT(px), fill='black')

FPS, DUR = 15, 10.0
W, H = 1280, 720
# colours
SKY, GROUND, GROUND2 = '#cfe6f5', '#b89a72', '#a8895f'
BRICK, BRICK_D, MORTAR, BOARD = '#b4472f', '#8e3522', '#5f6b5c', '#7a5230'
STEEL, STEEL_D = '#d7dadf', '#8f949a'
TAGS = [('#d93c2a', 10), ('#f28c28', 11), ('#2d6bd1', 12), ('#2e9e4f', 13), ('#8e44ad', 14), ('#17a2b8', 15)]   # the pan's bricks: a colour and a number each; the pile's are 1–9   # one colour per brick in the pan: red, orange, blue, green, purple, cyan; a guide, never the film's colour
SKIN, HAIR = '#6e4630', '#1c1410'
SHIRT_M, LUNGI_M, TOWEL = '#7fb3d9', '#3a5fa8', '#f1efe6'
VEST_H, LUNGI_H, PAD = '#f4f2ec', '#2f6b3a', '#8a8a86'
YELLOW = '#f2c21c'
random.seed(7)


def clamp(v, a=0.0, b=1.0): return max(a, min(b, v))
def ease(v): v = clamp(v); return v * v * (3 - 2 * v)
def lerp(a, b, k): return a + (b - a) * k
def ramp(t, t0, t1): return ease((t - t0) / (t1 - t0))


# ---------------- the world (one fixed drawing space 2560 x 1440; the camera crops it) ----------------
WW, WH = 2560, 1440
HORIZON = 600


def wall(d, x0, x1, base, courses=3, h=52, scale=1.0, label_x=None):
    """A plinth wall of red brick courses, seen from the front, finished to three courses; the word WALL on it once."""
    bw = int(120 * scale); h = int(h * scale)
    for c in range(courses):
        y1 = base - c * h; y0 = y1 - h
        d.rectangle([x0, y0, x1, y1], fill=MORTAR)
        off = (bw // 2) if c % 2 else 0
        x = x0 - off
        while x < x1:
            d.rectangle([max(x, x0) + 3, y0 + 3, min(x + bw, x1) - 3, y1 - 3], fill=BRICK)
            x += bw
    if label_x is not None:
        label(d, label_x, base - courses * h + 10, 'WALL', int(44 * scale))
    return base - courses * h


def brick(d, x, y, w=120, h=52, face=BRICK, angle=0, num=None, skew=0):
    d.polygon([(x + skew, y), (x + w + skew, y), (x + w, y + h), (x, y + h)], fill=face, outline=BRICK_D)
    if num is not None:
        px = int(h * 0.72)
        tw = d.textlength(str(num), font=FONT(px))
        d.text((x + w / 2 - tw / 2, y + h / 2 - px * 0.6), str(num), font=FONT(px), fill='white', stroke_width=2, stroke_fill='black')


def pile(d, x, y, scale=1.0, extra=()):
    """A stack of bricks on the ground; its left-bottom corner is (x, y). extra = bricks added by the helper (0..6)."""
    bw, bh = int(110 * scale), int(48 * scale)
    rows = [4, 3, 2]
    d.ellipse([x - 30, y - 14, x + 4 * (bw + 4) + 2 * (bw // 2) + 10, y + 16], fill='#8f7450')   # it lies loose on the ground: a shadow
    n = 0
    for r, cnt in enumerate(rows):
        for i in range(cnt):
            n += 1
            brick(d, x + i * (bw + 6) + r * (bw // 2) + (i * 7) % 11 - 5, y - (r + 1) * (bh + 5), bw, bh, face='#d2765a', num=n, skew=(-6, 5, 3, -4)[i % 4])
    # the new bricks go on top, left to right, keeping their guide colours and numbers
    for i, (col, num) in enumerate(extra):
        r = 3 + i // 2
        brick(d, x + (i % 2) * (bw + 6) + r * (bw // 2) - bw // 2, y - (r + 1) * (bh + 5), bw, bh, face=col, num=num, skew=(4, -5)[i % 2])
    label(d, x + bw, y - 5 * (bh + 5) - int(58 * scale), 'PILE', int(44 * scale))


def pan(d, cx, cy, scale=1.0, bricks=TAGS):
    """A shallow round steel pan seen from the side, with bricks standing in it; (cx, cy) is the bottom centre."""
    rx, ry = int(150 * scale), int(26 * scale); depth = int(60 * scale)
    d.ellipse([cx - rx, cy - depth - ry, cx + rx, cy - depth + ry], fill=STEEL_D)
    for i, (col, num) in enumerate(bricks):
        bx = cx - rx * 0.8 + i * (rx * 1.6 / 6)
        d.rectangle([bx, cy - depth - ry - int(110 * scale), bx + int(44 * scale), cy - depth], fill=col, outline=BRICK_D, width=3)
        px = int(30 * scale); tw = d.textlength(str(num), font=FONT(px))
        d.text((bx + int(22 * scale) - tw / 2, cy - depth - ry - int(80 * scale)), str(num), font=FONT(px), fill='white', stroke_width=2, stroke_fill='black')
    d.rectangle([cx - rx, cy - depth, cx + rx, cy], fill=STEEL)
    d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=STEEL)
    d.ellipse([cx - rx, cy - depth - ry, cx + rx, cy - depth + ry], outline=STEEL_D, width=4)
    label(d, cx - int(40 * scale), cy - depth + int(8 * scale), 'PAN', int(34 * scale))


def board(d, x, y, scale=1.0):
    bw = int(220 * scale)
    d.polygon([(x, y), (x + bw, y), (x + bw - 20, y + int(40 * scale)), (x + 20, y + int(40 * scale))], fill=BOARD)
    d.ellipse([x + 40, y - int(60 * scale), x + bw - 40, y + int(16 * scale)], fill=MORTAR)


def trowel(d, hx, hy, angle, scale=1.0, mortar=False):
    """Yellow-handled trowel; (hx, hy) is the hand; angle in degrees, 0 = blade to the right."""
    a = math.radians(angle)
    L = int(90 * scale)
    ex, ey = hx + math.cos(a) * L, hy - math.sin(a) * L   # handle end
    bx, by = ex + math.cos(a) * int(130 * scale), ey - math.sin(a) * int(130 * scale)
    d.line([hx, hy, ex, ey], fill=YELLOW, width=int(26 * scale))
    px, py = -math.sin(a), -math.cos(a)
    w = int(44 * scale)
    d.polygon([(ex + px * w, ey + py * w), (ex - px * w, ey - py * w), (bx, by)], fill=STEEL)
    if mortar:
        d.ellipse([ex - 30 * scale, ey - 30 * scale, ex + 50 * scale, ey + 10 * scale], fill=MORTAR)


def person_back(d, cx, base, scale, step, pan_on_head=True):
    """The helper from behind, walking: legs alternate with step (0..1 cycle)."""
    s = scale
    legsw = math.sin(step * 2 * math.pi) * 22 * s
    d.line([cx - 22 * s, base - 150 * s, cx - 22 * s + legsw, base], fill=SKIN, width=int(28 * s))
    d.line([cx + 22 * s, base - 150 * s, cx + 22 * s - legsw, base], fill=SKIN, width=int(28 * s))
    d.rectangle([cx - 60 * s, base - 300 * s, cx + 60 * s, base - 140 * s], fill=LUNGI_H)   # lungi to the knee
    d.rounded_rectangle([cx - 62 * s, base - 470 * s, cx + 62 * s, base - 290 * s], radius=int(30 * s), fill=VEST_H)
    d.rectangle([cx - 70 * s, base - 450 * s, cx - 40 * s, base - 320 * s], fill=SKIN)   # bare arms up to the pan
    d.rectangle([cx + 40 * s, base - 450 * s, cx + 70 * s, base - 320 * s], fill=SKIN)
    d.line([cx - 55 * s, base - 440 * s, cx - 120 * s, base - 600 * s], fill=SKIN, width=int(30 * s))
    d.line([cx + 55 * s, base - 440 * s, cx + 120 * s, base - 600 * s], fill=SKIN, width=int(30 * s))
    d.rectangle([cx - 20 * s, base - 500 * s, cx + 20 * s, base - 460 * s], fill=SKIN)   # neck
    d.ellipse([cx - 48 * s, base - 590 * s, cx + 48 * s, base - 490 * s], fill=HAIR)   # back of the head
    d.ellipse([cx - 60 * s, base - 610 * s, cx + 60 * s, base - 575 * s], fill=PAD)      # the pad
    if pan_on_head:
        pan(d, cx, base - 600 * s, s * 1.0)


def person_side(d, cx, base, scale, squat, facing=1):
    """The helper seen from the side (facing right when facing=1), standing or squatting (0..1)."""
    s = scale; f = facing
    hip = base - lerp(300, 170, squat) * s
    d.line([cx, hip, cx + f * lerp(5, 70, squat) * s, base - lerp(150, 90, squat) * s], fill=SKIN, width=int(34 * s))
    d.line([cx + f * lerp(5, 70, squat) * s, base - lerp(150, 90, squat) * s, cx + f * lerp(8, 10, squat) * s, base], fill=SKIN, width=int(30 * s))
    d.rectangle([cx - 45 * s, hip - 10 * s, cx + 45 * s, hip + lerp(150, 90, squat) * s], fill=LUNGI_H)
    d.rounded_rectangle([cx - 48 * s, hip - 180 * s, cx + 48 * s, hip], radius=int(28 * s), fill=VEST_H)
    d.ellipse([cx - 44 * s, hip - 290 * s, cx + 44 * s, hip - 190 * s], fill=SKIN)
    d.pieslice([cx - 46 * s, hip - 296 * s, cx + 46 * s, hip - 200 * s], 180, 360, fill=HAIR)
    d.polygon([(cx + f * 40 * s, hip - 250 * s), (cx + f * 58 * s, hip - 238 * s), (cx + f * 40 * s, hip - 228 * s)], fill=SKIN)   # nose, pointing the way he faces
    d.ellipse([cx + f * 22 * s, hip - 258 * s, cx + f * 32 * s, hip - 248 * s], fill=HAIR)   # eye
    d.ellipse([cx - 50 * s, hip - 310 * s, cx + 50 * s, hip - 280 * s], fill=PAD)
    return hip


def mason(d, cx, base, scale, bend, trowel_angle, mortar=False):
    """The mason facing the wall, seen from behind-left: bending over the wall top with the trowel in his right hand."""
    s = scale
    d.line([cx - 24 * s, base - 170 * s, cx - 28 * s, base], fill=SKIN, width=int(30 * s))
    d.line([cx + 24 * s, base - 170 * s, cx + 30 * s, base], fill=SKIN, width=int(30 * s))
    # checked lungi
    d.rectangle([cx - 62 * s, base - 320 * s, cx + 62 * s, base - 160 * s], fill=LUNGI_M)
    for y in range(int(base - 320 * s), int(base - 160 * s), int(26 * s)):
        d.line([cx - 62 * s, y, cx + 62 * s, y], fill='#dfe6f0', width=3)
    for x in range(int(cx - 62 * s), int(cx + 62 * s), int(26 * s)):
        d.line([x, base - 320 * s, x, base - 160 * s], fill='#dfe6f0', width=3)
    # torso bends forward (shorter with bend)
    top = base - lerp(500, 440, bend) * s
    d.rounded_rectangle([cx - 66 * s, top, cx + 66 * s, base - 300 * s], radius=int(30 * s), fill=SHIRT_M)
    d.polygon([(cx - 40 * s, top), (cx - 10 * s, top), (cx + 30 * s, base - 300 * s), (cx - 5 * s, base - 300 * s)], fill=TOWEL)   # towel over the left shoulder
    # seen from behind: the back of the head is all hair, two ears, no face; his feet point at the wall
    d.ellipse([cx - 40 * s, top - 95 * s, cx + 40 * s, top + 5 * s], fill=HAIR)
    d.ellipse([cx - 48 * s, top - 60 * s, cx - 32 * s, top - 36 * s], fill=SKIN); d.ellipse([cx + 32 * s, top - 60 * s, cx + 48 * s, top - 36 * s], fill=SKIN)
    d.rectangle([cx - 14 * s, top - 4 * s, cx + 14 * s, top + 10 * s], fill=SKIN)   # neck
    d.ellipse([cx - 44 * s, base - 14 * s, cx - 10 * s, base + 6 * s], fill=SKIN); d.ellipse([cx + 12 * s, base - 14 * s, cx + 46 * s, base + 6 * s], fill=SKIN)   # feet, toes towards the wall
    # right arm (screen-right) reaches to the wall with the trowel; the trowel's tip is at the point of contact given by the caller
    hx, hy = cx + lerp(90, 150, bend) * s, top + lerp(60, 40, bend) * s
    d.line([cx + 50 * s, top + 30 * s, hx, hy], fill=SHIRT_M, width=int(30 * s))
    d.ellipse([hx - 18 * s, hy - 18 * s, hx + 18 * s, hy + 18 * s], fill=SKIN)
    trowel(d, hx, hy, trowel_angle, s, mortar)
    return hx, hy
    # left arm rests on the wall
    d.line([cx - 50 * s, top + 30 * s, cx - 110 * s, top + 120 * s], fill=SHIRT_M, width=int(30 * s))


def hands(d, x, y, scale, holding, lift, rise=0.0, body=True, shoulder=None):
    """Two hands from the side holding two bricks (their guide colours in `holding`), for the close shot; rise lifts the helper's body."""
    s = scale
    y = y - lift * 90 * s
    for i, (col, num) in enumerate(holding):
        brick(d, x + i * 114 * s, y - 48 * s, int(110 * s), int(48 * s), face=col, num=num)
    bx = 840; up = rise * 220   # the squatting helper's body stays at the left edge of the world crop; rise = standing up at the end
    if not body:
        for hx in (x - 10 * s, x + 230 * s):
            d.line([shoulder[0], shoulder[1], hx, y - 30 * s], fill=SKIN, width=int(34 * s))
            d.ellipse([hx - 24 * s, y - 60 * s, hx + 24 * s, y - 5 * s], fill=SKIN)
        return
    d.rounded_rectangle([bx - 90 * s, HORIZON + 60 - up, bx + 90 * s, HORIZON + 250 - up], radius=int(30 * s), fill=VEST_H)
    d.rectangle([bx - 90 * s, HORIZON + 240 - up, bx + 90 * s, HORIZON + 330], fill=LUNGI_H)
    d.ellipse([bx - 48 * s, HORIZON - 50 - up, bx + 48 * s, HORIZON + 70 - up], fill=SKIN)
    d.pieslice([bx - 50 * s, HORIZON - 56 - up, bx + 50 * s, HORIZON + 60 - up], 180, 360, fill=HAIR)
    d.polygon([(bx + 44 * s, HORIZON + 10 - up), (bx + 66 * s, HORIZON + 24 - up), (bx + 44 * s, HORIZON + 36 - up)], fill=SKIN)   # nose towards the pile
    d.ellipse([bx + 22 * s, HORIZON - 2 - up, bx + 34 * s, HORIZON + 10 - up], fill=HAIR)
    for hx in (x - 10 * s, x + 230 * s):
        d.line([bx + 60 * s, HORIZON + 120 - up, hx, y - 30 * s], fill=SKIN, width=int(34 * s))   # both arms from the helper's shoulder to the hands
        d.ellipse([hx - 24 * s, y - 60 * s, hx + 24 * s, y - 5 * s], fill=SKIN)


# ---------------- shots ----------------
def world_base(d, t):
    d.rectangle([0, 0, WW, HORIZON], fill=SKY)
    d.rectangle([0, HORIZON, WW, WH], fill=GROUND)
    d.ellipse([-200, HORIZON - 40, 900, HORIZON + 40], fill='#c8b28b')   # distant heap of sand
    d.rectangle([1600, HORIZON - 160, 2100, HORIZON], fill='#d9d2c4')      # a far building
    for i in range(12):
        d.ellipse([200 * i + 60, HORIZON + 300 + (i * 37) % 90, 200 * i + 160, HORIZON + 330 + (i * 37) % 90], fill=GROUND2)


def shot1(t, k):
    """0–3.5 s: behind the helper, handheld, following. The helper walks away towards the mason; the wall across the back; pile left of the mason."""
    im = Image.new('RGB', (WW, WH)); d = ImageDraw.Draw(im)
    world_base(d, t)
    top = wall(d, 900, 2560, HORIZON + 300, scale=1.0, label_x=2250)
    board(d, 2200, HORIZON + 330, 1.0)
    pile(d, 1380, HORIZON + 360, 1.0)
    d.ellipse([1900, HORIZON + 345, 2110, HORIZON + 380], fill='#8f7450')   # the mason's shadow on the ground, on the camera's side of the wall
    mason(d, 2000, HORIZON + 360, 1.05, 0.6, -45 + 12 * math.sin(t * 3), mortar=True)
    d.ellipse([2120, HORIZON + 134, 2260, HORIZON + 152], fill=MORTAR)   # mortar already on the top course where he works
    # helper walks from near (big) to far (smaller), from screen-left-centre towards the pile
    k2 = ease(k)
    hx = lerp(700, 1200, k2); hb = lerp(1380, HORIZON + 420, k2); hs = lerp(1.45, 1.0, k2)
    person_back(d, hx, hb, hs, t * 1.6)
    # camera follows with a handheld shake
    cw = lerp(2100, 1600, k2); cx = lerp(300, 760, k2); cy = lerp(60, 260, k2)
    sx = 18 * math.sin(t * 7.3) + 8 * math.sin(t * 13.1); sy = 14 * math.sin(t * 9.7) + 6 * math.cos(t * 15.3)
    return cam(im, cx + sx, cy + sy, cw)


def shot2(t, k):
    """3.5–6 s: side-on medium, low, from the front-right. The helper squats and sets the pan down by the pile; the mason spreads mortar."""
    im = Image.new('RGB', (WW, WH)); d = ImageDraw.Draw(im)
    world_base(d, t)
    wall(d, 700, 2560, HORIZON + 260, label_x=760)
    board(d, 2120, HORIZON + 300, 1.0)
    pile(d, 1250, HORIZON + 340, 1.0)
    sq = ramp(t, 3.7, 4.9)
    hip = person_side(d, 980, HORIZON + 340, 1.0, sq)
    # the pan comes down from the head to the ground, between the helper and the pile
    py = lerp(hip - 320, HORIZON + 340, ramp(t, 3.9, 5.3)); px = lerp(980, 1110, ramp(t, 3.9, 5.3))
    pan(d, px, py, 0.9)
    d.line([980 + 40, hip - 150, px - 90, py - 50], fill=SKIN, width=30)   # arm to the pan
    d.ellipse([1850, HORIZON + 325, 2060, HORIZON + 360], fill='#8f7450')
    spread = ramp(t, 4.2, 5.4)
    hx, hy = mason(d, 1950, HORIZON + 340, 1.0, 0.6, lerp(35, -52, spread), mortar=spread < 0.6)   # the blade swings down until its tip rests on the top course
    if spread > 0.5:   # the mortar lands on the top course and stays there
        d.ellipse([2110, HORIZON + 92, 2110 + 150 * ramp(spread, 0.5, 1.0), HORIZON + 114], fill=MORTAR)
    cw = 1700; cx = 640 + 10 * math.sin(t * 2); cy = 180
    return cam(im, cx, cy, cw)


def shot3(t, k):
    """6–10 s: close low shot on the pile; the helper's hands set bricks on the pile, two at a time; the mason's trowel at the right edge."""
    im = Image.new('RGB', (WW, WH)); d = ImageDraw.Draw(im)
    world_base(d, t)
    wall(d, 500, 2560, HORIZON + 200, h=70, label_x=2060)
    board(d, 1680, HORIZON + 300, 1.0)
    # three placements of a pair, 0.9 s each from 6.1 s (lift at the pan, carry, set on the pile, hands back), then the closing action:
    # the hands take the empty pan and the helper rises (8.8–10 s)
    cycle = (t - 6.1) / 0.9
    n = max(0, int(cycle)); ph = clamp(cycle - n)
    if n >= 3:
        n, ph = 3, 1.0
    gone = TAGS[:2 * n] + (TAGS[2 * n:2 * n + 2] if n < 3 and ph > 0.15 else [])          # out of the pan
    on_pile = TAGS[:2 * n] + (TAGS[2 * n:2 * n + 2] if n < 3 and ph > 0.7 else [])        # on the pile
    carried = [c for c in gone if c not in on_pile]
    pile(d, 1180, HORIZON + 320, 1.1, extra=on_pile)
    closing = ramp(t, 8.8, 9.6)
    pan_y = HORIZON + 325 - closing * 260; pan_x = 1010 + closing * 40
    pan(d, pan_x, pan_y, 1.1, bricks=[c for c in TAGS if c not in gone])
    if n < 3:
        lift = math.sin(ph * math.pi)
        hx = lerp(900, 1230 + n * 50, ease(ph)) if ph < 0.75 else lerp(1230 + n * 50, 900, ramp(ph, 0.75, 1.0)); hy = HORIZON + 250 - 60 * lift
        hands(d, hx, hy, 1.3, holding=carried, lift=0)
    else:
        hands(d, pan_x - 120, pan_y - 40, 1.3, holding=[], lift=0, rise=ramp(t, 9.2, 10.0))
    mason(d, 1880, HORIZON + 330, 1.25, 0.6, -62 + 8 * math.sin(t * 4), mortar=True)
    cw = 1500; cx = 700 + 6 * math.sin(t * 1.5); cy = 120
    return cam(im, cx, cy, cw)


def cam(im, x, y, w):
    h = w * 9 / 16
    x = clamp(x, 0, WW - w); y = clamp(y, 0, WH - h)
    return im.crop((int(x), int(y), int(x + w), int(y + h))).resize((W, H), Image.LANCZOS)


def shot23(t, k):
    """3.5–10 s, one continuous shot: the side view while the helper squats and sets the pan down, then a slow push-in to the close view
    on the pile and the pan, which never leaves the frame; the bricks go from the pan to the pile; the empty pan is lifted and he rises."""
    im = Image.new('RGB', (WW, WH)); d = ImageDraw.Draw(im)
    world_base(d, t)
    wall(d, 500, 2560, HORIZON + 200, h=70, label_x=2060)
    board(d, 1680, HORIZON + 300, 1.0)
    # the pan: on his head, then down to the ground beside the pile at (1010, HORIZON+325); after 8.8 s lifted again
    sq = ramp(t, 3.7, 4.9)
    hip = HORIZON + 330 - lerp(300, 170, sq)
    down = ramp(t, 3.9, 5.3)
    cycle = (t - 6.1) / 0.9
    n = max(0, int(cycle)); ph = clamp(cycle - n)
    if n >= 3:
        n, ph = 3, 1.0
    started = t >= 6.1
    gone = (TAGS[:2 * n] + (TAGS[2 * n:2 * n + 2] if n < 3 and ph > 0.15 else [])) if started else []
    on_pile = (TAGS[:2 * n] + (TAGS[2 * n:2 * n + 2] if n < 3 and ph > 0.7 else [])) if started else []
    carried = [c for c in gone if c not in on_pile]
    pile(d, 1180, HORIZON + 320, 1.1, extra=on_pile)
    closing = ramp(t, 8.8, 9.6)
    pan_x = lerp(900, 1010, down) + closing * 40
    pan_y = lerp(hip - 320, HORIZON + 325, down) - closing * 260
    rise = ramp(t, 9.2, 10.0)
    # the helper: side view, squatting; drawn once for the whole shot
    hip2 = person_side(d, 900, HORIZON + 330 - rise * 140, 1.0, sq if rise == 0 else lerp(1.0, 0.0, rise))
    shoulder = (940, hip2 - 150)
    pan(d, pan_x, pan_y, 1.0, bricks=[c for c in TAGS if c not in gone])
    if t < 5.3:
        d.line([shoulder[0], shoulder[1], pan_x - 90, pan_y - 50], fill=SKIN, width=30)   # arms on the pan while it comes down
    elif not started:
        d.line([shoulder[0], shoulder[1], pan_x - 60, pan_y - 70], fill=SKIN, width=30)   # hands rest on the pan's rim before the first lift
    elif n < 3:
        lift = math.sin(ph * math.pi)
        hx = lerp(960, 1230 + n * 50, ease(ph)) if ph < 0.75 else lerp(1230 + n * 50, 960, ramp(ph, 0.75, 1.0)); hy = HORIZON + 250 - 60 * lift
        hands(d, hx, hy, 1.2, holding=carried, lift=0, body=False, shoulder=shoulder)
    else:
        hands(d, pan_x - 120, pan_y - 40, 1.2, holding=[], lift=0, body=False, shoulder=shoulder)
    d.ellipse([1780, HORIZON + 315, 1990, HORIZON + 350], fill='#8f7450')
    spread = ramp(t, 4.2, 5.4)
    mason(d, 1880, HORIZON + 330, 1.25, 0.6, lerp(35, -62, spread) if t < 5.4 else -62 + 8 * math.sin(t * 4), mortar=True)
    if spread > 0.5:
        d.ellipse([2000, HORIZON + 182, 2000 + 150 * ramp(spread, 0.5, 1.0), HORIZON + 204], fill=MORTAR)
    # the camera: the side view, then a slow push-in between 5.4 and 6.6 s to the close view; the pan is inside both frames
    z = ramp(t, 5.4, 6.6)
    cw = lerp(1800, 1450, z); cx = lerp(560, 720, z) + 6 * math.sin(t * 1.5); cy = lerp(60, 160, z)
    return cam(im, cx, cy, cw)


SHOTS = [(0.0, 3.5, shot1), (3.5, 10.0, shot23)]


def frame(t):
    for a, b, f in SHOTS:
        if a <= t < b:
            return f(t, (t - a) / (b - a))
    a, b, f = SHOTS[-1]
    return f(t, 1.0)


if __name__ == '__main__':
    mode = sys.argv[1]; out = sys.argv[2] if len(sys.argv) > 2 else '.'
    os.makedirs(out, exist_ok=True)
    if mode == 'keys':
        for name, tm in [('k1-start', 0.4), ('k1-mid', 2.0), ('k1-end', 3.3), ('k2-squat', 4.6), ('k2-down', 5.8), ('k3-lift', 6.6), ('k3-place', 8.2), ('k3-end', 9.8)]:
            frame(tm).save(os.path.join(out, name + '.png'))
    else:
        for i in range(int(FPS * DUR)):
            frame(i / FPS).save(os.path.join(out, f'f_{i:04d}.png'))
    print('done')
