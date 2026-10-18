"""Visuals pieces that need no database (design/45): route and length warnings (10.2, 10.7), the timing rule (10.6), the backoff (10.5)."""
from fractions import Fraction

import pytest

from app import visual_contract as VC
from app.visual_workers import backoff_minutes, timing_evidence

STATE = {'position': {'landmark_id': 'L1', 'relation': 'on it'}, 'facing': 'camera', 'pose': 'upright', 'holding': [], 'progress': 'whole'}


def shot(sid, a, b, visual_type):
    return {'id': sid, 'start_frame': a, 'end_frame': b, 'visual_type': visual_type, 'narration': '', 'purpose': 'show it', 'relation': 'illustration', 'framing': 'medium',
            'camera': 'static', 'focus': 'the block', 'element_ids': ['E1'], 'information_progression': 'A still of the block.'}


def plan(shots):
    return {'foundation': {'treatment': 'documentary realism', 'appearance': 'warm daylight'},
            'elements': [{'id': 'E1', 'name': 'Earth block', 'kind': 'object', 'identity': 'representative', 'requirements': 'pressed earth block'}],
            'gaps': [{'gap_id': 'G1', 'intent': 'kiln', 'treatment_fit': 'fits',
                      'scenes': [{'id': 'SC1', 'purpose': 'p', 'location_time': 'workshop, day', 'layout': 'table centre', 'landmarks': [{'id': 'L1', 'description': 'the table'}],
                                  'boundary_continuity': 'none', 'shots': shots}]}]}


GAPS = {'G1': {'start_frame': 0, 'end_frame': 1000}}


def test_routes_are_counted_and_file_shots_are_warned():
    doc = plan([shot('VS1', 0, 100, 'video'), shot('AN1', 100, 400, 'animation'), shot('DG1', 400, 500, 'diagram'), shot('IM1', 500, 1000, 'image')])
    result, warnings = VC.validate_plan(doc, GAPS, Fraction(25))
    route = [w for w in warnings if w.get('kind') == 'route']
    assert [w['shot_id'] for w in route] == ['AN1', 'DG1', 'IM1']
    assert 'the operator supplies this file' in route[0]['message'] and 'vw visuals still' in route[0]['message'] and 'animation, 12.0 s' in route[0]['message']
    assert VC.routes(result) == {'video': 1, 'still_or_file': 3, 'seconds': {'video': 4.0, 'still_or_file': 36.0}}


def test_a_video_shot_longer_than_the_default_generator_is_warned():
    doc = plan([shot('VS1', 0, 590, 'video'), shot('VS2', 590, 1000, 'video')])   # 23.6 s and 16.4 s
    result, warnings = VC.validate_plan(doc, GAPS, Fraction(25))
    length = [w for w in warnings if w.get('kind') == 'length']
    assert [w['shot_id'] for w in length] == ['VS1', 'VS2'] and '23.6 s' in length[0]['message'] and 'at most 10 s' in length[0]['message'] and 'Seedance' in length[0]['message']
    _, warnings = VC.validate_plan(plan([shot('VS1', 0, 250, 'video'), shot('IM1', 250, 1000, 'image')]), GAPS, Fraction(25))
    assert not [w for w in warnings if w.get('kind') == 'length']


def test_a_generated_shot_over_thirty_seconds_is_still_refused():
    with pytest.raises(ValueError, match='at most 30 s'):
        VC.validate_plan(plan([shot('VS1', 0, 1000, 'video')]), GAPS, Fraction(25))   # 40 s


# ---------- 10.6 timing: at least as long matches ----------

def test_timing_matches_when_the_take_is_at_least_as_long():
    assert timing_evidence(4.0, '17/5') == {'timing_matches_placement': True, 'shortfall_seconds': 0.0}          # 4.0 s for 3.4 s
    assert timing_evidence(3.4, '17/5') == {'timing_matches_placement': True, 'shortfall_seconds': 0.0}          # exact
    assert timing_evidence(3.0, '17/5') == {'timing_matches_placement': False, 'shortfall_seconds': 0.4}
    assert timing_evidence(3.3995, '17/5')['timing_matches_placement'] is True                                   # within a millisecond


# ---------- 10.5 backoff ----------

def test_backoff_is_thirty_seconds_then_a_minute():
    assert [backoff_minutes(n) for n in (1, 2, 3, 10)] == [0.5, 1, 1, 1]
