"""Text overlays, build step 6 (requirements version 3 of 28 Nov 2026, part G): the approved overlays in the editor's package. Each clip under
Media/Overlays/, on its own track above the picture (overlapping overlays on separate tracks), listed in Overlays.csv with its card, motion and place."""
import csv
import io
import xml.etree.ElementTree as ET

from app import overlay_stage as S
from app.stage3 import delivery as D
from app.stage3 import timeline as TL


def rec(rid, start, end, state='approved', clip=True, **row):
    return {'id': rid, 'state': state, 'given': {}, 'still': None,
            'clip': {'key': f'r1/visuals/overlays/{rid}.mov', 'sha256': rid.lower() * 16, 'bytes': 10, 'frames': end - start} if clip else None,
            'row': {'kind': 'callout', 'lines': ['Two weeks'], 'card': dict(S.O.CARDS['dark']), 'motion': 'wipe', 'place': 'bottom left', 'start_frame': start, 'end_frame': end, **row}}


SESSION = {'start': {'answer': 'defaults'}, 'proposed': True,
           'rows': [rec('O01', 20, 65), rec('O02', 50, 100, kind='list', lines=['Cement', 'Sand'], heading='Materials', card={**S.O.CARDS['cream'], 'corner': 'pill'}, place={'x': 70, 'y': 30}),
                    rec('O03', 70, 120, motion='fade'), rec('O04', 200, 260, state='removed', clip=False), rec('O05', 300, 350, state='proposed', clip=False)]}


def test_the_overlays_of_the_package_are_the_approved_ones_with_a_clip_each_on_a_track():
    rows = S.package_rows(SESSION)
    assert [(r['id'], r['track']) for r in rows] == [('O01', 1), ('O02', 2), ('O03', 1)]   # O02 overlaps O01: its own track; O03 begins after O01 ends
    assert rows[0] == {'id': 'O01', 'file': 'Media/Overlays/O01.mov', 'key': 'r1/visuals/overlays/O01.mov', 'sha256': 'o01' * 16, 'bytes': 10, 'frames': 45,
                       'record_in_frame': 20, 'record_out_frame': 65, 'track': 1, 'kind': 'callout', 'text': 'Two weeks', 'card': 'dark', 'motion': 'wipe', 'place': 'bottom left'}
    assert rows[1]['text'] == 'Materials: Cement / Sand' and rows[1]['card'] == 'own' and rows[1]['place'] == 'x 70 %, y 30 %'


def test_no_overlays_no_rows():
    assert S.package_rows({'start': {'answer': 'none'}, 'rows': []}) == [] and S.package_rows({'start': None}) == []


def test_the_overlays_table_names_each_overlay_its_times_its_track_and_its_look():
    rows = list(csv.DictReader(io.StringIO(S.overlays_csv(S.package_rows(SESSION), 25))))
    assert rows[0] == {'overlay': 'O01', 'file': 'Media/Overlays/O01.mov', 'kind': 'callout', 'text': 'Two weeks', 'in_tc': '00:00:00:20', 'out_tc': '00:00:02:15',
                       'in_s': '0.8', 'out_s': '2.6', 'track': 'Overlays 1', 'card': 'dark', 'motion': 'wipe', 'place': 'bottom left'}
    assert rows[1]['track'] == 'Overlays 2' and len(rows) == 3


def test_the_layout_puts_the_clips_under_media_overlays():
    assert D.layout('overlay', 'O01.mov') == 'Media/Overlays/O01.mov'


TL_ = {'fps': 25, 'width': 1920, 'height': 1080}
EVENT = {'file': 'Media/AI/S01-1.mp4', 'kind': 'movie', 'source_in_frame': 0, 'source_out_frame': 400, 'record_in_frame': 0, 'record_out_frame': 400, 'source_fps': '25',
         'marker': {'name': 'S01-1', 'note': 'AI take'}, 'a2': [], 'source_frames': 400, 'silent': True}


def test_the_timeline_carries_each_overlay_on_its_track_above_the_picture_and_the_captions():
    text = TL.fcpxml('VW-30', TL_, [EVENT], [], [], [], 400, reference=False, captions=[{'start_frame': 0, 'end_frame': 50, 'text': 'Hello'}], overlays=S.package_rows(SESSION))
    clips = [c for c in ET.fromstring(text.split('<!DOCTYPE fcpxml>\n', 1)[1]).iter('asset-clip') if c.get('name', '').startswith('Overlay ')]
    assert [(c.get('name'), c.get('lane'), c.get('offset'), c.get('duration'), c.get('start')) for c in clips] == [
        ('Overlay O01', '4', '4/5s', '9/5s', '0s'), ('Overlay O02', '5', '2s', '2s', '0s'), ('Overlay O03', '4', '14/5s', '2s', '0s')]
    assets = {a.get('id'): a for a in ET.fromstring(text.split('<!DOCTYPE fcpxml>\n', 1)[1]).iter('asset')}
    a = assets[clips[0].get('ref')]
    assert a.get('name') == 'O01.mov' and a.get('hasAudio') == '0' and a.get('hasVideo') == '1' and a.find('media-rep').get('src').endswith('Media/Overlays/O01.mov')


def test_a_timeline_without_overlays_is_as_before():
    assert TL.fcpxml('VW-30', TL_, [EVENT], [], [], [], 400, reference=False) == TL.fcpxml('VW-30', TL_, [EVENT], [], [], [], 400, reference=False, overlays=[])
    assert 'Overlay ' not in TL.fcpxml('VW-30', TL_, [EVENT], [], [], [], 400, reference=False)


def test_the_open_edit_text_says_where_the_overlays_are_only_when_there_are_some():
    from app.stage3 import early as E
    with_ = E.open_edit_text('VW-30', camera=False, overlays=3)
    assert 'Media/Overlays/' in with_ and 'Overlays.csv' in with_ and 'transparent' in with_
    assert 'Media/Overlays/' not in E.open_edit_text('VW-30', camera=False)
