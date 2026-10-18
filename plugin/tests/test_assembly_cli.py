"""vw assembly choose --file, frame notes by time, status --wait, the record and fetch lines (design/46); the texts."""
import argparse
import json

import pytest

from conftest import PLUGIN, STAGES
import vw


def args(**kw):
    base = {'what': 'status', 'shot': None, 'offset': None, 'end': None, 'sub': None, 'choice': None, 'decision': None, 'notes': None, 'quote': None,
            'accept_as_is': False, 'frame_note': None, 'file': None, 'wait': 0}
    return argparse.Namespace(**{**base, **kw})


@pytest.fixture
def harness(monkeypatch, tmp_path):
    monkeypatch.setattr(vw, 'active', lambda: {'code': 'VW-9', 'run_id': 'run-1', 'files': []})
    monkeypatch.setattr(vw, 'RUNS', tmp_path / 'runs')
    (tmp_path / 'runs' / 'VW-9' / 'out').mkdir(parents=True)
    clock = [0.0]
    slept = []

    def sleep(s):
        slept.append(s)
        clock[0] += s
    monkeypatch.setattr(vw.time, 'sleep', sleep)
    monkeypatch.setattr(vw.time, 'monotonic', lambda: clock[0])
    return tmp_path / 'runs' / 'VW-9', slept


def run(a, capsys):
    with pytest.raises(SystemExit) as exc:
        vw.cmd_assembly(a)
    out, err = capsys.readouterr()
    return exc.value.code, json.loads(out), err


# ---------- 11.3 choose --file, frame notes by time ----------

def test_choose_file_sends_in_order_and_stops_at_the_first_refusal(harness, monkeypatch, capsys):
    ws, _ = harness
    (ws / 'out' / 'fills.json').write_text(json.dumps([{'shot': 'VS1', 'offset': 12, 'end': 'trim'}, {'shot': 'VS9', 'end': 'hold_last'}, {'shot': 'VS2', 'accept_as_is': True}]), encoding='utf-8')
    sent = []

    def request(method, path, wait=None, **kw):
        body = kw['json']
        sent.append(body['shot_id'])
        if body['shot_id'] == 'VS9':
            return {'action': 'refused', 'message': 'No gap fill VS9.'}, 2
        return {**body}, 0
    monkeypatch.setattr(vw, 'request', request)
    code, out, err = run(args(what='choose', file='out/fills.json'), capsys)
    assert code == 2 and sent == ['VS1', 'VS9'] and out['recorded'] == ['VS1'] and out['refused']['shot'] == 'VS9' and out['remaining'] == ['VS2']
    (ws / 'out' / 'fills.json').write_text(json.dumps([{'shot': 'VS2', 'accept_as_is': True}]), encoding='utf-8')
    bodies = []
    monkeypatch.setattr(vw, 'request', lambda m, p, wait=None, **kw: (bodies.append(kw['json']) or (kw['json'], 0)))
    code, out, err = run(args(what='choose', file='out/fills.json'), capsys)
    assert code == 0 and out['recorded'] == ['VS2'] and bodies[0]['offset_frames'] == 0 and bodies[0]['end_policy'] == 'trim' and bodies[0]['accept_as_is'] is True


def test_frame_notes_take_a_time_or_a_frame():
    assert vw.frame_note('0:40:too short') == {'frame': 1000, 'note': 'too short'}
    assert vw.frame_note('1:02.5:late') == {'frame': 1563, 'note': 'late'}        # 62.5 s × 25
    assert vw.frame_note('1000:too short') == {'frame': 1000, 'note': 'too short'}
    assert vw.frame_note('12:a:b') == {'frame': 12, 'note': 'a:b'}


def test_review_posts_time_notes_as_frames(harness, monkeypatch, capsys):
    posted = {}
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: (posted.update(body) or {'decision': 'changes', 'next': 'x'}))
    code, out, err = run(args(what='review', decision='changes', notes='hold the wall', frame_note=['0:40:too short'], quote='change it'), capsys)
    assert code == 0 and posted['frame_notes'] == [{'frame': 1000, 'note': 'too short'}]


# ---------- 11.4 status --wait on the stage 3 path ----------

def status_answer(status, frames=7604, rate=40, error=None):
    return {'renders': {'assembly': {'status': status, 'frames': frames, 'error': error}}, 'render_rate_fps': rate}


def test_status_wait_follows_the_assembly_film(harness, monkeypatch, capsys):
    _, slept = harness
    paths = []
    answers = [status_answer('running'), status_answer('ready')]
    monkeypatch.setattr(vw, 'call', lambda method, path, wait=None, **kw: (paths.append(path) or (answers.pop(0) if answers else status_answer('ready'))))
    code, out, err = run(args(what='status', wait=900), capsys)
    assert code == 0 and slept == [15] and 'assembly film ready' in err and 'vw assembly fetch' in err and all(p.endswith('/stage3') for p in paths)


def test_status_wait_expiry_estimates(harness, monkeypatch, capsys):
    monkeypatch.setattr(vw, 'call', lambda method, path, wait=None, **kw: status_answer('running', frames=7604, rate=40))
    code, out, err = run(args(what='status', wait=30), capsys)
    assert code == 0 and 'assembly film rendering, about 3 min left' in err and 'run again with --wait' in err


# ---------- 11.5, 11.6 the record and fetch lines ----------

def test_record_says_the_review_is_included(harness, monkeypatch, capsys):
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: {'output': 'o1', 'version': 1, 'next': '`vw delivery bundle`'})
    code, out, err = run(args(what='record', quote='yes, watched and listened'), capsys)
    assert code == 0 and 'watched and listened' in err and 'vw delivery bundle' in err


def test_fetch_prints_the_loudness_against_the_targets(harness, monkeypatch, capsys):
    record = {'loudness_check': {'integrated_lufs': -15.8, 'true_peak_dbfs': -3.1, 'peak_ceiling_dbtp': -3, 'peak_inside': True, 'integrated_target_lufs': -16, 'integrated_inside': True}}
    monkeypatch.setattr(vw, 'call', lambda method, path, wait=None, **kw: {'renders': {'assembly': {'status': 'ready', 'result': {'key': 'k', 'sha256': 'x', 'duration_s': 304.2, 'bytes': 1, 'record': record}}}})
    monkeypatch.setattr(vw, '_download', lambda m, key, rel: '/tmp/x/' + rel)
    code, out, err = run(args(what='fetch'), capsys)
    assert code == 0 and 'mix -15.8 LUFS (target -16), peak -3.1 dBTP (ceiling -3): inside' in err
    record['loudness_check'].update(true_peak_dbfs=-1.0, peak_inside=False)
    code, out, err = run(args(what='fetch'), capsys)
    assert 'outside: peak' in err


# ---------- the steps and the command text ----------

def test_steps_and_command_text_carry_the_new_flow():
    steps = STAGES['assembly']['steps']
    assert 'one line' in steps[0] and 'ask once' in steps[1] and '--file' in steps[1] and 'defaults need no command' in steps[1]
    assert 'status --wait 900' in steps[2] and '-3 dBTP' in steps[2] and 'loudness' in steps[2]
    assert 'records the review and the output together' in steps[3] and 'mm:ss' in steps[3]
    md = (PLUGIN / 'commands' / 'vw.md').read_text(encoding='utf-8')
    assert 'vw assembly status --wait 900' in md and 'ask once' in md and 'records the review and the output together' in md
