"""scripts/vw24_step7_reset.py (SK, 21 Nov 2026): VW-24 taken back to the end of step 6, so step 7 (AI video) starts fresh. Its real path with a
fake store and a fake connection: the dry run changes nothing and lists the 19 guides; the confirmation words, an open job, an open defect and a
recorded AI video gap each refuse; apply backs the session up first, clears every step 7 key and leaves every step 6 key the same; --undo puts
the same bytes back. Without a database."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import vw24_step7_reset as R   # noqa: E402

LIVE = 'run-1/visuals/session.json'
PLAN_KEY = 'run-1/visuals/plans/d3.json'
VIDEO = [f'S{n}' for n in range(1, 20)]   # the 19 AI video shots, S7 the ponds shot held by the operator
PLAN = {'gaps': [{'gap_id': 'G1', 'scenes': [{'shots': [{'id': s, 'visual_type': 'video'} for s in VIDEO[:10]]}]},
                 {'gap_id': 'G2', 'scenes': [{'shots': [{'id': s, 'visual_type': 'video'} for s in VIDEO[10:]] + [{'id': 'VS1', 'visual_type': 'still'}]}]},
                 {'gap_id': 'G9', 'scenes': [{'shots': [{'id': 'MO1', 'visual_type': 'graphic'}, {'id': 'VS2', 'visual_type': 'still'}]}]}]}


def guide(n):
    g = {'sha256': f'{n:02d}' * 32, 'key': f'run-1/visuals/guides/{n}/scene.json', 'seconds': 5, 'frames': {'job_id': f'gf-{n}', 'status': 'ready'},
         'verdicts': [{'round': 1, 'pass': True}], 'drawing': {'status': 'approved', 'sha256': f'{n:02d}' * 32}, 'stills': [], 'takes': [],
         'render': {'status': 'ready', 'guide_key': 'g.mp4', 'frame1_key': 'f1.png'}}
    if n == 7:   # the ponds shot: three failed checks in a row, held
        g.update(verdicts=[{'round': r, 'pass': False, 'looks': [{'pass': False, 'check': 'c'}]} for r in (1, 2, 3)], drawing={'status': 'proposed'}, render={})
    return g


SESSION = {
    'contract': 'vw2-visuals-session-v1', 'versions': [{'version': 3, 'plan_digest': 'd3', 'file': {'key': PLAN_KEY}}], 'current': 'd3',
    'accepted': {'G1': {'digest': 'a'}, 'G2': {'digest': 'b'}, 'G9': {'digest': 'c'}}, 'choice_selections': {}, 'spec_approvals': {'MO1': {'digest': 's'}},
    'references': {'k1': {'kind': 'keyframe', 'status': 'approved'}}, 'drawings': {'E1': {'status': 'approved'}}, 'round': {'v': 2}, 'golden': {'E1': 'k1'},
    'treatment': {'digest': 't'}, 'font': {'name': 'NotoSans.ttf'}, 'bindings': {}, 'source': {'fps': 25},
    'motion_projects': {'a' * 64: {'shot_id': 'MO1'}}, 'motion_bound': {'MO1': 'a' * 64}, 'motion_stills': {'MO1': {'png': 'p'}},
    'preparations': {'MO1': {'preparation_id': 'r1', 'drawn': True}, 'VS1': {'preparation_id': 'v1'}, 'S3': {'preparation_id': 'p3', 'key': 'k', 'guide': True}},
    'selections': {'MO1': {'job_id': 'job-7'}, 'VS1': {'job_id': 'job-2'}, 'VS2': {'job_id': 'job-3'}, 'S5': {'job_id': 'vj-1'}},
    'reviews': {'job-7': [{'decision': 'accepted'}], 'job-2': [{'decision': 'accepted'}], 'vj-1': [{'decision': 'accepted'}]},
    'take_checks': {'job-7': {}, 'vj-1': {'state': 'pass'}}, 'assets': {'VS2': {'kind': 'still'}, 'S9': {'kind': 'movie'}},
    'recorded_gaps': {'G9': 'cut-9'}, 'guides': {s: guide(n) for n, s in enumerate(VIDEO, 1)},
    'chat_item': {'id': 'layout-held:S7:0707070707', 'at': 'x'}, 'chat_cards_done': ['card-1'],
    'page_refused': {'pic:still:S2:abc': 'refused', 'set:E1': 'kept'}, 'chat_record_wait': {'G1': 'not yet', 'G9': 'later'},
}
STEP7 = {'guides': None, 'preparations': ['S3'], 'selections': ['S5'], 'reviews': ['vj-1'], 'take_checks': ['vj-1'], 'assets': ['S9'],
         'chat_item': None, 'page_refused': ['pic:still:S2:abc'], 'chat_record_wait': ['G1']}


def without_step7(s):
    s = json.loads(json.dumps(s))
    for k, rows in STEP7.items():
        if rows is None:
            s.pop(k, None)
        else:
            for x in rows:
                s[k].pop(x, None)
    s.pop('updated_at', None)
    return s


class Store:
    def __init__(self, files):
        self.files, self.puts = dict(files), []

    def get(self, k):
        return self.files[k]

    def exists(self, k):
        return k in self.files

    def put(self, k, data, mime=None):
        self.puts.append(k)
        self.files[k] = data


class Rows:
    def __init__(self, rows):
        self.rows = rows

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def fetchall(self):
        return self.rows


class Conn:
    def __init__(self, open_jobs=(), defects=(), video_jobs=('vj-1',)):
        self.open_jobs, self.defects, self.video_jobs, self.log, self.locked = list(open_jobs), list(defects), list(video_jobs), [], False

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def execute(self, sql, params=()):
        if 'pg_advisory_xact_lock' in sql:
            assert params == ('run:run-1',)
            self.locked = True
            return Rows([])
        if 'from vw2_runs' in sql:
            return Rows([{'id': 'run-1', 'code': 'VW-24'}])
        if 'from vw2_defects' in sql:
            return Rows([{'id': d} for d in self.defects])
        if 'from vw2_jobs' in sql and 'status = any' in sql:
            return Rows(self.open_jobs)
        if 'from vw2_jobs' in sql and "provider='video'" in sql:
            return Rows([{'id': j} for j in self.video_jobs])
        if 'insert into vw2_log' in sql:
            assert self.locked
            self.log.append(params)
            return Rows([])
        raise AssertionError(sql)


@pytest.fixture
def env(monkeypatch):
    raw = json.dumps(SESSION, indent=1).encode('utf-8')
    store = Store({LIVE: raw, PLAN_KEY: json.dumps({'document': PLAN}).encode('utf-8')})
    box = {'conn': Conn()}
    monkeypatch.setattr(R, 'storage', lambda: store)
    monkeypatch.setattr(R, 'connect', lambda: box['conn'])
    return store, box, raw


def test_dry_run_changes_nothing_and_lists_the_19_guides(env, capsys):
    store, box, raw = env
    R.main(["SK's words"])
    out = capsys.readouterr().out
    assert store.puts == [] and store.files[LIVE] == raw and box['conn'].log == []
    assert '19 guides' in out and all(f'{s}:' in out for s in VIDEO) and 'HELD' in out and 'Dry run: nothing changed' in out
    assert 'No job of VW-24 is queued or running' in out


def test_apply_with_wrong_words_refuses(env):
    store, box, raw = env
    with pytest.raises(SystemExit, match='confirmation words'):
        R.main(["SK's words", '--apply', 'yes reset VW-24 step 7'])
    assert store.puts == [] and box['conn'].log == []


def test_apply_while_a_guide_job_is_queued_refuses(env, capsys):
    store, box, raw = env
    box['conn'] = Conn(open_jobs=[{'id': 'gf-99', 'unit': 'S4', 'provider': 'guide', 'status': 'queued', 'kind': 'guide-frames'}])
    R.main(["SK's words"])
    assert 'would refuse' in capsys.readouterr().out
    with pytest.raises(SystemExit, match='gf-99'):
        R.main(["SK's words", '--apply', R.WORDS])
    assert store.puts == [] and box['conn'].log == []


def test_apply_while_a_defect_is_open_refuses(env):
    store, box, raw = env
    box['conn'] = Conn(defects=[61])
    with pytest.raises(SystemExit, match='open defect'):
        R.main(["SK's words", '--apply', R.WORDS])
    assert store.puts == []


def test_an_ai_video_gap_recorded_into_the_film_refuses(env):
    store, box, raw = env
    s = json.loads(raw)
    s['recorded_gaps']['G1'] = 'cut-1'
    store.files[LIVE] = json.dumps(s).encode('utf-8')
    with pytest.raises(SystemExit, match='G1'):
        R.main(["SK's words", '--apply', R.WORDS])
    assert store.puts == []


def test_apply_backs_up_first_clears_step_7_keeps_step_6_and_undo_restores_the_bytes(env, capsys):
    store, box, raw = env
    backup = R.main(["SK's words", '--apply', R.WORDS])
    assert backup.startswith('run-1/visuals/session.backup-step7-') and backup.endswith('.json')
    assert store.puts == [backup, LIVE] and store.files[backup] == raw and box['conn'].locked
    after = json.loads(store.files[LIVE])
    assert 'guides' not in after and 'chat_item' not in after
    assert without_step7(after) == without_step7(SESSION)   # every step 6 key the same
    assert after['selections'] == {'MO1': {'job_id': 'job-7'}, 'VS1': {'job_id': 'job-2'}, 'VS2': {'job_id': 'job-3'}} and after['recorded_gaps'] == {'G9': 'cut-9'}
    assert len(box['conn'].log) == 1
    entry, quote = box['conn'].log[0][5], box['conn'].log[0][8]
    assert box['conn'].log[0][2] == 'override' and quote == "SK's words" and '19 guides' in entry and backup in entry
    assert f'--undo {backup}' in capsys.readouterr().out
    R.main(["SK's words", '--undo', backup])
    assert store.files[LIVE] == raw and len(box['conn'].log) == 2
    with pytest.raises(SystemExit, match='no step-7 backup'):
        R.main(["SK's words", '--undo', 'run-1/visuals/other.json'])


def test_no_write_when_the_backup_does_not_read_back(env):
    store, box, raw = env
    real = store.get
    store.get = lambda k: b'' if '.backup-step7-' in k else real(k)
    with pytest.raises(SystemExit, match='did not read back the same'):
        R.main(["SK's words", '--apply', R.WORDS])
    assert store.files[LIVE] == raw and box['conn'].log == []
