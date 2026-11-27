"""design/111 F18: a place carries its signs of use against its landmarks and the server writes two per shot in turn; the real-light line is composed
once per run from the footage; a place picture must look occupied; the measured light line is a must (SK's answer 8)."""
import json
import types
from fractions import Fraction
from io import BytesIO

import pytest
from PIL import Image

from app import image_check as IC, visual_contract as VC, visuals_stage as VS
from test_design106_pure import revise_start, start_store
from test_design110_f456_pure import doc_with, rich
from test_visuals_pure import GAPS, shot as pshot
from test_design111_f11_pure import golden_store, image
from test_visuals_stage_pure import FakeStore, ref, saved, session


def check(d):
    return VC.validate_plan(d, GAPS, Fraction(25))


def png(rgb):
    b = BytesIO()
    Image.new('RGB', (64, 36), rgb).save(b, 'PNG')
    return b.getvalue()


YARD = {'id': 'YARD', 'name': 'The yard', 'kind': 'place', 'identity': 'exact', 'requirements': 'the brick yard'}
SIGNS = [{'what': 'mortar droppings', 'landmark_id': 'L1'}, {'what': 'a stack of offcuts', 'landmark_id': 'L1'}, {'what': 'footprints in the dust', 'landmark_id': 'L1'}]


def test_a_place_shown_in_a_scene_needs_no_signs_of_use():
    """Release 1 of 27 Nov 2026, phase 2 part B (SK): until then two or more were required, each at a landmark, and the server wrote two per
    shot in turn (`signs_lines`); retired, see test_rel6b_signs_pure."""
    d = doc_with(rich(), pshot('VS2', 500, 1000, 'video'))
    d['elements'].append(dict(YARD))
    d['gaps'][0]['scenes'][0]['shots'][0]['element_ids'].append('YARD')
    check(d)
    d['elements'][-1]['signs_of_use'] = SIGNS[:2]
    check(d)
    assert VS._place_in(d, 'YARD', {'element_ids': []}) and not VS._place_in(d, 'E1', {'element_ids': ['BRICK']})


def test_the_real_light_line_is_composed_once_per_run_from_the_footage():
    sess = session(references={'F1': {**ref('F1', 'approved'), 'kind': 'frame'}, 'F2': {**ref('F2', 'approved'), 'kind': 'frame'}},
                   footage={'summary': {'camera': 'phone', 'support': 'handheld', 'look': 'natural'}, 'per_clip': {}})
    store = FakeStore({'run-1/visuals/references/F1.png': png((70, 85, 65)), 'run-1/visuals/references/F2.png': png((60, 70, 55))})
    line = VS.real_light_line(store, sess)
    assert line.startswith('Real light, as the footage has it: natural look, phone; dim light, ') and 'no added saturation' in line and sess['real_light_parts']['measured'].startswith('dim light')   # design/134 3: the parts are kept, the line is built per scene
    sess['footage']['summary']['look'] = 'graded'
    assert VS.real_light_line(store, sess) == line   # once per run
    assert VS.real_light_line(FakeStore({}), session()) == ''   # no footage, no frames: no line


def test_a_keyframe_prompt_carries_the_real_light_line_and_the_lines_ride_on_the_check(monkeypatch):
    monkeypatch.setattr(VS, 'real_light_line', lambda store, sess, scene=None: 'Real light, as the footage has it: natural look.')
    store = start_store()
    out = revise_start(store, role='start')
    assert 'Real light' not in saved(store)['references'][out['reference_id']]['generation']['prompt']   # E1 is a graphic there: no real-light line
    gstore = golden_store()   # E2 is an object: its isolated (golden) picture carries the line
    out = image(gstore, golden=True, parents=['S2', 'F2'], request_id='q-rl')
    row = saved(gstore)['references'][out['reference_id']]
    assert 'Real light, as the footage has it: natural look.' in row['generation']['prompt']
    assert 'occupied' not in {l['check'] for l in row['server_checklist']}   # no place in that shot


def test_the_measured_light_line_is_a_must_now(monkeypatch):
    monkeypatch.setattr(IC, 'settings', lambda: types.SimpleNamespace(GEMINI_API_KEY=types.SimpleNamespace(get_secret_value=lambda: '')))
    sess = session(references={'F1': {**ref('F1', 'approved'), 'kind': 'frame', 'source': {'media_id': 'c1'}}}, gap_neighbours={'G1': {'before': 'c1', 'after': None}})
    store = FakeStore({'run-1/visuals/references/F1.png': png((70, 85, 65)), 'run-1/visuals/references/K1.png': png((240, 205, 50))})
    rec = IC.run_check(store, sess, {'id': 'K1', 'gap_id': 'G1', 'element_kind': 'object', 'kind': 'keyframe', 'generation': {'parents': []}}, {'key': 'run-1/visuals/references/K1.png'}, None)
    assert rec['lines'][-1]['check'] == 'light and colour' and rec['lines'][-1]['weight'] == 'must' and rec['lines'][-1]['pass'] is False
    assert [l['check'] for l in rec['must_failed']] == ['light and colour']
    assert IC.LIGHT_JUMP == {'brightness': 0.15, 'saturation': 0.15, 'warmth': 0.08}   # the threshold stays; tuned if VW-7 shows false refusals
