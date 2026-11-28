"""Text overlays, build step 2 (requirements version 3 of 28 Nov 2026, part E): one overlay as a HyperFrames page. The card, the motion, the font, the
size and the place are settings of one template for each kind, never separate templates. The same page gives the still picture and the clip."""
import re

import pytest

from app import motion
from app import overlay_template as T
from app import overlays as O

FILM = {'fps': 25, 'frames': 400, 'cuts': [{'name': 'S01-1', 'start_frame': 0, 'end_frame': 400}],
        'words': [{'start_frame': i * 10, 'end_frame': i * 10 + 8, 'text': f'w{i + 1}'} for i in range(40)], 'font': 'Inter', 'scripts': ['latin']}
WIDE = {'fps': 25, 'width': 1920, 'height': 1080, 'accent': '#c8643c', 'fonts': [{'family': 'Inter', 'file': 'Inter-Variable.ttf', 'bold': False}]}
TALL = {**WIDE, 'width': 1080, 'height': 1920}


def row(**k):
    out = O.check({'overlays': [{'kind': 'callout', 'lines': ['Significant cost savings'], 'word': 3, **k}]}, FILM)
    assert out['problems'] == [], out['problems']
    return out['rows'][0]


def page(film=WIDE, **k):
    return T.page(row(**k), film)


def test_the_page_is_a_whole_hyperframes_page_as_long_as_the_overlay_with_only_the_servers_own_files():
    p = page()   # 3 words: 2.2 s = 55 frames
    assert p.startswith('<!doctype html>') and 'data-composition-id="main"' in p and 'data-duration="2.200"' in p and 'data-fps="25"' in p
    assert 'data-width="1920"' in p and 'data-height="1080"' in p and 'window.__timelines["main"] = tl' in p
    assert 'src="assets/vendor/gsap.min.js"' in p and "url('assets/fonts/Inter-Variable.ttf')" in p
    assert not motion.EXTERNAL.search(p) and not motion.NONDET.search(p)   # nothing from the network, nothing that draws differently twice
    assert 'background: transparent' in p


def test_the_words_are_whole_lines_and_are_written_safely():
    p = page(lines=['Fish & <chips>', 'Two weeks'])
    assert p.count('class="ln"') == 2 and 'Fish &amp; &lt;chips&gt;' in p and '>Two weeks<' in p   # a line is one box, never a box a word (the trial's lost spaces)


def test_the_same_overlay_gives_the_same_page_twice():
    assert page() == page()


def test_sizes_follow_the_shorter_side_and_the_three_sizes():
    assert 'font-size:62px' in page() and 'font-size:62px' in page(TALL)   # 5.7 % of 1080, in both shapes
    assert 'font-size:49px' in page(size='small') and 'font-size:77px' in page(size='large')
    assert 'font-size:46px' in page(kind='title') and 'font-size:140px' in page(kind='number', lines=['25 %', 'fewer bricks'])
    half = page({**WIDE, 'width': 960, 'height': 540})
    assert 'font-size:31px' in half and 'data-width="960"' in half


def test_the_weight_is_the_operators():
    assert 'font-weight:700' in page(weight='bold') and 'font-weight:500' in page(weight='regular')


@pytest.mark.parametrize('card, css', [
    ('dark', 'background: rgba(20, 20, 20, 0.55); color: #ffffff'),
    ('cream', 'background: rgba(246, 239, 226, 0.94); color: #2a2622'),
    ('bare', 'background: rgba(0, 0, 0, 0); color: #ffffff'),
    ({'ground': '#102030', 'opacity': 80, 'text': '#ffee00'}, 'background: rgba(16, 32, 48, 0.8); color: #ffee00'),
])
def test_the_card_is_its_settings(card, css):
    assert css in page(card=card)


def test_the_corner_the_border_and_the_accent_come_from_the_card():
    assert 'border-radius: 0px' in page(card={'corner': 'square'}) and 'border-radius: 999px' in page(card={'corner': 'pill'}) and 'border-radius: 14px' in page()
    assert 'border-left: 6px solid #c8643c' in page(card='bar')            # the bar is in the film's accent colour
    assert 'border: 2px solid #aabbcc' in page(card={'border': '#aabbcc'})
    assert '.em { color: #ff0000; }' in page(card={'accent': '#ff0000'}) and '.em { color: #c8643c; }' in page()
    assert '.em { color: #ffffff; }' in page({**WIDE, 'accent': None})    # a film that names no colour: the text's own
    assert 'text-shadow' in page(card='bare') and 'text-shadow' not in page(card='dark')   # bare text stays readable by its shadow


def test_one_phrase_is_stressed_once():
    p = page(stress='cost savings')
    assert p.count('<span class="em">cost savings</span>') == 1 and '>Significant <span' in p
    assert 'class="em"' not in page(stress='not in the words')


@pytest.mark.parametrize('place, css', [
    ('top left', 'left:5%;top:6.5%;transform:translate(0px, 0px)'),
    ('top', 'left:50%;top:6.5%;transform:translate(-50%, 0px)'),
    ('right', 'right:5%;top:50%;transform:translate(0px, -50%)'),
    ('centre', 'left:50%;top:50%;transform:translate(-50%, -50%)'),
    ('bottom left', 'left:5%;bottom:21%;transform:translate(0px, 0px)'),
    ('bottom right', 'right:5%;bottom:21%;transform:translate(0px, 0px)'),
    ({'x': 62, 'y': 30}, 'left:62%;top:30%;transform:translate(-50%, -50%)'),
])
def test_the_place_is_one_of_nine_or_a_spot(place, css):
    assert css in page(place=place)


def test_a_shift_moves_it_by_a_share_of_the_frame():
    assert 'transform:translate(calc(-50% + 96px), calc(-50% + -54px))' in page(place='centre', shift={'x': 5, 'y': -5})
    assert 'transform:translate(96px, 0px)' in page(place='top left', shift={'x': 5})


def timeline(p):
    return p[p.index('const tl ='):p.index('window.__timelines')]


def test_each_motion_is_its_own_entry_and_all_but_cut_leave_softly():
    code = {m: timeline(page(motion=m)) for m in O.MOTIONS}
    assert len(set(code.values())) == len(O.MOTIONS)
    assert 'clipPath' in code['wipe'] and 'clipPath' not in code['fade'] and "y: 24" in code['rise'] and 'x: -' in code['slide']
    assert 'fromTo' not in code['cut'] and "tl.set('#card', {opacity: 1}, 0)" in code['cut'] and "tl.to('#card', {opacity: 0" not in code['cut']
    for m in ('wipe', 'fade', 'rise', 'slide'):
        assert "tl.to('#card', {opacity: 0" in code[m] and 'bounce' not in code[m] and 'elastic' not in code[m]
    assert 'x: 1' in timeline(page(motion='slide', place='right'))   # from the side it sits on


def test_a_list_builds_item_by_item_on_its_words_in_every_motion():
    r = dict(kind='list', heading='Materials', lines=['Cement', 'Steel', 'Sand'], item_words=[3, 9, 14])
    p = page(**r)
    assert '>Materials<' in p and p.count('class="item"') == 3 and p.count('class="tick"') == 3
    code = timeline(p)   # the list starts at frame 20; the items come at 0.25 (never before the card), 2.4 and 4.4 seconds
    assert "'#i0'" in code and ', 0.250);' in code and ', 2.400);' in code and ', 4.400);' in code
    for m in O.MOTIONS:
        assert timeline(page(motion=m, **r)).count("'#i") >= 3
    both = timeline(page(kind='list', lines=['Cement', 'Steel'], word=3, all_at_once=True))
    assert both.count(', 0.250);') >= 2


def test_a_number_shows_its_figure_large_and_its_line_small_and_a_name_its_two_lines():
    p = page(kind='number', lines=['25 %', 'fewer bricks'])
    assert re.search(r'font-size:140px[^>]*>25 %<', p) and re.search(r'font-size:40px[^>]*>fewer bricks<', p)
    p = page(kind='name', lines=['Dr Meena Rao', 'Structural engineer'])
    assert re.search(r'font-size:46px[^>]*>Dr Meena Rao<', p) and re.search(r'font-size:32px[^>]*>Structural engineer<', p)


def test_every_font_file_of_the_film_is_declared_and_the_overlays_own_font_is_first():
    film = {**WIDE, 'fonts': [{'family': 'Noto Sans', 'file': 'NotoSans-wdth-wght.ttf', 'bold': False}, {'family': 'Noto Sans Tamil', 'file': 'NotoSansTamil-wdth-wght.ttf', 'bold': False}]}
    p = T.page(row(), film)
    assert "url('assets/fonts/NotoSans-wdth-wght.ttf')" in p and "url('assets/fonts/NotoSansTamil-wdth-wght.ttf')" in p
    assert "font-family: 'Noto Sans', 'Noto Sans Tamil', 'Noto Sans', sans-serif" in p


def test_the_moment_of_the_still_picture_is_when_everything_is_in():
    assert T.still_at(row(), 25) == pytest.approx(1.1)                      # half of a 2.2 s overlay: the entry is over, the exit not begun
    r = row(kind='list', lines=['Cement', 'Steel', 'Sand'], item_words=[3, 9, 14])
    assert T.still_at(r, 25) == pytest.approx((130 - 20) / 25 + 0.6)       # a list: after its last item has come in
