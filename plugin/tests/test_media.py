"""Media prepare and record as pure file functions with generated clips (design/41 5.1, 5.3–5.5); ffmpeg and ffprobe needed."""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import time

import pytest

from conftest import STAGES
import vw
from stages_av import Refused, file_sha256, media_prepare, media_record

pytestmark = pytest.mark.skipif(shutil.which('ffmpeg') is None or shutil.which('ffprobe') is None, reason='ffmpeg/ffprobe not installed')
PROC = STAGES['media']


def clip(path, seconds=1, audio=True, tone=440, size='64x64', rate=10, vfr=False):
    cmd = ['ffmpeg', '-y', '-v', 'error', '-f', 'lavfi', '-i', f'testsrc=duration={seconds}:size={size}:rate={rate}']
    if audio:
        cmd += ['-f', 'lavfi', '-i', f'sine=frequency={tone}:duration={seconds}', '-c:a', 'aac']
    if vfr:
        cmd += ['-vf', "select='not(eq(mod(n,7),3))'", '-fps_mode', 'vfr']
    cmd += ['-c:v', 'libx264', '-pix_fmt', 'yuv420p', str(path)]
    subprocess.run(cmd, check=True)


def prior(stage):
    raise AssertionError('media reads no earlier output')


def fake_upload(calls):
    def upload(stage, path, sha, size):
        calls.append(os.path.basename(str(path)))
        return {'name': os.path.basename(str(path)), 'key': f'k/{stage}/{os.path.basename(str(path))}', 'sha256': sha, 'bytes': size, 'receipt': True, 'location': 'storage'}
    return upload


def test_file_sha256_matches_a_whole_file_hash(tmp_path):
    p = tmp_path / 'x.bin'
    p.write_bytes(os.urandom(3 * 1024 * 1024 + 123))
    assert file_sha256(p) == hashlib.sha256(p.read_bytes()).hexdigest()


def test_prepare_keeps_name_order_reports_size_and_stores_stat(ws):
    for i, name in enumerate(('c.mp4', 'a.mp4', 'b.mp4', 'd.mp4', 'e.mp4', 'f.mp4')):
        clip(ws / 'in' / name, tone=400 + 10 * i, audio=(name != 'b.mp4'))
    out = media_prepare(ws, PROC, prior)
    names = [c['name'] for c in out['clips']]
    assert names == ['a.mp4', 'b.mp4', 'c.mp4', 'd.mp4', 'e.mp4', 'f.mp4'] and out['duplicates_skipped'] == 0
    detail = json.loads((ws / 'work' / 'media-clips.json').read_text(encoding='utf-8'))   # design/57: the full probe lives here, not in the output
    assert out['detail_file'] == 'work/media-clips.json' and [c['name'] for c in detail] == names
    assert out['total_bytes'] == sum(c['bytes'] for c in detail) and out['total_mb'] == round(out['total_bytes'] / 1e6)
    assert '6 clips' in out['message'] and 'MB' in out['message'] and 'reports when it is done' in out['message']
    for c in detail:
        st = (ws / 'in' / c['name']).stat()
        assert c['source_bytes'] == st.st_size and c['source_mtime'] == st.st_mtime and c['sha256'] == file_sha256(ws / 'in' / c['name']) and c['id'] == c['sha256'][:16]
    assert not detail[1]['has_audio'] and detail[0]['has_audio']
    for c in out['clips']:   # what the operator confirms, nothing else
        assert set(c) == {'name', 'duration_s', 'mb', 'sound'} and isinstance(c['sound'], bool) and c['mb'] >= 0
    assert out['clips'][1]['sound'] is False and out['clips'][0]['sound'] is True
    lines = out['listing'].split('\n')
    assert len(lines) == 7 and lines[0].startswith('a.mp4 · ') and ' s · ' in lines[0] and lines[0].endswith(' MB · sound') and lines[1].endswith(' MB · no sound')
    assert lines[6].startswith('6 clips · ') and lines[6].endswith(' MB')
    assert len(json.dumps(out)) < 4000


def test_prepare_guesses_the_footage_character_from_the_probe_and_record_stores_the_operators_answer(ws):
    """design/77 L42 (VW-6: the assistant assumed phone footage; the clips were from a cinema camera)."""
    from stages_av import footage_guess
    clip(ws / 'in' / 'a.mp4')
    out = media_prepare(ws, PROC, prior)
    assert out['footage_guess'].startswith('looks like phone footage') and 'footage' in out['message']   # 64x64 test clips at a few kbit/s
    assert footage_guess([{'width': 3840, 'height': 2160, 'bit_rate': 120_000_000, 'pix_fmt': 'yuv422p10le', 'codec': 'prores'}]).startswith('looks professional')
    assert 'prores' in footage_guess([{'width': 1920, 'height': 1080, 'bit_rate': 8_000_000, 'pix_fmt': 'yuv420p', 'codec': 'prores'}])
    assert footage_guess([{'width': 1920, 'height': 1080, 'bit_rate': 8_000_000, 'pix_fmt': 'yuv420p', 'codec': 'h264'}]).startswith('looks like phone footage')
    calls = []
    res = media_record(ws, PROC, prior, fake_upload(calls), camera_audio='allowed', note='ok', footage={'camera': 'cinema', 'support': 'tripod', 'look': 'natural', 'quote': 'Shot on a cinema camera, tripod, ungraded.'})
    assert res['summary']['footage_character'] == {'camera': 'cinema', 'support': 'tripod', 'look': 'natural', 'quote': 'Shot on a cinema camera, tripod, ungraded.'}
    res = media_record(ws, PROC, prior, fake_upload(calls), camera_audio='allowed', note='ok')
    assert res['summary']['footage_character'] is None
    steps = ' '.join(PROC['steps'])
    assert '--camera' in steps and '--support' in steps and '--look' in steps and 'footage_guess' in steps


def test_prepare_dedupes_first_name_wins_and_converts_vfr(ws):
    clip(ws / 'in' / 'a.mp4')
    (ws / 'in' / 'z-copy.mp4').write_bytes((ws / 'in' / 'a.mp4').read_bytes())
    clip(ws / 'in' / 'v.mp4', seconds=2, rate=25, vfr=True)
    out = media_prepare(ws, PROC, prior)
    by = {c['name']: c for c in json.loads((ws / 'work' / 'media-clips.json').read_text(encoding='utf-8'))}
    assert set(by) == {'a.mp4', 'v.mp4'} and out['duplicates_skipped'] == 1
    assert by['v.mp4']['transcoded_from_vfr'] and by['v.mp4']['path'] == 'work/cfr/v.mp4' and by['v.mp4']['is_variable_frame_rate'] is False
    assert by['v.mp4']['source_bytes'] == (ws / 'in' / 'v.mp4').stat().st_size   # the stat is of the original in in/, not the copy
    shown = {c['name']: c for c in out['clips']}
    assert shown['v.mp4']['transcoded_from_vfr'] is True and 'transcoded_from_vfr' not in shown['a.mp4']
    assert 'converted from variable frame rate' in out['listing'].split('\n')[1] and '1 duplicate skipped' in out['listing']


def test_prepare_refuses_an_oversized_clip_before_reading_it(ws):
    big = ws / 'in' / 'big.mp4'
    with big.open('wb') as f:
        f.seek(200 * 1024 * 1024)
        f.write(b'\0')   # sparse: the size check comes before any read
    clip(ws / 'in' / 'a.mp4')
    with pytest.raises(Refused) as exc:
        media_prepare(ws, PROC, prior)
    assert '200 MB' in str(exc.value) and 'big.mp4' in str(exc.value)


def test_a_refusal_inside_the_pool_surfaces_unchanged(ws):
    clip(ws / 'in' / 'a.mp4')
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'lavfi', '-i', 'sine=frequency=440:duration=1', '-c:a', 'aac', str(ws / 'in' / 'audio-only.mp4')], check=True)
    with pytest.raises(Refused) as exc:
        media_prepare(ws, PROC, prior)
    assert 'no video stream' in str(exc.value) and 'audio-only.mp4' in str(exc.value)


def test_record_stores_the_sound_answer_and_reports_progress(ws):
    clip(ws / 'in' / 'a.mp4')
    clip(ws / 'in' / 'b.mp4', tone=500)
    media_prepare(ws, PROC, prior)
    calls, progress = [], []
    res = media_record(ws, PROC, prior, fake_upload(calls), camera_audio='allowed', note='site noise only', progress=lambda k, n, name, size: progress.append((k, n, name)))
    s = res['summary']
    assert s['camera_audio'] == 'allowed' and s['camera_audio_note'] == 'site noise only' and len(s['clips']) == 2
    assert sorted(calls) == ['a.mp4', 'b.mp4'] and sorted(progress) == [(1, 2, 'a.mp4'), (2, 2, 'b.mp4')] or sorted(progress) == [(1, 2, 'b.mp4'), (2, 2, 'a.mp4')]
    assert [k for k, _, _ in sorted(progress)] == [1, 2]
    res = media_record(ws, PROC, prior, fake_upload([]))
    assert res['summary']['camera_audio'] is None and res['summary']['camera_audio_note'] == ''


def test_record_refuses_a_clip_changed_since_prepare(ws):
    clip(ws / 'in' / 'a.mp4')
    clip(ws / 'in' / 'b.mp4', tone=500)
    media_prepare(ws, PROC, prior)
    data = (ws / 'in' / 'b.mp4').read_bytes()
    time.sleep(0.02)
    (ws / 'in' / 'b.mp4').write_bytes(data[:-1] + bytes([data[-1] ^ 1]))   # same size, different bytes, new mtime
    with pytest.raises(Refused) as exc:
        media_record(ws, PROC, prior, fake_upload([]))
    assert 'changed since prepare' in str(exc.value) and 'b.mp4' in str(exc.value) and 'a.mp4' not in str(exc.value)
    media_prepare(ws, PROC, prior)
    os.utime(ws / 'in' / 'a.mp4')   # touched: same bytes, new mtime; prepare again is seconds
    with pytest.raises(Refused) as exc:
        media_record(ws, PROC, prior, fake_upload([]))
    assert 'a.mp4' in str(exc.value)
    media_prepare(ws, PROC, prior)
    assert media_record(ws, PROC, prior, fake_upload([]))['summary']['clips']


def test_cmd_stage_prints_progress_lines_and_passes_the_flags(ws, monkeypatch, capsys):
    clip(ws / 'in' / 'a.mp4')
    clip(ws / 'in' / 'b.mp4', tone=500)
    media_prepare(ws, PROC, prior)
    vw.save_json(ws / 'manifest.json', {'code': 'VW-9', 'run_id': 'run-1', 'client': 'VK', 'version': '2', 'files': []})
    monkeypatch.setattr(vw, 'RUNS', ws.parent)
    run = {'id': 'run-1', 'code': 'VW-9', 'procedure_version': '2', 'active_machine': None, 'outputs': [], 'next': {'stage': 'media', 'version': '2', 'active_machine': None}}
    monkeypatch.setattr(vw, 'request', lambda method, path, wait=None, **kw: (run, 0))
    monkeypatch.setattr(vw, 'machine_id', lambda: 'mac-1')
    monkeypatch.setattr(vw, 'upload_file', lambda m, stage, path, sha, size: {'name': os.path.basename(str(path)), 'key': f'k/{os.path.basename(str(path))}', 'sha256': sha, 'bytes': size, 'receipt': True, 'location': 'storage'})
    posted = {}

    def write(path, body, wait=None):
        posted.update(body)
        return {'id': 'out-1', 'stage': 'media', 'files': body['files'], 'summary': body['summary'], 'next': {'stage': 'analysis', 'paid': 'gemini-3.8-flash'}}
    monkeypatch.setattr(vw, 'write', write)
    a = argparse.Namespace(stage='media', step='record', quote='yes these clips', title=None, file=None, take_over=False, camera_audio='excluded', note='no usable sound',
                           camera='mirrorless', support='handheld', look='graded', footage_note='Sony, handheld, graded in camera')
    with pytest.raises(SystemExit) as exc:
        vw.cmd_stage(a)
    out, err = capsys.readouterr()
    assert exc.value.code == 0, err
    assert 'uploaded 1/2 ' in err and 'uploaded 2/2 ' in err and '(0 MB)' in err and 'Recorded media. Next: analysis.' in err
    assert posted['summary']['camera_audio'] == 'excluded' and posted['summary']['camera_audio_note'] == 'no usable sound' and len(posted['summary']['clips']) == 2
    assert posted['summary']['footage_character'] == {'camera': 'mirrorless', 'support': 'handheld', 'look': 'graded', 'quote': 'Sony, handheld, graded in camera'}   # design/77 L42
    shown = json.loads(out)   # design/57: the receipt, not the row; the per-clip summary and the file references stay on the server
    assert shown['id'] == 'out-1' and shown['next']['stage'] == 'analysis' and shown['clips_recorded'] == 2 and 'total_mb' in shown
    assert 'clips' not in shown['summary'] and shown['summary']['camera_audio'] == 'excluded' and isinstance(shown['files'], str) and '3 file' in shown['files']   # out/media.json and the two clips


def test_media_prompt_and_steps_are_v2():
    p = PROC['prompt']
    for stale in ('library', ' UI', 'page', 'backend', 'teammates', '50 videos', 'timeline'):
        assert stale not in p, stale
    assert p.startswith('VW-PROCEDURE') and 'names and bytes' in p and 'not an analysis' in p and '--camera-audio' in p and len(p.split()) < 160
    steps = ' '.join(PROC['steps'])
    assert '--camera-audio' in steps and 'total MB' in steps and 'reports when the upload is done' in steps and 'changed since prepare' in steps
    assert 'one line per clip' in steps and 'work/media-clips.json' in steps   # design/57
    assert 'in the foreground' in steps and 'at least 30 minutes' in steps and 'never as a background command' in steps   # design/59 L16
