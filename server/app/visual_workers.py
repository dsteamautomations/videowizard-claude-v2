"""Worker branches for the visuals stage: OpenAI image generation/edits and video takes (Google Omni).

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
    """design/114 P2: the call through the key pool; a 429 or a revoked key cools it and the same request goes to the next key at once, within this attempt."""
    if openai_client:
        return openai_client(path, **kw)
    from . import keys
    tries = keys.each('openai', settings())
    if not tries:
        raise Problem(503, 'IMAGE_CONFIGURATION', 'Configure VW2_OPENAI_API_KEY on the server.')
    r = None
    for idx, key in tries:
        r = httpx.post('https://api.openai.com/v1' + path, headers={'Authorization': 'Bearer ' + key}, timeout=300, **kw)
        r.key_index = idx
        reason = keys.reason_of(r.status_code)
        if reason is None:
            return r
        keys.cool('openai', idx, reason)
    return r   # every key answered a limit: the last answer, so the job requeues as before (design/82 U3)


GEMINI_URL = 'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent'   # design/120


class _Answer:
    """A response-shaped object for the common path: OpenAI's {data: [{b64_json}], usage} made from Gemini's answer, or an error with the model's words."""

    def __init__(self, status_code, body, text=''):
        self.status_code, self._body, self.text = status_code, body, text or json.dumps(body)
        self.content = json.dumps(body).encode('utf-8')

    def json(self):
        return self._body


def _gemini_image(req, parents):
    """design/120: one picture from Gemini's image model through the key pool (the same cooling as _openai): the prompt and the pictures as parts, the
    aspect and the tier in imageConfig; the first image part comes back as OpenAI's shape so the rest of process_image is shared."""
    from . import keys
    tries = keys.each('gemini', settings())
    if not tries:
        raise Problem(503, 'IMAGE_CONFIGURATION', 'Configure VW2_GEMINI_API_KEY on the server.')
    size = req.get('size') if isinstance(req.get('size'), dict) else {}
    parts = []
    for k, (pid, png) in enumerate(parents, 1):
        parts += [{'text': f'Image {k}.'}, {'inlineData': {'mimeType': 'image/png', 'data': base64.b64encode(png).decode('ascii')}}]
    parts.append({'text': req['prompt']})
    payload = {'contents': [{'role': 'user', 'parts': parts}],
               'generationConfig': {'responseModalities': ['IMAGE'], 'imageConfig': {'aspectRatio': size.get('aspect') or '16:9', 'imageSize': str(size.get('tier') or settings().GEMINI_IMAGE_SIZE).upper()}}}
    r = None
    for idx, key in tries:
        r = httpx.post(GEMINI_URL.format(model=req['model']), headers={'x-goog-api-key': key, 'Content-Type': 'application/json'}, json=payload, timeout=300)
        reason = keys.reason_of(r.status_code)
        if reason is None:
            break
        keys.cool('gemini', idx, reason)
    else:
        out = _Answer(r.status_code, {'error': {'type': 'provider', 'message': r.text[:300]}}, r.text)   # every key answered a limit: the last answer, so the job requeues (design/82 U3)
        out.key_index = idx
        return out
    if r.status_code >= 400:
        out = _Answer(r.status_code, {'error': {'type': 'provider', 'message': r.text[:300]}}, r.text)
        out.key_index = idx
        return out
    body = r.json()
    cands = body.get('candidates') or []
    parts_out = ((cands[0].get('content') or {}).get('parts') or []) if cands else []
    image = next((p['inlineData'] for p in parts_out if isinstance(p, dict) and p.get('inlineData')), None)
    if not image:
        words = ' '.join(str(p.get('text') or '') for p in parts_out if isinstance(p, dict)).strip() or (body.get('promptFeedback') or {}).get('blockReason') or 'no image in the answer'
        out = _Answer(400, {'error': {'type': 'no_image', 'message': words}}, words)
        out.key_index = idx
        return out
    usage = body.get('usageMetadata') or {}
    out = _Answer(200, {'data': [{'b64_json': image['data']}], 'usage': {'input_tokens': usage.get('promptTokenCount'), 'output_tokens': usage.get('candidatesTokenCount')}})
    out.key_index = idx
    return out


def key_out_green(png):
    """design/120: a component made on chroma green (#00FF00) keyed to alpha: green pixels (hue near 1/3, saturated, bright) go transparent."""
    import numpy as np
    from PIL import Image
    from io import BytesIO
    with Image.open(BytesIO(png)) as im:
        rgb = im.convert('RGB')
        hsv = np.asarray(rgb.convert('HSV')).astype(int)
        h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
        green = (h > 60) & (h < 110) & (s > 90) & (v > 60)   # PIL's hue is 0..255; pure green is 85
        alpha = np.where(green, 0, 255).astype('uint8')
        out = Image.fromarray(np.dstack([np.asarray(rgb), alpha]), 'RGBA')
        buf = BytesIO()
        out.save(buf, format='PNG')
        return buf.getvalue()


def process_image(job):
    """Returns (status, result, error, cost, retry_in)."""
    req, jid = job['request'], str(job['id'])
    store = storage()
    raw_path = SPOOL / f'{jid}.image.json'
    dispatched = False
    try:
        if not raw_path.exists():
            dispatched = True
            if req.get('provider') == 'gemini':   # design/120
                r = _gemini_image(req, [(p['id'], store.get(p['key'])) for p in req.get('parents') or []])
            elif req['op'] == 'generate':
                r = _openai('/images/generations', json={'model': req['model'], 'prompt': req['prompt'], 'size': req['size'], 'quality': req['quality'], 'output_format': 'png', 'n': 1,
                                                         **({'background': req['background']} if req.get('background') else {})})   # design/117 P1: a component's transparent background
            else:
                files = [('image[]', (p['id'] + '.png', store.get(p['key']), 'image/png')) for p in req['parents']]
                if req.get('region'):   # design/111 F11: the edit is masked to its region
                    files.append(('mask', ('mask.png', region_mask(store.get(req['parents'][0]['key']), req['region']), 'image/png')))
                r = _openai('/images/edits', data={'model': req['model'], 'prompt': req['prompt'], 'size': req['size'], 'quality': req['quality'],
                                                   **({'background': req['background']} if req.get('background') else {})}, files=files)
            if r.status_code == 404 or (r.status_code == 400 and 'model' in r.text.lower() and 'not' in r.text.lower()):
                return 'rejected', {'failure': 'MODEL_UNAVAILABLE', 'http_status': r.status_code}, f"OpenAI reports the model {req['model']} is unavailable on this account.", None, None
            if r.status_code >= 500 or r.status_code == 429:   # design/82 U3: back to the queue 1, 2 then 4 minutes later; the fourth attempt is rejected
                attempt = job.get('attempt') or 1
                if attempt < 4:
                    return 'queued', {'failure': 'provider', 'http_status': r.status_code}, f'OpenAI returned HTTP {r.status_code}; attempt {attempt + 1} of 4 in {2 ** (attempt - 1)} min.', None, 2 ** (attempt - 1)
                return 'rejected', {'failure': 'provider', 'http_status': r.status_code}, f'OpenAI returned HTTP {r.status_code} on {attempt} attempts; no further retry.', None, None
            if r.status_code >= 400:
                result, error = refusal(r)
                if getattr(r, '_body', None) and (r._body.get('error') or {}).get('type') == 'no_image':   # design/120: Gemini answered in words, not a picture
                    result, error = {**result, 'failure': 'no_image'}, f"The model returned no picture: {(r._body.get('error') or {}).get('message')}"
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
        if req.get('chroma_key'):   # design/120: a component made on chroma green
            png = key_out_green(png)
        edit = None
        if req.get('region') and req.get('parents'):   # design/111 F11: the start copied back outside the region; how much the model changed there is kept
            png, edit = composite_back(store.get(req['parents'][0]['key']), png, req['region'])
            width, height = Image.open(BytesIO(png)).size
        ref = req['reference']
        k = f"{job['run_id']}/visuals/references/{ref['id']}.png"
        store.put(k, png, 'image/png')
        sha = hashlib.sha256(png).hexdigest()
        usage = body.get('usage') or {}
        if req.get('provider') == 'gemini':   # design/120: priced flat per picture plus its inputs
            cost = {'provider': 'gemini', 'model': req['model'], 'tier': str((req.get('size') or {}).get('tier') if isinstance(req.get('size'), dict) else '') or settings().GEMINI_IMAGE_SIZE,
                    'inputs': len(req.get('parents') or []), 'input_tokens': usage.get('input_tokens'), 'output_tokens': usage.get('output_tokens')}
        else:
            cost = {'model': req['model'], 'quality': req['quality'], 'size': req['size'], 'input_tokens': usage.get('input_tokens'), 'output_tokens': usage.get('output_tokens')}
        return 'retained', {'key': k, 'sha256': sha, 'bytes': len(png), 'width': width, 'height': height, 'revised_prompt': body['data'][0].get('revised_prompt'), 'cost': cost,
                            **({'key_index': r.key_index} if getattr(r, 'key_index', None) is not None else {}),   # design/114: which key, never the key
                            **({'edit': edit} if edit else {})}, None, cost, None
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


def region_mask(parent_png, region):
    """design/111 F11: a PNG the size of Image 1, opaque everywhere but the region (GPT Image edits where the mask is clear)."""
    from PIL import Image
    from io import BytesIO
    with Image.open(BytesIO(parent_png)) as im:
        w, h = im.size
    mask = Image.new('RGBA', (w, h), (0, 0, 0, 255))
    box = region_box(region, w, h)
    mask.paste((0, 0, 0, 0), box)
    out = BytesIO()
    mask.save(out, format='PNG')
    return out.getvalue()


def region_box(region, w, h):
    l, t = int(round(float(region['left']) * w)), int(round(float(region['top']) * h))
    return (l, t, min(w, int(round((float(region['left']) + float(region['width'])) * w))), min(h, int(round((float(region['top']) + float(region['height'])) * h))))


def composite_back(parent_png, result_png, region):
    """design/111 F11: the model's region pasted onto the start; the rest is the start, pixel for pixel. Returns (png, the edit record with how much the model
    had changed outside the region, in percent of the grey range)."""
    from PIL import Image, ImageChops, ImageStat
    from io import BytesIO
    with Image.open(BytesIO(parent_png)) as p, Image.open(BytesIO(result_png)) as r:
        parent, result = p.convert('RGB'), r.convert('RGB')
        if result.size != parent.size:
            result = result.resize(parent.size)
        box = region_box(region, *parent.size)
        diff = ImageChops.difference(parent, result)   # per channel, so a colour shift counts
        outside = Image.new('L', parent.size, 255)
        outside.paste(0, box)
        stat = ImageStat.Stat(diff, mask=outside)
        changed = round(sum(stat.mean) / 3 / 255 * 100, 1) if stat.count and stat.count[0] else 0.0
        out = parent.copy()
        out.paste(result.crop(box), box)
        buf = BytesIO()
        out.save(buf, format='PNG')
    return buf.getvalue(), {'region': region, 'outside_changed_pct': changed, 'composited': True}


def apply_image_result(conn, run_id, ref, status, result, error, cost):
    """A finished image job's outcome on its reference: retained → candidate, rejected/failed → failed. Returns True when it changed."""
    if status == 'retained':
        ref.update(status='candidate', key=result['key'], sha256=result['sha256'], bytes=result['bytes'], width=result['width'], height=result['height'], **({'edit': result['edit']} if result.get('edit') else {}))
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
    due = False
    if ref and apply_image_result(conn, job['run_id'], ref, status, result, error, cost):
        if status == 'retained' and ((ref.get('answer') or {}).get('checklist') or ref.get('server_checklist')):   # design/86 K2: the check before the operator sees it
            ref['check_pending'] = due = True   # design/92: checked after this transaction, with no lock held (check_image)
        store.put(k, json.dumps(session, ensure_ascii=False, sort_keys=True).encode('utf-8'), 'application/json')
    return due


def check_image(job, result):
    """design/92 (L60): the picture's check (Gemini, the light against the footage) runs with no lock held; the run's lock is taken only to save it
    (design/96 X1: a fix is made only on request). A picture changed meanwhile (rejected, or made by another job) keeps what it has. Never raises."""
    from . import image_check
    from .analysis_jobs import transport_factory
    store = storage()
    k, rid = f"{job['run_id']}/visuals/session.json", job['request']['reference']['id']
    try:
        session = json.loads(store.get(k).decode('utf-8'))
        record = image_check.run_check(store, session, session['references'][rid], result, transport_factory)
        with connect() as conn:
            conn.execute('select pg_advisory_xact_lock(hashtextextended(%s, 0))', ('run:' + str(job['run_id']),))
            session = json.loads(store.get(k).decode('utf-8'))
            ref = session['references'].get(rid)
            if not ref or ref.get('job_id') != str(job['id']) or ref.get('status') != 'candidate' or 'check' in ref:
                return
            ref['check'] = record
            ref.pop('check_pending', None)
            store.put(k, json.dumps(session, ensure_ascii=False, sort_keys=True).encode('utf-8'), 'application/json')
    except Exception:   # a picture is never held back by its check
        return


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


def check_take(job, result):
    """design/91 N3: the ready take read by Gemini before the operator watches it; the record on the session, under the run's lock. Never raises.
    ponytail: runs in the take worker (about a minute a take); a queue of its own if takes pile up behind it."""
    from . import image_check
    from .analysis_jobs import transport_factory
    store = storage()
    try:
        snapshot = json.loads(store.get(job['request']['request_key']).decode('utf-8'))
        record = image_check.run_take_check(snapshot, SPOOL / str(job['id']) / 'output.mp4', result['sha256'], transport_factory)
        with connect() as conn:
            conn.execute('select pg_advisory_xact_lock(hashtextextended(%s, 0))', ('run:' + str(job['run_id']),))
            k = f"{job['run_id']}/visuals/session.json"
            session = json.loads(store.get(k).decode('utf-8'))
            session.setdefault('take_checks', {})[str(job['id'])] = record
            store.put(k, json.dumps(session, ensure_ascii=False, sort_keys=True).encode('utf-8'), 'application/json')
    except Exception:   # a take is never held back by its check
        return


def process_drawn(job):
    """design/117 P3, P4: the shot's SVG scene checked by the rules and measured, rendered in Chromium, its contact sheet read by Gemini against the shot's
    lines with the style and the shot's pictures, the SVG corrected and rendered again up to DRAWN_PASSES times, the best pass kept (fewest must failures).
    Free (no video provider). Returns (status, result, error, cost, retry_in)."""
    from . import drawn, image_check, svg_scene
    from .analysis_jobs import transport_factory
    req, jid = job['request'], str(job['id'])
    store = storage()
    folder = SPOOL / jid
    try:
        request = json.loads(store.get(req['request_key']).decode('utf-8'))
        svg0 = store.get(request['svg_key']).decode('utf-8')
        images = {rid: ('image/png', store.get(k)) for rid, k in (request.get('images') or {}).items()}
        fonts = {'Noto Sans': drawn.font_file().read_bytes()}
        if request.get('font_key'):
            fonts[request.get('font_name') or 'Brand'] = store.get(request['font_key'])
        refs = {rid: {'status': 'approved'} for rid in images}
        W, H = int(request['width']), int(request['height'])
        actions = request['scene'].get('actions') or []

        def problems_of(svg):
            out = svg_scene.check(svg, fonts=tuple(fonts), refs=refs)
            if not out:
                root = svg_scene.parse(svg)
                out = svg_scene.action_problems(actions, root) + svg_scene.spec_problems(root, request.get('spec'))
            return out   # the text boxes are measured by the render itself (drawn.TextOutside)

        bad = problems_of(svg0)
        if bad:
            return 'failed', {'phase': 'rules', 'problems': bad[:6]}, 'The scene cannot be rendered: ' + '; '.join(bad[:4]), None, None
        style_png = store.get(request['style_key']) if request.get('style_key') else None
        pictures = ([('the approved style', style_png)] if style_png else []) + [(f'picture {rid}', data) for rid, (_, data) in images.items()]
        asks = image_check.drawn_asks(request, [x for _, x in svg_scene.texts_of(svg_scene.parse(svg0))])
        planned, fps = int(request['frames']), Fraction(str(request['fps']))
        exact = planned / fps
        keep = set(drawn.sheet_indexes(str(fps), planned))
        rules = 'viewBox of the film\'s aspect; only plain SVG shapes, text, g, use, gradients, filters, clipPath and mask; no script, no style element, no animation, no external links; '
        rules += 'image href only ref:<id> as given; fonts ' + ', '.join(fonts) + '; colours #RRGGBB, none or url(#id); every text at least 4 % of the frame height and at most eight words, inside the inner 90 % of the frame.'
        passes, svg = [], svg0
        for p in range(1, image_check.DRAWN_PASSES + 1):
            path = folder / f'pass-{p}.mp4'
            try:
                try:
                    out = drawn.render(request, path, svg, images, fonts, keep=keep)
                except drawn.TextOutside:
                    raise
                except Exception:   # design/117 §5: a crashed browser is started again once
                    drawn.reset()
                    out = drawn.render(request, path, svg, images, fonts, keep=keep)
            except drawn.TextOutside as exc:
                if p == 1:
                    return 'failed', {'phase': 'rules', 'problems': [str(exc)]}, 'The scene cannot be rendered: ' + str(exc), None, None
                passes[-1]['fix_dropped'] = [str(exc)]   # the model's fix pushed a text out of the frame: the pass before stands
                break
            sheet = drawn.sheet(out['kept'], str(fps), W, H)
            ev = probe(path)
            code = [{'check': 'frames', 'weight': 'must', 'pass': abs(float(ev['duration_seconds']) * float(fps) - planned) < 1, 'seen': f"{float(ev['duration_seconds']):.3f} s at {fps} fps for {planned} frames"},
                    {'check': 'size', 'weight': 'must', 'pass': (ev.get('width'), ev.get('height')) == (W, H), 'seen': f"{ev.get('width')}x{ev.get('height')} for {W}x{H}"}]
            rec = image_check.drawn_sheet_check(sheet, pictures, asks, f"{request.get('view') or ''} drawing of the shot {request.get('shot_id')}", transport_factory)
            entry = {'pass': p, 'path': path, 'sheet': sheet, 'svg': svg, 'evidence': ev, 'code': code, 'lines': code + list(rec.get('lines') or []),
                     'must_failed': [c for c in code if c['pass'] is False] + list(rec.get('must_failed') or []), 'model': rec.get('model'), **({'error': rec['error']} if rec.get('error') else {})}
            passes.append(entry)
            if not entry['must_failed'] or rec.get('error') or p == image_check.DRAWN_PASSES:
                break
            fix = image_check.drawn_fix(svg, sheet, entry['must_failed'], rules, transport_factory)
            if fix.get('error') or not fix.get('svg'):
                entry['fix_error'] = fix.get('error') or 'the model returned no SVG'
                break
            probs = problems_of(fix['svg'])
            if probs:
                entry['fix_dropped'] = probs[:3]
                break
            entry['changed'] = fix.get('changed') or ''
            svg = fix['svg']
        best = min(passes, key=lambda e: (len(e['must_failed']), -e['pass']))
        data = Path(best['path']).read_bytes()
        sha = hashlib.sha256(data).hexdigest()
        k = f"{job['run_id']}/visuals/drawn/{jid}.mp4"
        store.put(k, data, 'video/mp4')
        for e in passes:
            store.put(f"{job['run_id']}/visuals/drawn/{jid}-sheet-{e['pass']}.jpg", e['sheet'], 'image/jpeg')
        sheet_key = f"{job['run_id']}/visuals/drawn/{jid}-sheet-{best['pass']}.jpg"
        fixed_key = None
        if best['svg'] != svg0:
            fixed_key = f"{job['run_id']}/visuals/drawn/{jid}-fixed.svg"
            store.put(fixed_key, best['svg'].encode('utf-8'), 'image/svg+xml')
        evidence = dict(best['evidence'])
        evidence.update(requested_duration_seconds=float(exact), placement=request['placement'], creative_approval=False, **timing_evidence(evidence['duration_seconds'], str(exact)))
        check = {'lines': best['lines'], 'must_failed': best['must_failed'], 'model': best.get('model'), 'best_pass': best['pass'], 'sheet_key': sheet_key, 'fixed_svg_key': fixed_key,
                 'passes': [{'pass': e['pass'], 'failed': [l['check'] for l in e['must_failed']], **{x: e[x] for x in ('changed', 'fix_dropped', 'fix_error', 'error') if e.get(x)}} for e in passes],
                 **({'error': best['error']} if best.get('error') else {})}
        return 'ready', {'provider_id': 'drawn', 'key': k, 'sha256': sha, 'bytes': len(data), 'evidence': evidence, 'code': best['code'], 'sheet_key': sheet_key, 'fixed_svg_key': fixed_key,
                         'check': check}, None, {'provider': 'drawn', 'seconds': float(exact), 'inr': 0}, None
    except Exception as exc:   # a render that fails is reported, never retried blindly
        return 'failed', {'phase': 'render'}, f'Render failed ({exc.__class__.__name__}: {exc}).', None, None


def check_drawn(job, result):
    """design/117 P4: the loop's record (the lines of the best pass, every pass, the sheet) kept on the session like a take's check. Never raises."""
    store = storage()
    try:
        with connect() as conn:
            conn.execute('select pg_advisory_xact_lock(hashtextextended(%s, 0))', ('run:' + str(job['run_id']),))
            k = f"{job['run_id']}/visuals/session.json"
            session = json.loads(store.get(k).decode('utf-8'))
            session.setdefault('take_checks', {})[str(job['id'])] = result.get('check') or {'lines': list(result.get('code') or []), 'must_failed': [c for c in result.get('code') or [] if c.get('pass') is False]}
            store.put(k, json.dumps(session, ensure_ascii=False, sort_keys=True).encode('utf-8'), 'application/json')
    except Exception:   # a drawing is never held back by its check
        return


def claim_take(conn):
    return conn.execute('''update vw2_jobs set status = case when status in ('queued','submitted') then 'running' else status end, lease_until = now() + interval '20 minutes',
                           attempt = attempt + 1, updated_at = now()
                           where id = (select id from vw2_jobs where provider='video' and (status='queued' or (status in ('submitted','storage_pending') and (lease_until is null or lease_until < now())))
                                       order by created_at limit 1 for update skip locked) returning *''').fetchone()


def tick():
    busy = False
    job = None
    for family in ('openai', 'gemini-image'):   # design/120: both image families, one worker
        with connect() as conn:
            job = jobs.claim(conn, family)
        if job:
            break
    if job:
        outcome = process_image(job)
        with connect() as conn:
            due = finalize_image(conn, job, *outcome)
        if due:
            check_image(job, outcome[1])   # design/92: after the transaction, no lock held while Gemini reads it
        busy = True
    from . import worker
    if worker.STOP:
        return busy
    with connect() as conn:
        job = jobs.claim(conn, 'drawn')   # design/113 E2: a render, a few seconds, free
    if job:
        status, result, error, cost, retry_in = process_drawn(job)
        with connect() as conn:
            jobs.finish(conn, job['id'], status, result=result, error=error, cost=cost, retry_in=retry_in)
            if status == 'ready':
                jobs.record_file(conn, job['run_id'], 'visuals', result['key'], Path(result['key']).name, result['sha256'], result['bytes'], 'video/mp4')
        if status == 'ready':
            check_drawn(job, result)
        busy = True
    with connect() as conn:
        job = claim_take(conn)
    if job:
        status, result, error, cost, retry_in = process_take(job)
        with connect() as conn:
            prior = (job.get('result') or {})
            jobs.finish(conn, job['id'], status, result={**prior, **(result or {})}, error=error, cost=cost, retry_in=retry_in)
            if status == 'ready':
                jobs.record_file(conn, job['run_id'], 'visuals', result['key'], Path(result['key']).name, result['sha256'], result['bytes'], 'video/mp4')
        if status == 'ready':
            check_take(job, result)   # design/91 N3
        busy = True
    return busy
