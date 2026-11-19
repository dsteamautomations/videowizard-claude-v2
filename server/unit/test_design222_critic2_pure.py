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

def test_select_on_the_page_records_the_review_the_selection_and_a_decision(film):
    store, conn, job_id, wrote = film
    said, out = on_page(store, conn, 'select')
    s = saved(store)
    assert said == 'Select' and s['selections']['VS1']['job_id'] == job_id and s['reviews'][job_id][-1]['decision'] == 'accepted'
    assert conn.rows[-1]['verdict'] == 'accepted'
    assert [(w['kind'], w['about'], w['entry']) for w in wrote] == [('decision', 'shot VS1', 'take 1 selected')]
    assert on_page_is_stale(store, conn, job_id)                                     # requirement test 22: "done" sent twice changes nothing


def on_page_is_stale(store, conn, job_id):
    ctx = {**CF._ctx(conn, store, USER, NEW, []), 'page': True}
    return PF._pictures_answer(ctx, {'item': f'take:{job_id}'}, 'select', '') is None and not [i for i in CF._waiting_items(ctx) if (i.get('_line') or {}).get('kind') == 'take']


def test_reject_on_the_page_records_the_words_orders_nothing_and_says_what_the_assistant_asks(film):
    store, conn, job_id, wrote = film
    n = len(conn.queued)
    on_page(store, conn, 'reject', 'The mother walks off the verandah.')
    s = saved(store)
    assert s['reviews'][job_id][-1]['decision'] == 'rejected' and s['reviews'][job_id][-1]['notes'] == 'The mother walks off the verandah.' and 'again' not in s['guides']['VS1']
    assert len(conn.queued) == n and conn.rows[-1]['verdict'] == 'rejected'
    assert 'ask the operator what happens to the shot' in T.rejected_due(s, V.current_plan(store, s), conn.takes)
    assert wrote[-1]['entry'] == 'take 1 rejected, no new take ordered' and wrote[-1]['quote'] == 'The mother walks off the verandah.'


def test_make_another_on_the_page_then_the_take_is_sent_once_with_no_second_card(film):
    store, conn, job_id, wrote = film
    on_page(store, conn, 'again', 'He walks more slowly.')
    s = saved(store)
    assert s['guides']['VS1']['again']['words'] == 'He walks more slowly.' and wrote[-1]['entry'].startswith('another take ordered on the page: 10 s, about ₹')
    assert [i['kind'] for i in CF._guide_items(CF._ctx(conn, store, USER, NEW, []))] == []            # no Shoot card: the word is given
    assert states(s, V.current_plan(store, s), conn.takes) == [('VS1', 'being redone')]
    G.set_cause(conn, store, USER, NEW, [], 'VS1', 'words', 'The walk was too fast.', 'slower pace words')
    G.set_prompt(conn, store, USER, NEW, [], 'VS1', TAKE_WORDS + ' They walk at an easy pace.')
    n = len(conn.queued)
    job2 = G.shoot(conn, store, USER, NEW, [], 'VS1', '')['job_id']
    s = saved(store)
    assert len(conn.queued) == n + 1 and s['guides']['VS1']['again']['sent'] == job2 and s['guides']['VS1']['takes'][-1]['quote'] == 'Make another: He walks more slowly.'
    conn.open_take = None
    with pytest.raises((ValueError, Problem)):                                      # the word is used: one order, one take
        G.shoot(conn, store, USER, NEW, [], 'VS1', '')


def test_use_take_1_after_all_selects_it_and_leaves_the_newer_take_and_the_record_clean(film):     # points 4 and 5
    store, conn, job1, wrote = film
    job2 = second_take(store, conn)
    rows_before = len(conn.rows)
    s = saved(store)
    s['questions'] = {'VS1': {'question': 'Which gate?', 'choices': ['a', 'b']}}                     # an open question on the shot: selecting is refused
    V.save_session(store, NEW, s)
    ctx = {**CF._ctx(conn, store, USER, NEW, []), 'page': True}
    with pytest.raises((ValueError, Problem)):
        T.answer(conn, store, USER, NEW, [], 'VS1', conn.takes, 'old:1', 'Use take 1 after all', '')
    s = saved(store)
    assert s['reviews'][job1][-1]['decision'] == 'rejected' and 'VS1' not in s['selections']         # point 5: the no-words path left take 1 as it was
    del s['questions']['VS1']
    V.save_session(store, NEW, s)
    T.answer(conn, store, USER, NEW, [], 'VS1', conn.takes, 'old:1', 'Use take 1 after all', '')
    s = saved(store)
    assert s['selections']['VS1']['job_id'] == job1 and s['reviews'][job1][-1]['decision'] == 'accepted'
    assert not s['reviews'].get(job2)                                                               # point 4: the newer take gets no review, so no rejection reason reaches the feedback
    assert len(conn.rows) == rows_before and conn.rows[-1]['verdict'] == 'accepted'                 # ... and no new attempt is opened and closed as rejected
    assert not any('earlier take was used' in str(f) for f in s.get('feedback') or [])
    assert [w['kind'] for w in V.waiting(s, V.current_plan(store, s), 'VW-99', conn.takes, gate=False) if w['kind'] == 'take to select'] == []   # the newer take is not asked about again
    assert wrote[-1]['entry'] == 'take 1 selected after all'


# ---------- point 3: an order does not outlive the shot's resolution ----------

def test_p3_selecting_the_shot_drops_the_order_and_a_new_take_is_refused(film):
    store, conn, job_id, wrote = film
    on_page(store, conn, 'again', 'He walks more slowly.')
    V.select_take(conn, store, USER, NEW, [], job_id, 'Keep it after all.', 'On a second look it reads fine.')      # in the chat, after all
    s = saved(store)
    assert 'again' not in s['guides']['VS1'] and T.again_due(s, V.current_plan(store, s), conn.takes) == ''
    with pytest.raises((ValueError, Problem), match='selected'):
        G.shoot(conn, store, USER, NEW, [], 'VS1', 'Shoot it again.')


# ---------- point 1: one rejected take does not hide the others ----------

def test_p1_a_rejected_take_keeps_the_page_open_for_the_unanswered_ones(held, monkeypatch):
    s, p = session(), plan(shot('S1'), shot('S2', start=129, end=260), shot('S3', start=260, end=400))
    s['guides'].update(S1=guide(takes=['j1']), S2=guide(takes=['j2']), S3=guide(takes=['j3']))
    s['take_checks'].update(j1=rec(look=look()), j2=rec(look=look()), j3=rec(look=look()))
    held(s, p)
    monkeypatch.setattr(V, 'item_link', lambda *a: '')
    rows = [job('j1'), job('j2', 'S2'), job('j3', 'S3')]
    s['reviews'].update(j1=[{'decision': 'rejected', 'notes': 'x'}])                                 # a plain Reject
    assert T.complete(T.expected(s, p, rows, NOW)) and [w['group'] for w in V.waiting(s, p, 'VW-99', rows)] == ['S2', 'S3']
    s['guides']['S1']['again'] = {'job_id': 'j1', 'words': 'x'}                                      # Make another, its take being made
    rows2 = rows[:1] + [job('j1b', 'S1', status='running')] + rows[1:]
    assert T.complete(T.expected(s, p, rows2, NOW)) and [w['group'] for w in V.waiting(s, p, 'VW-99', rows2)] == ['S2', 'S3']
    rows3 = rows[:1] + [job('j1b', 'S1')] + rows[1:]                                                 # the remake is back, not checked yet: it is not offered; the others are
    s['take_checks']['j1b'] = rec()
    assert [w['group'] for w in V.waiting(s, p, 'VW-99', rows3)] == ['S2', 'S3']
    s['take_checks']['j1b'] = rec(look=look())
    assert [w['group'] for w in V.waiting(s, p, 'VW-99', rows3)] == ['S1', 'S2', 'S3']
    s2 = session()
    s2['guides'].update(S1=guide(), S2=guide(), S3=guide())
    s2['take_checks'].update(j1=rec(look=look()), j2=rec(look=look()))
    held(s2, p)
    assert not T.complete(T.expected(s2, p, rows[:2] + [job('j3', 'S3', status='running')], NOW))    # a FIRST take still being made keeps the page closed (D9)


# ---------- point 2: an answer is stale when the check changed after the take was shown ----------

def test_p2_the_items_id_changes_with_the_check(held):
    s, p = session(), plan(shot('S1'))
    s['guides'].update(S1=guide(takes=['j1']))
    s['take_checks'].update(j1=rec(asked_at='2026-11-19T11:00:00+00:00'))
    held(s, p)
    j = job('j1')
    not_checked = T.item_id(s, j)
    s['take_checks']['j1'] = rec(look=look(fail=('objects',)))
    failed = T.item_id(s, j)
    s['take_checks']['j1'] = rec(look=look())
    assert not_checked.startswith('take:j1:') and len({not_checked, failed, T.item_id(s, j)}) == 3


def test_p2_an_answer_given_to_the_take_as_shown_before_its_check_arrived_is_stale(film):
    store, conn, job_id, wrote = film
    s = saved(store)
    s['take_checks'][job_id] = rec(asked_at='2026-11-19T09:00:00+00:00')                             # shown as not checked
    V.save_session(store, NEW, s)
    ctx, shown = item(store, conn)
    s = saved(store)
    s['take_checks'][job_id] = rec(look=look(fail=('objects',), sha='sha-take-1'))                   # a failing look arrives before "done"
    V.save_session(store, NEW, s)
    ctx = {**CF._ctx(conn, store, USER, NEW, []), 'page': True}
    assert PF._pictures_answer(ctx, {'item': shown['id']}, 'select', 'I looked at it myself.') is None and 'VS1' not in saved(store)['selections']


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

def test_p10_no_order_without_a_guide_and_nothing_is_saved(held, monkeypatch):
    s, p = session(), plan(shot('S1'))
    s['take_checks'].update(j1=rec(look=look()))
    held(s, p)
    seen = []
    monkeypatch.setattr(V, 'review_take', lambda *a, **k: seen.append(a) or {})
    assert [b['choice'] for b in line_of(s, p, [job('j1')])['buttons']] == ['select', 'reject']
    with pytest.raises(ValueError, match='no guide'):
        T.answer(None, None, OP, RUN, {}, 'S1', [job('j1')], 'again', 'Make another', 'Slower.')
    assert seen == []


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

def test_16_the_cause_is_the_still_its_card_comes_first_then_the_take_with_no_shoot_card(film):
    store, conn, job_id, wrote = film
    on_page(store, conn, 'again', 'The mother stands at the gate, not on the verandah.')
    G.set_cause(conn, store, USER, NEW, [], 'VS1', 'still', 'The still has the mother on the verandah.', 'a new still')
    new = still_made(store, conn)
    s = saved(store)
    plan_ = V.current_plan(store, s)
    assert states(s, plan_, conn.takes) == [('VS1', 'waiting for you in the chat')]                 # E30: its still's card waits
    assert [i['kind'] for i in CF._guide_items(CF._ctx(conn, store, USER, NEW, []))] == ['still']
    G.approve_still(conn, store, USER, NEW, [], 'VS1', new, 'sha-still', 'Yes.')
    s = saved(store)
    assert [i['kind'] for i in CF._guide_items(CF._ctx(conn, store, USER, NEW, []))] == [] and states(s, plan_, conn.takes) == [('VS1', 'being redone')]
    assert '`vw guide shoot --shot VS1`' in T.again_due(s, plan_, conn.takes) and s['guides']['VS1']['again']['words'].startswith('The mother stands')


def test_17_the_cause_is_the_layout_the_order_is_kept_and_its_drawing_card_comes_first(film):
    store, conn, job_id, wrote = film
    on_page(store, conn, 'again', 'The father starts nearer the gate.')
    G.set_cause(conn, store, USER, NEW, [], 'VS1', 'guide', 'His path starts too far left.', 'his start moves right')
    changed = spec10()
    changed['people'][2]['at'] = [4.0, 1.2, 0.3]
    scene(store, conn, changed)
    s = saved(store)
    assert s['guides']['VS1']['again']['words'] == 'The father starts nearer the gate.' and s['guides']['VS1']['drawing']['status'] == 'proposed'
    assert states(s, V.current_plan(store, s), conn.takes) == [('VS1', 'waiting for you in the chat')]


# ---------- requirement test 21: three orders and a limit that allows two ----------

def test_21_three_orders_and_a_limit_for_two_the_third_is_dropped_and_named(held, monkeypatch):
    s, p = session(), plan(shot('S1', title='One'), shot('S2', start=129, end=260, title='Two'), shot('S3', start=260, end=400, title='Three'))
    for n in (1, 2, 3):
        s['guides'][f'S{n}'] = guide(takes=[f'j{n}'], again={'job_id': f'j{n}', 'words': 'x'})
        s['reviews'][f'j{n}'] = [{'decision': 'rejected', 'notes': 'x'}]
    held(s, p)
    spent = []

    def cap(conn, run, session_, amount, what):
        if len(spent) >= 2:
            raise Problem(409, 'VISUALS_CAP', 'the limit')
        spent.append(amount)
    monkeypatch.setattr(V, 'check_cap', cap)
    for n in (1, 2):
        G.cap_or_drop(None, None, RUN, s, f'S{n}', s['guides'][f'S{n}']['again'], 48.0, 'a 6 s take')
        s['guides'][f'S{n}']['again']['sent'] = f'j{n}b'
    with pytest.raises(Problem):
        G.cap_or_drop(None, None, RUN, s, 'S3', s['guides']['S3']['again'], 48.0, 'a 6 s take')
    rows = [job('j1'), job('j1b', 'S1', status='running'), job('j2', 'S2'), job('j2b', 'S2', status='running'), job('j3', 'S3')]
    due = T.rejected_due(s, p, rows)
    assert due.startswith('Three (S3): its take was rejected') and 'the cost limit refused the take ordered on the page' in due and 'One' not in due and 'Two' not in due
    assert T.again_due(s, p, rows) == ''


# ---------- points 7 and 11: the counts in `vw visuals status`; the decisions in the log ----------

def test_the_status_carries_step_7s_line_of_counts(film):
    store, conn, job_id, wrote = film
    out = V.status(conn, store, NEW, [])
    assert 'AI video: 1 made and checked.' in out['step6']


def test_withdrawing_an_order_is_a_decision_in_the_log(film):
    store, conn, job_id, wrote = film
    on_page(store, conn, 'again', 'He walks more slowly.')
    G.cancel_order(conn, store, USER, NEW, [], 'VS1', 'Do not make another.')
    assert wrote[-1]['kind'] == 'decision' and wrote[-1]['entry'] == 'the take ordered on the page withdrawn' and wrote[-1]['quote'] == 'Do not make another.'
    assert 'again' not in saved(store)['guides']['VS1']
