"""cmd_stage and friends with the server replaced by fakes (design/34 1.15, 1.16, 1.18): which calls are made, in what
order, how a failure inside a thread surfaces, and what the record prints."""
import argparse
import json
import threading
import time
from pathlib import Path

import pytest

from conftest import STAGES
import vw

SOURCE = 'Narration: Earth blocks are made from the soil beneath our feet.\n'


class Fake:
    """Answers GET /api/runs/{id} and the procedure; records every request with its thread."""

    def __init__(self, procedure_fail=False, record_next=True):
        self.calls, self.procedure_fail, self.record_next = [], procedure_fail, record_next
        self.run = {'id': 'run-1', 'code': 'VW-9', 'client': 'VK', 'procedure_version': '2', 'active_machine': None,
                    'outputs': [], 'next': {'stage': 'intake', 'version': '2', 'active_machine': None, 'paid': None}}

    def request(self, method, path, wait=None, **kw):
        self.calls.append((method, path, threading.current_thread().name))
        time.sleep(0.2)   # long enough that two serial calls (0.4 s) and two side-by-side ones (0.2 s) are told apart
        if path.startswith('/api/procedures/'):
            if self.procedure_fail:
                return {'action': 'tell_builder', 'status': 503, 'message': 'procedures down'}, 2
            return STAGES['intake'], 0
        if path == '/api/runs/run-1':
            return self.run, 0
        if path.endswith('/output'):
            row = {'id': 'out-1234567890', 'stage': 'intake'}
            if self.record_next:
                row['next'] = {'stage': 'brief', 'paid': None}
            return row, 0
        raise AssertionError(path)


@pytest.fixture
def harness(ws, monkeypatch):
    fake = Fake()
    monkeypatch.setattr(vw, 'RUNS', ws.parent)
    monkeypatch.setattr(vw, 'request', fake.request)
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: vw.call('POST', path, json=body))
    monkeypatch.setattr(vw, 'machine_id', lambda: 'mac-1')
    uploaded = []

    def upload_file(m, stage, path, sha, size):
        uploaded.append((Path(path).name, threading.current_thread().name))
        return {'name': Path(path).name, 'key': f'VW-9/{stage}/{Path(path).name}', 'sha256': sha, 'bytes': size, 'receipt': True, 'location': 'storage'}
    monkeypatch.setattr(vw, 'upload_file', upload_file)
    vw.save_json(ws / 'manifest.json', {'code': 'VW-9', 'run_id': 'run-1', 'client': 'VK', 'version': '2', 'files': [],
                                        'client_runs': [{'code': 'VW-3', 'title': 'Earlier film'}]})
    (ws / 'in' / 'source.txt').write_text(SOURCE, encoding='utf-8')
    return fake, uploaded


def args(**kw):
    return argparse.Namespace(**{'stage': 'intake', 'step': 'prepare', 'quote': None, 'title': None, 'file': None, 'take_over': False, **kw})


def run(fn, a, capsys):
    with pytest.raises(SystemExit) as exc:
        fn(a)
    out, err = capsys.readouterr()
    return exc.value.code, json.loads(out), err


def test_prepare_fetches_run_and_procedure_side_by_side(harness, capsys):
    fake, _ = harness
    started = time.monotonic()
    code, out, err = run(vw.cmd_stage, args(), capsys)
    elapsed = time.monotonic() - started
    assert code == 0, err
    paths = sorted(p for _, p, _ in fake.calls)
    assert paths == ['/api/procedures/2/intake', '/api/runs/run-1'] and '/api/runs/run-1/next' not in paths
    assert all(t != 'MainThread' for _, _, t in fake.calls) and elapsed < 0.35   # side by side: not 0.4 s of serial waiting
    assert out['not_shareable'].startswith('The stage prompt') and 'VW-3: Earlier film' in out['prompt']


def test_procedure_failure_in_the_thread_surfaces_on_the_main_thread(harness, capsys):
    fake, _ = harness
    fake.procedure_fail = True
    code, out, _ = run(vw.cmd_stage, args(), capsys)
    assert code == 2 and out['action'] == 'tell_builder' and out['message'] == 'procedures down'


def test_record_fetches_the_run_alone_uploads_in_parallel_and_prints_next(harness, capsys, ws):
    fake, uploaded = harness
    run(vw.cmd_stage, args(), capsys)
    fake.calls.clear()
    (ws / 'out' / 'intake.json').write_text(json.dumps({'remove': [], 'titles': ['Earth Blocks - Explainer'], 'notes': ''}), encoding='utf-8')
    code, out, err = run(vw.cmd_stage, args(step='record', title='Earth Blocks - Explainer', quote='yes'), capsys)
    assert code == 0, err
    paths = [p for _, p, _ in fake.calls]
    assert paths == ['/api/runs/run-1', '/api/runs/run-1/output']   # no next, no procedure
    assert sorted(n for n, _ in uploaded) == ['intake.json', 'original.txt', 'source.txt']
    assert all(t != 'MainThread' for _, t in uploaded)
    assert 'Recorded intake. Next: brief.' in err
    assert out['next']['stage'] == 'brief'


def test_record_on_an_older_server_still_says_run_next(harness, capsys, ws):
    fake, _ = harness
    fake.record_next = False
    run(vw.cmd_stage, args(), capsys)
    (ws / 'out' / 'intake.json').write_text(json.dumps({'remove': [], 'titles': ['Earth Blocks - Explainer'], 'notes': ''}), encoding='utf-8')
    code, _, err = run(vw.cmd_stage, args(step='record', title='Earth Blocks - Explainer', quote='yes'), capsys)
    assert code == 0 and 'Run `vw next`' in err


def test_old_manifest_without_version_falls_back_to_serial_calls(harness, capsys, ws):
    fake, _ = harness
    m = vw.load_json(ws / 'manifest.json')
    del m['version']
    vw.save_json(ws / 'manifest.json', m)
    code, _, err = run(vw.cmd_stage, args(), capsys)
    assert code == 0, err
    assert [p for _, p, _ in fake.calls] == ['/api/runs/run-1', '/api/procedures/2/intake']
    assert all(t == 'MainThread' for _, _, t in fake.calls)


def test_next_line():
    assert vw.next_line({'stage': 'voice', 'paid': 'elevenlabs'}) == 'Next: voice. This step uses a paid provider (elevenlabs); tell the operator, do not ask.'
    assert vw.next_line({'stage': None}) == 'All stages done; close the run.'
    assert vw.next_line(None) == ''


def test_start_refuses_a_missing_script_before_creating_the_run(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(vw, 'RUNS', tmp_path / 'runs')
    created = []
    monkeypatch.setattr(vw, 'write', lambda *a, **k: created.append(a))
    monkeypatch.setattr(vw, 'preflight', lambda need: None)
    a = argparse.Namespace(client='VK', version=None, need_gb=0, keep_logs=False, script=str(tmp_path / 'missing.docx'))
    with pytest.raises(SystemExit) as exc:
        vw.cmd_start(a)
    out = json.loads(capsys.readouterr()[0])
    assert exc.value.code == 2 and 'not created' in out['message'] and created == []


def test_start_keeps_last_brief_and_client_rules_and_tolerates_their_absence(monkeypatch, tmp_path, capsys):
    """design/37 2.2, 2.3: the start answer's client memory lands in the manifest; an older server sends none."""
    monkeypatch.setattr(vw, 'RUNS', tmp_path / 'runs')
    monkeypatch.setattr(vw, 'preflight', lambda need: None)
    monkeypatch.setattr(vw, 'machine_id', lambda: 'mac-1')
    answers = [{'id': 'run-7', 'code': 'VW-7', 'client': 'VK', 'client_id': 'c-vk', 'procedure_version': '2', 'client_runs': [{'code': 'VW-3', 'title': 'T'}],
                'last_brief': {'run': 'VW-3', 'production': {'narration_language': 'en'}, 'answers': {}, 'questions': []},
                'client_rules': [{'rule': 'r1', 'source_run': 'VW-3', 'at': 'x'}]},
               {'id': 'run-8', 'code': 'VW-8', 'client': 'VK', 'client_id': 'c-vk', 'procedure_version': '2'}]
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: answers.pop(0) if path == '/api/runs' else {})
    monkeypatch.setattr(vw, 'request', lambda method, path, wait=None, **kw: ({'stage': 'intake'}, 0))
    a = argparse.Namespace(client='VK', version=None, need_gb=0, keep_logs=False, script=None)
    for code, expect_brief, expect_rules in (('VW-7', True, 1), ('VW-8', False, 0)):
        with pytest.raises(SystemExit) as exc:
            vw.cmd_start(a)
        assert exc.value.code == 0, capsys.readouterr()
        capsys.readouterr()
        m = vw.load_json(tmp_path / 'runs' / code / 'manifest.json')
        assert (m['last_brief'] is not None) is expect_brief and len(m['client_rules']) == expect_rules and m['version'] == '2'
