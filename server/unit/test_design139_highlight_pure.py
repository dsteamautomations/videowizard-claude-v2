"""design/139 R3 (SK, 2 Nov 2026, design/138 A5): the assistant chooses each drawing's highlight colour so it stands out and does not clash; the fixed
yellow is gone for new films (a film from before keeps it). The operator's preferred colours are recorded once, with their words."""
from fractions import Fraction

import pytest

from app import drawn, film as F, visual_contract as VC
from app.errors import Problem
from drawn_fixture import as_drawn
from test_design103_pure import doc_
from test_visuals_pure import GAPS, shot as pshot


def drawn_plan(action):
    d = as_drawn(pshot('DR1', 0, 100, 'diagram'))
    d['scene_svg']['actions'] = [action]
    return doc_(d, *[pshot(f'VS{n}', a, b, 'video') for n, (a, b) in enumerate([(100, 300), (300, 500), (500, 700), (700, 900), (900, 1000)], 1)])


def test_a_highlight_names_its_colour_on_a_new_film():
    with pytest.raises(ValueError, match='highlight_color'):
        VC.validate_plan(drawn_plan({'kind': 'highlight', 'ids': ['title'], 'at_s': 1}), GAPS, Fraction(25))
    VC.validate_plan(drawn_plan({'kind': 'highlight', 'ids': ['title'], 'at_s': 1, 'color': '#1E6FD9'}), GAPS, Fraction(25))
    with pytest.raises(ValueError):
        VC.validate_plan(drawn_plan({'kind': 'highlight', 'ids': ['title'], 'at_s': 1, 'color': 'blue'}), GAPS, Fraction(25))


def test_a_film_from_before_keeps_the_yellow():
    VC.validate_plan(drawn_plan({'kind': 'highlight', 'ids': ['title'], 'at_s': 1}), GAPS, Fraction(25), colour_required=False)
    st = drawn.states([{'kind': 'highlight', 'ids': ['a'], 'at_s': 0}], [0], 25, 2, ['a'], {})
    assert st[0]['a']['hl'] == drawn.HIGHLIGHT == '#FFC43D'


def test_the_named_colour_is_the_one_drawn():
    st = drawn.states([{'kind': 'highlight', 'ids': ['a'], 'at_s': 0, 'color': '#1E6FD9'}], [0], 25, 2, ['a'], {})
    assert st[0]['a']['highlight'] == 1.0 and st[0]['a']['hl'] == '#1E6FD9'
    assert '${s.hl}' in drawn.SET_STATE


def test_the_preferred_colours_are_recorded_as_said():
    assert F.check('colours', 'navy and orange') == {'value': 'navy and orange'}
    assert F.check('colours', 'no preference') == {'value': 'no preference'}
    with pytest.raises(Problem):
        F.check('colours', '')
    assert F.colours({'film': {'colours': {'value': 'navy'}}}) == 'navy' and F.colours({'film': {}}) is None
