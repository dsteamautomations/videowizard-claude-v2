"""Defect 35 (row 31, Revathi, 28 Oct): the spec_missing warning now reads production_method (a label, a title, a chart or a timeline needs no spec), and the
course rule A5 leaves a material's sizes to its material_spec (design/111 F10) instead of asking for a size list F10 refuses."""
from fractions import Fraction

from app import visual_contract as VC
from test_design111_f10_pure import BRICK
from test_visuals_pure import GAPS, plan, shot as pshot


def kinds(d):
    return {(w.get('shot_id') or w.get('element_id'), w.get('kind')) for w in VC.validate_plan(d, GAPS, Fraction(25))[1]}


def test_a_label_a_title_a_chart_or_a_timeline_needs_no_drawing_spec():
    d = plan([pshot('DG1', 0, 100, 'diagram'), pshot('VS1', 100, 500, 'video'), pshot('VS2', 500, 1000, 'video')])
    assert ('DG1', 'spec_missing') in kinds(d)   # a drawing of a real object with no spec: warned as before
    for words in ('Title card: the film\'s name over a faded frame, a label, no drawing', 'a chart of three storeys', 'a timeline of the seven days of curing'):
        d['gaps'][0]['scenes'][0]['shots'][0]['production_method'] = words
        assert ('DG1', 'spec_missing') not in kinds(d), words
    d['gaps'][0]['scenes'][0]['shots'][0]['production_method'] = 'a painted section of the wall'
    assert ('DG1', 'spec_missing') in kinds(d)
    d = plan([{**pshot('DG1', 0, 100, 'diagram'), 'graphic_kind': 'title'}, pshot('VS1', 100, 500, 'video'), pshot('VS2', 500, 1000, 'video')])
    assert ('DG1', 'spec_missing') not in kinds(d)   # the kind says it too


def test_a_material_with_its_spec_is_not_asked_for_a_size_list():
    d = plan([pshot('VS1', 0, 500, 'video'), pshot('VS2', 500, 1000, 'video')])
    d['elements'].append(dict(BRICK))
    assert ('BRICK', 'element_size_missing') not in kinds(d)
    d['elements'][-1] = {'id': 'PAN', 'name': 'Mortar pan', 'kind': 'object', 'identity': 'representative', 'requirements': 'a steel pan'}
    assert ('PAN', 'element_size_missing') in kinds(d)   # an object without a size: still asked, as before
