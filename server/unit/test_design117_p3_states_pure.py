"""design/117 P3: the per-frame states by element id (design/113's actions kept), a build stepping through a group's children, the cues from seconds
or the timed narration (carried over from design/113 E2), the contact sheet from frames, the frame indexes of the sheet, the page Chromium loads."""
import copy
from io import BytesIO

import pytest
from PIL import Image

from app import drawn as D, svg_scene as S
from svg_fixture import ACTIONS, SVG

IDS = ['bg', 'title', 'wall', 'c1', 'c2', 'c3', 'flame', 'arrow', 'pitch']
KIDS = {'wall': ['c1', 'c2', 'c3']}


def test_actions_set_each_elements_state_per_frame_and_a_build_steps_through_a_groups_children():
    st = D.states(ACTIONS, [0.0, 0.5, 2.0, 2.5, 3.0], '25', 100, IDS, KIDS)
    assert st[0]['bg']['visible'] and st[0]['title']['visible'] and not st[0]['c1']['visible'] and not st[0]['c3']['visible']   # named by a build: the courses wait
    assert st[13]['c1']['visible'] and not st[13]['c2']['visible'] and st[25]['c2']['visible'] and not st[25]['c3']['visible'] and st[38]['c3']['visible']   # one course every 0.5 s
    assert st[62]['c3']['highlight'] == 1.0 and st[90]['c3']['highlight'] == 0.0
    assert st[50]['flame']['dy'] == 0.0 and st[62]['flame']['dy'] == pytest.approx(-48, abs=2) and st[80]['flame']['dy'] == -100.0   # the move from 2 s over 1 s
    assert st[80]['arrow']['alpha'] < 0.7 and not st[90]['arrow']['visible']   # the fade from 3 s over 0.5 s
    st = D.states([{'kind': 'appear', 'ids': ['wall'], 'at_s': 1}], [1.0], '25', 50, IDS, KIDS)
    assert not st[0]['c1']['visible'] and st[25]['c1']['visible'] and st[25]['c3']['visible']   # appear on a group: all its children at once


def test_cues_come_from_seconds_or_the_timed_narration():
    sh = {'id': 'DR1', 'start_frame': 100, 'end_frame': 200}
    words = [{'text': 'The', 'start_frame': 100, 'end_frame': 104}, {'text': 'cavity', 'start_frame': 140, 'end_frame': 150}, {'text': 'holds', 'start_frame': 160, 'end_frame': 170},
             {'text': 'still', 'start_frame': 171, 'end_frame': 180}, {'text': 'air.', 'start_frame': 181, 'end_frame': 190}]
    scene = {'actions': [{'kind': 'appear', 'ids': ['title'], 'at_s': 0}, {'kind': 'build', 'ids': ['wall'], 'word': 'cavity'}, {'kind': 'highlight', 'ids': ['c3'], 'at_s': 2.5}]}
    assert D.cue_seconds(scene, sh, words, '25') == [0.0, 1.6, 2.5]
    sc = copy.deepcopy(scene)
    sc['actions'][1]['word'] = 'still air'
    assert D.cue_seconds(sc, sh, words, '25')[1] == 2.84
    with pytest.raises(ValueError, match="'cavity' but the run has no timed narration: give at_s"):
        D.cue_seconds(scene, sh, [], '25')
    with pytest.raises(ValueError, match='not spoken inside DR1'):
        D.cue_seconds(scene, {'id': 'DR1', 'start_frame': 0, 'end_frame': 90}, words, '25')


def test_the_sheet_takes_one_frame_every_half_second_and_the_first_and_last():
    assert D.sheet_indexes('25', 100) == [0, 12, 24, 36, 48, 60, 72, 84, 96, 99]
    assert D.sheet_indexes('30', 7) == [0, 6]
    assert D.sheet_indexes('25', 1) == [0]


def test_the_sheet_tiles_the_frames_with_the_time_under_each():
    def png(colour):
        buf = BytesIO()
        Image.new('RGB', (320, 180), colour).save(buf, 'PNG')
        return buf.getvalue()
    frames = {0: png((200, 0, 0)), 12: png((0, 200, 0)), 24: png((0, 0, 200))}
    out = Image.open(BytesIO(D.sheet(frames, '25', 320, 180)))
    assert out.format == 'JPEG' and out.size == (6 * 84 + 4, 45 + 22 + 8)   # six columns of a quarter-size tile, one row, a label line
    assert out.getpixel((10, 10))[0] > 150 and out.getpixel((4 + 84 + 10, 10))[1] > 150 and out.getpixel((4 + 2 * 84 + 10, 10))[2] > 150


def test_the_page_carries_the_scene_at_the_films_size_with_the_font_and_the_pictures_embedded():
    html = D.page_html(SVG, 1920, 1080, {'Noto Sans': b'FONT'}, {'comp-1': ('image/png', b'\x89PNG')})
    assert '<svg width="1920" height="1080"' in html and "@font-face{font-family:'Noto Sans'" in html and 'data:image/png;base64,' in html and 'ref:' not in html
    assert 'animation:none' in html and html.count('<rect') == SVG.count('<rect')
    with pytest.raises(ValueError, match='comp-1'):
        D.page_html(SVG, 1920, 1080, {'Noto Sans': b'FONT'}, {})


def test_outside_names_the_texts_whose_box_leaves_the_safe_area():
    boxes = [{'id': 'ok', 'text': 'fine', 'x': 200, 'y': 100, 'w': 300, 'h': 50}, {'id': 'off', 'text': 'runs off', 'x': 1700, 'y': 100, 'w': 400, 'h': 50},
             {'id': 'low', 'text': 'too low', 'x': 200, 'y': 1040, 'w': 300, 'h': 50}, {'id': 'empty', 'text': '', 'x': 0, 'y': 0, 'w': 0, 'h': 0}]
    assert [b['id'] for b in D.outside(boxes, 1920, 1080)] == ['off', 'low']


def test_the_font_file_is_the_repo_font_or_the_brand_font_and_a_missing_one_fails_by_name(tmp_path):
    assert D.font_file().name == 'NotoSans-Variable.ttf'
    with pytest.raises(ValueError, match='brand.ttf is not there'):
        D.font_file(str(tmp_path / 'brand.ttf'))
    bad = tmp_path / 'bad.ttf'
    bad.write_bytes(b'not a font')
    with pytest.raises(ValueError, match='cannot be read'):
        D.font_file(str(bad))
