"""Login ported from v1: shared employee directory (bcrypt in field ef-11, username in ef-02) + apps.members role."""
import json

import bcrypt
import httpx

from app import auth


def directory(username, password, role='Member'):
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    def handler(request):
        if request.url.path.endswith('/employees'):
            if username in request.url.query.decode():
                return httpx.Response(200, json=[{'employee_id': 'e1', 'field_values': [
                    {'fieldId': 'ef-01', 'value': 'Emp One'}, {'fieldId': 'ef-02', 'value': username}, {'fieldId': 'ef-11', 'value': hashed}]}])
            return httpx.Response(200, json=[])
        if request.url.path.endswith('/apps'):
            return httpx.Response(200, json=[{'members': [{'employeeId': 'e1', 'role': role}]}])
        return httpx.Response(404)

    return httpx.Client(base_url='https://shared.invalid/rest/v1', transport=httpx.MockTransport(handler))


def test_login_success_and_me_and_logout(client, monkeypatch):
    monkeypatch.setattr(auth, 'shared_client', lambda: directory('sk', 'pw1', 'Admin'))
    r = client.post('/api/auth/login', json={'username': 'sk', 'password': 'pw1', 'kind': 'executor'})
    assert r.status_code == 200, r.text
    tok = r.json()['token']
    me = client.get('/api/auth/me', headers={'Authorization': 'Bearer ' + tok})
    assert me.json() == {'id': 'e1', 'name': 'Emp One', 'role': 'Admin', 'kind': 'executor'}
    assert client.post('/api/auth/logout', headers={'Authorization': 'Bearer ' + tok}).status_code == 200
    assert client.get('/api/auth/me', headers={'Authorization': 'Bearer ' + tok}).status_code == 401


def test_login_wrong_password_and_unknown_user(client, monkeypatch):
    monkeypatch.setattr(auth, 'shared_client', lambda: directory('sk', 'pw1'))
    assert client.post('/api/auth/login', json={'username': 'sk', 'password': 'bad'}).status_code == 401
    assert client.post('/api/auth/login', json={'username': 'who', 'password': 'pw1'}).status_code == 401


def test_login_not_a_member(client, monkeypatch):
    monkeypatch.setattr(auth, 'shared_client', lambda: directory('sk', 'pw1', role='Guest'))
    r = client.post('/api/auth/login', json={'username': 'sk', 'password': 'pw1'})
    assert r.status_code == 403 and r.json()['code'] == 'MEMBERSHIP'
