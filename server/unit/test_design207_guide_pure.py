"""design/207, package C (SK, 16 Nov 2026): any kind of shot may be an AI video. The scene description takes a fourth kind, `other`;
a thing travels along a timed path as a person does; a run, crossing people, an untried kind and a shot where nothing moves warn and do not refuse."""
import copy

import pytest

from app import guide as GD, guide_drawing, guide_spec as G
from test_guide_spec_pure import box, counter_pour, home_walk, levels, said

NOTE = ('Bottles stand upright on a moving belt and travel along it at a steady 0.6 metres a second, one after another, left to right. '
        'Nothing else on the line moves; no person is in the hall.')
UNTRIED = 'This kind of shot has not been tried here; the first take is a trial and may need a second.'
STILL = 'Nothing moves in this shot; a still costs less.'


def line():
    """A bottling line with nobody in view: one bottle travels 3 m along the belt in 5 s."""
    return {
        'recipe': 'other', 'process_note': NOTE, 'seconds': 5,
        'camera': {'position': [0.0, -4.0, 1.4], 'aim': [0.0, 0.0, 1.0], 'lens': 35},
        'sun': {'direction': [0.5, 0.6, -0.62], 'from': 'stated'},
        'action': {'start': 0, 'end': 5},
        'set': [box('GROUND', 'the floor', -30, 30, -30, 30, -0.02, 0.0, [0.3, 0.3, 0.32], ground=True, level=True),
                box('BELT', 'the belt', -3.0, 3.0, -0.3, 0.3, 0.0, 0.9, [0.08, 0.2, 0.1]),
                {'id': 'BOTTLE', 'name': 'the bottle', 'shape': 'cylinder', 'centre': [-1.5, 0.0, 1.05], 'radius': 0.05, 'depth': 0.3, 'axis': 'Z', 'colour': [0.5, 0.05, 0.05],
                 'path': [{'t': 0, 'at': [-1.5, 0.0, 0.9]}, {'t': 5, 'at': [1.5, 0.0, 0.9]}]}],
        'people': [], 'props': [],
    }


def van():
    """A van pulls away along a road: a box 4 m long built pointing along +X, the way it first moves."""
    s = line()
    s['set'] = [s['set'][0], {**box('VAN', 'the van', -5.0, -1.0, 2.0, 4.0, 0.0, 2.0, [0.05, 0.1, 0.5]), 'path': [{'t': 0, 'at': [-3.0, 3.0, 0.0]}, {'t': 5, 'at': [3.0, 3.0, 0.0]}]}]
    s['camera'] = {'position': [0.0, -9.0, 1.6], 'aim': [0.0, 3.0, 1.0], 'lens': 35}
    return s


def warned(rows, check):
    return said(rows, check, 'warn')


# ---------- 1. a fourth kind ----------

def test_a_shot_of_another_kind_with_nobody_and_a_thing_on_a_path_is_taken_with_the_untried_warning():
    spec = line()
    assert G.problems(spec) == []
    rows = G.checks(spec)
    assert G.refusals(rows) == [], G.refusals(rows)
    assert warned(rows, 'untried').startswith(UNTRIED) and not warned(rows, 'still')
    assert next(r for r in rows if r['check'] == 'untried')['before_take'] is True


def test_the_three_proven_kinds_carry_no_untried_warning_and_no_nothing_moves_warning():
    for spec in (home_walk(), counter_pour()):
        rows = G.checks(spec)
        assert G.refusals(rows) == [] and not warned(rows, 'untried') and not warned(rows, 'still')


def test_an_unknown_kind_is_refused_naming_the_four_words():
    spec = line()
    spec['recipe'] = 'crowd'
    found = ' '.join(G.problems(spec))
    assert 'recipe: one of walker, one_action_close, transfer_close, other.' in found and 'not yet available' not in found


@pytest.mark.parametrize('change, word', [
    (lambda s: s.update(process_note='It moves.'), 'process_note'),
    (lambda s: s.pop('process_note'), 'process_note'),
    (lambda s: s.pop('action'), 'action'),
])
def test_another_kind_still_needs_the_real_process_and_its_one_action(change, word):
    spec = line()
    change(spec)
    assert any(word in m for m in G.problems(spec))


# ---------- 2. a thing travels ----------

@pytest.mark.parametrize('path, word', [
    ([{'t': 0, 'at': [-1.5, 0.0, 0.9]}], 'at least two timed points'),
    ([], 'at least two timed points'),
    ('along the belt', 'at least two timed points'),
    ([{'t': 3, 'at': [-1.5, 0.0, 0.9]}, {'t': 1, 'at': [1.5, 0.0, 0.9]}], 'in order'),
    ([{'t': 0, 'at': [-1.5, 0.0, 0.9]}, {'t': 9, 'at': [1.5, 0.0, 0.9]}], 'in order'),
    ([{'t': 0, 'at': [-1.5, 0.0, 0.9]}, {'t': 5, 'at': 'the end'}], 'every point is'),
    ([{'t': 0, 'at': [0.0, 0.0, 0.9]}, {'t': 5, 'at': [1.5, 0.0, 0.9]}], 'starts where the thing stands'),   # the cylinder stands at x = -1.5
])
def test_a_wrong_path_of_a_thing_is_refused_in_plain_words(path, word):
    spec = line()
    spec['set'][2]['path'] = path
    found = G.problems(spec)
    assert found and any(word in m and 'BOTTLE' in m for m in found), found


def test_a_thing_on_a_path_is_held_before_its_first_point_straight_between_and_held_after_the_last():
    spec = line()
    spec['set'][2]['path'] = [{'t': 1, 'at': [-1.5, 0.0, 0.9]}, {'t': 4, 'at': [1.5, 0.0, 0.9]}]
    b = spec['set'][2]
    mid = lambda t: [round((lo + hi) / 2, 3) for lo, hi in zip(*G.piece_box(b, t))]
    assert mid(0.0) == mid(1.0) == [-1.5, 0.0, 1.05] and mid(2.5) == [0.0, 0.0, 1.05] and mid(4.0) == mid(5.0) == [1.5, 0.0, 1.05]
    lo, hi = G.piece_box(b, 2.5)
    assert hi[0] - lo[0] == pytest.approx(0.1) and hi[2] - lo[2] == pytest.approx(0.3)   # its size never changes


def test_a_thing_at_rest_is_exactly_as_before():
    wall = home_walk()['set'][1]
    assert G.piece_box(wall) == G.piece_box(wall, 3.0) == ((-0.5, 2.0, 0.0), (7.5, 2.25, 3.0))
    assert G.piece_corners(wall, 3.0) == G._corners(*G.piece_box(wall))


def test_the_layout_follows_the_moving_thing():
    spec = line()
    first, last = ({r['id']: r for r in G.layout(spec, t)}['BOTTLE'] for t in (0.0, 5.0))
    assert first['right'] < 50 < last['left']
    block = G.layout_block(spec)
    assert '- the bottle: from ' in block and block.endswith('Nobody is in view.')


def test_a_thing_may_travel_and_spin_at_once():
    spec = line()
    spec['set'][2]['spin'] = {'axis': 'Z', 'keys': [{'t': 0, 'deg': 0}, {'t': 5, 'deg': 360}]}
    assert G.problems(spec) == [] and G.refusals(G.checks(spec)) == []


def test_a_moving_thing_points_along_its_path_and_turns_where_the_path_bends():
    spec = van()
    v = spec['set'][1]
    v['path'] = [{'t': 0, 'at': [-3.0, 3.0, 0.0]}, {'t': 2, 'at': [3.0, 3.0, 0.0]}, {'t': 5, 'at': [3.0, 9.0, 0.0]}]   # along +X, then along +Y
    assert G.problems(spec) == []
    size = lambda t: [round(hi - lo, 3) for lo, hi in zip(*G.piece_box(v, t))]
    assert size(1.0) == [4.0, 2.0, 2.0] and size(4.0) == [2.0, 4.0, 2.0]
    v['facing'] = [1, 0]   # a facing fixes the way it points: it no longer turns with the path
    assert G.problems(spec) == [] and size(4.0) == [4.0, 2.0, 2.0]
    v['facing'] = 'east'
    assert any('VAN' in m and 'facing' in m for m in G.problems(spec))


def test_a_thing_has_no_speed_limit():
    spec = van()
    spec['set'][1]['path'][1]['at'] = [57.0, 3.0, 0.0]   # 12 m/s
    rows = G.checks(spec)
    assert G.refusals(rows) == [] and not levels(rows, 'speed')


def test_a_prop_that_nobody_holds_may_travel_and_one_that_is_held_may_not():
    spec = counter_pour()
    spec['props'].append({'id': 'TIN', 'name': 'the tin', 'colour': [0.6, 0.1, 0.1], 'size': [0.1, 0.1, 0.1], 'at': [-1.0, -0.3, 1.0],
                          'path': [{'t': 0, 'at': [-1.0, -0.3, 1.0]}, {'t': 3, 'at': [-0.6, -0.3, 1.0]}]})
    assert G.problems(spec) == []
    tin = spec['props'][1]
    assert G.prop_at(spec, tin, 0.0) == pytest.approx((-1.0, -0.3, 1.05)) and G.prop_at(spec, tin, 1.5) == pytest.approx((-0.8, -0.3, 1.05)) and G.prop_at(spec, tin, 3.0) == pytest.approx((-0.6, -0.3, 1.05))
    assert G.refusals(G.checks(spec)) == []
    tin['path'] = tin['path'][:1]
    assert any('TIN' in m and 'at least two timed points' in m for m in G.problems(spec))
    tin['path'] = [{'t': 0, 'at': [0.0, -0.3, 1.0]}, {'t': 3, 'at': [-0.6, -0.3, 1.0]}]
    assert any('TIN' in m and 'starts where the thing stands' in m for m in G.problems(spec))
    jug = spec['props'][0]
    jug['path'] = [{'t': 0, 'at': jug['at']}, {'t': 3, 'at': [0.0, -0.3, 1.0]}]
    assert any('JUG' in m and 'held' in m and 'path' in m for m in G.problems(spec))


def test_a_person_in_the_way_of_a_moving_thing_is_refused_at_the_moment_they_meet():
    spec = van()
    spec['people'] = [{'id': 'GUARD', 'name': 'the guard', 'colour': [0.9, 0.5, 0.0], 'height': 1.7, 'at': [2.0, 3.0, 0.0], 'facing': [0, -1]}]
    text = said(G.checks(spec), 'clash')
    assert 'the guard passes through the van at' in text and ' at 0.0 s' not in text   # clear at the start; the van arrives later
    spec['people'][0]['at'] = [2.0, 0.5, 0.0]   # beside the road
    assert not said(G.checks(spec), 'clash')


def test_a_thing_that_comes_into_the_picture_after_the_first_frame_is_warned():
    spec = van()
    spec['set'][1].update(min=[-30.0, 2.0, 0.0], max=[-26.0, 4.0, 2.0], path=[{'t': 0, 'at': [-28.0, 3.0, 0.0]}, {'t': 5, 'at': [0.0, 3.0, 0.0]}])
    rows = G.checks(spec)
    assert 'the van is not in the first frame' in warned(rows, 'first_frame') and G.refusals(rows) == []
    assert not warned(G.checks(van()), 'first_frame')


# ---------- 3. refusals that became warnings ----------

def test_a_runner_is_a_warning_and_not_a_refusal():
    spec = home_walk()
    spec['people'][0]['path'][1]['at'] = [-2.2 + 4.0 * 5, -0.8, 0.0]
    del spec['people'][0]['pace']
    rows = G.checks(spec)
    text = warned(rows, 'speed')
    assert not said(rows, 'speed') and 'the father moves at 4.00 m/s' in text and 'A run has failed with a camera that follows' in text and 'keep the camera fixed' in text and 'second take' in text
    assert 'not yet available' not in text and next(r for r in rows if r['check'] == 'speed')['before_take'] is True


def test_two_crossing_walkers_are_a_warning_and_not_a_refusal():
    spec = home_walk()
    spec['people'][0]['path'] = [{'t': 0, 'at': [2.5, -0.8, 0.0]}, {'t': 5, 'at': [6.5, -0.8, 0.0]}]   # the father walks past the mother, between her and the camera
    rows = G.checks(spec)
    text = warned(rows, 'crossing')
    assert not said(rows, 'crossing') and G.refusals(rows) == []
    assert 'the father and the mother overlap in the picture' in text and 'have come out as copies' in text and 'keep the paths apart' in text and 'second take' in text
    assert next(r for r in rows if r['check'] == 'crossing')['before_take'] is True


def test_a_shot_where_nothing_moves_is_warned():
    spec = line()
    del spec['set'][2]['path']
    rows = G.checks(spec)
    assert warned(rows, 'still') == STILL and G.refusals(rows) == [] and next(r for r in rows if r['check'] == 'still')['before_take'] is True
    spec['set'][2]['spin'] = {'axis': 'Z', 'keys': [{'t': 0, 'deg': 0}, {'t': 5, 'deg': 90}]}   # a thing turning in place moves
    assert not warned(G.checks(spec), 'still')
    spec['set'][2]['spin'] = {'axis': 'Z', 'keys': [{'t': 0, 'deg': 30}, {'t': 5, 'deg': 30}]}   # held at one angle: it does not
    assert warned(G.checks(spec), 'still') == STILL
    spec['set'][2]['path'] = [{'t': 0, 'at': [-1.5, 0.0, 0.9]}, {'t': 5, 'at': [-1.5, 0.0, 0.9]}]   # a path that goes nowhere
    assert warned(G.checks(spec), 'still') == STILL


def test_people_who_only_stand_do_not_move_and_a_working_hand_does():
    spec = counter_pour()
    spec['props'] = []
    assert not warned(G.checks(spec), 'still')
    spec['people'][0]['hands'] = {'right': [{'t': 0, 'at': [-0.3, -0.3, 1.15]}, {'t': 3, 'at': [-0.3, -0.3, 1.15]}]}   # the hand rests in one place
    assert warned(G.checks(spec), 'still') == STILL
    spec = home_walk()
    spec['people'] = spec['people'][2:]   # only the mother, standing
    assert warned(G.checks(spec), 'still') == STILL


# ---------- 4. no people ----------

def test_every_person_rule_is_skipped_cleanly_with_nobody():
    for people in ([], None):
        spec = line()
        spec['people'] = people
        if people is None:
            assert any('people: a list' in m for m in G.problems(spec))   # the list itself stays required, empty when nobody is in the shot
            continue
        rows = G.checks(spec, subjects=[])
        assert not [r for r in rows if r['check'] in ('reach', 'right_hand', 'posture', 'speed', 'pace', 'crossing', 'visible_share', 'boxes', 'level_edge', 'pole')]
        assert G.layout_block(spec).endswith('Nobody is in view.') and 'Exactly' not in G.layout_block(spec)


def test_the_shots_drawing_is_made_with_nobody_and_says_what_moves():
    d, notes = guide_drawing.description(line())
    assert d['people'] == [] and {p['material'] for p in d['pieces']} == {'BELT', 'BOTTLE'}
    assert notes == ['the bottle (BOTTLE) moves in this shot; it is drawn where it starts.']
    assert guide_drawing.description(home_walk())[1] == []


# ---------- how a warning reaches the operator's ready-to-shoot card ----------

def test_the_ready_to_shoot_card_repeats_the_warnings_that_matter_before_a_paid_take():
    spec = line()
    session = {'guides': {'VS1': {'sha256': 'abc', 'seconds': 5, 'checks': G.checks(spec)}}}
    card = GD.ready_card(session, 'VS1', 8.0)
    assert card['warnings'] == [next(r['message'] for r in G.checks(spec) if r['check'] == 'untried')]
    assert 'red outlines' in card['look_for'] and card['look_for'].endswith('Before you pay: ' + card['warnings'][0])
    session['guides']['VS1']['checks'] = G.checks(home_walk())   # a proven kind: the card is as before
    card = GD.ready_card(session, 'VS1', 8.0)
    assert card['warnings'] == [] and card['look_for'] == 'On the overlay: every person and thing of the still sits on the red outlines of the guide.'
    session['guides']['VS1'].pop('checks')   # a guide stored before this change
    assert GD.ready_card(session, 'VS1', 8.0)['warnings'] == []
