"""Accurate images (design/194), Area B: the drawing of an AI video shot, made from the guide's own scene description.

The same numbers build the Blender guide and this drawing (app/guide_spec.py is the one source), so the two cannot disagree. The drawing adds what
the box render cannot say: every person drawn with face, chest, back and the working right arm marked; and, where a piece of the set or a prop is
`drawn_as` a thing with an approved drawing set, that thing's own model standing in the box's place. Two views: through the film's camera and from above.
"""
import math

from . import draw3d, guide_spec as G

MM = 0.001
MOST_LABELS = 12


def _c255(c):
    return [int(round(max(0.0, min(1.0, x)) * 255)) for x in c]


def _clear(c):
    """A piece's colour, kept away from the purple that marks a person's back."""
    return c if max(abs(a - b) for a, b in zip(c, draw3d.BACK)) >= 50 else [min(255, c[0] + 80), min(255, c[1] + 80), c[2]]


def _in_front(spec, corners):
    return all(G.project(spec, c)[0] is not None for c in corners)


def _extent(pieces, materials):
    pts = [p for f in draw3d.model({'materials': materials, 'pieces': pieces}) for p in f['pts']]
    lo, hi = [min(p[i] for p in pts) for i in range(3)], [max(p[i] for p in pts) for i in range(3)]
    return lo, hi


def _placed(thing, box_lo, box_hi, turn, prefix):
    """A thing's own model standing where its box stands: scaled to metres, turned, its base centre on the box's base centre.
    Returns (pieces, materials, the placed model's size)."""
    k = MM if thing['unit'] == 'mm' else 1.0
    lo, hi = _extent(thing['pieces'], thing['materials'])
    place = {'scale': k, 'turn': float(turn or 0.0), 'origin': [(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2]],
             'at': [(box_lo[0] + box_hi[0]) / 2, (box_lo[1] + box_hi[1]) / 2, box_lo[2]]}
    mats = {f'{prefix}.{n}': dict(m) for n, m in thing['materials'].items()}
    pieces = [{**p, 'material': f"{prefix}.{p['material']}", 'place': place} for p in draw3d.expanded(thing['pieces'])]
    plo, phi = _extent(pieces, mats)
    return pieces, mats, [phi[i] - plo[i] for i in range(3)]


def description(spec, things=None):
    """The shot as a drawing set (app/draw3d.py), at the moment the take starts. `things`: {element id: its approved drawing set}.
    Returns (description, notes); a note is a plain line for the operator: a piece left out, a thing whose drawn size and box disagree."""
    things, notes, mats, pieces, labels = things or {}, [], {}, [], []

    def add(i, name, colour, lo, hi, piece, drawn_as=None, turn=0.0):
        if not _in_front(spec, G._corners(lo, hi)):
            notes.append(f'{name} ({i}) is partly behind the camera and is left out of the drawing.')
            return
        if drawn_as and drawn_as in things:
            placed, pm, size = _placed(things[drawn_as], lo, hi, turn, i)
            if _in_front(spec, [p for f in draw3d.model({'materials': pm, 'pieces': placed}) for p in f['pts']]):
                box = [hi[k] - lo[k] for k in range(3)]
                off = [k for k in range(3) if abs(size[k] - box[k]) > 0.15 * max(box[k], 1e-6)]
                if off:
                    notes.append(f"{name} ({i}) is drawn {size[0]:.2f} x {size[1]:.2f} x {size[2]:.2f} m from its approved drawings, but its box in the scene is "
                                 f"{box[0]:.2f} x {box[1]:.2f} x {box[2]:.2f} m: make the two agree.")
                mats.update(pm)
                pieces.extend(placed)
                labels.append(([(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, hi[2]], name))
                return
            notes.append(f'{name} ({i}): its own drawing would reach behind the camera, so it is drawn as its box.')
        elif drawn_as:
            notes.append(f'{name} ({i}) is to be drawn as {drawn_as}, which has no approved drawing set: it is drawn as its box.')
        mats[i] = {'colour': _clear(_c255(colour)), 'is': name}
        pieces.append({**piece, 'material': i})
        labels.append(([(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, hi[2]], name))

    for s in spec['set']:
        if s.get('ground'):
            continue
        lo, hi = G.piece_box(s)
        if s.get('shape') == 'cylinder':
            a = 'XYZ'.index(s.get('axis', 'Z'))
            o = [k for k in range(3) if k != a]
            piece = {'shape': 'cylinder', 'axis': s.get('axis', 'Z'), 'centre': [s['centre'][o[0]], s['centre'][o[1]]], 'radius': s['radius'], 'from': s['centre'][a] - s['depth'] / 2, 'to': s['centre'][a] + s['depth'] / 2}
        else:
            piece = {'shape': 'box', 'min': list(lo), 'max': list(hi)}
        add(s['id'], s['name'], s['colour'], lo, hi, piece, s.get('drawn_as'), s.get('turn'))
    for pr in spec.get('props') or []:
        lo, hi = G.prop_box(spec, pr, 0.0)
        add(pr['id'], pr['name'], pr['colour'], lo, hi, {'shape': 'box', 'min': list(lo), 'max': list(hi)}, pr.get('drawn_as'), pr.get('turn'))
    people = []
    for p in spec.get('people') or []:
        if not _in_front(spec, G.person_corners(p, 0.0)):
            notes.append(f"{p['name']} ({p['id']}) is partly behind the camera and is left out of the drawing.")
            continue
        pos, yaw, _ = G.person_at(p, 0.0)
        fx, fy = G._rot(yaw, 0.0, -1.0)
        top = _clear(_c255(p['colour']))
        people.append({'at': list(pos), 'facing': [fx, fy], 'height': p['height'], 'hands': {side: list(G.hand(p, 0.0, side)) for side in (p.get('hands') or {})},
                       'clothes': {'top': top, 'legs': [int(c * 0.55) for c in top]}})
        labels.append(([pos[0], pos[1], pos[2] + p['height']], p['name']))
    cam = spec['camera']
    views = [{'id': 'camera', 'kind': 'through the camera', 'name': "The shot through the film's camera", 'camera': {'position': list(cam['position']), 'aim': list(cam['aim']), 'lens': cam['lens']},
              'shows': 'every person and thing of the shot where it stands; each person with front, back and working arm marked',
              'for': 'which way each person faces, which arm works and what each thing is; exact positions come from Image 1'},
             {'id': 'above', 'kind': 'from above', 'name': 'The place from above', 'toward': [0, 0, 1],
              'shows': 'where every person and thing stands on the ground', 'for': 'how far apart things stand and who faces what'}]
    text = lambda name: name if len(name) <= draw3d.MAX_LABEL else name[:draw3d.MAX_LABEL - 1] + '…'
    d = {'unit': 'm', 'level': 'shot', 'name': 'the shot', 'facts': [], 'materials': mats, 'pieces': pieces, 'people': people, 'views': views,
         'labels': [{'view': v, 'at': at, 'text': text(name)} for v in ('camera', 'above') for at, name in labels[:MOST_LABELS]]
                   + [{'view': 'above', 'at': [cam['position'][0], cam['position'][1], 0.0], 'text': 'the camera stands here'}],
         'dims': []}
    return d, notes
