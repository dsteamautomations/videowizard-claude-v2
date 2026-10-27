"""Code review of 27 Oct 2026, group B (design/109), the server side: fill shots are filed and referenced by the file that exists (delivery 1);
the nat sound of a stabilised cut sits on the original at its place (delivery 2); a stabilised cut keeps its clip id for the relink list (delivery 3);
EDL timecode counts frames at the nominal rate (delivery 4); a file key never leaves its run (page 3)."""
import xml.etree.ElementTree as ET
from fractions import Fraction

import pytest

from app import web
from app.errors import Problem
from app.stage3 import delivery as D, timeline as T
from test_design107_s1_pure import NARR, TL
from test_visuals_stage_pure import FakeStore

PK = {'sub_clips': [{'sub_clip_id': 'c1:S1', 'clip_id': 'c1', 'clip_name': 'C0120.MP4', 'source_fps': '50', 'zoom': 1.2, 'position': [0.05, -0.02], 'horizon_rotation_deg': 0, 'color_group': 'G1'}],
      'timeline': TL}
STAB = {'kind': 'event', 'sub_clip_id': 'c1:S1', 'source_in_frame': 1000, 'source_out_frame': 1200, 'timeline_in_frame': 0, 'timeline_out_frame': 100, 'timeline_frames': 100,
        'crop': 'solver', 'approved_from_option': 1, 'stabilize': True, 'a2_intervals': [{'in_frame': 1040, 'out_frame': 1100}]}
FILLS = [{'kind': 'fill', 'shot_id': 'DG1', 'file': {'name': 'DG1-asset.png'}, 'media': {'kind': 'still'}, 'timeline_in_frame': 100, 'timeline_out_frame': 175, 'timeline_frames': 75},
         {'kind': 'fill', 'shot_id': 'VS1', 'file': {'name': 'ref-abc.png'}, 'media': {'kind': 'video'}, 'timeline_in_frame': 175, 'timeline_out_frame': 300, 'timeline_frames': 125},
         {'kind': 'fill', 'shot_id': 'VS2', 'file': {'name': 'VS2.mp4'}, 'media': {'kind': 'video'}, 'timeline_in_frame': 300, 'timeline_out_frame': 400, 'timeline_frames': 100}]


# ---------- delivery 1: the fill's file is the one assembly rendered ----------

def test_fill_shots_are_filed_under_ai_and_referenced_by_the_rendered_file():
    asm = {'events': [STAB] + FILLS}
    names = D.fill_names(asm)
    assert names == {'DG1.mp4', 'VS1.mp4', 'VS2.mp4'}
    assert D.layout('normalised', 'DG1.mp4', names) == 'Media/AI/DG1.mp4' and D.layout('normalised', 'c1-S1-0.mp4', names) == 'Media/Camera/Stabilised/c1-S1-0.mp4'
    rows = D.resolve_events(asm, PK, {})
    assert [r['file'] for r in rows[1:]] == ['Media/AI/DG1.mp4', 'Media/AI/VS1.mp4', 'Media/AI/VS2.mp4'] and rows[1]['kind'] == 'still' and rows[2]['kind'] == 'movie'


# ---------- delivery 2 and 3: a stabilised cut's nat sound and clip id ----------

def test_a_stabilised_cut_keeps_its_clip_id_and_its_nat_sound_on_the_original_in_place():
    row = D.resolve_events({'events': [STAB]}, PK, {})[0]
    assert row['file'] == 'Media/Camera/Stabilised/c1-S1-0.mp4' and row['clip_id'] == 'c1' and row['stabilized']
    assert row['a2_file'] == 'Media/Camera/C0120.MP4' and row['a2_source_fps'] == '50' and row['a2_source_in_frame'] == 1000
    root = ET.fromstring(T.fcpxml('VW-9', TL, [row], NARR, [], [], film_frames=100))
    assets = {a.get('id'): a.find('media-rep').get('src') for a in root.findall('./resources/asset')}
    nat = next(c for c in root.iter('asset-clip') if c.get('lane') == '-2')
    assert assets[nat.get('ref')].endswith('Media/Camera/C0120.MP4')
    assert Fraction(nat.get('offset').rstrip('s')) == Fraction(40, 50) and Fraction(nat.get('start').rstrip('s')) == Fraction(1040, 50) and Fraction(nat.get('duration').rstrip('s')) == Fraction(60, 50)
    plain = T.fcpxml('VW-9', TL, [{**row, 'stabilized': False, 'file': 'Media/Camera/C0120.MP4', 'source_in_frame': 1000, 'source_out_frame': 1200, 'source_fps': '50'}], NARR, [], [], film_frames=100)
    nat = next(c for c in ET.fromstring(plain).iter('asset-clip') if c.get('lane') == '-2')
    assert Fraction(nat.get('offset').rstrip('s')) == Fraction(40, 50)   # the same place as on an unstabilised cut


# ---------- delivery 4: EDL timecode ----------

def test_edl_timecode_counts_frames_at_the_nominal_rate():
    assert T.tc(1800, '30000/1001') == '00:01:00:00' and T.tc(107892, '30000/1001') == '00:59:56:12' and T.tc(29, '30000/1001') == '00:00:00:29'
    assert T.tc(100, 25) == '00:00:04:00' and T.tc(3601 * 25 + 7, '25') == '01:00:01:07' and T.tc(Fraction(50), 25) == '00:00:02:00'
    assert T.tc(Fraction(1500) / 50 * 25, 25) == '00:00:30:00'   # a 50 fps source cut, scaled to the timeline's rate


# ---------- delivery 5 and 6: real file lengths, the DTD's audio role ----------

def test_every_media_file_declares_its_real_length_and_audio_roles_are_named_the_dtd_way():
    clips = {'c1': {'duration_s': 120.0, 'fps': '50/1'}}
    plain = {**STAB, 'stabilize': False, 'source_in_frame': 3000, 'source_out_frame': 3100, 'timeline_in_frame': 100, 'timeline_out_frame': 150, 'timeline_frames': 50, 'a2_intervals': []}
    rows = D.resolve_events({'events': [STAB, plain, FILLS[0]]}, PK, {}, clips)
    assert rows[0]['source_frames'] == 100 and rows[0]['a2_source_frames'] == 6000 and rows[1]['source_frames'] == 6000 and rows[2]['source_frames'] == 75
    assert D.clip_frames({}, 'c1') is None and D.resolve_events({'events': [plain]}, PK, {})[0]['source_frames'] is None   # no summary: the reader falls back to the cut
    root = ET.fromstring(T.fcpxml('VW-9', TL, rows, NARR, [], [], film_frames=175))
    dur = {a.get('name'): Fraction(a.get('duration').rstrip('s')) for a in root.findall('./resources/asset')}
    assert dur['C0120.MP4'] == 120 and dur['c1-S1-0.mp4'] == 4 and dur['DG1.mp4'] == 3
    text = ET.tostring(root).decode()
    assert 'audioRole="effects.nat-sound"' in text and 'audioRole="dialogue.voiceover"' in text and ' role=' not in text


# ---------- page 3: a key never leaves its run ----------

def test_a_key_with_dot_segments_is_refused_and_writes_nothing():
    store = FakeStore()
    store.files['run-2/visuals/references/K1.png'] = b'x'
    for key in ('run-1/../run-2/visuals/references/K1.png', 'run-1/./visuals/x.png', 'run-1\\..\\run-2\\x.png'):
        with pytest.raises(Problem):
            web.thumb_response(store, 'run-1', key, None)
        assert not web.own_key('run-1', key)
    assert web.own_key('run-1', 'run-1/visuals/references/K1.png') and not web.own_key('run-1', 'run-10/visuals/K1.png')
    assert [k for k in store.files if k.endswith('.thumb.jpg')] == []
    src = (web.__file__ and open(web.__file__, encoding='utf-8').read())
    assert src.count('own_key(') >= 3   # the thumb route and the file routes
