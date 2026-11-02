"""design/142 R5 (SK, 2 Nov 2026, design/140 Q4): the server measures each clip's look (brightness, warmth, colour strength) and groups clips that look
alike, log footage only with log; R1 fires only when a natural cut point was within reach and not used."""
from PIL import Image

from app.stage2 import looks as LK, validator as V


def picture(path, rgb):
    Image.new('RGB', (64, 36), rgb).save(path)
    return path


def test_a_look_is_measured_from_pictures(tmp_path):
    warm = LK.look_of([picture(tmp_path / 'a.png', (200, 150, 100)), picture(tmp_path / 'b.png', (190, 140, 90))])
    assert warm['brightness'] > 0.5 and warm['warmth'] > 0.2 and 0 < warm['strength'] < 1
    assert LK.look_of([]) is None


def test_clips_that_look_alike_are_one_group_and_a_different_one_splits():
    day = {'brightness': 0.62, 'warmth': 0.12, 'strength': 0.35, 'log': False}
    looks = {'c1': day, 'c2': {**day, 'brightness': 0.66}, 'c3': {**day, 'warmth': 0.10}, 'night': {'brightness': 0.15, 'warmth': -0.2, 'strength': 0.1, 'log': False}}
    g = LK.groups(looks)
    assert g['c1'] == g['c2'] == g['c3'] and g['night'] != g['c1']


def test_log_footage_is_grouped_only_with_log_and_an_unknown_look_has_no_group():
    day = {'brightness': 0.62, 'warmth': 0.12, 'strength': 0.35, 'log': False}
    g = LK.groups({'a': day, 'b': {**day, 'log': True}, 'c': None})
    assert g['a'] != g['b'] and g['c'] is None


def test_r1_fires_only_when_a_natural_cut_was_within_reach_and_unused():
    assert V.natural_cut_missed(100, [108], 2) is True      # 8 source frames = 4 timeline frames away at 50 over 25 fps: within reach
    assert V.natural_cut_missed(100, [100], 2) is False     # used
    assert V.natural_cut_missed(100, [160], 2) is False     # 30 timeline frames away: not within reach
    assert V.natural_cut_missed(100, [], 2) is False


# ---------- R6: the second look sees the shot as cut (design/140 Q5; design/141 point 8, Q4) ----------

def test_stills_cover_the_shot_as_cut():
    from app.stage2 import stage as S
    assert S.still_times(2.0, 5.0, 1.0) == [2.0, 3.0, 3.5, 4.0, 4.96]   # first, every second, the middle, the last frame (at 25 fps)
    assert S.still_times(2.0, 2.6, 1.0) == [2.0, 2.3, 2.56]             # under a second: first, middle, last
    half = S.still_times(0.0, 3.0, 0.5)
    assert half[:4] == [0.0, 0.5, 1.0, 1.5] and len(half) == 7
