"""design/142 R1: `vw log` adds the assistant's entry to the run's decision log, or shows the whole log in work/decision-log.md."""

import vw
from test_visuals_cli import harness  # noqa: F401


def run(argv, capsys):
    a = vw.build_parser().parse_args(argv)
    try:
        a.fn(a)
        code = 0
    except SystemExit as exc:
        code = exc.code
    out = capsys.readouterr().out
    import json
    return code, json.loads(out) if out.strip() else {}


def test_an_entry_is_sent_with_its_rule_and_about(harness, monkeypatch, capsys):
    sent = {}
    monkeypatch.setattr(vw, 'write', lambda path, body, wait=None: (sent.update(path=path, **body) or {'logged': True}))
    code, out = run(['log', '--about', 'C0073', '--rule', 'no rule', 'dropped', 'for', 'the', 'eye-trace'], capsys)
    assert code == 0 and sent['path'].endswith('/log') and sent['text'] == 'dropped for the eye-trace' and sent['about'] == 'C0073' and sent['rule'] == 'no rule'


def test_an_empty_entry_is_refused(harness, capsys):
    assert run(['log'], capsys)[0] == 2


def test_show_writes_the_whole_log(harness, monkeypatch, capsys):
    monkeypatch.setattr(vw, 'call', lambda method, path, wait=None, **kw: {'markdown': '# Decision log: VW-9\n'})
    code, out = run(['log', '--show'], capsys)
    assert code == 0 and (vw.RUNS / 'VW-9' / 'work' / 'decision-log.md').read_text(encoding='utf-8').startswith('# Decision log')
