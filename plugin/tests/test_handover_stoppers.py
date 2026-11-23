"""Hand-over stoppers (SK, 23 Nov 2026) on the operator's tool. Fix 1: `vw delivery open` on Resolve Studio uploads the Resolve timeline file
and reports it as a stored file. Fix 2: `download` always brings the server's current package list; `open` and `confirm` refuse on an old
one. Fix 3: `confirm` does not count the camera copies the default download left out."""
import argparse
import hashlib
import json

import pytest

import handoff as H
import vw
from test_handoff import edit

EVENTS = [{'file': 'Media/Camera/C1.MP4', 'source_in_frame': 250, 'source_out_frame': 350, 'record_in_frame': 0, 'record_out_frame': 100, 'source_fps': '25'},
          {'file': 'Media/AI/VS1.mp4', 'source_in_frame': 0, 'source_out_frame': 300, 'record_in_frame': 100, 'record_out_frame': 400, 'source_fps': '25'}]


@pytest.fixture
def film(monkeypatch, tmp_path):
    """An edit folder as `download` leaves it, the package list on the computer, and the server's answers; `say` holds what the tool sent."""
    d, manifest = edit(tmp_path)
    manifest['resolve_events'] = EVENTS
    manifest['narration_pieces'] = [{'file': 'Media/Voiceover/narration.mp3', 'source_in_frame': 0, 'source_out_frame': 400, 'record_in_frame': 0}]
    ws = d.parent
    (ws / 'work').mkdir()
    m = {'code': 'VW-9', 'run_id': 'run-1', 'files': []}
    say = {'writes': [], 'downloads': [], 'stage3': {}}
    monkeypatch.setattr(vw, 'RUNS', tmp_path / 'runs')
    monkeypatch.setattr(vw, 'HOME', tmp_path / 'home')
    monkeypatch.setattr(vw, 'active', lambda: m)
    monkeypatch.setattr(vw, 'manifest_path', lambda code: ws / 'manifest.json')
    monkeypatch.setattr(vw, 'machine_id', lambda: 'pc-b')
    monkeypatch.setattr(vw, 'call', lambda method, path, **kw: say['stage3'])
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: say['writes'].append((path, body)) or {'state': body.get('state', 'reserved')})
    monkeypatch.setattr(vw, 'download_bundle', lambda m, manifest, into=None, roles=None: {})
    monkeypatch.setattr(H, 'find_resolve', lambda *a, **kw: {'found': True, 'version': '21.1', 'edition': 'studio'})
    monkeypatch.setenv('VW2_RESOLVE_FAKE', '1')

    def put(manifest, current=True):
        """Write the list on this computer; the server's current list is this one, or (current=False) a newer one."""
        text = json.dumps(manifest).encode('utf-8')
        (ws / 'work' / 'manifest.json').write_bytes(text)
        newer = text if current else json.dumps({**manifest, 'made_again': True}).encode('utf-8')
        say['stage3'] = {'bundle': {'bytes': 100, 'manifest': {'key': 'run-1/delivery/manifest.json', 'sha256': hashlib.sha256(newer).hexdigest(), 'bytes': len(newer)}}}
        return newer
    return d, manifest, ws, say, put


def run(what, capsys, **kw):
    a = argparse.Namespace(what=what, camera=False, quote=None, originals=None, run_it=False, check=False, inspect=False, close=False, note=None)
    for k, v in kw.items():
        setattr(a, k, v)
    with pytest.raises(SystemExit) as exc:
        vw.cmd_delivery(a)
    cap = capsys.readouterr()
    return exc.value.code, json.loads(cap.out), cap.err


# ---------- fix 2: the package list ----------

def test_download_brings_the_current_list_over_an_old_one(film, monkeypatch, capsys):
    d, manifest, ws, say, put = film
    newer = put(manifest, current=False)

    def download(m, key, rel, expect=None):
        say['downloads'].append((key, rel, expect))
        (ws / rel).write_bytes(newer)
    monkeypatch.setattr(vw, '_download', download)
    code, out, err = run('download', capsys, camera=True)
    assert code == 0, out
    assert say['downloads'] == [('run-1/delivery/manifest.json', 'work/manifest.json', say['stage3']['bundle']['manifest'])]


def test_download_fetches_nothing_when_the_list_here_is_the_current_one(film, monkeypatch, capsys):
    d, manifest, ws, say, put = film
    put(manifest)
    monkeypatch.setattr(vw, 'api', lambda: (_ for _ in ()).throw(AssertionError('the list was fetched again')))
    code, out, err = run('download', capsys, camera=True)
    assert code == 0, out


def test_open_refuses_on_an_old_list_and_names_the_command(film, monkeypatch, capsys):
    d, manifest, ws, say, put = film
    put(manifest, current=False)
    code, out, err = run('open', capsys)
    assert code == 2 and '`vw delivery download`' in out['message'] and 'made again' in out['message'] and not say['writes']


def test_confirm_refuses_on_an_old_list_and_names_the_command(film, monkeypatch, capsys):
    d, manifest, ws, say, put = film
    put(manifest, current=False)
    code, out, err = run('confirm', capsys, quote='the start, the middle and the end match')
    assert code == 2 and '`vw delivery download`' in out['message'] and not say['writes']


# ---------- fix 3: confirm after the default download ----------

def test_confirm_passes_after_the_default_download_left_the_camera_copies_out(film, capsys):
    d, manifest, ws, say, put = film
    put(manifest)
    (d / 'Media' / 'Camera' / 'C1.MP4').unlink()
    code, out, err = run('confirm', capsys, quote='the start, the middle and the end match')
    assert code == 0, out
    assert [b.get('state') for p, b in say['writes']] == [None, 'dispatched', 'reported']


def test_confirm_names_a_camera_copy_missing_from_a_camera_download(film, capsys):
    d, manifest, ws, say, put = film
    manifest['files'].append({'name': 'Media/Camera/C2.MP4', 'role': 'original', 'sha256': 'c' * 64, 'bytes': 5})
    put(manifest)   # C1 is here, so the copies were brought; C2 is not
    code, out, err = run('confirm', capsys, quote='the start, the middle and the end match')
    assert code == 2 and 'C2.MP4' in out['message'] and '`vw delivery download --camera`' in out['message'] and not say['writes']


def test_confirm_still_names_any_other_missing_file(film, capsys):
    d, manifest, ws, say, put = film
    put(manifest)
    (d / 'Media' / 'Camera' / 'C1.MP4').unlink()
    (d / 'Media' / 'AI' / 'VS1.mp4').unlink()
    code, out, err = run('confirm', capsys, quote='the start, the middle and the end match')
    assert code == 2 and 'VS1.mp4' in out['message']


# ---------- fix 1: the Resolve timeline file goes to the server ----------

def test_open_on_studio_uploads_the_timeline_file_and_reports_it_as_stored(film, monkeypatch, capsys):
    d, manifest, ws, say, put = film
    put(manifest)
    H.write_timeline_for(d, manifest, base=str(d))
    sent = []
    ref = {'name': 'VW-9.drt', 'key': 'run-1/delivery/VW-9.drt', 'sha256': 'd' * 64, 'bytes': 7, 'receipt': True, 'location': 'storage'}
    monkeypatch.setattr(vw, 'upload_file', lambda m, stage, path, sha, size: sent.append((stage, str(path), sha, size)) or ref)
    code, out, err = run('open', capsys)
    assert code == 0, out
    drt = d / 'Timeline' / 'VW-9.drt'
    assert sent == [('delivery', str(drt), hashlib.sha256(drt.read_bytes()).hexdigest(), drt.stat().st_size)]
    report = say['writes'][-1][1]['report']
    assert report['drt'] == ref and report['drt_path'] == str(drt) and report['drt_verified'] and 'kept on the server' in err


def test_a_failed_upload_of_the_timeline_file_does_not_stop_the_hand_over(film, monkeypatch, capsys):
    d, manifest, ws, say, put = film
    put(manifest)
    H.write_timeline_for(d, manifest, base=str(d))

    def refused(*a):
        vw.emit({'action': 'tell_builder', 'message': 'Storage refused the upload'}, 2)
    monkeypatch.setattr(vw, 'upload_file', refused)
    code, out, err = run('open', capsys)
    assert code == 0, out
    report = say['writes'][-1][1]['report']
    assert 'drt' not in report and report['drt_path'].endswith('VW-9.drt') and say['writes'][-1][1]['state'] == 'reported'
    assert 'could not be uploaded' in err and 'Storage refused' not in err
