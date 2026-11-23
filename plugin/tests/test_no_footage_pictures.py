"""SK, 23 Nov 2026 (no-footage release 3, T3): the tool lists the operator's pictures of the run folder's in/, its folders too, and says which
files the server does not read. in/brand/ stays apart (logos are references)."""
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location('vw', Path(__file__).resolve().parents[1] / 'scripts' / 'vw.py')
vw = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vw)


def test_the_pictures_of_the_run_folder_are_listed(tmp_path):
    for name in ('in/site.JPG', 'in/photos/press.png', 'in/logo.svg', 'in/brand/mark.png', 'in/script.docx', 'in/clip.mp4', 'out/made.png'):
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_bytes(b'x')
    assert vw.in_pictures(tmp_path) == (['in/photos/press.png', 'in/site.JPG'], ['in/logo.svg'])
    line = vw.pictures_line(tmp_path)
    assert '2 pictures' in line and 'in/site.JPG' in line and 'in/logo.svg' in line and 'PNG, JPEG or WebP' in line


def test_a_run_folder_with_no_picture_says_nothing(tmp_path):
    assert vw.in_pictures(tmp_path) == ([], []) and vw.pictures_line(tmp_path) == ''
