"""Text overlays, the worker's side (requirements version 3 of 28 Nov 2026, part E). One resolved overlay row (overlays.check) becomes a HyperFrames
project with the server's own GSAP and fonts; from it the server makes the still picture the operator approves (the overlay laid on the shot's own frame)
and the transparent clip for the editor's package. The clip is passed on only when its length, its size and its transparent background are right.
Nothing here judges the overlay: the operator does."""
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

from . import drawn, film, motion
from . import overlay_template as T
from .config import settings

FALLBACK = {'family': 'Noto Sans', 'file': 'NotoSans-Variable.ttf', 'bold': False}   # the signs a font lacks (a currency sign, an arrow) are drawn in Noto Sans


def FFMPEG():
    return settings().FFMPEG_EXECUTABLE


def faces(font, scripts):
    own = film.font_faces(font, scripts)
    return own if any(f['family'] == FALLBACK['family'] for f in own) else own + [FALLBACK]


def _font_bytes(name):
    return (drawn.FONTS / name).read_bytes()


def project(folder, row, page, gsap=None, font_bytes=_font_bytes):
    """The overlay's project folder, written afresh: the page, GSAP and the font files, all the server's own."""
    folder = Path(folder)
    shutil.rmtree(folder, ignore_errors=True)
    fonts = faces(row['font'], page.get('scripts'))
    files = {'index.html': T.page(row, {**page, 'fonts': fonts}).encode('utf-8'),
             'hyperframes.json': json.dumps({'paths': {'blocks': 'compositions', 'assets': 'assets'}}).encode()}
    return motion.prepare(folder, files, motion.gsap_bytes() if gsap is None else gsap, {f['file']: font_bytes(f['file']) for f in fonts}, {}, None)


def probe(path):
    out = subprocess.run([settings().FFPROBE_EXECUTABLE, '-v', 'error', '-select_streams', 'v:0', '-count_frames', '-show_entries', 'stream=nb_read_frames,width,height,pix_fmt',
                          '-of', 'json', str(path)], capture_output=True, check=True, timeout=120).stdout
    v = (json.loads(out).get('streams') or [{}])[0]
    return {'frames': int(v.get('nb_read_frames') or 0), 'width': v.get('width'), 'height': v.get('height'), 'pix_fmt': v.get('pix_fmt')}


def clip_faults(seen, frames, width, height):
    """The three checks of a made clip, in plain words; [] when it is right."""
    return ([f"{seen['frames']} frames for {frames}"] if seen['frames'] != frames else []) + \
           ([f"{seen['width']}x{seen['height']} for {width}x{height}"] if (seen['width'], seen['height']) != (width, height) else []) + \
           ([] if 'yuva' in str(seen['pix_fmt']) or 'rgba' in str(seen['pix_fmt']) else [f"no transparent background ({seen['pix_fmt']})"])


def clip(row, page, folder, key, store, gsap=None, font_bytes=_font_bytes, render=None, probe=probe):
    """The transparent clip of one overlay, kept under `key`. (status, result, error)."""
    frames = row['end_frame'] - row['start_frame']
    try:
        out = (render or motion.render_mov)(project(folder, row, page, gsap, font_bytes), page['fps'], Path(folder) / 'overlay.mov')
        seen = probe(out)
    except (RuntimeError, OSError, subprocess.SubprocessError, ValueError) as e:
        return 'failed', {}, f'The overlay clip could not be made: {e}'[:500]
    faults = clip_faults(seen, frames, page['width'], page['height'])
    if faults:
        return 'failed', {'faults': faults, 'seen': seen}, f"The overlay clip is not right: {'; '.join(faults)}."
    data = Path(out).read_bytes()
    store.put(key, data, 'video/quicktime')
    return 'ready', {'key': key, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(), 'frames': frames}, None


def compose(base, over, out, width, height):
    """The transparent picture of the overlay laid on a frame of the film, at the film's size."""
    subprocess.run([FFMPEG(), '-y', '-v', 'error', '-i', str(base), '-i', str(over), '-filter_complex',
                    f'[0:v]scale={width}:{height}[b];[1:v]scale={width}:{height}[o];[b][o]overlay=format=auto', '-frames:v', '1', '-q:v', '3', str(out)],
                   check=True, capture_output=True, timeout=120)


def still(row, page, base, folder, key, store, gsap=None, font_bytes=_font_bytes, snapshot=None, compose=compose):
    """The picture the operator approves: the overlay, with everything in, on the shot's own frame (`base`, the picture's bytes). (status, result, error)."""
    folder = Path(folder)
    try:
        shots = (snapshot or motion.snapshot)(project(folder, row, page, gsap, font_bytes), [T.still_at(row, page['fps'])], None, folder / 'shots')
        if not shots:
            raise RuntimeError('snapshot gave no picture')
        (folder / 'base').write_bytes(base)
        compose(folder / 'base', shots[0], folder / 'still.jpg', page['width'], page['height'])
        data = (folder / 'still.jpg').read_bytes()
    except (RuntimeError, OSError, subprocess.SubprocessError) as e:
        return 'failed', {}, f'The overlay picture could not be made: {e}'[:500]
    store.put(key, data, 'image/jpeg')
    return 'ready', {'key': key, 'bytes': len(data)}, None


def frame_of(data, picture, at_s, folder, width, height):
    """The picture under a still, as bytes: the shot's own picture, the frame of its movie at `at_s`, or a plain ground when the shot has no file here."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    if data and picture:
        return data
    out = folder / 'base.png'
    if data:
        (folder / 'base-src').write_bytes(data)   # ponytail: the whole file is fetched for one frame; a proxy or a ranged read if camera files of gigabytes are ever read here
        args = ['-ss', f'{at_s:g}', '-i', str(folder / 'base-src')]
    else:
        args = ['-f', 'lavfi', '-i', f'color=c=0x555555:s={width}x{height}']
    subprocess.run([FFMPEG(), '-y', '-v', 'error', *args, '-frames:v', '1', str(out)], check=True, capture_output=True, timeout=300)
    return out.read_bytes()


def process(store, request, folder, still=None, clip=None, frame_of=frame_of):
    """One queued overlay request (overlay_stage.requests), made. Free. Returns (status, result, error, cost, retry_in) like every worker job."""
    cost = {'provider': 'motion', 'inr': 0}
    row, page = request['row'], request['page']
    if request['kind'] == 'overlay-clip':
        status, result, error = (clip or globals()['clip'])(row, page, Path(folder) / 'project', request['out_key'], store)
        return status, result, error, cost, None
    base, data = request.get('base'), None
    if base:
        try:
            data = store.get(base['key'])
        except Exception:   # noqa: BLE001  the shot's file is not on the server (a camera original kept on the laptop): the still is shown on a plain ground
            data = None
    try:
        ground = frame_of(data, bool(base and base['picture']), (base or {}).get('at_s') or 0, Path(folder) / 'base', page['width'], page['height'])
    except (OSError, subprocess.SubprocessError) as e:
        return 'failed', {}, f'The overlay picture could not be made: the shot\'s frame could not be read ({e.__class__.__name__}).', cost, None
    status, result, error = (still or globals()['still'])(row, page, ground, Path(folder) / 'project', request['out_key'], store)
    return status, ({**result, 'ground': 'shot' if data else 'plain'} if status == 'ready' else result), error, cost, None
