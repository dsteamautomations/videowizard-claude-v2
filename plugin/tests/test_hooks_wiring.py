"""hooks.json is the wiring; a typo there switches the guard off silently (the article's first failure mode). So the
wiring is tested, not only the guard function (design/34 1.12)."""
import json
import py_compile

from conftest import PLUGIN


def test_hooks_json_wires_guard_and_remind():
    doc = json.loads((PLUGIN / 'hooks' / 'hooks.json').read_text(encoding='utf-8'))
    pre = doc['hooks']['PreToolUse']
    assert len(pre) == 1 and 'matcher' not in pre[0]   # design/37 2.4: every tool goes through the guard
    assert pre[0]['hooks'][0]['type'] == 'command' and 'hooks/guard.py' in pre[0]['hooks'][0]['command']
    submit = doc['hooks']['UserPromptSubmit']
    assert len(submit) == 1 and 'matcher' not in submit[0]
    assert submit[0]['hooks'][0]['type'] == 'command' and 'hooks/remind.py' in submit[0]['hooks'][0]['command']
    for entry in pre + submit:
        for h in entry['hooks']:
            name = h['command'].split('/hooks/')[1].rstrip('"')
            assert (PLUGIN / 'hooks' / name).is_file(), name
            py_compile.compile(str(PLUGIN / 'hooks' / name), doraise=True)


def test_every_plugin_script_compiles():
    for f in PLUGIN.rglob('*.py'):
        if 'tests' in f.parts:
            continue
        py_compile.compile(str(f), doraise=True)
