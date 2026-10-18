"""PreToolUse guard: an allow-list (design/36 1.11–1.12, design/37 2.4). The operator assistant may run only vw.py, may read
and write only inside the active run folder, may ask the operator questions, keep its task list and use the web tools (the
warning-and-yes rule before a search is an instruction in vw.md: the guard cannot tell who asked). Everything else, connectors,
the browser pane and subagents included, is blocked. The stage procedure text (sentinel VW-PROCEDURE) never reaches a file or
a command. Every blocked call is one line in work/guard.log of the active run. Exit 2 blocks the call and sends the reason."""
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

SENTINEL = 'VW-PROCEDURE'   # the first line of every stage prompt (server/procedures/*.json)
WRITE_TOOLS = ('Edit', 'Write', 'MultiEdit', 'NotebookEdit')
READ_TOOLS = ('Read', 'Glob', 'Grep')
ALWAYS = ('AskUserQuestion', 'TodoWrite', 'TodoRead', 'ToolSearch',
          'mcp__ccd_turn__update_plan', 'mcp__ccd_turn__wrap_up', 'mcp__ccd_view__show_pane')
WEB_TOOLS = ('WebSearch', 'WebFetch')
WEB_MINUTES = 10   # design/48 O.1: one recorded yes covers the search and the fetches on that subject for ten minutes
WEB_BLOCKED = ("Blocked: a web search needs the operator's yes. Say to them: 'I am deviating from the usual procedure. I want to search the web for X, "
               "because Y. The result may affect Z.' On their yes run vw web --about \"X\" --ok \"<their words>\", then search.")
RECORDS = ('guard.log', 'manifest.json', '.active')   # design/48 O.4: the tool's own records, read-only for the assistant
VW_SKILLS = ('vw:vw', 'vw')
NOT_HERE = ("Blocked: {tool} is not available to the operator assistant. It uses only the vw tool, files inside the active run folder, "
            "questions to the operator, and the web after the warning and the operator's yes.")


def block(reason):
    print(reason, file=sys.stderr)
    sys.exit(2)


def builder_checkout(cwd, root):
    repo, here = root.parent, cwd.resolve()
    return here == repo or repo in here.parents or here in root.parents


def runs_dir(cwd):
    return Path(os.environ.get('VW2_RUNS') or cwd / 'runs').resolve()


def active_run(cwd):
    runs = runs_dir(cwd)
    marker = runs / '.active'
    code = marker.read_text(encoding='utf-8').strip() if marker.exists() else ''
    return (runs / code).resolve() if code else None


def web_permission(cwd, tool, inp):
    """design/48 O.1: allowed only with the operator's yes recorded by `vw web` less than WEB_MINUTES ago; every allowed call is appended
    to the permission file and to guard.log. Returns None when allowed, else the reason."""
    run = active_run(cwd)
    if run is None:
        return WEB_BLOCKED
    path = run / 'work' / 'web-ok.json'
    try:
        ok = json.loads(path.read_text(encoding='utf-8'))
        at = datetime.fromisoformat(ok['at'])
    except (OSError, ValueError, KeyError, TypeError):
        return WEB_BLOCKED
    now = datetime.now(timezone.utc)
    if at.tzinfo is None or now - at > timedelta(minutes=WEB_MINUTES):
        return WEB_BLOCKED
    detail = str(inp.get('query') or inp.get('url') or '')[:120]
    ok.setdefault('calls', []).append({'tool': tool, **({'query': detail} if tool == 'WebSearch' else {'url': detail}), 'at': now.isoformat(timespec='seconds')})
    try:
        path.write_text(json.dumps(ok, ensure_ascii=False, indent=1), encoding='utf-8')
    except OSError:
        pass
    log_block(cwd, tool, f"allowed ({ok.get('about', '')})", detail)
    return None


def own_record(target, cwd):
    """design/48 O.4: guard.log anywhere, the run's manifest.json at its root, runs/.active."""
    run = active_run(cwd)
    return target.name == 'guard.log' or (run is not None and target == run / 'manifest.json') or target == runs_dir(cwd) / '.active'


def decide(tool, inp, cwd, vw):
    """None when the call is allowed, otherwise the reason it is blocked."""
    if tool in WEB_TOOLS:
        return web_permission(cwd, tool, inp)
    if tool in WRITE_TOOLS or tool == 'Bash':
        if SENTINEL in json.dumps(inp, ensure_ascii=False):
            return "Blocked: the stage procedure text is the builder's; it is never written into a file or a command."
    if tool == 'Bash':
        cmd = (inp.get('command') or '').strip()
        m = re.match(r'^(?:python3?|py)\s+(?:"([^"]+)"|\'([^\']+)\'|(\S+))\s*(.*)$', cmd, re.S)
        script = m and (m.group(1) or m.group(2) or m.group(3))
        if not m or Path(script).resolve() != vw:
            return f'Blocked: the operator may only run the vw tool: python "{vw}" <command>. For anything else, tell the operator or file a defect.'
        if re.search(r'[;&|`<>]|\$\(', m.group(4)):
            return 'Blocked: no command chaining or redirection; run one vw command at a time.'
        return None
    if tool in WRITE_TOOLS or tool in READ_TOOLS:
        allowed = active_run(cwd)
        if allowed is None:
            return 'Blocked: no active run. Start or pull a run with vw first; files may only be read or written inside runs/<code>/.'
        raw = inp.get('file_path') or inp.get('notebook_path') or inp.get('path') or ''
        if not raw:
            return f'Blocked: give a path inside {allowed} (reads and searches are limited to the active run folder).'
        target = Path(raw).expanduser()
        target = (target if target.is_absolute() else cwd / target).resolve()
        if tool in WRITE_TOOLS and own_record(target, cwd):
            return f"Blocked: {target.name} is the tool's own record, read-only for the assistant."
        if target != allowed and allowed not in target.parents:
            return f'Blocked: files may only be read or written inside {allowed}.'
        return None
    if tool in ALWAYS:
        return None
    if tool == 'Skill':
        name = str(inp.get('skill') or '')
        return None if name in VW_SKILLS else f'Blocked: only the vw:vw skill is available here, not {name!r}.'
    return NOT_HERE.format(tool=tool)


def detail_of(tool, inp, reason):
    if SENTINEL in reason or "builder's" in reason:
        return '(procedure text)'
    for k in ('file_path', 'notebook_path', 'path'):
        if inp.get(k):
            return str(inp[k])   # a path in full: it is what the reviewer needs to see
    for k in ('skill', 'url', 'query'):
        if inp.get(k):
            return str(inp[k])[:120]
    if inp.get('command'):
        return str(inp['command'])[:80]
    return ''


def log_block(cwd, tool, reason, detail):
    """One line per blocked call, in work/guard.log of the active run (runs/guard.log when none), so blocks can be reviewed later."""
    try:
        run = active_run(cwd)
        path = (run / 'work' / 'guard.log') if run else (runs_dir(cwd) / 'guard.log')
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('a', encoding='utf-8') as f:
            f.write(f"{datetime.now(timezone.utc).isoformat(timespec='seconds')} · {tool} · {reason} · {detail}\n")
    except OSError:
        pass


def main():
    data = json.load(sys.stdin)
    tool = data.get('tool_name') or ''
    inp = data.get('tool_input') or {}
    cwd = Path(data.get('cwd') or os.getcwd())
    root = Path(os.environ.get('CLAUDE_PLUGIN_ROOT') or Path(__file__).resolve().parents[1]).resolve()
    vw = (root / 'scripts' / 'vw.py').resolve()
    if builder_checkout(cwd, root):
        sys.exit(0)  # builder checkout: the session works inside the repo that holds the plugin source; operators never do
    reason = decide(tool, inp, cwd, vw)
    if reason:
        log_block(cwd, tool, reason, detail_of(tool, inp, reason))
        block(reason)
    sys.exit(0)


if __name__ == '__main__':
    main()
