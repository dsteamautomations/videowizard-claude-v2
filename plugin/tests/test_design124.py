"""design/124 A3 decision 5 and the A4 fix-now texts in the chat tool: the open pictures counted for both picture AIs, the rejection's next step said
by the server alone, a person's sheet from words, the elements line in the order of the sources, the continuity request without 'the two frames',
and no change-history label in the tool's own messages."""
import pytest

import vw
from test_visuals_cli import args, harness, jobs_answer, run   # noqa: F401 (harness is a fixture)


def test_status_counts_open_pictures_for_either_picture_ai(harness, monkeypatch, capsys):
    monkeypatch.setattr(vw, 'call', lambda method, path, wait=None, **kw: jobs_answer(('j1', 'r1', 'gemini-image', 'running'), ('j2', 'r2', 'openai', 'queued'), ('j3', 'VS1', 'video', 'ready')))
    code, out, err = run(args(), capsys)
    assert code == 0 and '2 images open; 1 ready' in err


def test_reject_says_only_the_servers_next_step(harness, monkeypatch, capsys):
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: {'id': 'W1', 'kind': 'web', 'status': 'rejected', 'next': "Rejected: the next search or frame comes from the operator's words."})
    code, out, err = run(args(what='reject', ref='W1', notes='wrong', quote='No.'), capsys)
    assert code == 0 and 'end image' not in err and "operator's words" in err


def test_the_round_and_pick_lines_make_a_persons_sheet_from_words(harness, monkeypatch, capsys):
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: {'search_id': 's1', 'references': [{'id': 'r1'}]})
    code, out, err = run(args(what='pick', search='s1', n='1', quote='This one.'), capsys)
    assert code == 0 and "a person's from words" in err and 'design/' not in err


def test_the_elements_line_names_the_operators_picture_then_google_on_their_yes(harness, monkeypatch, capsys):
    monkeypatch.setattr(vw, 'call', lambda method, path, **kw: {'elements': [{'id': 'E1', 'name': 'Kadapari'}], 'matches': {}})
    code, out, err = run(args(what='elements'), capsys)
    assert code == 0 and "the operator's own picture (`supply`)" in err and 'Google on their yes' in err


def test_the_continuity_refusal_speaks_of_the_shot_not_two_frames(harness, capsys):
    code, out, err = run(args(what='prepare-take', shot='VS1', start='R1', motion='pours', subject=['E1="pours water"']), capsys)
    assert code == 2 and 'two frames' not in out['message'] and 'through the shot' in out['message']


def test_nothing_fits_carries_no_label(harness, monkeypatch, capsys):
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: {})
    code, out, err = run(args(what='nothing-fits', search='s1', reason='wrong tool'), capsys)
    assert code == 0 and 'design/' not in err
