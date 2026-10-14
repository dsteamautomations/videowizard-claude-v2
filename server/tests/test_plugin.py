"""Slice 2+3: the vw plugin CLI (P1–P10, P15) and the hooks guard (P11–P14), run as real subprocesses
against a live uvicorn server on the test database."""
import hashlib
import json
import os
import secrets
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

import psycopg
import pytest

from conftest import ROOT, VW, GUARD, vw, connected, server, home  # noqa: F401

START = ['start', '--client', 'C', '--version', 'test', '--need-gb', '0']


def test_p1_no_session_prints_connect_link(home):
    code, out, err = vw(home, 'next')
    assert code == 2 and out['action'] == 'connect' and out['url'].startswith('http') and 'code' in out


def test_p2_expired_session(home, database):
    connected(home, database)
    with psycopg.connect(database) as conn:
        conn.execute("update vw2_sessions set expires_at = now() - interval '1 hour'")
    code, out, _ = vw(home, 'whoami')
    assert code == 2 and out['action'] == 'connect'


def test_p3_server_unreachable(home, database):
    connected(home, database)
    home['env']['VW2_SERVER_URL'] = 'http://127.0.0.1:1'
    code, out, _ = vw(home, 'whoami')
    assert code == 2 and out['action'] == 'tell_builder' and '127.0.0.1:1' in out['message']


def test_p4_plugin_too_old(home, database):
    connected(home, database)
    home['env']['VW2_PLUGIN_VERSION'] = '0.0.1'
    code, out, _ = vw(home, *START)
    assert code == 2 and out['action'] == 'install_plugin' and out['required']


def test_connect_flow_end_to_end(home, database):
    """P1 companion: `connect` polls until the browser approves."""
    proc = subprocess.Popen([sys.executable, str(VW), 'connect', '--timeout', '30', '--poll', '0.5'], env=home['env'],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    from psycopg.rows import dict_row
    with psycopg.connect(database, row_factory=dict_row) as conn:
        row = None
        for _ in range(60):  # the subprocess registers its connection as soon as it starts; wait up to 30 s under load
            row = conn.execute('select id, token_hash, code from vw2_connections order by created_at desc limit 1').fetchone()
            if row:
                break
            time.sleep(0.5)
        assert row, 'vw connect never registered a connection'
        conn.execute("insert into vw2_sessions(token_hash,user_id,user_name,role,kind,expires_at) values (%s,'e1','Emp','Member','executor', now() + interval '1 day')", (row['token_hash'],))
        conn.execute('update vw2_connections set approved_by=%s, approved_at=now() where id=%s', ('e1', row['id']))
    out, err = proc.communicate(timeout=40)
    assert proc.returncode == 0, err
    assert json.loads(out)['user']['id'] == 'e1'
    assert json.loads((home['home'] / 'session.json').read_text())['token']


def test_p5_p6_p8_start_output_close(home, database):
    connected(home, database)
    code, out, _ = vw(home, *START)
    assert code == 0, out
    run_code = out['code']
    ws = home['runs'] / run_code
    assert all((ws / d).is_dir() for d in ('in', 'out', 'work', 'logs')) and (home['runs'] / '.active').read_text() == run_code
    assert vw(home, *START)[0] == 0  # a second start for the same client makes a new run; folders are per code
    # client must be one Active directory client: unknown → refused with candidates; the directory is listable
    rc, out, _ = vw(home, 'start', '--client', 'VK Nard', '--version', 'test', '--need-gb', '0')
    assert rc == 2 and out['code'] == 'CLIENT_UNKNOWN' and out['candidates'] == []
    rc, out, _ = vw(home, 'start', '--client', 'vk', '--version', 'test', '--need-gb', '0')
    assert rc == 0 and out['client'] == 'VK' and out['client_id'] == 'c-vk' and out['title'] == ''
    rc, out, _ = vw(home, 'clients', '--search', 'vk')
    assert rc == 0 and [c['client_name'] for c in out['clients']] == ['VK', 'VK Textiles']
    (home['runs'] / '.active').write_text(run_code)
    code, out, _ = vw(home, 'next')
    assert code == 0 and out['stage'] == 's1'
    (ws / 'out' / 'brief.json').write_text('{"x":1}')
    (ws / 'work' / 'scratch.txt').write_text('tmp')
    outside = home['runs'] / 'elsewhere.json'
    outside.write_text('{}')
    code, out, _ = vw(home, 'output', '--stage', 's1', '--quote', 'yes', '--file', str(outside))
    assert code == 2 and out['action'] == 'refused'
    code, out, _ = vw(home, 'output', '--stage', 's1', '--quote', 'yes', '--file', 'out/brief.json', '--retain')
    assert code == 0 and out['files'][0]['sha256'] == hashlib.sha256(b'{"x":1}').hexdigest()
    manifest = json.loads((ws / 'manifest.json').read_text())
    assert manifest['files'][0]['action'] == 'retain'
    # finish the test procedure with file-less outputs
    (ws / 'out' / 'v.mp3').write_bytes(b'abc')
    assert vw(home, 'output', '--stage', 's2', '--quote', 'yes', '--file', 'out/v.mp3', '--retain', '--summary', '{"units":{"s3":["u1"]}}')[0] == 0
    assert vw(home, 'output', '--stage', 's3', '--unit', 'u1')[0] == 0
    assert vw(home, 'output', '--stage', 's4', '--quote', 'yes')[0] == 0
    code, out, _ = vw(home, 'close')
    assert code == 0 and out['status'] == 'closed'
    assert not (ws / 'work').exists() and not (ws / 'logs').exists() and (ws / 'out' / 'brief.json').exists()


def test_p7_close_refuses_without_receipts(home, database):
    connected(home, database)
    _, out, _ = vw(home, *START)
    ws = home['runs'] / out['code']
    (ws / 'out' / 'a.json').write_text('{}')
    assert vw(home, 'output', '--stage', 's1', '--quote', 'yes', '--file', 'out/a.json')[0] == 0  # default action: upload, no receipt yet
    for args in (['output', '--stage', 's2', '--quote', 'yes', '--file', 'out/a.json', '--retain'], ['output', '--stage', 's3'], ['output', '--stage', 's4', '--quote', 'yes']):
        assert vw(home, *args)[0] == 0
    code, out, _ = vw(home, 'close')
    assert code == 2 and out['action'] == 'refused' and 'a.json' in out['files']
    assert (ws / 'work').exists()


def test_p9_p10_pull_and_takeover(home, database, tmp_path):
    connected(home, database)
    _, out, _ = vw(home, *START)
    run_code = out['code']
    other = {**home, 'home': tmp_path / 'home2', 'runs': tmp_path / 'runs2',
             'env': {**home['env'], 'VW2_HOME': str(tmp_path / 'home2'), 'VW2_RUNS': str(tmp_path / 'runs2')}}
    connected(other, database)
    code, out, _ = vw(other, 'pull', run_code)
    assert code == 2 and out['action'] == 'take_over' and out['active_machine']
    code, out, _ = vw(other, 'pull', run_code, '--take-over')
    assert code == 0 and (other['runs'] / run_code / 'manifest.json').exists()
    code, out, _ = vw(home, 'next')
    assert code == 2 and out['action'] == 'take_over'


def test_p15_needs_user_decision(home, database):
    connected(home, database)
    _, out, _ = vw(home, *START)
    for _ in range(3):
        assert vw(home, 'output', '--stage', 's1')[0] == 2  # no quote → 422, counts as attempt
    code, out, _ = vw(home, 'output', '--stage', 's1', '--quote', 'yes')
    assert code == 3 and out['code'] == 'NEEDS_USER_DECISION' and 'retry' in out['options']
    assert vw(home, 'decide', '--stage', 's1', '--decision', 'retry')[0] == 0


def guard(tool, tool_input, cwd):
    p = subprocess.run([sys.executable, str(GUARD)], input=json.dumps({'tool_name': tool, 'tool_input': tool_input, 'cwd': str(cwd)}),
                       capture_output=True, text=True, env={**os.environ, 'CLAUDE_PLUGIN_ROOT': str(ROOT / 'plugin')})
    return p.returncode, p.stderr


def test_p11_p12_guard_bash(tmp_path):
    for cmd in ('gcloud logging read x', 'psql -c "select 1"', 'git status', 'python other.py', 'python vw.py next; rm -rf /'):
        code, err = guard('Bash', {'command': cmd}, tmp_path)
        assert code == 2 and err.strip(), cmd
    assert guard('Bash', {'command': f'python "{VW}" next'}, tmp_path)[0] == 0
    assert guard('Bash', {'command': f"python '{VW}' output --stage s1 --quote \"yes\""}, tmp_path)[0] == 0


def test_p13_p14_guard_files(tmp_path):
    runs = tmp_path / 'runs'
    (runs / 'VW-3' / 'out').mkdir(parents=True)
    assert guard('Write', {'file_path': str(runs / 'VW-3' / 'out' / 'x.json')}, tmp_path)[0] == 2  # P14: no .active
    (runs / '.active').write_text('VW-3')
    assert guard('Write', {'file_path': str(runs / 'VW-3' / 'out' / 'x.json')}, tmp_path)[0] == 0
    assert guard('Edit', {'file_path': str(runs / 'VW-3' / 'work' / 'y.txt')}, tmp_path)[0] == 0
    assert guard('Write', {'file_path': str(tmp_path / 'elsewhere.txt')}, tmp_path)[0] == 2
    assert guard('Write', {'file_path': str(ROOT / 'plugin' / 'commands' / 'vw.md')}, tmp_path)[0] == 2
    assert guard('Write', {'file_path': str(runs / 'VW-4' / 'out' / 'x.json')}, tmp_path)[0] == 2
    assert guard('Read', {'file_path': str(tmp_path / 'anything')}, tmp_path)[0] == 0  # reads are not guarded


def test_guard_stands_down_in_the_builder_checkout():
    for cwd in (ROOT, ROOT / 'server', ROOT.parent):
        assert guard('Bash', {'command': 'git status'}, cwd)[0] == 0, cwd
        assert guard('Write', {'file_path': str(ROOT / 'README.md')}, cwd)[0] == 0, cwd
