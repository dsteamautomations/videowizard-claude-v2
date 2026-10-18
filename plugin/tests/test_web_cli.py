"""vw web (design/48 O.1): the operator's yes recorded for the guard."""
import argparse
import json

import pytest

import vw


@pytest.fixture
def harness(monkeypatch, tmp_path):
    monkeypatch.setattr(vw, 'RUNS', tmp_path / 'runs')
    ws = tmp_path / 'runs' / 'VW-9'
    (ws / 'work').mkdir(parents=True)
    monkeypatch.setattr(vw, 'active', lambda: {'code': 'VW-9', 'run_id': 'run-1', 'files': []})
    return ws


def run(a, capsys):
    with pytest.raises(SystemExit) as exc:
        vw.cmd_web(a)
    out, err = capsys.readouterr()
    return exc.value.code, json.loads(out), err


def test_web_records_the_subject_and_the_words(harness, capsys):
    code, out, err = run(argparse.Namespace(about='the client product photos', ok='yes, go ahead and search'), capsys)
    assert code == 0
    ok = json.loads((harness / 'work' / 'web-ok.json').read_text(encoding='utf-8'))
    assert ok['about'] == 'the client product photos' and ok['ok'] == 'yes, go ahead and search' and ok['by'] == 'operator' and ok['calls'] == [] and ok['at'].endswith('+00:00')
    assert 'ten minutes' in err and 'show what you found' in err


def test_web_without_the_words_is_refused(harness, capsys):
    code, out, err = run(argparse.Namespace(about='x', ok=None), capsys)
    assert code == 2 and '--ok' in out['message']
    assert not (harness / 'work' / 'web-ok.json').exists()
