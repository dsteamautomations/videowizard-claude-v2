"""Layout B, second part (SK, 20 Nov 2026): 1. "Yes, stripes on for every person in flat mode": in the flat look (the layout video and the
check frames) every box person has the yellow side stripes, whatever the scene's marks.stripes says, and the take's words name them whenever
the video shows them; the EEVEE first frame (the still's source) keeps the scene's own rule, so the still and its words agree. 2. "Marks only
where facing matters": a piece of the set or a prop may name its `front` ([x, y], as a person's facing, one of the four sides of its box);
it then gets a black front panel and a purple back panel in both looks, and the still's and the take's words say what they mark.
Each test failed first. guide_scene.py is read as text (it needs Blender to run)."""
import json
import sys
from pathlib import Path

import pytest

from app import guide as GD, guide_spec as G
from test_guide_route_pure import TAKE_WORDS, STILL_WORDS, film, prices, rendered, saved, scene, spec10, USER, NEW, Conn   # noqa: F401 (fixtures)
from test_guide_spec_pure import counter_pour, home_walk

ROOT = Path(__file__).resolve().parents[2]
SCENE = (ROOT / 'server' / 'blender' / 'guide_scene.py').read_text(encoding='utf-8')
STRIPE = "the thin yellow stripe down the side of each box person marks that person's side."
FRONT_ONE = 'the black panel marks the front of the chair, the purple panel its back; the panels are never shown.'


# ---------- 1. the stripes in the flat look ----------

def test_the_flat_look_gives_every_person_the_stripes_and_eevee_keeps_the_scenes_rule():
    people = SCENE[SCENE.index('# ---- the people'):SCENE.index('props = []')]
    assert "if marks.get('stripes') or look == 'flat':" in people
    assert SCENE.index("look = opt.get('look', 'eevee')") < SCENE.index('# ---- the people')


def test_the_take_names_the_stripes_whenever_the_flat_video_shows_them():
    assert STRIPE in GD.effective_prompt({'render': {'look': 'flat'}}, TAKE_WORDS)
    assert STRIPE in GD.effective_prompt({'render': {'look': 'flat'}, 'marks': {'band': None, 'stripes': False}}, TAKE_WORDS)
    assert GD.effective_prompt({'render': {'look': 'flat'}, 'marks': {'stripes': True}}, TAKE_WORDS).count(STRIPE) == 1
    assert STRIPE not in GD.effective_prompt({'render': {'look': 'eevee'}}, TAKE_WORDS) and STRIPE not in GD.effective_prompt({}, TAKE_WORDS)
    assert STRIPE in GD.effective_prompt({'render': {'look': 'eevee'}, 'marks': {'stripes': True}}, TAKE_WORDS)


def test_the_still_keeps_the_scenes_rule_for_the_stripes():
    assert GD.marks_line({}, 'image') == '' and GD.marks_line({'stripes': False}, 'image') == ''
    assert GD.marks_line({}, 'video', flat=True) == 'How to read the video: ' + STRIPE


def test_a_yellow_person_is_warned_in_the_flat_look_by_default():
    def yellow(spec, **kw):
        return [r['message'] for r in G.checks(spec, **kw) if r['check'] == 'colours' and 'yellow' in r['message']]
    s = counter_pour()   # the man is yellow; the scene has no stripes
    assert yellow(s) == ['Colours: the man is nearly the yellow of the side stripes on a box person; the mark would not show. Give the person another colour.']
    assert yellow(s, flat=False) == []
    s['marks'] = {'band': None, 'stripes': True}
    assert len(yellow(s, flat=False)) == 1
    assert "G.checks(spec, subjects=_people_of(plan, shot), flat=settings().GUIDE_VIDEO_LOOK == 'flat')" in (ROOT / 'server' / 'app' / 'guide.py').read_text(encoding='utf-8')


# ---------- 2. the front of a thing ----------

def chair_scene():
    s = counter_pour()
    s['set'].append({'id': 'CHAIR', 'name': 'the chair', 'shape': 'box', 'min': [0.8, -0.6, 0.0], 'max': [1.25, -0.15, 0.9], 'colour': [0.1, 0.35, 0.2], 'front': [0, -1]})
    return s


def test_a_scene_written_before_is_taken_as_it_was():
    assert G.problems(home_walk()) == [] and G.problems(counter_pour()) == [] and G.fronted(home_walk()) == []


@pytest.mark.parametrize('front', [[0, -1], [0, 1], [1, 0], [-1, 0], [0.0, -1.0]])
def test_every_side_of_the_box_is_a_front(front):
    s = chair_scene()
    s['set'][-1]['front'] = front
    s['props'][0]['front'] = front
    assert G.problems(s) == []


@pytest.mark.parametrize('front', [[1, 1], [0, -2], 'front', [0], {'x': 0}, 1, [0, -1, 0]])
def test_any_other_front_is_refused_with_the_way_to_fix_it(front):
    s = chair_scene()
    s['set'][-1]['front'] = front
    assert G.problems(s) == ["CHAIR: front is the side of the thing that is its front, as [x, y] like a person's facing: [0, -1] (toward the camera's side), "
                             "[0, 1], [1, 0] or [-1, 0]. Leave it out when the way the thing faces does not matter."]
    s = chair_scene()
    s['props'][0]['front'] = front
    assert G.problems(s)[0].startswith('JUG: front is the side of the thing')


def test_the_things_with_a_front_are_named_set_first_then_props():
    s = chair_scene()
    s['props'][0]['front'] = [1, 0]
    assert G.fronted(s) == ['the chair', 'the jug']


def test_the_words_say_what_the_panels_mark():
    assert GD.marks_line({}, 'image', fronts=['the chair']) == 'How to read the image: ' + FRONT_ONE
    assert GD.marks_line({}, 'video', fronts=['the chair', 'the cabinet']) == ('How to read the video: the black panel marks the front of the chair and the cabinet, '
                                                                                 'the purple panel their back; the panels are never shown.')
    sent = GD.effective_prompt({'render': {'look': 'flat'}, 'fronts': ['the chair']}, TAKE_WORDS)
    assert sent.count('How to read the video: ') == 1 and sent.index(STRIPE) < sent.index(FRONT_ONE) < sent.index(TAKE_WORDS)
    assert GD.prompt_problems(FRONT_ONE) == []


def test_the_script_puts_a_black_front_and_a_purple_back_on_a_thing_with_a_front_only():
    assert SCENE.count('fronts(') == 3   # the helper, the set, the props
    f = SCENE[SCENE.index('def fronts('):SCENE.index('# ---- the set ----')]
    assert "(1, BLACK, 'FRONT_')" in f and "(-1, BACK, 'REAR_')" in f and '0.3' in f   # 60 per cent of the face each way: never larger than the face
    assert 'o.matrix_parent_inverse = parent.matrix_world.inverted()' in f   # it moves, turns and spins with its thing
    assert "if s.get('front'):" in SCENE and "if pr.get('front'):" in SCENE
    assert SCENE.count('.data.materials.append(mat(') == 2   # the panels are boxes like every mark


def test_a_scene_with_a_front_carries_it_into_the_still_and_the_take(film):
    store, conn = film
    s = spec10()
    s['set'][4]['front'] = [0, -1]   # the door opens from the lane
    scene(store, conn, s)
    assert saved(store)['guides']['VS1']['fronts'] == ['the door']
    rendered(store, conn)
    store.files['run-1/visuals/references/R1.png'] = b'png'
    GD.request_still(conn, store, USER, NEW, [], 'VS1', STILL_WORDS, [{'id': 'R1', 'job': 'the mason: copy his face, build and clothes'}])
    door = 'the black panel marks the front of the door, the purple panel its back; the panels are never shown.'
    assert door in saved(store)['guides']['VS1']['stills'][-1]['effective_prompt']
    assert door in GD.set_prompt(conn, store, USER, NEW, [], 'VS1', TAKE_WORDS)['prompt']


def test_a_scene_without_a_front_stores_no_fronts(film):
    store, conn = film
    scene(store, conn)
    assert 'fronts' not in saved(store)['guides']['VS1']


# ---------- the helper texts ----------

def test_the_writer_the_skill_and_the_checker_are_told():
    sys.path.insert(0, str(ROOT / 'scripts'))
    import layoutb2_wording as L
    import layoutb_wording as L1
    retired = json.loads((ROOT / 'server' / 'retired-sentences.json').read_text(encoding='utf-8'))['sentences']
    for f, old, new in L.HELPERS:
        text = (ROOT / 'plugin' / f).read_text(encoding='utf-8')
        assert text.count(new) == 1, f
    check = (ROOT / 'plugin' / 'agents' / 'vw-guide-check.md').read_text(encoding='utf-8')
    assert L1.CHECK_NEW not in check and L1.CHECK_NEW in retired
    assert 'a yellow stripe down each side' in L.CHECK_NEW and 'when the scene has stripes' not in L.CHECK_NEW and 'never a fault' in L.CHECK_FRONT
    assert '`"front": [x, y]`' in L.WRITER and 'Never on a symmetric piece' in L.WRITER and '`"front": [x, y]`' in L.SKILL
    split = (ROOT / 'scripts' / 'c1_split_v3.py').read_text(encoding='utf-8')
    assert split.index('from layoutb_wording import apply as layoutb') < split.index('from layoutb2_wording import apply as layoutb2') < split.index('from d132_wording_v3 import')
