"""design/110 F1 and F2. F1: every beat of a video shot carries `done` (the action in the past tense); the end prompt's first sentence per acting
subject is cause, path, result, composed by the server. F2: a position is landmark + measured amount in a visible unit; the plan check refuses a
video shot's position without them or with a vague relation alone; the prompt check refuses "centre", "middle", "nearby", "closer", "further"
standing alone; the end sentence says how far the subject moved from Image 1."""
import copy
import json
from fractions import Fraction

import pytest

from app import library as L, visual_contract as VC, visuals_stage as VS
from test_design91_b1_pure import st, subject, video
from test_visuals_pure import GAPS, plan, shot as pshot
from test_visuals_stage_pure import RUN, plan_doc, shot


def doc_with(*shots):
    return plan(list(shots))


def check(d):
    return VC.validate_plan(d, GAPS, Fraction(25))


# ---------- the schema and the plan check ----------

def test_a_video_shots_positions_need_an_amount_and_a_unit_and_its_beats_need_done():
    good = video('VS1', 0, 500, [(0, 250, 3), (250, 500, 3)])
    check(doc_with(good, pshot('VS2', 500, 1000, 'video')))
    d = doc_with(copy.deepcopy(good), pshot('VS2', 500, 1000, 'video'))
    for st_ in (d['gaps'][0]['scenes'][0]['shots'][0]['subjects'][0]['start'], d['gaps'][0]['scenes'][0]['shots'][0]['subjects'][0]['beats'][0]['start']):
        st_['position'].pop('amount')
    with pytest.raises(ValueError, match='needs a measured amount and a visible unit'):
        check(d)
    d = doc_with(copy.deepcopy(good), pshot('VS2', 500, 1000, 'video'))
    d['gaps'][0]['scenes'][0]['shots'][0]['subjects'][0]['beats'][1]['done'] = ''
    with pytest.raises(ValueError, match='beat B2 needs done'):
        check(d)
    d = doc_with(copy.deepcopy(good), pshot('VS2', 500, 1000, 'video'))
    for s_ in ('start',):
        d['gaps'][0]['scenes'][0]['shots'][0]['subjects'][0][s_]['position']['relation'] = 'at the centre'
        d['gaps'][0]['scenes'][0]['shots'][0]['subjects'][0]['beats'][0]['start']['position']['relation'] = 'at the centre'
    with pytest.raises(ValueError, match='"at the centre" alone says nothing'):
        check(d)
    still = {**pshot('IM1', 0, 500, 'image'), 'subjects': [{**subject((0, 250, 3)), 'start': {**st('0 laid'), 'position': {'landmark_id': 'L1', 'relation': 'at'}}}]}
    still['subjects'][0]['beats'][0]['start'] = still['subjects'][0]['start']
    still['subjects'][0]['beats'][0]['done'] = ''
    check(doc_with(still, pshot('VS2', 500, 1000, 'video')))   # a still shot's subject keeps the old freedom
    out, _ = check(doc_with(good, pshot('VS2', 500, 1000, 'video')))
    sub = out['gaps'][0]['scenes'][0]['shots'][0]['subjects'][0]
    assert sub['start']['position']['amount'] == 1 and sub['start']['position']['unit'] == 'pace' and sub['beats'][0]['done'] == 'laid one brick'


# ---------- the end sentence ----------

def test_the_end_sentence_says_the_cause_the_path_the_result_and_how_far_it_moved():
    sh = video('VS1', 900, 1150, [(900, 1000, 3), (1000, 1150, 3)])
    sh['subjects'][0]['end']['position'] = {'landmark_id': 'L1', 'relation': 'to the right of', 'amount': 3, 'unit': 'pace'}
    sh['subjects'][0]['beats'][-1]['end']['position'] = sh['subjects'][0]['end']['position']
    scene = {'landmarks': [{'id': 'L1', 'description': 'the wall'}]}
    lines = VS.end_targets(scene, sh)
    assert lines == ['Because E1 has laid one brick, along the course, from 1 pace at the wall to 3 pace to the right of the wall, one more brick on the course is now in frame. '
                     'E1 ends 3 pace to the right of the wall, 2 pace from where it stood in Image 1, facing the wall, bending, holding nothing; 2 laid.']
    held = {**sh, 'subjects': [{**sh['subjects'][0], 'behaviour': 'holds', 'beats': [], 'end': sh['subjects'][0]['start']}]}
    assert VS.end_targets(scene, held) == ['E1 ends 1 pace at the wall, facing the wall, bending, holding nothing; 0 laid.']   # no action: no cause, no distance
    old = {**sh, 'subjects': [{**sh['subjects'][0], 'start': st('0 laid'), 'end': {**st('2 laid'), 'position': {'landmark_id': 'L1', 'relation': 'at the far end of'}}}]}
    assert VS.end_targets(scene, old)[0].endswith('E1 ends at the far end of the wall, facing the wall, bending, holding nothing; 2 laid.')   # an old plan without amounts still composes


# ---------- the prompt check ----------

def test_the_prompt_check_refuses_a_vague_place_standing_alone():
    for bad in ('The mason stands at the centre.', 'The truck is driven to the middle of the yard.', 'A helper nearby.', 'He steps closer.', 'The cows move further away.'):
        with pytest.raises(ValueError, match='no landmark and measured distance'):
            L.check_prompt(bad)
    for ok in ('The mason stands two paces to the right of the palm trunk.', 'He steps one brick closer to the stack.', 'The truck, 3 body-lengths further along the fence.',
               'The wall is centred in the frame.', 'A middle-aged man at the doorway.'):
        L.check_prompt(ok)
