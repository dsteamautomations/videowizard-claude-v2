"""Visuals pieces that need no database (design/45): route and length warnings (10.2, 10.7), the timing rule (10.6), the backoff (10.5)."""
from fractions import Fraction

import pytest

from app import visual_contract as VC
from app.visual_workers import backoff_minutes, timing_evidence

STATE = {'position': {'landmark_id': 'L1', 'relation': 'on it', 'amount': 0, 'unit': 'hand'}, 'facing': {'landmark_id': 'L1', 'edge': 'toward camera', 'camera_side': 'front'}, 'pose': 'upright', 'holding': [], 'progress': 'whole'}


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
    assert r['seconds'] == {'video': 4.0, 'still': 24.0, 'graphic_sequence': 12.0, 'drawn': 0.0} and r['graphic_seconds'] == 16.0   # diagram 4 s + sequence 12 s; design/113 adds the drawn route
    assert r['images_estimated'] == 1 + 3 + 1 + 1   # a start image (design/112 S1: no end unless exact), three states, a diagram, a picture


def test_video_images_count_a_run_of_segments_plus_one():
    """design/66 C1: every take has a start and an end image; consecutive video shots in a scene share their boundary picture."""
    result, _ = VC.validate_plan(plan([shot('V1', 0, 250, 'video'), shot('V2', 250, 500, 'video'), shot('V3', 500, 750, 'video'), shot('IM1', 750, 1000, 'image')]), GAPS, Fraction(25))
    r = VC.routes(result)
    assert r['video'] == 3 and r['images_estimated'] == 3 + 1   # three starts (design/112 S1); the still
    result, _ = VC.validate_plan(plan([shot('V1', 0, 250, 'video'), shot('DG1', 250, 500, 'diagram'), shot('V2', 500, 1000, 'video')]), GAPS, Fraction(25))
    assert VC.routes(result)['images_estimated'] == 1 + 1 + 1   # a start each, the diagram between (design/112 S1)


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
    kinds = {(w.get('shot_id'), w.get('kind')) for w in warnings}
    assert ('DG1', 'graphic_short') in kinds and ('DG2', 'graphics_back_to_back') in kinds and ('IM1', 'still_long') in kinds
    assert ('DG2', 'graphic_short') not in kinds and ('VS1', 'graphics_back_to_back') not in kinds
    short = next(w for w in warnings if w.get('kind') == 'graphic_short')
    assert 'DG1 is a graphic of 2.0 s' in short['message'] and 'at least 3 s' in short['message']
    pair = next(w for w in warnings if w.get('kind') == 'graphics_back_to_back')
    assert 'DG1 and DG2 are graphics back to back' in pair['message'] and "second shot's purpose" in pair['message']
    # design/89 B1: a still of four seconds that moves passes; the 20 s one above is warned (refused from the next release)
    _, warnings = VC.validate_plan(plan([shot('IM1', 0, 100, 'image'), shot('VS1', 100, 600, 'video'), shot('VS2', 600, 1000, 'video')]), GAPS, Fraction(25))
    assert not [w for w in warnings if w.get('kind') == 'still_long']
    long = next(w for w in VC.validate_plan(doc, GAPS, Fraction(25))[1] if w.get('kind') == 'still_long' and w['shot_id'] == 'IM1')
    assert 'IM1 is a still of 20.0 s' in long['message'] and 'at most 4 s' in long['message'] and 'refused from the next' in long['message']
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


def test_still_and_graphic_limits_motion_rules_and_the_frozen_share():
    """design/89 B1, B2, B4 with SK's figures: a moving still 4 s, a frozen still 3 s, a graphic state 5 s, a graphic over 4 s is a build; 10 % frozen."""
    kinds = lambda doc, **kw: {(w.get('shot_id'), w['kind']) for w in VC.validate_plan(doc, GAPS, Fraction(25), **kw)[1]}
    filler = [shot('VS1', 400, 700, 'video'), shot('VS2', 700, 1000, 'video')]
    ok = plan([shot('IM1', 0, 100, 'image'), shot('IM2', 100, 200, 'image'), {**shot('IM3', 200, 275, 'image'), 'motion': 'none', 'motion_reason': 'the label is read'},
               {**shot('AN1', 275, 400, 'animation'), 'states': states(5)}] + filler)
    with pytest.raises(ValueError, match='one state is a diagram still'):
        VC.validate_plan(ok, GAPS, Fraction(25))
    ok['gaps'][0]['scenes'][0]['shots'][3]['states'] = states(3, 2)
    ok['gaps'][0]['scenes'][0]['shots'][3]['end_frame'] = 400
    with pytest.raises(ValueError, match='holds at least 3'):
        VC.validate_plan(ok, GAPS, Fraction(25))
    ok['gaps'][0]['scenes'][0]['shots'][3]['states'] = states(3, 3)
    ok['gaps'][0]['scenes'][0]['shots'][3]['start_frame'] = 250
    ok['gaps'][0]['scenes'][0]['shots'][2]['end_frame'] = 250
    assert not {k for k in kinds(ok) if k[1] in ('still_long', 'state_long', 'graphic_unbuilt', 'frozen_share')}
    long = plan([shot('IM1', 0, 125, 'image'), {**shot('IM2', 125, 225, 'image'), 'motion': 'none', 'motion_reason': 'r'}, shot('DG1', 225, 350, 'diagram'),
                 {**shot('AN1', 350, 500, 'animation'), 'states': states(3, 3)}] + [shot('VS1', 500, 750, 'video'), shot('VS2', 750, 1000, 'video')])
    k = kinds(long)
    assert ('IM1', 'still_long') in k and ('IM2', 'still_long') in k and ('DG1', 'graphic_unbuilt') in k   # 5 s moving, 4 s frozen, a 5 s single diagram
    built = plan([{**shot('AN1', 0, 175, 'animation'), 'states': states(4, 3)}, {**shot('AN2', 175, 325, 'animation'), 'states': states(3, 3)},
                  {**shot('AN3', 325, 500, 'animation'), 'states': states(3.5, 3.5)}] + [shot('VS1', 500, 750, 'video'), shot('VS2', 750, 1000, 'video')])
    assert not {x for x in kinds(built) if x[1] == 'state_long'}
    st = plan([{**shot('AN1', 0, 200, 'animation'), 'states': states(5.5, 2.5)}] + [shot('VS1', 200, 600, 'video'), shot('VS2', 600, 1000, 'video')])
    with pytest.raises(ValueError, match='holds at least 3'):
        VC.validate_plan(st, GAPS, Fraction(25))
    st['gaps'][0]['scenes'][0]['shots'][0]['states'] = states(5.5, 3)
    st['gaps'][0]['scenes'][0]['shots'][0]['end_frame'] = 212
    st['gaps'][0]['scenes'][0]['shots'][1]['start_frame'] = 212
    assert ('AN1', 'state_long') in kinds(st)
    # B2: graphics move closer only; a frozen still says why
    with pytest.raises(ValueError, match='moves closer only'):
        VC.validate_plan(plan([{**shot('DG1', 0, 100, 'diagram'), 'motion': 'pan_left'}, shot('VS1', 100, 500, 'video'), shot('VS2', 500, 1000, 'video')]), GAPS, Fraction(25))
    with pytest.raises(ValueError, match='needs a reason'):
        VC.validate_plan(plan([{**shot('IM1', 0, 75, 'image'), 'motion': 'none'}, shot('VS1', 75, 500, 'video'), shot('VS2', 500, 1000, 'video')]), GAPS, Fraction(25))
    # B4: frozen seconds over 10 % of the film warn; with movement they do not count
    frozen = plan([{**shot('IM1', 0, 75, 'image'), 'motion': 'none', 'motion_reason': 'r'}, shot('VS1', 75, 500, 'video'), shot('VS2', 500, 1000, 'video')])
    assert (None, 'frozen_share') in kinds(frozen, film_frames=500) and (None, 'frozen_share') not in kinds(frozen, film_frames=1000)   # 3 s of 20 s is 15 %; of 40 s, 7.5 %
    assert (None, 'frozen_share') not in kinds(plan([shot('IM1', 0, 75, 'image'), shot('VS1', 75, 500, 'video'), shot('VS2', 500, 1000, 'video')]), film_frames=500)
    out, _ = VC.validate_plan(plan([shot('IM1', 0, 75, 'image'), shot('VS1', 75, 500, 'video'), shot('VS2', 500, 1000, 'video')]), GAPS, Fraction(25))
    assert 'motion' not in out['gaps'][0]['scenes'][0]['shots'][0]   # absent stays absent: an accepted plan's digest does not change


def test_a_return_is_reimagined_with_what_differs():
    """design/89 H7."""
    doc = plan([shot('IM1', 0, 100, 'image'), shot('VS1', 100, 500, 'video'), {**shot('VS2', 500, 1000, 'video'), 'return_of': 'IM1', 'differs_by': 'the same wall from ground level, looking up'}])
    VC.validate_plan(doc, GAPS, Fraction(25))
    doc['gaps'][0]['scenes'][0]['shots'][2]['differs_by'] = ''
    with pytest.raises(ValueError, match='say what differs'):
        VC.validate_plan(doc, GAPS, Fraction(25))
    doc['gaps'][0]['scenes'][0]['shots'][2].update(return_of='VS9', differs_by='x')
    with pytest.raises(ValueError, match='names an earlier shot'):
        VC.validate_plan(doc, GAPS, Fraction(25))


def test_cuts_fall_in_pauses_and_pictures_start_on_their_words():
    """design/89 A3: a cut 1 s inside a sentence warns, a cut in a pause does not; a picture 1.5 s after its words warns."""
    w = lambda text, a, b: {'text': text, 'start_frame': a, 'end_frame': b}
    timing = {'words': [w('Bricks', 0, 10), w('laid', 12, 20), w('on', 22, 25), w('edge.', 27, 40), w('The', 55, 60), w('cavity', 62, 75), w('keeps', 78, 85), w('heat', 87, 95), w('out.', 97, 110)]}
    gaps = {'G1': {'start_frame': 0, 'end_frame': 1000, 'timing': timing}}
    good = plan([{**shot('IM1', 0, 47, 'image'), 'narration': 'Bricks laid on edge.'}, {**shot('IM2', 47, 100, 'image'), 'narration': 'The cavity keeps heat out.'},
                 shot('VS1', 100, 500, 'video'), shot('VS2', 500, 1000, 'video')])
    found = {(x.get('shot_id'), x['kind']) for x in VC.validate_plan(good, gaps, Fraction(25))[1]}   # a scene's warning names no shot
    assert ('IM2', 'cut_off_pause') not in found and ('IM2', 'words_off_picture') not in found   # 47 sits in the pause 40–55
    bad = plan([{**shot('IM1', 0, 70, 'image'), 'narration': 'Bricks laid on edge.'}, {**shot('IM2', 70, 100, 'image'), 'narration': 'The cavity keeps heat out.'},
                shot('VS1', 100, 500, 'video'), shot('VS2', 500, 1000, 'video')])
    got = {x['kind']: x['message'] for x in VC.validate_plan(bad, gaps, Fraction(25))[1] if x.get('shot_id') == 'IM2'}
    assert "inside the word 'cavity'" in got['cut_off_pause'] and 'spoken at 2.2 s but the shot runs 2.8' in got['words_off_picture']   # the picture arrives 0.6 s after its words
    assert VC.timing_warnings('G1', [], timing, 25) == [] and VC.timing_warnings('G1', [], None, 25) == []


def test_a_shots_words_are_found_after_the_previous_shots_words():
    """Finding 4: two shots that open with the same words."""
    w = lambda text, a, b: {'text': text, 'start_frame': a, 'end_frame': b}
    timing = {'words': [w('The', 0, 5), w('wall', 6, 12), w('is', 13, 16), w('red.', 17, 30), w('The', 45, 50), w('wall', 51, 57), w('is', 58, 61), w('tall.', 62, 80)]}
    gaps = {'G1': {'start_frame': 0, 'end_frame': 1000, 'timing': timing}}
    doc = plan([{**shot('IM1', 0, 40, 'image'), 'narration': 'The wall is red.'}, {**shot('IM2', 40, 100, 'image'), 'narration': 'The wall is tall.'},
                shot('VS1', 100, 500, 'video'), shot('VS2', 500, 1000, 'video')])
    assert not [x for x in VC.validate_plan(doc, gaps, Fraction(25))[1] if x['kind'] == 'words_off_picture']


def test_a_return_names_a_shot_the_film_shows():
    """Finding 5: a shot of the alternative that is not recommended is never on screen."""
    base = plan([shot('VS1', 0, 500, 'video'), shot('VS2', 500, 1000, 'video')])
    gap = base['gaps'][0]
    scene = lambda sid, shots: {**gap['scenes'][0], 'id': sid, 'shots': shots}
    two = {**gap, 'scenes': [], 'recommended_choice': 'A', 'decision_reason': 'r',
           'choices': [{'id': 'A', 'title': 'a', 'why': 'w', 'formats': ['ai_video'], 'description': 'd', 'tradeoff': 't', 'source_strategy': 's', 'scenes': [scene('SA', [shot('A1', 0, 500, 'video'), shot('A2', 500, 1000, 'video')])]},
                       {'id': 'B', 'title': 'b', 'why': 'w', 'formats': ['ai_video'], 'description': 'd', 'tradeoff': 't', 'source_strategy': 's', 'scenes': [scene('SB', [shot('B1', 0, 500, 'video'), shot('B2', 500, 1000, 'video')])]}]}
    gaps2 = {'G1': {'start_frame': 0, 'end_frame': 1000}, 'G2': {'start_frame': 1000, 'end_frame': 2000}}
    later = {'gap_id': 'G2', 'intent': 'x', 'treatment_fit': 'fits', 'scenes': [scene('SC2', [{**shot('V3', 1000, 1500, 'video'), 'return_of': 'B1', 'differs_by': 'from above'}, shot('V4', 1500, 2000, 'video')])]}
    doc = {**base, 'gaps': [two, later]}
    with pytest.raises(ValueError, match='names an earlier shot'):
        VC.validate_plan(doc, gaps2, Fraction(25))
    later['scenes'][0]['shots'][0]['return_of'] = 'A1'
    VC.validate_plan(doc, gaps2, Fraction(25))


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
