"""design/120: `vw start` needs --images openai|gemini; without it the operator is asked and no run is created; with it the choice is posted and said."""
import argparse
import json

import pytest

import vw


def start_args(**kw):
    base = {'client': 'Cobuild', 'version': None, 'script': None, 'need_gb': 1, 'keep_logs': False, 'images': None}
    return argparse.Namespace(**{**base, **kw})


def run_start(a, capsys):
    with pytest.raises(SystemExit) as exc:
        vw.cmd_start(a)
    out, err = capsys.readouterr()
    return exc.value.code, json.loads(out), err


def test_start_without_images_asks_and_creates_nothing(monkeypatch, capsys):
    posted = []
    monkeypatch.setattr(vw, 'preflight', lambda need: None)
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: posted.append((path, body)) or {})
    code, out, err = run_start(start_args(), capsys)
    assert code == 2 and 'which image model' in out['message'] and '--images' in out['message'] and 'cannot change later' in out['message'] and posted == []


def test_start_with_images_posts_the_provider_and_says_it(monkeypatch, capsys, tmp_path):
    posted = []
    monkeypatch.setattr(vw, 'preflight', lambda need: None)
    monkeypatch.setattr(vw, 'workspace', lambda code: tmp_path / 'runs' / code)
    monkeypatch.setattr(vw, 'make_workspace', lambda run, keep_logs=False, **k: {'code': run['code']})
    monkeypatch.setattr(vw, 'call', lambda method, path, **k: {'stage': 'intake'})
    monkeypatch.setattr(vw, 'next_line', lambda nxt: 'next: intake')
    monkeypatch.setattr(vw, 'machine_id', lambda: 'pc-1')

    def write(path, body, wait=None):
        posted.append((path, body))
        return {'id': 'r1', 'code': 'VW-21', 'client': 'Cobuild', 'image_provider': body.get('image_provider')} if path == '/api/runs' else {}
    monkeypatch.setattr(vw, 'write', write)
    code, out, err = run_start(start_args(images='gemini'), capsys)
    assert code == 0 and posted[0] == ('/api/runs', {'client': 'Cobuild', 'image_provider': 'gemini'}) and out['image_provider'] == 'gemini' and 'images: gemini' in err
