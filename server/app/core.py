"""The ledger and gatekeeper: runs, next, output, revise, decide, close, adopt, defects.

Every function takes an open psycopg connection (one transaction per request) and the signed-in user.
Writes on a run are serialised with an advisory lock so `next` is computed on a consistent view.
"""
import hashlib
import json
from datetime import datetime
from uuid import UUID

from psycopg.types.json import Json

from .config import settings
from .db import stage_table
from .errors import Problem

UNIT_NONE = ''  # attempts primary key cannot hold NULL


def jsonable(value):
    """Plain JSON types only: datetimes as ISO-8601 with Z, UUIDs as strings. Used for responses and receipts."""
    if isinstance(value, dict):
        return {k: jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(v) for v in value]
    if isinstance(value, datetime):
        return value.isoformat().replace('+00:00', 'Z')
    if isinstance(value, UUID):
        return str(value)
    return value


# ---------- receipts (idempotency) ----------

def fingerprint(body):
    return hashlib.sha256(json.dumps({k: v for k, v in body.items() if k != 'request_id'}, sort_keys=True, default=str).encode()).hexdigest()


def with_receipt(conn, user, body, fn):
    """Run fn() once per (user, request_id). Same body again → stored response; different body → REQUEST_CONFLICT."""
    fp = fingerprint(body)
    conn.execute('select pg_advisory_xact_lock(hashtextextended(%s, 0))', (user['id'] + ':' + body['request_id'],))
    prior = conn.execute('select fingerprint, status, response from vw2_receipts where user_id=%s and request_id=%s',
                         (user['id'], body['request_id'])).fetchone()
    if prior:
        if prior['fingerprint'] != fp:
            raise Problem(409, 'REQUEST_CONFLICT', 'This request id was already used for different work. Use a new request id.')
        return prior['status'], prior['response']
    status, response = fn()
    response = jsonable(response)
    conn.execute('insert into vw2_receipts(user_id, request_id, fingerprint, status, response) values (%s,%s,%s,%s,%s)',
                 (user['id'], body['request_id'], fp, status, Json(response)))
    return status, response


PROCEDURE_KEYS = ('name', 'prompt', 'direction_prompt', 'steps', 'output_shape', 'output_file', 'needs_acceptance', 'paid', 'per_unit', 'cap')   # what the procedure route serves the plugin (every prompt of a stage)


# ---------- runs ----------

def resolve_client(client, rows=None):
    """Exactly one Active directory client by id or exact name, trade name or legal name (case-insensitive); otherwise refuse with candidates."""
    if rows is None:
        from .auth import client_directory
        rows = client_directory()
    term = (client or '').strip().lower()
    matches = [r for r in rows if term and (r['client_id'].lower() == term or r['client_name'].lower() == term
                                            or term in [x.lower() for x in r.get('dba_names') or []] or (r.get('company_legal_name') or '').lower() == term)]   # design/50 D
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise Problem(422, 'CLIENT_UNKNOWN', 'That name belongs to more than one Active client; ask the operator which one.', candidates=[r['client_name'] for r in matches][:10], ambiguous=True)
    containing = [r for r in rows if term and term in r['client_name'].lower()]
    if len(containing) == 1 and not matches:  # design/34 1.17: a partial name that fits exactly one Active client resolves to it
        return containing[0]
    candidates = [r['client_name'] for r in containing][:10]
    raise Problem(422, 'CLIENT_UNKNOWN', 'The client must be one Active client of the directory; ask the operator which one.', candidates=candidates, ambiguous=len(matches) > 1)


def client_runs(conn, client_id, limit=20):
    """Earlier runs for a client, any owner, newest first: code and title only (design/36 1.5, shown at intake)."""
    rows = conn.execute('select code, title from vw2_runs where client_id=%s order by created_at desc limit %s', (client_id, limit)).fetchall()
    return [{'code': r['code'], 'title': r['title']} for r in rows if r['title']]


def last_brief(conn, client_id):
    """What the client said at their latest brief, any owner (design/37 2.2): production values, answers, and the question texts from
    brief.json in storage when it can be read. None when the client has no brief yet. Shown as recommendations, never as answers."""
    row = conn.execute('''select r.code, o.summary, o.files from vw2_stage_outputs o join vw2_runs r on r.id = o.run_id
                          where r.client_id=%s and o.stage='brief' and o.unit is null and not o.stale order by o.created_at desc limit 1''', (client_id,)).fetchone()
    if not row:
        return None
    summary = row['summary'] or {}
    questions = []
    ref = next((f for f in (row['files'] or []) if f.get('name') == 'brief.json' and f.get('key')), None)
    if ref:
        try:
            from .storage import storage
            doc = json.loads(storage().get(ref['key']).decode('utf-8'))
            questions = [{'id': q.get('id'), 'question': q.get('question')} for q in doc.get('questions') or [] if isinstance(q, dict) and q.get('id')]
        except Exception:  # noqa: BLE001  the question texts are a convenience; a storage hiccup must never block a start
            questions = []
    return {'run': row['code'], 'production': summary.get('production') or {}, 'answers': summary.get('answers') or {}, 'questions': questions}


def last_voice(conn, client_id):
    """The client's narrator last time (design/39 4.2): from the most recent run with a current voice output. None when there is none."""
    row = conn.execute('''select r.code, o.summary from vw2_stage_outputs o join vw2_runs r on r.id = o.run_id
                          where r.client_id=%s and o.stage='voice' and o.unit is null and not o.stale order by o.created_at desc limit 1''', (client_id,)).fetchone()
    if not row:
        return None
    s = row['summary'] or {}
    return {'run': row['code'], 'voice_id': s.get('voice_id'), 'name': s.get('name'), 'model_id': s.get('model_id'), 'settings': s.get('settings') or {},
            'choice_note': s.get('choice_note') or ''}


def client_rules(conn, client_id):
    """Rules learned from master rejections for this client (design/37 2.3)."""
    rows = conn.execute('select rule, source_run, created_at from vw2_client_rules where client_id=%s order by id', (client_id or '',)).fetchall()
    return [{'rule': r['rule'], 'source_run': r['source_run'], 'at': str(r['created_at'])} for r in rows]


def analysis_waivers(conn, run):
    """Risk flags the operator waived for this run: from the latest analysis job's policy (on the job row after start; in the stored
    request after a re-solve)."""
    row = conn.execute("select request from vw2_jobs where run_id=%s and stage='analysis' and request->>'kind' = 'analysis' order by created_at desc limit 1",
                       (run['id'],)).fetchone()
    if not row:
        return []
    req = row['request'] or {}
    policy = req.get('policy')
    if policy is None and req.get('request_key'):
        try:
            from .storage import storage
            policy = json.loads(storage().get(req['request_key']).decode('utf-8')).get('policy') or {}
        except Exception:  # noqa: BLE001
            policy = {}
    return [str(w) for w in (policy or {}).get('waived_risk_flags') or []]


def effective_rules(conn, run, outputs):
    """One answer for every stage that applies rules (design/37 2.7): the brief's rules minus the waived flags (matched inside the rule text,
    as the solver matches flags), plus the rules learned for the client. Before analysis there are no waivers."""
    brief_o = next((o for o in outputs if o['stage'] == 'brief' and o['unit'] is None), None)
    production = ((brief_o['summary'] if brief_o else None) or {}).get('production') or {}
    brief_rules = [str(r) for r in production.get('brand_and_safety_rules') or []]
    waived = analysis_waivers(conn, run)
    brief_effective = [r for r in brief_rules if not any(w and w.lower() in r.lower() for w in waived)]
    learned = client_rules(conn, run.get('client_id') or '')
    return {'brief_rules': brief_rules, 'waived_flags': waived, 'brief_effective': brief_effective, 'learned': learned,
            'effective': brief_effective + [l['rule'] for l in learned]}


RETIRED_VERSIONS = {'1': 'procedure version 1 is retired; new films use version 3', '2': 'procedure version 2 is retired; new films use version 3'}   # design/35 Old ways 1, 2


def refuse_retired(version):
    if str(version) in RETIRED_VERSIONS:
        raise Problem(409, 'VERSION_RETIRED', RETIRED_VERSIONS[str(version)])


def create_run(conn, user, title, client, version, image_provider='openai'):
    version = version or settings().DEFAULT_PROCEDURE_VERSION
    refuse_retired(version)
    if stage_table(version) is None:
        raise Problem(404, 'VERSION_UNKNOWN', f'Procedure version {version!r} is not published.')
    chosen = resolve_client(client)
    return conn.execute('insert into vw2_runs(title, client, client_id, owner_id, owner_name, procedure_version, image_provider) values (%s,%s,%s,%s,%s,%s,%s) returning *',   # design/120: chosen once, never changed
                        (title or '', chosen['client_name'], chosen['client_id'], user['id'], user['name'], version, image_provider)).fetchone()


def is_admin(user):
    return user['role'] == 'Admin'


def open_defects(conn, run_id):
    return [r['id'] for r in conn.execute("select id from vw2_defects where run_id=%s and status='open' order by id", (run_id,)).fetchall()]


def try_lock(conn, run_id):
    """design/92: the run's lock if it is free right now, never waiting; a read that gets it may repair the session, one that does not answers as is."""
    row = conn.execute('select pg_try_advisory_xact_lock(hashtextextended(%s, 0)) as got', ('run:' + str(run_id),)).fetchone()
    return bool(row and row['got'])


def load_run(conn, user, run_id, lock=False):
    row = conn.execute('select * from vw2_runs where id = %s', (run_id,)).fetchone()
    if not row or (row['owner_id'] != user['id'] and not is_admin(user)):
        raise Problem(404, 'NOT_FOUND', 'Run not found.')  # 404 so run ids are not probeable
    if lock:
        conn.execute('select pg_advisory_xact_lock(hashtextextended(%s, 0))', ('run:' + str(run_id),))
        opened = open_defects(conn, run_id)   # design/48 O.2: every write waits for the builder while a defect is open
        if opened:
            raise Problem(409, 'DEFECT_OPEN', f'defect {opened[0]} is open on this run; the builder resolves it, then the run continues', defect=opened[0], defects=opened)
    return row


def list_runs(conn, user):
    sql = 'select id, code, title, client, owner_name, procedure_version, status, created_at, closed_at from vw2_runs'
    if is_admin(user):
        return conn.execute(sql + ' order by created_at desc limit 200').fetchall()
    return conn.execute(sql + ' where owner_id = %s order by created_at desc limit 200', (user['id'],)).fetchall()


def current_outputs(conn, run_id):
    return conn.execute('select * from vw2_stage_outputs where run_id=%s and not stale order by created_at', (run_id,)).fetchall()


def attempts_for(conn, run_id):
    return {(r['stage'], r['unit']): r for r in conn.execute('select * from vw2_attempts where run_id=%s', (run_id,))}


# ---------- next ----------

def _stage(stages, name):
    st = next((s for s in stages if s['name'] == name), None)
    if not st:
        raise Problem(422, 'UNKNOWN_STAGE', f'Stage {name!r} is not in this procedure version.')
    return st


def declared_units(outputs, stage_name):
    """Units for a per-unit stage are declared by an earlier output's summary.units[stage]; latest declaration wins."""
    units = None
    for o in outputs:
        declared = (o['summary'].get('units') or {}).get(stage_name)
        if isinstance(declared, list):
            units = [str(u) for u in declared]
    return units


def compute_next(run, stages, outputs, attempts):
    base = {'run_id': str(run['id']), 'code': run['code'], 'version': run['procedure_version'], 'active_machine': run['active_machine']}
    if run['status'] == 'closed':
        return {**base, 'stage': None, 'actor': 'none', 'allowed': ['view']}
    done = {(o['stage'], o['unit']) for o in outputs}
    for st in stages:
        units = declared_units(outputs, st['name']) if st['per_unit'] else None
        if st['per_unit'] and units == []:
            continue  # declared empty: nothing to do in this stage
        candidates = units if units else [None]
        open_units = [u for u in candidates if (st['name'], u) not in done]
        if not open_units:
            continue
        rows = [attempts.get((st['name'], u or UNIT_NONE)) for u in open_units]
        blocked = any(r and r['blocked'] for r in rows)
        info = {**base, 'stage': st['name'], 'needs_acceptance': st['needs_acceptance'], 'paid': st['paid'], 'cap': st['cap'],
                'attempts': max((r['count'] for r in rows if r), default=0),
                'actor': 'operator_decision' if blocked else 'operator',
                'allowed': (['decide'] if blocked else ['output']) + ['view', 'revise', 'defect', 'adopt']}
        if st['per_unit']:
            info['units_open'] = open_units if units else []
            info['units_declared'] = units is not None
        if blocked:
            info['options'] = ['retry', 'revise', 'defect', 'stop']
        return info
    return {**base, 'stage': None, 'actor': 'operator', 'allowed': ['close', 'view', 'revise', 'defect', 'adopt']}


def acceptance_quote(stage, quote, user):
    """design/98 W2: the voice stage records without the operator's words (their choice is the record); every other stage keeps the rule."""
    quote = str(quote or '').strip()
    return quote or (f"Chosen as final in chat by {user.get('name') or user.get('id')}" if stage == 'voice' else '')


def next_for(conn, run):
    nxt = compute_next(run, stage_table(run['procedure_version']), current_outputs(conn, run['id']), attempts_for(conn, run['id']))
    nxt = {**nxt, 'open_defects': open_defects(conn, run['id'])}   # design/48 O.2
    if nxt.get('stage') == 'voice':   # design/52 B: what the voices page holds (pick, narrations, direction, final)
        try:
            from . import voices
            from .storage import storage
            nxt['voice_page'] = voices.page_summary(storage(), run)
        except Problem:
            nxt['voice_page'] = None
    return nxt


# ---------- output ----------

def _bump_attempt(run_id, stage, unit, cap):
    """Record a failed attempt in its own transaction (the request transaction is rolled back)."""
    from .db import connect
    with connect() as conn:
        conn.execute('''insert into vw2_attempts(run_id, stage, unit, count, blocked) values (%s,%s,%s,1, 1 >= %s)
                        on conflict (run_id, stage, unit) do update set count = vw2_attempts.count + 1, blocked = vw2_attempts.count + 1 >= %s''',
                     (run_id, stage, unit or UNIT_NONE, cap, cap))


def _needs_decision(nxt):
    raise Problem(409, 'NEEDS_USER_DECISION', 'This step failed repeatedly. Ask the operator how to proceed.', options=nxt.get('options', []), next=nxt)


def output(conn, user, run, body):
    """Commit a stage output. Validation failures count as attempts; a wrong stage does not."""
    if run['status'] == 'closed':
        raise Problem(409, 'RUN_CLOSED', 'This run is closed.')
    stages = stage_table(run['procedure_version'])
    st = _stage(stages, body['stage'])
    outputs, attempts = current_outputs(conn, run['id']), attempts_for(conn, run['id'])   # read once; next is computed from these rows (design/37 2.9)
    nxt = compute_next(run, stages, outputs, attempts)
    unit = body.get('unit')
    if nxt['stage'] != st['name']:
        raise Problem(409, 'NOT_ALLOWED', f"The next step is {nxt['stage']!r}, not {st['name']!r}.", next=nxt)
    if st['per_unit'] and nxt['units_declared']:
        if unit is None or unit not in declared_units(outputs, st['name']):
            raise Problem(422, 'UNKNOWN_UNIT', 'This unit was not declared for this stage.', units_open=nxt['units_open'])
        if unit not in nxt['units_open']:
            raise Problem(409, 'NOT_ALLOWED', 'This unit already has an output. Use revise to redo it.', next=nxt)
    else:
        unit = None
    if nxt['actor'] == 'operator_decision':
        _needs_decision(nxt)
    try:
        quote = acceptance_quote(st['name'], body.get('accepted_quote'), user)
        if st['needs_acceptance'] and not quote:
            raise Problem(422, 'ACCEPTANCE_REQUIRED', "Ask the operator to approve this stage and pass their reply verbatim as accepted_quote.")
        if len(quote) > settings().MAX_QUOTE_CHARS:
            raise Problem(422, 'QUOTE_TOO_LONG', 'accepted_quote must be short: the operator reply, not the content.')
        files = body.get('files') or []
        if st['requires_files'] and not files:
            raise Problem(422, 'FILES_REQUIRED', 'This stage must record at least one file.')
        stored = [f for f in files if f.get('location') == 'storage']
        if stored:
            from .files import received
            ok = received(conn, run['id'], [f['key'] for f in stored])
            missing = [f['name'] for f in stored if f['key'] not in ok]
            if missing:
                raise Problem(422, 'FILE_NOT_RECEIVED', 'Upload these files and get receipts before recording the output.', files=missing)
            for f in stored:
                f['receipt'] = True
    except Problem:
        conn.rollback()
        _bump_attempt(run['id'], st['name'], unit, st['cap'])
        raise
    summary = body.get('summary') or {}
    row = conn.execute('''insert into vw2_stage_outputs(run_id, stage, unit, version, files, summary, cost_cents, accepted_by, accepted_at, accepted_quote)
                          values (%s,%s,%s,%s,%s,%s,%s,%s, case when %s then now() end, %s) returning *''',
                       (run['id'], st['name'], unit, run['procedure_version'], Json(files), Json(summary), summary.get('cost_cents'),
                        user['id'] if quote else None, bool(quote), quote or None)).fetchone()
    if st['name'] == 'intake' and str(summary.get('title') or '').strip():
        conn.execute('update vw2_runs set title=%s where id=%s', (str(summary['title']).strip()[:160], run['id']))
    conn.execute('delete from vw2_attempts where run_id=%s and stage=%s and unit=%s', (run['id'], st['name'], unit or UNIT_NONE))
    row = dict(row)
    remaining = {k: v for k, v in attempts.items() if k != (st['name'], unit or UNIT_NONE)}
    row['next'] = compute_next(run, stages, outputs + [row], remaining)   # the next stage comes back with the record (design/36 1.15), no re-read
    return row


# ---------- revise / decide / close / adopt / defects ----------

def revise(conn, user, run, stage, unit, confirm_quote):
    if run['status'] == 'closed':
        raise Problem(409, 'RUN_CLOSED', 'This run is closed.')
    stages = stage_table(run['procedure_version'])
    st = _stage(stages, stage)
    names = [s['name'] for s in stages]
    later = names[names.index(st['name']) + 1:]
    outputs = current_outputs(conn, run['id'])
    own = [o for o in outputs if o['stage'] == st['name'] and (unit is None or o['unit'] == unit)]
    if not own:
        raise Problem(409, 'NOT_ALLOWED', 'That stage has no output to revise.')
    paid_later = [o for o in outputs if o['stage'] in later and _stage(stages, o['stage'])['paid']]
    if paid_later and not (confirm_quote or '').strip():
        raise Problem(409, 'PAID_WORK_AFTER', 'Revising this stage discards paid work. Tell the operator what is lost and pass their explicit yes as confirm_quote.',
                      outputs=[{'stage': o['stage'], 'unit': o['unit'], 'cost_cents': o['cost_cents']} for o in paid_later])
    ids = [o['id'] for o in own] + [o['id'] for o in outputs if o['stage'] in later]
    conn.execute('update vw2_stage_outputs set stale = true where id = any(%s)', (ids,))
    reopened = [st['name']] + later
    if unit is None:
        conn.execute('delete from vw2_attempts where run_id=%s and stage = any(%s)', (run['id'], reopened))
    else:
        conn.execute('delete from vw2_attempts where run_id=%s and ((stage=%s and unit=%s) or stage = any(%s))', (run['id'], st['name'], unit, later))
    conn.execute('insert into vw2_revises(run_id, stage, unit, confirm_quote, by_user) values (%s,%s,%s,%s,%s)',
                 (run['id'], st['name'], unit, (confirm_quote or '').strip() or None, user['id']))
    return {'stale': len(ids), 'reopened': reopened}


def decide(conn, user, run, stage, unit, decision, note):
    st = _stage(stage_table(run['procedure_version']), stage)
    key = (run['id'], st['name'], unit or UNIT_NONE)
    row = conn.execute('select * from vw2_attempts where run_id=%s and stage=%s and unit=%s and blocked', key).fetchone()
    if not row:
        raise Problem(409, 'NOT_ALLOWED', 'That step is not waiting for a decision.')
    if decision == 'retry':
        conn.execute('update vw2_attempts set count = %s, blocked = false where run_id=%s and stage=%s and unit=%s', (st['cap'] - 1, *key))
    elif decision == 'revise':
        conn.execute('delete from vw2_attempts where run_id=%s and stage=%s and unit=%s', key)
        revise(conn, user, run, st['name'], unit, note)
    elif decision == 'defect':
        file_defect(conn, user, run, st['name'], note or 'Repeated failure', None)
    return {'decision': decision}


def close(conn, user, run):
    if run['status'] == 'closed':
        raise Problem(409, 'RUN_CLOSED', 'This run is already closed.')
    nxt = next_for(conn, run)
    if nxt['stage'] is not None:
        raise Problem(409, 'NOT_ALLOWED', f"Stage {nxt['stage']!r} is not done; a run closes only after delivery.", next=nxt)
    missing = [f.get('name') for o in current_outputs(conn, run['id']) for f in o['files'] if not f.get('receipt')]
    if missing:
        raise Problem(409, 'UPLOAD_INCOMPLETE', 'Some retained files have no upload receipt yet.', files=missing)
    row = conn.execute("update vw2_runs set status='closed', closed_at=now() where id=%s returning *", (run['id'],)).fetchone()
    import shutil
    from .stage2.render_jobs import CACHE
    shutil.rmtree(CACHE / str(run['id']), ignore_errors=True)   # design/46 11.7: the run's render cache goes with the run
    return row


def adopt(conn, user, run, version):
    refuse_retired(version)
    if stage_table(version) is None:
        raise Problem(404, 'VERSION_UNKNOWN', f'Procedure version {version!r} is not published.')
    return conn.execute('update vw2_runs set procedure_version=%s where id=%s returning *', (version, run['id'])).fetchone()


def claim(conn, user, run, machine):
    return conn.execute('update vw2_runs set active_machine=%s where id=%s returning *', (machine, run['id'])).fetchone()


def file_defect(conn, user, run, stage, error, log_excerpt):
    row = conn.execute('insert into vw2_defects(run_id, stage, error, log_excerpt, by_user) values (%s,%s,%s,%s,%s) returning id',
                       (run['id'], stage, error, (log_excerpt or '')[:8000], user['id'])).fetchone()
    return {'ticket': row['id']}
