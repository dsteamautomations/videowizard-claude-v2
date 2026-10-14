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
    print(summary or payload.get('message') or payload.get('action') or 'ok', file=sys.stderr)
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


def need_connect():
    p = begin_connect()
    emit({'action': 'connect', 'url': p['url'], 'code': p['code'], 'expires_at': p['expires_at'],
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
        need_connect()
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
    m = {'code': run['code'], 'run_id': run['id'], 'title': run.get('title'), 'created': datetime.now(timezone.utc).isoformat(),
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
    run = write('/api/runs', {'title': a.title, 'client': a.client, **({'procedure_version': a.version} if a.version else {})})
    if workspace(run['code']).exists():
        emit({'action': 'refused', 'message': f"Folder runs/{run['code']} already exists on this machine."}, 2)
    write(f"/api/runs/{run['id']}/claim", {'machine': machine_id()})
    m = make_workspace(run, a.keep_logs, a.assembly_machine)
    emit({**run, 'workspace': str(workspace(run['code'])), 'next': call('GET', f"/api/runs/{run['id']}/next")}, 0, f"Started {run['code']} in {m['code']}/")


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
    s.add_argument('--title', required=True); s.add_argument('--client'); s.add_argument('--version')
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
