"""design/204: the treatment answered on a Claude artifact page. The guard lets the operator's assistant publish the plugin's one page and read
and write that page's data from files inside the run folder, and nothing else; the page file holds what the design asks of it."""
from conftest import PLUGIN, run_hook

PAGE = PLUGIN / 'pages' / 'decisions.html'


def guard(tool, tool_input, cwd):
    code, _, err = run_hook('guard.py', {'tool_name': tool, 'tool_input': tool_input}, cwd, None)
    return code, err


def active(tmp_path):
    runs = tmp_path / 'runs'
    (runs / 'VW-3' / 'work' / 'page').mkdir(parents=True)
    (runs / '.active').write_text('VW-3')
    return runs / 'VW-3' / 'work' / 'page'


def test_only_the_plugins_decisions_page_can_be_published(tmp_path):
    folder = active(tmp_path)
    assert guard('Artifact', {'file_path': str(PAGE), 'title': 'VideoWizard decisions VW-3', 'capabilities': {'db': {}}}, tmp_path)[0] == 0
    assert guard('Artifact', {'action': 'publish', 'file_path': str(PAGE)}, tmp_path)[0] == 0
    assert guard('Artifact', {'action': 'open', 'url': 'https://claude.ai/artifact/x'}, tmp_path)[0] == 0
    for bad in ({'file_path': str(folder / 'other.html')}, {'file_path': str(tmp_path / 'x.html')}, {'action': 'delete', 'url': 'https://claude.ai/artifact/x'},
                {'action': 'list'}, {'file_path': str(PAGE), 'files': {'a.js': 'a.js'}}, {'file_path': str(PAGE), 'asset': True}, {}):
        code, err = guard('Artifact', bad, tmp_path)
        assert code == 2 and 'decisions page' in err, bad


def test_a_round_is_written_from_its_file_inside_the_run_folder(tmp_path):
    folder = active(tmp_path)
    ok = {'action': 'set', 'url': 'https://claude.ai/artifact/x', 'collection': 'rounds', 'doc_id': 'r1', 'file_path': str(folder / 'r1.json')}
    assert guard('ArtifactData', ok, tmp_path)[0] == 0
    assert guard('ArtifactData', {**ok, 'file_path': str(tmp_path / 'elsewhere.json')}, tmp_path)[0] == 2
    typed = {k: v for k, v in ok.items() if k != 'file_path'}
    code, err = guard('ArtifactData', {**typed, 'data': {'lines': []}}, tmp_path)
    assert code == 2 and 'never type' in err
    assert guard('ArtifactData', {**ok, 'data': {'x': 1}}, tmp_path)[0] == 2


def test_the_answers_are_read_into_the_run_folder_and_nothing_is_deleted_or_updated(tmp_path):
    folder = active(tmp_path)
    read = {'action': 'list', 'url': 'https://claude.ai/artifact/x', 'collection': 'rounds/r1/answers', 'out_dir': str(folder / 'answers')}
    assert guard('ArtifactData', read, tmp_path)[0] == 0
    assert guard('ArtifactData', {k: v for k, v in read.items() if k != 'out_dir'}, tmp_path)[0] == 0
    assert guard('ArtifactData', {**read, 'out_dir': str(tmp_path / 'out')}, tmp_path)[0] == 2
    for action in ('delete', 'update', 'batch', 'str_replace', 'query', 'profiles'):
        assert guard('ArtifactData', {'action': action, 'url': 'https://claude.ai/artifact/x'}, tmp_path)[0] == 2, action


def test_without_an_active_run_the_page_data_is_blocked(tmp_path):
    assert guard('ArtifactData', {'action': 'list', 'url': 'x', 'collection': 'rounds'}, tmp_path)[0] == 2


def test_the_page_file_holds_what_the_design_asks():
    html = PAGE.read_text(encoding='utf-8')
    assert html.lstrip().startswith('<title>') and '<html' not in html and '<body' not in html   # the page content only; the skeleton is added at publish
    for needed in ("claude.use('db')", "collection('rounds')", 'const MAX=2000', "setAttribute('maxlength','2000')", 'Undo my answer', 'Reopen', 'Changed as you asked', 'say <strong>done</strong>',
                   'prefers-color-scheme: dark', 'textContent'):
        assert needed in html, needed
    assert 'innerHTML' not in html   # text only ever goes in as text
