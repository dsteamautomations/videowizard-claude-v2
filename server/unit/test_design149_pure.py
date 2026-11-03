"""design/149 Set B on the server (SK's answers, 3 Nov 2026): B2 a change of clothes is a garment or a colour, not a note; B3 `repeating` retired;
B4 a size claim lives in `claims`; B5 a stray technique verb warns; B6 a figure the film states is never unknown; B9 a container that brings a thing is
named (warned), and the take prompt ends with where every subject and prop is."""
import copy
from fractions import Fraction

import pytest

from app import visual_contract as VC, visuals_stage as VS
from app.video_providers import motion_text
from test_design110_f456_pure import doc_with, rich
from test_visuals_pure import GAPS, plan, shot as pshot


def check(d):
    return VC.validate_plan(d, GAPS, Fraction(25))


def kinds(d):
    return {(w.get('shot_id') or w.get('scene_id'), w['kind']) for w in check(d)[1]}


def two_scenes(second_outfit, time_jump=''):
    d = doc_with(rich(), pshot('VS2', 500, 1000, 'video'))
    scene = d['gaps'][0]['scenes'][0]
    second = copy.deepcopy(scene)
    second.update(id='SC2', shots=[rich('VS2', 500, 1000)], outfit={'E1': second_outfit}, time_jump=time_jump)
    for b, c in zip(second['shots'][0]['subjects'][0]['beats'], second['shots'][0]['changes']):
        b['id'] = c['beat_id'] = b['id'] + 'b'
    scene['shots'] = [rich('VS1', 0, 500)]
    d['gaps'][0]['scenes'] = [scene, second]
    return d


# ---------- B2 ----------

def test_a_note_in_the_outfit_line_is_not_a_change_of_clothes():
    check(two_scenes('a faded blue shirt, a white lungi (the sleeve and forearms in frame)'))
    check(two_scenes('A white lungi and a faded blue shirt, to be confirmed (open question W03)'))   # the same garments and colours, another order


def test_a_garment_or_a_colour_change_still_needs_the_time_jump_and_unlisted_clothes_compare_as_text():
    with pytest.raises(ValueError, match='changes the colours of E1 .* time_jump'):
        check(two_scenes('a green shirt, a white lungi'))
    with pytest.raises(ValueError, match='changes the colours of E1 .* time_jump'):
        check(two_scenes('a faded blue shirt, white trousers'))
    check(two_scenes('a green shirt, a white lungi', time_jump='the next morning'))
    d = two_scenes('festival wear, as the client described')
    d['gaps'][0]['scenes'][0]['outfit'] = {'E1': 'festival wear, as the client described it'}   # nothing on the lists: the words themselves must match
    with pytest.raises(ValueError, match='changes the colours of E1'):
        check(d)


# ---------- B3 ----------

def test_repeating_is_refused_by_name_and_a_material_is_its_kind():
    d = plan([pshot('IM1', 0, 1000, 'image')])
    d['elements'].append({'id': 'BRICK', 'name': 'Red brick', 'kind': 'object', 'identity': 'representative', 'requirements': 'r', 'repeating': True})
    with pytest.raises(ValueError, match=r'`repeating` is retired \(design/149\).*BRICK'):
        check(d)
    d['elements'][-1].pop('repeating')
    check(d)   # an object with no spec is fine
    d['elements'][-1]['kind'] = 'material'
    with pytest.raises(ValueError, match='BRICK is a repeating material: give its material_spec'):
        check(d)


# ---------- B4 ----------

def test_a_size_word_in_the_descriptors_describes_and_a_size_claim_in_claims_is_checked():
    d = plan([{**pshot('IM1', 0, 100, 'image'), 'descriptors': ['a thin string', 'a smaller block']}, pshot('IM2', 100, 1000, 'image')])
    check(d)
    d['gaps'][0]['scenes'][0]['shots'][0]['claims'] = ['the string is thinner than a pencil']
    with pytest.raises(ValueError, match='is about size .* give the subject a size value and name compare_to'):
        check(d)


# ---------- B5 ----------

def test_a_technique_verb_with_no_technique_element_warns_and_the_warning_is_answerable():
    sh = rich()
    sh['subjects'][0]['beats'][0].update(action='points the joints of the course', done='pointed the joints of the course')
    d = doc_with(sh, pshot('VS2', 500, 1000, 'video'))
    out, warnings = check(d)
    w = [w for w in warnings if w['kind'] == 'technique_unnamed']
    assert len(w) == 1 and w[0]['shot_id'] == 'VS1' and "'pointing'" in w[0]['message'] and 'reference picture' in w[0]['message']
    d['gaps'][0]['scenes'][0]['shots'][0]['warning_answers'] = [{'kind': 'technique_unnamed', 'answer': 'the footage shows the trade\'s own pointing; no reference picture'}]
    check(d)
    d['elements'].append({'id': 'POINTING', 'name': 'Pointing', 'kind': 'technique', 'identity': 'representative', 'requirements': 'the joint struck flush'})
    assert not [w for w in check(d)[1] if w['kind'] == 'technique_unnamed']


# ---------- B6 ----------

def spec_shot(status, unit='kg/cm²', narration='a minimum crushing strength of 20, 35 and 75 kg/cm² for one, two and three storeys', claims=()):
    dims = [{'part': 'table', 'measure': 'strength for one storey', 'value': 20 if status != 'unknown' else None, 'unit': unit, 'source': 'the script' if status != 'unknown' else '', 'status': status,
             'tried': 'the client material, footage frames, a standard, an approved picture: none give it' if status == 'unknown' else ''}]
    sh = {**pshot('DG1', 0, 100, 'drawn'), 'narration': narration, 'claims': list(claims), 'depicts': 'the strength table',   # a graphic with figures is drawn (design/130 §12)
          'drawing_spec': {'dimensions': dims, 'proportions': ['three bars rising'], 'relationships': [], 'view': 'elevation', 'view_reason': 'a table reads flat', 'label': 'illustrative, not to scale' if status == 'unknown' else '',
                           'illustrative': status == 'unknown'}}
    return plan([sh, pshot('IM2', 100, 1000, 'image')])


def test_a_figure_the_narration_states_is_never_unknown():
    with pytest.raises(ValueError, match=r'the narration states 75 kg/cm².*strength for one storey is confirmed from the script, not unknown'):   # the figure beside the unit
        check(spec_shot('unknown'))
    check(spec_shot('confirmed'))
    check(spec_shot('unknown', narration='the bricks are tested for strength', claims=['the bricks are strong']))   # no figure spoken: unknown may stand (warned for research)
    with pytest.raises(ValueError, match='the narration states 20 kg/cm²'):
        check(spec_shot('unknown', narration='the bricks are tested', claims=['a strength of 20 kg/cm²']))   # a figure in the claims counts the same


# ---------- B9 ----------

def test_a_container_named_in_a_position_and_absent_from_the_shot_warns():
    sh = rich()
    sh['props'][0]['start'] = {'landmark_id': 'L1', 'relation': 'in the basket beside', 'amount': 1, 'unit': 'pace'}
    d = doc_with(sh, pshot('VS2', 500, 1000, 'video'))
    w = [w for w in check(d)[1] if w['kind'] == 'container_unnamed']
    assert len(w) == 1 and w[0]['shot_id'] == 'VS1' and 'basket' in w[0]['message'] and 'name it as a prop with its end' in w[0]['message']
    d['elements'].append({'id': 'BASKET', 'name': 'Brick basket', 'kind': 'object', 'identity': 'representative', 'requirements': 'a cane basket'})
    d['gaps'][0]['scenes'][0]['shots'][0]['element_ids'].append('BASKET')
    assert not [w for w in check(d)[1] if w['kind'] == 'container_unnamed']
    sh2 = rich('VS1', 0, 500)
    sh2['props'][0]['start'] = {'landmark_id': 'L1', 'relation': 'on the table beside', 'amount': 1, 'unit': 'pace'}   # a landmark's own word is scenery, not a container
    assert not [w for w in check(doc_with(sh2, pshot('VS2', 500, 1000, 'video')))[1] if w['kind'] == 'container_unnamed']


def test_the_take_prompt_ends_with_where_every_subject_and_prop_is():
    d = doc_with(rich(), pshot('VS2', 500, 1000, 'video'))
    out, _ = check(d)
    shot = out['gaps'][0]['scenes'][0]['shots'][0]
    f = VS.take_prompt_fields({'code': 'VW-19'}, out, shot, Fraction(25), 20)
    end = f['end_state']
    assert end[0] == 'two more bricks on the wall, set by the mason'   # the changes first, as before
    assert any(e.startswith('Mason: ') and 'the table' in e and 'bending' in e for e in end), end     # the subject's end against its landmark (by its description), with its pose
    assert any(e.startswith('Cow: ') and 'to the right of the table, 3 body-lengths' in e for e in end), end
    assert any(e.startswith('Pointing trowel: set down on the top course of the table, 2 bricks') for e in end), end   # the prop's end
    text = motion_text({'motion_prompt': 'm', 'subject_reconciliation': {}, 'continuity_notes': '', 'duration_seconds': 20, **f})
    assert 'By the end and until the last frame:' in text and 'Pointing trowel: set down' in text


# ---------- B10 ----------

def dim(status, source, value=190):
    return {'part': 'brick', 'measure': 'length', 'value': value, 'unit': 'mm', 'source': source, 'status': status}


def test_a_proposed_size_never_passes_the_check():
    d = plan([pshot('IM1', 0, 1000, 'image')])
    d['elements'][0]['size'] = [dim('proposed', 'recalled: IS 1077, to confirm')]
    with pytest.raises(ValueError, match=r'element E1: brick length is proposed \(recalled: IS 1077, to confirm\): put it to the operator in the missing-facts list'):
        check(d)
    d['elements'][0]['size'] = [dim('confirmed', 'the operator confirmed IS 1077')]
    check(d)


def test_a_size_confirmed_on_the_operators_word_shapes_a_drawing_but_is_never_written_on_screen():
    sh = {**pshot('DR1', 0, 100, 'drawn'), 'narration': 'the brick is laid on edge', 'depicts': 'the brick on edge',
          'drawing_spec': {'dimensions': [dim('confirmed', 'the operator confirmed IS 1077 (modular brick)')], 'proportions': ['about 2 : 1 : 1'], 'relationships': [], 'view': 'side', 'view_reason': 'the edge reads from the side'},
          'scene_motion': {'sha256': 'a' * 64, 'labels': ['brick on edge'], 'cues': []}}
    d = plan([sh, pshot('IM2', 100, 1000, 'image')])
    check(d)   # it shapes the drawing: no number on screen
    sh['scene_motion']['labels'] = ['190 mm']
    with pytest.raises(ValueError, match=r"brick length 190 mm is confirmed on the operator's word from a recalled standard .* and is written on screen"):
        check(d)
    sh['drawing_spec']['dimensions'][0]['source'] = 'IS 1077:1992, checked on the web with the run\'s yes'
    check(d)   # a real source: the number may be read
