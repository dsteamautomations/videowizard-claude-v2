"""design/220 (SK, 19 Nov 2026, after the stage review of VW-24's References step 2): the first three sets are made and checked by Claude. When
the check says "use" for each, the server orders the other sets itself, once, with no question, and the log says the rule ordered them. When one
does not pass (make again, doubtful, not checked, not made) the others wait for the operator's word, as before, and that set is seen first.
Three sets or fewer, the limit, a place held for its things and a thing set aside are as before. Without a database."""
import pytest

from app import chat_flow as CF, page_flow as P, ref_sets as RS, runlog, visuals_stage as VS
import d211_fixture as F
from test_design211b_older_pure import saved
from test_design211b_round_pure import RUN, USER, back, done, film, judge, looks, post, put, rows, state, yes   # noqa: F401
from test_design211b_sets_pure import finder   # noqa: F401 (the fixture)
from test_design211c_kit_pure import Film


@pytest.fixture(autouse=True)
def _v2_round(monkeypatch, _older_round_tests):   # conftest: a module not named test_design211* posts an older round; these post the round of today
    monkeypatch.setattr(VS, 'ROUND_V', 2)


@pytest.fixture
def written(monkeypatch):
    out = []
    monkeypatch.setattr(runlog, 'write', lambda conn, e: out.append(e))
    return out


def made(file=None, fail=(), **step1):
    """A round whose first sets are back and not looked at yet."""
    store, conn = film()
    post(store, conn, file)
    done(store, conn, **step1)
    back(store, fail=fail)
    return store, conn


def send(store, conn, sets):
    """The looks as the route records them: `round_looks`, then the rule."""
    return VS.guarded(lambda: RS.rest_by_check(conn, store, USER, RUN, [], RS.round_looks(store, USER, RUN, [], sets, 'helper')))


def ordered(conn):
    return [(p[2].obj if hasattr(p[2], 'obj') else p[2])['reference']['element_id'] for p in conn.inserted]


def test_every_first_set_passed_so_the_others_are_ordered_once_and_the_log_says_the_rule_did_it(written):
    store, conn = made()
    out = send(store, conn, looks(store, only=('MASON', 'STREET')))                      # two of the three looked at: nothing yet
    assert 'rest_ordered' not in out and state(store) == 'looking' and ordered(conn) == list(F.FIRST) and written == []
    out = send(store, conn, looks(store))
    assert out['rest_ordered'] == ['BRICK', 'TILE'] and out['errors'] == {} and out['pass'] == 'making' and out['recorded'] == ['T_LAY']
    assert out['then'] == RS.REST_BY_RULE.format(n='2 sets are') + ' ' + RS.ALL_MAKING.format(k=2)
    rd = saved(store)['round']
    assert rd['go'] == 2 and rd['rest'] == [] and rd['rest_word']['by'] == 'rule' and rd['rest_word']['quote'] == RS.REST_RULE and 'rest_held' not in rd
    assert ordered(conn) == [*F.FIRST, 'BRICK', 'TILE']
    assert len(written) == 1 and written[0]['by_kind'] == 'server' and written[0]['kind'] == 'decision' and written[0]['rule'] == RS.REST_RULE and written[0]['quote'] == ''
    assert written[0]['entry'] == 'ordered by the rule, not by the operator: BRICK, TILE; the first sets that passed: MASON, STREET, T_LAY'
    assert all(r['verdict'] != 'yes' for e, r in rd['elements'].items() if e in F.FIRST)                # nothing is approved for the operator
    back(store)                                                                          # the others come back and are looked at: no second order
    out = send(store, conn, looks(store))
    assert 'rest_ordered' not in out and out['then'] == RS.SETS_PAGE and len(conn.inserted) == 5 and len(written) == 1
    assert VS.guarded(lambda: RS.rest_by_check(conn, store, USER, RUN, [], {'then': None})) == {'then': None}


@pytest.mark.parametrize('recommend, kept', [('remake', 'fault'), ('doubt', 'fault')])
def test_a_first_set_the_check_did_not_pass_holds_the_others_for_the_operators_word(written, recommend, kept):
    store, conn = made()
    send(store, conn, looks(store, only=('MASON', 'STREET')))
    out = send(store, conn, looks(store, recommend=recommend))
    rd = saved(store)['round']
    assert 'rest_ordered' not in out and rd['go'] == 1 and rd['rest'] == ['BRICK', 'TILE'] and rd['rest_held'][kept] == ['T_LAY'] and ordered(conn) == list(F.FIRST) and written == []
    assert out['then'] == RS.REST_HELD.format(why='your look did not say use for T_LAY') + ' ' + RS.SETS_PAGE and state(store) == 2
    judge(store, conn, {'T_LAY': {'verdict': 'no'}})                                     # made again and passed later: the rule does not come back; the operator's word orders them
    VS.guarded(lambda: RS.round_rewrite(conn, store, USER, RUN, [], [{'element_id': 'T_LAY', 'prompt': 'The same, with the hand on the brick.'}]))
    back(store)
    out = send(store, conn, looks(store))
    assert 'rest_ordered' not in out and saved(store)['round']['go'] == 1 and written == []
    assert VS.guarded(lambda: RS.round_rest(conn, store, USER, RUN, [], 'make the other two'))['queued'] == ['BRICK', 'TILE']


def test_a_picture_that_could_not_be_checked_holds_the_others(written):
    store, conn = made()
    sets = looks(store)
    sets[0]['pictures'][0] = {'ref': sets[0]['pictures'][0]['ref'], 'view': sets[0]['pictures'][0]['view'], 'not_checked': 'The file would not open.'}
    out = send(store, conn, sets)
    assert out['refused'] == {} and 'rest_ordered' not in out and saved(store)['round']['rest_held']['unchecked'] == ['MASON'] and ordered(conn) == list(F.FIRST)
    assert out['then'].startswith(RS.REST_HELD.format(why='MASON could not be checked'))


def test_a_first_set_that_was_not_made_holds_the_others_and_its_line_says_why(written):
    store, conn = made(fail=('STREET',))
    out = send(store, conn, looks(store))
    rd = saved(store)['round']
    assert 'rest_ordered' not in out and rd['rest_held']['unmade'] == ['STREET'] and rd['rest'] == ['BRICK', 'TILE'] and ordered(conn) == list(F.FIRST) and written == []
    assert RS.first_sets(saved(store), rd) == {'use': ['MASON', 'T_LAY'], 'fault': [], 'unmade': ['STREET'], 'unchecked': []}
    names = {'STREET': 'The street'}
    assert CF._rest_held_why(rd, names) == CF.WORDS['rest_held_unmade'].format(names='The street')


def test_claudes_check_never_comes_so_nothing_is_ordered(written):
    store, conn = made()
    assert VS.guarded(lambda: RS.rest_by_check(conn, store, USER, RUN, [], {})) == {} and state(store) == 'looking'
    assert saved(store)['round']['rest'] == ['BRICK', 'TILE'] and 'rest_held' not in saved(store)['round'] and ordered(conn) == list(F.FIRST)


def test_three_sets_or_fewer_are_all_made_at_once_as_before(written):
    store, conn = made(BRICK={'verdict': 'ignore'}, TILE={'verdict': 'ignore'})
    out = send(store, conn, looks(store))
    assert saved(store)['round']['rest'] == [] and 'rest_ordered' not in out and out['then'] == RS.SETS_PAGE and len(conn.inserted) == 3 and written == []


def test_the_limit_with_no_room_orders_none_and_the_operator_reads_the_limit(written, monkeypatch):
    store, conn = made()
    monkeypatch.setattr(VS, '_set_budget', lambda run, session, spend: (0.0, 50.0, 35.0))       # two more sets do not fit
    out = send(store, conn, looks(store))
    rd = saved(store)['round']
    assert 'rest_ordered' not in out and rd['rest_held'].get('limit') is True and rd['go'] == 1 and rd['rest'] == ['BRICK', 'TILE'] and len(conn.inserted) == 3 and written == []
    assert CF._rest_held_why(rd, {}) == RS.LIMIT_PLAIN and '₹' not in out['then'] and 'limit its owner set' in out['then']


def test_a_thing_set_aside_is_not_ordered_and_a_place_still_waits_for_its_things(written):
    store, conn = made()
    VS.set_aside(store, USER, RUN, [], 'BRICK', 'not needed')
    out = send(store, conn, looks(store))
    assert out['rest_ordered'] == ['TILE'] and ordered(conn) == [*F.FIRST, 'TILE'] and written[0]['entry'].startswith('ordered by the rule, not by the operator: TILE;')
    # a place among the others whose thing has no approved reference yet is held by the order itself (design/216), not made
    store, conn = made()
    s = saved(store)
    s['round']['elements']['STREET'].update(set=None, error=None)                        # as if the street waited for the second go
    for k in [k for k, r in s['references'].items() if r.get('element_id') == 'STREET' and r.get('kind') == 'sheet']:
        s['references'].pop(k)
    s['round']['rest'] = ['BRICK', 'TILE', 'STREET']
    s['round']['elements']['STREET']['things'] = {'ids': ['BRICK'], 'reason': 'The street is of brick.', 'by': 'u1', 'at': F.NOW}
    put(store, s)
    out = send(store, conn, looks(store))
    assert out['rest_ordered'] == ['BRICK', 'TILE'] and saved(store)['round']['elements']['STREET'].get('held') == ['BRICK']
    assert written[-1]['entry'] == 'ordered by the rule, not by the operator: BRICK, TILE; the first sets that passed: MASON, T_LAY; waiting for their things: STREET'


def test_a_broken_log_does_not_stop_the_order(monkeypatch):
    store, conn = made()
    monkeypatch.setattr(runlog, 'write', lambda conn, e: (_ for _ in ()).throw(RuntimeError('no table')))
    assert send(store, conn, looks(store))['rest_ordered'] == ['BRICK', 'TILE']


def test_held_by_the_check_the_faulted_set_comes_before_the_line_of_the_other_sets_with_the_checks_words(monkeypatch):
    film_ = Film(monkeypatch, '2')
    before = [l['key'] for l in film_.page()['lines']]
    assert before[0] == 'sets:rest' and film_.lines()['sets:rest']['why'] == CF.WORDS['rest_why']    # not held by the rule: as before
    film_.change(lambda s: s['round'].update(rest_held={'fault': ['T_LAY'], 'at': F.NOW}))
    page = film_.page()
    keys = [l['key'] for l in page['lines']]
    assert keys[0] == 'set:T_LAY' and keys.index('sets:rest') > keys.index('set:STREET') and sorted(keys) == sorted(before)
    lines = {l['key']: l for l in page['lines']}
    assert lines['set:T_LAY']['rec']['do'] == 'remake' and lines['set:T_LAY']['state'] == 'open'
    assert lines['sets:rest']['why'] == CF.WORDS['rest_held_fault'].format(names=lines['set:T_LAY']['name'], it='it') and lines['sets:rest']['buttons'][0]['choice'] == 'rest'


def test_the_sentences_the_operator_reads_say_how_the_others_follow():
    said = RS.goes_said(20)
    assert said == ('The first 3 sets are made and checked first. When the check passes them all, the other 17 are made at once; when it does not, you see that set first '
                    'and the others wait for your word. A set you ask to change is made again, at most 3 times.')
    assert 'made and checked first; when the check passes them all, the others are made at once' in CF.WORDS['goes'] and CF.WORDS['goes'].format(m=3, x=3).strip() in CF.WORDS['help']
    assert RS.goes_said(3) == RS.SAID_ALL.format(n=3) and RS.goes_said(1) == RS.SAID_ONE
    for text in (said, CF.WORDS['goes'], CF.WORDS['help'], *[CF.WORDS['rest_held_' + k] for k in ('fault', 'unmade', 'unchecked')]):
        assert '₹' not in text and 'check the method' not in text
