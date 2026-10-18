"""vw options status --wait, the package reading copy and vw master rule --quote, with the server faked (design/43 7.2, 7.4, 7.5)."""
import argparse
import json

import pytest

from conftest import PLUGIN, STAGES
import vw


def args(**kw):
    base = {'what': 'status', 'file': None, 'sub': None, 'edge': None, 'option': None, 'unit': None, 'quote': None, 'wait': 0, 'film': None,
            'slide': None, 'action': None, 'note': None, 'edit': None, 'add': None}
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


def run(fn, a, capsys):
    with pytest.raises(SystemExit) as exc:
        fn(a)
    out, err = capsys.readouterr()
    return exc.value.code, json.loads(out), err


def status_answer(status, frames=12642, rate=40, error=None, film='review'):
    return {'state': 'prepared', 'renders': {film: {'status': status, 'frames': frames, 'error': error, 'job_id': 'j'}}, **({'render_rate_fps': rate} if rate else {})}


# ---------- 7.2 wait for the review film ----------

def test_wait_returns_when_the_film_is_ready(harness, monkeypatch, capsys):
    answers = [status_answer('queued'), status_answer('running'), status_answer('ready')]
    monkeypatch.setattr(vw, 'call', lambda method, path, wait=None, **kw: answers.pop(0) if answers else status_answer('ready'))
    code, out, err = run(vw.cmd_options, args(wait=900), capsys)
    assert code == 0 and harness == [15, 15] and 'ready' in err and 'vw options fetch' in err


def test_wait_stops_at_once_on_a_failed_render(harness, monkeypatch, capsys):
    monkeypatch.setattr(vw, 'call', lambda method, path, wait=None, **kw: status_answer('failed', error='ffmpeg failed: boom'))
    code, out, err = run(vw.cmd_options, args(wait=900), capsys)
    assert code == 0 and harness == [] and 'failed' in err and 'boom' in err


def test_wait_expiry_estimates_from_frames_and_the_measured_rate(harness, monkeypatch, capsys):
    monkeypatch.setattr(vw, 'call', lambda method, path, wait=None, **kw: status_answer('running', frames=12642, rate=40))
    code, out, err = run(vw.cmd_options, args(wait=60), capsys)
    # polls at 0, 15, 30, 45, 60 → expired; 12642 / 40 = 316 s, 60 s waited → about 4 min
    assert code == 0 and len(harness) == 4 and 'about 4 min left' in err and 'run again with --wait' in err


def test_no_wait_polls_once_and_uses_twenty_fps_without_a_rate(harness, monkeypatch, capsys):
    monkeypatch.setattr(vw, 'call', lambda method, path, wait=None, **kw: status_answer('running', frames=12642, rate=None))
    code, out, err = run(vw.cmd_options, args(), capsys)
    assert code == 0 and harness == [] and 'about 11 min left' in err and 'run again' not in err   # 12642 / 20 = 632 s


def test_status_without_a_render_says_so(harness, monkeypatch, capsys):
    monkeypatch.setattr(vw, 'call', lambda method, path, wait=None, **kw: {'state': 'prepared', 'renders': {}})
    code, out, err = run(vw.cmd_options, args(wait=900), capsys)
    assert code == 0 and harness == [] and 'no review film' in err


def test_wait_can_follow_the_master_film(harness, monkeypatch, capsys):
    answers = [status_answer('running', film='master'), status_answer('ready', film='master')]
    monkeypatch.setattr(vw, 'call', lambda method, path, wait=None, **kw: answers.pop(0) if answers else status_answer('ready', film='master'))
    code, out, err = run(vw.cmd_options, args(wait=900, film='master'), capsys)
    assert code == 0 and harness == [15] and 'master film ready' in err


# ---------- 7.4 the reading copy ----------

def package():
    return {'contract': 'vw2-options-package-v1', 'prompt': 'p' * 3000, 'entities': [{'name': 'Mason', 'kind': 'person'}],
            'cards': [{'clip_id': 'c1', 'lines': ['l1', 'l2']}],
            'sub_clips': [{'sub_clip_id': 'c1:SUB_01', 'grade': 'A', 'sfx_cues': [{'sfx_type': 'trowel'}], 'editorial_ideas': ['B-roll for beat 22'], 'landmarks': ['wall']},
                          {'sub_clip_id': 'c1:SUB_02', 'grade': 'B', 'sfx_cues': [], 'editorial_ideas': [], 'landmarks': []}],
            'narration': {'words': [{'id': 'W1', 'text': 'As', 'start_frame': 0}, {'id': 'W2', 'text': 'the', 'start_frame': 5}],
                          'sentences': [{'first_word_id': 'W1', 'last_word_id': 'W2', 'text': 'As the'}], 'pieces': [{'source_start_frame': 0}]},
            'beats': [{'beat_id': 'BEAT_01', 'title': 'As the demand…'}]}


def rows_on_one_line(text, marker):
    lines = [l for l in text.split('\n') if marker in l]
    return lines, all(json.loads(l.strip().rstrip(',')) for l in lines)


def test_reading_copy_drops_the_three_and_writes_tables_one_row_per_line(tmp_path):
    data = package()
    path = tmp_path / 'work' / 'options-package.json'
    vw.reading_copy(path, data)
    text = path.read_text(encoding='utf-8')
    got = json.loads(text)
    assert 'entities' not in got and all('sfx_cues' not in r and 'editorial_ideas' not in r for r in got['sub_clips'])
    assert got['sub_clips'][0]['landmarks'] == ['wall'] and got['cards'] == data['cards'] and got['narration']['pieces'] == data['narration']['pieces']
    subs, ok = rows_on_one_line(text, '"sub_clip_id"')
    assert len(subs) == 2 and ok
    words, ok = rows_on_one_line(text, '"start_frame"')
    assert len(words) == 2 and ok
    sentences, ok = rows_on_one_line(text, '"first_word_id"')
    assert len(sentences) == 1 and ok
    assert 'read options-package.prompt.md' in got['prompt'] and (tmp_path / 'work' / 'options-package.prompt.md').read_text(encoding='utf-8').startswith('ppp')
    # the data given is not changed: the server's package keeps everything
    assert 'entities' in data and data['sub_clips'][0]['sfx_cues'] == [{'sfx_type': 'trowel'}]


def test_download_uses_the_reading_copy_for_the_options_package_only(tmp_path, monkeypatch):
    monkeypatch.setattr(vw, 'RUNS', tmp_path / 'runs')
    (tmp_path / 'runs' / 'VW-9').mkdir(parents=True)
    body = json.dumps(package()).encode('utf-8')

    class Resp:
        status_code = 200
        content = body

    class Client:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def get(self, path, follow_redirects=True):
            return Resp()
    monkeypatch.setattr(vw, 'api', lambda: Client())
    m = {'code': 'VW-9', 'run_id': 'run-1'}
    p = vw._download(m, 'k', 'work/options-package.json')
    assert 'entities' not in json.loads(open(p, encoding='utf-8').read())
    q = vw._download(m, 'k', 'work/visuals-package.json')
    assert 'entities' in json.loads(open(q, encoding='utf-8').read())


# ---------- 7.5 a rule needs the operator's confirmation ----------

def test_master_rule_without_a_quote_is_refused(harness, capsys):
    code, out, err = run(vw.cmd_master, args(what='rule', add='no alternate takes for this client'), capsys)
    assert code == 2 and 'quote' in out['message']


def test_master_rule_posts_the_rule_and_the_quote(harness, monkeypatch, capsys):
    posted = {}

    def write(path, body, wait=None):
        posted.update(body)
        return {'rules': 1}
    monkeypatch.setattr(vw, 'write', write)
    code, out, err = run(vw.cmd_master, args(what='rule', add='no alternate takes for this client', quote='yes, keep that'), capsys)
    assert code == 0 and posted == {'rule': 'no alternate takes for this client', 'quote': 'yes, keep that'}


# ---------- the steps and the command text ----------

def test_steps_and_command_text_carry_the_new_wording():
    steps = STAGES['options']['steps']
    assert 'always' in steps[1] and 'chapter' in steps[1] and 'refused until the scenes are approved' in steps[1]
    assert 'grouped by rule' in steps[3] and 'R5' in steps[3] and 'R10' in steps[3]
    assert '--wait 900' in steps[4]
    assert 'R5, B1, B2, rule 11 and E1' in STAGES['options']['prompt']
    master = ' '.join(STAGES['master']['steps'])
    assert 'vw master rule --add' in master and '--quote' in master and 'stay with this run' in master
    md = (PLUGIN / 'commands' / 'vw.md').read_text(encoding='utf-8')
    assert 'vw options status --wait 900' in md and 'vw master rule --add' in md and 'always' in md
