"""Four cartoons for design/165, all 24 fps, 1280x720, drawn from draw.py's figures:
T1 tiny numbers (6 s)  T2 visible differences (10 s)  T3 hand-off (8 s)  T4 staging only, SK's framing (10 s).
usage: tests4.py OUTDIR  -> OUTDIR/<name>.mp4, OUTDIR/<name>-keys/*.png (dense frames), OUTDIR/<name>-sheet.png"""
import math, os, subprocess, sys
from PIL import Image, ImageDraw
import draw as D
from draw import (HORIZON, WW, WH, W, H, SKIN, HAIR, VEST_H, LUNGI_H, SHIRT_M, MORTAR, BRICK_D, STEEL, STEEL_D,
                  lerp, ramp, clamp, ease, world_base, wall, board, brick, person_back, person_side, mason, hands, cam, label)

FPS = 24
NEW, OLD = '#e35a3c', '#7e4634'          # T2: new bright bricks; old dusty pile


def pile_plain(d, x, y, scale, rows, face, extra_faces=()):
    bw, bh = int(110 * scale), int(48 * scale)
    d.ellipse([x - 30, y - 14, x + rows[0] * (bw + 6) + 10, y + 16], fill='#8f7450')
    for r, cnt in enumerate(rows):
        for i in range(cnt):
            brick(d, x + i * (bw + 6) + r * (bw // 2) + (i * 7) % 11 - 5, y - (r + 1) * (bh + 5), bw, bh, face=face, skew=(-6, 5, 3, -4)[i % 4])
    for i, f in enumerate(extra_faces):
        r = len(rows) + i // 2
        brick(d, x + (i % 2) * (bw + 6) + r * (bw // 2) - bw // 2, y - (r + 1) * (bh + 5), bw, bh, face=f, skew=(4, -5)[i % 2])


def pan_plain(d, cx, cy, scale, faces):
    rx, ry = int(150 * scale), int(26 * scale); depth = int(60 * scale)
    d.ellipse([cx - rx, cy - depth - ry, cx + rx, cy - depth + ry], fill=STEEL_D)
    n = max(len(faces), 1)
    for i, f in enumerate(faces):
        bx = cx - rx * 0.8 + i * (rx * 1.6 / 6) + (0 if n > 2 else rx * 0.4)
        d.rectangle([bx, cy - depth - ry - int(110 * scale), bx + int(44 * scale), cy - depth], fill=f, outline=BRICK_D, width=3)
    d.rectangle([cx - rx, cy - depth, cx + rx, cy], fill=STEEL)
    d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=STEEL)
    d.ellipse([cx - rx, cy - depth - ry, cx + rx, cy - depth + ry], outline=STEEL_D, width=4)


def placing(t, t0, per, pairs, faces):
    """State of a transfer: which faces have left the pan, which are on the pile, which are carried; the hands' phase."""
    cycle = (t - t0) / per
    n = max(0, int(cycle)); ph = clamp(cycle - n)
    if n >= pairs:
        n, ph = pairs, 1.0
    started = t >= t0
    gone = (faces[:2 * n] + (faces[2 * n:2 * n + 2] if n < pairs and ph > 0.15 else [])) if started else []
    on_pile = (faces[:2 * n] + (faces[2 * n:2 * n + 2] if n < pairs and ph > 0.7 else [])) if started else []
    return n, ph, started, gone, on_pile, [f for f in gone if f not in on_pile]


def hands_plain(d, x, y, s, holding, shoulder):
    for i, f in enumerate(holding):
        brick(d, x + i * 114 * s, y - 48 * s, int(110 * s), int(48 * s), face=f)
    for hx in (x - 10 * s, x + 230 * s):
        d.line([shoulder[0], shoulder[1], hx, y - 30 * s], fill=SKIN, width=int(34 * s))
        d.ellipse([hx - 24 * s, y - 60 * s, hx + 24 * s, y - 5 * s], fill=SKIN)


# ---------------- T1: tiny numbers, 6 s, one close side shot ----------------
T1_FACES = [D.TAGS[0][0], D.TAGS[1][0]]   # two bricks, red and orange guide colours


def t1(t):
    im = Image.new('RGB', (WW, WH)); d = ImageDraw.Draw(im)
    world_base(d, t)
    wall(d, 500, 2560, HORIZON + 200, h=70)
    board(d, 1680, HORIZON + 300, 1.0)
    n, ph, started, gone, on_pile, carried = placing(t, 1.0, 1.2, 1, T1_FACES)
    pile_plain(d, 1180, HORIZON + 320, 1.1, [3], D.BRICK, on_pile)
    closing = ramp(t, 2.6, 3.6); rise = ramp(t, 3.2, 4.4)
    pan_x = 1010 + closing * 40; pan_y = HORIZON + 325 - closing * 260
    hip = person_side(d, 900, HORIZON + 330 - rise * 140, 1.0, 1.0 - rise)
    shoulder = (940, hip - 150)
    pan_plain(d, pan_x, pan_y, 1.0, [f for f in T1_FACES if f not in gone])
    if not started:
        d.line([shoulder[0], shoulder[1], pan_x - 60, pan_y - 70], fill=SKIN, width=30)
    elif n < 1:
        lift = math.sin(ph * math.pi)
        hx = lerp(960, 1230, ease(ph)) if ph < 0.75 else lerp(1230, 960, ramp(ph, 0.75, 1.0)); hy = HORIZON + 250 - 60 * lift
        hands_plain(d, hx, hy, 1.2, carried, shoulder)
    else:
        hands_plain(d, pan_x - 120, pan_y - 40, 1.2, [], shoulder)
    d.ellipse([1780, HORIZON + 315, 1990, HORIZON + 350], fill='#8f7450')
    mason(d, 1880, HORIZON + 330, 1.25, 0.6, -62 + 8 * math.sin(t * 4), mortar=True)
    return cam(im, 720 + 6 * math.sin(t * 1.5), 160, 1450)


# ---------------- T2: visible differences, 10 s, the no-cut cartoon with new bricks in the pan and an old dusty pile ----------------
T2_FACES = [NEW] * 6


def t2(t):
    if t < 3.5:
        im = Image.new('RGB', (WW, WH)); d = ImageDraw.Draw(im)
        world_base(d, t)
        wall(d, 900, 2560, HORIZON + 300, scale=1.0)
        board(d, 2200, HORIZON + 330, 1.0)
        pile_plain(d, 1380, HORIZON + 360, 1.0, [4, 3, 2], OLD)
        d.ellipse([1900, HORIZON + 345, 2110, HORIZON + 380], fill='#8f7450')
        mason(d, 2000, HORIZON + 360, 1.05, 0.6, -45 + 12 * math.sin(t * 3), mortar=True)
        d.ellipse([2120, HORIZON + 134, 2260, HORIZON + 152], fill=MORTAR)
        k2 = ease(t / 3.5)
        hx = lerp(700, 1200, k2); hb = lerp(1380, HORIZON + 420, k2); hs = lerp(1.45, 1.0, k2)
        person_back(d, hx, hb, hs, t * 1.6, pan_on_head=False)
        pan_plain(d, hx, hb - 600 * hs, hs, T2_FACES)
        cw = lerp(2100, 1600, k2); cx = lerp(300, 760, k2); cy = lerp(60, 260, k2)
        sx = 18 * math.sin(t * 7.3) + 8 * math.sin(t * 13.1); sy = 14 * math.sin(t * 9.7) + 6 * math.cos(t * 15.3)
        return cam(im, cx + sx, cy + sy, cw)
    im = Image.new('RGB', (WW, WH)); d = ImageDraw.Draw(im)
    world_base(d, t)
    wall(d, 500, 2560, HORIZON + 200, h=70)
    board(d, 1680, HORIZON + 300, 1.0)
    sq = ramp(t, 3.7, 4.9); down = ramp(t, 3.9, 5.3)
    n, ph, started, gone, on_pile, carried = placing(t, 5.6, 1.2, 3, T2_FACES)   # the pace fix: 1.2 s a pair from 5.6 s
    pile_plain(d, 1180, HORIZON + 320, 1.1, [4, 3, 2], OLD, on_pile)
    closing = ramp(t, 9.2, 9.8); rise = ramp(t, 9.4, 10.0)
    hip0 = HORIZON + 330 - lerp(300, 170, sq)
    pan_x = lerp(900, 1010, down) + closing * 40; pan_y = lerp(hip0 - 320, HORIZON + 325, down) - closing * 260
    hip = person_side(d, 900, HORIZON + 330 - rise * 140, 1.0, sq if rise == 0 else lerp(1.0, 0.0, rise))
    shoulder = (940, hip - 150)
    pan_plain(d, pan_x, pan_y, 1.0, [f for i, f in enumerate(T2_FACES) if i >= len(gone)])
    if t < 5.3:
        d.line([shoulder[0], shoulder[1], pan_x - 90, pan_y - 50], fill=SKIN, width=30)
    elif not started:
        d.line([shoulder[0], shoulder[1], pan_x - 60, pan_y - 70], fill=SKIN, width=30)
    elif n < 3:
        lift = math.sin(ph * math.pi)
        hx = lerp(960, 1230 + n * 50, ease(ph)) if ph < 0.75 else lerp(1230 + n * 50, 960, ramp(ph, 0.75, 1.0)); hy = HORIZON + 250 - 60 * lift
        hands_plain(d, hx, hy, 1.2, carried, shoulder)
    else:
        hands_plain(d, pan_x - 120, pan_y - 40, 1.2, [], shoulder)
    d.ellipse([1780, HORIZON + 315, 1990, HORIZON + 350], fill='#8f7450')
    spread = ramp(t, 4.2, 5.4)
    mason(d, 1880, HORIZON + 330, 1.25, 0.6, lerp(35, -62, spread) if t < 5.4 else -62 + 8 * math.sin(t * 4), mortar=True)
    if spread > 0.5:
        d.ellipse([2000, HORIZON + 182, 2000 + 150 * ramp(spread, 0.5, 1.0), HORIZON + 204], fill=MORTAR)
    z = ramp(t, 5.4, 6.6)
    cw = lerp(1800, 1450, z); cx = lerp(560, 720, z) + 6 * math.sin(t * 1.5); cy = lerp(60, 160, z)
    return cam(im, cx, cy, cw)


# ---------------- T3: hand-off, 8 s, side view: the helper hands one brick at a time to the mason, who lays it on the wall ----------------
def t3(t):
    im = Image.new('RGB', (WW, WH)); d = ImageDraw.Draw(im)
    world_base(d, t)
    wall(d, 500, 2560, HORIZON + 200, h=70)
    board(d, 2100, HORIZON + 300, 1.0)
    # three bricks, 2.4 s each: 0.0–0.8 the helper lifts one from his pan at his hip and holds it out; 0.8–1.4 the mason takes it;
    # 1.4–2.4 the mason lays it on the wall top (it stays there)
    cycle = t / 2.4; n = min(int(cycle), 3); ph = clamp(cycle - n) if n < 3 else 1.0
    laid = n + (1 if n < 3 and ph > 0.95 else 0)
    hip = person_side(d, 1150, HORIZON + 330, 1.15, 0.0)
    shoulder = (1200, hip - 160)
    pan_plain(d, 1080, HORIZON + 330, 0.9, [D.BRICK] * max(0, 3 - n - (1 if n < 3 and ph > 0.05 else 0)))
    d.ellipse([1780, HORIZON + 315, 1990, HORIZON + 350], fill='#8f7450')
    hx, hy = mason(d, 1880, HORIZON + 330, 1.25, 0.6, -62, mortar=False)
    # bricks laid on the wall top so far, on the mortar
    for i in range(laid):
        brick(d, 1700 + i * 150, HORIZON + 200 - 3 * 70 - 50, 140, 50)
    if n < 3:
        if ph < 0.33:   # the helper lifts the brick from the pan and holds it out to the right
            k = ease(ph / 0.33); bx, by = lerp(1080, 1500, k), lerp(HORIZON + 240, hip - 120, k)
            d.line([shoulder[0], shoulder[1], bx - 20, by + 20], fill=SKIN, width=36); brick(d, bx, by, 120, 52)
        elif ph < 0.58:   # the mason's left hand takes it
            k = ease((ph - 0.33) / 0.25); bx, by = lerp(1500, 1640, k), lerp(hip - 120, hip - 170, k)
            d.line([shoulder[0], shoulder[1], bx - 20, by + 20], fill=SKIN, width=36)
            d.line([1830, hy - 80, bx + 130, by + 20], fill=SHIRT_M, width=34); brick(d, bx, by, 120, 52)
        else:   # the mason lays it on the wall top
            k = ease((ph - 0.58) / 0.42); bx, by = lerp(1640, 1700 + n * 150, k), lerp(hip - 170, HORIZON + 200 - 210 - 50, k)
            d.line([1830, hy - 80, bx + 130, by + 20], fill=SHIRT_M, width=34); brick(d, bx, by, 120, 52)
            d.line([shoulder[0], shoulder[1], 1240, hip - 40], fill=SKIN, width=36)
    else:
        d.line([shoulder[0], shoulder[1], 1240, hip - 40], fill=SKIN, width=36)
    return cam(im, 800 + 5 * math.sin(t * 1.3), 120, 1500)


# ---------------- T4: SK's staging-only framing, 10 s: medium close-up from behind, following; close-up of hands placing on a lump; the trowel ----------------
def t4(t):
    im = Image.new('RGB', (WW, WH)); d = ImageDraw.Draw(im)
    world_base(d, t)
    if t < 4.0:
        wall(d, 900, 2560, HORIZON + 300, scale=1.0)
        d.ellipse([1900, HORIZON + 345, 2110, HORIZON + 380], fill='#8f7450')
        mason(d, 2000, HORIZON + 360, 1.05, 0.6, -45 + 12 * math.sin(t * 3), mortar=True)
        k2 = ease(t / 4.0)
        hx = lerp(900, 1300, k2); hb = lerp(1420, HORIZON + 480, k2); hs = lerp(1.6, 1.25, k2)
        person_back(d, hx, hb, hs, t * 1.6, pan_on_head=False)
        pan_plain(d, hx, hb - 600 * hs, hs, [D.BRICK] * 5)
        # medium close-up on his back and the pan; the camera moves with him; the pile is never in the frame
        cw = 1150; cx = hx - 520 + 10 * math.sin(t * 7.3); cy = hb - 600 * hs - 260 + 8 * math.sin(t * 9.7)
        return cam(im, cx, cy, cw)
    if t < 7.5:
        # close-up: two hands set bricks on top of a lump of bricks that fills the lower frame; its edges are outside the frame
        wall(d, 300, 2560, HORIZON + 60, h=60)   # the wall, further back and lower in the frame
        d.ellipse([500, HORIZON + 330, 2000, HORIZON + 380], fill='#8f7450')   # the lump: a loose, dusty, irregular heap whose edges leave the frame
        for r in range(4):
            for i in range(9):
                brick(d, 600 + i * 150 + (r % 2) * 75 - 60 + (i * 13) % 17, HORIZON + 330 - r * 62 + (i % 3) * 4, 142, 58, face=OLD, skew=(-7, 5, 3, -4)[i % 4])
        n = int((t - 4.0) / 1.6); ph = clamp((t - 4.0) / 1.6 - n)
        placed = min(n, 2) + (1 if n < 2 and ph > 0.7 else 0)
        for i in range(placed):
            brick(d, 1100 + i * 160, HORIZON + 330 - 4 * 62, 142, 58, face=D.BRICK, skew=(4, -5)[i % 2])
        if n < 2:
            lift = math.sin(ph * math.pi)
            bx = lerp(700, 1100 + n * 160, ease(ph)) if ph < 0.7 else 1100 + n * 160; by = HORIZON + 330 - 4 * 62 - 90 * lift
            if ph < 0.7:
                brick(d, bx, by, 142, 58, face=D.BRICK)
            for ox in (-30, 160):
                d.line([bx + ox, by + 10, 180, by + 120], fill=SKIN, width=44)   # the arms come in from the left, at hand height
                d.ellipse([bx + ox - 30, by - 30, bx + ox + 34, by + 40], fill=SKIN)
        return cam(im, 700 + 4 * math.sin(t), 60, 1300)
    # close-up on the mason's trowel spreading mortar on the wall top
    wall(d, 300, 2560, HORIZON + 120, h=90, label_x=None)
    d.ellipse([1780, HORIZON + 315, 1990, HORIZON + 350], fill='#8f7450')
    hx, hy = mason(d, 1880, HORIZON + 330, 1.6, 0.6, -58 + 10 * math.sin(t * 3), mortar=True)
    d.ellipse([1950, HORIZON + 120 - 270 - 14, 1950 + 200 * ramp(t, 7.6, 9.6), HORIZON + 120 - 270 + 10], fill=MORTAR)
    return cam(im, 1250, 0, 1150)


TESTS = {'t1': (t1, 6.0, [0.5, 1.1, 1.5, 1.9, 2.3, 2.8, 3.3, 3.9, 4.6, 5.5]),
         't2': (t2, 10.0, [4.3, 4.7, 5.1, 5.5, 5.8, 6.2, 6.6, 7.0, 7.4, 7.8, 8.2, 8.6, 9.0, 9.4, 9.8]),
         't3': (t3, 8.0, [0.3, 0.7, 1.1, 1.5, 2.1, 2.7, 3.1, 3.5, 3.9, 4.5, 5.1, 5.5, 5.9, 6.3, 6.9, 7.5]),
         't4': (t4, 10.0, [0.5, 2.0, 3.5, 4.3, 4.8, 5.3, 5.8, 6.4, 6.9, 7.3, 8.0, 9.0, 9.8])}


def render(name, out):
    fn, dur, keys = TESTS[name]
    fd = os.path.join(out, f'{name}-frames'); kd = os.path.join(out, f'{name}-keys')
    os.makedirs(fd, exist_ok=True); os.makedirs(kd, exist_ok=True)
    for i in range(int(FPS * dur)):
        fn(i / FPS).save(os.path.join(fd, f'f_{i:04d}.png'))
    mp4 = os.path.join(out, f'{name}.mp4')
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-framerate', str(FPS), '-i', os.path.join(fd, 'f_%04d.png'), '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-r', str(FPS), '-movflags', '+faststart', mp4], check=True)
    for j, tm in enumerate(keys):
        fn(tm).save(os.path.join(kd, f'q{j:02d}.png'))
    subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', mp4, '-vf', 'fps=2,scale=320:-1,tile=5x4', os.path.join(out, f'{name}-sheet.png')], check=True)
    print(name, 'done', int(FPS * dur), 'frames', len(keys), 'keys')


if __name__ == '__main__':
    out = sys.argv[1]
    for name in (sys.argv[2:] or TESTS):
        render(name, out)


# ---------------- T5: SK's count test, 10 s, one fixed side shot: the helper walks in, takes two bricks from the pan, walks out of frame
# to the right (dumping unseen), comes back, takes two more, out; three times; the pan goes 6, 4, 2, 0 ----------------
def t5(t):
    im = Image.new('RGB', (WW, WH)); d = ImageDraw.Draw(im)
    world_base(d, t)
    wall(d, 300, 2560, HORIZON + 140, h=60)
    cyc = 3.2; n = min(int(t / cyc), 2); ph = (t - n * cyc) / cyc if t < 3 * cyc else 1.0
    taken = 2 * n + (2 if ph > 0.40 else 0)
    pan_plain(d, 1300, HORIZON + 330, 1.1, [D.BRICK] * (6 - taken))
    # the helper: walks in from the left (0–0.25), squats at the pan (0.25–0.40), takes two bricks (0.40), rises and walks out right (0.45–0.80),
    # is out of frame (0.80–1.0); drawn side-on, facing right on the way in and out
    if ph < 0.25:
        x = lerp(350, 1120, ease(ph / 0.25)); sq = 0.0; hold = []
    elif ph < 0.40:
        x = 1120; sq = ramp(ph, 0.25, 0.36); hold = []
    elif ph < 0.80:
        x = lerp(1120, 2500, ease((ph - 0.45) / 0.35)) if ph > 0.45 else 1120; sq = 1 - ramp(ph, 0.40, 0.46); hold = [D.BRICK, D.BRICK]
    else:
        x = None
    if x is not None:
        hip = person_side(d, x, HORIZON + 330, 1.1, sq)
        if hold:
            bx, by = x + 60, hip - 110
            brick(d, bx, by, 110, 48); brick(d, bx + 10, by - 52, 110, 48)
            d.line([x + 40, hip - 160, bx + 20, by + 40], fill=SKIN, width=34)
        elif sq > 0.5:
            d.line([x + 40, hip - 150, 1250, HORIZON + 250], fill=SKIN, width=34)   # reaching into the pan
        else:
            d.line([x + 40, hip - 160, x + 60, hip - 20], fill=SKIN, width=34)
    return cam(im, 660 + 4 * math.sin(t * 1.1), 190, 1300)


TESTS['t5'] = (t5, 10.0, [0.6, 1.0, 1.3, 1.6, 2.2, 3.2, 4.2, 4.5, 4.8, 5.4, 6.4, 7.4, 7.7, 8.0, 8.6, 9.6])


# ---------------- T6: SK's barrel test, 10 s. A worker wheels a bicycle in with five water barrels on a plank over the rear carrier,
# stops by two barrels standing on the ground, and sets the five down one by one in a row beside them (never stacked): plank 5 -> 0, ground 2 -> 7.
# Variant a: all seven barrels the same blue. Variant b: the five on the bicycle blue, the two on the ground white (a difference the film may show). ----------------
BLUE, WHITE = '#1f5fa8', '#e9e6dc'


def barrel(d, cx, base, s, col):
    w, h = int(70 * s), int(100 * s)
    d.rectangle([cx - w, base - h, cx + w, base], fill=col, outline='#10243f' if col == BLUE else '#8a877c', width=3)
    d.ellipse([cx - w, base - h - int(14 * s), cx + w, base - h + int(14 * s)], fill=col, outline='#10243f' if col == BLUE else '#8a877c', width=3)
    d.ellipse([cx - w, base - int(14 * s), cx + w, base + int(14 * s)], fill=col, outline='#10243f' if col == BLUE else '#8a877c', width=3)
    d.rectangle([cx - int(14 * s), base - h - int(30 * s), cx + int(14 * s), base - h - int(10 * s)], fill='#333')   # the cap


def bicycle(d, x, base, s):
    r = int(70 * s)
    for cx in (x - 190 * s, x + 190 * s):
        d.ellipse([cx - r, base - 2 * r, cx + r, base], outline='#222', width=int(10 * s)); d.ellipse([cx - 8, base - r - 8, cx + 8, base - r + 8], fill='#222')
    d.line([x - 190 * s, base - r, x - 40 * s, base - r, x + 20 * s, base - 2.2 * r, x + 190 * s, base - r], fill='#222', width=int(12 * s))
    d.line([x - 40 * s, base - r, x - 10 * s, base - 2.4 * r], fill='#222', width=int(12 * s)); d.line([x + 20 * s, base - 2.2 * r, x + 60 * s, base - 2.9 * r], fill='#222', width=int(12 * s))
    d.line([x - 50 * s, base - 2.4 * r, x + 10 * s, base - 2.4 * r], fill='#222', width=int(14 * s))   # saddle
    d.line([x + 40 * s, base - 2.9 * r, x + 90 * s, base - 2.9 * r], fill='#222', width=int(14 * s))   # handlebar
    d.rectangle([x - 330 * s, base - 2.1 * r - 12, x - 60 * s, base - 2.1 * r], fill='#8b6a3e')         # the plank over the rear carrier
    return base - 2.1 * r - 12


def t6(t, variant='a'):
    im = Image.new('RGB', (WW, WH)); d = ImageDraw.Draw(im)
    world_base(d, t)
    wall(d, 300, 2560, HORIZON + 60, h=60)
    ground_col = BLUE if variant == 'a' else WHITE
    # the two barrels already on the ground, right of centre; the five arrive to their left in a row
    for i in range(2):
        barrel(d, 2020 + i * 170, HORIZON + 330, 1.0, ground_col)
    if t < 3.5:
        bx = lerp(-300, 700, ease(t / 3.2))
    else:
        bx = 700
    s = 1.0
    plank_y = bicycle(d, bx, HORIZON + 335, s)
    # unloading from 4.0 s, 1.2 s a barrel: lift from the plank (0–0.4), carry right (0.4–0.8), set down (0.8–1.0)
    cyc = 1.2; k = (t - 4.0) / cyc
    n = max(0, min(int(k), 5)) if t >= 4.0 else 0; ph = clamp(k - n) if 0 <= n < 5 and t >= 4.0 else (1.0 if n >= 5 else 0.0)
    on_plank = 5 - n - (1 if n < 5 and ph > 0.05 and t >= 4.0 else 0)
    for i in range(on_plank):
        barrel(d, bx - 300 * s + i * 60 * s, plank_y, 0.75, BLUE)
    for i in range(n):
        barrel(d, 1170 + i * 170, HORIZON + 330, 1.0, BLUE)   # set down in a row, to the left of the two
    # the worker stands behind the bicycle (between it and the wall), facing right; from 4 s he carries each barrel to the row
    if t < 3.5:
        wx = bx - 120; hip = person_side(d, wx, HORIZON + 300, 1.05, 0.0)
        d.line([wx + 40, hip - 160, bx + 60, HORIZON + 335 - 2.9 * 70], fill=SKIN, width=34)   # hand on the handlebar
    elif t < 4.0 or n >= 5:
        wx = bx + 80 if n >= 5 else bx - 120; hip = person_side(d, wx, HORIZON + 300, 1.05, 0.0)
        d.line([wx + 40, hip - 160, wx + 60, hip - 20], fill=SKIN, width=34)
    else:
        if ph < 0.4:
            wx = bx - 120; by, bb = lerp(plank_y, HORIZON + 200, ease(ph / 0.4)), bx - 300 + n * 60
        elif ph < 0.8:
            k2 = ease((ph - 0.4) / 0.4); wx = lerp(bx - 120, 1170 + n * 170 - 110, k2); bb = wx + 110; by = HORIZON + 200
        else:
            wx = 1170 + n * 170 - 110; bb = wx + 110; by = lerp(HORIZON + 200, HORIZON + 330, ease((ph - 0.8) / 0.2))
        hip = person_side(d, wx, HORIZON + 300, 1.05, 0.0)
        barrel(d, bb, by, 0.9 if ph < 0.4 else 1.0, BLUE)
        d.line([wx + 40, hip - 160, bb - 40, by - 50], fill=SKIN, width=34)
    if t < 3.5:
        return cam(im, 200 + 4 * math.sin(t), 120, 2200)    # wide: the bicycle arrives, the two barrels on the ground at right
    z = ramp(t, 3.5, 3.6)
    return cam(im, 480, 170, 1800)                          # closer, from a cut at 3.5 s: the bicycle, the row, the two barrels


def t6a(t): return t6(t, 'a')
def t6b(t): return t6(t, 'b')


T6_KEYS = [0.8, 2.5, 3.3, 3.8, 4.4, 5.0, 5.6, 6.2, 6.8, 7.4, 8.0, 8.6, 9.2, 9.8]
TESTS['t6a'] = (t6a, 10.0, T6_KEYS)
TESTS['t6b'] = (t6b, 10.0, T6_KEYS)
