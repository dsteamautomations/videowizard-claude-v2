"""Stage 2 pieces that need no database (design/43): grouped flags (7.6), default scene titles (7.3), the review film at 720p (7.1)."""
import json
import subprocess
from pathlib import Path

import pytest

from app.stage2 import narration as NR
from app.stage2.validator import group_flags


# ---------- 7.6 flags grouped by rule ----------

def test_group_flags_counts_per_rule_with_three_examples():
    flags = [f'OPTION #1 shot {i} (c:{i}): R1 in-point is not at a natural cut point' for i in range(1, 6)]
    flags += ['OPTION #2 shot 1 (c:9): R10 colour group changes inside the beat', 'OPTION #2 shot 2 (c:8): R10 colour group changes inside the beat',
              'OPTION #3 shot 1 (c:7): rule 11 real shot of 5.0 s: cut it to the part that carries the meaning, or give hold_reason',
              'OPTION #4 blank at event 2: E1 blank of 2.0 s is under 3 s; the operator decides (fast cut)',
              'R4: three consecutive beats with the same peak energy', "OPTION #5 shot 1 (c:6): B2 the word 'laid' is not within 6 frames of the shot's action accent"]
    grouped = group_flags(flags)
    assert [(g['rule'], g['count']) for g in grouped] == [('R1', 5), ('R10', 2), ('B2', 1), ('E1', 1), ('R4', 1), ('rule 11', 1)]
    assert len(grouped[0]['examples']) == 3 and grouped[0]['examples'][0].startswith('OPTION #1 shot 1')
    assert group_flags([]) == []


def test_group_flags_keeps_an_unknown_shape_under_other():
    assert group_flags(['something the validator said'])[0]['rule'] == 'other'


# ---------- 7.3 default scene titles ----------

def words_for(beats):
    out = []
    for b in beats:
        for i, w in enumerate(b['text'].split()):
            out.append({'id': f"{b['passage_id']}-{i}", 'text': w, 'passage_id': b['passage_id'], 'start_s': 0.0, 'end_s': 0.1})
    return out


def test_paragraph_scenes_are_titled_by_their_first_six_words():
    beats = [{'beat_id': 'BEAT_01', 'passage_id': 'P001', 'text': 'As the demand for affordable housing continues to grow, the sector faces a challenge.'},
             {'beat_id': 'BEAT_02', 'passage_id': 'P002', 'text': 'Walls are cured for seven days.'},
             {'beat_id': 'BEAT_03', 'passage_id': 'P003', 'text': 'Six words make one whole title.'}]
    scenes = NR.paragraph_scenes(beats, words_for(beats))
    assert [s['title'] for s in scenes] == ['As the demand for affordable housing…', 'Walls are cured for seven days.', 'Six words make one whole title.']
    assert scenes[0]['first_word_id'] == 'P001-0' and scenes[0]['process_stages'] == []


# ---------- 7.1 review films at 1280×720, master at 1920×1080 ----------

def ffprobe_stream(path):
    out = subprocess.run(['ffprobe', '-v', 'error', '-show_streams', '-of', 'json', str(path)], capture_output=True, check=True).stdout
    return next(s for s in json.loads(out)['streams'] if s['codec_type'] == 'video')


@pytest.fixture
def narration(tmp_path):
    p = tmp_path / 'narration.wav'
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'lavfi', '-i', 'anullsrc=r=48000:cl=stereo', '-t', '2', str(p)], check=True, capture_output=True)
    return p


@pytest.mark.parametrize('kind,width,height', [('review', 1280, 720), ('assembly', 1920, 1080)])
def test_render_film_sizes_the_watched_films_and_keeps_the_delivered_one(tmp_path, narration, kind, width, height):
    pytest.importorskip('PIL')
    from app.stage2 import render as R
    plan = {'items': [{'kind': 'slate', 'lines': ['#01 | Scene 1: As the demand…', 'Clips: none'], 'frames': 25}, {'kind': 'narration', 'start_s': 0.0, 'end_s': 1.0}]}
    work = tmp_path / kind
    film, record = R.render_film(kind, plan, {}, narration, work, {'width': 1920, 'height': 1080, 'fps': 25})
    v = ffprobe_stream(film)
    assert v['width'] == width and v['height'] == height and v['codec_name'] == 'h264'
    if kind == 'review':
        assert record['mix'] is None and '1280x720' in record['codec'] and not (work / 'review-720p.mp4').exists()
    else:
        assert record['mix'] is not None and 'bt709' in record['codec']


# ---------- 7.8 a version answers the package it was checked against ----------

class Store:
    def __init__(self, files):
        self.files = files

    def get(self, k):
        return json.dumps(self.files[k]).encode('utf-8')


def test_a_version_whose_package_changed_is_refused():
    from app.errors import Problem
    from app.stage2 import stage
    session = {'package': {'digest': 'now'}}
    entry = {'version': 3, 'file': {'key': 'v3'}}
    stage._same_package(Store({'v3': {'package_digest': 'now'}}), session, entry)        # same package: fine
    stage._same_package(Store({'v3': {}}), session, entry)                               # a version from before the digest was stored: fine
    with pytest.raises(Problem) as exc:
        stage._same_package(Store({'v3': {'package_digest': 'before'}}), session, entry)
    assert exc.value.status == 409 and 'version 3' in exc.value.message and 'propose' in exc.value.message


# ---------- design/44 8.1: slide labels (numbers for options and backups, letters inside) ----------

def small_package():
    return {'beats': [{'beat_id': 'BEAT_01', 'title': 'Laying the first course', 'timeline_start_frame': 0, 'timeline_end_frame': 250, 'target_beat_frames': 250},
                      {'beat_id': 'BEAT_02', 'title': 'Curing', 'timeline_start_frame': 250, 'timeline_end_frame': 350, 'target_beat_frames': 100}],
            'sub_clips': [{'sub_clip_id': 'c1:SUB_01', 'clip_id': 'c1', 'clip_name': 'C0120.MP4'}, {'sub_clip_id': 'c2:SUB_01', 'clip_id': 'c2', 'clip_name': 'C0121.MP4'}],
            'cards': [{'clip_id': 'c1', 'descriptive_name': 'brick_stacking'}]}


def small_doc():
    shot = lambda sid, n, **kw: {'sub_clip_id': sid, 'source_in_frame': 0, 'source_out_frame': n, 'timeline_frames': n, 'match': 'direct', 'evidence': 'x', **kw}
    return {'options': [{'option_number': 1, 'beat_id': 'BEAT_01', 'rank': 'PRIMARY',
                         'events': [shot('c1:SUB_01', 75), {'blank': True, 'timeline_frames': 100, 'intent': 'a diagram'},
                                    shot('c2:SUB_01', 75, decision={'kind': 'b_roll', 'question': 'Related footage: keep or drop?'})]},
                        {'option_number': 2, 'beat_id': 'BEAT_01', 'rank': 'SECONDARY', 'events': [shot('c2:SUB_01', 250)]},
                        {'option_number': 3, 'beat_id': 'BEAT_02', 'rank': 'PRIMARY', 'events': [shot('c1:SUB_01', 100)]}],
            'gaps': []}


def test_slides_take_running_numbers_and_letters_inside_an_option():
    from app.stage2 import slides as SL
    sl = SL.slides(small_doc(), small_package(), 25)
    assert [(s['no'], s['type']) for s in sl] == [('1', 'option'), ('1A', 'blank'), ('1B', 'decision'), ('2', 'backup'), ('3', 'option')]
    assert sl[3]['backup_for'] == '1' and sl[3]['lines'][0].startswith('#2 | Scene 1: Laying the first course | BACKUP for #1 |')
    assert sl[1]['lines'][0].startswith('#1A | BLANK | Scene 1') and sl[2]['lines'][0] == '#1B | DECISION | Scene 1: Laying the first course'
    assert sl[4]['lines'][0].startswith('#3 | Scene 2: Curing |') and all(s['number'] == int(s['no'][0]) for s in sl)
    assert SL.letter(1) == 'A' and SL.letter(26) == 'Z' and SL.letter(27) == 'AA'


def test_review_items_carry_the_labels():
    from app.stage2 import slides as SL
    doc, pk = small_doc(), small_package()
    items = SL.review_items(doc, pk, SL.slides(doc, pk, 25), lambda evs: [{'kind': 'event', 'frames': e['timeline_frames']} for e in evs], 25)
    labels = [it.get('label') for it in items if it['kind'] == 'event']
    assert labels == ['#1', '#1B DECISION', '#2', '#3']


def test_slate_head_accepts_a_letter(tmp_path):
    pytest.importorskip('PIL')
    from app.stage2 import render as R
    assert R.SLATE_HEAD.match('#2B | DECISION | Scene 2').group(1) == '#2B' and R.SLATE_HEAD.match('#12 | Scene 5').group(1) == '#12'
    R.slate_png(['#2B | DECISION | Scene 2', 'Keep or drop?'], 320, 180, tmp_path / 's.png')
    assert (tmp_path / 's.png').exists()


def test_decide_label_normalisation():
    from app.stage2 import stage
    assert stage.slide_label('#2b') == '2B' and stage.slide_label(7) == '7' and stage.slide_label(' 1a ') == '1A'


# ---------- design/44 8.3: the master film at 720p with its sound measured ----------

def test_master_film_is_720p_and_still_measured(tmp_path, narration):
    pytest.importorskip('PIL')
    from app.stage2 import render as R
    plan = {'items': [{'kind': 'slate', 'lines': ['#1 | Scene 1', 'x'], 'frames': 25}]}
    film, record = R.render_film('master', plan, {}, narration, tmp_path / 'm', {'width': 1920, 'height': 1080, 'fps': 25})
    v = ffprobe_stream(film)
    assert v['width'] == 1280 and v['height'] == 720 and record['mix'] is not None and 'master, made at this size' in record['codec']
