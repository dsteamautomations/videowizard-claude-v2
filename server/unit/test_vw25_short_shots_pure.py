"""SK, 25 Nov 2026 (VW-25 issues 3b and 2; requirements R3b and R2 of design/_work/vw25-fixes-requirements-25-nov.md, "Approve as written").
- R3b: a footage shot may be shorter than its piece's hold, down to 1.0 s, when it carries `short` with one of six reasons; the options check,
  Trim and Other clips read one function (review.limits) for the lowest length and the main action; the card says "Short shot, 1.4 s: ...".
  `short` is a permission: it acts only on a cut that needs it (a cut that meets its piece's own hold and main action is judged as before).
- R2: a sentence with three or more commas that has fewer shots and blanks under it in time than things named is flagged (N18), never refused.
Older ways retired: the four separate copies of the rule (validator._piece, stage._trim, review.room, review.fit_piece), which differed (Trim knew
neither the still-frame nor the camera-move exception; the check and Trim compared the hold as a binary fraction, the form as a decimal)."""
import json
from copy import deepcopy
from pathlib import Path

import pytest

from app.errors import Problem
from app.stage2 import package as P, review as R, slides as SL, stage as S, validator as V
from test_design91_b2_pure import POLICY, ev, option, package as b2_package
from test_design127_review_pure import USER, film, saved
from test_review_page import FakeConn, FakeStore, RUN

SERVER = Path(__file__).resolve().parents[1]
SIX = ('list_item', 'thing', 'kinds', 'repeated_action', 'recap', 'b_roll')
# a close piece: 20 s at 25 frames a second, hold 2 s (50 frames), main action 100-160 (2.4 s)
ROW = {'in_frame': 0, 'out_frame': 500, 'source_fps': '25', 'min_hold_s': 2.0, 'action_peak': {'in_frame': 100, 'out_frame': 160}, 'camera_moves': [],
       'effective_shot_size': 'CU', 'eligibility': 'ELIGIBLE_AS_IS', 'client_safe': True, 'risk_flags': []}
PAN = {'start_frame': 140, 'end_frame': 200, 'kind': 'pan'}


# ---------- the one function ----------

def test_one_function_gives_the_lowest_length_and_the_action_kept_whole():
    assert R.limits(ROW) == (50, (100, 160), None)                                        # no `short`: the piece's hold, the main action whole
    assert set(R.SHORT) == set(SIX)
    for kind in SIX:
        assert R.limits(ROW, kind)[0] == 25                                               # 1.0 s in place of the hold (D1b)
    assert R.limits(ROW, 'list_item')[1] is None and R.limits(ROW, 'b_roll')[1] is None   # the main action need not be whole
    assert R.limits(ROW, 'repeated_action')[1] == (100, 160)                              # but for a repeated action: one stroke stays whole
    assert R.limits({**ROW, 'action_peak': None}) == (50, None, None)


def test_the_two_exceptions_of_the_proposal_check_are_in_the_one_function():
    assert R.limits(ROW, held=True)[0] == 1 and R.limits(ROW, 'thing', held=True)[0] == 1   # a still frame held at the end: no lowest length, with `short` too
    assert R.limits({**ROW, 'camera_moves': [PAN]}) == (50, (100, 140), PAN)              # the action is complete where a reported camera move starts inside it
    assert R.limits({**ROW, 'camera_moves': [{**PAN, 'start_frame': 100}, {**PAN, 'start_frame': 161}]})[1] == (100, 160)   # a move at the action's first frame or after it changes nothing
    two = [{**PAN, 'start_frame': 150}, PAN]
    assert R.limits({**ROW, 'camera_moves': two})[1:] == ((100, 140), PAN)                # the earliest move inside the action


def test_one_second_is_rounded_up_to_whole_source_frames():
    ntsc = {**ROW, 'source_fps': '30000/1001'}                                            # 29.97 frames a second
    assert R.limits(ntsc, 'thing')[0] == 30 and R.limits(ntsc)[0] == 60
    assert R.judge(0, 29, {**ntsc, 'action_peak': None}, 'thing')['least'] == 30
    fifty = {**ROW, 'source_fps': '50'}                                                   # the clip's rate, not the film's: 1.0 s is 50 of its frames
    assert R.limits(fifty, 'thing')[0] == 50 and R.limits(fifty)[0] == 100
    assert R.limits({**ROW, 'min_hold_s': 0.8})[0] == 20                                  # 0.8 s at 25 a second is 20 frames, as the trim form always said


# ---------- which rule judges a cut ----------

def test_short_is_used_only_by_a_cut_that_needs_it():
    j = R.judge(90, 170, ROW, 'thing')                                                    # 3.2 s, over its hold, its action whole
    assert (j['least'], j['action'], j['short'], j['why'], j['alone']) == (50, (100, 160), None, None, False)
    j = R.judge(0, 35, ROW, 'thing')                                                      # 1.4 s, under its hold
    assert (j['least'], j['action'], j['short'], j['why'], j['alone']) == (25, None, 'thing', None, True)
    assert R.judge(100, 140, ROW, 'thing')['short'] == 'thing' and not R.judge(100, 140, ROW, 'thing')['alone']   # 1.6 s: needs `short`, not a run
    assert R.judge(0, 35, ROW)['short'] is None and R.judge(0, 35, ROW)['least'] == 50   # no field: as before
    assert R.judge(0, 35, ROW, 'nonsense')['short'] is None                               # an unknown value gives no permission (the check refuses the value)
    assert R.judge(110, 180, ROW, 'recap')['short'] == 'recap'                            # over its hold, the main action cut: it needs `short` too


@pytest.mark.parametrize('row, match, why', [
    ({**ROW, 'effective_shot_size': 'WS'}, 'direct', 'a wide shot is not cut short'),
    ({**ROW, 'effective_shot_size': 'EWS'}, 'direct', 'a wide shot is not cut short'),
    ({**ROW, 'camera_moves': [{'start_frame': 20, 'end_frame': 60, 'kind': 'glide'}]}, 'direct', 'a short shot does not cut into a camera move (the reported glide at 20-60)'),
])
def test_what_the_server_can_see_is_refused_on_a_short_shot(row, match, why):
    assert R.judge(0, 35, row, 'thing', match=match)['why'] == why
    assert R.judge(0, 35, row, 'thing', match=match)['short'] == 'thing'


def test_a_camera_move_beside_the_cut_and_b_roll_on_a_b_roll_shot_are_fine():
    beside = [{'start_frame': 35, 'end_frame': 60, 'kind': 'pan'}, {'start_frame': 0, 'end_frame': 0, 'kind': 'pan'}]   # starts at the cut's last frame; ends at its first
    assert R.judge(0, 35, {**ROW, 'camera_moves': beside}, 'thing')['why'] is None
    assert R.judge(0, 35, {**ROW, 'camera_moves': [{'start_frame': 34, 'end_frame': 60, 'kind': 'pan'}]}, 'thing')['why']
    assert R.judge(10, 45, {**ROW, 'camera_moves': [{'start_frame': 0, 'end_frame': 11, 'kind': 'pan'}]}, 'thing')['why']
    assert R.judge(0, 35, ROW, 'b_roll', match='b_roll')['why'] is None
    assert R.judge(0, 35, ROW, 'b_roll', match='direct')['why'] == 'it is cut short as B-roll, and this piece is not placed as B-roll'
    assert R.judge(0, 35, ROW, 'b_roll', match='library')['why']
    assert R.judge(0, 60, {**ROW, 'effective_shot_size': 'WS', 'action_peak': None}, 'thing')['why'] is None   # a wide shot at its hold is not cut short: nothing to refuse


# ---------- the options check: one piece ----------

def piece(a, z, row=ROW, short=None, **kw):
    refusals, flags = [], []
    V._piece('T', {'source_in_frame': a, 'source_out_frame': z, 'match': 'direct', 'evidence': 'x', 'crop': 'full', **kw}, row, {}, refusals, flags, short)
    return refusals, flags


def test_a_shot_without_the_field_is_checked_as_before():
    assert piece(90, 170) == ([], [])
    assert piece(90, 139) == (['T: G2 must_include_action_peak 100-160 dropped', 'T: G3 shorter than min_comprehension_hold_s 2.0'], [])
    assert piece(110, 180) == (['T: G2 must_include_action_peak 100-160 dropped'], [])
    assert piece(200, 249, {**ROW, 'action_peak': None}) == (['T: G3 shorter than min_comprehension_hold_s 2.0'], [])
    assert piece(200, 250, {**ROW, 'action_peak': None}) == ([], [])
    assert piece(200, 210, {**ROW, 'action_peak': None}, hold_last_frame=True) == ([], [])   # a still frame held at the end
    refusals, flags = piece(90, 150, {**ROW, 'camera_moves': [PAN]})                      # ends after the reported pan starts: the action is complete
    assert refusals == [] and flags == ['T: G2 move: ends at 150, before the reported pan at 140; the action is complete']
    assert piece(90, 139, {**ROW, 'camera_moves': [PAN]})[0][0] == 'T: G2 must_include_action_peak 100-160 dropped'
    assert piece(90, 170, {**ROW, 'camera_moves': [PAN]}) == ([], [])                     # the whole action: no flag


@pytest.mark.parametrize('kind', SIX)
def test_each_of_the_six_values_lets_a_close_steady_shot_go_down_to_one_second(kind):
    row = {**ROW, 'action_peak': None}
    match = 'b_roll' if kind == 'b_roll' else 'direct'
    assert piece(200, 225, row, kind, match=match) == ([], [])                            # 1.0 s
    assert piece(200, 224, row, kind, match=match) == ([f'T: G3 a short shot is at least 1.0 s (25 source frames); it has 24'], [])


def test_the_main_action_stays_whole_only_for_a_repeated_action():
    assert piece(110, 145, ROW, 'thing') == ([], [])                                      # 1.4 s out of the middle of a 2.4 s action
    assert piece(110, 145, ROW, 'repeated_action') == (['T: G2 must_include_action_peak 100-160 dropped'], [])
    assert piece(100, 160, {**ROW, 'min_hold_s': 4.0}, 'repeated_action') == ([], [])     # one whole stroke, under the hold
    refusals, flags = piece(100, 140, {**ROW, 'min_hold_s': 4.0, 'camera_moves': [PAN]}, 'repeated_action')
    assert refusals == [] and len(flags) == 1 and 'G2 move' in flags[0]                   # the stroke is complete where the pan starts; the cut stops there


def test_each_refusal_of_a_short_shot_names_its_reason():
    assert piece(0, 35, {**ROW, 'effective_shot_size': 'WS'}, 'thing') == (['T: short thing: a wide shot is not cut short'], [])
    assert piece(0, 35, {**ROW, 'camera_moves': [{'start_frame': 20, 'end_frame': 60, 'kind': 'glide'}]}, 'kinds') == (
        ['T: short kinds: a short shot does not cut into a camera move (the reported glide at 20-60)'], [])
    assert piece(0, 35, ROW, 'b_roll') == (['T: short b_roll: it is cut short as B-roll, and this piece is not placed as B-roll'], [])
    assert piece(0, 35, ROW, 'b_roll', match='b_roll') == ([], [])
    assert piece(0, 24, ROW, 'thing') == (['T: G3 a short shot is at least 1.0 s (25 source frames); it has 24'], [])
    ntsc = {**ROW, 'source_fps': '30000/1001', 'action_peak': None}
    assert piece(0, 29, ntsc, 'thing')[0] == ['T: G3 a short shot is at least 1.0 s (30 source frames); it has 29'] and piece(0, 30, ntsc, 'thing')[0] == []
    fifty = {**ROW, 'source_fps': '50', 'action_peak': None}                              # measured in the clip's own frames
    assert piece(0, 49, fifty, 'thing')[0] and piece(0, 50, fifty, 'thing')[0] == []


def test_short_with_a_held_still_frame_is_allowed_and_the_still_frame_rule_is_unchanged():
    assert piece(200, 210, {**ROW, 'action_peak': None}, 'thing', hold_last_frame=True) == ([], [])
    assert piece(110, 120, ROW, 'thing', hold_last_frame=True) == ([], [])                # with `short` the main action need not be whole
    assert R.judge(110, 120, ROW, 'thing', True)['alone'] is False and R.judge(110, 120, ROW, 'thing')['alone'] is True   # held: its frames are not its time on screen, so it needs no run
    assert piece(110, 120, ROW, hold_last_frame=True)[0] == ['T: G2 must_include_action_peak 100-160 dropped']   # without: as before


def test_short_on_a_shot_at_or_over_its_hold_is_accepted():
    assert piece(90, 170, ROW, 'list_item') == ([], [])
    assert piece(90, 170, {**ROW, 'effective_shot_size': 'WS'}, 'list_item') == ([], [])  # not cut short, so nothing of the short rule applies
    assert piece(0, 22, {**ROW, 'min_hold_s': 0.8, 'action_peak': None}, 'list_item') == ([], [])   # a hold under 1.0 s: the piece's own figure still serves it


# ---------- the options check: the whole proposal ----------

BASE = b2_package()


def row_(i, **kw):
    """Piece p<i>: its own clip, 8 s at 25 a second, hold 2 s, no main action, close; neighbours differ in size."""
    return {**deepcopy(BASE['sub_clips'][0]), 'sub_clip_id': f'p{i}:S', 'clip_id': f'p{i}', 'clip_name': f'P{i}.MP4', 'in_frame': 0, 'out_frame': 200, 'source_fps': '25',
            'min_hold_s': 2.0, 'action_peak': None, 'camera_moves': [], 'effective_shot_size': ('CU', 'MCU', 'MS')[i % 3], 'eligibility': 'ELIGIBLE_AS_IS',
            'accent_frames': [], 'natural_cut_frames': [], **kw}


def pack(scenes, rows, sentences=()):
    pk, beats, at = deepcopy(BASE), [], 0
    for n, frames in enumerate(scenes, 1):
        beats.append({'beat_id': f'BEAT_0{n}', 'passage_id': f'P00{n}', 'text': '', 'process_stages': ['laying'], 'timeline_start_frame': at, 'timeline_end_frame': at + frames,
                      'target_beat_frames': frames})
        at += frames
    pk.update(beats=P.with_steps(beats, list(sentences)), sub_clips=rows, narration={'sentences': list(sentences), 'words': [], 'silences': []})
    return pk


def proposal(*scenes):
    return {'contract': 'vw2-options-v1', 'options': [option(n, f'BEAT_0{n}', 'PRIMARY', events) for n, events in enumerate(scenes, 1)],
            'qc_self': {f'Q{i}': {'pass': True, 'evidence': 'x'} for i in range(1, 9)}}


def shots(*lengths, short='list_item', first=0):
    """One shot per length (frames), each from its own piece; a length given as (n, None) carries no `short`."""
    out = []
    for i, n in enumerate(lengths, first):
        n, kind = n if isinstance(n, tuple) else (n, short)
        out.append(ev(f'p{i}:S', 0, n, **({'short': kind} if kind else {})))
    return out


def refused(doc, pk):
    return V.validate_options(deepcopy(doc), pk, POLICY)['refusals']


ROWS = [row_(i) for i in range(9)]


def test_a_proposal_without_the_field_is_valid_as_before():
    assert refused(proposal(shots(50, 60, 75, short=None)), pack([185], ROWS)) == []
    assert refused(proposal(shots(35, 60, 75, short=None)), pack([170], ROWS)) == ['OPTION #1 shot 1 (p0:S): G3 shorter than min_comprehension_hold_s 2.0']
    out = V.validate_options(proposal(shots(50, 50, short=None)), pack([100], [row_(0, effective_shot_size='WS'), row_(1)]), POLICY)
    assert out['refusals'] == [] and 'OPTION #1 shot 1 (p0:S): R5 hold under 3.0 s for a WS' in out['flags']   # the wide-shot warning stays for a normal shot


def test_a_value_that_is_not_one_of_the_six_and_short_on_an_ai_stretch_are_refused():
    pk = pack([150], ROWS)
    assert refused(proposal(shots(50, (50, 'quick'), 50, short=None)), pk) == [
        'OPTION #1 shot 2 (p1:S): short must be one of list_item, thing, kinds, repeated_action, recap, b_roll, or left out']
    assert refused(proposal(shots(50, (50, ['thing']), 50, short=None)), pk)[0].endswith('or left out')   # not a text at all
    assert refused(proposal(shots(50, (50, ''), 50, short=None)), pk) == []               # an empty field is no field
    blank = {'blank': True, 'timeline_frames': 50, 'intent': 'the mix', 'none_fit': 'no clip shows it', 'short': 'thing'}
    assert refused(proposal([*shots(50, short=None), blank, *shots(50, short=None, first=1)]), pk) == [
        'OPTION #1 blank at event 2: short is for a footage shot: a blank has no hold']


def test_a_shot_under_one_and_a_half_seconds_stands_only_in_a_run_of_three_short_shots():
    alone = 'short: a shot under 1.5 s stands only in a run of 3 or more shots in a row that each carry `short`; this run has '
    assert refused(proposal(shots(30, 30, 30)), pack([90], ROWS)) == []                   # three in a row, 1.2 s each
    assert refused(proposal(shots(40, 30, 40)), pack([110], ROWS)) == []                  # the 1.2 s one in the middle of two short shots of 1.6 s
    assert refused(proposal(shots((50, None), 30, (50, None))), pack([130], ROWS)) == [f'OPTION #1 shot 2 (p1:S): {alone}1']   # one short shot between two long ones
    assert refused(proposal(shots(30, 30, (50, None))), pack([110], ROWS)) == [f'OPTION #1 shot 1 (p0:S): {alone}2', f'OPTION #1 shot 2 (p1:S): {alone}2']
    assert refused(proposal(shots((50, None), 37, (50, None))), pack([137], ROWS)) == [f'OPTION #1 shot 2 (p1:S): {alone}1']   # 1.48 s
    assert refused(proposal(shots((50, None), 38, (50, None))), pack([138], ROWS)) == []  # 1.52 s: over 1.5 s, a single short shot may stand (25 a second: 37.5 frames)
    assert refused(proposal(shots(30, 60, 30)), pack([120], ROWS)) == []                  # a shot at its hold that carries `short` is part of the run
    assert refused(proposal(shots(30, (60, None), 30)), pack([120], ROWS)) == [f'OPTION #1 shot 1 (p0:S): {alone}1', f'OPTION #1 shot 3 (p2:S): {alone}1']


def test_the_run_is_counted_in_film_order_across_scenes_and_an_ai_stretch_ends_it():
    alone = 'this run has '
    pk = pack([60, 60], ROWS)
    assert refused(proposal(shots(30, 30), shots(30, (30, None), first=2)), pack([60, 60], [*ROWS[:3], row_(3, min_hold_s=1.2), *ROWS[4:]])) == []   # two close a scene, the third opens the next
    two = refused(proposal(shots(30, 30), shots((60, None), first=2)), pk)
    assert len(two) == 2 and all(x.endswith(alone + '2') for x in two)
    blank = {'blank': True, 'timeline_frames': 30, 'intent': 'the mix', 'none_fit': 'no clip shows it'}
    cut = refused(proposal([*shots(30, 30), blank, *shots(30, first=2)]), pack([120], ROWS))
    assert [x[-len(alone) - 1:] for x in cut] == [alone + '2', alone + '2', alone + '1']    # the AI stretch is not a short shot: it ends the run
    gap = refused(proposal(shots(30, 30)), pack([60, 60], ROWS))                          # scene 2 has no option at all
    assert sum(1 for x in gap if x.endswith(alone + '2')) == 2


def test_an_alternative_takes_its_shots_short():
    pk = pack([90], [*ROWS[:8], row_(8, min_hold_s=3.0)])
    alt = ev('p8:S', 0, 30)
    events = shots(30, 30, 30)
    events[1]['alternatives'] = [alt]
    assert refused(proposal(events), pk) == []                                            # 1.2 s of a piece with a 3 s hold: it stands where its shot stands
    wide = pack([90], [*ROWS[:8], row_(8, effective_shot_size='WS')])
    assert refused(proposal(events), wide) == ['OPTION #1 shot 2 (p1:S) alternative 1: short list_item: a wide shot is not cut short']
    plain = pack([150], [*ROWS[:8], row_(8, min_hold_s=3.0)])                             # the shot carries no `short`: its alternative gets none
    events = shots(50, 50, 50, short=None)
    events[1]['alternatives'] = [{**ev('p8:S', 0, 50), 'short': 'thing'}]
    assert refused(proposal(events), plain) == ['OPTION #1 shot 2 (p1:S) alternative 1: G3 shorter than min_comprehension_hold_s 3.0']
    lone = shots((50, None), 40, (50, None))                                              # the shot is 1.6 s and may stand alone; its alternative is checked in its place
    lone[1]['alternatives'] = [ev('p8:S', 0, 40)]
    assert refused(proposal(lone), pack([140], [*ROWS[:8], row_(8, min_hold_s=3.0)])) == []


def test_a_piece_with_under_one_second_of_usable_picture_cannot_be_a_short_shot():
    pk = pack([120], [row_(0, out_frame=20), *ROWS[1:]])
    assert 'OPTION #1 shot 1 (p0:S): G3 a short shot is at least 1.0 s (25 source frames); it has 20' in refused(
        proposal([ev('p0:S', 0, 20, short='thing'), *shots(50, 50, short=None, first=1)]), pk)
    assert R.fit_piece(row_(0, out_frame=20), 25, 25, short='thing') == 'it has 0.8 s of usable picture; the shot needs 1.0 s'


# ---------- R2: each thing named in a list ----------

NINE = 'The mix takes sand, cement, lime, tiles, bowls, shells, jelly, water and brick dust.'   # nine things, seven commas


def listed(events, sentences, scene=225):
    return [f for f in V.validate_options(proposal(events), pack([scene], ROWS, sentences), POLICY)['flags'] if 'N18' in f]


def test_a_list_sentence_shown_by_fewer_events_than_things_is_flagged_never_refused():
    one = [{'text': NINE, 'start_frame': 0, 'end_frame': 220}]
    out = V.validate_options(proposal(shots(75, 75, 75, short=None)), pack([225], ROWS, one), POLICY)
    assert out['refusals'] == []
    assert [f for f in out['flags'] if 'N18' in f] == [
        'OPTION #1: N18 list: step BEAT_01.S1 (The mix takes sand, cement, lime, tiles, bowls, shells, jell) names about 8 things and has 3 shots and blanks under it: '
        'check that each thing named has its picture, its blank or its note']
    assert V.answer_flags(out['flags'])['act_on'].count(next(f for f in out['flags'] if 'N18' in f)) == 1   # a flag to act on, said in full


def test_no_flag_when_each_thing_has_an_event_or_the_sentence_is_no_list_or_there_are_no_steps():
    one = [{'text': NINE, 'start_frame': 0, 'end_frame': 220}]
    blank = {'blank': True, 'timeline_frames': 25, 'intent': 'lime', 'none_fit': 'no clip shows it'}
    assert listed([*shots(25, 25), blank, *shots(25, 25, 25, 25, 25, 25, first=2)], one) == []   # eight shots and one blank under the sentence
    assert listed(shots(75, 75, 75, short=None), []) == []                                # a film with no sentences in its package: no steps, no flag
    assert listed(shots(75, 75, 75, short=None), [{'text': 'Sand, lime and water are mixed, then rested.', 'start_frame': 0, 'end_frame': 220}]) == []   # two commas
    assert listed(shots(75, 75, 75, short=None), [{'text': 'Sand and lime and water and jelly and tiles are mixed.', 'start_frame': 0, 'end_frame': 220}]) == []   # joined by "and": the instruction covers it


def test_the_events_are_counted_by_time_under_the_sentence():
    two = [{'text': 'First the ground is cleared.', 'start_frame': 0, 'end_frame': 70}, {'text': 'Then come sand, cement, lime, and water.', 'start_frame': 76, 'end_frame': 220}]
    assert len(listed(shots(75, 75, 75, short=None), two)) == 1                           # four things, two events under the second sentence (the first ends at frame 75)
    assert 'has 2 shots and blanks' in listed(shots(75, 75, 75, short=None), two)[0]
    assert listed(shots(75, 30, 40, 40, 40, short=None), two) == []                       # four events under it
    comma = [{'text': 'When it rains, as it does, the yard, which slopes, drains well.', 'start_frame': 0, 'end_frame': 220}]
    assert len(listed(shots(75, 75, 75, short=None), comma)) == 1                         # commas, no list: the flag shows and costs one read


# ---------- Trim ----------

def session(mark=None, at=1, **piece_c1):
    """The small film of design/127 (scene 1 = AI 100 + c1 75 + B-roll c2 75 with the alternative c4); mark: the `short` of shot 1.2 (c1), or of
    the event `at`; piece_c1: fields of the piece c1."""
    doc, pk = film()
    for r in pk['sub_clips']:
        r.update(effective_shot_size='CU', camera_moves=[])
    pk['sub_clips'][0].update(piece_c1)
    if mark:
        doc['options'][0]['events'][at]['short'] = mark
    sess = {'contract': 'vw2-stage2-session-v1', 'package': {'key': 'p', 'digest': 'pk1'}, 'current': 'd1', 'accepted': {'version': 1, 'digest': 'd1'},
            'versions': [{'version': 1, 'digest': 'd1', 'file': {'key': 'run-1/stage2/options-v1.json'}, 'slides': SL.slides(doc, pk, 25)}],
            'frames': {}, 'inspections': {}, 'renders': {}, 'decisions': {}, 'extra_rules': [], 'master': None, 'recorded': {}}
    return FakeStore({'run-1/stage2/session.json': sess, 'run-1/stage2/options-v1.json': {'document': doc, 'package_digest': 'pk1'}, 'p': pk})


def trim(store, slide, edit):
    return S.decide(FakeConn({}), store, USER, RUN, slide, 'TRIM', '', edit)


def test_trim_on_a_normal_shot_keeps_its_limits():
    store = session(min_hold_s=2.0)                                                       # shot 1.2 is 3.0 s of a piece with a 2 s hold
    assert S.trim_room(store, RUN, '1.2')['text'].startswith('This shot: 3.0 s. It can lose up to 1.0 s ')
    with pytest.raises(Problem, match=r'shorter than its hold 2.0 s\. This shot: 3.0 s\. It can lose up to 1.0 s'):
        trim(store, '1.2', 'start:0,end:1.2')
    trim(store, '1.2', 'start:0,end:1')
    assert saved(store)['decisions']['1.2']['edit'] == 'in:0,out:-25'


def test_trim_on_a_short_shot_uses_the_same_one_second():
    store = session('thing', min_hold_s=4.0)                                              # 3.0 s of a piece with a 4 s hold, marked short
    assert S.trim_room(store, RUN, '1.2')['text'].startswith('This shot: 3.0 s. It can lose up to 2.0 s (start up to 2.0 s later, end up to 2.0 s earlier).')
    with pytest.raises(Problem, match=r'shorter than 1.0 s, the least for a short shot\. This shot: 3.0 s\. It can lose up to 2.0 s'):
        trim(store, '1.2', 'start:1.2,end:1')
    assert '1.2' not in saved(store)['decisions']
    trim(store, '1.2', 'start:1,end:1')                                                   # down to 1.0 s
    assert saved(store)['decisions']['1.2']['edit'] == 'in:25,out:-25'
    plain = session(None, min_hold_s=3.0)                                                 # the same shot without the mark: its own figure
    assert S.trim_room(plain, RUN, '1.2')['text'].startswith('This shot: 3.0 s. It cannot get shorter.')


def test_trim_keeps_the_main_action_unless_the_shot_is_short_and_keeps_it_for_a_repeated_action():
    peak = {'in_frame': 20, 'out_frame': 60}
    with pytest.raises(Problem, match='drops the action peak 20-60'):
        trim(session(None, action_peak=peak), '1.2', 'start:1,end:0')
    store = session('repeated_action', action_peak=peak, min_hold_s=4.0)
    assert 'start up to 0.8 s later, end up to 0.6 s earlier' in S.trim_room(store, RUN, '1.2')['text']
    with pytest.raises(Problem, match='drops the action peak 20-60'):
        trim(store, '1.2', 'start:1,end:0')
    trim(store, '1.2', 'start:0.8,end:0.6')                                               # one whole stroke, 1.6 s
    loose = session('thing', action_peak=peak, min_hold_s=4.0)
    trim(loose, '1.2', 'start:1,end:0')                                                   # a thing, not an action: the cut may start inside it
    assert saved(loose)['decisions']['1.2']['edit'] == 'in:25,out:0'


def test_trim_now_knows_the_two_exceptions_of_the_proposal_check():
    row = {**ROW, 'camera_moves': [PAN]}
    shot = {'source_in_frame': 90, 'source_out_frame': 170}
    assert S._trim(dict(shot), 'in:0,out:-20', row, 25, 'Shot')['source_out_frame'] == 150   # ends after the pan starts: the action is complete there
    with pytest.raises(Problem, match='drops the action peak 100-160'):
        S._trim(dict(shot), 'in:0,out:-31', row, 25, 'Shot')
    with pytest.raises(Problem, match='drops the action peak 100-160'):
        S._trim(dict(shot), 'in:0,out:-20', ROW, 25, 'Shot')                               # no reported move: as before
    still = {'source_in_frame': 200, 'source_out_frame': 260, 'hold_last_frame': True}
    assert S._trim(dict(still), 'in:0,out:-40', {**ROW, 'action_peak': None}, 25, 'Shot')['timeline_frames'] == 20   # a still frame held at the end has no lowest length
    with pytest.raises(Problem, match='shorter than its hold 2.0 s'):
        S._trim({**still, 'hold_last_frame': False}, 'in:0,out:-40', {**ROW, 'action_peak': None}, 25, 'Shot')
    assert R.room(200, 260, {**ROW, 'action_peak': None}, held=True)['lose'] == 59          # and the form says the same


def test_a_trim_that_takes_a_short_shot_into_a_camera_move_is_refused_with_the_reason():
    store = session('thing', min_hold_s=4.0, camera_moves=[{'start_frame': 80, 'end_frame': 120, 'kind': 'pan'}])
    with pytest.raises(Problem, match=r'the trim cannot be made on Scene 1 · Shot 2: a short shot does not cut into a camera move \(the reported pan at 80-120\)\. This shot'):
        trim(store, '1.2', 'start:0,end:-0.4')
    trim(store, '1.2', 'start:0,end:-0.2')                                                # up to the frame where the pan starts
    long = session('thing', min_hold_s=3.0, camera_moves=[{'start_frame': 80, 'end_frame': 120, 'kind': 'pan'}])
    trim(long, '1.2', 'start:0,end:-0.4')                                                 # at its hold the shot is not cut short: a camera move is fine, as for any shot


def test_a_scene_out_of_balance_offers_a_short_shot_down_to_one_second():
    doc, pk = film()
    pk['sub_clips'][0]['min_hold_s'] = 4.0
    doc['options'][0]['events'][1]['short'] = 'thing'
    sl = SL.slides(doc, pk, 25)
    rows = {r['sub_clip_id']: r for r in pk['sub_clips']}
    targets = {b['beat_id']: b['target_beat_frames'] for b in pk['beats']}
    out = R.balance(doc['options'], {'1.3': {'action': 'TRIM', 'edit': 'in:0,out:25'}}, sl, rows, targets, 25)   # shot 1.3 grew by 1 s: the scene is 1 s long
    assert out[0]['takers'][0] == {'slide': '1.2', 'title': 'Scene 1 · Shot 2', 'edit': 'in:0,out:-25'}
    del doc['options'][0]['events'][1]['short']
    assert [t['slide'] for t in R.balance(doc['options'], {'1.3': {'action': 'TRIM', 'edit': 'in:0,out:25'}}, sl, rows, targets, 25)[0]['takers']] == ['1.3']


# ---------- Other clips ----------

def test_a_piece_is_fitted_to_a_short_shot_under_the_same_rule():
    row = {**ROW, 'in_frame': 0, 'out_frame': 500}
    assert R.fit_piece(row, 35, 25) == 'it needs 2.0 s on screen to be understood; the shot has 1.4 s'   # as before, on a normal shot
    assert R.fit_piece(row, 35, 25, short='thing') == (113, 148, 35)                      # 1.4 s out of the middle of its main action
    assert R.fit_piece({**row, 'action_peak': None}, 35, 25, short='list_item') == (0, 35, 35)
    assert R.fit_piece(row, 35, 25, short='repeated_action') == 'its main action takes 2.4 s; the shot has 1.4 s'
    assert R.fit_piece({**row, 'min_hold_s': 4.0}, 70, 25, short='repeated_action') == (95, 165, 70)   # the whole stroke, under the hold
    assert R.fit_piece({**row, 'effective_shot_size': 'WS'}, 35, 25, short='thing') == (
        'it needs 2.0 s on screen to be understood; the shot has 1.4 s; a wide shot is not cut short')
    assert R.fit_piece({**row, 'action_peak': None, 'camera_moves': [{'start_frame': 10, 'end_frame': 40, 'kind': 'pan'}]}, 35, 25, short='thing') == (
        'it needs 2.0 s on screen to be understood; the shot has 1.4 s; a short shot does not cut into a camera move (the reported pan at 10-40)')
    assert R.fit_piece(row, 35, 25, short='b_roll', match='direct').endswith('; it is cut short as B-roll, and this piece is not placed as B-roll')
    assert R.fit_piece(row, 35, 25, short='b_roll', match='b_roll') == (113, 148, 35)
    assert R.fit_piece(row, 20, 25, short='thing') == 'a short shot needs 1.0 s on screen; the shot has 0.8 s'
    assert R.fit_piece({**row, 'effective_shot_size': 'WS'}, 75, 25, short='thing') == (93, 168, 75)   # it fits by its own figures: `short` takes nothing away
    assert R.fit_piece(row, 600, 25, partial=True, short='thing') == (0, 500, 500)        # an all-AI scene has no `short`: as before


def spare(store, **fields):
    """c5 becomes a piece that fits scene 1 by chapter (it is offered under Other clips)."""
    pk = json.loads(store.files['p'])
    pk['sub_clips'][4].update(fit_kinds={'BEAT_01': 'chapter'}, eligibility='ELIGIBLE_AS_IS', grade='A', **fields)
    store.files['p'] = json.dumps(pk).encode('utf-8')
    return store


def test_other_clips_offers_a_piece_on_a_short_shot_that_a_normal_shot_refuses():
    store = spare(session('list_item', min_hold_s=4.0), min_hold_s=5.0)                   # c5 needs 5 s on screen; shots 1.2 (short) and 1.3 (normal) are 3 s
    got = S.others(store, RUN, '1.2')['pieces']
    assert [(p['sub_clip_id'], p['can'], p['why']) for p in got] == [('c5:S', True, '')]
    assert S.others(store, RUN, '1.3')['pieces'][0]['why'] == 'it needs 5.0 s on screen to be understood; the shot has 3.0 s'
    with pytest.raises(Problem, match='c5:S cannot be used on Scene 1 · Shot 3: it needs 5.0 s on screen'):
        S.decide(FakeConn({}), store, USER, RUN, '1.3', 'SWAP', '', None, 'c5:S')
    out = S.decide(FakeConn({}), store, USER, RUN, '1.2', 'SWAP', '', None, 'c5:S')
    assert out['swap']['short'] == 'Short shot, 3.0 s: one item of a list' and (out['swap']['source_in_frame'], out['swap']['source_out_frame']) == (0, 75)
    assert next(r for r in S.slides_view(store, RUN)['slides'] if r['slide'] == '1.2')['short'] == 'Short shot, 3.0 s: one item of a list'
    wide = spare(session('list_item', min_hold_s=4.0), min_hold_s=5.0, effective_shot_size='WS')
    assert S.others(wide, RUN, '1.2')['pieces'][0]['why'] == 'it needs 5.0 s on screen to be understood; the shot has 3.0 s; a wide shot is not cut short'
    with pytest.raises(Problem, match='a wide shot is not cut short'):
        S.decide(FakeConn({}), wide, USER, RUN, '1.2', 'SWAP', '', None, 'c5:S')


def test_a_piece_that_meets_its_own_hold_on_a_short_shot_carries_no_line():
    store = spare(session('list_item', min_hold_s=4.0), effective_shot_size='WS')         # c5: hold 1 s, wide; the short shot is 3 s
    out = S.decide(FakeConn({}), store, USER, RUN, '1.2', 'SWAP', '', None, 'c5:S')
    assert 'short' not in out['swap']
    assert next(r for r in S.slides_view(store, RUN)['slides'] if r['slide'] == '1.2')['short'] is None   # the line of the replaced clip does not stay


def test_short_b_roll_under_other_clips_is_for_a_piece_placed_as_b_roll():
    store = spare(session('b_roll', at=2), min_hold_s=5.0)                                # shot 1.3 is B-roll, 3 s, marked short as B-roll
    assert S.others(store, RUN, '1.3')['pieces'][0]['can'] is True                        # c5 fits the scene by chapter: placed as B-roll
    pk = json.loads(store.files['p'])
    pk['sub_clips'][4]['fit_kinds'] = {'BEAT_01': 'direct'}                               # the same piece as a direct match of the scene
    store.files['p'] = json.dumps(pk).encode('utf-8')
    assert S.others(store, RUN, '1.3')['pieces'][0]['why'].endswith('it is cut short as B-roll, and this piece is not placed as B-roll')


# ---------- the card ----------

def test_the_card_says_short_shot_with_its_length_and_reason_only_under_the_hold():
    doc, pk = film()
    pk['sub_clips'][0]['min_hold_s'] = 4.0                                                # c1 (shot 1.2, 3 s)
    pk['sub_clips'][3]['min_hold_s'] = 4.0                                                # c4, the alternative of shot 1.3
    rows = {s['no']: s for s in SL.slides(doc, pk, 25)}
    assert all(s.get('short') is None for s in rows.values())                             # no field anywhere: no line
    doc['options'][0]['events'][1]['short'] = 'list_item'
    doc['options'][0]['events'][2]['short'] = 'recap'
    rows = {s['no']: s for s in SL.slides(doc, pk, 25)}
    assert rows['1.2']['short'] == 'Short shot, 3.0 s: one item of a list'
    assert rows['1.3']['short'] is None                                                   # c2 has a 1 s hold: at or over its hold, no line
    assert rows['1.3A1']['short'] == 'Short shot, 3.0 s: a recap or a run of pictures'    # the alternative takes its shot's `short`
    assert rows['1.1'].get('short') is None and rows['1'].get('short') is None
    plain = {**ROW, 'action_peak': None}
    assert [R.short_text(0, 35, plain, k, False, 1.4) for k in SIX] == [
        'Short shot, 1.4 s: one item of a list', 'Short shot, 1.4 s: a thing, not an action', 'Short shot, 1.4 s: kinds of one thing side by side',
        'Short shot, 1.4 s: a repeated action', 'Short shot, 1.4 s: a recap or a run of pictures', 'Short shot, 1.4 s: B-roll under words with no specific claim']
    assert R.short_text(0, 60, plain, 'thing', False, 2.4) is None and R.short_text(0, 35, plain, None, False, 1.4) is None and R.short_text(0, 35, plain, 'quick', False, 1.4) is None
    assert R.short_text(100, 160, {**ROW, 'min_hold_s': 4.0}, 'repeated_action', False, 2.4) == 'Short shot, 2.4 s: a repeated action'
    assert R.short_text(110, 180, ROW, 'recap', False, 2.8) == 'Short shot, 2.8 s: a recap or a run of pictures'   # over its hold, its main action cut: said too
    assert R.short_text(200, 210, plain, 'thing', True, 0.4) is None                       # a still frame held at the end has no hold to go under


def test_the_page_and_the_chat_show_the_same_line():
    store = session('thing', min_hold_s=4.0)
    row = next(r for r in S.slides_view(store, RUN)['slides'] if r['slide'] == '1.2')     # `vw master slides`
    assert row['short'] == 'Short shot, 3.0 s: a thing, not an action'
    assert next(r for r in S.review_view(FakeConn({}), store, RUN)['slides'] if r['slide'] == '1.2')['short'] == row['short']   # the review page
    page = (SERVER / 'app' / 'templates' / 'review.html').read_text(encoding='utf-8')
    assert "esc(s.short)" in page


def test_the_package_shows_the_field_on_a_footage_shot_only():
    shape = BASE['shapes']['options']['options'][0]['events']
    assert shape[0]['short'] == 'only on a shot cut under its hold: list_item|thing|kinds|repeated_action|recap|b_roll'
    assert 'short' not in shape[0]['alternatives'][0] and 'short' not in shape[1]


# ---------- the instruction ----------

def stage_of(name):
    return next(s for s in json.loads((SERVER / 'procedures' / 'v3.json').read_text(encoding='utf-8'))['stages'] if s['name'] == name)


def test_the_options_instruction_carries_the_short_shot_rule_and_the_list_rule():
    p = stage_of('options')['prompt']
    rule2 = p[p.index('\n2. ') + 1:p.index('\n3. ')]
    assert rule2.startswith('2. Cut real shots to the meaning. Several short real shots may run together.') and rule2.rstrip().endswith('Never hold a shot longer because the footage exists.')
    for kind in SIX:
        assert kind + ' (' in rule2, kind
    for never in ('a step being shown', 'a wide shot', 'something to read', 'a camera move', 'the first time the film shows', 'a heavy crop', 'a pause in the narration'):
        assert never in rule2, never
    assert '`short`' in rule2 and 'down to 1 s' in rule2 and 'under 1.5 s only inside a run of three or more' in rule2
    assert '2 to 3.5 s each is normal' not in p
    assert 'each thing named has its own shot' in p and 'or a note for the operator saying it is not shown' in p and 'N18' in p
    for word in ('user', 'documentary', 'brick', 'mortar', 'concrete'):                    # every category of video; operator, never "user"
        assert word not in rule2.lower(), word


def test_the_master_instruction_no_longer_names_a_refusal_the_build_never_made():
    builds = [t for t in stage_of('master')['steps'] if '`vw master build`' in t and 'when it refuses' in t]
    assert len(builds) == 1 and "(a scene sent back to find footage, a trim that changes a scene's length, a clip used twice)" in builds[0]
    assert 'under 3 s' not in json.dumps(stage_of('master'))
    retired = json.loads((SERVER / 'retired-sentences.json').read_text(encoding='utf-8'))['sentences']
    assert 'a blank under 3 s' in retired and '2 to 3.5 s each is normal' in retired


def test_the_second_look_helper_knows_the_field_and_the_list_rule():
    text = (SERVER.parent / 'plugin' / 'agents' / 'vw-scene-review.md').read_text(encoding='utf-8')
    assert 'A shot that carries `short`' in text and 'list_item, thing, kinds, repeated_action, recap, b_roll' in text
    assert 'each thing named has its own shot' in text


def test_the_wording_script_changes_nothing_when_run_twice():
    import sys
    sys.path.insert(0, str(SERVER.parent / 'scripts'))
    import shortshots_wording as W
    d = json.loads((SERVER / 'procedures' / 'v3.json').read_text(encoding='utf-8'))
    before = json.dumps(d, ensure_ascii=False)
    W.apply(d)
    assert json.dumps(d, ensure_ascii=False) == before
    assert all(len(s.split()) >= 4 for s in W.RETIRED)
