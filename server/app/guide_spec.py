"""The scene description of a Blender guide, and everything that can be worked out from it without Blender (integration steps B to D, SK 12 Nov 2026).

A helper writes one JSON description per shot from the plan's numbers; the server's own Blender script (server/blender/guide_scene.py) builds
it, so the helper never runs code on the server. Because the description is data, the checks before any spend, the layout numbers of the
still's prompt and the frame-1 questions are plain arithmetic here, and the Blender script imports this same module for where everything is at
each moment: one source for the picture and for the checks.

Metres. X to the right, Y away from the camera's side of the set, Z up. A box person's front (the black face and chest marks) is local -Y.
No dependency beyond the standard library: Blender's own Python imports this file as it is.
"""
import math

FPS = 30                                    # the guide's frame rate (the consultant's film and all our runs); Gemini returns 24
SIZE = (1280, 720)                          # the guide; frame 1 is rendered again at full quality for the still
SENSOR = 36.0                               # mm, horizontal fit
MIN_S, MAX_S = 3, 15                        # one take (SK, 10 Nov 2026: up to 15 s)
REACH = 0.62                                # m, shoulder to hand; SK's instruction (rule 102); set on close hand shots, not a tested limit
TOP_SPEED = 2.5                             # m/s for a person's box (rule 45); set on street walks
BODY_W, BODY_D, HEAD = 0.44, 0.26, 0.22     # the consultant's box person
SHOULDER_OUT, SHOULDER_DOWN = 0.20, 0.30
RECIPES = ('walker', 'one_action_close', 'transfer_close')
PACES = {'stroll': (0.6, 1.1), 'everyday': (1.1, 1.5), 'brisk': (1.5, 1.9), 'hurried': (1.9, 2.5)}   # m/s (08-blender §5); a warning when the box is outside its band
BEATS = {'lift': 1.0, 'pass': 1.0, 'set_down': 1.0}   # the shortest real length of a beat, seconds (learning L4)


# ---------- small vector arithmetic ----------

def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _len(a):
    return math.sqrt(_dot(a, a))


def _unit(a):
    n = _len(a) or 1.0
    return (a[0] / n, a[1] / n, a[2] / n)


def _lerp(a, b, k):
    return tuple(a[i] + (b[i] - a[i]) * k for i in range(3))


def smooth(k):
    k = min(1.0, max(0.0, k))
    return k * k * (3 - 2 * k)


def _keys(keys, t, ease=False):
    """A value between timed keys [{'t', 'at'}]: held before the first and after the last; straight between (eased when asked)."""
    if t <= keys[0]['t']:
        return tuple(keys[0]['at'])
    for a, b in zip(keys, keys[1:]):
        if t <= b['t']:
            k = (t - a['t']) / ((b['t'] - a['t']) or 1e-9)
            return _lerp(a['at'], b['at'], smooth(k) if ease else k)
    return tuple(keys[-1]['at'])


def times(spec, step=None):
    n = int(round(spec['seconds'] * FPS))
    return [f / FPS for f in range(0, n, step or 1)] + [(n - 1) / FPS]


# ---------- where everything is at a moment ----------

def person_at(p, t):
    """(position, yaw, speed) of a person at t. A walker's heading follows the way they move; a person in place keeps `facing`."""
    if p.get('path'):
        pos, nxt = _keys(p['path'], t), _keys(p['path'], t + 1 / FPS)
        prev = _keys(p['path'], t - 1 / FPS)
        v = _sub(nxt, pos) if _len(_sub(nxt, pos)) > 1e-6 else _sub(pos, prev)
        speed = _len((v[0], v[1], 0.0)) * FPS
        if speed > 0.05:
            return pos, math.atan2(v[0], -v[1]), speed
        d = p.get('facing') or _heading_of_path(p['path'])
        return pos, math.atan2(d[0], -d[1]), 0.0
    d = p.get('facing') or (0.0, -1.0)
    return tuple(p['at']), math.atan2(d[0], -d[1]), 0.0


def _heading_of_path(path):
    a, b = path[0]['at'], path[-1]['at']
    d = (b[0] - a[0], b[1] - a[1])
    return d if abs(d[0]) + abs(d[1]) > 1e-6 else (0.0, -1.0)


def _rot(yaw, x, y):
    return (x * math.cos(yaw) - y * math.sin(yaw), x * math.sin(yaw) + y * math.cos(yaw))


def right_of(yaw):
    """The person's own right, as a direction on the ground (the front is local -Y, so the right hand is local -X)."""
    x, y = _rot(yaw, -1.0, 0.0)
    return (x, y, 0.0)


def shoulder(p, t, side):
    pos, yaw, _ = person_at(p, t)
    x, y = _rot(yaw, (-SHOULDER_OUT if side == 'right' else SHOULDER_OUT), 0.0)
    return (pos[0] + x, pos[1] + y, pos[2] + p['height'] - SHOULDER_DOWN)


def hand(p, t, side):
    """The hand point: its keys when the hand acts, else hanging below the shoulder."""
    keys = (p.get('hands') or {}).get(side)
    if keys:
        return _keys(keys, t, ease=True)
    s = shoulder(p, t, side)
    return (s[0], s[1], s[2] - 0.55 if not p.get('seated') else s[2] - 0.35)


def person_corners(p, t):
    """The eight corners of the box person (body and head as one box)."""
    pos, yaw, _ = person_at(p, t)
    out = []
    for x in (-BODY_W / 2, BODY_W / 2):
        for y in (-BODY_D / 2, BODY_D / 2):
            rx, ry = _rot(yaw, x, y)
            for z in (0.0, p['height']):
                out.append((pos[0] + rx, pos[1] + ry, pos[2] + z))
    return out


def piece_box(s):
    """(min, max) of a set piece or prop at rest."""
    if s.get('shape') == 'cylinder':
        c, r, d = s['centre'], s['radius'], s['depth'] / 2
        e = {'X': (d, r, r), 'Y': (r, d, r), 'Z': (r, r, d)}[s.get('axis', 'Z')]
        return _sub(c, e), _add(c, e)
    return tuple(s['min']), tuple(s['max'])


def _corners(lo, hi):
    return [(x, y, z) for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])]


def people_by_id(spec):
    return {p['id']: p for p in spec.get('people') or []}


def prop_at(spec, prop, t):
    """The centre of a prop: in the hand that holds it during a hold; where it was let go after one; its rest place before the first."""
    size = prop['size']
    centre = (prop['at'][0], prop['at'][1], prop['at'][2] + size[2] / 2)
    people = people_by_id(spec)
    for h in sorted(prop.get('held') or [], key=lambda h: h['from']):
        who, side = h['by'].split('.')
        if t < h['from']:
            break
        centre = hand(people[who], min(t, h['to']), side)
    return centre


def prop_box(spec, prop, t):
    c, s = prop_at(spec, prop, t), prop['size']
    return (c[0] - s[0] / 2, c[1] - s[1] / 2, c[2] - s[2] / 2), (c[0] + s[0] / 2, c[1] + s[1] / 2, c[2] + s[2] / 2)


# ---------- the camera ----------

def project(spec, point):
    """A point as (per cent from the left, per cent from the top, metres in front of the camera); the third is negative behind it."""
    cam = spec['camera']
    f = _unit(_sub(cam['aim'], cam['position']))
    r = _unit(_cross(f, (0.0, 0.0, 1.0)))
    u = _cross(r, f)
    d = _sub(point, cam['position'])
    z = _dot(d, f)
    if z <= 1e-6:
        return (None, None, z)
    k = cam['lens'] / SENSOR
    x = 0.5 + _dot(d, r) / z * k
    y = 0.5 + _dot(d, u) / z * k * SIZE[0] / SIZE[1]
    return (x * 100, (1 - y) * 100, z)


def rect(spec, corners):
    """The rectangle a thing covers in the picture: {left, right, top, bottom} in per cent (not clipped), or None when it is behind the camera."""
    pts = [project(spec, c) for c in corners]
    if any(p[0] is None for p in pts):
        return None
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return {'left': min(xs), 'right': max(xs), 'top': min(ys), 'bottom': max(ys), 'depth': min(p[2] for p in pts)}


def share_in_frame(r):
    """How much of a rectangle lies inside the picture, 0 to 1."""
    if not r:
        return 0.0
    w, h = r['right'] - r['left'], r['bottom'] - r['top']
    if w <= 0 or h <= 0:
        return 0.0
    iw = max(0.0, min(r['right'], 100) - max(r['left'], 0))
    ih = max(0.0, min(r['bottom'], 100) - max(r['top'], 0))
    return iw * ih / (w * h)


def _overlap(a, b):
    return bool(a and b) and min(a['right'], b['right']) - max(a['left'], b['left']) > 0.5 and min(a['bottom'], b['bottom']) - max(a['top'], b['top']) > 0.5


# ---------- the shape of a description ----------

def _vec(v, n=3):
    return isinstance(v, (list, tuple)) and len(v) == n and all(isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) for x in v)


def _timed(keys, seconds, what, out):
    if not isinstance(keys, list) or not keys:
        out.append(f'{what}: give at least one timed point {{"t": seconds, "at": [x, y, z]}}.')
        return
    last = -1.0
    for k in keys:
        if not isinstance(k, dict) or not isinstance(k.get('t'), (int, float)) or not _vec(k.get('at')):
            out.append(f'{what}: every point is {{"t": seconds, "at": [x, y, z]}}.')
            return
        if k['t'] < last or k['t'] < 0 or k['t'] > seconds + 1e-6:
            out.append(f'{what}: times run from 0 to {seconds} s, in order.')
            return
        last = k['t']


def problems(spec):
    """What is wrong with the description's shape, in plain sentences; empty when it can be built. Never raises: a helper's file may hold anything."""
    out = []
    if not isinstance(spec, dict):
        return ['The scene description is one JSON object.']
    if spec.get('recipe') not in RECIPES:
        out.append('recipe: one of ' + ', '.join(RECIPES) + '. Any other kind of shot is not yet available.')
    note = spec.get('process_note')
    if not isinstance(note, str) or len(note.split()) < 12:
        out.append('process_note: two to four lines on how the real thing works: what moves, how far, how fast, in what order.')
    sec = spec.get('seconds')
    if not isinstance(sec, int) or isinstance(sec, bool) or not MIN_S <= sec <= MAX_S:
        out.append(f'seconds: a whole number from {MIN_S} to {MAX_S}.')
        sec = MAX_S
    cam = spec.get('camera')
    if not (isinstance(cam, dict) and _vec(cam.get('position')) and _vec(cam.get('aim')) and isinstance(cam.get('lens'), (int, float)) and 18 <= cam['lens'] <= 135):
        out.append('camera: {"position": [x, y, z], "aim": [x, y, z], "lens": millimetres from 18 to 135}.')
    elif _len(_sub(cam['aim'], cam['position'])) < 0.1 or abs(_unit(_sub(cam['aim'], cam['position']))[2]) > 0.98:
        out.append('camera: the aim is a point in front of the camera, not straight above or below it.')
    sun = spec.get('sun')
    if not (isinstance(sun, dict) and _vec(sun.get('direction')) and _len(sun['direction']) > 0 and sun.get('from') in ('computed', 'stated')):
        out.append('sun: {"direction": [x, y, z] (the way the light travels), "from": "computed" or "stated"}.')
    ids = set()

    def name(x, what):
        if not isinstance(x, dict):
            out.append(f'{what}: each entry is an object.')
            return None
        i = x.get('id')
        if not isinstance(i, str) or not i.replace('_', '').isalnum() or i != i.upper() or len(i) > 40:
            out.append(f'{what}: every entry has an id in capitals, letters, digits and underscores (for example HOUSE_WALL).')
            return None
        if i in ids:
            out.append(f'{i}: the id is used twice.')
        ids.add(i)
        if not isinstance(x.get('name'), str) or not x['name'].strip():
            out.append(f'{i}: name it in plain words (for example "the house wall").')
        if not (_vec(x.get('colour')) and all(0 <= c <= 1 for c in x['colour'])):
            out.append(f'{i}: colour is [red, green, blue], each from 0 to 1.')
        return i

    pieces = spec.get('set')
    if not isinstance(pieces, list) or not pieces:
        out.append('set: the pieces of the place, at least the ground.')
        pieces = []
    for s in pieces:
        i = name(s, 'set')
        if not i:
            continue
        if s.get('shape') == 'cylinder':
            if not (_vec(s.get('centre')) and isinstance(s.get('radius'), (int, float)) and s['radius'] > 0 and isinstance(s.get('depth'), (int, float)) and s['depth'] > 0 and s.get('axis', 'Z') in ('X', 'Y', 'Z')):
                out.append(f'{i}: a cylinder has centre, radius, depth and axis (X, Y or Z).')
        elif not (_vec(s.get('min')) and _vec(s.get('max')) and all(a < b for a, b in zip(s['min'], s['max']))):
            out.append(f'{i}: a box has min [x, y, z] and max [x, y, z], each max larger than its min.')
        spin = s.get('spin')
        if spin is not None and not (isinstance(spin, dict) and spin.get('axis') in ('X', 'Y', 'Z') and isinstance(spin.get('keys'), list) and spin['keys']
                                     and all(isinstance(k, dict) and isinstance(k.get('t'), (int, float)) and isinstance(k.get('deg'), (int, float)) for k in spin['keys'])):
            out.append(f'{i}: spin is {{"axis": "X", "keys": [{{"t": seconds, "deg": degrees}}]}}.')
    people = spec.get('people')
    if not isinstance(people, list):
        out.append('people: a list (empty when nobody is in the shot).')
        people = []
    for p in people:
        i = name(p, 'people')
        if not i:
            continue
        if not isinstance(p.get('height'), (int, float)) or not 0.5 <= p['height'] <= 2.2:
            out.append(f'{i}: height in metres (the seated height for a seated person).')
        if p.get('path') is not None:
            _timed(p['path'], sec, f'{i} path', out)
        elif not _vec(p.get('at')):
            out.append(f'{i}: a person in place has "at": [x, y, z]; a walker has "path".')
        if p.get('facing') is not None and not (_vec(p['facing'], 2) and abs(p['facing'][0]) + abs(p['facing'][1]) > 0):
            out.append(f'{i}: facing is [x, y], the way the person looks on the ground.')
        if p.get('path') is None and p.get('facing') is None:
            out.append(f'{i}: say which way the person faces: "facing": [x, y].')
        if p.get('pace') is not None and p['pace'] not in PACES:
            out.append(f'{i}: pace is one of ' + ', '.join(PACES) + '.')
        hands = p.get('hands')
        if hands is not None:
            if not isinstance(hands, dict) or set(hands) - {'right', 'left'}:
                out.append(f'{i}: hands has "right" and, only when it must, "left".')
            else:
                for side, keys in hands.items():
                    _timed(keys, sec, f'{i} {side} hand', out)
    known = {p.get('id') for p in people if isinstance(p, dict)}
    props = spec.get('props') or []
    if not isinstance(props, list):
        out.append('props: a list.')
        props = []
    for pr in props:
        i = name(pr, 'props')
        if not i:
            continue
        if not (_vec(pr.get('size')) and all(x > 0 for x in pr['size']) and _vec(pr.get('at'))):
            out.append(f'{i}: a prop has size [x, y, z] and "at": [x, y, z], the middle of its foot where it rests.')
        for h in pr.get('held') or []:
            ok = isinstance(h, dict) and isinstance(h.get('from'), (int, float)) and isinstance(h.get('to'), (int, float)) and 0 <= h['from'] < h['to'] <= sec + 1e-6 and isinstance(h.get('by'), str)
            who, _, side = (h.get('by') or '').partition('.') if ok else ('', '', '')
            if not ok or who not in known or side not in ('right', 'left'):
                out.append(f'{i}: held is [{{"from": seconds, "to": seconds, "by": "PERSON.right"}}], by a person of this shot.')
    act = spec.get('action')
    if not (isinstance(act, dict) and isinstance(act.get('start'), (int, float)) and isinstance(act.get('end'), (int, float)) and 0 <= act['start'] < act['end'] <= sec + 1e-6):
        out.append('action: {"start": seconds, "end": seconds}, when the one action of the shot begins and ends.')
    marks = spec.get('marks')
    if marks is not None and not (isinstance(marks, dict) and set(marks) <= {'band', 'stripes'}):
        out.append('marks: {"band": id of the set piece that marks the walking line, or null; "stripes": true or false}.')
    elif marks and marks.get('band') and marks['band'] not in ids:
        out.append('marks: the band names a piece of the set.')
    for b in spec.get('beats') or []:
        if not (isinstance(b, dict) and b.get('kind') in BEATS and isinstance(b.get('from'), (int, float)) and isinstance(b.get('to'), (int, float)) and b['from'] < b['to']):
            out.append('beats: [{"kind": "lift" | "pass" | "set_down", "from": seconds, "to": seconds}].')
            break
    return out


# ---------- the checks before any spend ----------

def _row(check, level, message, **more):
    return {'check': check, 'level': level, 'message': message, **more}


def _supported(lo, hi, others, slack=0.012):
    """Rests on the ground or on something: its foot within 12 mm of the ground or of the top of a thing it stands over."""
    if lo[2] <= slack:
        return True
    return any(abs(lo[2] - ohi[2]) <= slack and min(hi[0], ohi[0]) - max(lo[0], olo[0]) > 0 and min(hi[1], ohi[1]) - max(lo[1], olo[1]) > 0 for olo, ohi in others)


def _dark_distinct(things):
    out = []
    for i, (na, ca) in enumerate(things):
        if 0.2126 * ca[0] + 0.7152 * ca[1] + 0.0722 * ca[2] > 0.80:
            out.append(f'{na} is pale')
        for nb, cb in things[i + 1:]:
            if _len(_sub(ca, cb)) < 0.12:
                out.append(f'{na} and {nb} are nearly the same colour')
    return out


def checks(spec, subjects=None):
    """Every check that can be made on a description that has no shape problems, as rows {check, level, message}.
    level: 'refuse' (the rule is proven or SK's decision and the consultant's film kept it in every shot), 'warn', or 'info'.
    subjects: the ids the plan puts in this shot, when known (every one needs a box)."""
    rows, people, props, pieces = [], spec.get('people') or [], spec.get('props') or [], spec['set']
    boxes = [(s, *piece_box(s)) for s in pieces]
    ts = times(spec, step=3)
    names = {x['id']: x['name'] for x in people + props + pieces}

    # everything rests on something (rule 104, SK's instruction)
    static = [(lo, hi) for _, lo, hi in boxes]
    for s, lo, hi in boxes:
        if not s.get('hung') and not _supported(lo, hi, [b for b in static if b != (lo, hi)]):
            rows.append(_row('support', 'refuse', f"{s['name']} ({s['id']}) rests on nothing: its foot is {lo[2]:.2f} m up with nothing under it. Build what holds it, or put it on the ground."))
    for pr in props:
        if any(h['from'] <= 0 for h in pr.get('held') or []):
            continue
        lo, hi = prop_box(spec, pr, 0.0)
        if not _supported(lo, hi, static):
            rows.append(_row('support', 'refuse', f"{pr['name']} ({pr['id']}) rests on nothing at the start: its foot is {lo[2]:.2f} m up with nothing under it."))
    for p in people:
        pos = person_at(p, 0.0)[0]
        if pos[2] > 0.012 and not any(abs(pos[2] - hi[2]) <= 0.012 and lo[0] <= pos[0] <= hi[0] and lo[1] <= pos[1] <= hi[1] for lo, hi in static):
            if not p.get('seated'):
                rows.append(_row('support', 'refuse', f"{p['name']} ({p['id']}) stands {pos[2]:.2f} m up with nothing under the feet."))

    # reach (rule 102) and the right hand (rule 99)
    for p in people:
        hands = p.get('hands') or {}
        for side, keys in hands.items():
            far = max((_len(_sub(hand(p, t, side), shoulder(p, t, side))), t) for t in ts)
            if far[0] > REACH + 1e-6:
                rows.append(_row('reach', 'refuse', f"{p['name']}'s {side} hand is {far[0]:.2f} m from the shoulder at {far[1]:.1f} s; the limit is {REACH} m. Move the person or the thing; an arm never stretches.", value=round(far[0], 3)))
            else:
                rows.append(_row('reach', 'info', f"{p['name']}'s {side} hand stays within {far[0]:.2f} m of the shoulder (limit {REACH} m).", value=round(far[0], 3)))
        moves = [s for s, keys in hands.items() if len({tuple(k['at']) for k in keys}) > 1]
        if 'left' in moves and 'right' not in moves:
            rows.append(_row('right_hand', 'refuse', f"{p['name']}'s left hand does the job. Give the job to the right hand and put what it uses on the person's right; choose a camera that sees that hand."))
        if 'right' in moves:
            cam = spec['camera']['position']

            def far_side(t):   # the hand lies behind the body as the camera sees it
                mid = _add(person_at(p, t)[0], (0, 0, p['height'] - SHOULDER_DOWN))
                to_cam, h = _sub(cam, mid), _sub(hand(p, t, 'right'), mid)
                return _dot((h[0], h[1], 0.0), _unit((to_cam[0], to_cam[1], 0.0))) < -0.1
            if any(far_side(t) for t in ts):
                rows.append(_row('right_hand', 'refuse', f"{p['name']}'s right hand works on the far side of the body from the camera, so it is hidden. Move the camera to the person's right side."))
    by = people_by_id(spec)
    for pr in props:
        for h in pr.get('held') or []:
            who, side = h['by'].split('.')
            if side == 'left':
                rows.append(_row('right_hand', 'refuse', f"{pr['name']} is held in {by[who]['name']}'s left hand. The right hand holds what the job uses."))
            pos, yaw, _ = person_at(by[who], h['from'])
            start = prop_at(spec, pr, max(0.0, h['from'] - 1e-3))
            if _dot(_sub(start, pos), right_of(yaw)) < -0.05:
                rows.append(_row('right_hand', 'refuse', f"{pr['name']} is picked up from {by[who]['name']}'s left side. Put it on the person's right, within reach."))

    # nobody passes through anything (rule 62); nobody faster than 2.5 m/s (rule 45)
    for p in people:
        hit, fastest = None, 0.0
        for t in ts:
            pos, yaw, speed = person_at(p, t)
            fastest = max(fastest, speed)
            if hit:
                continue
            for s, lo, hi in boxes:
                if min(hi[2], pos[2] + p['height']) - max(lo[2], pos[2]) > 0.02 and lo[0] - BODY_D / 2 < pos[0] < hi[0] + BODY_D / 2 and lo[1] - BODY_D / 2 < pos[1] < hi[1] + BODY_D / 2 and not (p.get('seated') and s.get('seat')):
                    hit = (s, t)
                    break
        if hit:
            rows.append(_row('clash', 'refuse', f"{p['name']} passes through {hit[0]['name']} at {hit[1]:.1f} s. Move the path clear of it."))
        if fastest > TOP_SPEED + 1e-6:
            rows.append(_row('speed', 'refuse', f"{p['name']} moves at {fastest:.2f} m/s; a person's box stays at {TOP_SPEED} m/s or slower. A run is not yet available."))
        elif p.get('path') and p.get('pace'):
            lo_, hi_ = PACES[p['pace']]
            if fastest and not lo_ - 0.05 <= fastest <= hi_ + 0.05:
                rows.append(_row('pace', 'warn', f"{p['name']} is planned at a {p['pace']} pace ({lo_} to {hi_} m/s) but the box moves at {fastest:.2f} m/s."))

    # nobody crosses or overlaps anybody on screen (rule 77, SK: "for now")
    said = set()
    for t in ts:
        rs = [(p, rect(spec, person_corners(p, t)), person_at(p, t)[2]) for p in people]
        for i, (a, ra, sa) in enumerate(rs):
            for b, rb, sb in rs[i + 1:]:
                if (a['id'], b['id']) in said or share_in_frame(ra) == 0 or share_in_frame(rb) == 0 or not _overlap(ra, rb):
                    continue
                said.add((a['id'], b['id']))
                moving = sa > 0.05 or sb > 0.05
                rows.append(_row('crossing', 'refuse' if moving else 'warn',
                                 f"{a['name']} and {b['name']} overlap in the picture at {t:.1f} s" + ('. Paths do not cross and nobody passes in front of anybody in one shot: move a path, or make it two shots.' if moving else '; neither moves. Check that both read clearly, or move one.')))

    # everybody and everything that matters is in the first frame, or walks in from the frame's edge (rules 43, 55, 75)
    for p in people:
        first = share_in_frame(rect(spec, person_corners(p, 0.0)))
        seen = [t for t in ts if share_in_frame(rect(spec, person_corners(p, t))) > 0]
        if first == 0 and not seen:
            rows.append(_row('first_frame', 'refuse', f"{p['name']} is never in the picture. Put the person in view, or take the person out of the shot."))
        elif first == 0 and not p.get('path'):
            rows.append(_row('first_frame', 'refuse', f"{p['name']} is outside the first frame and does not move: the still cannot show the person."))
        elif first == 0:
            rows.append(_row('first_frame', 'info', f"{p['name']} walks in from the edge of the picture at about {seen[0]:.1f} s.", enters_at=round(seen[0], 2)))
        else:
            rows.append(_row('visible_share', 'warn' if first < 0.3 else 'info', f"{p['name']}: {round(first * 100)}% of the box is inside the first frame" + ('; a person mostly out of the picture needs a decision.' if first < 0.3 else '.'), value=round(first, 2)))
    for pr in props:
        if share_in_frame(rect(spec, _corners(*prop_box(spec, pr, 0.0)))) == 0:
            rows.append(_row('first_frame', 'refuse', f"{pr['name']} is not in the first frame; the still is made from it, so the thing would be invented later."))
    if subjects is not None:
        have = {x.get('element_id') or x['id'] for x in people + props}
        for missing in [s for s in subjects if s not in have]:
            rows.append(_row('boxes', 'refuse', f"The plan puts {missing} in this shot and the scene has no box for it. Every person and thing of the shot is a box; words do not place anybody."))

    # warnings: rules on trial or never tested
    for b in spec.get('beats') or []:
        if b['to'] - b['from'] < BEATS[b['kind']] - 1e-6:
            rows.append(_row('beat', 'warn', f"A {b['kind'].replace('_', ' ')} from {b['from']} to {b['to']} s is shorter than a person takes (about {BEATS[b['kind']]:.0f} s or more). The guide's timing is copied."))
    levels = [(s, lo, hi) for s, lo, hi in boxes if s.get('level')]
    for p in people:
        for t in (ts[0], ts[-1]):
            pos = person_at(p, t)[0]
            for s, lo, hi in levels:
                if lo[0] <= pos[0] <= hi[0] and lo[1] <= pos[1] <= hi[1] and abs(pos[2] - hi[2]) <= 0.02:
                    edge = min(pos[0] - lo[0], hi[0] - pos[0], pos[1] - lo[1], hi[1] - pos[1])
                    if edge < 0.5:
                        rows.append(_row('level_edge', 'warn', f"{p['name']} is {edge:.2f} m from the edge of {s['name']}; keep people 0.5 m or more inside the ground they stand on."))
        if not p.get('path') or person_at(p, ts[-1])[2] <= 0.05:
            pos = person_at(p, ts[-1])[0]
            for s, lo, hi in boxes:
                if s.get('pole') and math.hypot(pos[0] - (lo[0] + hi[0]) / 2, pos[1] - (lo[1] + hi[1]) / 2) < 0.5:
                    rows.append(_row('pole', 'warn', f"{p['name']} stops within 0.5 m of {s['name']}; a post that close can hide the person."))
    if spec['action']['end'] < spec['seconds'] - 1.0 - 1e-6:
        rows.append(_row('action_fills', 'warn', f"The action ends at {spec['action']['end']} s and the clip runs to {spec['seconds']} s. In a still tail the model undoes the action; let the action run to the last second, or shorten the clip."))
    seen = [(x['name'], x['colour']) for x in pieces + people + props if share_in_frame(rect(spec, _corners(*piece_box(x)) if x in pieces else (person_corners(x, 0.0) if x in people else _corners(*prop_box(spec, x, 0.0))))) > 0]
    for line in _dark_distinct(seen)[:6]:
        rows.append(_row('colours', 'warn', f'Colours: {line}. Use dark, strongly contrasting colours, one per thing.'))
    return rows


def refusals(rows):
    return [r for r in rows if r['level'] == 'refuse']


BLIND = ('The checks cannot see: steps, seats, bending and door arcs; an arm passing through a thing; one thing hiding another from the camera; '
         'whether a mark will be read as a real thing. Look for these in the check frames.')


# ---------- the layout numbers of the still's prompt (rule 107), from the first frame ----------

def _pct(v):
    return f'{round(v)}%'


def layout(spec, t=0.0):
    """Where each person, prop and set piece sits in the first frame, in per cent of the picture, clipped to it. Things outside it are left out."""
    rows = []

    def add(kind, x, corners):
        r = rect(spec, corners)
        if share_in_frame(r) == 0:
            return
        rows.append({'kind': kind, 'id': x['id'], 'name': x['name'], 'share': round(share_in_frame(r), 2),
                     **{k: round(min(100.0, max(0.0, r[k])), 1) for k in ('left', 'right', 'top', 'bottom')},
                     'cut': [e for e, cut in (('left', r['left'] < 0), ('right', r['right'] > 100), ('top', r['top'] < 0), ('bottom', r['bottom'] > 100)) if cut]})
    for p in spec.get('people') or []:
        add('person', p, person_corners(p, t))
    for pr in spec.get('props') or []:
        add('prop', pr, _corners(*prop_box(spec, pr, t)))
    for s in spec['set']:
        if not s.get('ground'):
            add('set', s, _corners(*piece_box(s)))
    return rows


def layout_block(spec):
    """The EXACT LAYOUT block for the still's prompt, written by the server from the scene (nothing typed by hand)."""
    rows = layout(spec)
    out = ['EXACT LAYOUT, measured from the first image (0% = left or top edge, 100% = right or bottom edge). Draw each person and thing exactly this size and in exactly this place:']
    for r in rows:
        across = f"from {_pct(r['left'])} to {_pct(r['right'])} of the width"
        if r['kind'] == 'person':
            foot = 'cut off by the bottom edge' if 'bottom' in r['cut'] else f"the feet at {_pct(r['bottom'])} down"
            head = 'the head cut off by the top edge' if 'top' in r['cut'] else f"the top of the head at {_pct(r['top'])} down"
            out.append(f"- {r['name']}: {across}; {head}, {foot}.")
        else:
            out.append(f"- {r['name']}: {across}, from {_pct(r['top'])} to {_pct(r['bottom'])} down.")
    n = sum(1 for r in rows if r['kind'] == 'person')
    out.append(f"Exactly {n} {'person' if n == 1 else 'people'} in view; no one else." if n else 'Nobody is in view.')
    return '\n'.join(out)
