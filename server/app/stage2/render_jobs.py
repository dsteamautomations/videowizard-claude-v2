"""Worker branch for stage 2 renders (provider 'render'): download sources once per sha, render with FFmpeg, upload the film with a receipt."""
import hashlib
import json
import os
import tempfile
from pathlib import Path

from .. import jobs
from ..db import connect
from ..errors import Problem
from ..storage import storage
from . import render as R

CACHE = Path(os.environ.get('VW2_SPOOL') or Path(__file__).resolve().parents[2] / '.spool') / 'render'


def _source(store, run_id, clip, folder):
    """Download a source once per sha into the render cache: a media clip by name, or any file by key (takes, assets)."""
    p = CACHE / 'sources' / f"{clip['sha256'][:24]}{Path(clip['name']).suffix}"
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        data = store.get(clip['key'] if clip.get('key') else f"{run_id}/media/{clip['name']}")
        if hashlib.sha256(data).hexdigest() != clip['sha256']:
            raise Problem(409, 'RENDER_SOURCE', f"Stored clip {clip['name']} differs from the media record.")
        tmp = p.with_suffix(p.suffix + '.tmp')
        tmp.write_bytes(data)
        os.replace(tmp, p)
    return p


def process(job):
    store = storage()
    req = job['request']
    plan = json.loads(store.get(req['plan_key']).decode('utf-8'))
    work = CACHE / str(job['id'])
    work.mkdir(parents=True, exist_ok=True)
    try:
        sources = {}
        for item in plan['items']:
            if item['kind'] == 'event' and not item.get('gap'):
                sources[item['clip']['id']] = _source(store, job['run_id'], item['clip'], work)
            elif item['kind'] == 'still':
                sources[item['file']['sha256']] = _source(store, job['run_id'], {**item['file'], 'key': item['file']['key']}, work)
        narration = work / 'narration.mp3'
        narration.write_bytes(store.get(plan['narration_key']))
        items = [({'kind': 'slate', 'frames': it['timeline_frames'], 'lines': [f"GAP | {it['beat_id']} | {it['timeline_frames']} frames", 'to be filled by the visuals stage', '']} if it.get('gap') else it)
                 for it in plan['items']]
        film, record = R.render_film(plan['kind'], {'items': items}, sources, narration, work, plan['timeline'], plan.get('narration'))
        data = film.read_bytes()
        sha = hashlib.sha256(data).hexdigest()
        store.put(req['out_key'], data, 'video/mp4')
        if hashlib.sha256(store.get(req['out_key'])).hexdigest() != sha:
            raise Problem(502, 'STORAGE', 'Film read-back failed.')
        uploaded = []
        for nk, seg in record.pop('normalised_segments', []):
            blob = Path(seg).read_bytes()
            store.put(nk, blob, 'video/mp4')
            uploaded.append({'key': nk, 'sha256': hashlib.sha256(blob).hexdigest(), 'bytes': len(blob)})
        record['normalised'] = uploaded
        return 'ready', {'key': req['out_key'], 'sha256': sha, 'bytes': len(data), 'duration_s': record['duration_s'], 'record': record}, None
    except Problem as exc:
        return 'failed', {'phase': 'render'}, exc.message
    except (OSError, ValueError, KeyError) as exc:
        return 'failed', {'phase': 'render'}, f'{exc.__class__.__name__}: {exc}'


def tick():
    with connect() as conn:
        job = jobs.claim(conn, 'render')
    if not job:
        return False
    status, result, error = process(job)
    with connect() as conn:
        jobs.finish(conn, job['id'], status, result=result, error=error)
        if status == 'ready':
            jobs.record_file(conn, job['run_id'], job['stage'], result['key'], Path(result['key']).name, result['sha256'], result['bytes'], 'video/mp4')
    return True
