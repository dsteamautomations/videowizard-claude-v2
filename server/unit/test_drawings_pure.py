"""Accurate images, build step 3 (design/194): a thing's drawing set on the server (app/drawings.py): accepted as data, checked, drawn,
stored, shown to the operator in the chat and approved by its exact content. Nothing here costs money and nothing is queued."""
import copy
import io

import pytest
from PIL import Image

from app import chat_flow as CF, drawings as DR, visuals_stage as VS
from app.errors import Problem
from test_design151_refs_pure import KILN, MASON, NEW, doc_with, new_store
from test_draw3d_pure import dovetail
from test_guide_route_pure import Conn
from test_visuals_stage_pure import USER, accepted, saved

THING = 'E1'      # the fixture's plinth: an object


@pytest.fixture
def film():
    doc = doc_with(KILN, MASON)
    return new_store(doc, {}, accepted=accepted(doc)), Conn()


def refused(fn):
    with pytest.raises((Problem, ValueError)) as e:
        fn()
    return getattr(e.value, 'message', None) or str(e.value)


def put(store, conn, d=None, thing=THING):
    return DR.set_drawing(conn, store, USER, NEW, [], thing, d or dovetail())


def test_a_sound_drawing_set_is_stored_and_drawn_and_waits_for_the_operator(film):
    store, conn = film
    out = put(store, conn)
    row = saved(store)['drawings'][THING]
    assert row['status'] == 'proposed' and row['sha256'] == out['sha256'] and row['level'] == 'engineered'
    assert [v['id'] for v in row['views']] == ['a', 'b', 'c', 'd']
    for v in row['views']:                                   # both sheets of every view are picture files in the film's store
        for k in ('labelled_key', 'plain_key'):
            assert store.files[v[k]][:8] == b'\x89PNG\r\n\x1a\n'
        im = Image.open(io.BytesIO(store.files[v['plain_key']]))
        assert im.size == (v['width'], v['height'])
    assert conn.queued == []                                  # free: nothing is queued, nothing is paid
    assert 'approve' in out['next']


def test_the_assumed_sizes_are_listed_for_the_operator(film):
    store, conn = film
    put(store, conn)
    row = saved(store)['drawings'][THING]
    assert row['assumed'] == ['slope of a tail: 1 in 7'] and row['sourced'] == ["board thickness: 18 mm (the joiner's drawing)"]


def test_the_same_drawing_set_again_changes_nothing_and_a_changed_one_must_be_approved_again(film):
    store, conn = film
    first = put(store, conn)
    DR.verdict(conn, store, USER, NEW, [], THING, first['sha256'], True, 'yes, that is the joint')
    assert put(store, conn)['unchanged'] and saved(store)['drawings'][THING]['status'] == 'approved'
    d = dovetail()
    d['facts'][0]['value'] = 20
    second = put(store, conn, d)
    assert second['sha256'] != first['sha256'] and saved(store)['drawings'][THING]['status'] == 'proposed'


def test_a_faulty_drawing_set_is_refused_in_plain_words_and_nothing_is_stored(film):
    store, conn = film
    d = dovetail()
    d['views'][0].pop('shows')
    assert 'what it shows' in refused(lambda: put(store, conn, d))
    assert 'drawings' not in saved(store)


def test_a_drawing_is_for_a_thing_of_the_plan_never_for_a_person(film):
    store, conn = film
    assert 'not an element of the plan' in refused(lambda: put(store, conn, thing='E99'))
    assert 'person' in refused(lambda: put(store, conn, thing='P1'))


def test_approval_is_by_the_exact_content_and_carries_the_operators_words(film):
    store, conn = film
    sha = put(store, conn)['sha256']
    assert 'changed' in refused(lambda: DR.verdict(conn, store, USER, NEW, [], THING, 'another', True, 'yes'))
    assert 'words' in refused(lambda: DR.verdict(conn, store, USER, NEW, [], THING, sha, True, '  '))
    DR.verdict(conn, store, USER, NEW, [], THING, sha, True, 'yes, that is the joint')
    row = saved(store)['drawings'][THING]
    assert row['status'] == 'approved' and row['verdict']['quote'] == 'yes, that is the joint' and row['verdict']['by'] == 'u1'


def test_a_correction_is_kept_with_the_drawing_and_asks_for_a_new_one(film):
    store, conn = film
    sha = put(store, conn)['sha256']
    assert 'what is wrong' in refused(lambda: DR.verdict(conn, store, USER, NEW, [], THING, sha, False, 'no', notes=''))
    out = DR.verdict(conn, store, USER, NEW, [], THING, sha, False, 'no', notes='the tails are too wide')
    row = saved(store)['drawings'][THING]
    assert row['status'] == 'rejected' and row['verdict']['notes'] == 'the tails are too wide' and 'drawn again' in out['next']


def test_only_an_approved_set_gives_sheets_to_the_image_model_and_never_more_than_two(film):
    store, conn = film
    sha = put(store, conn)['sha256']
    session = saved(store)
    assert DR.approved_sheets(session, THING) == []                       # proposed: nothing goes to a model
    DR.verdict(conn, store, USER, NEW, [], THING, sha, True, 'yes')
    sheets = DR.approved_sheets(saved(store), THING)
    assert [s['view'] for s in sheets] == ['d', 'a']                       # the angled view first, then the first flat view: at most two
    assert all(s['key'].endswith('-plain.png') and s['sha256'] for s in sheets)
    assert DR.approved_sheets(saved(store), 'E2') == []                    # a thing with no drawing set


def test_the_words_for_the_prompt_explain_the_sheets_sent_and_state_the_facts(film):
    store, conn = film
    sha = put(store, conn)['sha256']
    DR.verdict(conn, store, USER, NEW, [], THING, sha, True, 'yes')
    text = DR.words(store, saved(store), THING, first=2)
    assert 'Image 2 is From outside the corner' in text and 'Image 3 is The tail board, square on' in text
    assert 'slanted' in text                                               # a flat angled view is among them
    facts = DR.must_be_true(saved(store), THING)
    assert facts == ['board thickness: 18 mm', 'slope of a tail: 1 in 7']


def test_a_sheet_is_fetched_by_its_name(film):
    store, conn = film
    put(store, conn)
    for name in ('a', 'a-plain'):
        got = DR.file(store, NEW, [], THING, name)
        assert got['mime'] == 'image/png' and got['file'] == name + '.png' and __import__('base64').b64decode(got['base64'])[:4] == b'\x89PNG'
    assert 'no sheet' in refused(lambda: DR.file(store, NEW, [], THING, 'zz'))


def test_the_operator_is_asked_about_a_proposed_drawing_set_in_the_chat(film):
    store, conn = film
    sha = put(store, conn)['sha256']
    session = saved(store)
    ctx = {'session': session, 'plan': VS.current_plan(store, session), 'run': NEW, 'store': store, 'user': USER, 'outputs': [], 'conn': conn}
    items = CF._drawing_items(ctx)
    assert len(items) == 1
    it = items[0]
    assert it['id'] == f'drawing:{THING}:{sha[:10]}' and it['kind'] == 'drawing' and 'Plinth' in it['question']
    assert [b['label'] for b in it['buttons']] == ['Yes', 'Correct it'] and it['buttons'][1].get('needs_words')
    assert len(it['show']) == 4 and all(p['key'].endswith('.png') and '-plain' not in p['key'] for p in it['show'])     # the labelled sheets
    assert 'ASSUMED' in it['text'] and 'slope of a tail' in it['text'] and "the joiner's drawing" in it['text']
    it['_run']('yes', 'yes, right', '')
    assert saved(store)['drawings'][THING]['status'] == 'approved'
    session = saved(store)
    ctx['session'] = session
    assert CF._drawing_items(ctx) == []                                    # nothing more to ask


def test_correct_it_in_the_chat_records_the_operators_words(film):
    store, conn = film
    put(store, conn)
    session = saved(store)
    ctx = {'session': session, 'plan': VS.current_plan(store, session), 'run': NEW, 'store': store, 'user': USER, 'outputs': [], 'conn': conn}
    CF._drawing_items(ctx)[0]['_run']('correct', 'not yet', 'the plinth is 300 high, not 440')
    row = saved(store)['drawings'][THING]
    assert row['status'] == 'rejected' and row['verdict']['notes'] == 'the plinth is 300 high, not 440'
