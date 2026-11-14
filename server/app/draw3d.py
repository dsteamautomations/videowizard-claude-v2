"""Accurate images (design/200): a drawing set is data, and the server draws it.

A helper writes ONE description of a thing or a place: its facts, its solid pieces in real units, its people, and the views wanted.
Every view is that same model seen from one place, with hidden surfaces worked out here, so the views cannot disagree; the helper never
runs code on the server. Each view gives two sheets: one for the operator (title, what the view is, labels, sizes) and one for the
image model (no text at all, one colour for one material).

A drawn person shows front and back (SK, 14 Nov 2026): the face and the chest are pale panels with dark marks, the back of the head and
trunk is one colour kept for backs alone, and the right arm, the arm that works, has its own colour.

Standard library only. Z is up."""
import heapq
import math

INK = '#2b2b2b'
FRONT, MARK, BACK, RIGHT_ARM = (250, 238, 205), (20, 20, 20), (120, 60, 170), (240, 140, 30)
SKIN, HAIR, TOP, LEGS = (150, 104, 76), (30, 28, 28), (70, 140, 110), (70, 70, 76)
KINDS = {   # the plain words a view is called by, and how the image model is told to read it
    'from above': 'seen straight down from above; it shows where things are and how far apart, and is not a view to reproduce',
    'square on': 'seen square on, flat, with no perspective',
    'cut through': 'a cut through it, showing what is inside',
    'pulled apart': 'the parts pulled apart, showing how they fit together',
    'three-quarter': 'seen at an angle from above, drawn flat with no perspective',
    'one unit enlarged': 'one repeating piece drawn large, with its sizes',
    'side by side': 'two things or two states drawn side by side for comparison',
    'through the camera': "seen through the film's camera with a real lens; this is the exact frame",
}
MIN_VIEWS = {'engineered': 4, 'composition': 3, 'form': 2, 'shot': 2}   # a shot's drawing: through the camera and from above
MAX_VIEWS, MAX_PIECES, MAX_LABEL, MAX_LINE = 6, 4000, 60, 120
MAX_REPEATS = 3   # a piece may be repeated along up to three directions: a row, rows of it, layers of those
AXES = {'X': 0, 'Y': 1, 'Z': 2}
NAMES = {'white': (245, 245, 240), 'black': (25, 25, 25), 'dark grey': (70, 70, 72), 'grey': (150, 150, 148), 'light grey': (195, 195, 198), 'red': (200, 60, 50),
         'brick red': (200, 100, 62), 'orange': (225, 130, 40), 'yellow': (220, 185, 50), 'green': (70, 135, 70), 'grey-green': (120, 140, 130), 'blue': (65, 100, 150),
         'purple': (120, 60, 170), 'brown': (130, 92, 62), 'tan': (225, 200, 155), 'pink': (220, 150, 170)}


def sub(a, b): return (a[0] - b[0], a[1] - b[1], a[2] - b[2])
def add(a, b): return (a[0] + b[0], a[1] + b[1], a[2] + b[2])
def mul(a, k): return (a[0] * k, a[1] * k, a[2] * k)
def dot(a, b): return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
def cross(a, b): return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def unit(a):
    n = math.sqrt(dot(a, a)) or 1.0
    return (a[0] / n, a[1] / n, a[2] / n)


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def _vec(v, n=3):
    return isinstance(v, (list, tuple)) and len(v) == n and all(_num(x) for x in v)


def _rgb(v):
    return _vec(v) and all(float(x).is_integer() and 0 <= x <= 255 for x in v)


def colour_name(c):
    return min(NAMES, key=lambda n: sum((a - b) ** 2 for a, b in zip(NAMES[n], c)))


def esc(s):
    return str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


# ---------- is the description sound? every refusal in plain words ----------

def _piece_problems(i, p, materials):
    what, out = f'piece {i + 1}', []
    if not isinstance(p, dict):
        return [f'{what}: a piece is {{"shape": "box" | "prism" | "cylinder", ...}}.']
    if p.get('material') not in materials:
        out.append(f"{what}: its material {p.get('material')!r} is not in the list of materials.")
    if 'colour' in p and not _rgb(p['colour']):
        out.append(f'{what}: its marking colour is three whole numbers from 0 to 255.')
    pl = p.get('place')
    if pl is not None and not (isinstance(pl, dict) and _num(pl.get('scale', 1.0)) and pl.get('scale', 1.0) > 0 and _num(pl.get('turn', 0.0))
                               and _vec(pl.get('origin', [0, 0, 0])) and _vec(pl.get('at', [0, 0, 0]))):
        out.append(f'{what}: "place" gives scale (greater than nothing), turn in degrees, and "origin" and "at" as three numbers each.')
    shape = p.get('shape')
    if shape == 'box':
        if not (_vec(p.get('min')) and _vec(p.get('max'))):
            out.append(f'{what}: a box gives "min" and "max" as three numbers each; every number is a real, finite number.')
        elif any(b - a <= 0 for a, b in zip(p['min'], p['max'])):
            out.append(f'{what}: the box has no thickness along one side (max is not greater than min).')
    elif shape == 'prism':
        pts = p.get('outline')
        if p.get('axis') not in AXES or not (_num(p.get('from')) and _num(p.get('to'))) or not (isinstance(pts, list) and len(pts) >= 3 and all(_vec(q, 2) for q in pts)):
            out.append(f'{what}: a prism gives "axis" (X, Y or Z), "from", "to" and an "outline" of at least three points of two numbers; every number is a real, finite number.')
        elif p['to'] - p['from'] <= 0:
            out.append(f'{what}: the prism has no thickness ("to" is not greater than "from").')
    elif shape == 'cylinder':
        if p.get('axis') not in AXES or not (_vec(p.get('centre'), 2) and _num(p.get('radius')) and _num(p.get('from')) and _num(p.get('to'))) or ('radius_to' in p and not _num(p['radius_to'])):
            out.append(f'{what}: a cylinder gives "axis" (X, Y or Z), "centre" (two numbers), "radius", "from" and "to"; every number is a real, finite number.')
        elif p['radius'] <= 0 or p['to'] - p['from'] <= 0:
            out.append(f'{what}: the cylinder has no thickness (radius and length must be greater than nothing).')
    else:
        out.append(f'{what}: its shape is "box", "prism" or "cylinder", not {shape!r}.')
    return out


def _shift(p, v):
    """A piece moved by v."""
    a = AXES.get(p.get('axis'), 0)
    o = [i for i in range(3) if i != a]
    if p['shape'] == 'box':
        return {**p, 'min': [p['min'][i] + v[i] for i in range(3)], 'max': [p['max'][i] + v[i] for i in range(3)]}
    if p['shape'] == 'prism':
        return {**p, 'from': p['from'] + v[a], 'to': p['to'] + v[a], 'outline': [[q[0] + v[o[0]], q[1] + v[o[1]]] for q in p['outline']]}
    return {**p, 'from': p['from'] + v[a], 'to': p['to'] + v[a], 'centre': [p['centre'][0] + v[o[0]], p['centre'][1] + v[o[1]]]}


def _repeats_ok(p):
    r = p.get('repeat')
    return r is None or (isinstance(r, list) and 1 <= len(r) <= MAX_REPEATS and all(isinstance(x, dict) and _vec(x.get('step')) and any(x['step']) and isinstance(x.get('count'), int)
                                                                                    and not isinstance(x.get('count'), bool) and 1 <= x['count'] <= MAX_PIECES for x in r))


def _count(p):
    n = 1
    for x in p.get('repeat') or []:
        n *= x['count']
    return n


def expanded(pieces):
    """Every piece with its repeats written out: "repeat": [{"step": [dx, dy, dz], "count": n}, …] makes n copies along each step, one inside the other.
    So a row of equal things, rows of it and layers of those are a few lines of data, each size written once."""
    out = []
    for p in pieces:
        copies = [{k: v for k, v in p.items() if k != 'repeat'}]
        for x in p.get('repeat') or []:
            copies = [_shift(c, [x['step'][i] * k for i in range(3)]) for k in range(x['count']) for c in copies]
        out += copies
    return out


def problems(d):
    """Everything wrong with a drawing set, in plain words; an empty list means it can be drawn."""
    if not isinstance(d, dict):
        return ['A drawing set is one description: unit, level, facts, materials, pieces, views.']
    out = []
    if d.get('unit') not in ('mm', 'm'):
        out.append('The unit of the drawing set is "mm" (a thing) or "m" (a place).')
    level = d.get('level')
    if level not in MIN_VIEWS:
        out.append('The level is "engineered", "composition" or "form" for a thing, "shot" for a shot.')
    for i, f in enumerate(d.get('facts') or []):
        if not (isinstance(f, dict) and str(f.get('what') or '').strip() and (str(f.get('source') or '').strip() or f.get('assumed') is True)):
            out.append(f'fact {i + 1}: a fact says what it is, and gives its source or is marked "assumed": true.')
    materials = d.get('materials') if isinstance(d.get('materials'), dict) else {}
    for name, m in materials.items():
        if not (isinstance(m, dict) and _rgb(m.get('colour')) and str(m.get('is') or '').strip()):
            out.append(f'material {name}: it gives a colour (three whole numbers from 0 to 255) and "is", what the material is in plain words.')
        elif max(abs(a - b) for a, b in zip(m['colour'], BACK)) < 50:
            out.append(f"material {name}: its colour is the purple kept for a person's back alone; choose another.")
    pieces, people = d.get('pieces'), d.get('people') or []
    if not isinstance(pieces, list) or (not pieces and not people):
        out.append('The drawing set has no pieces: give at least one solid piece or one person.')
        pieces = []
    bad = [i + 1 for i, p in enumerate(pieces) if isinstance(p, dict) and not _repeats_ok(p)]
    if bad:
        out.append(f"piece {bad[0]}: \"repeat\" is a list of one to {MAX_REPEATS} entries, each {{\"step\": [dx, dy, dz], \"count\": n}} with a step that moves and a whole count of at least 1.")
        pieces = []
    total = sum(_count(p) for p in pieces if isinstance(p, dict))
    if total > MAX_PIECES:
        out.append(f'The drawing set has {total} pieces with its repeats written out; the most is {MAX_PIECES}. Draw repeated pieces only where a camera can see them.')
        pieces = []
    for i, p in enumerate(pieces):
        out += _piece_problems(i, p, materials)
    for i, p in enumerate(people):
        hands = p.get('hands') or {} if isinstance(p, dict) else None
        if hands is None or not (_vec(p.get('at')) and _vec(p.get('facing'), 2) and any(p['facing']) and _num(p.get('height')) and p['height'] > 0
                                 and isinstance(hands, dict) and set(hands) <= {'left', 'right'} and all(_vec(h) for h in hands.values())):
            out.append(f'person {i + 1}: a person gives "at" (three numbers), "facing" (two numbers, the way the chest points), "height", and may give where each hand is.')
    views = d.get('views') if isinstance(d.get('views'), list) else []
    if level in MIN_VIEWS and len(views) < MIN_VIEWS[level]:
        out.append(f'A drawing set at the {level} level needs at least {MIN_VIEWS[level]} views; this one has {len(views)}.')
    if len(views) > MAX_VIEWS:
        out.append(f'A drawing set has at most {MAX_VIEWS} views; this one has {len(views)}.')
    ids = []
    for i, v in enumerate(views):
        what = f"view {v.get('id') or i + 1}" if isinstance(v, dict) else f'view {i + 1}'
        if not isinstance(v, dict) or not str(v.get('id') or '').strip() or v.get('id') in ids:
            out.append(f'{what}: every view has its own short id.')
            continue
        ids.append(v['id'])
        if v.get('kind') not in KINDS:
            out.append(f"{what}: its kind is one of: {', '.join(KINDS)}.")
        for key, words in (('name', 'its name'), ('shows', 'what it shows'), ('for', 'what it is for')):
            text = str(v.get(key) or '').strip()
            if not text or len(text) > MAX_LINE:
                out.append(f'{what}: say {words}, in one line of at most {MAX_LINE} letters.')
        cam = v.get('camera')
        if (v.get('kind') == 'through the camera') != (cam is not None) or (cam is None) == (v.get('toward') is None):
            out.append(f'{what}: a view through the camera gives "camera" (position, aim, lens); every other view gives "toward", the direction from the thing to the eye.')
        elif cam is not None and not (isinstance(cam, dict) and _vec(cam.get('position')) and _vec(cam.get('aim')) and _num(cam.get('lens')) and cam['lens'] > 0 and list(cam['position']) != list(cam['aim'])):
            out.append(f'{what}: the camera gives "position" and "aim" (three numbers each, not the same point) and "lens" in millimetres.')
        elif cam is None and not (_vec(v.get('toward')) and any(v['toward'])):
            out.append(f'{what}: "toward" is three numbers, not all nothing.')
    for kind, rows in (('label', d.get('labels') or []), ('size', d.get('dims') or [])):
        for i, r in enumerate(rows):
            if not isinstance(r, dict) or r.get('view') not in ids:
                out.append(f"{kind} {i + 1}: it belongs to view {r.get('view') if isinstance(r, dict) else '?'}, which is not among the views.")
            elif not str(r.get('text') or '').strip() or len(str(r['text'])) > MAX_LABEL:
                out.append(f'{kind} {i + 1}: its words are short, at most {MAX_LABEL} letters.')
            elif not all(_vec(r.get(k)) for k in (('at',) if kind == 'label' else ('from', 'to'))):
                out.append(f"{kind} {i + 1}: {'\"at\" is' if kind == 'label' else '\"from\" and \"to\" are'} three numbers, a point of the model.")
    if out:
        return out
    m = model(d)
    for v in views:
        if v.get('camera') and any(eye(d, v).depth(p) <= 1e-6 for f in m for p in f['pts']):
            out.append(f"view {v['id']}: part of the model is behind the camera; move the camera back or aim it at the model.")
    return out


# ---------- the model ----------

def _solid(faces, verts, idx, colour, mark=None):
    n = len(verts)
    c = (sum(v[0] for v in verts) / n, sum(v[1] for v in verts) / n, sum(v[2] for v in verts) / n)
    for f in idx:
        p = [verts[i] for i in f]
        nrm = unit(cross(sub(p[1], p[0]), sub(p[2], p[0])))
        if dot(nrm, sub(p[0], c)) < 0:
            nrm = (-nrm[0], -nrm[1], -nrm[2])
        faces.append({'pts': p, 'n': nrm, 'colour': tuple(colour), 'mark': tuple(mark) if mark else tuple(colour)})


def _prism(faces, axis, a0, a1, outline, colour, mark=None, turn=None, a1_outline=None):
    o = [i for i in range(3) if i != axis]

    def pt(a, q):
        v = [0.0, 0.0, 0.0]
        v[axis], v[o[0]], v[o[1]] = a, q[0], q[1]
        return turn(tuple(v)) if turn else tuple(v)
    n = len(outline)
    verts = [pt(a0, q) for q in outline] + [pt(a1, q) for q in (a1_outline or outline)]
    _solid(faces, verts, [list(range(n)), list(range(n, 2 * n))] + [[i, (i + 1) % n, n + (i + 1) % n, n + i] for i in range(n)], colour, mark)


def _box(faces, lo, hi, colour, mark=None, turn=None):
    _prism(faces, 2, lo[2], hi[2], [(lo[0], lo[1]), (hi[0], lo[1]), (hi[0], hi[1]), (lo[0], hi[1])], colour, mark, turn)


def _bar(faces, p0, p1, w, colour):
    """A straight square bar from one point to another: an arm."""
    d = unit(sub(p1, p0))
    a = unit(cross(d, (0, 0, 1))) if abs(d[2]) < 0.99 else (1.0, 0.0, 0.0)
    b = cross(d, a)
    corners = [add(mul(a, sa * w / 2), mul(b, sb * w / 2)) for sa, sb in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    verts = [add(p0, c) for c in corners] + [add(p1, c) for c in corners]
    _solid(faces, verts, [[0, 1, 2, 3], [4, 5, 6, 7]] + [[i, (i + 1) % 4, 4 + (i + 1) % 4, 4 + i] for i in range(4)], colour)


def shoulder_of(p, side):
    """Where a drawn person's shoulder is; the right side is the chest's direction turned a quarter turn to the right."""
    h, f = p['height'], unit((p['facing'][0], p['facing'][1], 0.0))
    r = (f[1], -f[0], 0.0)
    k = 0.147 * h * (1 if side == 'right' else -1)
    return (p['at'][0] + r[0] * k, p['at'][1] + r[1] * k, p['at'][2] + 0.80 * h)


def _person(faces, p):
    h, at = p['height'], p['at']
    f = unit((p['facing'][0], p['facing'][1], 0.0))
    r = (f[1], -f[0], 0.0)
    turn = lambda q: (at[0] + r[0] * q[0] + f[0] * q[1], at[1] + r[1] * q[0] + f[1] * q[1], at[2] + q[2])   # local: to his right, forward, up
    top, legs = (p.get('clothes') or {}).get('top', TOP), (p.get('clothes') or {}).get('legs', LEGS)
    box = lambda x0, x1, y0, y1, z0, z1, c: _box(faces, (x0 * h, y0 * h, z0 * h), (x1 * h, y1 * h, z1 * h), c, turn=turn)
    for sx in (-1, 1):
        box(sx * 0.09 - 0.033, sx * 0.09 + 0.033, -0.035, 0.035, 0.0, 0.49, legs)
    box(-0.12, 0.12, -0.06, 0.06, 0.49, 0.83, top)                      # trunk
    box(-0.12, 0.12, 0.06, 0.067, 0.49, 0.83, FRONT)                    # chest
    box(-0.017, 0.017, 0.067, 0.072, 0.54, 0.82, MARK)                  # the stripe down the chest
    box(-0.12, 0.12, -0.067, -0.06, 0.49, 0.83, BACK)                   # back
    box(-0.033, 0.033, -0.033, 0.033, 0.83, 0.86, SKIN)                 # neck
    box(-0.056, 0.056, -0.06, 0.06, 0.86, 0.975, SKIN)                  # head
    box(-0.056, 0.056, 0.06, 0.065, 0.86, 0.975, FRONT)                 # face
    for ex in (-0.03, 0.013):
        box(ex, ex + 0.017, 0.065, 0.069, 0.925, 0.942, MARK)           # eyes
    box(-0.018, 0.018, 0.065, 0.069, 0.885, 0.894, MARK)                # mouth
    box(-0.056, 0.056, -0.065, -0.06, 0.86, 0.975, BACK)                # back of the head
    box(-0.058, 0.058, -0.065, 0.06, 0.975, 1.0, HAIR)
    for side in ('right', 'left'):
        s = shoulder_of(p, side)
        hand = tuple((p.get('hands') or {}).get(side) or (s[0], s[1], s[2] - 0.34 * h))
        elbow = (s[0] + (hand[0] - s[0]) * 0.25, s[1] + (hand[1] - s[1]) * 0.25, min(s[2], hand[2]) - 0.02 * h if hand[2] < s[2] - 0.2 * h else (s[2] + hand[2]) / 2 - 0.1 * h)
        colour = RIGHT_ARM if side == 'right' else SKIN
        if math.dist(elbow, hand) < 1e-6 or math.dist(s, elbow) < 1e-6:
            _bar(faces, s, hand, 0.05 * h, colour)
        else:
            _bar(faces, s, elbow, 0.05 * h, colour)
            _bar(faces, elbow, hand, 0.05 * h, colour)


def _placer(pl):
    """The function that stands a piece in its place: scaled about `origin`, turned about the upright axis, with `origin` landing on `at`."""
    if not pl:
        return None
    k, th, o, a = pl.get('scale', 1.0), math.radians(pl.get('turn', 0.0)), pl.get('origin', (0, 0, 0)), pl.get('at', (0, 0, 0))
    c, s = math.cos(th), math.sin(th)
    return lambda p: (a[0] + k * ((p[0] - o[0]) * c - (p[1] - o[1]) * s), a[1] + k * ((p[0] - o[0]) * s + (p[1] - o[1]) * c), a[2] + k * (p[2] - o[2]))


def model(d):
    """Every face of the model: its corner points, the way it looks out, its material's colour and the operator's marking colour."""
    faces, mats = [], d['materials']
    for p in expanded(d.get('pieces') or []):
        colour, mark, turn = mats[p['material']]['colour'], p.get('colour'), _placer(p.get('place'))
        if p['shape'] == 'box':
            _box(faces, p['min'], p['max'], colour, mark, turn)
        elif p['shape'] == 'prism':
            _prism(faces, AXES[p['axis']], p['from'], p['to'], p['outline'], colour, mark, turn)
        else:
            ring = lambda rr: [(p['centre'][0] + rr * math.cos(2 * math.pi * i / 16), p['centre'][1] + rr * math.sin(2 * math.pi * i / 16)) for i in range(16)]
            _prism(faces, AXES[p['axis']], p['from'], p['to'], ring(p['radius']), colour, mark, turn, a1_outline=ring(p.get('radius_to', p['radius'])))
    for p in d.get('people') or []:
        _person(faces, p)
    return faces


# ---------- where it is seen from ----------

class Eye:
    def __init__(self, toward=None, camera=None, aspect=16 / 9):
        self.flat = camera is None
        if self.flat:
            self.v = unit(tuple(toward))
        else:
            self.pos = tuple(camera['position'])
            self.v, self.k, self.aspect = unit(sub(self.pos, tuple(camera['aim']))), camera['lens'] / 36.0, aspect
        self.r = unit(cross((0, 0, 1), self.v)) if abs(self.v[2]) < 0.999 else (1.0, 0.0, 0.0)
        self.u = cross(self.v, self.r)

    def sees(self, f):
        return dot(f['n'], self.v if self.flat else sub(self.pos, f['pts'][0])) > 1e-9

    def depth(self, p):
        """How far in front of the eye a point is (flat views: along the line of sight, from the origin)."""
        return -dot(p, self.v) if self.flat else -dot(sub(p, self.pos), self.v)

    def page(self, p):
        """Flat: model units on the page. Camera: 0..1 across and 0..1 down the frame."""
        if self.flat:
            return (dot(p, self.r), -dot(p, self.u))
        q = sub(p, self.pos)
        z = max(-dot(q, self.v), 1e-9)
        return (0.5 + dot(q, self.r) / z * self.k, 0.5 - dot(q, self.u) / z * self.k * self.aspect)


def eye(d, view):
    return Eye(toward=view.get('toward'), camera=view.get('camera'))


def _overlap(a, b, eps):
    for poly in (a, b):
        n = len(poly)
        for i in range(n):
            ex, ey = poly[(i + 1) % n][0] - poly[i][0], poly[(i + 1) % n][1] - poly[i][1]
            m = math.hypot(ex, ey)
            if m < 1e-12:
                continue
            ax, ay = -ey / m, ex / m
            pa, pb = [q[0] * ax + q[1] * ay for q in a], [q[0] * ax + q[1] * ay for q in b]
            if min(pa) >= max(pb) - eps or min(pb) >= max(pa) - eps:
                return False
    return True


def visible(faces, e):
    """The faces the eye sees, far to near: each with its outline on the page ('xy'), its depth and its two fills."""
    fs = [dict(f) for f in faces if e.sees(f)]
    if not fs:
        return []
    for f in fs:
        f['xy'] = [e.page(p) for p in f['pts']]
        xs, ys = [q[0] for q in f['xy']], [q[1] for q in f['xy']]
        f['bb'] = (min(xs), min(ys), max(xs), max(ys))
        f['depth'] = sum(e.depth(p) for p in f['pts']) / len(f['pts'])
    n = len(fs)
    eps = (max(f['bb'][2] for f in fs) - min(f['bb'][0] for f in fs) or 1.0) * 2e-5
    tol = max(max(abs(c) for f in fs for p in f['pts'] for c in p), 1.0) * 1e-7
    after, waits = [[] for _ in range(n)], [0] * n
    by_x = sorted(range(n), key=lambda i: fs[i]['bb'][0])
    for k, i in enumerate(by_x):
        A = fs[i]
        for j in by_x[k + 1:]:
            B = fs[j]
            if B['bb'][0] >= A['bb'][2] - eps:
                break
            if B['bb'][1] >= A['bb'][3] - eps or A['bb'][1] >= B['bb'][3] - eps or not _overlap(A['xy'], B['xy'], eps):
                continue
            a_behind = all(dot(sub(p, B['pts'][0]), B['n']) <= tol for p in A['pts']) or all(dot(sub(q, A['pts'][0]), A['n']) >= -tol for q in B['pts'])
            b_behind = all(dot(sub(q, A['pts'][0]), A['n']) <= tol for q in B['pts']) or all(dot(sub(p, B['pts'][0]), B['n']) >= -tol for p in A['pts'])
            if a_behind and not b_behind:
                after[i].append(j); waits[j] += 1
            elif b_behind and not a_behind:
                after[j].append(i); waits[i] += 1
    heap = [(-fs[i]['depth'], i) for i in range(n) if waits[i] == 0]
    heapq.heapify(heap)
    order, done = [], [False] * n
    while len(order) < n:
        if heap:
            _, i = heapq.heappop(heap)
            if done[i]:
                continue
        else:   # a ring of faces each in front of the next: take the farthest that is left
            i = max((i for i in range(n) if not done[i]), key=lambda i: fs[i]['depth'])
        done[i] = True
        order.append(i)
        for j in after[i]:
            waits[j] -= 1
            if waits[j] == 0 and not done[j]:
                heapq.heappush(heap, (-fs[j]['depth'], j))
    light = unit((-0.45, -0.7, 1.0))
    out = []
    for i in order:
        f = fs[i]
        k = 0.8 + 0.2 * max(0.0, dot(f['n'], light))
        shade = lambda c: '#%02x%02x%02x' % tuple(max(0, min(255, int(x * k))) for x in c)
        out.append({'pts': f['pts'], 'xy': f['xy'], 'depth': f['depth'], 'fill': shade(f['colour']), 'fill_marked': shade(f['mark'])})
    return out


# ---------- the sheets ----------

DRAW_W, DRAW_H, LEFT, TOP_Y, LABEL_X, SHEET_W = 720.0, 560.0, 30.0, 96.0, 790.0, 1100.0
FRAME_W = 800.0


def _layout(d, view):
    """The visible faces and the function from a model point to the operator's sheet, with the drawing's size on that sheet."""
    e = eye(d, view)
    faces = visible(model(d), e)
    if e.flat:
        xs, ys = [q[0] for f in faces for q in f['xy']], [q[1] for f in faces for q in f['xy']]
        x0, y0, w, h = min(xs), min(ys), (max(xs) - min(xs)) or 1.0, (max(ys) - min(ys)) or 1.0
        s = min(DRAW_W / w, DRAW_H / h)
        to = lambda q: (LEFT + (q[0] - x0) * s, TOP_Y + (q[1] - y0) * s)
        return e, faces, to, s, w * s, h * s
    fw, fh = DRAW_W, DRAW_W / e.aspect
    return e, faces, (lambda q: (LEFT + q[0] * fw, TOP_Y + q[1] * fh)), None, fw, fh


def pager(d, view_id):
    """The function from a model point to its place on the operator's sheet of one view."""
    view = next(v for v in d['views'] if v['id'] == view_id)
    e, _, to, _, _, _ = _layout(d, view)
    return lambda p: to(e.page(tuple(p)))


def scale_of(d, view_id):
    """Sheet units per model unit of a flat view (None for a camera view)."""
    return _layout(d, next(v for v in d['views'] if v['id'] == view_id))[3]


def svg_of(ops):
    """A sheet's drawing instructions as one SVG document."""
    w, h = ops['size']
    body = []
    if ops['clip']:
        x, y, cw, ch = ops['clip']
        body.append(f'<defs><clipPath id="f"><rect x="{x:.1f}" y="{y:.1f}" width="{cw:.1f}" height="{ch:.1f}"/></clipPath></defs><g clip-path="url(#f)">')
    body.append(f'<g stroke="{INK}" stroke-width="0.6" stroke-linejoin="round">')
    body += [f'<polygon points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in pts)}" fill="{fill}"/>' for pts, fill in ops['polys']]
    body.append('</g>' + ('</g>' if ops['clip'] else ''))
    if ops['frame']:
        x, y, fw, fh = ops['frame']
        body.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{fw:.1f}" height="{fh:.1f}" fill="none" stroke="#111" stroke-width="1.5"/>')
    body += [f'<path class="{cls}" d="M{" L".join(f"{x:.1f} {y:.1f}" for x, y in pts)}"/>' for pts, cls in ops['lines']]
    body += [f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2" fill="#555"/>' for x, y in ops['dots']]
    for cls, x, y, text, anchor in ops['texts']:
        body.append(f'<text class="{cls}" x="{x:.1f}" y="{y:.1f}">{esc(text)}</text>' if anchor == 'start' else f'<text class="{cls}" text-anchor="{anchor}" x="{x:.1f}" y="{y:.1f}">{esc(text)}</text>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w * 2:.0f}" height="{h * 2:.0f}" viewBox="0 0 {w:.1f} {h:.1f}">'
            '<style>.t{font:13px Arial,sans-serif;fill:#222}.d{font:12px Arial,sans-serif;fill:#222}.e{font:13px Arial,sans-serif;fill:#444}.h{font:bold 16px Arial,sans-serif;fill:#111}'
            '.ld{stroke:#555;stroke-width:.7;fill:none}.dm{stroke:#333;stroke-width:.7;fill:none}</style>'
            f'<rect width="{w:.1f}" height="{h:.1f}" fill="#ffffff"/>{"".join(body)}</svg>')


def _sheet(d, view):
    """The two sheets of one view as drawing instructions: the operator's (title, what the view is, labels in one column, sizes) and the image model's (the drawing alone)."""
    e, faces, to, s, w, h = _layout(d, view)
    at = lambda p: to(e.page(tuple(p)))
    lab = {'polys': [([to(q) for q in f['xy']], f['fill_marked']) for f in faces], 'clip': None if e.flat else (LEFT, TOP_Y, w, h), 'frame': None if e.flat else (LEFT, TOP_Y, w, h),
           'lines': [], 'dots': [], 'texts': [('h', LEFT, 30.0, f"{view['name']} ({view['kind']})", 'start'), ('e', LEFT, 52.0, f"What it shows: {view['shows']}", 'start'),
                                              ('e', LEFT, 70.0, f"What it is for: {view['for']}", 'start')]}
    ty = TOP_Y - 8
    for (ax, ay), text in sorted(((at(r['at']), r['text']) for r in d.get('labels') or [] if r['view'] == view['id']), key=lambda r: r[0][1]):
        ty = max(ty + 18, ay)                      # one column, in the order of the points, so the leaders do not cross
        lab['lines'].append(([(ax, ay), (LABEL_X - 6, ty - 4)], 'ld'))
        lab['dots'].append((ax, ay))
        lab['texts'].append(('t', LABEL_X, ty, text, 'start'))
    cx, cy = LEFT + w / 2, TOP_Y + h / 2
    for r in d.get('dims') or []:
        if r['view'] != view['id']:
            continue
        (ax, ay), (bx, by) = at(r['from']), at(r['to'])
        nx, ny = -(by - ay), bx - ax
        m = math.hypot(nx, ny) or 1.0
        nx, ny = nx / m * 16, ny / m * 16
        mx, my = (ax + bx) / 2, (ay + by) / 2
        if (mx + nx - cx) ** 2 + (my + ny - cy) ** 2 < (mx - nx - cx) ** 2 + (my - ny - cy) ** 2:
            nx, ny = -nx, -ny                      # the size line stands on the side away from the middle of the drawing
        lab['lines'].append(([(ax, ay), (ax + nx, ay + ny), (bx + nx, by + ny), (bx, by)], 'dm'))
        lab['texts'].append(('d', mx + nx * 1.9, my + ny * 1.9 + 4, r['text'], 'middle'))
    lab['size'] = (SHEET_W, max([TOP_Y + h, ty]) + 30)
    if e.flat:
        dx, dy = LEFT - 10, TOP_Y - 10
        plain = {'size': (w + 20, h + 20), 'clip': None, 'frame': None, 'polys': [([(x - dx, y - dy) for x, y in (to(q) for q in f['xy'])], f['fill']) for f in faces]}
    else:
        k = FRAME_W / w
        plain = {'size': (FRAME_W, FRAME_W / e.aspect), 'clip': (0.0, 0.0, FRAME_W, FRAME_W / e.aspect), 'frame': None,
                 'polys': [([((x - LEFT) * k, (y - TOP_Y) * k) for x, y in (to(q) for q in f['xy'])], f['fill']) for f in faces]}
    plain.update(lines=[], dots=[], texts=[])
    return lab, plain


def render(d):
    """One entry per view: 'labelled' (the operator's sheet) and 'plain' (the image model's copy: no text, one colour for one material) as SVG,
    the same two as drawing instructions ('labelled_ops', 'plain_ops') for a picture file, and the plain copy's size in pixels."""
    sheets = []
    for view in d['views']:
        lab, plain = _sheet(d, view)
        sheets.append({'view': view['id'], 'name': view['name'], 'kind': view['kind'], 'labelled': svg_of(lab), 'plain': svg_of(plain), 'labelled_ops': lab, 'plain_ops': plain,
                       'width': round(plain['size'][0] * 2), 'height': round(plain['size'][1] * 2)})
    return sheets


# ---------- the words that explain the drawings to the image model ----------

PERSON_WORDS = ("A block figure stands for each person. The pale side of the head with dark eyes and mouth is the face; the pale side of the body with one dark stripe is the chest; "
                "the purple side is the back; the orange arm is the right arm, the arm that works. The figure shows only where the person stands, which way the body faces and where the hands are.")
SLANT_WORDS = ("A drawing seen at an angle and drawn flat has no perspective, so walls and edges that are upright and level in real life look slanted or leaning in it. "
               "Do not carry that slant into the picture: every wall and upright edge stands plumb, every level line is level, and lines run away from the camera with ordinary lens perspective.")
CONVENTION_WORDS = 'Outlines, flat colours, the marks on a block figure and the plain background are drawing conventions, not things in the picture.'


def how_to_read(d, view_ids, first=1):
    """The paragraph that tells the image model how to read the drawings it is sent: one line per drawing in the order sent (Image `first`, …),
    then what each colour stands for, the block figure's marks when a person is drawn, the slant warning when a flat angled view is among them."""
    views = {v['id']: v for v in d['views']}
    lines = ['How to read the drawings.']
    for k, vid in enumerate(view_ids, first):
        v = views[vid]
        lines.append(f"Image {k} is {v['name']}: {KINDS[v['kind']]}. It shows {v['shows']}. Use it for {v['for']}.")
    used = {p['material'] for p in d.get('pieces') or []}
    if used:
        lines.append('In the drawings one flat colour is one material: ' + '; '.join(f"{colour_name(m['colour'])} is {m['is']}" for name, m in d['materials'].items() if name in used) + '.')
    if d.get('people'):
        lines.append(PERSON_WORDS)
    if any(views[v]['kind'] == 'three-quarter' for v in view_ids):
        lines.append(SLANT_WORDS)
    lines.append(CONVENTION_WORDS)
    return '\n'.join(lines)
