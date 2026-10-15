"""Object storage: Supabase Storage in production, a local folder for tests and local development.
Interface: put(key, data, mime), get(key), exists(key), signed_upload(key) -> (url, headers), signed_download(key) -> url."""
import hashlib
import uuid
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

    def size(self, key):
        p = self.path(key)
        if not p.exists():
            raise Problem(404, 'STORAGE', 'Object not found.')
        return p.stat().st_size

    def list(self, prefix):
        base = (self.root / prefix)
        return [p.relative_to(self.root).as_posix() for p in base.rglob('*') if p.is_file()] if base.exists() else []

    def delete(self, keys):
        for k in keys:
            p = self.path(k)
            if p.exists():
                p.unlink()

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
            r = httpx.request(method, self.url + path, headers={**self.headers, **kw.pop('headers', {})}, timeout=kw.pop('timeout', 120), **kw)
        except httpx.RequestError as exc:
            raise Problem(503, 'STORAGE', f'Storage not reachable ({exc.__class__.__name__}).') from None
        if not r.is_success:
            raise Problem(404 if r.status_code == 404 else 502, 'STORAGE', f'Storage returned {r.status_code}.')
        return r

    def put(self, key, data, mime=None, waits=(5, 15, 30)):
        """15 Oct 2026: a 513 MB film hit WriteTimeout once and the render failed. Retry like the plugin does; allow slow writes."""
        import time
        for attempt, wait in enumerate((*waits, None)):
            try:
                return self._call('POST', f'/storage/v1/object/{self.bucket}/{quote(key, safe="/")}', content=data, timeout=httpx.Timeout(120, write=600),
                                  headers={'Content-Type': mime or 'application/octet-stream', 'x-upsert': 'true'})
            except Problem as exc:
                if wait is None or exc.status != 503:
                    raise
                time.sleep(wait)

    def get(self, key):
        # Ticket 7 (15 Oct 2026): Supabase's CDN served a cached session.json right after an overwrite (cf-cache-status HIT),
        # so recorded scenes vanished. A unique query value forces a fresh read.
        return self._call('GET', f'/storage/v1/object/{self.bucket}/{quote(key, safe="/")}?nocache={uuid.uuid4().hex}').content

    def exists(self, key):
        try:
            self._call('HEAD', f'/storage/v1/object/{self.bucket}/{quote(key, safe="/")}')
            return True
        except Problem:
            return False

    def signed_upload(self, key):
        data = self._call('POST', f'/storage/v1/object/upload/sign/{self.bucket}/{quote(key, safe="/")}').json()
        return self.url + '/storage/v1' + data['url'], {'x-upsert': 'true'}

    def size(self, key):
        info = self._call('GET', f'/storage/v1/object/info/{self.bucket}/{quote(key, safe="/")}').json()
        return int(info.get('size') or (info.get('metadata') or {}).get('size') or -1)

    def list(self, prefix):
        out, offset = [], 0
        while True:
            page = self._call('POST', f'/storage/v1/object/list/{self.bucket}', json={'prefix': prefix, 'limit': 1000, 'offset': offset}).json()
            for o in page:
                if o.get('id'):
                    out.append(f"{prefix}/{o['name']}")
                else:
                    out += self.list(f"{prefix}/{o['name']}")
            if len(page) < 1000:
                return out
            offset += 1000

    def delete(self, keys):
        for i in range(0, len(keys), 100):
            self._call('DELETE', f'/storage/v1/object/{self.bucket}', json={'prefixes': keys[i:i + 100]})

    def signed_download(self, key, seconds=3600):
        data = self._call('POST', f'/storage/v1/object/sign/{self.bucket}/{quote(key, safe="/")}', json={'expiresIn': seconds}).json()
        return self.url + '/storage/v1' + data['signedURL']


def storage():
    local = settings().STORAGE_LOCAL_DIR
    return LocalStorage(local) if local else SupabaseStorage()


HASH_ON_RECEIPT_MAX = 8 * 1024 * 1024


def verify(store, key, sha256, bytes_):
    """Receipt check: the object exists with the declared size; small files are also hashed here. Large files (clips, films)
    are hashed by whoever downloads them (analysis and render check the sha before use), so the receipt never re-downloads
    hundreds of MB over a slow line (defect 6, 15 Oct 2026)."""
    if bytes_ > HASH_ON_RECEIPT_MAX:
        if store.size(key) != bytes_:
            raise Problem(409, 'FILE_MISMATCH', 'The stored file does not match the declared size. Upload it again.')
        return
    data = store.get(key)
    if len(data) != bytes_ or hashlib.sha256(data).hexdigest() != sha256:
        raise Problem(409, 'FILE_MISMATCH', 'The stored file does not match the declared size and hash. Upload it again.')
