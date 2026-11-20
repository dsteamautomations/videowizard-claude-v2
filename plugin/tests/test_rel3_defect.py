"""Release 3, C6 (SK, 20 Nov 2026): `vw defect` names the shot the defect is about (`--shot`), the server then holds only that shot; the
refusal of a held write is said in the server's own words (what is held, what goes on); the next line says what each open defect holds."""
import argparse

import pytest

import vw


def test_vw_defect_sends_the_shot_only_when_one_is_named(ws, monkeypatch, capsys):
    sent = []
    monkeypatch.setattr(vw, 'active', lambda: {'run_id': 'run-1', 'code': 'VW-9'})
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: sent.append((path, body)) or {'ticket': 7, 'holds': {'shot': 'S2'}})
    with pytest.raises(SystemExit):
        vw.cmd_defect(argparse.Namespace(stage='visuals', error='the brief of S2 is refused', log=None, shot='S2'))
    assert sent == [('/api/runs/run-1/defects', {'stage': 'visuals', 'error': 'the brief of S2 is refused', 'log_excerpt': '', 'shot': 'S2'})]
    assert 'Defect filed. It holds shot S2 only: go on with everything else.' in capsys.readouterr()[1]
    sent.clear()
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: sent.append((path, body)) or {'ticket': 8, 'holds': {'stage': 'visuals'}})
    with pytest.raises(SystemExit):
        vw.cmd_defect(argparse.Namespace(stage=None, error='nothing uploads', log=None, shot=None))
    assert sent[0][1] == {'stage': None, 'error': 'nothing uploads', 'log_excerpt': ''}        # no shot named: the body an older server takes
    err = capsys.readouterr()[1]
    assert 'Defect filed. It holds the visuals step: tell the operator the ticket number and stop; the builder takes it from here.' in err
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: {'ticket': 9})              # an older server: it says nothing of what is held
    with pytest.raises(SystemExit):
        vw.cmd_defect(argparse.Namespace(stage=None, error='x', log=None, shot=None))
    assert 'Defect filed. Tell the operator the ticket number and stop; the builder takes it from here.' in capsys.readouterr()[1]


def test_the_command_takes_the_shot_and_its_help_says_what_it_holds():
    a = vw.build_parser().parse_args(['defect', '--error', 'x', '--shot', 'S2'])
    assert a.shot == 'S2' and vw.build_parser().parse_args(['defect', '--error', 'x']).shot is None
    assert vw.DEFECT_HELP == ('File a defect for the builder. Name the shot it is about (--shot S): the server then holds only that shot and the rest of the run '
                              'goes on. With no shot the defect holds the whole step (--stage, else the step the run is in).')


def test_a_held_write_is_refused_in_the_servers_words(capsys):
    said = ('defect 7 is open on this run and holds shot S2 only; the rest of the run goes on. Do not send this call again now: tell the operator, go on with '
            'the other shots, and send it once the builder says the defect is fixed.')
    with pytest.raises(SystemExit) as exc:
        vw.finish({'action': 'refused', 'status': 409, 'code': 'DEFECT_OPEN', 'defect': 7, 'holds': {'shot': 'S2'}, 'message': said}, 2)
    err = capsys.readouterr()[1]
    assert exc.value.code == 2 and said in err and 'Nothing more can be recorded' not in err
    with pytest.raises(SystemExit):   # an older server (no `holds`): the sentence as before
        vw.finish({'action': 'refused', 'status': 409, 'code': 'DEFECT_OPEN', 'defect': 7, 'message': 'defect 7 is open on this run'}, 2)
    assert 'A defect is open on this run (7); the builder is on it. Nothing more can be recorded until it is fixed.' in capsys.readouterr()[1]


def test_the_next_line_says_what_each_open_defect_holds():
    nxt = {'stage': 'visuals', 'open_defects': [7, 8, 3], 'held': [{'defect': 7, 'shot': 'S2'}, {'defect': 8, 'stage': 'visuals'}, {'defect': 3}]}
    assert vw.next_line(nxt).endswith(' · defect 7 open (holds shot S2 only), defect 8 open (holds the visuals step), defect 3 open (holds every step)')
    assert vw.next_line({'stage': 'brief', 'open_defects': [7]}).endswith(' · defect 7 open')   # an older server
