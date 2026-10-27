"""design/107 slice 3: the media stage records what relinking needs and asks "originals or copies?"; the relink check with its five outcomes;
the Studio route (import the timeline by scripting, export, read back at 0 frames)."""
import argparse
import json
import os
import xml.etree.ElementTree as ET
from fractions import Fraction

import pytest

import handoff as H
import resolve_bridge as RB
import stages_av as AV
import vw
from test_handoff import fcp, edit


# ---------- the media stage ----------

def test_the_probe_reads_the_start_timecode_the_reel_and_the_original_name_when_the_file_has_them():
    data = {'format': {'tags': {'timecode': '14:23:10:05', 'reel_name': 'A001', 'original_filename': 'A001C012_0315XY.MXF'}}, 'streams': [{'codec_type': 'video', 'tags': {}}]}
    assert AV.relink_fields(data) == {'start_timecode': '14:23:10:05', 'reel': 'A001', 'original_name': 'A001C012_0315XY.MXF'}
    stream = {'format': {'tags': {}}, 'streams': [{'codec_type': 'video', 'tags': {'timecode': '01:00:00:00', 'reel_name': 'B002'}}, {'codec_type': 'data', 'tags': {'timecode': '01:00:00:00'}}]}
    assert AV.relink_fields(stream) == {'start_timecode': '01:00:00:00', 'reel': 'B002', 'original_name': ''}
    assert AV.relink_fields({'format': {}, 'streams': []}) == {'start_timecode': '', 'reel': '', 'original_name': ''}


def test_prepare_warns_once_about_copies_that_lost_their_timecode_or_frame_rate():
    clips = [{'name': 'C1.mp4', 'start_timecode': '', 'fps': '25/1'}, {'name': 'C2.mp4', 'start_timecode': '10:00:00:00', 'fps': '25/1'}, {'name': 'C3.mp4', 'start_timecode': '10:05:00:00', 'fps': '30000/1001'}]
    note = AV.copies_note(clips)
    assert 'C1.mp4' in note and 'no timecode' in note and 'C3.mp4' in note and 'frame rate' in note and 'C2.mp4' not in note
    assert 'keeps the original\'s name, length, frame rate and timecode' in note
    assert AV.copies_note([{'name': 'C2.mp4', 'start_timecode': '10:00:00:00', 'fps': '25/1'}]) == ''


def test_record_keeps_the_operators_answer_on_originals_or_copies(tmp_path):
    ws = tmp_path / 'VW-9'
    (ws / 'work').mkdir(parents=True)
    (ws / 'out').mkdir()
    clip = {'id': 'c1', 'name': 'C1.mp4', 'sha256': 'a' * 64, 'bytes': 3, 'duration_s': 1.0, 'has_audio': False, 'fps': '25/1', 'start_timecode': '', 'reel': '', 'original_name': ''}
    (ws / 'work' / 'media-clips.json').write_text(json.dumps([clip]), encoding='utf-8')
    out = AV.media_record(ws, {}, None, lambda stage, path, sha, size: {'name': 'C1.mp4'}, camera_audio='allowed', copies='copies')
    assert out['summary']['copies'] == 'copies' and out['summary']['clips'][0]['start_timecode'] == '' and 'reel' in out['summary']['clips'][0]
    with pytest.raises(AV.Refused, match='originals or copies'):
        AV.media_record(ws, {}, None, lambda *a: {}, camera_audio='allowed')


# ---------- the relink check ----------

ROWS = [{'name': 'C0120.mp4', 'stem': 'C0120', 'extension': '.mp4', 'frames': '3000', 'fps': '25', 'width': '1920', 'height': '1080', 'duration_s': '120.0', 'start_timecode': '', 'reel': '', 'cuts': '2'},
        {'name': 'C0130.mp4', 'stem': 'C0130', 'extension': '.mp4', 'frames': '6000', 'fps': '50', 'width': '1920', 'height': '1080', 'duration_s': '120.0', 'start_timecode': '14:23:10:05', 'reel': 'A001', 'cuts': '1'},
        {'name': 'C0140.mp4', 'stem': 'C0140', 'extension': '.mp4', 'frames': '2500', 'fps': '25', 'width': '1920', 'height': '1080', 'duration_s': '100.0', 'start_timecode': '', 'reel': '', 'cuts': '1'},
        {'name': 'C0150.mp4', 'stem': 'C0150', 'extension': '.mp4', 'frames': '1000', 'fps': '25', 'width': '1920', 'height': '1080', 'duration_s': '40.0', 'start_timecode': '', 'reel': '', 'cuts': '1'},
        {'name': 'C0160_proxy.mp4', 'stem': 'C0160_proxy', 'extension': '.mp4', 'frames': '500', 'fps': '25', 'width': '1920', 'height': '1080', 'duration_s': '20.0', 'start_timecode': '', 'reel': '', 'cuts': '1'}]
ORIGINALS = {'C0120.MOV': {'frames': 3000, 'fps': '25', 'start_timecode': '', 'width': 3840, 'height': 2160},            # extension differs, else the same
             'C0130.mp4': {'frames': 6000, 'fps': '50', 'start_timecode': '14:23:10:05', 'width': 1920, 'height': 1080},   # matches as is
             'C0140.MXF': {'frames': 2500, 'fps': '25', 'start_timecode': '09:00:00:00', 'width': 3840, 'height': 2160},   # the copy lost its timecode
             'C0150.MOV': {'frames': 1312, 'fps': '25', 'start_timecode': '', 'width': 3840, 'height': 2160},             # the copy is 312 frames shorter
             'C0160.MXF': {'frames': 500, 'fps': '25', 'start_timecode': '', 'width': 3840, 'height': 2160}}              # a proxy name


def originals(tmp_path):
    d = tmp_path / 'originals'
    d.mkdir()
    for n in ORIGINALS:
        (d / n).write_bytes(b'x')
    return d


CUTS = [('Media/Camera/C0120.mp4', 250, 0, 100), ('Media/Camera/C0120.mp4', 2000, 100, 150), ('Media/Camera/C0130.mp4', 0, 150, 200), ('Media/Camera/C0140.mp4', 100, 200, 300),
        ('Media/Camera/C0150.mp4', 0, 300, 350), ('Media/Camera/C0160_proxy.mp4', 0, 350, 400)]


def test_the_relink_check_gives_each_file_its_outcome_and_writes_the_relinked_timeline(tmp_path):
    d, _ = edit(tmp_path, cuts=CUTS)
    (d / 'Timeline' / 'VW-9.portable.fcpxml').write_bytes(fcp(CUTS).encode('utf-8'))
    grabs = []
    rep = H.relink_check(d, 'VW-9', ROWS, originals(tmp_path), probe=lambda p: ORIGINALS[p.name], grab=lambda src, at_s, out: grabs.append((src.name, at_s)) or out)
    lines = {l['copy']: l for l in rep['lines']}
    assert lines['C0130.mp4']['outcome'] == 'match' and 'Relinks as is' in lines['C0130.mp4']['line']
    assert lines['C0120.mp4']['outcome'] == 'renamed' and lines['C0120.mp4']['original'] == 'C0120.MOV'
    assert lines['C0140.mp4']['outcome'] == 'timecode' and '09:00:00:00' in lines['C0140.mp4']['line'] and 'corrected timeline' in lines['C0140.mp4']['line']
    assert lines['C0150.mp4']['outcome'] == 'by_hand' and '312 frames shorter' in lines['C0150.mp4']['line'] and lines['C0150.mp4']['cuts'] == [{'cut': 5, 'at_s': 0.0, 'grab': 'Timeline/grabs/C0150.mp4-cut5.png'}]
    assert grabs == [('C0150.MOV', 0.0)]
    assert lines['C0160_proxy.mp4']['outcome'] == 'renamed' and lines['C0160_proxy.mp4']['original'] == 'C0160.MXF' and 'length, frame rate, timecode agree' in lines['C0160_proxy.mp4']['line']
    root = ET.fromstring((d / 'Timeline' / 'VW-9-relinked.fcpxml').read_bytes().decode('utf-8'))
    srcs = {a.get('id'): a.find('media-rep').get('src') for a in root.findall('./resources/asset')}
    assert any(s.endswith('C0120.MOV') for s in srcs.values()) and any(s.endswith('C0160.MXF') for s in srcs.values()) and any(s.endswith('C0140.MXF') for s in srcs.values())
    assert any(s.endswith('C0150.mp4') for s in srcs.values())   # the trimmed one stays on the copy: lined up by hand
    shifted = [c for c in root.iter('asset-clip') if srcs[c.get('ref')].endswith('C0140.MXF')]
    assert Fraction(shifted[0].get('start').rstrip('s')) == Fraction(100, 25) + 9 * 3600   # moved by the original's start timecode
    assert rep['checklist'] == ['C0150.mp4 → C0150.MOV: the copy is 312 frames shorter than the original; line up cut 5 by hand (0.0 s into the copy; grab in Timeline/grabs/)']


def test_the_relink_check_never_guesses_between_two_originals_and_names_a_missing_one(tmp_path):
    d, _ = edit(tmp_path, cuts=[('Media/Camera/C0120.mp4', 250, 0, 100), ('Media/Camera/C0170.mp4', 0, 100, 400)])
    (d / 'Timeline' / 'VW-9.portable.fcpxml').write_bytes(fcp([('Media/Camera/C0120.mp4', 250, 0, 100), ('Media/Camera/C0170.mp4', 0, 100, 400)]).encode('utf-8'))
    o = tmp_path / 'originals'
    o.mkdir()
    for n in ('C0120.MOV', 'C0120.MXF'):
        (o / n).write_bytes(b'x')
    rows = [ROWS[0], {**ROWS[0], 'name': 'C0170.mp4', 'stem': 'C0170'}]
    rep = H.relink_check(d, 'VW-9', rows, o, probe=lambda p: ORIGINALS['C0120.MOV'], grab=lambda *a: None)
    lines = {l['copy']: l for l in rep['lines']}
    assert lines['C0120.mp4']['outcome'] == 'ask' and sorted(lines['C0120.mp4']['candidates']) == ['C0120.MOV', 'C0120.MXF'] and 'pick' in lines['C0120.mp4']['line']
    assert lines['C0170.mp4']['outcome'] == 'missing' and 'no original with this name' in lines['C0170.mp4']['line'] and lines['C0170.mp4']['cuts'] == [2]
    assert not (d / 'Timeline' / 'VW-9-relinked.fcpxml').exists()   # nothing written while a pick is open


def test_a_name_match_that_fails_the_length_check_is_not_a_match(tmp_path):
    d, _ = edit(tmp_path, cuts=[('Media/Camera/C0120.mp4', 250, 0, 400)])
    (d / 'Timeline' / 'VW-9.portable.fcpxml').write_bytes(fcp([('Media/Camera/C0120.mp4', 250, 0, 400)]).encode('utf-8'))
    o = tmp_path / 'originals'
    o.mkdir()
    (o / 'C0120.MOV').write_bytes(b'x')
    rep = H.relink_check(d, 'VW-9', [ROWS[0]], o, probe=lambda p: {'frames': 9000, 'fps': '25', 'start_timecode': '', 'width': 1920, 'height': 1080}, grab=lambda *a: None)
    assert rep['lines'][0]['outcome'] == 'by_hand' and '6000 frames shorter' in rep['lines'][0]['line']   # the copy (3000) against the original (9000)


# ---------- the Studio route ----------

def test_the_studio_route_imports_the_timeline_exports_and_reads_back_at_zero_frames(tmp_path, monkeypatch):
    d, manifest = edit(tmp_path)
    manifest['resolve_events'] = [{'file': f, 'source_in_frame': s, 'source_out_frame': s + (b - a), 'record_in_frame': a, 'record_out_frame': b, 'source_fps': '25'} for f, s, a, b in CUTS[:0]] + \
        [{'file': 'Media/Camera/C1.MP4', 'source_in_frame': 250, 'source_out_frame': 350, 'record_in_frame': 0, 'record_out_frame': 100, 'source_fps': '25'},
         {'file': 'Media/AI/VS1.mp4', 'source_in_frame': 0, 'source_out_frame': 300, 'record_in_frame': 100, 'record_out_frame': 400, 'source_fps': '25'}]
    manifest['narration_pieces'] = [{'file': 'Media/Voiceover/narration.mp3', 'source_in_frame': 0, 'source_out_frame': 400, 'record_in_frame': 0}]
    H.write_timeline_for(d, manifest, base=str(d))
    rep = RB.studio_import(RB.FakeAdapter(), d, manifest, 'VW-9')
    assert rep['drt_verified'] and rep['differences'] == [] and rep['events'] == 2
    assert (d / 'Timeline' / 'VW-9.drt').exists() and (d / 'Timeline' / 'VW-9.drp').exists() and rep['timeline'] == 'VW-9'
    manifest['resolve_events'][1]['record_out_frame'] = 401
    rep = RB.studio_import(RB.FakeAdapter(), d, manifest, 'VW-9')
    assert not rep['drt_verified'] and rep['differences'][0]['field'] == 'record_out'


# ---------- the commands ----------

@pytest.fixture
def cli(monkeypatch, tmp_path):
    monkeypatch.setattr(vw, 'RUNS', tmp_path / 'runs')
    m = {'code': 'VW-9', 'run_id': 'run-1', 'files': []}
    monkeypatch.setattr(vw, 'active', lambda: m)
    monkeypatch.setattr(vw, 'machine_id', lambda: 'pc-1')
    sent = []
    monkeypatch.setattr(vw, 'write', lambda path, body, **kw: sent.append((path.rsplit('/delivery/', 1)[-1], body)) or {'state': body.get('state', 'reserved')})
    return m, sent, tmp_path


def args(**kw):
    base = {'what': 'open', 'check': False, 'run_it': False, 'inspect': False, 'close': False, 'authorization': None, 'note': None, 'quote': None, 'originals': None}
    return argparse.Namespace(**{**base, **kw})


def run(a, capsys):
    with pytest.raises(SystemExit) as exc:
        vw.cmd_delivery(a)
    out, err = capsys.readouterr()
    return exc.value.code, json.loads(out), err


def test_open_on_studio_imports_and_reports_and_on_free_shows_the_steps(cli, monkeypatch, capsys):
    m, sent, tmp_path = cli
    d, manifest = edit(tmp_path)
    manifest['resolve_events'] = [{'file': 'Media/Camera/C1.MP4', 'source_in_frame': 250, 'source_out_frame': 350, 'record_in_frame': 0, 'record_out_frame': 100, 'source_fps': '25'},
                                  {'file': 'Media/AI/VS1.mp4', 'source_in_frame': 0, 'source_out_frame': 300, 'record_in_frame': 100, 'record_out_frame': 400, 'source_fps': '25'}]
    manifest['narration_pieces'] = [{'file': 'Media/Voiceover/narration.mp3', 'source_in_frame': 0, 'source_out_frame': 400, 'record_in_frame': 0}]
    (tmp_path / 'runs' / 'VW-9' / 'work').mkdir(parents=True, exist_ok=True)
    (tmp_path / 'runs' / 'VW-9' / 'work' / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
    H.write_timeline_for(d, manifest, base=str(d))
    monkeypatch.setenv('VW2_RESOLVE_FAKE', '1')
    monkeypatch.setattr(vw.handoff, 'find_resolve', lambda: {'found': True, 'version': '21.1', 'edition': 'studio'})
    code, out, err = run(args(what='open'), capsys)
    assert code == 0 and out['report']['drt_verified'] and [s[0] for s in sent] == ['resolve/reserve', 'resolve/mark', 'resolve/mark'] and sent[2][1]['report']['route'] == 'studio'
    monkeypatch.setattr(vw.handoff, 'find_resolve', lambda: {'found': True, 'version': '21.1', 'edition': 'free'})
    code, out, err = run(args(what='open'), capsys)
    assert code == 0 and 'File > Import > Timeline' in out['open']


def test_relink_check_needs_the_originals_folder_and_reports_each_line(cli, monkeypatch, capsys):
    m, sent, tmp_path = cli
    d, manifest = edit(tmp_path, cuts=[('Media/Camera/C0130.mp4', 0, 0, 400)])
    (d / 'Timeline' / 'VW-9.portable.fcpxml').write_bytes(fcp([('Media/Camera/C0130.mp4', 0, 0, 400)]).encode('utf-8'))
    (d / 'Relink-list.csv').write_text('name,stem,extension,frames,fps,width,height,duration_s,start_timecode,reel,original_name,sha256,bytes,cuts\nC0130.mp4,C0130,.mp4,6000,50,1920,1080,120.0,14:23:10:05,A001,,s,1,1\n', encoding='utf-8')
    o = originals(tmp_path)
    monkeypatch.setattr(vw.handoff, 'probe_original', lambda p: ORIGINALS[p.name])
    code, out, err = run(args(what='relink-check', originals=str(o)), capsys)
    assert code == 0 and out['lines'][0]['outcome'] == 'match' and 'Relinks as is' in err
    code, out, err = run(args(what='relink-check'), capsys)
    assert code == 2 and '--originals' in out['message']
