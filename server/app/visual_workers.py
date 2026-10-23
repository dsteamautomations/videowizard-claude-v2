"""Worker branches for the visuals stage: OpenAI image generation/edits and video takes (Google Omni / Higgsfield).

Rules kept from v1: write the intent before the one paid submit; never replay a dispatched submit; poll with backoff
and one row update per state change; retain the exact provider output; ffprobe evidence with the 1 ms timing check."""
import base64
import hashlib
import json
import os
import subprocess
import tempfile
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path

import httpx
from psycopg.types.json import Jsonb

from . import jobs
from .config import settings
from .db import connect
from .errors import Problem
from .storage import storage
from .video_providers import Provider

SPOOL = Path(os.environ.get('VW2_SPOOL') or Path(__file__).resolve().parents[1] / '.spool')

# Tests swap these; production uses the real clients.
openai_client = None   # callable(path, multipart|json) -> httpx.Response
provider_factory = Provider


def durable(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_bytes(data)
    os.replace(tmp, path)


# ---------- OpenAI images ----------

def _openai(path, **kw):
    if openai_client:
        return openai_client(path, **kw)
    key = settings().OPENAI_API_KEY.get_secret_value()
    if not key:
        raise Problem(503, 'IMAGE_CONFIGURATION', 'Configure VW2_OPENAI_API_KEY on the server.')
    return httpx.post('https://api.openai.com/v1' + path, headers={'Authorization': 'Bearer ' + key}, timeout=300, **kw)


def process_image(job):
    """Returns (status, result, error, cost, retry_in)."""
    req, jid = job['request'], str(job['id'])
    store = storage()
    raw_path = SPOOL / f'{jid}.image.json'
    dispatched = False
    try:
        if not raw_path.exists():
            dispatched = True
            if req['op'] == 'generate':
                r = _openai('/images/generations', json={'model': req['model'], 'prompt': req['prompt'], 'size': req['size'], 'quality': req['quality'], 'output_format': 'png', 'n': 1})
            else:
                files = [('image[]', (p['id'] + '.png', store.get(p['key']), 'image/png')) for p in req['parents']]
                r = _openai('/images/edits', data={'model': req['model'], 'prompt': req['prompt'], 'size': req['size'], 'quality': req['quality']}, files=files)
            if r.status_code == 404 or (r.status_code == 400 and 'model' in r.text.lower() and 'not' in r.text.lower()):
                return 'rejected', {'failure': 'MODEL_UNAVAILABLE', 'http_status': r.status_code}, f"OpenAI reports the model {req['model']} is unavailable on this account.", None, None
            if r.status_code >= 500 or r.status_code == 429:   # design/82 U3: back to the queue 1, 2 then 4 minutes later; the fourth attempt is rejected
                attempt = job.get('attempt') or 1
                if attempt < 4:
                    return 'queued', {'failure': 'provider', 'http_status': r.status_code}, f'OpenAI returned HTTP {r.status_code}; attempt {attempt + 1} of 4 in {2 ** (attempt - 1)} min.', None, 2 ** (attempt - 1)
                return 'rejected', {'failure': 'provider', 'http_status': r.status_code}, f'OpenAI returned HTTP {r.status_code} on {attempt} attempts; no further retry.', None, None
            if r.status_code >= 400:
                result, error = refusal(r)
                return 'failed', result, error, None, None
            durable(raw_path, r.content)
        body = json.loads(raw_path.read_text(encoding='utf-8'))
        png = base64.b64decode(body['data'][0]['b64_json'])
        from PIL import Image
        from io import BytesIO
        with Image.open(BytesIO(png)) as im:
            width, height = im.size
            if im.format != 'PNG':
                out = BytesIO()
                im.convert('RGB').save(out, format='PNG')
                png = out.getvalue()
        ref = req['reference']
        k = f"{job['run_id']}/visuals/references/{ref['id']}.png"
        store.put(k, png, 'image/png')
        sha = hashlib.sha256(png).hexdigest()
        usage = body.get('usage') or {}
        cost = {'model': req['model'], 'quality': req['quality'], 'size': req['size'], 'input_tokens': usage.get('input_tokens'), 'output_tokens': usage.get('output_tokens')}
        return 'retained', {'key': k, 'sha256': sha, 'bytes': len(png), 'width': width, 'height': height, 'revised_prompt': body['data'][0].get('revised_prompt'), 'cost': cost}, None, cost, None
    except (Problem, OSError, ValueError, KeyError, TypeError, httpx.RequestError) as exc:
        if raw_path.exists():
            return 'storage_pending', {'phase': 'store'}, f'Image saved locally; storage will be retried ({exc.__class__.__name__}).', None, 10
        if dispatched:
            return 'submission_unknown', {'phase': 'generate'}, f'Outcome unknown after dispatch ({exc.__class__.__name__}).', None, None
        return 'failed', {'phase': 'prepare'}, (exc.message if isinstance(exc, Problem) else f'{exc.__class__.__name__}: {exc}'), None, None


def refusal(r):
    """design/71 P5: a refused picture says why. OpenAI's error body names a moderation block (with its stage and categories) or a user error;
    anything else keeps the plain message. Returns (result, error)."""
    try:
        err = (r.json() or {}).get('error') or {}
    except ValueError:
        err = {}
    kind = err.get('type') or err.get('code') or ''
    result = {'failure': kind if kind in ('moderation_blocked', 'image_generation_user_error') else 'provider', 'http_status': r.status_code, 'detail': r.text[:300]}
    if kind == 'moderation_blocked':
        stage = err.get('moderation_stage') or 'unknown'
        cats = ', '.join(err.get('categories') or []) or 'no category given'
        return result, (f'OpenAI refused the pictures or the prompt (moderation, stage {stage}, {cats}). A frame with a recognisable face cannot be edited: '
                        'use it as a look reference only, pick a frame without a face, or change the prompt.')
    if kind == 'image_generation_user_error':
        return result, f"OpenAI refused the request: the prompt or the pictures are the problem; do not resend unchanged. ({err.get('message') or r.text[:120]})"
    return result, f'OpenAI rejected the request (HTTP {r.status_code}).'


def apply_image_result(conn, run_id, ref, status, result, error, cost):
    """A finished image job's outcome on its reference: retained → candidate, rejected/failed → failed. Returns True when it changed."""
    if status == 'retained':
        ref.update(status='candidate', key=result['key'], sha256=result['sha256'], bytes=result['bytes'], width=result['width'], height=result['height'])
        ref['generation'] = {**ref.get('generation', {}), 'cost': cost, 'revised_prompt': result.get('revised_prompt')}
        jobs.record_file(conn, run_id, 'visuals', result['key'], Path(result['key']).name, result['sha256'], result['bytes'], 'image/png')
        return True
    if status in ('rejected', 'failed'):
        ref.update(status='failed', error=error)
        return True
    return False


def finalize_image(conn, job, status, result, error, cost, retry_in):
    jobs.finish(conn, job['id'], status, result=result, error=error, cost=cost, retry_in=retry_in)
    # Ticket 9 (16 Oct 2026): this read-modify-write raced the server and the other workers, and two finished images were lost.
    # The same per-run lock every server write takes serialises it; it is held until this transaction ends.
    conn.execute('select pg_advisory_xact_lock(hashtextextended(%s, 0))', ('run:' + str(job['run_id']),))
    store = storage()
    k = f"{job['run_id']}/visuals/session.json"
    try:
        session = json.loads(store.get(k).decode('utf-8'))
    except Problem:
        return
    ref = session['references'].get(job['request']['reference']['id'])
    if ref and apply_image_result(conn, job['run_id'], ref, status, result, error, cost):
        if status == 'retained' and ((ref.get('answer') or {}).get('checklist') or ref.get('server_checklist')):   # design/86 K2: the check before the operator sees it
            from . import image_check
            from .analysis_jobs import transport_factory
            ref['check'] = image_check.run_check(store, session, ref, result, transport_factory)
        store.put(k, json.dumps(session, ensure_ascii=False, sort_keys=True).encode('utf-8'), 'application/json')
        if status == 'retained' and (ref.get('check') or {}).get('must_failed'):
            from . import image_check
            image_check.queue_fix(conn, store, job['run_id'], ref['id'])


# ---------- video takes ----------

def timing_evidence(duration_s, placement_exact):
    """design/45 10.6: a take at least as long as its placement matches (assembly trims); a shorter one is reported with its shortfall."""
    duration, placement = Fraction(str(duration_s)), Fraction(str(placement_exact))
    matches = duration >= placement - Fraction(1, 1000)
    return {'timing_matches_placement': bool(matches), 'shortfall_seconds': 0.0 if matches else round(float(placement - duration), 3)}


def backoff_minutes(polls):
    """design/45 10.5: 30 s after the first poll, then every minute (was up to 5 minutes)."""
    return min(1, 0.5 * polls)


def probe(path):
    out = subprocess.run([settings().FFPROBE_EXECUTABLE, '-v', 'error', '-show_format', '-show_streams', '-of', 'json', str(path)], capture_output=True, check=True, timeout=60).stdout
    data = json.loads(out)
    video = [s for s in data['streams'] if s.get('codec_type') == 'video']
    v = video[0]
    rotation = next((int(sd['rotation']) for sd in v.get('side_data_list') or [] if 'rotation' in sd), 0) % 360
    return {'duration_seconds': float(data['format']['duration']), 'width': v.get('width'), 'height': v.get('height'), 'fps': v.get('avg_frame_rate'),
            'has_audio': any(s.get('codec_type') == 'audio' for s in data['streams']),
            'color_transfer': v.get('color_transfer'), 'color_primaries': v.get('color_primaries'), 'rotation_deg': rotation,   # design/46 11.2: assembly reads these, no download
            'issues': ([] if v.get('color_transfer') and v.get('color_primaries') else ['colour untagged']) + (['rotation metadata'] if rotation else [])}


def take_cost(snapshot, result):
    """design/82 U5: the seconds, and the provider's usage when its result carries one."""
    return {'provider': snapshot['provider'], 'model': snapshot['model'], 'seconds': snapshot['duration_seconds'],
            **({'usage': result['usage']} if isinstance((result or {}).get('usage'), dict) else {})}


def process_take(job):
    """Submit once, poll, retain. Returns (status, result, error, cost, retry_in) where status 'submitted' means poll again later."""
    req, jid = job['request'], str(job['id'])
    store = storage()
    folder = SPOOL / jid
    intent, response_path, video_path = folder / 'attempt.json', folder / 'response.json', folder / 'output.mp4'
    snapshot = json.loads(store.get(req['request_key']).decode('utf-8'))
    remote = (job.get('result') or {}).get('provider_id')
    attempted = intent.exists() or remote is not None
    try:
        provider = provider_factory(snapshot['provider'])
        provider.model = snapshot['model']
        result = json.loads(response_path.read_text(encoding='utf-8'))['result'] if response_path.exists() else None
        if result is not None and not remote:
            remote = provider.identity(result)
        if not remote and not attempted:
            wire = provider.build(snapshot, store)
            durable(intent, json.dumps({'preparation_id': req['preparation_id'], 'at': datetime.now(timezone.utc).isoformat()}).encode())
            attempted = True
            result = provider.submit(wire, jid)
            durable(response_path, json.dumps({'preparation_id': req['preparation_id'], 'result': result}).encode())
            remote = provider.identity(result)
            receipt_key = f"{job['run_id']}/visuals/takes/{jid}.submission.json"
            store.put(receipt_key, response_path.read_bytes(), 'application/json')
        elif not remote:
            return 'submission_unknown', {'phase': 'submit'}, 'No provider identity is retained for a dispatched submit; recover or resolve, never resubmit automatically.', None, None
        if result is None or provider.state(result) == 'in_progress':
            result = provider.poll(remote)
            durable(response_path, json.dumps({'preparation_id': req['preparation_id'], 'provider_id': remote, 'result': result}).encode())
        state = provider.state(result)
        if state == 'in_progress':
            polls = ((job.get('result') or {}).get('polls') or 0) + 1
            return 'submitted', {'provider_id': remote, 'polls': polls}, None, None, backoff_minutes(polls)
        if state != 'completed':
            return ('cancelled' if state in ('canceled', 'cancelled') else 'failed'), {'provider_id': remote, 'provider_status': state}, f'Provider reported {state}. No automatic regeneration.', None, None
        data = video_path.read_bytes() if video_path.exists() else provider.output(result)
        if not data:
            raise ValueError('Empty provider output.')
        durable(video_path, data)
        sha = hashlib.sha256(data).hexdigest()
        k = f"{job['run_id']}/visuals/takes/{jid}.mp4"
        store.put(k, data, 'video/mp4')
        evidence = probe(video_path)
        placement = snapshot['placement']
        evidence.update(requested_duration_seconds=snapshot['duration_seconds'], placement=placement, creative_approval=False,
                        **timing_evidence(evidence['duration_seconds'], placement['duration_seconds']))
        cost = take_cost(snapshot, result)
        return 'ready', {'provider_id': remote, 'key': k, 'sha256': sha, 'bytes': len(data), 'evidence': evidence}, None, cost, None
    except (Problem, ValueError, KeyError, TypeError, OSError, subprocess.SubprocessError) as exc:
        rejected = isinstance(exc, Problem) and exc.code == 'VIDEO_REJECTED'
        if not attempted or rejected:
            return 'failed', {'phase': 'submit'}, ('Provider rejected the request; inspect the saved attempt before another authorized take.' if rejected else f'Preparation failed ({exc.__class__.__name__}: {exc}).'), None, None
        if remote or video_path.exists():
            return 'storage_pending', {'provider_id': remote, 'phase': 'retain'}, f'Retained response/output pending storage ({exc.__class__.__name__}).', None, 10
        return 'submission_unknown', {'phase': 'submit'}, 'Provider acceptance is unknown. Reconcile the retained attempt before any replacement.', None, None


def claim_take(conn):
    return conn.execute('''update vw2_jobs set status = case when status in ('queued','submitted') then 'running' else status end, lease_until = now() + interval '20 minutes',
                           attempt = attempt + 1, updated_at = now()
                           where id = (select id from vw2_jobs where provider='video' and (status='queued' or (status in ('submitted','storage_pending') and (lease_until is null or lease_until < now())))
                                       order by created_at limit 1 for update skip locked) returning *''').fetchone()


def tick():
    busy = False
    with connect() as conn:
        job = jobs.claim(conn, 'openai')
    if job:
        outcome = process_image(job)
        with connect() as conn:
            finalize_image(conn, job, *outcome)
        busy = True
    from . import worker
    if worker.STOP:
        return busy
    with connect() as conn:
        job = claim_take(conn)
    if job:
        status, result, error, cost, retry_in = process_take(job)
        with connect() as conn:
            prior = (job.get('result') or {})
            jobs.finish(conn, job['id'], status, result={**prior, **(result or {})}, error=error, cost=cost, retry_in=retry_in)
            if status == 'ready':
                jobs.record_file(conn, job['run_id'], 'visuals', result['key'], Path(result['key']).name, result['sha256'], result['bytes'], 'video/mp4')
        busy = True
    return busy
