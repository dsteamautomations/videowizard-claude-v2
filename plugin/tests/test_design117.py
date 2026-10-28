"""design/117 on the plugin: `vw visuals scene --shot S --file scene.svg` posts the file; `--download` saves the scene as the server left it;
`image --kind component` passes the kind through; both refuse without their argument."""
from test_visuals_cli import args, harness, run  # noqa: F401  (the fixture rides along)
import vw


def test_scene_posts_the_file_and_download_saves_the_servers_scene(harness, monkeypatch, capsys, tmp_path):
    posted, got = {}, {}
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: (posted.update(body, path=path) or {'sha256': 'a' * 64, 'next': 'Scene stored.'}))
    monkeypatch.setattr(vw, 'call', lambda method, path, **kw: (got.update(method=method, path=path) or {'shot_id': 'DR1', 'job_id': 'j1', 'fixed': True, 'svg': '<svg/>', 'passes': [{'pass': 1}]}))
    code, out, err = run(args(what='scene'), capsys)
    assert code == 2 and 'scene --shot S' in out['message'] and not posted
    code, out, err = run(args(what='scene', shot='DR1', file=str(tmp_path / 'none.svg')), capsys)
    assert code == 2 and '.svg file' in out['message'] and not posted
    f = tmp_path / 'scene.svg'
    f.write_bytes(b'<svg/>')
    code, out, err = run(args(what='scene', shot='DR1', file=str(f)), capsys)
    assert code == 0 and posted['shot_id'] == 'DR1' and posted['name'] == 'scene.svg' and posted['content_base64'] == 'PHN2Zy8+' and posted['path'].endswith('/scene')
    code, out, err = run(args(what='scene', shot='DR1', download=True), capsys)
    assert code == 0 and got['method'] == 'GET' and got['path'].endswith('/scene/DR1') and out['fixed'] is True and out['file'].endswith('scene-DR1-fixed.svg')
    assert open(out['file'], encoding='utf-8').read() == '<svg/>'


def test_image_passes_the_component_kind_through(harness, monkeypatch, capsys):
    posted = {}
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: (posted.update(body, path=path) or {'model': 'm', 'reference_id': 'r1'}))
    code, out, err = run(args(what='image', element='E2', kind='component', prompt='One flame on logs, front on.', name='flame', subject='the flame'), capsys)
    assert code == 0 and posted['kind'] == 'component' and posted['element_id'] == 'E2' and posted['path'].endswith('/images')


def test_scene_takes_only_its_flags():
    assert vw.VISUALS_FLAGS['scene'] == {'shot', 'file', 'download'} and 'scene' in vw.VISUALS_WHAT
