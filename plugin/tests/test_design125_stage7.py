"""design/125 stage 7, the chat tool's side: P3 the pieces read by scene; O4-O6 the second look (`vw options second-look`, the helper,
`vw options join-second-look`); O9 the plan's helper; the retired ways refused (`vw options record`, `vw first-cut record`, `vw planning`);
P10 and the old ways in the command text; the guard lets the two named helpers run."""
import argparse
import json

import pytest

from conftest import PLUGIN
from test_guard import active as guard_active, guard
import vw

COMMAND = (PLUGIN / 'commands' / 'vw.md').read_text(encoding='utf-8')
CARD = {'clip_id': 'c1', 'clip_name': 'C1.mp4', 'lines': ['OVERVIEW: A mason lays bricks on edge.', 'SOURCE SPECS: 25 fps']}


def row(sub, clip='c1', **kw):
    base = {'sub_clip_id': sub, 'clip_id': clip, 'clip_name': clip.upper() + '.mp4', 'grade': 'A', 'duration_s': 4.0, 'in_frame': 0, 'out_frame': 100,
            'native_shot_size': 'MS', 'effective_shot_size': 'MS', 'action_peak': None, 'outcome_state': 'a course laid', 'pairing_constraints': [],
            'risk_flags': [], 'eligibility': 'ELIGIBLE_AS_IS', 'min_hold_s': 1.5, 'primary_fits': [], 'secondary_fits': [], 'process_stage': '',
            'source_fps': '25', 'landmarks': ['wall'], 'energy': 2, 'color_group': 'g', 'handles': {}, 'sfx_cues': [], 'entry_eye_grid': 'Center'}
    return {**base, **kw}


def package():
    beats = [{'beat_id': 'BEAT_01', 'title': 'Laying', 'process_stages': ['Laying bricks'], 'target_beat_frames': 150, 'timeline_start_frame': 0,
              'steps': [{'step_id': 'BEAT_01.S1', 'text': 'Bricks go on edge.', 'start_frame': 0, 'end_frame': 70},
                        {'step_id': 'BEAT_01.S2', 'text': 'Cavities form.', 'start_frame': 72, 'end_frame': 148}]},
             {'beat_id': 'BEAT_02', 'title': 'Curing', 'process_stages': ['Curing'], 'target_beat_frames': 100, 'timeline_start_frame': 150,
              'steps': [{'step_id': 'BEAT_02.S1', 'text': 'The wall is cured.', 'start_frame': 150, 'end_frame': 248}]}]
    subs = [row('c1:S1', primary_fits=['BEAT_01']),
            row('c1:S2', secondary_fits=['BEAT_01'], grade='B'),
            row('c2:S1', 'c2', fit_kinds={'BEAT_01': 'chapter'}),
            row('c3:S1', 'c3', fit_kinds={'BEAT_02': 'direct', 'BEAT_01': 'related'}, primary_fits=['BEAT_01']),
            row('c4:S1', 'c4', source_fps='50', in_frame=0, out_frame=400)]
    cards = [CARD, {'clip_id': 'c2', 'lines': ['OVERVIEW: Mortar mixed by hand.']}, {'clip_id': 'c3', 'lines': ['OVERVIEW: Wet sacks on a wall.']},
             {'clip_id': 'c4', 'lines': ['OVERVIEW: A finished house.']}]
    return {'prompt': 'ppp', 'beats': beats, 'sub_clips': subs, 'cards': cards, 'coverage': [], 'shapes': {'options': {}}, 'timeline': {'fps': 25},
            'narration': {'sentences': [{'first_word_id': 'W1', 'text': 'Bricks go on edge.'}], 'words': [{'id': 'W1', 'start_frame': 0}]},
            'entities': [1], 'policy': {}, 'project': {}}


def read_rows(path):
    return json.loads(path.read_text(encoding='utf-8'))


# ---------- P3: the pieces by scene ----------

def test_p3_one_file_per_scene_with_its_sentences_and_its_pieces_in_fit_order(tmp_path):
    files = vw.options_reading_files(tmp_path, package())
    folder = tmp_path / 'work' / 'options'
    names = sorted(p.name for p in folder.iterdir() if p.is_file())
    assert names == ['beats.json', 'coverage.json', 'narration.json', 'pieces-BEAT_01.json', 'pieces-BEAT_02.json', 'pieces-other.json', 'prompt.md', 'rest.json',
                     'shapes.json', 'words-1.json']
    one = read_rows(folder / 'pieces-BEAT_01.json')
    assert one['beat_id'] == 'BEAT_01' and [s['step_id'] for s in one['sentences']] == ['BEAT_01.S1', 'BEAT_01.S2']
    assert one['sentences'][0] == {'step_id': 'BEAT_01.S1', 'text': 'Bricks go on edge.', 'start_frame': 0, 'end_frame': 70}
    # direct first, then related, then the same chapter; fit_kinds (after the scenes are approved) wins over the primary and secondary fits
    assert [(p['sub_clip_id'], p['fit']) for p in one['pieces']] == [('c1:S1', 'direct'), ('c1:S2', 'related'), ('c3:S1', 'related'), ('c2:S1', 'chapter')]
    assert [(p['sub_clip_id'], p['fit']) for p in read_rows(folder / 'pieces-BEAT_02.json')['pieces']] == [('c3:S1', 'direct')]
    piece = one['pieces'][0]
    assert set(piece) == {'sub_clip_id', 'clip_name', 'seen', 'fit', 'grade', 'duration_s', 'in_frame', 'out_frame', 'native_shot_size', 'effective_shot_size',
                          'outcome_state', 'eligibility', 'min_hold_s'}   # the empty ones (action_peak, pairing_constraints, risk_flags) left out
    assert piece['seen'] == 'A mason lays bricks on edge.' and 'seen' not in one['pieces'][1]   # a clip's overview once a file
    assert vw.pieces_by_scene({**package(), 'sub_clips': [row('c1:S1', primary_fits=['BEAT_01'], risk_flags=['ppe'], action_peak={'in_frame': 5})]})[0][0]['pieces'][0]['risk_flags'] == ['ppe']
    assert 'steps' not in read_rows(folder / 'beats.json')[0] and 'text' not in read_rows(folder / 'beats.json')[0]
    assert [p['sub_clip_id'] for p in read_rows(folder / 'pieces-other.json')] == ['c4:S1']   # fits no scene: listed once, at the end
    by = {f['file']: f for f in files}
    assert by['work/options/pieces-BEAT_01.json']['rows'] == 4 and by['work/options/pieces-other.json']['rows'] == 1
    for line in (folder / 'pieces-BEAT_01.json').read_text(encoding='utf-8').split('\n'):
        if '"sub_clip_id"' in line:
            json.loads(line.strip().rstrip(','))   # one piece a line


def test_p3_a_scene_too_big_for_one_read_continues_in_a_second_file(tmp_path, monkeypatch):
    monkeypatch.setattr(vw, 'OPTIONS_FILE_BYTES', 2000)
    data = package()
    data['sub_clips'] = [row(f'c1:S{i}', primary_fits=['BEAT_01'], outcome_state='x' * 200) for i in range(12)]
    vw.options_reading_files(tmp_path, data)
    folder = tmp_path / 'work' / 'options'
    first, second = read_rows(folder / 'pieces-BEAT_01.json'), read_rows(folder / 'pieces-BEAT_01-2.json')
    assert first['sentences'] and second['beat_id'] == 'BEAT_01' and 'continues pieces-BEAT_01.json' in second['note']
    assert len(first['pieces']) + len(second['pieces']) + sum(len(read_rows(p)['pieces']) for p in folder.glob('pieces-BEAT_01-[3-9].json')) == 12
    assert all(p.stat().st_size < 2600 for p in folder.glob('pieces-BEAT_01*.json'))


def test_show_sub_prints_the_full_row_and_the_card(monkeypatch, capsys):
    monkeypatch.setattr(vw, 'active', lambda: {'code': 'VW-9', 'run_id': 'run-1'})
    monkeypatch.setattr(vw, 'options_package', lambda m: package())
    code, out, err = run(vw.cmd_options, opt(what='show', sub='c1:S1'), capsys)
    assert code == 0 and out['row']['landmarks'] == ['wall'] and out['row']['sfx_cues'] == [] and out['card'] == CARD
    code, out, err = run(vw.cmd_options, opt(what='show', sub='c9:S1'), capsys)
    assert code == 2 and 'c9:S1' in out['message']


# ---------- O4-O6: the second look ----------

def opt(**kw):
    base = {'what': 'status', 'file': None, 'sub': None, 'edge': None, 'option': None, 'unit': None, 'quote': None, 'wait': 0, 'film': None}
    return argparse.Namespace(**{**base, **kw})


def run(fn, a, capsys):
    with pytest.raises(SystemExit) as exc:
        fn(a)
    out, err = capsys.readouterr()
    return exc.value.code, json.loads(out), err


def options_doc():
    return {'contract': 'vw2-options-v1', 'options': [
        {'option_number': 1, 'beat_id': 'BEAT_01', 'rank': 'PRIMARY', 'steps': [{'step_id': 'BEAT_01.S1', 'event': 1}],
         'events': [{'sub_clip_id': 'c1:S1', 'source_in_frame': 0, 'source_out_frame': 75, 'match': 'direct'},
                    {'blank': True, 'timeline_frames': 75, 'intent': 'cavities'}]},
        {'option_number': 2, 'beat_id': 'BEAT_02', 'rank': 'PRIMARY',
         'events': [{'sub_clip_id': 'c4:S1', 'source_in_frame': 0, 'source_out_frame': 200, 'match': 'b_roll', 'decision': {'kind': 'b_roll', 'question': '?'}}]}],
        'qc_self': {}}


@pytest.fixture
def ws(tmp_path, monkeypatch):
    monkeypatch.setattr(vw, 'RUNS', tmp_path / 'runs')
    w = tmp_path / 'runs' / 'VW-9'
    (w / 'out').mkdir(parents=True)
    (w / 'out' / 'options.json').write_text(json.dumps(options_doc()), encoding='utf-8')
    monkeypatch.setattr(vw, 'active', lambda: {'code': 'VW-9', 'run_id': 'run-1'})
    monkeypatch.setattr(vw, 'options_package', lambda m: package())
    return w


def test_second_look_writes_one_file_per_scene_with_its_own_sentences_and_frames(ws, monkeypatch, capsys):
    asked = []

    def request(method, path, **kw):
        asked.append((path, kw['json']['sub_clip_id'], kw['json']['edge']))
        if kw['json']['sub_clip_id'] == 'c4:S1' and kw['json']['edge'] == 'out':
            return {'action': 'refused', 'message': 'no frame there'}, 422
        return {'frames': [{'frame_id': f'F{i}', 'key': f'k{i}'} for i in range(1, 10)]}, 0
    monkeypatch.setattr(vw, 'request', request)
    monkeypatch.setattr(vw, '_download', lambda m, key, rel, expect=None: rel)
    code, out, err = run(vw.cmd_options, opt(what='second-look'), capsys)
    assert code == 0 and 'vw-scene-review' in err and 'join-second-look' in err
    assert {(s, e) for _, s, e in asked} == {('c1:S1', 'in'), ('c1:S1', 'out'), ('c4:S1', 'in'), ('c4:S1', 'out')} and asked[0][0] == '/api/runs/run-1/options/frames'
    one = read_rows(ws / 'work' / 'options' / 'scenes' / 'BEAT_01.json')
    assert [s['step_id'] for s in one['sentences']] == ['BEAT_01.S1', 'BEAT_01.S2'] and one['target_beat_frames'] == 150
    assert [(e['at_frame'], e['frames']) for e in one['options'][0]['events']] == [(0, 75), (75, 75)]
    assert [p['sub_clip_id'] for p in one['candidates']][:2] == ['c1:S1', 'c1:S2'] and one['candidates'][0]['seen'] == 'A mason lays bricks on edge.'
    assert one['frames']['c1:S1']['in'] == ['work/frames/c1-S1-in/F1.png', 'work/frames/c1-S1-in/F5.png', 'work/frames/c1-S1-in/F9.png']
    two = read_rows(ws / 'work' / 'options' / 'scenes' / 'BEAT_02.json')
    assert [s['step_id'] for s in two['sentences']] == ['BEAT_02.S1'] and two['options'][0]['events'][0]['frames'] == 100   # 200 source frames at 50 fps
    assert two['frames']['c4:S1']['out'] == [] and 'no frame there' in two['frames']['c4:S1']['note']
    assert {f['file'] for f in out['files']} == {'work/options/scenes/BEAT_01.json', 'work/options/scenes/BEAT_02.json'}


def test_second_look_needs_the_cut(ws, capsys):
    (ws / 'out' / 'options.json').unlink()
    code, out, err = run(vw.cmd_options, opt(what='second-look'), capsys)
    assert code == 2 and 'out/options.json' in out['message']


def fix(ws, beat, body):
    (ws / 'out' / 'second-look').mkdir(exist_ok=True)
    (ws / 'out' / 'second-look' / f'{beat}.json').write_text(json.dumps(body), encoding='utf-8')


def test_join_replaces_only_that_scenes_events(ws, capsys):
    new = [{'sub_clip_id': 'c1:S2', 'source_in_frame': 0, 'source_out_frame': 50, 'match': 'direct'}, {'blank': True, 'timeline_frames': 100, 'intent': 'cavities'}]
    fix(ws, 'BEAT_01', {'why': 'S2 shows the edge', 'options': [{'option_number': 1, 'events': new, 'steps': [{'step_id': 'BEAT_01.S1', 'event': 1}]}]})
    fix(ws, 'BEAT_02', {'why': 'no change: the house is right'})
    code, out, err = run(vw.cmd_options, opt(what='join-second-look'), capsys)
    doc = read_rows(ws / 'out' / 'options.json')
    assert code == 0 and doc['options'][0]['events'] == new and doc['options'][1] == options_doc()['options'][1] and doc['qc_self'] == {}
    assert out['changed'] == ['BEAT_01'] and out['unchanged'] == {'BEAT_02': 'no change: the house is right'} and 'vw options check' in err


def test_join_refuses_a_fix_of_the_wrong_length_by_name_and_writes_nothing(ws, capsys):
    fix(ws, 'BEAT_01', {'why': 'shorter', 'options': [{'option_number': 1, 'events': [{'blank': True, 'timeline_frames': 140, 'intent': 'x'}]}]})
    fix(ws, 'BEAT_02', {'why': 'other', 'options': [{'option_number': 2, 'events': [{'blank': True, 'timeline_frames': 100, 'intent': 'x'}]}]})
    code, out, err = run(vw.cmd_options, opt(what='join-second-look'), capsys)
    assert code == 2 and 'out/second-look/BEAT_01.json' in out['message'] and '140' in out['message'] and '150' in out['message']
    assert read_rows(ws / 'out' / 'options.json') == options_doc()


def test_join_refuses_another_scenes_option_and_an_unknown_piece(ws, capsys):
    fix(ws, 'BEAT_01', {'why': 'x', 'options': [{'option_number': 2, 'events': [{'blank': True, 'timeline_frames': 150, 'intent': 'x'}]}]})
    code, out, err = run(vw.cmd_options, opt(what='join-second-look'), capsys)
    assert code == 2 and 'BEAT_01' in out['message'] and '#2' in out['message']
    fix(ws, 'BEAT_01', {'why': 'x', 'options': [{'option_number': 1, 'events': [{'sub_clip_id': 'c9:S1', 'source_in_frame': 0, 'source_out_frame': 150}]}]})
    code, out, err = run(vw.cmd_options, opt(what='join-second-look'), capsys)
    assert code == 2 and 'c9:S1' in out['message']


def test_join_without_fixes_is_refused(ws, capsys):
    code, out, err = run(vw.cmd_options, opt(what='join-second-look'), capsys)
    assert code == 2 and 'out/second-look/' in out['message']


# ---------- the helpers ----------

def frontmatter(name):
    text = (PLUGIN / 'agents' / f'{name}.md').read_text(encoding='utf-8')
    head, body = text.split('\n---\n', 1)
    meta = dict(line.split(': ', 1) for line in head.strip('-\n').split('\n'))
    return meta, body


def test_the_two_helpers_run_on_opus_at_high_effort_with_few_tools():
    meta, body = frontmatter('vw-scene-review')
    assert meta['name'] == 'vw-scene-review' and meta['model'] == 'opus' and meta['effort'] == 'high' and meta['tools'] == 'Read, Write' and meta['description']
    for needle in ('work/options/scenes/', 'out/second-look/', 'what the words say', 'better piece', 'action ends', 'no change'):
        assert needle in body, needle
    meta, body = frontmatter('vw-plan-gaps')
    assert meta['name'] == 'vw-plan-gaps' and meta['model'] == 'opus' and meta['effort'] == 'high' and meta['tools'] == 'Read, Write'
    assert 'out/plan-gaps/' in body and 'out/plan-base.json' in body and 'never another helper' in body and 'new_elements' in body


def test_the_guard_lets_only_the_two_named_helpers_run(tmp_path):
    guard_active(tmp_path)
    for name in ('vw:vw-scene-review', 'vw:vw-plan-gaps', 'vw-scene-review'):
        assert guard('Agent', {'subagent_type': name, 'prompt': 'BEAT_01'}, tmp_path)[0] == 0, name
    for inp in ({'subagent_type': 'general-purpose', 'prompt': 'x'}, {'prompt': 'x'}):
        assert guard('Agent', inp, tmp_path)[0] == 2 and guard('Task', inp, tmp_path)[0] == 2


# ---------- the retired ways ----------

def test_the_retired_records_and_planning_are_refused_with_the_new_way(monkeypatch, capsys):
    monkeypatch.setattr(vw, 'write', lambda *a, **k: pytest.fail('nothing is sent'))
    code, out, err = run(vw.cmd_options, opt(what='record', quote='yes'), capsys)
    assert code == 2 and out['message'] == vw.RETIRED['options record']
    assert out['message'] == 'The separate options approval is retired: answering the first slide approves the options.'
    code, out, err = run(vw.cmd_first_cut, argparse.Namespace(what='record', quote='yes'), capsys)
    assert code == 2 and out['message'] == 'The separate first-cut record is retired: the first cut is recorded with the master (`vw master record`).'
    a = vw.build_parser().parse_args(['planning', 'prepare', '--file', 'x'])
    with pytest.raises(SystemExit) as exc:
        a.fn(a)
    assert exc.value.code == 2 and 'vw options' in json.loads(capsys.readouterr()[0])['message']
    assert 'def cmd_planning' not in (PLUGIN / 'scripts' / 'vw.py').read_text(encoding='utf-8')


# ---------- the command text ----------

def test_the_command_text_points_to_the_steps_and_drops_the_old_ways():
    assert '**Planning**' not in COMMAND and 'vw planning' not in COMMAND and 'planning (version 1)' not in COMMAND
    options = next(line for line in COMMAND.split('\n') if line.startswith('**Options and master**'))
    assert 'remains for an explicit approval' not in options and 'backup are 2 and 3' not in options and 'design/21' not in options
    assert 'the steps name the flags to act on' in options and 'act on R5, B1' not in options   # P10
    assert '`vw options second-look`' in options and '`vw-scene-review`' in options and 'join-second-look' in options
    assert '2-2' in options and 'its parts decide it; a trim if wanted' in options and 'a clip reused in another scene' in options and 'procedure versions 2 and 3' not in options
    assert 'vw-scene-review' in COMMAND and 'vw-plan-gaps' in COMMAND
