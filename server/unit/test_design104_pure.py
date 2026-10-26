"""design/104, Release 6 (course D1-D3, C2-C5): the packet's bind advice, the scale-reference rule, and the new check lines."""
import json
import random
import types
from io import BytesIO
from pathlib import Path

from PIL import Image

from app import image_check as IC, visuals_stage as VS
from test_design101_pure import take_store
from test_design91_b1_pure import Video
from test_visuals_stage_pure import RUN, USER, FakeConn, FakeStore, accepted, gap_digest, plan_doc, ref, saved, session, shot, store_with

ROOT = Path(__file__).resolve().parents[1]
LIGHT = 'Late-morning sun from behind the half-built house, hard and warm'


def png(noisy):
    img = Image.new('L', (192, 108), 128)
    if noisy:
        rnd = random.Random(1)
        img.putdata([rnd.randrange(256) for _ in range(192 * 108)])
    buf = BytesIO()
    img.convert('RGB').save(buf, 'PNG')
    return buf.getvalue()


# ---------- D1, D2: the packet advises what to bind ----------

def advised_store(size='MS', place=True):
    store, doc = take_store()
    doc['elements'] += [{'id': 'BRICK', 'name': 'The client brick', 'kind': 'material', 'identity': 'exact', 'requirements': 'red-oxide wire-cut brick'},
                        {'id': 'LANE', 'name': 'The lane', 'kind': 'place', 'identity': 'exact', 'requirements': 'the site lane'}]
    sh = doc['gaps'][1]['scenes'][0]['shots'][0]
    sh['element_ids'] = ['E1', 'BRICK'] + (['LANE'] if place else [])
    if size:
        sh['size'] = size
    store.files['run-1/visuals/plan-v1.json'] = json.dumps({'document': doc}).encode('utf-8')
    s = saved(store)
    s['accepted'] = accepted(doc)   # the plan changed: its gaps accepted again, the shot bound again
    s['bindings']['VS1']['gap_digest'] = gap_digest(doc, doc['gaps'][1])
    s['references'].update({'F1': {**ref('F1', 'approved'), 'kind': 'frame', 'element_id': 'BRICK'}, 'F2': {**ref('F2', 'approved'), 'kind': 'frame', 'element_id': 'LANE'},
                            'F3': {**ref('F3', 'rejected'), 'kind': 'frame', 'element_id': 'BRICK'}})
    store.files['run-1/visuals/session.json'] = json.dumps(s).encode('utf-8')
    return store


def test_the_packet_advises_the_texture_and_the_look_reference():
    advice = VS.packet(advised_store('MS'), RUN, [], 'VS1')['preparation']['context']['bind_advice']
    by = {a['use']: a for a in advice}
    assert by['texture']['element_id'] == 'BRICK' and by['texture']['reference_ids'] == ['F1'] and 'take only its surface' in by['texture']['line']
    assert by['look']['element_id'] == 'LANE' and by['look']['reference_ids'] == ['F2'] and 'take only its light and colour' in by['look']['line']
    wide = VS.packet(advised_store('WS', place=False), RUN, [], 'VS1')['preparation']['context']['bind_advice']
    assert wide == []   # a wide shot needs no texture reference; no place in the shot
    assert any(a['use'] == 'texture' for a in VS.packet(advised_store(None, place=False), RUN, [], 'VS1')['preparation']['context']['bind_advice'])   # size not stated


def test_the_advice_changes_no_preparation_digest(monkeypatch):
    out = VS.packet(advised_store(), RUN, [], 'VS1')
    monkeypatch.setattr(VS, 'bind_advice', lambda *a: [])
    assert VS.packet(advised_store(), RUN, [], 'VS1')['preparation_digest'] == out['preparation_digest']


def test_the_procedure_says_how_to_make_a_scale_reference():
    doc = json.loads((ROOT / 'procedures' / 'v2.json').read_text(encoding='utf-8'))
    steps = next(s for s in doc['stages'] if s['name'] == 'visuals')['steps']
    assert 'scale reference' in steps[3] and 'true relative size' in steps[3]


# ---------- C2 ----------

def test_a_scene_picture_is_checked_for_wear_and_a_graphic_is_not():
    assert any(l['check'] == 'wear' and l['weight'] == 'should' for l in IC.lines_of({'element_kind': 'object'}))
    assert not any(l['check'] == 'wear' for l in IC.lines_of({'element_kind': 'graphic'}))


# ---------- C3 ----------

def detail_session(n_frames):
    store = FakeStore({})
    refs = {}
    for i in range(n_frames):
        k = f'run-1/visuals/references/F{i}.png'
        store.files[k] = png(True)
        refs[f'F{i}'] = {'id': f'F{i}', 'kind': 'frame', 'status': 'approved', 'key': k}
    return store, {'references': refs, 'gap_neighbours': {}}


def test_a_picture_much_smoother_than_its_footage_is_marked_and_the_ratio_is_reported():
    store, sess = detail_session(3)
    line = IC.detail_line(store, sess, {'kind': 'keyframe', 'element_kind': 'object'}, png(False))
    assert line['check'] == 'fine detail' and line['weight'] == 'should' and line['pass'] is False and 'of the fine detail' in line['seen']
    ok = IC.detail_line(store, sess, {'kind': 'keyframe', 'element_kind': 'object'}, png(True))
    assert ok['pass'] is True
    assert IC.detail_line(*detail_session(2), {'kind': 'keyframe', 'element_kind': 'object'}, png(False)) is None   # fewer than 3 frames
    assert IC.detail_line(store, sess, {'kind': 'keyframe', 'element_kind': 'graphic'}, png(False)) is None


# ---------- C4, C5 on takes ----------

def test_every_take_is_asked_the_frozen_person_line_and_a_lit_take_must_keep_its_light(monkeypatch, tmp_path):
    monkeypatch.setattr(IC, 'settings', lambda: types.SimpleNamespace(GEMINI_API_KEY=types.SimpleNamespace(get_secret_value=lambda: 'k')))
    video = tmp_path / 'o.mp4'
    video.write_bytes(b'mp4')
    assert any(l['check'] == 'frozen person' and l['weight'] == 'should' for l in IC.TAKE_LINES)
    IC.run_take_check({'motion_prompt': 'm', 'light': LIGHT}, video, 'a' * 64, Video)
    asked = json.dumps(Video.payload)
    assert 'light kept' in asked and LIGHT in asked and IC.LIGHT_KEPT['weight'] == 'must'
    IC.run_take_check({'motion_prompt': 'm'}, video, 'a' * 64, Video)
    assert 'light kept' not in json.dumps(Video.payload)


# ---------- C5 on pictures: the lines a picture gains from its scene, shot and elements ----------

def test_a_picture_gains_light_air_size_and_real_size_lines_only_when_given():
    scene = {'light': LIGHT, 'air': 'fine dust in the light'}
    shot_ = {'size': 'MS', 'element_ids': ['E1', 'BRICK']}
    elements = [{'id': 'BRICK', 'name': 'The client brick', 'size': [{'part': 'brick', 'measure': 'length', 'value': 23, 'unit': 'cm', 'status': 'confirmed'}]},
                {'id': 'E1', 'name': 'Wall'}]
    got = {l['check']: l for l in VS.picture_lines(scene, shot_, elements)}
    assert set(got) == {'light', 'air', 'shot size', 'real size'} and all(l['weight'] == 'should' for l in got.values())
    assert LIGHT in got['light']['pass_when'] and 'MS' in got['shot size']['pass_when'] and '23' in got['real size']['pass_when']
    assert VS.picture_lines({'air': 'clean'}, {}, []) == []
    assert VS.picture_lines({}, {}, elements) == []   # no shot elements named: no size line
