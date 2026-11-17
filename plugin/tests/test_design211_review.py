"""design/211, the review of 17 Nov 2026, the tool's side with the server faked: the status of a round made after the references step was
rebuilt is the server's sentence and no line of the tool's (N1); a thing left out, asked for again, prints the server's sentence (M5); the
two helper files say how to write a path and a command so the guard takes it the first time, the finder how to replace a kept frame, the
looker where the judging points are (N2, N10, S16)."""
from conftest import PLUGIN
from test_visuals_cli import args, harness, jobs_answer, run   # noqa: F401 (harness is a fixture)
import vw

DUE = 'The sets are back. Look at them before the operator does.'


def test_N1_the_status_of_a_v2_round_prints_the_servers_sentence_and_no_line_of_its_own(harness, monkeypatch, capsys):
    for at in (1, 'making', 'looking', 'rewrite', 2, 'complete'):
        st = {**jobs_answer(), 'round': {'pass': at, 'kept': True, 'v': 2, 'elements': {}}, 'round_due': DUE}
        monkeypatch.setattr(vw, 'call', lambda method, path, wait=None, st=st, **kw: st)
        err = run(args(), capsys)[2]
        assert DUE in err and 'reference round at pass' not in err and 'the approved sets are the references' not in err and 'the sets are being made, wait' not in err, at


def test_N1_the_status_of_an_older_round_prints_what_it_printed_before(harness, monkeypatch, capsys):
    st = {**jobs_answer(), 'round': {'pass': 'complete', 'kept': True, 'elements': {}}}
    monkeypatch.setattr(vw, 'call', lambda method, path, wait=None, **kw: st)
    assert 'reference round at pass complete: complete; the approved sets are the references' in run(args(), capsys)[2]


def test_M5_a_thing_left_out_and_asked_for_again_prints_the_servers_sentence(harness, monkeypatch, capsys):
    sent = []
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: sent.append((path.rsplit('/visuals', 1)[-1], body)) or {'element_id': 'FAN', 'aside': False, 'next': 'FAN is back in the round.', 'then': DUE})
    code, out, err = run(args(what='round', back='FAN'), capsys)
    assert code == 0 and sent == [('/round/aside', {'element_id': 'FAN', 'words': '', 'back': True})] and err.strip() == DUE
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: {'element_id': 'FAN', 'aside': False, 'next': 'FAN is back in the round.'})   # an older round: the tool's own line
    assert run(args(what='round', back='FAN'), capsys)[2].strip() == 'FAN is back in the round.'


def test_N10_the_helper_files_say_how_a_path_and_a_command_are_written():
    for name in ('vw-reference-finder.md', 'vw-set-look.md'):
        body = (PLUGIN / 'agents' / name).read_text(encoding='utf-8').split('---\n', 2)[2]
        assert "the run folder's full path and the tool's command line" in body and 'Read and write every file by its full path' in body, name
        assert 'as a call of its own' in body and 'nothing joined, piped or redirected' in body and '\r' not in body, name
    finder = (PLUGIN / 'agents' / 'vw-reference-finder.md').read_text(encoding='utf-8')
    assert "send the first frame's look again without `keep`" in finder
    looker = (PLUGIN / 'agents' / 'vw-set-look.md').read_text(encoding='utf-8')
    assert '`how.judge`' in looker and '`how.file`' in looker and '`how.may_show`' in looker and 'approved drawing' in looker and 'footage picture' in looker
    assert 'hands and forearms doing it' not in looker   # hands are allowed, never required: the server's words
