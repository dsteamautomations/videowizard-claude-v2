"""Background jobs: one row per job, updated only on state change. Providers run inside the worker with server keys.

Status: queued → running → ready | failed | submission_unknown (provider outcome unknown; needs recover) |
storage_pending (result journaled locally but not yet stored; the worker retries storage, never the provider)."""
import hashlib
import json
from datetime import datetime, timedelta, timezone

from psycopg.types.json import Json, Jsonb

from . import elevenlabs, narration_pieces, voice_direction
from .config import settings
from .errors import Problem

OPEN = ('queued', 'running', 'storage_pending', 'submission_unknown')


def submit_voice(conn, user, run, outputs, request, request_id, store=None):
    """Validate an audition/narration request against the accepted script, then queue it. Paid; informed, not gated.
    A narration carries the run's recorded direction (design/52 D): the provider reads the tagged text, the record keeps the accepted one."""
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
    limit = available.get('max_characters') if isinstance(available.get('max_characters'), int) else 10000
    pieces, directed = None, {}
    if kind == 'narration':   # design/40: a long script is narrated in pieces, split at paragraph and sentence ends
        direction = None
        if store is not None:
            from . import voices
            direction = voices.direction_for(store, run, request.get('voice_id'))
        provider_text = text
        if direction:
            tagged, spans = voice_direction.apply(text, direction['items'], direction['register'], direction['tweaks'])
            provider_text = tagged
            directed = {'text_tagged': tagged, 'tag_spans': spans, 'direction_digest': direction['digest'], 'direction_register': direction['register'], 'tweaks': direction['tweaks']}
        try:
            pieces = narration_pieces.split_for_narration(provider_text, limit)
        except ValueError as exc:
            raise Problem(422, 'VOICE_LENGTH', str(exc))
    elif len(text) > limit:
        raise Problem(422, 'VOICE_LENGTH', f"Text has {len(text)} characters; {model} accepts {limit} per request.")
    from . import voices
    voice, saved_now = voices.ensure_on_account(conn, provider, request.get('voice_id'))  # exact identity; a library voice is saved to the account first (defect 16)
    if kind == 'narration':
        open_jobs = conn.execute("""select id from vw2_jobs where run_id=%s and stage='voice' and status = any(%s)
                                    and request->>'kind' = 'narration' and request->>'voice_id' = %s""", (run['id'], list(OPEN), voice['voice_id'])).fetchall()   # design/54: up to three voices at once
        if open_jobs:
            raise Problem(409, 'JOB_OPEN', 'Finish or recover the open narration in this voice before starting another.', jobs=[str(j['id']) for j in open_jobs])
    snapshot = {'kind': kind, 'voice_id': voice['voice_id'], 'name': voice['name'], 'model_id': model, 'settings': settings_, 'text': text, **({'saved_from_library': True} if saved_now else {}),
                'characters': len(text), 'format': 'mp3_44100_128', 'source_script': script['summary']['content_digest'],
                **({'timing_mode': 'generation', 'pieces': pieces, **directed} if kind == 'narration' else {})}
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
