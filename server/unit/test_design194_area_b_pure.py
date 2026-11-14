"""Accurate images, build step 5 (design/194), Area B: the start picture of an AI video shot.
The scene's own numbers make the shot's drawing (through the camera and from above, each person with front, back and working arm marked); the operator
approves it before the still; the still's request carries the box frame first, the two drawings, then the given pictures; its words explain the
drawings, tell GPT image what not to copy, and carry the right-hand lines. No Blender, no paid call."""
import io

import pytest
from PIL import Image

from app import chat_flow as CF, draw3d as D, drawings as DR, guide as GD, guide_drawing as GDR, guide_spec as G, visuals_stage as VS
from test_design151_refs_pure import NEW
from test_draw3d_pure import dovetail
from test_guide_route_pure import Conn, STILL_WORDS, film, frames_back, prices, refused, scene, spec10   # noqa: F401  (film and prices are fixtures)
from test_guide_spec_pure import counter_pour, home_walk
from test_visuals_stage_pure import USER, saved

MASON = [{'id': 'R1', 'job': 'the mason: copy his face, build and clothes'}]


def ready_for_the_still(store, conn):
    """The guide is checked and rendered; the shot's drawing still waits for the operator."""
    scene(store, conn)
    sha = frames_back(store, conn)
    GD.verdict(conn, store, {'id': 'u2', 'name': 'Revathi'}, NEW, [], 'VS1', sha, True, [{'look': 'everyone reads as a person', 'pass': True}])
    s = saved(store)
    g = s['guides']['VS1']
    GD.apply_result(s, {'id': g['render']['job_id'], 'request': {'kind': 'guide-render', 'shot_id': 'VS1', 'sha256': g['sha256']}}, 'ready',
                    {'guide_key': 'run-1/visuals/guides/x/guide.mp4', 'sha256': 'sha-guide', 'bytes': 9, 'frame1_key': 'run-1/visuals/guides/x/frame1.png', 'frame1_sha256': 'sha-f1', 'render_seconds': 600}, None)
    VS.save_session(store, NEW, s)
    store.files['run-1/visuals/references/R1.png'] = b'png'
    return g['sha256']


# ---------- the shot's drawing, from the scene's own numbers ----------

def test_the_scene_gives_a_drawing_through_the_camera_and_from_above_and_it_waits_for_the_operator(film):
    store, conn = film
    out = scene(store, conn)
    d = saved(store)['guides']['VS1']['drawing']
    assert d['status'] == 'proposed' and [v['id'] for v in d['views']] == ['camera', 'above'] and 'drawing is made (free)' in out['next']
    cam = d['views'][0]
    assert Image.open(io.BytesIO(store.files[cam['plain_key']])).size == (1600, 900)          # the camera view is the frame itself, 16:9
    assert "Image 2 is The shot through the film's camera" in d['how'] and 'Image 3 is The place from above' in d['how']
    assert 'the purple side is the back' in d['how'] and 'the right arm' in d['how'] and 'not a view to reproduce' in d['how']
    assert not any(q['provider'] != 'guide' for q in conn.queued)                              # free: only the guide's own check frames are queued


def test_the_drawing_places_people_and_things_as_the_guide_does():
    spec = home_walk()
    d, notes = GDR.description(spec)
    assert D.problems(d) == [] and notes == []
    assert set(d['materials']) == {'HOUSE_WALL', 'VER_FLOOR', 'VER_ROOF', 'DOOR', 'WINDOW'}      # every piece of the set but the ground, each its own material named in plain words
    assert d['materials']['DOOR']['is'] == 'the door' and len(d['people']) == 3
    father = d['people'][0]
    assert father['at'] == [-2.2, -0.8, 0.0] and father['facing'][0] > 0.99                     # he walks to the right, so his chest points right
    mother = d['people'][2]
    assert mother['facing'] == pytest.approx([-1.0, 0.0], abs=1e-9)
    assert d['views'][0]['camera'] == {'position': [0.6, -9.5, 1.7], 'aim': [0.6, 0.0, 1.1], 'lens': 35}


def test_a_working_hand_is_drawn_where_the_scene_puts_it():
    d, _ = GDR.description(counter_pour())
    man = d['people'][0]
    assert man['hands']['right'] == pytest.approx([-0.3, -0.3, 1.15])
    assert any(p['material'] == 'JUG' for p in d['pieces'])


def test_what_stands_behind_the_camera_is_left_out_and_said():
    spec = home_walk()
    spec['set'].append({'id': 'SHED', 'name': 'the shed', 'shape': 'box', 'min': [0, -14, 0], 'max': [2, -12, 2], 'colour': [0.3, 0.3, 0.3]})
    d, notes = GDR.description(spec)
    assert 'SHED' not in d['materials'] and any('the shed' in n and 'behind the camera' in n for n in notes) and D.problems(d) == []


def test_a_piece_drawn_as_a_thing_carries_that_things_own_model():
    spec = home_walk()
    spec['set'].append({'id': 'JOINT', 'name': 'the joint on the step', 'shape': 'box', 'min': [2.0, -0.4, 0.0], 'max': [2.15, -0.25, 0.12], 'colour': [0.6, 0.4, 0.2], 'drawn_as': 'E1'})
    d, notes = GDR.description(spec, {'E1': dovetail()})
    assert D.problems(d) == []
    assert 'JOINT.maple' in d['materials'] and 'JOINT.walnut' in d['materials'] and 'JOINT' not in d['materials']      # the thing's own pieces, not the box
    placed = [p for p in d['pieces'] if p['material'].startswith('JOINT.')]
    assert len(placed) == len(dovetail()['pieces']) and all(p['place']['scale'] == 0.001 for p in placed)            # millimetres into the scene's metres
    assert notes == []                                                                                                # its drawn size and its box agree
    spec['set'][-1]['max'] = [3.0, 0.6, 1.0]
    _, notes = GDR.description(spec, {'E1': dovetail()})
    assert any('make the two agree' in n for n in notes)
    spec['set'][-1]['drawn_as'] = 'E9'
    d, notes = GDR.description(spec, {'E1': dovetail()})
    assert 'JOINT' in d['materials'] and any('no approved drawing set' in n for n in notes)


def test_the_changes_made_to_the_plans_layout_are_plain_lines(film):
    store, conn = film
    spec = spec10()
    spec['changed_from_plan'] = 'mirrored'
    assert 'changed_from_plan' in refused(lambda: scene(store, conn, spec))
    spec['changed_from_plan'] = ['The plan had the mother at the right; she stands at the left so her right hand is toward the camera.']
    scene(store, conn, spec)
    assert saved(store)['guides']['VS1']['drawing']['changes'] == spec['changed_from_plan']


# ---------- the operator's approval ----------

def test_no_still_is_made_until_the_operator_has_approved_the_shots_drawing(film):
    store, conn = film
    sha = ready_for_the_still(store, conn)
    said = refused(lambda: GD.request_still(conn, store, USER, NEW, [], 'VS1', STILL_WORDS, MASON))
    assert "has not approved this shot's drawing" in said and sha in said
    assert 'changed' in refused(lambda: GD.drawing_verdict(conn, store, USER, NEW, [], 'VS1', 'another', True, 'yes'))
    assert 'words' in refused(lambda: GD.drawing_verdict(conn, store, USER, NEW, [], 'VS1', sha, True, ''))
    assert 'what is wrong' in refused(lambda: GD.drawing_verdict(conn, store, USER, NEW, [], 'VS1', sha, False, 'no'))
    GD.drawing_verdict(conn, store, USER, NEW, [], 'VS1', sha, True, 'yes, that is the shot')
    assert saved(store)['guides']['VS1']['drawing']['verdict']['quote'] == 'yes, that is the shot'
    GD.request_still(conn, store, USER, NEW, [], 'VS1', STILL_WORDS, MASON)


def test_a_correction_sends_the_scene_back_and_a_changed_scene_is_drawn_and_approved_again(film):
    store, conn = film
    sha = ready_for_the_still(store, conn)
    out = GD.drawing_verdict(conn, store, USER, NEW, [], 'VS1', sha, False, 'not yet', 'the mother faces the wrong way')
    assert out['status'] == 'rejected' and 'Change the scene' in out['next']
    changed = spec10()
    changed['people'][2]['facing'] = [1, 0]
    scene(store, conn, changed)
    d = saved(store)['guides']['VS1']['drawing']
    assert d['status'] == 'proposed' and d['sha256'] != sha


def test_the_operator_is_asked_about_the_shots_drawing_in_the_chat(film):
    store, conn = film
    scene(store, conn)
    session = saved(store)
    ctx = {'session': session, 'plan': VS.current_plan(store, session), 'run': NEW, 'store': store, 'user': USER, 'outputs': [], 'conn': conn}
    items = [i for i in CF._drawing_items(ctx) if i['id'].startswith('shot-drawing:')]
    assert len(items) == 1 and [b['label'] for b in items[0]['buttons']] == ['Yes', 'Correct it'] and len(items[0]['show']) == 2
    assert 'the purple side is the back' in items[0]['text'] and all('-plain' not in p['key'] for p in items[0]['show'])
    items[0]['_run']('yes', 'yes', '')
    assert saved(store)['guides']['VS1']['drawing']['status'] == 'approved'


# ---------- the still's request ----------

def approved(store, conn):
    sha = ready_for_the_still(store, conn)
    GD.drawing_verdict(conn, store, USER, NEW, [], 'VS1', sha, True, 'yes')
    return sha


def test_the_stills_words_explain_the_drawings_and_say_what_not_to_copy(film):
    store, conn = film
    approved(store, conn)
    GD.request_still(conn, store, USER, NEW, [], 'VS1', STILL_WORDS, MASON)
    p = conn.queued[-1]['request']['prompt']
    assert p.startswith(GD.STILL_OPEN) and 'How to read the drawings.' in p and GD.DIAGRAM_WORDS in p and STILL_WORDS in p
    assert p.index(GD.STILL_OPEN) < p.index('How to read the drawings.') < p.index(GD.DIAGRAM_WORDS) < p.index(STILL_WORDS) < p.index('EXACT LAYOUT')
    assert GD.RIGHT_HAND_WORDS not in p and 'look reference' not in p and 'What must be true' not in p      # nobody's hand works in this shot; no look reference; no drawn thing among the pictures


def test_the_right_hand_lines_go_with_a_shot_in_which_a_hand_works(film, monkeypatch):
    store, conn = film
    approved(store, conn)
    worked = spec10()
    worked['people'][2]['hands'] = {'right': [{'t': 0, 'at': [4.0, 1.0, 1.3]}]}
    monkeypatch.setattr(VS, 'load_json', lambda st, k, _real=VS.load_json: worked if k.endswith('/scene.json') else _real(st, k))
    GD.request_still(conn, store, USER, NEW, [], 'VS1', STILL_WORDS, MASON)
    assert GD.RIGHT_HAND_WORDS in conn.queued[-1]['request']['prompt']


def test_a_look_reference_is_the_last_picture_and_only_its_look_is_taken(film):
    store, conn = film
    approved(store, conn)
    assert 'not approved' in refused(lambda: GD.request_still(conn, store, USER, NEW, [], 'VS1', STILL_WORDS, [], look='R2'))      # a candidate is never a look reference
    GD.request_still(conn, store, USER, NEW, [], 'VS1', STILL_WORDS, [], look='R1')
    r = conn.queued[-1]['request']
    assert len(r['parents']) == 4 and r['parents'][-1]['key'] == 'run-1/visuals/references/R1.png'
    assert GD.LOOK_WORDS.format(n=4) in r['prompt'] and 'Take nothing else from it' in r['prompt']
    assert saved(store)['guides']['VS1']['stills'][0]['look'] == 'R1'


def test_the_facts_of_a_drawn_thing_among_the_pictures_are_stated(film):
    store, conn = film
    sha = DR.set_drawing(conn, store, USER, NEW, [], 'E1', dovetail())['sha256']
    DR.verdict(conn, store, USER, NEW, [], 'E1', sha, True, 'yes')
    s = saved(store)
    s['references']['R3'] = {'id': 'R3', 'kind': 'sheet', 'element_id': 'E1', 'status': 'approved', 'key': 'run-1/visuals/references/R3.png', 'sha256': 'sha-R3'}
    VS.save_session(store, NEW, s)
    store.files['run-1/visuals/references/R3.png'] = b'png'
    approved(store, conn)
    GD.request_still(conn, store, USER, NEW, [], 'VS1', STILL_WORDS, [{'id': 'R3', 'job': 'the plinth: copy how it is built'}])
    p = conn.queued[-1]['request']['prompt']
    assert 'What must be true:\n- Dovetail corner: board thickness: 18 mm\n- Dovetail corner: slope of a tail: 1 in 7' in p


def test_the_shots_drawing_can_be_fetched_as_the_operators_sheets(film):
    store, conn = film
    approved(store, conn)
    st = GD.status(conn, store, NEW, [], 'VS1')
    assert 'drawing-camera' in st['files'] and 'drawing-above' in st['files'] and st['guide']['drawing']['status'] == 'approved'
    got = GD.file(store, NEW, [], 'VS1', 'drawing-camera')
    assert got['mime'] == 'image/png' and got['file'] == 'drawing-camera.png'
