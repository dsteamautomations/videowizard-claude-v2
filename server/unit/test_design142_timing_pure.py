"""design/142 R4 (SK, 2 Nov 2026: design/140 Q2, Q3; design/141 Q2): every real shot names its two markers or says why not; the whole action, then
starting before the word, then the action on its word; the analysis reports camera moves apart from the action, and a shot may end before one."""
from fractions import Fraction

from app.clip_log import prompt as PR, schema as SC
from app.stage2 import package as P, validator as V

ROWS = {'c1:S1': {'clip_id': 'c1'}}


def cut(ev):
    return {'options': [{'option_number': 1, 'beat_id': 'BEAT_01', 'events': [ev]}]}


def test_a_real_shot_names_both_markers_or_says_why():
    bare = {'sub_clip_id': 'c1:S1'}
    r = V.cut_reasons(cut(bare), ROWS)
    assert any('illustrates_word_id' in x for x in r) and any('action_word_id' in x for x in r)
    assert V.cut_reasons(cut({**bare, 'illustrates_word_id': 'W1', 'action_word_id': 'W2'}), ROWS) == []
    assert V.cut_reasons(cut({**bare, 'illustrates_word_id': 'W1', 'marker_reasons': {'action': 'no action word in its sentence'}}), ROWS) == []


def test_an_answered_b2_and_a_shot_ending_before_a_move_are_information():
    flags = ['OPTION #1 shot 1 (c:1): B2 answered: the word "laid" is not within 6 frames of the action accent (no action word in its sentence)',
             'OPTION #1 shot 2 (c:2): G2 move: ends at 300, before the reported whip at 300; the action is complete',
             'OPTION #1 shot 3 (c:3): B2 the word "laid" is not within 6 frames of the shot\'s action accent']
    out = V.answer_flags(flags)
    assert out['act_on'] == [flags[2]] and 'B2 answered 1' in out['for_information'] and 'G2 move 1' in out['for_information']


def row(moves=()):
    return {'eligibility': 'ELIGIBLE', 'client_safe': True, 'risk_flags': [], 'in_frame': 0, 'out_frame': 500, 'source_fps': '50', 'min_hold_s': 1.0, 'action_peak': {'in_frame': 100, 'out_frame': 300}, 'camera_moves': list(moves)}


def ev(a, z):
    return {'source_in_frame': a, 'source_out_frame': z, 'match': 'direct', 'evidence': 'x', 'crop': 'full'}


def test_a_shot_may_end_before_a_reported_camera_move_inside_the_peak():
    refusals, flags = [], []
    V._piece('T', ev(90, 260), row([{'start_frame': 250, 'end_frame': 320, 'kind': 'whip'}]), {}, refusals, flags)
    assert refusals == [] and len(flags) == 1 and 'G2 move' in flags[0] and 'whip' in flags[0]
    refusals = []
    V._piece('T', ev(90, 240), row([{'start_frame': 250, 'end_frame': 320, 'kind': 'whip'}]), {}, refusals, [])
    assert refusals and 'G2' in refusals[0]   # ends before the move starts: the action is not complete
    refusals = []
    V._piece('T', ev(90, 260), row(), {}, refusals, [])
    assert refusals and 'G2' in refusals[0]   # no reported move: G2 as today


def test_the_analysis_reports_camera_moves_and_the_peak_stops_before_them():
    sub = SC.SUB_CLIP
    assert 'camera_moves' in sub['properties'] and 'camera_moves' not in sub['required']   # an older log without it still reads
    assert 'never inside a camera move' in PR.TEMPLATE if hasattr(PR, 'TEMPLATE') else 'never inside a camera move' in open(PR.__file__, encoding='utf-8').read()
    assert P.camera_moves({'camera_moves': [{'start_s': 5.0, 'end_s': 6.5, 'kind': 'pan'}]}, Fraction(50)) == [{'start_frame': 250, 'end_frame': 325, 'kind': 'pan'}]
    assert P.camera_moves({}, Fraction(50)) == []
