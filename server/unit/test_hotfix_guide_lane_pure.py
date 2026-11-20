"""Hotfix (VW-24, 20 Nov 2026): a scene's check frames run in a lane of their own, so they do not wait behind a 16-minute guide render; the check
frames of a scene that was replaced are not rendered. No database: the connection is a recorder."""
import contextlib

from app import guide_worker as GW, jobs, worker
from app import visual_workers


class Conn:
    """Answers the worker's SQL from a small script and keeps what was asked."""

    def __init__(self, running, queued):
        self.running, self.queued, self.sql = set(running), list(queued), []

    def execute(self, sql, params=()):
        self.sql.append((sql, tuple(params)))
        self._row = None
        if sql.startswith("select count(*) as n from vw2_jobs where status='running' and provider='guide'"):
            self._row = {'n': 1 if params[0] in self.running else 0}
        elif sql.startswith("select count(*) as n from vw2_jobs where status='running' and provider in"):
            self._row = {'n': 0}
        elif 'update vw2_jobs set status = case' in sql:
            provider, kind = params[0], params[1]
            hit = next((j for j in self.queued if j['provider'] == provider and (kind is None or j['request']['kind'] == kind)), None)
            if hit:
                self.queued.remove(hit)
            self._row = hit
        return self

    def fetchone(self):
        return self._row


def run_tick(monkeypatch, conn):
    done = []
    monkeypatch.setattr(GW, 'connect', lambda: contextlib.nullcontext(conn))
    monkeypatch.setattr(GW, 'process', lambda job, renew=None: ('ready', {}, None, None, None))
    monkeypatch.setattr(GW, 'finish', lambda job, *a: done.append(job['request']['kind']))
    monkeypatch.setattr(worker, 'STOP', False, raising=False)
    monkeypatch.setattr(visual_workers, 'renders_free', lambda c, cap: True)
    GW.tick()
    return done


def job(kind, n=1):
    return {'id': f'{kind}-{n}', 'provider': 'guide', 'request': {'kind': kind}}


def test_check_frames_are_taken_while_a_render_runs(monkeypatch):
    conn = Conn(running={'guide-render'}, queued=[job('guide-render'), job('guide-frames')])
    assert run_tick(monkeypatch, conn) == ['guide-frames']   # before: nothing was taken while any guide job ran
    assert [j['request']['kind'] for j in conn.queued] == ['guide-render']   # a second render still waits for the first


def test_one_set_of_check_frames_at_a_time_and_a_render_beside_it(monkeypatch):
    conn = Conn(running={'guide-frames'}, queued=[job('guide-frames'), job('guide-render')])
    assert run_tick(monkeypatch, conn) == ['guide-render']


def test_with_nothing_running_the_frames_come_first_then_the_render(monkeypatch):
    conn = Conn(running=set(), queued=[job('guide-render'), job('guide-frames')])
    assert run_tick(monkeypatch, conn) == ['guide-frames', 'guide-render']


def test_the_frames_of_a_replaced_scene_are_closed_before_a_job_is_taken(monkeypatch):
    conn = Conn(running=set(), queued=[])
    run_tick(monkeypatch, conn)
    sqls = [s for s, _ in conn.sql]
    close = next(i for i, s in enumerate(sqls) if s == GW.SUPERSEDE)
    assert close < next(i for i, s in enumerate(sqls) if 'update vw2_jobs set status = case' in s and conn.sql[i][1][0] == 'guide')
    assert conn.sql[close][1] == (GW.SUPERSEDED,)
    assert "j.status='queued'" in GW.SUPERSEDE and "n.created_at > j.created_at" in GW.SUPERSEDE and "n.unit=j.unit" in GW.SUPERSEDE and "n.run_id=j.run_id" in GW.SUPERSEDE


def test_claim_with_no_kind_is_as_before(monkeypatch):
    conn = Conn(running=set(), queued=[{'id': 'm1', 'provider': 'motion', 'request': {'kind': 'x'}}])
    assert jobs.claim(conn, 'motion')['id'] == 'm1'
    assert conn.sql[-1][1] == ('motion', None, None)
