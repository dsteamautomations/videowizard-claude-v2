"""Hotfix 2, 11 Nov 2026 (VW-19): a second pass of step 2 could never be recorded. After a first pass with one Yes and one
Correct it, the set approved in the first pass still needed a verdict, and its Yes was refused ("its set did not come back"),
because its pictures were approved and no longer candidates. A set approved in an earlier pass is settled: it needs no
verdict again and keeps its golden picture."""
import pytest

from app import visuals_stage as VS
from app.errors import Problem
from test_design151_refs_pure import KILN, MASON, NEW, doc_with, with_sets
from test_visuals_stage_pure import USER, g, saved


def _first_pass():
    store, conn, s = with_sets(doc_with(KILN, MASON))
    sets = {eid: sorted(r['id'] for r in s['references'].values() if r.get('kind') == 'sheet' and r['element_id'] == eid) for eid in ('E1', 'E2', 'P1')}
    out = VS.round_sets(store, USER, NEW, [], {'E1': {'verdict': 'yes', 'golden': sets['E1'][0]}, 'E2': {'verdict': 'correct', 'words': 'no chimney'},
                                               'P1': {'verdict': 'no', 'words': 'too young'}}, 'Pass one.', conn=conn)
    assert out['pass'] == 'making'
    s = saved(store)
    for r in s['references'].values():   # the remade sets come back
        if r.get('kind') == 'sheet' and r['status'] == 'generating':
            r['status'] = 'candidate'
    VS.save_session(store, NEW, s)
    new = {eid: sorted(r['id'] for r in s['references'].values() if r.get('kind') == 'sheet' and r['element_id'] == eid and r['status'] == 'candidate') for eid in ('E2', 'P1')}
    return store, conn, sets, new


def test_a_second_pass_needs_verdicts_only_for_the_sets_made_again():
    store, conn, sets, new = _first_pass()
    out = VS.round_sets(store, USER, NEW, [], {'E2': {'verdict': 'yes', 'golden': new['E2'][0]}, 'P1': {'verdict': 'yes'}}, 'Pass two.', conn=conn)
    s = saved(store)
    assert out['pass'] == 'complete' and s['round']['pass'] == 'complete'
    assert s['golden']['E1'] == sets['E1'][0] and s['golden']['E2'] == new['E2'][0]   # the first pass's golden picture is kept
    assert all(s['references'][i]['status'] == 'approved' for i in sets['E1'])


def test_a_yes_sent_again_for_a_set_approved_earlier_is_accepted_and_changes_nothing():
    store, conn, sets, new = _first_pass()
    out = VS.round_sets(store, USER, NEW, [], {'E1': {'verdict': 'yes', 'golden': sets['E1'][0]}, 'E2': {'verdict': 'yes', 'golden': new['E2'][0]},
                                               'P1': {'verdict': 'yes'}}, 'Pass two.', conn=conn)   # the page sends every card's answer
    s = saved(store)
    assert out['pass'] == 'complete' and s['golden']['E1'] == sets['E1'][0]
    assert s['references'][sets['E1'][0]]['approval']['quote'] == 'Pass one.'   # not approved a second time


def test_a_set_made_again_still_needs_its_verdict_on_the_second_pass():
    store, conn, sets, new = _first_pass()
    with pytest.raises(Problem, match='P1: a verdict is required'):
        g(lambda: VS.round_sets(store, USER, NEW, [], {'E2': {'verdict': 'yes', 'golden': new['E2'][0]}}, 'Pass two.', conn=conn))
