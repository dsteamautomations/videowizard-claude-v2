"""Fix set phase 3 (19 Nov 2026) on the plugin. A2.1: the guard lets the `vw-still-prompts` helper through. M7: the served text's example of
the still batch file, sent by the tool itself, reaches the server with every field as text and the route's own model takes it. A3.4: a finished
drawing that comes with the next decision is shown first. M6: the open-defect refusal ends with the next step."""
import json
import os
import re
import sys
import uuid

import pytest

from conftest import PLUGIN, REPO, run_hook
from test_visuals_cli import args, harness, run   # noqa: F401  (harness is a fixture)
import vw


def test_the_guard_allows_the_still_prompts_helper(tmp_path):
    for helper in ('vw:vw-still-prompts', 'vw-still-prompts'):
        assert run_hook('guard.py', {'tool_name': 'Agent', 'tool_input': {'subagent_type': helper, 'prompt': 'IM1, IM2'}}, tmp_path)[0] == 0, helper
    text = (PLUGIN / 'agents' / 'vw-still-prompts.md').read_text(encoding='utf-8')
    assert text.startswith('---\nname: vw-still-prompts\n') and 'tools: Read, Write\nmodel: opus\neffort: high\n---\n' in text


def test_m7_the_example_of_the_batch_file_is_sent_with_every_field_as_text_and_the_route_takes_it(harness, monkeypatch, capsys):
    ws, _ = harness
    stage = next(s for s in json.loads((REPO / 'server' / 'procedures' / 'v3.json').read_text(encoding='utf-8'))['stages'] if s['name'] == 'visuals')
    later = next(p['text'] for p in stage['parts'] if p['name'] == 'later')
    example = re.search(r'`(\[\{"element": .*?\}\])`', later).group(1)
    assert example in (PLUGIN / 'agents' / 'vw-still-prompts.md').read_text(encoding='utf-8')   # the helper is shown the same file
    (ws / 'out' / 'images.json').write_text(example, encoding='utf-8')
    sent = []
    monkeypatch.setattr(vw, 'request', lambda method, path, **kw: (sent.append(kw['json']) or {'reference_id': f'R{len(sent)}'}, 0))
    code, out, err = run(args(what='image', file='out/images.json'), capsys)
    assert code == 0 and out['queued'] == ['R1'] and len(sent) == 1
    body = sent[0]
    assert all(isinstance(body[k], str) and body[k] for k in ('element_id', 'name', 'kind', 'subject', 'prompt', 'shot_id')), body
    os.environ.setdefault('VW2_DATABASE_URL', '')   # the server's settings load without a database, as in its unit tests
    sys.path.insert(0, str(REPO / 'server'))
    from app.main import ImageGenerate   # the route's own model
    took = ImageGenerate(**{**body, 'request_id': uuid.UUID(body['request_id'])})
    assert (took.element_id, took.kind, took.shot_id) == ('E1', 'keyframe', 'S1')
    with pytest.raises(Exception, match='element_id'):   # the first call of the run: a row whose fields were not text
        ImageGenerate(**{**body, 'request_id': uuid.UUID(body['request_id']), 'element_id': None, 'subject': None, 'prompt': None})


ITEM = {'id': 'question:IM1', 'kind': 'question', 'position': '1 of 1 waiting', 'question': 'IM1: which wall is shown?', 'ask': 'Which wall is shown?',
        'buttons': [{'label': 'The north wall', 'choice': 'c1'}], 'how': 'HOW', 'show': []}
SHOW = [{'key': 'run-1/takes/job-7.mp4', 'name': 'MO1-drawing.mp4', 'say': 'MO1: made and checked, no notes. You judge it on the page with the others.'}]


def test_a34_a_finished_drawing_that_comes_with_a_decision_is_shown_first(harness, monkeypatch, capsys):
    got = []
    monkeypatch.setattr(vw, '_download', lambda m, key, rel, expect=None: got.append((key, rel)) or rel)
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: {'item': dict(ITEM), 'show': SHOW})
    code, out, err = run(args(what='next', one=False), capsys)
    assert code == 0 and got == [('run-1/takes/job-7.mp4', 'work/chat/MO1-drawing.mp4')]
    assert err.startswith('First show these finished drawings, each with its line, and ask nothing about them: work/chat/MO1-drawing.mp4: MO1: made and checked, no notes. '
                          'You judge it on the page with the others.. Then: 1 of 1 waiting. Post `message` as it is, then ask `ask`: "Which wall is shown?"')
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: {'item': dict(ITEM)})
    assert run(args(what='next', one=False), capsys)[2].startswith('1 of 1 waiting.')   # nothing finished: the line as before
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: {'item': None, 'working': ['Drawn graphics: 1 made and checked.'], 'say_last': 'Nothing is needed from you now.', 'show': SHOW})
    assert run(args(what='next', one=False), capsys)[2].startswith('Show these files, each with its line, and ask nothing: work/chat/MO1-drawing.mp4: ')   # with nothing waiting: as before


def test_m6_the_open_defect_refusal_ends_with_the_next_step(capsys):
    with pytest.raises(SystemExit) as exc:
        vw.finish({'action': 'refused', 'status': 409, 'code': 'DEFECT_OPEN', 'defect': 7, 'message': 'defect 7 is open on this run'}, 2)
    err = capsys.readouterr()[1]
    assert exc.value.code == 2 and err.strip().endswith('Do not send this call again now: tell the operator, and send it once the builder says the defect is fixed.')
