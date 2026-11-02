"""design/139 R13 (SK, 2 Nov 2026, design/138 C16, Q4): the drawing font is asked once with Noto Sans as the reference, from five free fonts held on the
server (renders have no network); both drawing routes use it; a film from before keeps Noto Sans."""
import pytest

from app import drawn, film as F, visuals_stage as VS
from app.errors import Problem
from PIL import ImageFont


def test_every_offered_font_is_a_readable_file_of_its_family():
    for family, file in F.FONTS.items():
        assert ImageFont.truetype(str(drawn.FONTS / file), 12).getname()[0] == family


def test_the_font_choice_is_checked():
    assert F.check('font', 'Inter') == {'value': 'Inter'}
    with pytest.raises(Problem) as e:
        F.check('font', 'Comic Sans')
    assert 'Noto Sans recommended' in e.value.message


def test_the_recorded_font_reaches_the_motion_route_beside_noto_sans():
    files, names = VS._motion_fonts(None, {}, {'film': {'font': {'value': 'Montserrat'}}})
    assert set(files) == {'NotoSans-Variable.ttf', 'Montserrat-Variable.ttf'} and names == ['Noto Sans', 'Montserrat']
    assert VS._motion_fonts(None, {}, {'film': None}) == ({'NotoSans-Variable.ttf': drawn.font_file().read_bytes()}, ['Noto Sans'])
    assert VS.film_font_files({'film': {'font': {'value': 'Lato'}}}) == {'Lato-Regular.ttf': 'server'}


def test_a_new_film_asks_the_font_before_drawing():
    with pytest.raises(ValueError, match='vw font'):
        VS.need_font({'film': {}})
    VS.need_font({'film': None})
    VS.need_font({'film': {'font': {'value': 'Noto Sans'}}})
    VS.need_font({'film': {}}, {'font': {'name': 'brand.ttf', 'key': 'k'}})   # a brand font given with `vw visuals font`
