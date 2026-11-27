"""design/207 package B2 (SK, 16 Nov 2026): the pictures half of the visuals rules review.
D1: a person is their own likeness (a photo, with the operator's recorded yes) or a stand-in (made from the description). D2: a footage reuse that
passes the checks is kept, with the assistant's reason on record; nothing waits for the operator; 60 s apart, or a quarter of the film when that is
shorter. D3: every person gets a character sheet. D4: a living extra (kind animal) has no sheet: it is carried by its words. The size sentence is in
every picture's prompt (a still, a guide still), never in a reference set. A real speaker may have an AI picture. No check line says "crowd"."""
import json
from pathlib import Path

import pytest

from app import chat_flow as CF, guide as GD, visuals_stage as VS
from app.errors import Problem
from test_batch89_pure import MEDIA, clip_session
from test_design151_refs_pure import KILN, MASON, NEW, OLD, _req, doc_with, frames_only, new_store, with_sets
from test_ui_visuals_actions_pure import own, sheets, view
from test_visuals_stage_pure import FakeConn, RUN, USER, accepted, g, ref, saved, store_with

DOG = {'id': 'DOG', 'name': 'Street dog', 'kind': 'animal', 'identity': 'representative', 'requirements': 'a dog asleep by the gate',
       'description': 'an Indian street dog, short tan coat, a white chest, one ear folded',
       'size': [{'part': 'body', 'measure': 'height at the shoulder', 'value': 50, 'unit': 'cm', 'source': 'the breed standard', 'status': 'confirmed'}]}
PASSER = {'id': 'P2', 'name': 'Neighbour', 'kind': 'person', 'identity': 'representative', 'requirements': 'a neighbour who walks by in the background',
          'description': 'a woman of about sixty, stout, grey hair in a bun, glasses, a cotton sari'}
WORDS = 'Yes, he signed the release last week.'


@pytest.fixture(autouse=True)
def prices(monkeypatch):
    monkeypatch.setattr(VS, 'prices', lambda: {'image_inr': 20.0, 'video_inr_per_s': 8.0, 'usd_inr': 88.0})


def refused(fn):
    with pytest.raises((Problem, ValueError)) as e:
        g(fn)
    return getattr(e.value, 'message', None) or str(e.value)


def yes(store, conn, eid='P1', quote=WORDS, **kw):
    return g(lambda: VS.likeness(store, USER, NEW, [], eid, quote, conn=conn, **kw))


# ---------- D1: the permission record ----------

def test_the_permission_is_recorded_with_the_operators_words_and_one_run_log_line():
    store, conn, s = with_sets(doc_with(KILN, MASON))
    out = yes(store, conn)
    rec = saved(store)['likeness']['P1']
    assert rec['quote'] == WORDS and rec['by'] == 'u1' and rec['at'] and out['likeness'] is True and 'P1' in out['next']
    logged = [p for sql, p in conn.sql if 'vw2_log' in sql]
    assert len(logged) == 1 and WORDS in logged[0] and any('P1' in str(x) for x in logged[0])


@pytest.mark.parametrize('eid, quote, word', [('P1', '   ', "operator's own words"), ('E2', WORDS, 'E2 is a place'), ('E9', WORDS, 'E9 is not an element of the plan')])
def test_a_permission_without_words_or_for_a_thing_or_an_unknown_element_is_refused(eid, quote, word):
    store, conn, s = with_sets(doc_with(KILN, MASON))
    assert word in refused(lambda: VS.likeness(store, USER, NEW, [], eid, quote, conn=conn))
    assert 'likeness' not in saved(store) and not [1 for sql, _ in conn.sql if 'vw2_log' in sql]


def test_a_photo_of_a_person_is_refused_without_the_permission_and_says_how_to_record_it():
    store, conn, s = with_sets(doc_with(KILN, MASON))
    n = len(saved(store)['references'])
    said = refused(lambda: VS.supply_own(conn, store, USER, NEW, [], 'P1', content=b'x', name='x'))
    assert said == VS.own_picture_refused('person', {}, 'P1') and 'permission' in said and 'vw visuals likeness --element P1 --quote' in said
    assert len(saved(store)['references']) == n
    assert VS.own_picture_refused('place', {}, 'E2') is None and not hasattr(VS, 'OWN_PICTURE_FOR_PEOPLE')   # the switch is gone: the record decides


def test_with_the_permission_the_photo_is_taken_and_the_sheet_is_made_from_it():
    store, conn, s = with_sets(doc_with(KILN, MASON))
    yes(store, conn)
    photo = own(store, conn, 'P1')
    assert photo['kind'] == 'supplied' and photo['status'] == 'approved' and VS.likeness_photo(saved(store), 'P1') == photo['id']
    row = view(store, conn)['round']['elements']['P1']
    assert row['spec_changed'] is True and row['photo_changed'] is True   # the sheet made from words is out of date
    n0 = len(conn.inserted)
    out = VS.set_make(conn, store, USER, NEW, [], 'P1')
    req = _req(conn.inserted[n0])
    assert out['queued'] is True and [p['id'] for p in req['parents']] == [photo['id']]
    assert 'Image 1 is a photograph of this person' in req['prompt'] and VS.PERSON_SET in req['prompt']
    s = saved(store)
    assert s['round']['elements']['P1']['made']['photo'] == photo['id'] and not sheets(s, 'P1')   # the older set is rejected, the new one is being made
    assert 'the photo or the permission changed' in [r for r in s['references'].values() if r.get('status') == 'rejected' and r['element_id'] == 'P1'][0]['rejection']['notes']


def test_a_second_photo_replaces_the_first():
    store, conn, s = with_sets(doc_with(KILN, MASON))
    yes(store, conn)
    first = own(store, conn, 'P1')
    VS.set_make(conn, store, USER, NEW, [], 'P1')
    second = own(store, conn, 'P1', colour=(90, 9, 9), name='another.png')
    s = saved(store)
    assert first['id'] != second['id'] and VS.likeness_photo(s, 'P1') == second['id']
    assert VS._spec_changed(s, VS.current_plan(store, s), 'P1', s['round']['elements']['P1'])   # made from the first photo: out of date again
    assert 'make its sheet again' in second['next']


def test_a_stand_in_removes_the_record_and_marks_the_sheet_made_from_the_photo_out_of_date():
    store, conn, s = with_sets(doc_with(KILN, MASON))
    assert "operator's own words" in refused(lambda: VS.likeness(store, USER, NEW, [], 'P1', '', conn=conn, stand_in=True))
    yes(store, conn)
    photo = own(store, conn, 'P1')
    VS.set_make(conn, store, USER, NEW, [], 'P1')
    s = saved(store)
    for r in s['references'].values():   # the set made from the photo comes back
        if r.get('kind') == 'sheet' and r['status'] == 'generating':
            r.update(status='candidate', sha256='sha-' + r['id'], key='k')
    s['golden'] = {'P1': photo['id']}
    VS.save_session(store, NEW, s)
    out = yes(store, conn, quote='He would rather not be shown.', stand_in=True)
    s = saved(store)
    assert out['likeness'] is False and 'P1' not in s['likeness'] and 'P1' not in s['golden'] and VS.likeness_photo(s, 'P1') is None
    assert not sheets(s, 'P1') and any('the permission was removed' in r['rejection']['notes'] for r in s['references'].values() if r.get('status') == 'rejected' and r['element_id'] == 'P1')   # the review of design/207: the set made from the photo is rejected, not only marked out of date
    n0 = len(conn.inserted)
    VS.set_make(conn, store, USER, NEW, [], 'P1')
    req = _req(conn.inserted[n0])
    assert req['parents'] == [] and 'Image 1' not in req['prompt']   # the next sheet is made from words
    assert 'permission' in refused(lambda: VS.supply_own(conn, store, USER, NEW, [], 'P1', content=b'x', name='x'))   # and a photo is refused again
    assert len([p for sql, p in conn.sql if 'vw2_log' in sql]) == 2


def test_a_footage_frame_of_the_person_is_the_source_only_with_the_permission():
    doc = doc_with(KILN, MASON)
    store = frames_only(doc)
    s = saved(store)
    s['references']['F2'] = {**ref('F2', 'approved'), 'kind': 'frame', 'element_id': 'P1', 'width': 1920, 'height': 1080}
    VS.save_session(store, NEW, s)
    conn = FakeConn([])
    rows = [{'element_id': 'E1', 'frames': ['F1'], 'prompt': 'the plinth top'}, {'element_id': 'E2', 'prompt': 'the kiln during firing'}, {'element_id': 'P1', 'frames': ['F2'], 'prompt': 'kneels'}]
    assert VS.likeness_photo(s, 'P1') is None
    yes(store, conn)
    VS.round_start(store, USER, NEW, [], rows, conn=conn)
    VS.round_done(store, USER, NEW, [], {r['element_id']: {'verdict': 'approve'} for r in rows}, 'yes', conn=conn)
    req = {_req(p)['reference']['element_id']: _req(p) for p in conn.inserted}
    assert [p['id'] for p in req['P1']['parents']] == ['F2'] and 'Image 1 is a photograph of this person' in req['P1']['prompt']
    assert req['E2']['parents'] == []


def test_a_persons_footage_frame_or_photo_never_goes_to_the_picture_ai_without_the_permission():
    doc = doc_with(KILN, MASON)
    f2 = {**ref('F2', 'approved'), 'kind': 'frame', 'element_id': 'P1'}
    mine = {**ref('M1', 'approved'), 'kind': 'supplied', 'element_id': 'P1'}
    store = new_store(doc, {'F2': f2, 'M1': mine}, accepted=accepted(doc))
    body = lambda rid: {'request_id': 'q-' + rid, 'element_id': 'E2', 'name': 'kiln', 'kind': 'isolated', 'subject': 'the kiln', 'parents': [rid],
                        'prompt': 'Image 1 is the mason: take his look. The kiln in its yard.'}
    for rid, word in (('F2', 'footage frame'), ('M1', 'own picture')):
        said = refused(lambda: VS.generate_image(FakeConn([]), store, USER, OLD, [], body(rid)))
        assert word in said and 'permission' in said and 'vw visuals likeness --element P1' in said


def test_a_refused_photo_says_give_another_photo_or_make_the_person_a_stand_in():
    store, conn, s = with_sets(doc_with(KILN, MASON))
    yes(store, conn)
    own(store, conn, 'P1')
    VS.set_make(conn, store, USER, NEW, [], 'P1')
    s = saved(store)
    for r in s['references'].values():
        if r.get('kind') == 'sheet' and r['status'] == 'generating':
            r.update(status='failed', error='Provider rejected the request; inspect the saved attempt.')
    VS.save_session(store, NEW, s)
    row = view(store, conn)['round']['elements']['P1']
    assert row['problem'] == 'The picture service refused the request. ' + VS.LIKENESS_REFUSED and '`' not in row['problem']
    assert 'vw visuals own --element P1' in row['next'] and 'vw visuals likeness --element P1 --stand-in' in row['next'] and 'vw visuals round --make P1' in row['next']
    # the chat asks the same thing, one question with two buttons
    s = saved(store)
    ctx = {'session': s, 'plan': VS.current_plan(store, s), 'run': NEW, 'store': store, 'user': USER, 'outputs': [], 'conn': conn}
    item = next(i for i in CF._round_items(ctx) if i['id'].startswith('likeness:P1'))
    assert [b['label'] for b in item['buttons']] == ['Another photo', 'A stand-in'] and "refused this person's photo" in item['question']
    assert 'vw visuals own --element P1' in item['_run']('photo', '', '')['for_the_assistant']
    out = item['_run']('standin', '', 'Make him a stand-in.')
    assert out['queued'] is True and 'P1' not in saved(store)['likeness'] and _req(conn.inserted[-1])['parents'] == []
    # another photo given after a refusal: the card says only that the set failed, and Make it now uses the new photo
    store, conn, s = with_sets(doc_with(KILN, MASON))
    yes(store, conn)
    own(store, conn, 'P1')
    VS.set_make(conn, store, USER, NEW, [], 'P1')
    s = saved(store)
    for r in s['references'].values():
        if r.get('kind') == 'sheet' and r['status'] == 'generating':
            r.update(status='failed', error='Provider rejected the request.')
    VS.save_session(store, NEW, s)
    second = own(store, conn, 'P1', colour=(90, 9, 9), name='another.png')
    row = view(store, conn)['round']['elements']['P1']
    assert row['problem'] == 'The picture service refused the request.' and 'next' not in row
    VS.set_make(conn, store, USER, NEW, [], 'P1')
    assert [p['id'] for p in _req(conn.inserted[-1])['parents']] == [second['id']]


def test_a_stand_ins_failed_set_says_only_what_failed():
    store, conn, s = with_sets(doc_with(KILN, MASON))
    for r in s['references'].values():
        if r.get('kind') == 'sheet' and r['element_id'] == 'P1':
            r.update(status='failed', error='Provider rejected the request.')
    VS.save_session(store, NEW, s)
    row = view(store, conn)['round']['elements']['P1']
    assert row['problem'] == 'The picture service refused the request.' and 'next' not in row


# ---------- D3: a sheet for every person; D4: none for a living extra ----------

def test_every_person_gets_a_row_in_the_round_a_background_person_with_no_picture_too():
    doc = doc_with(KILN, MASON, PASSER)
    doc['gaps'][0]['scenes'][0]['shots'][0]['element_ids'] = ['E1', 'P1', 'P2']   # both are in a picture the AI makes (a person seen only in their own footage needs no row)
    store, conn = frames_only(doc), FakeConn([])
    rows = [{'element_id': 'E1', 'frames': ['F1'], 'prompt': 'the plinth top'}, {'element_id': 'E2', 'prompt': 'the kiln'}, {'element_id': 'P1', 'prompt': 'kneels'}]
    said = refused(lambda: VS.round_start(store, USER, NEW, [], rows, conn=conn))
    assert 'P2' in said and 'Every person gets a character sheet' in said
    rows.append({'element_id': 'P2', 'prompt': 'walks by, so seen full length'})
    VS.round_start(store, USER, NEW, [], rows, conn=conn)
    out = VS.round_done(store, USER, NEW, [], {r['element_id']: {'verdict': 'approve'} for r in rows}, 'yes', conn=conn)
    assert 'P2' in out['queued']   # no source picture: its sheet is made from the description


def test_an_older_films_person_with_no_source_picture_is_cued_for_its_sheet_from_words():
    doc = doc_with(KILN, MASON)
    s = saved(new_store(doc, {'W1': {**ref('W1', 'approved'), 'kind': 'web', 'element_id': 'E2'}}))
    due = {d['element_id']: d['next'] for d in VS.sheet_due(s, doc)}
    assert 'P1' in due and "from the person's description" in due['P1'] and '--parents' not in due['P1']


def test_an_animal_has_no_row_no_sheet_and_nothing_later_demands_one():
    doc = doc_with(KILN, MASON, DOG)
    doc['gaps'][1]['scenes'][0]['shots'][0]['element_ids'] = ['E1', 'DOG']
    store, conn = frames_only(doc), FakeConn([])
    rows = [{'element_id': 'E1', 'frames': ['F1'], 'prompt': 'the plinth top'}, {'element_id': 'E2', 'prompt': 'the kiln'}, {'element_id': 'P1', 'prompt': 'kneels'}]
    said = refused(lambda: VS.round_start(store, USER, NEW, [], rows + [{'element_id': 'DOG', 'prompt': 'the dog'}], conn=conn))
    assert 'DOG is an animal' in said and 'exact kind and size' in said
    VS.round_start(store, USER, NEW, [], rows, conn=conn)   # the round without it is whole
    said = refused(lambda: VS.generate_image(conn, store, USER, NEW, [], {'request_id': 'q1', 'element_id': 'DOG', 'kind': 'sheet', 'name': 'dog', 'subject': 'the dog', 'prompt': 'the dog', 'parents': []}))
    assert 'DOG is an animal' in said
    s = saved(store)
    s['accepted'] = accepted(doc)
    s['references']['F1']['status'] = 'approved'
    s['references']['F1']['element_kind'] = 'object'
    VS.save_session(store, NEW, s)
    assert VS.bind(store, USER, NEW, [], 'VS1', {'E1': ['F1']}, {})['elements'] == ['E1']   # the shot shows the dog; no reference of it is asked
    assert 'Cover every required shot element' in refused(lambda: VS.bind(store, USER, NEW, [], 'VS1', {}, {}))
    old = saved(new_store(doc, {'FD': {**ref('FD', 'approved'), 'kind': 'frame', 'element_id': 'DOG'}}))
    assert 'DOG' not in [d['element_id'] for d in VS.sheet_due(old, doc)]


def test_an_animals_words_and_size_are_in_the_prompt_of_a_picture_that_shows_it():
    doc = doc_with(KILN, MASON, DOG)
    assert VS.animal_lines(doc, ['E1', 'DOG']) == ['Street dog: an Indian street dog, short tan coat, a white chest, one ear folded.']
    assert VS.animal_lines(doc, ['E1', 'P1']) == []
    doc['gaps'][0]['scenes'][0]['shots'][0]['element_ids'] = ['E1', 'DOG']
    store = frames_only(doc)
    s = saved(store)
    s['accepted'] = accepted(doc)
    s['references']['F1']['status'] = 'approved'
    VS.save_session(store, NEW, s)
    out = VS.generate_image(FakeConn([]), store, USER, NEW, [], {'request_id': 'q1', 'element_id': 'E1', 'kind': 'keyframe', 'shot_id': 'IM1', 'name': 'plinth', 'subject': 'the plinth',
                                                                'parents': ['F1'], 'prompt': 'Image 1 is the footage frame of the plinth: take its shape. The plinth in the yard, a dog asleep beside it.'})
    prompt = saved(store)['references'][out['reference_id']]['generation']['prompt']
    assert 'Street dog: an Indian street dog, short tan coat' in prompt and 'Street dog: body height at the shoulder 50 cm' in prompt.split('Sizes:')[1]


# ---------- the word "crowd" ----------

def test_no_group_line_says_crowd():
    shot = {'groups': [{'kind': 'onlookers', 'count': 12, 'mode': 'varied', 'items': ['a red sari', 'a white cap']}]}
    lines = VS.group_rule_lines({'elements': []}, shot)
    assert lines[0]['pass_when'] == 'about 12 onlookers are in frame' and 'crowd' not in json.dumps(lines + VS.group_lines({'elements': []}, shot))


# ---------- D2: a reuse is kept without the operator's approval ----------

WHY = {'reason': 'the only shot of the kiln', 'considered': 'a drone view: none exists'}
CROP = [0.1, 0.1, 0.7, 0.7]


def film(first_cut_at_s, length_s=None):
    """The first cut shows c1 0-4 s at the given film second; VS1 fills film 36-46 s. Returns the outputs and the master's file."""
    ev = [{'kind': 'event', 'sub_clip_id': 'c1:SUB_01', 'source_in_frame': 0, 'source_out_frame': 100, 'timeline_in_frame': first_cut_at_s * 25, 'timeline_out_frame': first_cut_at_s * 25 + 100}]
    m = {'stage': 'master', 'unit': None, 'files': [{'name': 'master-v1.json', 'key': 'run-1/master-v1.json'}], 'summary': {'duration_frames': length_s * 25} if length_s else {}}
    return [MEDIA, m], json.dumps({'events': ev}).encode()


def reuse_store(first_cut_at_s, length_s=None, **extra):
    doc, sess = clip_session(clip_safe_zoom={'c1': 2.0}, **extra)
    store = store_with(sess, doc)
    outputs, store.files['run-1/master-v1.json'] = film(first_cut_at_s, length_s)
    return store, outputs


def test_a_reuse_with_its_reason_61_s_apart_in_a_long_film_is_kept_and_nothing_waits():
    store, outputs = reuse_store(107, length_s=1200)   # 107 s is 61 s after VS1 ends
    out = VS.fill_clip(store, USER, RUN, outputs, 'VS1', 'c1', 10.0, 'Use the kiln clip.', WHY, CROP)
    s = saved(store)
    assert out['reuse']['reason'] == WHY['reason'] and out['reuse']['considered'] == WHY['considered'] and out['reuse']['crop'] == CROP and 'approval' not in out['reuse']
    assert s['assets']['VS1']['reuse']['reason'] == WHY['reason'] and not s.get('reuse_pending')
    plan = VS.current_plan(store, s)
    assert not [i for i in VS.waiting(s, plan, 'VW-9', []) if 'reuse' in i['kind'].lower()]


@pytest.mark.parametrize('at_s, kept', [(71, True), (66, False)])
def test_in_a_100_second_film_a_quarter_of_its_length_is_far_enough(at_s, kept):
    store, outputs = reuse_store(at_s, length_s=100)   # 71 s: 25 s after VS1 ends; 66 s: 20 s
    if kept:
        assert VS.fill_clip(store, USER, RUN, outputs, 'VS1', 'c1', 10.0, 'yes', WHY, CROP)['reuse']['reason'] == WHY['reason']
    else:
        assert refused(lambda: VS.fill_clip(store, USER, RUN, outputs, 'VS1', 'c1', 10.0, 'yes', WHY, CROP)).endswith('is 20 s from c1:SUB_01; a reuse is at least 25 s apart.')


def test_with_no_film_length_the_distance_is_60_s_and_no_reason_is_refused_as_before():
    store, outputs = reuse_store(100)   # 54 s after VS1 ends
    assert 'is 54 s from c1:SUB_01; a reuse is at least 60 s apart.' in refused(lambda: VS.fill_clip(store, USER, RUN, outputs, 'VS1', 'c1', 10.0, 'yes', WHY, CROP))
    store, outputs = reuse_store(107, length_s=1200)
    said = refused(lambda: VS.fill_clip(store, USER, RUN, outputs, 'VS1', 'c1', 10.0, 'yes'))
    assert 'showing it again is a reuse' in said and '--reuse, --considered' in said and 'approval' not in said
    assert 'different stretch' in refused(lambda: VS.fill_clip(store, USER, RUN, outputs, 'VS1', 'c1', 2.0, 'yes', WHY, CROP))   # the other checks stay


def test_the_retired_approval_answers_plainly_and_an_older_waiting_reuse_is_no_longer_asked():
    old = {'VS1': {'action': 'clip', 'clip_id': 'c1', 'in_s': 10.0, 'reason': 'r', 'considered': 'c', 'crop': CROP, 'on_screen': 'x', 'quote': 'q'},
           'IM1': {'action': 'still', 'reference_id': 'F1', 'clip_id': 'c2', 'reason': 'r', 'considered': 'c', 'crop': CROP, 'on_screen': 'x', 'quote': 'q'}}
    store, outputs = reuse_store(107, length_s=1200, reuse_pending=old)
    said = refused(lambda: VS.approve_reuse(store, USER, RUN, outputs, 'VS1', 'Yes, reuse it.'))
    assert said == VS.REUSE_RETIRED and 'no longer needs' in said
    s = saved(store)
    assert not [i for i in VS.waiting(s, VS.current_plan(store, s), 'VW-9', []) if i['label'].startswith('Reuse')]
    VS.fill_clip(store, USER, RUN, outputs, 'VS1', 'c1', 10.0, 'Use the kiln clip.', WHY, CROP)   # the gate runs: the older entries are cleared
    assert not saved(store).get('reuse_pending') and saved(store)['assets']['VS1']['reuse']['reason'] == WHY['reason']
    src = Path(CF.__file__).read_text(encoding='utf-8')
    assert 'Allow it?' not in src and 'reuse to approve' not in src


# ---------- the size sentence in every picture's prompt ----------

def sized(doc, sid, gap, compare='E2'):
    doc['gaps'][gap]['scenes'][0]['shots'][0].update(claims=['a smaller plinth carries the same wall'], compare_to=compare, element_ids=['E1', compare])
    return doc


def test_the_size_sentence_reads_beside_the_person_when_a_person_is_the_comparison():
    doc = doc_with(KILN, MASON)
    shot = sized(doc, 'IM1', 0, 'P1')['gaps'][0]['scenes'][0]['shots'][0]
    assert VS.size_line(doc, shot) == 'Size is the point: Plinth, top width 230 mm, beside the person (Mason); the sizes read true against each other and the place.'
    shot['compare_to'] = 'E2'
    assert VS.size_line(doc, shot) == 'Size is the point: Plinth, top width 230 mm, against the Clamp kiln beside it; the sizes read true against each other and the place.'


def test_a_stills_picture_carries_the_size_sentence_and_its_must_line_and_a_reference_set_does_not():
    doc = sized(doc_with(KILN, MASON), 'IM1', 0)
    store = frames_only(doc)
    s = saved(store)
    s['accepted'] = accepted(doc)
    s['references']['F1']['status'] = 'approved'
    s['round'] = {'elements': {}}   # release 1, phase 2 part C: the round lists nothing here, so no reference holds the still
    VS.save_session(store, NEW, s)
    conn = FakeConn([])
    out = VS.generate_image(conn, store, USER, NEW, [], {'request_id': 'q1', 'element_id': 'E1', 'kind': 'keyframe', 'shot_id': 'IM1', 'name': 'plinth', 'subject': 'the plinth',
                                                         'parents': ['F1'], 'prompt': 'Image 1 is the footage frame of the plinth: take its shape. The plinth in the yard, the kiln behind it.'})
    r = saved(store)['references'][out['reference_id']]
    line = VS.size_line(doc, doc['gaps'][0]['scenes'][0]['shots'][0])
    assert line in r['generation']['prompt']
    assert {'check': 'size is the point', 'weight': 'must', 'pass_when': line[len('Size is the point: '):].rstrip('.')} in r['server_checklist']
    out = VS.generate_image(conn, store, USER, NEW, [], {'request_id': 'q2', 'element_id': 'E2', 'kind': 'sheet', 'name': 'kiln', 'subject': 'the kiln', 'parents': [],
                                                         'prompt': 'a country brick kiln as it stands during firing, nobody in the picture'})
    r = saved(store)['references'][out['reference_id']]
    assert 'Size is the point' not in r['generation']['prompt'] and 'size is the point' not in json.dumps(r.get('server_checklist') or [])


def test_a_guide_stills_prompt_carries_the_size_sentence():
    import test_guide_route_pure as GR
    doc = sized(doc_with(KILN, MASON), 'VS1', 1, 'P1')
    doc['gaps'][1]['scenes'][0]['shots'][0]['element_ids'] = ['E1']   # the fixture's scene has a box for the plinth only; the sentence reads compare_to, not the list
    refs ={'R0': {'id': 'R0', 'kind': 'sheet', 'element_id': 'E1', 'status': 'approved', 'key': 'run-1/visuals/references/R0.png', 'sha256': 'sha-R0'},   # phase 4 part C: a still waits for the plinth's approved reference
           'R1': {'id': 'R1', 'kind': 'sheet', 'element_id': 'P1', 'status': 'approved', 'key': 'run-1/visuals/references/R1.png', 'sha256': 'sha-R1'}}
    store, conn = new_store(doc, refs, accepted=accepted(doc)), GR.Conn()
    GR.rendered(store, conn)
    store.files['run-1/visuals/references/R1.png'] = b'png'
    GD.request_still(conn, store, USER, NEW, [], 'VS1', GR.STILL_WORDS, [{'id': 'R1', 'job': 'the mason: copy his face, build and clothes'}])
    assert 'Size is the point: Plinth, top width 230 mm, beside the person (Mason)' in conn.queued[-1]['request']['prompt']


# ---------- a real speaker may have an AI picture (the stage half) ----------

def test_an_ai_picture_of_a_real_speaker_is_no_longer_refused():
    doc = doc_with(KILN, {**MASON, 'speaker': True})
    store, conn = frames_only(doc), FakeConn([])
    out = VS.generate_image(conn, store, USER, NEW, [], {'request_id': 'q1', 'element_id': 'P1', 'kind': 'sheet', 'name': 'sheet-P1', 'subject': 'the mason', 'parents': [], 'prompt': 'he speaks to camera in the yard'})
    assert out['reference_id'] and len(conn.inserted) == 1


# ---------- the page: the permission line for a person; no reuse approval ----------

HTML = (Path(VS.__file__).parent / 'templates' / 'visuals.html').read_text(encoding='utf-8')


def test_the_page_shows_the_permission_line_for_a_person_and_no_reuse_approval():
    assert "I have this person\\'s permission to make AI pictures of them" in HTML and "action:'likeness'" in HTML and 'OWN_FOR_PEOPLE' not in HTML
    assert 'function reuseBox' not in HTML and 'approve-reuse' not in HTML and 'Approve the reuse' not in HTML
    assert 'an uploaded photo is not used for people' not in HTML


def test_the_api_has_the_likeness_route_and_keeps_the_retired_reuse_route():
    import inspect
    import uuid
    from app import main as M, web as W
    paths = {getattr(r, 'path', '') for r in M.app.routes}
    assert '/api/runs/{run_id}/visuals/likeness' in paths and '/api/runs/{run_id}/visuals/reuse' in paths   # an older tool may still call the reuse route
    body = M.Likeness(request_id=uuid.uuid4(), element_id='P1')
    assert body.quote == '' and body.stand_in is False   # the server function refuses the empty words in plain words
    assert 'visuals_stage.likeness(' in inspect.getsource(M.visuals_likeness) and 'visuals_stage.approve_reuse(' in inspect.getsource(M.visuals_reuse)
    assert "'likeness': lambda: V.likeness(" in inspect.getsource(W._visuals_act)   # one flow, two front ends: the page calls the same function


def test_the_page_data_carries_the_permission_records():
    store, conn, s = with_sets(doc_with(KILN, MASON))
    assert view(store, conn)['likeness'] == {}
    yes(store, conn)
    assert view(store, conn)['likeness']['P1']['quote'] == WORDS


def test_the_elements_answer_leaves_out_an_animal_and_names_it_as_needing_no_reference():
    """design/207 (D4): `vw visuals elements` lists what the reference round takes; a living extra is carried by its words."""
    plan = {'elements': [MASON, KILN, DOG, {'id': 'G1', 'name': 'Chart', 'kind': 'graphic'}]}
    out = VS.elements_answer(plan, [])
    assert [e['id'] for e in out['elements']] == [MASON['id'], KILN['id']] and out['graphics'] == ['G1'] and out['no_reference'] == ['DOG']
    assert set(out['matches']) == {MASON['id'], KILN['id']}
