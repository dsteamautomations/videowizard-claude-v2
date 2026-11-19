"""design/222, the critic's nine points on the finished branch (19 Nov 2026), each with a test that failed first. Without a database."""
from datetime import timedelta

import pytest

from app import guide as G, guide_worker as GW, pictures as P, takes as T, visual_workers as VW, visuals_stage as V
from app.errors import Problem
from test_design222_takes_pure import NOW, RUN, SHA, USER, guide, held, job, line_of, look, plan, rec, session, shot, states   # noqa: F401 (`held` is the fixture)


# S1: while step 6 is still being made, no take is asked one by one in the chat
def test_s1_the_takes_wait_for_step_6_too(held, monkeypatch):
    s, p = session(), plan(shot('S1'), shot('S2', 'still', 129, 260))
    s['guides'].update(S1=guide())
    s['take_checks'].update(j1=rec(look=look()))
    held(s, p)
    monkeypatch.setattr(V, 'item_link', lambda *a: '')
    assert T.complete(T.expected(s, p, [job('j1')], NOW)) and not P.complete(P.expected(s, p, [job('j1')]))      # every take is made and checked; a still of step 6 is not started
    assert [w['kind'] for w in V.waiting(s, p, 'VW-99', [job('j1')])] == []
    assert [w['kind'] for w in V.waiting(s, p, 'VW-99', [job('j1')], gate=False)] == ['take to select']


# S2: "Use take n after all": the earlier take is selected first; a refusal leaves the newer take as it was
def test_s2_the_earlier_take_is_selected_before_the_newer_is_rejected(held, monkeypatch):
    s, p = session(), plan(shot('S1'))
    s['guides'].update(S1=guide(takes=['j1', 'j2']))
    s['take_checks'].update(j1=rec(look=look(fail=('objects',))), j2=rec(look=look()))
    s['reviews'].update(j1=[{'decision': 'rejected', 'notes': ''}])
    held(s, p)
    seen = []
    monkeypatch.setattr(V, 'review_take', lambda conn, store, user, run, outputs, jid, decision, notes, timing, quote: seen.append(('review', jid, decision, notes)) or {})

    def select(conn, store, user, run, outputs, jid, quote, notes='', timing='', in_s=None):
        if 'refuse' in notes:
            raise ValueError('The plan changed since this take was shot.')
        seen.append(('select', jid, notes, timing))
        return {}
    monkeypatch.setattr(V, 'select_take', select)
    old = job('j1')
    old['result']['evidence']['timing_matches_placement'] = False        # the earlier take is shorter than its place: the reason is its timing note too
    rows = [old, job('j2')]
    with pytest.raises(ValueError):
        T.answer(None, None, USER, RUN, {}, 'S1', rows, 'old:1', 'Use take 1 after all', 'refuse this')
    assert seen == []                                                    # nothing was rejected: the newer take still waits for its answer
    T.answer(None, None, USER, RUN, {}, 'S1', rows, 'old:1', 'Use take 1 after all', 'The first one reads better.')
    assert seen == [('select', 'j1', 'The first one reads better.', 'The first one reads better.'), ('review', 'j2', 'rejected', T.W['old_used'])]


# S3: a take rejected with no new one ordered: the server says what the assistant asks
def test_s3_a_plain_reject_is_said_to_the_assistant(held):
    s, p = session(), plan(shot('S1', title='Mason'))
    s['guides'].update(S1=guide(takes=['j1']))
    s['reviews'].update(j1=[{'decision': 'rejected', 'notes': 'A second helper appears.'}])
    held(s, p)
    due = T.rejected_due(s, p, [job('j1')])
    assert due == ('Mason (S1): its take was rejected ("A second helper appears.") and no new take is ordered: ask the operator what happens to the shot: '
                   'cut it into shorter shots, another angle, or leave it out; a new take after that is asked with its card.')
    s['guides']['S1']['again'] = {'job_id': 'j1', 'words': 'x'}
    assert T.rejected_due(s, p, [job('j1')]) == ''                        # an order is pending: `again_due` says what to do
    assert T.rejected_due(s, p, [job('j1'), job('j2', status='running')]) == ''


# S4: a take shot for an older plan: on the page with Make another and Reject, never a dead end
def test_s4_a_take_for_an_older_plan_is_on_the_page_and_cannot_be_selected(held):
    s, p = session(), plan(shot('S1'))
    s['guides'].update(S1=guide(takes=['j1']))
    s['take_checks'].update(j1=rec(look=look()))
    held(s, p)
    rows = [job('j1', plan_digest='another plan')]
    assert T.complete(T.expected(s, p, rows, NOW))                         # it does not keep the page closed
    line = line_of(s, p, rows)
    assert [b['choice'] for b in line['buttons']] == ['again', 'reject'] and line['takes'][0]['short'] == T.W['stale']
    with pytest.raises(ValueError, match='earlier plan'):
        T.answer(None, None, USER, RUN, {}, 'S1', rows, 'select', 'Select', '')
    assert G.same_of('r', 's', 'p', 'plan-1') != G.same_of('r', 's', 'p', 'plan-2')   # the same guide, still and words for another plan is another request


# S5: a changed layout keeps the order given on the page
def test_s5_a_new_scene_keeps_the_order():
    order = {'job_id': 'j1', 'words': 'He lays the broom down.'}
    assert G.carried({'again': order, 'shoot_asked': {'stamp': 'x'}, 'stills': []}) == {'again': order}
    assert G.carried({'again': {**order, 'sent': 'j2'}}) == {} and G.carried({}) == {}


# S6: an order the cost limit refuses is dropped and said; an order can be withdrawn
def test_s6_a_refused_or_withdrawn_order_does_not_stay_pending(held, monkeypatch):
    s, p = session(), plan(shot('S1'))
    s['guides'].update(S1=guide(takes=['j1'], again={'job_id': 'j1', 'words': 'x'}))
    s['reviews'].update(j1=[{'decision': 'rejected', 'notes': 'x'}])
    held(s, p)

    def over(conn, run, session_, amount, what):
        raise Problem(409, 'VISUALS_CAP', 'the limit')
    monkeypatch.setattr(V, 'check_cap', over)
    with pytest.raises(Problem):
        G.cap_or_drop(None, None, RUN, s, 'S1', s['guides']['S1']['again'], 120.0, 'a 6 s take')
    assert 'again' not in s['guides']['S1'] and s['guides']['S1']['again_refused'] == 'the limit' and states(s, p, [job('j1')]) == [('S1', 'waiting for you in the chat')]
    assert 'the cost limit' in T.rejected_due(s, p, [job('j1')])
    s['guides']['S1']['again'] = {'job_id': 'j1', 'words': 'x'}
    out = G.cancel_order(None, USER, RUN, {}, 'S1', 'Do not make another.')
    assert 'again' not in s['guides']['S1'] and out['next'].startswith('The order for another take of S1 is withdrawn')
    with pytest.raises(ValueError):
        G.cancel_order(None, USER, RUN, {}, 'S1', 'x')                    # nothing to withdraw


# S7: the price line is said once per order, on both paths
def test_s7_the_line_of_new_takes_counts_each_order_once(held):
    s, p = session(), plan(shot('S1'), shot('S2', start=129, end=260))
    s['guides'].update(S1=guide(again={'job_id': 'j1', 'words': 'x'}), S2=guide(again={'job_id': 'j2', 'words': 'y'}))
    held(s, p)
    assert T.ordered(s, p, 20.0) == '2 new takes are ordered: 12 s, about ₹240.'
    assert T.ordered(s, p, 20.0) == '' and s['guides']['S1']['again']['told']    # a second "done" does not say it again
    s['guides']['S1']['again'] = {'job_id': 'j3', 'words': 'z'}
    assert T.ordered(s, p, 20.0) == '1 new take is ordered: 6 s, about ₹120.'


# S8: the looks list names the takes' own helper, and the takes still due are counted
def test_s8_the_looks_answer_names_the_take_helper_and_counts_the_takes_left(held):
    s, p = session(), plan(shot('S1'), shot('S2', start=129, end=260))
    s['guides'].update(S1=guide(), S2=guide())
    s['take_checks'].update(j1=rec(), j2=rec())
    held(s, p)
    rows = [job('j1'), job('j2', 'S2')]
    listed = P.looks_due(None, RUN, {}, rows)
    assert [x['ref'] for x in listed['pictures']] == ['j1', 'j2'] and 'vw-take-look' in listed['then'] and 'about three takes each' in listed['then'] and 'how_take' in listed
    full = [{'id': l['id'], 'pass': True, 'seen': ''} for l in T.look_lines()]
    out = P.record_looks(None, USER, RUN, {}, [{'ref': 'j1', 'sha10': SHA[:10], 'lines': full}], 'helper', rows)
    assert out['recorded'] == ['j1'] and out['left'] == ['j2'] and "1 take(s) wait for Claude's check" in out['then']


# S9: a take whose submission is unknown is still open, never "could not be made"
def test_s9_an_unknown_submission_is_being_made(held):
    s, p = session(), plan(shot('S1'))
    s['guides'].update(S1=guide())
    held(s, p)
    assert states(s, p, [job('j1', status='submission_unknown')]) == [('S1', 'being made')]


# not built: a take ordered from the page is a decision in the run's log, with its price
def test_an_order_from_the_page_is_a_decision_in_the_log(held, monkeypatch):
    s, p = session(), plan(shot('S1', title='Mason'))
    s['guides'].update(S1=guide(takes=['j1']))
    s['take_checks'].update(j1=rec(look=look()))
    held(s, p)
    monkeypatch.setattr(V, 'review_take', lambda *a, **k: {})
    monkeypatch.setattr(V, 'prices', lambda: {'video_inr_per_s': 20.0})
    wrote = []
    monkeypatch.setattr(T.runlog, 'write', lambda conn, row: wrote.append(row))
    T.answer('conn', None, USER, RUN, {}, 'S1', [job('j1')], 'again', 'Make another', 'He lays the broom down.')
    assert wrote and wrote[0]['kind'] == 'decision' and wrote[0]['about'] == 'shot S1' and wrote[0]['entry'] == 'another take ordered on the page: 6 s, about ₹120' and wrote[0]['quote'] == 'He lays the broom down.'


# lesser: a failed measurement leaves the line out; a re-run of the worker's check keeps Claude's lines on the card
def test_a_failed_jump_measurement_raises_and_a_rerun_keeps_claudes_look(monkeypatch):
    class R:
        returncode, stderr = 1, b'boom'
    monkeypatch.setattr(GW.subprocess, 'run', lambda *a, **k: R())
    with pytest.raises(RuntimeError):
        GW.jumps('x.mp4')
    before = rec(look=look(fail=('objects',)), asked_at='t')
    merged = VW.merged_check(before, {k: v for k, v in rec().items() if k != 'look'}, SHA)
    assert merged['look'] == before['look'] and merged['asked_at'] == 't' and merged['not_read'] is False
    assert [r['state'] for r in merged['scorecard'] if r['line'] == 'objects'] == ['Fail']
    assert 'look' not in VW.merged_check(before, rec(), 'b' * 64)        # another file: the look of the earlier one is not carried
    assert T.offered({'take_checks': {'j1': rec()}}, job('j1'), NOW + timedelta(minutes=5)) is False
