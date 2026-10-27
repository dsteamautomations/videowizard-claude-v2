"""design/113 E2: the drawn-graphic renderer. A declarative scene (design/113 E1: plain data, never code) becomes the shot's exact frames at the
film's size and frame rate: Pillow draws each frame at twice the size and downsamples, ffmpeg encodes. The repo's Noto Sans is the font (design/113
E4), a client's brand font when the run carries one; a font that cannot be read fails the render by name, nothing is substituted silently."""
import hashlib
import json
import re
import subprocess
from fractions import Fraction
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .config import settings

FONTS = Path(__file__).resolve().parents[1] / 'fonts'   # server/fonts: NotoSans-Variable.ttf (Google Fonts' one file for every weight, OFL), the Bold instance chosen by name
MARGIN = 0.04            # the canvas is contained in the frame with this margin on every side
HIGHLIGHT = '#FFC43D'    # the highlight ring
SUPER = 2                # drawn at twice the size, then downsampled: clean edges without an extra dependency


def font_file(bold=False, brand=None):
    """The font to draw with: the brand font when the run carries one, else the repo's Noto Sans (static Regular/Bold files when present, else the one
    variable file, whose Bold instance is chosen by name). Missing or unreadable: a named failure."""
    if brand:
        p = Path(brand)
    else:
        static = FONTS / ('NotoSans-Bold.ttf' if bold else 'NotoSans-Regular.ttf')
        p = static if static.exists() else FONTS / 'NotoSans-Variable.ttf'
    if not p.exists():
        raise ValueError(f'font {p.name} is not there ({"the brand font of this run" if brand else "under server/fonts"}); nothing is substituted (design/113 E4)')
    try:
        ImageFont.truetype(str(p), 12)
    except OSError as exc:
        raise ValueError(f'font {p.name} cannot be read by Pillow: {exc}') from None
    return p


def typeface(path, size, bold=False):
    """A Pillow font at a size; a variable font takes its Bold or Regular instance by name, a static file is used as it is."""
    f = ImageFont.truetype(str(path), size)
    try:
        names = [n.decode() if isinstance(n, bytes) else n for n in f.get_variation_names()]
    except OSError:
        return f   # a static font has no instances
    want = 'Bold' if bold else 'Regular'
    if want in names:
        f.set_variation_by_name(want)
    return f


def _tokens(text):
    return re.findall(r"[a-z0-9']+", str(text or '').lower())


def cue_seconds(scene, shot, words, fps):
    """design/113 E1: each action's start in seconds from the shot's start: at_s as given, or the first narration word (film frames) inside the shot
    whose text carries the cue. A word cue with no timed narration on the run is a named failure: give at_s."""
    f, a, b = float(Fraction(str(fps))), shot['start_frame'], shot['end_frame']
    out = []
    for n, act in enumerate(scene.get('actions') or [], 1):
        if act.get('at_s') is not None:
            out.append(float(act['at_s']))
            continue
        cue = ' '.join(_tokens(act.get('word')))
        if not words:
            raise ValueError(f"action {n} is keyed to the word '{act.get('word')}' but the run has no timed narration: give at_s (seconds from the shot's start)")
        hit = next((w for w in words if a <= w['start_frame'] < b and cue in ' '.join(_tokens(w['text']))), None)
        if hit is None:   # a cue of several words: the first word that starts the phrase
            flat = [(w, t) for w in words if a <= w['start_frame'] < b for t in _tokens(w['text'])]
            toks = cue.split()
            for i in range(len(flat) - len(toks) + 1):
                if [t for _, t in flat[i:i + len(toks)]] == toks:
                    hit = flat[i][0]
                    break
        if hit is None:
            raise ValueError(f"action {n}: the word '{act.get('word')}' is not spoken inside {shot['id']} ({a}-{b}); the plan check reads the shot's narration, the timing the recorded words: give at_s")
        out.append(round((hit['start_frame'] - a) / f, 3))
    return out


def layout(scene, W, H):
    """Units to pixels: the canvas contained in the frame with a margin, the same scale both ways, y down."""
    sw, sh = float(scene['width']), float(scene['height'])
    scale = min(W * (1 - 2 * MARGIN) / sw, H * (1 - 2 * MARGIN) / sh)
    ox, oy = (W - sw * scale) / 2, (H - sh * scale) / 2
    return lambda x, y: (ox + float(x) * scale, oy + float(y) * scale), scale


def _members(scene, ids):
    """The shapes an action touches: a group stands for its members, a repeat for itself."""
    by = {s['id']: s for s in scene['shapes']}
    out = []
    for i in ids:
        s = by.get(i)
        if s and s['kind'] == 'group':
            out += [m for m in s.get('members') or [] if m not in out]
        elif i not in out:
            out.append(i)
    return out


def states(scene, cues, fps, n_frames):
    """Per frame, per shape: visible, alpha (0..1), offset in units (dx, dy), highlight (0..1). A shape an appear or build names waits for its
    time; every other shape is there from the first frame. Later actions on a shape win over earlier ones."""
    f = float(Fraction(str(fps)))
    ids = [s['id'] for s in scene['shapes']]
    waits = set()
    starts = []   # (frame, kind, shape ids, action)
    for act, t in zip(scene.get('actions') or [], cues):
        members = _members(scene, act['ids'])
        if act['kind'] in ('appear', 'build'):
            waits.update(members)
        starts.append((int(round(t * f)), act, members))
    frames = []
    for n in range(n_frames):
        st = {i: {'visible': i not in waits, 'alpha': 1.0, 'dx': 0.0, 'dy': 0.0, 'highlight': 0.0} for i in ids}
        for f0, act, members in starts:
            k = act['kind']
            for j, i in enumerate(members):
                if k == 'appear' and n >= f0:
                    st[i]['visible'] = True
                elif k == 'build':
                    if n >= f0 + int(round(j * float(act.get('every_s') or 0.5) * f)):
                        st[i]['visible'] = True
                elif k == 'fade' and n >= f0:
                    span = max(int(round(float(act.get('seconds') or 1) * f)), 1)
                    st[i]['alpha'] = max(0.0, 1.0 - (n - f0) / span)
                    st[i]['visible'] = st[i]['alpha'] > 0
                elif k == 'highlight' and n >= f0:
                    span = max(int(round(float(act.get('seconds') or 1) * f)), 1)
                    st[i]['highlight'] = 1.0 if n - f0 < span else 0.0
                elif k == 'move' and n >= f0 and len(act.get('path') or []) >= 2:
                    span = max(int(round(float(act.get('seconds') or 1) * f)), 1)
                    u = min((n - f0) / span, 1.0)
                    path = act['path']
                    seg = u * (len(path) - 1)
                    idx = min(int(seg), len(path) - 2)   # the last point is reached, never passed
                    a_, b_, w = path[idx], path[idx + 1], seg - idx
                    st[i]['dx'] = (a_[0] + (b_[0] - a_[0]) * w) - path[0][0]
                    st[i]['dy'] = (a_[1] + (b_[1] - a_[1]) * w) - path[0][1]
        frames.append(st)
    return frames


def _rgb(hexs, default):
    h = (hexs or default).lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def draw_frame(scene, labels, state, W, H, fonts, images=None):
    """One frame as a PIL image: the background, then the shapes in order (and the server's labels last), each at its state."""
    S = SUPER
    img = Image.new('RGBA', (W * S, H * S), _rgb(scene.get('background'), '#FFFFFF') + (255,))
    to, scale = layout(scene, W * S, H * S)
    layer = Image.new('RGBA', img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    by = {s['id']: s for s in scene['shapes']}

    def draw_shape(s, st, dx=0.0, dy=0.0):
        a = int(255 * st['alpha'])
        stroke = _rgb(s.get('stroke'), '#222222') + (a,)
        fill = (_rgb(s['fill'], '#FFFFFF') + (a,)) if s.get('fill') else None
        wt = max(1, int(round(float(s.get('weight') or 2) * S)))
        ox, oy = dx + st['dx'], dy + st['dy']
        k = s['kind']
        if k == 'rect' or k == 'image':
            x0, y0 = to(s['x'] + ox, s['y'] + oy)
            x1, y1 = to(s['x'] + ox + s['w'], s['y'] + oy + s['h'])
            if k == 'image' and images and s.get('image_ref') in images:
                pic = Image.open(BytesIO(images[s['image_ref']])).convert('RGBA').resize((max(1, int(x1 - x0)), max(1, int(y1 - y0))))
                if a < 255:
                    pic.putalpha(pic.getchannel('A').point(lambda v: v * a // 255))
                layer.paste(pic, (int(x0), int(y0)), pic)
            else:
                d.rectangle((x0, y0, x1, y1), fill=fill, outline=stroke, width=wt)
            if st['highlight']:
                d.rectangle((x0 - wt * 2, y0 - wt * 2, x1 + wt * 2, y1 + wt * 2), outline=_rgb(HIGHLIGHT, HIGHLIGHT) + (a,), width=wt * 2)
        elif k in ('line', 'arrow'):
            x0, y0 = to(s['x'] + ox, s['y'] + oy)
            x1, y1 = to(s['x2'] + ox, s['y2'] + oy)
            d.line((x0, y0, x1, y1), fill=stroke, width=wt)
            if k == 'arrow':
                import math
                ang = math.atan2(y1 - y0, x1 - x0)
                head = wt * 5
                pts = [(x1, y1), (x1 - head * math.cos(ang - 0.45), y1 - head * math.sin(ang - 0.45)), (x1 - head * math.cos(ang + 0.45), y1 - head * math.sin(ang + 0.45))]
                d.polygon(pts, fill=stroke)
            if st['highlight']:
                d.line((x0, y0, x1, y1), fill=_rgb(HIGHLIGHT, HIGHLIGHT) + (a,), width=wt * 3)
                d.line((x0, y0, x1, y1), fill=stroke, width=wt)
        elif k == 'circle':
            cx, cy = to(s['x'] + ox, s['y'] + oy)
            r = float(s['r']) * scale
            d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=fill, outline=stroke, width=wt)
            if st['highlight']:
                d.ellipse((cx - r - wt * 2, cy - r - wt * 2, cx + r + wt * 2, cy + r + wt * 2), outline=_rgb(HIGHLIGHT, HIGHLIGHT) + (a,), width=wt * 2)
        elif k == 'polygon':
            pts = [to(px + ox, py + oy) for px, py in s['points']]
            d.polygon(pts, fill=fill, outline=stroke, width=wt)
        elif k == 'text':
            x0, y0 = to(s['x'] + ox, s['y'] + oy)
            size = max(8, int(round(float(s.get('size_pct') or 4) / 100 * H * S)))
            fnt = typeface(fonts['bold' if s.get('bold') else 'regular'], size, bool(s.get('bold')))
            if st['highlight']:
                box = d.textbbox((x0, y0), s['text'], font=fnt)
                d.rectangle((box[0] - wt * 2, box[1] - wt * 2, box[2] + wt * 2, box[3] + wt * 2), fill=_rgb(HIGHLIGHT, HIGHLIGHT) + (a,))
            d.text((x0, y0), s['text'], fill=stroke, font=fnt)
            if s.get('leader'):
                lx, ly = to(s['leader'][0] + ox, s['leader'][1] + oy)
                d.line((lx, ly, x0 - wt, y0 + size * 0.5), fill=stroke, width=max(1, wt // 2))
        elif k == 'repeat':
            base = by.get(s.get('of'))
            if base:
                for i in range(int(s.get('count') or 0)):
                    draw_shape(base, st, ox + i * float(s.get('dx') or 0), oy + i * float(s.get('dy') or 0))
        # a group draws nothing itself: its members are shapes of their own

    for s in list(scene['shapes']) + list(labels or []):
        st = state.get(s['id'], {'visible': True, 'alpha': 1.0, 'dx': 0.0, 'dy': 0.0, 'highlight': 0.0})
        if s['kind'] == 'group' or not st['visible']:
            continue
        draw_shape(s, st)
    img.alpha_composite(layer)
    return img.convert('RGB').resize((W, H), Image.LANCZOS)


def render(request, out_path, images=None):
    """The whole shot: request = {scene, labels, width, height, fps, frames, cues, font (optional brand path)}. Writes out_path (mp4), returns
    {'frames': n, 'digest': sha256 of the request}."""
    scene, labels, W, H = request['scene'], request.get('labels') or [], int(request['width']), int(request['height'])
    fps, n = str(request['fps']), int(request['frames'])
    fonts = {'regular': font_file(False, request.get('font')), 'bold': font_file(True, request.get('font_bold') or request.get('font'))}
    frames = states(scene, request['cues'], fps, n)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [settings().FFMPEG_EXECUTABLE, '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', fps, '-i', '-',
           '-an', '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p', '-r', fps, '-frames:v', str(n), str(out_path)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        for i in range(n):
            proc.stdin.write(draw_frame(scene, labels, frames[i], W, H, fonts, images).tobytes())
        proc.stdin.close()
        err = proc.stderr.read().decode('utf-8', 'replace')
        if proc.wait(timeout=600) != 0:
            raise ValueError(f'ffmpeg failed: {err[-400:]}')
    finally:
        if proc.poll() is None:
            proc.kill()
    return {'frames': n, 'digest': hashlib.sha256(json.dumps(request, sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()}


def frame_png(request, index, images=None):
    """One frame as PNG bytes, for the check (the first and the last frame) and for tests."""
    fonts = {'regular': font_file(False, request.get('font')), 'bold': font_file(True, request.get('font_bold') or request.get('font'))}
    st = states(request['scene'], request['cues'], str(request['fps']), int(request['frames']))[index]
    buf = BytesIO()
    draw_frame(request['scene'], request.get('labels') or [], st, int(request['width']), int(request['height']), fonts, images).save(buf, 'PNG')
    return buf.getvalue()
