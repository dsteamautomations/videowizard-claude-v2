"""Integration step A on the plugin: a hand-in says how the file was made (`--made`), and `vw visuals generations --shot S` lists a shot's attempts."""
from test_visuals_cli import args, harness, run  # noqa: F401  (the fixture rides along)
import vw

FILES = [{'name': 'walk.mp4', 'receipt': 'r1', 'key': 'run-1/uploads/walk.mp4', 'sha256': 'a' * 64, 'bytes': 10}]


def test_a_hand_in_without_how_it_was_made_is_refused_before_anything_is_sent(harness, monkeypatch, capsys):
    monkeypatch.setattr(vw, 'active', lambda: {'code': 'VW-9', 'run_id': 'run-1', 'files': FILES})
    sent = []
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: sent.append(body) or {})
    for made in (None, '', '   '):
        code, out, err = run(args(what='asset', shot='S1', file='out/walk.mp4', kind='movie', quote='use mine', made=made), capsys)
        assert code == 2 and '--made' in out['message'] and 'Nothing was sent' in out['message']
    assert sent == []


def test_a_hand_in_sends_how_it_was_made(harness, monkeypatch, capsys):
    monkeypatch.setattr(vw, 'active', lambda: {'code': 'VW-9', 'run_id': 'run-1', 'files': FILES})
    sent = []
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: sent.append((path, body)) or {'kind': 'movie', 'record': 'made outside; checks skipped'})
    code, out, err = run(args(what='asset', shot='S1', file='out/walk.mp4', kind='movie', quote='use mine', made='Blender guide and a Gemini edit, by hand.'), capsys)
    assert code == 0 and sent[0][0].endswith('/asset') and sent[0][1]['made'] == 'Blender guide and a Gemini edit, by hand.'
    assert out['record'] == 'made outside; checks skipped'


def test_generations_needs_a_shot_and_lists_the_attempts(harness, monkeypatch, capsys):
    assert run(args(what='generations'), capsys)[0] == 2
    asked = []
    rows = [{'attempt': 1, 'how': 'handed in', 'verdict': None, 'record': [{'made': 'First try.'}]}, {'attempt': 2, 'how': 'handed in', 'verdict': None, 'record': [{'made': 'Second try.'}]}]
    monkeypatch.setattr(vw, 'request', lambda method, path, wait=None, **kw: asked.append((method, path)) or ({'shot_id': 'S1', 'generations': rows}, 0))
    code, out, err = run(args(what='generations', shot='S1'), capsys)
    assert code == 0 and asked == [('GET', '/api/runs/run-1/visuals/shots/S1/generations')]
    assert 'S1: 2 generations.' in err and '#1 handed in: First try.' in err and '#2 handed in: Second try.' in err
    monkeypatch.setattr(vw, 'request', lambda method, path, wait=None, **kw: ({'shot_id': 'S1', 'generations': [], 'message': 'No generations yet for S1.'}, 0))
    code, out, err = run(args(what='generations', shot='S1'), capsys)
    assert code == 0 and 'No generations yet for S1.' in err


def test_only_the_flags_each_command_reads():
    assert 'made' in vw.VISUALS_FLAGS['asset'] and vw.VISUALS_FLAGS['generations'] == {'shot'}
