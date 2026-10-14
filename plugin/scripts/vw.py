#!/usr/bin/env python
"""vw: the VideoWizard executor CLI the plugin's /vw command drives.

Prints JSON on stdout and one line on stderr. Exit codes: 0 ok · 2 operator action needed (connect, refused,
take over, tell builder) · 3 the server needs a user decision · 1 unexpected error.
Stage scripts (later slices) call `output`; this file holds only the generic run plumbing.
"""
import argparse
import hashlib
import json
import os
import secrets
import shutil
import socket
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx

VERSION = os.environ.get('VW2_PLUGIN_VERSION') or '0.1.0'
HOME = Path(os.environ.get('VW2_HOME') or (Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'vw2' if os.name == 'nt' else Path.home() / '.vw2'))
RUNS = Path(os.environ.get('VW2_RUNS') or Path.cwd() / 'runs')


# ---------- output helpers ----------

def emit(payload, code=0, summary=None):
    print(json.dumps(payload, indent=1, default=str))
    hint = (payload.get('message') or payload.get('action')) if isinstance(payload, dict) else f'{len(payload)} item(s)'
    print(summary or hint or 'ok', file=sys.stderr)
    sys.exit(code)


def load_json(path, default=None):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return default


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=1, default=str), encoding='utf-8')


# ---------- session / server ----------

def session():
    return load_json(HOME / 'session.json') or {}


def server_url():
    return (os.environ.get('VW2_SERVER_URL') or session().get('server') or 'http://localhost:8002').rstrip('/')


def machine_id():
    m = load_json(HOME / 'machine.json')
    if not m:
        m = {'id': socket.gethostname()[:40] + '-' + secrets.token_hex(3)}
        save_json(HOME / 'machine.json', m)
    return m['id']


def begin_connect():
    """Start (or reuse) a pending connection and tell the operator what to do. Never prints the token."""
    pending = load_json(HOME / 'pending.json')
    if pending and pending.get('expires_at', '') > datetime.now(timezone.utc).isoformat():
        return pending
    token = secrets.token_urlsafe(32)
    body = {'request_id': str(uuid.uuid4()), 'token_hash': hashlib.sha256(token.encode()).hexdigest()}
    try:
        r = httpx.post(server_url() + '/api/connect', json=body, timeout=30)
    except httpx.RequestError as exc:
        emit({'action': 'tell_builder', 'message': f'VideoWizard server not reachable at {server_url()} ({exc.__class__.__name__}). Tell the builder; do not debug.'}, 2)
    if r.status_code != 201:
        emit({'action': 'tell_builder', 'message': f'Connect failed: {r.status_code} {r.text[:200]}'}, 2)
    pending = {**r.json(), 'token': token, 'server': server_url()}
    save_json(HOME / 'pending.json', pending)
    return pending


def need_connect(reason=''):
    p = begin_connect()
    emit({'action': 'connect', 'url': p['url'], 'code': p['code'], 'expires_at': p['expires_at'], 'reason': reason,
          'message': f"Ask the operator to open {p['url']}, sign in, check that the page shows code {p['code']}, and approve. Then run `vw connect`."}, 2)


def api():
    tok = session().get('token')
    return httpx.Client(base_url=server_url(), headers={'Authorization': 'Bearer ' + tok} if tok else {}, timeout=60)


def call(method, path, **kw):
    """One server call with the standard outcomes handled: unreachable → tell builder; 401 → connect;
    NEEDS_USER_DECISION → exit 3; other 4xx → refused; 5xx → tell builder."""
    try:
        with api() as c:
            r = c.request(method, path, **kw)
    except httpx.RequestError as exc:
        emit({'action': 'tell_builder', 'message': f'VideoWizard server not reachable at {server_url()} ({exc.__class__.__name__}). Tell the builder; do not debug.'}, 2)
    if r.status_code == 401:
        need_connect(f'{method} {path} returned 401')
    body = r.json() if r.headers.get('content-type', '').startswith('application/json') else {'message': r.text[:300]}
    if r.status_code < 300:
        return body
    if body.get('code') == 'NEEDS_USER_DECISION':
        emit({**body, 'action': 'ask_operator'}, 3, 'The server needs the operator to decide: ' + ', '.join(body.get('options', [])))
    if r.status_code >= 500:
        emit({'action': 'tell_builder', 'status': r.status_code, **body}, 2)
    emit({'action': 'refused', 'status': r.status_code, **body}, 2)


def write(path, body):
    return call('POST', path, json={'request_id': str(uuid.uuid4()), **body})


# ---------- workspace ----------

def workspace(code):
    return RUNS / code


def manifest_path(code):
    return workspace(code) / 'manifest.json'


def active():
    code = (RUNS / '.active').read_text(encoding='utf-8').strip() if (RUNS / '.active').exists() else ''
    m = load_json(manifest_path(code)) if code else None
    if not m:
        emit({'action': 'refused', 'message': 'No active run on this machine. Use `vw start` for a new run or `vw pull <code>` for an existing one.'}, 2)
    return m


def make_workspace(run, keep_logs=False, assembly_machine=None, files=None):
    ws = workspace(run['code'])
    for d in ('in', 'out', 'work', 'logs'):
        (ws / d).mkdir(parents=True, exist_ok=True)
    m = {'code': run['code'], 'run_id': run['id'], 'title': run.get('title'), 'client': run.get('client'), 'client_id': run.get('client_id'), 'created': datetime.now(timezone.utc).isoformat(),
         'keep_logs': keep_logs, 'assembly_machine': assembly_machine, 'closed': False, 'files': files or []}
    save_json(manifest_path(run['code']), m)
    (RUNS / '.active').write_text(run['code'], encoding='utf-8')
    return m


def ensure_mine(nxt, take_over, run_id):
    other = nxt.get('active_machine')
    if other and other != machine_id():
        if not take_over:
            emit({'action': 'take_over', 'active_machine': other, 'run_id': run_id,
                  'message': f'This run is active on {other}. Ask the operator whether to take it over here; if yes, repeat with --take-over.'}, 2)
        write(f'/api/runs/{run_id}/claim', {'machine': machine_id()})


def version_tuple(v):
    return tuple(int(x) for x in str(v).split('.') if x.isdigit())


# ---------- commands ----------

def cmd_connect(a):
    p = begin_connect()
    print(f"Open {p['url']} · code {p['code']}", file=sys.stderr)
    deadline = time.time() + a.timeout
    while time.time() < deadline:
        try:
            r = httpx.get(p['server'] + '/api/auth/me', headers={'Authorization': 'Bearer ' + p['token']}, timeout=30)
        except httpx.RequestError:
            r = None
        if r is not None and r.status_code == 200:
            save_json(HOME / 'session.json', {'token': p['token'], 'server': p['server'], 'user': r.json()['id']})
            (HOME / 'pending.json').unlink(missing_ok=True)
            emit({'action': 'connected', 'user': r.json()}, 0, 'Connected as ' + r.json()['name'])
        time.sleep(a.poll)
    emit({'action': 'connect', 'url': p['url'], 'code': p['code'], 'message': 'Not approved yet. Ask the operator to approve, then run `vw connect` again.'}, 2)


def cmd_whoami(a):
    emit(call('GET', '/api/auth/me'))


def preflight(need_gb):
    meta = call('GET', '/api/meta')
    if version_tuple(VERSION) < version_tuple(meta['plugin_min_version']):
        emit({'action': 'install_plugin', 'installed': VERSION, 'required': meta['plugin_min_version'],
              'message': f"Plugin {VERSION} is older than the server requires ({meta['plugin_min_version']}). Ask the operator to update the vw plugin, then retry."}, 2)
    me = call('GET', '/api/auth/me')
    RUNS.mkdir(parents=True, exist_ok=True)
    free_gb = shutil.disk_usage(RUNS).free / 1e9
    if free_gb < need_gb:
        emit({'action': 'refused', 'message': f'Only {free_gb:.1f} GB free under {RUNS}; the operator said {need_gb} GB are needed.'}, 2)
    return me


def cmd_start(a):
    missing = [q for q, ok in (('Are the input files already in the run folder and under the size limit? (--inputs-ready)', a.inputs_ready),
                               ('Are spend caps set on the provider dashboards? (--spend-caps-set)', a.spend_caps_set),
                               ('Which machine will do assembly? (--assembly-machine)', a.assembly_machine)) if not ok]
    if missing:
        emit({'action': 'ask_operator', 'questions': missing, 'message': 'Ask the operator these before starting; pass the answers as flags.'}, 2)
    preflight(a.need_gb)
    run = write('/api/runs', {'client': a.client, **({'procedure_version': a.version} if a.version else {})})
    if workspace(run['code']).exists():
        emit({'action': 'refused', 'message': f"Folder runs/{run['code']} already exists on this machine."}, 2)
    write(f"/api/runs/{run['id']}/claim", {'machine': machine_id()})
    m = make_workspace(run, a.keep_logs, a.assembly_machine)
    emit({**run, 'workspace': str(workspace(run['code'])), 'next': call('GET', f"/api/runs/{run['id']}/next")}, 0, f"Started {run['code']} in {m['code']}/")


def cmd_clients(a):
    rows = call('GET', '/api/clients', params={'search': a.search or ''})
    emit({'clients': rows}, 0, f'{len(rows)} active client(s)' + (f" matching {a.search!r}" if a.search else '') + '; the operator picks one, then `vw start --client "<name>"`.')


def cmd_next(a):
    m = active()
    nxt = call('GET', f"/api/runs/{m['run_id']}/next")
    ensure_mine(nxt, a.take_over, m['run_id'])
    paid = f" This step uses a paid provider ({nxt['paid']}); tell the operator, do not ask." if nxt.get('paid') else ''
    emit(nxt, 0, (f"Next: {nxt['stage']}" if nxt.get('stage') else 'All stages done; close the run.') + paid)


def file_refs(m, paths, stage, retain):
    ws = workspace(m['code']).resolve()
    out_dir = (ws / 'out').resolve()
    refs = []
    for p in paths:
        path = (ws / p).resolve() if not Path(p).is_absolute() else Path(p).resolve()
        if out_dir not in path.parents or not path.is_file():
            emit({'action': 'refused', 'message': f'Only files under {out_dir} can be recorded; {p} is outside or missing.'}, 2)
        data = path.read_bytes()
        name = path.relative_to(out_dir).as_posix()
        refs.append({'name': name, 'key': f"{m['code']}/{stage}/{name}", 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data), 'receipt': retain})
    return refs


def cmd_output(a):
    m = active()
    nxt = call('GET', f"/api/runs/{m['run_id']}/next")
    ensure_mine(nxt, a.take_over, m['run_id'])
    try:
        summary = json.loads(a.summary) if a.summary else {}
    except ValueError:
        emit({'action': 'refused', 'message': '--summary must be JSON.'}, 2)
    refs = file_refs(m, a.file, a.stage, a.retain)
    body = {'stage': a.stage, 'files': refs, 'summary': summary}
    if a.unit:
        body['unit'] = a.unit
    if a.quote:
        body['accepted_quote'] = a.quote
    row = write(f"/api/runs/{m['run_id']}/output", body)
    for ref in refs:
        m['files'] = [f for f in m['files'] if f['name'] != ref['name']] + [{**ref, 'stage': a.stage, 'action': 'retain' if a.retain else 'upload'}]
    save_json(manifest_path(m['code']), m)
    emit(row, 0, f"Recorded {a.stage}{' / ' + a.unit if a.unit else ''} (revision {row['id'][:8]})")


def cmd_view(a):
    m = active()
    emit(call('GET', f"/api/runs/{m['run_id']}/stages/{a.stage}"))


def cmd_revise(a):
    m = active()
    body = {'stage': a.stage, **({'unit': a.unit} if a.unit else {}), **({'confirm_quote': a.confirm} if a.confirm else {})}
    emit(write(f"/api/runs/{m['run_id']}/revise", body))


def cmd_decide(a):
    m = active()
    emit(write(f"/api/runs/{m['run_id']}/decide", {'stage': a.stage, **({'unit': a.unit} if a.unit else {}), 'decision': a.decision, **({'note': a.note} if a.note else {})}))


def cmd_defect(a):
    m = active()
    log = ''
    if a.log:
        try:
            log = Path(a.log).read_text(encoding='utf-8', errors='replace')[-4000:]
        except OSError:
            pass
    emit(write(f"/api/runs/{m['run_id']}/defects", {'stage': a.stage, 'error': a.error, 'log_excerpt': log}), 0,
         'Defect filed. Tell the operator the ticket number and stop; the builder takes it from here.')


def cmd_stage(a):
    """Stage scripts: prepare (inputs + prompt for the model) and record (validate out/<stage>.json, record output)."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import stages_text
    import stages_av
    m = active()
    nxt = call('GET', f"/api/runs/{m['run_id']}/next")
    ensure_mine(nxt, a.take_over, m['run_id'])
    if nxt.get('stage') != a.stage:
        emit({'action': 'refused', 'message': f"The next stage is {nxt.get('stage')!r}, not {a.stage!r}. Run `vw next`.", 'next': nxt}, 2)
    scripts = {**stages_text.STAGES, 'media': (stages_av.media_prepare, stages_av.media_record), 'voice': (stages_av.voice_prepare, stages_av.voice_record)}
    if a.stage not in scripts:
        emit({'action': 'refused', 'message': f'Stage {a.stage!r} has no script in this plugin version.'}, 2)
    procedure = call('GET', f"/api/procedures/{nxt['version']}/{a.stage}")
    full = call('GET', f"/api/runs/{m['run_id']}")
    current = {o['stage']: o for o in full['outputs'] if o['unit'] is None}

    def prior(stage):
        if stage not in current:
            emit({'action': 'refused', 'message': f'Stage {stage} has no current output; run `vw next`.'}, 2)
        return current[stage]

    ws = workspace(m['code'])
    prepare, record = scripts[a.stage]
    try:
        if a.step == 'prepare':
            emit({'stage': a.stage, **prepare(ws, procedure, prior)}, 0, f'{a.stage}: inputs and prompt ready')
        if a.stage == 'media':
            result = record(ws, procedure, prior, lambda stage, path, sha, size: upload_file(m, stage, path, sha, size))
        elif a.stage == 'voice':
            result = record(ws, procedure, prior, None)
        elif a.stage == 'intake':
            result = record(ws, procedure, prior, a.title, m.get('client') or '')
        else:
            result = record(ws, procedure, prior)
    except stages_text.Refused as exc:
        emit({'action': 'refused', 'message': str(exc)}, 2)
    if result.get('upload'):  # stage files the server needs later (brief, script, media list, voice.json) go to storage
        ws_out = workspace(m['code'])
        refs = [upload_file(m, a.stage, ws_out / f, hashlib.sha256((ws_out / f).read_bytes()).hexdigest(), (ws_out / f).stat().st_size) for f in result['files']]
        for r in refs:  # keep the local copy on close as well as the stored one
            m['files'] = [{**f, 'action': 'retain'} if f.get('key') == r['key'] else f for f in m['files']]
    else:
        refs = file_refs(m, result['files'], a.stage, result.get('retain', True))
    refs = refs + result.get('stored', [])
    body = {'stage': a.stage, 'files': refs, 'summary': result['summary']}
    if a.quote:
        body['accepted_quote'] = a.quote
    row = write(f"/api/runs/{m['run_id']}/output", body)
    for ref in refs:
        m['files'] = [f for f in m['files'] if f['name'] != ref['name']] + [{**ref, 'stage': a.stage, 'action': 'retain' if result.get('retain', True) else 'upload'}]
    save_json(manifest_path(m['code']), m)
    emit(row, 0, f'Recorded {a.stage}; run `vw next`.')


def upload_file(m, stage, path, sha, size):
    """Sign → PUT → receipt. Skips files the manifest already shows as receipted (resumable)."""
    path = Path(path)
    name = path.name
    done = next((f for f in m['files'] if f.get('sha256') == sha and f.get('receipt') and f.get('location') == 'storage'), None)
    if done:
        return {k: done[k] for k in ('name', 'key', 'sha256', 'bytes', 'receipt', 'location')}
    signed = write(f"/api/runs/{m['run_id']}/files/sign", {'stage': stage, 'name': name})
    url = signed['url'] if signed['url'].startswith('http') else server_url() + signed['url']
    try:
        with path.open('rb') as f:
            r = httpx.put(url, content=f, headers=signed.get('headers') or {}, timeout=httpx.Timeout(600, connect=30))
    except httpx.RequestError as exc:
        emit({'action': 'refused', 'message': f'Upload of {name} was interrupted ({exc.__class__.__name__}). Run the step again; finished files are skipped.'}, 2)
    if r.status_code >= 300:
        emit({'action': 'tell_builder', 'message': f'Storage refused the upload of {name}: HTTP {r.status_code}.'}, 2)
    write(f"/api/runs/{m['run_id']}/files/receipt", {'key': signed['key'], 'sha256': sha, 'bytes': size})
    ref = {'name': name, 'key': signed['key'], 'sha256': sha, 'bytes': size, 'receipt': True, 'location': 'storage'}
    m['files'] = [f for f in m['files'] if f.get('key') != ref['key']] + [{**ref, 'stage': stage, 'action': 'upload'}]
    save_json(manifest_path(m['code']), m)
    return ref


def cmd_upload(a):
    m = active()
    ws = workspace(m['code'])
    path = (ws / a.file).resolve()
    if not path.is_file() or ws.resolve() not in path.parents:
        emit({'action': 'refused', 'message': f'{a.file} must be a file inside the run folder.'}, 2)
    data = path.read_bytes()
    emit(upload_file(m, a.stage, path, hashlib.sha256(data).hexdigest(), len(data)), 0, f'Uploaded {path.name}')


def cmd_voice(a):
    m = active() if a.what in ('audition', 'narrate', 'jobs', 'fetch', 'recover', 'resolve') else None
    if a.what == 'recover':
        emit(write(f"/api/runs/{m['run_id']}/jobs/{a.job}/recover", {}))
    if a.what == 'resolve':
        emit(write(f"/api/runs/{m['run_id']}/jobs/{a.job}/resolve", {'note': a.note or ''}), 0, 'Attempt set aside; a new narration may be submitted.')
    if a.what == 'catalog':
        params = {k: v for k, v in (('scope', a.scope), ('search', a.search), ('cursor', a.cursor), ('language', a.language), ('accent', a.accent),
                                    ('gender', a.gender), ('age', a.age), ('use_cases', ','.join(a.use_case or [])), ('high_quality', 'true' if a.high_quality else '')) if v}
        emit(call('GET', '/api/voice/catalog', params=params))
    if a.what == 'models':
        emit(call('GET', '/api/voice/models'))
    if a.what == 'preview':
        emit(call('GET', f'/api/voice/preview/{a.voice[0]}'), 0, 'Give the operator the preview link to listen.')
    if a.what == 'add-library':
        emit(call('POST', '/api/voice/library-add', json={'public_owner_id': a.owner, 'voice_id': a.voice[0]}))
    if a.what in ('audition', 'narrate'):
        script = load_json(workspace(m['code']) / 'out' / 'script.json') or {}
        text = a.excerpt if a.what == 'audition' else script.get('spoken_text')
        if not text:
            emit({'action': 'refused', 'message': 'No text: auditions need --excerpt; narration needs out/script.json.'}, 2)
        settings_ = json.loads(a.settings) if a.settings else None
        rows = []
        for voice in (a.voice if a.what == 'audition' else a.voice[:1]):
            req = {'kind': 'audition' if a.what == 'audition' else 'narration', 'voice_id': voice, 'model_id': a.model, 'text': text, **({'settings': settings_} if settings_ else {})}
            rows.append(write(f"/api/runs/{m['run_id']}/jobs", {'stage': 'voice', 'provider': 'elevenlabs', 'request': req}))
        emit({'jobs': [{'id': r['id'], 'voice_id': r['request']['voice_id'], 'status': r['status']} for r in rows]}, 0,
             f"Submitted {len(rows)} paid ElevenLabs {a.what} job(s); tell the operator, then poll with `vw voice jobs`.")
    if a.what == 'jobs':
        emit(call('GET', f"/api/runs/{m['run_id']}/jobs", params={'stage': 'voice'}))
    if a.what == 'fetch':
        job = call('GET', f"/api/runs/{m['run_id']}/jobs/{a.job}")
        if job['status'] != 'ready':
            emit({'action': 'refused', 'message': f"Job is {job['status']}: {job.get('error') or 'not ready yet'}.", 'job': job}, 2)
        ws = workspace(m['code'])
        res = job['result']
        for name, key in (('narration.mp3' if job['request']['kind'] == 'narration' else f"audition-{job['request']['voice_id']}.mp3", res['audio_key']), ('timing.json', res.get('timing_key'))):
            if not key:
                continue
            try:
                with api() as c:
                    r = c.get(f"/api/runs/{m['run_id']}/files/{key}", follow_redirects=True)
            except httpx.RequestError as exc:
                emit({'action': 'tell_builder', 'message': f'Download failed ({exc.__class__.__name__}).'}, 2)
            if r.status_code != 200:
                emit({'action': 'tell_builder', 'message': f'Download of {name} failed: HTTP {r.status_code}.'}, 2)
            (ws / 'out' / name).write_bytes(r.content)
        if job['request']['kind'] == 'narration':
            save_json(ws / 'work' / 'voice-fetched.json', job)
        emit({'job': job['id'], 'files': [str(ws / 'out' / 'narration.mp3')], 'duration_s': res.get('duration_s')}, 0,
             'Fetched. Give the operator the file to listen to, ask for approval, then `vw stage voice record --quote`.')


def cmd_analysis(a):
    m = active()
    run = m['run_id']
    if a.what == 'start':
        missing = [q for q, ok in (('May camera audio be used in the film? (--camera-audio allowed|excluded)', a.camera_audio),
                                   ('What kind of film is this? (--film-type "…")', a.film_type)) if not ok]
        if missing:
            emit({'action': 'ask_operator', 'questions': missing + ['Should the model listen to the clips\' audio to understand them? (--understand-audio yes|no, default yes)', 'Any clip to leave out? (--exclude <name>, repeatable)']}, 2)
        body = {'camera_audio': a.camera_audio, 'understand_audio': a.understand_audio != 'no', 'film_type': a.film_type, 'exclude': a.exclude or [], 'again': a.again}
        emit(write(f'/api/runs/{run}/analysis/start', body), 0, 'Analysis started: one paid Gemini 4 Argon request per clip. Tell the operator; poll with `vw analysis status`.')
    if a.what == 'status':
        st = call('GET', f'/api/runs/{run}/analysis')
        c = st['counts']
        emit(st, 0, 'Analysis: ' + ', '.join(f'{v} {k}' for k, v in sorted(c.items())))
    if a.what == 'show':
        st = call('GET', f'/api/runs/{run}/analysis')
        u = next((x for x in st['units'] if x['unit'] == a.unit), None)
        emit(u or {'action': 'refused', 'message': f'No clip {a.unit}.'}, 0 if u else 2)
    if a.what in ('retry', 'recover', 'resolve', 'exclude'):
        emit(write(f'/api/runs/{run}/analysis/{a.unit}/{a.what}', {'note': a.note or ''}))


def _json_file(m, rel):
    path = workspace(m['code']) / rel
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError) as exc:
        emit({'action': 'refused', 'message': f'{rel} is missing or not valid JSON ({exc.__class__.__name__}).'}, 2)


def _download(m, key, rel):
    ws = workspace(m['code'])
    with api() as c:
        r = c.get(f"/api/runs/{m['run_id']}/files/{key}", follow_redirects=True)
    if r.status_code != 200:
        emit({'action': 'tell_builder', 'message': f'Download of {key} failed: HTTP {r.status_code}.'}, 2)
    (ws / rel).parent.mkdir(parents=True, exist_ok=True)
    (ws / rel).write_bytes(r.content)
    return str(ws / rel)


def cmd_planning(a):
    m = active()
    run = m['run_id']
    base = f'/api/runs/{run}/planning'
    if a.what == 'prepare':
        missing = [q for q, ok in (('Output fps? (--fps 24|25|30)', a.fps), ('Output resolution? (--resolution 1920x1080)', a.resolution),
                                   ('May original camera sound be heard in the film? (--source-audio none|ambient|speech|both)', a.source_audio),
                                   ('May people be seen speaking on screen? (--visible-speaking allow|avoid)', a.visible_speaking)) if not ok]
        if missing:
            emit({'action': 'ask_operator', 'questions': missing}, 2)
        w, h = (int(x) for x in a.resolution.lower().split('x'))
        out = write(base + '/prepare', {'fps': int(a.fps), 'resolution': [w, h], 'source_audio_in_output': a.source_audio, 'visible_speaking': a.visible_speaking, 'film_type': a.film_type or ''})
        path = _download(m, out['package']['key'], 'work/planning-package.json')
        emit({**out, 'package_path': path}, 0, 'Planning package ready in work/planning-package.json. Next: group scenes (out/scenes.json) then `vw planning scenes`.')
    if a.what == 'package':
        st = call('GET', base)
        if st.get('state') != 'prepared':
            emit({'action': 'refused', 'message': 'Run `vw planning prepare` first.'}, 2)
        full = call('GET', f'/api/runs/{run}')
        emit({'package_path': _download(m, f"{run}/planning/package.json", 'work/planning-package.json'), 'status': st}, 0, 'Package downloaded.')
    if a.what == 'scenes':
        out = write(base + '/scenes', {'scenes': _json_file(m, a.file), 'quote': a.quote or ''})
        _download(m, out['package']['key'], 'work/planning-package.json')
        emit(out, 0, f"Scenes saved; passages {out['passages']}. Package refreshed. Next: author out/plan.json and `vw planning check`.")
    if a.what in ('check', 'draft', 'revise'):
        body = {'plan': _json_file(m, a.file)}
        if a.what != 'check':
            body['quote'] = a.quote
        out = write(base + '/' + a.what, body)
        emit(out, 0 if out.get('status') in (None, 'draft_technically_valid') else 2, f"{a.what}: {out.get('status', 'ok')}")
    if a.what == 'status':
        emit(call('GET', base))
    if a.what == 'answer':
        emit(write(base + '/answer', {'question_id': a.question, 'answer': a.answer, 'quote': a.quote}))
    if a.what == 'mechanical':
        emit(write(base + '/answer', {'question_id': a.question, 'check': json.loads(a.check)}))
    if a.what == 'frames':
        emit(write(base + '/frames', {'question_id': a.question, 'source_id': a.source, 'times': [float(t) for t in a.times.split(',')]}))
    if a.what == 'inspect':
        emit(write(base + '/inspect', {'question_ids': a.question_ids or ([a.question] if a.question else [])}), 0, 'Paid Gemini 4 Argon inspection queued; tell the operator. Poll `vw planning status`.')
    if a.what == 'review-input':
        out = call('GET', base + '/review-input')
        (workspace(m['code']) / 'work' / 'inspector-answers.json').write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding='utf-8')
        emit(out, 0, 'Inspector answers in work/inspector-answers.json; write out/answer-review.json with a scope and reason per field.')
    if a.what == 'review':
        emit(write(base + '/review', _json_file(m, a.file)))
    if a.what == 'ledger':
        out = write(base + '/ledger', {})
        _download(m, out['ledger']['key'], 'work/ledger.json')
        emit(out, 0, f"Ledger prepared (digest {out['ledger_digest'][:12]}…) in work/ledger.json. Revise the plan, then `vw planning revise`.")
    if a.what == 'finalize':
        out = write(base + '/finalize', {'assessment': _json_file(m, a.file), 'quote': a.quote})
        emit(out, 0, 'Planning finalized; certificate recorded. Run `vw next`.')


def cmd_visuals(a):
    m = active()
    run = m['run_id']
    base = f'/api/runs/{run}/visuals'
    ws = workspace(m['code'])
    if a.what == 'prepare':
        out = write(base + '/prepare', {})
        _download(m, out['package']['key'], 'work/visuals-package.json')
        emit(out, 0, f"Visuals package in work/visuals-package.json; gaps: {out['gaps']}. Author out/visual-plan.json, then `vw visuals check`.")
    if a.what in ('check', 'propose'):
        out = write(base + '/' + a.what, {'plan': _json_file(m, a.file)})
        emit(out, 0 if out.get('status') != 'rejected' else 2, f"{a.what}: {out.get('status', 'saved')}")
    if a.what == 'select' and a.gap:
        emit(write(base + '/select', {'choices': {a.gap: a.choice}}))
    if a.what == 'accept':
        emit(write(base + '/accept', {'gap_ids': a.gaps, 'quote': a.quote}))
    if a.what in ('frame', 'supply', 'web'):
        body = {'element_id': a.element, 'name': a.name or f'{a.what}-{a.element}', 'kind': 'frame' if a.what == 'frame' else 'supplied' if a.what == 'supply' else 'web', 'subject': a.subject or a.element}
        if a.what == 'frame':
            body.update(source_media_id=a.clip, requested_s=float(a.at))
        else:
            path = (ws / a.file).resolve()
            if ws.resolve() not in path.parents or not path.is_file():
                emit({'action': 'refused', 'message': 'The image must be a file inside the run folder.'}, 2)
            body['content_base64'] = __import__('base64').b64encode(path.read_bytes()).decode()
            if a.what == 'web':
                body.update(source_url=a.url or '', selection_reply=a.quote or '')
        out = write(base + '/references', body)
        emit(out, 0, f"Reference {out['id']} ({out['kind']}) is a candidate; show it to the operator (`vw visuals fetch --ref {out['id']}`) and approve with its sha256.")
    if a.what == 'image':
        body = {'element_id': a.element, 'name': a.name or f'{a.kind}-{a.element}', 'kind': a.kind or 'keyframe', 'subject': a.subject or a.element, 'prompt': a.prompt,
                'parents': a.parents.split(',') if a.parents else [], **({'size': a.size} if a.size else {}), **({'quality': a.quality} if a.quality else {})}
        out = write(base + '/images', body)
        emit(out, 0, f"Paid OpenAI image ({out['model']}) queued for reference {out['reference_id']}; tell the operator, poll `vw visuals status`.")
    if a.what == 'approve':
        emit(write(f"{base}/references/{a.ref}/approve", {'sha256': a.sha, 'quote': a.quote}))
    if a.what == 'bind':
        refs = {}
        for item in a.refs or []:
            eid, ids = item.split('=', 1)
            refs[eid] = ids.split(',')
        emit(write(base + '/bind', {'shot_id': a.shot, 'references': refs, 'quote': a.quote}))
    if a.what == 'packet':
        out = call('GET', f'{base}/shots/{a.shot}/packet')
        (ws / 'work' / f'packet-{a.shot}.json').write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding='utf-8')
        emit(out, 0, f'Composition packet for {a.shot} in work/packet-{a.shot}.json')
    if a.what == 'generator':
        emit(write(base + '/generator', {'shot_id': a.shot, 'provider': a.provider, 'model': a.model}))
    if a.what == 'prepare-take':
        subjects = dict(s.split('=', 1) for s in (a.subject or []))
        body = {'shot_id': a.shot, 'start_image': a.start, 'motion_prompt': a.motion, 'subject_reconciliation': subjects, 'continuity_notes': a.continuity or '',
                **({'end_image': a.end} if a.end else {}), **({'duration_seconds': int(a.seconds)} if a.seconds else {})}
        emit(write(base + '/prepare-take', body))
    if a.what == 'take':
        emit(write(base + '/take', {'shot_id': a.shot}), 0, 'Paid video take submitted; tell the operator and poll `vw visuals status`.')
    if a.what == 'status':
        emit(call('GET', base))
    if a.what == 'fetch':
        if a.ref:
            st = call('GET', base)
            ref = next((r for r in st['references'] if r['id'] == a.ref), None)
            if not ref or not ref.get('sha256'):
                emit({'action': 'refused', 'message': 'Unknown or not yet generated reference.'}, 2)
            path = _download(m, f"{run}/visuals/references/{a.ref}.png", f'work/ref-{a.ref}.png')
            emit({'ref': a.ref, 'path': path, 'sha256': ref['sha256']}, 0, f'Reference image at {path}; show it to the operator.')
        if a.job:
            job = call('GET', f'/api/runs/{run}/jobs/{a.job}')
            if job['status'] != 'ready':
                emit({'action': 'refused', 'message': f"Take is {job['status']}: {job.get('error') or 'not ready'}", 'job': job}, 2)
            path = _download(m, job['result']['key'], f"work/take-{a.job}.mp4")
            emit({'job': a.job, 'path': path, 'sha256': job['result']['sha256'], 'evidence': job['result']['evidence']}, 0, f'Take at {path}; let the operator watch it.')
    if a.what == 'review':
        emit(write(base + '/review', {'job_id': a.job, 'decision': a.decision, 'notes': a.notes, 'timing_notes': a.timing or '', 'quote': a.quote}))
    if a.what == 'select' and a.job:
        emit(write(base + '/select-take', {'job_id': a.job, 'quote': a.quote}))
    if a.what == 'asset':
        entry = next((f for f in m['files'] if f.get('name') == Path(a.file).name and f.get('receipt')), None)
        if not entry:
            emit({'action': 'refused', 'message': 'Upload the asset first: `vw upload --stage visuals --file out/<name>`.'}, 2)
        emit(write(base + '/asset', {'shot_id': a.shot, 'key': entry['key'], 'sha256': entry['sha256'], 'bytes': entry['bytes'], 'kind': a.kind, 'quote': a.quote}))
    if a.what == 'record':
        emit(write(base + '/record', {'gap_id': a.gap, 'quote': a.quote}), 0, 'Gap recorded; `vw next`.')


def cmd_pull(a):
    runs = call('GET', '/api/runs')
    run = next((r for r in runs if r['code'] == a.code), None)
    if not run:
        emit({'action': 'refused', 'message': f'No run {a.code} visible to this operator.'}, 2)
    full = call('GET', f"/api/runs/{run['id']}")
    ensure_mine(full['next'], a.take_over, run['id'])
    if not full['next'].get('active_machine'):
        write(f"/api/runs/{run['id']}/claim", {'machine': machine_id()})
    files = [{**f, 'stage': o['stage'], 'action': 'upload'} for o in full['outputs'] for f in o['files']]
    m = make_workspace(full, files=files)
    emit({**full, 'workspace': str(workspace(a.code))}, 0, f"Pulled {a.code}; files are listed in the manifest (downloads arrive with storage).")


def cmd_close(a):
    m = active()
    missing = [f['name'] for f in m['files'] if f['action'] == 'upload' and not f.get('receipt')]
    if missing:
        emit({'action': 'refused', 'files': missing, 'message': 'These files are not uploaded yet; nothing was deleted.'}, 2)
    run = write(f"/api/runs/{m['run_id']}/close", {})
    ws = workspace(m['code'])
    shutil.rmtree(ws / 'work', ignore_errors=True)
    if not m.get('keep_logs'):
        shutil.rmtree(ws / 'logs', ignore_errors=True)
    keep = {f['name'] for f in m['files'] if f['action'] == 'retain'}
    for p in (ws / 'out').rglob('*'):
        if p.is_file() and p.relative_to(ws / 'out').as_posix() not in keep:
            p.unlink()
    m['closed'] = True
    save_json(manifest_path(m['code']), m)
    (RUNS / '.active').unlink(missing_ok=True)
    emit(run, 0, f"Closed {m['code']}; scratch deleted, {len(keep)} retained file(s) kept in out/.")


def main(argv=None):
    p = argparse.ArgumentParser(prog='vw', description=__doc__)
    sub = p.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('connect'); s.add_argument('--timeout', type=float, default=600); s.add_argument('--poll', type=float, default=2); s.set_defaults(fn=cmd_connect)
    sub.add_parser('whoami').set_defaults(fn=cmd_whoami)
    s = sub.add_parser('start')
    s.add_argument('--client', required=True); s.add_argument('--version')
    s.add_argument('--need-gb', type=float, default=5); s.add_argument('--inputs-ready', action='store_true'); s.add_argument('--spend-caps-set', action='store_true')
    s.add_argument('--assembly-machine'); s.add_argument('--keep-logs', action='store_true'); s.set_defaults(fn=cmd_start)
    s = sub.add_parser('next'); s.add_argument('--take-over', action='store_true'); s.set_defaults(fn=cmd_next)
    s = sub.add_parser('output')
    s.add_argument('--stage', required=True); s.add_argument('--unit'); s.add_argument('--file', action='append', default=[])
    s.add_argument('--summary'); s.add_argument('--quote'); s.add_argument('--retain', action='store_true'); s.add_argument('--take-over', action='store_true'); s.set_defaults(fn=cmd_output)
    s = sub.add_parser('view'); s.add_argument('--stage', required=True); s.set_defaults(fn=cmd_view)
    s = sub.add_parser('revise'); s.add_argument('--stage', required=True); s.add_argument('--unit'); s.add_argument('--confirm'); s.set_defaults(fn=cmd_revise)
    s = sub.add_parser('decide'); s.add_argument('--stage', required=True); s.add_argument('--unit'); s.add_argument('--decision', required=True, choices=['retry', 'revise', 'defect', 'stop']); s.add_argument('--note'); s.set_defaults(fn=cmd_decide)
    s = sub.add_parser('defect'); s.add_argument('--stage'); s.add_argument('--error', required=True); s.add_argument('--log'); s.set_defaults(fn=cmd_defect)
    s = sub.add_parser('clients'); s.add_argument('--search'); s.set_defaults(fn=cmd_clients)
    s = sub.add_parser('stage'); s.add_argument('stage'); s.add_argument('step', choices=['prepare', 'record']); s.add_argument('--quote'); s.add_argument('--title'); s.add_argument('--take-over', action='store_true'); s.set_defaults(fn=cmd_stage)
    s = sub.add_parser('upload'); s.add_argument('--stage', required=True); s.add_argument('--file', required=True); s.set_defaults(fn=cmd_upload)
    s = sub.add_parser('voice'); s.add_argument('what', choices=['catalog', 'models', 'preview', 'add-library', 'audition', 'narrate', 'jobs', 'fetch', 'recover', 'resolve'])
    s.add_argument('--scope', default='account'); s.add_argument('--search', default=''); s.add_argument('--cursor', default=''); s.add_argument('--language', default='')
    s.add_argument('--accent', default=''); s.add_argument('--gender', default=''); s.add_argument('--age', default=''); s.add_argument('--use-case', action='append')
    s.add_argument('--high-quality', action='store_true'); s.add_argument('--voice', action='append', default=[]); s.add_argument('--owner')
    s.add_argument('--model', default='eleven_v4'); s.add_argument('--settings'); s.add_argument('--excerpt'); s.add_argument('--job'); s.add_argument('--note'); s.set_defaults(fn=cmd_voice)
    s = sub.add_parser('analysis'); s.add_argument('what', choices=['start', 'status', 'show', 'retry', 'recover', 'resolve', 'exclude'])
    s.add_argument('--camera-audio', choices=['allowed', 'excluded']); s.add_argument('--understand-audio', choices=['yes', 'no'], default='yes'); s.add_argument('--film-type')
    s.add_argument('--exclude', action='append'); s.add_argument('--again', action='store_true'); s.add_argument('--unit'); s.add_argument('--note'); s.set_defaults(fn=cmd_analysis)
    s = sub.add_parser('planning'); s.add_argument('what', choices=['prepare', 'package', 'scenes', 'check', 'draft', 'answer', 'mechanical', 'frames', 'inspect', 'review-input', 'review', 'ledger', 'revise', 'finalize', 'status'])
    s.add_argument('--fps'); s.add_argument('--resolution'); s.add_argument('--source-audio', choices=['none', 'ambient', 'speech', 'both']); s.add_argument('--visible-speaking', choices=['allow', 'avoid']); s.add_argument('--film-type')
    s.add_argument('--file'); s.add_argument('--quote'); s.add_argument('--question'); s.add_argument('--question-ids', nargs='*'); s.add_argument('--answer'); s.add_argument('--check'); s.add_argument('--source'); s.add_argument('--times'); s.set_defaults(fn=cmd_planning)
    s = sub.add_parser('visuals'); s.add_argument('what', choices=['prepare', 'check', 'propose', 'select', 'accept', 'frame', 'supply', 'web', 'image', 'approve', 'bind', 'packet', 'generator', 'prepare-take', 'take', 'status', 'fetch', 'review', 'asset', 'record'])
    for flag in ('--file', '--gap', '--choice', '--quote', '--element', '--name', '--subject', '--clip', '--at', '--url', '--kind', '--prompt', '--parents', '--size', '--quality', '--ref', '--sha', '--shot', '--provider', '--model', '--start', '--end', '--motion', '--continuity', '--seconds', '--job', '--decision', '--notes', '--timing'):
        s.add_argument(flag)
    s.add_argument('--gaps', nargs='*'); s.add_argument('--refs', nargs='*'); s.add_argument('--subject-rec', dest='subject', action='append'); s.set_defaults(fn=cmd_visuals)
    s = sub.add_parser('pull'); s.add_argument('code'); s.add_argument('--take-over', action='store_true'); s.set_defaults(fn=cmd_pull)
    sub.add_parser('close').set_defaults(fn=cmd_close)
    a = p.parse_args(argv)
    if a.cmd not in ('connect',) and not session().get('token'):
        need_connect()
    a.fn(a)


if __name__ == '__main__':
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:  # last resort: never a traceback into the chat
        emit({'action': 'tell_builder', 'message': f'vw failed unexpectedly: {exc.__class__.__name__}: {exc}'}, 1)
