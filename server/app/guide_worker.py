"""The worker side of the guide route (integration steps B to D, SK 12 Nov 2026): Blender renders on the server, the overlay of a still on its
guide frame, and the frames kept of a returned take (design/223: nothing is measured on a take and nothing is set aside).

Renders are free and slow (about 4 s a frame on the VM, software graphics): one at a time, at low priority, in chunks with the job's claim
renewed between them; the frame folders are deleted when the job ends, whatever happened.
"""
import hashlib
import json
import os
import shutil
import subprocess
import time
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageFilter

from . import guide, guide_spec as G, generations, jobs
from .config import settings
from .db import connect
from .storage import storage

SCRIPT = Path(__file__).resolve().parents[1] / 'blender' / 'guide_scene.py'


def spool():
    from .visual_workers import SPOOL
    return SPOOL


# ---------- Blender ----------

def run_blender(spec_path, outdir, frames, samples, look='eevee'):
    """One Blender call for a list of frames. Succeeds only when the script's last line says so and every frame is on disk.
    look: 'eevee' (the first frame, for the still) or 'flat' (layout B: Workbench, flat colours, thin black outlines)."""
    s = settings()
    cmd = [s.BLENDER_BIN, '-b', '--factory-startup', '--gpu-backend', 'opengl', '--python', str(SCRIPT), '--', str(spec_path), str(outdir),
           'frames=' + ','.join(str(f) for f in frames), f'samples={samples}', f'look={look}']
    env = {**os.environ, 'LIBGL_ALWAYS_SOFTWARE': '1'}
    r = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=s.GUIDE_TIMEOUT, preexec_fn=(lambda: os.nice(10)) if hasattr(os, 'nice') else None)
    tail = [l for l in (r.stdout or '').splitlines() if l.startswith('GUIDE ')]
    if r.returncode != 0 or not tail or not tail[-1].startswith('GUIDE DONE'):
        why = tail[-1] if tail else ((r.stderr or r.stdout or '').strip().splitlines() or ['Blender gave no answer'])[-1]
        raise RuntimeError(f'Blender did not build the guide: {why[:300]}')
    missing = [f for f in frames if not (Path(outdir) / f'g{f:04d}.png').exists()]
    if missing:
        raise RuntimeError(f'Blender wrote no picture for frames {missing[:5]}')


def strip(pngs, height=240):
    """The check frames side by side, small: what a fresh checker and the operator look at."""
    ims = [Image.open(BytesIO(p)).convert('RGB') for p in pngs]
    ims = [im.resize((max(1, im.width * height // im.height), height), Image.LANCZOS) for im in ims]
    out = Image.new('RGB', (sum(im.width for im in ims) + 4 * (len(ims) - 1), height), (20, 20, 20))
    x = 0
    for im in ims:
        out.paste(im, (x, 0))
        x += im.width + 4
    buf = BytesIO()
    out.save(buf, format='JPEG', quality=86)
    return buf.getvalue()


def overlay(frame_png, still_png, threshold=28):
    """The overlay check: the guide frame's edges drawn in red over the still; below it the guide frame and the plain still, half size. JPEG bytes."""
    import numpy as np
    still = Image.open(BytesIO(still_png)).convert('RGB')
    W, H = still.size
    frame = Image.open(BytesIO(frame_png)).convert('RGB').resize((W, H), Image.LANCZOS)
    g = np.asarray(frame.filter(ImageFilter.GaussianBlur(1.2)), dtype=np.float32)
    dx = np.abs(np.diff(g, axis=1, append=g[:, -1:, :])).max(axis=2)
    dy = np.abs(np.diff(g, axis=0, append=g[-1:, :, :])).max(axis=2)
    edge = np.asarray(Image.fromarray(((np.maximum(dx, dy) > threshold) * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(3))) > 0
    over = np.asarray(still).copy()
    over[edge] = (255, 0, 0)
    half = (W // 2, H // 2)
    sheet = Image.new('RGB', (W, H + half[1]), (20, 20, 20))
    sheet.paste(Image.fromarray(over), (0, 0))
    sheet.paste(frame.resize(half, Image.LANCZOS), (0, H))
    sheet.paste(still.resize(half, Image.LANCZOS), (half[0], H))
    buf = BytesIO()
    sheet.save(buf, format='JPEG', quality=88)
    return buf.getvalue()


def _put(store, k, data, mime):
    store.put(k, data, mime)
    return hashlib.sha256(data).hexdigest()


def process(job, renew=None):
    """One guide job. Returns (status, result, error, cost, retry_in)."""
    req, jid, store = job['request'], str(job['id']), storage()
    base = f"{job['run_id']}/visuals/guides/{req['sha256']}"
    if req['kind'] == 'guide-still':
        from .visual_workers import process_image
        status, result, error, cost, retry_in = process_image(job)
        if status == 'retained':
            try:
                session = json.loads(store.get(f"{job['run_id']}/visuals/session.json").decode('utf-8'))
                g = (session.get('guides') or {}).get(req['shot_id']) or {}
                frame_key = (g.get('render') or {}).get('frame1_key')
                data = overlay(store.get(frame_key), store.get(result['key']))
                result['overlay_key'] = f"{base}/overlay-{req['reference']['id']}.jpg"
                store.put(result['overlay_key'], data, 'image/jpeg')
            except Exception as exc:   # a still without its overlay cannot be approved; the reason is kept
                result['overlay_error'] = f'{exc.__class__.__name__}: {str(exc)[:200]}'
        return status, result, error, cost, retry_in
    folder = spool() / jid
    t0 = time.time()
    try:
        shutil.rmtree(folder, ignore_errors=True)
        folder.mkdir(parents=True)
        spec_path = folder / 'scene.json'
        spec_path.write_bytes(store.get(req['spec_key']))
        if req['kind'] == 'guide-frames':
            run_blender(spec_path, folder / 'check', req['frames'], 1, settings().GUIDE_VIDEO_LOOK)   # layout B: the checker sees what the video shows
            pngs = [(folder / 'check' / f'g{f:04d}.png').read_bytes() for f in req['frames']]
            frames = []
            for f, png in zip(req['frames'], pngs):
                k = f'{base}/check-{f:04d}.png'
                store.put(k, png, 'image/png')
                frames.append({'n': f, 'key': k})
            strip_key = f'{base}/check-strip.jpg'
            store.put(strip_key, strip(pngs), 'image/jpeg')
            return 'ready', {'frames': frames, 'strip_key': strip_key, 'render_seconds': round(time.time() - t0, 1)}, None, {'provider': 'guide', 'inr': 0}, None
        s = settings()
        n = int(round(req['seconds'] * G.FPS))
        frame1_key = f'{base}/frame1.png'
        # release 4 (SK, 20 Nov 2026): the first frame is a job of its own (`guide-frame1`, the quick lane), so a still never waits behind a video.
        # The video's job makes it only when it is not stored yet: a job queued by the older code (one job for both), or a first-frame job that failed.
        # ponytail: two workers can each render a missing first frame at the same moment (the later file stays); a claim on the frame if that is ever seen.
        if req['kind'] == 'guide-frame1' or not store.exists(frame1_key):
            run_blender(spec_path, folder / 'first', [1], s.GUIDE_FRAME1_SAMPLES)   # the still is made from this frame: full quality, true shadows
            store.put(frame1_key, (folder / 'first' / 'g0001.png').read_bytes(), 'image/png')
        first = {'frame1_key': frame1_key, 'frame1_sha256': hashlib.sha256(store.get(frame1_key)).hexdigest()}   # of the file as it is stored
        if req['kind'] == 'guide-frame1':
            return 'ready', {**first, 'render_seconds': round(time.time() - t0, 1)}, None, {'provider': 'guide', 'inr': 0}, None
        for a in range(1, n + 1, s.GUIDE_CHUNK):   # layout B (SK, 20 Nov 2026): every frame of the video in one look, its frame 1 too; the still keeps the EEVEE frame 1 above
            run_blender(spec_path, folder / 'all', list(range(a, min(a + s.GUIDE_CHUNK, n + 1))), 1, s.GUIDE_VIDEO_LOOK)
            if renew:
                renew()   # a guide of 15 s is about half an hour of rendering; the claim lasts twenty minutes
        out = folder / 'guide.mp4'
        r = subprocess.run([s.FFMPEG_EXECUTABLE, '-y', '-v', 'error', '-framerate', str(G.FPS), '-i', str(folder / 'all' / 'g%04d.png'), '-c:v', 'libx264', '-crf', '16', '-pix_fmt', 'yuv420p', str(out)],
                           capture_output=True, text=True, timeout=300)
        if r.returncode != 0 or not out.exists():
            raise RuntimeError('the frames could not be joined into a video: ' + (r.stderr or '').strip()[-200:])
        data = out.read_bytes()
        guide_key = f'{base}/guide.mp4'
        sha = _put(store, guide_key, data, 'video/mp4')
        return 'ready', {'guide_key': guide_key, 'sha256': sha, 'bytes': len(data), **first, 'frames': n, 'render_seconds': round(time.time() - t0, 1), 'look': s.GUIDE_VIDEO_LOOK}, None, {'provider': 'guide', 'inr': 0}, None
    except Exception as exc:   # a fault is reported as it is; nothing was paid for
        return 'failed', {'phase': req['kind']}, f'{exc.__class__.__name__}: {str(exc)[:400]}', None, None
    finally:
        shutil.rmtree(folder, ignore_errors=True)   # a disk once filled with 8.7 GB of frame folders


def finish(job, status, result, error, cost, retry_in):
    """The job's end, then its result on the film's session and in the record of generations, under the run's lock."""
    store = storage()
    with connect() as conn:
        jobs.finish(conn, job['id'], status, result=result, error=error, cost=cost, retry_in=retry_in)
        if status not in ('ready', 'retained', 'failed', 'rejected'):
            return
        conn.execute('select pg_advisory_xact_lock(hashtextextended(%s, 0))', ('run:' + str(job['run_id']),))
        k = f"{job['run_id']}/visuals/session.json"
        session = json.loads(store.get(k).decode('utf-8'))
        entry = guide.apply_result(session, job, status, result or {}, error)
        if entry is None:
            return
        store.put(k, json.dumps(session, ensure_ascii=False, sort_keys=True).encode('utf-8'), 'application/json')
        generations.add(conn, job['run_id'], job['request']['shot_id'], guide.HOW, entry)
        if status in ('ready', 'retained') and (result or {}).get('key'):
            jobs.record_file(conn, job['run_id'], 'visuals', result['key'], Path(result['key']).name, result['sha256'], result['bytes'], 'image/png')


def guide_running(conn, kind):
    row = conn.execute("select count(*) as n from vw2_jobs where status='running' and provider='guide' and request->>'kind' = %s", (kind,)).fetchone()
    return (row['n'] if isinstance(row, dict) else row[0]) > 0


# hotfix (VW-24, 20 Nov 2026): a scene sent again for a shot replaces the one before it (`guide.apply_result` ignores the older result), so the
# older scene's check frames are not rendered at all. Said on the job; nothing is written to the run's log.
SUPERSEDED = 'superseded: a newer scene of this shot was sent; nothing to do'
# Release 2, the critic's point 1: the older scene's queued guide render too (16 minutes, one lane). A job is replaced when a guide-frames job of the
# same run and shot was created after it (a newer scene was sent); a scene sent again later gets a fresh render at its pass, newer than every frames job.
# Release 4: the queued first frame of the older scene too.
SUPERSEDE = ("update vw2_jobs j set status='failed', error=%s, updated_at=now() where j.provider='guide' and j.status='queued' and j.request->>'kind' in ('guide-frames','guide-frame1','guide-render') "
             "and exists (select 1 from vw2_jobs n where n.run_id=j.run_id and n.unit=j.unit and n.provider='guide' and n.request->>'kind'='guide-frames' and n.created_at > j.created_at)")
# Release 4, the film in mid-step at the deploy: a video job queued by the older code (one job for the first frame and the video: its request has no
# `split`) gets a first-frame job of its own, once, so its still does not wait for its turn in the render lane. Kept until no such job is queued.
BACKFILL = ("insert into vw2_jobs(run_id, stage, unit, provider, request, request_id) "
            "select j.run_id, j.stage, j.unit, j.provider, jsonb_set(j.request, '{kind}', '\"guide-frame1\"'), gen_random_uuid() from vw2_jobs j "
            "where j.provider='guide' and j.status='queued' and j.request->>'kind'='guide-render' and not (j.request ? 'split') "
            "and not exists (select 1 from vw2_jobs n where n.run_id=j.run_id and n.unit=j.unit and n.provider='guide' and n.request->>'kind'='guide-frame1' "
            "and n.request->>'sha256'=j.request->>'sha256')")
BACKFILL_LOCK = "select pg_advisory_xact_lock(hashtext('vw2-guide-backfill'))"   # the critic's point 5 on release 4: workers tick at once; the second insert waits and sees the first's row


def tick():
    """A still first (a paid call, quick); then one quick Blender job (seconds to a minute; one at a time, in a lane of their own: hotfix of 20 Nov
    2026, the check frames waited 16 minutes behind each render): the first frame of a layout that passed (release 4), else the check frames of a
    scene; then one render, only when no other guide render runs and the drawn renders leave room."""
    from . import worker
    from .visual_workers import renders_free
    busy = False
    with connect() as conn:
        job = jobs.claim(conn, 'guide-still')
    if job:
        finish(job, *process(job))
        busy = True
    if worker.STOP:
        return busy
    with connect() as conn:
        conn.execute(SUPERSEDE, (SUPERSEDED,))
    try:   # in a transaction of its own: this statement was never run against a database in the tests; its fault must not stop the lanes
        with connect() as conn:
            conn.execute(BACKFILL_LOCK)
            conn.execute(BACKFILL)
    except Exception:
        import logging
        logging.getLogger('vw2.guide').exception('the first-frame jobs of older video jobs were not queued')
    with connect() as conn:
        quick = not guide_running(conn, 'guide-frame1') and not guide_running(conn, 'guide-frames')
        job = (jobs.claim(conn, 'guide', 'guide-frame1') or jobs.claim(conn, 'guide', 'guide-frames')) if quick else None
    if job:
        finish(job, *process(job, renew=lambda: worker.renew_lease(job['id'])))
        busy = True
    if worker.STOP:
        return busy
    with connect() as conn:
        conn.execute(SUPERSEDE, (SUPERSEDED,))   # again: a scene sent while the check frames above were rendered
        job = jobs.claim(conn, 'guide', 'guide-render') if not guide_running(conn, 'guide-render') and renders_free(conn, settings().MOTION_CAP) else None
    if job:
        finish(job, *process(job, renew=lambda: worker.renew_lease(job['id'])))
        busy = True
    return busy


# ---------- the frames of a take ----------
# design/223 (SK, 22 Nov 2026): nothing is measured on a take and nothing is set aside: every take goes to the operator as it is. The server only keeps
# frames of it, for the assistant to choose a correction's route and to place a cut; they are no check. (Until then: "real footage", "as long as the
# guide", "first frame matches the still" and "one continuous shot" were measured, the first three set a clip aside, and a scorecard was kept;
# design/35 rows 319 and 327.)

def frame_rate(value):
    """A file's frame rate as a number: ffprobe gives it as text like "24/1" (design/222: `float()` of that raised, and no sheet was ever made)."""
    from fractions import Fraction
    try:
        return float(Fraction(str(value))) or 24.0
    except (ValueError, ZeroDivisionError):
        return 24.0


FRAME_EVERY_S, FRAME_WIDTH = 0.5, 960   # the frames of a take: one every half second, the first and the last, this wide


def half_second_frames(video_path, seconds, folder):
    """The frames of a take: [(second, jpeg file)], one every FRAME_EVERY_S, then the last frame."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    ff = settings().FFMPEG_EXECUTABLE
    subprocess.run([ff, '-y', '-v', 'error', '-i', str(video_path), '-vf', f'fps={1 / FRAME_EVERY_S:g},scale={FRAME_WIDTH}:-2', '-q:v', '3', str(folder / 'h-%03d.jpg')], check=True, timeout=180)
    out = [(round(i * FRAME_EVERY_S, 1), p) for i, p in enumerate(sorted(folder.glob('h-*.jpg')))]
    last = folder / 'last.jpg'
    subprocess.run([ff, '-y', '-v', 'error', '-sseof', '-0.25', '-i', str(video_path), '-vf', f'scale={FRAME_WIDTH}:-2', '-q:v', '3', '-update', '1', str(last)], timeout=120)
    return out + ([(round(float(seconds), 1), last)] if last.is_file() and (not out or round(float(seconds), 1) > out[-1][0]) else [])


def take_frames(video_path, store, run_id, jid):
    """The frames of a take or of a version, stored beside it: the sheet at four a second and one frame every half second. Never raises: a fault
    here leaves the take without frames, said in `frames_error`; the take is shown all the same."""
    from . import drawn, motion
    from .visual_workers import probe
    out = {'guide': True, 'frames': [], 'sheet_key': None}
    try:
        ev = probe(video_path)
        fps = frame_rate(ev.get('fps'))
        n = max(1, int(round(ev['duration_seconds'] * fps)))
        idx = sorted(set(range(0, n, max(1, int(round(fps / 4))))) | {n - 1})
        sheet = drawn.sheet(motion.frames_png(video_path, idx), fps, ev.get('width') or 1280, ev.get('height') or 720)
        out['sheet_key'] = f'{run_id}/visuals/takes/{jid}-sheet-4fps.jpg'
        store.put(out['sheet_key'], sheet, 'image/jpeg')
        for at, path in half_second_frames(video_path, ev['duration_seconds'], Path(video_path).with_name('frames')):
            k = f'{run_id}/visuals/takes/{jid}-f-{int(round(at * 10)):04d}.jpg'
            store.put(k, path.read_bytes(), 'image/jpeg')
            out['frames'].append({'at_s': at, 'key': k})
    except Exception as exc:
        out['frames_error'] = f'{exc.__class__.__name__}: {str(exc)[:200]}'
    return out
