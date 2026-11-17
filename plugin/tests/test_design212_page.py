"""design/212: the tool's side of the new layout of the references step 1, with the server faked. The round file written for the page
carries the server's `layout` (how the page lays the step out) as it came; a step that has none gets none. The new choices of a line
(`use`, `set`, `fix`) travel with their picture marks as every answer does."""
import json

from test_design210_pictures import fake, with_pics
from test_design210b_own import begin, doc, record, sent
from test_visuals_cli import args, harness, run   # noqa: F401 (harness is a fixture)

LAYOUT = {'kind': 'things', 'made': 'Nothing is made until you say done in the chat.', 'help': 'How this works.'}


def round_doc(out):
    return json.loads(open(out['round_file'], encoding='utf-8').read())


def test_the_round_file_carries_the_layout_the_server_gives(harness, monkeypatch, capsys):
    fake(monkeypatch, lambda: {**with_pics('r1', 1, 2), 'layout': LAYOUT})
    rc, out, _err = run(args(what='page', record=False), capsys)
    assert rc == 0 and round_doc(out)['layout'] == LAYOUT


def test_a_step_with_no_layout_gets_none(harness, monkeypatch, capsys):
    fake(monkeypatch, lambda: with_pics('r1', 1, 2))
    rc, out, _err = run(args(what='page', record=False), capsys)
    assert 'layout' not in round_doc(out)


def test_the_new_choices_travel_with_their_picture_marks_and_words(harness, monkeypatch, capsys):
    ws, _ = harness
    calls = begin(ws, monkeypatch, capsys, [doc('ref:TROWEL', 'round1:TROWEL', 'use', pics={'f-trowel-use': 'not'}),
                                           doc('ref:FAN', 'round1:FAN', 'set', pics={'t0000000000c1': 'use'})])
    rc, _out, _err = record(capsys)
    assert rc == 0 and sent(calls) == [
        {'line': 'l01', 'key': 'ref:TROWEL', 'item': 'round1:TROWEL', 'choice': 'use', 'notes': '', 'pics': {'f-trowel-use': 'not'}},
        {'line': 'l02', 'key': 'ref:FAN', 'item': 'round1:FAN', 'choice': 'set', 'notes': '', 'pics': {'t0000000000c1': 'use'}}]
