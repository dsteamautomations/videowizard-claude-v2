"""design/113 E6 (SK's answer 6): until the sample is approved, a diagram or build with exact sizes or numbers is warned toward the drawn route, never refused;
the procedure says when a graphic is drawn; AI video for graphics stays off."""
import copy
import json

import pytest
from fractions import Fraction
from pathlib import Path

from app import visual_contract as VC
from test_batch89b_pure import SPEC
from test_visuals_pure import GAPS, plan, shot as pshot

PROC = json.loads((Path(__file__).resolve().parents[1] / 'procedures' / 'v2.json').read_text(encoding='utf-8'))


def kinds(d):
    return {(w.get('shot_id'), w.get('kind')) for w in VC.validate_plan(d, GAPS, Fraction(25))[1]}


def test_a_graphic_with_exact_sizes_or_numbers_is_refused_unless_drawn():
    """SK, 27 Oct, after the sample: the drawn route is the default; the warning became the rule."""
    d = plan([{**pshot('DG1', 0, 100, 'diagram'), 'drawing_spec': copy.deepcopy(SPEC)}, pshot('VS1', 100, 500, 'video'), pshot('VS2', 500, 1000, 'video')])
    with pytest.raises(ValueError, match='DG1 is a diagram with exact sizes or numbers: the drawn route is the default'):
        VC.validate_plan(d, GAPS, Fraction(25))
    d = plan([{**pshot('DG1', 0, 100, 'diagram'), 'claims': ['1 brick in 4 is saved against a solid wall']}, pshot('VS1', 100, 500, 'video'), pshot('VS2', 500, 1000, 'video')])
    with pytest.raises(ValueError, match='the drawn route is the default'):
        VC.validate_plan(d, GAPS, Fraction(25))
    d = plan([{**pshot('DG1', 0, 100, 'diagram'), 'claims': ['the wall breathes']}, pshot('VS1', 100, 500, 'video'), pshot('VS2', 500, 1000, 'video')])
    assert ('DG1', 'route_drawn') not in kinds(d)   # nothing exact: the AI graphic stays


def test_the_procedure_says_when_a_graphic_is_drawn():
    text = json.dumps(PROC, ensure_ascii=False)
    assert 'design/113' in text and 'vw visuals draw' in text and 'scene_drawn' in text and 'the drawn route' in text
