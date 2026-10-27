"""design/91 batch 3: N4 life in the frame, N9 one world (the background line, light and colour measured), N11 no repeated message."""
from fractions import Fraction
from io import BytesIO
import types

from PIL import Image

from app import image_check as IC, visual_contract as VC, visuals_stage as VS
from test_visuals_stage_pure import FakeConn, FakeStore, RUN, USER, accepted, plan_doc, ref, saved, session, shot, store_with
from test_visuals_pure import GAPS, plan, shot as pshot


def kinds(doc):
    return {(w.get('shot_id'), w.get('scene_id'), w['kind']) for w in VC.validate_plan(doc, GAPS, Fraction(25))[1]}


def rest(a=100):
    return [pshot('VS1', a, 500, 'video'), pshot('VS2', 500, 1000, 'video')]


# ---------- N4 ----------

def test_a_busy_scene_with_one_subject_and_no_background_activity_warns():
    doc = plan([pshot('IM1', 0, 100, 'image')] + rest())
    assert (None, 'SC1', 'activity_missing') in kinds(doc)
    doc['gaps'][0]['scenes'][0]['activity_level'] = 'busy'
    found = kinds(doc)
    assert (None, 'SC1', 'life_missing') in found and (None, 'SC1', 'activity_missing') not in found
    doc['gaps'][0]['scenes'][0]['activity_level'] = 'quiet'
    assert (None, 'SC1', 'life_missing') not in kinds(doc)
    out, _ = VC.validate_plan(plan([pshot('IM1', 0, 100, 'image')] + rest()), GAPS, Fraction(25))
    assert 'activity_level' not in out['gaps'][0]['scenes'][0]   # absent stays absent


# ---------- N11 ----------

def test_the_same_message_twice_warns_unless_the_second_adds_something():
    a = {**pshot('IM1', 0, 100, 'image'), 'message': 'rat-trap bond uses fewer bricks and less mortar'}
    b = {**pshot('VS1', 100, 500, 'video'), 'message': 'the bond uses fewer bricks and less mortar'}
    doc = plan([a, b, pshot('VS2', 500, 1000, 'video')])
    found = {w['shot_id']: w for w in VC.validate_plan(doc, GAPS, Fraction(25))[1] if w['kind'] == 'message_repeated'}
    assert 'VS1' in found and 'IM1' in found['VS1']['message']
    b['adds'] = 'the figure: 25 % fewer bricks'
    assert not [w for w in VC.validate_plan(doc, GAPS, Fraction(25))[1] if w['kind'] == 'message_repeated']
    c = {**b, 'message': 'the wall stays cool inside', 'adds': ''}
    assert not [w for w in VC.validate_plan(plan([a, c, pshot('VS2', 500, 1000, 'video')]), GAPS, Fraction(25))[1] if w['kind'] == 'message_repeated']


# ---------- N9: the background line ----------

def world_session(studio=''):
    im = shot('IM1', 0, 500, 'image', narration='', element_ids=['E2'])
    doc = plan_doc([im], [shot('VS1', 900, 1150, 'video', subjects=[])])
    doc['elements'].append({'id': 'E2', 'name': 'Burnt brick', 'kind': 'object', 'identity': 'representative', 'requirements': 'a burnt brick'})
    if studio:
        doc['foundation']['studio_background'] = studio
    return doc, session(versions=[{'version': 1, 'file': {'key': 'run-1/visuals/plan-v1.json'}, 'plan_digest': 'd1', 'warnings': []}], current='d1', accepted=accepted(doc))


def test_a_picture_in_the_film_is_in_its_world_unless_the_treatment_allows_a_studio(monkeypatch):
    monkeypatch.setattr(VS, 'prices', lambda: {'image_inr': 4.0, 'video_inr_per_s': 8.9})
    doc, sess = world_session()
    store = store_with(sess, doc)
    body = {'request_id': 'w1', 'element_id': 'E2', 'name': 'brick', 'kind': 'isolated', 'subject': 'a brick', 'prompt': 'A brick.', 'shot_id': 'IM1'}
    out = VS.generate_image(FakeConn([]), store, USER, RUN, [], body)
    row = saved(store)['references'][out['reference_id']]
    world = [l for l in row['server_checklist'] if l['check'] == "the film's world"]
    assert world and world[0]['weight'] == 'should' and row['shot_id'] == 'IM1' and row['gap_id'] == 'G1'
    out = VS.generate_image(FakeConn([]), store, USER, RUN, [], {**body, 'request_id': 'w2', 'kind': 'sheet', 'shot_id': None})
    assert not [l for l in saved(store)['references'][out['reference_id']].get('server_checklist') or [] if l['check'] == "the film's world"]   # a sheet is a reference, not the film
    doc, sess = world_session('product shots on white, as the brand asks')
    store = store_with(sess, doc)
    out = VS.generate_image(FakeConn([]), store, USER, RUN, [], body)
    assert not [l for l in saved(store)['references'][out['reference_id']].get('server_checklist') or [] if l['check'] == "the film's world"]


# ---------- N9: light and colour, measured ----------

def png(rgb):
    b = BytesIO()
    Image.new('RGB', (64, 36), rgb).save(b, 'PNG')
    return b.getvalue()


def frames_store():
    sess = session(references={'F1': {**ref('F1', 'approved'), 'kind': 'frame', 'source': {'media_id': 'c1'}},
                               'F2': {**ref('F2', 'approved'), 'kind': 'frame', 'source': {'media_id': 'c9'}}},
                   gap_neighbours={'G1': {'before': 'c1', 'after': None}})
    store = FakeStore({'run-1/visuals/references/F1.png': png((70, 85, 65)), 'run-1/visuals/references/F2.png': png((235, 210, 60))})
    return store, sess


def test_a_picture_much_brighter_and_more_saturated_than_the_footage_beside_it_is_marked():
    store, sess = frames_store()
    line = IC.light_line(store, sess, {'gap_id': 'G1', 'element_kind': 'object', 'kind': 'keyframe'}, png((240, 205, 50)))
    assert line['pass'] is False and line['weight'] == 'must' and 'brighter' in line['seen'] and 'saturated' in line['seen']   # design/111 F18: a must
    assert IC.light_line(store, sess, {'gap_id': 'G1', 'element_kind': 'object', 'kind': 'keyframe'}, png((72, 88, 66)))['pass'] is True
    # without the gap, the film's footage frames together: the bright one pulls the average up
    assert IC.light_line(store, sess, {'element_kind': 'object', 'kind': 'keyframe'}, png((150, 148, 62)))['pass'] is True


def test_a_graphic_a_sheet_and_a_film_without_footage_frames_are_not_measured():
    store, sess = frames_store()
    assert IC.light_line(store, sess, {'element_kind': 'graphic', 'kind': 'isolated'}, png((255, 255, 255))) is None
    assert IC.light_line(store, sess, {'element_kind': 'object', 'kind': 'sheet'}, png((255, 255, 255))) is None
    assert IC.light_line(FakeStore({}), session(), {'element_kind': 'object', 'kind': 'keyframe'}, png((255, 255, 255))) is None


def test_the_light_line_joins_the_check_even_when_gemini_cannot_run(monkeypatch):
    monkeypatch.setattr(IC, 'settings', lambda: types.SimpleNamespace(GEMINI_API_KEY=types.SimpleNamespace(get_secret_value=lambda: '')))
    store, sess = frames_store()
    store.files['run-1/visuals/references/K1.png'] = png((240, 205, 50))
    rec = IC.run_check(store, sess, {'id': 'K1', 'gap_id': 'G1', 'element_kind': 'object', 'kind': 'keyframe', 'generation': {'parents': []}},
                       {'key': 'run-1/visuals/references/K1.png'}, None)
    assert rec['error'] == 'no Gemini key on the server' and rec['lines'][-1]['check'] == 'light and colour' and rec['lines'][-1]['pass'] is False and rec['must_failed'] == [rec['lines'][-1]]   # design/111 F18
