"""Voice and media stages on the operator machine.

voice: the model discusses voices with the operator using `vw voice catalog|preview|add-library|models`, then
`vw voice audition` (paid, informed) and `vw voice narrate` (paid, informed); `vw voice fetch` downloads the ready
narration and timing into out/; `vw stage voice record --quote` records the stage output.
media: clips in in/ are probed, hashed, deduplicated, uploaded with receipts, and recorded with analysis units."""
import hashlib
import json
import subprocess
from pathlib import Path

from stages_text import Refused, digest, read_proposal

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
    return {'duration_s': float(data['format'].get('duration') or 0), 'width': video[0].get('width'), 'height': video[0].get('height'),
            'codec': video[0].get('codec_name'), 'fps': video[0].get('avg_frame_rate'), 'has_audio': bool(audio)}


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
        clips.append({'id': sha[:16], 'name': p.name, 'sha256': sha, 'bytes': size, **probe(p)})
    (ws / 'work' / 'media-clips.json').write_text(json.dumps(clips), encoding='utf-8')
    return {'prompt': procedure.get('prompt') or '', 'clips': clips, 'duplicates_skipped': len(files) - len(clips),
            'output_file': 'out/media.json', 'steps': procedure.get('steps') or [], 'message': 'Confirm the clip list with the operator, then record.'}


def media_record(ws, procedure, prior, upload):
    try:
        clips = json.loads((ws / 'work' / 'media-clips.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        raise Refused('Run `vw stage media prepare` before record.')
    refs = []
    for c in clips:
        refs.append(upload('media', ws / 'in' / c['name'], c['sha256'], c['bytes']))  # skips files already receipted
    (ws / 'out' / 'media.json').write_text(json.dumps({'clips': clips}, indent=1), encoding='utf-8')
    summary = {'clips': [{k: c[k] for k in ('id', 'name', 'sha256', 'bytes', 'duration_s', 'has_audio')} for c in clips],
               'units': {'analysis': [c['id'] for c in clips]}, 'total_duration_s': round(sum(c['duration_s'] for c in clips), 1)}
    return {'files': ['out/media.json'], 'stored': refs, 'summary': summary, 'retain': True, 'upload': True}


# ---------- voice ----------

def voice_prepare(ws, procedure, prior):
    script = json.loads((ws / 'out' / 'script.json').read_text(encoding='utf-8'))
    return {'prompt': procedure.get('prompt') or '', 'steps': procedure.get('steps') or [],
            'inputs': {'spoken_text': script['spoken_text'], 'characters': len(script['spoken_text']), 'content_digest': script['content_digest'],
                       'passages': len(script['passages'])},
            'output_file': 'out/voice.json',
            'message': 'Agree a voice with the operator (catalog/preview/audition), narrate, fetch, then record.'}


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
             'settings': job['request']['settings'], 'duration_s': res.get('duration_s'), 'source_script': job['request']['source_script']}
    (ws / 'out' / 'voice.json').write_text(json.dumps(voice, indent=1), encoding='utf-8')
    stored = [{'name': 'narration.mp3', 'key': res['audio_key'], 'sha256': res['sha256'], 'bytes': res['bytes'], 'location': 'storage', 'receipt': True},
              {'name': 'timing.json', 'key': res['timing_key'], 'sha256': res['timing_sha256'], 'bytes': res['timing_bytes'], 'location': 'storage', 'receipt': True}]
    summary = {**voice, 'cost': job.get('cost'), 'content_digest': script['content_digest']}
    return {'files': ['out/voice.json'], 'stored': stored, 'summary': summary, 'retain': True, 'upload': True}
