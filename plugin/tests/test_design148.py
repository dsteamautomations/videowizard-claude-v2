"""design/148 Set A on the plugin: A2 `plan-join` names the new things still to complete (and still writes the plan); A3 the guard lets the
plugin's helpers hand back their report, and still blocks a message to a helper."""
from conftest import run_hook
from test_design124_c6_c9 import gap, joined, write_parts
from test_visuals_cli import args, harness, run   # noqa: F401 (harness is a fixture)


def test_plan_join_names_the_new_things_still_to_complete(harness, capsys):
    ws, _ = harness
    write_parts(ws, {'a.json': {'gaps': [gap('G1', 'E1', 'N2'), gap('G2', 'N2'), gap('G3', 'N3')],
                                'new_elements': [{'id': 'N2', 'name': 'Lorry driver'}, {'id': 'N3', 'name': 'Water drum', 'kind': 'object', 'identity': 'representative', 'requirements': 'r'}]}})
    code, out, err = run(args(what='plan-join', base='out/plan-base.json', gaps=['out/plan-gaps/']), capsys)
    assert code == 0 and [e['id'] for e in joined(ws)['elements']] == ['E1', 'N2', 'N3']
    assert out['incomplete'] == ['N2']
    assert '1 new thing needs kind, identity and requirements before check: N2' in err and 'vw visuals check' in err


def test_plan_join_says_nothing_when_every_new_thing_is_complete(harness, capsys):
    ws, _ = harness
    write_parts(ws, {'a.json': {'gaps': [gap('G1'), gap('G2'), gap('G3')]}})
    code, out, err = run(args(what='plan-join', base='out/plan-base.json', gaps=['out/plan-gaps/']), capsys)
    assert code == 0 and out['incomplete'] == [] and 'need' not in err


def test_the_guard_lets_a_helper_hand_back_and_still_blocks_a_message_to_one(tmp_path):
    assert run_hook('guard.py', {'tool_name': 'SubagentHandback', 'tool_input': {'result': 'gaps-02.json written'}}, tmp_path)[0] == 0
    code, _, err = run_hook('guard.py', {'tool_name': 'SendMessage', 'tool_input': {'to': 'helper', 'message': 'finish'}}, tmp_path)
    assert code == 2 and 'SendMessage' in err
