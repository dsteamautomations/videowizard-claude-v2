"""Login ported from v1: shared employee directory (username ef-02, bcrypt ef-11) and apps.members role.
Role is stored on the session at sign-in; requests read only vw2_sessions."""
import hashlib
import json
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
import httpx
from fastapi import Cookie, Depends, Header

from .config import settings
from .db import connect
from .errors import Problem

_dummy = bcrypt.hashpw(secrets.token_bytes(32), bcrypt.gensalt())


def shared_client():
    cfg = settings()
    key = cfg.SHARED_SUPABASE_SERVICE_KEY.get_secret_value()
    if not cfg.SHARED_SUPABASE_URL or not key:
        raise Problem(503, 'CONFIGURATION', 'The administrator must configure the employee directory connection.')
    headers = {'apikey': key}
    if not key.startswith('sb_secret_'):
        headers['Authorization'] = 'Bearer ' + key
    return httpx.Client(base_url=settings().SHARED_SUPABASE_URL.rstrip('/') + '/rest/v1', headers=headers, timeout=30)


from .client_card import CARD_COLUMNS, LOGO_FIELDS, card_fields, card_of  # noqa: E402,F401  (design/50; pure, 3.9-safe for the unit tests)


def client_card(client_id):
    """The card for one client, read live; any failure gives {} and never blocks a start (design/50 F)."""
    columns = ['client_id'] + [c for cols in CARD_COLUMNS.values() for c in cols]
    try:
        with shared_client() as shared:
            page = shared.get('/clients', params={'select': ','.join(columns), 'client_id': 'eq.' + str(client_id), 'limit': '1'}).json()
        return card_of(page[0]) if isinstance(page, list) and page else {}
    except Exception:  # noqa: BLE001  the card is context; a directory hiccup must never fail the run
        return {}


def client_directory():
    """Active clients from the shared directory (v1 client_list), with their trade and legal names for matching (design/50 D)."""
    rows, offset = [], 0
    with shared_client() as shared:
        while True:
            page = shared.get('/clients', params={'select': 'client_id,client_name,dba_names,company_legal_name', 'status': 'eq.Active', 'order': 'client_name.asc,client_id.asc', 'limit': '500', 'offset': str(offset)}).json()
            if not isinstance(page, list):
                raise Problem(503, 'DIRECTORY', 'The client directory did not answer.')
            rows.extend({'client_id': str(r['client_id']), 'client_name': str(r['client_name']), 'dba_names': [str(x) for x in (r.get('dba_names') or []) if x],
                         'company_legal_name': str(r.get('company_legal_name') or '')} for r in page)
            if len(page) < 500 or offset >= 50000:
                return rows
            offset += 500


def _field(employee, key):
    return next((f.get('value') for f in (employee or {}).get('field_values') or [] if isinstance(f, dict) and f.get('fieldId') == key), None)


def _password_valid(employee, password):
    hashed = _field(employee, 'ef-11')
    if not isinstance(hashed, str) or not hashed.startswith(('$2a$', '$2b$', '$2y$')):
        bcrypt.checkpw(password.encode()[:72], _dummy)
        return False
    try:
        return bcrypt.checkpw(password.encode()[:72], hashed.encode())
    except ValueError:
        return False


def sign_in(username, password, kind):
    with shared_client() as shared:
        rows = shared.get('/employees', params={'select': 'employee_id,field_values', 'limit': '2',
                          'field_values': 'cs.' + json.dumps([{'fieldId': 'ef-02', 'value': username.strip()}])}).json()
        employee = rows[0] if isinstance(rows, list) and len(rows) == 1 else None
        if not _password_valid(employee, password):
            raise Problem(401, 'SIGN_IN', 'Username or password is incorrect.')
        apps = shared.get('/apps', params={'select': 'members', 'app_id': 'eq.' + settings().APP_ID, 'limit': '2'}).json()
    members = [m for m in ((apps[0].get('members') or []) if isinstance(apps, list) and len(apps) == 1 else [])
               if isinstance(m, dict) and m.get('employeeId') == str(employee['employee_id'])]
    if len(members) != 1 or members[0].get('role') not in ('Admin', 'Member'):
        raise Problem(403, 'MEMBERSHIP', 'You do not have access to this application. Contact its administrator.')
    user = {'id': str(employee['employee_id']), 'name': str(_field(employee, 'ef-01') or employee['employee_id']), 'role': members[0]['role'], 'kind': kind}
    token = secrets.token_urlsafe(48)
    expires = datetime.now(timezone.utc) + timedelta(hours=settings().SESSION_HOURS)
    with connect() as conn:
        conn.execute('insert into vw2_sessions(token_hash,user_id,user_name,role,kind,expires_at) values (%s,%s,%s,%s,%s,%s)',
                     (_hash(token), user['id'], user['name'], user['role'], kind, expires))
    return {'token': token, 'user': user, 'expires_at': expires}


def _hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def current_user(authorization: str | None = Header(default=None), vw2_session: str | None = Cookie(default=None)):
    token = authorization[7:] if authorization and authorization.startswith('Bearer ') else vw2_session
    if not token:
        raise Problem(401, 'LOGIN_REQUIRED', 'Sign in first.')
    with connect() as conn:
        row = conn.execute('select user_id, user_name, role, kind, token_hash from vw2_sessions where token_hash=%s and not revoked and expires_at > now()',
                           (_hash(token),)).fetchone()
    if not row:
        raise Problem(401, 'SESSION_EXPIRED', 'Your session expired. Sign in again.')
    return {'id': row['user_id'], 'name': row['user_name'], 'role': row['role'], 'kind': row['kind'], '_session': row['token_hash']}


def sign_out(user):
    with connect() as conn:
        conn.execute('update vw2_sessions set revoked = true where token_hash = %s', (user['_session'],))


User = Depends(current_user)
