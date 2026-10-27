"""design/113 E1 and E5: a drawn shot carries a declarative scene (plain data, no code), its units and labels come from the approved drawing spec, a word
cue names a word of the shot's narration; the plan check refuses what the renderer could not draw honestly."""
import copy
from fractions import Fraction

import pytest

from app import visual_contract as VC, visuals_stage as VS
from test_batch89b_pure import SPEC
from test_visuals_pure import GAPS, plan, shot as pshot

SCENE = {'unit': 'mm', 'width': 400, 'height': 300, 'background': '#F6F1E8',
         'shapes': [{'id': 'outer', 'kind': 'rect', 'x': 40, 'y': 30, 'w': 110, 'h': 240, 'stroke': '#7A2E1D', 'fill': '#C9573A', 'weight': 3, 'dim': 'leaf thickness'},
                    {'id': 'inner', 'kind': 'rect', 'x': 250, 'y': 30, 'w': 110, 'h': 240, 'stroke': '#7A2E1D', 'fill': '#C9573A', 'weight': 3},
                    {'id': 'cavity', 'kind': 'rect', 'x': 150, 'y': 30, 'w': 100, 'h': 240, 'stroke': '#7A2E1D', 'fill': '#F6F1E8', 'weight': 2},
                    {'id': 'air', 'kind': 'arrow', 'x': 200, 'y': 250, 'x2': 200, 'y2': 60, 'stroke': '#2B5D8C', 'weight': 3},
                    {'id': 'title', 'kind': 'text', 'x': 40, 'y': 285, 'text': 'Rat-trap bond, section', 'size_pct': 6, 'bold': True, 'stroke': '#222222'}],
         'actions': [{'kind': 'appear', 'ids': ['outer', 'inner'], 'at_s': 0},
                     {'kind': 'build', 'ids': ['cavity', 'air'], 'word': 'cavity', 'every_s': 0.5},
                     {'kind': 'highlight', 'ids': ['cavity'], 'at_s': 2.5, 'seconds': 1}]}


def drawn(**over):
    sh = {**pshot('DR1', 0, 100, 'diagram'), 'visual_type': 'drawn', 'depicts': 'the wall section', 'narration': 'The cavity between the two leaves holds still air.',
          'drawing_spec': copy.deepcopy(SPEC), 'scene_drawn': copy.deepcopy(SCENE), **over}
    return plan([sh, pshot('VS1', 100, 500, 'video'), pshot('VS2', 500, 1000, 'video')])


def check(d):
    return VC.validate_plan(d, GAPS, Fraction(25))


def scene_of(d):
    return d['gaps'][0]['scenes'][0]['shots'][0]['scene_drawn']


def test_a_drawn_shot_passes_with_its_scene_and_spec_and_counts_as_a_route():
    out, warnings = check(drawn())
    assert out['gaps'][0]['scenes'][0]['shots'][0]['visual_type'] == 'drawn'
    r = VC.routes(out)
    assert r['drawn'] == 1 and r['graphic_seconds'] == 4.0 and r['images_estimated'] == 2   # no picture for the drawn shot; the two video starts
    assert VC.route_of({'visual_type': 'drawn'}) == 'drawn'
    assert VS.split_of([{'visual_type': 'drawn', 'start_frame': 0, 'end_frame': 100}], 25) == [{'route': 'drawn', 'seconds': 4.0, 'shots': 1}]
    assert not [w for w in warnings if w.get('shot_id') == 'DR1' and w.get('kind') in ('spec_missing', 'short_route')]


def test_the_scene_is_plain_data_and_the_spec_is_required():
    d = drawn()
    scene_of(d)['shapes'][0]['script'] = 'import os'
    with pytest.raises(ValueError, match='script'):
        check(d)
    d = drawn()
    scene_of(d)['shapes'][0]['kind'] = 'bezier'
    with pytest.raises(ValueError):
        check(d)
    with pytest.raises(ValueError, match='DR1 is drawn: give scene_drawn'):
        check(drawn(scene_drawn=None))
    with pytest.raises(ValueError, match='DR1 is drawn: it needs a drawing_spec'):
        check(drawn(drawing_spec=None))


def test_geometry_ids_colours_and_sizes_are_checked():
    d = drawn()
    scene_of(d)['shapes'].append({'id': 'outer', 'kind': 'circle', 'x': 1, 'y': 1, 'r': 5})
    with pytest.raises(ValueError, match="shape id 'outer' twice"):
        check(d)
    d = drawn()
    scene_of(d)['shapes'].append({'id': 'c', 'kind': 'circle', 'x': 1, 'y': 1})
    with pytest.raises(ValueError, match="shape 'c' \\(circle\\) needs x, y, r"):
        check(d)
    d = drawn()
    scene_of(d)['shapes'][0]['fill'] = 'red'
    with pytest.raises(ValueError, match="colour 'red' .* #RRGGBB"):
        check(d)
    d = drawn()
    scene_of(d)['shapes'][4]['size_pct'] = 2
    with pytest.raises(ValueError, match='of the frame height: at least 4 %'):
        check(d)
    d = drawn()
    scene_of(d)['shapes'][4]['x'] = 2
    with pytest.raises(ValueError, match='outside the safe area'):
        check(d)
    d = drawn()
    scene_of(d)['shapes'].append({'id': 'g', 'kind': 'group', 'members': ['outer', 'nope']})
    with pytest.raises(ValueError, match="'g' names 'nope', which is not a shape"):
        check(d)


def test_units_come_from_the_spec_and_an_unknown_size_shows_no_figure():
    d = drawn()
    scene_of(d)['shapes'][0]['dim'] = 'leaf width'
    with pytest.raises(ValueError, match="dim 'leaf width' is not a dimension of the spec"):
        check(d)
    d = drawn()
    scene_of(d)['shapes'].append({'id': 'cw', 'kind': 'text', 'x': 160, 'y': 150, 'text': 'cavity width 60 mm', 'size_pct': 4})
    with pytest.raises(ValueError, match='cavity width is unknown: no figure'):
        check(d)
    labels = VC.drawn_labels(drawn()['gaps'][0]['scenes'][0]['shots'][0])
    assert labels == [{'id': 'label-1', 'kind': 'text', 'x': 158, 'y': 30, 'text': 'leaf thickness 110 mm', 'size_pct': 4, 'stroke': '#222222', 'bold': False, 'leader': [150, 30]}]
    d = drawn()
    scene_of(d)['labels'] = [{'dim': 'leaf thickness', 'x': 60, 'y': 280}]   # the planner moves a label; the server still writes it
    moved = VC.drawn_labels(d['gaps'][0]['scenes'][0]['shots'][0])
    assert moved[0]['x'] == 60 and moved[0]['y'] == 280 and moved[0]['text'] == 'leaf thickness 110 mm'
    d = drawn()
    scene_of(d)['labels'] = [{'dim': 'cavity width', 'x': 60, 'y': 280}]
    with pytest.raises(ValueError, match='labels names cavity width, which is unknown'):
        check(d)


def test_actions_are_keyed_to_a_second_inside_the_shot_or_a_word_of_its_narration():
    d = drawn()
    scene_of(d)['actions'][1]['word'] = 'mortar'
    with pytest.raises(ValueError, match="word 'mortar' is not in the narration of DR1"):
        check(d)
    d = drawn()
    scene_of(d)['actions'][2]['at_s'] = 9
    with pytest.raises(ValueError, match='at 9.0 s, past the end of DR1 \\(4.0 s\\)'):
        check(d)
    d = drawn()
    scene_of(d)['actions'][0]['ids'] = ['ghost']
    with pytest.raises(ValueError, match="action 1 names 'ghost', which is not a shape"):
        check(d)
    d = drawn()
    scene_of(d)['actions'][0].pop('at_s')
    with pytest.raises(ValueError, match='action 1: give at_s or word'):
        check(d)
    d = drawn()
    scene_of(d)['actions'].append({'kind': 'move', 'ids': ['air'], 'at_s': 1, 'path': [[200, 250]]})
    with pytest.raises(ValueError, match='move needs a path of two points or more'):
        check(d)
