"""Release 1 of 27 Nov 2026, phase 3, part B (SK approved: one style leads, the operator's full words go into every brief).

The operator's words on the motion style ("a mix of restrained and technical") were stored and read by nothing. Now they are in the Motion
style part of every drawing's brief, in the line that confirms the choice and on the page's recorded line. Each test failed first.
Without a database."""
from app import film, page_flow
from test_design221_p1_pure import MRUN

SAID = 'a mix of restrained and technical'


def run(quote, style='restrained'):
    return {**MRUN, 'film': {'motion': {'value': style, 'quote': quote}}}


def test_typed_words_reach_the_motion_style_part_of_the_brief_whole():
    long = SAID + ', ' + 'calm ' * 80 + 'to the end'   # no cut at 300 characters
    for said in (SAID, long):
        part = film.style_part(run(said))
        assert f"In the operator's words: '{said}'. Follow them inside the rules of the style above." in part
    assert part.startswith('Motion style (Restrained)')


def test_a_plain_click_adds_nothing():
    for said in ('Restrained', 'restrained', ' Restrained. ', ''):
        assert "In the operator's words" not in film.style_part(run(said)) and film.style_words(run(said)) == ''
    assert film.style_part(run('Restrained')) == film.style_part({**MRUN, 'film': {'motion': {'value': 'restrained'}}})   # the brief of a film with no words is as it was


def test_the_rules_are_those_of_the_recorded_style_only():
    part, st = film.style_part(run(SAID)), film.styles()
    assert f"Camera flows this style allows on a shot that explains: {', '.join(st['restrained']['camera'])}." in part
    assert st['technical']['text'] not in part
    assert film.camera_allowed(run(SAID), 'fixed')


def test_the_confirming_line_names_the_style_and_the_words():
    assert film.style_line(run(SAID)) == f"Motion style: Restrained. Your words '{SAID}' go to every drawing."
    assert film.style_line(run('Restrained')) == 'Motion style: Restrained.'
    assert film.style_line({**MRUN, 'film': {}}) == ''


def test_the_pages_recorded_line_shows_the_style_and_the_words():
    assert page_flow._motion_line(run(SAID), None)['title'] == f"How things move in this film: Restrained. Your words '{SAID}' go to every drawing."
    assert page_flow._motion_line(run('Restrained'), None)['title'] == 'How things move in this film: Restrained'


def test_a_film_from_before_keeps_the_older_fixed_style():
    assert film.style_part(MRUN).startswith('Motion style (the older fixed style') and film.style_words(MRUN) == ''
