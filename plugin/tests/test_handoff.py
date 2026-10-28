"""design/107 slice 2, on the operator's computer: the Resolve check (Step B), the download into runs/VW-n/edit (C), the count and cross-check (D),
the timeline written with this computer's paths (E), the free route's steps (F) and the zip (G)."""
import argparse
import hashlib
import json
import zipfile

import pytest

import handoff as H
import vw


def fcp(cuts, film_frames=400, fps=25, narration=True):
    """A timeline file as the server writes it (design/107 slice 1): one gap, connected clips with lanes, one asset per file."""
    files = sorted({c[0] for c in cuts} | ({'Media/Voiceover/narration.mp3'} if narration else set()))
    ids = {f: f'a{i + 1}' for i, f in enumerate(files)}
    assets = ''.join(f'<asset id="{ids[f]}" name="{f.rsplit("/", 1)[-1]}" start="0s" duration="0s" hasVideo="1" hasAudio="1" format="r1"><media-rep kind="original-media" src="file://./{f}"/></asset>' for f in files)
    clips = ''.join(f'<asset-clip ref="{ids[f]}" lane="1" offset="{a}/{fps}s" name="c{i}" start="{s}/{fps}s" duration="{b - a}/{fps}s" format="r1" enabled="1"/>' for i, (f, s, a, b) in enumerate(cuts))
    voice = f'<asset-clip ref="{ids["Media/Voiceover/narration.mp3"]}" lane="-1" offset="0s" name="Voiceover" start="0s" duration="{film_frames}/{fps}s" role="dialogue.voiceover" enabled="1"/>' if narration else ''
    return (f'<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE fcpxml>\n<fcpxml version="1.9"><resources><format id="r1" name="FFVideoFormat1080p25" frameDuration="1/{fps}s" width="1920" height="1080"/>{assets}</resources>'
            f'<library><event name="VW-9"><project name="VW-9"><sequence format="r1" duration="{film_frames}/{fps}s" tcStart="0s" tcFormat="NDF"><spine><gap name="Film" offset="0s" start="0s" duration="{film_frames}/{fps}s">'
            f'{clips}{voice}</gap></spine></sequence></project></event></library></fcpxml>')


CUTS = [('Media/Camera/C1.MP4', 250, 0, 100), ('Media/AI/VS1.mp4', 0, 100, 400)]


def edit(tmp_path, bad=None, missing=None, cuts=CUTS, film_frames=400, n_cuts=2):
    """An edit folder downloaded from a manifest; `bad` gets wrong bytes, `missing` is left out."""
    d = tmp_path / 'runs' / 'VW-9' / 'edit'
    import shutil
    shutil.rmtree(d, ignore_errors=True)   # each call is a fresh folder
    rows = []
    for name, body in (('Media/Camera/C1.MP4', b'camera' * 10), ('Media/AI/VS1.mp4', b'ai' * 10), ('Media/Voiceover/narration.mp3', b'voice' * 10), ('Approved-film.mp4', b'film' * 10)):
        rows.append({'name': name, 'role': {'Camera': 'original', 'AI': 'ai', 'Voiceover': 'narration'}.get(name.split('/')[1] if '/' in name else '', 'film'), 'sha256': hashlib.sha256(body).hexdigest(), 'bytes': len(body)})
        if name != missing:
            (d / name).parent.mkdir(parents=True, exist_ok=True)
            (d / name).write_bytes(body[:-1] + b'!' if name == bad else body)
    text = fcp(cuts, film_frames)
    (d / 'Timeline').mkdir(parents=True, exist_ok=True)
    (d / 'Timeline' / 'VW-9.fcpxml').write_bytes(text.encode('utf-8'))   # bytes, as a download lands
    rows.append({'name': 'Timeline/VW-9.fcpxml', 'role': 'generated', 'sha256': hashlib.sha256(text.encode('utf-8')).hexdigest(), 'bytes': len(text.encode('utf-8'))})
    manifest = {'run': 'VW-9', 'files': rows, 'timeline': {'fps': 25}, 'timeline_file': 'Timeline/VW-9.fcpxml', 'film_frames': film_frames, 'cuts': n_cuts}
    return d, manifest


# ---------- Step B ----------

def test_the_resolve_check_reads_windows_and_mac_and_says_studio_free_or_not_found():
    r = H.find_resolve('Windows', entries=[('Blackmagic RAW Player', '4.6'), ('DaVinci Resolve Studio', '21.1.1.0')], plist=None)
    assert r == {'found': True, 'version': '21.1.1', 'edition': 'studio'}
    assert H.find_resolve('Windows', entries=[('DaVinci Resolve', '21.1.1.0')], plist=None)['edition'] == 'free'
    assert H.find_resolve('Windows', entries=[], plist=None) == {'found': False, 'version': None, 'edition': None}
    assert H.find_resolve('Darwin', entries=None, plist={'CFBundleShortVersionString': '21.1', 'CFBundleName': 'DaVinci Resolve Studio'}) == {'found': True, 'version': '21.1', 'edition': 'studio'}
    assert H.find_resolve('Darwin', entries=None, plist={'CFBundleShortVersionString': '21.1', 'CFBundleName': 'DaVinci Resolve'})['edition'] == 'free'
    assert H.find_resolve('Darwin', entries=None, plist=None)['found'] is False


def test_the_check_is_said_in_plain_words():
    gb = 1024 ** 3
    assert H.check_words({'found': True, 'version': '21.1', 'edition': 'studio'}, int(3.2 * gb), 140 * gb) == 'Resolve 21.1 Studio found. 3.2 GB needed, 140 GB free.'
    assert H.check_words({'found': True, 'version': '21.1', 'edition': 'free'}, gb, 10 * gb) == 'Resolve 21.1 (free) found. The edit will open by one import step, shown at the end. 1.0 GB needed, 10 GB free.'
    assert H.check_words({'found': False, 'version': None, 'edition': None}, gb, 10 * gb) == 'Resolve not found. Install it, then press the button again.'
    assert H.check_words({'found': True, 'version': '21.1', 'edition': 'studio'}, 50 * gb, 10 * gb) == 'Resolve 21.1 Studio found. Not enough disk space: 50.0 GB needed, 10 GB free. Free some space, then press the button again.'


# ---------- Step D ----------

def test_the_cross_check_passes_a_complete_folder_and_counts_it(tmp_path):
    d, manifest = edit(tmp_path)
    rep = H.cross_check(d, manifest)
    assert rep['ok'] and rep['present'] == '5 of 5 files' and rep['cuts'] == 2 and rep['timeline_frames'] == 400 and rep['problems'] == []


def test_the_cross_check_names_a_wrong_file_a_missing_file_a_cut_pointing_nowhere_and_a_wrong_length(tmp_path):
    d, manifest = edit(tmp_path, bad='Media/AI/VS1.mp4')
    rep = H.cross_check(d, manifest)
    assert not rep['ok'] and any('Media/AI/VS1.mp4' in p and 'fingerprint' in p for p in rep['problems'])
    d, manifest = edit(tmp_path, missing='Media/Camera/C1.MP4')
    rep = H.cross_check(d, manifest)
    assert rep['present'] == '4 of 5 files' and any('Media/Camera/C1.MP4' in p and 'missing' in p for p in rep['problems']) and any('cut 1' in p and 'Media/Camera/C1.MP4' in p for p in rep['problems'])
    d, manifest = edit(tmp_path, film_frames=401)   # the timeline's gap says 401, the cuts end at 400
    manifest['film_frames'] = 400
    rep = H.cross_check(d, manifest)
    assert any('401' in p and '400' in p for p in rep['problems'])
    d, manifest = edit(tmp_path, n_cuts=3)
    assert any('2 cuts' in p and '3' in p for p in H.cross_check(d, manifest)['problems'])


def test_the_voiceover_must_be_the_approved_one_byte_for_byte(tmp_path):
    d, manifest = edit(tmp_path, bad='Media/Voiceover/narration.mp3')
    assert any('voiceover' in p.lower() for p in H.cross_check(d, manifest)['problems'])


# ---------- Step E ----------

def test_the_timeline_is_written_with_this_computers_paths_and_the_portable_one_kept(tmp_path):
    d, manifest = edit(tmp_path)
    out = H.write_timeline_for(d, manifest, base='C:\\Users\\Revathi\\runs\\VW-9\\edit')
    final = (d / 'Timeline' / 'VW-9.fcpxml').read_text(encoding='utf-8')
    assert 'file:///C:/Users/Revathi/runs/VW-9/edit/Media/Camera/C1.MP4' in final and 'file://./' not in final
    assert 'file://./Media/Camera/C1.MP4' in (d / 'Timeline' / 'VW-9.portable.fcpxml').read_text(encoding='utf-8')
    assert out.endswith('VW-9.fcpxml')
    H.write_timeline_for(d, manifest, base='/Users/sk/My Films/VW-9/edit')
    assert 'file:///Users/sk/My%20Films/VW-9/edit/Media/AI/VS1.mp4' in (d / 'Timeline' / 'VW-9.fcpxml').read_text(encoding='utf-8')


# ---------- Steps F and G ----------

def test_the_free_route_says_three_steps_and_the_side_by_side_check():
    text = H.free_route_text('VW-9')
    for words in ('1.', 'new project', 'File > Import > Timeline', 'Timeline/VW-9.fcpxml', 'start, the middle and the end', 'Approved-film.mp4', 'vw delivery confirm'):
        assert words in text, words


def test_the_zip_has_open_edit_first_and_everything_else(tmp_path):
    d, manifest = edit(tmp_path)
    (d / 'OPEN-EDIT.md').write_text('# OPEN-EDIT', encoding='utf-8')
    z = H.zip_edit(d, 'VW-9')
    with zipfile.ZipFile(z) as zf:
        names = zf.namelist()
    assert names[0] == 'VW-9-edit/OPEN-EDIT.md' and 'VW-9-edit/Timeline/VW-9.fcpxml' in names and 'VW-9-edit/Media/Camera/C1.MP4' in names and z.name == 'VW-9-edit.zip'


# ---------- the command ----------

@pytest.fixture
def cli(monkeypatch, tmp_path):
    monkeypatch.setattr(vw, 'RUNS', tmp_path / 'runs')
    m = {'code': 'VW-9', 'run_id': 'run-1', 'files': []}
    monkeypatch.setattr(vw, 'active', lambda: m)
    monkeypatch.setattr(vw, 'machine_id', lambda: 'pc-1')
    sent = []
    monkeypatch.setattr(vw, 'write', lambda path, body, **kw: sent.append((path.rsplit('/delivery/', 1)[-1], body)) or {'state': body.get('state', 'reserved'), 'manifest': {'key': 'k-man'}, 'files': 5, 'bytes': 1})
    return m, sent, tmp_path


def args(**kw):
    base = {'what': 'check', 'check': False, 'run_it': False, 'inspect': False, 'close': False, 'authorization': None, 'note': None, 'quote': None, 'camera': False, 'originals': None}
    return argparse.Namespace(**{**base, **kw})


def run(a, capsys):
    with pytest.raises(SystemExit) as exc:
        vw.cmd_delivery(a)
    out, err = capsys.readouterr()
    return exc.value.code, json.loads(out), err


def test_download_stops_before_any_download_when_resolve_is_not_found(cli, monkeypatch, capsys):
    m, sent, tmp_path = cli
    monkeypatch.setattr(vw.handoff, 'find_resolve', lambda: {'found': False, 'version': None, 'edition': None})
    monkeypatch.setattr(vw, 'call', lambda *a, **k: {'bundle': {'manifest': {'key': 'k-man'}, 'bytes': 10}})
    monkeypatch.setattr(vw, 'download_bundle', lambda *a, **k: pytest.fail('nothing may download'))
    code, out, err = run(args(what='download'), capsys)
    assert code == 2 and out['message'].startswith('Resolve not found')


def test_download_checks_downloads_cross_checks_and_writes_the_timeline(cli, monkeypatch, capsys):
    m, sent, tmp_path = cli
    d, manifest = edit(tmp_path)
    monkeypatch.setattr(vw.handoff, 'find_resolve', lambda: {'found': True, 'version': '21.1', 'edition': 'free'})
    monkeypatch.setattr(vw, 'call', lambda *a, **k: {'bundle': {'manifest': {'key': 'k-man'}, 'bytes': 10}})
    monkeypatch.setattr(vw, '_download', lambda m, key, rel, expect=None: str(tmp_path / 'runs' / 'VW-9' / rel))
    (tmp_path / 'runs' / 'VW-9' / 'work').mkdir(parents=True, exist_ok=True)
    (tmp_path / 'runs' / 'VW-9' / 'work' / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
    got = []
    monkeypatch.setattr(vw, 'download_bundle', lambda m, man, into=None, **kw: got.append(into) or {})
    code, out, err = run(args(what='download'), capsys)
    assert code == 0 and got == [d] and out['check']['ok'] and out['resolve']['edition'] == 'free' and 'free' in out['open'].lower()
    assert 'file:///' in (d / 'Timeline' / 'VW-9.fcpxml').read_text(encoding='utf-8')


def test_confirm_records_the_operators_side_by_side_check_on_the_ledger(cli, monkeypatch, capsys):
    m, sent, tmp_path = cli
    d, manifest = edit(tmp_path)
    (tmp_path / 'runs' / 'VW-9' / 'work').mkdir(parents=True, exist_ok=True)
    (tmp_path / 'runs' / 'VW-9' / 'work' / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
    code, out, err = run(args(what='confirm', quote='Yes, the start, middle and end match the film.'), capsys)
    assert code == 0 and [s[0] for s in sent] == ['resolve/reserve', 'resolve/mark', 'resolve/mark']
    rep = sent[2][1]['report']
    assert sent[2][1]['state'] == 'reported' and rep['route'] == 'free' and rep['timeline_verified'] is True and rep['cuts'] == 2 and rep['quote'].startswith('Yes')
    code, out, err = run(args(what='confirm'), capsys)
    assert code == 2 and 'words' in out['message']
