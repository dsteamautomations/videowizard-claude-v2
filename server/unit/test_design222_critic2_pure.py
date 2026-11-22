"""design/222, the second critic's points on cfabf4d (20 Nov 2026), each with a test that failed first; and the requirement's tests that had none
(16, 17, 21, 22). The answers go through the page's own route (`page_flow._pictures_answer`) with nothing mocked: a real session in a store, a fake
connection that holds the job rows. Without a database."""
import pytest

from app import chat_flow as CF, guide as G, page_flow as PF, pictures as P, takes as T, visuals_stage as V
from app.errors import Problem
from test_design151_refs_pure import NEW
from test_design222_takes_pure import NOW, RUN, SHA, USER as OP, guide, held, job, line_of, look, plan, rec, session, shot, states   # noqa: F401
from test_guide_route_pure import TAKE_WORDS, TakeConn, ready, scene, spec10, still_made, take_film   # noqa: F401 (`take_film` is the fixture)
from test_visuals_stage_pure import USER, saved


# ---------- the harness: a film with one AI video shot (VS1), its take made by the real functions ----------

class R:
    def __init__(self, rows):
        self.rows = rows

    def fetchall(self):
        return self.rows

    def fetchone(self):
        return self.rows[0] if self.rows else None


class PageConn(TakeConn):
    """Plus every take's job row, as `take_jobs`, `select_take` and the spend read them."""

    def __init__(self):
        super().__init__()
        self.takes = []

    def execute(self, sql, params=()):
        if 'select id, unit, provider, status, request, result' in sql:
            return R([t for t in self.takes if len(params) < 2 or t['unit'] == params[1]])
        if 'select provider, status, request, cost from vw2_jobs' in sql:
            return R([])
        if 'select * from vw2_jobs where id=' in sql:
            return R([t for t in self.takes if str(t['id']) == str(params[0])])
        return super().execute(sql, params)


def landed(conn, store, job_id, sha, fail=()):
    """The take comes back: its job row, and its check record with Claude's look."""
    conn.takes.append({'id': job_id, 'run_id': 'run-1', 'unit': 'VS1', 'provider': 'video', 'status': 'ready', 'request': conn.queued[-1]['request'], 'error': None, 'cost': None, 'attempt': 1,
                       'created_at': '2026-11-19T10:00:00+00:00', 'updated_at': '2026-11-19T10:00:00+00:00',
                       'result': {'key': f'run-1/visuals/takes/{job_id}.mp4', 'sha256': sha, 'bytes': 9, 'evidence': {'timing_matches_placement': True, 'duration_seconds': 10.0}}})
    s = saved(store)
    s.setdefault('take_checks', {})[job_id] = rec(look=look(fail=fail, sha=sha))
    s['round'] = {'v': 2, 'kept': True, 'pass': 'complete', 'elements': {}}
    V.save_session(store, NEW, s)


@pytest.fixture
def film(take_film, monkeypatch):
    store, _ = take_film
    conn = PageConn()
    wrote = []
    monkeypatch.setattr(T.runlog, 'write', lambda c, row: wrote.append(row))
    ready(store, conn)
    job_id = G.shoot(conn, store, USER, NEW, [], 'VS1', 'Shoot.')['job_id']
    landed(conn, store, job_id, 'sha-take-1')
    return store, conn, job_id, wrote


def item(store, conn):
    ctx = {**CF._ctx(conn, store, USER, NEW, []), 'page': True}
    return ctx, next(i for i in CF._waiting_items(ctx) if (i.get('_line') or {}).get('kind') == 'take')


def on_page(store, conn, choice, words=''):
    """One answer as the page's record sends it: by the line's item, through `_pictures_answer`."""
    ctx, it = item(store, conn)
    return PF._pictures_answer(ctx, {'item': it['id'], 'key': 'pic:' + it['id']}, choice, words)


def second_take(store, conn, words='He walks more slowly.'):
    """Make another on the page, the cause in the words, the words changed, the take sent with the page's word, and it comes back."""
    on_page(store, conn, 'again', words)
    G.set_cause(conn, store, USER, NEW, [], 'VS1', 'words', 'The walk was too fast.', 'slower pace words')
    G.set_prompt(conn, store, USER, NEW, [], 'VS1', TAKE_WORDS + ' They walk at an easy pace.')
    job2 = G.shoot(conn, store, USER, NEW, [], 'VS1', '')['job_id']
    landed(conn, store, job2, 'sha-take-2')
    return job2


# ---------- point 6: the page's real route, nothing mocked ----------


def on_page_is_stale(store, conn, job_id):
    ctx = {**CF._ctx(conn, store, USER, NEW, []), 'page': True}
    return PF._pictures_answer(ctx, {'item': f'take:{job_id}'}, 'select', '') is None and not [i for i in CF._waiting_items(ctx) if (i.get('_line') or {}).get('kind') == 'take']


# ---------- point 3: an order does not outlive the shot's resolution ----------


# ---------- point 1: one rejected take does not hide the others ----------


# ---------- point 2: an answer is stale when the check changed after the take was shown ----------


# ---------- point 9 (E18): an open question on the shot ----------

def test_p9_a_take_of_a_shot_with_an_open_question_is_not_offered(held, monkeypatch):
    s, p = session(), plan(shot('S1'))
    s['guides'].update(S1=guide(takes=['j1']))
    s['take_checks'].update(j1=rec(look=look()))
    s['questions'] = {'S1': {'question': 'Which gate?', 'choices': ['a', 'b']}}
    held(s, p)
    monkeypatch.setattr(V, 'item_link', lambda *a: '')
    assert states(s, p, [job('j1')]) == [('S1', 'waiting for you in the chat')]
    assert [w['kind'] for w in V.waiting(s, p, 'VW-99', [job('j1')])] == ['question to answer']


# ---------- point 10: "Make another" on a take with no guide entry ----------


# ---------- point 8: a take whose page video cannot be made ----------

def test_p8_a_take_with_no_page_video_shows_its_frames(held, monkeypatch):
    s, p = session(), plan(shot('S1'))
    s['guides'].update(S1=guide(takes=['j1']))
    s['take_checks'].update(j1=rec(look=look()))
    held(s, p)
    line = line_of(s, p, [job('j1')])
    assert [(x['role'], x.get('take')) for x in line['pics'] if x['role'] == 'sheet'] == [('sheet', 1)]

    def no_copy(store, key, mark=''):
        raise ValueError('over the page limit')
    monkeypatch.setattr(PF, 'video_copy', no_copy)
    page = PF._with_videos(None, {'lines': [line]})
    v = page['lines'][0]['takes'][0]['video']
    assert v['code'] == '' and v['none'] == T.W['video_none'] == 'The take cannot be played here: these are its frames, in order.' and 'videos' not in page


# ---------- requirement tests 16 and 17, and E30: the cause is the still, the cause is the layout ----------


# ---------- requirement test 21: three orders and a limit that allows two ----------


# ---------- points 7 and 11: the counts in `vw visuals status`; the decisions in the log ----------

def test_the_status_carries_step_7s_line_of_counts(film):
    store, conn, job_id, wrote = film
    out = V.status(conn, store, NEW, [])
    assert 'AI video: 1 made.' in out['step6']
