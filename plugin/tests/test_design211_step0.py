"""design/211, step 0: the tool knows the new words and flags and says each is not built yet; the guard knows the two new helpers; the
shared fixture can be imported from here."""
import sys

from conftest import PLUGIN, REPO, run_hook
from test_visuals_cli import args, harness, run   # noqa: F401 (harness is a fixture)
import vw


def test_the_new_words_and_their_flags():
    assert {'digest', 'trial', 'look'} <= set(vw.VISUALS_WHAT)
    assert vw.VISUALS_FLAGS['digest'] == set() and vw.VISUALS_FLAGS['trial'] == {'file', 'element', 'clip', 'at'} and vw.VISUALS_FLAGS['look'] == {'file'}
    assert {'rest', 'rewrite', 'looks'} <= vw.VISUALS_FLAGS['round']
    assert vw.visuals_flags_refused(args(what='digest', file='x.json')) == 'vw visuals digest does not take --file; nothing was sent.'
    assert vw.visuals_flags_refused(args(what='round', rest=True)) == '' and vw.visuals_flags_refused(args(what='page', looks=True)).startswith('vw visuals page does not take --looks')


def test_each_new_command_says_it_is_not_built_and_sends_nothing(harness, monkeypatch, capsys):
    sent = []
    monkeypatch.setattr(vw, 'write', lambda *a, **k: sent.append(a) or {})
    monkeypatch.setattr(vw, 'call', lambda *a, **k: sent.append(a) or {})
    for kw in ({'what': 'digest'}, {'what': 'trial', 'file': 'work/t.json'}, {'what': 'look', 'file': 'work/l.json'},
               {'what': 'round', 'rest': True, 'quote': 'make them'}, {'what': 'round', 'rewrite': 'out/round-rewrites.json'}, {'what': 'round', 'looks': True}):
        code, out, _ = run(args(**kw), capsys)
        assert code == 2 and 'not built yet (design/211' in out['message'], kw
    assert sent == []


def test_the_guard_knows_the_two_helpers_and_their_files_name_them(tmp_path):
    for helper in ('vw:vw-reference-finder', 'vw-reference-finder', 'vw:vw-set-look', 'vw-set-look'):
        assert run_hook('guard.py', {'tool_name': 'Agent', 'tool_input': {'subagent_type': helper, 'prompt': 'PAN'}}, tmp_path)[0] == 0, helper
    assert run_hook('guard.py', {'tool_name': 'Agent', 'tool_input': {'subagent_type': 'vw-finder', 'prompt': 'PAN'}}, tmp_path)[0] == 2
    for name in ('vw-reference-finder', 'vw-set-look'):
        text = (PLUGIN / 'agents' / f'{name}.md').read_text(encoding='utf-8')
        assert text.startswith(f'---\nname: {name}\n') and 'tools: Read, Write, Bash\nmodel: opus\neffort: high\n---\n' in text


def test_the_shared_fixture_is_plain_data():
    sys.path.insert(0, str(REPO / 'server' / 'unit'))
    import d211_fixture as F
    assert F.session('2')['round']['v'] == 2 and 'v' not in F.older_session()['round'] and len(F.plan()['elements']) == 8
