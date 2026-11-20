"""Fix set, the critic's points (19 Nov 2026) on the plugin. 6: the round's list is written in two parts, the open rules and below them the
musts that passed (answered only when the upload broke one). 7: for the still end-frame of a drawing that continues another, the brief puts
the earlier drawing's approved still end-frame and that still's files beside it. 10: the still-prompts helper may list a folder. 11: the guard
lets through every helper the served text, the server's own lines and the plugin's texts tell the assistant to start."""
import io
import zipfile

from conftest import PLUGIN, REPO, run_hook
from test_design130 import margs, mrun, project
from test_visuals_cli import harness  # noqa: F401  (the fixture rides along)
import vw


def test_p6_the_rounds_list_is_written_in_two_parts(harness, monkeypatch, capsys):
    ws, _ = harness
    project(ws)
    answer = {'sha256': 'b' * 64, 'next': 'Project stored.', 'round_rules': ['must: There are four rods.', 'should: The leader lines do not cross.'],
              'round_passed': ['must: The block rests on the rods.', 'must: The rods appear first.']}
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: answer)
    assert mrun(margs(what='upload', shot='MO1'), capsys)[0] == 0
    assert (ws / 'work/motion/MO1/rules-round.md').read_text(encoding='utf-8') == (
        '1. must: There are four rods.\n2. should: The leader lines do not cross.\n'
        '\nPassed before. Answer one of these ONLY if this upload broke it ("pass": false, with where); leave the others out:\n'
        '3. must: The block rests on the rods.\n4. must: The rods appear first.\n')
    answer['round_passed'] = []   # no must passed before: the open rules alone, as before
    assert mrun(margs(what='upload', shot='MO1'), capsys)[0] == 0
    assert (ws / 'work/motion/MO1/rules-round.md').read_text(encoding='utf-8') == '1. must: There are four rods.\n2. should: The leader lines do not cross.\n'


def test_p7_the_brief_of_a_continuing_still_brings_the_earlier_approved_still_and_its_files(harness, monkeypatch, capsys):
    ws, _ = harness
    project(ws)
    got = []
    zipped = io.BytesIO()
    with zipfile.ZipFile(zipped, 'w') as z:
        z.writestr('index.html', '<html></html>')

    def download(m, key, rel, expect=None):
        got.append((key, rel))
        (ws / rel).parent.mkdir(parents=True, exist_ok=True)
        (ws / rel).write_bytes(zipped.getvalue() if rel.endswith('.zip') else b'\x89PNG')
        return ws / rel
    monkeypatch.setattr(vw, '_download', download)
    continues = {'shot_id': 'MO0', 'project_key': 'run-1/visuals/motion/projects/s.zip', 'opens_on_key': 'run-1/visuals/motion/tools/s0/0.png'}   # MO0's project has not passed: its still
    monkeypatch.setattr(vw, 'call', lambda method, path, **kw: {'brief': '# Brief', 'lines': {}, 'refs': [], 'continues': continues})
    code, out, err = mrun(margs(what='brief', shot='MO1'), capsys)
    assert code == 0 and ('run-1/visuals/motion/tools/s0/0.png', 'work/motion/MO1/from-MO0/opens-on.png') in got
    assert (ws / 'work/motion/MO1/from-MO0/index.html').is_file() and (ws / 'work/motion/MO1/from-MO0/opens-on.png').is_file()
    assert err.strip().endswith("MO0's approved still end-frame (opens-on.png) and that still's files are in work/motion/MO1/from-MO0/: build MO1's still end-frame "
                                "from them; its motion waits for MO0's passed project.")


def test_p10_the_still_prompts_helper_may_list_the_folder_it_is_told_to_read():
    text = (PLUGIN / 'agents' / 'vw-still-prompts.md').read_text(encoding='utf-8').replace('\r\n', '\n')
    assert text.startswith('---\nname: vw-still-prompts\n') and 'tools: Read, Write, Glob\nmodel: opus\neffort: high\n---\n' in text


def test_p11_the_guard_allows_every_helper_the_texts_tell_the_assistant_to_start(tmp_path):
    said = ''.join(p.read_text(encoding='utf-8') for p in [REPO / 'server' / 'procedures' / 'v3.json', *sorted((REPO / 'server' / 'app').glob('*.py')),
                                                           PLUGIN / 'commands' / 'vw.md', *sorted((PLUGIN / 'skills').glob('*/SKILL.md'))])
    named = [p.stem for p in sorted((PLUGIN / 'agents').glob('*.md')) if p.stem in said]
    assert {'vw-picture-look', 'vw-take-look', 'vw-motion-parts', 'vw-still-prompts', 'vw-motion-shot', 'vw-motion-check'} <= set(named)
    blocked = [helper for name in named for helper in (name, 'vw:' + name)
               if run_hook('guard.py', {'tool_name': 'Agent', 'tool_input': {'subagent_type': helper, 'prompt': 'the run folder'}}, tmp_path)[0] != 0]
    assert blocked == []
    assert run_hook('guard.py', {'tool_name': 'Agent', 'tool_input': {'subagent_type': 'general-purpose', 'prompt': 'x'}}, tmp_path)[0] == 2   # any other helper stays blocked
