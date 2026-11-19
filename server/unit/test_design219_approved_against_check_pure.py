"""SK, 19 Nov 2026 (the stage review of VW-24's References step 2): when the operator approves a set and Claude's check of it did not say "use",
the decision log says so on the approval's own line, with the check's verdict and its reason. Nothing else changes: the screen, the buttons,
the chat's words and what later steps read are as before; the older line ("answered on the page") is still written by the middleware."""
import pytest

from app import chat_flow as CF, ref_sets as RS, runlog, visuals_stage as VS
from test_design211b_older_pure import saved
from test_design211b_round_pure import RUN, USER, at_two, judge, look, looks, put, yes   # noqa: F401
from test_design211b_sets_pure import finder   # noqa: F401 (the fixture)


@pytest.fixture(autouse=True)
def _v2_round(monkeypatch, _older_round_tests):   # conftest: a module not named test_design211* posts an older round; these post the round of today
    monkeypatch.setattr(VS, 'ROUND_V', 2)


@pytest.fixture
def written(monkeypatch):
    out = []
    monkeypatch.setattr(runlog, 'write', lambda conn, e: out.append(e))
    return out


def relook(store, eid, recommend, reason):
    """The set's look as a helper would have recorded it: its recommendation and its reason."""
    s = saved(store)
    row = s['round']['elements'][eid]
    row['set_look'] = {**(row.get('set_look') or {}), 'set': row['set'], 'recommend': recommend, 'reason': reason}
    put(store, s)


def due(store):
    s = saved(store)
    return [e for e, r in s['round']['elements'].items() if r.get('set') and VS._set_rows(s, e, r['set'], ('candidate',))]


def test_the_line_of_a_pure_row():
    row = {'set': 's1', 'set_look': {'set': 's1', 'recommend': 'remake', 'reason': 'round clay pans,\n not Mangalore tiles'}}
    assert RS.approved_against('SITE_DECK', row) == 'set SITE_DECK: approved by the operator; the check said make again: round clay pans, not Mangalore tiles'
    row['set_look'].update(recommend='doubt', reason='which bag is the film\'s?')
    assert RS.approved_against('BAG', row) == "set BAG: approved by the operator; the check said doubtful: which bag is the film's?"
    row['set_look']['recommend'] = 'use'
    assert RS.approved_against('BAG', row) is None                                                    # the check agreed: no extra line
    assert RS.approved_against('BAG', {'set': 's1'}) == 'set BAG: approved by the operator; the set was not checked'
    assert RS.approved_against('BAG', {'set': 's2', 'set_look': {'set': 's1', 'recommend': 'remake', 'reason': 'x'}}) == 'set BAG: approved by the operator; the set was not checked'   # the look is of a set made before this one
    long = RS.approved_against('BAG', {'set': 's1', 'set_look': {'set': 's1', 'recommend': 'remake', 'reason': 'word ' * 200}})
    assert len(long.split(': ', 2)[2]) <= 300 and '\n' not in long


def test_an_approval_against_the_check_is_logged_once_and_one_the_check_agreed_with_is_not(written):
    store, conn = at_two()
    a, b, c = due(store)[:3]
    relook(store, a, 'remake', 'The filler is wrong.')
    relook(store, b, 'doubt', 'The colour may be wrong.')
    judge(store, conn, {e: yes(store, e) for e in (a, b, c)})
    assert [(e['about'], e['entry']) for e in written] == [
        (f'set {a}', f'set {a}: approved by the operator; the check said make again: The filler is wrong.'),
        (f'set {b}', f'set {b}: approved by the operator; the check said doubtful: The colour may be wrong.')]
    assert all(e['kind'] == 'decision' and e['stage'] == 'visuals' and e['by_kind'] == 'operator' and e['quote'] == 'Sets done' and e['run_id'] == RUN['id'] for e in written)
    judge(store, conn, {})                                                                            # the same word again: the sets are settled
    assert len(written) == 2


def test_a_correction_or_a_no_writes_no_line(written):
    store, conn = at_two()
    a, b = due(store)[:2]
    relook(store, a, 'remake', 'x')
    relook(store, b, 'remake', 'x')
    judge(store, conn, {a: {'verdict': 'no'}, b: {'verdict': 'correct', 'words': 'Make the wall darker.'}})
    assert written == []


def test_a_kept_answer_recorded_later_writes_the_same_line(written):
    store, conn = at_two()
    a = due(store)[0]
    relook(store, a, 'remake', 'The filler is wrong.')
    VS.guarded(lambda: VS.set_answer(store, USER, RUN, [], a, **{k: v for k, v in yes(store, a).items()}))
    assert written == []                                                                              # kept, not recorded yet
    CF.flush_sets(conn, store, USER, RUN, [], 'Approve A')
    assert [(e['entry'], e['quote']) for e in written] == [(f'set {a}: approved by the operator; the check said make again: The filler is wrong.', 'Approve A')]
    CF.flush_sets(conn, store, USER, RUN, [], 'Approve A')
    assert len(written) == 1


def test_a_log_that_cannot_be_written_never_stops_the_approval(monkeypatch):
    def broken(conn, e):
        raise RuntimeError('the log is down')
    monkeypatch.setattr(runlog, 'write', broken)
    store, conn = at_two()
    a = due(store)[0]
    relook(store, a, 'remake', 'x')
    out = judge(store, conn, {a: yes(store, a)})
    assert out['approved'] == [a] and saved(store)['round']['elements'][a]['verdict'] == 'yes'


def test_a_round_of_before_writes_no_line():
    import inspect
    assert 'if v2 and ref_sets.approved_against(eid, r)' in inspect.getsource(VS.round_sets)   # the line is written only in a round of today
