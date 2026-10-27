"""design/113 E2, E4: `vw visuals draw --shot S` posts the shot; `vw visuals font --file brand.ttf` posts the file; both refuse without their argument."""
from test_visuals_cli import args, harness, run  # noqa: F401  (the fixture rides along)
import vw


def test_draw_posts_the_shot_and_font_posts_the_file(harness, monkeypatch, capsys, tmp_path):
    posted = {}
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: (posted.update(body, path=path) or {'job_id': 'j1', 'frames': 100, 'next': 'Rendering 100 frames, free.'}))
    code, out, err = run(args(what='draw'), capsys)
    assert code == 2 and 'draw --shot S' in out['message'] and not posted
    code, out, err = run(args(what='draw', shot='DR1'), capsys)
    assert code == 0 and posted['shot_id'] == 'DR1' and posted['path'].endswith('/draw')
    posted.clear()
    code, out, err = run(args(what='font', file=str(tmp_path / 'none.ttf')), capsys)
    assert code == 2 and '.ttf or .otf' in out['message'] and not posted
    f = tmp_path / 'brand.otf'
    f.write_bytes(b'OTTO-fake')
    code, out, err = run(args(what='font', file=str(f)), capsys)
    assert code == 0 and posted['name'] == 'brand.otf' and posted['content_base64'] == 'T1RUTy1mYWtl' and posted['path'].endswith('/font')
