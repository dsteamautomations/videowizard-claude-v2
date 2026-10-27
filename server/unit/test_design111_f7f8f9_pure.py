"""design/111 F7, F8, F9. F7: where each person looks is a target (a landmark or a named person), a head turn and a mouth, per state; "as before" is refused;
a look-only shot is warned toward a profile or back view; the eye line goes into the start, the end and the motion text, with the two constraints, and the
end picture is checked. F8: every video shot names three fixed things from the landmarks; the end prompt and the motion text say the background is Image 1's
with those three named; the end picture and the take are checked. F9: when the action places something, the end prompt says how it sits, from the facts and
the material spec, never guessed; the end picture is checked."""
import copy
import json
from fractions import Fraction

import pytest

from app import library as L, visual_contract as VC, visuals_stage as VS
from app.video_providers import motion_text
from test_design110_f456_pure import HEAD, doc_with, rich
from test_design91_b1_pure import st
from test_visuals_pure import GAPS, shot as pshot

GAZE = {'target': 'L1', 'head_turn': 'toward the table, about 30°', 'mouth': 'closed'}


def check(d):
    return VC.validate_plan(d, GAPS, Fraction(25))


def person_shot():
    """rich() with E1 a person: every state carries a gaze, the shot names its three fixed things."""
    sh = rich()
    m = sh['subjects'][0]
    for state in (m['start'], m['end'], *(x for b in m['beats'] for x in (b['start'], b['end']))):
        state['gaze'] = copy.deepcopy(GAZE)
    sh['fixed'] = ['L1', 'L2', 'L3']
    sh['face_in_frame'] = True
    return sh


def scene_with_landmarks(d):
    d['gaps'][0]['scenes'][0]['landmarks'] = [{'id': 'L1', 'description': 'the table'}, {'id': 'L2', 'description': 'the window at the back'}, {'id': 'L3', 'description': 'the door at the right'}]
    return d


# ---------- F7 ----------

def test_a_persons_states_carry_a_gaze_when_the_face_is_in_frame_and_a_look_only_shot_is_warned():
    d = scene_with_landmarks(doc_with(person_shot(), pshot('VS2', 500, 1000, 'video')))
    out, warnings = check(d)
    assert out['gaps'][0]['scenes'][0]['shots'][0]['subjects'][0]['start']['gaze'] == GAZE
    bad = copy.deepcopy(d)
    bad['gaps'][0]['scenes'][0]['shots'][0]['subjects'][0]['start'].pop('gaze')
    bad['gaps'][0]['scenes'][0]['shots'][0]['subjects'][0]['beats'][0]['start'].pop('gaze')
    with pytest.raises(ValueError, match='E1 is a person with the face in frame: give gaze'):
        check(bad)
    bad['gaps'][0]['scenes'][0]['shots'][0]['face_in_frame'] = False
    check(bad)   # from behind, or hands in close: no eye line asked
    bad = copy.deepcopy(d)
    bad['gaps'][0]['scenes'][0]['shots'][0]['subjects'][0]['end']['gaze']['target'] = 'NOPE'
    bad['gaps'][0]['scenes'][0]['shots'][0]['subjects'][0]['beats'][1]['end']['gaze']['target'] = 'NOPE'
    with pytest.raises(ValueError, match='gaze target is a landmark of the scene or a named element'):
        check(bad)
    look = copy.deepcopy(d)
    m = look['gaps'][0]['scenes'][0]['shots'][0]['subjects'][0]
    for state in (m['end'], m['beats'][0]['end'], m['beats'][1]['start'], m['beats'][1]['end']):
        state['objects'] = copy.deepcopy(m['start']['objects'])   # nothing moves: the look is the only change
    look['gaps'][0]['scenes'][0]['shots'][0]['changes'] = [{'what': 'E1 looks up from the course to the window', 'beat_id': 'B2'}]
    _, warnings = check(look)
    assert any(w['kind'] == 'look_only' and 'profile' in w['message'] for w in warnings)


def test_as_before_and_facing_each_other_are_refused_in_a_prompt():
    for bad in ('The parents as before.', 'They sit as before, facing each other.', 'The father\'s gaze changes; the mother as before.'):
        with pytest.raises(ValueError, match='says nothing a picture can show'):
            L.check_prompt(bad)
    L.check_prompt("The father's eyes are on the gate; head turned toward it about 45°; mouth a closed smile.")


def test_the_eye_line_goes_into_start_end_and_motion_and_the_end_is_checked():
    d = scene_with_landmarks(doc_with(person_shot()))
    scene, sh = d['gaps'][0]['scenes'][0], d['gaps'][0]['scenes'][0]['shots'][0]
    assert VS.gaze_lines(d, scene, sh, 'start') == ["E1's eyes are on the table; head turned toward the table, about 30°; mouth closed. No one looks at the lens."]
    end = VS.gaze_lines(d, scene, sh, 'end')
    assert end == ["E1's eyes are on the table; head turned toward the table, about 30°; mouth closed. No one looks at the lens; no one looks where they looked in Image 1 unless named here."]
    assert VS.gaze_lines(d, scene, {**sh, 'subjects': []}, 'end') == []
    block = VS.composed_block(d, scene, sh, 'end')
    assert "E1's eyes are on the table" in block
    lines = VS.picture_rule_lines(d, scene, sh, 'end')
    assert any(l['check'] == 'eye lines' and 'no one looks at the lens' in l['pass_when'] for l in lines)
    assert not any(l['check'] == 'eye lines' for l in VS.picture_rule_lines(d, scene, sh, 'start'))


# ---------- F8 ----------

def test_a_video_shot_names_three_fixed_things_from_the_landmarks_and_the_end_and_the_take_keep_them():
    d = scene_with_landmarks(doc_with(person_shot(), pshot('VS2', 500, 1000, 'video')))
    check(d)
    bad = copy.deepcopy(d)
    bad['gaps'][0]['scenes'][0]['shots'][0]['fixed'] = ['L1', 'L2']
    with pytest.raises(ValueError, match='names three fixed things'):
        check(bad)
    bad['gaps'][0]['scenes'][0]['shots'][0]['fixed'] = ['L1', 'L2', 'L9']
    with pytest.raises(ValueError, match='L9 is not a landmark'):
        check(bad)
    two = copy.deepcopy(d)
    two['gaps'][0]['scenes'][0]['landmarks'] = two['gaps'][0]['scenes'][0]['landmarks'][:2]
    two['gaps'][0]['scenes'][0]['shots'][0]['fixed'] = ['L1', 'L2']
    check(two)   # a scene with fewer than three landmarks names them all
    scene, sh = d['gaps'][0]['scenes'][0], d['gaps'][0]['scenes'][0]['shots'][0]
    line = VS.fixed_line(scene, sh)
    assert line == "The background is Image 1's background: the table, the window at the back, the door at the right are in the same place, same size, same light."
    assert line in VS.composed_block(d, scene, sh, 'end') and line not in VS.composed_block(d, scene, sh, 'start')
    assert any(l['check'] == 'background kept' and 'the window at the back' in l['pass_when'] for l in VS.picture_rule_lines(d, scene, sh, 'end'))
    assert 'background is Image 1' in motion_text({'motion_prompt': 'm', 'subject_reconciliation': {}, 'duration_seconds': 5, 'end_image': {}, 'fixed_line': line})


# ---------- F9 ----------

def test_a_placed_thing_gets_its_how_it_sits_line_from_the_facts_and_the_spec_and_the_end_is_checked():
    d = scene_with_landmarks(doc_with(person_shot()))
    d['elements'][2]['kind'] = 'material'
    d['elements'][2]['material_spec'] = {'dimensions': [{'part': 'brick', 'measure': 'length', 'value': 190, 'unit': 'mm', 'source': 'brief', 'status': 'confirmed'}],
                                         'laid': 'on edge', 'joint': '10 mm mortar joints', 'pattern': 'one long face then one header', 'proportions': ['2 : 1']}
    d['visual_facts'] = [{'id': 'F1', 'about': 'BRICK', 'looks': 'a fired red brick', 'how': 'bedded on fresh mortar and tapped level', 'status': 'confirmed', 'source': 'the mason'}]
    scene, sh = d['gaps'][0]['scenes'][0], d['gaps'][0]['scenes'][0]['shots'][0]
    sh['subjects'][0]['beats'][-1]['action'] = 'sets one more brick on the course'
    sh['subjects'][0]['beats'][-1]['done'] = 'set one more brick on the course'
    lines = VS.sits_lines(d, scene, sh)
    assert lines == ['Red brick rests on the table with full contact; lined up with its neighbours; 10 mm mortar joints; bedded on fresh mortar and tapped level; not tilted, not floating.',
                     'Pointing trowel rests on the table with full contact; lined up with its neighbours; not tilted, not floating.']   # the brick the action sets, the trowel set down
    assert all(l in VS.composed_block(d, scene, sh, 'end') for l in lines)
    assert [l for l in VS.picture_rule_lines(d, scene, sh, 'end') if l['check'].startswith('sits')][0]['pass_when'].startswith('Red brick rests on the table with full contact')
    for b in sh['subjects'][0]['beats']:
        b.update(action='walks to the stack', done='walked to the stack')
    sh['props'] = []
    assert VS.sits_lines(d, scene, sh) == []   # no placing verb, nothing set down: no line
