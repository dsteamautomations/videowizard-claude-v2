"""Release 3, E1 (c): a question the assistant asks with the question tool, outside any server item, already becomes a `question` line of the
run's log in the visuals stage (design/192, extended to the visuals stage by design/221 row 22): the guard calls `asked.log` before the tool,
`vw log --kind question` keeps the entry in the text stages and the visuals stage. Nothing was changed here: these tests prove it."""
import argparse

import pytest

import asked
import vw


def test_the_hook_reads_the_question_before_the_tool_and_the_answer_after_it():
    q = {'hook_event_name': 'PreToolUse', 'tool_name': 'AskUserQuestion', 'tool_input': {'questions': [{'question': 'Which logo closes the film?'}, {'question': 'Fixed camera?'}]}}
    assert asked.entry(q) == ('question', 'Which logo closes the film? | Fixed camera?')
    a = {'hook_event_name': 'PostToolUse', 'tool_name': 'AskUserQuestion', 'tool_input': {}, 'tool_response': {'answers': {'Which logo closes the film?': 'The agency logo'}}}
    assert asked.entry(a) == ('answer', 'Which logo closes the film? -> The agency logo')


@pytest.mark.parametrize('stage, kept', [('visuals', True), ('brief', True), ('voice', False)])
def test_vw_log_keeps_a_question_in_the_visuals_stage(monkeypatch, stage, kept):
    sent = []
    monkeypatch.setattr(vw, 'active', lambda: {'run_id': 'run-1', 'code': 'VW-9'})
    monkeypatch.setattr(vw, 'call', lambda method, path, wait=None, **kw: {'stage': stage})
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: sent.append((path, body)) or {'logged': True})
    with pytest.raises(SystemExit) as exc:
        vw.cmd_log(argparse.Namespace(kind='question', text=['Which', 'logo', 'closes', 'the', 'film?'], show=False, about=None, rule=None))
    assert exc.value.code == 0
    assert sent == ([('/api/runs/run-1/log', {'text': 'Which logo closes the film?', 'kind': 'question'})] if kept else [])
