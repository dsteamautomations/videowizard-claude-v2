"""Background jobs: one row per job, updated only on state change. Providers run inside the worker with server keys.

Status: queued → running → ready | failed | submission_unknown (provider outcome unknown; needs recover) |
storage_pending (result journaled locally but not yet stored; the worker retries storage, never the provider)."""
import hashlib
import json
from datetime import datetime, timedelta, timezone

from psycopg.types.json import Json, Jsonb

from . import elevenlabs
from .config import settings
from .errors import Problem

OPEN = ('queued', 'running', 'storage_pending', 'submission_unknown')


def submit_voice(conn, user, run, outputs, request, request_id):
    """Validate an audition/narration request against the accepted script, then queue it. Paid; informed, not gated."""
    kind = request.get('kind')
    if kind not in ('audition', 'narration'):
        raise Problem(422, 'VOICE_REQUEST', "kind must be 'audition' or 'narration'.")
    script = next((o for o in outputs if o['stage'] == 'script' and o['unit'] is None), None)
    if not script:
        raise Problem(409, 'NOT_ALLOWED', 'Voice needs an accepted script first.')
    text = request.get('text')
    if not isinstance(text, str) or not text.strip():
        raise Problem(422, 'VOICE_REQUEST', 'text is required.')
    if kind == 'narration' and hashlib.sha256(text.encode('utf-8')).hexdigest() != script['summary']['content_digest']:
        raise Problem(409, 'SCRIPT_CHANGED', 'Narration text must be exactly the accepted script (content digest mismatch). Re-read out/script.json.')
    if kind == 'audition' and len(text) > 3000:
        raise Problem(422, 'VOICE_REQUEST', 'Audition excerpts are at most 3000 characters.')
    model = request.get('model_id') or elevenlabs.DEFAULT_MODEL
    settings_ = request.get('settings') or elevenlabs.DEFAULT_SETTINGS.get(model)
    elevenlabs.validate_settings(model, settings_)
    provider = elevenlabs.ElevenLabs()
    available = next((m for m in provider.models() if m['id'] == model and m['supported']), None)
    if not available:
        raise Problem(422, 'VOICE_MODEL', f'Model {model} is not available on the connected account.')
    if isinstance(available.get('max_characters'), int) and len(text) > available['max_characters']:
        raise Problem(422, 'VOICE_LENGTH', f"Text has {len(text)} characters; {model} accepts {available['max_characters']} per request.")
    voice = provider.voice(request.get('voice_id'))  # exact identity/access check, no substitution
    if kind == 'narration':
        open_jobs = conn.execute("select id from vw2_jobs where run_id=%s and stage='voice' and status = any(%s)", (run['id'], list(OPEN))).fetchall()
        if open_jobs:
            raise Problem(409, 'JOB_OPEN', 'Finish or recover the open voice job before starting narration.', jobs=[str(j['id']) for j in open_jobs])
    snapshot = {'kind': kind, 'voice_id': voice['voice_id'], 'name': voice['name'], 'model_id': model, 'settings': settings_, 'text': text,
                'characters': len(text), 'format': 'mp3_44100_128', 'source_script': script['summary']['content_digest'],
                **({'timing_mode': 'generation'} if kind == 'narration' else {})}
    row = conn.execute('''insert into vw2_jobs(run_id, stage, unit, provider, request, request_id) values (%s,'voice',%s,'elevenlabs',%s,%s) returning *''',
                       (run['id'], voice['voice_id'] if kind == 'audition' else None, Json(snapshot), request_id)).fetchone()
    return row


def claim(conn, provider):
    """Claim one queued job (or a storage_pending one whose retry delay passed) with a lease."""
    return conn.execute('''update vw2_jobs set status = case when status='queued' then 'running' else status end,
                           lease_until = now() + interval '20 minutes', attempt = attempt + 1, updated_at = now()
                           where id = (select id from vw2_jobs where provider=%s and (status='queued' or (status='storage_pending' and (lease_until is null or lease_until < now())))
                                       order by created_at limit 1 for update skip locked)
                           returning *''', (provider,)).fetchone()


def finish(conn, job_id, status, *, result=None, error=None, cost=None, retry_in=None):
    conn.execute('''update vw2_jobs set status=%s, result=coalesce(%s, result), error=%s, cost=coalesce(%s, cost),
                    lease_until=%s, updated_at=now() where id=%s''',
                 (status, Jsonb(result) if result is not None else None, error, Jsonb(cost) if cost is not None else None,
                  datetime.now(timezone.utc) + timedelta(minutes=retry_in) if retry_in else None, job_id))


def record_file(conn, run_id, stage, key, name, sha256, bytes_, mime):
    conn.execute('''insert into vw2_files(key, run_id, stage, name, sha256, bytes, mime) values (%s,%s,%s,%s,%s,%s,%s)
                    on conflict (key) do update set sha256=excluded.sha256, bytes=excluded.bytes, verified_at=now()''',
                 (key, run_id, stage, name, sha256, bytes_, mime))
