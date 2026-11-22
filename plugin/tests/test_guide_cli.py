"""Integration steps B to D on the plugin: `vw guide` (the scene, the check frames, the verdict, the still, the overlay, the take's words, Shoot),
the guide skill and the two helpers the guard lets through."""
import argparse
import base64
import json

import pytest

from conftest import PLUGIN, run_hook
from test_visuals_cli import harness  # noqa: F401  (the fixture rides along)
import vw


def args(**kw):
    base = {'what': 'status', 'shot': None, 'file': None, 'override': None, 'still': None, 'sha': None, 'quote': None, 'notes': None, 'region': None, 'prompt': None, 'again': False, 'cause': None, 'fix': None}
    return argparse.Namespace(**{**base, **kw})


def run(a, capsys):
    with pytest.raises(SystemExit) as exc:
        vw.cmd_guide(a)
    out, err = capsys.readouterr()
    return exc.value.code, json.loads(out), err


@pytest.fixture
def sent(monkeypatch):
    calls = []
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: calls.append((path, body)) or {'sha256': 'a' * 64, 'round': 1, 'pass': True, 'words': 40, 'next': 'the next step', 'warnings': ['one warning'], 'cannot_see': 'The checks cannot see steps.', 'layout': 'EXACT LAYOUT'})
    return calls


def test_every_command_needs_its_shot(harness, capsys):
    for what in ('scene', 'status', 'frames', 'verdict', 'still', 'look', 'repair', 'approve', 'reject', 'prompt', 'shoot'):
        code, out, err = run(args(what=what), capsys)
        assert code == 2 and f'vw guide {what} --shot S' in out['message'], what


def test_the_scene_is_sent_as_data_with_its_override_and_the_layout_is_kept(harness, sent, capsys):
    ws, _ = harness
    (ws / 'work' / 'guide' / 'VS1').mkdir(parents=True)
    (ws / 'work' / 'guide' / 'VS1' / 'scene.json').write_text(json.dumps({'recipe': 'walker', 'seconds': 5}), encoding='utf-8')
    code, out, err = run(args(what='scene', shot='VS1', file='work/guide/VS1/scene.json', override='the shelf is fixed to the wall'), capsys)
    assert code == 0 and sent == [('/api/runs/run-1/visuals/guide/scene', {'shot_id': 'VS1', 'scene': {'recipe': 'walker', 'seconds': 5}, 'overrides': {'support': 'the shelf is fixed to the wall'}})]
    assert '1 warnings: one warning.' in err and 'cannot see' in err and 'the next step' in err
    assert (ws / 'work' / 'guide' / 'VS1' / 'layout.txt').read_text(encoding='utf-8') == 'EXACT LAYOUT'
    assert json.loads((ws / 'work' / 'guide' / 'VS1' / 'last.json').read_text(encoding='utf-8'))['sha256'] == 'a' * 64


def test_a_missing_or_broken_scene_file_is_refused_before_anything_is_sent(harness, sent, capsys):
    ws, _ = harness
    assert run(args(what='scene', shot='VS1'), capsys)[0] == 2
    assert 'not a file of this run folder' in run(args(what='scene', shot='VS1', file='work/guide/VS1/nope.json'), capsys)[1]['message']
    (ws / 'work' / 'broken.json').write_text('{not json', encoding='utf-8')
    assert 'not valid JSON' in run(args(what='scene', shot='VS1', file='work/broken.json'), capsys)[1]['message']
    assert sent == []


def test_frames_saves_the_strip_and_the_check_frames_and_look_saves_the_stills_and_overlays(harness, monkeypatch, capsys):
    ws, _ = harness
    files = ['strip', 'check-0001', 'check-0075', 'frame1', 'guide', 'still-abc', 'overlay-abc']
    asked = []

    def call(method, path, wait=None, **kw):
        asked.append(path)
        if '/file/' in path:
            name = path.rsplit('/', 1)[1]
            return {'name': name, 'file': name + ('.jpg' if name.startswith(('strip', 'overlay')) else '.png'), 'mime': 'x', 'base64': base64.b64encode(name.encode()).decode()}
        return {'shot_id': 'VS1', 'files': files, 'guide': {'sha256': 'f' * 64, 'cannot_see': 'The checks cannot see steps.'}, 'next': 'n'}
    monkeypatch.setattr(vw, 'call', call)
    code, out, err = run(args(what='frames', shot='VS1'), capsys)
    folder = ws / 'work' / 'guide' / 'VS1' / 'frames'
    assert code == 0 and sorted(p.name for p in folder.iterdir()) == ['check-0001.png', 'check-0075.png', 'strip.jpg'] and (folder / 'strip.jpg').read_bytes() == b'strip'
    assert 'fresh vw-guide-check helper' in err and 'cannot see' in err
    code, out, err = run(args(what='look', shot='VS1'), capsys)
    look = ws / 'work' / 'guide' / 'VS1' / 'look'
    assert code == 0 and sorted(p.name for p in look.iterdir()) == ['frame1.png', 'overlay-abc.jpg', 'still-abc.png'] and 'red' in err
    assert not any(p.endswith('/file/guide') for p in asked)   # the video itself is not fetched by either


def test_a_verdict_is_sent_for_the_scene_last_uploaded(harness, sent, capsys):
    ws, _ = harness
    folder = ws / 'work' / 'guide' / 'VS1'
    folder.mkdir(parents=True)
    (folder / 'last.json').write_text(json.dumps({'sha256': 'b' * 64}), encoding='utf-8')
    (folder / 'verdict.json').write_text(json.dumps({'pass': True, 'looks': [{'look': 'nobody stands in front of anybody', 'pass': True}], 'notes': 'clear'}), encoding='utf-8')
    code, out, err = run(args(what='verdict', shot='VS1', file='work/guide/VS1/verdict.json'), capsys)
    assert code == 0 and sent[0] == ('/api/runs/run-1/visuals/guide/verdict', {'shot_id': 'VS1', 'sha256': 'b' * 64, 'passed': True, 'looks': [{'look': 'nobody stands in front of anybody', 'pass': True}], 'notes': 'clear'})
    assert 'Round 1: passed.' in err


def test_the_still_its_repair_and_its_verdicts(harness, sent, capsys):
    ws, _ = harness
    (ws / 'work' / 'still.json').write_text(json.dumps({'prompt': 'A wide shot.', 'parents': [{'id': 'R1', 'job': 'the father'}]}), encoding='utf-8')
    assert run(args(what='still', shot='VS1', file='work/still.json'), capsys)[0] == 0
    assert sent[-1] == ('/api/runs/run-1/visuals/guide/still', {'shot_id': 'VS1', 'prompt': 'A wide shot.', 'parents': [{'id': 'R1', 'job': 'the father'}]})
    assert run(args(what='repair', shot='VS1', still='abc'), capsys)[0] == 2
    assert run(args(what='repair', shot='VS1', still='abc', region='0.2,0.8,0.4,0.15', prompt='the band is teal; make it grey paving.'), capsys)[0] == 0
    assert sent[-1][1] == {'shot_id': 'VS1', 'prompt': 'the band is teal; make it grey paving.', 'parents': [], 'repair_of': 'abc', 'region': {'left': 0.2, 'top': 0.8, 'width': 0.4, 'height': 0.15}}
    assert run(args(what='approve', shot='VS1', still='abc'), capsys)[0] == 2   # the exact file is named by its sha
    assert run(args(what='approve', shot='VS1', still='abc', sha='c' * 64, quote='Yes.'), capsys)[0] == 0
    assert sent[-1] == ('/api/runs/run-1/visuals/guide/approve', {'shot_id': 'VS1', 'still_id': 'abc', 'sha256': 'c' * 64, 'notes': '', 'quote': 'Yes.'})
    assert run(args(what='reject', shot='VS1', still='abc'), capsys)[0] == 2
    assert run(args(what='reject', shot='VS1', still='abc', notes='the father is twice his box'), capsys)[0] == 0 and sent[-1][0].endswith('/guide/reject')


def test_the_takes_words_come_from_a_file_and_shoot_needs_the_operators_words(harness, sent, capsys):
    ws, _ = harness
    (ws / 'work' / 'take.txt').write_text('ONE action only: he walks.', encoding='utf-8')
    assert run(args(what='prompt', shot='VS1'), capsys)[0] == 2
    code, out, err = run(args(what='prompt', shot='VS1', file='work/take.txt'), capsys)
    assert code == 0 and sent[-1] == ('/api/runs/run-1/visuals/guide/prompt', {'shot_id': 'VS1', 'prompt': 'ONE action only: he walks.'}) and '40 words kept' in err
    n = len(sent)
    # design/222: with no --quote the tool sends the call and the server decides: it uses the word the operator gave on the page ("Make another"),
    # and refuses a take with no word at all (`guide.shoot`; server/unit/test_guide_route_pure.py)
    assert run(args(what='shoot', shot='VS1', quote=None), capsys)[0] == 0
    assert len(sent) == n + 1 and sent[-1] == ('/api/runs/run-1/visuals/guide/shoot', {'shot_id': 'VS1', 'quote': '', 'again': False})
    assert run(args(what='shoot', shot='VS1', quote='Yes, shoot it.', again=True), capsys)[0] == 0
    assert sent[-1] == ('/api/runs/run-1/visuals/guide/shoot', {'shot_id': 'VS1', 'quote': 'Yes, shoot it.', 'again': True})


def test_the_parser_knows_the_command():
    a = vw.build_parser().parse_args(['guide', 'shoot', '--shot', 'VS1', '--quote', 'go', '--again']) if hasattr(vw, 'build_parser') else None
    if a is not None:
        assert a.fn is vw.cmd_guide and a.again is True


# ---------- the skill, the helpers, the guard ----------

def guard(tool, tool_input, cwd):
    code, _, err = run_hook('guard.py', {'tool_name': tool, 'tool_input': tool_input}, cwd)
    return code, err


def test_the_guard_allows_the_guide_skill_and_its_two_helpers(tmp_path):
    assert guard('Skill', {'skill': 'vw:guide'}, tmp_path)[0] == 0
    for helper in ('vw:vw-guide-scene', 'vw-guide-scene', 'vw:vw-guide-check', 'vw-guide-check'):
        assert guard('Agent', {'subagent_type': helper, 'prompt': 'VS1'}, tmp_path)[0] == 0, helper
    assert guard('Agent', {'subagent_type': 'general-purpose', 'prompt': 'VS1'}, tmp_path)[0] == 2
    assert guard('Bash', {'command': 'blender -b scene.blend'}, tmp_path)[0] == 2   # Blender runs on the server, never here


def test_the_helpers_and_the_skill_exist_and_the_checker_cannot_run_anything():
    scene = (PLUGIN / 'agents' / 'vw-guide-scene.md').read_text(encoding='utf-8')
    check = (PLUGIN / 'agents' / 'vw-guide-check.md').read_text(encoding='utf-8')
    skill = (PLUGIN / 'skills' / 'guide' / 'SKILL.md').read_text(encoding='utf-8')
    assert 'name: vw-guide-scene' in scene and 'vw:guide' in scene and 'never run Blender' in scene
    assert 'name: vw-guide-check' in check and 'tools: Read, Write, Glob' in check and 'did not build it' in check
    assert 'name: guide' in skill and 'ONE action only' in skill and "only on the operator's word" in skill
    # design/207: any kind of shot may be an AI video; three kinds are proven here; a thing travels along a timed path
    assert 'not yet available' not in skill and 'not yet available' not in scene
    for word in ('Any kind of shot may be an AI video', 'proven here', '`other`', 'has not been tried here', 'A thing on a path', '"path"', 'Nobody is in view', 'lips will not match'):
        assert word in skill, word
    assert '`other`' in scene and 'trial' in scene
    for text in (PLUGIN / 'operator-CLAUDE.md', PLUGIN / 'commands' / 'vw.md'):
        assert 'vw-guide-scene' in text.read_text(encoding='utf-8') and 'vw-guide-check' in text.read_text(encoding='utf-8')


def test_the_skill_names_no_one_film(tmp_path):
    skill = (PLUGIN / 'skills' / 'guide' / 'SKILL.md').read_text(encoding='utf-8').lower()
    for word in ('tea stall', 'tea master', 'kettle', 'hospital', 'documentary'):
        assert word not in skill, word


def test_the_cause_of_a_rejected_take_is_retired_and_refused_by_name(harness, sent, capsys):   # design/223
    code, out, err = run(args(what='cause', shot='VS1', cause='guide', notes='the path crosses the post', fix='move the path 0.5 m'), capsys)
    assert code == 2 and 'retired (design/223)' in out['message'] and 'vw guide correct --shot S' in out['message'] and sent == []


def test_the_corrections_are_listed_with_their_frames_and_pictures_fetched_and_the_rule_kept(harness, capsys, monkeypatch):   # design/223
    ws, _ = harness
    listed = {'corrections': [{'shot_id': 'VS1', 'name': 'The walk home', 'words': 'There are poles on the left.', 'frames': [{'at_s': 0.0, 'key': 'k/f0.jpg'}, {'at_s': 2.5, 'key': 'k/f25.jpg'}],
                               'sheet': 'k/sheet.jpg', 'pictures': [{'id': 'R1', 'kind': 'sheet', 'element_id': 'P1', 'key': 'k/R1.png'}]}],
              'rule': 'The route of a correction.', 'file': '{...}', 'then': 'For each: choose the route by the rule.'}
    got = []
    monkeypatch.setattr(vw, 'call', lambda method, path, *a, **k: listed if (method, path) == ('GET', '/api/runs/run-1/visuals/guide-corrections') else {})
    monkeypatch.setattr(vw, '_download', lambda m, key, rel, expect=None: got.append((key, rel)))
    code, out, err = run(args(what='corrections'), capsys)   # no --shot: every correction that waits
    assert code == 0 and out['corrections'] == ['VS1'] and out['file'] == 'work/guide/corrections.json' and 'choose the route by the rule' in err
    assert got == [('k/f0.jpg', 'work/guide/VS1/correction/frame-0000.jpg'), ('k/f25.jpg', 'work/guide/VS1/correction/frame-0025.jpg'),
                   ('k/sheet.jpg', 'work/guide/VS1/correction/sheet.jpg'), ('k/R1.png', 'work/guide/VS1/correction/picture-R1.png')]
    kept = json.loads((ws / 'work' / 'guide' / 'corrections.json').read_text(encoding='utf-8'))
    assert kept['rule'] == 'The route of a correction.' and kept['corrections'][0]['frames'][1]['file'].endswith('frame-0025.jpg') and kept['corrections'][0]['pictures'][0]['file'].endswith('picture-R1.png')


def test_a_correction_is_sent_from_its_file_withdrawn_with_the_operators_words_or_reopened(harness, sent, capsys):   # design/223
    ws, _ = harness
    assert run(args(what='correct'), capsys)[0] == 2                                                   # it needs its shot
    code, out, err = run(args(what='correct', shot='VS1', withdraw=False, reopen=None, reason=None), capsys)
    assert code == 2 and 'vw guide correct --shot S --file' in out['message'] and sent == []
    (ws / 'work' / 'guide' / 'VS1').mkdir(parents=True)
    body = {'route': 'edit', 'reason': 'Only the poles are wrong.', 'changes': ['Remove the poles on the left.'], 'keep': 'the people, the place, the camera, the light, the timing'}
    (ws / 'work' / 'guide' / 'VS1' / 'correction.json').write_text(json.dumps(body), encoding='utf-8')
    run(args(what='correct', shot='VS1', file='work/guide/VS1/correction.json', withdraw=False, reopen=None, reason=None), capsys)
    run(args(what='correct', shot='VS1', withdraw=True, reopen=None, reason='Leave it as it is.'), capsys)
    run(args(what='correct', shot='VS1', withdraw=False, reopen='The roof is wrong after all.', quote='The roof is wrong after all.', reason=None), capsys)
    assert sent == [('/api/runs/run-1/visuals/guide/correct', {'shot_id': 'VS1', 'correction': body}),
                    ('/api/runs/run-1/visuals/guide/correct', {'shot_id': 'VS1', 'correction': {'route': 'none', 'withdrawn': True, 'reason': 'Leave it as it is.'}}),
                    ('/api/runs/run-1/visuals/guide/correct', {'shot_id': 'VS1', 'reopen': 'The roof is wrong after all.', 'quote': 'The roof is wrong after all.'})]
