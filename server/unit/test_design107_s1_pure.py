"""design/107 slice 1: the timeline file (FCPXML) with a reader of our own, the EDL, Relink-list.csv, the bundle's new layout and OPEN-EDIT."""
import csv
import io
import xml.etree.ElementTree as ET
from fractions import Fraction

from app.stage3 import delivery as D, timeline as T

TL = {'width': 1920, 'height': 1080, 'fps': 25}


def ev(file, kind, s_in, s_out, r_in, r_out, src_fps='25', zoom=1.0, pan=0.0, tilt=0.0, rot=0.0, group=None, name='x', a2=(), stab=False, frames=None):
    return {'file': file, 'kind': kind, 'source_in_frame': s_in, 'source_out_frame': s_out, 'record_in_frame': r_in, 'record_out_frame': r_out, 'source_fps': src_fps,
            'zoom': zoom, 'pan': pan, 'tilt': tilt, 'rotation': rot, 'color_group': group, 'marker': {'name': name, 'note': 'option #1', 'colour': 'Blue'},
            'a2': list(a2), 'stabilized': stab, **({'source_frames': frames} if frames else {})}


EVENTS = [ev('Media/Camera/C0120.MP4', 'camera', 250, 350, 0, 100, '25', zoom=1.2, pan=0.05, tilt=-0.02, rot=1.5, group='G1', name='c1:S1', a2=[{'in_frame': 260, 'out_frame': 300}], frames=3000),
          ev('Media/Camera/Stabilised/c2-S1-100.mp4', 'camera', 0, 50, 100, 150, '25', name='c2:S1', stab=True),
          ev('Media/Camera/C0130.MOV', 'camera', 1500, 1600, 150, 200, '50', name='c3:S2', frames=6000),   # a 50 fps source: 100 source frames fill 50 timeline frames (2 s)
          ev('Media/AI/VS1.mp4', 'movie', 0, 125, 200, 325, '25', name='VS1'),
          ev('Media/AI/DG1-asset.png', 'still', 0, 75, 325, 400, '25', name='DG1')]
NARR = [{'file': 'Media/Voiceover/narration.mp3', 'source_in_frame': 0, 'source_out_frame': 400, 'record_in_frame': 0}]
FINISHING = [{'item': 'Stabilise c2:S1 in Resolve', 'timeline_in_frame': 100}]
SFX = [{'sub_clip_id': 'c1:S1', 'sfx_type': 'trowel', 'description': 'trowel scraping', 'start_tc': '00:00:01:00'}]


def doc():
    return T.fcpxml('VW-9', TL, EVENTS, NARR, FINISHING, SFX, film_frames=400)


def frames(s):
    """'12/25s' or '3s' -> timeline frames at 25."""
    v = Fraction(s.rstrip('s'))
    return int(v * 25)


# ---------- the timeline file ----------

def test_the_timeline_file_has_the_films_format_one_asset_per_file_and_every_cut_at_its_frame():
    root = ET.fromstring(doc())
    assert root.tag == 'fcpxml' and root.get('version') == '1.9'
    fmt = root.find('./resources/format')
    assert fmt.get('frameDuration') == '1/25s' and fmt.get('width') == '1920' and fmt.get('height') == '1080'
    assets = {a.find('media-rep').get('src'): a for a in root.findall('./resources/asset')}
    assert set(assets) == {'file://./Media/Camera/C0120.MP4', 'file://./Media/Camera/Stabilised/c2-S1-100.mp4', 'file://./Media/Camera/C0130.MOV', 'file://./Media/AI/VS1.mp4',
                           'file://./Media/AI/DG1-asset.png', 'file://./Media/Voiceover/narration.mp3', 'file://./Approved-film.mp4'}
    seq = root.find('.//sequence')
    assert seq.get('duration') == '16s' and seq.get('format') == fmt.get('id')
    video = [c for c in root.iter('asset-clip') if c.get('lane') == '1']
    assert [(frames(c.get('offset')), frames(c.get('duration'))) for c in video] == [(0, 100), (100, 50), (150, 50), (200, 125), (325, 75)]
    c3 = video[2]   # the 50 fps source: the start is in source time, 1500/50 s = 30 s
    assert Fraction(c3.get('start').rstrip('s')) == 30 and frames(c3.get('duration')) == 50


def test_the_transform_is_relative_to_the_frame_and_a_stabilised_copy_has_none():
    root = ET.fromstring(doc())
    video = [c for c in root.iter('asset-clip') if c.get('lane') == '1']
    t = video[0].find('adjust-transform')
    assert t.get('scale') == '1.2 1.2' and t.get('position') == '0.05 -0.02' and t.get('rotation') == '1.5'
    assert video[1].find('adjust-transform') is None and video[3].find('adjust-transform') is None


def test_the_voiceover_the_nat_sound_and_the_reference_track_are_connected_with_their_lanes():
    root = ET.fromstring(doc())
    a1 = [c for c in root.iter('asset-clip') if c.get('lane') == '-1']
    assert len(a1) == 1 and frames(a1[0].get('offset')) == 0 and frames(a1[0].get('duration')) == 400 and a1[0].get('role') == 'dialogue.voiceover'
    a2 = [c for c in root.iter('asset-clip') if c.get('lane') == '-2']
    assert len(a2) == 1 and frames(a2[0].get('offset')) == 10 and frames(a2[0].get('duration')) == 40 and a2[0].get('role') == 'effects.nat-sound'   # 260-250 frames into the cut
    ref = [c for c in root.iter('asset-clip') if c.get('lane') == '2']
    assert len(ref) == 1 and ref[0].get('enabled') == '0' and ref[0].get('name') == 'REFERENCE – approved film' and frames(ref[0].get('duration')) == 400
    assert root.find('.//spine/gap').get('duration') == '16s'   # the primary story: one gap the length of the film, everything connected to it


def test_markers_name_every_cut_every_finishing_item_and_every_sound_cue():
    root = ET.fromstring(doc())
    markers = [(frames(m.get('start')), m.get('value')) for m in root.iter('marker')]
    names = [v for _, v in markers]
    assert names[:5] == ['c1:S1', 'c2:S1', 'c3:S2', 'VS1', 'DG1']
    assert ('Stabilise c2:S1 in Resolve', 100) in [(v, f) for f, v in markers]
    assert any(v.startswith('SFX trowel') for v in names)
    notes = {m.get('value'): m.get('note') for m in root.iter('marker')}
    assert 'colour group G1' in notes['c1:S1']


def test_our_reader_gives_the_cuts_back_frame_for_frame():
    cuts = T.read_fcpxml(doc(), TL['fps'])
    video = [c for c in cuts if c['lane'] == 1]
    assert [(c['file'], c['record_in'], c['record_out'], c['source_in'], c['source_out']) for c in video] == \
        [('Media/Camera/C0120.MP4', 0, 100, 250, 350), ('Media/Camera/Stabilised/c2-S1-100.mp4', 100, 150, 0, 50), ('Media/Camera/C0130.MOV', 150, 200, 1500, 1600),
         ('Media/AI/VS1.mp4', 200, 325, 0, 125), ('Media/AI/DG1-asset.png', 325, 400, 0, 75)]
    assert T.timeline_frames(cuts) == 400 and len(video) == 5
    assert T.differences(cuts, EVENTS, NARR) == []
    off = [dict(e) for e in EVENTS]
    off[2]['record_out_frame'] = 201
    assert T.differences(cuts, off, NARR) == [{'cut': 3, 'file': 'Media/Camera/C0130.MOV', 'field': 'record_out', 'timeline': 200, 'plan': 201}]


def test_paths_with_spaces_and_other_scripts_are_written_as_valid_urls():
    text = T.fcpxml('VW-9', TL, [ev('Media/Camera/சுவர் 1.MP4', 'camera', 0, 25, 0, 25, name='x')], NARR, [], [], film_frames=25)
    root = ET.fromstring(text)
    srcs = [a.find('media-rep').get('src') for a in root.findall('./resources/asset')]
    assert 'file://./Media/Camera/%E0%AE%9A%E0%AF%81%E0%AE%B5%E0%AE%B0%E0%AF%8D%201.MP4' in srcs
    assert T.read_fcpxml(text, 25)[0]['file'] == 'Media/Camera/சுவர் 1.MP4'
    assert 'file:///C:/Users/Revathi/runs/VW-9/edit/Media/' in T.with_base(text, 'C:\\Users\\Revathi\\runs\\VW-9\\edit')   # slice 2 rewrites the base with this PC's path
    assert 'file:///Users/sk/My%20Films/VW-9/edit/Media/' in T.with_base(text, '/Users/sk/My Films/VW-9/edit')


# ---------- the EDL ----------

def test_the_edl_lists_every_cut_with_source_and_record_timecodes():
    lines = T.edl('VW-9', TL, EVENTS).splitlines()
    assert lines[0] == 'TITLE: VW-9' and lines[1] == 'FCM: NON-DROP FRAME'
    body = [l for l in lines if l[:3].isdigit()]
    assert body[0].split() == ['001', 'AX', 'V', 'C', '00:00:10:00', '00:00:14:00', '00:00:00:00', '00:00:04:00']
    assert body[2].split()[4:6] == ['00:00:30:00', '00:00:32:00']   # 1500-1600 at 50 fps is 30-32 s, written at the timeline's 25
    assert '* FROM CLIP NAME: C0120.MP4' in lines and len(body) == 5


# ---------- Relink-list.csv ----------

def test_the_relink_list_has_one_line_per_camera_file_with_what_relink_needs():
    clips = [{'id': 'c1', 'name': 'C0120.MP4', 'sha256': 'a' * 64, 'bytes': 10, 'fps': '25/1', 'duration_s': 120.0, 'width': 1920, 'height': 1080},
             {'id': 'c3', 'name': 'C0130.MOV', 'sha256': 'b' * 64, 'bytes': 20, 'fps': '50/1', 'duration_s': 120.0, 'width': 3840, 'height': 2160, 'start_timecode': '14:23:10:05', 'reel': 'A001'},
             {'id': 'c9', 'name': 'unused.MP4', 'sha256': 'c' * 64, 'bytes': 1, 'fps': '25/1', 'duration_s': 1.0, 'width': 1920, 'height': 1080}]
    rows = list(csv.DictReader(io.StringIO(T.relink_csv(clips, used_ids=['c1', 'c3'], cuts_per_clip={'c1': 1, 'c3': 1}))))
    assert [r['name'] for r in rows] == ['C0120.MP4', 'C0130.MOV']
    assert rows[0]['stem'] == 'C0120' and rows[0]['extension'] == '.MP4' and rows[0]['frames'] == '3000' and rows[0]['fps'] == '25' and rows[0]['start_timecode'] == '' and rows[0]['reel'] == ''
    assert rows[1]['frames'] == '6000' and rows[1]['fps'] == '50' and rows[1]['start_timecode'] == '14:23:10:05' and rows[1]['reel'] == 'A001' and rows[1]['cuts'] == '1'
    assert set(rows[0]) >= {'name', 'stem', 'extension', 'frames', 'fps', 'width', 'height', 'duration_s', 'start_timecode', 'reel', 'original_name', 'sha256', 'bytes', 'cuts'}


# ---------- the bundle's layout and OPEN-EDIT ----------

def test_the_bundle_names_follow_the_fixed_layout():
    assert D.layout('original', 'C0120.MP4') == 'Media/Camera/C0120.MP4'
    assert D.layout('normalised', 'c2-S1-100.mp4', fills=set()) == 'Media/Camera/Stabilised/c2-S1-100.mp4'
    assert D.layout('normalised', 'VS1.mp4', fills={'VS1.mp4'}) == 'Media/AI/VS1.mp4'
    assert D.layout('narration', 'narration.mp3') == 'Media/Voiceover/narration.mp3'
    assert D.layout('generated', 'VW-9.fcpxml') == 'Timeline/VW-9.fcpxml' and D.layout('generated', 'Subtitles.srt') == 'Subtitles.srt'


def test_resolve_events_use_the_new_layout_and_a_stills_real_file():
    pk = {'sub_clips': [{'sub_clip_id': 'c1:S1', 'clip_id': 'c1', 'clip_name': 'C0120.MP4', 'source_fps': '25', 'zoom': 1.2, 'position': [0.05, -0.02], 'horizon_rotation_deg': 0, 'color_group': 'G1'}],
          'timeline': TL}
    asm = {'events': [{'kind': 'event', 'sub_clip_id': 'c1:S1', 'source_in_frame': 250, 'source_out_frame': 350, 'timeline_in_frame': 0, 'timeline_out_frame': 100, 'timeline_frames': 100,
                       'crop': 'solver', 'approved_from_option': 1, 'a2_intervals': []},
                      {'kind': 'fill', 'shot_id': 'DG1', 'file': {'name': 'DG1-asset.png'}, 'media': {'kind': 'still'}, 'timeline_in_frame': 100, 'timeline_out_frame': 175, 'timeline_frames': 75}]}
    rows = D.resolve_events(asm, pk, {})
    assert rows[0]['file'] == 'Media/Camera/C0120.MP4' and rows[0]['kind'] == 'camera' and rows[0]['zoom'] == 1.2
    assert rows[1]['file'] == 'Media/AI/DG1-asset.png' and rows[1]['kind'] == 'still'


def test_open_edit_tells_the_editor_how_to_open_and_relink_on_any_computer():
    text = D.open_edit_text({'code': 'VW-9', 'client': 'C'}, ai=True)
    for words in ('Timeline/VW-9.fcpxml', 'File > Import > Timeline', 'Relink', 'Relink-list.csv', 'REFERENCE', 'Scale entire image to fit', 'Windows or Mac', 'AI-shots.md', "Editor's table"):
        assert words in text, words
    assert 'on the Mac' not in text and '.drt' not in text.split('Resolve Studio')[0]
