"""Hotfix, 11 Nov 2026 (VW-19, SK: "Hotfix now"): a reference set of an element with a material spec was refused every time,
because the material-words check (design/111 F10) read the whole kept prompt and the server's own kept preamble says
"the one most typical of the place I describe". The check reads the writer's words only: for a kept set, the subject block."""
import pytest

from app import library as L
from app import visuals_stage as VS

SUBJECT = 'A newly finished rat-trap bond brick wall about chest high: red burnt clay bricks laid on edge. Nobody in the picture.'


def test_the_kept_preamble_alone_trips_the_material_check():
    with pytest.raises(ValueError, match='relative'):   # the clash this hotfix removes: the server's own words
        L.check_material_prompt(VS.KEPT_PREAMBLE)


def test_a_kept_set_is_checked_on_its_subject_block_not_on_the_servers_preamble():
    whole = VS.KEPT_PREAMBLE + '\n\n' + SUBJECT
    L.check_material_prompt(VS.material_words(whole, SUBJECT, True))   # passes: the subject has no relative size word


def test_a_relative_word_in_the_subject_block_is_still_refused_on_a_set():
    bad = 'A wall of typical red bricks. Nobody in the picture.'
    with pytest.raises(ValueError, match='typical'):
        L.check_material_prompt(VS.material_words(VS.KEPT_PREAMBLE + '\n\n' + bad, bad, True))


def test_any_other_picture_is_checked_on_the_writers_prompt_as_before():
    assert VS.material_words('the writer prompt', 'ignored', False) == 'the writer prompt'
    with pytest.raises(ValueError, match='relative'):
        L.check_material_prompt(VS.material_words('A wall of short bricks.', '', False))
