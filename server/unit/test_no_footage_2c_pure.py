"""SK, 23 Nov 2026 (no-footage release 2c): the look picture is read where the footage is read. The light of a made picture is measured
against the look board of the Direction taken (the board of the closer period on a film of two), never against a library clip; a run whose
picture AI is Nano Banana is handed the board as a reference. A film with footage is measured against its footage as before."""
import json
from io import BytesIO
from pathlib import Path

from PIL import Image

from app import core, image_check as IC, visuals_stage as VS

SERVER = Path(__file__).resolve().parents[1]
VISUALS = next(s for s in json.loads((SERVER / 'procedures' / 'v3.json').read_text(encoding='utf-8'))['stages'] if s['name'] == 'visuals')
TWO = [{'period': '1950s', 'look': 'Faded colour.'}, {'period': 'today', 'look': 'Clean daylight.'}]


def png(rgb):
    out = BytesIO()
    Image.new('RGB', (64, 36), rgb).save(out, format='PNG')
    return out.getvalue()


class Store(dict):
    def get(self, key):
        return self[key]


def film(looks, colours):
    """A film whose taken Direction has these looks, each with a made board of one colour."""
    s = {'treatment': {'direction': 'The mason tells it.', 'direction_look': looks}, 'references': {}, 'boards': {}}
    store = Store()
    for n, (e, rgb) in enumerate(zip(looks, colours)):
        s['boards'][f'b{n}'] = {'id': f'b{n}', 'of': VS._board_of('The mason tells it.', e), 'n': 0, 'remakes': 0, 'period': e['period'], 'status': 'candidate', 'key': f'k{n}', 'sha256': f's{n}'}
        store[f'k{n}'] = png(rgb)
    return s, store


REF = {'kind': 'keyframe', 'element_kind': 'object'}


def test_the_light_of_a_picture_is_measured_against_the_look_picture():
    s, store = film(TWO[:1], [(120, 110, 100)])
    near, far = IC.light_line(store, s, REF, png((122, 110, 100))), IC.light_line(store, s, REF, png((250, 250, 250)))
    assert near['pass'] and "close to the film's look picture" in near['seen'] and 'footage' not in json.dumps(near)
    assert not far['pass'] and 'brighter' in far['seen'] and far['weight'] == 'should'


def test_a_film_of_two_periods_is_measured_against_the_closer_board():
    s, store = film(TWO, [(60, 50, 40), (200, 205, 210)])
    assert IC.light_line(store, s, REF, png((200, 205, 212)))['pass'] and IC.light_line(store, s, REF, png((62, 50, 40)))['pass']


def test_a_library_clip_is_never_the_measure_of_such_a_film():
    s, store = film(TWO[:1], [(120, 110, 100)])
    s['references']['f1'] = {'id': 'f1', 'kind': 'frame', 'status': 'approved', 'key': 'frame'}
    store['frame'] = png((250, 250, 250))
    assert IC.light_line(store, s, REF, png((120, 110, 100)))['pass']   # the Direction's look, not the clip's
    assert IC.detail_line(store, s, REF, png((120, 110, 100))) is None   # no footage of its own to compare fine detail with


def test_a_look_with_no_picture_measures_nothing():
    s, store = film(TWO[:1], [(1, 1, 1)])
    s['boards'] = {}
    assert IC.light_line(store, s, REF, png((1, 1, 1))) is None


def test_a_film_with_footage_is_measured_against_its_footage_as_before():
    s = {'references': {'f1': {'id': 'f1', 'kind': 'frame', 'status': 'approved', 'key': 'frame'}}}
    store = Store(frame=png((120, 110, 100)))
    line = IC.light_line(store, s, REF, png((120, 110, 100)))
    assert line['pass'] and line['seen'] == 'close to the footage beside it (1 frame)' and line['weight'] == 'must'


BODY = {'kind': 'keyframe', 'prompt': "A wall. The film's look: Clean daylight. No studio light."}
ELEMENT = {'kind': 'object'}


def test_nano_banana_is_handed_the_look_board_as_a_reference():
    s, _ = film(TWO, [(1, 1, 1), (2, 2, 2)])
    entry, line = VS.look_parent(s, 'gemini', BODY, ELEMENT, 2)
    assert entry == {'id': 'b1', 'key': 'k1', 'sha256': 's1', 'look': True} and 'Image 3' in line and 'look board' in line   # the board of the period the prompt names
    one, _ = film(TWO[:1], [(1, 1, 1)])
    assert VS.look_parent(one, 'gemini', {'kind': 'isolated', 'prompt': 'x'}, ELEMENT, 0)[0]['id'] == 'b0'


def test_the_look_board_is_not_judged_as_a_parent_of_the_picture():
    ref = {'kind': 'keyframe', 'generation': {'parents': [{'id': 'b1', 'key': 'k1', 'sha256': 's1', 'look': True}]}}
    lines = IC.code_only({'references': {}}, ref)['code']
    assert not [l for l in lines if l['check'] == 'parent']


def test_no_board_is_handed_where_it_does_not_belong():
    s, _ = film(TWO[:1], [(1, 1, 1)])
    none = (None, '')
    assert VS.look_parent(s, 'openai', BODY, ELEMENT, 0) == none   # GPT Image reads the words
    assert VS.look_parent(s, 'gemini', {**BODY, 'set': True}, ELEMENT, 0) == none and VS.look_parent(s, 'gemini', {**BODY, 'fix_of': 'r'}, ELEMENT, 0) == none
    assert VS.look_parent(s, 'gemini', {**BODY, 'kind': 'sheet'}, ELEMENT, 0) == none and VS.look_parent(s, 'gemini', BODY, {'kind': 'graphic'}, 0) == none
    assert VS.look_parent(s, 'gemini', BODY, ELEMENT, VS.GEMINI_MAX_INPUTS) == none   # no room
    assert VS.look_parent({'references': {}}, 'gemini', BODY, ELEMENT, 0) == none   # a film with footage
    two, _ = film(TWO, [(1, 1, 1), (2, 2, 2)])
    assert VS.look_parent(two, 'gemini', {'kind': 'keyframe', 'prompt': 'no look named'}, ELEMENT, 0) == none   # two periods and the prompt names neither: no guess


def test_the_directions_are_written_with_the_library_clips_in_view():
    none, own = core.for_footage(VISUALS, 'none'), core.for_footage(VISUALS, 'own')
    part = lambda st: next(p['text'] for p in st['parts'] if p['name'] == 'treatment')
    assert 'library clip' in part(none) and 'follows the Direction' in part(none)
    assert 'follows the Direction' not in json.dumps(own)
