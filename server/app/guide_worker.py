"""The worker side of the guide route (integration steps B to D, SK 12 Nov 2026): Blender renders on the server, the overlay of a still on its
guide frame, and the checks on a returned take that block it before anyone is shown it.

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
LENGTH_SLACK_S = 0.6        # a take is as long as its guide, give or take; double length is the guide followed by new footage
SAME_AS_GUIDE = 0.04        # mean difference of small grey frames, 0 to 1, under which the clip is the guide itself; set on our own runs' box guides
# hotfix (SK, 21 Nov 2026: "the upper limit as 30% shift and 30% zoom so that this doesn't initiate any retakes"): the take's first frame against
# the still. (Until then 3 % of the width and 3 % of zoom, "starting values at 720p": on VW-24 they set aside 8 of 18 takes, at 0.8 to 6.7 %.)
FIRST_FRAME_SHIFT, FIRST_FRAME_ZOOM = 0.30, 0.30


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


# ---------- the checks on a returned take that block it (step D) ----------

def _grey(im):
    from .image_check import ALIGN_H, ALIGN_W
    return im.convert('L').resize((ALIGN_W, ALIGN_H), Image.BILINEAR)


def length_line(take_seconds, guide_seconds):
    ok = abs(float(take_seconds) - float(guide_seconds)) <= LENGTH_SLACK_S
    return {'check': 'as long as the guide', 'weight': 'must', 'pass': ok, 'pass_when': 'the clip is as long as its guide',
            'seen': f'the clip is {float(take_seconds):.1f} s, the guide {float(guide_seconds):.1f} s' + ('' if ok else ' (the guide followed by new footage comes back at double length)')}


def same_line(take_frames, guide_frames):
    import numpy as np
    pairs = list(zip(take_frames, guide_frames))
    diff = float(np.mean([np.abs(np.asarray(a, dtype=float) - np.asarray(b, dtype=float)).mean() for a, b in pairs])) / 255 if pairs else 1.0
    ok = diff > SAME_AS_GUIDE
    return {'check': 'real footage', 'weight': 'must', 'pass': ok, 'pass_when': 'the clip is new footage, not the box guide sent back',
            'seen': f'the clip differs from its guide by {diff * 100:.1f} % on {len(pairs)} frames' + ('' if ok else ': it is the guide itself, unedited'), 'difference': round(diff, 4)}


def first_frame_line(first, still):
    import numpy as np
    from . import image_check as IC
    a, b = _grey(first), _grey(still)
    m = IC._match(IC._fft(np.asarray(a, dtype=float)), lambda z, im=b: IC._scaled(im, z))
    ok = round(m['shift'], 4) <= FIRST_FRAME_SHIFT and round(abs(m['scale'] - 1), 4) <= FIRST_FRAME_ZOOM   # rounded: exactly at the limit is within it
    return {'check': 'first frame matches the still', 'weight': 'must', 'pass': ok, 'pass_when': "the take's first frame is the still: nothing moved, nothing pushed in",
            'seen': f"shifted {m['shift'] * 100:.1f} % of the width, zoom {abs(m['scale'] - 1) * 100:.1f} %" + ('' if ok else ': the fault is before the video, in the still or the guide; look at the overlay'),
            'shift_pct': round(m['shift'] * 100, 2), 'zoom_pct': round(abs(m['scale'] - 1) * 100, 2)}


def frame_rate(value):
    """A file's frame rate as a number: ffprobe gives it as text like "24/1" (design/222: `float()` of that raised, and no sheet was ever made)."""
    from fractions import Fraction
    try:
        return float(Fraction(str(value))) or 24.0
    except (ValueError, ZeroDivisionError):
        return 24.0


JUMP_SCORE = 0.25   # ffmpeg's scene score between two neighbouring frames above which the picture has jumped to another view; on VW-12's 17 takes it marks exactly the three with a jump (0.51 to 0.60) and no other
FRAME_EVERY_S, FRAME_WIDTH = 0.5, 960   # design/222: the frames Claude judges a take from: one every half second, the first and the last, this wide


def jumps(video_path):
    """The seconds at which the picture jumps to another view (a sudden change between two neighbouring frames), measured from the file."""
    import re
    r = subprocess.run([settings().FFMPEG_EXECUTABLE, '-hide_banner', '-i', str(video_path), '-vf', f"select='gt(scene,{JUMP_SCORE})',metadata=print", '-an', '-f', 'null', '-'],
                       capture_output=True, timeout=120)
    if r.returncode:   # a measurement that did not run is never read as "no jump": the line is left out
        raise RuntimeError('ffmpeg: ' + r.stderr.decode('utf-8', 'replace')[-200:])
    return [float(x) for x in re.findall(r'pts_time:([0-9.]+)', r.stderr.decode('utf-8', 'replace'))]


def continuous_line(at):
    """design/222: one continuous shot, measured. It marks the take's line; the take is not set aside."""
    line = {'check': 'one continuous shot', 'weight': 'must', 'pass': not at, 'pass_when': 'the clip is one shot from its first frame to its last: the picture never jumps to another view',
            'seen': 'no jump to another view' if not at else 'the picture jumps to another view at ' + ' and at '.join(f'{t:.1f} s' for t in at[:4])}
    return {**line, 'at_s': round(at[0], 1)} if at else line


def half_second_frames(video_path, seconds, folder):
    """The frames Claude judges the take from: [(second, jpeg file)], one every FRAME_EVERY_S, then the last frame."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    ff = settings().FFMPEG_EXECUTABLE
    subprocess.run([ff, '-y', '-v', 'error', '-i', str(video_path), '-vf', f'fps={1 / FRAME_EVERY_S:g},scale={FRAME_WIDTH}:-2', '-q:v', '3', str(folder / 'h-%03d.jpg')], check=True, timeout=180)
    out = [(round(i * FRAME_EVERY_S, 1), p) for i, p in enumerate(sorted(folder.glob('h-*.jpg')))]
    last = folder / 'last.jpg'
    subprocess.run([ff, '-y', '-v', 'error', '-sseof', '-0.25', '-i', str(video_path), '-vf', f'scale={FRAME_WIDTH}:-2', '-q:v', '3', '-update', '1', str(last)], timeout=120)
    return out + ([(round(float(seconds), 1), last)] if last.is_file() and (not out or round(float(seconds), 1) > out[-1][0]) else [])


def blocked_by(lines):
    """Why a clip is not shown as a take, in the operator's words; None when it may be shown."""
    failed = {l['check']: l for l in lines if l.get('pass') is False}
    if 'real footage' in failed:
        return 'the guide came back unedited'
    if 'as long as the guide' in failed:
        return failed['as long as the guide']['seen']
    if 'first frame matches the still' in failed:
        return 'the first frame does not match the still (' + failed['first frame matches the still']['seen'].split(':')[0] + ')'
    return None


def released(rec):
    """Hotfix (21 Nov 2026): a take's check record written under the older first-frame limits, brought to today's: when the take was set aside
    for its first frame only and its measured shift and zoom are within the limits, the line passes, the block is gone and the scorecard is
    rebuilt (Claude's look, when one is there, is kept in it). Returns whether the record changed. Nothing else of the record is touched."""
    lines = rec.get('code_lines') or []
    line = next((l for l in lines if l.get('check') == 'first frame matches the still'), None)
    if not line or line.get('pass') is not False or blocked_by(lines) != rec.get('blocked'):
        return False
    if any(l.get('pass') is False for l in lines if l is not line) or line.get('shift_pct') is None or line.get('zoom_pct') is None:
        return False
    if line['shift_pct'] / 100 > FIRST_FRAME_SHIFT or line['zoom_pct'] / 100 > FIRST_FRAME_ZOOM:
        return False
    line.update({'pass': True, 'seen': str(line.get('seen') or '').split(':')[0]})
    rec['blocked'] = None
    rec['scorecard'], rec['watch'] = scorecard(lines, rec.get('look'))
    return True


SCORECARD = ('real footage and length', 'first frame', 'one continuous shot', 'people', 'the action', 'objects', 'bodies and contact', 'the place and the light')   # design/222: "the join" is retired (the page's film order is how it is judged); one continuous shot is measured


def scorecard(code_lines, reading):
    """The lines of the review, each Pass, Fail or Not sure, with one thing to watch and the second it happens. Not sure is never rounded up.
    design/222: `reading` is Claude's look from frames ({lines: [{check, pass, seen, at_s}]}), None before it comes."""
    by = {l['check']: l for l in code_lines}
    read = {l['check']: l for l in (reading or {}).get('lines') or []}

    def state(*ls):
        if any(l is None or l.get('pass') is None for l in ls):
            return 'Not sure'
        if any(l['pass'] == 'na' for l in ls):   # release 1, A3 (visuals_stage.NA): the line does not apply to this take: never a fail, never a pass
            return 'Does not apply'
        return 'Pass' if all(l['pass'] for l in ls) else 'Fail'
    rows = [{'line': 'real footage and length', 'state': state(by.get('real footage'), by.get('as long as the guide')), 'seen': '; '.join(l['seen'] for l in (by.get('real footage'), by.get('as long as the guide')) if l)},
            {'line': 'first frame', 'state': state(by.get('first frame matches the still')), 'seen': (by.get('first frame matches the still') or {}).get('seen', '')}]
    if by.get('one continuous shot'):
        rows.append({'line': 'one continuous shot', 'state': state(by['one continuous shot']), 'seen': by['one continuous shot'].get('seen', ''), 'at_s': by['one continuous shot'].get('at_s')})
    for name in SCORECARD[3:]:
        l = read.get(name)
        rows.append({'line': name, 'state': state(l), 'seen': (l or {}).get('seen') or ('not read' if not l else ''), 'at_s': (l or {}).get('at_s')})
    worst = next((r for r in rows if r['state'] == 'Fail'), None) or next((r for r in rows if r['line'] in SCORECARD[3:] and r['state'] == 'Not sure'), None)
    watch = {'line': worst['line'], 'what': worst['seen'], 'at_s': worst.get('at_s')} if worst else {'line': 'the action', 'what': 'the one action of the shot, from its first move to its last', 'at_s': None}
    return rows, watch


def take_checks(snapshot, video_path, store, run_id, jid, reading):
    """Everything a guide take is checked for in code, the sheets the operator looks at, and the scorecard. Never raises: a fault here is 'not checked', said so."""
    from . import drawn, motion
    from .image_check import _frames
    from .visual_workers import probe
    lines, out = [], {'guide': True}
    try:
        ev = probe(video_path)
        lines.append(length_line(ev['duration_seconds'], snapshot['guide']['seconds']))
        guide_path = Path(video_path).with_name('guide.mp4')
        guide_path.write_bytes(store.get(snapshot['guide']['key']))
        take_frames = _frames(video_path, per_second=1, limit=8)
        lines.append(same_line(take_frames, _frames(guide_path, per_second=1, limit=8)))
        still = Image.open(BytesIO(store.get(snapshot['start_image']['key'])))
        first_png = motion.frames_png(video_path, [0])[0]
        first = Image.open(BytesIO(first_png))
        lines.append(first_frame_line(first, still))
        try:   # design/222: one continuous shot, measured; a fault here leaves the line out, never the take
            lines.append(continuous_line(jumps(video_path)))
        except Exception:
            pass
        fps = frame_rate(ev.get('fps'))
        n = max(1, int(round(ev['duration_seconds'] * fps)))
        idx = sorted(set(range(0, n, max(1, int(round(fps / 4))))) | {n - 1})
        sheet = drawn.sheet(motion.frames_png(video_path, idx), fps, ev.get('width') or 1280, ev.get('height') or 720)
        out['sheet_key'] = f'{run_id}/visuals/takes/{jid}-sheet-4fps.jpg'
        store.put(out['sheet_key'], sheet, 'image/jpeg')
        pair = Image.new('RGB', (1280, 360), (20, 20, 20))
        pair.paste(first.convert('RGB').resize((640, 360), Image.LANCZOS), (0, 0))
        pair.paste(still.convert('RGB').resize((640, 360), Image.LANCZOS), (640, 0))
        buf = BytesIO()
        pair.save(buf, format='JPEG', quality=88)
        out['pair_key'] = f'{run_id}/visuals/takes/{jid}-first-frame-and-still.jpg'
        store.put(out['pair_key'], buf.getvalue(), 'image/jpeg')
        out['frames'] = []   # design/222: what Claude judges the take from, stored beside it
        for at, path in half_second_frames(video_path, ev['duration_seconds'], Path(video_path).with_name('frames')):
            k = f'{run_id}/visuals/takes/{jid}-f-{int(round(at * 10)):04d}.jpg'
            store.put(k, path.read_bytes(), 'image/jpeg')
            out['frames'].append({'at_s': at, 'key': k})
    except Exception as exc:
        out['code_error'] = f'{exc.__class__.__name__}: {str(exc)[:200]}'
    out['blocked'] = blocked_by(lines) or ('the checks could not be run (' + out['code_error'] + ')' if out.get('code_error') and len([l for l in lines if l['check'] != 'one continuous shot']) < 3 else None)
    out['code_lines'] = lines
    out['scorecard'], out['watch'] = scorecard(lines, reading)
    out['not_read'] = bool((reading or {}).get('error')) or not (reading or {}).get('lines')
    return out
