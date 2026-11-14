"""Integration steps B to D: the scene description of a guide and the checks made on it before any spend (app/guide_spec.py).
The fixture is our own hand-made walk shot of 11 Nov (videobuilder-v4/phase2/shots/home/home_set.py), whose layout numbers Blender printed
and the still's prompt used: the arithmetic here must give the same numbers."""
import copy

import pytest

from app import guide_spec as G

NOTE = ('A family coming home walks at a relaxed stroll, about 0.95 metres a second, the child a little behind the father, nobody running. '
        'A person walking keeps one line and one pace; the mother on the verandah stands still; nothing else in the lane moves.')


def box(i, name, x0, x1, y0, y1, z0, z1, colour, **more):
    return {'id': i, 'name': name, 'shape': 'box', 'min': [x0, y0, z0], 'max': [x1, y1, z1], 'colour': colour, **more}


def home_walk():
    """The walk home: the mother stands on the verandah; the father and the daughter stroll along the lane, left to right, for the whole 5 s."""
    walk = lambda x0: [{'t': 0, 'at': [x0, -0.8, 0.0]}, {'t': 5, 'at': [x0 + 0.95 * 5, -0.8, 0.0]}]
    return {
        'recipe': 'walker', 'process_note': NOTE, 'seconds': 5,
        'camera': {'position': [0.6, -9.5, 1.7], 'aim': [0.6, 0.0, 1.1], 'lens': 35},
        'sun': {'direction': [0.5, 0.6, -0.62], 'from': 'stated'},
        'action': {'start': 0, 'end': 5},
        'set': [box('GROUND', 'the earth', -30, 30, -30, 30, -0.02, 0.0, [0.55, 0.48, 0.38], ground=True, level=True),
                box('HOUSE_WALL', 'the house wall', -0.5, 7.5, 2.0, 2.25, 0.0, 3.0, [0.45, 0.12, 0.06]),
                box('VER_FLOOR', 'the verandah floor', -0.5, 7.5, 0.5, 2.0, 0.0, 0.3, [0.26, 0.08, 0.30], level=True),
                box('VER_ROOF', 'the verandah roof', -0.8, 7.8, 0.2, 2.25, 3.0, 3.15, [0.20, 0.20, 0.23]),
                box('DOOR', 'the door', 4.9, 5.8, 1.96, 2.0, 0.3, 2.4, [0.04, 0.32, 0.12]),
                box('WINDOW', 'the window', 0.9, 1.9, 1.96, 2.0, 1.3, 2.3, [0.03, 0.05, 0.30], hung=True)],
        'people': [{'id': 'FATHER', 'name': 'the father', 'colour': [0.10, 0.30, 0.85], 'height': 1.70, 'pace': 'stroll', 'path': walk(-2.2)},
                   {'id': 'DAUGHTER', 'name': 'the daughter', 'colour': [0.95, 0.45, 0.02], 'height': 1.25, 'pace': 'stroll', 'path': walk(-3.6)},
                   {'id': 'MOTHER', 'name': 'the mother', 'colour': [0.80, 0.05, 0.50], 'height': 1.58, 'at': [4.2, 1.2, 0.3], 'facing': [-1, 0]}],
        'props': [],
    }


def counter_pour():
    """One action, close: a man behind a counter lifts a jug with his right hand; the camera is on his right side."""
    return {
        'recipe': 'one_action_close', 'process_note': NOTE, 'seconds': 3,
        'camera': {'position': [-2.0, -1.6, 1.3], 'aim': [-0.3, -0.3, 1.2], 'lens': 50},
        'sun': {'direction': [0.5, 0.6, -0.62], 'from': 'stated'},
        'action': {'start': 0.3, 'end': 2.6},
        'set': [box('GROUND', 'the floor', -10, 10, -10, 10, -0.02, 0.0, [0.3, 0.3, 0.32], ground=True, level=True),
                box('COUNTER', 'the counter', -1.25, 0.5, -0.5, -0.15, 0.0, 1.0, [0.55, 0.4, 0.25])],
        'people': [{'id': 'MAN', 'name': 'the man', 'colour': [0.95, 0.85, 0.1], 'height': 1.70, 'at': [0.0, 0.1, 0.0], 'facing': [0, -1],
                    'hands': {'right': [{'t': 0, 'at': [-0.3, -0.3, 1.15]}, {'t': 0.3, 'at': [-0.3, -0.3, 1.15]}, {'t': 1.3, 'at': [-0.3, -0.3, 1.40]}, {'t': 3, 'at': [-0.3, -0.3, 1.40]}]}}],
        'props': [{'id': 'JUG', 'name': 'the jug', 'colour': [0.1, 0.12, 0.5], 'size': [0.12, 0.12, 0.2], 'at': [-0.3, -0.3, 1.0],
                   'held': [{'from': 0.3, 'to': 3, 'by': 'MAN.right'}]}],
        'beats': [{'kind': 'lift', 'from': 0.3, 'to': 1.3}],
    }


def levels(rows, check=None):
    return [(r['check'], r['level']) for r in rows if check is None or r['check'] == check]


def said(rows, check, level='refuse'):
    return ' '.join(r['message'] for r in rows if r['check'] == check and r['level'] == level)


# ---------- the camera gives the numbers Blender printed for the hand-made shot ----------

def test_the_layout_numbers_match_the_hand_made_walk_shot():
    rows = {r['id']: r for r in G.layout(home_walk())}
    # the still's prompt of 11 Nov: father 16-21% wide, head 40% down, feet 74%; daughter 1-6%, feet 74% (her "50%" was the top of the body box,
    # printed without the head; here the head is counted); mother 81-85%, head 37%, feet 62%; the door 86-94% wide, 29-60% down; the window 53-61%, 30-45%
    for who, left, right, top, bottom in (('FATHER', 16, 21, 40, 74), ('DAUGHTER', 1, 6, None, 74), ('MOTHER', 81, 85, 37, 62), ('DOOR', 86, 94, 29, 60), ('WINDOW', 53, 61, 30, 45)):
        r = rows[who]
        assert abs(r['left'] - left) <= 1.5 and abs(r['right'] - right) <= 1.5 and (top is None or abs(r['top'] - top) <= 1.5) and abs(r['bottom'] - bottom) <= 1.5, (who, r)
    assert 'GROUND' not in rows   # the ground is not a thing to place


def test_the_layout_block_names_everyone_counts_them_and_is_written_by_the_server():
    text = G.layout_block(home_walk())
    assert text.startswith('EXACT LAYOUT, measured from the first image')
    father = next(line for line in text.splitlines() if line.startswith('- the father:'))
    assert father == '- the father: from 16% to 21% of the width; the top of the head at 39% down, the feet at 73% down.'   # Blender printed 16-21, 40, 74
    assert '- the door: from 8' in text and '% of the width, from ' in text and text.endswith('Exactly 3 people in view; no one else.')


def test_a_person_cut_by_the_frame_is_said_so_and_one_outside_is_left_out():
    spec = home_walk()
    spec['camera'] = {'position': [0.6, -3.0, 1.2], 'aim': [0.6, 0.0, 1.1], 'lens': 50}   # close: the walkers' feet fall below the frame
    spec['people'][0]['path'] = [{'t': 0, 'at': [0.6, -0.8, 0.0]}, {'t': 5, 'at': [1.2, -0.8, 0.0]}]
    spec['people'][1]['path'] = [{'t': 0, 'at': [-9.0, -0.8, 0.0]}, {'t': 5, 'at': [-5.0, -0.8, 0.0]}]   # far outside the picture
    text = G.layout_block(spec)
    assert 'the father' in text and 'cut off by the bottom edge' in text and 'the daughter' not in text


# ---------- the shape of a description ----------

def test_the_two_fixtures_have_no_shape_problems_and_pass_every_refusal():
    for spec in (home_walk(), counter_pour()):
        assert G.problems(spec) == []
        assert G.refusals(G.checks(spec)) == [], G.refusals(G.checks(spec))


@pytest.mark.parametrize('change, word', [
    (lambda s: s.update(recipe='crowd'), 'not yet available'),
    (lambda s: s.update(process_note='He walks.'), 'process_note'),
    (lambda s: s.update(seconds=16), 'whole number from 3 to 15'),
    (lambda s: s.update(seconds=2), 'whole number from 3 to 15'),
    (lambda s: s.update(seconds=4.5), 'whole number'),
    (lambda s: s['camera'].update(lens=10), 'camera'),
    (lambda s: s.pop('sun'), 'sun'),
    (lambda s: s['sun'].update({'from': 'guessed'}), 'sun'),
    (lambda s: s.update(set=[]), 'set'),
    (lambda s: s['set'][1].update(min=[0, 0, 5]), 'each max larger than its min'),
    (lambda s: s['set'][1].update(id='house wall'), 'capitals'),
    (lambda s: s['set'][2].update(id='HOUSE_WALL'), 'used twice'),
    (lambda s: s['people'][0].update(height=0), 'height'),
    (lambda s: s['people'][0].update(path=[{'t': 3, 'at': [0, 0, 0]}, {'t': 1, 'at': [1, 0, 0]}]), 'in order'),
    (lambda s: s['people'][2].pop('facing'), 'which way the person faces'),
    (lambda s: s['people'][0].update(pace='sprint'), 'pace'),
    (lambda s: s['people'][0].update(colour=[2, 0, 0]), 'colour'),
    (lambda s: s.pop('action'), 'action'),
    (lambda s: s.update(props=[{'id': 'POT', 'name': 'the pot', 'colour': [0, 0, 0], 'size': [0.2, 0.2, 0.2], 'at': [0, 0, 0], 'held': [{'from': 0, 'to': 1, 'by': 'NOBODY.right'}]}]), 'by a person of this shot'),
    (lambda s: s.update(marks={'band': 'NOPE'}), 'band'),
])
def test_a_wrong_description_is_named_in_plain_words_and_never_crashes(change, word):
    spec = home_walk()
    change(spec)
    found = G.problems(spec)
    assert found and any(word in line for line in found), found


@pytest.mark.parametrize('junk', [None, [], 'a scene', 7, {}, {'set': 'x', 'people': 3, 'camera': [], 'props': {}}])
def test_anything_at_all_in_the_file_is_answered_not_crashed(junk):
    assert G.problems(junk)


# ---------- the checks before any spend: refusals ----------

def test_a_thing_resting_on_nothing_is_refused():
    spec = home_walk()
    spec['set'].append(box('SHELF', 'the shelf', 3.0, 4.0, 1.9, 2.0, 1.5, 1.55, [0.1, 0.4, 0.4]))
    assert 'the shelf (SHELF) rests on nothing' in said(G.checks(spec), 'support')
    spec['set'][-1]['hung'] = True   # a thing fixed to a wall says so
    assert levels(G.checks(spec), 'support') == []


def test_a_hand_beyond_reach_is_refused_with_the_distance_and_the_moment():
    spec = counter_pour()
    spec['people'][0]['hands']['right'][2]['at'] = [-0.75, -0.45, 1.40]
    spec['people'][0]['hands']['right'][3]['at'] = [-0.75, -0.45, 1.40]
    text = said(G.checks(spec), 'reach')
    assert "the man's right hand is" in text and 'the limit is 0.62 m' in text and 'never stretches' in text


def test_the_left_hand_doing_the_job_is_refused_and_so_is_a_thing_on_the_left():
    spec = counter_pour()
    spec['people'][0]['hands'] = {'left': [{'t': 0, 'at': [0.3, -0.3, 1.15]}, {'t': 2, 'at': [0.3, -0.3, 1.40]}]}
    spec['props'][0].update(at=[0.3, -0.3, 1.0], held=[{'from': 0.3, 'to': 3, 'by': 'MAN.left'}])
    text = said(G.checks(spec), 'right_hand')
    assert 'left hand does the job' in text and "held in the man's left hand" in text and "picked up from the man's left side" in text


def test_a_right_hand_hidden_behind_the_body_is_refused():
    spec = counter_pour()
    spec['camera'] = {'position': [2.0, 1.5, 1.3], 'aim': [-0.3, -0.3, 1.2], 'lens': 50}   # the camera behind him, on his LEFT side
    assert 'hidden' in said(G.checks(spec), 'right_hand')


def test_a_path_through_a_wall_is_refused_and_a_person_standing_on_a_floor_is_not():
    spec = home_walk()
    assert levels(G.checks(spec), 'clash') == []   # the mother stands ON the verandah floor
    spec['people'][0]['path'] = [{'t': 0, 'at': [2.0, -0.8, 0.0]}, {'t': 5, 'at': [2.0, 3.0, 0.0]}]   # straight through the verandah and the wall
    assert 'the father passes through' in said(G.checks(spec), 'clash')


def test_a_box_faster_than_the_top_speed_is_refused_and_a_pace_off_its_band_is_warned():
    spec = home_walk()
    spec['people'][0]['path'][1]['at'] = [-2.2 + 3.0 * 5, -0.8, 0.0]
    assert '3.00 m/s' in said(G.checks(spec), 'speed')
    spec['people'][0]['path'][1]['at'] = [-2.2 + 1.7 * 5, -0.8, 0.0]
    assert levels(G.checks(spec), 'speed') == [] and 'stroll' in said(G.checks(spec), 'pace', 'warn')


def test_a_walker_passing_in_front_of_somebody_is_refused():
    spec = home_walk()
    spec['people'][0]['path'] = [{'t': 0, 'at': [2.5, -0.8, 0.0]}, {'t': 5, 'at': [6.5, -0.8, 0.0]}]   # the father walks past the mother, between her and the camera
    assert 'the father and the mother overlap in the picture' in said(G.checks(spec), 'crossing')


def test_two_people_in_place_who_overlap_are_a_warning_only():
    spec = home_walk()
    spec['people'] = [spec['people'][2], {**copy.deepcopy(spec['people'][2]), 'id': 'AUNT', 'name': 'the aunt', 'colour': [0, 0.6, 0.6], 'at': [4.3, 1.6, 0.3]}]
    assert levels(G.checks(spec), 'crossing') == [('crossing', 'warn')]


def test_somebody_never_in_the_picture_is_refused_and_an_edge_entry_is_allowed_with_its_moment():
    spec = home_walk()
    spec['people'][1]['path'] = [{'t': 0, 'at': [-9.0, -0.8, 0.0]}, {'t': 5, 'at': [-1.0, -0.8, 0.0]}]   # walks in from the left edge
    rows = G.checks(spec)
    entry = next(r for r in rows if r['check'] == 'first_frame')
    assert entry['level'] == 'info' and 'walks in from the edge' in entry['message'] and 0 < entry['enters_at'] < 5
    spec['people'][1] = {**spec['people'][1], 'path': None, 'at': [-20.0, -0.8, 0.0], 'facing': [1, 0]}
    del spec['people'][1]['path']
    assert 'the daughter is never in the picture' in said(G.checks(spec), 'first_frame')


def test_a_prop_outside_the_first_frame_is_refused():
    spec = counter_pour()
    spec['props'][0].update(at=[-6.0, 6.0, 0.0], held=[])
    assert 'the jug is not in the first frame' in said(G.checks(spec), 'first_frame')


def test_everything_the_plan_puts_in_the_shot_needs_a_box():
    spec = home_walk()
    spec['people'][0]['element_id'] = 'P1'
    rows = G.checks(spec, subjects=['P1', 'P9'])
    assert 'The plan puts P9 in this shot and the scene has no box for it' in said(rows, 'boxes') and 'P1' not in said(rows, 'boxes')


# ---------- warnings: rules on trial, never a refusal ----------

def test_the_warnings_never_refuse():
    spec = counter_pour()
    spec['beats'] = [{'kind': 'lift', 'from': 0.3, 'to': 0.6}]
    spec['action']['end'] = 1.3
    spec['set'].append(box('KERB', 'the kerb', -3, -2.9, -3, -2.9, 0.0, 0.2, [0.95, 0.95, 0.95]))
    rows = G.checks(spec)
    assert ('beat', 'warn') in levels(rows) and ('action_fills', 'warn') in levels(rows)
    assert G.refusals(rows) == []


def test_a_person_at_the_edge_of_the_ground_they_stand_on_is_warned():
    spec = home_walk()
    spec['people'][2]['at'] = [4.2, 0.7, 0.3]   # 0.2 m from the verandah's front edge
    assert 'from the edge of the verandah floor' in said(G.checks(spec), 'level_edge', 'warn')


def test_the_share_of_each_person_in_the_first_frame_is_printed():
    rows = [r for r in G.checks(home_walk()) if r['check'] == 'visible_share']
    assert {r['message'].split(':')[0] for r in rows} == {'the father', 'the daughter', 'the mother'} and all(r['value'] > 0.9 for r in rows)


def test_the_blind_spots_are_told():
    assert 'cannot see' in G.BLIND and 'door arcs' in G.BLIND


# ---------- where things are ----------

def test_a_held_prop_follows_the_hand_and_stays_where_it_was_let_go():
    spec = counter_pour()
    spec['props'][0]['held'] = [{'from': 0.3, 'to': 2.0, 'by': 'MAN.right'}]
    assert G.prop_at(spec, spec['props'][0], 0.0) == (-0.3, -0.3, 1.1)   # at rest: the middle of the jug above its foot
    assert G.prop_at(spec, spec['props'][0], 1.5)[2] == pytest.approx(1.40, abs=0.01)
    assert G.prop_at(spec, spec['props'][0], 2.9) == G.prop_at(spec, spec['props'][0], 2.0)


def test_a_walker_faces_the_way_they_walk_and_the_right_is_the_persons_own_right():
    spec = home_walk()
    pos, yaw, speed = G.person_at(spec['people'][0], 1.0)
    assert speed == pytest.approx(0.95, abs=0.02) and pos[0] == pytest.approx(-2.2 + 0.95, abs=0.01)
    assert G.right_of(yaw) == pytest.approx((0.0, -1.0, 0.0), abs=1e-6)   # walking to +X, his right is toward the camera (-Y)


# ---------- posture (design/200, SK 14 Nov 2026): a person stands where a real person would do the job ----------

def test_a_hand_working_in_front_of_the_body_passes_the_posture_check():
    rows = G.checks(counter_pour())
    assert not said(rows, 'posture') and ('posture', 'info') in levels(rows, 'posture')


def test_a_hand_reaching_behind_the_shoulders_is_refused_with_the_distance_and_the_moment():
    """The lab shot as first planned: the body faces one way and the right hand works a knob behind it. No person can."""
    spec = counter_pour()
    spec['people'][0]['hands']['right'] = [{'t': 0, 'at': [-0.2, 0.45, 1.15]}, {'t': 3, 'at': [-0.2, 0.45, 1.25]}]   # he faces -Y; the hand is 0.35 m behind him
    spec['props'] = []
    text = said(G.checks(spec), 'posture')
    assert 'behind the line of the shoulders' in text and '0.35 m' in text and 'the man' in text and 'in front' in text


def test_the_same_job_mirrored_so_the_person_faces_it_passes():
    spec = counter_pour()
    spec['people'][0].update(facing=[0, 1], hands={'right': [{'t': 0, 'at': [0.2, 0.45, 1.15]}, {'t': 3, 'at': [0.2, 0.45, 1.25]}]})   # turned round: the knob is now in front, on his right
    spec['props'] = []
    assert not said(G.checks(spec), 'posture')


def test_what_a_person_watches_lies_within_a_comfortable_turn_of_the_head():
    spec = counter_pour()
    spec['people'][0]['watches'] = [-0.8, -2.0, 1.4]          # ahead and a little to one side: 22 degrees
    assert not said(G.checks(spec), 'posture')
    spec['people'][0]['watches'] = [3.0, 0.1, 1.4]            # square to his side: 90 degrees
    text = said(G.checks(spec), 'posture')
    assert '90 degrees' in text and '45 degrees' in text and 'Turn the body' in text


def test_a_walker_is_judged_by_the_way_they_walk():
    spec = home_walk()
    spec['people'][0]['watches'] = [-10.0, -0.8, 1.5]         # the father walks to the right and looks straight back
    assert '180 degrees' in said(G.checks(spec), 'posture')


def test_what_is_watched_is_a_point_of_three_numbers():
    spec = counter_pour()
    spec['people'][0]['watches'] = 'the dial'
    assert any('watches' in m for m in G.problems(spec))
