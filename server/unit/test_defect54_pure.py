"""Defect 54 (VW-24, 17 Nov 2026): the set of a place was refused because the plan's own words, placed in the request by the server,
said "the woven mat in the middle of the floor". The placement rule is for a shot's prompt; a reference set's request is not composed."""
import inspect

import pytest

from app import library, visuals_stage as V

ROOM = ("What the picture must represent: The family room under the filler slab ceiling. A wooden table against the wall; "
        "the woven mat in the middle of the floor; a window with a wooden shutter.")


def test_a_shot_prompt_with_a_bare_middle_is_still_refused():
    with pytest.raises(ValueError, match="no landmark and measured distance"):
        library.check_prompt(ROOM)
    with pytest.raises(ValueError, match="says nothing a picture can show"):
        library.check_prompt('The parents as before, at the table.')


def test_a_set_request_from_the_plans_words_is_not_refused_for_its_placing():
    library.check_prompt(ROOM, placed=False)
    library.check_prompt('The parents as before, at the table.', placed=False)


def test_the_other_rules_still_hold_for_a_set_request():
    with pytest.raises(ValueError, match='logo'):
        library.check_prompt('A tin with the maker logo on its side.', placed=False)
    with pytest.raises(ValueError, match='pixel size'):
        library.check_prompt('A picture at 1920x1080.', placed=False)


def test_only_a_set_of_the_rebuilt_round_is_checked_without_the_placing_rules():
    src = inspect.getsource(V.generate_image)
    assert "placed=not (body.get('set') and round_v2(session))" in src
