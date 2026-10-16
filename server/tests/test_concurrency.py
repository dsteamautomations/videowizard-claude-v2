"""Ticket 9 (16 Oct 2026): two finished image jobs were lost because the worker's read-modify-write of the visuals session raced the
server and the other workers. Every writer of a run's session now takes the same per-run lock."""
import json
import re
import threading
import time
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

from app import jobs, visual_workers as VW, visuals_stage as VS


class SlowStore:
    """In-memory storage whose reads are slow, so two unlocked writers would both read before either writes."""
    def __init__(self, data):
        self.data = data

    def get(self, k):
        value = self.data[k]
        time.sleep(0.4)
        return value

    def put(self, k, v, mime=None):
        self.data[k] = v


def test_two_images_finishing_together_are_both_recorded(database, monkeypatch):
    run_id = '11111111-1111-1111-1111-111111111111'
    k = f'{run_id}/visuals/session.json'
    session = {'references': {r: {'id': r, 'status': 'generating', 'job_id': f'j-{r}'} for r in ('trolley', 'house2')}}
    store = SlowStore({k: json.dumps(session).encode()})
    monkeypatch.setattr(VW, 'storage', lambda: store)
    monkeypatch.setattr(jobs, 'finish', lambda *a, **kw: None)          # no job rows needed: the lock is what is under test
    monkeypatch.setattr(jobs, 'record_file', lambda *a, **kw: None)

    def finish(ref):
        result = {'key': f'{run_id}/visuals/references/{ref}.png', 'sha256': ref * 4, 'bytes': 10, 'width': 1, 'height': 1}
        with psycopg.connect(database, row_factory=dict_row) as conn:
            VW.finalize_image(conn, {'id': f'j-{ref}', 'run_id': run_id, 'request': {'reference': {'id': ref}}}, 'retained', result, None, 4, None)
    threads = [threading.Thread(target=finish, args=(r,)) for r in ('trolley', 'house2')]
    [t.start() for t in threads]
    [t.join() for t in threads]
    refs = json.loads(store.data[k])['references']
    assert {r['status'] for r in refs.values()} == {'candidate'}, refs   # before the fix one of them stayed 'generating'


def test_a_reference_left_generating_is_repaired_from_its_finished_job(monkeypatch):
    monkeypatch.setattr(jobs, 'record_file', lambda *a, **kw: None)
    rows = {'j1': {'status': 'retained', 'result': {'key': 'k1', 'sha256': 'a' * 64, 'bytes': 5, 'width': 2, 'height': 2}, 'error': None, 'cost': 4},
            'j2': {'status': 'failed', 'result': {}, 'error': 'provider refused', 'cost': None},
            'j3': {'status': 'running', 'result': None, 'error': None, 'cost': None}}

    class Conn:
        def execute(self, sql, params):
            return type('C', (), {'fetchone': lambda s: rows.get(params[0])})()
    session = {'references': {'a': {'status': 'generating', 'job_id': 'j1'}, 'b': {'status': 'generating', 'job_id': 'j2'},
                              'c': {'status': 'generating', 'job_id': 'j3'}, 'd': {'status': 'approved', 'job_id': 'j1'}}}
    assert VS.reconcile(Conn(), {'id': 'r'}, session) == 2
    refs = session['references']
    assert (refs['a']['status'], refs['a']['sha256'], refs['b']['status'], refs['c']['status'], refs['d']['status']) == ('candidate', 'a' * 64, 'failed', 'generating', 'approved')


def test_every_request_that_saves_a_session_takes_the_run_lock_and_no_route_is_defined_twice():
    from app.main import app
    from collections import Counter
    counts = Counter((m, r.path) for r in app.routes for m in (getattr(r, 'methods', None) or []))
    assert [k for k, v in counts.items() if v > 1] == []
    src = (Path(__file__).resolve().parents[1] / 'app' / 'main.py').read_text(encoding='utf-8')
    for name in ('visuals_status', 'planning_status', 'stage2_status', 'stage3_status'):
        body = re.search(rf'def {name}\(.*?\n(.*?)\n\n', src, re.S).group(1)
        assert 'lock=True' in body, name


# ---------- ticket 12: two shots sharing one file ----------

def test_a_recorded_gap_keeps_every_shot_that_shares_one_file():
    files = [{'name': 'S4-asset.png', 'key': 'run/visuals/placeholder.png', 'sha256': 'p'}, {'name': 'S5-asset.png', 'key': 'run/visuals/placeholder.png', 'sha256': 'p'},
             {'name': 'ref-1.png', 'key': 'run/visuals/references/1.png', 'sha256': 'r'}, {'name': 'ref-1.png', 'key': 'run/visuals/references/1.png', 'sha256': 'r'}]
    assert [f['name'] for f in VS.unique_by_name(files)] == ['S4-asset.png', 'S5-asset.png', 'ref-1.png']


def test_assembly_finds_a_shared_file_in_a_gap_recorded_before_the_fix():
    from app.stage3.assembly import fill_file
    files = [{'name': 'S4-asset.png', 'key': 'run/visuals/placeholder.png', 'sha256': 'p', 'bytes': 1}]       # S5's entry was dropped
    s5 = {'shot_id': 'S5', 'source': 'asset', 'kind': 'still'}
    assert fill_file(files, s5, 'S5-asset.png', {'S5': {'key': 'run/visuals/placeholder.png', 'sha256': 'p'}})['name'] == 'S5-asset.png'
    assert fill_file(files, s5, 'S5-asset.png', {'S5': {'key': 'run/visuals/placeholder.png', 'sha256': 'other'}}) is None   # different file: refused
    assert fill_file(files, s5, 'S5-asset.png', {}) is None
    assert fill_file(files, {'shot_id': 'T1', 'source': 'take'}, 'T1.mp4', {}) is None                       # takes are never guessed
