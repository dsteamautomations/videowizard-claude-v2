"""Fix set phase 1 (B3, 19 Nov 2026) on the plugin: the still's rule list the server gives at the upload is written beside rules.md for the still's
checker, and taken away again when the next upload has none (the animated project, or a rule list with no marks)."""
from test_design130 import margs, mrun, project
from test_visuals_cli import harness  # noqa: F401  (the fixture rides along)
import vw


def test_the_stills_rules_are_written_for_its_checker_and_removed_with_the_next_upload(harness, monkeypatch, capsys):
    ws, _ = harness
    project(ws)
    answer = {'sha256': 'b' * 64, 'next': 'Still stored.', 'still': True, 'still_rules': ['must: The block rests on the rods.', 'must: There are four rods.']}
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: answer)
    code, _, _ = mrun(margs(what='upload', shot='MO1', still=True), capsys)
    assert code == 0
    assert (ws / 'work/motion/MO1/rules-still.md').read_text(encoding='utf-8') == '1. must: The block rests on the rods.\n2. must: There are four rods.\n'
    answer.pop('still_rules')   # the animated project: its checker reads rules.md
    code, _, _ = mrun(margs(what='upload', shot='MO1'), capsys)
    assert code == 0 and not (ws / 'work/motion/MO1/rules-still.md').exists()
