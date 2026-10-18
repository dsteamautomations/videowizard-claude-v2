"""design/48 O.3: vw defect --log and vw start --script stay inside what the operator may read; O.2: the open-defect refusal."""
import argparse
import json
from pathlib import Path

import pytest

import vw


@pytest.fixture
def harness(monkeypatch, tmp_path):
    monkeypatch.setattr(vw, 'RUNS', tmp_path / 'runs')
    monkeypatch.setattr(vw, 'HOME', tmp_path / 'home')
    ws = tmp_path / 'runs' / 'VW-9'
    for d in ('in', 'out', 'work', 'logs'):
        (ws / d).mkdir(parents=True)
    monkeypatch.setattr(vw, 'active', lambda: {'code': 'VW-9', 'run_id': 'run-1', 'files': []})
    return tmp_path, ws


def run(fn, a, capsys):
    with pytest.raises(SystemExit) as exc:
        fn(a)
    out, err = capsys.readouterr()
    return exc.value.code, json.loads(out), err


# ---------- vw defect --log ----------

def test_defect_log_outside_the_run_is_refused(harness, monkeypatch, capsys):
    tmp_path, ws = harness
    secret = tmp_path / '.vw2' / 'session.json'
    secret.parent.mkdir()
    secret.write_text('{"token": "secret"}', encoding='utf-8')
    monkeypatch.setattr(vw, 'write', lambda *a, **k: pytest.fail('nothing should be sent'))
    code, out, err = run(vw.cmd_defect, argparse.Namespace(stage='brief', error='boom', log=str(secret)), capsys)
    assert code == 2 and 'inside the run folder' in out['message']


def test_defect_log_inside_the_run_is_sent(harness, monkeypatch, capsys):
    tmp_path, ws = harness
    (ws / 'logs' / 'vw.log').write_text('line one\nline two\n', encoding='utf-8')
    posted = {}
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: (posted.update(body) or {'ticket': 7}))
    code, out, err = run(vw.cmd_defect, argparse.Namespace(stage='brief', error='boom', log='logs/vw.log'), capsys)
    assert code == 0 and posted['log_excerpt'] == 'line one\nline two\n' and 'ticket' in err


# ---------- vw start --script ----------

def test_start_script_refuses_hidden_and_system_places(harness, monkeypatch, capsys):
    tmp_path, ws = harness
    hidden = tmp_path / '.claude' / 'notes.md'
    hidden.parent.mkdir()
    hidden.write_text('x', encoding='utf-8')
    monkeypatch.setattr(vw, 'write', lambda *a, **k: pytest.fail('the run must not be created'))
    for path in (str(hidden), '/private/etc/hosts.md', str(Path.home() / 'Library' / 'Application Support' / 'x.txt')):
        code, out, err = run(vw.cmd_start, argparse.Namespace(client='C', version=None, script=path, need_gb=0, keep_logs=False), capsys)
        assert code == 2 and 'cannot read from' in out['message'], path


def test_start_script_copies_an_ordinary_file_and_logs_it(harness, monkeypatch, capsys):
    tmp_path, ws = harness
    script = tmp_path / 'Desktop' / 'script.md'
    script.parent.mkdir()
    script.write_text('A script.', encoding='utf-8')
    monkeypatch.setattr(vw, 'preflight', lambda gb: None)
    monkeypatch.setattr(vw, 'machine_id', lambda: 'mac-1')
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: {'id': 'run-2', 'code': 'VW-10', 'client': 'C', 'procedure_version': '2'})
    monkeypatch.setattr(vw, 'call', lambda method, path, wait=None, **kw: {'stage': 'intake', 'needs_acceptance': True})
    code, out, err = run(vw.cmd_start, argparse.Namespace(client='C', version=None, script=str(script), need_gb=0, keep_logs=False), capsys)
    assert code == 0 and out['script_file'] == 'script.md' and (tmp_path / 'runs' / 'VW-10' / 'in' / 'script.md').read_text(encoding='utf-8') == 'A script.'
    log = (tmp_path / 'runs' / 'VW-10' / 'work' / 'guard.log').read_text(encoding='utf-8')
    assert ' · vw start --script · allowed · ' in log and 'script.md' in log


# ---------- the open-defect refusal and the next line ----------

def test_an_open_defect_refusal_tells_the_operator(capsys):
    with pytest.raises(SystemExit) as exc:
        vw.finish({'action': 'refused', 'status': 409, 'code': 'DEFECT_OPEN', 'defect': 7, 'message': 'defect 7 is open on this run; the builder resolves it, then the run continues'}, 2)
    out, err = capsys.readouterr()
    assert exc.value.code == 2 and 'A defect is open on this run (7)' in err and 'builder is on it' in err


def test_next_line_names_open_defects():
    assert vw.next_line({'stage': 'brief', 'open_defects': [7]}).endswith(' · defect 7 open')
    assert 'defect' not in vw.next_line({'stage': 'brief', 'open_defects': []})
