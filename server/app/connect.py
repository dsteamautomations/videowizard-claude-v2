"""Connect flow: begin (executor, unauthenticated) → approve (browser session) → executor token works."""
import secrets
from datetime import datetime, timedelta, timezone

from .config import settings
from .errors import Problem


def begin(conn, request_id, token_hash):
    code = secrets.token_hex(4).upper()
    code = code[:4] + '-' + code[4:]
    expires = datetime.now(timezone.utc) + timedelta(minutes=settings().CONNECT_MINUTES)
    row = conn.execute('''insert into vw2_connections(id, token_hash, code, expires_at) values (%s,%s,%s,%s)
                          on conflict (id) do update set id = excluded.id returning id, code, expires_at, token_hash''',
                       (request_id, token_hash, code, expires)).fetchone()
    if row['token_hash'] != token_hash:
        raise Problem(409, 'REQUEST_CONFLICT', 'This request id was used for a different connection.')
    return {'id': str(row['id']), 'code': row['code'], 'expires_at': row['expires_at'],
            'url': settings().APP_ORIGIN.rstrip('/') + '/connect/' + str(row['id'])}


def load(conn, connection_id):
    row = conn.execute('select * from vw2_connections where id = %s', (connection_id,)).fetchone()
    if not row:
        raise Problem(404, 'NOT_FOUND', 'Connection request not found.')
    if row['expires_at'] < datetime.now(timezone.utc):
        raise Problem(410, 'CONNECTION_EXPIRED', 'This connection request expired. Start the connection again from the operator.')
    return row


def status(conn, connection_id):
    row = load(conn, connection_id)
    return {'id': str(row['id']), 'status': 'approved' if row['approved_at'] else 'pending', 'expires_at': row['expires_at']}


def approve(conn, user, connection_id, code):
    if user['kind'] != 'browser':
        raise Problem(403, 'BROWSER_REQUIRED', 'Approve the connection from your signed-in browser.')
    row = load(conn, connection_id)
    if row['approved_at']:
        raise Problem(410, 'CONNECTION_SPENT', 'This connection was already approved.')
    if code.strip().upper() != row['code']:
        raise Problem(400, 'WRONG_CODE', 'That code does not match. Check the code shown by the operator.')
    expires = datetime.now(timezone.utc) + timedelta(hours=settings().SESSION_HOURS)
    conn.execute('insert into vw2_sessions(token_hash,user_id,user_name,role,kind,expires_at) values (%s,%s,%s,%s,%s,%s)',
                 (row['token_hash'], user['id'], user['name'], user['role'], 'executor', expires))
    conn.execute('update vw2_connections set approved_by=%s, approved_at=now() where id=%s', (user['id'], connection_id))
    return {'id': str(connection_id), 'status': 'approved', 'user': user['name']}
