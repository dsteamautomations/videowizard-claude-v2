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


def test_the_page_draws_a_plan_gaps_shots_as_a_table_and_each_offered_way():
    """design/206: the plan on the page: a gap's shots as a table under their totals, a gap offered two ways with each way's shots, a number that jumps to its block."""
    html = PAGE.read_text(encoding='utf-8')
    for needed in ('function shots(cols,src)', "if(line.table) body.appendChild(shots(line.cols,line))", '(line.ways||[]).forEach', "' (advised)'", 'table.shots thead{display:none}',
                   "td.setAttribute('data-l'", 'scrollIntoView', "indexOf('way:')===0", 'Saved on this page.'):
        assert needed in html, needed
    # design/207: a gap's plain lines (`line.warnings`) are drawn above its shots, as text
    assert html.index("line.warnings.forEach(x=>ul.appendChild(el('li',null,x)))") < html.index('if(line.table) body.appendChild(shots(line.cols,line))') and 'Read before you answer' in html


def test_the_page_can_play_a_sample_of_every_motion_style_the_server_holds():
    """design/205: "Show me" beside the motion style; a style file added on the server needs its sample here."""
    html = PAGE.read_text(encoding='utf-8')
    names = sorted(p.stem for p in (PLUGIN.parent / 'server' / 'motion_styles').glob('*.md'))
    assert len(names) == 8 and all(f'.stage.m-{n}>' in html for n in names), names
    assert "'Show me: '+st.title" in html and 'a rough sample' in html and 'prefers-reduced-motion' in html


def test_the_list_of_differences_is_folded_unless_the_operator_asked_for_the_change():
    """SK, 16 Nov 2026: 'Changed since you last saw it' confused; it is a folded line now, open only for a change the operator asked for."""
    html = PAGE.read_text(encoding='utf-8')
    assert "el('details','changed')" in html and 'c.open=!!line.asked' in html and "el('summary'" in html


def test_the_page_draws_a_drawings_parts_and_sizes_and_a_materials_facts_in_plain_words():
    """design/209: a spec line: what it is drawn as, its parts, how they sit, the sizes to confirm as a table, one muted line each for what is
    already confirmed and what is not known, a remark where a size differs; a recorded one folded; the line's own question."""
    html = PAGE.read_text(encoding='utf-8')
    for needed in ('function spec(line)', 'if(line.spec) body.appendChild(spec(line));', "'Drawn as: '+s.drawn_as", "list('Parts',s.parts)", "list('How they sit',s.sits)",
                   "grid(['Part','Measure','Size','From'],s.sizes,'sizes')", "'Already confirmed: '+s.confirmed", "'Not known, so no figure is shown: '+s.unknown", 's.differs.forEach',
                   "el(rec?'details':'div','group')", 'What you approved', "body.appendChild(el('p','totals',line.ask))", "a.choice==='yes'", 'function grid(cols,rows,kind)',
                   'wrap.appendChild(grid(cols,src.table))'):
        assert needed in html, needed
    assert '.open=true' not in html[html.index('function spec(line)'):html.index('const KINDS=')]   # a recorded line's content is closed until the operator opens it


def test_the_world_of_the_film_is_grouped_under_one_heading_per_kind():
    """SK, 16 Nov 2026: 'Not shown' was repeated on every row. The page groups the world's rows under one heading each, with the rules listed
    under it; people, places and things are grouped by kind; the block is read, not answered."""
    html = PAGE.read_text(encoding='utf-8')
    for needed in ('function world(rows)', "if(line.key==='world') body.appendChild(world(line.rows)); else", "Person:'People'", "label==='The graphic style'",
                   "el('details','group')", "return ['t-open','To read']", 'For reading only: nothing to answer here.'):
        assert needed in html, needed


def test_the_page_file_is_readable_before_it_is_published_and_nothing_else_of_the_plugin(tmp_path):
    """SK, 24 Nov 2026 (VW-25): the Claude app publishes a file only after reading it whole. The guard let the assistant publish the page and
    not read it, so no page was published and every step fell back to the chat. The page file alone is readable, with or without an active run;
    it is never writable, and no other file of the plugin outside skills/ is readable."""
    assert PAGE.is_file()
    assert guard('Read', {'file_path': str(PAGE)}, tmp_path)[0] == 0
    assert guard('Read', {'file_path': str(PAGE), 'offset': 800, 'limit': 700}, tmp_path)[0] == 0   # a large file is read in parts
    assert guard('Read', {'file_path': str(PAGE.parent / '..' / 'pages' / 'decisions.html')}, tmp_path)[0] == 0
    for tool in ('Write', 'Edit'):
        assert guard(tool, {'file_path': str(PAGE)}, tmp_path)[0] == 2, tool
    for other in (PAGE.parent / 'other.html', PAGE.parent, PLUGIN / 'scripts' / 'vw.py', PLUGIN / 'hooks' / 'guard.py'):
        assert guard('Read', {'file_path': str(other)}, tmp_path)[0] == 2, other
    assert guard('Grep', {'pattern': 'x', 'path': str(PAGE.parent)}, tmp_path)[0] == 2
