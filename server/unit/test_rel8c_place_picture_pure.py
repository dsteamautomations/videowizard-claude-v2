"""Release 1 of 27 Nov 2026, phase 4, part C (SK): the picture that starts an AI video shot is made with the approved picture of the shot's
place, added by the server with its job in the server's own words; and it is made only after the references of everything the shot shows are
approved. Without a database."""
import pytest

from app import guide as G, takes as T, visuals_stage as V
from test_design151_refs_pure import KILN, MASON, NEW, doc_with, new_store
from test_guide_route_pure import STILL_WORDS, Conn, accepted, refused, rendered
from test_visuals_stage_pure import USER, saved

MASON_PIC = {'id': 'R1', 'job': 'the mason: copy his face, build and clothes'}
JOB = ('is the place (Clamp kiln): keep its walls, floor, surfaces, colours and fixed things. '
       'Take the camera angle, the framing and every position from Image 1 only, never from this picture.')


def ref(rid, element, status='approved', kind='sheet'):
    return {'id': rid, 'kind': kind, 'element_id': element, 'status': status, 'key': f'run-1/visuals/references/{rid}.png', 'sha256': 'sha-' + rid}


def film(*more, place=True, **over):
    """The mason's shot VS1, at the kiln when `place`; the plinth's and the mason's references are approved."""
    doc = doc_with(KILN, MASON)
    doc['gaps'][1]['scenes'][0]['shots'][0]['element_ids'] = ['E1', 'E2'] if place else ['E1']
    refs = {r['id']: r for r in (ref('R0', 'E1'), ref('R1', 'P1')) + more}
    store, conn = new_store(doc, refs, accepted=accepted(doc), **over), Conn()
    rendered(store, conn)
    for rid in refs:
        store.files[f'run-1/visuals/references/{rid}.png'] = b'png'
    return store, conn


def order(store, conn, parents=(MASON_PIC,), **more):
    out = G.request_still(conn, store, USER, NEW, [], 'VS1', STILL_WORDS, list(parents), **more)
    return conn.queued[-1]['request'], out


def test_the_still_carries_the_places_approved_picture_with_the_servers_job_sentence():
    store, conn = film(ref('K1', 'E2'))
    req, out = order(store, conn)
    ids = [p['id'] for p in req['parents']]
    assert ids[-2:] == ['R1', 'K1'] and f'Image {len(ids)} {JOB}' in req['prompt']
    still = saved(store)['guides']['VS1']['stills'][-1]
    assert [i['id'] for i in still['inputs']] == ['R1', 'K1'] and still['inputs'][1]['job'].startswith('the place (Clamp kiln)')   # the record lists it


def test_the_golden_picture_of_the_place_is_the_one_sent():
    store, conn = film(ref('K1', 'E2'), ref('K2', 'E2', kind='isolated'), golden={'E2': 'K2'})
    ids = [p['id'] for p in order(store, conn)[0]['parents']]
    assert 'K2' in ids and 'K1' not in ids


def test_a_picture_the_assistant_already_named_is_not_doubled_and_gets_the_sentence_about_the_camera():
    store, conn = film(ref('K1', 'E2'))
    req, _ = order(store, conn, [MASON_PIC, {'id': 'K1', 'job': 'the kiln behind him.'}])
    assert [p['id'] for p in req['parents']].count('K1') == 1
    assert 'is the kiln behind him. Take the camera angle, the framing and every position from Image 1 only, never from this picture.' in req['prompt']


def test_a_shot_that_names_no_place_gets_nothing_added():
    store, conn = film(ref('K1', 'E2'), place=False)
    req, _ = order(store, conn)
    assert [p['id'] for p in req['parents']][-1] == 'R1' and 'the place (' not in req['prompt']


def start_line(store):
    s = saved(store)
    return T.starts(s, V.current_plan(store, s), [])


def test_the_still_waits_for_the_references_of_what_the_shot_shows_and_is_due_when_the_last_is_approved():
    store, conn = film(ref('K1', 'E2', status='candidate'), round={'v': 2, 'kept': True, 'pass': 'complete', 'elements': {'E1': {}, 'P1': {}, 'E2': {}}})
    n = len(conn.queued)
    said = refused(lambda: order(store, conn))
    assert said == G.REFS_WAIT.format(shot='VS1', names='Clamp kiln') and len(conn.queued) == n       # refused with the name; nothing ordered
    line = start_line(store)
    assert 'the stills of' not in line and line.endswith('AI video: 1 still waits for the approved reference of: Clamp kiln. It is ordered when that is approved; no order is taken before.')
    s = saved(store)
    s['references']['K1']['status'] = 'approved'
    V.save_session(store, NEW, s)
    assert 'the stills of VS1 (1)' in start_line(store) and 'waits for the approved reference' not in start_line(store)
    assert order(store, conn)[1]['still_id']


def test_a_place_the_operator_left_without_a_reference_adds_no_picture_and_holds_nothing():
    store, conn = film(round={'v': 2, 'kept': True, 'pass': 'complete', 'elements': {'E1': {}, 'P1': {}, 'E2': {'ignored': True}}})
    req, _ = order(store, conn)
    assert 'the place (' not in req['prompt'] and 'the stills of VS1 (1)' not in start_line(store)   # ordered; nothing held it


def test_the_sixteen_picture_limit_still_refuses_and_counts_the_places_picture():
    own = tuple(ref(f'X{n}', 'E1') for n in range(13))
    store, conn = film(ref('K1', 'E2'), *own)
    said = refused(lambda: order(store, conn, [{'id': r['id'], 'job': 'the plinth, from another side'} for r in own]))
    assert said.startswith('17 input pictures; GPT image takes at most 16')


def test_a_masked_repair_sends_only_the_still_to_repair():
    store, conn = film(ref('K1', 'E2'))
    _, out = order(store, conn)
    s = saved(store)
    job = {'id': out['job_id'], 'request': {'kind': 'guide-still', 'shot_id': 'VS1', 'sha256': s['guides']['VS1']['sha256'], 'reference': {'id': out['still_id']}}}
    G.apply_result(s, job, 'retained', {'key': 'run-1/visuals/references/st.png', 'sha256': 'sha-still', 'bytes': 5, 'width': 1536, 'height': 864, 'overlay_key': 'ov.jpg', 'cost': {}}, None)
    V.save_session(store, NEW, s)
    req, _ = order(store, conn, [], repair_of=out['still_id'], region={'left': 0.1, 'top': 0.1, 'width': 0.2, 'height': 0.2})
    assert [p['id'] for p in req['parents']] == [out['still_id']]
