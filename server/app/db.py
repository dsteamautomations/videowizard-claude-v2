"""Postgres access: one connection per request, plain SQL, migrations applied in order, procedures seeded from JSON."""
import json
from functools import lru_cache
from pathlib import Path

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Json

from .config import settings

ROOT = Path(__file__).resolve().parents[1]


def connect(url=None):
    return psycopg.connect(url or settings().DATABASE_URL, row_factory=dict_row)


def migrate(url=None):
    """Apply migrations/*.sql once each (tracked in vw2_migrations), then upsert procedures/*.json by version."""
    with connect(url) as conn:
        conn.execute('create table if not exists vw2_migrations (name text primary key, applied_at timestamptz not null default now())')
        done = {r['name'] for r in conn.execute('select name from vw2_migrations')}
        for path in sorted((ROOT / 'migrations').glob('*.sql')):
            if path.name not in done:
                conn.execute(path.read_text(encoding='utf-8'))
                conn.execute('insert into vw2_migrations(name) values (%s)', (path.name,))
        for path in sorted((ROOT / 'procedures').glob('*.json')):
            doc = json.loads(path.read_text(encoding='utf-8'))
            conn.execute('insert into vw2_procedures(version, document) values (%s, %s) on conflict (version) do update set document = excluded.document',
                         (doc['version'], Json(doc)))
    stage_table.cache_clear()


@lru_cache(maxsize=64)
def stage_table(version):
    """Stage list for a procedure version, cached in-process (procedures are immutable once published)."""
    with connect() as conn:
        row = conn.execute('select document from vw2_procedures where version = %s', (version,)).fetchone()
    return [dict(s) for s in row['document']['stages']] if row else None
