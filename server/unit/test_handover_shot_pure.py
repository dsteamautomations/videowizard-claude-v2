"""SK, 23 Nov 2026 (VW-25, plan of action Phase 4b): what reaches DaVinci Resolve for each camera cut.
R1. The position of a cropped shot is written in the timeline file's own unit (per cent of the frame's height); it was written in pixels, so a
    shot moved 270 pixels would have landed 2,916 pixels off. The direct Resolve script keeps pixels (Resolve's Pan and Tilt).
R2-R6. Each camera cut carries a `shot` block: its name on the review page, the words under it, exact match or B-roll, the crop and what the
    crop is for, the warnings, and what the operator decided at review. The marker shows the readable name and the same in short form.
R7. A held last frame is said on the cut (the timeline file cannot hold a frame: the editor freezes it).
R8. No changed speed is planned at this stage (a cut always plays in real time; the clip's own rate carries it): nothing to pass.
R9. The cut list (CSV) carries the position and the rotation.
Not checked here: the result in Resolve itself. This PC has no Resolve."""
import csv
import io
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from app.stage2 import stage as S
from app.stage3 import delivery as D, early as E, timeline as T
from test_design127_review_pure import USER, answer_all, decide, plan, session_store
from test_review_page import FakeConn, RUN
from test_review_swap_trim_pure import package_of, put_package

SERVER = Path(__file__).resolve().parents[1]
TL = {'width': 1920, 'height': 1080, 'fps': 25}
ROW = {'sub_clip_id': 'c1:S1', 'clip_id': 'c1', 'clip_name': 'C0098.MP4', 'source_fps': '25', 'zoom': 1.47, 'position': [270.0, 152.0], 'crop_rect': [0.16, 0.42, 0.68, 0.68],
       'horizon_rotation_deg': 1.5, 'color_group': 'G1', 'risk_flags': ['soft picture, zoom 1.47', 'no_gloves']}
EVENT = {'kind': 'event', 'sub_clip_id': 'c1:S1', 'source_in_frame': 250, 'source_out_frame': 350, 'timeline_in_frame': 0, 'timeline_out_frame': 100, 'timeline_frames': 100,
         'crop': 'solver', 'approved_from_option': 8, 'a2_intervals': [], 'edited': 'in:0,out:-25',
         'shot': {'slide': '8.2', 'title': 'Scene 8 · Shot 2', 'words': 'He lays the tile between the bars.', 'match': 'b_roll'}}
MASTER = {'decisions': {'8.2': {'action': 'TRIM', 'edit': 'in:0,out:-25', 'edit_text': 'ends 1.0 s earlier', 'note': 'the hand only'}}}


def rows(event=EVENT, row=ROW, master=MASTER):
    return D.resolve_events({'events': [event]}, {'sub_clips': [row], 'timeline': TL}, master)


def test_each_camera_cut_says_what_it_is_the_crop_the_warnings_and_the_review():
    e = rows()[0]
    assert e['shot'] == {'name': 'Scene 8 · Shot 2', 'slide': '8.2', 'words': 'He lays the tile between the bars.', 'match': 'B-roll',
                         'crop': {'rect': [0.16, 0.42, 0.68, 0.68], 'purpose': 'keeps the person who speaks to the camera out of the frame; the work stays in view'},
                         'warnings': ['soft picture, zoom 1.47', 'no_gloves'], 'review': ['trimmed by the operator (ends 1.0 s earlier)', "the operator's note: the hand only"], 'hold_last_frame': False}
    assert e['marker']['name'] == 'c1:S1' and e['marker']['title'] == 'Scene 8 · Shot 2'   # the id still names the clip; the marker shows the readable name
    assert e['marker']['note'] == ('option #8; Scene 8 · Shot 2; B-roll; words: “He lays the tile between the bars.”; '
                                   'crop: keeps the person who speaks to the camera out of the frame; the work stays in view (x 0.16, y 0.42, w 0.68, h 0.68 of the frame); '
                                   "warnings: soft picture, zoom 1.47, no_gloves; trimmed by the operator (ends 1.0 s earlier); the operator's note: the hand only")
    assert (e['zoom'], e['pan'], e['tilt'], e['rotation']) == (1.47, 270.0, 152.0, 1.5)     # pixels, as the direct Resolve script needs them


def test_the_other_review_records_and_a_cut_made_before_this_release():
    swapped = rows({**EVENT, 'edited': None, 'swapped_from': 'c9:S1', 'crop': 'full'}, master={})[0]
    assert swapped['shot']['review'] == ['the operator chose this clip in place of c9:S1'] and swapped['shot']['crop'] is None and swapped['pan'] == 0.0
    assert rows({**EVENT, 'edited': None, 'swapped_from': 'AI'}, master={})[0]['shot']['review'] == ['the operator chose this clip in place of an AI shot']
    alt = rows({**EVENT, 'edited': None, 'from_alternative': '8.2A1', 'shot': {**EVENT['shot'], 'match': 'direct'}}, master={})[0]
    assert alt['shot']['review'] == ['taken from alternative 8.2A1: the operator rejected the first choice'] and alt['shot']['match'] == 'matches the words'
    hands = rows({**EVENT, 'crop': 'hands_only'}, master={})[0]
    assert hands['shot']['crop']['purpose'] == 'tight on the hands' and hands['shot']['review'] == ['trimmed by the operator (in:0,out:-25)']   # no record of the words: the frames
    held = rows({**EVENT, 'hold_last_frame': True}, master={})[0]
    assert held['shot']['hold_last_frame'] is True and 'hold the last frame to fill the shot (freeze it in Resolve)' in held['marker']['note']
    old = rows({k: v for k, v in EVENT.items() if k not in ('shot', 'edited')}, {k: v for k, v in ROW.items() if k != 'risk_flags'}, {})[0]   # a master built before this release
    assert old['marker']['title'] == 'c1:S1' and old['marker']['note'].startswith('option #8; crop: ') and old['shot']['name'] is None and old['shot']['warnings'] == []
    stab = rows({**EVENT, 'stabilize': True}, master={})[0]
    assert stab['marker']['note'].startswith('option #8, stabilised copy; Scene 8 · Shot 2') and stab['zoom'] == 1.0 and stab['shot']['crop']['rect'] == ROW['crop_rect']


def test_the_position_is_written_in_the_timeline_files_unit_and_the_marker_shows_the_readable_name():
    events = rows()
    root = ET.fromstring(T.fcpxml('VW-9', TL, events, [], [], [{'sub_clip_id': 'c1:S1', 'sfx_type': 'trowel'}], film_frames=100, reference=False))
    clip = next(c for c in root.iter('asset-clip') if c.get('lane') == '1')
    t = clip.find('adjust-transform')
    assert t.get('scale') == '1.47 1.47' and t.get('position') == '25 14.0741' and t.get('rotation') == '1.5'   # 270 and 152 pixels of a 1080-high film, in per cent of its height
    m = clip.find('marker')
    assert clip.get('name') == 'c1:S1' and m.get('value') == 'Scene 8 · Shot 2' and m.get('note').startswith('option #8; Scene 8 · Shot 2; B-roll')
    assert any(x.get('value') == 'SFX trowel' and x.get('start') == '0s' for x in root.iter('marker'))   # a sound cue still finds its cut by the clip's id
    small = ET.fromstring(T.fcpxml('VW-9', {'width': 1280, 'height': 720, 'fps': 25}, [{**events[0], 'pan': 180.0, 'tilt': -72.0}], [], [], [], film_frames=100, reference=False))
    assert next(small.iter('adjust-transform')).get('position') == '25 -10'                          # the unit follows the film's own height


def test_the_cut_list_carries_the_position_and_the_rotation():
    table = list(csv.reader(io.StringIO(E.cut_list_csv(rows(), 25))))
    assert table[0][-4:] == ['note', 'position x (px)', 'position y (px)', 'rotation (deg)'] and table[1][-3:] == ['270', '152', '1.5']
    assert table[1][11] == '1.47' and table[1][12].startswith('option #8; Scene 8 · Shot 2')
    plain = list(csv.reader(io.StringIO(E.cut_list_csv([{**rows()[0], 'pan': 0.0, 'tilt': 0.0, 'rotation': 0.0}], 25))))
    assert plain[1][-3:] == ['0', '0', '0']


def test_the_master_gives_every_camera_cut_its_name_words_and_match():
    store = session_store()
    pk = package_of(store)
    pk['sub_clips'][4].update(fit_kinds={'BEAT_02': 'chapter'}, eligibility='ELIGIBLE_AS_IS', grade='A')
    put_package(store, pk)
    answer_all(store, **{'1.3': 'REJECT'})
    decide(store, '1.3A1', 'KEEP')
    S.decide(FakeConn({}), store, USER, RUN, '2.1', 'SWAP', '', None, 'c5:S')
    S.build_master(FakeConn({}), store, USER, RUN)
    shots = {e['sub_clip_id']: e['shot'] for e in plan(store)['events'] if e['kind'] == 'event'}
    assert shots['c1:S'] == {'slide': '1.2', 'title': 'Scene 1 · Shot 2', 'words': 'cost', 'match': 'direct'}
    assert shots['c4:S'] == {'slide': '1.3', 'title': 'Scene 1 · Shot 3', 'words': 'less. Bricks', 'match': 'direct'}   # the kept alternative, under the shot's own name
    assert shots['c5:S'] == {'slide': '2.1', 'title': 'Scene 2 · Shot 1', 'words': 'save', 'match': 'b_roll'}       # the clip the operator put on the all-AI scene


def test_the_direct_resolve_script_keeps_pixels_and_shows_the_readable_name():
    sys.path.insert(0, str(SERVER.parent / 'plugin' / 'scripts'))
    text = (SERVER.parent / 'plugin' / 'scripts' / 'resolve_bridge.py').read_text(encoding='utf-8')
    assert "Pan=e['pan'], Tilt=e['tilt']" in text and "e['marker'].get('title') or e['marker']['name']" in text
