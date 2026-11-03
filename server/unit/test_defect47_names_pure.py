"""Defect 47 (VW-18, 3 Nov 2026): `vw options propose` crashed (HTTP 500, NameError: fps) because a text replacement in design/139 R1 reached a function
that never defines fps. No test ran the proposal end to end. This check reads every server module for a name used but never defined."""
import subprocess
import sys
from pathlib import Path

import pytest

APP = Path(__file__).resolve().parents[1] / 'app'


def test_no_server_module_uses_an_undefined_name():
    pytest.importorskip('pyflakes')
    files = [str(p) for p in APP.rglob('*.py') if '__pycache__' not in p.parts]
    out = subprocess.run([sys.executable, '-m', 'pyflakes', *files], capture_output=True, text=True).stdout
    undefined = [line for line in out.splitlines() if 'undefined name' in line]
    assert undefined == []
