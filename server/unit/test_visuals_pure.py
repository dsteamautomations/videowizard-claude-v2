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


def states(*holds):
    return [{'what_appears': f'state {i + 1}', 'hold_s': h} for i, h in enumerate(holds)]


def test_routes_count_video_stills_and_graphic_sequences_with_no_file_warning():
    """design/65 B1: every route is made in the pipeline; an animation shot is a graphic sequence of states."""
    doc = plan([shot('VS1', 0, 100, 'video'), {**shot('AN1', 100, 400, 'animation'), 'states': states(4, 4, 4)}, shot('DG1', 400, 500, 'diagram'), shot('IM1', 500, 1000, 'image')])
    result, warnings = VC.validate_plan(doc, GAPS, Fraction(25))
    assert not [w for w in warnings if w.get('kind') == 'route']
    r = VC.routes(result)
    assert r['video'] == 1 and r['still'] == 2 and r['graphic_sequence'] == 1
    assert r['seconds'] == {'video': 4.0, 'still': 24.0, 'graphic_sequence': 12.0} and r['graphic_seconds'] == 16.0   # diagram 4 s + sequence 12 s
    assert r['images_estimated'] == 2 + 3 + 1 + 1   # a start and an end image, three states, a diagram, a picture


def test_video_images_count_a_run_of_segments_plus_one():
    """design/66 C1: every take has a start and an end image; consecutive video shots in a scene share their boundary picture."""
    result, _ = VC.validate_plan(plan([shot('V1', 0, 250, 'video'), shot('V2', 250, 500, 'video'), shot('V3', 500, 750, 'video'), shot('IM1', 750, 1000, 'image')]), GAPS, Fraction(25))
    r = VC.routes(result)
    assert r['video'] == 3 and r['images_estimated'] == 4 + 1   # three segments, four images; the still
    result, _ = VC.validate_plan(plan([shot('V1', 0, 250, 'video'), shot('DG1', 250, 500, 'diagram'), shot('V2', 500, 1000, 'video')]), GAPS, Fraction(25))
    assert VC.routes(result)['images_estimated'] == 2 + 1 + 2   # separated by a still: two images each


def test_an_animation_shot_needs_two_to_four_states_that_fill_it():
    with pytest.raises(ValueError, match='one state is a diagram still'):
        VC.validate_plan(plan([{**shot('AN1', 0, 1000, 'animation'), 'states': states(40)}]), GAPS, Fraction(25))
    with pytest.raises(ValueError, match='two to four states'):
        VC.validate_plan(plan([shot('AN1', 0, 1000, 'animation')]), GAPS, Fraction(25))
    with pytest.raises(ValueError, match='two to four states'):
        VC.validate_plan(plan([{**shot('AN1', 0, 1000, 'animation'), 'states': states(8, 8, 8, 8, 8)}]), GAPS, Fraction(25))
    with pytest.raises(ValueError, match='at least 3 s'):
        VC.validate_plan(plan([{**shot('AN1', 0, 1000, 'animation'), 'states': states(2, 38)}]), GAPS, Fraction(25))
    with pytest.raises(ValueError, match='holds add up to 30.0 s; the shot is 40.0 s'):
        VC.validate_plan(plan([{**shot('AN1', 0, 1000, 'animation'), 'states': states(10, 10, 10)}]), GAPS, Fraction(25))
    with pytest.raises(ValueError, match='states belong to an animation shot'):
        VC.validate_plan(plan([{**shot('DG1', 0, 1000, 'diagram'), 'states': states(20, 20)}]), GAPS, Fraction(25))
    result, _ = VC.validate_plan(plan([{**shot('AN1', 0, 1000, 'animation'), 'states': states(20, 20.1)}]), GAPS, Fraction(25))   # within 0.2 s
    assert result['gaps'][0]['scenes'][0]['shots'][0]['states'][1]['hold_s'] == 20.1
    result, _ = VC.validate_plan(plan([shot('IM1', 0, 1000, 'image')]), GAPS, Fraction(25))
    assert 'states' not in result['gaps'][0]['scenes'][0]['shots'][0]   # absent in the document, absent in the digest material


def test_graphic_warnings_short_static_back_to_back_and_all_graphics():
    """design/64 B4 as kept by design/65: warnings, never refusals."""
    doc = plan([shot('DG1', 0, 50, 'diagram'), shot('DG2', 50, 250, 'diagram'), shot('VS1', 250, 500, 'video'), shot('IM1', 500, 1000, 'image')])
    _, warnings = VC.validate_plan(doc, GAPS, Fraction(25))
    kinds = {(w['shot_id'], w.get('kind')) for w in warnings}
    assert ('DG1', 'graphic_short') in kinds and ('DG2', 'graphics_back_to_back') in kinds and ('IM1', 'static_long') in kinds
    assert ('DG2', 'graphic_short') not in kinds and ('VS1', 'graphics_back_to_back') not in kinds
    short = next(w for w in warnings if w.get('kind') == 'graphic_short')
    assert 'DG1 is a graphic of 2.0 s' in short['message'] and 'at least 3 s' in short['message']
    pair = next(w for w in warnings if w.get('kind') == 'graphics_back_to_back')
    assert 'DG1 and DG2 are graphics back to back' in pair['message'] and "second shot's purpose" in pair['message']
    # a still of five seconds is not asked to earn its time; the 20 s one above is
    _, warnings = VC.validate_plan(plan([shot('IM1', 0, 125, 'image'), shot('VS1', 125, 625, 'video'), shot('VS2', 625, 1000, 'video')]), GAPS, Fraction(25))
    assert not [w for w in warnings if w.get('kind') == 'static_long']
    long = next(w for w in VC.validate_plan(doc, GAPS, Fraction(25))[1] if w.get('kind') == 'static_long' and w['shot_id'] == 'IM1')
    assert 'IM1 is a still of 20.0 s' in long['message'] and 'earn the time' in long['message']
    # a gap of more than one shot that is all graphics
    doc = plan([shot('DG1', 0, 500, 'diagram'), {**shot('AN1', 500, 1000, 'animation'), 'states': states(10, 10)}])
    _, warnings = VC.validate_plan(doc, GAPS, Fraction(25))
    assert any(w.get('kind') == 'all_graphics' and w['gap_id'] == 'G1' for w in warnings)
    assert any(w.get('kind') == 'graphics_back_to_back' and w['shot_id'] == 'AN1' for w in warnings)


def test_graphics_back_to_back_across_two_gaps_with_no_footage_between():
    doc = plan([shot('DG1', 0, 1000, 'diagram')])
    doc['gaps'].append({'gap_id': 'G2', 'intent': 'next', 'treatment_fit': 'fits',
                        'scenes': [{'id': 'SC2', 'purpose': 'p', 'location_time': 'workshop, day', 'layout': 'table centre', 'landmarks': [{'id': 'L2', 'description': 'the table'}],
                                    'boundary_continuity': 'none', 'shots': [shot('DG2', 1000, 1200, 'diagram')]}]})
    gaps = {'G1': {'start_frame': 0, 'end_frame': 1000}, 'G2': {'start_frame': 1000, 'end_frame': 1200}}   # G2 starts where G1 ends: no footage between
    _, warnings = VC.validate_plan(doc, gaps, Fraction(25))
    assert any(w.get('kind') == 'graphics_back_to_back' and w['shot_id'] == 'DG2' and 'DG1 and DG2' in w['message'] for w in warnings)
    doc['gaps'][1]['scenes'][0]['shots'][0].update(start_frame=1100, end_frame=1300)
    gaps = {'G1': {'start_frame': 0, 'end_frame': 1000}, 'G2': {'start_frame': 1100, 'end_frame': 1300}}   # four seconds of footage between them
    _, warnings = VC.validate_plan(doc, gaps, Fraction(25))
    assert not any(w.get('kind') == 'graphics_back_to_back' for w in warnings)


def test_a_run_of_ai_video_over_twelve_seconds_in_one_gap_is_warned():
    """design/85 G2, G3: the run, not the shot, is what reads as synthetic; a frame, a still or a graphic breaks it."""
    _, warnings = VC.validate_plan(plan([shot('V1', 0, 250, 'video'), shot('V2', 250, 500, 'video'), shot('V3', 500, 750, 'video'), shot('IM1', 750, 1000, 'image')]), GAPS, Fraction(25))
    run_ = [w for w in warnings if w.get('kind') == 'ai_run']
    assert len(run_) == 1 and run_[0]['gap_id'] == 'G1' and 'shots V1, V2, V3 are 30.0 s of AI video back to back' in run_[0]['message'] and 'three to five seconds' in run_[0]['message']
    _, warnings = VC.validate_plan(plan([shot('V1', 0, 250, 'video'), shot('IM1', 250, 500, 'image'), shot('V2', 500, 750, 'video'), shot('DG1', 750, 1000, 'diagram')]), GAPS, Fraction(25))
    assert not [w for w in warnings if w.get('kind') == 'ai_run']   # 10 s runs, broken by a still and a graphic
    _, warnings = VC.validate_plan(plan([shot('IM1', 0, 250, 'image'), shot('V1', 250, 1000, 'video')]), GAPS, Fraction(25))
    assert [w['shot_id'] for w in warnings if w.get('kind') == 'ai_run'] == ['V1']   # one 30 s shot is a run too


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
    result, _ = VC.validate_plan(plan([{**shot('AN1', 0, 1000, 'animation'), 'states': states(10, 10, 10, 10)}]), GAPS, Fraction(25))   # 40 s of stills is fine
    assert len(result['gaps'][0]['scenes'][0]['shots'][0]['states']) == 4


# ---------- 10.6 timing: at least as long matches ----------

def test_timing_matches_when_the_take_is_at_least_as_long():
    assert timing_evidence(4.0, '17/5') == {'timing_matches_placement': True, 'shortfall_seconds': 0.0}          # 4.0 s for 3.4 s
    assert timing_evidence(3.4, '17/5') == {'timing_matches_placement': True, 'shortfall_seconds': 0.0}          # exact
    assert timing_evidence(3.0, '17/5') == {'timing_matches_placement': False, 'shortfall_seconds': 0.4}
    assert timing_evidence(3.3995, '17/5')['timing_matches_placement'] is True                                   # within a millisecond


# ---------- 10.5 backoff ----------

def test_backoff_is_thirty_seconds_then_a_minute():
    assert [backoff_minutes(n) for n in (1, 2, 3, 10)] == [0.5, 1, 1, 1]


def test_default_aspect_comes_from_the_brief_unless_the_body_says():
    from app.visuals_stage import default_aspect
    assert default_aspect({'production': {'format': {'frame': '9:16'}}}, {}) == '9:16'
    assert default_aspect({'production': {'format': {'frame': '9:16'}}}, {'aspect_ratio': '1:1'}) == '1:1'
    assert default_aspect({}, {}) == '16:9' and default_aspect(None, {}) == '16:9'
