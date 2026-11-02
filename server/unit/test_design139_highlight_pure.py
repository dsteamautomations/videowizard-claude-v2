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


def joined(d):   # design/139 R8: a new film's plan names every join
    shots = [sh for sc in d['gaps'][0]['scenes'] for sh in sc['shots']]
    for sh in shots:
        sh['transition_in'] = 'cut'
    shots[-1]['transition_out'] = 'cut'
    return d


def test_a_highlight_names_its_colour_on_a_new_film():
    with pytest.raises(ValueError, match='highlight_color'):
        VC.validate_plan(drawn_plan({'kind': 'highlight', 'ids': ['title'], 'at_s': 1}), GAPS, Fraction(25), new_film=True)
    VC.validate_plan(joined(drawn_plan({'kind': 'highlight', 'ids': ['title'], 'at_s': 1, 'color': '#1E6FD9'})), GAPS, Fraction(25), new_film=True)
    with pytest.raises(ValueError):
        VC.validate_plan(joined(drawn_plan({'kind': 'highlight', 'ids': ['title'], 'at_s': 1, 'color': 'blue'})), GAPS, Fraction(25), new_film=True)


def test_a_film_from_before_keeps_the_yellow():
    VC.validate_plan(drawn_plan({'kind': 'highlight', 'ids': ['title'], 'at_s': 1}), GAPS, Fraction(25), new_film=False)
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


def test_a_new_film_names_every_join():   # design/139 R8 (SK, 2 Nov 2026, design/138 B6)
    d = drawn_plan({'kind': 'appear', 'ids': ['title'], 'at_s': 0})
    with pytest.raises(ValueError, match='name its join'):
        VC.validate_plan(d, GAPS, Fraction(25), new_film=True)
    VC.validate_plan(joined(d), GAPS, Fraction(25), new_film=True)
    d['gaps'][0]['scenes'][0]['shots'][-1].pop('transition_out')
    with pytest.raises(ValueError, match='transition_out'):
        VC.validate_plan(d, GAPS, Fraction(25), new_film=True)
    d = joined(drawn_plan({'kind': 'appear', 'ids': ['title'], 'at_s': 0}))
    d['gaps'][0]['scenes'][0]['shots'][0]['transition_in'] = 'dissolve'
    with pytest.raises(ValueError, match='reason'):
        VC.validate_plan(d, GAPS, Fraction(25), new_film=True)
    VC.validate_plan(drawn_plan({'kind': 'appear', 'ids': ['title'], 'at_s': 0}), GAPS, Fraction(25))   # a film from before: the default joins
