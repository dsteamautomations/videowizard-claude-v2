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
    files = vw.download_options_package(m, 'k')   # design/61: one file per section under work/options/
    folder = tmp_path / 'runs' / 'VW-9' / 'work' / 'options'
    assert {f['file'] for f in files} >= {'work/options/beats.json', 'work/options/pieces-BEAT_01.json', 'work/options/pieces-other.json', 'work/options/prompt.md'}
    assert not (folder.parent / 'options-package.json').exists() and 'entities' not in (folder / 'rest.json').read_text(encoding='utf-8')
    q = vw._download(m, 'k', 'work/visuals-package.json')
    assert 'entities' in json.loads(open(q, encoding='utf-8').read())


def test_options_reading_files_write_one_file_per_section(tmp_path):
    """design/61 L17: no offsets to guess, no read refused; design/125 P3: the pieces by scene with only the details a choice needs (test_design125_stage7)."""
    data = package()
    data['sub_clips'] = [{'sub_clip_id': f'c1:SUB_{i:02d}', 'grade': 'A', 'landmarks': ['wall'], 'handles': {'in': 5, 'out': 5}, 'sfx_cues': [1], 'editorial_ideas': ['x'],
                          'ui_path': 'Inspector > …', 'crop_rect': [0, 0, 1, 1], 'position': [0, 0], 'zoom': 1.0, 'source_width': 1920, 'source_height': 1080, 'source_fps': 50.0,
                          'horizon_rotation_deg': 0, 'stabilization_needed': False, 'log_sub_clip_id': 'SUB_01', 'fit_source': 'scene', 'risk_flags_waived': []} for i in range(30)]
    data.update({'coverage': [{'beat_id': 'BEAT_01'}], 'shapes': {'options': {}}, 'landmarks': ['wall'], 'policy': {}, 'project': {}, 'timeline': {'fps': 25}, 'learned_rules': []})
    ws = tmp_path / 'VW-9'
    (ws / 'work' / 'options').mkdir(parents=True)
    (ws / 'work' / 'options' / 'sub-clips-9.json').write_text('stale', encoding='utf-8')
    files = vw.options_reading_files(ws, data)
    folder = ws / 'work' / 'options'
    names = sorted(p.name for p in folder.iterdir())
    assert names == ['beats.json', 'coverage.json', 'narration.json', 'pieces-BEAT_01.json', 'pieces-other.json', 'prompt.md', 'rest.json', 'shapes.json', 'words-1.json']
    rows, ok = rows_on_one_line((folder / 'pieces-other.json').read_text(encoding='utf-8'), '"sub_clip_id"')
    assert len(rows) == 30 and ok   # no scene names them: listed once, at the end
    row = json.loads(rows[0].strip().rstrip(','))
    assert row == {'sub_clip_id': 'c1:SUB_00', 'grade': 'A'}
    narration = (folder / 'narration.json').read_text(encoding='utf-8')
    assert 'words' not in json.loads(narration) and len(rows_on_one_line(narration, '"first_word_id"')[0]) == 1 and json.loads(narration)['pieces'] == data['narration']['pieces']
    assert len(rows_on_one_line((folder / 'words-1.json').read_text(encoding='utf-8'), '"start_frame"')[0]) == 2
    assert (folder / 'prompt.md').read_text(encoding='utf-8').startswith('ppp') and 'entities' not in (folder / 'rest.json').read_text(encoding='utf-8')
    assert json.loads((folder / 'beats.json').read_text(encoding='utf-8')) == data['beats'] and json.loads((folder / 'shapes.json').read_text(encoding='utf-8')) == data['shapes']
    by = {f['file']: f for f in files}
    assert by['work/options/pieces-other.json']['rows'] == 30 and by['work/options/pieces-BEAT_01.json']['rows'] == 0 and by['work/options/words-1.json']['rows'] == 2
    assert by['work/options/beats.json']['for'] == 'scenes' and by['work/options/pieces-BEAT_01.json']['for'] == 'placements' and by['work/options/prompt.md']['for'] == 'read first'
    assert 'entities' in data and data['sub_clips'][0]['sfx_cues'] == [1]   # the data given is not changed


def test_rows_files_split_by_count_and_by_size(tmp_path):
    """design/61: a table file is never over the byte budget (the reader refuses ~25k tokens) and never over the row cap."""
    small = [{'id': i} for i in range(30)]
    assert vw.rows_files(tmp_path, 't', small, cap=25) == [('t-1.json', 25), ('t-2.json', 5)]
    big = [{'id': i, 'pad': 'x' * 1000} for i in range(10)]
    parts = vw.rows_files(tmp_path, 'b', big, budget=3500)   # three rows fit a file
    assert [n for _, n in parts] == [3, 3, 3, 1] and all((tmp_path / name).stat().st_size < 3600 for name, _ in parts)
    assert vw.rows_files(tmp_path, 'e', []) == [('e-1.json', 0)] and (tmp_path / 'e-1.json').read_text(encoding='utf-8') == '[\n\n]\n'


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
    assert 'work/options/' in steps[0] and 'never by line offsets' in steps[0] and 'sub-clips-' in steps[0]   # design/61 L17
    assert 'beats.json' in steps[1] and 'narration.json' in steps[1] and 'shapes.json' in steps[1] and 'coverage.json' in steps[3] and 'sub-clips' in steps[3]
    assert 'always' in steps[1] and 'chapter' in steps[1] and 'refused until the scenes are approved' in steps[1]
    assert 'grouped by rule' in steps[3] and 'R5' in steps[3] and 'R10' in steps[3]
    assert '--wait 900' in steps[4]
    assert 'R5, B1, B2, rule 11 and E1' in STAGES['options']['prompt']
    master = ' '.join(STAGES['master']['steps'])
    assert 'vw master rule --add' in master and '--quote' in master and 'stay with this run' in master
    md = (PLUGIN / 'commands' / 'vw.md').read_text(encoding='utf-8')
    assert 'vw options status --wait 900' in md and 'vw master rule --add' in md and 'always' in md
