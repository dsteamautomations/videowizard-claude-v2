"""Accurate images, build step 4 (design/200), Area A: the reference set of a thing that has an approved drawing set.
The drawings go with the set's request as parent pictures, after the footage frame when there is one; the prompt explains them and states the facts;
the check carries the facts. A thing without a drawing set goes exactly the older way."""
import pytest

from app import drawings as DR, visuals_stage as VS
from app.errors import Problem
from test_design151_refs_pure import KILN, MASON, NEW, FakeConn, _req, doc_with, frames_only, g
from test_draw3d_pure import dovetail
from test_visuals_stage_pure import USER, saved

ROWS = [{'element_id': 'E1', 'frames': ['F1'], 'prompt': 'the plinth top'}, {'element_id': 'E2', 'prompt': 'the kiln during firing'}, {'element_id': 'P1', 'prompt': 'kneels all day'}]
YES = {'E1': {'verdict': 'approve'}, 'E2': {'verdict': 'approve'}, 'P1': {'verdict': 'approve'}}


def drawn(store, thing, approve=True, d=None):
    conn = FakeConn([])
    sha = DR.set_drawing(conn, store, USER, NEW, [], thing, d or dovetail())['sha256']
    if approve:
        DR.verdict(conn, store, USER, NEW, [], thing, sha, True, 'yes, that is it')
    return sha


def ids(request):
    return [p['id'] for p in request['parents']]


def round_made(store):
    conn = FakeConn([])
    VS.round_start(store, USER, NEW, [], ROWS, conn=conn)
    out = VS.round_done(store, USER, NEW, [], YES, 'Yes, the frame.', conn=conn)
    return out, {_req(p)['reference']['element_id']: _req(p) for p in conn.inserted}


def test_a_thing_with_no_footage_and_an_approved_drawing_set_sends_its_drawings_and_explains_them():
    store = frames_only(doc_with(KILN, MASON))
    sha = drawn(store, 'E2')
    out, req = round_made(store)
    r = req['E2']
    assert ids(r) == [f'drawing-E2-d-{sha[:8]}', f'drawing-E2-a-{sha[:8]}']            # the angled view, then the first flat view: two at most
    p = r['prompt']
    assert p.startswith(VS.KEPT_PREAMBLE) and r['search'] is True and r['set'] is True          # still the kept method, still on Gemini with its look-up for the material
    assert 'How to read the drawings.' in p and 'Image 1 is From outside the corner' in p and 'Image 2 is The tail board, square on' in p
    assert VS.KEPT_DRAWN_LINE in p and 'the drawings win' in p
    assert 'What must be true:\n- board thickness: 18 mm\n- slope of a tail: 1 in 7' in p
    assert p.index('How to read the drawings.') < p.index('Cosmetic requirements')
    made = next(x for x in saved(store)['references'].values() if x.get('kind') == 'sheet' and x.get('element_id') == 'E2')
    checks = [l['check'] for l in made['server_checklist']]
    assert 'drawn fact: board thickness: 18 mm' in checks and 'drawn fact: slope of a tail: 1 in 7' in checks and 'a photograph, not a drawing' in checks
    assert all(l['weight'] == 'must' for l in made['server_checklist'] if l['check'].startswith('drawn fact') or l['check'] == 'a photograph, not a drawing')


def test_a_thing_the_footage_shows_now_gets_a_set_from_its_frame_and_its_drawings():
    store = frames_only(doc_with(KILN, MASON))
    sha = drawn(store, 'E1')
    out, req = round_made(store)
    assert 'E1' in out['queued'] and 'E1' not in out['from_footage']
    r = req['E1']
    assert ids(r) == ['F1', f'drawing-E1-d-{sha[:8]}', f'drawing-E1-a-{sha[:8]}']       # the footage frame stays Image 1
    assert VS.KEPT_FRAME_LINE.format(name='Plinth') in r['prompt'] and 'Image 2 is From outside the corner' in r['prompt'] and 'Image 3 is The tail board, square on' in r['prompt']


def test_a_thing_without_a_drawing_set_goes_the_older_way_unchanged():
    store = frames_only(doc_with(KILN, MASON))
    out, req = round_made(store)
    assert out['from_footage'] == ['E1'] and 'E1' not in req                                   # SK, 5 Nov 2026: its footage picture is its reference; no set
    r = req['E2']
    assert r['parents'] == [] and 'How to read the drawings.' not in r['prompt'] and VS.KEPT_DRAWN_LINE not in r['prompt'] and 'drawn_facts' not in r
    made = next(x for x in saved(store)['references'].values() if x.get('kind') == 'sheet' and x.get('element_id') == 'E2')
    assert not any(l['check'].startswith('drawn fact') for l in made['server_checklist'])


def test_a_drawing_set_that_is_not_approved_is_never_sent():
    store = frames_only(doc_with(KILN, MASON))
    drawn(store, 'E2', approve=False)
    assert DR.approved_sheets(saved(store), 'E2') == [] and not [r for r in saved(store)['references'].values() if r.get('kind') == 'drawing']
    with pytest.raises((Problem, ValueError), match='not approved yet'):            # and the round's Done waits for the operator's answer
        round_made(store)


def test_a_changed_drawing_set_takes_its_old_sheets_out_until_it_is_approved_again():
    store = frames_only(doc_with(KILN, MASON))
    drawn(store, 'E2')
    d = dovetail()
    d['facts'][0]['value'] = 20
    sha2 = drawn(store, 'E2', approve=False, d=d)
    assert not [r for r in saved(store)['references'].values() if r.get('kind') == 'drawing'] and DR.approved_sheets(saved(store), 'E2') == []
    store2 = frames_only(doc_with(KILN, MASON))
    sha = drawn(store2, 'E2')
    sheets = [r for r in saved(store2)['references'].values() if r.get('kind') == 'drawing']
    assert len(sheets) == 4 and all(r['status'] == 'approved' and r['element_id'] == 'E2' and r['drawing_sha256'] == sha for r in sheets)


def test_a_person_never_carries_a_drawing():
    store = frames_only(doc_with(KILN, MASON))
    drawn(store, 'E2')
    _, req = round_made(store)
    assert req['P1']['parents'] == [] and 'How to read the drawings.' not in req['P1']['prompt']


# ---------- the review round: the round waits for the drawings ----------

def test_done_waits_while_a_drawing_set_is_unanswered_or_corrected():
    store = frames_only(doc_with(KILN, MASON))
    sha = drawn(store, 'E2', approve=False)
    conn = FakeConn([])
    VS.round_start(store, USER, NEW, [], ROWS, conn=conn)
    with pytest.raises((Problem, ValueError), match='reference drawings of E2 are not approved yet'):
        g(lambda: VS.round_done(store, USER, NEW, [], YES, 'Yes, the frame.', conn=conn))
    assert conn.inserted == []                                                       # nothing was made
    DR.verdict(conn, store, USER, NEW, [], 'E2', sha, False, 'no', 'the kiln is round, not square')
    with pytest.raises((Problem, ValueError), match='not approved yet'):
        g(lambda: VS.round_done(store, USER, NEW, [], YES, 'Yes, the frame.', conn=conn))
    out = VS.round_done(store, USER, NEW, [], {**YES, 'E2': {'verdict': 'ignore'}}, 'Yes, the frame.', conn=conn)   # a thing the operator leaves out does not hold the round
    assert 'E2' not in out['queued']


def test_a_drawing_set_sent_after_its_things_set_was_made_says_so():
    store = frames_only(doc_with(KILN, MASON))
    round_made(store)
    conn = FakeConn([])
    late_set = DR.set_drawing(conn, store, USER, NEW, [], 'E2', dovetail())
    assert 'already made without these drawings' in late_set['late'] and late_set['next'].startswith('Its set was already made')
    late_frame = DR.set_drawing(conn, store, USER, NEW, [], 'E1', dovetail())
    assert 'footage picture was already taken as its reference' in late_frame['late']
    store2 = frames_only(doc_with(KILN, MASON))
    assert 'late' not in DR.set_drawing(conn, store2, USER, NEW, [], 'E2', dovetail())
