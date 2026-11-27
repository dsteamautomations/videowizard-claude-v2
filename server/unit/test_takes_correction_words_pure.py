"""SK, 27 Nov 2026 (VW-25: two of twelve takes ended at "no route" because the operator asked for a camera change): the takes page and the
chat form tell the operator what a correction can change and what it cannot, before they write."""
from app import takes as T

OLD_HINT = 'What is wrong with it? Say it in plain words.'


def test_the_hint_says_what_to_write_and_that_the_camera_cannot_change():
    hint = T.W['hint_again']
    assert hint != OLD_HINT and hint.startswith('What is wrong with it?')
    assert 'what you see, where, and what should be there instead' in hint
    assert 'cannot change the camera' in hint and 'zoom' in hint and 'pan' in hint


def test_the_help_has_one_line_on_what_a_correction_can_and_cannot_change():
    lines = [x for x in T.W['help'] if 'cannot change the camera' in x]
    assert len(lines) == 1
    line = lines[0]
    for word in ('an object', 'a surface', 'a colour', 'a size', 'add or remove', 'the action', 'the movement', 'how it ends', 'held still', 'no zoom', 'no pan'):
        assert word in line, word


def test_the_older_help_lines_stay():
    assert any(x.startswith('Nobody has checked these takes') for x in T.W['help'])
    assert any(x.startswith('You are never asked for seconds') for x in T.W['help'])


def test_the_hint_stays_short_enough_for_the_words_box():
    assert len(T.W['hint_again']) <= 240   # two to three lines at phone width
