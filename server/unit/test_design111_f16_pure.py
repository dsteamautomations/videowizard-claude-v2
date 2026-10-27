"""design/111 F16: a person carries a fixed description (build, age, skin, hair, posture, garment types and how worn) and each scene gives the garment
colours (outfit); a colour change from the scene before needs the script's time jump; the server pastes both layers into every keyframe prompt, the
continuity line of the take and the not-this line, and the check compares against both."""
import copy
from fractions import Fraction

import pytest

from app import visual_contract as VC, visuals_stage as VS
from app.video_providers import motion_text
from test_design110_f456_pure import doc_with, rich
from test_visuals_pure import GAPS, shot as pshot


def check(d):
    return VC.validate_plan(d, GAPS, Fraction(25))


def test_a_person_needs_a_description_and_each_scene_its_colours_and_a_colour_change_its_time_jump():
    d = doc_with(rich(), pshot('VS2', 500, 1000, 'video'))
    scene = d['gaps'][0]['scenes'][0]
    d['elements'][0]['description'] = ''
    with pytest.raises(ValueError, match='E1 is a person: give description'):
        check(d)
    d['elements'][0]['description'] = 'a lean man of about forty, dark skin, short grey hair, stooped at the work; a cotton shirt with the sleeves rolled, a lungi folded to the knee'
    scene['outfit'] = {}
    with pytest.raises(ValueError, match='scene SC1 shows E1: give outfit'):
        check(d)
    scene['outfit'] = {'E1': 'a faded blue shirt, a white lungi', 'NOPE': 'red'}
    with pytest.raises(ValueError, match='outfit names NOPE'):
        check(d)
    del scene['outfit']['NOPE']
    check(d)
    # a second scene with other colours needs the script's time jump
    d = doc_with(rich())
    scene = d['gaps'][0]['scenes'][0]
    second = copy.deepcopy(scene)
    second.update(id='SC2', shots=[rich('VS2', 500, 1000)])
    for b, c in zip(second['shots'][0]['subjects'][0]['beats'], second['shots'][0]['changes']):   # beat ids are unique across the plan
        b['id'] = c['beat_id'] = b['id'] + 'b'
    second['outfit'] = {'E1': 'a green shirt, the same lungi'}
    d['gaps'][0]['scenes'].append(second)
    with pytest.raises(ValueError, match='changes the colours of E1 .* time_jump'):
        check(d)
    second['time_jump'] = 'the next morning'
    check(d)
    second['outfit'] = {'E1': 'a faded blue shirt, a white lungi'}
    second['time_jump'] = ''
    check(d)   # the same colours need no jump


def test_the_server_writes_both_layers_into_the_prompt_the_check_and_the_not_this_line():
    d = doc_with(rich())
    scene, sh = d['gaps'][0]['scenes'][0], d['gaps'][0]['scenes'][0]['shots'][0]
    lines = VS.person_lines(d, scene, sh)
    assert lines == ['Mason: a lean man of about forty, dark skin, short grey hair; a cotton shirt with the sleeves rolled, a lungi to the knee; wearing in this scene: a faded blue shirt, a white lungi.']
    assert lines[0] in VS.composed_block(d, scene, sh, 'start') and lines[0] in VS.composed_block(d, scene, sh, 'end')
    for when in ('start', 'end'):
        must = [l for l in VS.picture_rule_lines(d, scene, sh, when) if l['check'] == 'person kept: Mason']
        assert must and must[0]['weight'] == 'must' and 'faded blue shirt' in must[0]['pass_when'] and 'no other garment colours' in must[0]['pass_when']
    assert VS.not_this_line({}, d, 'E1', sh, scene) == 'Not this (Mason): garment colours other than a faded blue shirt, a white lungi.'
    assert VS.not_this_line({'not_this': {'E1': {'lines': ['a hard hat']}}}, d, 'E1', sh, scene) == 'Not this (Mason): a hard hat; garment colours other than a faded blue shirt, a white lungi.'
    assert VS.not_this_line({}, d, 'BRICK', sh, scene) == ''   # not a person: nothing without a list
    snap = {'motion_prompt': 'm', 'subject_reconciliation': {}, 'duration_seconds': 5, 'end_image': {}, 'continuity_notes': 'the wall', 'person_lines': lines}
    assert 'Continuity: the wall\n' + lines[0] in motion_text(snap)
