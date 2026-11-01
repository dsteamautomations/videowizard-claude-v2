"""design/128: the take prompt carries the plan's timeline (T1) and end state (T2); a pronoun that contradicts the one person warns (T3);
VW-12 keeps today's prompt (T4). The nine tests of the note."""
from fractions import Fraction

from app import visuals_stage as VS
from app.video_providers import motion_text

FPS = Fraction(25)
PLAN = {'elements': [{'id': 'engineer', 'name': 'Engineer', 'kind': 'person', 'description': 'An Indian woman in her thirties, a site engineer'},
                     {'id': 'machine', 'name': 'Compression testing machine', 'kind': 'object'},
                     {'id': 'mason', 'name': 'Mason', 'kind': 'person', 'description': 'An Indian man in his forties'}]}


def beat(bid, a, b, action, result):
    return {'id': bid, 'start_frame': a, 'end_frame': b, 'action': action, 'result': result}


G07 = {'id': 'g07-s4-sh1', 'start_frame': 4262, 'end_frame': 4455, 'element_ids': ['engineer', 'machine'],
       'subjects': [{'element_id': 'engineer', 'beats': [beat('e1', 4262, 4380, 'Steps half a pace closer and leans toward the machine', 'She is closer, leaning in'),
                                                         beat('e2', 4380, 4455, 'Straightens and writes the reading on the sheet', 'A line of handwriting on the sheet')]},
                    {'element_id': 'machine', 'beats': [beat('m1', 4262, 4342, 'The load rises; the dial needle climbs', "Hairline cracks open across the brick's face"),
                                                        beat('m2', 4342, 4455, 'The brick fails; a corner breaks away and red dust falls', 'A crushed brick between the platens')]}],
       'changes': [{'beat_id': 'm1', 'what': "Hairline cracks open across the brick's face."}, {'beat_id': 'm2', 'what': 'The brick crushes: a corner breaks off onto the lower platen.'}]}

BASE = {'motion_prompt': 'The engineer watches the test.', 'subject_reconciliation': {}, 'continuity_notes': 'the lab stays the same', 'duration_seconds': 8}


def fields(run_code, shot, duration=8):
    return VS.take_prompt_fields({'code': run_code}, PLAN, shot, FPS, duration)


def test_1_two_beats_give_two_lines_in_seconds_and_time_order():
    shot = {**G07, 'subjects': [G07['subjects'][1]], 'changes': []}
    tl = fields('VW-13', shot)['timeline']
    assert [(t['start_s'], t['end_s']) for t in tl] == [(0.0, 3.2), (3.2, 7.7)]
    text = motion_text({**BASE, **fields('VW-13', shot)})
    assert '0.0–3.2 s: Compression testing machine: The load rises; the dial needle climbs; Hairline cracks open across the brick\'s face.' in text
    assert text.index('0.0–3.2 s') < text.index('3.2–7.7 s')


def test_2_overlapping_beats_of_two_subjects_are_both_listed_in_start_order():
    tl = fields('VW-13', G07)['timeline']
    assert [(t['name'], t['start_s']) for t in tl] == [('Engineer', 0.0), ('Compression testing machine', 0.0), ('Compression testing machine', 3.2), ('Engineer', 4.7)]


def test_3_a_take_longer_than_the_last_beat_holds():
    text = motion_text({**BASE, **fields('VW-13', G07, duration=8)})
    assert 'Then hold until 8 s.' in text
    shot = {**G07, 'end_frame': 4462}   # the beats end at 7.7 s; a take of 8 s on a 8.0 s shot whose beats end earlier still holds
    assert 'Then hold until 8 s.' in motion_text({**BASE, **fields('VW-13', shot, duration=8)})


def test_4_changes_give_the_end_state_line_and_none_give_none():
    text = motion_text({**BASE, **fields('VW-13', G07)})
    assert ("By the end and until the last frame: Hairline cracks open across the brick's face; The brick crushes: a corner breaks off onto the lower platen; "
            'each stays where it is, in plain view.') in text
    assert 'By the end' not in motion_text({**BASE, **fields('VW-13', {**G07, 'changes': []})})


def test_5_a_held_only_shot_gives_todays_prompt_byte_for_byte():
    held = {'id': 'H1', 'start_frame': 0, 'end_frame': 100, 'element_ids': ['mason'], 'subjects': [{'element_id': 'mason', 'beats': []}], 'changes': []}
    assert motion_text({**BASE, **fields('VW-13', held)}) == motion_text(BASE)


def test_6_vw12_gives_todays_prompt_another_run_gets_t1_and_t2():
    assert fields('VW-12', G07) == {} and motion_text({**BASE, **fields('VW-12', G07)}) == motion_text(BASE)
    other = fields('VW-13', G07)
    assert other['prompt_version'] == 2 and other['timeline'] and other['end_state']
    assert motion_text({**BASE, 'timeline': other['timeline'], 'end_state': other['end_state']}) == motion_text(BASE)   # a record without prompt_version is read as 1


def test_7_the_pronoun_warning():
    one_woman = {**G07}
    assert VS.take_prompt_warnings(PLAN, one_woman, 'The engineer writes on his clipboard.')
    assert not VS.take_prompt_warnings(PLAN, one_woman, 'The engineer writes on her clipboard.')
    one_man = {**G07, 'element_ids': ['mason', 'machine']}
    assert VS.take_prompt_warnings(PLAN, one_man, 'The mason sets her brick.') and not VS.take_prompt_warnings(PLAN, one_man, 'The mason sets his brick.')
    two = {**G07, 'element_ids': ['engineer', 'mason', 'machine']}
    assert not VS.take_prompt_warnings(PLAN, two, 'She hands him the trowel.')


def test_8_a_motion_prompt_with_its_own_seconds_warns():
    said = VS.take_prompt_warnings(PLAN, {**G07, 'element_ids': ['machine']}, 'From 0.0-2.0 s the load rises; at 3.5 s the corner breaks.')
    assert any('make them agree' in w for w in said)
    assert not VS.take_prompt_warnings(PLAN, {**G07, 'element_ids': ['machine']}, 'An 8 seconds documentary scene of a brick test.')


def test_9_the_g07_s4_sh1_shape_gives_a_block_like_take_d():
    text = motion_text({**BASE, **fields('VW-13', G07)})
    block = text[text.index('The events happen in this order and at these times:'):]
    for line in ('0.0–4.7 s: Engineer:', '0.0–3.2 s: Compression testing machine:', '3.2–7.7 s: Compression testing machine: The brick fails',
                 '4.7–7.7 s: Engineer: Straightens and writes the reading', 'Then hold until 8 s.', 'By the end and until the last frame:'):
        assert line in block
    assert text.index('The engineer watches the test.') < text.index('The events happen in this order')   # after the motion prompt, as in take D
