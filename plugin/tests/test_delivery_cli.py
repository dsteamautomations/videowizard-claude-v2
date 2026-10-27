"""vw delivery --run's pooled bundle download and vw close keeping the guard log (design/47 12.4, 12.5); the command text."""
import argparse
import json

import pytest

from conftest import PLUGIN
import vw


@pytest.fixture
def harness(monkeypatch, tmp_path):
    monkeypatch.setattr(vw, 'RUNS', tmp_path / 'runs')
    monkeypatch.setattr(vw, 'HOME', tmp_path / 'home')
    ws = tmp_path / 'runs' / 'VW-9'
    for d in ('in', 'out', 'work', 'logs'):
        (ws / d).mkdir(parents=True)
    (tmp_path / 'runs' / '.active').write_text('VW-9', encoding='utf-8')
    manifest = {'code': 'VW-9', 'run_id': 'run-1', 'files': [{'name': 'Approved-film.mp4', 'action': 'retain', 'receipt': True}], 'keep_logs': False, 'closed': False}
    (ws / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
    monkeypatch.setattr(vw, 'active', lambda: manifest)
    monkeypatch.setattr(vw, 'manifest_path', lambda code: ws / 'manifest.json')
    return ws, manifest


# ---------- 12.4 the bundle downloads three at a time, with a line each ----------

def test_bundle_download_is_pooled_and_reports_each_file(harness, monkeypatch, capsys):
    ws, m = harness
    files = [{'role': 'original', 'name': f'Media/Originals/C{i}.MP4', 'key': f'k{i}', 'bytes': 20_000_000} for i in range(5)] + \
            [{'role': 'narration', 'name': 'Audio/narration.mp3', 'key': 'kn', 'bytes': 4_000_000}, {'role': 'generated', 'name': 'Subtitles.srt', 'key': 'ks', 'bytes': 100}]
    done = []
    monkeypatch.setattr(vw, '_download', lambda m, key, rel, expect=None: (done.append(rel) or str(ws / rel)))
    got = vw.download_bundle(m, {'files': files})
    assert len(got) == 6 and sorted(done) == sorted('bundle/' + f['name'] for f in files if f['role'] != 'generated')
    err = capsys.readouterr().err
    assert 'downloaded 1/6' in err and 'downloaded 6/6' in err and 'narration.mp3 (4 MB)' in err


def test_bundle_download_stops_on_a_failed_file(harness, monkeypatch, capsys):
    ws, m = harness
    files = [{'role': 'original', 'name': 'Media/Originals/C1.MP4', 'key': 'k1', 'bytes': 1}, {'role': 'original', 'name': 'Media/Originals/C2.MP4', 'key': 'k2', 'bytes': 1}]

    def download(m, key, rel, expect=None):
        if key == 'k2':
            raise SystemExit(2)
        return str(ws / rel)
    monkeypatch.setattr(vw, '_download', download)
    with pytest.raises(SystemExit) as exc:
        vw.download_bundle(m, {'files': files})
    out = json.loads(capsys.readouterr().out)
    assert exc.value.code == 2 and 'C2.MP4' in out['message'] and 'before dispatch' in out['message']


def test_delivery_command_has_no_dead_branch():
    src = (PLUGIN / 'scripts' / 'vw.py').read_text(encoding='utf-8')
    assert 'if False else None' not in src


# ---------- 12.5 close keeps logs/ with the guard log ----------

def test_close_moves_the_guard_log_into_logs_and_keeps_logs(harness, monkeypatch, capsys):
    ws, m = harness
    (ws / 'work' / 'guard.log').write_text('12:00 · Bash · NOT_HERE · git status\n', encoding='utf-8')
    (ws / 'work' / 'options-package.json').write_text('{}', encoding='utf-8')
    (ws / 'logs' / 'vw.log').write_text('x', encoding='utf-8')
    (ws / 'out' / 'Approved-film.mp4').write_bytes(b'film')
    (ws / 'out' / 'review.mp4').write_bytes(b'scratch')
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: {'status': 'closed', 'retention': {'kept': 3, 'deleted': 9}})
    with pytest.raises(SystemExit) as exc:
        vw.cmd_close(argparse.Namespace())
    err = capsys.readouterr().err
    assert exc.value.code == 0
    assert not (ws / 'work').exists() and (ws / 'logs' / 'guard.log').read_text(encoding='utf-8').startswith('12:00') and (ws / 'logs' / 'vw.log').exists()
    assert (ws / 'out' / 'Approved-film.mp4').exists() and not (ws / 'out' / 'review.mp4').exists()
    assert 'logs/ kept' in err and 'guard log' in err


def test_close_without_a_guard_log_still_keeps_logs(harness, monkeypatch, capsys):
    ws, m = harness
    (ws / 'logs' / 'vw.log').write_text('x', encoding='utf-8')
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: {'status': 'closed', 'retention': {'kept': 1, 'deleted': 0}})
    with pytest.raises(SystemExit):
        vw.cmd_close(argparse.Namespace())
    assert (ws / 'logs' / 'vw.log').exists() and not (ws / 'logs' / 'guard.log').exists()


def test_command_text_names_the_pooled_download_and_the_kept_logs():
    md = (PLUGIN / 'commands' / 'vw.md').read_text(encoding='utf-8')
    assert 'three at a time' in md and 'keeps logs/' in md
