"""Hotfix 2, 11 Nov 2026 (VW-19): a second pass of step 2 could never be recorded. After a first pass with one Yes and one
No, the set approved in the first pass still needed a verdict, and its Yes was refused ("its set did not come back"),
because its pictures were approved and no longer candidates. A set approved in an earlier pass is settled: it needs no
verdict again and keeps its golden picture.
(E1 has an approved footage frame: on main it gets no AI set, design/151 section 15, so the test works on E2 and P1 and
answers E1 only where it has a set.)"""
import pytest

from app import visuals_stage as VS
from app.errors import Problem
from test_design151_refs_pure import KILN, MASON, NEW, doc_with, with_sets
from test_visuals_stage_pure import USER, g, saved


def _sheets(s, eid, status=None):
    return sorted(r['id'] for r in s['references'].values() if r.get('kind') == 'sheet' and r['element_id'] == eid and (status is None or r['status'] == status))


def _first_pass():
    store, conn, s = with_sets(doc_with(KILN, MASON))
    sets = {eid: _sheets(s, eid) for eid in ('E1', 'E2', 'P1')}
    first = {'E2': {'verdict': 'yes', 'golden': sets['E2'][0]}, 'P1': {'verdict': 'no', 'words': 'too young'}}
    if sets['E1']:
        first['E1'] = {'verdict': 'yes', 'golden': sets['E1'][0]}
    out = VS.round_sets(store, USER, NEW, [], first, 'Pass one.', conn=conn)
    assert out['pass'] == 'making' and out['queued'] == ['P1']
    s = saved(store)
    for r in s['references'].values():   # the remade set comes back
        if r.get('kind') == 'sheet' and r['status'] == 'generating':
            r['status'] = 'candidate'
    VS.save_session(store, NEW, s)
    assert len(_sheets(s, 'P1', 'candidate')) > 0
    return store, conn, sets


def test_a_second_pass_needs_a_verdict_only_for_the_set_made_again():
    store, conn, sets = _first_pass()
    out = VS.round_sets(store, USER, NEW, [], {'P1': {'verdict': 'yes'}}, 'Pass two.', conn=conn)
    s = saved(store)
    assert out['pass'] == 'complete' and s['round']['pass'] == 'complete'
    assert s['golden']['E2'] == sets['E2'][0]   # the first pass's golden picture is kept
    assert all(s['references'][i]['status'] == 'approved' for i in sets['E2'])


def test_a_yes_sent_again_for_a_set_approved_earlier_is_accepted_and_changes_nothing():
    store, conn, sets = _first_pass()
    out = VS.round_sets(store, USER, NEW, [], {'E2': {'verdict': 'yes', 'golden': sets['E2'][0]}, 'P1': {'verdict': 'yes'}}, 'Pass two.', conn=conn)   # the page sends every card's answer
    s = saved(store)
    assert out['pass'] == 'complete' and s['golden']['E2'] == sets['E2'][0]
    assert s['references'][sets['E2'][0]]['approval']['quote'] == 'Pass one.'   # not approved a second time


def test_a_set_made_again_still_needs_its_verdict_on_the_second_pass():
    store, conn, sets = _first_pass()
    with pytest.raises(Problem, match='P1: a verdict is required'):
        g(lambda: VS.round_sets(store, USER, NEW, [], {'E2': {'verdict': 'yes', 'golden': sets['E2'][0]}}, 'Pass two.', conn=conn))
