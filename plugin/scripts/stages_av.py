"""Voice and media stages on the operator machine.

voice: the model discusses voices with the operator using `vw voice catalog|preview|add-library|models`, then
`vw voice audition` (paid, informed) and `vw voice narrate` (paid, informed); `vw voice fetch` downloads the ready
narration and timing into out/; `vw stage voice record --quote` records the stage output.
media: clips in in/ are probed, hashed, deduplicated, uploaded with receipts, and recorded with analysis units."""
import hashlib
import json
import subprocess
from pathlib import Path

from stages_text import Refused, digest, read_proposal, stamp, stamps

VIDEO_SUFFIXES = ('.mp4', '.mov', '.m4v', '.mkv', '.webm', '.avi', '.mpg', '.mpeg')
MAX_MEDIA_BYTES = 200 * 1024 * 1024


def probe(path):
    try:
        out = subprocess.run(['ffprobe', '-v', 'error', '-show_format', '-show_streams', '-of', 'json', str(path)], capture_output=True, check=True, timeout=60).stdout
        data = json.loads(out)
    except (OSError, subprocess.SubprocessError, ValueError):
        raise Refused(f'ffprobe could not read {path.name}. Install ffmpeg or check the file.')
    video = [s for s in data.get('streams', []) if s.get('codec_type') == 'video']
    audio = [s for s in data.get('streams', []) if s.get('codec_type') == 'audio']
    if not video:
        raise Refused(f'{path.name} has no video stream.')
    v = video[0]
    rotation = next((int(sd['rotation']) for sd in v.get('side_data_list') or [] if 'rotation' in sd), None)
    if rotation is None and (v.get('tags') or {}).get('rotate'):
        rotation = int(v['tags']['rotate'])
    rotation = (rotation or 0) % 360
    w, h = v.get('width'), v.get('height')
    if rotation in (90, 270):
        w, h = h, w  # displayed orientation; later stages use these
    return {'duration_s': float(data['format'].get('duration') or 0), 'width': w, 'height': h, 'stored_width': v.get('width'), 'stored_height': v.get('height'),
            'rotation_deg': rotation, 'codec': v.get('codec_name'), 'fps': v.get('avg_frame_rate'), 'r_frame_rate': v.get('r_frame_rate'),
            'is_variable_frame_rate': bool(v.get('r_frame_rate') and v.get('avg_frame_rate') and v['r_frame_rate'] != v['avg_frame_rate']),
            'color_transfer': v.get('color_transfer'), 'has_audio': bool(audio),
            'audio_channels': audio[0].get('channels') if audio else 0, 'audio_sample_rate_hz': int(audio[0]['sample_rate']) if audio and audio[0].get('sample_rate') else None,
            'creation_time': (data['format'].get('tags') or {}).get('creation_time')}


def to_cfr(src, dst, fps):
    """Blueprint edge rule 6: a variable-frame-rate source is transcoded to constant frame rate before anything downstream sees it."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', str(src), '-fps_mode', 'cfr', '-r', str(fps), '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p',
                        '-c:a', 'copy', '-movflags', '+faststart', str(dst)], check=True, capture_output=True, timeout=1800)
    except (OSError, subprocess.SubprocessError) as exc:
        detail = getattr(exc, 'stderr', b'') or b''
        raise Refused(f'{src.name} is variable frame rate and could not be converted: {detail.decode(errors="replace")[:300] or exc.__class__.__name__}')


# ---------- media ----------

def media_prepare(ws, procedure, prior):
    files = sorted(p for p in (ws / 'in').iterdir() if p.is_file() and p.suffix.lower() in VIDEO_SUFFIXES)
    if not files:
        raise Refused(f"Put the source clips in {ws / 'in'} (mp4/mov/mkv/webm…), then run prepare again.")
    clips, seen = [], {}
    for p in files:
        size = p.stat().st_size
        if size > MAX_MEDIA_BYTES:
            raise Refused(f'{p.name} is {size / 1e6:.0f} MB; the limit is 200 MB per clip. Ask the operator to trim or re-encode it.')
        sha = hashlib.sha256(p.read_bytes()).hexdigest()
        if sha in seen:
            continue  # duplicate content: listed once
        seen[sha] = p.name
        meta = probe(p)
        path = p
        if meta['is_variable_frame_rate']:
            from fractions import Fraction
            fps = round(float(Fraction(meta['r_frame_rate'])))
            path = ws / 'work' / 'cfr' / p.name
            to_cfr(p, path, fps)
            data = path.read_bytes()
            meta = {**probe(path), 'transcoded_from_vfr': True, 'original_sha256': sha, 'original_fps': meta['fps']}
            sha, size = hashlib.sha256(data).hexdigest(), len(data)
        clips.append({'id': sha[:16], 'name': p.name, 'path': str(path.relative_to(ws).as_posix()), 'sha256': sha, 'bytes': size, **meta})
    (ws / 'work' / 'media-clips.json').write_text(json.dumps(clips, indent=1), encoding='utf-8')
    return {'prompt': procedure.get('prompt') or '', 'clips': clips, 'duplicates_skipped': len(files) - len(clips), 'prepared_at': stamp(ws, 'media'),
            'output_file': 'out/media.json', 'steps': procedure.get('steps') or [], 'message': 'Confirm the clip list with the operator, then record.'}


def media_record(ws, procedure, prior, upload):
    try:
        clips = json.loads((ws / 'work' / 'media-clips.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        raise Refused('Run `vw stage media prepare` before record.')
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=3) as pool:   # design/19 C2: three uploads at a time; each keeps its own retry
        refs = list(pool.map(lambda c: upload('media', ws / c.get('path', 'in/' + c['name']), c['sha256'], c['bytes']), clips))  # skips files already receipted
    (ws / 'out' / 'media.json').write_text(json.dumps({'clips': clips}, indent=1), encoding='utf-8')
    summary = {'clips': [{k: c.get(k) for k in ('id', 'name', 'sha256', 'bytes', 'duration_s', 'has_audio', 'width', 'height', 'fps', 'rotation_deg', 'audio_channels', 'audio_sample_rate_hz', 'color_transfer', 'creation_time', 'transcoded_from_vfr')} for c in clips],
               'units': {'analysis': [c['id'] for c in clips]}, 'total_duration_s': round(sum(c['duration_s'] for c in clips), 1), **stamps(ws, 'media')}
    return {'files': ['out/media.json'], 'stored': refs, 'summary': summary, 'retain': True, 'upload': True}


# ---------- voice ----------

def voice_prepare(ws, procedure, prior):
    script = json.loads((ws / 'out' / 'script.json').read_text(encoding='utf-8'))
    return {'prompt': procedure.get('prompt') or '', 'steps': procedure.get('steps') or [],
            'inputs': {'spoken_text': script['spoken_text'], 'characters': len(script['spoken_text']), 'content_digest': script['content_digest'],
                       'passages': len(script['passages'])},
            'output_file': 'out/voice.json', 'prepared_at': stamp(ws, 'voice'),
            'message': 'Agree a voice with the operator (catalog/preview/audition), narrate, fetch, then record.'}


BREATHING_PAUSE_S = 0.8


def beat_durations(script, ws):
    """Blueprint Stage 0: measured narration per beat from the ElevenLabs word timing, plus the breathing pause. Frames are set at planning (timeline fps)."""
    try:
        timing = json.loads((ws / 'out' / 'timing.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        raise Refused('Run `vw voice fetch --job <id>` for the ready narration before record (timing.json missing).')
    words = timing.get('words') or []
    rows = []
    for b in script.get('beats') or []:
        own = [w for w in words if w['passage_id'] == b['passage_id']]
        if not own:
            raise Refused(f"Narration timing has no words for {b['beat_id']}; narrate the accepted script again.")
        measured = round(own[-1]['end_s'] - own[0]['start_s'], 3)
        rows.append({'beat_id': b['beat_id'], 'passage_id': b['passage_id'], 'start_s': own[0]['start_s'], 'end_s': own[-1]['end_s'], 'measured_vo_duration_s': measured,
                     'breathing_pause_s': BREATHING_PAUSE_S, 'target_beat_duration_s': round(measured + BREATHING_PAUSE_S, 3), 'words': len(own)})
    return rows


def voice_record(ws, procedure, prior, fetched):
    """fetched: the ready narration job (dict with result keys) saved by `vw voice fetch` into work/voice-fetched.json."""
    try:
        job = json.loads((ws / 'work' / 'voice-fetched.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        raise Refused('Run `vw voice fetch <job-id>` for the ready narration before record.')
    script = json.loads((ws / 'out' / 'script.json').read_text(encoding='utf-8'))
    if job['request']['source_script'] != script['content_digest']:
        raise Refused('The narration was generated for a different script version. Narrate again.')
    res = job['result']
    voice = {'job_id': job['id'], 'voice_id': job['request']['voice_id'], 'name': job['request']['name'], 'model_id': job['request']['model_id'],
             'settings': job['request']['settings'], 'duration_s': res.get('duration_s'), 'source_script': job['request']['source_script'],
             'beats': beat_durations(script, ws)}
    (ws / 'out' / 'voice.json').write_text(json.dumps(voice, indent=1), encoding='utf-8')
    stored = [{'name': 'narration.mp3', 'key': res['audio_key'], 'sha256': res['sha256'], 'bytes': res['bytes'], 'location': 'storage', 'receipt': True},
              {'name': 'timing.json', 'key': res['timing_key'], 'sha256': res['timing_sha256'], 'bytes': res['timing_bytes'], 'location': 'storage', 'receipt': True}]
    summary = {**voice, 'cost': job.get('cost'), 'content_digest': script['content_digest'], **stamps(ws, 'voice')}
    return {'files': ['out/voice.json'], 'stored': stored, 'summary': summary, 'retain': True, 'upload': True}
