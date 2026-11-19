"""PreToolUse guard: an allow-list (design/36 1.11–1.12, design/37 2.4). The operator assistant may run only vw.py, may read
and write only inside the active run folder, may ask the operator questions, keep its task list and use the web tools (the
warning-and-yes rule before a search is an instruction in vw.md: the guard cannot tell who asked). Everything else, connectors,
the browser pane and subagents other than the plugin's two helpers included, is blocked. The stage procedure text (sentinel VW-PROCEDURE) never reaches a file or
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
FILE_TOOLS = ('SendUserFile', 'mcp__ccd_host__reveal_path')   # design/49 V5: show a run file to the operator
ALWAYS = ('AskUserQuestion', 'TodoWrite', 'TodoRead', 'ToolSearch',
          'mcp__ccd_turn__update_plan', 'mcp__ccd_turn__wrap_up', 'mcp__ccd_view__show_pane', 'mcp__visualize__show_widget', 'mcp__visualize__read_me',   # design/190: the card of a whole step
          'SubagentHandback')   # design/148 A3 (SK, 3 Nov 2026): the plugin's own helpers report back; a message to a helper stays blocked
WEB_TOOLS = ('WebSearch', 'WebFetch')
WEB_MINUTES = 10   # design/48 O.1: one recorded yes covers the search and the fetches on that subject for ten minutes
WEB_BLOCKED = ("Blocked: a web search needs the operator's yes. Say to them: 'I am deviating from the usual procedure. I want to search the web for X, "
               "because Y. The result may affect Z.' On their yes run vw web --about \"X\" --ok \"<their words>\", then search.")
RECORDS = ('guard.log', 'manifest.json', '.active')   # design/48 O.4: the tool's own records, read-only for the assistant
VW_SKILLS = ('vw:vw', 'vw', 'vw:motion', 'motion', 'vw:guide', 'guide', 'vw:drawing', 'drawing')   # design/130: the motion skill of the drawn-shot helper; integration steps B to D: the guide skill of an AI video shot
VW_HELPERS = ('vw:vw-scene-review', 'vw-scene-review', 'vw:vw-plan-gaps', 'vw-plan-gaps',   # design/125 O6, O9: the plugin's own helpers; their calls pass this guard too
              'vw:vw-motion-shot', 'vw-motion-shot', 'vw:vw-motion-rules', 'vw-motion-rules', 'vw:vw-motion-check', 'vw-motion-check',   # design/130
              'vw:vw-motion-parts', 'vw-motion-parts',   # design/221 row 1: the drawer of the film's shared parts
              'vw:vw-still-prompts', 'vw-still-prompts',   # fix set A2.1: the writer of the still pictures' prompts (out/images.json)
              'vw:vw-guide-scene', 'vw-guide-scene', 'vw:vw-guide-check', 'vw-guide-check',
              'vw:vw-drawing', 'vw-drawing',
              'vw:vw-reference-finder', 'vw-reference-finder', 'vw:vw-set-look', 'vw-set-look')   # design/211: the finder of the footage pictures, the looker at the made sets; design/200: the drawer of one thing's drawing set   # integration steps B to D: the builder and the fresh checker of an AI video shot's guide
NOT_HERE = ("Blocked: {tool} is not available to the operator assistant. It uses only the vw tool, files inside the active run folder, "
            "questions to the operator, and the web after the warning and the operator's yes.")


def block(reason):
    print(reason, file=sys.stderr)
    sys.exit(2)


def builder_checkout(cwd, root):
    repo, here = root.parent, cwd.resolve()
    return here == repo or repo in here.parents or here in root.parents


def operator_folder(cwd):
    """design/129 G1: the hooks act only in a folder whose own Claude settings name the VideoWizard server (the operator folder), or below it.
    The user's own settings folder is not counted, so a plugin switched on everywhere steps aside everywhere else."""
    here, home = Path(cwd).resolve(), Path.home().resolve()
    for d in (here, *here.parents):
        if d == home:
            continue
        for name in ('settings.json', 'settings.local.json'):
            try:
                if 'VW2_SERVER_URL' in (d / '.claude' / name).read_text(encoding='utf-8'):
                    return True
            except (OSError, UnicodeDecodeError):
                continue
    return False


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
        bare = re.sub(r'"(?:[^"\\]|\\.)*"|\'[^\']*\'', '""', m.group(4))   # design/49 V4: an operator's quoted words may hold & | < >
        found = sorted(set(re.findall(r'&&|\|\||2>&1|[;&|`<>]|\$\(', bare)))
        if found:   # VW-22 (12 Nov 2026): the block names what it found, so the next call is right the first time
            return ('Blocked: one vw command per call, and nothing else in it. Found ' + ' '.join(found) + ' outside quotes. Do not join commands (&&, ;), pipe (|), '
                    "redirect (>, <, 2>&1) or use backticks or $(...); put the operator's words inside double quotes; run the next command as its own call.")
        return None
    if tool in FILE_TOOLS:   # design/49 V5: a file inside the run may be shown to the operator
        allowed = active_run(cwd)
        if allowed is None:
            return 'Blocked: no active run; only files inside runs/<code>/ can be shown.'
        raw = inp.get('files') if isinstance(inp.get('files'), list) else [inp.get('path') or inp.get('file_path') or '']
        for item in raw:
            target = Path(str(item)).expanduser()
            target = (target if target.is_absolute() else cwd / target).resolve()
            if target != allowed and allowed not in target.parents:
                return f'Blocked: only files inside {allowed} can be shown to the operator.'
        return None
    if tool in READ_TOOLS:   # design/130: the plugin's own skill files (the motion references) are readable; never writable
        raw0 = inp.get('file_path') or inp.get('path') or ''
        if raw0:
            t0 = Path(raw0).expanduser()
            t0 = (t0 if t0.is_absolute() else cwd / t0).resolve()
            skills = (vw.parent.parent / 'skills').resolve()
            if t0 == skills or skills in t0.parents:
                return None
    if tool in READ_TOOLS:   # VW-22 (12 Nov 2026): an answer of the tool too long for one message is saved by Claude Code under the session's own tool-results folder; reading it back is reading the tool's answer
        raw1 = inp.get('file_path') or inp.get('path') or ''
        if raw1:
            t1 = Path(raw1).expanduser().resolve()
            projects = (Path.home() / '.claude' / 'projects').resolve()
            if projects in t1.parents and 'tool-results' in t1.parts:
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
    if tool == 'Artifact':   # design/204: the one page the operator answers on; nothing else is published from here
        page = (vw.parent.parent / 'pages' / 'decisions.html').resolve()
        action = str(inp.get('action') or 'publish')
        if action == 'open':
            return None
        if action == 'read':   # design/210 part 2: a picture the operator added on the page, fetched by its id into the run's own-picture folder, and nothing else
            run = active_run(cwd)
            own = (run / 'work' / 'page' / 'own').resolve() if run else None
            raw = inp.get('out_dir')
            into = (Path(raw).expanduser() if Path(raw).expanduser().is_absolute() else cwd / raw).resolve() if isinstance(raw, str) and raw else None
            if (own and into == own and inp.get('url') and isinstance(inp.get('path'), str) and re.fullmatch(r'[0-9a-f]{32}', inp['path'])
                    and not (inp.get('paths') or inp.get('page') or inp.get('type_url'))):
                return None
            return ("Blocked: the only thing read from the run's decisions page (`url`) is a picture the operator added there: `path` its id (32 hex characters), `out_dir` "
                    f"{own or 'work/page/own/ of the active run'}, as `vw visuals page --record` lists them.")
        if action == 'publish' and inp.get('asset') is True:   # design/210: the run's large pictures, uploaded to the page's file store, and nothing else
            run = active_run(cwd)
            paths = inp.get('file_paths') if 'file_paths' in inp else [inp.get('file_path')]
            zoom = run / 'work' / 'page' / 'zoom' if run else None
            inside = lambda raw: isinstance(raw, str) and raw and zoom in (Path(raw).expanduser() if Path(raw).expanduser().is_absolute() else cwd / raw).resolve().parents
            if (zoom and inp.get('url') and isinstance(paths, list) and paths and all(inside(x) for x in paths)
                    and not (inp.get('files') or inp.get('type_url') or inp.get('from_url') or inp.get('asset_ids'))):
                return None
            return (f"Blocked: only the large pictures of the active run (files inside its work/page/zoom/ folder) are uploaded, to the run's decisions page (`url`), "
                    'as `vw visuals page` lists them.')
        if action != 'publish' or inp.get('asset') or inp.get('files') or inp.get('type_url'):
            return f"Blocked: the operator assistant publishes only the plugin's decisions page ({page}), as `vw visuals page` says."
        target = Path(str(inp.get('file_path') or '')).expanduser()
        target = (target if target.is_absolute() else cwd / target).resolve()
        return None if target == page else f"Blocked: only the plugin's decisions page can be published: {page}."
    if tool == 'ArtifactData':   # design/204: one round written to the page from its file; the operator's answers read into the run folder
        allowed = active_run(cwd)
        if allowed is None:
            return 'Blocked: no active run; the decisions page belongs to a run.'
        action = str(inp.get('action') or '')
        if action == 'batch':   # design/210: the pictures of a round, each written from its file in the run folder to the page's two picture collections
            writes = inp.get('writes')
            ok = isinstance(writes, list) and writes and all(
                isinstance(w, dict) and w.get('op') == 'set' and w.get('collection') in ('pics', 'zoom') and 'data' not in w and isinstance(w.get('file_path'), str) and w['file_path']
                and allowed in (Path(w['file_path']).expanduser() if Path(w['file_path']).expanduser().is_absolute() else cwd / w['file_path']).resolve().parents for w in writes)
            return None if ok else ('Blocked: a batch only writes picture files to the page: every entry is `op` "set", collection "pics" or "zoom", with a `file_path` '
                                    f'inside {allowed} and no typed `data`, as `vw visuals page` gives them.')
        if action not in ('set', 'list', 'get'):
            return 'Blocked: the page is written one round at a time (set, from the round file) and its answers are read (list). Nothing else.'
        if action == 'set' and (not inp.get('file_path') or inp.get('data')):
            return 'Blocked: write the round from its file (`file_path` = the `round_file` of `vw visuals page`); never type its content.'
        for raw in (inp.get('file_path'), inp.get('out_dir')):
            if raw:
                target = Path(str(raw)).expanduser()
                target = (target if target.is_absolute() else cwd / target).resolve()
                if target != allowed and allowed not in target.parents:
                    return f'Blocked: the page reads and writes only files inside {allowed}.'
        return None
    if tool in ALWAYS:
        return None
    if tool in ('Agent', 'Task') and str(inp.get('subagent_type') or '') in VW_HELPERS:
        return None
    if tool == 'Skill':
        name = str(inp.get('skill') or '')
        return None if name in VW_SKILLS else f"Blocked: only these skills are available here: {', '.join(s for s in VW_SKILLS if ':' in s)}; not {name!r}."
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
        return str(inp['command'])[:400]   # the whole command, so a block can be understood afterwards (was 80 characters)
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
    if not operator_folder(cwd):
        sys.exit(0)  # design/129 G1: not the operator folder; the plugin stays out of the way
    reason = decide(tool, inp, cwd, vw)
    if reason:
        log_block(cwd, tool, reason, detail_of(tool, inp, reason))
        block(reason)
    if tool == 'AskUserQuestion':   # design/192 (intake 8, brief 7): the question goes to the run's log; never a reason to stop it
        try:
            import asked
            asked.log(data, cwd, root)
        except Exception:   # noqa: BLE001
            pass
    sys.exit(0)


if __name__ == '__main__':
    main()
