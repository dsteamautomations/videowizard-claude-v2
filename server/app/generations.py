"""The record of every generation of a shot (integration step A, SK 12 Nov 2026): one row per attempt, a list of dated entries, never overwritten.
Step A writes one kind of entry ("handed in"); each later step of the new AI video process appends its own."""
from datetime import datetime, timezone

from psycopg.types.json import Jsonb


def opened(conn, run_id, shot_id, how, entry):
    """A new attempt of the shot with its first entry; the attempt's number is the next one for this shot (the run's lock serialises writers; the unique key guards the rest)."""
    entry = {'at': datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z'), **entry}
    return conn.execute('insert into vw2_generations(run_id, shot_id, attempt, how, record) '
                        'select %s, %s, coalesce(max(attempt), 0) + 1, %s, %s from vw2_generations where run_id=%s and shot_id=%s '
                        'returning attempt, how, verdict, record, created_at, updated_at', (run_id, shot_id, how, Jsonb([entry]), run_id, shot_id)).fetchone()


def of_shot(conn, run_id, shot_id):
    """Every attempt of the shot, oldest first."""
    return [dict(r) for r in conn.execute('select attempt, how, verdict, record, created_at, updated_at from vw2_generations where run_id=%s and shot_id=%s order by attempt', (run_id, shot_id)).fetchall()]


def _now():
    return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')


def add(conn, run_id, shot_id, how, entry):
    """One more dated entry on the shot's open attempt of this kind (the latest row with no verdict); a new attempt when there is none."""
    entry = {'at': _now(), **entry}
    row = conn.execute('update vw2_generations set record = record || %s, updated_at = now() where id = (select id from vw2_generations where run_id=%s and shot_id=%s and how=%s and verdict is null '
                       'order by attempt desc limit 1) returning attempt', (Jsonb([entry]), run_id, shot_id, how)).fetchone()
    return row or opened(conn, run_id, shot_id, how, entry)


def closed(conn, run_id, shot_id, how, verdict, entry):
    """The open attempt gets its verdict and a last entry; the next step opens a new attempt."""
    add(conn, run_id, shot_id, how, entry)
    conn.execute('update vw2_generations set verdict=%s, updated_at = now() where id = (select id from vw2_generations where run_id=%s and shot_id=%s and how=%s and verdict is null order by attempt desc limit 1)',
                 (verdict, run_id, shot_id, how))
