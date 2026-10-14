"""Test harness: a throwaway postgres:17 in Docker, fresh tables per test.

Run: python -m pytest server/tests -q  (Docker Desktop must be running).
"""
import hashlib
import os
import secrets
import socket
import subprocess
import time
import uuid

import psycopg
import pytest

CONTAINER = 'vw2-test-pg'
PORT = int(os.environ.get('VW2_TEST_PG_PORT', '55433'))
URL = f'postgresql://postgres:pw@127.0.0.1:{PORT}/postgres'


def _port_open():
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(('127.0.0.1', PORT)) == 0


def _start_container():
    if _port_open():
        return
    subprocess.run(['docker', 'rm', '-f', CONTAINER], capture_output=True)
    subprocess.run(['docker', 'run', '-d', '--rm', '--name', CONTAINER, '-e', 'POSTGRES_PASSWORD=pw',
                    '-p', f'{PORT}:5432', 'postgres:17'], check=True, capture_output=True)
    for _ in range(60):
        try:
            with psycopg.connect(URL, connect_timeout=2):
                return
        except psycopg.Error:
            time.sleep(1)
    raise RuntimeError('postgres container did not become ready')


@pytest.fixture(scope='session', autouse=True)
def database():
    _start_container()
    os.environ['VW2_DATABASE_URL'] = URL
    os.environ['VW2_SHARED_SUPABASE_URL'] = 'https://shared.invalid'
    os.environ['VW2_SHARED_SUPABASE_SERVICE_KEY'] = 'sb_secret_test'
    os.environ['VW2_APP_ID'] = 'app-test'
    from app import db
    db.migrate(URL)
    yield URL


TEST_PROCEDURE = {
    'version': 'test',
    'stages': [
        {'name': 's1', 'needs_acceptance': True, 'paid': None, 'per_unit': None, 'requires_files': False, 'cap': 3},
        {'name': 's2', 'needs_acceptance': True, 'paid': 'fakevoice', 'per_unit': None, 'requires_files': True, 'cap': 2},
        {'name': 's3', 'needs_acceptance': False, 'paid': 'fakeanalysis', 'per_unit': 'item', 'requires_files': False, 'cap': 2},
        {'name': 's4', 'needs_acceptance': True, 'paid': None, 'per_unit': None, 'requires_files': False, 'cap': 2},
    ],
}
TEST2_PROCEDURE = {
    'version': 'test2',
    'stages': [{'name': 's0', 'needs_acceptance': False, 'paid': None, 'per_unit': None, 'requires_files': False, 'cap': 3}]
    + TEST_PROCEDURE['stages'],
}


@pytest.fixture(autouse=True)
def clean_tables(database):
    from app import db
    with psycopg.connect(database) as conn:
        conn.execute("truncate vw2_receipts, vw2_defects, vw2_jobs, vw2_attempts, vw2_revises, vw2_stage_outputs, vw2_runs, vw2_sessions")
        conn.execute("delete from vw2_procedures where version in ('test','test2')")
        conn.execute("insert into vw2_procedures(version, document) values ('test', %s::jsonb), ('test2', %s::jsonb)",
                     (psycopg.types.json.Json(TEST_PROCEDURE), psycopg.types.json.Json(TEST2_PROCEDURE)))
    db.stage_table.cache_clear()
    yield


@pytest.fixture
def client(database):
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as c:
        yield c


def seed_session(url, user_id, name='Tester', role='Member', kind='executor', expired=False):
    token = secrets.token_urlsafe(24)
    with psycopg.connect(url) as conn:
        conn.execute(
            "insert into vw2_sessions(token_hash,user_id,user_name,role,kind,expires_at) "
            "values (%s,%s,%s,%s,%s, now() + (%s || ' hours')::interval)",
            (hashlib.sha256(token.encode()).hexdigest(), user_id, name, role, kind, '-1' if expired else '24'))
    return {'Authorization': 'Bearer ' + token}


@pytest.fixture
def alice(database):
    return seed_session(database, 'alice')


@pytest.fixture
def bob(database):
    return seed_session(database, 'bob')


@pytest.fixture
def admin(database):
    return seed_session(database, 'root', name='Root', role='Admin', kind='browser')


def rid():
    return str(uuid.uuid4())
