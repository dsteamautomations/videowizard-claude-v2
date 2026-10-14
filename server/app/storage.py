"""Object storage: Supabase Storage in production, a local folder for tests and local development.
Interface: put(key, data, mime), get(key), exists(key), signed_upload(key) -> (url, headers), signed_download(key) -> url."""
import hashlib
from pathlib import Path
from urllib.parse import quote

import httpx

from .config import settings
from .errors import Problem


class LocalStorage:
    """Files under VW2_STORAGE_LOCAL_DIR; signed URLs are plain server routes (/files/local/{key})."""

    def __init__(self, root):
        self.root = Path(root)

    def path(self, key):
        p = (self.root / key).resolve()
        if self.root.resolve() not in p.parents:
            raise Problem(422, 'FILE_KEY', 'Invalid file key.')
        return p

    def put(self, key, data, mime=None):
        p = self.path(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)

    def get(self, key):
        p = self.path(key)
        if not p.is_file():
            raise Problem(404, 'FILE_MISSING', 'Stored file not found.')
        return p.read_bytes()

    def exists(self, key):
        return self.path(key).is_file()

    def signed_upload(self, key):
        return '/files/local/' + quote(key, safe='/'), {}

    def signed_download(self, key):
        return '/files/local/' + quote(key, safe='/')


class SupabaseStorage:
    def __init__(self):
        cfg = settings()
        self.url = cfg.STORAGE_SUPABASE_URL.rstrip('/')
        if not self.url:  # same Supabase project as the database: derive https://<ref>.supabase.co from postgres.<ref>@
            import re
            m = re.search(r'postgres\.([a-z0-9]+)[:@]', cfg.DATABASE_URL)
            self.url = f'https://{m.group(1)}.supabase.co' if m else ''
        key = cfg.STORAGE_SUPABASE_SERVICE_KEY.get_secret_value()
        if not self.url or not key or not cfg.STORAGE_BUCKET:
            raise Problem(503, 'CONFIGURATION', 'The administrator must configure file storage (service key and bucket).')
        self.bucket = cfg.STORAGE_BUCKET
        self.headers = {'apikey': key, **({} if key.startswith('sb_secret_') else {'Authorization': 'Bearer ' + key})}

    def _call(self, method, path, **kw):
        try:
            r = httpx.request(method, self.url + path, headers={**self.headers, **kw.pop('headers', {})}, timeout=120, **kw)
        except httpx.RequestError as exc:
            raise Problem(503, 'STORAGE', f'Storage not reachable ({exc.__class__.__name__}).') from None
        if not r.is_success:
            raise Problem(404 if r.status_code == 404 else 502, 'STORAGE', f'Storage returned {r.status_code}.')
        return r

    def put(self, key, data, mime=None):
        self._call('POST', f'/storage/v1/object/{self.bucket}/{quote(key, safe="/")}', content=data,
                   headers={'Content-Type': mime or 'application/octet-stream', 'x-upsert': 'true'})

    def get(self, key):
        return self._call('GET', f'/storage/v1/object/{self.bucket}/{quote(key, safe="/")}').content

    def exists(self, key):
        try:
            self._call('HEAD', f'/storage/v1/object/{self.bucket}/{quote(key, safe="/")}')
            return True
        except Problem:
            return False

    def signed_upload(self, key):
        data = self._call('POST', f'/storage/v1/object/upload/sign/{self.bucket}/{quote(key, safe="/")}').json()
        return self.url + '/storage/v1' + data['url'], {'x-upsert': 'true'}

    def signed_download(self, key, seconds=3600):
        data = self._call('POST', f'/storage/v1/object/sign/{self.bucket}/{quote(key, safe="/")}', json={'expiresIn': seconds}).json()
        return self.url + '/storage/v1' + data['signedURL']


def storage():
    local = settings().STORAGE_LOCAL_DIR
    return LocalStorage(local) if local else SupabaseStorage()


def verify(store, key, sha256, bytes_):
    """Receipt check: the object exists with the declared size and hash. ponytail: hashes by downloading; fine for
    voice files and single clips, revisit with a streaming hash if clips grow past a few hundred MB."""
    data = store.get(key)
    if len(data) != bytes_ or hashlib.sha256(data).hexdigest() != sha256:
        raise Problem(409, 'FILE_MISMATCH', 'The stored file does not match the declared size and hash. Upload it again.')
