"""Release 1 of 27 Nov 2026, phase 4, part D (SK): a shot that is stuck does not keep the takes page closed, and by his second decision
the same 30 minutes hold for the page of step 6. Stuck: not complete, nothing queued or running for it, nothing happened for 30 minutes.
Without a database."""
from datetime import timedelta

import pytest

from app import page_flow as PF, pictures as P, takes as T, visuals_stage as V
from test_design222_takes_pure import NOW, RUN, USER as OP, guide, held, job, plan, session, shot   # noqa: F401 (held: the fixture)

LOOKED = {'sha256': 's' * 64, 'lines': []}
ago = lambda minutes: (NOW - timedelta(minutes=minutes)).isoformat()


def film(minutes=31, **third):
    """S1 and S2 have their takes; S3's still waits for the operator's answer in the chat, asked `minutes` ago."""
    s, p = session(), plan(shot('S1', end=100, title='Mason'), shot('S2', start=100, end=200, title='Wall'), shot('S3', start=200, end=300, title='Roof'))
    s['guides'] = {'S1': guide(takes=['j1']), 'S2': guide(takes=['j2']), 'S3': guide(still='candidate', prompt=False, **third)}
    s['guides']['S3']['stills'][0].update(check_look=LOOKED, asked_at=ago(minutes))
    return s, p, [job('j1', 'S1', at=ago(300)), job('j2', 'S2', at=ago(300))]


def items(s, p, rows, now=NOW):
    return T.expected(s, p, rows, now)


def test_a_shot_with_nothing_running_and_its_last_mark_31_minutes_old_is_stuck_and_the_page_opens_without_it(held):
    s, p, rows = film(31)
    held(s, p)
    got = items(s, p, rows)
    assert [bool(i.get('stuck')) for i in got] == [False, False, True] and T.complete(got)
    assert got[2]['stuck'] == {'since': ago(31), 'waits': 'It waits for your answer in the chat since 11:29 UTC.'}
    assert P.stuck_due(got) == 'Not moving for 30 minutes or more: Housing at work, shot 3 of 3: It waits for your answer in the chat since 11:29 UTC.' or P.stuck_due(got).endswith(': It waits for your answer in the chat since 11:29 UTC.')
    assert P.waiting_rows(s, p, got) == [{'name': got[2]['name'], 'kind_words': P.heading_text(s, p, ['S3']), 'state': 'stuck', 'note': got[2]['stuck']['waits']}]


def test_at_29_minutes_the_page_stays_closed(held):
    s, p, rows = film(29)
    held(s, p)
    got = items(s, p, rows)
    assert not any(i.get('stuck') for i in got) and not T.complete(got) and P.stuck_due(got) == ''


@pytest.mark.parametrize('busy', ['a take running for 40 minutes', 'its layout video queued', 'its check frames queued', 'its first frame being made', 'a still being made'])
def test_a_shot_with_a_job_queued_or_running_is_never_stuck(held, busy):
    s, p, rows = film(120)
    g = s['guides']['S3']
    if busy.startswith('a take'):
        g['stills'][0]['status'] = 'approved'
        rows.append(job('j3', 'S3', status='running', at=ago(40)))
    elif busy.startswith('its layout'):
        g['render'] = {**g['render'], 'status': 'queued'}
    elif busy.startswith('its check'):
        g['frames'] = {'status': 'queued', 'job_id': 'f1'}
    elif busy.startswith('its first'):
        g['render'] = {'frame1_job_id': 'f1'}
    else:
        g['stills'].append({'id': 'st2', 'status': 'generating', 'guide_sha256': 'g' * 64})
    held(s, p)
    got = items(s, p, rows)
    assert not got[2].get('stuck') and not T.complete(got), busy


def test_every_state_that_is_not_complete_has_its_own_sentence():
    for mod in (T, P):
        open_ = [k for k, words in mod.STATE.items() if words not in mod.COMPLETE]
        assert all(k in mod.STUCK and '{since}' in mod.STUCK[k] for k in open_), mod.__name__
        assert len({mod.STUCK[k] for k in open_}) == len(open_)


def test_every_shot_stuck_gives_no_page_and_the_status_says_each_one(held):
    s, p = session(), plan(shot('S1', end=100, title='Mason'), shot('S2', start=100, end=200, title='Wall'))
    s['guides'] = {sid: guide(still='candidate', prompt=False) for sid in ('S1', 'S2')}
    for sid in ('S1', 'S2'):
        s['guides'][sid]['stills'][0].update(check_look=LOOKED, asked_at=ago(45))
    held(s, p)
    got = items(s, p, [])
    assert all(i.get('stuck') for i in got) and not T.complete(got) and P.stuck_due(got).count('It waits for your answer in the chat since 11:15 UTC.') == 1 and P.stuck_due(got).count('; ') == 1   # one sentence for both


def test_a_stuck_shot_whose_take_arrives_is_a_take_to_answer_and_no_longer_stuck(held):
    s, p, rows = film(90)
    held(s, p)
    assert items(s, p, rows)[2].get('stuck')
    s['guides']['S3'] = guide(takes=['j3'])
    got = items(s, p, rows + [job('j3', 'S3', at=ago(1))])
    assert got[2]['state'] == T.STATE['done'] and not got[2].get('stuck') and T.complete(got)


def test_a_shot_with_no_mark_counts_from_the_plans_last_version_and_one_with_none_at_all_is_not_called_stuck(held):
    s, p = session(), plan(shot('S1', end=100, title='Mason'), shot('S2', start=100, end=200, title='Wall'))
    s['guides'] = {'S1': guide(takes=['j1'])}                                                       # S2 has no scene yet, and no record at all
    held(s, p)
    rows = [job('j1', 'S1', at=ago(300))]
    assert not items(s, p, rows)[1].get('stuck')
    s['versions'] = [{'version': 1, 'at': ago(50)}]
    got = items(s, p, rows)
    assert got[1]['stuck']['waits'] == 'Its scene has not been written; nothing has been started since 11:10 UTC. Ask the assistant why.' and T.complete(got)
    assert T.expected(s, p, rows, NOW + timedelta(days=1))[1]['stuck']['waits'].startswith('Its scene has not been written; nothing has been started since 19 Nov, 11:10 UTC.')


def test_a_result_that_comes_back_from_a_worker_is_the_shots_newest_mark():
    from app import guide as G
    s = {'guides': {'S1': {'sha256': 'x', 'stills': []}}}
    G.apply_result(s, {'id': 'j', 'request': {'kind': 'guide-frames', 'shot_id': 'S1', 'sha256': 'x'}}, 'failed', {}, 'boom')
    assert list(P._marks(s['guides']['S1']))


def test_the_closed_page_says_the_stuck_shot_with_the_counts(held, monkeypatch):
    s, p = session(), plan(shot('S1', end=100, title='Mason'), shot('S2', start=100, end=200, title='Wall'))
    s['guides'] = {'S1': guide(takes=['j1']), 'S2': guide(still='candidate', prompt=False)}
    s['guides']['S2']['stills'][0].update(check_look=LOOKED, asked_at=ago(45))
    held(s, p)
    rows = [job('j1', 'S1', status='running', at=ago(5))]
    monkeypatch.setattr(V, 'take_jobs', lambda conn, run, sid=None: rows)
    got = items(s, p, rows)
    page = PF._takes_page({'session': s, 'plan': p, 'run': RUN, 'conn': None, 'user': OP}, {}, None, got)
    assert page['closed'] and page['say'].startswith('AI video: 1 being made, 1 waiting for you in the chat. Not moving for 30 minutes or more: ') and 'since 11:15 UTC' in page['then']


# ---------- step 6 (SK's second decision) ----------

def test_a_thing_of_step_6_is_stuck_by_the_same_rule(held):
    s, p = session(), plan(shot('S1', 'still', end=100, title='Mason'))
    s['versions'] = [{'version': 1, 'at': ago(29)}]
    held(s, p)
    assert not P.expected(s, p, [], NOW)[0].get('stuck')
    s['versions'] = [{'version': 1, 'at': ago(31)}]
    got = P.expected(s, p, [], NOW)
    assert got[0]['stuck']['waits'] == 'Nothing has been ordered for it since 11:29 UTC. Ask the assistant why.'
    assert P.settled(got) and not P.complete(got)                                                   # stuck alone: no page; the status says it
    done = {'kind': 'still', 'id': 'S0', 'name': 'x', 'state': P.STATE['done']}
    assert P.complete(got + [done]) and not P.complete(got + [{**done, 'state': P.STATE['making']}])   # with something to answer the page opens; never while another thing is being made
    s['references'] = {'R1': {'id': 'R1', 'kind': 'keyframe', 'shot_id': 'S1', 'element_id': 'E1', 'status': 'generating', 'at': ago(200)}}
    assert not P.expected(s, p, [], NOW)[0].get('stuck')                                            # a picture being made: never stuck
