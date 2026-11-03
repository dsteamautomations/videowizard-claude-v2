"""design/148 Set A on the server: A1 the plan check lists every error (per element, fact, gap and scene; the cross-plan checks wait),
A4 a shape error in the tool's voice, A5 a return_of that differs only in case names the nearest id."""
from fractions import Fraction

import pytest

from app import visual_contract as VC
from test_visuals_pure import GAPS, plan, shot


def pic(sid, a, b):   # a still: no length limit to trip over (the video limit is Omni's 10 s)
    return shot(sid, a, b, 'image')


def two_gaps(first, second):
    base = plan(first)
    g1 = base['gaps'][0]
    g2 = {'gap_id': 'G2', 'intent': 'x', 'treatment_fit': 'fits', 'scenes': [{**g1['scenes'][0], 'id': 'SC2', 'shots': second}]}
    return {**base, 'gaps': [g1, g2]}, {'G1': {'start_frame': 0, 'end_frame': 1000}, 'G2': {'start_frame': 1000, 'end_frame': 2000}}


# ---------- A1 ----------

def test_a_valid_plan_is_unchanged():
    result, warnings = VC.validate_plan(plan([shot('V1', 0, 250, 'video'), pic('I2', 250, 1000)]), GAPS, Fraction(25))
    assert [s['id'] for s in result['gaps'][0]['scenes'][0]['shots']] == ['V1', 'I2']


def test_errors_in_two_elements_and_two_gaps_come_back_together():
    doc, gaps = two_gaps([{**pic('V1', 0, 1000), 'states': [{'what_appears': 's', 'hold_s': 4}]}],      # states on a still
                         [{**pic('V3', 1000, 1500), 'states': [{'what_appears': 's', 'hold_s': 4}]}, pic('V4', 1500, 2000)])
    doc['elements'] += [{'id': 'M1', 'name': 'Brick', 'kind': 'material', 'identity': 'representative', 'requirements': 'r'},            # a material without its spec
                        {'id': 'P1', 'name': 'Mason', 'kind': 'person', 'identity': 'representative', 'requirements': 'r', 'speaker': True, 'description': ''}]
    doc['elements'][2]['kind'] = 'object'   # a speaker that is not a person
    with pytest.raises(ValueError) as exc:
        VC.validate_plan(doc, gaps, Fraction(25))
    text = str(exc.value)
    assert text.startswith('4 things to fix:')
    assert 'element M1 is a repeating material' in text and 'element P1: speaker marks a real person' in text
    assert 'states belong to an animation shot (shot V1 is a image)' in text and 'states belong to an animation shot (shot V3 is a image)' in text
    assert exc.value.errors == [line.split('. ', 1)[1] for line in text.split('\n')[1:]]   # the list, one message each, word for word


def test_one_scenes_failure_does_not_stop_the_next_gap_and_skips_the_gap_length_check():
    doc, gaps = two_gaps([{**pic('V1', 0, 400), 'states': [{'what_appears': 's', 'hold_s': 4}]}, pic('V2', 400, 1000)],
                         [pic('V3', 1000, 1500), {**shot('V4', 1500, 2000, 'diagram'), 'states': [{'what_appears': 's', 'hold_s': 4}]}])
    with pytest.raises(ValueError) as exc:
        VC.validate_plan(doc, gaps, Fraction(25))
    assert exc.value.errors == ['states belong to an animation shot (shot V1 is a image).', 'states belong to an animation shot (shot V4 is a diagram).']   # not the cover-the-gap message


def test_the_first_message_still_matches_alone():
    """The 147 older assertions match one message; the joined text still carries it word for word."""
    with pytest.raises(ValueError, match='states belong to an animation shot'):
        VC.validate_plan(plan([{**pic('V1', 0, 1000), 'states': [{'what_appears': 's', 'hold_s': 4}]}]), GAPS, Fraction(25))


# ---------- A4 ----------

def test_a_shape_error_names_the_object_and_its_missing_fields():
    doc = plan([pic('V1', 0, 1000)])
    doc['elements'].append({'id': 'lorry_driver', 'name': 'Lorry driver'})
    with pytest.raises(ValueError) as exc:
        VC.validate_plan(doc, GAPS, Fraction(25))
    text = str(exc.value)
    assert text == 'elements[1] lorry_driver: missing kind, identity, requirements.'
    assert 'pydantic' not in text and 'input_value' not in text


# ---------- A5 ----------

def test_a_return_of_in_the_wrong_case_names_the_nearest_id():
    doc, gaps = two_gaps([pic('VS1', 0, 500), pic('VS2', 500, 1000)],
                         [{**pic('V3', 1000, 1500), 'return_of': 'vs1', 'differs_by': 'from above'}, pic('V4', 1500, 2000)])
    with pytest.raises(ValueError, match=r'return_of names an earlier shot of this plan \(vs1 is not one\)\. Did you mean VS1\?'):
        VC.validate_plan(doc, gaps, Fraction(25))
    doc['gaps'][1]['scenes'][0]['shots'][0]['return_of'] = 'VS1'
    VC.validate_plan(doc, gaps, Fraction(25))
