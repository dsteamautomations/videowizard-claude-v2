"""Stage 2 pieces that need no database (design/43): grouped flags (7.6), default scene titles (7.3), the review film at 720p (7.1)."""
import json
import shutil
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


def test_a_blank_over_twelve_seconds_is_flagged_e2_not_refused():
    """design/85 G1."""
    from app.stage2.validator import long_blank_flag
    assert long_blank_flag(12 * 25, 25, 'OPTION #1 blank at event 2') is None
    f = long_blank_flag(13 * 25, 25, 'OPTION #1 blank at event 2')
    assert f.startswith('OPTION #1 blank at event 2: E2 blank of 13.0 s is over 12 s') and 'footage cut-in' in f
    assert [g['rule'] for g in group_flags([f])] == ['E2']


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


# ---------- design/60 L18: scenes must name chapters when the brief has them ----------

def test_scenes_without_chapters_are_refused_when_the_brief_has_them():
    beats = [{'beat_id': 'BEAT_01', 'passage_id': 'P001', 'text': 'Walls are cured for seven days.'}]
    words = words_for(beats)
    untagged = [{'first_word_id': 'P001-0', 'title': 'Curing', 'process_stages': []}]
    with pytest.raises(ValueError) as exc:
        NR.validate_scenes(words, untagged, ['Mixing the mortar', 'Curing the wall'])
    assert 'process_stages' in str(exc.value) and 'Mixing the mortar, Curing the wall' in str(exc.value) and 'none of the scenes' in str(exc.value)
    NR.validate_scenes(words, [{'first_word_id': 'P001-0', 'title': 'Curing', 'process_stages': ['Curing the wall']}], ['Mixing the mortar', 'Curing the wall'])
    NR.validate_scenes(words, untagged, [])   # a film without chapters: untagged scenes are fine


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


# ---------- design/46 11.1: the assembly film is the full one; 11.6 the limiter; 11.7 the cache folder ----------

def peak_db(path):
    r = subprocess.run(['ffmpeg', '-i', str(path), '-af', 'volumedetect', '-f', 'null', '-'], capture_output=True)
    import re
    return float(re.search(r'max_volume: (-?[0-9.]+) dB', r.stderr.decode(errors='replace')).group(1))


def test_assembly_film_is_1080p_with_the_whole_narration_and_a_loudness_check(tmp_path, narration):
    pytest.importorskip('PIL')
    from app.stage2 import render as R
    plan = {'items': [{'kind': 'slate', 'lines': ['BLANK | BEAT_01 | 50 frames', 'for AI video'], 'frames': 50}]}   # no narration items: the whole recording runs under it
    film, record = R.render_film('assembly', plan, {}, narration, tmp_path / 'a', {'width': 1920, 'height': 1080, 'fps': 25})
    v = ffprobe_stream(film)
    assert v['width'] == 1920 and v['height'] == 1080 and record['mix'] is not None and 'made at this size' not in record['codec']
    lc = record['loudness_check']
    assert lc['peak_ceiling_dbtp'] == -3 and lc['integrated_target_lufs'] == -16 and set(lc) >= {'integrated_lufs', 'true_peak_dbfs', 'peak_inside', 'integrated_inside'}


def test_the_mix_of_a_delivered_film_is_limited_to_minus_three(tmp_path):
    from app.stage2 import render as R
    loud = tmp_path / 'loud.wav'
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'lavfi', '-i', "aevalsrc=0.999*sin(2*PI*440*t):s=48000:c=stereo", '-t', '1', str(loud)], check=True, capture_output=True)
    assert peak_db(loud) > -0.5
    r = R.Renderer(tmp_path / 'w', {'width': 320, 'height': 180, 'fps': 25})
    out = r.mix(loud, [], 1.0, tmp_path / 'mix.wav', limit=True)
    assert peak_db(out) <= -2.9
    plain = r.mix(loud, [], 1.0, tmp_path / 'plain.wav')
    assert peak_db(plain) > -0.5


def test_renderer_uses_the_cache_folder_it_is_given(tmp_path):
    pytest.importorskip('PIL')
    from app.stage2 import render as R
    cache = tmp_path / 'run-cache'
    r = R.Renderer(tmp_path / 'w', {'width': 320, 'height': 180, 'fps': 25}, cache=cache)
    seg = r.slate(['x'], 5)
    assert seg.parent == cache and (tmp_path / 'w' / 'cache').exists() is False


# ---------- design/46 11.2: the take evidence carries colour tags and rotation ----------

def test_probe_reports_colour_tags_and_rotation(tmp_path):
    from app.visual_workers import probe
    untagged = tmp_path / 'u.mp4'
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'lavfi', '-i', 'color=c=0x204060:s=64x64:r=25:d=1', '-pix_fmt', 'yuv420p', str(untagged)], check=True, capture_output=True)
    tagged = tmp_path / 't.mp4'
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'lavfi', '-i', 'color=c=0x204060:s=64x64:r=25:d=1', '-vf', 'format=yuv420p,setparams=color_primaries=bt709:color_trc=bt709:colorspace=bt709',
                    '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709', str(tagged)], check=True, capture_output=True)
    u, t = probe(untagged), probe(tagged)
    assert u['issues'] == ['colour untagged'] and u['rotation_deg'] == 0 and u['duration_seconds'] == pytest.approx(1.0, abs=0.05)
    assert t['issues'] == [] and t['color_transfer'] == 'bt709' and t['color_primaries'] == 'bt709'


# ---------- design/65 B8: a graphic sequence of stills ----------

def png(path, colour):
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'lavfi', '-i', f'color=c={colour}:s=64x48', '-frames:v', '1', str(path)], check=True)


def frames_of(path):
    out = subprocess.run(['ffprobe', '-v', 'error', '-count_frames', '-select_streams', 'v:0', '-show_entries', 'stream=nb_read_frames', '-of', 'csv=p=0', str(path)], capture_output=True, text=True, check=True).stdout
    return int(out.strip())


@pytest.mark.skipif(not (shutil.which('ffmpeg') and shutil.which('ffprobe')), reason='ffmpeg not installed')
def test_a_graphic_sequence_renders_exactly_the_shot_frames_with_dissolves(tmp_path):
    from app.stage2.render import Renderer
    pngs = [tmp_path / f's{i}.png' for i in range(3)]
    for p, c in zip(pngs, ('red', 'green', 'blue')):
        png(p, c)
    r = Renderer(tmp_path / 'work', {'width': 64, 'height': 48, 'fps': 25})
    out = r.sequence([(pngs[0], 'a', 25), (pngs[1], 'b', 25), (pngs[2], 'c', 25)], dissolve=5, n_tl=75)
    assert out.exists() and frames_of(out) == 75
    again = r.sequence([(pngs[0], 'a', 25), (pngs[1], 'b', 25), (pngs[2], 'c', 25)], dissolve=5, n_tl=75)
    assert again == out   # cached by the states, the holds, the dissolve and the length
    single = r.sequence([(pngs[0], 'a', 30)], dissolve=5, n_tl=30)
    assert frames_of(single) == 30
    plain = r.sequence([(pngs[0], 'a', 10), (pngs[1], 'b', 15)], dissolve=0, n_tl=25)
    assert frames_of(plain) == 25


# ---------- design/71 P4: two takes sharing a boundary picture are cross-faded over six frames; the timeline length is unchanged ----------

@pytest.mark.skipif(not (shutil.which('ffmpeg') and shutil.which('ffprobe')), reason='ffmpeg not installed')
def test_dissolve_pair_renders_exactly_n1_plus_n2_frames(tmp_path):
    from app.stage2.render import Renderer
    r = Renderer(tmp_path / 'work', {'width': 64, 'height': 48, 'fps': 25})
    a, b = r.slate(['a'], 31), r.slate(['b'], 25)   # the first piece carries its six-frame tail
    out = r.dissolve_pair(a, 31, b, 25, 6)
    assert out.exists() and frames_of(out) == 50
    assert r.dissolve_pair(a, 31, b, 25, 6) == out   # cached


@pytest.mark.skipif(not (shutil.which('ffmpeg') and shutil.which('ffprobe')), reason='ffmpeg not installed')
def test_render_film_dissolves_a_fill_into_the_next_from_its_spare_tail(tmp_path, narration):
    pytest.importorskip('PIL')
    from app.stage2 import render as R
    clip = tmp_path / 'take.mp4'
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'lavfi', '-i', 'color=c=red:s=64x48:r=25:d=2', '-pix_fmt', 'yuv420p', str(clip)], check=True, capture_output=True)

    def take(sid, **extra):
        return {'kind': 'event', 'sub_clip_id': sid, 'clip': {'id': sid, 'name': 't.mp4', 'sha256': sid, 'fps': '25', 'rotation_deg': 0.0, 'hdr': False},
                'source_in_frame': 0, 'source_out_frame': 25, 'timeline_frames': 25, 'crop_rect': None, 'hold_last_frame': False, 'a2': [], **extra}
    plan = {'items': [take('VS1', dissolve_into_next=6, normalised_key='n/VS1.mp4'), take('VS2', normalised_key='n/VS2.mp4')]}
    film, record = R.render_film('assembly', plan, {'VS1': clip, 'VS2': clip}, narration, tmp_path / 'w', {'width': 64, 'height': 48, 'fps': 25})
    assert record['frames'] == 50 and frames_of(film) == 50
    assert [k for k, _ in record['normalised_segments']] == ['n/VS1.mp4', 'n/VS2.mp4'] and frames_of(Path(record['normalised_segments'][0][1])) == 25   # the delivered piece is the plain take
