"""vw master slides, decide --file, status --wait and record, with the server faked (design/44 8.1, 8.2, 8.4); the steps' wording."""
import argparse
import json

import pytest

from conftest import PLUGIN, STAGES
import vw


def args(**kw):
    base = {'what': 'status', 'file': None, 'slide': None, 'option': None, 'action': None, 'note': None, 'edit': None, 'add': None, 'quote': None, 'wait': 0}
    return argparse.Namespace(**{**base, **kw})


@pytest.fixture
def harness(monkeypatch):
    monkeypatch.setattr(vw, 'active', lambda: {'code': 'VW-9', 'run_id': 'run-1', 'files': []})
    clock = [0.0]
    slept = []

    def sleep(s):
        slept.append(s)
        clock[0] += s
    monkeypatch.setattr(vw.time, 'sleep', sleep)
    monkeypatch.setattr(vw.time, 'monotonic', lambda: clock[0])
    return slept


def run(a, capsys):
    with pytest.raises(SystemExit) as exc:
        vw.cmd_master(a)
    out, err = capsys.readouterr()
    return exc.value.code, json.loads(out), err


# ---------- 8.1 labels, a file of answers, the slides view ----------

def test_slide_labels_are_normalised():
    assert vw.slide_label('#2b') == '2B' and vw.slide_label(' 3 ') == '3' and vw.slide_label(7) == '7'


def test_decide_by_slide_posts_the_label(harness, monkeypatch, capsys):
    posted = {}

    def write(path, body, wait=None):
        posted.update(body)
        return {'slide': '2B', 'type': 'decision', 'action': 'DROP', 'decided': 1, 'of': 3}
    monkeypatch.setattr(vw, 'write', write)
    code, out, err = run(args(what='decide', slide='#2b', action='DROP'), capsys)
    assert code == 0 and posted['slide'] == '2B' and posted['action'] == 'DROP'


def test_decide_file_sends_in_order_and_stops_at_the_first_refusal(harness, monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(vw, 'RUNS', tmp_path / 'runs')
    ws = tmp_path / 'runs' / 'VW-9' / 'out'
    ws.mkdir(parents=True)
    (ws / 'decisions.json').write_text(json.dumps([{'slide': '2', 'action': 'KEEP'}, {'slide': '3', 'action': 'REJECT'}, {'slide': '1b', 'action': 'DROP'}]), encoding='utf-8')
    sent = []

    def request(method, path, wait=None, **kw):
        body = kw['json']
        sent.append(body['slide'])
        if body['slide'] == '3' and not body.get('note'):
            return {'action': 'refused', 'message': "REJECT needs the operator's reason (--note); it stays with this run's decisions."}, 2
        return {'slide': body['slide'], 'action': body['action'], 'decided': len(sent), 'of': 3}, 0
    monkeypatch.setattr(vw, 'request', request)
    code, out, err = run(args(what='decide', file='out/decisions.json'), capsys)
    assert code == 2 and sent == ['2', '3'] and out['recorded'] == ['2'] and out['refused']['slide'] == '3' and 'reason' in out['refused']['message'] and out['remaining'] == ['1B']
    (ws / 'decisions.json').write_text(json.dumps([{'slide': '3', 'action': 'REJECT', 'note': 'the wide reads better'}, {'slide': '1B', 'action': 'DROP'}]), encoding='utf-8')
    sent.clear()
    code, out, err = run(args(what='decide', file='out/decisions.json'), capsys)
    assert code == 0 and sent == ['3', '1B'] and out['recorded'] == ['3', '1B'] and out['decided'] == 2 and out['of'] == 3


def test_decide_needs_a_slide_or_a_file(harness, capsys):
    code, out, err = run(args(what='decide', action='KEEP'), capsys)
    assert code == 2 and '--file' in out['message'] and '--slide' in out['message']


def test_slides_view_says_what_is_waiting(harness, monkeypatch, capsys):
    monkeypatch.setattr(vw, 'call', lambda method, path, wait=None, **kw: {'slides': [{'slide': '1', 'type': 'option', 'needs_answer': True, 'answer': {'action': 'KEEP'}},
                                                                                      {'slide': '1A', 'type': 'blank', 'needs_answer': False, 'answer': None},
                                                                                      {'slide': '1B', 'type': 'decision', 'needs_answer': True, 'answer': None},
                                                                                      {'slide': '2', 'type': 'backup', 'needs_answer': True, 'answer': None}],
                                                                           'answered': 1, 'of': 3, 'waiting': ['1B', '2']})
    code, out, err = run(args(what='slides'), capsys)
    assert code == 0 and '1 of 3 answered' in err and 'waiting: 1B, 2' in err


# ---------- 8.2 wait for the master film ----------

def status_answer(status, frames=7604, rate=40, error=None):
    return {'state': 'prepared', 'renders': {'master': {'status': status, 'frames': frames, 'error': error}}, 'render_rate_fps': rate}


def test_master_status_wait_follows_the_master_film(harness, monkeypatch, capsys):
    answers = [status_answer('running'), status_answer('ready')]
    monkeypatch.setattr(vw, 'call', lambda method, path, wait=None, **kw: answers.pop(0) if answers else status_answer('ready'))
    code, out, err = run(args(what='status', wait=600), capsys)
    assert code == 0 and harness == [15] and 'master film ready' in err and 'vw master fetch' in err


def test_master_status_expiry_estimates(harness, monkeypatch, capsys):
    monkeypatch.setattr(vw, 'call', lambda method, path, wait=None, **kw: status_answer('running', frames=7604, rate=40))
    code, out, err = run(args(what='status', wait=30), capsys)
    assert code == 0 and 'master film rendering, about 3 min left' in err and 'run again with --wait' in err   # 7604 / 40 = 190 s − 30 s


# ---------- 8.4 one approval ----------

def test_record_says_both_are_recorded(harness, monkeypatch, capsys):
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: {'output': 'o1', 'first_cut_output': 'o2', 'version': 1, 'gaps': ['BEAT_02'], 'next': 'visuals for each gap'})
    code, out, err = run(args(what='record', quote='watched and listened, yes'), capsys)
    assert code == 0 and 'Master and first cut recorded' in err and 'visuals for each gap' in err


# ---------- the steps and the command text ----------

def test_slides_prints_the_review_page_link(harness, monkeypatch, capsys):
    """design/62: the page is the default place to decide; the slides line names it."""
    monkeypatch.setattr(vw, 'server_url', lambda: 'https://x.example')
    monkeypatch.setattr(vw, 'call', lambda method, path, wait=None, **kw: {'slides': [{'slide': '1', 'type': 'option', 'needs_answer': True, 'answer': None}], 'answered': 0, 'of': 1, 'waiting': ['1']})
    code, out, err = run(args(what='slides'), capsys)
    assert code == 0 and out['review_page_url'] == 'https://x.example/runs/VW-9/review' and 'Review page: https://x.example/runs/VW-9/review' in err
    monkeypatch.setattr(vw, 'call', lambda method, path, wait=None, **kw: {'slides': [], 'answered': 2, 'of': 2, 'waiting': [], 'both_kept': [{'scene': 'Scene 2: Mixing', 'slides': ['1', '2']}]})
    code, out, err = run(args(what='slides'), capsys)
    assert code == 0 and 'Both cuts kept: Scene 2: Mixing (#1, #2): reject one' in err   # design/63


def test_next_carries_the_review_page_link_at_the_options_and_master_stages(harness, monkeypatch, capsys):
    monkeypatch.setattr(vw, 'server_url', lambda: 'https://x.example')
    monkeypatch.setattr(vw, 'ensure_mine', lambda nxt, take_over, run_id: None)
    for stage in ('options', 'master'):
        monkeypatch.setattr(vw, 'call', lambda method, path, **kw: {'stage': stage, 'paid': None})
        with pytest.raises(SystemExit) as exc:
            vw.cmd_next(argparse.Namespace(take_over=False))
        out, err = capsys.readouterr()
        assert exc.value.code == 0 and json.loads(out)['review_page_url'] == 'https://x.example/runs/VW-9/review' and 'Review page: https://x.example/runs/VW-9/review' in err
    monkeypatch.setattr(vw, 'call', lambda method, path, **kw: {'stage': 'media'})
    with pytest.raises(SystemExit):
        vw.cmd_next(argparse.Namespace(take_over=False))
    assert 'review_page_url' not in json.loads(capsys.readouterr()[0])
    monkeypatch.setattr(vw, 'call', lambda method, path, **kw: {'stage': 'visuals', 'paid': 'openai'})   # design/65: the visuals page
    with pytest.raises(SystemExit):
        vw.cmd_next(argparse.Namespace(take_over=False))
    out, err = capsys.readouterr()
    assert json.loads(out)['visuals_page_url'] == 'https://x.example/runs/VW-9/visuals' and 'Visuals page: https://x.example/runs/VW-9/visuals' in err


def test_review_fetch_names_the_page(harness, monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(vw, 'server_url', lambda: 'https://x.example')
    monkeypatch.setattr(vw, 'call', lambda method, path, wait=None, **kw: {'renders': {'review': {'status': 'ready', 'result': {'key': 'k', 'sha256': 's', 'duration_s': 7.0}}}})
    monkeypatch.setattr(vw, '_download', lambda m, key, rel: str(tmp_path / rel))
    with pytest.raises(SystemExit) as exc:
        vw._s2_fetch({'code': 'VW-9', 'run_id': 'run-1'}, 'review', 'out/review.mp4')
    out, err = capsys.readouterr()
    assert exc.value.code == 0 and json.loads(out)['review_page_url'] == 'https://x.example/runs/VW-9/review' and 'Review page' in err and 'the default' in err
    with pytest.raises(SystemExit):
        vw._s2_fetch({'code': 'VW-9', 'run_id': 'run-1'}, 'master', 'out/master.mp4')
    out, err = capsys.readouterr()
    assert 'review_page_url' not in json.loads(out)


def test_steps_and_command_text_carry_the_labels_and_the_one_approval():
    master = STAGES['master']['steps']
    assert 'vw master slides' in master[0] and '--file out/decisions.json' in master[0] and '2B' in master[0] and 'between 2 and 3' in master[0] and '1/25 s' in master[0]
    assert 'question tool' in master[0] and 'one slide per question' in master[0] and 'at most four questions' in master[0] and 'as buttons' in master[0] and 'Never ask for labels typed' in master[0]   # design/62 A
    assert 'review page' in master[0] and 'default place to decide' in master[0] and 'review page' in STAGES['options']['steps'][4] and 'approve' in STAGES['options']['steps'][4]   # design/62 B
    assert vw.review_page_url('VW-9').endswith('/runs/VW-9/review')
    assert 'review page' in (PLUGIN / 'commands' / 'vw.md').read_text(encoding='utf-8').lower()
    assert '--wait 600' in master[1] and 'say every swap' in master[1] and 'watch' in master[1] and 'listen' in master[1] and 'records the master and the first cut together' in master[1]
    assert 'design/44' in STAGES['first_cut']['steps'][0]
    assert '#2A' in STAGES['options']['prompt'] and 'running numbers' in STAGES['options']['prompt']
    md = (PLUGIN / 'commands' / 'vw.md').read_text(encoding='utf-8')
    assert '--file out/decisions.json' in md and 'vw master status --wait 600' in md and '2B' in md and 'first cut together' in md
