"""design/218: `vw font --sample` saves the server's picture of the offered fonts in work/chat/ and says to show it, then ask as before; when the
server cannot make it, the one line and exit 0 (the question is never blocked). `vw motion colour` records a neutral colour Claude chose."""
import argparse
import base64
import json

import pytest

from test_visuals_cli import harness  # noqa: F401  (the fixture rides along)
import vw


def _film(capsys, **kw):
    with pytest.raises(SystemExit) as exc:
        vw.cmd_film(argparse.Namespace(**{'key': 'font', 'value': [], 'quote': None, 'sample': True, **kw}))
    out, err = capsys.readouterr()
    return exc.value.code, json.loads(out), err


def test_the_sample_is_saved_and_shown_first(harness, monkeypatch, capsys):
    ws, _ = harness
    png = b'\x89PNG fake'
    monkeypatch.setattr(vw, 'call', lambda method, path, wait=None, **kw: {'available': True, 'asked': True, 'message': '', 'file': 'font-sample.png',
                                                                       'base64': base64.b64encode(png).decode('ascii'), 'fonts': ['Anek', 'Mukta']})
    code, out, err = _film(capsys)
    saved = ws / 'work' / 'chat' / 'font-sample.png'
    assert code == 0 and saved.read_bytes() == png and out['show_files'] == [str(saved)] and 'base64' not in out
    assert f'File to show: {saved}' in err and 'Anek, Mukta' in err and 'Other' in err


def test_no_sample_says_the_one_line_and_does_not_block(harness, monkeypatch, capsys):
    monkeypatch.setattr(vw, 'call', lambda method, path, wait=None, **kw: {'available': False, 'asked': True, 'message': 'The font sample is not available.', 'reason': 'x', 'fonts': []})
    code, out, err = _film(capsys)
    assert code == 0 and 'The font sample is not available.' in err and 'ask the font question as before' in err and 'reason' not in out


def test_motion_colour_posts_the_thing_the_colour_and_the_reason(harness, monkeypatch, capsys):
    posted = {}
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: (posted.update(body, path=path) or {'next': 'Added.'}))
    a = argparse.Namespace(what='colour', shot='D1,D2', thing='walls', colour='#5A524C', words='dark warm grey', reason='the palette named none', quote=None,
                           dir=None, sha=None, at=None, zoom=None, job=None, file=None, subject=None, add=None, crop=None, off=False, on=False)
    with pytest.raises(SystemExit) as exc:
        vw.cmd_motion(a)
    assert exc.value.code == 0 and posted['path'].endswith('/motion/colour')
    assert posted['shots'] == ['D1', 'D2'] and posted['thing'] == 'walls' and posted['colour'] == '#5A524C' and posted['quote'] == ''
    with pytest.raises(SystemExit) as exc:
        vw.cmd_motion(argparse.Namespace(**{**vars(a), 'reason': None}))
    assert exc.value.code == 2
