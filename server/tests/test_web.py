"""Slice 2+3: browser connect flow (C1–C5) and server-rendered pages (C6–C8)."""
import hashlib
import secrets

import psycopg
import pytest

from app import auth
from conftest import rid, seed_session
from test_auth import directory


def browser_login(client, monkeypatch, username='sk', password='pw1', role='Member'):
    monkeypatch.setattr(auth, 'shared_client', lambda: directory(username, password, role))
    r = client.post('/login', data={'username': username, 'password': password}, follow_redirects=False)
    assert r.status_code == 303, r.text
    assert 'vw2_session' in r.cookies
    return r


def begin_connect(client):
    token = secrets.token_urlsafe(32)
    r = client.post('/api/connect', json={'request_id': rid(), 'token_hash': hashlib.sha256(token.encode()).hexdigest()})
    assert r.status_code == 201, r.text
    return token, r.json()


def test_c1_connect_approve_then_executor_token_works(client, monkeypatch):
    token, conn = begin_connect(client)
    assert conn['url'].endswith('/connect/' + conn['id']) and len(conn['code']) == 9
    assert client.get(f"/api/connect/{conn['id']}").json()['status'] == 'pending'
    assert client.get('/api/auth/me', headers={'Authorization': 'Bearer ' + token}).status_code == 401
    browser_login(client, monkeypatch)
    page = client.get(f"/connect/{conn['id']}")
    assert page.status_code == 200 and conn['code'] in page.text
    r = client.post(f"/connect/{conn['id']}", data={'code': conn['code']}, follow_redirects=False)
    assert r.status_code == 200 and 'connected' in r.text.lower()
    assert client.get(f"/api/connect/{conn['id']}").json()['status'] == 'approved'
    me = client.get('/api/auth/me', headers={'Authorization': 'Bearer ' + token})
    assert me.status_code == 200 and me.json()['kind'] == 'executor' and me.json()['id'] == 'e1'


def test_c2_wrong_code(client, monkeypatch):
    token, conn = begin_connect(client)
    browser_login(client, monkeypatch)
    r = client.post(f"/connect/{conn['id']}", data={'code': 'ZZZZ-ZZZZ'})
    assert r.status_code == 400 and 'code' in r.text.lower()
    assert client.get(f"/api/connect/{conn['id']}").json()['status'] == 'pending'
    assert client.get('/api/auth/me', headers={'Authorization': 'Bearer ' + token}).status_code == 401


def test_c3_approve_needs_browser_session(client, database):
    token, conn = begin_connect(client)
    r = client.post(f"/api/connect/{conn['id']}/approve", json={'code': conn['code']}, headers=seed_session(database, 'e9', kind='executor'))
    assert r.status_code == 403 and r.json()['code'] == 'BROWSER_REQUIRED'
    r = client.post(f"/api/connect/{conn['id']}/approve", json={'code': conn['code']})
    assert r.status_code == 401


def test_c4_expired_connection(client, monkeypatch, database):
    token, conn = begin_connect(client)
    with psycopg.connect(database) as c:
        c.execute("update vw2_connections set expires_at = now() - interval '1 minute' where id = %s", (conn['id'],))
    assert client.get(f"/api/connect/{conn['id']}").status_code == 410
    browser_login(client, monkeypatch)
    assert client.post(f"/connect/{conn['id']}", data={'code': conn['code']}).status_code == 410


def test_c5_server_never_returns_a_token_and_approve_is_single_use(client, monkeypatch):
    token, conn = begin_connect(client)
    assert 'token' not in conn
    browser_login(client, monkeypatch)
    client.post(f"/connect/{conn['id']}", data={'code': conn['code']})
    status = client.get(f"/api/connect/{conn['id']}").json()
    assert 'token' not in status and status['status'] == 'approved'
    r = client.post(f"/connect/{conn['id']}", data={'code': conn['code']})
    assert r.status_code == 410


def test_c6_login_wrong_password(client, monkeypatch):
    monkeypatch.setattr(auth, 'shared_client', lambda: directory('sk', 'pw1'))
    r = client.post('/login', data={'username': 'sk', 'password': 'bad'})
    assert r.status_code == 401 and 'incorrect' in r.text.lower() and 'vw2_session' not in r.cookies
    assert client.get('/runs', follow_redirects=False).status_code == 303  # not signed in → login


def test_c7_c8_run_pages_and_admin(client, monkeypatch, alice, admin):
    r = client.post('/api/runs', json={'request_id': rid(), 'title': 'Alice film', 'procedure_version': 'test'}, headers=alice)
    code = r.json()['code']
    client.post(f"/api/runs/{r.json()['id']}/output", json={'request_id': rid(), 'stage': 's1', 'accepted_quote': 'yes'}, headers=alice)
    browser_login(client, monkeypatch, username='bob', password='pw2')  # directory user e1 ≠ alice
    assert client.get(f'/runs/{code}').status_code == 404
    client.post('/logout')
    browser_login(client, monkeypatch, username='root', password='pw3', role='Admin')
    page = client.get('/runs')
    assert page.status_code == 200 and 'Alice film' in page.text
    page = client.get(f'/runs/{code}')
    assert page.status_code == 200 and 's1' in page.text and 'yes' in page.text
    assert client.get('/defects').status_code == 200


def test_meta_and_claim(client, alice):
    assert 'plugin_min_version' in client.get('/api/meta').json()
    run = client.post('/api/runs', json={'request_id': rid(), 'procedure_version': 'test'}, headers=alice).json()
    r = client.post(f"/api/runs/{run['id']}/claim", json={'request_id': rid(), 'machine': 'mac-1'}, headers=alice)
    assert r.status_code == 200 and r.json()['active_machine'] == 'mac-1'
    assert client.get(f"/api/runs/{run['id']}/next", headers=alice).json()['active_machine'] == 'mac-1'
