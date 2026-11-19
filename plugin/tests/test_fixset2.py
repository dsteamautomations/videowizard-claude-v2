"""Fix set phase 2 (19 Nov 2026) on the plugin. A1.6: the rules of a later round, as the server gives them at the upload, are written beside
rules.md for the round's checker and taken away with the next upload that has none. A1.2: the other drawings' approved still end-frames that a
comparing rule is checked against are saved in the shot's folder, at the upload and with the brief."""
from test_design130 import margs, mrun, project
from test_visuals_cli import harness  # noqa: F401  (the fixture rides along)
import vw


def test_the_rounds_rules_are_written_for_its_checker_and_removed_with_the_next_upload(harness, monkeypatch, capsys):
    ws, _ = harness
    project(ws)
    answer = {'sha256': 'b' * 64, 'next': 'Project stored.', 'round_rules': ['must: There are four rods.', 'should: The leader lines do not cross.']}
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: answer)
    assert mrun(margs(what='upload', shot='MO1'), capsys)[0] == 0
    assert (ws / 'work/motion/MO1/rules-round.md').read_text(encoding='utf-8') == '1. must: There are four rods.\n2. should: The leader lines do not cross.\n'
    answer.pop('round_rules')   # a first round, or the brief changed: the checker reads rules.md
    assert mrun(margs(what='upload', shot='MO1'), capsys)[0] == 0 and not (ws / 'work/motion/MO1/rules-round.md').exists()


def test_the_frames_a_comparing_rule_is_checked_against_are_saved_at_the_upload_and_with_the_brief(harness, monkeypatch, capsys):
    ws, _ = harness
    project(ws)
    got = []
    monkeypatch.setattr(vw, '_download', lambda m, key, rel, expect=None: got.append((key, rel)) or rel)
    compare = [{'shot_id': 'MO2', 'key': 'run-1/visuals/motion/tools/s2/0.png'}]
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: {'sha256': 'b' * 64, 'next': 'Still stored.', 'still': True, 'compare': compare})
    assert mrun(margs(what='upload', shot='MO1', still=True), capsys)[0] == 0
    assert got == [('run-1/visuals/motion/tools/s2/0.png', 'work/motion/MO1/with-MO2/last-frame.png')]
    monkeypatch.setattr(vw, 'call', lambda method, path, **kw: {'brief': '# Brief', 'lines': {}, 'refs': [], 'compare': compare})
    assert mrun(margs(what='brief', shot='MO1'), capsys)[0] == 0
    assert got[-1] == ('run-1/visuals/motion/tools/s2/0.png', 'work/motion/MO1/with-MO2/last-frame.png')
