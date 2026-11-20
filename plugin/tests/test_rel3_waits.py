"""Release 3, E2 (SK, 20 Nov 2026, N2: "check first"): which commands already wait for the job they start was listed first (the builder's
report); the wait was missing on a drawing's render. `vw motion render --wait` and `vw motion status --job J --wait` wait inside the tool for
that one job, with the helper the check and the snapshot already use (`motion_wait`); without `--wait` both answer at once, as before."""
import argparse
import json

import pytest

import vw


def ns(**kw):
    base = {'what': 'render', 'shot': 'D1', 'dir': None, 'sha': None, 'at': None, 'zoom': None, 'job': None, 'file': None, 'subject': None, 'add': None, 'quote': None, 'thing': None,
            'colour': None, 'words': None, 'reason': None, 'text': None, 'remove': None, 'crop': None, 'off': False, 'on': False, 'still': False, 'wait': False}
    return argparse.Namespace(**{**base, **kw})


@pytest.fixture
def motion(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(vw, 'active', lambda: {'code': 'VW-9', 'run_id': 'run-1'})
    monkeypatch.setattr(vw, 'RUNS', tmp_path / 'runs')
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: calls.append(('POST', path)) or {'job_id': 'job-7', 'next': 'Rendering 250 frames on the server.'})
    states = iter(['queued', 'running', 'ready'])
    monkeypatch.setattr(vw, 'call', lambda method, path, wait=None, **kw: calls.append((method, path)) or {'status': next(states), 'result': {'key': 'run-1/takes/job-7.mp4'}})
    monkeypatch.setattr(vw.time, 'sleep', lambda s: calls.append(('sleep', s)))
    return calls


def run(a, capsys):
    with pytest.raises(SystemExit) as exc:
        vw.cmd_motion(a)
    out, err = capsys.readouterr()
    return exc.value.code, json.loads(out), err


def test_render_without_wait_answers_at_once_as_before(motion, capsys):
    code, out, err = run(ns(), capsys)
    assert code == 0 and motion == [('POST', '/api/runs/run-1/visuals/motion/render')] and err.strip() == 'Rendering 250 frames on the server.'


def test_render_with_wait_waits_for_that_job_in_the_tool(motion, capsys):
    code, out, err = run(ns(wait=True), capsys)
    assert code == 0 and out['job_id'] == 'job-7' and out['status'] == 'ready'
    assert motion == [('POST', '/api/runs/run-1/visuals/motion/render'), ('GET', '/api/runs/run-1/visuals/motion/jobs/job-7'), ('sleep', 3),
                      ('GET', '/api/runs/run-1/visuals/motion/jobs/job-7'), ('sleep', 3), ('GET', '/api/runs/run-1/visuals/motion/jobs/job-7')]
    assert err.strip() == 'The render of D1 is ready (job job-7).'


def test_a_render_that_fails_while_waited_for_says_so(motion, monkeypatch, capsys):
    monkeypatch.setattr(vw, 'call', lambda method, path, wait=None, **kw: {'status': 'failed', 'error': 'the label "Tile" is not in the project'})
    code, out, err = run(ns(wait=True), capsys)
    assert code == 2 and err.strip() == 'The render of D1 failed (job job-7): the label "Tile" is not in the project'


def test_status_of_a_job_waits_only_when_asked(motion, capsys):
    code, out, err = run(ns(what='status', shot=None, job='job-7'), capsys)
    assert code == 0 and out['status'] == 'queued' and motion == [('GET', '/api/runs/run-1/visuals/motion/jobs/job-7')]
    motion.clear()
    code, out, err = run(ns(what='status', shot=None, job='job-7', wait=True), capsys)
    assert out['status'] == 'ready' and [c for c in motion if c[0] == 'sleep'] == [('sleep', 3)]


def test_the_flag_is_on_the_command():
    a = vw.build_parser().parse_args(['motion', 'render', '--shot', 'D1', '--wait'])
    assert a.wait is True and vw.build_parser().parse_args(['motion', 'render', '--shot', 'D1']).wait is False
