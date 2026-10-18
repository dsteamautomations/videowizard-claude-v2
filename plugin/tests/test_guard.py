"""The guard hook (design/34 1.11 sentinel, 1.12 reads), fed JSON on stdin as Claude Code does."""
from conftest import PLUGIN, REPO, run_hook

VW = PLUGIN / 'scripts' / 'vw.py'


def guard(tool, tool_input, cwd, runs=None):
    code, _, err = run_hook('guard.py', {'tool_name': tool, 'tool_input': tool_input}, cwd, runs)
    return code, err


def test_bash_only_vw(tmp_path):
    for cmd in ('gcloud logging read x', 'psql -c "select 1"', 'git status', 'python other.py', 'python vw.py next; rm -rf /'):
        code, err = guard('Bash', {'command': cmd}, tmp_path)
        assert code == 2 and err.strip(), cmd
    assert guard('Bash', {'command': f'python "{VW}" next'}, tmp_path)[0] == 0
    assert guard('Bash', {'command': f"python '{VW}' output --stage s1 --quote \"yes\""}, tmp_path)[0] == 0


def test_writes_only_inside_the_active_run(tmp_path):
    runs = tmp_path / 'runs'
    (runs / 'VW-3' / 'out').mkdir(parents=True)
    assert guard('Write', {'file_path': str(runs / 'VW-3' / 'out' / 'x.json')}, tmp_path)[0] == 2  # no .active
    (runs / '.active').write_text('VW-3')
    assert guard('Write', {'file_path': str(runs / 'VW-3' / 'out' / 'x.json')}, tmp_path)[0] == 0
    assert guard('Edit', {'file_path': str(runs / 'VW-3' / 'work' / 'y.txt')}, tmp_path)[0] == 0
    assert guard('Write', {'file_path': str(tmp_path / 'elsewhere.txt')}, tmp_path)[0] == 2
    assert guard('Write', {'file_path': str(REPO / 'plugin' / 'commands' / 'vw.md')}, tmp_path)[0] == 2
    assert guard('Write', {'file_path': str(runs / 'VW-4' / 'out' / 'x.json')}, tmp_path)[0] == 2


def test_reads_only_inside_the_active_run(tmp_path):
    """1.12: Read, Glob and Grep are gated like writes; the session token file is out of reach."""
    runs = tmp_path / 'runs'
    (runs / 'VW-3' / 'out').mkdir(parents=True)
    (runs / '.active').write_text('VW-3')
    home = tmp_path / '.vw2'
    home.mkdir()
    (home / 'session.json').write_text('{"token": "secret"}')
    code, err = guard('Read', {'file_path': str(home / 'session.json')}, tmp_path)
    assert code == 2 and 'inside' in err
    assert guard('Read', {'file_path': str(tmp_path / 'CLAUDE.md')}, tmp_path)[0] == 2
    assert guard('Read', {'file_path': str(runs / 'VW-3' / 'out' / 'intake.json')}, tmp_path)[0] == 0
    assert guard('Read', {'file_path': str(runs / 'VW-3' / 'work' / 'intake-numbered.md')}, tmp_path)[0] == 0
    assert guard('Glob', {'pattern': '**/*.json', 'path': str(runs / 'VW-3')}, tmp_path)[0] == 0
    assert guard('Glob', {'pattern': '**/*.json', 'path': str(tmp_path)}, tmp_path)[0] == 2
    assert guard('Grep', {'pattern': 'token', 'path': str(runs / 'VW-3' / 'out')}, tmp_path)[0] == 0
    code, err = guard('Grep', {'pattern': 'token'}, tmp_path)   # no path: would search the whole folder
    assert code == 2 and 'give a path' in err
    assert guard('Read', {'file_path': 'runs/VW-3/out/x.json'}, tmp_path)[0] == 0   # relative to cwd


def test_reads_need_an_active_run(tmp_path):
    (tmp_path / 'runs').mkdir()
    assert guard('Read', {'file_path': str(tmp_path / 'runs' / 'VW-3' / 'out' / 'x.json')}, tmp_path)[0] == 2


def test_sentinel_never_reaches_disk_or_a_command(tmp_path):
    """1.11: a Write, Edit or Bash call carrying the procedure sentinel is blocked, even inside the run folder."""
    runs = tmp_path / 'runs'
    (runs / 'VW-3' / 'out').mkdir(parents=True)
    (runs / '.active').write_text('VW-3')
    inside = str(runs / 'VW-3' / 'out' / 'notes.md')
    code, err = guard('Write', {'file_path': inside, 'content': 'VW-PROCEDURE — for the assistant only\n\nYou separate a script...'}, tmp_path)
    assert code == 2 and "builder's" in err
    assert guard('Edit', {'file_path': inside, 'old_string': 'a', 'new_string': 'see VW-PROCEDURE'}, tmp_path)[0] == 2
    assert guard('MultiEdit', {'file_path': inside, 'edits': [{'old_string': 'a', 'new_string': 'VW-PROCEDURE'}]}, tmp_path)[0] == 2
    assert guard('Bash', {'command': f'python "{VW}" output --stage intake --summary "VW-PROCEDURE"'}, tmp_path)[0] == 2
    assert guard('Write', {'file_path': inside, 'content': 'plain notes for the operator'}, tmp_path)[0] == 0


def test_guard_stands_down_in_the_builder_checkout():
    for cwd in (REPO, REPO / 'server', REPO.parent):
        assert guard('Bash', {'command': 'git status'}, cwd)[0] == 0, cwd
        assert guard('Write', {'file_path': str(REPO / 'README.md')}, cwd)[0] == 0, cwd
        assert guard('Read', {'file_path': str(REPO / 'README.md')}, cwd)[0] == 0, cwd


# ---------- design/37 2.4: the allow-list ----------

def active(tmp_path):
    runs = tmp_path / 'runs'
    (runs / 'VW-3' / 'out').mkdir(parents=True, exist_ok=True)
    (runs / '.active').write_text('VW-3')
    return runs


def test_connectors_browser_and_subagents_are_blocked(tmp_path):
    runs = active(tmp_path)
    for tool, inp in (('mcp__f9783728-2460-4ddc-ad0b-aabb93fd9f53__execute_sql', {'project_id': 'x', 'query': 'select 1'}),
                      ('mcp__57d87662-6036-43fc-a8ca-5d74f781cbfe__send_message', {'to': 'a@b'}),
                      ('mcp__Claude_Browser__navigate', {'url': 'https://8-234-82-225.sslip.io/connect'}),
                      ('mcp__claude-in-chrome__computer', {'action': 'left_click'}),
                      ('mcp__computer-use__app_click', {}),
                      ('mcp__ccd_session__start_session', {'title': 'x'}),
                      ('Agent', {'prompt': 'run git status'}), ('Task', {'prompt': 'x'}),
                      ('Workflow', {'script': 'x'}), ('SendMessage', {'to': 'x', 'message': 'y'}), ('CronCreate', {}), ('EnterWorktree', {}),
                      ('SomethingNew', {})):
        code, err = guard(tool, inp, tmp_path)
        assert code == 2 and 'not available to the operator assistant' in err, tool
    assert guard('Skill', {'skill': 'anthropic-skills:docs'}, tmp_path)[0] == 2
    assert guard('Skill', {'skill': 'vw:vw', 'args': 'what is next'}, tmp_path)[0] == 0


def test_questions_task_list_and_web_tools_are_allowed(tmp_path):
    active(tmp_path)
    for tool, inp in (('AskUserQuestion', {'questions': []}), ('TodoWrite', {'todos': []}), ('TodoRead', {}),
                      ('mcp__ccd_turn__update_plan', {'items': []}), ('mcp__ccd_turn__wrap_up', {'recap': 'x'}), ('mcp__ccd_view__show_pane', {}),
                      ('WebSearch', {'query': 'rat-trap bond'}), ('WebFetch', {'url': 'https://example.org', 'prompt': 'x'}), ('ToolSearch', {'query': 'select:WebSearch'})):
        assert guard(tool, inp, tmp_path)[0] == 0, tool


def test_blocked_calls_are_logged_and_allowed_calls_are_not(tmp_path):
    runs = active(tmp_path)
    log = runs / 'VW-3' / 'work' / 'guard.log'
    guard('Read', {'file_path': str(runs / 'VW-3' / 'out' / 'x.json')}, tmp_path)
    guard('WebSearch', {'query': 'x'}, tmp_path)
    assert not log.exists()
    guard('mcp__Claude_Browser__navigate', {'url': 'https://example.org/page'}, tmp_path)
    guard('Read', {'file_path': str(tmp_path / '.vw2' / 'session.json')}, tmp_path)
    guard('Bash', {'command': 'git status'}, tmp_path)
    guard('Write', {'file_path': str(runs / 'VW-3' / 'out' / 'n.md'), 'content': 'VW-PROCEDURE secret text'}, tmp_path)
    lines = log.read_text(encoding='utf-8').splitlines()
    assert len(lines) == 4
    assert ' · mcp__Claude_Browser__navigate · ' in lines[0] and lines[0].endswith('https://example.org/page')
    assert ' · Read · ' in lines[1] and 'session.json' in lines[1]
    assert ' · Bash · ' in lines[2] and lines[2].endswith('git status')
    assert ' · Write · ' in lines[3] and lines[3].endswith('(procedure text)') and 'secret' not in lines[3]
    for line in lines:
        assert line[:4].isdigit() and ' · Blocked' in line


def test_blocked_call_without_an_active_run_is_logged_at_the_runs_root(tmp_path):
    (tmp_path / 'runs').mkdir()
    guard('mcp__Claude_Browser__navigate', {'url': 'x'}, tmp_path)
    assert (tmp_path / 'runs' / 'guard.log').read_text(encoding='utf-8').count('\n') == 1
