"""design/130 on the plugin: `vw start --drawn`, the `vw motion` commands (the brief and its pictures, the zip, check and snapshot waited for and
saved, render), and the guard (the motion skill and helpers allowed, the skill files readable and never writable, npx still blocked)."""
import argparse
import base64
import io
import json
import zipfile

import pytest

from conftest import PLUGIN, run_hook
from test_visuals_cli import harness  # noqa: F401  (the fixture rides along)
import vw

VW = PLUGIN / 'scripts' / 'vw.py'


def margs(**kw):
    return argparse.Namespace(**{'what': 'status', 'shot': None, 'dir': None, 'sha': None, 'at': None, 'zoom': None, 'job': None, 'file': None,
                                 'subject': None, 'add': None, 'quote': None, 'crop': None, **kw})


def mrun(a, capsys):
    with pytest.raises(SystemExit) as exc:
        vw.cmd_motion(a)
    out, err = capsys.readouterr()
    return exc.value.code, json.loads(out), err


def project(ws, shot='MO1'):
    p = ws / 'work' / 'motion' / shot / 'project'
    (p / 'compositions').mkdir(parents=True)
    (p / 'index.html').write_text('<html>root</html>', encoding='utf-8')
    (p / 'compositions' / 'wall.html').write_text('<template>wall</template>', encoding='utf-8')
    for junk in ('assets/vendor/gsap.min.js', 'assets/ref/comp-1.png', '.hyperframes/state.json', 'snapshots/at-1s.png', 'out.mp4', 'index.motion.json'):
        (p / junk).parent.mkdir(parents=True, exist_ok=True)
        (p / junk).write_bytes(b'x')
    return p


def test_the_zip_holds_the_project_and_leaves_out_the_servers_files_and_scratch(harness):
    ws, _ = harness
    names = zipfile.ZipFile(io.BytesIO(vw.motion_zip(project(ws)))).namelist()
    assert sorted(names) == ['compositions/wall.html', 'index.html']


def test_brief_writes_the_brief_and_brings_the_pictures(harness, monkeypatch, capsys):
    ws, _ = harness
    got = []
    monkeypatch.setattr(vw, 'call', lambda method, path, **kw: {'brief': '# Brief: drawn shot MO1\n', 'refs': ['comp-1']})
    monkeypatch.setattr(vw, '_download', lambda m, key, rel, expect=None: got.append((key, rel)) or str(ws / rel))
    code, out, _ = mrun(margs(what='brief'), capsys)
    assert code == 2 and '--shot S' in out['message']
    code, out, _ = mrun(margs(what='brief', shot='MO1'), capsys)
    assert code == 0 and (ws / 'work/motion/MO1/brief.md').read_text(encoding='utf-8').startswith('# Brief') and (ws / 'work/motion/MO1/project').is_dir()
    assert got == [('run-1/visuals/references/comp-1.png', 'work/motion/MO1/refs/comp-1.png')]


def test_upload_posts_the_zip_and_remembers_the_sha_for_check_and_snapshot(harness, monkeypatch, capsys):
    ws, _ = harness
    posted, polls = [], iter([{'status': 'running'}, {'status': 'ready', 'result': {'ok': False, 'errors': [{'code': 'motion_appears_late', 'message': 'late', 'fix': 'earlier'}], 'warnings': []}}])
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: posted.append((path, body)) or ({'sha256': 'b' * 64, 'next': 'Project stored.'} if path.endswith('/upload') else {'job_id': 'j1'}))
    monkeypatch.setattr(vw, 'call', lambda method, path, **kw: next(polls))
    code, out, _ = mrun(margs(what='upload', shot='MO1'), capsys)
    assert code == 2 and 'No index.html' in out['message']
    project(ws)
    code, out, _ = mrun(margs(what='upload', shot='MO1'), capsys)
    assert code == 0 and posted[-1][0].endswith('/motion/upload') and posted[-1][1]['name'] == 'MO1.zip'
    assert sorted(zipfile.ZipFile(io.BytesIO(base64.b64decode(posted[-1][1]['content_base64']))).namelist()) == ['compositions/wall.html', 'index.html']
    code, out, _ = mrun(margs(what='check', shot='MO1'), capsys)
    assert code == 0 and posted[-1][1] == {'shot_id': 'MO1', 'op': 'check', 'sha256': 'b' * 64, 'at': [], 'zoom': ''}
    assert out['errors'][0]['code'] == 'motion_appears_late' and json.loads((ws / 'work/motion/MO1/check.json').read_text(encoding='utf-8'))['ok'] is False


def test_snapshot_saves_each_png_by_its_second(harness, monkeypatch, capsys):
    ws, _ = harness
    (ws / 'work/motion/MO1').mkdir(parents=True)
    (ws / 'work/motion/MO1/last-upload.json').write_text(json.dumps({'sha256': 'b' * 64}), encoding='utf-8')
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: {'job_id': 'j2'})
    monkeypatch.setattr(vw, 'call', lambda method, path, **kw: {'status': 'ready', 'result': {'snapshots': [{'at': 0.5, 'png_base64': base64.b64encode(b'png1').decode()}, {'at': 2.0, 'png_base64': base64.b64encode(b'png2').decode()}]}})
    code, out, _ = mrun(margs(what='snapshot', shot='MO1'), capsys)
    assert code == 2 and '--at' in out['message']
    code, out, _ = mrun(margs(what='snapshot', shot='MO1', at='0.5,2'), capsys)
    assert code == 0 and (ws / 'work/motion/MO1/snapshots/at-0.5s.png').read_bytes() == b'png1' and (ws / 'work/motion/MO1/snapshots/at-2s.png').read_bytes() == b'png2'


def test_check_without_an_upload_is_refused_and_render_posts_the_shot(harness, monkeypatch, capsys):
    posted = []
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: posted.append((path, body)) or {'job_id': 'j3', 'next': 'Rendering 139 frames'})
    code, out, _ = mrun(margs(what='check', shot='MO2'), capsys)
    assert code == 2 and 'Upload the project first' in out['message']
    code, out, _ = mrun(margs(what='render', shot='MO1'), capsys)
    assert code == 0 and posted == [('/api/runs/run-1/visuals/motion/render', {'shot_id': 'MO1'})]


def test_start_sends_the_drawn_route_only_when_given():
    p = vw.build_parser()
    assert p.parse_args(['start', '--client', 'C', '--images', 'openai', '--drawn', 'motion']).drawn == 'motion'
    assert p.parse_args(['start', '--client', 'C', '--images', 'openai']).drawn is None
    a = p.parse_args(['motion', 'snapshot', '--shot', 'MO1', '--at', '0.5,2'])
    assert a.fn is vw.cmd_motion and a.at == '0.5,2'


# ---------- the guard ----------

def guard(tool, tool_input, cwd):
    code, _, err = run_hook('guard.py', {'tool_name': tool, 'tool_input': tool_input}, cwd)
    return code, err


def test_the_guard_allows_the_motion_skill_and_helpers_and_still_blocks_npx(tmp_path):
    assert guard('Skill', {'skill': 'vw:motion'}, tmp_path)[0] == 0
    assert guard('Skill', {'skill': 'hyperframes'}, tmp_path)[0] == 2
    for helper in ('vw:vw-motion-shot', 'vw-motion-rules', 'vw:vw-motion-check'):
        assert guard('Agent', {'subagent_type': helper, 'prompt': 'MO1'}, tmp_path)[0] == 0, helper
    for cmd in ('npx hyperframes render', 'node x.js', 'hyperframes check'):
        assert guard('Bash', {'command': cmd}, tmp_path)[0] == 2, cmd
    assert guard('Bash', {'command': f'python "{VW}" motion check --shot MO1'}, tmp_path)[0] == 0


def test_the_skill_files_are_readable_and_never_writable(tmp_path):
    ref = PLUGIN / 'skills' / 'motion' / 'references' / 'format.md'
    assert ref.is_file()
    assert guard('Read', {'file_path': str(ref)}, tmp_path)[0] == 0
    assert guard('Glob', {'pattern': '*.md', 'path': str(ref.parent)}, tmp_path)[0] == 0
    assert guard('Write', {'file_path': str(ref)}, tmp_path)[0] == 2
    assert guard('Read', {'file_path': str(PLUGIN / 'scripts' / 'vw.py')}, tmp_path)[0] == 2


# ---------- phase 3: verdicts, subject rules, close-ups ----------

def test_verdict_posts_the_checkers_file(harness, monkeypatch, capsys):
    ws, _ = harness
    posted = []
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: posted.append((path, body)) or {'failed': ['rule 2'], 'next': '1 rules failed'})
    code, out, _ = mrun(margs(what='verdict', shot='MO1'), capsys)
    assert code == 2 and 'check-1.json' in out['message']
    f = ws / 'work/motion/MO1/check-1.json'
    f.parent.mkdir(parents=True)
    f.write_text(json.dumps({'shot_id': 'MO1', 'sha256': 'b' * 64, 'round': 1, 'stranger': ['a wall'], 'rules': [{'n': 1, 'rule': 'r', 'pass': False}]}), encoding='utf-8')
    code, out, _ = mrun(margs(what='verdict', shot='MO1', file='work/motion/MO1/check-1.json'), capsys)
    assert code == 0 and posted == [('/api/runs/run-1/visuals/motion/verdict', {'shot_id': 'MO1', 'sha256': 'b' * 64, 'round': 1, 'stranger': ['a wall'], 'rules': [{'n': 1, 'rule': 'r', 'pass': False}]})]
    f.write_text('{not json', encoding='utf-8')
    code, out, _ = mrun(margs(what='verdict', shot='MO1', file='work/motion/MO1/check-1.json'), capsys)
    assert code == 2 and 'not valid JSON' in out['message']


def test_rule_needs_the_subject_the_rule_and_the_operators_words(harness, monkeypatch, capsys):
    posted = []
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: posted.append((path, body)) or {'next': 'Kept'})
    code, out, _ = mrun(margs(what='rule', subject='rat-trap-bond', add='An opening has a lintel.'), capsys)
    assert code == 2 and '--quote' in out['message'] and not posted
    code, out, _ = mrun(margs(what='rule', subject='rat-trap-bond', add='An opening has a lintel.', quote='yes'), capsys)
    assert code == 0 and posted == [('/api/runs/run-1/visuals/motion/rule', {'subject': 'rat-trap-bond', 'rule': 'An opening has a lintel.', 'quote': 'yes'})]


def test_snapshot_sends_the_crops_and_saves_each_close_up(harness, monkeypatch, capsys):
    ws, _ = harness
    (ws / 'work/motion/MO1').mkdir(parents=True)
    (ws / 'work/motion/MO1/last-upload.json').write_text(json.dumps({'sha256': 'b' * 64}), encoding='utf-8')
    posted = []
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: posted.append(body) or {'job_id': 'j2'})
    monkeypatch.setattr(vw, 'call', lambda method, path, **kw: {'status': 'ready', 'result': {'snapshots': [{'at': 1.0, 'png_base64': base64.b64encode(b'f').decode(),
                                                                                                         'crops': [{'box': [0.5, 0.5, 0.2, 0.2], 'png_base64': base64.b64encode(b'c').decode()}]}]}})
    code, out, _ = mrun(margs(what='snapshot', shot='MO1', at='1', crop=['0.5,0.5,0.2,0.2']), capsys)
    assert code == 0 and posted[-1]['crops'] == [[0.5, 0.5, 0.2, 0.2]] and (ws / 'work/motion/MO1/snapshots/at-1s-crop1.png').read_bytes() == b'c'
    code, out, _ = mrun(margs(what='snapshot', shot='MO1', at='1', crop=['half']), capsys)
    assert code == 2 and 'fractions' in out['message']
