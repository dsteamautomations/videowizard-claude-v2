"""design/130: the HyperFrames motion route for drawn shots. A shot's project (HTML + GSAP, made by the operator's helper) is checked by these rules,
its labels read word for word, given the server's own GSAP, fonts and approved pictures, and checked, snapshotted or rendered by the pinned CLI
on the VM (`hyperframes@0.8.226` in /opt/vw2/hyperframes, phase 0). No network at render: every script, font and picture is a file in the project."""
import html as html_lib
import io
import json
import os
import re
import shutil
import subprocess
import zipfile
from pathlib import Path, PurePosixPath

from .config import settings

MAX_ZIP = 10_000_000
MAX_FILES = 200
MAX_UNPACKED = 50_000_000
EXT = ('.html', '.css', '.js', '.json', '.svg', '.png', '.jpg', '.jpeg', '.webp', '.woff2', '.woff', '.ttf', '.otf', '.md', '.txt')
SUPPLIED = ('assets/vendor/', 'assets/ref/', 'assets/fonts/')   # the server places these at check and render; an upload never carries them
GSAP = 'assets/vendor/gsap.min.js'
GENERIC_FONTS = {'sans-serif', 'serif', 'monospace', 'system-ui', 'inherit', 'initial', 'unset'}
CUE_SLACK_S = 0.6   # a cued element is visible by its word's start plus this

EXTERNAL = re.compile(r'''(?:src|href)\s*=\s*["']\s*(?:https?:)?//|url\(\s*["']?\s*(?:https?:)?//|@import\s+(?:url\()?\s*["']?\s*(?:https?:)?//|\bfetch\s*\(|XMLHttpRequest|\bimport\s*\(''', re.I)
NONDET = re.compile(r'\b(Math\.random|Date\.now|new\s+Date|setTimeout|setInterval|requestAnimationFrame|performance\.now)\s*\(')
REF = re.compile(r'assets/ref/([0-9A-Za-z_-]+)\.png')
FONT_FAMILY = re.compile(r'''font-family\s*:\s*((?:"[^"]*"|'[^']*'|[^;}<>"'])+)|font-family\s*=\s*["']([^"']+)["']''', re.I)   # CSS, then an SVG attribute
ROOT = re.compile(r'''<[a-z]+\b[^>]*\bdata-composition-id\s*=\s*["'][^"']+["'][^>]*>''', re.I | re.S)


def unpack(data):
    """The project's files by path from its zip; one top folder (a zipped folder) is stripped. ValueError names what is wrong."""
    try:
        z = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        raise ValueError('the upload is not a zip file')
    infos = [i for i in z.infolist() if not i.is_dir()]
    if len(infos) > MAX_FILES:
        raise ValueError(f'too many files ({len(infos)}; at most {MAX_FILES})')
    if sum(i.file_size for i in infos) > MAX_UNPACKED:
        raise ValueError(f'the project unpacks to more than {MAX_UNPACKED // 1_000_000} MB')
    files = {}
    for i in infos:
        name = i.filename.replace('\\', '/')
        p = PurePosixPath(name)
        if name.startswith('/') or re.match(r'^[A-Za-z]:', name) or '..' in p.parts:
            raise ValueError(f'{name} lies outside the project')
        files[str(p)] = z.read(i)
    tops = {k.split('/', 1)[0] for k in files}
    if 'index.html' not in files and len(tops) == 1 and all('/' in k for k in files):
        top = tops.pop() + '/'
        files = {k[len(top):]: v for k, v in files.items()}
    return files


def _texts(files, ext=('.html', '.css', '.js', '.svg')):
    return {k: v.decode('utf-8', 'replace') for k, v in files.items() if k.lower().endswith(ext)}


def problems(files, refs, fonts, frames, fps, width, height):
    """Every rule the project breaks, as one line each; empty when it may be checked and rendered."""
    out = []
    if 'index.html' not in files:
        return ['no index.html at the project root']
    for k in files:
        if not k.lower().endswith(EXT):
            out.append(f'{k}: a {Path(k).suffix or "plain"} file; a project holds HTML, CSS, JS, JSON, SVG, pictures and fonts only')
        if k.startswith(SUPPLIED):
            out.append(f'{k}: the server supplies assets/vendor (GSAP), assets/fonts and assets/ref (the approved pictures); leave them out of the upload')
    allowed = {f.lower() for f in fonts} | GENERIC_FONTS
    for k, text in _texts(files).items():
        if EXTERNAL.search(text):
            out.append(f'{k} loads from the network ({EXTERNAL.search(text).group(0).strip()}): GSAP is {GSAP}, fonts are in assets/fonts, pictures in assets/ref')
        m = NONDET.search(text)
        if m:
            out.append(f'{k} uses {m.group(1)}: every frame must follow from the timeline alone')
        for css, attr in FONT_FAMILY.findall(text):
            for name in (n.strip().strip('"\'') for n in (css or attr).split(',')):
                if name and name.lower() not in allowed and not name.startswith('var('):
                    out.append(f'{k} uses the font {name}: use {", ".join(fonts)}')
    for rid in ref_ids(files):
        r = refs.get(rid) or {}
        if r.get('status') != 'approved' or not r.get('key'):
            out.append(f'ref {rid} is not an approved picture of this run (assets/ref/{rid}.png)')
    root = root_attrs(files['index.html'].decode('utf-8', 'replace'))
    try:
        dur = float(root.get('data-duration', 'x'))
        f = float(_fraction(fps))
        if abs(dur * f - frames) >= 0.5:
            out.append(f'the root data-duration of {root.get("data-duration")} s is {round(dur * f)} frames at {fps} fps; the shot is {frames} frames ({frames / f:.3f} s)')
    except ValueError:
        out.append('the root composition in index.html has no data-duration in seconds')
    if root.get('data-fps') and abs(float(_fraction(root['data-fps'])) - float(_fraction(fps))) > 1e-6:
        out.append(f'the root says data-fps {root["data-fps"]}; the film runs at {fps} fps')
    if (root.get('data-width'), root.get('data-height')) != (str(width), str(height)):
        out.append(f'the root is {root.get("data-width")}x{root.get("data-height")}; the film is {width}x{height}')
    return list(dict.fromkeys(out))


def _fraction(v):
    from fractions import Fraction
    return Fraction(str(v))


def root_attrs(index_html):
    m = ROOT.search(index_html)
    return dict(re.findall(r'([\w-]+)\s*=\s*["\']([^"\']*)["\']', m.group(0))) if m else {}


def ref_ids(files):
    return sorted({rid for text in _texts(files).values() for rid in REF.findall(text)})


def visible_text(files):
    """The words a viewer can read: every HTML file's text without scripts, styles and tags, a line break or a block end read as a space."""
    parts = []
    for k, text in sorted(_texts(files, ('.html',)).items()):
        t = re.sub(r'<!--.*?-->|<script\b.*?</script>|<style\b.*?</style>', ' ', text, flags=re.S | re.I)
        t = re.sub(r'<br\s*/?>|</(div|p|h[1-6]|li|span|text|tspan|tr|td)>', ' ', t, flags=re.I)
        t = re.sub(r'<[^>]+>', '', t)
        parts.append(html_lib.unescape(t))
    return re.sub(r'\s+', ' ', ' '.join(parts)).strip()


def missing_labels(files, labels):
    text = visible_text(files)
    return [l for l in labels if re.sub(r'\s+', ' ', l).strip() not in text]


def missing_selectors(files, selectors):
    ids = {i for text in _texts(files, ('.html', '.svg')).values() for i in re.findall(r'\bid\s*=\s*["\']([^"\']+)["\']', text)}
    return [s for s in selectors if s.lstrip('#') not in ids]


def sidecar(cue_seconds, selectors, slack=CUE_SLACK_S):
    """design/130 §4: the plan's cues as HyperFrames assertions, so `check` verifies the narration timing on the seeked timeline."""
    return {'assertions': [{'kind': 'appearsBy', 'selector': s, 'bySec': round(float(t) + slack, 2)} for s, t in zip(selectors, cue_seconds)]}


def prepare(folder, files, gsap, fonts, refs, sidecar):
    """The project written out with the server's files beside it: GSAP, the fonts by file name, the approved pictures, the timing sidecar."""
    folder = Path(folder)
    for k, v in files.items():
        p = folder / k
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(v)
    for rel, data in [(GSAP, gsap)] + [(f'assets/fonts/{n}', b) for n, b in fonts.items()] + [(f'assets/ref/{rid}.png', b) for rid, b in refs.items()]:
        p = folder / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
    (folder / 'index.motion.json').write_text(json.dumps(sidecar), encoding='utf-8')
    return folder


def gsap_bytes():
    return Path(settings().MOTION_GSAP).read_bytes()


def available():
    return Path(settings().MOTION_CLI).exists()


def run(args, cwd, timeout=None):
    """The pinned CLI with its own HOME (its Chrome lives there), telemetry off, the VM's FFmpeg."""
    s = settings()
    env = {**os.environ, 'HOME': s.MOTION_HOME, 'HYPERFRAMES_NO_TELEMETRY': '1', 'CI': '1',
           'HYPERFRAMES_FFMPEG_PATH': shutil.which(s.FFMPEG_EXECUTABLE) or s.FFMPEG_EXECUTABLE, 'HYPERFRAMES_FFPROBE_PATH': shutil.which(s.FFPROBE_EXECUTABLE) or s.FFPROBE_EXECUTABLE}
    return subprocess.run([s.MOTION_CLI, *args], cwd=str(cwd), env=env, capture_output=True, text=True, timeout=timeout or s.MOTION_TIMEOUT)


def _json(stdout):
    i = stdout.find('{')
    return json.loads(stdout[i:]) if i >= 0 else {}


def compact(report):
    """`check --json` reduced to what a helper acts on: ok, and each error and warning as code, message, fix."""
    errors, warnings = [], []
    for section in report.values() if isinstance(report, dict) else []:
        for f in (section.get('findings') or []) if isinstance(section, dict) else []:
            item = {'code': f.get('code'), 'message': str(f.get('message') or '')[:400], 'fix': str(f.get('fixHint') or '')[:300], **({'time': f['time']} if f.get('time') else {})}
            (errors if f.get('severity') == 'error' else warnings if f.get('severity') == 'warning' else []).append(item)
    return {'ok': bool(report.get('ok')) and not errors, 'errors': errors, 'warnings': warnings}


def check(folder):
    r = run(['check', '--json'], folder)
    try:
        return compact(_json(r.stdout))
    except ValueError:
        return {'ok': False, 'errors': [{'code': 'check_failed', 'message': (r.stderr or r.stdout)[-400:], 'fix': ''}], 'warnings': []}


def snapshot(folder, at, zoom, out_dir):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    args = ['snapshot', '--at', ','.join(f'{float(t):g}' for t in at), '--output', str(out_dir)] + (['--zoom', zoom] if zoom else [])
    r = run(args, folder)
    if r.returncode:
        raise RuntimeError(f'snapshot failed: {(r.stderr or r.stdout)[-300:]}')
    return sorted(out_dir.glob('*.png'))


def render(folder, fps, out):
    r = run(['render', '--fps', str(fps), '--quality', 'delivery', '--workers', '2', '-o', str(out)], folder)
    if r.returncode or not Path(out).exists():
        raise RuntimeError(f'render failed: {(r.stderr or r.stdout)[-300:]}')
    return Path(out)


def frames_png(mp4, indexes):
    """The contact sheet's frames, {index: png}, read from the rendered movie."""
    s = settings()
    out = {}
    for n in indexes:
        r = subprocess.run([s.FFMPEG_EXECUTABLE, '-v', 'error', '-i', str(mp4), '-vf', rf'select=eq(n\,{n})', '-vframes', '1', '-f', 'image2', '-c:v', 'png', '-'],
                           capture_output=True, timeout=60)
        if r.stdout:
            out[n] = r.stdout
    return out
