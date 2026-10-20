"""Layer-one plugin tests (design/34 §E): no server, no database, no network. They run on any machine with
`.venv/bin/python -m pytest plugin/tests`. The server-side tests in server/tests need the Docker Postgres."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

PLUGIN = Path(__file__).resolve().parents[1]
REPO = PLUGIN.parent
sys.path.insert(0, str(PLUGIN / 'scripts'))
sys.path.insert(0, str(PLUGIN / 'hooks'))

PROCEDURES = json.loads((REPO / 'server' / 'procedures' / 'v2.json').read_text(encoding='utf-8'))
STAGES = {s['name']: s for s in PROCEDURES['stages']}


@pytest.fixture
def ws(tmp_path):
    """A run workspace outside the repo, as on an operator machine."""
    root = tmp_path / 'runs' / 'VW-9'
    for d in ('in', 'out', 'work', 'logs'):
        (root / d).mkdir(parents=True)
    (tmp_path / 'runs' / '.active').write_text('VW-9', encoding='utf-8')
    return root


def run_hook(name, payload, cwd, runs=None, env=None):
    """Run a hook the way Claude Code does: JSON on stdin, CLAUDE_PLUGIN_ROOT set. Returns (exit code, stdout, stderr)."""
    env = {**os.environ, 'CLAUDE_PLUGIN_ROOT': str(PLUGIN), **(env or {})}
    if runs is not None:
        env['VW2_RUNS'] = str(runs)
    p = subprocess.run([sys.executable, str(PLUGIN / 'hooks' / name)], input=json.dumps({**payload, 'cwd': str(cwd)}),
                       capture_output=True, text=True, env=env, cwd=str(cwd), timeout=30)
    return p.returncode, p.stdout, p.stderr
