"""Retained files: signed uploads, receipts (size + hash verified), downloads, and the local-storage routes used in tests/dev."""
import hashlib
from uuid import UUID

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, Response as RawResponse

from . import auth, core
from .db import connect
from .errors import Problem
from .storage import storage, verify

router = APIRouter()
User = auth.User


def _key(run, stage, name):
    if '..' in name or name.startswith('/') or not name.strip():
        raise Problem(422, 'FILE_NAME', 'Invalid file name.')
    return f"{run['id']}/{stage}/{name}"


def sign(conn, user, run, stage, name):
    key = _key(run, stage, name)
    url, headers = storage().signed_upload(key)
    return {'key': key, 'url': url, 'method': 'PUT', 'headers': headers}


def receipt(conn, user, run, key, sha256, bytes_):
    if not key.startswith(f"{run['id']}/"):
        raise Problem(422, 'FILE_KEY', 'That key does not belong to this run.')
    verify(storage(), key, sha256, bytes_)
    stage, name = key.split('/', 2)[1:]
    conn.execute('''insert into vw2_files(key, run_id, stage, name, sha256, bytes) values (%s,%s,%s,%s,%s,%s)
                    on conflict (key) do update set sha256=excluded.sha256, bytes=excluded.bytes, verified_at=now()''',
                 (key, run['id'], stage, name, sha256, bytes_))
    return {'key': key, 'receipt': True}


def received(conn, run_id, keys):
    """Keys of this run that have a verified receipt."""
    if not keys:
        return set()
    return {r['key'] for r in conn.execute('select key from vw2_files where run_id=%s and key = any(%s)', (run_id, list(keys)))}


@router.get('/api/runs/{run_id}/files/{key:path}')
def download(run_id: UUID, key: str, user=User):
    with connect() as conn:
        run = core.load_run(conn, user, run_id)
        row = conn.execute('select * from vw2_files where run_id=%s and key=%s', (run['id'], key)).fetchone()
    if not row:
        raise Problem(404, 'FILE_MISSING', 'No such retained file.')
    return RedirectResponse(storage().signed_download(key), status_code=307)


# Local storage backend only (tests / local dev): PUT and GET objects directly through the server.

@router.put('/files/local/{key:path}')
async def local_put(key: str, request: Request):
    store = storage()
    if not hasattr(store, 'root'):
        raise Problem(404, 'NOT_FOUND', 'Local storage is not enabled.')
    store.put(key, await request.body())
    return {'ok': True}


@router.get('/files/local/{key:path}')
def local_get(key: str):
    store = storage()
    if not hasattr(store, 'root'):
        raise Problem(404, 'NOT_FOUND', 'Local storage is not enabled.')
    return RawResponse(store.get(key), media_type='application/octet-stream')
