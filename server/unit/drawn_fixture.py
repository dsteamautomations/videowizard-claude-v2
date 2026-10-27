"""design/113: a drawn scene for the tests, and the helper that turns a diagram shot with a drawing spec into a drawn shot (SK, 27 Oct: a diagram with
exact sizes is drawn, so the spec tests exercise the drawn route)."""
import copy

SCENE = {'unit': 'mm', 'width': 400, 'height': 300, 'background': '#F6F1E8',
         'shapes': [{'id': 'outer', 'kind': 'rect', 'x': 40, 'y': 30, 'w': 110, 'h': 240, 'stroke': '#7A2E1D', 'fill': '#C9573A', 'weight': 3, 'dim': 'leaf thickness'},
                    {'id': 'inner', 'kind': 'rect', 'x': 250, 'y': 30, 'w': 110, 'h': 240, 'stroke': '#7A2E1D', 'fill': '#C9573A', 'weight': 3},
                    {'id': 'cavity', 'kind': 'rect', 'x': 150, 'y': 30, 'w': 100, 'h': 240, 'stroke': '#7A2E1D', 'fill': '#F6F1E8', 'weight': 2},
                    {'id': 'air', 'kind': 'arrow', 'x': 200, 'y': 250, 'x2': 200, 'y2': 60, 'stroke': '#2B5D8C', 'weight': 3},
                    {'id': 'title', 'kind': 'text', 'x': 40, 'y': 285, 'text': 'Rat-trap bond, section', 'size_pct': 6, 'bold': True, 'stroke': '#222222'}],
         'actions': [{'kind': 'appear', 'ids': ['outer', 'inner'], 'at_s': 0},
                     {'kind': 'build', 'ids': ['cavity', 'air'], 'word': 'cavity', 'every_s': 0.5},
                     {'kind': 'highlight', 'ids': ['cavity'], 'at_s': 2.5, 'seconds': 1}]}

SCENE_TIMED = {**SCENE, 'actions': [{'kind': 'appear', 'ids': ['outer', 'inner'], 'at_s': 0}, {'kind': 'build', 'ids': ['cavity', 'air'], 'at_s': 1, 'every_s': 0.5}]}   # no word cue: any narration


def as_drawn(shot):
    """A diagram shot with a drawing spec, as the drawn shot the rule now asks for: the scene's one dimension is the spec's leaf thickness."""
    return {**shot, 'visual_type': 'drawn', 'depicts': shot.get('depicts') or 'the wall section', 'scene_drawn': copy.deepcopy(SCENE_TIMED)}
