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
    assert f'File to show: {saved}' in err and 'Anek, Mukta' in err and 'Other fonts are not available.' in err and '`vw visuals next`' in err   # release 1 of 27 Nov 2026, phase 3 part A: the server's card asks


def test_no_sample_says_the_one_line_and_does_not_block(harness, monkeypatch, capsys):
    monkeypatch.setattr(vw, 'call', lambda method, path, wait=None, **kw: {'available': False, 'asked': True, 'message': 'The font sample is not available.', 'reason': 'x', 'fonts': []})
    code, out, err = _film(capsys)
    assert code == 0 and 'The font sample is not available.' in err and 'Other fonts are not available.' in err and 'reason' not in out


def test_motion_colour_posts_the_thing_the_colour_and_the_reason(harness, monkeypatch, capsys):
    posted = {}
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: (posted.update(body, path=path) or {'next': 'Added.'}))
    a = argparse.Namespace(what='colour', shot='D1,D2', thing='walls', colour='#5A524C', words='dark warm grey', reason='the palette named none', quote=None,
                           dir=None, sha=None, at=None, zoom=None, job=None, file=None, subject=None, add=None, crop=None, off=False, on=False, text=None, remove=None)
    with pytest.raises(SystemExit) as exc:
        vw.cmd_motion(a)
    assert exc.value.code == 0 and posted['path'].endswith('/motion/colour')
    assert posted['shots'] == ['D1', 'D2'] and posted['thing'] == 'walls' and posted['colour'] == '#5A524C' and posted['quote'] == ''
    with pytest.raises(SystemExit) as exc:
        vw.cmd_motion(argparse.Namespace(**{**vars(a), 'reason': None}))
    assert exc.value.code == 2


def test_motion_note_posts_the_shots_and_the_line(harness, monkeypatch, capsys):
    posted = {}
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: (posted.update(body, path=path) or {'next': 'Recorded.'}))
    a = argparse.Namespace(what='note', shot='D1, D2', text='The steel is shown from the side in D1 and cut across here.', quote=None, thing=None, colour=None, words=None, reason=None,
                           dir=None, sha=None, at=None, zoom=None, job=None, file=None, subject=None, add=None, crop=None, off=False, on=False, remove=None)
    with pytest.raises(SystemExit) as exc:
        vw.cmd_motion(a)
    assert exc.value.code == 0 and posted['path'].endswith('/motion/note') and posted['remove'] == '' and posted['shots'] == ['D1', 'D2'] and posted['text'].startswith('The steel')
    with pytest.raises(SystemExit) as exc:
        vw.cmd_motion(argparse.Namespace(**{**vars(a), 'text': ' '}))
    assert exc.value.code == 2


def test_motion_note_remove_posts_the_line_to_withdraw(harness, monkeypatch, capsys):
    posted = {}
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: (posted.update(body, path=path) or {'next': 'Withdrawn.'}))
    a = argparse.Namespace(what='note', shot='D2', text=None, remove='The steel is shown from the side in D1 and cut across here.', quote=None, thing=None, colour=None,
                           words=None, reason=None, dir=None, sha=None, at=None, zoom=None, job=None, file=None, subject=None, add=None, crop=None, off=False, on=False)
    with pytest.raises(SystemExit) as exc:
        vw.cmd_motion(a)
    assert exc.value.code == 0 and posted['shots'] == ['D2'] and posted['remove'].startswith('The steel') and posted['text'] == ''
