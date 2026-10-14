"""Analysis jobs: start (one job per clip), status, retry/recover/resolve/exclude, and the worker phases.

Outcome classes, defined once:
  retained · retained_unstructured · rejected · failed · submission_unknown · storage_pending
Only `retained` records a stage output for the clip. Every phase leaves a local receipt in the spool so a killed
worker resumes at the last phase and never pays twice."""
import hashlib
import json
import os
import subprocess
import tempfile
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from psycopg.types.json import Json, Jsonb

from . import analysis, core, jobs
from .config import settings
from .db import connect
from .errors import Problem
from .storage import storage
from .video_evidence.transport import GeminiTransport, GeminiTransportError, classify_failure
from .video_evidence.world import provider_schema

PROVIDER = 'gemini'
SPOOL = Path(os.environ.get('VW2_SPOOL') or Path(__file__).resolve().parents[1] / '.spool')
LEASE_MINUTES = 45
GLOBAL_CAP = 3
MAX_EXPLICIT_RETRIES = 3
TERMINAL = ('retained', 'retained_unstructured', 'rejected', 'failed')

# Tests and local runs swap the transport; production uses the ported Gemini transport.
transport_factory = GeminiTransport


def durable(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    with temp.open('wb') as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    temp.replace(path)


def read_json(path):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None


# ---------- start / status / controls ----------

def _inputs(conn, run, outputs):
    by = {o['stage']: o for o in outputs if o['unit'] is None}
    for stage in ('brief', 'script', 'media'):
        if stage not in by:
            raise Problem(409, 'NOT_ALLOWED', f'Analysis needs an accepted {stage} first.')
    store = storage()

    def file_of(output, name):
        ref = next((f for f in output['files'] if f['name'] == name), None)
        if not ref:
            raise Problem(409, 'FILE_MISSING', f'{name} is not recorded on the {output["stage"]} output; re-record that stage.')
        return json.loads(store.get(ref['key']).decode('utf-8'))
    return file_of(by['brief'], 'brief.json') | {'content_digest': by['brief']['summary'].get('content_digest')}, \
        file_of(by['script'], 'script.json'), by['media']


def start(conn, user, run, outputs, policy, again):
    """One job per clip in the media output (minus exclusions). Same inputs → same job reused unless `again`."""
    brief, script, media = _inputs(conn, run, outputs)
    procedure = core._stage(core.stage_table(run['procedure_version']), analysis.STAGE)
    excluded = set(policy.get('exclude') or [])
    clips = [c for c in media['summary']['clips'] if c['id'] not in excluded and c['name'] not in excluded]
    if not clips:
        raise Problem(422, 'ANALYSIS_POLICY', 'Every clip is excluded; nothing to analyse.')
    open_jobs = conn.execute("select unit from vw2_jobs where run_id=%s and stage='analysis' and status in ('queued','running','submission_unknown','storage_pending')",
                             (run['id'],)).fetchall()
    if open_jobs and again:
        raise Problem(409, 'JOB_OPEN', 'Finish or resolve the open analysis jobs before analysing again.', units=[r['unit'] for r in open_jobs])
    done = {o['unit'] for o in outputs if o['stage'] == 'analysis'}
    store = storage()
    created, reused = [], []
    for clip in clips:
        policy_clip = {**policy, 'collection': [{'id': c['id'], 'sha256': c['sha256']} for c in clips]}
        req = analysis.build_request(run, procedure, brief, script, clip, policy_clip, generation=(datetime.now(timezone.utc).isoformat() if again else None))
        existing = conn.execute("select id, status from vw2_jobs where run_id=%s and stage='analysis' and unit=%s and request->>'analysis_key'=%s order by created_at desc limit 1",
                                (run['id'], clip['id'], req['analysis_key'])).fetchone()
        if existing and (existing['status'] not in ('rejected', 'failed') or clip['id'] in done) and not again:
            reused.append(clip['id'])
            continue
        key = f"{run['id']}/analysis/{clip['id']}.request.json"
        store.put(key, json.dumps(req, ensure_ascii=False).encode('utf-8'), 'application/json')
        row = conn.execute('''insert into vw2_jobs(run_id, stage, unit, provider, request, request_id) values (%s,'analysis',%s,%s,%s,%s) returning id''',
                           (run['id'], clip['id'], PROVIDER, Jsonb({'kind': 'analysis', 'analysis_key': req['analysis_key'], 'request_key': key,
                                                                    'clip': {k: clip.get(k) for k in ('id', 'name', 'sha256', 'bytes', 'duration_s', 'has_audio')},
                                                                    'identity': req['identity'], 'policy': policy}),
                            uuid.uuid5(uuid.NAMESPACE_URL, req['analysis_key']))).fetchone()
        created.append({'unit': clip['id'], 'job_id': str(row['id'])})
    conn.execute("update vw2_jobs set request = request || %s where run_id=%s and stage='analysis' and status='queued'", (Jsonb({'policy': policy}), run['id']))
    return {'created': created, 'reused': reused, 'excluded': sorted(excluded), 'clips': len(clips)}


def status(conn, run, outputs):
    rows = conn.execute("select id, unit, status, attempt, error, cost, result, created_at, updated_at, lease_until from vw2_jobs where run_id=%s and stage='analysis' order by created_at", (run['id'],)).fetchall()
    latest = {}
    for r in rows:
        latest[r['unit']] = r  # last row per unit wins (created_at order)
    done = {o['unit']: o for o in outputs if o['stage'] == 'analysis'}
    units = []
    for unit, r in latest.items():
        phase = ((r['result'] or {}).get('phase') if r['status'] in ('running', 'storage_pending', 'submission_unknown') else None)
        units.append({'unit': unit, 'job_id': str(r['id']), 'status': r['status'], 'attempt': r['attempt'], 'phase': phase, 'error': r['error'], 'cost': r['cost'],
                      'recorded': unit in done, 'excluded': bool((done.get(unit) or {}).get('summary', {}).get('excluded')) if unit in done else False,
                      'summary': (done[unit]['summary'] if unit in done else None), 'updated_at': r['updated_at']})
    counts = {}
    for u in units:
        counts[u['status']] = counts.get(u['status'], 0) + 1
    return {'units': units, 'counts': counts}


def _job(conn, run, unit):
    row = conn.execute("select * from vw2_jobs where run_id=%s and stage='analysis' and unit=%s order by created_at desc limit 1", (run['id'], unit)).fetchone()
    if not row:
        raise Problem(404, 'NOT_FOUND', f'No analysis job for clip {unit}.')
    return row


def retry(conn, user, run, unit, note):
    """Explicit retry of a terminal failure: a fresh job row for the same frozen request. Capped per clip."""
    row = _job(conn, run, unit)
    if row['status'] not in ('rejected', 'failed', 'retained_unstructured'):
        raise Problem(409, 'NOT_ALLOWED', f"Clip {unit} is {row['status']}; retry applies to rejected/failed/unstructured clips.")
    tries = conn.execute("select count(*) from vw2_jobs where run_id=%s and stage='analysis' and unit=%s and request->>'analysis_key'=%s and request ? 'retry_of'",
                         (run['id'], unit, row['request']['analysis_key'])).fetchone()['count']  # explicit retries only; the automatic capacity retry is not counted
    if tries >= MAX_EXPLICIT_RETRIES:
        raise Problem(409, 'NEEDS_USER_DECISION', f'Clip {unit} has been retried {tries} times already. Decide: exclude it, re-encode and re-upload it, or file a defect.', options=['exclude', 'defect', 'stop'])
    new = conn.execute('''insert into vw2_jobs(run_id, stage, unit, provider, request, request_id) values (%s,'analysis',%s,%s,%s, gen_random_uuid()) returning id''',
                       (run['id'], unit, PROVIDER, Jsonb({**row['request'], 'retry_note': note, 'retry_of': str(row['id'])}))).fetchone()
    return {'job_id': str(new['id']), 'attempt_of_clip': tries + 1}


def recover(conn, user, run, unit):
    """Unknown outcome or storage failure: re-run the worker from the receipts; never a new generation."""
    row = _job(conn, run, unit)
    if row['status'] not in ('submission_unknown', 'storage_pending'):
        raise Problem(409, 'NOT_ALLOWED', f"Clip {unit} is {row['status']}; recover applies to unknown/storage-pending clips.")
    if not any((SPOOL / f"{row['id']}.{n}").exists() for n in ('response.json', 'upload.json')):
        raise Problem(409, 'NO_RECEIPT', 'No local receipt exists for this attempt on this worker. Check the provider account, then resolve or retry.')
    conn.execute("update vw2_jobs set status='storage_pending', lease_until=null, error=null, updated_at=now() where id=%s", (row['id'],))
    return {'job_id': str(row['id']), 'status': 'storage_pending'}


def resolve(conn, user, run, unit, note):
    row = _job(conn, run, unit)
    if row['status'] not in ('submission_unknown', 'storage_pending'):
        raise Problem(409, 'NOT_ALLOWED', 'Only an unresolved clip can be set aside.')
    conn.execute("update vw2_jobs set status='failed', error=%s, lease_until=null, updated_at=now() where id=%s", ('Set aside by operator: ' + (note or ''), row['id']))
    return {'job_id': str(row['id']), 'status': 'failed'}


def exclude(conn, user, run, unit, note):
    """Record the clip as excluded: a stage output without files so the stage can complete and planning knows."""
    row = conn.execute("select 1 from vw2_jobs where run_id=%s and stage='analysis' and unit=%s and status in ('queued','running')", (run['id'], unit)).fetchone()
    if row:
        raise Problem(409, 'JOB_OPEN', 'Wait for the running job or resolve it before excluding the clip.')
    return core.output(conn, user, run, {'stage': 'analysis', 'unit': unit, 'files': [], 'summary': {'excluded': True, 'note': note or ''}})


def release(conn, job_id):
    """Admin: release a stuck claim (replaces v1's hand-written SQL)."""
    conn.execute("update vw2_jobs set status='submission_unknown', lease_until=null, updated_at=now() where id=%s and status='running'", (job_id,))


# ---------- worker ----------

def claim(conn):
    """One queued job (or a storage_pending retry) with a lease; global cap; runs with fewer active jobs go first."""
    active = conn.execute("select count(*) from vw2_jobs where provider=%s and status='running' and lease_until > now()", (PROVIDER,)).fetchone()['count']
    if active >= GLOBAL_CAP:
        return None
    return conn.execute('''update vw2_jobs set status='running', lease_until = now() + make_interval(mins => %s), attempt = attempt + 1, updated_at = now()
                           where id = (select j.id from vw2_jobs j where j.provider=%s and (j.status='queued' or (j.status='storage_pending' and (j.lease_until is null or j.lease_until < now()))
                                                                                           or (j.status='running' and j.lease_until < now()))
                                       order by (select count(*) from vw2_jobs a where a.run_id=j.run_id and a.status='running' and a.lease_until > now()), j.created_at limit 1 for update skip locked)
                           returning *''', (LEASE_MINUTES, PROVIDER)).fetchone()


def renew(job_id, phase):
    with connect() as conn:
        conn.execute("update vw2_jobs set lease_until = now() + make_interval(mins => %s), result = coalesce(result,'{}'::jsonb) || %s, updated_at=now() where id=%s",
                     (LEASE_MINUTES, Jsonb({'phase': phase}), job_id))


def silent_copy(src, directory):
    target = Path(directory) / 'silent.mp4'
    subprocess.run([settings().FFMPEG_EXECUTABLE, '-nostdin', '-v', 'error', '-i', str(src), '-map', '0:v:0', '-c:v', 'copy', '-an', '-map_metadata', '-1', str(target)],
                   check=True, capture_output=True, timeout=300)
    return target


def process_inspection(job):
    """Paid focused inspection for one planning question: ≤3 originals or the extracted stills, schema-constrained answer."""
    import base64
    jid = str(job['id'])
    store = storage()
    req = json.loads(store.get(job['request']['request_key']).decode('utf-8'))
    raw_path = SPOOL / f'{jid}.response.json'
    dispatched = False
    try:
        if not raw_path.exists():
            version = job['request'].get('procedure_version')
            if not version:
                with connect() as conn:
                    version = conn.execute('select procedure_version from vw2_runs where id=%s', (job['run_id'],)).fetchone()['procedure_version']
            procedure = core._stage(core.stage_table(version), 'analysis')  # the model is never a literal here
            inspection = procedure.get('inspection') or {}
            transport = transport_factory(settings().GEMINI_API_KEY.get_secret_value(), procedure['model'], terminal_deadline_seconds=settings().ANALYSIS_DEADLINE_SECONDS,
                                          initial_soft_wait_seconds=60, on_update=lambda e: None, capture_answer_deltas=False, allow_agentic_video=True)
            parts = []
            with tempfile.TemporaryDirectory(prefix='vw2-inspect-') as directory:
                if req['mode'] == 'frames':
                    for f in req['frames']:
                        parts += [{'text': f"Frame {f['frame_id']}; original source time {f['original_s']:.6f} seconds."},
                                  {'inlineData': {'mimeType': 'image/png', 'data': base64.b64encode(store.get(f['key'])).decode()}}]
                else:
                    for sid, src in req['sources'].items():
                        path = Path(directory) / (sid + '.mp4')
                        data = store.get(f"{job['run_id']}/media/{src['name']}")
                        if hashlib.sha256(data).hexdigest() != src['sha256']:
                            raise Problem(409, 'ANALYSIS_SOURCE', 'Stored clip hash differs from the media record.')
                        path.write_bytes(data)
                        receipt_path = SPOOL / f'{jid}.{sid}.upload.json'
                        uploaded = transport.upload(path, 'video/mp4', src['sha256'], existing_receipt=read_json(receipt_path))
                        durable(receipt_path, json.dumps(uploaded).encode('utf-8'))
                        parts += [{'text': 'Original source ' + sid + '; its own original-source seconds clock.'}, {'fileData': {'fileUri': uploaded['uri'], 'mimeType': uploaded['mimeType']}}]
                parts.append({'text': req['prompt']})
                payload = {'contents': [{'role': 'user', 'parts': parts}],
                           'generationConfig': {'responseMimeType': 'application/json', 'responseJsonSchema': req['schema'], 'thinkingConfig': {'thinkingLevel': inspection.get('thinking_level', 'HIGH')},
                                                'mediaResolution': procedure['settings']['media_resolution'], 'maxOutputTokens': inspection.get('max_output_tokens', 16384)}}
                renew(jid, 'generate')
                dispatched = True
                try:
                    received = transport.generate(payload)
                    durable(raw_path, json.dumps({'raw': received.get('raw') or json.dumps(received['body']), 'metadata': received['metadata'], 'model': procedure['model']}, ensure_ascii=False).encode('utf-8'))
                except GeminiTransportError as exc:
                    if exc.code == 'http_error' and exc.http_status in (400, 401, 403, 404, 413, 429):
                        return 'rejected', {'failure': exc.code, 'http_status': exc.http_status}, f'Provider rejected the inspection ({exc.code}, HTTP {exc.http_status}).', None, None
                    if exc.code in ('incomplete_response', 'empty_response', 'model_json', 'blocked_response', 'provider_stream_error'):
                        return 'failed', {'failure': exc.code}, str(exc), None, None
                    return 'submission_unknown', {'failure': exc.code}, f'Outcome unknown after dispatch ({exc.code}).', None, None
        saved = read_json(raw_path)
        parsed = json.loads(saved['raw'])
        from jsonschema import Draft202012Validator
        errors = list(Draft202012Validator(req['schema']).iter_errors(parsed))
        if errors:
            return 'failed', {'failure': 'schema', 'errors': [e.message for e in errors[:5]]}, 'Inspector answer did not match the schema; retained, not regenerated.', None, None
        usage = (saved.get('metadata') or {}).get('usage') or {}
        cost = {'model': saved.get('model') or 'unknown', 'input_tokens': usage.get('promptTokenCount'), 'output_tokens': usage.get('candidatesTokenCount')}
        if req['mode'] == 'frames':
            frames = parsed['frames']
            answer = {'answers': [{'question_id': req['question_id'], 'status': 'partly_answered', 'answer': 'Sampled still contact/position only: ' + json.dumps(frames),
                                   'observations': [], 'interpretation': 'Only the named frames were supplied. Motion and exact onset remain unchecked.',
                                   'uncertainty': 'Frame answers are model claims; inspect overlap and hand ownership before relying on them.',
                                   'inspection_method': 'Extracted labelled stills', 'sampling_rate': 'Explicit manifest timestamps'}],
                      'inspection_limits': 'No continuous viewing; no movement or onset established.'}
            frame_rows = [{**f, 'original_s': next(x['original_s'] for x in req['frames'] if x['frame_id'] == f['frame_id'])} for f in frames]
        else:
            answer, frame_rows = parsed, []
        k = f"{job['run_id']}/planning/inspection/{req['question_id']}.answer.json"
        store.put(k, json.dumps({'answer': answer, 'frames': frame_rows}, ensure_ascii=False).encode('utf-8'), 'application/json')
        return 'retained', {'answer': answer, 'frames': frame_rows, 'answer_key': k}, None, cost, None
    except (Problem, OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        if raw_path.exists():
            return 'storage_pending', {'phase': 'store'}, f'Response saved locally; storage will be retried ({exc.__class__.__name__}).', None, 10
        if dispatched:
            return 'submission_unknown', {'phase': 'generate'}, f'Interrupted after dispatch ({exc.__class__.__name__}).', None, None
        return 'failed', {'phase': 'prepare'}, (exc.message if isinstance(exc, Problem) else f'{exc.__class__.__name__}: {exc}'), None, None


def process(job):
    """Returns (status, result, error, cost, retry_in_minutes). Resumes from spool receipts."""
    if job['request'].get('kind') == 'inspection':
        return process_inspection(job)
    jid = str(job['id'])
    store = storage()
    req_meta = job['request']
    paths = {n: SPOOL / f'{jid}.{n}' for n in ('request.json', 'upload.json', 'response.json', 'evidence.json')}
    dispatched = False
    try:
        request = read_json(paths['request.json'])
        if request is None:
            request = json.loads(store.get(req_meta['request_key']).decode('utf-8'))
            durable(paths['request.json'], json.dumps(request, ensure_ascii=False).encode('utf-8'))
        clip = request['clip']
        if job['status'] == 'storage_pending' and not paths['response.json'].exists():
            raise Problem(409, 'NO_RECEIPT', 'Saved response is missing on this worker. Resolve the attempt; nothing was regenerated.')
        if not paths['response.json'].exists():
            renew(jid, 'download')
            with tempfile.TemporaryDirectory(prefix='vw2-analysis-') as directory:
                original = Path(directory) / 'original.mp4'
                data = store.get(f"{job['run_id']}/media/{clip['name']}")
                if hashlib.sha256(data).hexdigest() != clip['sha256']:
                    raise Problem(409, 'ANALYSIS_SOURCE', 'Stored clip hash differs from the media record.')
                original.write_bytes(data)
                attachment = original if request['identity']['understand_audio'] else silent_copy(original, directory)
                sha = hashlib.sha256(attachment.read_bytes()).hexdigest()
                transport = transport_factory(settings().GEMINI_API_KEY.get_secret_value(), request['identity']['model'],
                                              terminal_deadline_seconds=settings().ANALYSIS_DEADLINE_SECONDS, initial_soft_wait_seconds=60,
                                              on_update=lambda e: None, capture_answer_deltas=False, allow_agentic_video=True)
                renew(jid, 'upload')
                uploaded = transport.upload(attachment, request['mime'], sha, existing_receipt=read_json(paths['upload.json']))
                durable(paths['upload.json'], json.dumps(uploaded).encode('utf-8'))
                mode = request['identity']['settings']['processing_mode']
                wire_schema = provider_schema(request['schema'], mode)
                parts = [{'fileData': {'fileUri': uploaded['uri'], 'mimeType': uploaded['mimeType']}}, {'text': request['prompt']}]
                if mode == 'AGENTIC':
                    parts[0]['mediaProcessing'] = 'AGENTIC'
                payload = {'contents': [{'role': 'user', 'parts': parts}],
                           'generationConfig': {'responseMimeType': 'application/json', 'responseJsonSchema': wire_schema,
                                                'thinkingConfig': {'thinkingLevel': request['identity']['settings']['thinking_level']},
                                                'mediaResolution': request['identity']['settings']['media_resolution'],
                                                'maxOutputTokens': request['identity']['settings']['max_output_tokens']}}
                renew(jid, 'generate')
                dispatched = True
                try:
                    received = transport.generate(payload)
                    raw = received.get('raw') or json.dumps(received['body'], ensure_ascii=False)
                    durable(paths['response.json'], json.dumps({'raw': raw, 'metadata': received['metadata'], 'received_at': datetime.now(timezone.utc).isoformat()}, ensure_ascii=False).encode('utf-8'))
                except GeminiTransportError as exc:
                    cls = classify_failure(exc)
                    meta = exc.metadata or {}
                    if exc.code == 'http_error' and exc.http_status in (400, 401, 403, 404, 413, 429) or cls['category'] in ('spending_or_billing_limit', 'quota_limit'):
                        return 'rejected', {'failure': exc.code, 'http_status': exc.http_status, 'category': cls['category']}, f'Provider rejected the request ({exc.code}, HTTP {exc.http_status}).', None, None
                    if exc.code in ('incomplete_response', 'empty_response', 'model_json', 'blocked_response'):
                        return 'failed', {'failure': exc.code}, str(exc), None, None
                    if exc.code == 'provider_stream_error':
                        return 'failed', {'failure': exc.code, 'provider_error': meta.get('provider_error')}, 'Provider reported an error in its stream; no retry was made.', None, None
                    return 'submission_unknown', {'failure': exc.code, 'phase': 'generate'}, f'Outcome unknown after dispatch ({exc.code}). Recover from the receipt or resolve.', None, None
        renew(jid, 'review')
        saved = read_json(paths['response.json'])
        reviewed = analysis.review_response(saved['raw'], request)
        usage = (saved.get('metadata') or {}).get('usage') or {}
        cost = {'model': request['identity']['model'], 'input_tokens': usage.get('promptTokenCount'), 'output_tokens': usage.get('candidatesTokenCount'),
                'thoughts_tokens': usage.get('thoughtsTokenCount'), 'tool_use_prompt_tokens': usage.get('toolUsePromptTokenCount'), 'cached_tokens': usage.get('cachedContentTokenCount'),
                'video_tokens': next((d.get('tokenCount') for d in usage.get('promptTokensDetails') or [] if d.get('modality') == 'VIDEO'), None),
                'thinking_tokens': usage.get('thoughtsTokenCount'), 'elapsed_seconds': (saved.get('metadata') or {}).get('elapsed_seconds')}
        renew(jid, 'store')
        base = f"{job['run_id']}/analysis/{clip['id']}"
        raw_bytes = saved['raw'].encode('utf-8')
        store.put(base + '.response.json', raw_bytes, 'application/json')
        result = {'response_key': base + '.response.json', 'response_sha256': hashlib.sha256(raw_bytes).hexdigest(), 'response_bytes': len(raw_bytes),
                  'finish_reason': (saved.get('metadata') or {}).get('finish_reason'), 'summary': analysis.summary_of(reviewed, clip)}
        if reviewed['status'] == 'retained':
            ev = json.dumps({'evidence': reviewed['evidence'], 'gaps': reviewed['gaps'], 'descriptive_name': (reviewed['result'] or {}).get('descriptive_name'),
                             'identity': request['identity'], 'clip': clip}, ensure_ascii=False).encode('utf-8')
            store.put(base + '.evidence.json', ev, 'application/json')
            if store.get(base + '.evidence.json') != ev:
                raise Problem(502, 'STORAGE', 'Evidence read-back failed.')
            result.update(evidence_key=base + '.evidence.json', evidence_sha256=hashlib.sha256(ev).hexdigest(), evidence_bytes=len(ev))
            return 'retained', result, None, cost, None
        if reviewed['status'] == 'identity_mismatch':
            return 'failed', {**result, 'identity_errors': reviewed['identity_errors']}, 'Response identity did not match the request (' + '; '.join(reviewed['identity_errors'][:3]) + ').', cost, None
        return 'retained_unstructured', result, 'The provider answer is not structured JSON; retained for review, not regenerated.', cost, None
    except (Problem, OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        if paths['response.json'].exists():
            return 'storage_pending', {'phase': 'store'}, f'Response saved locally; storage will be retried ({exc.__class__.__name__}).', None, 10
        if dispatched:
            return 'submission_unknown', {'phase': 'generate'}, f'Interrupted after dispatch ({exc.__class__.__name__}); recover from receipts or resolve.', None, None
        msg = exc.message if isinstance(exc, Problem) else f'{exc.__class__.__name__}: {exc}'
        return 'failed', {'phase': 'prepare'}, msg, None, None


def finalize(conn, user_id, job, status, result, error, cost, retry_in):
    jobs.finish(conn, job['id'], status, result=result, error=error, cost=cost, retry_in=retry_in)
    if job['request'].get('kind') == 'inspection':
        return
    if status == 'retained':
        run = conn.execute('select * from vw2_runs where id=%s', (job['run_id'],)).fetchone()
        clip = job['request']['clip']
        for key, sha, n in ((result['response_key'], result['response_sha256'], result['response_bytes']), (result['evidence_key'], result['evidence_sha256'], result['evidence_bytes'])):
            jobs.record_file(conn, job['run_id'], 'analysis', key, Path(key).name, sha, n, 'application/json')
        files = [{'name': Path(result['response_key']).name, 'key': result['response_key'], 'sha256': result['response_sha256'], 'bytes': result['response_bytes'], 'location': 'storage', 'receipt': True},
                 {'name': Path(result['evidence_key']).name, 'key': result['evidence_key'], 'sha256': result['evidence_sha256'], 'bytes': result['evidence_bytes'], 'location': 'storage', 'receipt': True}]
        user = {'id': user_id or run['owner_id'], 'name': 'worker', 'role': 'Member', 'kind': 'executor'}
        conn.execute('select pg_advisory_xact_lock(hashtextextended(%s, 0))', ('run:' + str(run['id']),))
        existing = conn.execute("select 1 from vw2_stage_outputs where run_id=%s and stage='analysis' and unit=%s and not stale", (run['id'], clip['id'])).fetchone()
        if not existing:
            core.output(conn, user, run, {'stage': 'analysis', 'unit': clip['id'], 'files': files,
                                          'summary': {**result['summary'], 'cost': cost, 'job_id': str(job['id'])}})
    elif status == 'rejected' and (result or {}).get('http_status') in (429, 503) and (result or {}).get('category') not in ('spending_or_billing_limit', 'quota_limit')             and not job['request'].get('capacity_retry_of') and not job['request'].get('retry_of'):
        # one automatic capacity retry (v1 rule): same frozen request, fresh row
        conn.execute('''insert into vw2_jobs(run_id, stage, unit, provider, request, request_id, attempt) values (%s,'analysis',%s,%s,%s, gen_random_uuid(), 1)''',
                     (job['run_id'], job['unit'], PROVIDER, Jsonb({**job['request'], 'capacity_retry_of': str(job['id'])})))


def tick():
    with connect() as conn:
        job = claim(conn)
    if not job:
        return False
    outcome = process(job)
    with connect() as conn:
        finalize(conn, None, job, *outcome)
    return True
