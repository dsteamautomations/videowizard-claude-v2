"""PreToolUse guard: the executor may run only vw.py, may read and write only inside the active run folder, and may never
put the stage procedure text into a file or a command. Exit 2 blocks the call and sends the reason to the model."""
import json
import os
import re
import sys
from pathlib import Path

SENTINEL = 'VW-PROCEDURE'   # the first line of every stage prompt (server/procedures/*.json); design/34 1.11
WRITE_TOOLS = ('Edit', 'Write', 'MultiEdit', 'NotebookEdit')
READ_TOOLS = ('Read', 'Glob', 'Grep')


def block(reason):
    print(reason, file=sys.stderr)
    sys.exit(2)


def builder_checkout(cwd, root):
    repo, here = root.parent, cwd.resolve()
    return here == repo or repo in here.parents or here in root.parents


def active_run(cwd):
    runs = Path(os.environ.get('VW2_RUNS') or cwd / 'runs').resolve()
    marker = runs / '.active'
    code = marker.read_text(encoding='utf-8').strip() if marker.exists() else ''
    return (runs / code).resolve() if code else None


def main():
    data = json.load(sys.stdin)
    tool = data.get('tool_name')
    inp = data.get('tool_input') or {}
    cwd = Path(data.get('cwd') or os.getcwd())
    root = Path(os.environ.get('CLAUDE_PLUGIN_ROOT') or Path(__file__).resolve().parents[1]).resolve()
    vw = (root / 'scripts' / 'vw.py').resolve()
    if builder_checkout(cwd, root):
        sys.exit(0)  # builder checkout: the session works inside the repo that holds the plugin source; operators never do

    if tool in WRITE_TOOLS or tool == 'Bash':
        if SENTINEL in json.dumps(inp, ensure_ascii=False):
            block("Blocked: the stage procedure text is the builder's; it is never written into a file or a command.")

    if tool == 'Bash':
        cmd = (inp.get('command') or '').strip()
        m = re.match(r'^(?:python3?|py)\s+(?:"([^"]+)"|\'([^\']+)\'|(\S+))\s*(.*)$', cmd, re.S)
        script = m and (m.group(1) or m.group(2) or m.group(3))
        if not m or Path(script).resolve() != vw:
            block(f'Blocked: the operator may only run the vw tool: python "{vw}" <command>. For anything else, tell the operator or file a defect.')
        if re.search(r'[;&|`<>]|\$\(', m.group(4)):
            block('Blocked: no command chaining or redirection; run one vw command at a time.')
        sys.exit(0)

    if tool in WRITE_TOOLS or tool in READ_TOOLS:
        allowed = active_run(cwd)
        if allowed is None:
            block('Blocked: no active run. Start or pull a run with vw first; files may only be read or written inside runs/<code>/.')
        raw = inp.get('file_path') or inp.get('notebook_path') or inp.get('path') or ''
        if not raw:
            block(f'Blocked: give a path inside {allowed} (reads and searches are limited to the active run folder).')
        target = Path(raw).expanduser()
        target = (target if target.is_absolute() else cwd / target).resolve()
        if target != allowed and allowed not in target.parents:
            block(f'Blocked: files may only be read or written inside {allowed}.')
    sys.exit(0)


if __name__ == '__main__':
    main()
