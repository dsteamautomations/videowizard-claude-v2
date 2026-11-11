"""Faults 1 to 4 of the VW-20 test run, 11 Nov 2026 (videobuilder-v4/phase2/testrun/requirements-faults-1-4.md): the server side.
F1: the page data carries the price of one set. F2: an approved own picture of a thing or a place is its reference; Done makes no set
for it. F3: a ready set is answered while another is being made; Done waits and says for what. F4: a set that failed in the call says
why. M1: the timing file of a drawn shot is written only when it holds a cue."""
import json

import pytest

from app import motion as M
from app import visuals_stage as VS
from app.errors import Problem
from test_design151_refs_pure import KILN, MASON, NEW, doc_with, frames_only, with_sets
from test_ui_visuals_actions_pure import back, own, sheets, view
from test_visuals_stage_pure import FakeConn, USER, g, saved

HOSE = {'id': 'E3', 'name': 'Garden hose', 'kind': 'object', 'identity': 'representative', 'requirements': 'a plain green garden hose'}
ROWS = [{'element_id': 'E1', 'frames': ['F1'], 'prompt': 'the plinth top'}, {'element_id': 'E2', 'prompt': 'the kiln during firing'}, {'element_id': 'E3', 'prompt': 'the hose'}]
YES = {r['element_id']: {'verdict': 'approve'} for r in ROWS}


def step1(*els):
    store, conn = frames_only(doc_with(KILN, HOSE, *els)), FakeConn([])
    VS.round_start(store, USER, NEW, [], ROWS, conn=conn)
    return store, conn


def fail(store, eid, error):
    """What the image worker writes when a set's call fails."""
    s = saved(store)
    for r in s['references'].values():
        if r.get('kind') == 'sheet' and r['element_id'] == eid and r['status'] == 'generating':
            r.update(status='failed', error=error)
    VS.save_session(store, NEW, s)


# ---------- F1 ----------

def test_the_page_data_carries_the_price_of_one_set():
    store, conn = step1()
    assert view(store, conn)['budget']['set_inr'] == round(VS.image_price_inr(NEW, provider='gemini') * VS.SET_MAX, 2) > 0


def test_done_at_step_1_reports_the_same_price_per_set():
    store, conn = step1()
    out = VS.round_done(store, USER, NEW, [], YES, 'yes', conn=conn)
    assert out['cost_inr'] == pytest.approx(len(out['queued']) * view(store, conn)['budget']['set_inr'], abs=0.02)


# ---------- F2 ----------

def test_an_approved_own_picture_of_a_thing_stops_its_set():
    store, conn = step1()
    mine = own(store, conn, 'E3')
    out = VS.round_done(store, USER, NEW, [], YES, 'yes', conn=conn)
    s = saved(store)
    assert out['queued'] == ['E2'] and 'E3' in out['from_footage'] and not [r for r in s['references'].values() if r.get('kind') == 'sheet' and r['element_id'] == 'E3']
    row = view(store, conn)['round']['elements']['E3']
    assert row['from_footage'] is True and row['own'] is True and s['golden']['E3'] == mine['id']
    assert 'own' not in view(store, conn)['round']['elements']['E1']   # the footage picture's row is as before


def test_an_own_picture_removed_before_done_lets_the_set_be_made():
    store, conn = step1()
    mine = own(store, conn, 'E3')
    VS.reject_reference(store, USER, NEW, [], mine['id'], '', 'Removed')
    out = VS.round_done(store, USER, NEW, [], YES, 'yes', conn=conn)
    assert sorted(out['queued']) == ['E2', 'E3']


def test_a_footage_picture_stays_the_starting_picture_beside_an_own_picture():
    store, conn = step1()
    own(store, conn, 'E1')
    VS.round_done(store, USER, NEW, [], YES, 'yes', conn=conn)
    s = saved(store)
    assert s['golden']['E1'] == 'F1' and 'own' not in s['round']['elements']['E1']


def test_a_person_still_gets_the_sheet():
    store, conn = frames_only(doc_with(KILN, MASON)), FakeConn([])
    rows = [{'element_id': 'E2', 'prompt': 'the kiln'}, {'element_id': 'P1', 'prompt': 'kneels'}]
    VS.round_start(store, USER, NEW, [], rows, conn=conn)
    with pytest.raises(Problem, match='not used for people'):
        own(store, conn, 'P1')
    out = VS.round_done(store, USER, NEW, [], {r['element_id']: {'verdict': 'approve'} for r in rows}, 'yes', conn=conn)
    assert 'P1' in out['queued']


def test_an_own_picture_on_a_failed_card_becomes_its_reference():
    store, conn = step1()
    VS.round_done(store, USER, NEW, [], YES, 'yes', conn=conn)
    fail(store, 'E3', 'OpenAI rejected the request (HTTP 400).')
    back(store)   # the kiln's set is back: step 2
    mine = own(store, conn, 'E3')
    s = saved(store)
    row = s['round']['elements']['E3']
    assert row['from_footage'] is True and row['own'] is True and s['golden']['E3'] == mine['id']
    v = view(store, conn)
    assert not [i for i in v['waiting'] if i['group'] == 'E3'] and not v['round']['elements']['E3'].get('problem')
    kiln = sheets(s, 'E2')[0]
    done = VS.round_sets(store, USER, NEW, [], {'E2': {'verdict': 'yes', 'golden': kiln}}, 'Yes.', conn=conn, partial=True)
    assert done['pass'] == 'complete'   # nothing waits on the hose


def test_an_own_picture_beside_a_set_that_is_back_or_being_made_changes_nothing():
    store, conn, s = with_sets(doc_with(KILN, MASON))
    own(store, conn, 'E2')   # its set is back: the picture is one more choice of starting picture, as before
    row = saved(store)['round']['elements']['E2']
    assert not row.get('from_footage') and not row.get('own')
    two, conn2 = step1()
    VS.round_done(two, USER, NEW, [], YES, 'yes', conn=conn2)
    own(two, conn2, 'E3')   # its set is being made: nothing is cancelled
    row = saved(two)['round']['elements']['E3']
    assert not row.get('from_footage') and sheets(saved(two), 'E3', 'generating')


# ---------- F3 ----------

def making_round():
    """Step 2 with the kiln's set back and the hose's set made again (Make it now): the round is 'making'."""
    store, conn = step1()
    VS.round_done(store, USER, NEW, [], YES, 'yes', conn=conn)
    fail(store, 'E3', 'The model returned no picture: no image in the answer')
    s = back(store)
    VS.set_make(conn, store, USER, NEW, [], 'E3')
    assert view(store, conn)['round']['pass'] == 'making'
    return store, conn, sheets(s, 'E2')[0]


def test_a_ready_set_is_answered_while_another_is_being_made():
    store, conn, kiln = making_round()
    out = VS.set_answer(store, USER, NEW, [], 'E2', 'yes', kiln, '')
    assert out['stored'] is True
    v = view(store, conn)
    assert v['round']['elements']['E2']['answer'] == {'verdict': 'yes', 'golden': kiln, 'words': ''}
    with pytest.raises(Problem, match='E3: its set is being made'):
        g(lambda: VS.set_answer(store, USER, NEW, [], 'E3', 'yes', None, ''))


def test_an_unanswered_ready_set_is_listed_as_waiting_while_another_is_being_made():
    store, conn, kiln = making_round()
    kinds = sorted((i['group'], i['kinds'] if 'kinds' in i else i.get('kind')) for i in view(store, conn)['waiting'] if i['step'] == 'references')
    assert [k for k in kinds if k[0] == 'E2'] and not [k for k in kinds if k[0] == 'E3']


def test_done_waits_while_a_set_is_being_made_and_names_it():
    store, conn, kiln = making_round()
    with pytest.raises(Problem, match='1 set is still being made: Garden hose') as e:
        g(lambda: VS.round_sets(store, USER, NEW, [], {'E2': {'verdict': 'yes', 'golden': kiln}}, 'Yes.', conn=conn, partial=True))
    assert not sheets(saved(store), 'E2', 'approved') and '`' not in e.value.message


def test_the_answer_survives_the_other_set_coming_back():
    store, conn, kiln = making_round()
    VS.set_answer(store, USER, NEW, [], 'E2', 'yes', kiln, '')
    back(store)
    v = view(store, conn)
    assert v['round']['pass'] == 2 and v['round']['elements']['E2']['answer']['verdict'] == 'yes'


# ---------- F4 ----------

@pytest.mark.parametrize('error, words', [
    ('The model returned no picture: no image in the answer', 'The model returned no picture.'),
    ('OpenAI rejected the request (HTTP 400).', 'The picture service refused the request.'),
    ('ReadTimeout: HTTPSConnectionPool(host=x, port=443): Read timed out. (read timeout=120)', 'The picture service did not answer in time.'),
    ('KeyError: candidates', 'The picture could not be made.'),
])
def test_a_set_that_failed_in_the_call_says_why_in_one_plain_sentence(error, words):
    store, conn = step1()
    VS.round_done(store, USER, NEW, [], YES, 'yes', conn=conn)
    fail(store, 'E3', error)
    back(store)
    row = view(store, conn)['round']['elements']['E3']
    assert row['problem'] == words and not row.get('cause')


def test_a_set_that_fails_again_says_the_new_reason():
    store, conn, kiln = making_round()
    fail(store, 'E3', 'OpenAI rejected the request (HTTP 400).')
    v = view(store, conn)
    assert v['round']['pass'] == 2 and v['round']['elements']['E3']['problem'] == 'The picture service refused the request.'
    assert [i for i in v['waiting'] if i['group'] == 'E3']   # Make it now is offered again


# ---------- M1 ----------

def test_the_timing_file_is_written_only_when_it_holds_a_cue(tmp_path):
    files = {'index.html': b'<html></html>', 'index.motion.json': b'{"assertions": []}'}   # a stray one in the upload goes too
    M.prepare(tmp_path / 'a', files, gsap=b'g', fonts={}, refs={}, sidecar={'assertions': []})
    assert not (tmp_path / 'a/index.motion.json').exists()
    M.prepare(tmp_path / 'b', files, gsap=b'g', fonts={}, refs={}, sidecar=M.sidecar([1.0], ['#label']))
    assert json.loads((tmp_path / 'b/index.motion.json').read_text())['assertions'][0]['selector'] == '#label'
