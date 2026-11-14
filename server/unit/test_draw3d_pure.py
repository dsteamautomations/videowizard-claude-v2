"""Accurate images, build step 1 (design/194): a drawing set is data, and the server draws it (app/draw3d.py).
One table of measurements makes one model; every view is that model seen from one place, so the views cannot disagree.
The fixture is the dovetail corner of the trial (14 Nov 2026): two boards, three tails, four pins."""
import copy
import re

import pytest

from app import draw3d as D

T, W, L, PIN, RUN = 18.0, 120.0, 150.0, 6.0, 18.0 / 7.0
TAIL = (W - 4 * PIN) / 3


def dovetail():
    pins, tails, z = [], [], 0.0
    for i in range(4):
        lo, hi = z, z + PIN
        pins.append(((lo, hi), (lo - (0 if i == 0 else RUN), hi + (0 if i == 3 else RUN))))
        if i < 3:
            tails.append(((hi, hi + TAIL), (hi + RUN, hi + TAIL - RUN)))
        z = hi + TAIL
    pieces = [{'shape': 'box', 'min': [T, 0, 0], 'max': [L, T, W], 'material': 'maple'},
              {'shape': 'box', 'min': [0, T, 0], 'max': [T, L, W], 'material': 'walnut'}]
    pieces += [{'shape': 'prism', 'axis': 'X', 'from': 0, 'to': T, 'outline': [[0, e[0]], [T, b[0]], [T, b[1]], [0, e[1]]], 'material': 'maple'} for e, b in pins]
    pieces += [{'shape': 'prism', 'axis': 'X', 'from': 0, 'to': T, 'outline': [[0, e[0]], [T, b[0]], [T, b[1]], [0, e[1]]], 'material': 'walnut'} for e, b in tails]
    view = lambda i, kind, name, **more: {'id': i, 'kind': kind, 'name': name, 'shows': 'the tails and the ends of the pins between them', 'for': 'the pattern on this face', **more}
    return {
        'unit': 'mm', 'level': 'engineered', 'name': 'Dovetail corner',
        'facts': [{'what': 'board thickness', 'value': 18, 'unit': 'mm', 'source': 'the joiner\'s drawing'},
                  {'what': 'slope of a tail', 'value': '1 in 7', 'assumed': True}],
        'materials': {'maple': {'colour': [230, 201, 154], 'is': 'pale maple, the pin board'}, 'walnut': {'colour': [139, 90, 60], 'is': 'dark walnut, the tail board'}},
        'pieces': pieces,
        'views': [view('a', 'square on', 'The tail board, square on', toward=[-1, 0, 0]),
                  view('b', 'square on', 'The pin board, square on', toward=[0, -1, 0]),
                  view('c', 'from above', 'From above', toward=[0, 0, 1]),
                  view('d', 'three-quarter', 'From outside the corner', toward=[-1, -1, 0.9])],
        'labels': [{'view': 'a', 'at': [0, 9, 22], 'text': 'tail: 32 at the end'}, {'view': 'a', 'at': [0, 9, 41], 'text': 'pin, end grain'},
                   {'view': 'd', 'at': [9, 9, 120], 'text': 'top half pin'}],
        'dims': [{'view': 'a', 'from': [0, 0, 0], 'to': [0, 0, 120], 'text': '120'}],
    }


def polygons(svg):
    return re.findall(r'<polygon points="([^"]+)" fill="(#[0-9a-f]{6})"', svg)


def test_a_sound_drawing_set_has_no_problems_and_gives_one_sheet_per_view():
    d = dovetail()
    assert D.problems(d) == []
    sheets = D.render(d)
    assert [s['view'] for s in sheets] == ['a', 'b', 'c', 'd']
    for s in sheets:
        assert s['labelled'].startswith('<svg') and s['plain'].startswith('<svg') and s['width'] > 0 and s['height'] > 0


def test_the_copy_for_the_image_model_carries_no_text_at_all():
    for s in D.render(dovetail()):
        assert '<text' not in s['plain'] and '<text' in s['labelled']
        assert 'From outside the corner' not in s['plain']


def test_one_material_is_one_colour_family_on_the_models_copy_even_when_the_operators_copy_marks_a_piece():
    d = dovetail()
    d['pieces'][2]['colour'] = [255, 0, 0]          # the operator's copy marks one pin red
    labelled, plain = D.render(d)[1]['labelled'], D.render(d)[1]['plain']
    reds = lambda svg: [f for _, f in polygons(svg) if int(f[1:3], 16) > 150 and int(f[3:5], 16) < 60]
    assert reds(labelled) and not reds(plain)


def test_every_view_comes_from_the_same_numbers():
    """A corner of the model lands where its numbers say, in every flat view: 120 mm of height is the same length on the page in views a, b and d (times each view's own scale)."""
    d = dovetail()
    for vid, expect in (('a', 120.0), ('b', 120.0)):
        at = D.pager(d, vid)
        (x0, y0), (x1, y1) = at([0, 0, 0]), at([0, 0, 120])
        assert abs(x0 - x1) < 1e-6 and abs(abs(y1 - y0) / D.scale_of(d, vid) - expect) < 1e-6
    top = D.pager(d, 'c')
    assert abs(top([0, 0, 0])[0] - top([0, 0, 120])[0]) < 1e-6 and abs(top([0, 0, 0])[1] - top([0, 0, 120])[1]) < 1e-6   # straight down: height vanishes


def test_what_is_behind_is_hidden_by_what_is_in_front():
    """Square on the pin board's face (view b), the far tail board is behind the near pieces: the last polygon drawn over the corner strip is a near one."""
    d = dovetail()
    faces = D.visible(D.model(d), D.eye(d, d['views'][1]))
    depths = [f['depth'] for f in faces]
    covering = [f for f in faces if all(abs(p[1]) < 1e-6 for p in f['pts'])]     # faces lying in the plane Y = 0: the nearest plane
    assert covering and faces.index(covering[-1]) > len(faces) // 2 and max(depths) > min(depths)


def test_a_view_explains_itself_on_the_operators_sheet_and_in_the_words_for_the_prompt():
    d = dovetail()
    sheet = D.render(d)[0]['labelled']
    assert 'The tail board, square on' in sheet and 'the tails and the ends of the pins between them' in sheet and 'the pattern on this face' in sheet
    words = D.how_to_read(d, ['a', 'd'])
    assert 'Image 1' in words and 'Image 2' in words and 'square on' in words and 'pale maple, the pin board' in words and 'dark walnut, the tail board' in words
    assert 'not things in the picture' in words


def test_a_view_only_for_understanding_is_named_as_not_to_be_reproduced():
    d = dovetail()
    words = D.how_to_read(d, ['c'])
    assert 'not a view to reproduce' in words          # the view from above


@pytest.mark.parametrize('change, said', [
    (lambda d: d.update(pieces=[]), 'no pieces'),
    (lambda d: d['pieces'][0].update(material='oak'), 'oak'),
    (lambda d: d['pieces'][0].update(min=[0, 0, float('nan')]), 'number'),
    (lambda d: d['pieces'][0].update(max=[T, 0, 0]), 'no thickness'),
    (lambda d: d['views'][0].pop('shows'), 'what it shows'),
    (lambda d: d['views'][0].update(kind='isometric'), 'kind'),
    (lambda d: d.update(views=d['views'][:2]), 'at least 4 views'),
    (lambda d: d['facts'][0].pop('source'), 'source'),
    (lambda d: d['labels'][0].update(view='z'), 'view z'),
    (lambda d: d['labels'][0].update(text='x' * 80), 'short'),
    (lambda d: d.update(unit='inch'), 'unit'),
    (lambda d: d['materials']['maple'].update(colour=[300, 0, 0]), 'colour'),
])
def test_a_faulty_drawing_set_is_refused_in_plain_words(change, said):
    d = dovetail()
    change(d)
    out = ' '.join(D.problems(d))
    assert said in out, out


def test_a_camera_view_refuses_a_model_behind_the_camera():
    d = dovetail()
    d['views'][3] = {**d['views'][3], 'kind': 'through the camera', 'camera': {'position': [60, 60, 60], 'aim': [300, 300, 60], 'lens': 35}}
    d['views'][3].pop('toward')
    assert 'behind the camera' in ' '.join(D.problems(d))
    d['views'][3]['camera'] = {'position': [-400, -500, 300], 'aim': [40, 40, 60], 'lens': 35}
    assert D.problems(d) == []
    s = D.render(d)[3]
    assert abs(s['width'] / s['height'] - 16 / 9) < 0.01          # a camera view is the frame itself


def test_a_form_sheet_needs_two_views_and_a_composition_set_three():
    d = dovetail()
    d.update(level='form', views=d['views'][:2], labels=d['labels'][:2])
    assert D.problems(d) == []
    d.update(level='composition')
    assert 'at least 3 views' in ' '.join(D.problems(d))


def test_too_many_pieces_are_refused():
    d = dovetail()
    d['pieces'] = d['pieces'] * 700
    assert 'pieces' in ' '.join(D.problems(d))


def test_labels_sit_in_one_column_in_the_order_of_their_points_so_leaders_do_not_cross():
    d = dovetail()
    sheet = D.render(d)[0]['labelled']
    ys = [float(y) for y in re.findall(r'<text class="t" x="[\d.]+" y="([\d.]+)">(?:tail|pin)', sheet)]
    assert len(ys) == 2 and ys == sorted(ys) and ys[1] - ys[0] >= 16


# ---------- a person shows front, back and the working arm (SK, 14 Nov) ----------

def man(**more):
    return {'at': [0, 0, 0], 'facing': [1, 0], 'height': 1700, 'hands': {'right': [420, -200, 1050]}, **more}


def test_a_person_is_drawn_with_face_chest_back_and_right_arm_in_their_own_fixed_colours():
    d = dovetail()
    d.update(level='composition', people=[man()], views=[
        {'id': 'front', 'kind': 'square on', 'name': 'Seen from in front', 'shows': 'his front', 'for': 'facing', 'toward': [1, 0, 0]},
        {'id': 'back', 'kind': 'square on', 'name': 'Seen from behind', 'shows': 'his back', 'for': 'facing', 'toward': [-1, 0, 0]},
        {'id': 'side', 'kind': 'square on', 'name': 'From his right', 'shows': 'the working arm', 'for': 'the arm', 'toward': [0, -1, 0]}], labels=[], dims=[], pieces=d['pieces'][:1])
    d['pieces'][0].update(min=[2000, 2000, 0], max=[2100, 2100, 100], material='walnut')   # a far block of a colour unlike any of the figure's
    assert D.problems(d) == []
    def on_top(view_id, point):
        """The colour of the face nearest the eye at a point of the model, in one view."""
        e = D.eye(d, next(v for v in d['views'] if v['id'] == view_id))
        x, y = e.page(point)
        inside = lambda poly: all((poly[(k + 1) % len(poly)][0] - poly[k][0]) * (y - poly[k][1]) - (poly[(k + 1) % len(poly)][1] - poly[k][1]) * (x - poly[k][0]) >= -1e-6 for k in range(len(poly)))             or all((poly[(k + 1) % len(poly)][0] - poly[k][0]) * (y - poly[k][1]) - (poly[(k + 1) % len(poly)][1] - poly[k][1]) * (x - poly[k][0]) <= 1e-6 for k in range(len(poly)))
        fill = [f['fill'] for f in D.visible(D.model(d), e) if inside(f['xy'])][-1]
        return tuple(int(fill[k:k + 2], 16) for k in (1, 3, 5))
    near = lambda got, c: all(abs(a - b) <= 60 for a, b in zip(got, c))
    chest, head, upper_arm = (0, -102, 1122), (0, -50, 1530), (52, -244, 1197)       # beside the chest stripe; beside the face marks; the middle of his right upper arm
    assert near(on_top('front', chest), D.FRONT) and near(on_top('front', head), D.FRONT)      # from in front: the pale chest and the pale face
    assert near(on_top('back', chest), D.BACK) and near(on_top('back', head), D.BACK)          # from behind: the back colour on trunk and head
    assert near(on_top('side', upper_arm), D.RIGHT_ARM)                                         # from his right: the working arm in its own colour
    words = D.how_to_read(d, ['front'])
    assert 'chest' in words and 'back' in words and 'right arm' in words


def test_the_back_colour_is_kept_for_backs_alone():
    d = dovetail()
    d['materials']['maple']['colour'] = list(D.BACK)
    assert 'kept for' in ' '.join(D.problems(d))
