"""design/211 part C: the tool's side of the page for a v2 reference round, with the server faked. `vw visuals page --record` passes on the
pictures the operator answered on their own (`pics`: "not this picture", "that is it") with the line's answer, and sends nothing new for
an answer without them, so an older server and an older round get what they got before."""
from test_design210b_own import begin, doc, record, sent
from test_visuals_cli import harness   # noqa: F401 (a fixture)


def test_the_picture_marks_travel_with_the_answer(harness, monkeypatch, capsys):
    ws, _ = harness
    calls = begin(ws, monkeypatch, capsys, [doc('ref:TROWEL', 'round1:TROWEL', 'approve', pics={'f-trowel-use': 'not'}),
                                           doc('ref:FAN', 'round1:FAN', 'pics', pics={'t0000000000c1': 'use'}),
                                           doc('refs:proposals', 'round1:all', 'accept_all')])
    rc, _out, _err = record(capsys)
    assert rc == 0 and sent(calls) == [
        {'line': 'l01', 'key': 'ref:TROWEL', 'item': 'round1:TROWEL', 'choice': 'approve', 'notes': '', 'pics': {'f-trowel-use': 'not'}},
        {'line': 'l02', 'key': 'ref:FAN', 'item': 'round1:FAN', 'choice': 'pics', 'notes': '', 'pics': {'t0000000000c1': 'use'}},
        {'line': 'l03', 'key': 'refs:proposals', 'item': 'round1:all', 'choice': 'accept_all', 'notes': ''}]


def test_an_answer_without_marks_is_sent_as_before_and_marks_are_bounded(harness, monkeypatch, capsys):
    ws, _ = harness
    many = {f'f{i}': 'not' for i in range(12)}
    calls = begin(ws, monkeypatch, capsys, [doc('ref:E1', 'round1:E1', 'approve', pics={}), doc('ref:E2', 'round1:E2', 'ignore', pics='x'), doc('ref:E3', 'round1:E3', 'pics', pics=many)])
    record(capsys)
    got = sent(calls)
    assert got[0] == {'line': 'l01', 'key': 'ref:E1', 'item': 'round1:E1', 'choice': 'approve', 'notes': ''} and 'pics' not in got[1]   # no new field where there is no mark
    assert len(got[2]['pics']) == 8 and all(v == 'not' for v in got[2]['pics'].values())                                           # at most 8, as the server takes
