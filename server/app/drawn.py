"""design/117 P3: the drawn-graphic renderer. The planner's SVG scene (design/117 P2: data, never code) becomes the shot's exact frames at the film's
size and frame rate: headless Chromium (Playwright) draws each frame with the scene's state set by the server, ffmpeg encodes. The repo's Noto Sans is
the font (design/113 E4), a client's brand font when the run carries one. The actions (appear, build, move, highlight, fade) and their cues are
design/113's, kept; the contact sheet of P4 is made here from the frames."""
import base64
import hashlib
import json
import re
import subprocess
from fractions import Fraction
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from . import svg_scene
from .config import settings

FONTS = Path(__file__).resolve().parents[1] / 'fonts'   # server/fonts: NotoSans-Variable.ttf (Google Fonts' one file for every weight, OFL)
HIGHLIGHT = '#FFC43D'
FRAME_TIMEOUT_MS, RENDER_TIMEOUT_S = 10_000, 120   # design/117 §5
SHEET_EVERY_S, SHEET_COLS, SHEET_SCALE = 0.5, 6, 0.25


def font_file(brand=None):
    """The font to draw with: the brand font when the run carries one, else the repo's Noto Sans. Missing or unreadable: a named failure."""
    p = Path(brand) if brand else (FONTS / 'NotoSans-Variable.ttf')
    if not p.exists():
        raise ValueError(f'font {p.name} is not there ({"the brand font of this run" if brand else "under server/fonts"}); nothing is substituted (design/113 E4)')
    try:
        ImageFont.truetype(str(p), 12)
    except OSError as exc:
        raise ValueError(f'font {p.name} cannot be read: {exc}') from None
    return p


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


def states(actions, cues, fps, n_frames, ids, kids):
    """Per frame, per element id: visible, alpha (0..1), offset in viewBox units (dx, dy), highlight (0..1). An element an appear or build names waits
    for its time; every other element is there from the first frame. A build steps through a group's children (kids: group id → child ids), every_s
    apart. Later actions on an element win over earlier ones."""
    f = float(Fraction(str(fps)))
    waits, starts = set(), []
    for act, t in zip(actions or [], cues):
        members = []
        for i in act['ids']:
            for j in (kids.get(i) or [i]):
                if j not in members:
                    members.append(j)
        if act['kind'] in ('appear', 'build'):
            waits.update(members)
        starts.append((int(round(t * f)), act, members))
    frames = []
    for n in range(n_frames):
        st = {i: {'visible': i not in waits, 'alpha': 1.0, 'dx': 0.0, 'dy': 0.0, 'highlight': 0.0} for i in ids}
        for f0, act, members in starts:
            k = act['kind']
            for j, i in enumerate(members):
                if i not in st:
                    continue
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


# ---------- the page Chromium draws ----------

SET_STATE = '''(state) => {
  for (const [id, s] of Object.entries(state)) {
    const el = document.getElementById(id);
    if (!el) continue;
    if (!el.dataset.t0) el.dataset.t0 = el.getAttribute('transform') || '';
    el.style.visibility = s.visible ? 'visible' : 'hidden';
    el.style.opacity = String(s.alpha);
    el.setAttribute('transform', ((s.dx || s.dy) ? `translate(${s.dx} ${s.dy}) ` : '') + el.dataset.t0);
    el.style.filter = s.highlight ? 'drop-shadow(0 0 6px %(hl)s) drop-shadow(0 0 14px %(hl)s)' : '';
  }
  return true;
}''' % {'hl': HIGHLIGHT}

MEASURE = '''() => Array.from(document.querySelectorAll('text')).map((el, n) => {
  const b = el.getBoundingClientRect();
  return {id: el.id || ('text-' + (n + 1)), text: (el.textContent || '').trim().replace(/\\s+/g, ' '), x: b.left, y: b.top, w: b.width, h: b.height};
})'''


def page_html(svg_text, W, H, fonts, images):
    """The HTML Chromium loads: the scene inline at the film's size, the fonts as @font-face from data URIs, the pictures embedded, no animation."""
    faces = ''.join(f"@font-face{{font-family:'{name}';src:url(data:font/ttf;base64,{base64.b64encode(data).decode('ascii')}) format('truetype');font-weight:100 900;}}"
                    for name, data in fonts.items())
    svg = svg_scene.embed(svg_text, images)
    svg = re.sub(r'<svg\b', f'<svg width="{W}" height="{H}" preserveAspectRatio="xMidYMid meet"', svg, count=1)
    return (f'<!doctype html><html><head><meta charset="utf-8"><style>{faces}'
            f'html,body{{margin:0;padding:0;width:{W}px;height:{H}px;overflow:hidden;background:#FFFFFF}}'
            f'svg{{display:block;font-family:"{next(iter(fonts))}"}}*{{animation:none!important;transition:none!important}}</style></head>'
            f'<body>{svg}</body></html>')


_pw = {'p': None, 'b': None, 'ok': None}


def available():
    """Whether this host can render: Playwright installed and its Chromium present (reported by /api/meta, design/117 §5)."""
    if _pw['ok'] is None:
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                _pw['ok'] = Path(p.chromium.executable_path).exists()
        except Exception:
            _pw['ok'] = False
    return _pw['ok']


def browser():
    """One Chromium per worker process, started on first use, restarted after a failure (design/117 §5)."""
    if _pw['b'] is None or not _pw['b'].is_connected():
        from playwright.sync_api import sync_playwright
        if _pw['p'] is None:
            _pw['p'] = sync_playwright().start()
        _pw['b'] = _pw['p'].chromium.launch(args=['--disable-gpu', '--force-color-profile=srgb', '--font-render-hinting=none'])
    return _pw['b']


def reset():
    """Forget the browser (a crash, or a test); the next render starts a new one."""
    try:
        if _pw['b'] is not None:
            _pw['b'].close()
    except Exception:
        pass
    _pw['b'] = None


def stop():
    """Close the browser and the Playwright driver (a worker shutting down, a test module ending)."""
    reset()
    try:
        if _pw['p'] is not None:
            _pw['p'].stop()
    except Exception:
        pass
    _pw['p'] = None


def _page(html, W, H):
    page = browser().new_page(viewport={'width': W, 'height': H}, device_scale_factor=1)
    page.set_default_timeout(FRAME_TIMEOUT_MS)
    page.set_content(html, wait_until='load')
    page.evaluate('() => document.fonts.ready.then(() => true)')
    return page


def measure(svg_text, W, H, fonts, images):
    """Every text's box in frame pixels (all elements visible), for the safe-area rule: [{'id', 'text', 'x', 'y', 'w', 'h'}]."""
    page = _page(page_html(svg_text, W, H, fonts, images), W, H)
    try:
        return page.evaluate(MEASURE)
    finally:
        page.close()


class TextOutside(ValueError):
    """A text's box leaves the safe area; .boxes names them. Raised by the render before frame 0 (the page measures itself, no second load)."""

    def __init__(self, boxes):
        self.boxes = boxes
        super().__init__('; '.join(f"text '{b['text'][:40]}' leaves the safe area (the inner 90 % of the frame)" for b in boxes))


def outside(boxes, W, H, safe=svg_scene.SAFE):
    """The texts whose box leaves the inner (1 - 2·safe) of the frame."""
    return [b for b in boxes if b['w'] > 0 and (b['x'] < safe * W or b['y'] < safe * H or b['x'] + b['w'] > (1 - safe) * W or b['y'] + b['h'] > (1 - safe) * H)]


def _frames(request, svg_text, images, fonts, every=None):
    """Yield (index, png bytes) for every frame, with the state set on the page before each screenshot; `every` keeps every k-th frame only."""
    W, H, fps, n = int(request['width']), int(request['height']), str(request['fps']), int(request['frames'])
    root = svg_scene.parse(svg_text)
    ids = list(svg_scene.ids_of(root))
    sts = states(request['scene'].get('actions') or [], request['cues'], fps, n, ids, svg_scene.children_of(root))
    page = _page(page_html(svg_text, W, H, fonts, images), W, H)
    try:
        off = outside(page.evaluate(MEASURE), W, H)   # review 28 Oct: measured on the render's own page, before frame 0
        if off:
            raise TextOutside(off)
        for i in range(n):
            if every and i % every and i != n - 1:
                continue
            page.evaluate(SET_STATE, sts[i])
            yield i, page.screenshot(type='png', clip={'x': 0, 'y': 0, 'width': W, 'height': H})
    finally:
        page.close()


def render(request, out_path, svg_text, images, fonts, keep=None):
    """The whole shot: request = {scene: {actions}, width, height, fps, frames, cues}. Writes out_path (mp4); returns {'frames', 'digest', 'kept'}
    where kept is {frame index: png} for the indexes in `keep` (the sheet's frames, the first and the last)."""
    W, H, fps, n = int(request['width']), int(request['height']), str(request['fps']), int(request['frames'])
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [settings().FFMPEG_EXECUTABLE, '-y', '-v', 'error', '-f', 'image2pipe', '-framerate', fps, '-c:v', 'png', '-i', '-',
           '-an', '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p', '-r', fps, '-frames:v', str(n), str(out_path)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    kept = {}
    try:
        for i, png in _frames(request, svg_text, images, fonts):
            proc.stdin.write(png)
            if keep and i in keep:
                kept[i] = png
        proc.stdin.close()
        err = proc.stderr.read().decode('utf-8', 'replace')
        if proc.wait(timeout=RENDER_TIMEOUT_S) != 0:
            raise ValueError(f'ffmpeg failed: {err[-400:]}')
    finally:
        if proc.poll() is None:
            proc.kill()
    return {'frames': n, 'digest': hashlib.sha256(json.dumps(request, sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest(), 'kept': kept}


def frame_png(request, index, svg_text, images, fonts):
    """One frame as PNG bytes (tests, the check)."""
    for i, png in _frames(request, svg_text, images, fonts):
        if i == index:
            return png
    raise ValueError(f'frame {index} is past the end ({request["frames"]} frames)')


def sheet_indexes(fps, n, every_s=SHEET_EVERY_S):
    """The frames of the contact sheet: one every half second, the first and the last."""
    step = max(int(round(float(Fraction(str(fps))) * every_s)), 1)
    return sorted(set(range(0, n, step)) | {0, max(n - 1, 0)})


def sheet(frames, fps, W, H, font=None, cols=SHEET_COLS, scale=SHEET_SCALE):
    """design/117 P4: the contact sheet: the given {index: png} tiled in order at a quarter size, the time under each. Returns JPEG bytes."""
    f = float(Fraction(str(fps)))
    tw, th, label = max(int(W * scale), 1), max(int(H * scale), 1), 22
    idx = sorted(frames)
    rows = max((len(idx) + cols - 1) // cols, 1)
    out = Image.new('RGB', (cols * (tw + 4) + 4, rows * (th + label + 4) + 4), (32, 32, 32))
    d = ImageDraw.Draw(out)
    try:
        fnt = ImageFont.truetype(str(font or font_file()), 14)
    except (OSError, ValueError):
        fnt = ImageFont.load_default()
    for k, i in enumerate(idx):
        im = Image.open(BytesIO(frames[i])).convert('RGB').resize((tw, th), Image.LANCZOS)
        x, y = 4 + (k % cols) * (tw + 4), 4 + (k // cols) * (th + label + 4)
        out.paste(im, (x, y))
        d.text((x + 4, y + th + 3), f'{i / f:.2f} s', fill=(240, 240, 240), font=fnt)
    buf = BytesIO()
    out.save(buf, 'JPEG', quality=88)
    return buf.getvalue()
