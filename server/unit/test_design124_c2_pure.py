"""design/124 C2 trial: the seven problems the trial found in version 3's visuals stage (SK, 29 Oct 2026: "Yes, fix all seven").
1 route code words; 2 a subject's beats start and end in its states, the refusal names the shot, subject and beat; 3 the treatment's `images` is a count;
4 a material spec without proportions is refused; 5 a footage shot needs no information_progression; 6 a drawn shot is named at plan time and finished
after the picture search (scene refused at draw, unresearched sizes refused at spec approval, warned in the plan); 7 light, proportions and technique."""
import copy
import json
from fractions import Fraction
from pathlib import Path

import pytest

from app import visual_contract as VC, visuals_stage as VS
from app.errors import Problem
from drawn_fixture import as_drawn
from test_batch89b_pure import SPEC, graphic_session
from test_design91_b1_pure import video
from test_visuals_pure import GAPS, plan, shot as pshot
from test_visuals_stage_pure import FakeConn, RUN, USER, accepted, g, gap_digest, saved, store_with

ROOT = Path(__file__).resolve().parents[2]
VIS = next(s for s in json.loads((ROOT / 'server' / 'procedures' / 'v3.json').read_text(encoding='utf-8'))['stages'] if s['name'] == 'visuals')
PART = {p['name']: p['text'] for p in VIS['parts']}
UNTRIED = {'part': 'cavity', 'measure': 'width', 'value': None, 'unit': 'mm', 'source': '', 'status': 'unknown', 'tried': ''}


def check(d):
    return VC.validate_plan(d, GAPS, Fraction(25))


def kinds(d):
    return {(w.get('shot_id') or w.get('scene_id') or w.get('element_id'), w['kind']) for w in check(d)[1]}


# ---------- 1. route code words ----------

def test_the_common_part_gives_each_route_its_code_word_for_the_treatment():
    for code in ('footage', 'still', 'graphic_sequence', 'video', 'drawn'):
        assert f'(`{code}`)' in VIS['prompt'], code
    assert "the treatment's `routes` and `shots[].route` use" in VIS['prompt']


# ---------- 2. beats start and end in the subject's states ----------

def test_a_first_beat_off_the_start_state_is_refused_naming_shot_subject_beat_and_field():
    d = plan([video('VS1', 0, 250, [(0, 125, 3), (125, 250, 3)]), pshot('IM2', 250, 1000, 'image')])
    d['gaps'][0]['scenes'][0]['shots'][0]['subjects'][0]['beats'][0]['start']['pose'] = 'standing'
    with pytest.raises(ValueError, match=r"Beat starting state must continue this subject's preceding state: shot VS1, subject E1, beat B1 differs in pose"):
        check(d)


def test_a_last_beat_off_the_end_state_is_refused_naming_shot_subject_beat_and_field():
    d = plan([video('VS1', 0, 250, [(0, 125, 3), (125, 250, 3)]), pshot('IM2', 250, 1000, 'image')])
    d['gaps'][0]['scenes'][0]['shots'][0]['subjects'][0]['end']['progress'] = '3 laid'
    with pytest.raises(ValueError, match=r"Final beat must leave the subject in the shot's ending state: shot VS1, subject E1, beat B2 differs in progress"):
        check(d)


def test_the_plan_part_says_beats_start_and_end_exactly_in_the_subjects_states():
    assert "Its first beat starts exactly in the subject's `start` state and its last beat ends exactly in its `end` state" in PART['plan']
    assert '(position, facing, pose, holding, progress, objects, gaze)' in PART['plan']


# ---------- 3, 4. the treatment's images; a material spec's proportions ----------

def test_the_treatment_part_says_images_is_a_whole_number_per_gap():
    assert '`images`, a whole number for the gap (a count, never a list' in PART['treatment']


def test_the_plan_part_says_a_material_spec_without_proportions_is_refused():
    assert 'a drawing spec is warned without them, a material spec refused' in PART['plan']
    d = plan([pshot('IM1', 0, 1000, 'image')])
    d['elements'].append({'id': 'BRICK', 'name': 'Brick', 'kind': 'material', 'identity': 'representative', 'requirements': 'a brick',
                          'material_spec': {'dimensions': [SPEC['dimensions'][0]], 'laid': 'on edge', 'pattern': 'alternating'}})
    with pytest.raises(ValueError, match='material spec of BRICK: give the proportions that matter'):
        check(d)


# ---------- 5. footage ----------

def test_a_footage_shot_needs_no_information_progression_and_a_generated_one_is_refused_by_name():
    check(plan([{**pshot('FT1', 0, 500, 'footage'), 'information_progression': ''}, pshot('IM2', 500, 1000, 'image')]))
    with pytest.raises(ValueError, match='shot IM1: describe the composition or information progression'):
        check(plan([{**pshot('IM1', 0, 500, 'image'), 'information_progression': ''}, pshot('IM2', 500, 1000, 'image')]))
    assert '(the 10 s limit and `information_progression` among them)' in PART['plan']


# ---------- 6. a drawn shot: named at plan time, finished after the picture search ----------

def drawn_plan(**over):
    return plan([{**as_drawn({**pshot('DR1', 0, 100, 'diagram'), 'drawing_spec': copy.deepcopy(SPEC)}), **over}, pshot('IM2', 100, 1000, 'image')])


def test_a_drawn_shot_without_its_scene_passes_the_plan_check():
    out, _ = check(drawn_plan(scene_svg=None))
    assert out['gaps'][0]['scenes'][0]['shots'][0]['scene_svg'] is None
    with pytest.raises(ValueError, match='at_s or word'):   # a scene that is named is still checked
        check(drawn_plan(scene_svg={'sha256': 'a' * 64, 'actions': [{'kind': 'appear', 'ids': ['x']}]}))


def test_adding_the_scene_after_acceptance_needs_no_re_acceptance():
    doc = drawn_plan(scene_svg=None)
    later = drawn_plan()
    assert gap_digest(doc, doc['gaps'][0]) == gap_digest(later, later['gaps'][0])


def drawn_store(scene_svg=None):
    doc, sess = graphic_session()
    doc['gaps'][0]['scenes'][0]['shots'][0].update(visual_type='drawn', depicts='the wall', scene_svg=scene_svg)
    sess['spec_approvals'] = {'DG1': {'digest': VS.spec_digest(SPEC)}}
    sess['accepted'] = accepted(doc)
    return store_with(sess, doc)


def test_draw_is_refused_while_the_shot_has_no_scene():
    with pytest.raises(Problem, match='DG1 has no scene yet'):
        g(lambda: VS.render_drawn(FakeConn([]), drawn_store(), USER, RUN, [], {'shot_id': 'DG1'}))
    with pytest.raises(Problem, match='names no uploaded scene'):
        g(lambda: VS.render_drawn(FakeConn([]), drawn_store({'sha256': 'b' * 64, 'actions': []}), USER, RUN, [], {'shot_id': 'DG1'}))


def spec_store(doc, sess):
    sess['accepted'] = accepted(doc)   # the spec's sizes are part of the gap
    return store_with(sess, doc)


def test_an_unresearched_size_is_warned_in_the_plan_and_refused_at_spec_approval():
    unresearched = {**SPEC, 'dimensions': [SPEC['dimensions'][0], UNTRIED], 'illustrative': False}
    out, warns = check(drawn_plan(drawing_spec=unresearched))
    w = [x for x in warns if x['kind'] == 'spec_unresearched']
    assert w and w[0]['shot_id'] == 'DR1' and 'record the sources tried' in w[0]['message'] and 'refused when the spec is approved' in w[0]['message']
    assert ('DR1', 'spec_unresearched') not in kinds(drawn_plan())   # the shared fixture tried all four
    doc, sess = graphic_session()
    doc['gaps'][0]['scenes'][0]['shots'][0]['drawing_spec'] = unresearched
    with pytest.raises(Problem, match='record the sources tried'):
        g(lambda: VS.approve_spec(spec_store(doc, sess), USER, RUN, [], 'DG1', ''))
    store = spec_store(doc, sess)
    with pytest.raises(Problem, match='record the sources tried'):
        g(lambda: VS.approve_specs(store, USER, RUN, [], ''))
    assert not saved(store).get('spec_approvals')   # nothing half-approved
    half = {**SPEC, 'dimensions': [SPEC['dimensions'][0], {**UNTRIED, 'tried': 'not in the client brochure; no footage frame shows it'}]}
    doc['gaps'][0]['scenes'][0]['shots'][0]['drawing_spec'] = half
    with pytest.raises(Problem, match="'illustrative' is earned only after all four sources were tried"):
        g(lambda: VS.approve_spec(spec_store(doc, sess), USER, RUN, [], 'DG1', ''))
    doc['gaps'][0]['scenes'][0]['shots'][0]['drawing_spec'] = SPEC
    assert VS.approve_spec(spec_store(doc, sess), USER, RUN, [], 'DG1', '')['shot_id'] == 'DG1'


def test_an_unresearched_material_spec_is_warned_in_the_plan_and_refused_at_approval():
    mat = {'id': 'BRICK', 'name': 'Brick', 'kind': 'material', 'identity': 'representative', 'requirements': 'a brick',
           'material_spec': {'dimensions': [{**UNTRIED, 'part': 'brick', 'measure': 'length'}], 'laid': 'on edge', 'pattern': 'alternating', 'proportions': ['3 : 1.5 : 1']}}
    d = plan([pshot('IM1', 0, 1000, 'image')])
    d['elements'].append(mat)
    assert ('BRICK', 'spec_unresearched') in kinds(d)
    doc, sess = graphic_session()
    doc['elements'].append(mat)
    with pytest.raises(Problem, match='material spec of BRICK: brick length is unknown: record the sources tried'):
        g(lambda: VS.approve_spec(spec_store(doc, sess), USER, RUN, [], 'element:BRICK', ''))


def test_the_text_names_the_drawn_shot_at_plan_time_and_uploads_the_scene_after_the_picture_search():
    assert 'A drawn shot is named at plan time by `visual_type: drawn` alone' in PART['plan']
    assert 'are warned in the plan (`spec_unresearched`) and refused when the spec is approved' in PART['plan']
    assert 'uploaded first with' not in PART['later'] and 'its `scene_svg` comes after the picture search' in PART['later']
    assert 'refused while the shot has no uploaded scene or its drawing spec is not approved' in PART['later']


# ---------- 7. warnings ----------

def test_a_scene_of_graphics_only_asks_no_light():
    assert ('SC1', 'light_missing') not in kinds(plan([as_drawn(pshot('DR1', 0, 500, 'diagram')), pshot('DG2', 500, 1000, 'diagram')]))
    assert ('SC1', 'light_missing') in kinds(plan([as_drawn(pshot('DR1', 0, 500, 'diagram')), pshot('IM2', 500, 1000, 'image')]))
    assert 'a scene of graphics only (diagrams, sequences, drawn) has none' in PART['plan']


def test_proportions_are_asked_only_of_a_drawing_of_a_real_object():
    no_props = {**SPEC, 'proportions': []}
    assert ('DR1', 'spec_proportions_missing') in kinds(drawn_plan(drawing_spec=no_props))   # E1 is an object
    d = drawn_plan(drawing_spec=no_props, element_ids=['CURE'])
    d['elements'].append({'id': 'CURE', 'name': 'Curing', 'kind': 'process', 'identity': 'representative', 'requirements': 'seven days wet'})
    assert ('DR1', 'spec_proportions_missing') not in kinds(d)   # a day-count strip
    assert ('DR1', 'spec_proportions_missing') not in kinds(drawn_plan(drawing_spec=no_props, graphic_kind='chart'))


def test_the_text_says_when_a_technique_is_exact():
    assert 'a technique is `identity: representative` (the trade\'s usual way) unless its fact or size cites the footage' in PART['plan']


def test_a_spec_researched_after_acceptance_keeps_the_gap_accepted():
    """design/124 C2 fix 6: drawing and material specs are finished after the picture search and approved in their own table; the gap's acceptance stays."""
    from copy import deepcopy
    from test_visuals_stage_pure import plan_doc, shot
    from app.visual_contract import gap_digest
    doc = plan_doc([shot('DG1', 0, 250, 'diagram', drawing_spec={'parts': ['brick'], 'dimensions': []})], [shot('VS1', 900, 1150, 'video')])
    doc['elements'].append({'id': 'M1', 'name': 'Brick', 'kind': 'material', 'identity': 'representative', 'requirements': 'a brick', 'material_spec': {'dimensions': []}})
    before = gap_digest(doc, doc['gaps'][0])
    later = deepcopy(doc)
    later['gaps'][0]['scenes'][0]['shots'][0]['drawing_spec']['dimensions'] = [{'part': 'brick', 'measure': 'length', 'value': 230, 'unit': 'mm', 'status': 'measured'}]
    later['elements'][-1]['material_spec']['dimensions'] = [{'part': 'brick', 'measure': 'length', 'value': 230, 'unit': 'mm', 'status': 'measured'}]
    assert gap_digest(later, later['gaps'][0]) == before
    later['gaps'][0]['scenes'][0]['shots'][0]['purpose'] = 'something else'   # a real change still needs acceptance
    assert gap_digest(later, later['gaps'][0]) != before
