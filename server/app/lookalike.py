"""design/89 H6: pictures that look alike, by a cheap fingerprint (a difference hash of 64 bits).

A photograph is hashed whole. A graphic is hashed on its content only (the box around what differs from its background colour), so two
different diagrams drawn in one approved style are not flagged for sharing a background. Pairs within a few bits are listed with their times."""
import subprocess
import tempfile
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageChops, ImageStat

BITS_PICTURE = 6   # of 64: the same picture, re-encoded, cropped a little or moved 5 %
BITS_GRAPHIC = 3   # graphics are flat; only near-identical content counts


def _content(img):
    bg = img.getpixel((0, 0))
    mask = ImageChops.difference(img, Image.new(img.mode, img.size, bg)).convert('L').point(lambda p: 255 if p > 24 else 0)
    box = mask.getbbox()
    return img.crop(box) if box else img


def dhash(image, graphic=False):
    img = image.convert('RGB')
    if graphic:
        img = _content(img)
    small = img.convert('L').resize((9, 8))
    if ImageStat.Stat(small).stddev[0] < 2:   # too flat to fingerprint: a plain field matches every other plain field
        return None
    px = list(small.getdata())
    value = 0
    for r in range(8):
        for c in range(8):
            value = (value << 1) | (px[r * 9 + c] > px[r * 9 + c + 1])
    return value


def distance(a, b):
    return bin(a ^ b).count('1')


def pairs(items):
    """items: [{'label', 'at_s', 'hashes': [...], 'graphic': bool}] in film order. A pair is listed when any of their sampled frames match;
    a piece's last frame against the very next piece's first frame is skipped (a shared boundary picture within one shot is by design)."""
    out = []
    for i, a in enumerate(items):
        for j in range(i + 1, len(items)):
            b = items[j]
            limit = BITS_GRAPHIC if a.get('graphic') and b.get('graphic') else BITS_PICTURE
            best = None
            for x, ha in enumerate(a['hashes']):
                for y, hb in enumerate(b['hashes']):
                    if ha is None or hb is None:
                        continue
                    if j == i + 1 and len(a['hashes']) > 1 and len(b['hashes']) > 1 and x == len(a['hashes']) - 1 and y == 0:   # two rendered pieces side by side
                        continue
                    d = distance(ha, hb)
                    best = d if best is None else min(best, d)
            if best is not None and best <= limit:
                out.append({'a': a['label'], 'a_at_s': round(a['at_s'], 2), 'b': b['label'], 'b_at_s': round(b['at_s'], 2), 'distance': best})
    return out


def image_hashes(png_bytes, graphic=False):
    return [dhash(Image.open(BytesIO(png_bytes)), graphic)]


def video_hashes(path, frames, graphic=False, ffmpeg='ffmpeg'):
    """The first, middle and last frame of a rendered piece."""
    n = max(int(frames), 1)
    picks = sorted({0, n // 2, n - 1})
    with tempfile.TemporaryDirectory(prefix='vw2-look-') as d:
        sel = '+'.join(f'eq(n\\,{k})' for k in picks)
        subprocess.run([ffmpeg, '-y', '-v', 'error', '-i', str(path), '-vf', f"select='{sel}',scale=160:-2", '-fps_mode', 'passthrough', str(Path(d) / 'f%02d.png')],
                       check=True, capture_output=True, timeout=120)
        return [dhash(Image.open(p), graphic) for p in sorted(Path(d).glob('f*.png'))]
