"""PreToolUse guard: the executor may run only vw.py, and may write only inside the active run folder.
Exit 2 blocks the call and sends the reason to the model."""
import json
import os
import re
import sys
from pathlib import Path


def block(reason):
    print(reason, file=sys.stderr)
    sys.exit(2)


def main():
    data = json.load(sys.stdin)
    tool = data.get('tool_name')
    inp = data.get('tool_input') or {}
    cwd = Path(data.get('cwd') or os.getcwd())
    root = Path(os.environ.get('CLAUDE_PLUGIN_ROOT') or Path(__file__).resolve().parents[1]).resolve()
    vw = (root / 'scripts' / 'vw.py').resolve()

    if tool == 'Bash':
        cmd = (inp.get('command') or '').strip()
        m = re.match(r'^(?:python3?|py)\s+(?:"([^"]+)"|\'([^\']+)\'|(\S+))\s*(.*)$', cmd, re.S)
        script = m and (m.group(1) or m.group(2) or m.group(3))
        if not m or Path(script).resolve() != vw:
            block(f'Blocked: the operator may only run the vw tool: python "{vw}" <command>. For anything else, tell the operator or file a defect.')
        if re.search(r'[;&|`<>]|\$\(', m.group(4)):
            block('Blocked: no command chaining or redirection; run one vw command at a time.')
        sys.exit(0)

    if tool in ('Edit', 'Write', 'MultiEdit', 'NotebookEdit'):
        target = Path(inp.get('file_path') or inp.get('notebook_path') or '').resolve()
        runs = Path(os.environ.get('VW2_RUNS') or cwd / 'runs').resolve()
        marker = runs / '.active'
        code = marker.read_text(encoding='utf-8').strip() if marker.exists() else ''
        if not code:
            block('Blocked: no active run. Start or pull a run with vw first; files may only be written inside runs/<code>/.')
        allowed = (runs / code).resolve()
        if allowed not in target.parents:
            block(f'Blocked: files may only be written inside {allowed}.')
    sys.exit(0)


if __name__ == '__main__':
    main()
