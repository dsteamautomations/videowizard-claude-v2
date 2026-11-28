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


# ---------- build step 7 (part H) and the comparisons ----------

import shutil
import subprocess

import pytest

from app import overlay_jobs as J
from app.errors import Problem
from app.stage3 import assembly as A


def test_the_fingerprint_of_the_overlays_changes_with_a_clip_and_is_empty_without_any():
    assert S.package_digest({'start': {'answer': 'none'}, 'rows': []}) == ''
    d = S.package_digest(SESSION)
    changed = {**SESSION, 'rows': [rec('O01', 20, 70)] + SESSION['rows'][1:]}
    assert len(d) == 64 and S.package_digest(changed) != d and S.package_digest(SESSION) == d


def test_the_proof_film_lays_the_overlays_in_the_order_of_the_list():
    session = {**SESSION, 'rows': [SESSION['rows'][2], SESSION['rows'][0], SESSION['rows'][4]]}
    assert [(r['id'], r['record_in_frame'], r['frames']) for r in S.film_rows(session)] == [('O03', 70, 50), ('O01', 20, 45)]
    assert S.film_rows(session)[0]['key'] == 'r1/visuals/overlays/O03.mov'


OUTPUTS = [{'stage': 'master', 'unit': None, 'id': 'm', 'summary': {'plan_digest': 'p'}}, {'stage': 'visuals', 'unit': 'G1', 'id': 'v1', 'summary': {}}]


def test_a_package_made_before_an_overlay_changed_is_out_of_date():
    bundle = {'bundle': {'early': True, 'inputs': A.early_inputs(OUTPUTS, 'd1')}}
    assert A.package_first(bundle, OUTPUTS, 'd1') is None
    with pytest.raises(Problem) as e:
        A.package_first(bundle, OUTPUTS, 'd2')
    assert 'text overlays changed' in e.value.message and '`vw delivery bundle`' in e.value.message


def test_a_film_without_overlays_compares_as_before():
    assert A.early_inputs(OUTPUTS) == {'master_digest': 'p', 'gaps': {'G1': 'v1'}} and A.early_inputs(OUTPUTS, '') == A.early_inputs(OUTPUTS)
    assert A.package_first({'bundle': {'early': True, 'inputs': A.early_inputs(OUTPUTS)}}, OUTPUTS, '') is None


def test_the_command_lays_each_clip_at_its_moment_and_copies_the_sound():
    args = J.lay_args('film.mp4', [{'path': 'a.mov', 'record_in_frame': 25, 'frames': 50}, {'path': 'b.mov', 'record_in_frame': 50, 'frames': 25}], 'out.mp4', 25)
    fc = args[args.index('-filter_complex') + 1]
    assert args[args.index('a.mov') - 3:args.index('a.mov')] == ['-itsoffset', '1.000000', '-i'] and "[0:v][1:v]overlay=eof_action=pass:enable='between(t,1.000000,3.000000)'[v1]" in fc
    assert "[v1][2:v]overlay" in fc and args[args.index('-map') + 1] == '[v2]' and '0:a?' in args and args[args.index('-c:a') + 1] == 'copy'
    assert J.lay('film.mp4', [], 'out.mp4', 25).name == 'film.mp4'


@pytest.mark.skipif(not shutil.which('ffmpeg'), reason='needs ffmpeg')
def test_a_real_film_shows_the_overlay_only_during_its_moment(tmp_path, monkeypatch):
    monkeypatch.setattr(J, 'FFMPEG', lambda: 'ffmpeg')
    ff = lambda *a: subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', *a], check=True)
    ff('-f', 'lavfi', '-i', 'color=c=black:s=320x180:d=4:r=25', '-f', 'lavfi', '-i', 'sine=d=4', '-shortest', '-pix_fmt', 'yuv420p', str(tmp_path / 'film.mp4'))
    ff('-f', 'lavfi', '-i', 'color=c=white@1.0:s=320x180:d=1:r=25,format=yuva444p10le,geq=lum=940:cb=512:cr=512:a=if(lt(X\\,160)\\,1023\\,0)',
       '-c:v', 'prores_ks', '-profile:v', '4444', '-pix_fmt', 'yuva444p10le', str(tmp_path / 'o.mov'))
    out = J.lay(tmp_path / 'film.mp4', [{'path': tmp_path / 'o.mov', 'record_in_frame': 50, 'frames': 25}], tmp_path / 'out.mp4', 25)

    def grey(t, x):
        raw = subprocess.run(['ffmpeg', '-v', 'error', '-ss', str(t), '-i', str(out), '-frames:v', '1', '-vf', f'crop=2:2:{x}:90,format=gray', '-f', 'rawvideo', '-'], capture_output=True, check=True).stdout
        return raw[0]
    assert grey(1.0, 40) < 40 and grey(2.5, 40) > 200 and grey(2.5, 280) < 40 and grey(3.5, 40) < 40   # before, during (left half only: the right is transparent), after
    probe = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'stream=codec_type', '-of', 'csv=p=0', str(out)], capture_output=True, text=True).stdout.split()
    assert sorted(probe) == ['audio', 'video']


# ---------- parts I and J: the instruction ----------

def steps_of(name, footage):
    import json
    from pathlib import Path
    from app import core
    d = core.for_footage(json.loads((Path(__file__).resolve().parents[1] / 'procedures' / 'v3.json').read_text(encoding='utf-8')), footage)
    return next(s for s in d['stages'] if s['name'] == name)['steps']


@pytest.mark.parametrize('footage', ['own', 'none'])
def test_the_assembly_instruction_names_the_overlays_and_moves_the_hand_over_after_the_proof_film(footage):
    asm = steps_of('assembly', footage)
    assert 'the text overlays are settled' in asm[0] and 'Overlays.csv' in asm[0] and 'while the overlays step is open' in asm[0]
    assert "person B's, after the hand-over" in asm[0] and '`vw delivery check`' not in asm[0] and 'hands over after it' in asm[0]
    assert '`vw assembly prepare`' in asm[1]


def test_no_question_before_the_film_except_a_fill_with_an_issue():
    asm = steps_of('assembly', 'own')
    text = ' '.join(asm)
    assert 'ask once' not in text and asm[2].startswith('No question before the film, with one exception.')
    assert '"Use it as it is"' in asm[2] and '"Swap it in visuals"' in asm[2] and 'the build waits for the answer' in asm[2]
    assert 'Trims, holds and shaky shots are not asked' in asm[2] and 'say as plain facts, asking nothing' in asm[3]


def test_a_change_to_an_overlay_after_the_film_is_written_out():
    last = steps_of('assembly', 'own')[-1]
    assert '`vw overlays change O01' in last and '`vw delivery bundle` again' in last and 'the operator watches again' in last


@pytest.mark.parametrize('footage', ['own', 'none'])
def test_the_delivery_instruction_names_the_overlays_and_person_b(footage):
    dl = steps_of('delivery', footage)
    assert 'approved text overlays are in it' in dl[0] and dl[1].startswith('On the editing computer (person B, after the hand-over')
    assert 'switch those tracks off when comparing with Approved-film.mp4' in dl[1]


def test_after_the_last_gap_the_server_names_the_overlays_then_the_package():
    from app import visuals_stage as VS
    said = VS.record_next({'gaps': [{'gap_id': 'G1'}]}, {'G1': 'o'}, {})
    assert said.index('`vw overlays start`') < said.index('`vw delivery bundle`')


def test_after_the_package_the_server_names_the_assembly_first():
    assert D.early_next(True).startswith('the package is made. Next on this computer: the assembly') and 'person B' in D.early_next(False)
