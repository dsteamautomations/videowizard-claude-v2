"""vw analysis start and status with the server faked (design/42 6.1, 6.2)."""
import argparse
import json

import pytest

from conftest import PLUGIN, STAGES
import vw


def args(**kw):
    base = {'what': 'status', 'camera_audio': None, 'understand_audio': 'yes', 'film_type': None, 'exclude': None, 'again': False, 'unit': None,
            'note': None, 'show_speaker_video': None, 'waive': None, 'wait': 0}
    return argparse.Namespace(**{**base, **kw})


@pytest.fixture
def harness(monkeypatch):
    monkeypatch.setattr(vw, 'active', lambda: {'code': 'VW-9', 'run_id': 'run-1', 'files': []})
    slept = []
    monkeypatch.setattr(vw.time, 'sleep', lambda s: slept.append(s))
    return slept


def run(a, capsys):
    with pytest.raises(SystemExit) as exc:
        vw.cmd_analysis(a)
    out, err = capsys.readouterr()
    return exc.value.code, json.loads(out), err


def unit(uid, status, elapsed=None, **extra):
    return {'unit': uid, 'status': status, 'recorded': status == 'retained', 'excluded': False, 'cost': ({'elapsed_seconds': elapsed} if elapsed else None), **extra}


def status_answer(units, cap=15):
    counts = {}
    for u in units:
        counts[u['status']] = counts.get(u['status'], 0) + 1
    return {'counts': counts, 'units': units, 'cap': cap}


# ---------- 6.1 wait with an estimate ----------

def test_wait_returns_when_settled_and_says_done(harness, monkeypatch, capsys):
    answers = [status_answer([unit('a', 'running'), unit('b', 'queued')]), status_answer([unit('a', 'retained', 280), unit('b', 'running')]),
               status_answer([unit('a', 'retained', 280), unit('b', 'retained', 300)])]
    monkeypatch.setattr(vw, 'call', lambda method, path, wait=None, **kw: answers.pop(0) if answers else status_answer([unit('a', 'retained', 280), unit('b', 'retained', 300)]))
    code, out, err = run(args(wait=600), capsys)
    assert code == 0 and harness == [15, 15] and '2 retained' in err and 'done' in err


def test_wait_estimates_time_left_from_elapsed_and_cap(harness, monkeypatch, capsys):
    clock = [0.0]
    monkeypatch.setattr(vw.time, 'monotonic', lambda: clock[0])

    def sleep(s):
        harness.append(s)
        clock[0] += s
    monkeypatch.setattr(vw.time, 'sleep', sleep)
    units = [unit(f'r{i}', 'retained', 300) for i in range(12)] + [unit(f'o{i}', 'running') for i in range(5)] + [unit(f'q{i}', 'queued') for i in range(29)]
    monkeypatch.setattr(vw, 'call', lambda method, path, wait=None, **kw: status_answer(units, cap=15))
    code, out, err = run(args(wait=30), capsys)
    assert code == 0 and len(harness) == 2   # 0, 15, 30 → expired
    # 34 open units ÷ cap 15 → 3 rounds × 300 s = 15 min
    assert '12 retained' in err and '5 running' in err and '29 queued' in err and 'about 15 min left' in err and 'run again with --wait' in err


def test_wait_without_cap_uses_fifteen_and_default_elapsed(harness, monkeypatch, capsys):
    units = [unit(f'q{i}', 'queued') for i in range(15)]
    answer = status_answer(units)
    del answer['cap']
    monkeypatch.setattr(vw, 'call', lambda method, path, wait=None, **kw: answer)
    code, out, err = run(args(), capsys)
    assert code == 0 and harness == [] and 'about 5 min left' in err   # ceil(15/15) × 288 s


def test_wait_stops_when_a_clip_needs_a_decision(harness, monkeypatch, capsys):
    monkeypatch.setattr(vw, 'call', lambda method, path, wait=None, **kw: status_answer([unit('a', 'running'), unit('b', 'failed', error='boom')]))
    code, out, err = run(args(wait=600), capsys)
    assert code == 0 and harness == [] and '1 need a decision: b' in err


def test_an_excluded_failure_does_not_need_a_decision(harness, monkeypatch, capsys):
    monkeypatch.setattr(vw, 'call', lambda method, path, wait=None, **kw: status_answer([unit('a', 'retained', 200), {**unit('b', 'failed'), 'excluded': True, 'recorded': True}]))
    code, out, err = run(args(wait=600), capsys)
    assert code == 0 and 'need a decision' not in err and 'done' in err


# ---------- 6.2 start without the two old flags ----------

def test_start_without_flags_posts_nothing_for_camera_audio_and_says_the_source(harness, monkeypatch, capsys):
    posted = {}

    def write(path, body, wait=None):
        posted.update(body)
        return {'created': [{'unit': 'a', 'job_id': 'j'}], 'reused': [], 'excluded': [], 'clips': 1, 'camera_audio': 'allowed', 'camera_audio_source': 'media'}
    monkeypatch.setattr(vw, 'write', write)
    code, out, err = run(args(what='start'), capsys)
    assert code == 0 and 'camera_audio' not in posted and 'film_type' not in posted and posted['understand_audio'] is True and posted['exclude'] == []
    assert 'camera audio: allowed (from the media stage)' in err and '--wait 600' in err


def test_start_with_flags_posts_them(harness, monkeypatch, capsys):
    posted = {}

    def write(path, body, wait=None):
        posted.update(body)
        return {'created': [], 'reused': ['a'], 'excluded': [], 'clips': 1, 'camera_audio': 'excluded', 'camera_audio_source': 'flag'}
    monkeypatch.setattr(vw, 'write', write)
    code, out, err = run(args(what='start', camera_audio='excluded', understand_audio='no', exclude=['x.mp4'], film_type='doc'), capsys)
    assert code == 0 and posted['camera_audio'] == 'excluded' and posted['understand_audio'] is False and posted['exclude'] == ['x.mp4'] and posted['film_type'] == 'doc'
    assert 'camera audio: excluded (as given)' in err


def test_steps_and_command_text_carry_the_wait_and_the_two_questions():
    steps = ' '.join(STAGES['analysis']['steps'])
    assert '--wait 600' in steps and 'default yes' in steps and 'default none' in steps and 'every minute' not in steps and 'media stage' in steps
    md = (PLUGIN / 'commands' / 'vw.md').read_text(encoding='utf-8')
    assert '--wait 600' in md and 'every minute' not in md and '--film-type' not in md
