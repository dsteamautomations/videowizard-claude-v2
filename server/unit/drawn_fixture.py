"""design/117: the helper that turns a diagram shot with a drawing spec into a drawn shot (SK, 27 Oct: a diagram with exact sizes is drawn, so the
spec tests exercise the drawn route). The scene is an uploaded SVG named by its hash (design/117 P2); the hash here is a stand-in."""

ACTIONS = [{'kind': 'appear', 'ids': ['title'], 'at_s': 0}]


def as_drawn(shot):
    return {**shot, 'visual_type': 'drawn', 'depicts': shot.get('depicts') or 'the wall section', 'scene_svg': {'sha256': 'a' * 64, 'actions': list(ACTIONS)}}
