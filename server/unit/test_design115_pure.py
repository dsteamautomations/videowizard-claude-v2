"""design/115: the editor's early package. The events from the master plan and the recorded gaps (a take, a picture, a clip stretch, a sequence),
the AI files under Media/AI, the cut list, the caption cues broken at the recorded pauses, the timeline without the reference track, the refusal
while a gap has no recorded visuals."""
import copy
import re
from fractions import Fraction

from app.stage3 import delivery as D, early as E, timeline as TL

FPS = '25'
PK = {'timeline': {'fps': 25, 'width': 1920, 'height': 1080},
      'sub_clips': [{'sub_clip_id': 'c1:S1', 'clip_id': 'c1', 'clip_name': 'C0120.MP4', 'source_fps': '25', 'zoom': 1.2, 'position': [0.05, -0.02], 'horizon_rotation_deg': 0.0, 'color_group': 'G1', 'crop_rect': None}],
      'narration': {'sentences': [{'text': 'The wall stands.', 'start_frame': 0, 'end_frame': 50},
                                  {'text': 'Rat-trap bond saves a quarter of the bricks and keeps the house cool through the long summer afternoons of the plains.', 'start_frame': 50, 'end_frame': 250}],
                    'words': [{'text': w, 'start_frame': 50 + i * 10, 'end_frame': 58 + i * 10} for i, w in enumerate('Rat-trap bond saves a quarter of the bricks and keeps the house cool through the long summer afternoons of the plains.'.split())],
                    'pieces': [{'source_start_frame': 0, 'source_end_frame': 300, 'timeline_start_frame': 0}]}}
PLAN = {'duration_frames': 300,
        'events': [{'kind': 'event', 'sub_clip_id': 'c1:S1', 'source_in_frame': 250, 'source_out_frame': 350, 'timeline_in_frame': 0, 'timeline_out_frame': 100, 'timeline_frames': 100, 'crop': 'solver', 'a2_intervals': []},
                   {'kind': 'gap', 'beat_id': 'B2', 'gap_id': 'G1', 'timeline_in_frame': 100, 'timeline_out_frame': 300, 'timeline_frames': 200}],
        'gaps': [{'shot_id': 'G1', 'start_frame': 100, 'end_frame': 300}]}
CLIPS = {'c1': {'id': 'c1', 'name': 'C0120.MP4', 'fps': '25', 'duration_s': 20.0, 'sha256': 'c' * 64, 'bytes': 10}}
VIS = {'stage': 'visuals', 'unit': 'G1', 'files': [{'name': 'VS1.mp4', 'key': 'k/VS1.mp4', 'sha256': 'a' * 64, 'bytes': 1}, {'name': 'IM1-asset.png', 'key': 'k/IM1.png', 'sha256': 'b' * 64, 'bytes': 2},
                                                   {'name': 'AN1-state1.png', 'key': 'k/s1.png', 'sha256': 'd' * 64, 'bytes': 3}, {'name': 'AN1-state2.png', 'key': 'k/s2.png', 'sha256': 'e' * 64, 'bytes': 4}],
       'summary': {'shots': [{'shot_id': 'IM1', 'source': 'asset', 'kind': 'still', 'placement': {'start_frame': 150, 'end_frame': 200}, 'media': {'kind': 'still', 'motion': 'push_in'}},
                             {'shot_id': 'VS1', 'source': 'take', 'placement': {'start_frame': 100, 'end_frame': 150}, 'media': {'kind': 'movie', 'duration_s': 1.6}},
                             {'shot_id': 'CL1', 'source': 'clip', 'kind': 'clip', 'placement': {'start_frame': 200, 'end_frame': 250}, 'media': {'kind': 'clip', 'clip': {'id': 'c1', 'name': 'C0120.MP4', 'fps': '25', 'duration_s': 20.0}, 'in_s': 2.0, 'out_s': 4.0}},
                             {'shot_id': 'AN1', 'source': 'asset', 'kind': 'sequence', 'placement': {'start_frame': 250, 'end_frame': 300},
                              'media': {'kind': 'sequence', 'motion': 'push_in', 'states': [{'name': 'AN1-state1.png', 'hold_frames': 30}, {'name': 'AN1-state2.png', 'hold_frames': 20}]}}]}}


def test_the_early_events_follow_the_film_from_the_master_and_the_recorded_gaps():
    events, ai = E.events_of(PLAN, PK, [VIS], CLIPS)
    assert [e['record_in_frame'] for e in events] == [0, 100, 150, 200, 250, 280] and events[-1]['record_out_frame'] == 300
    cam = events[0]
    assert cam['file'] == 'Media/Camera/C0120.MP4' and cam['kind'] == 'camera' and cam['source_in_frame'] == 250 and cam['zoom'] == 1.2 and cam['stabilized'] is False
    take = events[1]
    assert take['file'] == 'Media/AI/VS1.mp4' and take['kind'] == 'movie' and take['source_out_frame'] == 40 and 'hold the last frame' in take['marker']['note']   # 1.6 s for a 2 s slot
    still = events[2]
    assert still['file'] == 'Media/AI/IM1-asset.png' and still['kind'] == 'still' and still['source_out_frame'] == 50 and 'planned move push_in' in still['marker']['note']
    clip = events[3]
    assert clip['file'] == 'Media/Camera/C0120.MP4' and clip['source_in_frame'] == 50 and clip['source_out_frame'] == 100 and clip['clip_id'] == 'c1'
    assert [e['file'] for e in events[4:]] == ['Media/AI/AN1-state1.png', 'Media/AI/AN1-state2.png'] and events[4]['source_out_frame'] == 30
    assert [f['name'] for f in ai] == ['VS1.mp4', 'IM1-asset.png', 'AN1-state1.png', 'AN1-state2.png']
    assert E.gaps_missing(PLAN, [VIS]) == [] and E.gaps_missing(PLAN, []) == ['G1']
    assert D.layout('ai', 'VS1.mp4') == 'Media/AI/VS1.mp4'


def test_the_cut_list_and_the_timeline_carry_every_cut_and_the_timeline_has_no_reference_track():
    events, _ = E.events_of(PLAN, PK, [VIS], CLIPS)
    rows = E.cut_list_csv(events, FPS).splitlines()
    assert rows[0].startswith('cut,kind,file,source in (s),source in (tc),source out (s),source out (tc),film in (s),film in (tc),film out (s),film out (tc),zoom,note')
    assert rows[1].startswith('1,camera,Media/Camera/C0120.MP4,10.000,00:00:10:00,14.000,00:00:14:00,0.000,00:00:00:00,4.000,00:00:04:00,1.2,')
    assert len(rows) == 1 + len(events) and E.tc(1501, 25) == '00:01:00:01'
    cues = E.cues(PK['narration']['sentences'], PK['narration']['words'], FPS)
    text = TL.fcpxml('VW-9', PK['timeline'], events, [{'file': 'Media/Voiceover/narration.mp3', 'source_in_frame': 0, 'source_out_frame': 300, 'record_in_frame': 0}], [], [], 300, reference=False, captions=cues)
    cuts = TL.read_fcpxml(text, 25)
    assert text.count('<caption ') == len(cues) and 'The wall stands.' in text and 'captionFormat=ITT.en' in text   # H3: the subtitle track names the same cues
    assert TL.timeline_frames(cuts) == 300 and len([c for c in cuts if c['lane'] == 1]) == len(events) and 'Approved-film.mp4' not in text
    assert 'Approved-film.mp4' in TL.fcpxml('VW-9', PK['timeline'], events, [], [], [], 300)   # the late bundle keeps its reference track


def test_the_captions_are_one_cue_per_sentence_broken_at_the_recorded_pauses_two_lines_of_42():
    cues = E.cues(PK['narration']['sentences'], PK['narration']['words'], FPS)
    assert cues[0] == {'start_frame': 0, 'end_frame': 50, 'text': 'The wall stands.'}
    assert len(cues) == 3 and all(len(l) <= 42 for c in cues for l in c['text'].split('\n')) and all(c['text'].count('\n') <= 1 for c in cues)
    assert cues[1]['start_frame'] == 50 and cues[2]['end_frame'] == 250 and cues[1]['end_frame'] == cues[2]['start_frame']   # the split falls on a word start
    text = E.srt(cues, FPS)
    assert text.startswith('1\n00:00:00,000 --> 00:00:02,000\nThe wall stands.\n\n2\n00:00:02,000 --> ')
    assert 'File > Import > Subtitle' in E.open_edit_text('VW-9') and 'vw delivery open --originals' in E.open_edit_text('VW-9')


def test_a_sub_clip_placed_twice_keeps_both_placements_in_the_early_events():
    """Review 28 Oct: the camera rows were keyed by sub_clip_id, so a callback to an earlier shot took the later placement's time."""
    plan = copy.deepcopy(PLAN)
    plan['events'] = [plan['events'][0], {'kind': 'gap', 'beat_id': 'B2', 'gap_id': 'G1', 'timeline_in_frame': 100, 'timeline_out_frame': 200, 'timeline_frames': 100},
                      {'kind': 'event', 'sub_clip_id': 'c1:S1', 'source_in_frame': 300, 'source_out_frame': 400, 'timeline_in_frame': 200, 'timeline_out_frame': 300, 'timeline_frames': 100, 'crop': 'solver', 'a2_intervals': []}]
    vis = copy.deepcopy(VIS)
    vis['summary']['shots'] = [{'shot_id': 'VS1', 'source': 'take', 'placement': {'start_frame': 100, 'end_frame': 200}, 'media': {'kind': 'movie', 'duration_s': 4.0}}]
    events, _ = E.events_of(plan, PK, [vis], CLIPS)
    cams = [e for e in events if e['kind'] == 'camera']
    assert [(c['record_in_frame'], c['source_in_frame']) for c in cams] == [(0, 250), (200, 300)]


def test_every_caption_carries_its_own_text_style_definition():
    cues = E.cues(PK['narration']['sentences'], PK['narration']['words'], FPS)
    text = TL.fcpxml('VW-9', PK['timeline'], [], [], [], [], 300, reference=False, captions=cues)
    assert text.count('<caption ') == len(cues) == text.count('<text-style-def ') and len(set(re.findall(r'text-style-def id="([^"]+)"', text))) == len(cues)
