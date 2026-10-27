"""Code review of 27 Oct 2026, group B (design/109), the plugin side: the cross-check reads the portable timeline, so `confirm` passes after
`download` wrote this computer's paths (plugin 1); the relink check compares frame rates to three decimals (plugin 2); the disk-space check counts
what is already in the edit folder (plugin 3)."""
import hashlib
import json

import pytest

import handoff as H
import vw
from test_download import Storage, Stream, body, setup   # noqa: F401 (the fixture)
from test_handoff import cli, edit, args, run   # noqa: F401 (the fixture)


class Flaky(Storage):
    """A storage link whose failure script may also answer with an HTTP status."""
    def stream(self, method, url, headers=None):
        if self.failures and isinstance(self.failures[0], int) and self.failures[0] > 1:
            self.ranges.append((headers or {}).get('Range'))
            return Stream(self.failures.pop(0), {}, b'')
        return super().stream(method, url, headers)


# ---------- plugin minor: a storage 5xx is retried, a 4xx is not ----------

def test_a_storage_503_is_retried_after_the_usual_wait_and_a_404_is_not(setup, monkeypatch):
    m, api, use, slept, ws = setup
    data = body(2000)
    st = Flaky(data, failures=[503, 0])
    monkeypatch.setattr(vw, '_storage_client', lambda: st)
    vw._download(m, 'k1', 'bundle/C1.MP4', expect={'bytes': 2000, 'sha256': hashlib.sha256(data).hexdigest()})
    assert (ws / 'bundle/C1.MP4').read_bytes() == data and len(st.ranges) == 2 and slept == [5]
    st = Flaky(data, failures=[404])
    monkeypatch.setattr(vw, '_storage_client', lambda: st)
    with pytest.raises(SystemExit):
        vw._download(m, 'k1', 'bundle/C2.MP4', expect={'bytes': 2000, 'sha256': hashlib.sha256(data).hexdigest()})
    assert len(st.ranges) == 1 and slept == [5]


# ---------- plugin 1 ----------

def test_the_cross_check_passes_after_the_timeline_got_this_computers_paths(tmp_path):
    d, manifest = edit(tmp_path)
    H.write_timeline_for(d, manifest, base='C:\\Users\\Revathi\\runs\\VW-9\\edit')
    rep = H.cross_check(d, manifest)
    assert rep['ok'] and rep['present'] == '5 of 5 files' and rep['cuts'] == 2, rep['problems']
    H.write_timeline_for(d, manifest, base='/Users/sk/edit')   # written again for another computer: still the same portable file
    assert H.cross_check(d, manifest)['ok']
    (d / 'Timeline' / 'VW-9.portable.fcpxml').write_bytes(b'<fcpxml/>')
    assert any('Timeline/VW-9.fcpxml' in p for p in H.cross_check(d, manifest)['problems'])   # a changed timeline is still caught


def test_confirm_passes_after_download_on_the_same_folder(cli, monkeypatch, capsys):
    m, sent, tmp_path = cli
    d, manifest = edit(tmp_path)
    (tmp_path / 'runs' / 'VW-9' / 'work').mkdir(parents=True, exist_ok=True)
    (tmp_path / 'runs' / 'VW-9' / 'work' / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
    H.write_timeline_for(d, manifest)   # what `vw delivery download` leaves behind
    code, out, err = run(args(what='confirm', quote='Yes, the start, middle and end match the film.'), capsys)
    assert code == 0 and [s[0] for s in sent] == ['resolve/reserve', 'resolve/mark', 'resolve/mark'], out


# ---------- plugin 2 ----------

def test_the_relink_check_matches_an_ntsc_rate_written_to_three_decimals(tmp_path):
    cuts = [('Media/Camera/C0170.mp4', 0, 0, 100)]
    d, manifest = edit(tmp_path, cuts=cuts, n_cuts=1)
    H.write_timeline_for(d, manifest)
    o = tmp_path / 'originals'
    o.mkdir()
    (o / 'C0170.mp4').write_bytes(b'x')
    row = {'name': 'C0170.mp4', 'stem': 'C0170', 'extension': '.mp4', 'frames': '3000', 'fps': '29.970', 'width': '1920', 'height': '1080', 'duration_s': '100.1', 'start_timecode': '', 'reel': '', 'cuts': '1'}
    probe = lambda p: {'frames': 3000, 'fps': '30000/1001', 'start_timecode': '', 'width': 1920, 'height': 1080}
    rep = H.relink_check(d, 'VW-9', [row], o, probe=probe, grab=lambda *a: None)
    assert [l['outcome'] for l in rep['lines']] == ['match'], rep['lines']
    rep = H.relink_check(d, 'VW-9', [{**row, 'fps': '25'}], o, probe=probe, grab=lambda *a: None)
    assert [l['outcome'] for l in rep['lines']] == ['by_hand'] and 'frame rate differs' in rep['lines'][0]['line']
    assert H.same_rate('29.970', '30000/1001') and H.same_rate('23.976', '24000/1001') and not H.same_rate('25', '24') and not H.same_rate('30', '30000/1001')


# ---------- plugin 3 ----------

def test_the_disk_space_check_counts_what_the_edit_folder_already_holds(tmp_path):
    d, manifest = edit(tmp_path)
    have = sum(p.stat().st_size for p in d.rglob('*') if p.is_file())
    assert H.present_bytes(d) == have and H.present_bytes(tmp_path / 'nowhere') == 0
    assert H.needed_bytes(have + 100, d) == 100 and H.needed_bytes(10, d) == 0


def test_a_second_download_is_not_refused_for_the_space_the_first_one_took(cli, monkeypatch, capsys):
    m, sent, tmp_path = cli
    d, manifest = edit(tmp_path)
    have = H.present_bytes(d)
    monkeypatch.setattr(vw.handoff, 'find_resolve', lambda: {'found': True, 'version': '21.1', 'edition': 'free'})
    monkeypatch.setattr(vw.handoff, 'free_bytes', lambda ws: 5)
    monkeypatch.setattr(vw, 'call', lambda *a, **k: {'bundle': {'manifest': {'key': 'k-man'}, 'bytes': have}})
    (tmp_path / 'runs' / 'VW-9' / 'work').mkdir(parents=True, exist_ok=True)
    (tmp_path / 'runs' / 'VW-9' / 'work' / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
    monkeypatch.setattr(vw, 'download_bundle', lambda m, man, into=None, **kw: {})
    code, out, err = run(args(what='download'), capsys)
    assert code == 0 and out['check']['ok'], out   # the folder already holds the bundle: nothing more is needed
    have = H.present_bytes(d)   # the download left the portable timeline beside the rewritten one
    monkeypatch.setattr(vw, 'call', lambda *a, **k: {'bundle': {'manifest': {'key': 'k-man'}, 'bytes': have + 6}})
    code, out, err = run(args(what='check'), capsys)
    assert code == 2 and 'Not enough disk space' in out['message'] and out['needed_bytes'] == 6
