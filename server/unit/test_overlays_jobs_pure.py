"""Text overlays, build step 2b (requirements version 3 of 28 Nov 2026, part E): the worker's side. One overlay becomes a project folder with the
server's own files, a still picture on the shot's frame, and a transparent clip that is passed on only when its length, size and transparency are right."""
import shutil
import subprocess
from pathlib import Path

import pytest

from app import motion
from app import overlay_jobs as J
from app import overlays as O

FILM = {'fps': 25, 'frames': 400, 'cuts': [{'name': 'S01-1', 'start_frame': 0, 'end_frame': 400}],
        'words': [{'start_frame': i * 10, 'end_frame': i * 10 + 8, 'text': 'w'} for i in range(40)], 'font': 'Inter', 'scripts': ['latin']}
PAGE = {'fps': 25, 'width': 1920, 'height': 1080, 'accent': '#c8643c', 'scripts': ['latin']}


def row(**k):
    out = O.check({'overlays': [{'kind': 'callout', 'lines': ['Two weeks'], 'word': 3, **k}]}, FILM)
    assert out['problems'] == []
    return out['rows'][0]


class Store(dict):
    def put(self, key, data, kind):
        self[key] = (data, kind)


def test_the_fonts_of_an_overlay_are_its_own_fonts_files_and_noto_sans_for_the_signs():
    files = [f['file'] for f in J.faces('Inter', ['latin'])]
    assert files[0].startswith('Inter') and 'NotoSans-Variable.ttf' in files
    assert [f['family'] for f in J.faces('Noto Sans', ['latin'])].count('Noto Sans') == 1
    tamil = J.faces('Noto Sans', ['latin', 'tamil'])
    assert any('Tamil' in f['file'] for f in tamil)


def test_the_project_folder_holds_the_page_and_the_servers_gsap_and_fonts(tmp_path):
    folder = J.project(tmp_path / 'p', row(), PAGE, gsap=b'GSAP', font_bytes=lambda name: b'FONT ' + name.encode())
    assert (folder / 'index.html').read_text(encoding='utf-8').startswith('<!doctype html>')
    assert (folder / 'assets/vendor/gsap.min.js').read_bytes() == b'GSAP'
    assert (folder / 'assets/fonts/NotoSans-Variable.ttf').read_bytes() == b'FONT NotoSans-Variable.ttf'
    assert any(p.name.startswith('Inter') for p in (folder / 'assets/fonts').iterdir())
    assert (folder / 'hyperframes.json').exists() and not (folder / 'index.motion.json').exists()


def test_a_folder_from_an_earlier_try_is_written_afresh(tmp_path):
    (tmp_path / 'p').mkdir()
    (tmp_path / 'p' / 'old.txt').write_text('x')
    J.project(tmp_path / 'p', row(), PAGE, gsap=b'G', font_bytes=lambda n: b'F')
    assert not (tmp_path / 'p' / 'old.txt').exists()


def test_the_transparent_clip_is_asked_of_hyperframes_as_a_mov(monkeypatch, tmp_path):
    seen = {}

    def run(args, cwd, timeout=None):
        seen['args'] = args
        Path(args[args.index('-o') + 1]).write_bytes(b'MOV')
        return subprocess.CompletedProcess(args, 0, '', '')
    monkeypatch.setattr(motion, 'run', run)
    out = motion.render_mov(tmp_path, 25, tmp_path / 'o.mov')
    assert seen['args'][:5] == ['render', '--format', 'mov', '--fps', '25'] and out.read_bytes() == b'MOV'
    monkeypatch.setattr(motion, 'run', lambda args, cwd, timeout=None: subprocess.CompletedProcess(args, 1, '', 'chrome crashed'))
    with pytest.raises(RuntimeError, match='chrome crashed'):
        motion.render_mov(tmp_path, 25, tmp_path / 'none.mov')


GOOD = {'frames': 45, 'width': 1920, 'height': 1080, 'pix_fmt': 'yuva444p12le'}


@pytest.mark.parametrize('seen, said', [
    (GOOD, []),
    ({**GOOD, 'frames': 44}, ['44 frames for 45']),
    ({**GOOD, 'width': 1280, 'height': 720}, ['1280x720 for 1920x1080']),
    ({**GOOD, 'pix_fmt': 'yuv422p10le'}, ['no transparent background (yuv422p10le)']),
    ({'frames': 0, 'width': None, 'height': None, 'pix_fmt': None}, ['0 frames for 45', 'NonexNone for 1920x1080', 'no transparent background (None)']),
])
def test_the_three_checks_of_a_clip(seen, said):
    assert J.clip_faults(seen, 45, 1920, 1080) == said


def render_to(data=b'CLIP'):
    def render(folder, fps, out):
        Path(out).write_bytes(data)
        return Path(out)
    return render


def clip(tmp_path, store, **k):
    return J.clip(row(), PAGE, tmp_path / 'job', 'run/visuals/overlays/O01.mov', store, gsap=b'G', font_bytes=lambda n: b'F', **{'render': render_to(), 'probe': lambda p: GOOD, **k})


def test_a_good_clip_is_kept_with_its_fingerprint(tmp_path):
    store = Store()
    status, result, error = clip(tmp_path, store)
    assert (status, error) == ('ready', None) and store['run/visuals/overlays/O01.mov'] == (b'CLIP', 'video/quicktime')
    assert result['key'] == 'run/visuals/overlays/O01.mov' and result['bytes'] == 4 and len(result['sha256']) == 64 and result['frames'] == 45


def test_a_clip_that_fails_a_check_is_not_passed_on(tmp_path):
    store = Store()
    status, result, error = clip(tmp_path, store, probe=lambda p: {**GOOD, 'pix_fmt': 'yuv420p'})
    assert status == 'failed' and store == {} and error == 'The overlay clip is not right: no transparent background (yuv420p).' and result['faults']


def test_a_render_that_fails_is_reported_with_its_reason(tmp_path):
    def boom(folder, fps, out):
        raise RuntimeError('render failed: chrome crashed')
    status, result, error = clip(tmp_path, Store(), render=boom)
    assert status == 'failed' and 'chrome crashed' in error


def test_the_still_is_the_overlay_laid_on_the_shots_frame_at_the_moment_everything_is_in(tmp_path):
    store, seen = Store(), {}

    def snapshot(folder, at, zoom, out_dir):
        seen['at'] = at
        Path(out_dir).mkdir(parents=True, exist_ok=True)
        (Path(out_dir) / 'frame-00.png').write_bytes(b'PNG')
        return [Path(out_dir) / 'frame-00.png']

    def compose(base, over, out, width, height):
        seen['compose'] = (Path(base).read_bytes(), Path(over).read_bytes(), width, height)
        Path(out).write_bytes(b'JPG')
    status, result, error = J.still(row(), PAGE, b'BASE', tmp_path / 'job', 'run/visuals/overlays/O01.jpg', store, gsap=b'G', font_bytes=lambda n: b'F',
                                    snapshot=snapshot, compose=compose)
    assert (status, error) == ('ready', None) and store['run/visuals/overlays/O01.jpg'] == (b'JPG', 'image/jpeg')
    assert seen['at'] == [pytest.approx(0.9)] and seen['compose'] == (b'BASE', b'PNG', 1920, 1080)   # 2 words: 1.8 s; the middle


def test_a_still_that_cannot_be_drawn_is_reported(tmp_path):
    def snapshot(folder, at, zoom, out_dir):
        raise RuntimeError('snapshot failed: no chrome')
    status, result, error = J.still(row(), PAGE, b'BASE', tmp_path / 'job', 'k.jpg', Store(), gsap=b'G', font_bytes=lambda n: b'F', snapshot=snapshot, compose=None)
    assert status == 'failed' and 'no chrome' in error


@pytest.mark.skipif(not shutil.which('ffmpeg'), reason='needs ffmpeg')
def test_laying_a_transparent_picture_on_a_frame_gives_a_picture_of_the_films_size(tmp_path, monkeypatch):
    monkeypatch.setattr(J, 'FFMPEG', lambda: 'ffmpeg')
    make = lambda spec, out: subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'lavfi', '-i', spec, '-frames:v', '1', str(out)], check=True)
    make('color=c=red:s=640x360', tmp_path / 'base.png')                     # a frame smaller than the film: it is fitted
    make('color=c=black@0.0:s=1280x720,format=rgba', tmp_path / 'over.png')
    J.compose(tmp_path / 'base.png', tmp_path / 'over.png', tmp_path / 'out.jpg', 1280, 720)
    size = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'stream=width,height', '-of', 'csv=p=0', str(tmp_path / 'out.jpg')], capture_output=True, text=True).stdout.strip()
    assert size == '1280,720'
