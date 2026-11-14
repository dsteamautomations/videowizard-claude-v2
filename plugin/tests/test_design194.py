"""design/194 on the plugin: `vw drawing` (a thing's drawing set), `vw guide drawing` and its two answers, a still's look reference,
the drawing skill and its helper, and what the guard lets through. Nothing here reaches a server."""
import argparse
import base64
import json

import pytest

from conftest import PLUGIN, run_hook
from test_visuals_cli import harness  # noqa: F401  (the fixture rides along)
import vw

SET = {'unit': 'mm', 'level': 'form', 'pieces': []}


def drawing(**kw):
    return argparse.Namespace(**{**{'what': 'set', 'element': None, 'file': None, 'sha': None, 'quote': None, 'notes': None}, **kw})


def guide(**kw):
    base = {'what': 'status', 'shot': None, 'file': None, 'override': None, 'still': None, 'sha': None, 'quote': None, 'notes': None, 'region': None, 'prompt': None, 'again': False, 'cause': None, 'fix': None}
    return argparse.Namespace(**{**base, **kw})


def run(fn, a, capsys):
    with pytest.raises(SystemExit) as exc:
        fn(a)
    out, err = capsys.readouterr()
    return exc.value.code, json.loads(out), err


@pytest.fixture
def sent(monkeypatch):
    calls = []
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: calls.append((path, body)) or {'sha256': 'a' * 64, 'status': 'proposed', 'next': 'the next step'})
    return calls


# ---------- a thing's drawing set ----------

def test_every_drawing_command_needs_its_thing(harness, capsys):
    for what in ('set', 'show', 'approve', 'reject'):
        code, out, _ = run(vw.cmd_drawing, drawing(what=what), capsys)
        assert code == 2 and f'vw drawing {what} --element E' in out['message'], what


def test_the_drawing_set_is_sent_as_data(harness, sent, capsys):
    ws, _ = harness
    (ws / 'work' / 'drawing' / 'E1').mkdir(parents=True)
    (ws / 'work' / 'drawing' / 'E1' / 'set.json').write_text(json.dumps(SET), encoding='utf-8')
    code, out, err = run(vw.cmd_drawing, drawing(what='set', element='E1', file='work/drawing/E1/set.json'), capsys)
    assert code == 0 and sent == [('/api/runs/run-1/visuals/drawing/set', {'element_id': 'E1', 'drawing': SET})] and 'the next step' in err


def test_a_missing_or_broken_drawing_file_is_refused_before_anything_is_sent(harness, sent, capsys):
    ws, _ = harness
    assert run(vw.cmd_drawing, drawing(what='set', element='E1'), capsys)[0] == 2
    (ws / 'work' / 'broken.json').write_text('{not json', encoding='utf-8')
    assert 'not valid JSON' in run(vw.cmd_drawing, drawing(what='set', element='E1', file='work/broken.json'), capsys)[1]['message']
    assert sent == []


def test_show_saves_the_labelled_sheets_and_says_what_is_assumed(harness, monkeypatch, capsys):
    ws, _ = harness
    asked = []

    def call(method, path, wait=None, **kw):
        asked.append(path)
        if path.endswith('/drawing/E1'):
            return {'element_id': 'E1', 'status': 'proposed', 'sha256': 'b' * 64, 'assumed': ['slope of a tail: 1 in 7'], 'views': [{'id': 'a', 'name': 'Face', 'kind': 'square on'}, {'id': 'd', 'name': 'Angled', 'kind': 'three-quarter'}]}
        name = path.rsplit('/', 1)[1]
        return {'name': name, 'file': name + '.png', 'mime': 'image/png', 'base64': base64.b64encode(b'png-' + name.encode()).decode()}
    monkeypatch.setattr(vw, 'call', call)
    code, out, err = run(vw.cmd_drawing, drawing(what='show', element='E1'), capsys)
    assert code == 0 and (ws / 'work' / 'drawing' / 'E1' / 'a.png').read_bytes() == b'png-a' and (ws / 'work' / 'drawing' / 'E1' / 'd.png').exists()
    assert len(out['files']) == 2 and 'slope of a tail: 1 in 7' in err and 'proposed' in err
    assert not any(p.endswith('-plain') for p in asked)          # the operator is shown the labelled sheets, never the picture AI's copies


def test_the_operators_answer_goes_with_the_exact_content_and_their_words(harness, sent, capsys):
    assert run(vw.cmd_drawing, drawing(what='approve', element='E1', quote='yes'), capsys)[0] == 2          # no sha
    assert run(vw.cmd_drawing, drawing(what='reject', element='E1', sha='b' * 64, quote='no'), capsys)[0] == 2   # no reason
    assert sent == []
    run(vw.cmd_drawing, drawing(what='approve', element='E1', sha='b' * 64, quote='yes, that is it'), capsys)
    run(vw.cmd_drawing, drawing(what='reject', element='E1', sha='b' * 64, quote='no', notes='the tails are too wide'), capsys)
    assert sent == [('/api/runs/run-1/visuals/drawing/verdict', {'element_id': 'E1', 'sha256': 'b' * 64, 'approved': True, 'quote': 'yes, that is it', 'notes': ''}),
                    ('/api/runs/run-1/visuals/drawing/verdict', {'element_id': 'E1', 'sha256': 'b' * 64, 'approved': False, 'quote': 'no', 'notes': 'the tails are too wide'})]


# ---------- the shot's drawing, and the still's look reference ----------

def test_the_shots_drawing_is_fetched_and_answered(harness, sent, monkeypatch, capsys):
    ws, _ = harness

    def call(method, path, wait=None, **kw):
        if path.endswith('/guide/VS1'):
            return {'shot_id': 'VS1', 'files': ['strip', 'drawing-camera', 'drawing-above'], 'guide': {'drawing': {'status': 'proposed', 'sha256': 'c' * 64, 'changes': ['mirrored'], 'notes': []}}}
        name = path.rsplit('/', 1)[1]
        return {'name': name, 'file': name + '.png', 'mime': 'image/png', 'base64': base64.b64encode(b'x').decode()}
    monkeypatch.setattr(vw, 'call', call)
    code, out, err = run(vw.cmd_guide, guide(what='drawing', shot='VS1'), capsys)
    assert code == 0 and len(out['files']) == 2 and out['changes'] == ['mirrored'] and (ws / 'work' / 'guide' / 'VS1' / 'drawing' / 'drawing-camera.png').exists()
    assert 'the purple side the back' in err and 'drawing-approve' in err
    assert run(vw.cmd_guide, guide(what='drawing-approve', shot='VS1', quote='yes'), capsys)[0] == 2         # no sha
    assert run(vw.cmd_guide, guide(what='drawing-reject', shot='VS1', sha='c' * 64, quote='no'), capsys)[0] == 2   # no reason
    run(vw.cmd_guide, guide(what='drawing-approve', shot='VS1', sha='c' * 64, quote='yes'), capsys)
    run(vw.cmd_guide, guide(what='drawing-reject', shot='VS1', sha='c' * 64, quote='no', notes='she faces the wrong way'), capsys)
    assert sent == [('/api/runs/run-1/visuals/guide/drawing', {'shot_id': 'VS1', 'sha256': 'c' * 64, 'approved': True, 'quote': 'yes', 'notes': ''}),
                    ('/api/runs/run-1/visuals/guide/drawing', {'shot_id': 'VS1', 'sha256': 'c' * 64, 'approved': False, 'quote': 'no', 'notes': 'she faces the wrong way'})]


def test_a_shot_with_no_drawing_yet_says_to_send_its_scene(harness, monkeypatch, capsys):
    monkeypatch.setattr(vw, 'call', lambda method, path, wait=None, **kw: {'shot_id': 'VS1', 'guide': None, 'files': []})
    code, out, _ = run(vw.cmd_guide, guide(what='drawing', shot='VS1'), capsys)
    assert code == 2 and 'send its scene first' in out['message']


def test_a_stills_look_reference_travels_with_it(harness, sent, capsys):
    ws, _ = harness
    (ws / 'work' / 'still.json').write_text(json.dumps({'prompt': 'the words', 'parents': [], 'look': 'R7'}), encoding='utf-8')
    run(vw.cmd_guide, guide(what='still', shot='VS1', file='work/still.json'), capsys)
    assert sent[-1] == ('/api/runs/run-1/visuals/guide/still', {'shot_id': 'VS1', 'prompt': 'the words', 'parents': [], 'look': 'R7'})
    (ws / 'work' / 'still.json').write_text(json.dumps({'prompt': 'the words', 'parents': []}), encoding='utf-8')
    run(vw.cmd_guide, guide(what='still', shot='VS1', file='work/still.json'), capsys)
    assert 'look' not in sent[-1][1]


# ---------- the skill, the helper, the guard ----------

def guard(tool, tool_input, cwd):
    code, _, err = run_hook('guard.py', {'tool_name': tool, 'tool_input': tool_input}, cwd)
    return code, err


def test_the_guard_allows_the_drawing_skill_and_its_helper(tmp_path):
    for skill in ('vw:drawing', 'drawing'):
        assert guard('Skill', {'skill': skill}, tmp_path)[0] == 0, skill
    for helper in ('vw:vw-drawing', 'vw-drawing'):
        assert guard('Agent', {'subagent_type': helper, 'prompt': 'E1'}, tmp_path)[0] == 0, helper
    assert guard('Bash', {'command': 'python work/drawing/E1/make.py'}, tmp_path)[0] == 2      # a helper never runs a script of its own: repeated pieces are data ("repeat")


def test_the_skill_and_the_helper_exist_and_agree_with_the_guard():
    helper = (PLUGIN / 'agents' / 'vw-drawing.md').read_text(encoding='utf-8')
    skill = (PLUGIN / 'skills' / 'drawing' / 'SKILL.md').read_text(encoding='utf-8')
    assert 'name: vw-drawing' in helper and 'vw:drawing' in helper and 'cannot run a script' in helper and 'never approve your own drawings' in helper
    assert 'name: drawing' in skill and '"repeat"' in skill and 'vw drawing set --element E' in skill and 'a person never gets a drawing set' in skill
    assert 'script of your own' not in helper and 'script of your own' not in skill
    for text in (PLUGIN / 'operator-CLAUDE.md', PLUGIN / 'commands' / 'vw.md'):
        assert 'vw-drawing' in text.read_text(encoding='utf-8'), text.name
    guide_skill = (PLUGIN / 'skills' / 'guide' / 'SKILL.md').read_text(encoding='utf-8')
    for word in ('watches', 'drawn_as', 'changed_from_plan', 'drawing-approve', '"look"', 'Images 2 and 3', 'start at Image 4'):
        assert word in guide_skill, word
    assert 'posture' in (PLUGIN / 'agents' / 'vw-guide-scene.md').read_text(encoding='utf-8')
