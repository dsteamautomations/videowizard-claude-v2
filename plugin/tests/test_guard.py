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


def test_questions_task_list_and_tool_search_are_allowed_and_the_web_needs_a_yes(tmp_path):
    runs = active(tmp_path)
    for tool, inp in (('AskUserQuestion', {'questions': []}), ('TodoWrite', {'todos': []}), ('TodoRead', {}),
                      ('mcp__ccd_turn__update_plan', {'items': []}), ('mcp__ccd_turn__wrap_up', {'recap': 'x'}), ('mcp__ccd_view__show_pane', {}),
                      ('ToolSearch', {'query': 'select:WebSearch'})):
        assert guard(tool, inp, tmp_path)[0] == 0, tool
    assert guard('WebSearch', {'query': 'rat-trap bond'}, tmp_path)[0] == 2   # design/48 O.1: no recorded yes
    web_ok(runs)
    assert guard('WebSearch', {'query': 'rat-trap bond'}, tmp_path)[0] == 0 and guard('WebFetch', {'url': 'https://example.org', 'prompt': 'x'}, tmp_path)[0] == 0


def test_blocked_calls_are_logged_and_allowed_calls_are_not(tmp_path):
    runs = active(tmp_path)
    log = runs / 'VW-3' / 'work' / 'guard.log'
    guard('Read', {'file_path': str(runs / 'VW-3' / 'out' / 'x.json')}, tmp_path)
    guard('AskUserQuestion', {'questions': []}, tmp_path)
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


# ---------- design/48 O.1: the web gate ----------

def web_ok(runs, minutes_ago=0, about='the client product'):
    import json
    from datetime import datetime, timedelta, timezone
    (runs / 'VW-3' / 'work').mkdir(parents=True, exist_ok=True)
    at = (datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)).isoformat(timespec='seconds')
    (runs / 'VW-3' / 'work' / 'web-ok.json').write_text(json.dumps({'about': about, 'ok': 'yes, search', 'at': at, 'by': 'operator', 'calls': []}), encoding='utf-8')


def test_web_tools_need_the_operators_recorded_yes(tmp_path):
    import json
    runs = tmp_path / 'runs'
    (runs / 'VW-3' / 'work').mkdir(parents=True)
    (runs / '.active').write_text('VW-3')
    code, err = guard('WebSearch', {'query': 'rat trap bond'}, tmp_path)
    assert code == 2 and 'I am deviating from the usual procedure' in err and 'vw web --about' in err
    web_ok(runs)
    assert guard('WebSearch', {'query': 'rat trap bond'}, tmp_path)[0] == 0
    assert guard('WebFetch', {'url': 'https://example.org/bond', 'prompt': 'x'}, tmp_path)[0] == 0
    ok = json.loads((runs / 'VW-3' / 'work' / 'web-ok.json').read_text(encoding='utf-8'))
    assert [c['tool'] for c in ok['calls']] == ['WebSearch', 'WebFetch'] and ok['calls'][0]['query'] == 'rat trap bond'
    log = (runs / 'VW-3' / 'work' / 'guard.log').read_text(encoding='utf-8').splitlines()
    assert any(' · WebSearch · allowed (the client product) · rat trap bond' in l for l in log) and any(' · WebFetch · allowed' in l for l in log)
    web_ok(runs, minutes_ago=11)
    code, err = guard('WebSearch', {'query': 'again'}, tmp_path)
    assert code == 2 and 'yes' in err


def test_web_tools_are_blocked_without_an_active_run(tmp_path):
    (tmp_path / 'runs').mkdir()
    assert guard('WebSearch', {'query': 'x'}, tmp_path)[0] == 2


# ---------- design/48 O.4: the tool's own records are read-only ----------

def test_the_tools_own_records_are_read_only(tmp_path):
    runs = tmp_path / 'runs'
    (runs / 'VW-3' / 'work').mkdir(parents=True)
    (runs / 'VW-3' / 'out').mkdir()
    (runs / '.active').write_text('VW-3')
    for target in (runs / 'VW-3' / 'work' / 'guard.log', runs / 'VW-3' / 'logs' / 'guard.log', runs / 'VW-3' / 'manifest.json', runs / '.active'):
        for tool in ('Write', 'Edit'):
            code, err = guard(tool, {'file_path': str(target)}, tmp_path)
            assert code == 2 and 'read-only' in err, (tool, target)
    assert guard('Write', {'file_path': str(runs / 'VW-3' / 'out' / 'manifest.json')}, tmp_path)[0] == 0
    assert guard('Read', {'file_path': str(runs / 'VW-3' / 'work' / 'guard.log')}, tmp_path)[0] == 0
    assert guard('Read', {'file_path': str(runs / 'VW-3' / 'manifest.json')}, tmp_path)[0] == 0


# ---------- design/49 V4, V5: an operator quote may hold shell characters; files inside the run may be shown ----------

def test_shell_characters_inside_a_quoted_argument_are_not_chaining(tmp_path):
    (tmp_path / 'runs' / 'VW-9').mkdir(parents=True)
    (tmp_path / 'runs' / '.active').write_text('VW-9', encoding='utf-8')
    vw_path = str(PLUGIN / 'scripts' / 'vw.py')
    code, err = guard('Bash', {'command': f'python "{vw_path}" stage brief record --quote "same as last time & I approve <all of it> | yes"'}, tmp_path)
    assert code == 0, err
    code, err = guard('Bash', {'command': f'python "{vw_path}" stage brief record --quote "yes" && rm -rf /'}, tmp_path)
    assert code == 2 and 'chaining' in err
    code, err = guard('Bash', {'command': f'python "{vw_path}" next > /tmp/x'}, tmp_path)
    assert code == 2 and 'chaining' in err


def test_files_inside_the_run_may_be_sent_or_revealed_to_the_operator(tmp_path):
    (tmp_path / 'runs' / 'VW-9' / 'out').mkdir(parents=True)
    (tmp_path / 'runs' / '.active').write_text('VW-9', encoding='utf-8')
    inside = str(tmp_path / 'runs' / 'VW-9' / 'out' / 'audition-A.mp3')
    for tool, inp in (('SendUserFile', {'files': [inside]}), ('mcp__ccd_host__reveal_path', {'path': 'runs/VW-9/out/audition-A.mp3'})):
        code, err = guard(tool, inp, tmp_path)
        assert code == 0, (tool, err)
    code, err = guard('SendUserFile', {'files': [inside, str(tmp_path / 'other.mp3')]}, tmp_path)
    assert code == 2 and 'inside' in err
    code, err = guard('mcp__ccd_host__reveal_path', {'path': '/Users/x/.vw2/session.json'}, tmp_path)
    assert code == 2
