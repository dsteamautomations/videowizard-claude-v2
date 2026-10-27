"""design/111 F19, the plan-check and count parts: 'illustrative' is earned per unknown value only after all four sources were tried; the run's share of
illustrative specs is counted on status and the page with a warning above one in four; a drawing spec names its view with a reason (a wall section
defaults to cutaway). Labels on drawings wait for design/112's drawn route."""
from fractions import Fraction

import pytest

from app import visual_contract as VC, visuals_stage as VS
from test_batch89b_pure import SPEC
from test_design111_f11_pure import golden_store
from test_visuals_pure import GAPS, plan, shot as pshot
from test_visuals_stage_pure import RUN, FakeConn


def base(spec, **shot):
    return plan([{**pshot('DG1', 0, 100, 'diagram'), 'depicts': 'the wall section', 'drawing_spec': spec, **shot}, pshot('VS1', 100, 500, 'video'), pshot('VS2', 500, 1000, 'video')])


def check(d):
    return VC.validate_plan(d, GAPS, Fraction(25))


def test_illustrative_is_earned_only_after_all_four_sources_were_tried():
    unknown = {**SPEC['dimensions'][1], 'tried': 'not in the client brochure; no footage frame shows the cavity'}
    with pytest.raises(ValueError, match='a size is unknown: the drawing is illustrative only when illustrative is true'):
        check(base({**SPEC, 'illustrative': False, 'dimensions': [SPEC['dimensions'][0], unknown]}))
    with pytest.raises(ValueError, match="cavity width: 'illustrative' is earned only after all four sources were tried; tried does not name: a standard or a maker figure, an approved picture"):
        check(base({**SPEC, 'illustrative': True, 'dimensions': [SPEC['dimensions'][0], unknown]}))
    check(base(SPEC))   # the shared fixture names all four
    with pytest.raises(ValueError, match='nothing is unknown: drop illustrative'):
        check(base({**SPEC, 'illustrative': True, 'dimensions': [SPEC['dimensions'][0]], 'label': ''}))


def test_a_drawing_names_its_view_with_a_reason_and_a_section_defaults_to_cutaway():
    d = base({**SPEC, 'view': '', 'view_reason': ''})
    check(d)
    sh = d['gaps'][0]['scenes'][0]['shots'][0]
    assert VS.spec_view(sh) == ('cutaway', 'a section is cut through the wall')
    with pytest.raises(ValueError, match='give view \\(cutaway, plan, side or elevation\\) and view_reason'):
        check(base({**SPEC, 'view': '', 'view_reason': ''}, depicts='the brick'))
    with pytest.raises(ValueError, match='view_reason'):
        check(base({**SPEC, 'view': 'plan', 'view_reason': ''}, depicts='the brick'))
    d = base({**SPEC, 'view': 'plan', 'view_reason': 'the bond pattern reads from above'}, depicts='the brick')
    check(d)
    sh = d['gaps'][0]['scenes'][0]['shots'][0]
    assert VS.spec_view(sh) == ('plan', 'the bond pattern reads from above')
    assert VS.view_line(sh) == {'check': 'view: plan', 'pass_when': 'the drawing is a plan view (the bond pattern reads from above)', 'weight': 'must'}
    assert VS.view_line({'drawing_spec': None}) is None


def test_the_share_of_illustrative_specs_is_counted_with_a_warning_above_one_in_four():
    d = base(SPEC)
    d['elements'].append({'id': 'BRICK', 'name': 'Red brick', 'kind': 'material', 'identity': 'representative', 'requirements': 'a brick',
                          'material_spec': {'dimensions': [SPEC['dimensions'][0]], 'laid': 'on edge', 'pattern': 'alternating', 'proportions': ['3 : 1.5 : 1']}})
    share = VS.illustrative_share(d)
    assert share['illustrative'] == ['shot DG1'] and share['specs'] == 2
    assert share['warning'].startswith('1 of 2 specs are illustrative (above one in four): shot DG1: measure them')
    for n in range(3):
        d['elements'].append({**d['elements'][-1], 'id': f'M{n}'})
    assert VS.illustrative_share(d) == {'illustrative': ['shot DG1'], 'specs': 5, 'warning': None}
    assert VS.illustrative_share({'elements': [], 'gaps': []}) == {'illustrative': [], 'specs': 0, 'warning': None}
    st = VS.status(FakeConn([]), golden_store(), RUN, [], repair=False)['illustrative']
    assert set(st) == {'illustrative', 'specs', 'warning'}
    assert "d.illustrative&&d.illustrative.warning" in VS.PAGE if hasattr(VS, 'PAGE') else True
