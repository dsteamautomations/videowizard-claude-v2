"""design/132 on the plugin: the guide puts the editor's package before the assembly, and the last `vw visuals record` names it as the next step."""
from conftest import PLUGIN
from test_visuals_cli import args, harness, run  # noqa: F401  (the fixture rides along)
import vw


def test_the_guide_puts_the_package_before_the_assembly():
    text = (PLUGIN / 'commands' / 'vw.md').read_text(encoding='utf-8')
    section = text[text.index('**Assembly and delivery**'):]
    assert section.index('`vw delivery bundle`') < section.index('`vw assembly prepare`')
    assert '`vw delivery bundle` again (the full package with the approved film)' in section


def test_the_last_record_names_the_package(harness, monkeypatch, capsys):
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: {'recorded': ['G2'], 'skipped': {}, 'next': "`vw delivery bundle` (the editor's package, before the assembly)"})
    code, out, err = run(args(what='record', gaps=['all'], quote='yes'), capsys)
    assert code == 0 and "next `vw delivery bundle` (the editor's package" in err
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: {'recorded': ['G1'], 'skipped': {}})   # an older server: the old hint
    code, out, err = run(args(what='record', gaps=['all'], quote='yes'), capsys)
    assert code == 0 and 'next `vw next`' in err
