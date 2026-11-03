"""design/149 Set B on the plugin: B7 the gap files are the master (`plan-join` refuses to overwrite a joined plan edited after the last join; `--rebuild`
drops the edits); B8 the helper brief carries the shape checklist; B9 the brief carries the principle that nothing in the frame vanishes."""
import json
import os
import time

from conftest import PLUGIN
from test_design124_c6_c9 import gap, joined, write_parts
from test_visuals_cli import args, harness, run   # noqa: F401 (harness is a fixture)


def join(capsys, **kw):
    return run(args(what='plan-join', base='out/plan-base.json', gaps=['out/plan-gaps/'], **kw), capsys)


def test_plan_join_refuses_to_overwrite_a_joined_plan_edited_by_hand_unless_rebuilt(harness, capsys):
    ws, _ = harness
    write_parts(ws, {'a.json': {'gaps': [gap('G1'), gap('G2'), gap('G3')]}})
    code, out, err = join(capsys)
    assert code == 0
    plan_file = ws / 'out' / 'visual-plan.json'
    doc = joined(ws)
    doc['gaps'][0]['intent'] = 'edited by hand after the join'
    plan_file.write_text(json.dumps(doc), encoding='utf-8')
    later = time.time() + 5
    os.utime(plan_file, (later, later))
    code, out, err = join(capsys)
    assert code == 2 and 'edited after the last join' in out['message'] and '--rebuild' in out['message']
    assert joined(ws)['gaps'][0]['intent'] == 'edited by hand after the join'   # untouched
    code, out, err = join(capsys, rebuild=True)
    assert code == 0 and joined(ws)['gaps'][0]['intent'] == 'i'   # rebuilt from the gap files


def test_plan_join_runs_again_when_a_gap_file_is_newer_than_the_joined_plan(harness, capsys):
    ws, _ = harness
    write_parts(ws, {'a.json': {'gaps': [gap('G1'), gap('G2'), gap('G3')]}})
    assert join(capsys)[0] == 0
    gap_file = ws / 'out' / 'plan-gaps' / 'a.json'
    gap_file.write_text(json.dumps({'gaps': [{**gap('G1'), 'intent': 'revised by the helper'}, gap('G2'), gap('G3')]}), encoding='utf-8')
    later = time.time() + 5
    os.utime(gap_file, (later, later))
    code, out, err = join(capsys)
    assert code == 0 and joined(ws)['gaps'][0]['intent'] == 'revised by the helper'


def test_the_helper_brief_carries_the_checklist_and_the_principle():
    text = (PLUGIN / 'agents' / 'vw-plan-gaps.md').read_text(encoding='utf-8')
    for phrase in ('Before you write, every shot and scene carries', '`outfit`', '`props`', '`groups`', '`changes`', '`drawing_spec`', '`states`', '`claims`', 'techniques', '`new_elements`',
                   '`return_of`', 'Nothing in the frame vanishes', 'container'):
        assert phrase in text, phrase
